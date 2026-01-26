"""
Integration tests for F068 Planning Data Export/Import.

Tests that the new planning fields and junction tables are correctly
exported and imported by the import/export service.
"""

import json
import os
import pytest
import tempfile
from datetime import date
from decimal import Decimal

from src.services.database import session_scope
from src.services import event_service
from src.services.import_export_service import export_all_to_json, import_all_from_json_v4
from src.models.event import Event, PlanState
from src.models.event_recipe import EventRecipe
from src.models.event_finished_good import EventFinishedGood
from src.models.batch_decision import BatchDecision
from src.models.plan_amendment import PlanAmendment, AmendmentType
from src.models.recipe import Recipe
from src.models.finished_good import FinishedGood
from src.models.finished_unit import FinishedUnit
from src.models.ingredient import Ingredient


@pytest.fixture
def planning_test_data(test_db):
    """Create test data for planning export/import tests."""
    with session_scope() as session:
        # Create ingredient
        ingredient = Ingredient(
            display_name="Test Flour",
            slug="test-flour",
            category="dry",
        )
        session.add(ingredient)
        session.flush()

        # Create recipe (F056 removed batch_size fields, use FinishedUnit for yield)
        recipe = Recipe(
            name="Test Cookies",
            category="Cookies",
            notes="Mix and bake",
        )
        session.add(recipe)
        session.flush()

        # Create finished unit (provides yield info for recipe)
        from src.models.finished_unit import YieldMode
        finished_unit = FinishedUnit(
            recipe_id=recipe.id,
            display_name="Cookie",
            slug="cookie",
            yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=24,
            item_unit="piece",
        )
        session.add(finished_unit)
        session.flush()

        # Create finished good
        finished_good = FinishedGood(
            display_name="Cookie Gift Box",
            slug="cookie-gift-box",
        )
        session.add(finished_good)
        session.flush()

        # Create event with F068 planning fields
        event = Event(
            name="Holiday 2026",
            event_date=date(2026, 12, 20),
            year=2026,
            expected_attendees=50,
            plan_state=PlanState.DRAFT,
        )
        session.add(event)
        session.flush()

        # Create EventRecipe association
        event_recipe = EventRecipe(
            event_id=event.id,
            recipe_id=recipe.id,
        )
        session.add(event_recipe)

        # Create EventFinishedGood association
        event_fg = EventFinishedGood(
            event_id=event.id,
            finished_good_id=finished_good.id,
            quantity=25,
        )
        session.add(event_fg)

        # Create BatchDecision
        batch_decision = BatchDecision(
            event_id=event.id,
            recipe_id=recipe.id,
            batches=3,
            finished_unit_id=finished_unit.id,
        )
        session.add(batch_decision)

        # Create PlanAmendment
        plan_amendment = PlanAmendment(
            event_id=event.id,
            amendment_type=AmendmentType.MODIFY_BATCH,
            amendment_data={"old_batches": 2, "new_batches": 3},
            reason="Increased attendee count",
        )
        session.add(plan_amendment)

        session.commit()

        return {
            "event_id": event.id,
            "event_name": event.name,
            "recipe_id": recipe.id,
            "recipe_name": recipe.name,
            "finished_good_id": finished_good.id,
            "finished_good_name": finished_good.display_name,
            "finished_unit_id": finished_unit.id,
            "finished_unit_name": finished_unit.display_name,
        }


class TestF068PlanningFieldsExport:
    """Tests for exporting F068 planning fields with events."""

    def test_event_exports_expected_attendees(self, test_db, planning_test_data):
        """Verify expected_attendees is included in event export."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            export_path = f.name

        try:
            result = export_all_to_json(export_path)
            assert result.success  # Export succeeded

            with open(export_path, "r") as f:
                export_data = json.load(f)

            events = export_data.get("events", [])
            holiday_event = next(
                (e for e in events if e["name"] == "Holiday 2026"), None
            )

            assert holiday_event is not None
            assert holiday_event["expected_attendees"] == 50
        finally:
            os.unlink(export_path)

    def test_event_exports_plan_state(self, test_db, planning_test_data):
        """Verify plan_state is included in event export."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            export_path = f.name

        try:
            result = export_all_to_json(export_path)

            with open(export_path, "r") as f:
                export_data = json.load(f)

            events = export_data.get("events", [])
            holiday_event = next(
                (e for e in events if e["name"] == "Holiday 2026"), None
            )

            assert holiday_event is not None
            assert holiday_event["plan_state"] == "draft"
        finally:
            os.unlink(export_path)


class TestF068PlanningTablesExport:
    """Tests for exporting F068 planning junction tables."""

    def test_exports_event_recipes(self, test_db, planning_test_data):
        """Verify event_recipes are exported."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            export_path = f.name

        try:
            export_all_to_json(export_path)

            with open(export_path, "r") as f:
                export_data = json.load(f)

            event_recipes = export_data.get("event_recipes", [])
            assert len(event_recipes) >= 1

            er = next(
                (r for r in event_recipes if r["event_name"] == "Holiday 2026"), None
            )
            assert er is not None
            assert er["recipe_name"] == "Test Cookies"
        finally:
            os.unlink(export_path)

    def test_exports_event_finished_goods(self, test_db, planning_test_data):
        """Verify event_finished_goods are exported."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            export_path = f.name

        try:
            export_all_to_json(export_path)

            with open(export_path, "r") as f:
                export_data = json.load(f)

            event_fgs = export_data.get("event_finished_goods", [])
            assert len(event_fgs) >= 1

            efg = next(
                (r for r in event_fgs if r["event_name"] == "Holiday 2026"), None
            )
            assert efg is not None
            assert efg["finished_good_name"] == "Cookie Gift Box"
            assert efg["quantity"] == 25
        finally:
            os.unlink(export_path)

    def test_exports_batch_decisions(self, test_db, planning_test_data):
        """Verify batch_decisions are exported."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            export_path = f.name

        try:
            export_all_to_json(export_path)

            with open(export_path, "r") as f:
                export_data = json.load(f)

            batch_decisions = export_data.get("batch_decisions", [])
            assert len(batch_decisions) >= 1

            bd = next(
                (r for r in batch_decisions if r["event_name"] == "Holiday 2026"), None
            )
            assert bd is not None
            assert bd["recipe_name"] == "Test Cookies"
            assert bd["batches"] == 3
            assert bd.get("finished_unit_name") == "Cookie"
        finally:
            os.unlink(export_path)

    def test_exports_plan_amendments(self, test_db, planning_test_data):
        """Verify plan_amendments are exported."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            export_path = f.name

        try:
            export_all_to_json(export_path)

            with open(export_path, "r") as f:
                export_data = json.load(f)

            plan_amendments = export_data.get("plan_amendments", [])
            assert len(plan_amendments) >= 1

            pa = next(
                (r for r in plan_amendments if r["event_name"] == "Holiday 2026"), None
            )
            assert pa is not None
            assert pa["amendment_type"] == "modify_batch"
            assert pa["reason"] == "Increased attendee count"
            assert pa["amendment_data"]["new_batches"] == 3
        finally:
            os.unlink(export_path)


class TestF068PlanningImport:
    """Tests for importing F068 planning data."""

    def test_import_restores_event_planning_fields(self, test_db, planning_test_data):
        """Verify import restores expected_attendees and plan_state."""
        # First export
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            export_path = f.name

        try:
            export_all_to_json(export_path)

            # Clear the database
            with session_scope() as session:
                session.query(PlanAmendment).delete()
                session.query(BatchDecision).delete()
                session.query(EventFinishedGood).delete()
                session.query(EventRecipe).delete()
                session.query(Event).delete()
                session.commit()

            # Verify event is deleted
            with session_scope() as session:
                count = session.query(Event).count()
                assert count == 0

            # Import
            result = import_all_from_json_v4(export_path, mode="replace")
            assert result.successful > 0

            # Verify event has planning fields restored
            with session_scope() as session:
                event = session.query(Event).filter_by(name="Holiday 2026").first()
                assert event is not None
                assert event.expected_attendees == 50
                assert event.plan_state == PlanState.DRAFT
        finally:
            os.unlink(export_path)

    def test_import_restores_event_recipes(self, test_db, planning_test_data):
        """Verify import restores event_recipes."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            export_path = f.name

        try:
            export_all_to_json(export_path)

            # Clear planning data
            with session_scope() as session:
                session.query(PlanAmendment).delete()
                session.query(BatchDecision).delete()
                session.query(EventFinishedGood).delete()
                session.query(EventRecipe).delete()
                session.query(Event).delete()
                session.commit()

            # Import
            result = import_all_from_json_v4(export_path, mode="replace")

            # Verify event_recipe restored
            with session_scope() as session:
                event = session.query(Event).filter_by(name="Holiday 2026").first()
                recipe = session.query(Recipe).filter_by(name="Test Cookies").first()

                er = session.query(EventRecipe).filter_by(
                    event_id=event.id, recipe_id=recipe.id
                ).first()
                assert er is not None
        finally:
            os.unlink(export_path)

    def test_import_restores_batch_decisions(self, test_db, planning_test_data):
        """Verify import restores batch_decisions."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            export_path = f.name

        try:
            export_all_to_json(export_path)

            # Clear planning data
            with session_scope() as session:
                session.query(PlanAmendment).delete()
                session.query(BatchDecision).delete()
                session.query(EventFinishedGood).delete()
                session.query(EventRecipe).delete()
                session.query(Event).delete()
                session.commit()

            # Import
            result = import_all_from_json_v4(export_path, mode="replace")

            # Verify batch_decision restored
            with session_scope() as session:
                event = session.query(Event).filter_by(name="Holiday 2026").first()
                recipe = session.query(Recipe).filter_by(name="Test Cookies").first()

                bd = session.query(BatchDecision).filter_by(
                    event_id=event.id, recipe_id=recipe.id
                ).first()
                assert bd is not None
                assert bd.batches == 3
        finally:
            os.unlink(export_path)

    def test_import_restores_plan_amendments(self, test_db, planning_test_data):
        """Verify import restores plan_amendments."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            export_path = f.name

        try:
            export_all_to_json(export_path)

            # Clear planning data
            with session_scope() as session:
                session.query(PlanAmendment).delete()
                session.query(BatchDecision).delete()
                session.query(EventFinishedGood).delete()
                session.query(EventRecipe).delete()
                session.query(Event).delete()
                session.commit()

            # Import
            result = import_all_from_json_v4(export_path, mode="replace")

            # Verify plan_amendment restored
            with session_scope() as session:
                event = session.query(Event).filter_by(name="Holiday 2026").first()

                pa = session.query(PlanAmendment).filter_by(
                    event_id=event.id
                ).first()
                assert pa is not None
                assert pa.amendment_type == AmendmentType.MODIFY_BATCH
                assert pa.reason == "Increased attendee count"
        finally:
            os.unlink(export_path)


class TestF068RoundTrip:
    """End-to-end roundtrip tests for F068 planning data."""

    def test_full_roundtrip_preserves_all_planning_data(
        self, test_db, planning_test_data
    ):
        """
        Verify complete Export -> Delete -> Import cycle preserves all planning data.

        This is the key acceptance test for Constitution Principle VI compliance.
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            export_path = f.name

        try:
            # Export
            export_result = export_all_to_json(export_path)

            # Capture expected counts
            with open(export_path, "r") as f:
                export_data = json.load(f)

            expected_event_recipes = len(export_data["event_recipes"])
            expected_event_fgs = len(export_data["event_finished_goods"])
            expected_batch_decisions = len(export_data["batch_decisions"])
            expected_plan_amendments = len(export_data["plan_amendments"])

            # Clear all planning data (simulates database reset)
            with session_scope() as session:
                session.query(PlanAmendment).delete()
                session.query(BatchDecision).delete()
                session.query(EventFinishedGood).delete()
                session.query(EventRecipe).delete()
                session.query(Event).delete()
                session.commit()

            # Import
            import_result = import_all_from_json_v4(export_path, mode="replace")

            # Verify counts match
            with session_scope() as session:
                actual_event_recipes = session.query(EventRecipe).count()
                actual_event_fgs = session.query(EventFinishedGood).count()
                actual_batch_decisions = session.query(BatchDecision).count()
                actual_plan_amendments = session.query(PlanAmendment).count()

                assert actual_event_recipes == expected_event_recipes
                assert actual_event_fgs == expected_event_fgs
                assert actual_batch_decisions == expected_batch_decisions
                assert actual_plan_amendments == expected_plan_amendments

            # Verify specific data integrity
            with session_scope() as session:
                event = session.query(Event).filter_by(name="Holiday 2026").first()
                assert event is not None
                assert event.expected_attendees == 50
                assert event.plan_state == PlanState.DRAFT
        finally:
            os.unlink(export_path)
