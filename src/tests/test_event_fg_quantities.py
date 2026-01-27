"""
Tests for F071 event FG quantity methods in event_service.

Tests cover:
- get_event_fg_quantities
- set_event_fg_quantities
- remove_event_fg
"""

import pytest
from datetime import date

from src.services import event_service
from src.services.event_service import (
    get_event_fg_quantities,
    set_event_fg_quantities,
    remove_event_fg,
    set_event_recipes,
    get_available_finished_goods,
)
from src.services.exceptions import ValidationError
from src.models.event import Event
from src.models.event_finished_good import EventFinishedGood
from src.models.finished_good import FinishedGood
from src.models.finished_unit import FinishedUnit
from src.models.composition import Composition
from src.models.recipe import Recipe


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def planning_event(test_db):
    """Create a test event for quantity tests."""
    event = Event(
        name="Test Quantity Event",
        event_date=date(2026, 12, 25),
        year=2026,
    )
    test_db.add(event)
    test_db.flush()
    return event


@pytest.fixture
def test_recipe(test_db):
    """Create a test recipe."""
    recipe = Recipe(name="Test Recipe", category="Test")
    test_db.add(recipe)
    test_db.flush()
    return recipe


@pytest.fixture
def test_finished_unit(test_db, test_recipe):
    """Create a FinishedUnit linked to a recipe."""
    fu = FinishedUnit(
        slug=f"test-fu-qty-{test_recipe.id}",
        display_name="Test Finished Unit",
        recipe_id=test_recipe.id,
    )
    test_db.add(fu)
    test_db.flush()
    return fu


@pytest.fixture
def test_finished_good(test_db, test_finished_unit):
    """Create a FinishedGood with a FinishedUnit composition."""
    fg = FinishedGood(
        slug="test-fg-qty",
        display_name="Test Finished Good",
    )
    test_db.add(fg)
    test_db.flush()

    # Add composition linking FG to FU
    comp = Composition(
        assembly_id=fg.id,
        finished_unit_id=test_finished_unit.id,
        component_quantity=1.0,
    )
    test_db.add(comp)
    test_db.flush()

    # Store recipe id for convenience
    fg.expected_recipe_id = test_finished_unit.recipe_id
    return fg


@pytest.fixture
def available_fg(test_db, planning_event, test_finished_good, test_recipe):
    """Create a FG that is available for the event (recipe selected)."""
    # Select the recipe for the event to make FG available
    set_event_recipes(test_db, planning_event.id, [test_recipe.id])
    test_db.flush()
    return test_finished_good


@pytest.fixture
def second_recipe(test_db):
    """Create a second test recipe."""
    recipe = Recipe(name="Second Recipe", category="Test")
    test_db.add(recipe)
    test_db.flush()
    return recipe


@pytest.fixture
def second_finished_good(test_db, second_recipe):
    """Create a second FG with its own recipe."""
    fu = FinishedUnit(
        slug=f"test-fu-qty-2-{second_recipe.id}",
        display_name="Second Finished Unit",
        recipe_id=second_recipe.id,
    )
    test_db.add(fu)
    test_db.flush()

    fg = FinishedGood(
        slug="test-fg-qty-2",
        display_name="Second Finished Good",
    )
    test_db.add(fg)
    test_db.flush()

    comp = Composition(
        assembly_id=fg.id,
        finished_unit_id=fu.id,
        component_quantity=1.0,
    )
    test_db.add(comp)
    test_db.flush()

    fg.expected_recipe_id = second_recipe.id
    return fg


# ============================================================================
# Tests: get_event_fg_quantities
# ============================================================================


class TestGetEventFgQuantities:
    """Tests for get_event_fg_quantities method."""

    def test_returns_empty_list_for_event_without_fgs(self, test_db, planning_event):
        """Event with no FG quantities returns empty list."""
        result = get_event_fg_quantities(test_db, planning_event.id)
        assert result == []

    def test_returns_fg_quantity_tuples(self, test_db, planning_event, available_fg):
        """Returns (FinishedGood, quantity) tuples for event with FGs."""
        # Setup: Add FG to event with quantity
        efg = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=available_fg.id,
            quantity=24,
        )
        test_db.add(efg)
        test_db.flush()

        result = get_event_fg_quantities(test_db, planning_event.id)

        assert len(result) == 1
        fg, qty = result[0]
        assert fg.id == available_fg.id
        assert qty == 24

    def test_returns_multiple_fgs_with_quantities(
        self, test_db, planning_event, available_fg, second_finished_good, second_recipe
    ):
        """Returns all FGs with their quantities for an event."""
        # Make second FG available
        set_event_recipes(
            test_db, planning_event.id, [available_fg.expected_recipe_id, second_recipe.id]
        )

        # Add both FGs with quantities
        test_db.add(
            EventFinishedGood(
                event_id=planning_event.id,
                finished_good_id=available_fg.id,
                quantity=12,
            )
        )
        test_db.add(
            EventFinishedGood(
                event_id=planning_event.id,
                finished_good_id=second_finished_good.id,
                quantity=36,
            )
        )
        test_db.flush()

        result = get_event_fg_quantities(test_db, planning_event.id)

        assert len(result) == 2
        # Create dict for easier assertion
        result_dict = {fg.id: qty for fg, qty in result}
        assert result_dict[available_fg.id] == 12
        assert result_dict[second_finished_good.id] == 36

    def test_raises_validation_error_for_missing_event(self, test_db):
        """Non-existent event raises ValidationError."""
        with pytest.raises(ValidationError, match="Event not found"):
            get_event_fg_quantities(test_db, 99999)


# ============================================================================
# Tests: set_event_fg_quantities
# ============================================================================


class TestSetEventFgQuantities:
    """Tests for set_event_fg_quantities method."""

    def test_creates_new_records(self, test_db, planning_event, available_fg):
        """Creates EventFinishedGood records with quantities."""
        fg_quantities = [(available_fg.id, 24)]

        count = set_event_fg_quantities(test_db, planning_event.id, fg_quantities)

        assert count == 1
        efg = (
            test_db.query(EventFinishedGood)
            .filter_by(event_id=planning_event.id, finished_good_id=available_fg.id)
            .first()
        )
        assert efg is not None
        assert efg.quantity == 24

    def test_replaces_existing_quantities(self, test_db, planning_event, available_fg):
        """Existing quantities are replaced, not appended."""
        # Setup: existing record with quantity 10
        test_db.add(
            EventFinishedGood(
                event_id=planning_event.id,
                finished_good_id=available_fg.id,
                quantity=10,
            )
        )
        test_db.flush()

        # Replace with new quantity 25
        count = set_event_fg_quantities(
            test_db, planning_event.id, [(available_fg.id, 25)]
        )

        assert count == 1
        test_db.expire_all()
        efg = (
            test_db.query(EventFinishedGood)
            .filter_by(event_id=planning_event.id)
            .first()
        )
        assert efg.quantity == 25

    def test_empty_list_clears_all_fgs(self, test_db, planning_event, available_fg):
        """Empty list removes all FG associations."""
        # Setup: existing record
        test_db.add(
            EventFinishedGood(
                event_id=planning_event.id,
                finished_good_id=available_fg.id,
                quantity=10,
            )
        )
        test_db.flush()

        count = set_event_fg_quantities(test_db, planning_event.id, [])

        assert count == 0
        assert (
            test_db.query(EventFinishedGood)
            .filter_by(event_id=planning_event.id)
            .count()
            == 0
        )

    def test_filters_invalid_fg_ids(self, test_db, planning_event):
        """Invalid FG IDs (not available) are filtered out."""
        # FG ID 99999 doesn't exist
        count = set_event_fg_quantities(test_db, planning_event.id, [(99999, 10)])
        assert count == 0

    def test_filters_zero_quantities(self, test_db, planning_event, available_fg):
        """Quantities <= 0 are filtered out."""
        count = set_event_fg_quantities(
            test_db, planning_event.id, [(available_fg.id, 0)]
        )
        assert count == 0

    def test_filters_negative_quantities(self, test_db, planning_event, available_fg):
        """Negative quantities are filtered out."""
        count = set_event_fg_quantities(
            test_db, planning_event.id, [(available_fg.id, -5)]
        )
        assert count == 0

    def test_creates_multiple_records(
        self, test_db, planning_event, available_fg, second_finished_good, second_recipe
    ):
        """Creates multiple EventFinishedGood records."""
        # Make second FG available
        set_event_recipes(
            test_db, planning_event.id, [available_fg.expected_recipe_id, second_recipe.id]
        )
        test_db.flush()

        fg_quantities = [
            (available_fg.id, 12),
            (second_finished_good.id, 48),
        ]

        count = set_event_fg_quantities(test_db, planning_event.id, fg_quantities)

        assert count == 2
        records = (
            test_db.query(EventFinishedGood)
            .filter_by(event_id=planning_event.id)
            .all()
        )
        assert len(records) == 2

    def test_raises_validation_error_for_missing_event(self, test_db):
        """Non-existent event raises ValidationError."""
        with pytest.raises(ValidationError, match="Event not found"):
            set_event_fg_quantities(test_db, 99999, [])


# ============================================================================
# Tests: remove_event_fg
# ============================================================================


class TestRemoveEventFg:
    """Tests for remove_event_fg method."""

    def test_removes_existing_record(self, test_db, planning_event, available_fg):
        """Returns True and removes record when it exists."""
        # Setup: create record to remove
        test_db.add(
            EventFinishedGood(
                event_id=planning_event.id,
                finished_good_id=available_fg.id,
                quantity=10,
            )
        )
        test_db.flush()

        result = remove_event_fg(test_db, planning_event.id, available_fg.id)

        assert result is True
        assert (
            test_db.query(EventFinishedGood)
            .filter_by(event_id=planning_event.id, finished_good_id=available_fg.id)
            .first()
            is None
        )

    def test_returns_false_for_missing_record(self, test_db, planning_event):
        """Returns False when record doesn't exist."""
        result = remove_event_fg(test_db, planning_event.id, 99999)
        assert result is False

    def test_only_removes_specified_fg(
        self, test_db, planning_event, available_fg, second_finished_good, second_recipe
    ):
        """Removing one FG doesn't affect other FGs for the event."""
        # Make second FG available
        set_event_recipes(
            test_db, planning_event.id, [available_fg.expected_recipe_id, second_recipe.id]
        )

        # Add both FGs
        test_db.add(
            EventFinishedGood(
                event_id=planning_event.id,
                finished_good_id=available_fg.id,
                quantity=10,
            )
        )
        test_db.add(
            EventFinishedGood(
                event_id=planning_event.id,
                finished_good_id=second_finished_good.id,
                quantity=20,
            )
        )
        test_db.flush()

        # Remove only first FG
        result = remove_event_fg(test_db, planning_event.id, available_fg.id)

        assert result is True
        # First FG should be removed
        assert (
            test_db.query(EventFinishedGood)
            .filter_by(event_id=planning_event.id, finished_good_id=available_fg.id)
            .first()
            is None
        )
        # Second FG should still exist
        second_efg = (
            test_db.query(EventFinishedGood)
            .filter_by(event_id=planning_event.id, finished_good_id=second_finished_good.id)
            .first()
        )
        assert second_efg is not None
        assert second_efg.quantity == 20
