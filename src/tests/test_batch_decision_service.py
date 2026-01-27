"""Tests for batch decision CRUD service.

Feature 073: Batch Calculation User Decisions
Work Package: WP03 - Batch Decision CRUD Service
Subtask: T021 - Write tests

This test module verifies:
1. BatchDecisionInput dataclass
2. save_batch_decision() with validation and upsert
3. get_batch_decisions() for all decisions in an event
4. get_batch_decision() for a single decision
5. delete_batch_decisions() to clear all decisions for an event
6. is_shortfall_option() helper function
7. Session parameter pattern works correctly
"""

import pytest
from datetime import date

from src.models.batch_decision import BatchDecision
from src.models.event import Event
from src.models.finished_unit import FinishedUnit, YieldMode
from src.models.recipe import Recipe
from src.services.database import session_scope
from src.services.batch_decision_service import (
    BatchDecisionInput,
    save_batch_decision,
    get_batch_decisions,
    get_batch_decision,
    delete_batch_decisions,
    is_shortfall_option,
)
from src.services.exceptions import ValidationError


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def batch_decision_setup(test_db):
    """Set up an event with finished units for batch decision testing.

    Creates:
    - Event
    - Recipe
    - 2 FinishedUnits with different yield configurations

    Returns a setup object with IDs for use in tests.
    """
    session = test_db()

    # Create event
    event = Event(
        name="Batch Decision Test Event",
        event_date=date(2024, 12, 25),
        year=2024,
    )
    session.add(event)
    session.flush()

    # Create recipe
    recipe = Recipe(
        name="Test Cookie Recipe",
        category="Cookies",
    )
    session.add(recipe)
    session.flush()

    # Create first finished unit (24 cookies per batch)
    fu1 = FinishedUnit(
        recipe_id=recipe.id,
        display_name="Small Cookies",
        slug="small-cookies",
        yield_mode=YieldMode.DISCRETE_COUNT,
        items_per_batch=24,
        item_unit="cookies",
    )
    session.add(fu1)
    session.flush()

    # Create second finished unit (12 cookies per batch)
    fu2 = FinishedUnit(
        recipe_id=recipe.id,
        display_name="Large Cookies",
        slug="large-cookies",
        yield_mode=YieldMode.DISCRETE_COUNT,
        items_per_batch=12,
        item_unit="cookies",
    )
    session.add(fu2)
    session.commit()

    class SetupData:
        pass

    data = SetupData()
    data.event_id = event.id
    data.recipe_id = recipe.id
    data.fu1_id = fu1.id
    data.fu2_id = fu2.id
    data.session_factory = test_db

    return data


@pytest.fixture(scope="function")
def second_event(test_db, batch_decision_setup):
    """Create a second event for isolation testing."""
    session = test_db()

    event = Event(
        name="Second Test Event",
        event_date=date(2024, 12, 31),
        year=2024,
    )
    session.add(event)
    session.commit()

    return event.id


# =============================================================================
# Tests for BatchDecisionInput dataclass (T015)
# =============================================================================


class TestBatchDecisionInputDataclass:
    """Tests for BatchDecisionInput dataclass."""

    def test_create_basic_input(self):
        """Test creating BatchDecisionInput with required fields."""
        decision = BatchDecisionInput(
            finished_unit_id=1,
            batches=3,
        )
        assert decision.finished_unit_id == 1
        assert decision.batches == 3
        assert decision.is_shortfall is False
        assert decision.confirmed_shortfall is False

    def test_create_with_shortfall(self):
        """Test creating BatchDecisionInput with shortfall fields."""
        decision = BatchDecisionInput(
            finished_unit_id=1,
            batches=2,
            is_shortfall=True,
            confirmed_shortfall=True,
        )
        assert decision.is_shortfall is True
        assert decision.confirmed_shortfall is True

    def test_dataclass_equality(self):
        """Test BatchDecisionInput equality comparison."""
        d1 = BatchDecisionInput(finished_unit_id=1, batches=3)
        d2 = BatchDecisionInput(finished_unit_id=1, batches=3)
        d3 = BatchDecisionInput(finished_unit_id=1, batches=4)

        assert d1 == d2
        assert d1 != d3


# =============================================================================
# Tests for save_batch_decision() (T016)
# =============================================================================


class TestSaveBatchDecision:
    """Tests for save_batch_decision() function."""

    def test_save_new_decision(self, batch_decision_setup):
        """Test creating a new batch decision."""
        setup = batch_decision_setup
        decision_input = BatchDecisionInput(
            finished_unit_id=setup.fu1_id,
            batches=3,
        )

        result = save_batch_decision(setup.event_id, decision_input)

        assert result is not None
        assert result.event_id == setup.event_id
        assert result.finished_unit_id == setup.fu1_id
        assert result.batches == 3
        assert result.recipe_id == setup.recipe_id

    def test_save_decision_upsert_update(self, batch_decision_setup):
        """Test that save_batch_decision updates existing decision (upsert)."""
        setup = batch_decision_setup

        # Create initial decision
        decision1 = BatchDecisionInput(finished_unit_id=setup.fu1_id, batches=2)
        save_batch_decision(setup.event_id, decision1)

        # Update with new value
        decision2 = BatchDecisionInput(finished_unit_id=setup.fu1_id, batches=5)
        result = save_batch_decision(setup.event_id, decision2)

        assert result.batches == 5

        # Verify only one decision exists
        decisions = get_batch_decisions(setup.event_id)
        assert len(decisions) == 1
        assert decisions[0].batches == 5

    def test_save_decision_validates_event_exists(self, batch_decision_setup):
        """Test that save_batch_decision validates event exists."""
        setup = batch_decision_setup
        decision = BatchDecisionInput(finished_unit_id=setup.fu1_id, batches=3)

        with pytest.raises(ValidationError) as exc_info:
            save_batch_decision(event_id=99999, decision=decision)

        assert "Event with ID 99999 does not exist" in str(exc_info.value)

    def test_save_decision_validates_fu_exists(self, batch_decision_setup):
        """Test that save_batch_decision validates FinishedUnit exists."""
        setup = batch_decision_setup
        decision = BatchDecisionInput(finished_unit_id=99999, batches=3)

        with pytest.raises(ValidationError) as exc_info:
            save_batch_decision(event_id=setup.event_id, decision=decision)

        assert "FinishedUnit with ID 99999 does not exist" in str(exc_info.value)

    def test_save_decision_validates_batches_positive(self, batch_decision_setup):
        """Test that save_batch_decision validates batches > 0."""
        setup = batch_decision_setup

        # Test zero batches
        decision_zero = BatchDecisionInput(finished_unit_id=setup.fu1_id, batches=0)
        with pytest.raises(ValidationError) as exc_info:
            save_batch_decision(setup.event_id, decision_zero)
        assert "Batches must be a positive integer" in str(exc_info.value)

        # Test negative batches
        decision_neg = BatchDecisionInput(finished_unit_id=setup.fu1_id, batches=-1)
        with pytest.raises(ValidationError) as exc_info:
            save_batch_decision(setup.event_id, decision_neg)
        assert "Batches must be a positive integer" in str(exc_info.value)

    def test_save_decision_validates_shortfall_confirmation(self, batch_decision_setup):
        """Test that shortfall requires confirmation."""
        setup = batch_decision_setup
        decision = BatchDecisionInput(
            finished_unit_id=setup.fu1_id,
            batches=2,
            is_shortfall=True,
            confirmed_shortfall=False,  # Not confirmed!
        )

        with pytest.raises(ValidationError) as exc_info:
            save_batch_decision(setup.event_id, decision)

        assert "Shortfall must be confirmed" in str(exc_info.value)

    def test_save_decision_allows_confirmed_shortfall(self, batch_decision_setup):
        """Test that confirmed shortfall is allowed."""
        setup = batch_decision_setup
        decision = BatchDecisionInput(
            finished_unit_id=setup.fu1_id,
            batches=2,
            is_shortfall=True,
            confirmed_shortfall=True,
        )

        result = save_batch_decision(setup.event_id, decision)
        assert result.batches == 2

    def test_save_decision_with_session_param(self, batch_decision_setup):
        """Test save_batch_decision with explicit session parameter."""
        setup = batch_decision_setup

        with session_scope() as session:
            decision = BatchDecisionInput(finished_unit_id=setup.fu1_id, batches=4)
            result = save_batch_decision(setup.event_id, decision, session=session)

            assert result.batches == 4

            # Verify we can see the decision within the same session
            same_session_decision = get_batch_decision(
                setup.event_id, setup.fu1_id, session=session
            )
            assert same_session_decision is not None
            assert same_session_decision.batches == 4


# =============================================================================
# Tests for get_batch_decisions() (T017)
# =============================================================================


class TestGetBatchDecisions:
    """Tests for get_batch_decisions() function."""

    def test_get_empty_decisions(self, batch_decision_setup):
        """Test getting decisions when none exist."""
        setup = batch_decision_setup
        decisions = get_batch_decisions(setup.event_id)
        assert decisions == []

    def test_get_single_decision(self, batch_decision_setup):
        """Test getting decisions when one exists."""
        setup = batch_decision_setup
        decision = BatchDecisionInput(finished_unit_id=setup.fu1_id, batches=3)
        save_batch_decision(setup.event_id, decision)

        decisions = get_batch_decisions(setup.event_id)

        assert len(decisions) == 1
        assert decisions[0].batches == 3

    def test_get_multiple_decisions(self, batch_decision_setup):
        """Test getting multiple decisions for an event."""
        setup = batch_decision_setup

        # Save decisions for both FUs
        save_batch_decision(
            setup.event_id,
            BatchDecisionInput(finished_unit_id=setup.fu1_id, batches=3),
        )
        save_batch_decision(
            setup.event_id,
            BatchDecisionInput(finished_unit_id=setup.fu2_id, batches=5),
        )

        decisions = get_batch_decisions(setup.event_id)

        assert len(decisions) == 2
        # Ordered by finished_unit_id
        fu_ids = [d.finished_unit_id for d in decisions]
        assert fu_ids == sorted(fu_ids)

    def test_get_decisions_isolated_by_event(self, batch_decision_setup, second_event):
        """Test that decisions are isolated by event."""
        setup = batch_decision_setup

        # Save decision for first event
        save_batch_decision(
            setup.event_id,
            BatchDecisionInput(finished_unit_id=setup.fu1_id, batches=3),
        )

        # Save decision for second event
        save_batch_decision(
            second_event,
            BatchDecisionInput(finished_unit_id=setup.fu1_id, batches=10),
        )

        # Get decisions for first event
        decisions1 = get_batch_decisions(setup.event_id)
        assert len(decisions1) == 1
        assert decisions1[0].batches == 3

        # Get decisions for second event
        decisions2 = get_batch_decisions(second_event)
        assert len(decisions2) == 1
        assert decisions2[0].batches == 10

    def test_get_decisions_with_session_param(self, batch_decision_setup):
        """Test get_batch_decisions with explicit session parameter."""
        setup = batch_decision_setup

        with session_scope() as session:
            decision = BatchDecisionInput(finished_unit_id=setup.fu1_id, batches=7)
            save_batch_decision(setup.event_id, decision, session=session)

            # Get decisions using same session (should see uncommitted changes)
            decisions = get_batch_decisions(setup.event_id, session=session)
            assert len(decisions) == 1
            assert decisions[0].batches == 7


# =============================================================================
# Tests for get_batch_decision() (T018)
# =============================================================================


class TestGetBatchDecision:
    """Tests for get_batch_decision() function."""

    def test_get_nonexistent_decision(self, batch_decision_setup):
        """Test getting a decision that doesn't exist."""
        setup = batch_decision_setup
        result = get_batch_decision(setup.event_id, setup.fu1_id)
        assert result is None

    def test_get_existing_decision(self, batch_decision_setup):
        """Test getting an existing decision."""
        setup = batch_decision_setup
        decision = BatchDecisionInput(finished_unit_id=setup.fu1_id, batches=4)
        save_batch_decision(setup.event_id, decision)

        result = get_batch_decision(setup.event_id, setup.fu1_id)

        assert result is not None
        assert result.batches == 4
        assert result.event_id == setup.event_id
        assert result.finished_unit_id == setup.fu1_id

    def test_get_decision_correct_fu(self, batch_decision_setup):
        """Test that get_batch_decision returns correct FU's decision."""
        setup = batch_decision_setup

        # Save decisions for both FUs
        save_batch_decision(
            setup.event_id,
            BatchDecisionInput(finished_unit_id=setup.fu1_id, batches=3),
        )
        save_batch_decision(
            setup.event_id,
            BatchDecisionInput(finished_unit_id=setup.fu2_id, batches=8),
        )

        # Get decision for fu1
        result1 = get_batch_decision(setup.event_id, setup.fu1_id)
        assert result1.batches == 3

        # Get decision for fu2
        result2 = get_batch_decision(setup.event_id, setup.fu2_id)
        assert result2.batches == 8

    def test_get_decision_with_session_param(self, batch_decision_setup):
        """Test get_batch_decision with explicit session parameter."""
        setup = batch_decision_setup

        with session_scope() as session:
            decision = BatchDecisionInput(finished_unit_id=setup.fu1_id, batches=6)
            save_batch_decision(setup.event_id, decision, session=session)

            result = get_batch_decision(setup.event_id, setup.fu1_id, session=session)
            assert result is not None
            assert result.batches == 6


# =============================================================================
# Tests for delete_batch_decisions() (T019)
# =============================================================================


class TestDeleteBatchDecisions:
    """Tests for delete_batch_decisions() function."""

    def test_delete_no_decisions(self, batch_decision_setup):
        """Test deleting when no decisions exist."""
        setup = batch_decision_setup
        count = delete_batch_decisions(setup.event_id)
        assert count == 0

    def test_delete_single_decision(self, batch_decision_setup):
        """Test deleting a single decision."""
        setup = batch_decision_setup
        save_batch_decision(
            setup.event_id,
            BatchDecisionInput(finished_unit_id=setup.fu1_id, batches=3),
        )

        count = delete_batch_decisions(setup.event_id)

        assert count == 1
        assert get_batch_decisions(setup.event_id) == []

    def test_delete_multiple_decisions(self, batch_decision_setup):
        """Test deleting multiple decisions."""
        setup = batch_decision_setup

        # Save multiple decisions
        save_batch_decision(
            setup.event_id,
            BatchDecisionInput(finished_unit_id=setup.fu1_id, batches=3),
        )
        save_batch_decision(
            setup.event_id,
            BatchDecisionInput(finished_unit_id=setup.fu2_id, batches=5),
        )

        count = delete_batch_decisions(setup.event_id)

        assert count == 2
        assert get_batch_decisions(setup.event_id) == []

    def test_delete_decisions_isolated_by_event(self, batch_decision_setup, second_event):
        """Test that delete only affects specified event."""
        setup = batch_decision_setup

        # Save decisions for both events
        save_batch_decision(
            setup.event_id,
            BatchDecisionInput(finished_unit_id=setup.fu1_id, batches=3),
        )
        save_batch_decision(
            second_event,
            BatchDecisionInput(finished_unit_id=setup.fu1_id, batches=10),
        )

        # Delete only first event's decisions
        count = delete_batch_decisions(setup.event_id)

        assert count == 1
        assert get_batch_decisions(setup.event_id) == []
        assert len(get_batch_decisions(second_event)) == 1

    def test_delete_decisions_with_session_param(self, batch_decision_setup):
        """Test delete_batch_decisions with explicit session parameter."""
        setup = batch_decision_setup

        with session_scope() as session:
            save_batch_decision(
                setup.event_id,
                BatchDecisionInput(finished_unit_id=setup.fu1_id, batches=3),
                session=session,
            )

            count = delete_batch_decisions(setup.event_id, session=session)

            assert count == 1
            # Verify deletion within same session
            remaining = get_batch_decisions(setup.event_id, session=session)
            assert remaining == []


# =============================================================================
# Tests for is_shortfall_option() helper (T020)
# =============================================================================


class TestIsShortfallOption:
    """Tests for is_shortfall_option() helper function."""

    def test_no_shortfall_exact_match(self):
        """Test when yield exactly matches quantity needed."""
        # 3 batches * 20 per batch = 60 = 60 needed
        assert is_shortfall_option(batches=3, yield_per_batch=20, quantity_needed=60) is False

    def test_no_shortfall_excess(self):
        """Test when yield exceeds quantity needed."""
        # 3 batches * 24 per batch = 72 > 60 needed
        assert is_shortfall_option(batches=3, yield_per_batch=24, quantity_needed=60) is False

    def test_shortfall_detected(self):
        """Test when yield is less than quantity needed."""
        # 2 batches * 24 per batch = 48 < 60 needed
        assert is_shortfall_option(batches=2, yield_per_batch=24, quantity_needed=60) is True

    def test_shortfall_minimal(self):
        """Test shortfall by just one unit."""
        # 2 batches * 24 per batch = 48 < 49 needed (shortfall of 1)
        assert is_shortfall_option(batches=2, yield_per_batch=24, quantity_needed=49) is True

    def test_zero_batches_is_shortfall(self):
        """Test that zero batches is always a shortfall when something is needed."""
        assert is_shortfall_option(batches=0, yield_per_batch=24, quantity_needed=10) is True

    def test_zero_needed_no_shortfall(self):
        """Test that zero needed is never a shortfall."""
        assert is_shortfall_option(batches=0, yield_per_batch=24, quantity_needed=0) is False
        assert is_shortfall_option(batches=1, yield_per_batch=24, quantity_needed=0) is False


# =============================================================================
# Integration Tests
# =============================================================================


class TestBatchDecisionIntegration:
    """Integration tests for batch decision service."""

    def test_full_workflow(self, batch_decision_setup):
        """Test complete workflow: create, read, update, delete."""
        setup = batch_decision_setup

        # Create
        save_batch_decision(
            setup.event_id,
            BatchDecisionInput(finished_unit_id=setup.fu1_id, batches=3),
        )

        # Read
        decision = get_batch_decision(setup.event_id, setup.fu1_id)
        assert decision.batches == 3

        # Update
        save_batch_decision(
            setup.event_id,
            BatchDecisionInput(finished_unit_id=setup.fu1_id, batches=5),
        )
        updated = get_batch_decision(setup.event_id, setup.fu1_id)
        assert updated.batches == 5

        # Delete
        count = delete_batch_decisions(setup.event_id)
        assert count == 1
        assert get_batch_decision(setup.event_id, setup.fu1_id) is None

    def test_session_atomicity(self, batch_decision_setup):
        """Test that operations share session for atomicity."""
        setup = batch_decision_setup

        with session_scope() as session:
            # Save multiple decisions in same transaction
            save_batch_decision(
                setup.event_id,
                BatchDecisionInput(finished_unit_id=setup.fu1_id, batches=3),
                session=session,
            )
            save_batch_decision(
                setup.event_id,
                BatchDecisionInput(finished_unit_id=setup.fu2_id, batches=5),
                session=session,
            )

            # All should be visible within same session
            decisions = get_batch_decisions(setup.event_id, session=session)
            assert len(decisions) == 2

        # After commit, changes should be persisted
        decisions = get_batch_decisions(setup.event_id)
        assert len(decisions) == 2
