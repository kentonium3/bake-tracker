"""
Unit tests for planning service facade (Feature 039 WP06, F065 WP07).

Tests cover:
- calculate_plan() for BUNDLED and BULK_COUNT modes (deprecated)
- check_staleness() - deprecated, always returns (False, None) with snapshots
- get_plan_summary() for phase statuses
- get_plan_calculation() for on-demand calculation from snapshots (WP07)
- Exception handling (EventNotConfiguredError, etc.)
- Facade method delegation
- Performance tests for snapshot-based calculation

F065 Changes (WP07):
- check_staleness() deprecated (snapshots are immutable)
- get_plan_calculation() added for snapshot-based calculation
- Performance test for <5 second calculation target
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal

from src.services.planning import (
    # Facade functions
    create_plan,  # WP04: New snapshot-based planning
    get_plan_calculation,  # WP07: On-demand calculation from snapshots
    calculate_plan,  # Deprecated
    check_staleness,
    get_plan_summary,
    get_recipe_batches,
    calculate_batches_for_quantity,
    get_assembly_checklist,
    record_assembly_confirmation,
    # Exceptions
    PlanningError,
    StalePlanError,
    IncompleteRequirementsError,
    EventNotConfiguredError,
    EventNotFoundError,
    # DTOs
    PlanSummary,
    PlanPhase,
    PhaseStatus,
)
from src.models import (
    Event,
    EventAssemblyTarget,
    EventProductionTarget,
    ProductionPlanSnapshot,
    Recipe,
    FinishedGood,
    FinishedUnit,
    Composition,
)
from src.models.event import OutputMode
from src.models.assembly_type import AssemblyType
from src.utils.datetime_utils import utc_now


class TestPlanningExceptions:
    """Tests for planning service exceptions."""

    def test_planning_error_base(self):
        """Verify PlanningError is base exception."""
        err = PlanningError("test error")
        assert str(err) == "test error"

    def test_stale_plan_error(self):
        """Verify StalePlanError includes reason."""
        err = StalePlanError("recipe modified")
        assert err.reason == "recipe modified"
        assert "Plan is stale: recipe modified" in str(err)

    def test_incomplete_requirements_error(self):
        """Verify IncompleteRequirementsError includes missing list."""
        err = IncompleteRequirementsError(["output_mode", "assembly_targets"])
        assert err.missing == ["output_mode", "assembly_targets"]
        assert "output_mode" in str(err)

    def test_event_not_configured_error(self):
        """Verify EventNotConfiguredError includes event_id."""
        err = EventNotConfiguredError(42)
        assert err.event_id == 42
        assert "42" in str(err)
        assert "output_mode" in str(err)

    def test_event_not_found_error(self):
        """Verify EventNotFoundError includes event_id."""
        err = EventNotFoundError(99)
        assert err.event_id == 99
        assert "99" in str(err)


class TestPlanPhaseAndStatus:
    """Tests for PlanPhase and PhaseStatus enums."""

    def test_plan_phase_values(self):
        """Verify all expected phase values exist."""
        assert PlanPhase.REQUIREMENTS.value == "requirements"
        assert PlanPhase.SHOPPING.value == "shopping"
        assert PlanPhase.PRODUCTION.value == "production"
        assert PlanPhase.ASSEMBLY.value == "assembly"

    def test_phase_status_values(self):
        """Verify all expected status values exist."""
        assert PhaseStatus.NOT_STARTED.value == "not_started"
        assert PhaseStatus.IN_PROGRESS.value == "in_progress"
        assert PhaseStatus.COMPLETE.value == "complete"


class TestCalculatePlan:
    """Tests for calculate_plan() function."""

    @pytest.fixture
    def bundled_setup(self, test_db):
        """Create event with BUNDLED output mode."""
        session = test_db()

        # Create event
        event = Event(
            name="Holiday Baking 2025",
            event_date=date(2025, 12, 25),
            year=2025,
            output_mode=OutputMode.BUNDLED,
        )
        session.add(event)
        session.flush()

        # Create recipe (F056: yield fields removed from Recipe model)
        cookie_recipe = Recipe(
            name="Sugar Cookies",
            category="Cookies",
        )
        session.add(cookie_recipe)
        session.flush()

        # Create FinishedUnit (F056: items_per_batch holds yield data)
        cookie_unit = FinishedUnit(
            display_name="Sugar Cookie",
            slug="sugar-cookie",
            recipe_id=cookie_recipe.id,
            items_per_batch=48,  # Was Recipe.yield_quantity
            item_unit="cookies",  # Was Recipe.yield_unit
            inventory_count=0,
        )
        session.add(cookie_unit)
        session.flush()

        # Create FinishedGood (bundle)
        gift_bag = FinishedGood(
            display_name="Holiday Gift Bag",
            slug="holiday-gift-bag",
            assembly_type=AssemblyType.GIFT_BOX,
            inventory_count=0,
        )
        session.add(gift_bag)
        session.flush()

        # Create composition: 6 cookies per bag
        comp = Composition.create_unit_composition(
            assembly_id=gift_bag.id,
            finished_unit_id=cookie_unit.id,
            quantity=6,
        )
        session.add(comp)

        # Create assembly target: 50 bags
        target = EventAssemblyTarget(
            event_id=event.id,
            finished_good_id=gift_bag.id,
            target_quantity=50,
        )
        session.add(target)
        session.commit()

        return {
            "event_id": event.id,
            "gift_bag_id": gift_bag.id,
            "cookie_unit_id": cookie_unit.id,
            "recipe_id": cookie_recipe.id,
        }

    @pytest.fixture
    def bulk_setup(self, test_db):
        """Create event with BULK_COUNT output mode."""
        session = test_db()

        # Create event
        event = Event(
            name="Bulk Baking 2025",
            event_date=date(2025, 12, 25),
            year=2025,
            output_mode=OutputMode.BULK_COUNT,
        )
        session.add(event)
        session.flush()

        # Create recipe (F056: yield fields removed from Recipe model)
        brownie_recipe = Recipe(
            name="Fudge Brownies",
            category="Brownies",
        )
        session.add(brownie_recipe)
        session.flush()

        # Create production target: 5 batches
        target = EventProductionTarget(
            event_id=event.id,
            recipe_id=brownie_recipe.id,
            target_batches=5,
        )
        session.add(target)
        session.commit()

        return {
            "event_id": event.id,
            "recipe_id": brownie_recipe.id,
        }

    def test_bundled_mode_calculates_batches(self, test_db, bundled_setup):
        """Test calculate_plan with BUNDLED output mode."""
        session = test_db()

        result = calculate_plan(bundled_setup["event_id"], session=session)

        assert "plan_id" in result
        assert "calculated_at" in result
        assert "recipe_batches" in result
        assert "feasibility" in result

        # 50 bags * 6 cookies = 300 cookies needed
        # 300 / 48 yield = 6.25 -> 7 batches
        if result["recipe_batches"]:
            rb = result["recipe_batches"][0]
            assert rb["units_needed"] == 300
            assert rb["batches"] == 7

    def test_bulk_mode_calculates_batches(self, test_db, bulk_setup):
        """Test calculate_plan with BULK_COUNT output mode."""
        session = test_db()

        result = calculate_plan(bulk_setup["event_id"], session=session)

        assert "plan_id" in result
        assert "recipe_batches" in result

    def test_force_recalculate(self, test_db, bundled_setup):
        """Test force_recalculate=True creates new plan."""
        session = test_db()

        # First calculation
        result1 = calculate_plan(bundled_setup["event_id"], session=session)
        plan_id1 = result1["plan_id"]

        # Force recalculate
        result2 = calculate_plan(bundled_setup["event_id"], force_recalculate=True, session=session)
        plan_id2 = result2["plan_id"]

        assert plan_id2 > plan_id1

    def test_event_not_configured_raises(self, test_db):
        """Test that unconfigured event raises EventNotConfiguredError."""
        session = test_db()

        # Create event without output_mode
        event = Event(
            name="Unconfigured Event",
            event_date=date(2025, 12, 25),
            year=2025,
            output_mode=None,
        )
        session.add(event)
        session.commit()

        with pytest.raises(EventNotConfiguredError) as exc_info:
            calculate_plan(event.id, session=session)

        assert exc_info.value.event_id == event.id

    def test_event_not_found_raises(self, test_db):
        """Test that nonexistent event raises EventNotFoundError."""
        session = test_db()

        with pytest.raises(EventNotFoundError) as exc_info:
            calculate_plan(99999, session=session)

        assert exc_info.value.event_id == 99999


class TestCreatePlan:
    """Tests for create_plan() function (WP04).

    Tests the new snapshot-based planning workflow that creates
    RecipeSnapshot for each production target and FinishedGoodSnapshot
    for each assembly target.
    """

    @pytest.fixture
    def production_target_setup(self, test_db):
        """Create event with production targets for snapshot creation."""
        session = test_db()

        # Create recipe with finished unit
        recipe = Recipe(
            name="Test Cookie Recipe",
            category="Cookies",
        )
        session.add(recipe)
        session.flush()

        finished_unit = FinishedUnit(
            slug="test-cookie",
            display_name="Test Cookie",
            recipe_id=recipe.id,
            items_per_batch=24,
            item_unit="cookies",
        )
        session.add(finished_unit)
        session.flush()

        # Create event with production target
        event = Event(
            name="Production Test Event",
            event_date=date(2025, 12, 25),
            year=2025,
            output_mode=OutputMode.BULK_COUNT,
        )
        session.add(event)
        session.flush()

        # Add production target
        target = EventProductionTarget(
            event_id=event.id,
            recipe_id=recipe.id,
            target_batches=3,
        )
        session.add(target)
        session.commit()

        return {
            "event_id": event.id,
            "recipe_id": recipe.id,
            "target_id": target.id,
        }

    def test_create_plan_success(self, test_db, production_target_setup):
        """Test basic create_plan() success."""
        session = test_db()

        result = create_plan(production_target_setup["event_id"], session=session)

        assert result["success"] is True
        assert result["planning_snapshot_id"] is not None
        assert result["recipe_snapshots_created"] >= 0
        assert result["finished_good_snapshots_created"] >= 0

    def test_create_plan_creates_recipe_snapshots(self, test_db, production_target_setup):
        """Test that create_plan creates RecipeSnapshot for production targets."""
        session = test_db()

        result = create_plan(production_target_setup["event_id"], session=session)

        # Verify snapshot was created
        assert result["recipe_snapshots_created"] == 1

        # Verify target now has recipe_snapshot_id set
        target = session.get(EventProductionTarget, production_target_setup["target_id"])
        assert target.recipe_snapshot_id is not None

        # Verify the snapshot exists and has planning context (no production_run_id)
        from src.models import RecipeSnapshot
        snapshot = session.get(RecipeSnapshot, target.recipe_snapshot_id)
        assert snapshot is not None
        assert snapshot.production_run_id is None  # Planning context

    def test_create_plan_atomic_transaction(self, test_db, production_target_setup):
        """Test that create_plan uses atomic transaction."""
        session = test_db()

        # Create plan
        result = create_plan(production_target_setup["event_id"], session=session)

        # Verify all created within same session (not detached)
        snapshot = session.get(ProductionPlanSnapshot, result["planning_snapshot_id"])
        assert snapshot is not None
        assert snapshot in session

    def test_create_plan_event_not_found(self, test_db):
        """Test that create_plan raises for nonexistent event."""
        session = test_db()

        with pytest.raises(EventNotFoundError):
            create_plan(99999, session=session)

    def test_create_plan_event_not_configured(self, test_db):
        """Test that create_plan raises for event without output_mode."""
        session = test_db()

        # Event without output_mode
        event = Event(
            name="Unconfigured Event",
            event_date=date(2025, 12, 25),
            year=2025,
            # output_mode not set
        )
        session.add(event)
        session.commit()

        with pytest.raises(EventNotConfiguredError):
            create_plan(event.id, session=session)

    def test_create_plan_force_recreate(self, test_db, production_target_setup):
        """Test force_recreate creates new snapshots even if they exist."""
        session = test_db()

        # Create plan first time
        result1 = create_plan(production_target_setup["event_id"], session=session)
        first_snapshot_id = result1["planning_snapshot_id"]

        # Get the recipe snapshot ID
        target = session.get(EventProductionTarget, production_target_setup["target_id"])
        first_recipe_snapshot_id = target.recipe_snapshot_id

        # Force recreate
        result2 = create_plan(
            production_target_setup["event_id"],
            force_recreate=True,
            session=session
        )

        # Should create new planning snapshot
        assert result2["planning_snapshot_id"] != first_snapshot_id

        # Should create new recipe snapshot (force_recreate)
        target = session.get(EventProductionTarget, production_target_setup["target_id"])
        assert target.recipe_snapshot_id != first_recipe_snapshot_id

    def test_create_plan_skips_existing_snapshots(self, test_db, production_target_setup):
        """Test that create_plan skips targets that already have snapshots."""
        session = test_db()

        # Create plan first time
        result1 = create_plan(production_target_setup["event_id"], session=session)
        assert result1["recipe_snapshots_created"] == 1

        # Get the recipe snapshot ID
        target = session.get(EventProductionTarget, production_target_setup["target_id"])
        first_recipe_snapshot_id = target.recipe_snapshot_id

        # Create again without force_recreate
        result2 = create_plan(production_target_setup["event_id"], session=session)

        # Should NOT create new recipe snapshot (already exists)
        assert result2["recipe_snapshots_created"] == 0

        # Recipe snapshot ID should be unchanged
        target = session.get(EventProductionTarget, production_target_setup["target_id"])
        assert target.recipe_snapshot_id == first_recipe_snapshot_id


class TestGetPlanCalculation:
    """Tests for get_plan_calculation() function (WP07)."""

    @pytest.fixture
    def plan_with_snapshots_setup(self, test_db):
        """Create event with plan and snapshots for calculation tests."""
        session = test_db()

        # Create event
        event = Event(
            name="Calculation Test Event",
            event_date=date(2025, 12, 25),
            year=2025,
            output_mode=OutputMode.BULK_COUNT,
        )
        session.add(event)
        session.flush()

        # Create recipe
        recipe = Recipe(name="Test Cookies", category="Cookies")
        session.add(recipe)
        session.flush()

        # Create production target
        target = EventProductionTarget(
            event_id=event.id,
            recipe_id=recipe.id,
            target_batches=5,
        )
        session.add(target)
        session.commit()

        # Create plan (this creates snapshots)
        result = create_plan(event.id, session=session)

        return {
            "event_id": event.id,
            "recipe_id": recipe.id,
            "target_id": target.id,
            "target_batches": 5,
            "planning_snapshot_id": result["planning_snapshot_id"],
        }

    def test_get_plan_calculation_returns_dict(self, test_db, plan_with_snapshots_setup):
        """Test that get_plan_calculation returns expected dict structure."""
        session = test_db()

        result = get_plan_calculation(
            plan_with_snapshots_setup["event_id"],
            session=session
        )

        assert isinstance(result, dict)
        assert "recipe_batches" in result
        assert "shopping_list" in result
        assert "aggregated_ingredients" in result

    def test_get_plan_calculation_recipe_batches(self, test_db, plan_with_snapshots_setup):
        """Test that recipe_batches contains correct data."""
        session = test_db()

        result = get_plan_calculation(
            plan_with_snapshots_setup["event_id"],
            session=session
        )

        recipe_batches = result["recipe_batches"]
        assert len(recipe_batches) == 1

        batch = recipe_batches[0]
        assert batch["recipe_id"] == plan_with_snapshots_setup["recipe_id"]
        assert batch["target_batches"] == plan_with_snapshots_setup["target_batches"]
        assert "recipe_name" in batch
        assert "has_snapshot" in batch
        assert batch["has_snapshot"] is True

    def test_get_plan_calculation_uses_snapshots(self, test_db, plan_with_snapshots_setup):
        """Test that calculation uses snapshot data, not live recipe."""
        session = test_db()

        # Modify the live recipe after plan was created
        recipe = session.get(Recipe, plan_with_snapshots_setup["recipe_id"])
        original_name = recipe.name
        recipe.name = "MODIFIED - Should Not Appear"
        session.commit()

        # Get calculation - should use snapshot data
        result = get_plan_calculation(
            plan_with_snapshots_setup["event_id"],
            session=session
        )

        # Recipe name should be from snapshot (original), not modified live data
        recipe_batches = result["recipe_batches"]
        assert len(recipe_batches) == 1
        assert recipe_batches[0]["recipe_name"] == original_name

    def test_get_plan_calculation_event_not_found(self, test_db):
        """Test that get_plan_calculation raises for nonexistent event."""
        session = test_db()

        with pytest.raises(EventNotFoundError):
            get_plan_calculation(99999, session=session)

    def test_get_plan_calculation_fallback_to_live(self, test_db):
        """Test fallback to live recipe when no snapshot exists."""
        session = test_db()

        # Create event with target but no plan (no snapshots)
        event = Event(
            name="No Snapshot Event",
            event_date=date(2025, 12, 25),
            year=2025,
            output_mode=OutputMode.BULK_COUNT,
        )
        session.add(event)
        session.flush()

        recipe = Recipe(name="Live Recipe", category="Test")
        session.add(recipe)
        session.flush()

        target = EventProductionTarget(
            event_id=event.id,
            recipe_id=recipe.id,
            target_batches=3,
        )
        session.add(target)
        session.commit()

        # Get calculation without creating plan first
        result = get_plan_calculation(event.id, session=session)

        # Should fall back to live recipe data
        recipe_batches = result["recipe_batches"]
        assert len(recipe_batches) == 1
        assert recipe_batches[0]["recipe_name"] == "Live Recipe"
        assert recipe_batches[0]["has_snapshot"] is False


class TestGetPlanCalculationPerformance:
    """Performance tests for get_plan_calculation() (WP07 T034)."""

    def test_get_plan_calculation_performance(self, test_db):
        """Verify get_plan_calculation completes in <5 seconds."""
        import time
        session = test_db()

        # Setup: create event with typical number of targets
        event = Event(
            name="Performance Test Event",
            event_date=date(2025, 12, 25),
            year=2025,
            output_mode=OutputMode.BULK_COUNT,
        )
        session.add(event)
        session.flush()

        # Create 20 production targets (typical event size per WP07)
        for i in range(20):
            recipe = Recipe(name=f"Recipe {i}", category="Test")
            session.add(recipe)
            session.flush()

            target = EventProductionTarget(
                event_id=event.id,
                recipe_id=recipe.id,
                target_batches=5,
            )
            session.add(target)

        session.commit()

        # Create plan (creates snapshots)
        create_plan(event.id, session=session)

        # Time the calculation
        start = time.time()
        result = get_plan_calculation(event.id, session=session)
        elapsed = time.time() - start

        # Assert performance
        assert elapsed < 5.0, f"get_plan_calculation took {elapsed:.2f}s, expected <5s"
        assert "recipe_batches" in result
        assert len(result["recipe_batches"]) == 20


class TestCheckStaleness:
    """Tests for check_staleness() function.

    F065: With snapshot-based planning, check_staleness() is DEPRECATED.
    Plans use immutable snapshots, so they never become stale.
    The function now always returns (False, None).

    These tests verify the deprecated behavior.
    """

    def test_check_staleness_always_returns_false(self, test_db):
        """F065: check_staleness always returns (False, None) with snapshots."""
        session = test_db()

        # Create event without a plan
        event = Event(
            name="Test Event",
            event_date=date(2025, 12, 25),
            year=2025,
        )
        session.add(event)
        session.commit()

        # Should always return (False, None) regardless of state
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            is_stale, reason = check_staleness(event.id, session=session)
            # Verify deprecation warning was issued
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()

        assert is_stale is False
        assert reason is None

    def test_check_staleness_ignores_modifications(self, test_db):
        """F065: check_staleness ignores all modifications (deprecated)."""
        session = test_db()

        # Create event with plan
        event = Event(
            name="Modified Event",
            event_date=date(2025, 12, 25),
            year=2025,
            output_mode=OutputMode.BUNDLED,
        )
        session.add(event)
        session.flush()

        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=event.id,
            calculated_at=now,
        )
        session.add(snapshot)
        session.commit()

        # Modify event after plan was calculated
        event.last_modified = now + timedelta(minutes=5)
        session.commit()

        # Should still return (False, None) - staleness concept deprecated
        import warnings
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            is_stale, reason = check_staleness(event.id, session=session)

        assert is_stale is False
        assert reason is None


class TestGetPlanSummary:
    """Tests for get_plan_summary() function."""

    @pytest.fixture
    def summary_setup(self, test_db):
        """Create event with plan for summary testing."""
        session = test_db()

        # Create event
        event = Event(
            name="Summary Test Event",
            event_date=date(2025, 12, 25),
            year=2025,
            output_mode=OutputMode.BUNDLED,
        )
        session.add(event)
        session.flush()

        # Create snapshot
        # Note: WP01 removed calculation_results and staleness fields from model
        now = utc_now()
        snapshot = ProductionPlanSnapshot(
            event_id=event.id,
            calculated_at=now,
            shopping_complete=False,
        )
        session.add(snapshot)
        session.commit()

        return {"event_id": event.id, "snapshot_id": snapshot.id}

    def test_returns_plan_summary(self, test_db, summary_setup):
        """Test that get_plan_summary returns PlanSummary."""
        session = test_db()

        summary = get_plan_summary(summary_setup["event_id"], session=session)

        assert isinstance(summary, PlanSummary)
        assert summary.event_id == summary_setup["event_id"]
        assert summary.plan_id == summary_setup["snapshot_id"]

    def test_includes_phase_statuses(self, test_db, summary_setup):
        """Test that summary includes phase statuses."""
        session = test_db()

        summary = get_plan_summary(summary_setup["event_id"], session=session)

        assert PlanPhase.REQUIREMENTS in summary.phase_statuses
        assert PlanPhase.SHOPPING in summary.phase_statuses
        assert PlanPhase.PRODUCTION in summary.phase_statuses
        assert PlanPhase.ASSEMBLY in summary.phase_statuses

    def test_event_not_found_raises(self, test_db):
        """Test that nonexistent event raises EventNotFoundError."""
        session = test_db()

        with pytest.raises(EventNotFoundError):
            get_plan_summary(99999, session=session)


class TestGetRecipeBatches:
    """Tests for get_recipe_batches() function."""

    @pytest.fixture
    def recipe_setup(self, test_db):
        """Create event with recipe for batch testing."""
        session = test_db()

        event = Event(
            name="Recipe Test Event",
            event_date=date(2025, 12, 25),
            year=2025,
            output_mode=OutputMode.BULK_COUNT,
        )
        session.add(event)
        session.flush()

        recipe = Recipe(
            name="Test Cookies",
            category="Cookies",
        )
        session.add(recipe)
        session.flush()

        target = EventProductionTarget(
            event_id=event.id,
            recipe_id=recipe.id,
            target_batches=3,
        )
        session.add(target)
        session.commit()

        return {"event_id": event.id, "recipe_id": recipe.id}

    def test_returns_batch_results(self, test_db, recipe_setup):
        """Test that get_recipe_batches returns list."""
        session = test_db()

        results = get_recipe_batches(recipe_setup["event_id"], session=session)

        assert isinstance(results, list)


class TestCalculateBatchesForQuantity:
    """Tests for calculate_batches_for_quantity() utility."""

    def test_basic_calculation(self):
        """Test basic batch calculation."""
        result = calculate_batches_for_quantity(100, 48)

        assert result["batches"] == 3  # ceil(100/48)
        assert result["total_yield"] == 144  # 3 * 48
        assert result["waste_units"] == 44  # 144 - 100
        assert 0 <= result["waste_percent"] <= 100

    def test_exact_fit(self):
        """Test calculation with exact fit."""
        result = calculate_batches_for_quantity(48, 48)

        assert result["batches"] == 1
        assert result["total_yield"] == 48
        assert result["waste_units"] == 0
        assert result["waste_percent"] == 0.0


class TestGetAssemblyChecklist:
    """Tests for get_assembly_checklist() function."""

    @pytest.fixture
    def checklist_setup(self, test_db):
        """Create event with assembly targets for checklist."""
        session = test_db()

        event = Event(
            name="Checklist Test Event",
            event_date=date(2025, 12, 25),
            year=2025,
            output_mode=OutputMode.BUNDLED,
        )
        session.add(event)
        session.flush()

        recipe = Recipe(
            name="Cookies",
            category="Cookies",
        )
        session.add(recipe)
        session.flush()

        cookie_unit = FinishedUnit(
            display_name="Cookie",
            slug="cookie",
            recipe_id=recipe.id,
            items_per_batch=48,  # F056: Was Recipe.yield_quantity
            item_unit="cookies",
            inventory_count=100,
        )
        session.add(cookie_unit)
        session.flush()

        gift_box = FinishedGood(
            display_name="Cookie Box",
            slug="cookie-box",
            assembly_type=AssemblyType.GIFT_BOX,
            inventory_count=5,
        )
        session.add(gift_box)
        session.flush()

        comp = Composition.create_unit_composition(
            assembly_id=gift_box.id,
            finished_unit_id=cookie_unit.id,
            quantity=6,
        )
        session.add(comp)

        target = EventAssemblyTarget(
            event_id=event.id,
            finished_good_id=gift_box.id,
            target_quantity=20,
        )
        session.add(target)
        session.commit()

        return {"event_id": event.id, "gift_box_id": gift_box.id}

    def test_returns_checklist(self, test_db, checklist_setup):
        """Test that checklist is returned."""
        session = test_db()

        checklist = get_assembly_checklist(checklist_setup["event_id"], session=session)

        assert isinstance(checklist, list)
        assert len(checklist) == 1

        item = checklist[0]
        assert item["finished_good_id"] == checklist_setup["gift_box_id"]
        assert item["target_quantity"] == 20
        assert "assembled_count" in item
        assert "can_assemble" in item
        assert "status" in item
        assert "remaining" in item

    def test_empty_checklist_for_no_targets(self, test_db):
        """Test empty checklist when no targets."""
        session = test_db()

        event = Event(
            name="No Targets Event",
            event_date=date(2025, 12, 25),
            year=2025,
        )
        session.add(event)
        session.commit()

        checklist = get_assembly_checklist(event.id, session=session)

        assert checklist == []


class TestRecordAssemblyConfirmation:
    """Tests for record_assembly_confirmation() function."""

    @pytest.fixture
    def confirmation_setup(self, test_db):
        """Create finished good for confirmation testing."""
        session = test_db()

        event = Event(
            name="Confirmation Test Event",
            event_date=date(2025, 12, 25),
            year=2025,
        )
        session.add(event)
        session.flush()

        gift_box = FinishedGood(
            display_name="Test Gift Box",
            slug="test-gift-box",
            assembly_type=AssemblyType.GIFT_BOX,
            inventory_count=0,
        )
        session.add(gift_box)
        session.commit()

        return {"event_id": event.id, "gift_box_id": gift_box.id}

    def test_returns_confirmation(self, test_db, confirmation_setup):
        """Test that confirmation is returned."""
        session = test_db()

        result = record_assembly_confirmation(
            confirmation_setup["gift_box_id"],
            10,
            confirmation_setup["event_id"],
            session=session,
        )

        assert result["finished_good_id"] == confirmation_setup["gift_box_id"]
        assert result["quantity_confirmed"] == 10
        assert result["event_id"] == confirmation_setup["event_id"]

    def test_nonexistent_bundle_raises(self, test_db, confirmation_setup):
        """Test that nonexistent bundle raises error."""
        session = test_db()

        with pytest.raises(PlanningError):
            record_assembly_confirmation(99999, 10, confirmation_setup["event_id"], session=session)


class TestIntegration:
    """Integration tests for full planning workflow."""

    @pytest.fixture
    def full_setup(self, test_db):
        """Create complete setup for integration testing."""
        session = test_db()

        # Create event
        event = Event(
            name="Integration Test Event",
            event_date=date(2025, 12, 25),
            year=2025,
            output_mode=OutputMode.BUNDLED,
        )
        session.add(event)
        session.flush()

        # Create recipe
        cookie_recipe = Recipe(
            name="Holiday Cookies",
            category="Cookies",
        )
        session.add(cookie_recipe)
        session.flush()

        # Create FinishedUnit (F056: items_per_batch holds yield data)
        cookie = FinishedUnit(
            display_name="Holiday Cookie",
            slug="holiday-cookie",
            recipe_id=cookie_recipe.id,
            items_per_batch=48,  # Was Recipe.yield_quantity
            item_unit="cookies",
            inventory_count=0,
        )
        session.add(cookie)
        session.flush()

        # Create FinishedGood
        gift_bag = FinishedGood(
            display_name="Holiday Gift Bag",
            slug="holiday-gift-bag",
            assembly_type=AssemblyType.GIFT_BOX,
            inventory_count=0,
        )
        session.add(gift_bag)
        session.flush()

        # Create composition
        comp = Composition.create_unit_composition(
            assembly_id=gift_bag.id,
            finished_unit_id=cookie.id,
            quantity=6,
        )
        session.add(comp)

        # Create assembly target
        target = EventAssemblyTarget(
            event_id=event.id,
            finished_good_id=gift_bag.id,
            target_quantity=50,
        )
        session.add(target)
        session.commit()

        return {
            "event_id": event.id,
            "gift_bag_id": gift_bag.id,
            "cookie_id": cookie.id,
            "recipe_id": cookie_recipe.id,
        }

    def test_full_workflow(self, test_db, full_setup):
        """Test complete planning workflow."""
        session = test_db()
        event_id = full_setup["event_id"]

        # 1. Calculate plan
        plan_result = calculate_plan(event_id, session=session)
        assert plan_result["plan_id"] is not None

        # 2. Check staleness (should be fresh)
        is_stale, reason = check_staleness(event_id, session=session)
        assert is_stale is False

        # 3. Get summary
        summary = get_plan_summary(event_id, session=session)
        assert summary.plan_id == plan_result["plan_id"]
        assert summary.is_stale is False

        # 4. Get checklist
        checklist = get_assembly_checklist(event_id, session=session)
        assert len(checklist) == 1
        assert checklist[0]["target_quantity"] == 50

        # 5. Record confirmation
        confirmation = record_assembly_confirmation(
            full_setup["gift_bag_id"], 5, event_id, session=session
        )
        assert confirmation["quantity_confirmed"] == 5

    def test_workflow_with_multiple_bundles(self, test_db, full_setup):
        """Test workflow with multiple assembly targets."""
        session = test_db()
        event_id = full_setup["event_id"]

        # Add another bundle
        another_bag = FinishedGood(
            display_name="Mini Gift Bag",
            slug="mini-gift-bag",
            assembly_type=AssemblyType.GIFT_BOX,
            inventory_count=0,
        )
        session.add(another_bag)
        session.flush()

        # Add composition
        comp = Composition.create_unit_composition(
            assembly_id=another_bag.id,
            finished_unit_id=full_setup["cookie_id"],
            quantity=3,
        )
        session.add(comp)

        # Add target
        target = EventAssemblyTarget(
            event_id=event_id,
            finished_good_id=another_bag.id,
            target_quantity=30,
        )
        session.add(target)
        session.commit()

        # Calculate plan
        plan_result = calculate_plan(event_id, force_recalculate=True, session=session)

        # 50 bags * 6 cookies + 30 bags * 3 cookies = 390 cookies
        if plan_result["recipe_batches"]:
            rb = plan_result["recipe_batches"][0]
            assert rb["units_needed"] == 390
            assert rb["batches"] == 9  # ceil(390/48)


class TestAggregatedIngredients:
    """Tests for aggregated ingredients in planning snapshots (WP04)."""

    @pytest.fixture
    def ingredients_setup(self, test_db):
        """Create event with recipe that has ingredients."""
        from src.models import Ingredient, RecipeIngredient

        session = test_db()

        # Create event
        event = Event(
            name="Ingredients Test Event",
            event_date=date(2025, 12, 25),
            year=2025,
            output_mode=OutputMode.BUNDLED,
        )
        session.add(event)
        session.flush()

        # Create ingredients
        flour = Ingredient(
            display_name="All-Purpose Flour",
            slug="all-purpose-flour",
            category="Baking",
        )
        sugar = Ingredient(
            display_name="White Sugar",
            slug="white-sugar",
            category="Baking",
        )
        session.add_all([flour, sugar])
        session.flush()

        # Create recipe
        cookie_recipe = Recipe(
            name="Sugar Cookies",
            category="Cookies",
        )
        session.add(cookie_recipe)
        session.flush()

        # Add ingredients to recipe
        ri_flour = RecipeIngredient(
            recipe_id=cookie_recipe.id,
            ingredient_id=flour.id,
            quantity=2.0,
            unit="cups",
        )
        ri_sugar = RecipeIngredient(
            recipe_id=cookie_recipe.id,
            ingredient_id=sugar.id,
            quantity=1.0,
            unit="cups",
        )
        session.add_all([ri_flour, ri_sugar])
        session.flush()

        # Create FinishedUnit
        cookie_unit = FinishedUnit(
            display_name="Sugar Cookie",
            slug="sugar-cookie",
            recipe_id=cookie_recipe.id,
            items_per_batch=48,
            item_unit="cookies",
            inventory_count=0,
        )
        session.add(cookie_unit)
        session.flush()

        # Create FinishedGood (bundle)
        gift_bag = FinishedGood(
            display_name="Holiday Gift Bag",
            slug="holiday-gift-bag",
            assembly_type=AssemblyType.GIFT_BOX,
            inventory_count=0,
        )
        session.add(gift_bag)
        session.flush()

        # Create composition: 6 cookies per bag
        comp = Composition.create_unit_composition(
            assembly_id=gift_bag.id,
            finished_unit_id=cookie_unit.id,
            quantity=6,
        )
        session.add(comp)

        # Create assembly target: 50 bags
        target = EventAssemblyTarget(
            event_id=event.id,
            finished_good_id=gift_bag.id,
            target_quantity=50,
        )
        session.add(target)
        session.commit()

        return {
            "event_id": event.id,
            "recipe_id": cookie_recipe.id,
            "flour_id": flour.id,
            "sugar_id": sugar.id,
        }
