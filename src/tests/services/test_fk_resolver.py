"""
Unit tests for FK Resolver Service.

Tests the foreign key resolution functionality including:
- Resolution dataclasses and enums
- CREATE, MAP, and SKIP resolution paths
- Entity creation for suppliers, ingredients, products
- Fuzzy search for mapping suggestions
- Dependency ordering
- Validation errors
"""

import pytest
from unittest.mock import MagicMock

from src.services.database import session_scope
from src.services.fk_resolver_service import (
    # Enums and dataclasses
    ResolutionChoice,
    MissingFK,
    Resolution,
    FKResolverCallback,
    # Exceptions
    FKResolutionError,
    EntityCreationError,
    # Entity creation
    _create_supplier,
    _create_ingredient,
    _create_product,
    # Fuzzy search
    find_similar_entities,
    # Core resolution
    resolve_missing_fks,
    collect_missing_fks,
    ENTITY_DEPENDENCY_ORDER,
)
from src.models.supplier import Supplier
from src.models.ingredient import Ingredient
from src.models.product import Product


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_supplier_data():
    """Sample supplier data for creation tests."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    return {
        "name": f"Test Supplier {unique_id}",
        "city": "Boston",
        "state": "MA",
        "zip_code": "02101",
        "street_address": "123 Main St",
        "notes": "Test notes",
    }


@pytest.fixture
def sample_ingredient_data():
    """Sample ingredient data for creation tests."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    return {
        "slug": f"test_ingredient_{unique_id}",
        "display_name": f"Test Ingredient {unique_id}",
        "category": "Testing",
        "description": "An ingredient for testing",
        "is_packaging": False,
    }


@pytest.fixture
def sample_product_data(sample_ingredient_data):
    """Sample product data for creation tests."""
    return {
        "ingredient_slug": sample_ingredient_data["slug"],
        "brand": "Test Brand",
        "product_name": "Test Product",
        "package_unit": "lb",
        "package_unit_quantity": 5.0,
        "package_size": "5 lb",
        "package_type": "bag",
    }


@pytest.fixture
def existing_ingredient(test_db, sample_ingredient_data):
    """Create an ingredient in the database for FK tests."""
    with session_scope() as session:
        ingredient = Ingredient(
            slug=sample_ingredient_data["slug"],
            display_name=sample_ingredient_data["display_name"],
            category=sample_ingredient_data["category"],
        )
        session.add(ingredient)
        session.flush()
        ingredient_id = ingredient.id
    return ingredient_id


@pytest.fixture
def existing_supplier(test_db, sample_supplier_data):
    """Create a supplier in the database for FK tests."""
    with session_scope() as session:
        supplier = Supplier(
            name=sample_supplier_data["name"],
            city=sample_supplier_data["city"],
            state=sample_supplier_data["state"],
            zip_code=sample_supplier_data["zip_code"],
        )
        session.add(supplier)
        session.flush()
        supplier_id = supplier.id
    return supplier_id


class MockResolver:
    """Mock resolver for testing that returns predetermined resolutions."""

    def __init__(self, resolutions: dict = None):
        """
        Initialize with a mapping of missing_value -> Resolution.

        Args:
            resolutions: Dict mapping missing_value to Resolution object
        """
        self.resolutions = resolutions or {}
        self.calls = []

    def resolve(self, missing: MissingFK) -> Resolution:
        """Return predetermined resolution or default to SKIP."""
        self.calls.append(missing)
        if missing.missing_value in self.resolutions:
            return self.resolutions[missing.missing_value]
        # Default: skip
        return Resolution(
            choice=ResolutionChoice.SKIP,
            entity_type=missing.entity_type,
            missing_value=missing.missing_value,
        )


# ============================================================================
# Test Dataclasses and Enums
# ============================================================================


class TestResolutionChoice:
    """Tests for ResolutionChoice enum."""

    def test_enum_values(self):
        """Verify all expected enum values exist."""
        assert ResolutionChoice.CREATE.value == "create"
        assert ResolutionChoice.MAP.value == "map"
        assert ResolutionChoice.SKIP.value == "skip"

    def test_enum_is_str(self):
        """Verify enum values are strings."""
        assert isinstance(ResolutionChoice.CREATE.value, str)
        assert str(ResolutionChoice.CREATE) == "ResolutionChoice.CREATE"


class TestMissingFK:
    """Tests for MissingFK dataclass."""

    def test_basic_creation(self):
        """Test creating a MissingFK with required fields."""
        missing = MissingFK(
            entity_type="supplier",
            missing_value="Unknown Supplier",
            field_name="supplier_name",
            affected_record_count=5,
        )
        assert missing.entity_type == "supplier"
        assert missing.missing_value == "Unknown Supplier"
        assert missing.field_name == "supplier_name"
        assert missing.affected_record_count == 5
        assert missing.sample_records == []

    def test_with_sample_records(self):
        """Test MissingFK with sample records."""
        samples = [{"id": 1, "name": "test"}]
        missing = MissingFK(
            entity_type="ingredient",
            missing_value="unknown_slug",
            field_name="ingredient_slug",
            affected_record_count=1,
            sample_records=samples,
        )
        assert len(missing.sample_records) == 1
        assert missing.sample_records[0]["id"] == 1


class TestResolution:
    """Tests for Resolution dataclass."""

    def test_skip_resolution(self):
        """Test creating a SKIP resolution."""
        resolution = Resolution(
            choice=ResolutionChoice.SKIP,
            entity_type="supplier",
            missing_value="Unknown",
        )
        assert resolution.choice == ResolutionChoice.SKIP
        assert resolution.mapped_id is None
        assert resolution.created_entity is None

    def test_map_resolution(self):
        """Test creating a MAP resolution."""
        resolution = Resolution(
            choice=ResolutionChoice.MAP,
            entity_type="ingredient",
            missing_value="flour",
            mapped_id=42,
        )
        assert resolution.choice == ResolutionChoice.MAP
        assert resolution.mapped_id == 42

    def test_create_resolution(self):
        """Test creating a CREATE resolution."""
        entity_data = {"name": "New Supplier", "city": "Boston"}
        resolution = Resolution(
            choice=ResolutionChoice.CREATE,
            entity_type="supplier",
            missing_value="New Supplier",
            created_entity=entity_data,
        )
        assert resolution.choice == ResolutionChoice.CREATE
        assert resolution.created_entity == entity_data


# ============================================================================
# Test Entity Creation
# ============================================================================


class TestCreateSupplier:
    """Tests for _create_supplier function."""

    def test_create_supplier_success(self, test_db, sample_supplier_data):
        """Test successful supplier creation."""
        with session_scope() as session:
            supplier_id = _create_supplier(sample_supplier_data, session)
            assert supplier_id is not None
            assert isinstance(supplier_id, int)

            # Verify supplier was created
            supplier = session.get(Supplier, supplier_id)
            assert supplier.name == sample_supplier_data["name"]
            assert supplier.city == sample_supplier_data["city"]
            assert supplier.state == "MA"
            assert supplier.is_active is True

    def test_create_supplier_normalizes_state(self, test_db):
        """Test that state is normalized to uppercase."""
        with session_scope() as session:
            data = {
                "name": "Lowercase State Supplier",
                "city": "Portland",
                "state": "or",  # lowercase
                "zip_code": "97201",
            }
            supplier_id = _create_supplier(data, session)
            supplier = session.get(Supplier, supplier_id)
            assert supplier.state == "OR"

    def test_create_supplier_missing_required_field(self, test_db):
        """Test that missing required fields raise EntityCreationError."""
        with session_scope() as session:
            data = {"name": "Incomplete Supplier"}  # Missing city, state, zip
            with pytest.raises(EntityCreationError) as exc_info:
                _create_supplier(data, session)
            assert exc_info.value.entity_type == "supplier"
            assert "city" in exc_info.value.missing_fields


class TestCreateIngredient:
    """Tests for _create_ingredient function."""

    def test_create_ingredient_success(self, test_db):
        """Test successful ingredient creation."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        with session_scope() as session:
            data = {
                "slug": f"new_test_ingredient_{unique_id}",
                "display_name": f"New Test Ingredient {unique_id}",
                "category": "Testing",
            }
            ingredient_id = _create_ingredient(data, session)
            assert ingredient_id is not None

            ingredient = session.get(Ingredient, ingredient_id)
            assert ingredient.slug == data["slug"]
            assert ingredient.display_name == data["display_name"]

    def test_create_ingredient_missing_slug(self, test_db):
        """Test that missing slug raises EntityCreationError."""
        with session_scope() as session:
            data = {"display_name": "No Slug", "category": "Testing"}
            with pytest.raises(EntityCreationError) as exc_info:
                _create_ingredient(data, session)
            assert "slug" in exc_info.value.missing_fields


class TestCreateProduct:
    """Tests for _create_product function."""

    def test_create_product_with_ingredient_id(self, existing_ingredient):
        """Test creating product with explicit ingredient_id."""
        with session_scope() as session:
            data = {
                "package_unit": "oz",
                "package_unit_quantity": 16.0,
                "brand": "Test Brand",
            }
            product_id = _create_product(data, session, ingredient_id=existing_ingredient)
            assert product_id is not None

            product = session.get(Product, product_id)
            assert product.ingredient_id == existing_ingredient
            assert product.package_unit == "oz"

    def test_create_product_with_ingredient_slug(self, existing_ingredient, sample_ingredient_data):
        """Test creating product by resolving ingredient_slug."""
        with session_scope() as session:
            data = {
                "ingredient_slug": sample_ingredient_data["slug"],
                "package_unit": "lb",
                "package_unit_quantity": 5.0,
            }
            product_id = _create_product(data, session)
            assert product_id is not None

            product = session.get(Product, product_id)
            assert product.ingredient_id == existing_ingredient

    def test_create_product_missing_ingredient(self, test_db):
        """Test that missing ingredient raises error."""
        with session_scope() as session:
            data = {
                "ingredient_slug": "nonexistent_ingredient",
                "package_unit": "lb",
                "package_unit_quantity": 5.0,
            }
            with pytest.raises(FKResolutionError):
                _create_product(data, session)

    def test_create_product_missing_package_info(self, existing_ingredient):
        """Test that missing package info raises EntityCreationError."""
        with session_scope() as session:
            data = {"brand": "No Package Info"}
            with pytest.raises(EntityCreationError) as exc_info:
                _create_product(data, session, ingredient_id=existing_ingredient)
            assert "package_unit" in exc_info.value.missing_fields


# ============================================================================
# Test Fuzzy Search
# ============================================================================


class TestFindSimilarEntities:
    """Tests for find_similar_entities function."""

    def test_find_similar_suppliers(self, existing_supplier, sample_supplier_data):
        """Test finding similar suppliers by name."""
        with session_scope() as session:
            # Search using the unique part of the name
            results = find_similar_entities(
                "supplier",
                sample_supplier_data["name"],  # Full name with unique suffix
                session,
            )
            assert len(results) >= 1
            # Just verify we got results containing "Test Supplier"
            assert any("Test Supplier" in r["name"] for r in results)

    def test_find_similar_ingredients(self, existing_ingredient, sample_ingredient_data):
        """Test finding similar ingredients by display_name."""
        with session_scope() as session:
            # Search using the unique part of the name
            results = find_similar_entities(
                "ingredient",
                sample_ingredient_data["display_name"],  # Full name with unique suffix
                session,
            )
            assert len(results) >= 1
            # Just verify we got results containing "Test Ingredient"
            assert any("Test Ingredient" in r["display_name"] for r in results)

    def test_find_similar_case_insensitive(self, existing_supplier, sample_supplier_data):
        """Test that search is case-insensitive."""
        with session_scope() as session:
            results = find_similar_entities(
                "supplier",
                sample_supplier_data["name"].upper(),
                session,
            )
            assert len(results) >= 1

    def test_find_similar_no_matches(self, test_db):
        """Test that no matches returns empty list."""
        with session_scope() as session:
            results = find_similar_entities(
                "supplier",
                "xyznonexistent12345",
                session,
            )
            assert results == []

    def test_find_similar_respects_limit(self, existing_supplier):
        """Test that limit parameter works."""
        with session_scope() as session:
            results = find_similar_entities("supplier", "a", session, limit=2)
            assert len(results) <= 2


# ============================================================================
# Test Core Resolution Logic
# ============================================================================


class TestResolveMissingFks:
    """Tests for resolve_missing_fks function."""

    def test_skip_resolution_no_mapping(self, test_db):
        """Test that SKIP resolution creates no mapping entry."""
        missing = [
            MissingFK(
                entity_type="supplier",
                missing_value="Unknown",
                field_name="supplier_name",
                affected_record_count=1,
            )
        ]
        resolver = MockResolver()

        with session_scope() as session:
            mapping, resolutions = resolve_missing_fks(missing, resolver, session)

        assert "Unknown" not in mapping["supplier"]
        assert len(resolutions) == 1
        assert resolutions[0].choice == ResolutionChoice.SKIP

    def test_map_resolution_stores_id(self, existing_supplier):
        """Test that MAP resolution stores the mapped ID."""
        missing = [
            MissingFK(
                entity_type="supplier",
                missing_value="Some Supplier",
                field_name="supplier_name",
                affected_record_count=1,
            )
        ]
        resolver = MockResolver(
            {
                "Some Supplier": Resolution(
                    choice=ResolutionChoice.MAP,
                    entity_type="supplier",
                    missing_value="Some Supplier",
                    mapped_id=existing_supplier,
                )
            }
        )

        with session_scope() as session:
            mapping, resolutions = resolve_missing_fks(missing, resolver, session)

        assert mapping["supplier"]["Some Supplier"] == existing_supplier
        assert resolutions[0].choice == ResolutionChoice.MAP

    def test_create_resolution_creates_entity(self, test_db):
        """Test that CREATE resolution creates entity and stores ID."""
        missing = [
            MissingFK(
                entity_type="supplier",
                missing_value="New Vendor",
                field_name="supplier_name",
                affected_record_count=1,
            )
        ]
        resolver = MockResolver(
            {
                "New Vendor": Resolution(
                    choice=ResolutionChoice.CREATE,
                    entity_type="supplier",
                    missing_value="New Vendor",
                    created_entity={
                        "name": "New Vendor",
                        "city": "Chicago",
                        "state": "IL",
                        "zip_code": "60601",
                    },
                )
            }
        )

        with session_scope() as session:
            mapping, resolutions = resolve_missing_fks(missing, resolver, session)

            assert "New Vendor" in mapping["supplier"]
            supplier_id = mapping["supplier"]["New Vendor"]

            # Verify supplier was created
            supplier = session.get(Supplier, supplier_id)
            assert supplier.name == "New Vendor"
            assert supplier.city == "Chicago"

    def test_dependency_ordering(self, test_db):
        """Test that suppliers/ingredients are resolved before products."""
        missing = [
            MissingFK(
                entity_type="product",
                missing_value="Unknown Product",
                field_name="product_key",
                affected_record_count=1,
            ),
            MissingFK(
                entity_type="supplier",
                missing_value="Unknown Supplier",
                field_name="supplier_name",
                affected_record_count=1,
            ),
            MissingFK(
                entity_type="ingredient",
                missing_value="unknown_ingredient",
                field_name="ingredient_slug",
                affected_record_count=1,
            ),
        ]
        resolver = MockResolver()

        with session_scope() as session:
            mapping, resolutions = resolve_missing_fks(missing, resolver, session)

        # Verify order: supplier first, then ingredient, then product
        call_order = [call.entity_type for call in resolver.calls]
        supplier_idx = call_order.index("supplier")
        ingredient_idx = call_order.index("ingredient")
        product_idx = call_order.index("product")

        assert supplier_idx < product_idx
        assert ingredient_idx < product_idx

    def test_resolver_called_for_each_missing(self, test_db):
        """Test that resolver is called once for each missing FK."""
        missing = [
            MissingFK(
                entity_type="supplier",
                missing_value="Supplier A",
                field_name="supplier_name",
                affected_record_count=1,
            ),
            MissingFK(
                entity_type="supplier",
                missing_value="Supplier B",
                field_name="supplier_name",
                affected_record_count=2,
            ),
        ]
        resolver = MockResolver()

        with session_scope() as session:
            resolve_missing_fks(missing, resolver, session)

        assert len(resolver.calls) == 2
        assert resolver.calls[0].missing_value == "Supplier A"
        assert resolver.calls[1].missing_value == "Supplier B"


class TestCollectMissingFks:
    """Tests for collect_missing_fks function."""

    def test_collect_missing_suppliers(self, existing_supplier, sample_supplier_data):
        """Test collecting missing supplier references."""
        records = [
            {"supplier_name": sample_supplier_data["name"]},  # Exists
            {"supplier_name": "Nonexistent Supplier"},  # Missing
            {"supplier_name": "Nonexistent Supplier"},  # Same missing (counted)
        ]

        with session_scope() as session:
            missing = collect_missing_fks(
                records,
                "purchase",
                {"supplier_name": "supplier"},
                session,
            )

        assert len(missing) == 1
        assert missing[0].missing_value == "Nonexistent Supplier"
        assert missing[0].affected_record_count == 2
        assert missing[0].entity_type == "supplier"

    def test_collect_missing_ingredients(self, existing_ingredient, sample_ingredient_data):
        """Test collecting missing ingredient references."""
        records = [
            {"ingredient_slug": sample_ingredient_data["slug"]},  # Exists
            {"ingredient_slug": "nonexistent_slug"},  # Missing
        ]

        with session_scope() as session:
            missing = collect_missing_fks(
                records,
                "product",
                {"ingredient_slug": "ingredient"},
                session,
            )

        assert len(missing) == 1
        assert missing[0].missing_value == "nonexistent_slug"
        assert missing[0].entity_type == "ingredient"

    def test_collect_multiple_fk_types(self, existing_supplier, existing_ingredient):
        """Test collecting missing FKs of different types."""
        records = [
            {
                "supplier_name": "Missing Supplier",
                "ingredient_slug": "missing_ingredient",
            }
        ]

        with session_scope() as session:
            missing = collect_missing_fks(
                records,
                "combined",
                {"supplier_name": "supplier", "ingredient_slug": "ingredient"},
                session,
            )

        assert len(missing) == 2
        entity_types = {m.entity_type for m in missing}
        assert "supplier" in entity_types
        assert "ingredient" in entity_types

    def test_sample_records_limited_to_three(self, test_db):
        """Test that sample_records is limited to 3."""
        records = [
            {"supplier_name": "Missing Supplier", "id": i}
            for i in range(10)
        ]

        with session_scope() as session:
            missing = collect_missing_fks(
                records,
                "purchase",
                {"supplier_name": "supplier"},
                session,
            )

        assert len(missing) == 1
        assert len(missing[0].sample_records) == 3


class TestDependencyOrder:
    """Tests for ENTITY_DEPENDENCY_ORDER constant."""

    def test_order_contains_expected_entities(self):
        """Verify dependency order contains expected entity types."""
        assert "supplier" in ENTITY_DEPENDENCY_ORDER
        assert "ingredient" in ENTITY_DEPENDENCY_ORDER
        assert "product" in ENTITY_DEPENDENCY_ORDER

    def test_product_is_last(self):
        """Verify product comes after supplier and ingredient."""
        product_idx = ENTITY_DEPENDENCY_ORDER.index("product")
        supplier_idx = ENTITY_DEPENDENCY_ORDER.index("supplier")
        ingredient_idx = ENTITY_DEPENDENCY_ORDER.index("ingredient")

        assert product_idx > supplier_idx
        assert product_idx > ingredient_idx
