"""
Unit tests for manual inventory adjustment functionality (Feature 041).

Tests the manual_adjustment() and get_depletion_history() service methods
for recording manual inventory depletions with proper validation and cost tracking.
"""

import pytest
from decimal import Decimal
from datetime import date

from src.models.enums import DepletionReason
from src.services import (
    ingredient_service,
    product_service,
    inventory_item_service,
    supplier_service,
)
from src.services.exceptions import (
    ValidationError as ServiceValidationError,
    InventoryItemNotFound,
)


@pytest.fixture
def adjustment_test_supplier(test_db):
    """Create a test supplier for adjustment tests."""
    result = supplier_service.create_supplier(
        name="Adjustment Test Supplier",
        city="Boston",
        state="MA",
        zip_code="02101",
    )

    class SupplierObj:
        def __init__(self, supplier_dict):
            self.id = supplier_dict["id"]
            self.name = supplier_dict["name"]

    return SupplierObj(result)


@pytest.fixture
def adjustment_test_ingredient(test_db):
    """Create a test ingredient for adjustment tests."""
    return ingredient_service.create_ingredient(
        {
            "display_name": "Adjustment Test Flour",
            "category": "Flour",
        }
    )


@pytest.fixture
def adjustment_test_product(test_db, adjustment_test_ingredient):
    """Create a test product for adjustment tests."""
    return product_service.create_product(
        adjustment_test_ingredient.slug,
        {
            "brand": "Test Brand",
            "package_unit": "cup",
            "package_unit_quantity": Decimal("20.0"),
        },
    )


@pytest.fixture
def adjustment_test_inventory_item(test_db, adjustment_test_product, adjustment_test_supplier):
    """Create a test inventory item with 10 cups at $0.50/cup."""
    return inventory_item_service.add_to_inventory(
        product_id=adjustment_test_product.id,
        quantity=Decimal("10.0"),
        supplier_id=adjustment_test_supplier.id,
        unit_price=Decimal("0.50"),
        purchase_date=date(2026, 1, 1),
    )


class TestManualAdjustmentHappyPath:
    """Tests for successful manual adjustments."""

    def test_deplete_with_spoilage_reason(self, test_db, adjustment_test_inventory_item):
        """Depletion with SPOILAGE reason creates record and updates quantity."""
        initial_qty = adjustment_test_inventory_item.quantity

        depletion = inventory_item_service.manual_adjustment(
            inventory_item_id=adjustment_test_inventory_item.id,
            quantity_to_deplete=Decimal("3.0"),
            reason=DepletionReason.SPOILAGE,
            notes="Weevils discovered",
        )

        # Verify depletion record
        assert depletion.quantity_depleted == Decimal("3.0")
        assert depletion.depletion_reason == "spoilage"
        assert depletion.notes == "Weevils discovered"
        assert depletion.created_by == "desktop-user"

        # Verify inventory updated - refetch item to get current state
        items = inventory_item_service.get_inventory_items(
            product_id=adjustment_test_inventory_item.product_id
        )
        assert len(items) == 1
        assert abs(items[0].quantity - (initial_qty - 3.0)) < 0.001

    def test_deplete_with_gift_reason(self, test_db, adjustment_test_inventory_item):
        """Depletion with GIFT reason works correctly."""
        depletion = inventory_item_service.manual_adjustment(
            inventory_item_id=adjustment_test_inventory_item.id,
            quantity_to_deplete=Decimal("2.0"),
            reason=DepletionReason.GIFT,
            notes="Gave to neighbor",
        )

        assert depletion.depletion_reason == "gift"
        assert depletion.notes == "Gave to neighbor"

    def test_deplete_with_correction_reason(self, test_db, adjustment_test_inventory_item):
        """Depletion with CORRECTION reason works correctly."""
        depletion = inventory_item_service.manual_adjustment(
            inventory_item_id=adjustment_test_inventory_item.id,
            quantity_to_deplete=Decimal("1.5"),
            reason=DepletionReason.CORRECTION,
        )

        assert depletion.depletion_reason == "correction"

    def test_deplete_with_ad_hoc_usage_reason(self, test_db, adjustment_test_inventory_item):
        """Depletion with AD_HOC_USAGE reason works correctly."""
        depletion = inventory_item_service.manual_adjustment(
            inventory_item_id=adjustment_test_inventory_item.id,
            quantity_to_deplete=Decimal("0.5"),
            reason=DepletionReason.AD_HOC_USAGE,
        )

        assert depletion.depletion_reason == "ad_hoc_usage"

    def test_deplete_all_available_quantity(self, test_db, adjustment_test_inventory_item):
        """Can deplete entire available quantity (result is 0)."""
        initial_qty = Decimal(str(adjustment_test_inventory_item.quantity))

        depletion = inventory_item_service.manual_adjustment(
            inventory_item_id=adjustment_test_inventory_item.id,
            quantity_to_deplete=initial_qty,
            reason=DepletionReason.SPOILAGE,
            notes="Entire lot spoiled",
        )

        assert depletion.quantity_depleted == initial_qty

        # Verify inventory is now 0
        items = inventory_item_service.get_inventory_items(
            product_id=adjustment_test_inventory_item.product_id
        )
        # Item should exist but with 0 or near-0 quantity
        assert len(items) == 0 or items[0].quantity < 0.001


class TestManualAdjustmentValidation:
    """Tests for validation rules."""

    def test_cannot_deplete_more_than_available(self, test_db, adjustment_test_inventory_item):
        """Depleting more than available raises ValidationError."""
        with pytest.raises(ServiceValidationError) as exc_info:
            inventory_item_service.manual_adjustment(
                inventory_item_id=adjustment_test_inventory_item.id,
                quantity_to_deplete=Decimal("15.0"),  # Only 10 available
                reason=DepletionReason.SPOILAGE,
            )
        error_message = str(exc_info.value).lower()
        assert "only" in error_message or "10" in error_message

    def test_quantity_must_be_positive(self, test_db, adjustment_test_inventory_item):
        """Zero quantity raises ValidationError."""
        with pytest.raises(ServiceValidationError) as exc_info:
            inventory_item_service.manual_adjustment(
                inventory_item_id=adjustment_test_inventory_item.id,
                quantity_to_deplete=Decimal("0"),
                reason=DepletionReason.SPOILAGE,
            )
        assert "positive" in str(exc_info.value).lower()

    def test_negative_quantity_fails(self, test_db, adjustment_test_inventory_item):
        """Negative quantity raises ValidationError."""
        with pytest.raises(ServiceValidationError):
            inventory_item_service.manual_adjustment(
                inventory_item_id=adjustment_test_inventory_item.id,
                quantity_to_deplete=Decimal("-1.0"),
                reason=DepletionReason.SPOILAGE,
            )

    def test_other_reason_requires_notes(self, test_db, adjustment_test_inventory_item):
        """OTHER reason without notes raises ValidationError."""
        with pytest.raises(ServiceValidationError) as exc_info:
            inventory_item_service.manual_adjustment(
                inventory_item_id=adjustment_test_inventory_item.id,
                quantity_to_deplete=Decimal("1.0"),
                reason=DepletionReason.OTHER,
                notes=None,  # Missing notes
            )
        assert "notes" in str(exc_info.value).lower()

    def test_other_reason_with_empty_notes_fails(self, test_db, adjustment_test_inventory_item):
        """OTHER reason with empty string notes raises ValidationError."""
        with pytest.raises(ServiceValidationError) as exc_info:
            inventory_item_service.manual_adjustment(
                inventory_item_id=adjustment_test_inventory_item.id,
                quantity_to_deplete=Decimal("1.0"),
                reason=DepletionReason.OTHER,
                notes="",  # Empty string
            )
        assert "notes" in str(exc_info.value).lower()

    def test_other_reason_with_notes_succeeds(self, test_db, adjustment_test_inventory_item):
        """OTHER reason with notes succeeds."""
        depletion = inventory_item_service.manual_adjustment(
            inventory_item_id=adjustment_test_inventory_item.id,
            quantity_to_deplete=Decimal("1.0"),
            reason=DepletionReason.OTHER,
            notes="Custom reason explained here",
        )
        assert depletion.notes == "Custom reason explained here"
        assert depletion.depletion_reason == "other"

    def test_nonexistent_inventory_item_fails(self, test_db):
        """Non-existent inventory item ID raises InventoryItemNotFound."""
        with pytest.raises(InventoryItemNotFound):
            inventory_item_service.manual_adjustment(
                inventory_item_id=99999,  # Does not exist
                quantity_to_deplete=Decimal("1.0"),
                reason=DepletionReason.SPOILAGE,
            )


class TestCostCalculation:
    """Tests for cost impact calculation."""

    def test_cost_equals_quantity_times_unit_cost(self, test_db, adjustment_test_inventory_item):
        """Cost is calculated as quantity * unit_cost."""
        # item has unit_cost = 0.50
        depletion = inventory_item_service.manual_adjustment(
            inventory_item_id=adjustment_test_inventory_item.id,
            quantity_to_deplete=Decimal("4.0"),
            reason=DepletionReason.SPOILAGE,
        )

        expected_cost = Decimal("4.0") * Decimal("0.50")  # $2.00
        assert depletion.cost == expected_cost

    def test_cost_with_decimal_quantity(self, test_db, adjustment_test_inventory_item):
        """Cost calculation handles decimal quantities."""
        depletion = inventory_item_service.manual_adjustment(
            inventory_item_id=adjustment_test_inventory_item.id,
            quantity_to_deplete=Decimal("2.5"),
            reason=DepletionReason.SPOILAGE,
        )

        expected_cost = Decimal("2.5") * Decimal("0.50")  # $1.25
        assert depletion.cost == expected_cost

    def test_cost_with_zero_unit_cost(
        self, test_db, adjustment_test_product, adjustment_test_supplier
    ):
        """Cost is $0 when unit_cost is None/0."""
        # Create inventory item without unit_cost
        item = inventory_item_service.add_to_inventory(
            product_id=adjustment_test_product.id,
            quantity=Decimal("5.0"),
            supplier_id=adjustment_test_supplier.id,
            unit_price=Decimal("0"),  # Zero price
            purchase_date=date(2026, 1, 15),
        )

        depletion = inventory_item_service.manual_adjustment(
            inventory_item_id=item.id,
            quantity_to_deplete=Decimal("2.0"),
            reason=DepletionReason.SPOILAGE,
        )

        assert depletion.cost == Decimal("0")


class TestDepletionHistory:
    """Tests for depletion history retrieval."""

    def test_history_empty_for_new_item(self, test_db, adjustment_test_inventory_item):
        """New item has empty history."""
        history = inventory_item_service.get_depletion_history(
            inventory_item_id=adjustment_test_inventory_item.id,
        )
        assert history == []

    def test_history_contains_depletion_records(self, test_db, adjustment_test_inventory_item):
        """History contains created depletion records."""
        # Create a depletion
        inventory_item_service.manual_adjustment(
            inventory_item_id=adjustment_test_inventory_item.id,
            quantity_to_deplete=Decimal("1.0"),
            reason=DepletionReason.SPOILAGE,
            notes="First depletion",
        )

        history = inventory_item_service.get_depletion_history(
            inventory_item_id=adjustment_test_inventory_item.id,
        )

        assert len(history) == 1
        assert history[0].notes == "First depletion"

    def test_history_ordered_by_date_desc(self, test_db, adjustment_test_inventory_item):
        """History returns records newest first."""
        # Create multiple depletions
        inventory_item_service.manual_adjustment(
            inventory_item_id=adjustment_test_inventory_item.id,
            quantity_to_deplete=Decimal("1.0"),
            reason=DepletionReason.SPOILAGE,
            notes="First",
        )
        inventory_item_service.manual_adjustment(
            inventory_item_id=adjustment_test_inventory_item.id,
            quantity_to_deplete=Decimal("1.0"),
            reason=DepletionReason.GIFT,
            notes="Second",
        )
        inventory_item_service.manual_adjustment(
            inventory_item_id=adjustment_test_inventory_item.id,
            quantity_to_deplete=Decimal("1.0"),
            reason=DepletionReason.CORRECTION,
            notes="Third",
        )

        history = inventory_item_service.get_depletion_history(
            inventory_item_id=adjustment_test_inventory_item.id,
        )

        assert len(history) == 3
        # Newest should be first
        assert history[0].notes == "Third"
        assert history[1].notes == "Second"
        assert history[2].notes == "First"

    def test_history_only_returns_item_depletions(
        self,
        test_db,
        adjustment_test_inventory_item,
        adjustment_test_product,
        adjustment_test_supplier,
    ):
        """History only returns depletions for the specified item."""
        # Create depletion on first item
        inventory_item_service.manual_adjustment(
            inventory_item_id=adjustment_test_inventory_item.id,
            quantity_to_deplete=Decimal("1.0"),
            reason=DepletionReason.SPOILAGE,
            notes="Item 1 depletion",
        )

        # Create second inventory item and depletion
        item2 = inventory_item_service.add_to_inventory(
            product_id=adjustment_test_product.id,
            quantity=Decimal("5.0"),
            supplier_id=adjustment_test_supplier.id,
            unit_price=Decimal("0.75"),
            purchase_date=date(2026, 1, 10),
        )
        inventory_item_service.manual_adjustment(
            inventory_item_id=item2.id,
            quantity_to_deplete=Decimal("1.0"),
            reason=DepletionReason.GIFT,
            notes="Item 2 depletion",
        )

        # Get history for first item only
        history = inventory_item_service.get_depletion_history(
            inventory_item_id=adjustment_test_inventory_item.id,
        )

        assert len(history) == 1
        assert history[0].notes == "Item 1 depletion"


class TestAuditTrail:
    """Tests for audit trail fields."""

    def test_depletion_has_created_by(self, test_db, adjustment_test_inventory_item):
        """Depletion record has created_by set to 'desktop-user'."""
        depletion = inventory_item_service.manual_adjustment(
            inventory_item_id=adjustment_test_inventory_item.id,
            quantity_to_deplete=Decimal("1.0"),
            reason=DepletionReason.SPOILAGE,
        )

        assert depletion.created_by == "desktop-user"

    def test_depletion_has_created_at(self, test_db, adjustment_test_inventory_item):
        """Depletion record has created_at timestamp."""
        depletion = inventory_item_service.manual_adjustment(
            inventory_item_id=adjustment_test_inventory_item.id,
            quantity_to_deplete=Decimal("1.0"),
            reason=DepletionReason.SPOILAGE,
        )

        assert depletion.created_at is not None

    def test_depletion_has_depletion_date(self, test_db, adjustment_test_inventory_item):
        """Depletion record has depletion_date timestamp."""
        depletion = inventory_item_service.manual_adjustment(
            inventory_item_id=adjustment_test_inventory_item.id,
            quantity_to_deplete=Decimal("1.0"),
            reason=DepletionReason.SPOILAGE,
        )

        assert depletion.depletion_date is not None

    def test_depletion_has_uuid(self, test_db, adjustment_test_inventory_item):
        """Depletion record has UUID for distributed scenarios."""
        depletion = inventory_item_service.manual_adjustment(
            inventory_item_id=adjustment_test_inventory_item.id,
            quantity_to_deplete=Decimal("1.0"),
            reason=DepletionReason.SPOILAGE,
        )

        assert depletion.uuid is not None
        assert len(depletion.uuid) == 36  # Standard UUID format
