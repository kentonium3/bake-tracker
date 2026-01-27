"""
Unit tests for shopping list service (Feature 039).

Tests cover:
- calculate_purchase_gap() with various inputs
- get_shopping_list() wrapper functionality
- get_items_to_buy() filtering
- get_shopping_summary() statistics
- mark_shopping_complete() / unmark_shopping_complete() status tracking
- is_shopping_complete() status checking

Per WP03 specification:
- SC-004: Users can identify all items to purchase in a single view
- SC-008: Buy = max(0, Need - Have) with 100% accuracy
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest

from src.services.planning import (
    calculate_purchase_gap,
    get_shopping_list,
    get_items_to_buy,
    get_shopping_summary,
    mark_shopping_complete,
    unmark_shopping_complete,
    is_shopping_complete,
    ShoppingListItem,
)
from src.models import ProductionPlanSnapshot, Event
from src.utils.datetime_utils import utc_now


class TestCalculatePurchaseGap:
    """Tests for calculate_purchase_gap() function."""

    def test_need_more_than_have(self):
        """Test: need 10, have 5 = buy 5."""
        result = calculate_purchase_gap(Decimal("10"), Decimal("5"))
        assert result == Decimal("5")

    def test_need_equals_have(self):
        """Test: need 5, have 5 = buy 0."""
        result = calculate_purchase_gap(Decimal("5"), Decimal("5"))
        assert result == Decimal("0")

    def test_have_more_than_need(self):
        """Test: need 5, have 10 = buy 0 (never negative)."""
        result = calculate_purchase_gap(Decimal("5"), Decimal("10"))
        assert result == Decimal("0")

    def test_zero_needed(self):
        """Test: need 0, have 5 = buy 0."""
        result = calculate_purchase_gap(Decimal("0"), Decimal("5"))
        assert result == Decimal("0")

    def test_zero_in_stock(self):
        """Test: need 10, have 0 = buy 10."""
        result = calculate_purchase_gap(Decimal("10"), Decimal("0"))
        assert result == Decimal("10")

    def test_both_zero(self):
        """Test: need 0, have 0 = buy 0."""
        result = calculate_purchase_gap(Decimal("0"), Decimal("0"))
        assert result == Decimal("0")

    def test_decimal_precision(self):
        """Test decimal precision is maintained."""
        result = calculate_purchase_gap(Decimal("10.5"), Decimal("3.25"))
        assert result == Decimal("7.25")

    def test_never_returns_negative(self):
        """Property test: result is always >= 0."""
        test_cases = [
            (Decimal("0"), Decimal("100")),
            (Decimal("1"), Decimal("1000")),
            (Decimal("0.001"), Decimal("999.999")),
        ]
        for needed, in_stock in test_cases:
            result = calculate_purchase_gap(needed, in_stock)
            assert result >= Decimal("0"), f"Got negative for needed={needed}, in_stock={in_stock}"


class TestShoppingListItem:
    """Tests for ShoppingListItem dataclass."""

    def test_dataclass_fields(self):
        """Test that ShoppingListItem has all required fields."""
        item = ShoppingListItem(
            ingredient_id=1,
            ingredient_slug="flour",
            ingredient_name="All-Purpose Flour",
            needed=Decimal("10.5"),
            in_stock=Decimal("3.0"),
            to_buy=Decimal("7.5"),
            unit="cups",
            is_sufficient=False,
        )

        assert item.ingredient_id == 1
        assert item.ingredient_slug == "flour"
        assert item.ingredient_name == "All-Purpose Flour"
        assert item.needed == Decimal("10.5")
        assert item.in_stock == Decimal("3.0")
        assert item.to_buy == Decimal("7.5")
        assert item.unit == "cups"
        assert item.is_sufficient is False

    def test_sufficient_item(self):
        """Test item with sufficient stock."""
        item = ShoppingListItem(
            ingredient_id=2,
            ingredient_slug="sugar",
            ingredient_name="Granulated Sugar",
            needed=Decimal("5.0"),
            in_stock=Decimal("10.0"),
            to_buy=Decimal("0"),
            unit="cups",
            is_sufficient=True,
        )

        assert item.is_sufficient is True
        assert item.to_buy == Decimal("0")

    def test_dataclass_equality(self):
        """Test dataclass equality comparison."""
        item1 = ShoppingListItem(
            1, "flour", "Flour", Decimal("10"), Decimal("5"), Decimal("5"), "cups", False
        )
        item2 = ShoppingListItem(
            1, "flour", "Flour", Decimal("10"), Decimal("5"), Decimal("5"), "cups", False
        )
        assert item1 == item2


class TestGetShoppingList:
    """Tests for get_shopping_list() wrapper function."""

    @patch("src.services.planning.shopping_list.event_service")
    def test_returns_shopping_list_items(self, mock_event_service, test_db):
        """Test that get_shopping_list returns ShoppingListItem DTOs."""
        session = test_db()

        mock_event_service.get_shopping_list.return_value = {
            "items": [
                {
                    "ingredient_id": 1,
                    "ingredient_slug": "flour",
                    "ingredient_name": "All-Purpose Flour",
                    "quantity_needed": 10.0,
                    "quantity_on_hand": 5.0,
                    "unit": "cups",
                },
                {
                    "ingredient_id": 2,
                    "ingredient_slug": "sugar",
                    "ingredient_name": "Sugar",
                    "quantity_needed": 3.0,
                    "quantity_on_hand": 10.0,
                    "unit": "cups",
                },
            ]
        }

        result = get_shopping_list(event_id=1, session=session)

        assert len(result) == 2
        assert all(isinstance(item, ShoppingListItem) for item in result)

        # Check flour item (needs purchase)
        flour = next(i for i in result if i.ingredient_slug == "flour")
        assert flour.needed == Decimal("10")
        assert flour.in_stock == Decimal("5")
        assert flour.to_buy == Decimal("5")
        assert flour.is_sufficient is False

        # Check sugar item (sufficient)
        sugar = next(i for i in result if i.ingredient_slug == "sugar")
        assert sugar.needed == Decimal("3")
        assert sugar.in_stock == Decimal("10")
        assert sugar.to_buy == Decimal("0")
        assert sugar.is_sufficient is True

    @patch("src.services.planning.shopping_list.event_service")
    def test_filters_sufficient_items(self, mock_event_service, test_db):
        """Test that include_sufficient=False filters out sufficient items."""
        session = test_db()

        mock_event_service.get_shopping_list.return_value = {
            "items": [
                {
                    "ingredient_id": 1,
                    "ingredient_slug": "flour",
                    "ingredient_name": "Flour",
                    "quantity_needed": 10.0,
                    "quantity_on_hand": 5.0,
                    "unit": "cups",
                },
                {
                    "ingredient_id": 2,
                    "ingredient_slug": "sugar",
                    "ingredient_name": "Sugar",
                    "quantity_needed": 3.0,
                    "quantity_on_hand": 10.0,
                    "unit": "cups",
                },
            ]
        }

        result = get_shopping_list(event_id=1, include_sufficient=False, session=session)

        assert len(result) == 1
        assert result[0].ingredient_slug == "flour"
        assert result[0].is_sufficient is False

    @patch("src.services.planning.shopping_list.event_service")
    def test_empty_shopping_list(self, mock_event_service, test_db):
        """Test handling of empty shopping list."""
        session = test_db()

        mock_event_service.get_shopping_list.return_value = {"items": []}

        result = get_shopping_list(event_id=1, session=session)

        assert result == []


class TestGetItemsToBuy:
    """Tests for get_items_to_buy() convenience function."""

    @patch("src.services.planning.shopping_list.event_service")
    def test_returns_only_insufficient_items(self, mock_event_service, test_db):
        """Test that get_items_to_buy returns only items needing purchase."""
        session = test_db()

        mock_event_service.get_shopping_list.return_value = {
            "items": [
                {
                    "ingredient_id": 1,
                    "ingredient_slug": "flour",
                    "ingredient_name": "Flour",
                    "quantity_needed": 10.0,
                    "quantity_on_hand": 5.0,
                    "unit": "cups",
                },
                {
                    "ingredient_id": 2,
                    "ingredient_slug": "sugar",
                    "ingredient_name": "Sugar",
                    "quantity_needed": 3.0,
                    "quantity_on_hand": 10.0,
                    "unit": "cups",
                },
            ]
        }

        result = get_items_to_buy(event_id=1, session=session)

        assert len(result) == 1
        assert result[0].ingredient_slug == "flour"


class TestGetShoppingSummary:
    """Tests for get_shopping_summary() function."""

    @patch("src.services.planning.shopping_list.event_service")
    def test_returns_correct_summary(self, mock_event_service, test_db):
        """Test that summary statistics are correct."""
        session = test_db()

        mock_event_service.get_shopping_list.return_value = {
            "items": [
                {
                    "ingredient_id": 1,
                    "ingredient_slug": "flour",
                    "ingredient_name": "Flour",
                    "quantity_needed": 10.0,
                    "quantity_on_hand": 5.0,
                    "unit": "cups",
                },
                {
                    "ingredient_id": 2,
                    "ingredient_slug": "sugar",
                    "ingredient_name": "Sugar",
                    "quantity_needed": 3.0,
                    "quantity_on_hand": 10.0,
                    "unit": "cups",
                },
                {
                    "ingredient_id": 3,
                    "ingredient_slug": "eggs",
                    "ingredient_name": "Eggs",
                    "quantity_needed": 6.0,
                    "quantity_on_hand": 6.0,
                    "unit": "count",
                },
            ]
        }

        result = get_shopping_summary(event_id=1, session=session)

        assert result["total_items"] == 3
        assert result["items_sufficient"] == 2  # sugar and eggs
        assert result["items_to_buy"] == 1  # flour
        assert result["all_sufficient"] is False

    @patch("src.services.planning.shopping_list.event_service")
    def test_all_sufficient_summary(self, mock_event_service, test_db):
        """Test summary when all items have sufficient stock."""
        session = test_db()

        mock_event_service.get_shopping_list.return_value = {
            "items": [
                {
                    "ingredient_id": 1,
                    "ingredient_slug": "flour",
                    "ingredient_name": "Flour",
                    "quantity_needed": 5.0,
                    "quantity_on_hand": 10.0,
                    "unit": "cups",
                },
            ]
        }

        result = get_shopping_summary(event_id=1, session=session)

        assert result["all_sufficient"] is True
        assert result["items_to_buy"] == 0

    @patch("src.services.planning.shopping_list.event_service")
    def test_empty_list_summary(self, mock_event_service, test_db):
        """Test summary for empty shopping list."""
        session = test_db()

        mock_event_service.get_shopping_list.return_value = {"items": []}

        result = get_shopping_summary(event_id=1, session=session)

        assert result["total_items"] == 0
        assert result["items_sufficient"] == 0
        assert result["items_to_buy"] == 0
        assert result["all_sufficient"] is True


class TestMarkShoppingComplete:
    """Tests for mark_shopping_complete() function."""

    @pytest.fixture
    def event_with_snapshot(self, test_db):
        """Create an event with a ProductionPlanSnapshot."""
        session = test_db()
        now = utc_now()

        event = Event(
            name="Holiday Baking 2024",
            event_date=date(2024, 12, 25),
            year=2024,
        )
        session.add(event)
        session.flush()

        snapshot = ProductionPlanSnapshot(
            event_id=event.id,
            calculated_at=now,
            shopping_complete=False,
            shopping_completed_at=None,
        )
        session.add(snapshot)
        session.commit()

        return {"event_id": event.id, "snapshot_id": snapshot.id}

    def test_marks_shopping_complete(self, test_db, event_with_snapshot):
        """Test that mark_shopping_complete sets flag and timestamp."""
        session = test_db()

        result = mark_shopping_complete(event_with_snapshot["event_id"], session=session)

        assert result is True

        # Verify the snapshot was updated
        snapshot = session.get(ProductionPlanSnapshot, event_with_snapshot["snapshot_id"])
        assert snapshot.shopping_complete is True
        assert snapshot.shopping_completed_at is not None

    def test_returns_false_for_nonexistent_event(self, test_db):
        """Test that mark_shopping_complete returns False for missing event."""
        session = test_db()

        result = mark_shopping_complete(99999, session=session)

        assert result is False


class TestUnmarkShoppingComplete:
    """Tests for unmark_shopping_complete() function."""

    @pytest.fixture
    def event_with_complete_snapshot(self, test_db):
        """Create an event with a completed ProductionPlanSnapshot."""
        session = test_db()
        now = utc_now()

        event = Event(
            name="Holiday Baking 2024",
            event_date=date(2024, 12, 25),
            year=2024,
        )
        session.add(event)
        session.flush()

        snapshot = ProductionPlanSnapshot(
            event_id=event.id,
            calculated_at=now,
            shopping_complete=True,
            shopping_completed_at=now,
        )
        session.add(snapshot)
        session.commit()

        return {"event_id": event.id, "snapshot_id": snapshot.id}

    def test_unmarks_shopping_complete(self, test_db, event_with_complete_snapshot):
        """Test that unmark_shopping_complete resets flag and timestamp."""
        session = test_db()

        result = unmark_shopping_complete(event_with_complete_snapshot["event_id"], session=session)

        assert result is True

        # Verify the snapshot was updated
        snapshot = session.get(ProductionPlanSnapshot, event_with_complete_snapshot["snapshot_id"])
        assert snapshot.shopping_complete is False
        assert snapshot.shopping_completed_at is None

    def test_returns_false_for_nonexistent_event(self, test_db):
        """Test that unmark_shopping_complete returns False for missing event."""
        session = test_db()

        result = unmark_shopping_complete(99999, session=session)

        assert result is False


class TestIsShoppingComplete:
    """Tests for is_shopping_complete() function."""

    @pytest.fixture
    def event_with_incomplete_snapshot(self, test_db):
        """Create an event with incomplete shopping."""
        session = test_db()
        now = utc_now()

        event = Event(
            name="Holiday Baking 2024",
            event_date=date(2024, 12, 25),
            year=2024,
        )
        session.add(event)
        session.flush()

        snapshot = ProductionPlanSnapshot(
            event_id=event.id,
            calculated_at=now,
            shopping_complete=False,
        )
        session.add(snapshot)
        session.commit()

        return {"event_id": event.id}

    @pytest.fixture
    def event_with_complete_snapshot(self, test_db):
        """Create an event with complete shopping."""
        session = test_db()
        now = utc_now()

        event = Event(
            name="Holiday Baking 2024 Complete",
            event_date=date(2024, 12, 25),
            year=2024,
        )
        session.add(event)
        session.flush()

        snapshot = ProductionPlanSnapshot(
            event_id=event.id,
            calculated_at=now,
            shopping_complete=True,
            shopping_completed_at=now,
        )
        session.add(snapshot)
        session.commit()

        return {"event_id": event.id}

    def test_returns_false_for_incomplete(self, test_db, event_with_incomplete_snapshot):
        """Test is_shopping_complete returns False when not complete."""
        session = test_db()

        result = is_shopping_complete(event_with_incomplete_snapshot["event_id"], session=session)

        assert result is False

    def test_returns_true_for_complete(self, test_db, event_with_complete_snapshot):
        """Test is_shopping_complete returns True when complete."""
        session = test_db()

        result = is_shopping_complete(event_with_complete_snapshot["event_id"], session=session)

        assert result is True

    def test_returns_false_for_nonexistent_event(self, test_db):
        """Test is_shopping_complete returns False for missing event."""
        session = test_db()

        result = is_shopping_complete(99999, session=session)

        assert result is False
