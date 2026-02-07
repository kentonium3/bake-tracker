"""
Unit tests for finished_goods_inventory_service (Feature 061).

Tests cover all 6 service functions:
- get_inventory_status()
- get_low_stock_items()
- get_total_inventory_value()
- check_availability()
- validate_consumption()
- adjust_inventory()
"""

import pytest
from decimal import Decimal

from src.services import finished_goods_inventory_service as fg_inv
from src.models import FinishedUnit, FinishedGood, FinishedGoodsAdjustment, Recipe
from src.models.finished_unit import YieldMode
from src.models.assembly_type import AssemblyType


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_recipe(test_db):
    """Create a sample recipe for testing."""
    session = test_db()
    recipe = Recipe(
        name="Test Cookie Recipe",
        category="Cookies",
        notes="Test recipe for unit tests",
    )
    session.add(recipe)
    session.commit()
    session.refresh(recipe)
    return recipe


@pytest.fixture
def sample_finished_unit(test_db, sample_recipe):
    """Create a sample finished unit with inventory."""
    session = test_db()
    fu = FinishedUnit(
        display_name="Test Cookies",
        slug="test-cookies",
        recipe_id=sample_recipe.id,
        yield_mode=YieldMode.DISCRETE_COUNT,
        items_per_batch=24,
        inventory_count=50,
    )
    session.add(fu)
    session.commit()
    session.refresh(fu)
    return fu


@pytest.fixture
def sample_finished_good(test_db):
    """Create a sample finished good (assembly) with inventory."""
    session = test_db()
    fg = FinishedGood(
        display_name="Cookie Gift Box",
        slug="cookie-gift-box",
        assembly_type=AssemblyType.BUNDLE,
        inventory_count=10,
    )
    session.add(fg)
    session.commit()
    session.refresh(fg)
    return fg


# =============================================================================
# T024: Tests for get_inventory_status()
# =============================================================================


class TestGetInventoryStatus:
    """Tests for get_inventory_status()"""

    def test_get_all_items(self, test_db, sample_finished_unit, sample_finished_good):
        """Returns both FU and FG when no filter."""
        session = test_db()
        result = fg_inv.get_inventory_status(session=session)
        assert len(result) >= 2
        types = {r["item_type"] for r in result}
        assert "finished_unit" in types
        assert "finished_good" in types

    def test_filter_by_finished_unit(self, test_db, sample_finished_unit, sample_finished_good):
        """Returns only FinishedUnits when filtered."""
        session = test_db()
        result = fg_inv.get_inventory_status(item_type="finished_unit", session=session)
        assert len(result) >= 1
        assert all(r["item_type"] == "finished_unit" for r in result)

    def test_filter_by_finished_good(self, test_db, sample_finished_unit, sample_finished_good):
        """Returns only FinishedGoods when filtered."""
        session = test_db()
        result = fg_inv.get_inventory_status(item_type="finished_good", session=session)
        assert len(result) >= 1
        assert all(r["item_type"] == "finished_good" for r in result)

    def test_filter_by_item_id(self, test_db, sample_finished_unit):
        """Returns specific item when filtered by ID."""
        session = test_db()
        result = fg_inv.get_inventory_status(
            item_type="finished_unit",
            item_id=sample_finished_unit.id,
            session=session,
        )
        assert len(result) == 1
        assert result[0]["id"] == sample_finished_unit.id

    def test_exclude_zero_inventory(self, test_db, sample_finished_unit):
        """Excludes items with zero inventory when flag set."""
        session = test_db()
        # Set inventory to zero
        sample_finished_unit.inventory_count = 0
        session.merge(sample_finished_unit)
        session.commit()

        result = fg_inv.get_inventory_status(exclude_zero=True, session=session)
        fu_ids = [r["id"] for r in result if r["item_type"] == "finished_unit"]
        assert sample_finished_unit.id not in fu_ids

    def test_invalid_item_type_raises(self, test_db):
        """Raises ValueError for invalid item_type."""
        session = test_db()
        with pytest.raises(ValueError, match="Invalid item_type"):
            fg_inv.get_inventory_status(item_type="invalid", session=session)

    def test_item_id_without_type_raises(self, test_db):
        """Raises ValueError when item_id provided without item_type."""
        session = test_db()
        with pytest.raises(ValueError, match="item_id requires item_type"):
            fg_inv.get_inventory_status(item_id=1, session=session)

    def test_returns_dict_structure(self, test_db, sample_finished_unit):
        """Returns proper dict structure with all fields."""
        session = test_db()
        result = fg_inv.get_inventory_status(
            item_type="finished_unit",
            item_id=sample_finished_unit.id,
            session=session,
        )
        assert len(result) == 1
        item = result[0]
        assert "item_type" in item
        assert "id" in item
        assert "slug" in item
        assert "display_name" in item
        assert "inventory_count" in item
        assert "current_cost" in item
        assert "total_value" in item
        assert isinstance(item["current_cost"], Decimal)
        assert isinstance(item["total_value"], Decimal)

    def test_works_without_session(self, test_db, sample_finished_unit):
        """Works when session=None (creates own transaction)."""
        # Note: test_db fixture patches the global session factory
        result = fg_inv.get_inventory_status(item_type="finished_unit")
        assert isinstance(result, list)


# =============================================================================
# T025: Tests for check_availability() and validate_consumption()
# =============================================================================


class TestCheckAvailability:
    """Tests for check_availability()"""

    def test_available_when_sufficient(self, test_db, sample_finished_unit):
        """Returns available=True when sufficient inventory."""
        session = test_db()
        # sample_finished_unit has inventory_count=50
        result = fg_inv.check_availability(
            "finished_unit", sample_finished_unit.id, 30, session=session
        )
        assert result["available"] is True
        assert result["current_count"] == 50
        assert result["requested"] == 30
        assert "shortage" not in result

    def test_unavailable_when_insufficient(self, test_db, sample_finished_unit):
        """Returns available=False with shortage when insufficient."""
        session = test_db()
        result = fg_inv.check_availability(
            "finished_unit", sample_finished_unit.id, 60, session=session
        )
        assert result["available"] is False
        assert result["shortage"] == 10  # Need 60, have 50

    def test_item_not_found_raises(self, test_db):
        """Raises ValueError when item doesn't exist."""
        session = test_db()
        with pytest.raises(ValueError, match="not found"):
            fg_inv.check_availability("finished_unit", 99999, 5, session=session)

    def test_invalid_item_type_raises(self, test_db):
        """Raises ValueError for invalid item_type."""
        session = test_db()
        with pytest.raises(ValueError, match="Invalid item_type"):
            fg_inv.check_availability("invalid", 1, 5, session=session)

    def test_zero_quantity_raises(self, test_db, sample_finished_unit):
        """Raises ValueError for zero quantity."""
        session = test_db()
        with pytest.raises(ValueError, match="positive"):
            fg_inv.check_availability(
                "finished_unit", sample_finished_unit.id, 0, session=session
            )

    def test_negative_quantity_raises(self, test_db, sample_finished_unit):
        """Raises ValueError for negative quantity."""
        session = test_db()
        with pytest.raises(ValueError, match="positive"):
            fg_inv.check_availability(
                "finished_unit", sample_finished_unit.id, -5, session=session
            )

    def test_works_with_finished_good(self, test_db, sample_finished_good):
        """Works for finished_good item type."""
        session = test_db()
        result = fg_inv.check_availability(
            "finished_good", sample_finished_good.id, 5, session=session
        )
        assert result["available"] is True
        assert result["item_type"] == "finished_good"


class TestValidateConsumption:
    """Tests for validate_consumption()"""

    def test_valid_when_sufficient(self, test_db, sample_finished_unit):
        """Returns valid=True with remaining_after when sufficient."""
        session = test_db()
        result = fg_inv.validate_consumption(
            "finished_unit", sample_finished_unit.id, 20, session=session
        )
        assert result["valid"] is True
        assert result["remaining_after"] == 30  # 50 - 20

    def test_invalid_when_insufficient(self, test_db, sample_finished_unit):
        """Returns valid=False with error message when insufficient."""
        session = test_db()
        result = fg_inv.validate_consumption(
            "finished_unit", sample_finished_unit.id, 60, session=session
        )
        assert result["valid"] is False
        assert "error" in result
        assert result["shortage"] == 10

    def test_item_not_found_raises(self, test_db):
        """Raises ValueError when item doesn't exist."""
        session = test_db()
        with pytest.raises(ValueError, match="not found"):
            fg_inv.validate_consumption("finished_unit", 99999, 5, session=session)

    def test_works_with_finished_good(self, test_db, sample_finished_good):
        """Works for finished_good item type."""
        session = test_db()
        result = fg_inv.validate_consumption(
            "finished_good", sample_finished_good.id, 5, session=session
        )
        assert result["valid"] is True
        assert result["remaining_after"] == 5  # 10 - 5


# =============================================================================
# T026: Tests for adjust_inventory()
# =============================================================================


class TestAdjustInventory:
    """Tests for adjust_inventory()"""

    def test_positive_adjustment(self, test_db, sample_finished_unit):
        """Positive quantity increases inventory."""
        session = test_db()
        initial_count = sample_finished_unit.inventory_count

        result = fg_inv.adjust_inventory(
            "finished_unit",
            sample_finished_unit.id,
            10,
            "production",
            notes="Test production",
            session=session,
        )

        assert result["success"] is True
        assert result["previous_count"] == initial_count
        assert result["new_count"] == initial_count + 10
        assert result["quantity_change"] == 10

        # Verify in database
        session.refresh(sample_finished_unit)
        assert sample_finished_unit.inventory_count == initial_count + 10

    def test_negative_adjustment(self, test_db, sample_finished_unit):
        """Negative quantity decreases inventory."""
        session = test_db()
        initial_count = sample_finished_unit.inventory_count

        result = fg_inv.adjust_inventory(
            "finished_unit",
            sample_finished_unit.id,
            -15,
            "consumption",
            notes="Test consumption",
            session=session,
        )

        assert result["new_count"] == initial_count - 15
        session.refresh(sample_finished_unit)
        assert sample_finished_unit.inventory_count == initial_count - 15

    def test_creates_audit_record(self, test_db, sample_finished_unit):
        """Creates FinishedGoodsAdjustment record."""
        session = test_db()
        initial_count = sample_finished_unit.inventory_count

        result = fg_inv.adjust_inventory(
            "finished_unit",
            sample_finished_unit.id,
            5,
            "production",
            notes="Test production run",
            session=session,
        )

        # Verify audit record
        adjustment = (
            session.query(FinishedGoodsAdjustment)
            .filter_by(id=result["adjustment_id"])
            .first()
        )
        assert adjustment is not None
        assert adjustment.finished_unit_id == sample_finished_unit.id
        assert adjustment.finished_good_id is None  # XOR constraint
        assert adjustment.quantity_change == 5
        assert adjustment.previous_count == initial_count
        assert adjustment.new_count == initial_count + 5
        assert adjustment.reason == "production"
        assert adjustment.notes == "Test production run"

    def test_prevents_negative_inventory(self, test_db, sample_finished_unit):
        """Raises ValueError when adjustment would cause negative inventory."""
        session = test_db()
        initial_count = sample_finished_unit.inventory_count

        with pytest.raises(ValueError, match="negative inventory"):
            fg_inv.adjust_inventory(
                "finished_unit",
                sample_finished_unit.id,
                -(initial_count + 10),  # More than available
                "consumption",
                notes="Test",
                session=session,
            )

        # Verify inventory unchanged
        session.refresh(sample_finished_unit)
        assert sample_finished_unit.inventory_count == initial_count

    def test_invalid_reason_raises(self, test_db, sample_finished_unit):
        """Raises ValueError for invalid reason."""
        session = test_db()
        with pytest.raises(ValueError, match="Invalid reason"):
            fg_inv.adjust_inventory(
                "finished_unit",
                sample_finished_unit.id,
                5,
                "invalid_reason",
                session=session,
            )

    def test_adjustment_reason_requires_notes(self, test_db, sample_finished_unit):
        """Raises ValueError when reason is 'adjustment' but notes not provided."""
        session = test_db()
        with pytest.raises(ValueError, match="Notes are required"):
            fg_inv.adjust_inventory(
                "finished_unit",
                sample_finished_unit.id,
                5,
                "adjustment",
                session=session,
            )

    def test_adjustment_reason_with_notes_succeeds(self, test_db, sample_finished_unit):
        """Succeeds when reason is 'adjustment' with notes."""
        session = test_db()
        result = fg_inv.adjust_inventory(
            "finished_unit",
            sample_finished_unit.id,
            2,
            "adjustment",
            notes="Manual correction for count error",
            session=session,
        )
        assert result["success"] is True

    def test_works_with_finished_good(self, test_db, sample_finished_good):
        """Works for finished_good item type."""
        session = test_db()
        initial_count = sample_finished_good.inventory_count

        result = fg_inv.adjust_inventory(
            "finished_good",
            sample_finished_good.id,
            3,
            "assembly",
            notes="Test assembly",
            session=session,
        )

        assert result["item_type"] == "finished_good"
        session.refresh(sample_finished_good)
        assert sample_finished_good.inventory_count == initial_count + 3

    def test_item_not_found_raises(self, test_db):
        """Raises ValueError when item doesn't exist."""
        session = test_db()
        with pytest.raises(ValueError, match="not found"):
            fg_inv.adjust_inventory(
                "finished_unit", 99999, 5, "production", notes="Test", session=session
            )

    def test_all_valid_reasons(self, test_db, sample_finished_unit):
        """All valid reasons work correctly."""
        session = test_db()
        valid_reasons = ["production", "assembly", "consumption", "spoilage", "gift"]

        for reason in valid_reasons:
            result = fg_inv.adjust_inventory(
                "finished_unit",
                sample_finished_unit.id,
                1,
                reason,
                notes=f"Test {reason}",
                session=session,
            )
            assert result["success"] is True
            assert result["reason"] == reason

    def test_works_without_session(self, test_db, sample_finished_unit):
        """Works when session=None (creates own transaction)."""
        # Note: test_db fixture patches the global session factory
        result = fg_inv.adjust_inventory(
            "finished_unit",
            sample_finished_unit.id,
            1,
            "production",
            notes="Test without session",
        )
        assert result["success"] is True


# =============================================================================
# T027: Tests for get_low_stock_items() and get_total_inventory_value()
# =============================================================================


class TestGetLowStockItems:
    """Tests for get_low_stock_items()"""

    def test_default_threshold(self, test_db, sample_finished_unit):
        """Uses DEFAULT_LOW_STOCK_THRESHOLD when none provided."""
        session = test_db()
        # Set inventory below default threshold (5)
        sample_finished_unit.inventory_count = 3
        session.merge(sample_finished_unit)
        session.commit()

        result = fg_inv.get_low_stock_items(session=session)
        fu_ids = [r["id"] for r in result if r["item_type"] == "finished_unit"]
        assert sample_finished_unit.id in fu_ids

    def test_custom_threshold(self, test_db, sample_finished_unit):
        """Uses custom threshold when provided."""
        session = test_db()
        # sample_finished_unit has inventory_count=50
        # With threshold=60, it should be considered low stock
        result = fg_inv.get_low_stock_items(threshold=60, session=session)
        fu_ids = [r["id"] for r in result if r["item_type"] == "finished_unit"]
        assert sample_finished_unit.id in fu_ids

    def test_not_low_when_above_threshold(self, test_db, sample_finished_unit):
        """Items above threshold not included."""
        session = test_db()
        # sample_finished_unit has inventory_count=50
        # With default threshold=5, it should NOT be low stock
        result = fg_inv.get_low_stock_items(session=session)
        fu_ids = [r["id"] for r in result if r["item_type"] == "finished_unit"]
        assert sample_finished_unit.id not in fu_ids

    def test_filter_by_item_type(self, test_db, sample_finished_unit, sample_finished_good):
        """Filters by item type."""
        session = test_db()
        # Set both to low stock
        sample_finished_unit.inventory_count = 2
        sample_finished_good.inventory_count = 2
        session.merge(sample_finished_unit)
        session.merge(sample_finished_good)
        session.commit()

        result = fg_inv.get_low_stock_items(item_type="finished_unit", session=session)
        assert all(r["item_type"] == "finished_unit" for r in result)

    def test_ordered_by_count_ascending(self, test_db, sample_recipe):
        """Results ordered by inventory_count ascending."""
        session = test_db()

        # Create multiple finished units with different counts
        fu1 = FinishedUnit(
            display_name="Low Stock 1",
            slug="low-stock-1",
            recipe_id=sample_recipe.id,
            yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=12,
            inventory_count=1,
        )
        fu2 = FinishedUnit(
            display_name="Low Stock 2",
            slug="low-stock-2",
            recipe_id=sample_recipe.id,
            yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=12,
            inventory_count=3,
        )
        fu3 = FinishedUnit(
            display_name="Low Stock 3",
            slug="low-stock-3",
            recipe_id=sample_recipe.id,
            yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=12,
            inventory_count=2,
        )
        session.add_all([fu1, fu2, fu3])
        session.commit()

        result = fg_inv.get_low_stock_items(threshold=10, session=session)
        counts = [r["inventory_count"] for r in result]
        assert counts == sorted(counts)


class TestGetTotalInventoryValue:
    """Tests for get_total_inventory_value()"""

    def test_returns_all_fields(self, test_db, sample_finished_unit, sample_finished_good):
        """Returns dict with all required fields."""
        session = test_db()
        result = fg_inv.get_total_inventory_value(session=session)

        assert "finished_units_value" in result
        assert "finished_goods_value" in result
        assert "total_value" in result
        assert "finished_units_count" in result
        assert "finished_goods_count" in result
        assert "total_items_count" in result

    def test_values_are_decimal(self, test_db, sample_finished_unit):
        """Value fields are Decimal type."""
        session = test_db()
        result = fg_inv.get_total_inventory_value(session=session)

        assert isinstance(result["finished_units_value"], Decimal)
        assert isinstance(result["finished_goods_value"], Decimal)
        assert isinstance(result["total_value"], Decimal)

    def test_counts_are_int(self, test_db, sample_finished_unit):
        """Count fields are int type."""
        session = test_db()
        result = fg_inv.get_total_inventory_value(session=session)

        assert isinstance(result["finished_units_count"], int)
        assert isinstance(result["finished_goods_count"], int)
        assert isinstance(result["total_items_count"], int)

    def test_total_is_sum(self, test_db, sample_finished_unit, sample_finished_good):
        """total_value equals sum of unit and good values."""
        session = test_db()
        result = fg_inv.get_total_inventory_value(session=session)

        expected_total = result["finished_units_value"] + result["finished_goods_value"]
        assert result["total_value"] == expected_total

    def test_total_items_is_sum(self, test_db, sample_finished_unit, sample_finished_good):
        """total_items_count equals sum of unit and good counts."""
        session = test_db()
        result = fg_inv.get_total_inventory_value(session=session)

        expected_count = result["finished_units_count"] + result["finished_goods_count"]
        assert result["total_items_count"] == expected_count

    def test_works_without_session(self, test_db, sample_finished_unit):
        """Works when session=None (creates own transaction)."""
        result = fg_inv.get_total_inventory_value()
        assert isinstance(result, dict)
        assert "total_value" in result
