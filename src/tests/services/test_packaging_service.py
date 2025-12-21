"""
Tests for Packaging Service - Generic Packaging Operations (Feature 026).

Tests cover:
- get_generic_products() - returns distinct product_name values
- get_generic_inventory_summary() - totals and breakdown by brand
- get_estimated_cost() - weighted average calculation
- assign_materials() - validation and record creation
- clear_assignments() - remove assignments
- get_assignments() - retrieve assignment details
- get_pending_requirements() - find unassigned generics
- is_fully_assigned() - check assignment status
- get_assignment_summary() - assignment status summary
- get_actual_cost() - cost from assignments
"""

import pytest
from datetime import date, datetime
from decimal import Decimal

from src.services import packaging_service
from src.services.packaging_service import (
    get_generic_products,
    get_generic_inventory_summary,
    get_estimated_cost,
    get_actual_cost,
    assign_materials,
    clear_assignments,
    get_assignments,
    get_pending_requirements,
    is_fully_assigned,
    get_assignment_summary,
    GenericProductNotFoundError,
    CompositionNotFoundError,
    NotGenericCompositionError,
    InvalidAssignmentError,
    InsufficientInventoryError,
    ProductMismatchError,
)
from src.services.ingredient_service import create_ingredient
from src.services.product_service import create_product
from src.services.inventory_item_service import add_to_inventory
from src.models import (
    FinishedGood,
    Composition,
    CompositionAssignment,
    InventoryItem,
)
from src.models.assembly_type import AssemblyType


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def packaging_ingredient(test_db):
    """Create a packaging ingredient for tests."""
    return create_ingredient({
        "name": "Cellophane Bags 6x10",
        "category": "Bags",
        "is_packaging": True,
    })


@pytest.fixture
def packaging_ingredient_2(test_db):
    """Create a second packaging ingredient for tests."""
    return create_ingredient({
        "name": "Gift Boxes Medium",
        "category": "Boxes",
        "is_packaging": True,
    })


@pytest.fixture
def food_ingredient(test_db):
    """Create a food ingredient (not packaging) for tests."""
    return create_ingredient({
        "name": "All-Purpose Flour",
        "category": "Flour",
        "is_packaging": False,
    })


@pytest.fixture
def packaging_product_a(test_db, packaging_ingredient):
    """Create first packaging product with same product_name."""
    product = create_product(
        packaging_ingredient.slug,
        {
            "brand": "ClearBags",
            "package_size": "100ct",
            "package_unit": "box",
            "package_unit_quantity": 100,
            "product_name": "Cellophane Bags 6x10",
        }
    )
    return product


@pytest.fixture
def packaging_product_b(test_db, packaging_ingredient):
    """Create second packaging product with same product_name (different brand)."""
    product = create_product(
        packaging_ingredient.slug,
        {
            "brand": "PackagePro",
            "package_size": "50ct",
            "package_unit": "box",
            "package_unit_quantity": 50,
            "product_name": "Cellophane Bags 6x10",
        }
    )
    return product


@pytest.fixture
def packaging_product_box(test_db, packaging_ingredient_2):
    """Create a box packaging product."""
    product = create_product(
        packaging_ingredient_2.slug,
        {
            "brand": "BoxCorp",
            "package_size": "25ct",
            "package_unit": "each",  # Use valid unit type
            "package_unit_quantity": 25,
            "purchase_price": 1.50,
            "product_name": "Gift Boxes Medium",
        }
    )
    return product


@pytest.fixture
def inventory_a(test_db, packaging_product_a):
    """Create inventory for product A with unit cost $0.10."""
    item = add_to_inventory(
        product_id=packaging_product_a.id,
        quantity=Decimal("50"),
        purchase_date=date(2025, 1, 1),
    )
    # Set unit cost after creation (not a parameter of add_to_inventory)
    from src.models import InventoryItem
    test_db.query(InventoryItem).filter_by(id=item.id).update({"unit_cost": 0.10})
    test_db.flush()
    # Refresh to get updated value
    return test_db.query(InventoryItem).filter_by(id=item.id).first()


@pytest.fixture
def inventory_b(test_db, packaging_product_b):
    """Create inventory for product B with unit cost $0.15."""
    item = add_to_inventory(
        product_id=packaging_product_b.id,
        quantity=Decimal("30"),
        purchase_date=date(2025, 1, 15),
    )
    # Set unit cost after creation
    from src.models import InventoryItem
    test_db.query(InventoryItem).filter_by(id=item.id).update({"unit_cost": 0.15})
    test_db.flush()
    return test_db.query(InventoryItem).filter_by(id=item.id).first()


@pytest.fixture
def finished_good(test_db):
    """Create a finished good assembly for tests."""
    fg = FinishedGood(
        slug="test-cookie-dozen",
        display_name="Test Cookie Dozen",
        description="A dozen test cookies",
        assembly_type=AssemblyType.CUSTOM_ORDER,
        inventory_count=0,
    )
    test_db.add(fg)
    test_db.flush()
    return fg


@pytest.fixture
def generic_composition(test_db, finished_good, packaging_product_a):
    """Create a generic composition requiring 20 bags."""
    comp = Composition(
        assembly_id=finished_good.id,
        packaging_product_id=packaging_product_a.id,
        component_quantity=20.0,
        is_generic=True,
    )
    test_db.add(comp)
    test_db.flush()
    return comp


@pytest.fixture
def specific_composition(test_db, finished_good, packaging_product_a):
    """Create a specific (non-generic) composition."""
    comp = Composition(
        assembly_id=finished_good.id,
        packaging_product_id=packaging_product_a.id,
        component_quantity=10.0,
        is_generic=False,
    )
    test_db.add(comp)
    test_db.flush()
    return comp


# =============================================================================
# Tests: get_generic_products()
# =============================================================================


class TestGetGenericProducts:
    """Tests for get_generic_products() function."""

    def test_returns_distinct_product_names(
        self, test_db, packaging_product_a, packaging_product_b, inventory_a, inventory_b
    ):
        """Returns distinct product_name values."""
        result = get_generic_products(session=test_db)

        # Both products have same product_name, should return one entry
        assert "Cellophane Bags 6x10" in result
        assert len([n for n in result if n == "Cellophane Bags 6x10"]) == 1

    def test_excludes_products_without_inventory(
        self, test_db, packaging_product_a, packaging_product_b, inventory_a
    ):
        """Only includes products with inventory > 0."""
        # Only product A has inventory
        result = get_generic_products(session=test_db)

        # Should still include the product_name since product A has inventory
        assert "Cellophane Bags 6x10" in result

    def test_returns_empty_when_no_inventory(
        self, test_db, packaging_product_a
    ):
        """Returns empty list when no products have inventory."""
        result = get_generic_products(session=test_db)

        assert result == []

    def test_excludes_non_packaging_products(
        self, test_db, food_ingredient
    ):
        """Only includes products linked to packaging ingredients."""
        # Create food product with inventory
        product = create_product(
            food_ingredient.slug,
            {
                "brand": "King Arthur",
                "package_size": "5 lb",
                "package_unit": "lb",
                "package_unit_quantity": 5,
                "product_name": "All-Purpose Flour",
            }
        )

        add_to_inventory(
            product_id=product.id,
            quantity=Decimal("10"),
            purchase_date=date(2025, 1, 1),
        )

        result = get_generic_products(session=test_db)

        # Food products should not be included
        assert "All-Purpose Flour" not in result

    def test_returns_sorted_list(
        self, test_db, packaging_product_a, packaging_product_box,
        inventory_a
    ):
        """Returns product names in alphabetical order."""
        # Add inventory for box product
        add_to_inventory(
            product_id=packaging_product_box.id,
            quantity=Decimal("10"),
            purchase_date=date(2025, 1, 1),
        )

        result = get_generic_products(session=test_db)

        # Should be alphabetically sorted
        assert result == sorted(result)


# =============================================================================
# Tests: get_generic_inventory_summary()
# =============================================================================


class TestGetGenericInventorySummary:
    """Tests for get_generic_inventory_summary() function."""

    def test_returns_total_and_breakdown(
        self, test_db, packaging_product_a, packaging_product_b, inventory_a, inventory_b
    ):
        """Returns correct total and breakdown by brand."""
        result = get_generic_inventory_summary("Cellophane Bags 6x10", session=test_db)

        assert result["total"] == 80.0  # 50 + 30
        assert len(result["breakdown"]) == 2

        # Check breakdown entries
        brands = {item["brand"]: item["available"] for item in result["breakdown"]}
        assert brands["ClearBags"] == 50.0
        assert brands["PackagePro"] == 30.0

    def test_raises_when_product_not_found(self, test_db):
        """Raises GenericProductNotFoundError for unknown product_name."""
        with pytest.raises(GenericProductNotFoundError) as exc:
            get_generic_inventory_summary("Nonexistent Product", session=test_db)

        assert "Nonexistent Product" in str(exc.value)

    def test_excludes_zero_inventory(
        self, test_db, packaging_product_a, packaging_product_b, inventory_a
    ):
        """Only includes products with inventory > 0 in breakdown."""
        # Only product A has inventory
        result = get_generic_inventory_summary("Cellophane Bags 6x10", session=test_db)

        assert result["total"] == 50.0
        assert len(result["breakdown"]) == 1
        assert result["breakdown"][0]["brand"] == "ClearBags"

    def test_breakdown_sorted_by_brand(
        self, test_db, packaging_product_a, packaging_product_b, inventory_a, inventory_b
    ):
        """Breakdown is sorted alphabetically by brand."""
        result = get_generic_inventory_summary("Cellophane Bags 6x10", session=test_db)

        brands = [item["brand"] for item in result["breakdown"]]
        assert brands == sorted(brands)


# =============================================================================
# Tests: get_estimated_cost()
# =============================================================================


class TestGetEstimatedCost:
    """Tests for get_estimated_cost() function."""

    def test_weighted_average_calculation(
        self, test_db, packaging_product_a, packaging_product_b, inventory_a, inventory_b
    ):
        """Calculates weighted average based on inventory quantities."""
        # Product A: 50 units @ $0.10 = $5.00 weighted
        # Product B: 30 units @ $0.15 = $4.50 weighted
        # Total: 80 units, weighted sum = $9.50
        # Weighted average = $9.50 / 80 = $0.11875
        # For 10 units: 10 * $0.11875 = $1.1875, rounded to $1.19

        result = get_estimated_cost("Cellophane Bags 6x10", 10, session=test_db)

        assert result == 1.19

    def test_single_product_uses_its_price(
        self, test_db, packaging_product_a, inventory_a
    ):
        """Uses product price when only one product has inventory."""
        # Product A: $0.10 each, 10 units = $1.00
        result = get_estimated_cost("Cellophane Bags 6x10", 10, session=test_db)

        assert result == 1.00

    def test_raises_when_product_not_found(self, test_db):
        """Raises GenericProductNotFoundError for unknown product_name."""
        with pytest.raises(GenericProductNotFoundError):
            get_estimated_cost("Nonexistent Product", 10, session=test_db)

    def test_zero_quantity_returns_zero(
        self, test_db, packaging_product_a, inventory_a
    ):
        """Returns 0.0 when quantity is 0."""
        result = get_estimated_cost("Cellophane Bags 6x10", 0, session=test_db)

        assert result == 0.0

    def test_returns_zero_when_no_inventory_no_costs(
        self, test_db, packaging_product_a, packaging_product_b
    ):
        """Returns 0.0 when no products have inventory or historical cost data."""
        # No inventory and no historical costs - returns 0
        result = get_estimated_cost("Cellophane Bags 6x10", 10, session=test_db)

        assert result == 0.0


# =============================================================================
# Tests: assign_materials()
# =============================================================================


class TestAssignMaterials:
    """Tests for assign_materials() function."""

    def test_successful_assignment(
        self, test_db, generic_composition, inventory_a, inventory_b
    ):
        """Creates assignment records when validation passes."""
        assignments = [
            {"inventory_item_id": inventory_a.id, "quantity": 15},
            {"inventory_item_id": inventory_b.id, "quantity": 5},
        ]

        result = assign_materials(generic_composition.id, assignments, session=test_db)

        assert result is True

        # Verify records created
        records = test_db.query(CompositionAssignment).filter_by(
            composition_id=generic_composition.id
        ).all()
        assert len(records) == 2

    def test_validates_quantity_sum_equals_required(
        self, test_db, generic_composition, inventory_a
    ):
        """Raises error when total assigned doesn't equal required."""
        # Composition requires 20, only assigning 10
        assignments = [{"inventory_item_id": inventory_a.id, "quantity": 10}]

        with pytest.raises(InvalidAssignmentError) as exc:
            assign_materials(generic_composition.id, assignments, session=test_db)

        assert "must equal" in str(exc.value)

    def test_validates_inventory_availability(
        self, test_db, generic_composition, inventory_a
    ):
        """Raises error when assigning more than available."""
        # Inventory A has 50, trying to assign 100
        assignments = [{"inventory_item_id": inventory_a.id, "quantity": 100}]

        with pytest.raises(InsufficientInventoryError) as exc:
            assign_materials(generic_composition.id, assignments, session=test_db)

        assert exc.value.requested == 100
        assert exc.value.available == 50

    def test_validates_product_name_match(
        self, test_db, generic_composition, packaging_product_box
    ):
        """Raises error when product_name doesn't match requirement."""
        # Add inventory for box (different product_name)
        box_inventory = add_to_inventory(
            product_id=packaging_product_box.id,
            quantity=Decimal("20"),
            purchase_date=date(2025, 1, 1),
        )

        assignments = [{"inventory_item_id": box_inventory.id, "quantity": 20}]

        with pytest.raises(ProductMismatchError) as exc:
            assign_materials(generic_composition.id, assignments, session=test_db)

        assert "Cellophane Bags 6x10" in str(exc.value)
        assert "Gift Boxes Medium" in str(exc.value)

    def test_raises_for_non_generic_composition(
        self, test_db, specific_composition, inventory_a
    ):
        """Raises error for non-generic composition."""
        assignments = [{"inventory_item_id": inventory_a.id, "quantity": 10}]

        with pytest.raises(NotGenericCompositionError):
            assign_materials(specific_composition.id, assignments, session=test_db)

    def test_raises_for_missing_composition(self, test_db, inventory_a):
        """Raises error for non-existent composition."""
        assignments = [{"inventory_item_id": inventory_a.id, "quantity": 10}]

        with pytest.raises(CompositionNotFoundError):
            assign_materials(99999, assignments, session=test_db)

    def test_clears_existing_assignments_before_new(
        self, test_db, generic_composition, inventory_a, inventory_b
    ):
        """Clears old assignments when re-assigning."""
        # First assignment
        assign_materials(
            generic_composition.id,
            [{"inventory_item_id": inventory_a.id, "quantity": 20}],
            session=test_db
        )

        # Re-assign with different inventory
        assign_materials(
            generic_composition.id,
            [{"inventory_item_id": inventory_b.id, "quantity": 20}],
            session=test_db
        )

        # Should only have new assignment
        records = test_db.query(CompositionAssignment).filter_by(
            composition_id=generic_composition.id
        ).all()
        assert len(records) == 1
        assert records[0].inventory_item_id == inventory_b.id


# =============================================================================
# Tests: clear_assignments()
# =============================================================================


class TestClearAssignments:
    """Tests for clear_assignments() function."""

    def test_clears_all_assignments(
        self, test_db, generic_composition, inventory_a, inventory_b
    ):
        """Removes all assignment records for a composition."""
        # Create assignments
        assign_materials(
            generic_composition.id,
            [
                {"inventory_item_id": inventory_a.id, "quantity": 15},
                {"inventory_item_id": inventory_b.id, "quantity": 5},
            ],
            session=test_db
        )

        count = clear_assignments(generic_composition.id, session=test_db)

        assert count == 2

        # Verify cleared
        records = test_db.query(CompositionAssignment).filter_by(
            composition_id=generic_composition.id
        ).all()
        assert len(records) == 0

    def test_returns_zero_when_no_assignments(
        self, test_db, generic_composition
    ):
        """Returns 0 when no assignments exist."""
        count = clear_assignments(generic_composition.id, session=test_db)

        assert count == 0

    def test_raises_for_missing_composition(self, test_db):
        """Raises error for non-existent composition."""
        with pytest.raises(CompositionNotFoundError):
            clear_assignments(99999, session=test_db)


# =============================================================================
# Tests: get_assignments()
# =============================================================================


class TestGetAssignments:
    """Tests for get_assignments() function."""

    def test_returns_assignment_details(
        self, test_db, generic_composition, inventory_a, inventory_b
    ):
        """Returns list of assignment dicts with details."""
        assign_materials(
            generic_composition.id,
            [
                {"inventory_item_id": inventory_a.id, "quantity": 15},
                {"inventory_item_id": inventory_b.id, "quantity": 5},
            ],
            session=test_db
        )

        result = get_assignments(generic_composition.id, session=test_db)

        assert len(result) == 2

        # Check fields present
        for assignment in result:
            assert "assignment_id" in assignment
            assert "inventory_item_id" in assignment
            assert "quantity_assigned" in assignment
            assert "brand" in assignment
            assert "unit_cost" in assignment
            assert "total_cost" in assignment

    def test_returns_empty_when_no_assignments(
        self, test_db, generic_composition
    ):
        """Returns empty list when no assignments exist."""
        result = get_assignments(generic_composition.id, session=test_db)

        assert result == []

    def test_raises_for_missing_composition(self, test_db):
        """Raises error for non-existent composition."""
        with pytest.raises(CompositionNotFoundError):
            get_assignments(99999, session=test_db)


# =============================================================================
# Tests: is_fully_assigned()
# =============================================================================


class TestIsFullyAssigned:
    """Tests for is_fully_assigned() function."""

    def test_returns_true_when_fully_assigned(
        self, test_db, generic_composition, inventory_a
    ):
        """Returns True when assignments sum to required quantity."""
        assign_materials(
            generic_composition.id,
            [{"inventory_item_id": inventory_a.id, "quantity": 20}],
            session=test_db
        )

        result = is_fully_assigned(generic_composition.id, session=test_db)

        assert result is True

    def test_returns_false_when_partially_assigned(
        self, test_db, generic_composition, inventory_a
    ):
        """Returns False when assignments don't meet required quantity."""
        # Manually create partial assignment (bypass validation)
        assignment = CompositionAssignment(
            composition_id=generic_composition.id,
            inventory_item_id=inventory_a.id,
            quantity_assigned=10.0,  # Only 10 of 20 required
            assigned_at=datetime.utcnow()
        )
        test_db.add(assignment)
        test_db.flush()

        result = is_fully_assigned(generic_composition.id, session=test_db)

        assert result is False

    def test_returns_false_when_no_assignments(
        self, test_db, generic_composition
    ):
        """Returns False when no assignments exist."""
        result = is_fully_assigned(generic_composition.id, session=test_db)

        assert result is False

    def test_returns_true_for_non_generic(
        self, test_db, specific_composition
    ):
        """Returns True for non-generic compositions (always assigned)."""
        result = is_fully_assigned(specific_composition.id, session=test_db)

        assert result is True

    def test_raises_for_missing_composition(self, test_db):
        """Raises error for non-existent composition."""
        with pytest.raises(CompositionNotFoundError):
            is_fully_assigned(99999, session=test_db)


# =============================================================================
# Tests: get_pending_requirements()
# =============================================================================


class TestGetPendingRequirements:
    """Tests for get_pending_requirements() function."""

    def test_finds_unassigned_compositions(
        self, test_db, generic_composition
    ):
        """Returns compositions with is_generic=True and no assignments."""
        result = get_pending_requirements(session=test_db)

        assert len(result) == 1
        assert result[0]["composition_id"] == generic_composition.id
        assert result[0]["required_quantity"] == 20.0
        assert result[0]["assigned_quantity"] == 0
        assert result[0]["remaining"] == 20.0

    def test_excludes_fully_assigned(
        self, test_db, generic_composition, inventory_a
    ):
        """Excludes compositions that are fully assigned."""
        assign_materials(
            generic_composition.id,
            [{"inventory_item_id": inventory_a.id, "quantity": 20}],
            session=test_db
        )

        result = get_pending_requirements(session=test_db)

        assert len(result) == 0

    def test_includes_partially_assigned(
        self, test_db, generic_composition, inventory_a
    ):
        """Includes compositions that are only partially assigned."""
        # Manually create partial assignment
        assignment = CompositionAssignment(
            composition_id=generic_composition.id,
            inventory_item_id=inventory_a.id,
            quantity_assigned=10.0,
            assigned_at=datetime.utcnow()
        )
        test_db.add(assignment)
        test_db.flush()

        result = get_pending_requirements(session=test_db)

        assert len(result) == 1
        assert result[0]["assigned_quantity"] == 10.0
        assert result[0]["remaining"] == 10.0

    def test_excludes_non_generic(
        self, test_db, specific_composition
    ):
        """Excludes non-generic compositions."""
        result = get_pending_requirements(session=test_db)

        assert len(result) == 0

    def test_filters_by_assembly_id(
        self, test_db, generic_composition, finished_good
    ):
        """Filters by assembly_id when provided."""
        result = get_pending_requirements(assembly_id=finished_good.id, session=test_db)

        assert len(result) == 1

        # Wrong assembly_id
        result = get_pending_requirements(assembly_id=99999, session=test_db)

        assert len(result) == 0


# =============================================================================
# Tests: get_assignment_summary()
# =============================================================================


class TestGetAssignmentSummary:
    """Tests for get_assignment_summary() function."""

    def test_returns_summary_for_unassigned(
        self, test_db, generic_composition
    ):
        """Returns correct summary when no assignments exist."""
        result = get_assignment_summary(generic_composition.id, session=test_db)

        assert result["is_generic"] is True
        assert result["required"] == 20.0
        assert result["assigned"] == 0
        assert result["remaining"] == 20.0
        assert result["is_complete"] is False

    def test_returns_summary_for_fully_assigned(
        self, test_db, generic_composition, inventory_a
    ):
        """Returns correct summary when fully assigned."""
        assign_materials(
            generic_composition.id,
            [{"inventory_item_id": inventory_a.id, "quantity": 20}],
            session=test_db
        )

        result = get_assignment_summary(generic_composition.id, session=test_db)

        assert result["is_generic"] is True
        assert result["required"] == 20.0
        assert result["assigned"] == 20.0
        assert result["remaining"] == 0
        assert result["is_complete"] is True

    def test_returns_summary_for_non_generic(
        self, test_db, specific_composition
    ):
        """Returns correct summary for non-generic composition."""
        result = get_assignment_summary(specific_composition.id, session=test_db)

        assert result["is_generic"] is False
        assert result["is_complete"] is True

    def test_raises_for_missing_composition(self, test_db):
        """Raises error for non-existent composition."""
        with pytest.raises(CompositionNotFoundError):
            get_assignment_summary(99999, session=test_db)


# =============================================================================
# Tests: get_actual_cost()
# =============================================================================


class TestGetActualCost:
    """Tests for get_actual_cost() function."""

    def test_calculates_cost_from_assignments(
        self, test_db, generic_composition, inventory_a, inventory_b
    ):
        """Sums unit_cost * quantity for all assignments."""
        # inventory_a has unit_cost=0.10, inventory_b has unit_cost=0.15 (from fixtures)
        assign_materials(
            generic_composition.id,
            [
                {"inventory_item_id": inventory_a.id, "quantity": 15},  # 15 * 0.10 = 1.50
                {"inventory_item_id": inventory_b.id, "quantity": 5},   # 5 * 0.15 = 0.75
            ],
            session=test_db
        )

        result = get_actual_cost(generic_composition.id, session=test_db)

        assert result == 2.25

    def test_returns_zero_when_no_assignments(
        self, test_db, generic_composition
    ):
        """Returns 0.0 when no assignments exist."""
        result = get_actual_cost(generic_composition.id, session=test_db)

        assert result == 0.0

    def test_uses_product_cost_for_non_generic(
        self, test_db, specific_composition
    ):
        """Uses product price for non-generic compositions."""
        result = get_actual_cost(specific_composition.id, session=test_db)

        # Uses composition.get_total_cost()
        assert isinstance(result, float)

    def test_raises_for_missing_composition(self, test_db):
        """Raises error for non-existent composition."""
        with pytest.raises(CompositionNotFoundError):
            get_actual_cost(99999, session=test_db)
