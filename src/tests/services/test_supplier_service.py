"""Tests for Supplier Service (Feature 027, 050).

Tests cover:
- Create supplier with validation
- Get supplier by ID and UUID
- Get all suppliers (active/inactive filtering)
- Get active suppliers for dropdowns
- Update supplier attributes
- Deactivate supplier with product cascade (FR-009)
- Reactivate supplier
- Delete supplier (with/without purchases)
- Error handling for not found cases
- Slug generation (Feature 050)
"""

import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.base import Base
from src.models.supplier import Supplier
from src.models.ingredient import Ingredient
from src.models.product import Product
from src.models.purchase import Purchase
from src.services import supplier_service
from src.services.supplier_service import generate_supplier_slug
from src.services.exceptions import SupplierNotFoundError


@pytest.fixture
def engine():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create database session for testing."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def test_ingredient(session):
    """Create a test ingredient."""
    ingredient = Ingredient(
        display_name="Test Flour",
        slug="test-flour",
        category="Flour",
    )
    session.add(ingredient)
    session.flush()
    return ingredient


@pytest.fixture
def test_product(session, test_ingredient):
    """Create a test product."""
    product = Product(
        ingredient_id=test_ingredient.id,
        product_name="Test Product",
        package_unit="lb",
        package_unit_quantity=5.0,
    )
    session.add(product)
    session.flush()
    return product


class TestCreateSupplier:
    """Tests for create_supplier function."""

    def test_create_supplier_success(self, session):
        """Test creating a supplier with valid data."""
        result = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        assert result["name"] == "Costco"
        assert result["city"] == "Issaquah"
        assert result["state"] == "WA"
        assert result["zip_code"] == "98027"
        assert result["is_active"] is True
        assert "id" in result
        assert "uuid" in result

    def test_create_supplier_with_optional_fields(self, session):
        """Test creating a supplier with all optional fields."""
        result = supplier_service.create_supplier(
            name="Wegmans",
            city="Rochester",
            state="NY",
            zip_code="14624",
            street_address="123 Main St",
            notes="Great bakery selection",
            session=session,
        )

        assert result["street_address"] == "123 Main St"
        assert result["notes"] == "Great bakery selection"

    def test_create_supplier_normalizes_state(self, session):
        """Test that state is uppercased."""
        result = supplier_service.create_supplier(
            name="Test Store",
            city="Boston",
            state="ma",  # lowercase
            zip_code="02101",
            session=session,
        )

        assert result["state"] == "MA"

    def test_create_supplier_validates_state_length(self, session):
        """Test that state must be 2 characters."""
        with pytest.raises(ValueError) as exc_info:
            supplier_service.create_supplier(
                name="Test Store",
                city="Boston",
                state="MAS",  # Too long
                zip_code="02101",
                session=session,
            )

        assert "2-letter code" in str(exc_info.value)

    def test_create_supplier_validates_state_too_short(self, session):
        """Test that single character state is rejected."""
        with pytest.raises(ValueError) as exc_info:
            supplier_service.create_supplier(
                name="Test Store",
                city="Boston",
                state="M",  # Too short
                zip_code="02101",
                session=session,
            )

        assert "2-letter code" in str(exc_info.value)


class TestGetSupplier:
    """Tests for get_supplier and get_supplier_by_uuid functions."""

    def test_get_supplier_by_id(self, session):
        """Test retrieving supplier by ID."""
        created = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        result = supplier_service.get_supplier(created["id"], session=session)

        assert result is not None
        assert result["name"] == "Costco"

    def test_get_supplier_not_found(self, session):
        """Test that get_supplier raises SupplierNotFoundError for missing ID."""
        import pytest
        from src.services.exceptions import SupplierNotFoundError

        with pytest.raises(SupplierNotFoundError):
            supplier_service.get_supplier(999, session=session)

    def test_get_supplier_by_uuid(self, session):
        """Test retrieving supplier by UUID."""
        created = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        result = supplier_service.get_supplier_by_uuid(created["uuid"], session=session)

        assert result is not None
        assert result["name"] == "Costco"
        assert result["id"] == created["id"]

    def test_get_supplier_by_uuid_not_found(self, session):
        """Test that get_supplier_by_uuid raises SupplierNotFoundError for missing UUID."""
        import pytest
        from src.services.exceptions import SupplierNotFoundError

        with pytest.raises(SupplierNotFoundError):
            supplier_service.get_supplier_by_uuid(
                "00000000-0000-0000-0000-000000000000",
                session=session,
            )

    def test_get_supplier_or_raise_success(self, session):
        """Test get_supplier_or_raise returns supplier."""
        created = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        result = supplier_service.get_supplier_or_raise(created["id"], session=session)

        assert result["name"] == "Costco"

    def test_get_supplier_or_raise_not_found(self, session):
        """Test get_supplier_or_raise raises exception."""
        with pytest.raises(SupplierNotFoundError) as exc_info:
            supplier_service.get_supplier_or_raise(999, session=session)

        assert exc_info.value.supplier_id == 999


class TestGetAllSuppliers:
    """Tests for get_all_suppliers and get_active_suppliers functions."""

    def test_get_all_suppliers_active_only(self, session):
        """Test getting only active suppliers."""
        # Create active supplier
        supplier_service.create_supplier(
            name="Active Store",
            city="Boston",
            state="MA",
            zip_code="02101",
            session=session,
        )

        # Create and deactivate another supplier
        inactive = supplier_service.create_supplier(
            name="Inactive Store",
            city="Boston",
            state="MA",
            zip_code="02102",
            session=session,
        )
        supplier_service.deactivate_supplier(inactive["id"], session=session)

        results = supplier_service.get_all_suppliers(include_inactive=False, session=session)

        assert len(results) == 1
        assert results[0]["name"] == "Active Store"

    def test_get_all_suppliers_includes_inactive(self, session):
        """Test getting all suppliers including inactive."""
        supplier_service.create_supplier(
            name="Active Store",
            city="Boston",
            state="MA",
            zip_code="02101",
            session=session,
        )

        inactive = supplier_service.create_supplier(
            name="Inactive Store",
            city="Boston",
            state="MA",
            zip_code="02102",
            session=session,
        )
        supplier_service.deactivate_supplier(inactive["id"], session=session)

        results = supplier_service.get_all_suppliers(include_inactive=True, session=session)

        assert len(results) == 2

    def test_get_all_suppliers_sorted_by_name(self, session):
        """Test that suppliers are sorted by name."""
        supplier_service.create_supplier(
            name="Zebra Store", city="A", state="MA", zip_code="02101", session=session
        )
        supplier_service.create_supplier(
            name="Alpha Store", city="B", state="MA", zip_code="02102", session=session
        )
        supplier_service.create_supplier(
            name="Middle Store", city="C", state="MA", zip_code="02103", session=session
        )

        results = supplier_service.get_all_suppliers(session=session)

        assert results[0]["name"] == "Alpha Store"
        assert results[1]["name"] == "Middle Store"
        assert results[2]["name"] == "Zebra Store"

    def test_get_active_suppliers(self, session):
        """Test get_active_suppliers convenience method."""
        supplier_service.create_supplier(
            name="Active Store",
            city="Boston",
            state="MA",
            zip_code="02101",
            session=session,
        )

        inactive = supplier_service.create_supplier(
            name="Inactive Store",
            city="Boston",
            state="MA",
            zip_code="02102",
            session=session,
        )
        supplier_service.deactivate_supplier(inactive["id"], session=session)

        results = supplier_service.get_active_suppliers(session=session)

        assert len(results) == 1
        assert all(s["is_active"] for s in results)


class TestUpdateSupplier:
    """Tests for update_supplier function."""

    def test_update_supplier_single_field(self, session):
        """Test updating a single field."""
        created = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        result = supplier_service.update_supplier(
            created["id"],
            name="Costco Business Center",
            session=session,
        )

        assert result["name"] == "Costco Business Center"
        assert result["city"] == "Issaquah"  # Unchanged

    def test_update_supplier_multiple_fields(self, session):
        """Test updating multiple fields."""
        created = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        result = supplier_service.update_supplier(
            created["id"],
            name="New Name",
            city="New City",
            notes="New notes",
            session=session,
        )

        assert result["name"] == "New Name"
        assert result["city"] == "New City"
        assert result["notes"] == "New notes"

    def test_update_supplier_normalizes_state(self, session):
        """Test that state is uppercased on update."""
        created = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        result = supplier_service.update_supplier(
            created["id"],
            state="ca",  # lowercase
            session=session,
        )

        assert result["state"] == "CA"

    def test_update_supplier_validates_state(self, session):
        """Test that invalid state is rejected on update."""
        created = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        with pytest.raises(ValueError) as exc_info:
            supplier_service.update_supplier(
                created["id"],
                state="WAA",  # Too long
                session=session,
            )

        assert "2-letter code" in str(exc_info.value)

    def test_update_supplier_not_found(self, session):
        """Test updating non-existent supplier raises error."""
        with pytest.raises(SupplierNotFoundError) as exc_info:
            supplier_service.update_supplier(999, name="Test", session=session)

        assert exc_info.value.supplier_id == 999


class TestDeactivateSupplier:
    """Tests for deactivate_supplier function."""

    def test_deactivate_supplier_success(self, session):
        """Test deactivating a supplier."""
        created = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        result = supplier_service.deactivate_supplier(created["id"], session=session)

        assert result["is_active"] is False

    def test_deactivate_supplier_clears_product_references(self, session, test_ingredient):
        """Test that deactivation clears product.preferred_supplier_id (FR-009)."""
        # Create supplier
        supplier = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        # Create product with preferred supplier
        product = Product(
            ingredient_id=test_ingredient.id,
            product_name="Test Product",
            package_unit="lb",
            package_unit_quantity=5.0,
            preferred_supplier_id=supplier["id"],
        )
        session.add(product)
        session.flush()

        assert product.preferred_supplier_id == supplier["id"]

        # Deactivate supplier
        supplier_service.deactivate_supplier(supplier["id"], session=session)

        # Verify product reference was cleared
        session.refresh(product)
        assert product.preferred_supplier_id is None

    def test_deactivate_supplier_clears_multiple_products(self, session, test_ingredient):
        """Test that deactivation clears all affected products."""
        supplier = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        # Create multiple products with same preferred supplier
        products = []
        for i in range(3):
            product = Product(
                ingredient_id=test_ingredient.id,
                product_name=f"Test Product {i}",
                package_unit="lb",
                package_unit_quantity=5.0,
                preferred_supplier_id=supplier["id"],
            )
            session.add(product)
            products.append(product)
        session.flush()

        # Deactivate supplier
        supplier_service.deactivate_supplier(supplier["id"], session=session)

        # Verify all product references were cleared
        for product in products:
            session.refresh(product)
            assert product.preferred_supplier_id is None

    def test_deactivate_supplier_not_found(self, session):
        """Test deactivating non-existent supplier raises error."""
        with pytest.raises(SupplierNotFoundError):
            supplier_service.deactivate_supplier(999, session=session)


class TestReactivateSupplier:
    """Tests for reactivate_supplier function."""

    def test_reactivate_supplier_success(self, session):
        """Test reactivating a deactivated supplier."""
        created = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        # Deactivate then reactivate
        supplier_service.deactivate_supplier(created["id"], session=session)
        result = supplier_service.reactivate_supplier(created["id"], session=session)

        assert result["is_active"] is True

    def test_reactivate_supplier_not_found(self, session):
        """Test reactivating non-existent supplier raises error."""
        with pytest.raises(SupplierNotFoundError):
            supplier_service.reactivate_supplier(999, session=session)


class TestDeleteSupplier:
    """Tests for delete_supplier function."""

    def test_delete_supplier_success(self, session):
        """Test deleting a supplier with no purchases."""
        import pytest
        from src.services.exceptions import SupplierNotFoundError

        created = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        result = supplier_service.delete_supplier(created["id"], session=session)

        assert result is True

        # Verify supplier is gone - should raise SupplierNotFoundError
        with pytest.raises(SupplierNotFoundError):
            supplier_service.get_supplier(created["id"], session=session)

    def test_delete_supplier_with_purchases_fails(self, session, test_product):
        """Test that deleting supplier with purchases raises error."""
        # Create supplier
        supplier_data = supplier_service.create_supplier(
            name="Costco",
            city="Issaquah",
            state="WA",
            zip_code="98027",
            session=session,
        )

        # Create a purchase for this supplier
        purchase = Purchase(
            product_id=test_product.id,
            supplier_id=supplier_data["id"],
            purchase_date=date.today(),
            unit_price=Decimal("9.99"),
            quantity_purchased=1,
        )
        session.add(purchase)
        session.flush()

        # Attempt to delete should fail
        with pytest.raises(ValueError) as exc_info:
            supplier_service.delete_supplier(supplier_data["id"], session=session)

        assert "Cannot delete supplier" in str(exc_info.value)
        assert "1 purchases" in str(exc_info.value)
        assert "Deactivate instead" in str(exc_info.value)

    def test_delete_supplier_not_found(self, session):
        """Test deleting non-existent supplier raises error."""
        with pytest.raises(SupplierNotFoundError):
            supplier_service.delete_supplier(999, session=session)


class TestSupplierSlugGeneration:
    """Tests for supplier slug generation (Feature 050)."""

    def test_physical_supplier_slug(self):
        """Physical supplier slug includes name, city, and state."""
        slug = generate_supplier_slug(
            name="Wegmans",
            supplier_type="physical",
            city="Burlington",
            state="MA",
        )
        assert slug == "wegmans_burlington_ma"

    def test_online_supplier_slug(self):
        """Online supplier slug is name only, no city/state."""
        slug = generate_supplier_slug(
            name="King Arthur Baking",
            supplier_type="online",
        )
        assert slug == "king_arthur_baking"

    def test_slug_unicode_normalization(self):
        """Accented characters are normalized to ASCII equivalents."""
        slug = generate_supplier_slug(
            name="Cafe Creme",
            supplier_type="online",
        )
        assert slug == "cafe_creme"

    def test_slug_special_characters_removed(self):
        """Special characters removed, spaces become underscores."""
        slug = generate_supplier_slug(
            name="Bob's Market & Deli",
            supplier_type="physical",
            city="New York",
            state="NY",
        )
        assert slug == "bobs_market_deli_new_york_ny"

    def test_slug_hyphens_converted_to_underscores(self):
        """Hyphens are converted to underscores."""
        slug = generate_supplier_slug(
            name="Whole-Foods",
            supplier_type="physical",
            city="Cambridge",
            state="MA",
        )
        assert slug == "whole_foods_cambridge_ma"

    def test_slug_multiple_spaces_collapsed(self):
        """Multiple consecutive spaces become single underscore."""
        slug = generate_supplier_slug(
            name="Test   Store",
            supplier_type="physical",
            city="Boston",
            state="MA",
        )
        assert slug == "test_store_boston_ma"

    def test_slug_leading_trailing_spaces_stripped(self):
        """Leading and trailing spaces are stripped."""
        slug = generate_supplier_slug(
            name="  Store Name  ",
            supplier_type="physical",
            city="  City  ",
            state="MA",
        )
        assert slug == "store_name_city_ma"

    def test_physical_supplier_missing_city(self):
        """Physical supplier with only state in location."""
        slug = generate_supplier_slug(
            name="Rural Store",
            supplier_type="physical",
            city=None,
            state="VT",
        )
        assert slug == "rural_store_vt"

    def test_physical_supplier_missing_state(self):
        """Physical supplier with only city in location."""
        slug = generate_supplier_slug(
            name="City Market",
            supplier_type="physical",
            city="Burlington",
            state=None,
        )
        assert slug == "city_market_burlington"

    def test_slug_conflict_resolution(self, session):
        """Duplicate slugs get numeric suffix _1, _2, etc."""
        # Create first supplier with slug "test_store_boston_ma"
        supplier1 = Supplier(
            name="Test Store",
            slug="test_store_boston_ma",
            supplier_type="physical",
            city="Boston",
            state="MA",
        )
        session.add(supplier1)
        session.flush()

        # Generate slug for supplier with same details
        slug = generate_supplier_slug(
            name="Test Store",
            supplier_type="physical",
            city="Boston",
            state="MA",
            session=session,
        )

        assert slug == "test_store_boston_ma_1"

    def test_slug_conflict_resolution_multiple(self, session):
        """Multiple conflicts increment suffix correctly."""
        # Create suppliers with base slug and _1 suffix
        supplier1 = Supplier(
            name="Test Store",
            slug="test_store_boston_ma",
            supplier_type="physical",
            city="Boston",
            state="MA",
        )
        supplier2 = Supplier(
            name="Test Store 2",
            slug="test_store_boston_ma_1",
            supplier_type="physical",
            city="Boston",
            state="MA",
        )
        session.add(supplier1)
        session.add(supplier2)
        session.flush()

        # Generate slug for third supplier with same details
        slug = generate_supplier_slug(
            name="Test Store",
            supplier_type="physical",
            city="Boston",
            state="MA",
            session=session,
        )

        assert slug == "test_store_boston_ma_2"

    def test_identical_suppliers_same_location(self, session):
        """Two suppliers with identical names in same city get different slugs (Edge case per FR-004)."""
        # First "Costco" in Burlington, MA
        supplier1 = Supplier(
            name="Costco",
            slug="costco_burlington_ma",
            supplier_type="physical",
            city="Burlington",
            state="MA",
        )
        session.add(supplier1)
        session.flush()

        # Second "Costco" opening in same location
        slug = generate_supplier_slug(
            name="Costco",
            supplier_type="physical",
            city="Burlington",
            state="MA",
            session=session,
        )

        # Conflict resolved with numeric suffix
        assert slug == "costco_burlington_ma_1"

    def test_slug_without_session_no_uniqueness_check(self):
        """Without session, returns base slug without uniqueness check."""
        # Even if duplicates would exist, returns base slug
        slug1 = generate_supplier_slug(
            name="Test Store",
            supplier_type="physical",
            city="Boston",
            state="MA",
        )
        slug2 = generate_supplier_slug(
            name="Test Store",
            supplier_type="physical",
            city="Boston",
            state="MA",
        )
        # Both return same base slug (no session = no uniqueness check)
        assert slug1 == slug2 == "test_store_boston_ma"


class TestSupplierCreationWithAutoSlug:
    """Tests for automatic slug generation on supplier creation (T010)."""

    def test_create_supplier_generates_slug(self, session):
        """Creating supplier auto-generates slug based on name/city/state."""
        result = supplier_service.create_supplier(
            name="Test Store",
            supplier_type="physical",
            city="Boston",
            state="MA",
            zip_code="02101",
            session=session,
        )

        assert result["slug"] == "test_store_boston_ma"

    def test_create_online_supplier_generates_slug(self, session):
        """Online supplier slug uses name only (no city/state)."""
        result = supplier_service.create_supplier(
            name="Amazon Fresh",
            supplier_type="online",
            website_url="https://www.amazon.com/fresh",
            session=session,
        )

        assert result["slug"] == "amazon_fresh"

    def test_create_supplier_slug_handles_conflicts(self, session):
        """Creating suppliers with same name/location gets numeric suffix."""
        # Create first supplier
        result1 = supplier_service.create_supplier(
            name="Costco",
            supplier_type="physical",
            city="Burlington",
            state="MA",
            zip_code="01803",
            session=session,
        )
        assert result1["slug"] == "costco_burlington_ma"

        # Create second supplier with same details
        result2 = supplier_service.create_supplier(
            name="Costco",
            supplier_type="physical",
            city="Burlington",
            state="MA",
            zip_code="01803",
            session=session,
        )
        assert result2["slug"] == "costco_burlington_ma_1"

    def test_created_supplier_has_slug_in_dict(self, session):
        """Verify slug is included in to_dict() output."""
        result = supplier_service.create_supplier(
            name="Wegmans",
            supplier_type="physical",
            city="Burlington",
            state="MA",
            zip_code="01803",
            session=session,
        )

        assert "slug" in result
        assert result["slug"] == "wegmans_burlington_ma"


class TestMigrateSupplierSlugs:
    """Tests for migrate_supplier_slugs() function (T011, T012)."""

    def test_migration_generates_slugs_for_all(self, session):
        """Migration assigns slugs to all suppliers."""
        # Create suppliers with placeholder slugs (simulating pre-migration state)
        supplier1 = Supplier(
            name="Store A",
            slug="placeholder_1",
            supplier_type="physical",
            city="Boston",
            state="MA",
            zip_code="02101",
        )
        supplier2 = Supplier(
            name="Store B",
            slug="placeholder_2",
            supplier_type="physical",
            city="Cambridge",
            state="MA",
            zip_code="02139",
        )
        session.add(supplier1)
        session.add(supplier2)
        session.flush()

        # Run migration
        from src.services.supplier_service import migrate_supplier_slugs

        result = migrate_supplier_slugs(session=session)

        # Verify all suppliers got proper slugs
        assert result["migrated"] == 2
        assert supplier1.slug == "store_a_boston_ma"
        assert supplier2.slug == "store_b_cambridge_ma"

    def test_migration_regenerates_existing_slugs(self, session):
        """Migration regenerates even existing slugs (per clarification)."""
        # Create supplier with non-standard slug
        supplier = Supplier(
            name="Test Store",
            slug="wrong_format_slug",
            supplier_type="physical",
            city="Boston",
            state="MA",
            zip_code="02101",
        )
        session.add(supplier)
        session.flush()

        # Run migration
        from src.services.supplier_service import migrate_supplier_slugs

        result = migrate_supplier_slugs(session=session)

        # Verify slug was regenerated
        assert result["migrated"] == 1
        assert supplier.slug == "test_store_boston_ma"

    def test_migration_handles_conflicts(self, session):
        """Duplicate names get numeric suffixes during migration."""
        # Create two suppliers that would have the same slug
        supplier1 = Supplier(
            name="Costco",
            slug="temp_1",
            supplier_type="physical",
            city="Burlington",
            state="MA",
            zip_code="01803",
        )
        supplier2 = Supplier(
            name="Costco",
            slug="temp_2",
            supplier_type="physical",
            city="Burlington",
            state="MA",
            zip_code="01803",
        )
        session.add(supplier1)
        session.add(supplier2)
        session.flush()

        # Run migration
        from src.services.supplier_service import migrate_supplier_slugs

        result = migrate_supplier_slugs(session=session)

        # Verify one has the base slug and one has _1 suffix
        assert result["migrated"] == 2
        assert result["conflicts"] == 1  # Second one needed suffix
        slugs = {supplier1.slug, supplier2.slug}
        assert "costco_burlington_ma" in slugs
        assert "costco_burlington_ma_1" in slugs

    def test_migration_idempotent(self, session):
        """Running migration multiple times produces same result."""
        # Create supplier
        supplier = Supplier(
            name="Test Store",
            slug="temp_slug",
            supplier_type="physical",
            city="Boston",
            state="MA",
            zip_code="02101",
        )
        session.add(supplier)
        session.flush()

        # Run migration twice
        from src.services.supplier_service import migrate_supplier_slugs

        result1 = migrate_supplier_slugs(session=session)
        slug_after_first = supplier.slug

        result2 = migrate_supplier_slugs(session=session)
        slug_after_second = supplier.slug

        # Slug should be the same after both migrations
        assert slug_after_first == slug_after_second == "test_store_boston_ma"

    def test_malformed_slug_regenerated(self, session):
        """Malformed slugs (uppercase, spaces) are corrected during migration (T012)."""
        # Insert supplier with malformed slug
        supplier = Supplier(
            name="Test Store",
            slug="UPPERCASE_SLUG",  # Wrong format
            supplier_type="physical",
            city="Boston",
            state="MA",
            zip_code="02101",
        )
        session.add(supplier)
        session.flush()

        # Run migration
        from src.services.supplier_service import migrate_supplier_slugs

        result = migrate_supplier_slugs(session=session)

        # Verify slug is now proper format
        assert result["migrated"] == 1
        assert supplier.slug == "test_store_boston_ma"

    def test_migration_online_supplier(self, session):
        """Online suppliers get name-only slugs during migration."""
        supplier = Supplier(
            name="King Arthur Baking",
            slug="temp_online",
            supplier_type="online",
            website_url="https://www.kingarthurbaking.com",
        )
        session.add(supplier)
        session.flush()

        from src.services.supplier_service import migrate_supplier_slugs

        result = migrate_supplier_slugs(session=session)

        assert result["migrated"] == 1
        assert supplier.slug == "king_arthur_baking"


class TestValidateSupplierData:
    """Tests for validate_supplier_data() function (T009)."""

    def test_validation_requires_name(self):
        """Name is required."""
        from src.services.supplier_service import validate_supplier_data

        errors = validate_supplier_data({"name": ""})
        assert "Supplier name is required" in errors

    def test_validation_requires_name_not_whitespace(self):
        """Name cannot be just whitespace."""
        from src.services.supplier_service import validate_supplier_data

        errors = validate_supplier_data({"name": "   "})
        assert "Supplier name is required" in errors

    def test_validation_rejects_invalid_slug_format(self):
        """Invalid slug formats are rejected."""
        from src.services.supplier_service import validate_supplier_data

        errors = validate_supplier_data(
            {
                "name": "Test",
                "slug": "UPPERCASE_NOT_ALLOWED",
                "city": "Boston",
                "state": "MA",
                "zip_code": "02101",
            }
        )
        assert any("Invalid slug format" in e for e in errors)

    def test_validation_accepts_valid_slug(self):
        """Valid slug format is accepted."""
        from src.services.supplier_service import validate_supplier_data

        errors = validate_supplier_data(
            {
                "name": "Test",
                "slug": "valid_slug_format",
                "city": "Boston",
                "state": "MA",
                "zip_code": "02101",
            }
        )
        assert not any("Invalid slug format" in e for e in errors)

    def test_validation_requires_physical_supplier_fields(self):
        """Physical suppliers require city, state, zip_code."""
        from src.services.supplier_service import validate_supplier_data

        errors = validate_supplier_data(
            {
                "name": "Test Store",
                "supplier_type": "physical",
            }
        )
        assert "City is required for physical suppliers" in errors
        assert "State is required for physical suppliers" in errors
        assert "ZIP code is required for physical suppliers" in errors

    def test_validation_online_supplier_no_location_required(self):
        """Online suppliers don't require city/state/zip."""
        from src.services.supplier_service import validate_supplier_data

        errors = validate_supplier_data(
            {
                "name": "Online Store",
                "supplier_type": "online",
            }
        )
        assert "City is required" not in str(errors)
        assert "State is required" not in str(errors)
        assert "ZIP code is required" not in str(errors)

    def test_validation_rejects_invalid_supplier_type(self):
        """Invalid supplier_type is rejected."""
        from src.services.supplier_service import validate_supplier_data

        errors = validate_supplier_data(
            {
                "name": "Test",
                "supplier_type": "invalid_type",
            }
        )
        assert "supplier_type must be 'physical' or 'online'" in errors

    def test_validation_rejects_invalid_state_length(self):
        """State must be 2 characters."""
        from src.services.supplier_service import validate_supplier_data

        errors = validate_supplier_data(
            {
                "name": "Test",
                "state": "MAS",
                "city": "Boston",
                "zip_code": "02101",
            }
        )
        assert "State must be a 2-letter code" in errors


class TestGetOrCreateSupplier:
    """Tests for get_or_create_supplier function (F092 Service Boundary Compliance)."""

    def test_get_or_create_supplier_creates_new(self, session):
        """Creates new supplier when not found."""
        # Verify no suppliers exist with this name
        existing = session.query(Supplier).filter(Supplier.name == "New Store").first()
        assert existing is None

        # Call get_or_create_supplier
        result = supplier_service.get_or_create_supplier(
            name="New Store",
            session=session,
        )

        # Verify supplier was created with defaults
        assert result is not None
        assert isinstance(result, Supplier)  # Returns model, not dict
        assert result.name == "New Store"
        assert result.city == "Unknown"  # Default
        assert result.state == "XX"  # Default
        assert result.zip_code == "00000"  # Default
        assert result.id is not None

    def test_get_or_create_supplier_returns_existing(self, session):
        """Returns existing supplier when found by name."""
        # Create supplier first
        existing = Supplier(
            name="Existing Store",
            city="Boston",
            state="MA",
            zip_code="02101",
        )
        session.add(existing)
        session.flush()
        existing_id = existing.id

        # Call get_or_create_supplier with same name
        result = supplier_service.get_or_create_supplier(
            name="Existing Store",
            city="New York",  # Different city - should be ignored
            state="NY",  # Different state - should be ignored
            session=session,
        )

        # Verify existing supplier returned (not new one)
        assert result.id == existing_id
        assert result.city == "Boston"  # Original city preserved
        assert result.state == "MA"  # Original state preserved

    def test_get_or_create_supplier_with_custom_defaults(self, session):
        """Uses custom city/state/zip when provided for new supplier."""
        result = supplier_service.get_or_create_supplier(
            name="Custom Store",
            city="Seattle",
            state="WA",
            zip_code="98101",
            session=session,
        )

        assert result.city == "Seattle"
        assert result.state == "WA"
        assert result.zip_code == "98101"

    def test_get_or_create_supplier_without_session(self, engine):
        """Works correctly when session is NOT passed (creates own)."""
        # Patch session_scope to use our test engine
        from src.services.supplier_service import get_or_create_supplier
        from sqlalchemy.orm import sessionmaker
        from unittest.mock import patch

        Session = sessionmaker(bind=engine)

        # Create a context manager that uses our test session
        from contextlib import contextmanager

        @contextmanager
        def test_session_scope():
            sess = Session()
            try:
                yield sess
                sess.commit()
            except Exception:
                sess.rollback()
                raise
            finally:
                sess.close()

        with patch("src.services.supplier_service.session_scope", test_session_scope):
            # Call without session parameter
            result = get_or_create_supplier(name="No Session Store")

            # Verify it returned a Supplier (will be detached after session closes)
            assert result is not None
            assert isinstance(result, Supplier)

        # Verify supplier was persisted by querying with a new session
        verify_session = Session()
        try:
            persisted = verify_session.query(Supplier).filter(
                Supplier.name == "No Session Store"
            ).first()
            assert persisted is not None
            assert persisted.name == "No Session Store"
        finally:
            verify_session.close()

    def test_get_or_create_supplier_name_matching_case_sensitive(self, session):
        """Supplier name matching is case-sensitive (matches existing behavior)."""
        # Create supplier with specific case
        existing = Supplier(
            name="My Store",
            city="Boston",
            state="MA",
            zip_code="02101",
        )
        session.add(existing)
        session.flush()

        # Different case - should create new supplier
        result = supplier_service.get_or_create_supplier(
            name="my store",  # Different case
            session=session,
        )

        # Should be a NEW supplier (different ID)
        assert result.id != existing.id
        assert result.name == "my store"


class TestSlugImmutability:
    """Test slug immutability enforcement (Feature 050 - T031)."""

    def test_update_supplier_rejects_slug_change(self, test_db):
        """Attempting to change slug raises error."""
        from src.services.supplier_service import create_supplier, update_supplier

        session = test_db()
        supplier = create_supplier(
            name="Original Store",
            supplier_type="physical",
            city="Boston",
            state="MA",
            zip_code="02101",
            session=session,
        )
        original_slug = supplier["slug"]

        with pytest.raises(ValueError) as exc_info:
            update_supplier(
                supplier["id"],
                slug="different_slug",
                session=session,
            )

        assert "cannot be modified" in str(exc_info.value).lower()
        assert "immutable" in str(exc_info.value).lower()

        # Verify slug unchanged in database
        from src.models.supplier import Supplier

        db_supplier = session.query(Supplier).get(supplier["id"])
        assert db_supplier.slug == original_slug

    def test_update_supplier_name_preserves_slug(self, test_db):
        """Changing name doesn't change slug."""
        from src.services.supplier_service import create_supplier, update_supplier

        session = test_db()
        supplier = create_supplier(
            name="Original Store",
            supplier_type="physical",
            city="Boston",
            state="MA",
            zip_code="02101",
            session=session,
        )
        original_slug = supplier["slug"]

        updated = update_supplier(
            supplier["id"],
            name="New Store Name",
            session=session,
        )

        assert updated["name"] == "New Store Name"
        assert updated["slug"] == original_slug  # Unchanged!

    def test_update_supplier_location_preserves_slug(self, test_db):
        """Changing location doesn't change slug."""
        from src.services.supplier_service import create_supplier, update_supplier

        session = test_db()
        supplier = create_supplier(
            name="Test Store",
            supplier_type="physical",
            city="Boston",
            state="MA",
            zip_code="02101",
            session=session,
        )
        original_slug = supplier["slug"]  # test_store_boston_ma

        updated = update_supplier(
            supplier["id"],
            city="Cambridge",
            state="MA",
            session=session,
        )

        assert updated["city"] == "Cambridge"
        assert updated["slug"] == original_slug  # Still test_store_boston_ma!

    def test_update_supplier_same_slug_allowed(self, test_db):
        """Passing same slug value is allowed (no-op)."""
        from src.services.supplier_service import create_supplier, update_supplier

        session = test_db()
        supplier = create_supplier(
            name="Test Store",
            supplier_type="physical",
            city="Boston",
            state="MA",
            zip_code="02101",
            session=session,
        )

        # This should NOT raise an error
        updated = update_supplier(
            supplier["id"],
            slug=supplier["slug"],  # Same value
            name="Updated Name",
            session=session,
        )

        assert updated["name"] == "Updated Name"
        assert updated["slug"] == supplier["slug"]

    def test_slug_error_message_includes_values(self, test_db):
        """Error message includes current and attempted slug values."""
        from src.services.supplier_service import create_supplier, update_supplier

        session = test_db()
        supplier = create_supplier(
            name="Test Store",
            supplier_type="physical",
            city="Boston",
            state="MA",
            zip_code="02101",
            session=session,
        )

        with pytest.raises(ValueError) as exc_info:
            update_supplier(
                supplier["id"],
                slug="new_slug_value",
                session=session,
            )

        error_msg = str(exc_info.value)
        assert supplier["slug"] in error_msg  # Current slug in message
        assert "new_slug_value" in error_msg  # Attempted slug in message
