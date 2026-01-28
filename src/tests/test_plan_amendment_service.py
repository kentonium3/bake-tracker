"""Unit tests for plan_amendment_service.

Feature 078: Plan Snapshots & Amendments
"""

import pytest
from datetime import datetime

from src.models import Event, EventFinishedGood, BatchDecision, FinishedGood, Recipe
from src.models.event import PlanState
from src.models.plan_amendment import AmendmentType
from src.services import plan_amendment_service
from src.services.exceptions import ValidationError, PlanStateError


class TestAmendmentValidation:
    """Tests for amendment validation rules."""

    def test_rejects_amendment_when_not_in_production(self, test_db):
        """Amendments require IN_PRODUCTION state."""
        session = test_db()

        event = Event(
            name="Draft Event",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.DRAFT,
        )
        session.add(event)
        session.flush()

        with pytest.raises(PlanStateError):
            plan_amendment_service.create_amendment(
                event.id,
                AmendmentType.DROP_FG,
                {"fg_id": 1},
                "test reason",
                session
            )

    def test_rejects_amendment_when_locked(self, test_db):
        """Amendments require IN_PRODUCTION state, not LOCKED."""
        session = test_db()

        event = Event(
            name="Locked Event",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.LOCKED,
        )
        session.add(event)
        session.flush()

        with pytest.raises(PlanStateError):
            plan_amendment_service.create_amendment(
                event.id,
                AmendmentType.DROP_FG,
                {"fg_id": 1},
                "test reason",
                session
            )

    def test_rejects_amendment_with_empty_reason(self, test_db):
        """Amendments require non-empty reason."""
        session = test_db()

        event = Event(
            name="In Production",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        with pytest.raises(ValidationError):
            plan_amendment_service.create_amendment(
                event.id,
                AmendmentType.DROP_FG,
                {"fg_id": 1},
                "",  # Empty reason
                session
            )

    def test_rejects_amendment_with_whitespace_only_reason(self, test_db):
        """Amendments require non-whitespace reason."""
        session = test_db()

        event = Event(
            name="In Production",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        with pytest.raises(ValidationError):
            plan_amendment_service.create_amendment(
                event.id,
                AmendmentType.DROP_FG,
                {"fg_id": 1},
                "   ",  # Whitespace only
                session
            )


class TestDropFinishedGood:
    """Tests for drop_finished_good function."""

    def test_drops_fg_and_creates_amendment(self, test_db):
        """Successfully drops FG and records amendment."""
        session = test_db()

        # Create FG
        fg = FinishedGood(
            display_name="Test Gift Box",
            slug="test-gift-box",
        )
        session.add(fg)
        session.flush()

        # Create event
        event = Event(
            name="Test",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        # Add FG to event
        event_fg = EventFinishedGood(
            event_id=event.id,
            finished_good_id=fg.id,
            quantity=10,
        )
        session.add(event_fg)
        session.flush()

        # Drop
        amendment = plan_amendment_service.drop_finished_good(
            event.id, fg.id, "Not needed", session
        )

        # Verify amendment
        assert amendment.amendment_type == AmendmentType.DROP_FG
        assert amendment.amendment_data["fg_id"] == fg.id
        assert amendment.amendment_data["original_quantity"] == 10
        assert amendment.reason == "Not needed"

        # Verify EventFinishedGood deleted
        remaining = session.query(EventFinishedGood).filter(
            EventFinishedGood.event_id == event.id,
            EventFinishedGood.finished_good_id == fg.id,
        ).first()
        assert remaining is None

    def test_rejects_drop_when_fg_not_in_plan(self, test_db):
        """Cannot drop FG that's not in plan."""
        session = test_db()

        event = Event(
            name="Test",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        with pytest.raises(ValidationError) as exc_info:
            plan_amendment_service.drop_finished_good(
                event.id, 99999, "Test", session
            )
        assert "not in event plan" in str(exc_info.value)


class TestAddFinishedGood:
    """Tests for add_finished_good function."""

    def test_adds_fg_and_creates_amendment(self, test_db):
        """Successfully adds FG and records amendment."""
        session = test_db()

        # Create FG
        fg = FinishedGood(
            display_name="New Gift Box",
            slug="new-gift-box",
        )
        session.add(fg)
        session.flush()

        # Create event
        event = Event(
            name="Test",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        # Add FG via amendment
        amendment = plan_amendment_service.add_finished_good(
            event.id, fg.id, 5, "Adding more", session
        )

        assert amendment.amendment_type == AmendmentType.ADD_FG
        assert amendment.amendment_data["quantity"] == 5
        assert amendment.amendment_data["fg_name"] == "New Gift Box"

        # Verify EventFinishedGood created
        event_fg = session.query(EventFinishedGood).filter(
            EventFinishedGood.event_id == event.id,
            EventFinishedGood.finished_good_id == fg.id,
        ).first()
        assert event_fg is not None
        assert event_fg.quantity == 5

    def test_rejects_add_when_fg_already_in_plan(self, test_db):
        """Cannot add FG that's already in plan."""
        session = test_db()

        # Create FG
        fg = FinishedGood(
            display_name="Existing Gift Box",
            slug="existing-gift-box",
        )
        session.add(fg)
        session.flush()

        # Create event
        event = Event(
            name="Test",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        # Add FG first time directly
        event_fg = EventFinishedGood(
            event_id=event.id,
            finished_good_id=fg.id,
            quantity=10,
        )
        session.add(event_fg)
        session.flush()

        # Try to add again via amendment
        with pytest.raises(ValidationError) as exc_info:
            plan_amendment_service.add_finished_good(
                event.id, fg.id, 5, "Duplicate", session
            )
        assert "already in event plan" in str(exc_info.value)

    def test_rejects_add_when_fg_not_found(self, test_db):
        """Cannot add FG that doesn't exist."""
        session = test_db()

        event = Event(
            name="Test",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        with pytest.raises(ValidationError) as exc_info:
            plan_amendment_service.add_finished_good(
                event.id, 99999, 5, "Ghost FG", session
            )
        assert "not found" in str(exc_info.value)

    def test_rejects_add_with_zero_quantity(self, test_db):
        """Cannot add FG with zero quantity."""
        session = test_db()

        fg = FinishedGood(
            display_name="Test Box",
            slug="test-box",
        )
        session.add(fg)
        session.flush()

        event = Event(
            name="Test",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        with pytest.raises(ValidationError) as exc_info:
            plan_amendment_service.add_finished_good(
                event.id, fg.id, 0, "Zero quantity", session
            )
        assert "positive" in str(exc_info.value)


class TestModifyBatchDecision:
    """Tests for modify_batch_decision function."""

    def test_modifies_batch_and_creates_amendment(self, test_db):
        """Successfully modifies batch count and records amendment."""
        session = test_db()

        # Create recipe
        recipe = Recipe(
            name="Test Cookies",
            category="Cookies",
        )
        session.add(recipe)
        session.flush()

        # Create event
        event = Event(
            name="Test",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        # Create FinishedUnit (requires recipe_id)
        from src.models import FinishedUnit

        finished_unit = FinishedUnit(
            display_name="Cookie",
            slug="cookie-test",
            recipe_id=recipe.id,
            items_per_batch=24,
            item_unit="cookie",
        )
        session.add(finished_unit)
        session.flush()

        batch_decision = BatchDecision(
            event_id=event.id,
            recipe_id=recipe.id,
            finished_unit_id=finished_unit.id,
            batches=5,
        )
        session.add(batch_decision)
        session.flush()

        # Modify batch
        amendment = plan_amendment_service.modify_batch_decision(
            event.id, recipe.id, 8, "Need more", session
        )

        assert amendment.amendment_type == AmendmentType.MODIFY_BATCH
        assert amendment.amendment_data["old_batches"] == 5
        assert amendment.amendment_data["new_batches"] == 8
        assert amendment.amendment_data["recipe_name"] == "Test Cookies"

        # Verify BatchDecision updated
        session.refresh(batch_decision)
        assert batch_decision.batches == 8

    def test_rejects_modify_when_no_batch_decision(self, test_db):
        """Cannot modify batch for recipe without batch decision."""
        session = test_db()

        event = Event(
            name="Test",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        with pytest.raises(ValidationError) as exc_info:
            plan_amendment_service.modify_batch_decision(
                event.id, 99999, 10, "No batch", session
            )
        assert "No batch decision" in str(exc_info.value)

    def test_rejects_negative_batch_count(self, test_db):
        """Cannot set negative batch count."""
        session = test_db()

        # Create recipe
        recipe = Recipe(
            name="Test Recipe Neg",
            category="Test",
        )
        session.add(recipe)
        session.flush()

        event = Event(
            name="Test",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        # Create FinishedUnit (requires recipe_id)
        from src.models import FinishedUnit

        finished_unit = FinishedUnit(
            display_name="Test Unit Neg",
            slug="test-unit-neg",
            recipe_id=recipe.id,
            items_per_batch=12,
            item_unit="unit",
        )
        session.add(finished_unit)
        session.flush()

        batch_decision = BatchDecision(
            event_id=event.id,
            recipe_id=recipe.id,
            finished_unit_id=finished_unit.id,
            batches=5,
        )
        session.add(batch_decision)
        session.flush()

        with pytest.raises(ValidationError) as exc_info:
            plan_amendment_service.modify_batch_decision(
                event.id, recipe.id, -1, "Negative", session
            )
        assert "cannot be negative" in str(exc_info.value)


class TestGetAmendments:
    """Tests for get_amendments function."""

    def test_returns_amendments_in_chronological_order(self, test_db):
        """Amendments returned oldest first."""
        session = test_db()

        event = Event(
            name="Test",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        # Create multiple amendments
        for i in range(3):
            plan_amendment_service.create_amendment(
                event.id,
                AmendmentType.DROP_FG,
                {"fg_id": i},
                f"Reason {i}",
                session
            )

        amendments = plan_amendment_service.get_amendments(event.id, session)

        assert len(amendments) == 3
        # Verify chronological order
        for i in range(len(amendments) - 1):
            assert amendments[i].created_at <= amendments[i + 1].created_at

    def test_returns_empty_list_when_no_amendments(self, test_db):
        """Returns empty list for event with no amendments."""
        session = test_db()

        event = Event(
            name="No Amendments",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
        )
        session.add(event)
        session.flush()

        amendments = plan_amendment_service.get_amendments(event.id, session)
        assert amendments == []

    def test_amendments_contain_correct_data(self, test_db):
        """Amendment data is accessible."""
        session = test_db()

        event = Event(
            name="Test",
            event_date=datetime(2026, 12, 25).date(),
            year=2026,
            plan_state=PlanState.IN_PRODUCTION,
        )
        session.add(event)
        session.flush()

        plan_amendment_service.create_amendment(
            event.id,
            AmendmentType.DROP_FG,
            {"fg_id": 123, "fg_name": "Test Box"},
            "Testing data",
            session
        )

        amendments = plan_amendment_service.get_amendments(event.id, session)

        assert len(amendments) == 1
        assert amendments[0].amendment_type == AmendmentType.DROP_FG
        assert amendments[0].amendment_data["fg_id"] == 123
        assert amendments[0].amendment_data["fg_name"] == "Test Box"
        assert amendments[0].reason == "Testing data"
