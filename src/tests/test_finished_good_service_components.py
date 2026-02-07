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
        assembly_type=AssemblyType.BUNDLE,
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

        # Use BUNDLE as it has no minimum component requirements
        fg = finished_good_service.create_finished_good(
            display_name="Cookie Gift Box",
            assembly_type=AssemblyType.BUNDLE,
            components=components,
            session=db_session,
        )

        assert fg.id is not None
        assert fg.display_name == "Cookie Gift Box"
        assert fg.assembly_type == AssemblyType.BUNDLE
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
            assembly_type=AssemblyType.BUNDLE,
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
            assembly_type=AssemblyType.BUNDLE,
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
            assembly_type=AssemblyType.BUNDLE,
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
            assembly_type=AssemblyType.BUNDLE,
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
            assembly_type=AssemblyType.BUNDLE,
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
            assembly_type=AssemblyType.BUNDLE,
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
            assembly_type=AssemblyType.BUNDLE,
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
            assembly_type=AssemblyType.BUNDLE,
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
            assembly_type=AssemblyType.BUNDLE,
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
                assembly_type=AssemblyType.BUNDLE,
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
                assembly_type=AssemblyType.BUNDLE,
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
                assembly_type=AssemblyType.BUNDLE,
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
                assembly_type=AssemblyType.BUNDLE,
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
                assembly_type=AssemblyType.BUNDLE,
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
                assembly_type=AssemblyType.BUNDLE,
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
                assembly_type=AssemblyType.BUNDLE,
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
                assembly_type=AssemblyType.BUNDLE,
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
            assembly_type=AssemblyType.BUNDLE,
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
            assembly_type=AssemblyType.BUNDLE,
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
            assembly_type=AssemblyType.BUNDLE,
            components=components,
            session=db_session,
        )

        assert fg.id is not None
        assert len(fg.components) == 1
        assert fg.components[0].finished_unit_id == finished_unit.id


# =============================================================================
# T014-T020: WP03 - Update and Validation Tests
# =============================================================================


class TestUpdateWithComponents:
    """Test update functionality with component replacement (T014, T018)."""

    def test_update_finished_good_basic_fields(self, db_session, finished_unit):
        """Test updating basic fields of a FinishedGood."""
        fg = finished_good_service.create_finished_good(
            display_name="Original Box",
            assembly_type=AssemblyType.BARE,
            components=[{"type": "finished_unit", "id": finished_unit.id, "quantity": 2}],
            session=db_session,
        )
        original_id = fg.id

        updated = finished_good_service.update_finished_good(
            fg.id,
            display_name="Updated Box Name",
            assembly_type=AssemblyType.BUNDLE,
            notes="New notes here",
            session=db_session,
        )

        assert updated.id == original_id
        assert updated.display_name == "Updated Box Name"
        assert updated.assembly_type == AssemblyType.BUNDLE
        assert updated.notes == "New notes here"

    def test_update_finished_good_replace_components(
        self, db_session, finished_unit, another_finished_unit
    ):
        """Test replacing components atomically (old deleted, new created)."""
        # Create with initial component
        fg = finished_good_service.create_finished_good(
            display_name="Replaceable Box",
            assembly_type=AssemblyType.BUNDLE,
            components=[{"type": "finished_unit", "id": finished_unit.id, "quantity": 5}],
            session=db_session,
        )

        original_count = len(fg.components)
        assert original_count == 1
        assert fg.components[0].finished_unit_id == finished_unit.id

        # Replace with different component
        new_components = [
            {"type": "finished_unit", "id": another_finished_unit.id, "quantity": 10}
        ]
        finished_good_service.update_finished_good(
            fg.id,
            components=new_components,
            session=db_session,
        )

        # Refresh to get updated state from database
        db_session.expire(fg)
        db_session.refresh(fg)

        # Verify components were replaced
        assert len(fg.components) == 1
        assert fg.components[0].finished_unit_id == another_finished_unit.id
        assert fg.components[0].component_quantity == 10

    def test_update_finished_good_clear_components(self, db_session, finished_unit):
        """Test clearing all components with empty list."""
        fg = finished_good_service.create_finished_good(
            display_name="Box to Clear",
            assembly_type=AssemblyType.BUNDLE,
            components=[{"type": "finished_unit", "id": finished_unit.id, "quantity": 3}],
            session=db_session,
        )
        assert len(fg.components) == 1

        # Clear all components
        updated = finished_good_service.update_finished_good(
            fg.id,
            components=[],
            session=db_session,
        )

        # Refresh to get updated state
        db_session.refresh(updated)
        assert len(updated.components) == 0

    def test_update_finished_good_with_nested_component(
        self, db_session, finished_unit, inner_finished_good
    ):
        """Test updating to include a nested FinishedGood."""
        fg = finished_good_service.create_finished_good(
            display_name="To Be Nested",
            assembly_type=AssemblyType.BUNDLE,
            components=[{"type": "finished_unit", "id": finished_unit.id, "quantity": 2}],
            session=db_session,
        )

        # Update to include both types
        new_components = [
            {"type": "finished_unit", "id": finished_unit.id, "quantity": 3, "sort_order": 0},
            {"type": "finished_good", "id": inner_finished_good.id, "quantity": 1, "sort_order": 1},
        ]
        finished_good_service.update_finished_good(
            fg.id,
            components=new_components,
            session=db_session,
        )

        # Refresh to get updated state from database
        db_session.expire(fg)
        db_session.refresh(fg)

        assert len(fg.components) == 2

        # Verify sort order preserved
        sorted_comps = sorted(fg.components, key=lambda c: c.sort_order)
        assert sorted_comps[0].finished_unit_id == finished_unit.id
        assert sorted_comps[1].finished_good_id == inner_finished_good.id

    def test_update_finished_good_preserves_unchanged_fields(
        self, db_session, finished_unit
    ):
        """Test that update preserves fields not explicitly changed."""
        fg = finished_good_service.create_finished_good(
            display_name="Preserve Test",
            assembly_type=AssemblyType.BUNDLE,
            packaging_instructions="Original instructions",
            notes="Original notes",
            components=[{"type": "finished_unit", "id": finished_unit.id, "quantity": 1}],
            session=db_session,
        )

        # Only update display_name
        updated = finished_good_service.update_finished_good(
            fg.id,
            display_name="New Name Only",
            session=db_session,
        )

        # Other fields should be preserved
        assert updated.display_name == "New Name Only"
        assert updated.packaging_instructions == "Original instructions"
        assert updated.notes == "Original notes"
        assert len(updated.components) == 1


# =============================================================================
# T015, T019: Circular Reference Detection Tests
# =============================================================================


class TestCircularReferenceDetection:
    """Test circular reference detection during create and update (T015, T019)."""

    def test_circular_reference_self_create(self, db_session, finished_unit):
        """Test that self-reference is rejected on create."""
        # First create the FinishedGood without nested components
        fg = finished_good_service.create_finished_good(
            display_name="Self Reference Test",
            assembly_type=AssemblyType.BUNDLE,
            components=[{"type": "finished_unit", "id": finished_unit.id, "quantity": 1}],
            session=db_session,
        )

        # Try to update to reference itself
        with pytest.raises(Exception) as exc:
            finished_good_service.update_finished_good(
                fg.id,
                components=[{"type": "finished_good", "id": fg.id, "quantity": 1}],
                session=db_session,
            )
        assert "itself" in str(exc.value).lower()

    def test_circular_reference_direct(self, db_session, finished_unit):
        """Test direct cycle detection (A -> B -> A)."""
        # Create A (empty for now, will add component later)
        fg_a = finished_good_service.create_finished_good(
            display_name="FG A",
            assembly_type=AssemblyType.BUNDLE,
            session=db_session,
        )

        # Create B containing A
        fg_b = finished_good_service.create_finished_good(
            display_name="FG B",
            assembly_type=AssemblyType.BUNDLE,
            components=[{"type": "finished_good", "id": fg_a.id, "quantity": 1}],
            session=db_session,
        )

        # Try to add B to A - should fail (creates A -> B -> A)
        with pytest.raises(Exception) as exc:
            finished_good_service.update_finished_good(
                fg_a.id,
                components=[{"type": "finished_good", "id": fg_b.id, "quantity": 1}],
                session=db_session,
            )
        assert "circular reference" in str(exc.value).lower()

    def test_circular_reference_transitive(self, db_session, finished_unit):
        """Test transitive cycle detection (A -> B -> C -> A)."""
        # Create A (empty initially)
        fg_a = finished_good_service.create_finished_good(
            display_name="FG A Transitive",
            assembly_type=AssemblyType.BUNDLE,
            session=db_session,
        )

        # Create B containing A
        fg_b = finished_good_service.create_finished_good(
            display_name="FG B Transitive",
            assembly_type=AssemblyType.BUNDLE,
            components=[{"type": "finished_good", "id": fg_a.id, "quantity": 1}],
            session=db_session,
        )

        # Create C containing B
        fg_c = finished_good_service.create_finished_good(
            display_name="FG C Transitive",
            assembly_type=AssemblyType.BUNDLE,
            components=[{"type": "finished_good", "id": fg_b.id, "quantity": 1}],
            session=db_session,
        )

        # Try to add C to A - should fail (creates A -> C -> B -> A)
        with pytest.raises(Exception) as exc:
            finished_good_service.update_finished_good(
                fg_a.id,
                components=[{"type": "finished_good", "id": fg_c.id, "quantity": 1}],
                session=db_session,
            )
        assert "circular reference" in str(exc.value).lower()

    def test_valid_non_circular_nesting(self, db_session, finished_unit):
        """Test that valid (non-circular) nesting is allowed."""
        # Create A containing FinishedUnit
        fg_a = finished_good_service.create_finished_good(
            display_name="FG A Valid",
            assembly_type=AssemblyType.BUNDLE,
            components=[{"type": "finished_unit", "id": finished_unit.id, "quantity": 2}],
            session=db_session,
        )

        # Create B containing A - this should succeed (A -> B is fine)
        fg_b = finished_good_service.create_finished_good(
            display_name="FG B Valid",
            assembly_type=AssemblyType.BUNDLE,
            components=[{"type": "finished_good", "id": fg_a.id, "quantity": 1}],
            session=db_session,
        )

        # B should have A as a component
        assert len(fg_b.components) == 1
        assert fg_b.components[0].finished_good_id == fg_a.id


# =============================================================================
# T016, T017, T020: Delete Safety Checks Tests
# =============================================================================


class TestDeleteSafetyChecks:
    """Test delete safety checks (T016, T017, T020)."""

    def test_delete_blocked_by_finished_good_reference(self, db_session, finished_unit):
        """Test delete is blocked when referenced by another FinishedGood."""
        # Create inner FG
        inner = finished_good_service.create_finished_good(
            display_name="Inner Box",
            assembly_type=AssemblyType.BUNDLE,
            components=[{"type": "finished_unit", "id": finished_unit.id, "quantity": 1}],
            session=db_session,
        )

        # Create outer FG containing inner
        outer = finished_good_service.create_finished_good(
            display_name="Outer Box",
            assembly_type=AssemblyType.BUNDLE,
            components=[{"type": "finished_good", "id": inner.id, "quantity": 1}],
            session=db_session,
        )

        # Try to delete inner - should fail
        with pytest.raises(ValueError) as exc:
            finished_good_service.delete_finished_good(inner.id, session=db_session)

        assert "Outer Box" in str(exc.value)
        assert "referenced by" in str(exc.value).lower()

    def test_delete_succeeds_no_references(self, db_session, finished_unit):
        """Test delete succeeds when there are no references."""
        fg = finished_good_service.create_finished_good(
            display_name="Standalone Box",
            assembly_type=AssemblyType.BUNDLE,
            components=[{"type": "finished_unit", "id": finished_unit.id, "quantity": 1}],
            session=db_session,
        )
        fg_id = fg.id

        result = finished_good_service.delete_finished_good(fg_id, session=db_session)
        assert result is True

        # Verify deleted
        deleted = db_session.query(FinishedGood).filter_by(id=fg_id).first()
        assert deleted is None

    def test_delete_cascades_compositions(self, db_session, finished_unit):
        """Test that deleting FinishedGood cascades to Composition records."""
        fg = finished_good_service.create_finished_good(
            display_name="Test Cascade Box",
            assembly_type=AssemblyType.BUNDLE,
            components=[
                {"type": "finished_unit", "id": finished_unit.id, "quantity": 2},
            ],
            session=db_session,
        )
        fg_id = fg.id

        # Verify composition exists
        comps_before = db_session.query(Composition).filter_by(assembly_id=fg_id).count()
        assert comps_before == 1

        # Delete
        finished_good_service.delete_finished_good(fg_id, session=db_session)

        # Verify compositions also deleted
        remaining = db_session.query(Composition).filter_by(assembly_id=fg_id).count()
        assert remaining == 0

    def test_delete_not_found_returns_false(self, db_session):
        """Test delete returns False for non-existent ID."""
        result = finished_good_service.delete_finished_good(99999, session=db_session)
        assert result is False

    def test_delete_after_removing_reference(self, db_session, finished_unit):
        """Test delete succeeds after reference is removed."""
        # Create inner FG
        inner = finished_good_service.create_finished_good(
            display_name="Inner to Remove",
            assembly_type=AssemblyType.BUNDLE,
            components=[{"type": "finished_unit", "id": finished_unit.id, "quantity": 1}],
            session=db_session,
        )

        # Create outer FG containing inner
        outer = finished_good_service.create_finished_good(
            display_name="Outer Container",
            assembly_type=AssemblyType.BUNDLE,
            components=[{"type": "finished_good", "id": inner.id, "quantity": 1}],
            session=db_session,
        )

        # First, try to delete inner - should fail
        with pytest.raises(ValueError):
            finished_good_service.delete_finished_good(inner.id, session=db_session)

        # Remove reference by updating outer to have no components
        finished_good_service.update_finished_good(
            outer.id,
            components=[],
            session=db_session,
        )

        # Now delete should succeed
        result = finished_good_service.delete_finished_good(inner.id, session=db_session)
        assert result is True


# =============================================================================
# Event Reference Tests (T017)
# =============================================================================


class TestEventReferenceChecks:
    """Test delete safety checks for event references (T017)."""

    def test_delete_blocked_by_event_reference(self, db_session, finished_unit):
        """Test delete is blocked when referenced by an event."""
        from src.models.event_finished_good import EventFinishedGood
        from src.models.event import Event
        from datetime import date

        # Create FinishedGood
        fg = finished_good_service.create_finished_good(
            display_name="Event Box",
            assembly_type=AssemblyType.BUNDLE,
            components=[{"type": "finished_unit", "id": finished_unit.id, "quantity": 1}],
            session=db_session,
        )

        # Create an event
        event = Event(
            name="Christmas 2024",
            event_date=date(2024, 12, 25),
            year=2024,
        )
        db_session.add(event)
        db_session.flush()

        # Link FinishedGood to event
        event_fg = EventFinishedGood(
            event_id=event.id,
            finished_good_id=fg.id,
            quantity=10,
        )
        db_session.add(event_fg)
        db_session.flush()

        # Try to delete - should fail
        with pytest.raises(ValueError) as exc:
            finished_good_service.delete_finished_good(fg.id, session=db_session)

        assert "Christmas 2024" in str(exc.value)
        assert "event" in str(exc.value).lower()

    def test_delete_succeeds_without_event_reference(self, db_session, finished_unit):
        """Test delete succeeds when not referenced by any events."""
        from src.models.event import Event
        from datetime import date

        # Create FinishedGood
        fg = finished_good_service.create_finished_good(
            display_name="Non-Event Box",
            assembly_type=AssemblyType.BUNDLE,
            components=[{"type": "finished_unit", "id": finished_unit.id, "quantity": 1}],
            session=db_session,
        )

        # Create an event (but don't link the FG to it)
        event = Event(
            name="Unrelated Event",
            event_date=date(2024, 1, 1),
            year=2024,
        )
        db_session.add(event)
        db_session.flush()

        # Delete should succeed since FG is not linked to event
        result = finished_good_service.delete_finished_good(fg.id, session=db_session)
        assert result is True
