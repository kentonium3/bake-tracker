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

        # Use production_aware=False to trigger legacy behavior using event_service
        result = get_shopping_list(event_id=1, production_aware=False, session=session)

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

        # Use production_aware=False to trigger legacy behavior using event_service
        result = get_shopping_list(event_id=1, include_sufficient=False, production_aware=False, session=session)

        assert len(result) == 1
        assert result[0].ingredient_slug == "flour"
        assert result[0].is_sufficient is False

    @patch("src.services.planning.shopping_list.event_service")
    def test_empty_shopping_list(self, mock_event_service, test_db):
        """Test handling of empty shopping list."""
        session = test_db()

        mock_event_service.get_shopping_list.return_value = {"items": []}

        # Use production_aware=False to trigger legacy behavior using event_service
        result = get_shopping_list(event_id=1, production_aware=False, session=session)

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

        # Use production_aware=False to trigger legacy behavior using event_service
        result = get_items_to_buy(event_id=1, production_aware=False, session=session)

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

        # Use production_aware=False to trigger legacy behavior using event_service
        result = get_shopping_summary(event_id=1, production_aware=False, session=session)

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

        # Use production_aware=False to trigger legacy behavior using event_service
        result = get_shopping_summary(event_id=1, production_aware=False, session=session)

        assert result["all_sufficient"] is True
        assert result["items_to_buy"] == 0

    @patch("src.services.planning.shopping_list.event_service")
    def test_empty_list_summary(self, mock_event_service, test_db):
        """Test summary for empty shopping list."""
        session = test_db()

        mock_event_service.get_shopping_list.return_value = {"items": []}

        # Use production_aware=False to trigger legacy behavior using event_service
        result = get_shopping_summary(event_id=1, production_aware=False, session=session)

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


# =============================================================================
# Production-Aware Shopping List Tests (F079 WP03)
# =============================================================================


class TestProductionAwareShoppingList:
    """Tests for production-aware shopping list calculation (F079 WP03)."""

    @patch("src.services.planning.shopping_list.get_remaining_production_needs")
    @patch("src.services.planning.shopping_list.recipe_service")
    @patch("src.services.planning.shopping_list._get_inventory_for_ingredient")
    def test_partial_production_shows_remaining_needs(
        self, mock_get_inventory, mock_recipe_service, mock_remaining_needs, test_db
    ):
        """
        Given: 10 batches target (100g flour each), 7 completed, 200g flour in stock
        When: get_shopping_list(production_aware=True)
        Then: Shows 100g flour to buy (3 batches * 100g = 300g needed, 200g in stock)
        """
        session = test_db()

        # Create event and target
        from src.models import Event, EventProductionTarget, Recipe
        from datetime import date

        event = Event(name="Test Event", event_date=date(2024, 12, 25), year=2024)
        session.add(event)
        session.flush()

        recipe = Recipe(name="Test Recipe", category="Test")
        session.add(recipe)
        session.flush()

        target = EventProductionTarget(
            event_id=event.id,
            recipe_id=recipe.id,
            target_batches=10,
        )
        session.add(target)
        session.commit()

        # Mock remaining batches: 3 remaining (10 - 7 completed)
        mock_remaining_needs.return_value = {recipe.id: 3}

        # Mock recipe ingredients
        mock_recipe_service.get_aggregated_ingredients.return_value = [
            {
                "ingredient_id": 1,
                "ingredient_slug": "flour",
                "ingredient_name": "All-Purpose Flour",
                "total_quantity": 100,  # 100g per batch
                "unit": "g",
            }
        ]

        # Mock inventory: 200g in stock
        mock_get_inventory.return_value = Decimal("200")

        # Get shopping list
        items = get_shopping_list(
            event.id,
            production_aware=True,
            session=session,
        )

        flour_item = next((i for i in items if "flour" in i.ingredient_slug.lower()), None)
        assert flour_item is not None
        assert flour_item.needed == Decimal("300")  # 3 remaining * 100g
        assert flour_item.in_stock == Decimal("200")
        assert flour_item.to_buy == Decimal("100")

    @patch("src.services.planning.shopping_list.get_remaining_production_needs")
    def test_all_production_complete_returns_empty_list(
        self, mock_remaining_needs, test_db
    ):
        """
        Given: All production batches completed
        When: get_shopping_list(production_aware=True)
        Then: Returns empty list (nothing needed)
        """
        session = test_db()

        # Create event and target
        from src.models import Event, EventProductionTarget, Recipe
        from datetime import date

        event = Event(name="Complete Event", event_date=date(2024, 12, 25), year=2024)
        session.add(event)
        session.flush()

        recipe = Recipe(name="Complete Recipe", category="Test")
        session.add(recipe)
        session.flush()

        target = EventProductionTarget(
            event_id=event.id,
            recipe_id=recipe.id,
            target_batches=5,
        )
        session.add(target)
        session.commit()

        # Mock remaining batches: 0 remaining (all complete)
        mock_remaining_needs.return_value = {recipe.id: 0}

        # Get shopping list
        items = get_shopping_list(
            event.id,
            production_aware=True,
            session=session,
        )

        assert items == []

    @patch("src.services.planning.shopping_list.get_remaining_production_needs")
    @patch("src.services.planning.shopping_list.recipe_service")
    @patch("src.services.planning.shopping_list._get_inventory_for_ingredient")
    def test_sufficient_inventory_for_remaining_is_sufficient(
        self, mock_get_inventory, mock_recipe_service, mock_remaining_needs, test_db
    ):
        """
        Given: Remaining needs 300g flour, 500g in stock
        When: get_shopping_list(production_aware=True)
        Then: Flour item shows is_sufficient=True, to_buy=0
        """
        session = test_db()

        # Create event and target
        from src.models import Event, EventProductionTarget, Recipe
        from datetime import date

        event = Event(name="Sufficient Event", event_date=date(2024, 12, 25), year=2024)
        session.add(event)
        session.flush()

        recipe = Recipe(name="Sufficient Recipe", category="Test")
        session.add(recipe)
        session.flush()

        target = EventProductionTarget(
            event_id=event.id,
            recipe_id=recipe.id,
            target_batches=10,
        )
        session.add(target)
        session.commit()

        # Mock remaining batches: 3 remaining
        mock_remaining_needs.return_value = {recipe.id: 3}

        # Mock recipe ingredients: 100g flour per batch
        mock_recipe_service.get_aggregated_ingredients.return_value = [
            {
                "ingredient_id": 1,
                "ingredient_slug": "flour",
                "ingredient_name": "All-Purpose Flour",
                "total_quantity": 100,
                "unit": "g",
            }
        ]

        # Mock inventory: 500g in stock (more than needed)
        mock_get_inventory.return_value = Decimal("500")

        # Get shopping list
        items = get_shopping_list(
            event.id,
            production_aware=True,
            session=session,
        )

        flour_item = next((i for i in items if "flour" in i.ingredient_slug.lower()), None)
        assert flour_item is not None
        assert flour_item.is_sufficient is True
        assert flour_item.to_buy == Decimal("0")

    @patch("src.services.planning.shopping_list.event_service")
    def test_legacy_mode_shows_total_needs(self, mock_event_service, test_db):
        """
        Given: 10 batches target (100g flour each), 7 completed
        When: get_shopping_list(production_aware=False)
        Then: Shows needs for all 10 batches (1000g flour)
        """
        session = test_db()

        # Mock event_service response (legacy behavior)
        mock_event_service.get_shopping_list.return_value = {
            "items": [
                {
                    "ingredient_id": 1,
                    "ingredient_slug": "flour",
                    "ingredient_name": "All-Purpose Flour",
                    "quantity_needed": 1000.0,  # Total for all 10 batches
                    "quantity_on_hand": 200.0,
                    "unit": "g",
                },
            ]
        }

        items = get_shopping_list(
            event_id=1,
            production_aware=False,  # Legacy mode
            session=session,
        )

        flour_item = next((i for i in items if "flour" in i.ingredient_slug.lower()), None)
        assert flour_item is not None
        assert flour_item.needed == Decimal("1000")  # All 10 batches

    @patch("src.services.planning.shopping_list.get_remaining_production_needs")
    @patch("src.services.planning.shopping_list.recipe_service")
    @patch("src.services.planning.shopping_list._get_inventory_for_ingredient")
    def test_default_is_production_aware(
        self, mock_get_inventory, mock_recipe_service, mock_remaining_needs, test_db
    ):
        """Default behavior should be production_aware=True."""
        session = test_db()

        # Create event and target
        from src.models import Event, EventProductionTarget, Recipe
        from datetime import date

        event = Event(name="Default Event", event_date=date(2024, 12, 25), year=2024)
        session.add(event)
        session.flush()

        recipe = Recipe(name="Default Recipe", category="Test")
        session.add(recipe)
        session.flush()

        target = EventProductionTarget(
            event_id=event.id,
            recipe_id=recipe.id,
            target_batches=10,
        )
        session.add(target)
        session.commit()

        # Mock remaining batches
        mock_remaining_needs.return_value = {recipe.id: 3}

        # Mock recipe ingredients
        mock_recipe_service.get_aggregated_ingredients.return_value = [
            {
                "ingredient_id": 1,
                "ingredient_slug": "flour",
                "ingredient_name": "Flour",
                "total_quantity": 100,
                "unit": "g",
            }
        ]

        mock_get_inventory.return_value = Decimal("0")

        # Call without explicit production_aware parameter
        items_default = get_shopping_list(event.id, session=session)
        # Call with explicit production_aware=True
        items_explicit = get_shopping_list(
            event.id,
            production_aware=True,
            session=session,
        )

        # Both should return same result
        assert len(items_default) == len(items_explicit)
        if items_default:
            assert items_default[0].needed == items_explicit[0].needed


class TestGetItemsToBuyProductionAware:
    """Tests for get_items_to_buy with production_aware."""

    @patch("src.services.planning.shopping_list.get_remaining_production_needs")
    @patch("src.services.planning.shopping_list.recipe_service")
    @patch("src.services.planning.shopping_list._get_inventory_for_ingredient")
    def test_respects_production_aware_flag(
        self, mock_get_inventory, mock_recipe_service, mock_remaining_needs, test_db
    ):
        """get_items_to_buy should pass through production_aware parameter."""
        session = test_db()

        # Create event and target
        from src.models import Event, EventProductionTarget, Recipe
        from datetime import date

        event = Event(name="Buy Event", event_date=date(2024, 12, 25), year=2024)
        session.add(event)
        session.flush()

        recipe = Recipe(name="Buy Recipe", category="Test")
        session.add(recipe)
        session.flush()

        target = EventProductionTarget(
            event_id=event.id,
            recipe_id=recipe.id,
            target_batches=10,
        )
        session.add(target)
        session.commit()

        # Mock remaining batches
        mock_remaining_needs.return_value = {recipe.id: 3}

        # Mock recipe ingredients
        mock_recipe_service.get_aggregated_ingredients.return_value = [
            {
                "ingredient_id": 1,
                "ingredient_slug": "flour",
                "ingredient_name": "Flour",
                "total_quantity": 100,
                "unit": "g",
            }
        ]

        # Mock inventory: 0 (need to buy)
        mock_get_inventory.return_value = Decimal("0")

        from src.services.planning import get_items_to_buy

        items = get_items_to_buy(
            event.id,
            production_aware=True,
            session=session,
        )

        # Should only return items that need to be purchased
        assert all(item.to_buy > 0 for item in items)


class TestGetShoppingSummaryProductionAware:
    """Tests for get_shopping_summary with production_aware."""

    @patch("src.services.planning.shopping_list.get_remaining_production_needs")
    def test_all_complete_shows_empty_summary(self, mock_remaining_needs, test_db):
        """
        Given: All production complete
        When: get_shopping_summary(production_aware=True)
        Then: Shows 0 total items and all_sufficient=True
        """
        session = test_db()

        # Create event and target
        from src.models import Event, EventProductionTarget, Recipe
        from datetime import date

        event = Event(name="Summary Event", event_date=date(2024, 12, 25), year=2024)
        session.add(event)
        session.flush()

        recipe = Recipe(name="Summary Recipe", category="Test")
        session.add(recipe)
        session.flush()

        target = EventProductionTarget(
            event_id=event.id,
            recipe_id=recipe.id,
            target_batches=5,
        )
        session.add(target)
        session.commit()

        # All complete
        mock_remaining_needs.return_value = {recipe.id: 0}

        from src.services.planning import get_shopping_summary

        summary = get_shopping_summary(
            event.id,
            production_aware=True,
            session=session,
        )

        assert summary["total_items"] == 0
        assert summary["all_sufficient"] is True
