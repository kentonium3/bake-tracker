"""
Integration tests for F065 Production Plan Snapshot Refactor.

Tests the complete workflow from plan creation through production/assembly,
verifying snapshot reuse and immutability.

Covers:
- T040: Plan -> Production workflow with snapshot reuse (SC-002)
- T041: Plan -> Assembly workflow with snapshot reuse (SC-003)
- T042: Backward compatibility for legacy events (SC-004)
- SC-001: Plan immutability after definition changes

Reference: kitty-specs/065-production-plan-snapshot-refactor/spec.md
"""

import pytest
from datetime import date, datetime
from decimal import Decimal

from src.models import (
    Event,
    EventAssemblyTarget,
    EventProductionTarget,
    ProductionPlanSnapshot,
    ProductionRun,
    AssemblyRun,
    Recipe,
    RecipeIngredient,
    FinishedGood,
    FinishedUnit,
    Composition,
    Ingredient,
    Product,
    InventoryItem,
)
from src.models.event import OutputMode
from src.models.assembly_type import AssemblyType
from src.services.planning import (
    create_plan,
    get_plan_calculation,
)
from src.services.batch_production_service import record_batch_production
from src.services.assembly_service import record_assembly


class TestPlanProductionSnapshotReuse:
    """T040: Integration test for plan -> production -> snapshot reuse."""

    @pytest.fixture
    def production_workflow_setup(self, test_db):
        """Create event with production targets for workflow testing."""
        session = test_db()

        # Create event
        event = Event(
            name="Holiday Baking 2025",
            event_date=date(2025, 12, 25),
            year=2025,
            output_mode=OutputMode.BULK_COUNT,
        )
        session.add(event)
        session.flush()

        # Create ingredient with density for unit conversion
        flour = Ingredient(
            display_name="All Purpose Flour",
            slug="all-purpose-flour",
            category="Flour",
            # 1 cup = 120g (approximately), used for cup <-> lb conversion
            density_volume_value=Decimal("1.0"),
            density_volume_unit="cup",
            density_weight_value=Decimal("120.0"),
            density_weight_unit="g",
        )
        session.add(flour)
        session.flush()

        # Create product for inventory (in lbs)
        flour_product = Product(
            brand="Test Brand",
            ingredient_id=flour.id,
            package_size="5 lb bag",
            package_unit="lb",
            package_unit_quantity=Decimal("5.0"),
            preferred=True,
        )
        session.add(flour_product)
        session.flush()

        # Add inventory (enough for production)
        inventory = InventoryItem(
            product_id=flour_product.id,
            quantity=10.0,  # 10 lbs
            unit_cost=Decimal("1.00"),
            purchase_date=datetime(2024, 1, 1),
        )
        session.add(inventory)
        session.flush()

        # Create recipe
        cookie_recipe = Recipe(
            name="Sugar Cookies",
            category="Cookies",
        )
        session.add(cookie_recipe)
        session.flush()

        # Add ingredient to recipe (in cups - will need conversion from lb inventory)
        recipe_ingredient = RecipeIngredient(
            recipe_id=cookie_recipe.id,
            ingredient_id=flour.id,
            quantity=Decimal("2.0"),
            unit="cup",
        )
        session.add(recipe_ingredient)
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

        # Create production target
        target = EventProductionTarget(
            event_id=event.id,
            recipe_id=cookie_recipe.id,
            target_batches=10,
        )
        session.add(target)
        session.commit()

        return {
            "session": session,
            "event_id": event.id,
            "recipe_id": cookie_recipe.id,
            "finished_unit_id": cookie_unit.id,
            "target": target,
        }

    def test_planning_production_workflow_snapshot_reuse(
        self, test_db, production_workflow_setup
    ):
        """Integration test: plan creation -> production -> snapshot reuse.

        Verifies SC-002: Production runs for planned events reference
        the same snapshot as the plan (100% snapshot reuse).
        """
        session = production_workflow_setup["session"]
        event_id = production_workflow_setup["event_id"]
        recipe_id = production_workflow_setup["recipe_id"]
        finished_unit_id = production_workflow_setup["finished_unit_id"]
        target = production_workflow_setup["target"]

        # Act 1: Create plan (creates snapshots)
        plan_result = create_plan(event_id, session=session)
        assert plan_result["success"]
        assert plan_result["recipe_snapshots_created"] == 1

        # Verify target has snapshot linked
        session.refresh(target)
        planning_snapshot_id = target.recipe_snapshot_id
        assert planning_snapshot_id is not None

        # Act 2: Record production for the planned event
        production_result = record_batch_production(
            recipe_id=recipe_id,
            finished_unit_id=finished_unit_id,
            num_batches=2,
            actual_yield=96,  # 2 batches * 48 cookies
            event_id=event_id,
            session=session,
        )

        # Assert: Same snapshot reused
        assert production_result["snapshot_id"] == planning_snapshot_id
        assert production_result["snapshot_reused"] is True

        # Verify production run references planning snapshot
        production_run = session.get(
            ProductionRun, production_result["production_run_id"]
        )
        assert production_run.recipe_snapshot_id == planning_snapshot_id

    def test_plan_immutable_after_recipe_change(
        self, test_db, production_workflow_setup
    ):
        """Integration test: modifying recipe doesn't affect plan.

        Verifies SC-001: Event plans remain stable after definition changes.
        """
        session = production_workflow_setup["session"]
        event_id = production_workflow_setup["event_id"]
        recipe_id = production_workflow_setup["recipe_id"]

        # Create plan
        create_plan(event_id, session=session)

        # Get plan calculation (captures original recipe name)
        calculation_before = get_plan_calculation(event_id, session=session)
        original_name = calculation_before["recipe_batches"][0]["recipe_name"]
        assert original_name == "Sugar Cookies"

        # Modify the recipe
        recipe = session.get(Recipe, recipe_id)
        recipe.name = "Changed Name"
        session.flush()

        # Get plan calculation again
        calculation_after = get_plan_calculation(event_id, session=session)
        name_in_plan = calculation_after["recipe_batches"][0]["recipe_name"]

        # Assert: Plan still shows original name (from snapshot)
        assert name_in_plan == original_name
        assert name_in_plan != "Changed Name"


class TestPlanAssemblySnapshotReuse:
    """T041: Integration test for plan -> assembly -> snapshot reuse."""

    @pytest.fixture
    def assembly_workflow_setup(self, test_db):
        """Create event with assembly targets for workflow testing."""
        session = test_db()

        # Create event
        event = Event(
            name="Holiday Gifts 2025",
            event_date=date(2025, 12, 25),
            year=2025,
            output_mode=OutputMode.BUNDLED,
        )
        session.add(event)
        session.flush()

        # Create recipe for cookies
        cookie_recipe = Recipe(
            name="Sugar Cookies",
            category="Cookies",
        )
        session.add(cookie_recipe)
        session.flush()

        # Create FinishedUnit
        cookie_unit = FinishedUnit(
            display_name="Sugar Cookie",
            slug="sugar-cookie",
            recipe_id=cookie_recipe.id,
            items_per_batch=48,
            item_unit="cookies",
            inventory_count=100,  # Pre-stock inventory
        )
        session.add(cookie_unit)
        session.flush()

        # Create FinishedGood (bundle)
        gift_box = FinishedGood(
            display_name="Holiday Gift Box",
            slug="holiday-gift-box",
            assembly_type=AssemblyType.GIFT_BOX,
            inventory_count=0,
        )
        session.add(gift_box)
        session.flush()

        # Create composition: 6 cookies per box
        comp = Composition.create_unit_composition(
            assembly_id=gift_box.id,
            finished_unit_id=cookie_unit.id,
            quantity=6,
        )
        session.add(comp)
        session.flush()

        # Create assembly target
        target = EventAssemblyTarget(
            event_id=event.id,
            finished_good_id=gift_box.id,
            target_quantity=10,
        )
        session.add(target)
        session.commit()

        return {
            "session": session,
            "event_id": event.id,
            "finished_good_id": gift_box.id,
            "finished_unit_id": cookie_unit.id,
            "target": target,
        }

    def test_planning_assembly_workflow_snapshot_reuse(
        self, test_db, assembly_workflow_setup
    ):
        """Integration test: plan creation -> assembly -> snapshot reuse.

        Verifies SC-003: Assembly runs for planned events reference
        the same snapshot as the plan (100% snapshot reuse).
        """
        session = assembly_workflow_setup["session"]
        event_id = assembly_workflow_setup["event_id"]
        finished_good_id = assembly_workflow_setup["finished_good_id"]
        target = assembly_workflow_setup["target"]

        # Act 1: Create plan (creates snapshots)
        plan_result = create_plan(event_id, session=session)
        assert plan_result["success"]
        assert plan_result["finished_good_snapshots_created"] == 1

        # Verify target has snapshot linked
        session.refresh(target)
        planning_snapshot_id = target.finished_good_snapshot_id
        assert planning_snapshot_id is not None

        # Act 2: Record assembly for the planned event
        assembly_result = record_assembly(
            finished_good_id=finished_good_id,
            quantity=5,
            event_id=event_id,
            session=session,
        )

        # Assert: Same snapshot reused
        assert assembly_result["finished_good_snapshot_id"] == planning_snapshot_id
        assert assembly_result["snapshot_reused"] is True

        # Verify assembly run references planning snapshot
        assembly_run = session.get(AssemblyRun, assembly_result["assembly_run_id"])
        assert assembly_run.finished_good_snapshot_id == planning_snapshot_id


class TestBackwardCompatibility:
    """T042: Backward compatibility tests for legacy events without planning snapshots."""

    @pytest.fixture
    def legacy_production_setup(self, test_db):
        """Create recipe setup without event/plan (legacy ad-hoc production)."""
        session = test_db()

        # Create ingredient with density for unit conversion
        flour = Ingredient(
            display_name="All Purpose Flour",
            slug="all-purpose-flour",
            category="Flour",
            density_volume_value=Decimal("1.0"),
            density_volume_unit="cup",
            density_weight_value=Decimal("120.0"),
            density_weight_unit="g",
        )
        session.add(flour)
        session.flush()

        # Create product for inventory
        flour_product = Product(
            brand="Test Brand",
            ingredient_id=flour.id,
            package_size="5 lb bag",
            package_unit="lb",
            package_unit_quantity=Decimal("5.0"),
            preferred=True,
        )
        session.add(flour_product)
        session.flush()

        # Add inventory
        inventory = InventoryItem(
            product_id=flour_product.id,
            quantity=10.0,
            unit_cost=Decimal("1.00"),
            purchase_date=datetime(2024, 1, 1),
        )
        session.add(inventory)
        session.flush()

        # Create recipe
        cookie_recipe = Recipe(
            name="Sugar Cookies",
            category="Cookies",
        )
        session.add(cookie_recipe)
        session.flush()

        # Add ingredient to recipe
        recipe_ingredient = RecipeIngredient(
            recipe_id=cookie_recipe.id,
            ingredient_id=flour.id,
            quantity=Decimal("2.0"),
            unit="cup",
        )
        session.add(recipe_ingredient)
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
        session.commit()

        return {
            "session": session,
            "recipe_id": cookie_recipe.id,
            "finished_unit_id": cookie_unit.id,
        }

    @pytest.fixture
    def legacy_assembly_setup(self, test_db):
        """Create finished good setup without event/plan (legacy ad-hoc assembly)."""
        session = test_db()

        # Create recipe for cookies
        cookie_recipe = Recipe(
            name="Sugar Cookies",
            category="Cookies",
        )
        session.add(cookie_recipe)
        session.flush()

        # Create FinishedUnit with inventory
        cookie_unit = FinishedUnit(
            display_name="Sugar Cookie",
            slug="sugar-cookie",
            recipe_id=cookie_recipe.id,
            items_per_batch=48,
            item_unit="cookies",
            inventory_count=100,
        )
        session.add(cookie_unit)
        session.flush()

        # Create FinishedGood
        gift_box = FinishedGood(
            display_name="Holiday Gift Box",
            slug="holiday-gift-box",
            assembly_type=AssemblyType.GIFT_BOX,
            inventory_count=0,
        )
        session.add(gift_box)
        session.flush()

        # Create composition
        comp = Composition.create_unit_composition(
            assembly_id=gift_box.id,
            finished_unit_id=cookie_unit.id,
            quantity=6,
        )
        session.add(comp)
        session.commit()

        return {
            "session": session,
            "finished_good_id": gift_box.id,
        }

    @pytest.fixture
    def legacy_event_no_snapshots(self, test_db, legacy_production_setup):
        """Create event with targets but NO planning snapshots (legacy state)."""
        session = legacy_production_setup["session"]
        recipe_id = legacy_production_setup["recipe_id"]

        # Create event
        event = Event(
            name="Legacy Event",
            event_date=date(2025, 12, 25),
            year=2025,
            output_mode=OutputMode.BULK_COUNT,
        )
        session.add(event)
        session.flush()

        # Create production target WITHOUT planning snapshot (legacy state)
        target = EventProductionTarget(
            event_id=event.id,
            recipe_id=recipe_id,
            target_batches=5,
            recipe_snapshot_id=None,  # Legacy: no planning snapshot
        )
        session.add(target)
        session.commit()

        return {
            "session": session,
            "event_id": event.id,
            "recipe_id": recipe_id,
            "finished_unit_id": legacy_production_setup["finished_unit_id"],
        }

    def test_legacy_production_without_plan_creates_snapshot(
        self, test_db, legacy_production_setup
    ):
        """Backward compatibility: production without plan creates new snapshot.

        Verifies SC-004: Legacy events without planning snapshots
        continue to function.
        """
        session = legacy_production_setup["session"]
        recipe_id = legacy_production_setup["recipe_id"]
        finished_unit_id = legacy_production_setup["finished_unit_id"]

        # Act: Record production without event (ad-hoc production)
        result = record_batch_production(
            recipe_id=recipe_id,
            finished_unit_id=finished_unit_id,
            num_batches=1,
            actual_yield=48,
            event_id=None,  # No event (ad-hoc production)
            session=session,
        )

        # Assert: New snapshot created
        assert result["snapshot_id"] is not None
        assert result["snapshot_reused"] is False

    def test_legacy_event_without_snapshots(self, test_db, legacy_event_no_snapshots):
        """Backward compatibility: event with targets but no snapshots.

        Simulates events created before F065 (no planning snapshots on targets).
        """
        session = legacy_event_no_snapshots["session"]
        event_id = legacy_event_no_snapshots["event_id"]
        recipe_id = legacy_event_no_snapshots["recipe_id"]
        finished_unit_id = legacy_event_no_snapshots["finished_unit_id"]

        # Act: Record production for legacy event
        result = record_batch_production(
            recipe_id=recipe_id,
            finished_unit_id=finished_unit_id,
            num_batches=2,
            actual_yield=96,
            event_id=event_id,
            session=session,
        )

        # Assert: New snapshot created (backward compatibility)
        assert result["snapshot_id"] is not None
        assert result["snapshot_reused"] is False

    def test_legacy_assembly_without_plan_creates_snapshot(
        self, test_db, legacy_assembly_setup
    ):
        """Backward compatibility: assembly without plan creates new snapshot."""
        session = legacy_assembly_setup["session"]
        finished_good_id = legacy_assembly_setup["finished_good_id"]

        result = record_assembly(
            finished_good_id=finished_good_id,
            quantity=5,
            event_id=None,  # No event
            session=session,
        )

        assert result["finished_good_snapshot_id"] is not None
        assert result["snapshot_reused"] is False


class TestMultipleProductionRuns:
    """Test multiple production runs reuse the same planning snapshot."""

    @pytest.fixture
    def multi_production_setup(self, test_db):
        """Create event with inventory for multiple production runs."""
        session = test_db()

        # Create event
        event = Event(
            name="Multi Production Event",
            event_date=date(2025, 12, 25),
            year=2025,
            output_mode=OutputMode.BULK_COUNT,
        )
        session.add(event)
        session.flush()

        # Create ingredient with density for unit conversion
        flour = Ingredient(
            display_name="All Purpose Flour",
            slug="all-purpose-flour",
            category="Flour",
            density_volume_value=Decimal("1.0"),
            density_volume_unit="cup",
            density_weight_value=Decimal("120.0"),
            density_weight_unit="g",
        )
        session.add(flour)
        session.flush()

        # Create product for inventory
        flour_product = Product(
            brand="Test Brand",
            ingredient_id=flour.id,
            package_size="5 lb bag",
            package_unit="lb",
            package_unit_quantity=Decimal("5.0"),
            preferred=True,
        )
        session.add(flour_product)
        session.flush()

        # Add lots of inventory for multiple production runs
        inventory = InventoryItem(
            product_id=flour_product.id,
            quantity=50.0,
            unit_cost=Decimal("1.00"),
            purchase_date=datetime(2024, 1, 1),
        )
        session.add(inventory)
        session.flush()

        # Create recipe
        cookie_recipe = Recipe(
            name="Sugar Cookies",
            category="Cookies",
        )
        session.add(cookie_recipe)
        session.flush()

        # Add ingredient to recipe
        recipe_ingredient = RecipeIngredient(
            recipe_id=cookie_recipe.id,
            ingredient_id=flour.id,
            quantity=Decimal("2.0"),
            unit="cup",
        )
        session.add(recipe_ingredient)
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

        # Create production target
        target = EventProductionTarget(
            event_id=event.id,
            recipe_id=cookie_recipe.id,
            target_batches=10,
        )
        session.add(target)
        session.commit()

        return {
            "session": session,
            "event_id": event.id,
            "recipe_id": cookie_recipe.id,
            "finished_unit_id": cookie_unit.id,
        }

    def test_multiple_production_runs_same_snapshot(
        self, test_db, multi_production_setup
    ):
        """Multiple production runs for same event reuse the same snapshot.

        Verifies that once a plan is created, all subsequent production
        runs use the same snapshot (100% reuse).
        """
        session = multi_production_setup["session"]
        event_id = multi_production_setup["event_id"]
        recipe_id = multi_production_setup["recipe_id"]
        finished_unit_id = multi_production_setup["finished_unit_id"]

        # Create plan
        plan_result = create_plan(event_id, session=session)
        assert plan_result["success"]

        # Get the planning snapshot ID
        target = (
            session.query(EventProductionTarget)
            .filter_by(event_id=event_id, recipe_id=recipe_id)
            .first()
        )
        planning_snapshot_id = target.recipe_snapshot_id

        # Record first production run
        result1 = record_batch_production(
            recipe_id=recipe_id,
            finished_unit_id=finished_unit_id,
            num_batches=2,
            actual_yield=96,
            event_id=event_id,
            session=session,
        )
        assert result1["snapshot_id"] == planning_snapshot_id
        assert result1["snapshot_reused"] is True

        # Record second production run
        result2 = record_batch_production(
            recipe_id=recipe_id,
            finished_unit_id=finished_unit_id,
            num_batches=3,
            actual_yield=144,
            event_id=event_id,
            session=session,
        )
        assert result2["snapshot_id"] == planning_snapshot_id
        assert result2["snapshot_reused"] is True

        # Record third production run
        result3 = record_batch_production(
            recipe_id=recipe_id,
            finished_unit_id=finished_unit_id,
            num_batches=1,
            actual_yield=48,
            event_id=event_id,
            session=session,
        )
        assert result3["snapshot_id"] == planning_snapshot_id
        assert result3["snapshot_reused"] is True

        # All three runs should reference the same snapshot
        assert result1["snapshot_id"] == result2["snapshot_id"] == result3["snapshot_id"]
