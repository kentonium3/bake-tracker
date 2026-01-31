"""
Unit tests for FinishedGood service - create with components.

Feature 088: Finished Goods Catalog UI - WP02

Tests cover:
- T011: Create with FinishedUnit (foods) components
- T012: Create with MaterialUnit (materials) components
- T013: Create with nested FinishedGood components

These tests validate the enhanced create_finished_good() function that accepts
a components list parameter and creates all Composition records atomically
within a single transaction.
"""

import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.base import Base
from src.models import (
    FinishedGood,
    FinishedUnit,
    Composition,
    Recipe,
    MaterialUnit,
    MaterialProduct,
    MaterialCategory,
    MaterialSubcategory,
    Material,
    AssemblyType,
)
from src.models.finished_unit import YieldMode
from src.services import finished_good_service
from src.services.finished_good_service import (
    FinishedGoodService,
    InvalidComponentError,
)
from src.services.exceptions import ValidationError
from src.services import database


# Mock business rule validation to always pass
# This is necessary because business rules include cost validation
# but costs are calculated on instances, not definitions (F045)
@pytest.fixture(autouse=True)
def mock_business_rules():
    """Mock business rule validation to always pass for testing."""
    with patch(
        "src.services.finished_good_service.validate_assembly_type_business_rules",
        return_value=(True, []),
    ):
        yield


@pytest.fixture(scope="function")
def db_session():
    """
    Create a test database session.

    This fixture creates an in-memory database for each test,
    ensuring tests are isolated. It also patches the global
    session factory so services use the test database.
    """
    # Create in-memory database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    # Create session factory with expire_on_commit=False
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    # Patch the global session factory
    original_get_session = database.get_session
    database._SessionFactory = Session

    def patched_get_session():
        return Session()

    database.get_session = patched_get_session

    # Create a session for the test
    session = Session()

    yield session

    # Cleanup
    session.close()
    database.get_session = original_get_session


@pytest.fixture
def recipe(db_session):
    """Create a basic recipe for testing."""
    recipe = Recipe(
        name="Test Cookie Recipe",
        category="Cookies",
        source="Test",
    )
    db_session.add(recipe)
    db_session.flush()
    return recipe


@pytest.fixture
def finished_unit(db_session, recipe):
    """Create a basic FinishedUnit for testing."""
    fu = FinishedUnit(
        slug="test-cookie",
        display_name="Test Cookie",
        recipe_id=recipe.id,
        yield_mode=YieldMode.DISCRETE_COUNT,
        items_per_batch=24,
        item_unit="cookie",
        inventory_count=100,
    )
    db_session.add(fu)
    db_session.flush()
    return fu


@pytest.fixture
def another_finished_unit(db_session, recipe):
    """Create a second FinishedUnit for testing multiple components."""
    fu = FinishedUnit(
        slug="test-brownie",
        display_name="Test Brownie",
        recipe_id=recipe.id,
        yield_mode=YieldMode.DISCRETE_COUNT,
        items_per_batch=16,
        item_unit="brownie",
        inventory_count=50,
    )
    db_session.add(fu)
    db_session.flush()
    return fu


@pytest.fixture
def material_category(db_session):
    """Create a material category for testing."""
    cat = MaterialCategory(
        name="Packaging",
        slug="packaging",
    )
    db_session.add(cat)
    db_session.flush()
    return cat


@pytest.fixture
def material_subcategory(db_session, material_category):
    """Create a material subcategory for testing."""
    subcat = MaterialSubcategory(
        name="Gift Boxes",
        slug="gift-boxes",
        category_id=material_category.id,
    )
    db_session.add(subcat)
    db_session.flush()
    return subcat


@pytest.fixture
def material(db_session, material_subcategory):
    """Create a material for testing."""
    mat = Material(
        name="Red Ribbon",
        slug="red-ribbon",
        subcategory_id=material_subcategory.id,
        base_unit_type="linear_cm",
    )
    db_session.add(mat)
    db_session.flush()
    return mat


@pytest.fixture
def material_product(db_session, material):
    """Create a material product for testing."""
    prod = MaterialProduct(
        name="Red Satin Ribbon 1inch",
        slug="red-satin-ribbon-1inch",
        material_id=material.id,
        package_quantity=100.0,
        package_unit="inch",
        quantity_in_base_units=254.0,  # 100 inches in cm (100 * 2.54)
    )
    db_session.add(prod)
    db_session.flush()
    return prod


@pytest.fixture
def material_unit(db_session, material_product):
    """Create a MaterialUnit for testing."""
    mu = MaterialUnit(
        name="6-inch Red Ribbon",
        slug="6-inch-red-ribbon",
        material_product_id=material_product.id,
        quantity_per_unit=6.0,
    )
    db_session.add(mu)
    db_session.flush()
    return mu


@pytest.fixture
def inner_finished_good(db_session, finished_unit):
    """Create a nested FinishedGood for testing composite assemblies."""
    fg = finished_good_service.create_finished_good(
        display_name="Small Gift Box",
        assembly_type=AssemblyType.CUSTOM_ORDER,
        components=[{"type": "finished_unit", "id": finished_unit.id, "quantity": 2}],
        session=db_session,
    )
    return fg


# =============================================================================
# T011: Tests for create with FinishedUnit (foods) components
# =============================================================================


class TestCreateWithFoodsComponents:
    """Test creating FinishedGood with FinishedUnit components (T011)."""

    def test_create_finished_good_with_single_food(self, db_session, finished_unit):
        """Test creating a FinishedGood with a single FinishedUnit component."""
        components = [
            {"type": "finished_unit", "id": finished_unit.id, "quantity": 6, "sort_order": 0}
        ]

        # Use CUSTOM_ORDER as it has no minimum component requirements
        fg = finished_good_service.create_finished_good(
            display_name="Cookie Gift Box",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            components=components,
            session=db_session,
        )

        assert fg.id is not None
        assert fg.display_name == "Cookie Gift Box"
        assert fg.assembly_type == AssemblyType.CUSTOM_ORDER
        assert len(fg.components) == 1
        assert fg.components[0].finished_unit_id == finished_unit.id
        assert fg.components[0].component_quantity == 6

    def test_create_finished_good_with_multiple_foods(
        self, db_session, finished_unit, another_finished_unit
    ):
        """Test creating a FinishedGood with multiple FinishedUnit components."""
        components = [
            {"type": "finished_unit", "id": finished_unit.id, "quantity": 3, "sort_order": 0},
            {"type": "finished_unit", "id": another_finished_unit.id, "quantity": 3, "sort_order": 1},
        ]

        fg = finished_good_service.create_finished_good(
            display_name="Variety Cookie Box",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            components=components,
            session=db_session,
        )

        assert fg.id is not None
        assert len(fg.components) == 2

        # Verify each component
        fu_ids = {c.finished_unit_id for c in fg.components}
        assert finished_unit.id in fu_ids
        assert another_finished_unit.id in fu_ids

    def test_create_finished_good_with_foods_preserves_quantities(
        self, db_session, finished_unit
    ):
        """Test that component quantities are correctly preserved."""
        components = [
            {"type": "finished_unit", "id": finished_unit.id, "quantity": 12}
        ]

        fg = finished_good_service.create_finished_good(
            display_name="Dozen Cookie Box",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            components=components,
            session=db_session,
        )

        assert fg.components[0].component_quantity == 12

    def test_create_finished_good_with_foods_preserves_notes(
        self, db_session, finished_unit
    ):
        """Test that component notes are correctly preserved."""
        components = [
            {
                "type": "finished_unit",
                "id": finished_unit.id,
                "quantity": 6,
                "notes": "Arrange in two rows",
            }
        ]

        fg = finished_good_service.create_finished_good(
            display_name="Cookie Box with Notes",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            components=components,
            session=db_session,
        )

        assert fg.components[0].component_notes == "Arrange in two rows"


# =============================================================================
# T012: Tests for create with MaterialUnit (materials) components
# =============================================================================


class TestCreateWithMaterialsComponents:
    """Test creating FinishedGood with MaterialUnit components (T012)."""

    def test_create_finished_good_with_materials(self, db_session, material_unit):
        """Test creating a FinishedGood with a MaterialUnit component."""
        components = [
            {"type": "material_unit", "id": material_unit.id, "quantity": 1}
        ]

        fg = finished_good_service.create_finished_good(
            display_name="Gift Package",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            components=components,
            session=db_session,
        )

        assert fg.id is not None
        assert len(fg.components) == 1
        assert fg.components[0].material_unit_id == material_unit.id

    def test_create_finished_good_with_mixed_components(
        self, db_session, finished_unit, material_unit
    ):
        """Test creating a FinishedGood with mixed food + material components."""
        components = [
            {"type": "finished_unit", "id": finished_unit.id, "quantity": 6, "sort_order": 0},
            {
                "type": "material_unit",
                "id": material_unit.id,
                "quantity": 1,
                "notes": "Ribbon wrap",
                "sort_order": 1,
            },
        ]

        fg = finished_good_service.create_finished_good(
            display_name="Complete Gift Box",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            components=components,
            session=db_session,
        )

        assert len(fg.components) == 2

        # Find each component by type
        food_comp = next(c for c in fg.components if c.finished_unit_id is not None)
        material_comp = next(c for c in fg.components if c.material_unit_id is not None)

        assert food_comp.finished_unit_id == finished_unit.id
        assert food_comp.component_quantity == 6
        assert material_comp.material_unit_id == material_unit.id
        assert material_comp.component_notes == "Ribbon wrap"

    def test_create_finished_good_materials_preserves_notes(
        self, db_session, material_unit
    ):
        """Test that notes are preserved on material components."""
        components = [
            {
                "type": "material_unit",
                "id": material_unit.id,
                "quantity": 2,
                "notes": "Use for bow decoration",
            }
        ]

        fg = finished_good_service.create_finished_good(
            display_name="Decorated Package",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            components=components,
            session=db_session,
        )

        assert fg.components[0].component_notes == "Use for bow decoration"


# =============================================================================
# T013: Tests for create with nested FinishedGood components
# =============================================================================


class TestCreateWithNestedComponents:
    """Test creating FinishedGood with nested FinishedGood components (T013)."""

    def test_create_finished_good_with_nested_component(
        self, db_session, inner_finished_good
    ):
        """Test creating a FinishedGood containing another FinishedGood."""
        components = [
            {"type": "finished_good", "id": inner_finished_good.id, "quantity": 2}
        ]

        fg = finished_good_service.create_finished_good(
            display_name="Large Gift Bundle",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            components=components,
            session=db_session,
        )

        assert fg.id is not None
        assert len(fg.components) == 1
        assert fg.components[0].finished_good_id == inner_finished_good.id
        assert fg.components[0].component_quantity == 2

    def test_create_finished_good_with_all_component_types(
        self, db_session, finished_unit, material_unit, inner_finished_good
    ):
        """Test creating a FinishedGood with all three component types."""
        components = [
            {"type": "finished_unit", "id": finished_unit.id, "quantity": 4, "sort_order": 0},
            {"type": "material_unit", "id": material_unit.id, "quantity": 1, "sort_order": 1},
            {"type": "finished_good", "id": inner_finished_good.id, "quantity": 1, "sort_order": 2},
        ]

        fg = finished_good_service.create_finished_good(
            display_name="Ultimate Gift Package",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            components=components,
            session=db_session,
        )

        assert len(fg.components) == 3

        # Verify sort order is preserved
        sorted_comps = sorted(fg.components, key=lambda c: c.sort_order)
        assert sorted_comps[0].finished_unit_id is not None
        assert sorted_comps[1].material_unit_id is not None
        assert sorted_comps[2].finished_good_id is not None

    def test_create_finished_good_nested_preserves_sort_order(
        self, db_session, finished_unit, inner_finished_good
    ):
        """Test that sort order is correctly preserved across component types."""
        components = [
            {"type": "finished_good", "id": inner_finished_good.id, "quantity": 1, "sort_order": 10},
            {"type": "finished_unit", "id": finished_unit.id, "quantity": 3, "sort_order": 5},
        ]

        fg = finished_good_service.create_finished_good(
            display_name="Sorted Bundle",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            components=components,
            session=db_session,
        )

        sorted_comps = sorted(fg.components, key=lambda c: c.sort_order)

        # FinishedUnit (sort_order=5) should come before FinishedGood (sort_order=10)
        assert sorted_comps[0].finished_unit_id == finished_unit.id
        assert sorted_comps[0].sort_order == 5
        assert sorted_comps[1].finished_good_id == inner_finished_good.id
        assert sorted_comps[1].sort_order == 10


# =============================================================================
# Validation Tests (T010)
# =============================================================================


class TestComponentValidation:
    """Test component data validation (T010)."""

    def test_create_with_missing_type_fails(self, db_session, finished_unit):
        """Test that missing 'type' field raises ValidationError."""
        components = [
            {"id": finished_unit.id, "quantity": 6}  # Missing 'type'
        ]

        with pytest.raises(ValidationError, match="missing 'type' field"):
            finished_good_service.create_finished_good(
                display_name="Invalid Box",
                assembly_type=AssemblyType.CUSTOM_ORDER,
                components=components,
                session=db_session,
            )

    def test_create_with_missing_id_fails(self, db_session):
        """Test that missing 'id' field raises ValidationError."""
        components = [
            {"type": "finished_unit", "quantity": 6}  # Missing 'id'
        ]

        with pytest.raises(ValidationError, match="missing 'id' field"):
            finished_good_service.create_finished_good(
                display_name="Invalid Box",
                assembly_type=AssemblyType.CUSTOM_ORDER,
                components=components,
                session=db_session,
            )

    def test_create_with_invalid_type_fails(self, db_session):
        """Test that invalid component type raises ValidationError."""
        components = [
            {"type": "invalid_type", "id": 1, "quantity": 6}
        ]

        with pytest.raises(ValidationError, match="invalid type"):
            finished_good_service.create_finished_good(
                display_name="Invalid Box",
                assembly_type=AssemblyType.CUSTOM_ORDER,
                components=components,
                session=db_session,
            )

    def test_create_with_zero_quantity_fails(self, db_session, finished_unit):
        """Test that zero quantity raises ValidationError."""
        components = [
            {"type": "finished_unit", "id": finished_unit.id, "quantity": 0}
        ]

        with pytest.raises(ValidationError, match="quantity must be positive"):
            finished_good_service.create_finished_good(
                display_name="Invalid Box",
                assembly_type=AssemblyType.CUSTOM_ORDER,
                components=components,
                session=db_session,
            )

    def test_create_with_negative_quantity_fails(self, db_session, finished_unit):
        """Test that negative quantity raises ValidationError."""
        components = [
            {"type": "finished_unit", "id": finished_unit.id, "quantity": -1}
        ]

        with pytest.raises(ValidationError, match="quantity must be positive"):
            finished_good_service.create_finished_good(
                display_name="Invalid Box",
                assembly_type=AssemblyType.CUSTOM_ORDER,
                components=components,
                session=db_session,
            )

    def test_create_with_nonexistent_finished_unit_fails(self, db_session):
        """Test that non-existent FinishedUnit reference raises error."""
        components = [
            {"type": "finished_unit", "id": 99999, "quantity": 6}
        ]

        with pytest.raises(InvalidComponentError, match="FinishedUnit 99999 not found"):
            finished_good_service.create_finished_good(
                display_name="Invalid Box",
                assembly_type=AssemblyType.CUSTOM_ORDER,
                components=components,
                session=db_session,
            )

    def test_create_with_nonexistent_material_unit_fails(self, db_session):
        """Test that non-existent MaterialUnit reference raises error."""
        components = [
            {"type": "material_unit", "id": 99999, "quantity": 1}
        ]

        with pytest.raises(InvalidComponentError, match="MaterialUnit 99999 not found"):
            finished_good_service.create_finished_good(
                display_name="Invalid Box",
                assembly_type=AssemblyType.CUSTOM_ORDER,
                components=components,
                session=db_session,
            )

    def test_create_with_nonexistent_finished_good_fails(self, db_session):
        """Test that non-existent FinishedGood reference raises error."""
        components = [
            {"type": "finished_good", "id": 99999, "quantity": 1}
        ]

        with pytest.raises(InvalidComponentError, match="FinishedGood 99999 not found"):
            finished_good_service.create_finished_good(
                display_name="Invalid Box",
                assembly_type=AssemblyType.CUSTOM_ORDER,
                components=components,
                session=db_session,
            )


# =============================================================================
# Session Management Tests
# =============================================================================


class TestSessionManagement:
    """Test session management pattern compliance."""

    def test_create_with_explicit_session(self, db_session, finished_unit):
        """Test that explicit session parameter is properly used."""
        components = [
            {"type": "finished_unit", "id": finished_unit.id, "quantity": 6}
        ]

        fg = finished_good_service.create_finished_good(
            display_name="Session Test Box",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            components=components,
            session=db_session,
        )

        # Verify the object is still tracked by the session
        assert fg in db_session
        assert fg.id is not None

    def test_create_without_session_uses_scope(self, db_session, finished_unit):
        """Test that function works without explicit session (uses session_scope)."""
        # This test verifies the function can work standalone
        # Note: We still need the db_session fixture to set up test data
        components = [
            {"type": "finished_unit", "id": finished_unit.id, "quantity": 3}
        ]

        fg = finished_good_service.create_finished_good(
            display_name="No Session Box",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            components=components,
            # No session parameter - should use session_scope
        )

        assert fg.id is not None
        assert fg.display_name == "No Session Box"


# =============================================================================
# Legacy Format Compatibility Tests
# =============================================================================


class TestLegacyFormatCompatibility:
    """Test backward compatibility with legacy component_type/component_id format."""

    def test_create_with_legacy_format(self, db_session, finished_unit):
        """Test that legacy component_type/component_id format still works."""
        components = [
            {
                "component_type": "finished_unit",
                "component_id": finished_unit.id,
                "quantity": 6,
            }
        ]

        fg = finished_good_service.create_finished_good(
            display_name="Legacy Format Box",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            components=components,
            session=db_session,
        )

        assert fg.id is not None
        assert len(fg.components) == 1
        assert fg.components[0].finished_unit_id == finished_unit.id
