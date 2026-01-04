"""
Tests for the production snapshot migration script.

Feature 037: Recipe Template & Snapshot System
"""

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock

from src.models import Recipe, ProductionRun, RecipeSnapshot, Ingredient, RecipeIngredient, FinishedUnit
from src.services.database import session_scope
from src.utils.datetime_utils import utc_now


def create_finished_unit(session, recipe):
    """Helper to create a FinishedUnit for tests."""
    fu = FinishedUnit(
        display_name=f"{recipe.name} Unit",
        recipe_id=recipe.id,
        slug=f"{recipe.name.lower().replace(' ', '-')}-unit",
        items_per_batch=recipe.yield_quantity,
    )
    session.add(fu)
    session.flush()
    return fu

# Import the migration functions
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from scripts.migrate_production_snapshots import (
    migrate_production_snapshots,
    _create_backfill_snapshot,
    verify_migration,
)


class TestMigrateProductionSnapshots:
    """Tests for migration script functionality."""

    def test_dry_run_reports_counts(self, test_db):
        """Dry run should report what would be migrated without changing data."""
        session = test_db()

        # Create a recipe
        recipe = Recipe(
            name="Test Recipe",
            category="Test",
            yield_quantity=12,
            yield_unit="cookies",
        )
        session.add(recipe)
        session.flush()

        # Create finished unit for the recipe
        fu = create_finished_unit(session, recipe)

        # Create a production run without snapshot
        run = ProductionRun(
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            num_batches=1,
            expected_yield=12,
            actual_yield=12,
            produced_at=utc_now(),
        )
        session.add(run)
        session.commit()

        # Verify run has no snapshot
        assert run.recipe_snapshot_id is None

        # Run dry-run migration (uses the patched session from test_db)
        stats = migrate_production_snapshots(dry_run=True)

        # Should report one run to migrate
        assert stats["migrated"] == 1
        assert stats["errors"] == []

        # Run should still have no snapshot (dry run)
        session.refresh(run)
        assert run.recipe_snapshot_id is None

    def test_actual_migration_creates_snapshots(self, test_db):
        """Actual migration should create backfilled snapshots."""
        session = test_db()

        # Create a recipe with ingredients
        recipe = Recipe(
            name="Chocolate Chip Cookies",
            category="Cookies",
            yield_quantity=24,
            yield_unit="cookies",
        )
        session.add(recipe)
        session.flush()

        # Create finished unit for the recipe
        fu = create_finished_unit(session, recipe)

        # Create an ingredient
        ingredient = Ingredient(
            display_name="All-Purpose Flour",
            slug="all-purpose-flour",
        )
        session.add(ingredient)
        session.flush()

        # Link ingredient to recipe
        ri = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            quantity=Decimal("2.5"),
            unit="cups",
        )
        session.add(ri)

        # Create production runs without snapshots
        run1 = ProductionRun(
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            num_batches=2,
            expected_yield=48,
            actual_yield=45,
            produced_at=utc_now(),
        )
        run2 = ProductionRun(
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            num_batches=1,
            expected_yield=24,
            actual_yield=24,
            produced_at=utc_now(),
        )
        session.add(run1)
        session.add(run2)
        session.commit()

        # Run actual migration (uses patched session from test_db)
        stats = migrate_production_snapshots(dry_run=False)

        # Should migrate both runs
        assert stats["migrated"] == 2
        assert stats["errors"] == []

        # Verify snapshots created
        session.refresh(run1)
        session.refresh(run2)
        assert run1.recipe_snapshot_id is not None
        assert run2.recipe_snapshot_id is not None

        # Verify snapshots are marked as backfilled
        snapshot1 = session.query(RecipeSnapshot).filter_by(id=run1.recipe_snapshot_id).first()
        snapshot2 = session.query(RecipeSnapshot).filter_by(id=run2.recipe_snapshot_id).first()
        assert snapshot1.is_backfilled is True
        assert snapshot2.is_backfilled is True

        # Verify snapshot data
        assert snapshot1.scale_factor == 1.0  # Default for historical runs
        recipe_data = snapshot1.get_recipe_data()
        assert recipe_data["name"] == "Chocolate Chip Cookies"

        ingredients_data = snapshot1.get_ingredients_data()
        assert len(ingredients_data) == 1
        assert ingredients_data[0]["ingredient_slug"] == "all-purpose-flour"
        assert ingredients_data[0]["quantity"] == 2.5

    def test_skips_deleted_recipes(self, test_db):
        """Migration should skip runs where recipe was deleted."""
        session = test_db()

        # Create a dummy recipe first to get a finished unit
        dummy_recipe = Recipe(
            name="Dummy Recipe",
            category="Test",
            yield_quantity=12,
            yield_unit="each",
        )
        session.add(dummy_recipe)
        session.flush()
        fu = create_finished_unit(session, dummy_recipe)

        # Create a production run referencing non-existent recipe
        # (after we delete the recipe or use non-existent ID)
        run = ProductionRun(
            recipe_id=99999,  # Non-existent recipe
            finished_unit_id=fu.id,
            num_batches=1,
            expected_yield=12,
            actual_yield=12,
            produced_at=utc_now(),
        )
        session.add(run)
        session.commit()

        # Run migration (uses patched session from test_db)
        stats = migrate_production_snapshots(dry_run=False)

        # Should skip the run
        assert stats["skipped_no_recipe"] == 1
        assert stats["migrated"] == 0

    def test_idempotent_migration(self, test_db):
        """Running migration twice should not create duplicate snapshots."""
        session = test_db()

        # Create recipe and run
        recipe = Recipe(
            name="Test Recipe",
            category="Test",
            yield_quantity=12,
            yield_unit="each",
        )
        session.add(recipe)
        session.flush()

        # Create finished unit for the recipe
        fu = create_finished_unit(session, recipe)

        run = ProductionRun(
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            num_batches=1,
            expected_yield=12,
            actual_yield=12,
            produced_at=utc_now(),
        )
        session.add(run)
        session.commit()

        # Run migration first time
        stats1 = migrate_production_snapshots(dry_run=False)
        assert stats1["migrated"] == 1

        # Run migration second time
        stats2 = migrate_production_snapshots(dry_run=False)

        # Should report already migrated
        assert stats2["already_migrated"] == 1
        assert stats2["migrated"] == 0

        # Should only have one snapshot
        snapshot_count = session.query(RecipeSnapshot).count()
        assert snapshot_count == 1


class TestCreateBackfillSnapshot:
    """Tests for the _create_backfill_snapshot helper."""

    def test_snapshot_uses_production_date(self, test_db):
        """Backfilled snapshot should use production run's date."""
        from datetime import datetime, timezone
        session = test_db()

        # Create recipe
        recipe = Recipe(
            name="Test Recipe",
            category="Test",
            yield_quantity=12,
            yield_unit="each",
        )
        session.add(recipe)
        session.flush()

        # Create finished unit for the recipe
        fu = create_finished_unit(session, recipe)

        # Create run with specific date
        production_date = datetime(2024, 6, 15, 10, 30, tzinfo=timezone.utc)
        run = ProductionRun(
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            num_batches=1,
            expected_yield=12,
            actual_yield=12,
            produced_at=production_date,
        )
        session.add(run)
        session.flush()

        # Create backfill snapshot
        snapshot = _create_backfill_snapshot(run, recipe, session)

        # Snapshot date should match production date
        assert snapshot.snapshot_date == production_date
        assert snapshot.is_backfilled is True

    def test_snapshot_captures_recipe_data(self, test_db):
        """Backfilled snapshot should capture current recipe state."""
        session = test_db()

        # Create detailed recipe
        recipe = Recipe(
            name="Grandma's Cookies",
            category="Cookies",
            source="Family Recipe",
            yield_quantity=36,
            yield_unit="cookies",
            yield_description="About 3 dozen",
            estimated_time_minutes=45,
            notes="Use cold butter",
        )
        session.add(recipe)
        session.flush()

        # Create finished unit for the recipe
        fu = create_finished_unit(session, recipe)

        # Create ingredient
        flour = Ingredient(display_name="Flour", slug="flour")
        session.add(flour)
        session.flush()

        # Link to recipe
        ri = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=flour.id,
            quantity=Decimal("3.0"),
            unit="cups",
            notes="sifted",
        )
        session.add(ri)

        run = ProductionRun(
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            num_batches=1,
            expected_yield=36,
            actual_yield=35,
            produced_at=utc_now(),
        )
        session.add(run)
        session.flush()

        # Create snapshot
        snapshot = _create_backfill_snapshot(run, recipe, session)

        # Verify recipe data captured
        recipe_data = snapshot.get_recipe_data()
        assert recipe_data["name"] == "Grandma's Cookies"
        assert recipe_data["category"] == "Cookies"
        assert recipe_data["source"] == "Family Recipe"
        assert recipe_data["yield_quantity"] == 36
        assert recipe_data["notes"] == "Use cold butter"

        # Verify ingredients captured
        ingredients_data = snapshot.get_ingredients_data()
        assert len(ingredients_data) == 1
        assert ingredients_data[0]["ingredient_name"] == "Flour"
        assert ingredients_data[0]["quantity"] == 3.0
        assert ingredients_data[0]["unit"] == "cups"
        assert ingredients_data[0]["notes"] == "sifted"


class TestVerifyMigration:
    """Tests for the verify_migration function."""

    def test_verify_reports_correct_counts(self, test_db):
        """Verify should report accurate migration status."""
        session = test_db()

        # Create recipe
        recipe = Recipe(
            name="Test",
            category="Test",
            yield_quantity=12,
            yield_unit="each",
        )
        session.add(recipe)
        session.flush()

        # Create finished unit for the recipe
        fu = create_finished_unit(session, recipe)

        # Create migrated run with snapshot
        snapshot = RecipeSnapshot(
            recipe_id=recipe.id,
            production_run_id=None,
            scale_factor=1.0,
            snapshot_date=utc_now(),
            recipe_data="{}",
            ingredients_data="[]",
            is_backfilled=True,
        )
        session.add(snapshot)
        session.flush()

        migrated_run = ProductionRun(
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            num_batches=1,
            expected_yield=12,
            actual_yield=12,
            recipe_snapshot_id=snapshot.id,
        )
        session.add(migrated_run)

        # Create unmigrated run
        unmigrated_run = ProductionRun(
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            num_batches=1,
            expected_yield=12,
            actual_yield=12,
            recipe_snapshot_id=None,
        )
        session.add(unmigrated_run)
        session.commit()

        # Verify
        status = verify_migration(session)

        assert status["unmigrated_runs"] == 1
        assert status["backfilled_snapshots"] == 1
        assert status["total_snapshots"] == 1
