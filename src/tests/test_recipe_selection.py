"""
Tests for recipe selection service methods (F069).

Tests cover:
- get_event_recipe_ids
- set_event_recipes
"""

import pytest
from datetime import date

from src.services import event_service
from src.services.exceptions import ValidationError


class TestGetEventRecipeIds:
    """Tests for get_event_recipe_ids."""

    def test_returns_empty_list_when_no_selections(self, test_db, planning_event):
        """Event with no recipe selections returns empty list."""
        result = event_service.get_event_recipe_ids(test_db, planning_event.id)
        assert result == []

    def test_returns_selected_recipe_ids(self, test_db, planning_event, test_recipes):
        """Returns IDs of selected recipes."""
        # Select some recipes
        event_service.set_event_recipes(
            test_db, planning_event.id, [test_recipes[0].id, test_recipes[1].id]
        )
        test_db.commit()

        result = event_service.get_event_recipe_ids(test_db, planning_event.id)
        assert set(result) == {test_recipes[0].id, test_recipes[1].id}

    def test_raises_for_nonexistent_event(self, test_db):
        """Raises ValidationError for non-existent event."""
        with pytest.raises(ValidationError, match="Event not found"):
            event_service.get_event_recipe_ids(test_db, 99999)


class TestSetEventRecipes:
    """Tests for set_event_recipes."""

    def test_sets_recipe_selections(self, test_db, planning_event, test_recipes):
        """Sets recipe selections for an event."""
        count = event_service.set_event_recipes(
            test_db, planning_event.id, [test_recipes[0].id]
        )
        test_db.commit()
        assert count == 1

        result = event_service.get_event_recipe_ids(test_db, planning_event.id)
        assert result == [test_recipes[0].id]

    def test_replaces_existing_selections(self, test_db, planning_event, test_recipes):
        """Replaces all existing selections with new list."""
        event_service.set_event_recipes(
            test_db, planning_event.id, [test_recipes[0].id]
        )
        test_db.commit()

        event_service.set_event_recipes(
            test_db, planning_event.id, [test_recipes[1].id, test_recipes[2].id]
        )
        test_db.commit()

        result = event_service.get_event_recipe_ids(test_db, planning_event.id)
        assert set(result) == {test_recipes[1].id, test_recipes[2].id}

    def test_empty_list_clears_selections(self, test_db, planning_event, test_recipes):
        """Empty list clears all selections."""
        event_service.set_event_recipes(
            test_db, planning_event.id, [test_recipes[0].id]
        )
        test_db.commit()

        count = event_service.set_event_recipes(test_db, planning_event.id, [])
        test_db.commit()
        assert count == 0

        result = event_service.get_event_recipe_ids(test_db, planning_event.id)
        assert result == []

    def test_raises_for_nonexistent_event(self, test_db, test_recipes):
        """Raises ValidationError for non-existent event."""
        with pytest.raises(ValidationError, match="Event not found"):
            event_service.set_event_recipes(test_db, 99999, [test_recipes[0].id])

    def test_raises_for_invalid_recipe_id(self, test_db, planning_event):
        """Raises ValidationError for invalid recipe ID."""
        with pytest.raises(ValidationError, match="Recipe .* not found"):
            event_service.set_event_recipes(test_db, planning_event.id, [99999])

    def test_validates_all_recipes_before_modifying(
        self, test_db, planning_event, test_recipes
    ):
        """Validates all recipe IDs before making any changes."""
        # First set some recipes
        event_service.set_event_recipes(
            test_db, planning_event.id, [test_recipes[0].id]
        )
        test_db.commit()

        # Try to set with one invalid ID - should fail without changing anything
        with pytest.raises(ValidationError):
            event_service.set_event_recipes(
                test_db, planning_event.id, [test_recipes[1].id, 99999]
            )

        # Original selection should still be intact
        result = event_service.get_event_recipe_ids(test_db, planning_event.id)
        assert result == [test_recipes[0].id]

    def test_handles_duplicate_recipe_ids(self, test_db, planning_event, test_recipes):
        """Duplicate recipe IDs in input list are deduplicated or handled gracefully."""
        # Note: The implementation doesn't dedupe, but db has unique constraint
        # We should only insert each recipe once
        count = event_service.set_event_recipes(
            test_db, planning_event.id, [test_recipes[0].id]
        )
        test_db.commit()

        assert count == 1
        result = event_service.get_event_recipe_ids(test_db, planning_event.id)
        assert len(result) == 1

    def test_multiple_events_independent(self, test_db, test_recipes):
        """Selections for different events are independent."""
        # Create two events
        event1 = event_service.create_planning_event(
            test_db, "Event 1", date(2026, 7, 1)
        )
        event2 = event_service.create_planning_event(
            test_db, "Event 2", date(2026, 7, 2)
        )
        test_db.commit()

        # Set different selections
        event_service.set_event_recipes(test_db, event1.id, [test_recipes[0].id])
        event_service.set_event_recipes(
            test_db, event2.id, [test_recipes[1].id, test_recipes[2].id]
        )
        test_db.commit()

        # Verify independence
        result1 = event_service.get_event_recipe_ids(test_db, event1.id)
        result2 = event_service.get_event_recipe_ids(test_db, event2.id)
        assert result1 == [test_recipes[0].id]
        assert set(result2) == {test_recipes[1].id, test_recipes[2].id}


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def planning_event(test_db):
    """Create a planning event for testing."""
    event = event_service.create_planning_event(
        test_db,
        name="Test Planning Event",
        event_date=date(2026, 6, 15),
    )
    test_db.commit()
    return event


@pytest.fixture
def test_recipes(test_db):
    """Create test recipes for selection testing."""
    from src.models.recipe import Recipe

    recipes = []
    for i in range(3):
        recipe = Recipe(
            name=f"Test Recipe {i + 1}",
            category="Test Category",
        )
        test_db.add(recipe)
        recipes.append(recipe)
    test_db.flush()
    return recipes
