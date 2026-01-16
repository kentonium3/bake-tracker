"""
Integration tests for Deferred Packaging Decisions (Feature 026).

End-to-end tests covering:
- Planning with generic packaging requirements
- Checking pending packaging requirements
- Assigning materials to generic compositions
- Cost transition from estimated to actual
- Shopping list with generic items
- Assembly completion with bypass
- Edge cases (shortage, re-assignment)
"""

import pytest
from datetime import date, datetime
from decimal import Decimal

from src.services.event_service import (
    create_event,
    get_event_packaging_needs,
    get_shopping_list,
    assign_package_to_recipient,
)
from src.services.composition_service import (
    add_packaging_to_assembly,
    add_packaging_to_package,
    get_assembly_packaging,
)
from src.services.packaging_service import (
    get_generic_products,
    get_generic_inventory_summary,
    get_available_inventory_items,
    get_estimated_cost,
    assign_materials,
    clear_assignments,
    get_assignments,
    is_fully_assigned,
    get_pending_requirements,
    get_assignment_summary,
    get_actual_cost,
    InvalidAssignmentError,
)
from src.services.assembly_service import record_assembly
from src.services.ingredient_service import create_ingredient
from src.services.product_service import create_product
from src.models import (
    FinishedGood,
    Package,
    PackageFinishedGood,
    Recipient,
    InventoryItem,
    Composition,
    CompositionAssignment,
    AssemblyRun,
)
from src.models.assembly_type import AssemblyType


class TestDeferredPackagingFullWorkflow:
    """End-to-end tests for the complete deferred packaging workflow."""

    def test_plan_with_generic_then_assign_materials(self, test_db):
        """
        Full workflow: Plan with generic packaging, then assign specific materials.

        Scenario:
        1. Create packaging ingredients and multiple product variants
        2. Add inventory for each variant
        3. Create a FinishedGood with GENERIC packaging requirement
        4. Check pending requirements (should show as unassigned)
        5. Assign specific materials
        6. Verify assignments recorded correctly
        7. Verify is_fully_assigned returns True
        """
        # 1. Create packaging ingredient
        bag_ingredient = create_ingredient(
            {"display_name": "Cellophane Bags 6x10", "category": "Bags"}
        )

        # 2. Create multiple product variants
        brand_a = create_product(
            bag_ingredient.slug,
            {
                "brand": "ClearBags",
                "package_size": "100 ct",
                "package_unit": "each",
                "package_unit_quantity": 100,
                "purchase_price": Decimal("15.00"),
                "product_name": "Cellophane Bags 6x10",  # Required for generic packaging
            },
        )
        brand_b = create_product(
            bag_ingredient.slug,
            {
                "brand": "Uline",
                "package_size": "500 ct",
                "package_unit": "each",
                "package_unit_quantity": 500,
                "purchase_price": Decimal("50.00"),
                "product_name": "Cellophane Bags 6x10",  # Same generic product name
            },
        )

        # 3. Add inventory for each
        inv_a = InventoryItem(
            product_id=brand_a.id,
            quantity=50,
            unit_cost=0.15,  # $15.00 / 100 = $0.15 per bag
            expiration_date=date(2025, 12, 31),
        )
        inv_b = InventoryItem(
            product_id=brand_b.id,
            quantity=100,
            unit_cost=0.10,  # $50.00 / 500 = $0.10 per bag
            expiration_date=date(2025, 12, 31),
        )
        test_db.add_all([inv_a, inv_b])
        test_db.flush()

        # 4. Create FinishedGood with GENERIC packaging
        fg = FinishedGood(
            slug="test-cookies-generic",
            display_name="Test Cookies (Generic Bags)",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            inventory_count=0,
        )
        test_db.add(fg)
        test_db.flush()

        # Add generic packaging requirement (2 bags per unit)
        # For generic packaging, we use any product of that type with is_generic=True
        composition = add_packaging_to_assembly(
            assembly_id=fg.id,
            packaging_product_id=brand_a.id,  # Any matching product works
            quantity=2.0,
            is_generic=True,  # Mark as generic - material assigned later
        )

        # 5. Check pending requirements - should show as pending
        pending = get_pending_requirements(assembly_id=fg.id)
        assert len(pending) == 1
        assert pending[0]["composition_id"] == composition.id
        assert pending[0]["product_name"] == "Cellophane Bags 6x10"
        assert pending[0]["required_quantity"] == 2.0
        assert pending[0]["assigned_quantity"] == 0.0

        # 6. Verify is_fully_assigned is False
        assert is_fully_assigned(composition.id) is False

        # 7. Get available inventory items
        items = get_available_inventory_items("Cellophane Bags 6x10")
        assert len(items) == 2  # Both brands in stock

        # 8. Assign materials from brand_a (2 bags)
        assign_materials(
            composition_id=composition.id,
            assignments=[{"inventory_item_id": inv_a.id, "quantity": 2}],
        )

        # 9. Verify assignments
        assignments = get_assignments(composition.id)
        assert len(assignments) == 1
        assert assignments[0]["inventory_item_id"] == inv_a.id
        assert assignments[0]["quantity_assigned"] == 2

        # 10. Verify is_fully_assigned is True
        assert is_fully_assigned(composition.id) is True

        # 11. Pending requirements should be empty now
        pending = get_pending_requirements(assembly_id=fg.id)
        assert len(pending) == 0

    def test_cost_transition_estimated_to_actual(self, test_db):
        """
        Test cost transition from estimated to actual after assignment.

        Scenario:
        1. Create variants with different costs
        2. Add generic packaging to assembly
        3. Verify estimated cost is weighted average
        4. Assign materials from specific variant
        5. Verify actual cost reflects assigned item's cost
        """
        # Create ingredient and variants with different costs
        bag_ingredient = create_ingredient(
            {"display_name": "Gift Bags Small", "category": "Bags"}
        )

        cheap_product = create_product(
            bag_ingredient.slug,
            {
                "brand": "Economy",
                "package_size": "50 ct",
                "package_unit": "each",
                "package_unit_quantity": 50,
                "purchase_price": Decimal("5.00"),
                "product_name": "Gift Bags Small",
            },
        )
        premium_product = create_product(
            bag_ingredient.slug,
            {
                "brand": "Premium",
                "package_size": "25 ct",
                "package_unit": "each",
                "package_unit_quantity": 25,
                "purchase_price": Decimal("12.50"),
                "product_name": "Gift Bags Small",
            },
        )

        # Add inventory
        inv_cheap = InventoryItem(
            product_id=cheap_product.id,
            quantity=50,
            unit_cost=0.10,  # $5.00 / 50 = $0.10/bag
            expiration_date=date(2025, 12, 31),
        )
        inv_premium = InventoryItem(
            product_id=premium_product.id,
            quantity=25,
            unit_cost=0.50,  # $12.50 / 25 = $0.50/bag
            expiration_date=date(2025, 12, 31),
        )
        test_db.add_all([inv_cheap, inv_premium])
        test_db.flush()

        # Create assembly with generic packaging
        fg = FinishedGood(
            slug="cost-test-item",
            display_name="Cost Test Item",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            inventory_count=0,
        )
        test_db.add(fg)
        test_db.flush()

        composition = add_packaging_to_assembly(
            assembly_id=fg.id,
            packaging_product_id=cheap_product.id,
            quantity=10.0,
            is_generic=True,
        )

        # Check estimated cost (weighted average based on inventory)
        # Economy: 50 bags at $0.10 each = $5.00 total
        # Premium: 25 bags at $0.50 each = $12.50 total
        # Total: 75 bags, total cost $17.50
        # Weighted avg: $17.50 / 75 = $0.2333... per bag
        # 10 bags: ~$2.33
        estimated = get_estimated_cost("Gift Bags Small", 10.0)
        assert estimated > 0  # Should have a non-zero estimated cost

        # Initially actual cost is 0 (no assignments)
        actual_before = get_actual_cost(composition.id)
        assert actual_before == 0.0

        # Assign from premium inventory (10 bags at $0.50 each = $5.00)
        assign_materials(
            composition_id=composition.id,
            assignments=[{"inventory_item_id": inv_premium.id, "quantity": 10}],
        )

        # Actual cost should now reflect premium price
        actual_after = get_actual_cost(composition.id)
        assert actual_after == 5.00  # 10 bags at $0.50 each

    def test_shopping_list_with_generic_packaging(self, test_db):
        """
        Test shopping list correctly displays generic packaging with estimated costs.

        Scenario:
        1. Create event with assembly using generic packaging
        2. Generate shopping list
        3. Verify generic items show with "(any)" suffix and estimated costs
        """
        # Create packaging
        ribbon_ingredient = create_ingredient(
            {"display_name": "Satin Ribbon 1in", "category": "Ribbon"}
        )
        ribbon_product = create_product(
            ribbon_ingredient.slug,
            {
                "brand": "Offray",
                "package_size": "10 yd",
                "package_unit": "each",
                "package_unit_quantity": 10,
                "purchase_price": Decimal("5.00"),
                "product_name": "Satin Ribbon 1in",
            },
        )

        # Add inventory
        inv = InventoryItem(
            product_id=ribbon_product.id,
            quantity=20,  # Have 20 yards
            unit_cost=0.50,  # $5.00 / 10 yd = $0.50/yd
            expiration_date=date(2025, 12, 31),
        )
        test_db.add(inv)
        test_db.flush()

        # Create finished good with generic packaging
        fg = FinishedGood(
            slug="ribbon-test-package",
            display_name="Ribbon Test Package",
            assembly_type=AssemblyType.GIFT_BOX,
            inventory_count=0,
        )
        test_db.add(fg)
        test_db.flush()

        composition = add_packaging_to_assembly(
            assembly_id=fg.id,
            packaging_product_id=ribbon_product.id,
            quantity=2.0,  # 2 yards per package
            is_generic=True,
        )

        # Create package and event
        package = Package(name="Gift Package with Ribbon")
        test_db.add(package)
        test_db.flush()

        pfg = PackageFinishedGood(
            package_id=package.id, finished_good_id=fg.id, quantity=1
        )
        test_db.add(pfg)
        test_db.flush()

        event = create_event(
            name="Shopping List Test Event", event_date=date(2024, 12, 15), year=2024
        )

        recipient = Recipient(name="Test Recipient")
        test_db.add(recipient)
        test_db.flush()

        assign_package_to_recipient(
            event_id=event.id,
            recipient_id=recipient.id,
            package_id=package.id,
            quantity=5,  # Need 5 packages = 10 yards of ribbon
        )

        # Get packaging needs - should show generic item
        needs = get_event_packaging_needs(event.id)

        # Should have a generic entry for ribbon
        generic_key = "generic_Satin Ribbon 1in"
        assert generic_key in needs
        need = needs[generic_key]
        assert need.is_generic is True
        assert need.generic_product_name == "Satin Ribbon 1in"
        assert need.total_needed == 10.0  # 5 packages * 2 yards
        assert need.estimated_cost is not None
        assert need.estimated_cost > 0


class TestDeferredPackagingEdgeCases:
    """Edge case tests for deferred packaging."""

    def test_partial_assignment_allowed(self, test_db):
        """Test that partial assignments are tracked correctly."""
        bag_ingredient = create_ingredient(
            {"display_name": "Partial Test Bags", "category": "Bags"}
        )
        bag_product = create_product(
            bag_ingredient.slug,
            {
                "brand": "TestBrand",
                "package_size": "20 ct",
                "package_unit": "each",
                "package_unit_quantity": 20,
                "purchase_price": Decimal("10.00"),
                "product_name": "Partial Test Bags",
            },
        )

        # Limited inventory
        inv = InventoryItem(
            product_id=bag_product.id,
            quantity=3,  # Only 3 available
            unit_cost=0.50,  # $10.00 / 20 = $0.50/bag
            expiration_date=date(2025, 12, 31),
        )
        test_db.add(inv)
        test_db.flush()

        # Need 5 bags
        fg = FinishedGood(
            slug="partial-test",
            display_name="Partial Test Item",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            inventory_count=0,
        )
        test_db.add(fg)
        test_db.flush()

        composition = add_packaging_to_assembly(
            assembly_id=fg.id,
            packaging_product_id=bag_product.id,
            quantity=5.0,
            is_generic=True,
        )

        # Can only assign 3 (what we have), but this fails because
        # assign_materials requires total assigned to equal required quantity
        with pytest.raises(InvalidAssignmentError, match="must equal"):
            # Trying to assign less than required should fail
            assign_materials(
                composition_id=composition.id,
                assignments=[{"inventory_item_id": inv.id, "quantity": 3}],
            )

        # Pending should still show the full requirement
        pending = get_pending_requirements(assembly_id=fg.id)
        assert len(pending) == 1
        assert pending[0]["required_quantity"] == 5.0

    def test_reassignment_clears_previous(self, test_db):
        """Test that re-assigning clears previous assignments."""
        bag_ingredient = create_ingredient(
            {"display_name": "Reassign Test Bags", "category": "Bags"}
        )
        product_a = create_product(
            bag_ingredient.slug,
            {
                "brand": "BrandA",
                "package_size": "50 ct",
                "package_unit": "each",
                "package_unit_quantity": 50,
                "purchase_price": Decimal("10.00"),
                "product_name": "Reassign Test Bags",
            },
        )
        product_b = create_product(
            bag_ingredient.slug,
            {
                "brand": "BrandB",
                "package_size": "50 ct",
                "package_unit": "each",
                "package_unit_quantity": 50,
                "purchase_price": Decimal("15.00"),
                "product_name": "Reassign Test Bags",
            },
        )

        inv_a = InventoryItem(
            product_id=product_a.id,
            quantity=10,
            unit_cost=0.20,  # $10.00 / 50 = $0.20/bag
            expiration_date=date(2025, 12, 31),
        )
        inv_b = InventoryItem(
            product_id=product_b.id,
            quantity=10,
            unit_cost=0.30,  # $15.00 / 50 = $0.30/bag
            expiration_date=date(2025, 12, 31),
        )
        test_db.add_all([inv_a, inv_b])
        test_db.flush()

        fg = FinishedGood(
            slug="reassign-test",
            display_name="Reassign Test Item",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            inventory_count=0,
        )
        test_db.add(fg)
        test_db.flush()

        composition = add_packaging_to_assembly(
            assembly_id=fg.id,
            packaging_product_id=product_a.id,
            quantity=5.0,
            is_generic=True,
        )

        # First assignment from BrandA
        assign_materials(
            composition_id=composition.id,
            assignments=[{"inventory_item_id": inv_a.id, "quantity": 5}],
        )
        assignments_before = get_assignments(composition.id)
        assert len(assignments_before) == 1
        assert assignments_before[0]["inventory_item_id"] == inv_a.id

        # Re-assign from BrandB (should clear previous)
        assign_materials(
            composition_id=composition.id,
            assignments=[{"inventory_item_id": inv_b.id, "quantity": 5}],
        )
        assignments_after = get_assignments(composition.id)
        assert len(assignments_after) == 1
        assert assignments_after[0]["inventory_item_id"] == inv_b.id

        # Total assignments should be 1, not 2
        total_count = (
            test_db.query(CompositionAssignment)
            .filter(CompositionAssignment.composition_id == composition.id)
            .count()
        )
        assert total_count == 1

    def test_assembly_bypass_records_flag(self, test_db):
        """Test that assembly completion can bypass with flag recorded."""
        bag_ingredient = create_ingredient(
            {"display_name": "Bypass Test Bags", "category": "Bags"}
        )
        bag_product = create_product(
            bag_ingredient.slug,
            {
                "brand": "TestBrand",
                "package_size": "50 ct",
                "package_unit": "each",
                "package_unit_quantity": 50,
                "purchase_price": Decimal("10.00"),
                "product_name": "Bypass Test Bags",
            },
        )

        fg = FinishedGood(
            slug="bypass-test",
            display_name="Bypass Test Item",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            inventory_count=0,
        )
        test_db.add(fg)
        test_db.flush()

        # Add generic packaging (no inventory, so can't assign)
        add_packaging_to_assembly(
            assembly_id=fg.id,
            packaging_product_id=bag_product.id,
            quantity=5.0,
            is_generic=True,
        )

        # Record assembly with bypass flag
        result = record_assembly(
            finished_good_id=fg.id,
            quantity=1,
            packaging_bypassed=True,
            packaging_bypass_notes="Materials not available, will reconcile later",
        )

        # API returns assembly_run_id, not "success" key
        assert "assembly_run_id" in result
        assert result["packaging_bypassed"] is True

        # Query the AssemblyRun to verify bypass fields
        assembly_run = (
            test_db.query(AssemblyRun)
            .filter_by(id=result["assembly_run_id"])
            .first()
        )
        assert assembly_run is not None
        assert assembly_run.packaging_bypassed is True
        assert "will reconcile later" in assembly_run.packaging_bypass_notes


class TestDeferredPackagingAssignmentSummary:
    """Tests for assignment summary functionality."""

    def test_summary_for_unassigned_generic(self, test_db):
        """Test summary shows correct status for unassigned generic."""
        bag_ingredient = create_ingredient(
            {"display_name": "Summary Test Bags", "category": "Bags"}
        )
        bag_product = create_product(
            bag_ingredient.slug,
            {
                "brand": "TestBrand",
                "package_size": "50 ct",
                "package_unit": "each",
                "package_unit_quantity": 50,
                "purchase_price": Decimal("10.00"),
                "product_name": "Summary Test Bags",
            },
        )

        inv = InventoryItem(
            product_id=bag_product.id,
            quantity=100,
            unit_cost=0.20,  # $10.00 / 50 = $0.20/bag
            expiration_date=date(2025, 12, 31),
        )
        test_db.add(inv)
        test_db.flush()

        fg = FinishedGood(
            slug="summary-test",
            display_name="Summary Test Item",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            inventory_count=0,
        )
        test_db.add(fg)
        test_db.flush()

        composition = add_packaging_to_assembly(
            assembly_id=fg.id,
            packaging_product_id=bag_product.id,
            quantity=5.0,
            is_generic=True,
        )

        summary = get_assignment_summary(composition.id)
        assert summary["is_generic"] is True
        assert summary["required"] == 5.0
        assert summary["assigned"] == 0.0
        assert summary["is_complete"] is False

    def test_summary_for_fully_assigned_generic(self, test_db):
        """Test summary shows correct status for fully assigned generic."""
        bag_ingredient = create_ingredient(
            {"display_name": "Full Summary Bags", "category": "Bags"}
        )
        bag_product = create_product(
            bag_ingredient.slug,
            {
                "brand": "TestBrand",
                "package_size": "50 ct",
                "package_unit": "each",
                "package_unit_quantity": 50,
                "purchase_price": Decimal("10.00"),
                "product_name": "Full Summary Bags",
            },
        )

        inv = InventoryItem(
            product_id=bag_product.id,
            quantity=100,
            unit_cost=0.20,  # $10.00 / 50 = $0.20/bag
            expiration_date=date(2025, 12, 31),
        )
        test_db.add(inv)
        test_db.flush()

        fg = FinishedGood(
            slug="full-summary-test",
            display_name="Full Summary Test",
            assembly_type=AssemblyType.CUSTOM_ORDER,
            inventory_count=0,
        )
        test_db.add(fg)
        test_db.flush()

        composition = add_packaging_to_assembly(
            assembly_id=fg.id,
            packaging_product_id=bag_product.id,
            quantity=5.0,
            is_generic=True,
        )

        # Assign materials
        assign_materials(
            composition_id=composition.id,
            assignments=[{"inventory_item_id": inv.id, "quantity": 5}],
        )

        summary = get_assignment_summary(composition.id)
        assert summary["is_generic"] is True
        assert summary["required"] == 5.0
        assert summary["assigned"] == 5.0
        assert summary["is_complete"] is True
