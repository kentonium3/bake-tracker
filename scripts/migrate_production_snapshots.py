#!/usr/bin/env python3
"""
Migration script: Backfill RecipeSnapshots for existing ProductionRuns.

Feature 037: Recipe Template & Snapshot System

This script creates snapshots for historical production runs that were
created before the snapshot system existed. These snapshots use CURRENT
recipe data (best approximation) and are marked with is_backfilled=True.

The UI will display "(approximated)" badge for backfilled snapshots to
indicate the data may not exactly match the original production.

Usage:
    python scripts/migrate_production_snapshots.py --dry-run  # Validate
    python scripts/migrate_production_snapshots.py            # Execute

IMPORTANT: Backup your database before running without --dry-run!

The script is idempotent - running it multiple times is safe.
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.database import session_scope
from src.models import ProductionRun, Recipe, RecipeSnapshot
from src.utils.datetime_utils import utc_now


def migrate_production_snapshots(dry_run: bool = True, session=None) -> dict:
    """
    Backfill snapshots for existing ProductionRuns.

    Args:
        dry_run: If True, validate without modifying data
        session: Optional SQLAlchemy session. If provided, migration will run
            within this session and will NOT open/close its own session.

    Returns:
        dict with migration statistics
    """
    stats = {
        "total_runs": 0,
        "already_migrated": 0,
        "migrated": 0,
        "skipped_no_recipe": 0,
        "errors": []
    }

    def _run(session) -> None:
        # Count already migrated runs
        already_migrated = (
            session.query(ProductionRun)
            .filter(ProductionRun.recipe_snapshot_id.isnot(None))
            .count()
        )
        stats["already_migrated"] = already_migrated
        print(f"Already migrated: {already_migrated} production runs")

        # Find all ProductionRuns without snapshots
        runs = (
            session.query(ProductionRun)
            .filter(ProductionRun.recipe_snapshot_id.is_(None))
            .all()
        )

        stats["total_runs"] = len(runs) + already_migrated
        print(f"Found {len(runs)} production runs without snapshots")

        for run in runs:
            try:
                # Check if recipe still exists
                recipe = session.query(Recipe).filter_by(id=run.recipe_id).first()
                if not recipe:
                    print(f"  SKIP: Run {run.id} - Recipe {run.recipe_id} not found")
                    stats["skipped_no_recipe"] += 1
                    continue

                if dry_run:
                    print(f"  WOULD MIGRATE: Run {run.id} (Recipe: {recipe.name})")
                    stats["migrated"] += 1
                    continue

                # Create backfilled snapshot
                snapshot = _create_backfill_snapshot(run, recipe, session)

                # Update ProductionRun
                run.recipe_snapshot_id = snapshot.id

                print(f"  MIGRATED: Run {run.id} -> Snapshot {snapshot.id}")
                stats["migrated"] += 1

            except Exception as e:
                print(f"  ERROR: Run {run.id} - {e}")
                stats["errors"].append({"run_id": run.id, "error": str(e)})

        if not dry_run and stats["migrated"] > 0:
            session.commit()
            print(f"\nCommitted {stats['migrated']} migrations")
        elif dry_run:
            print(f"\nDRY RUN - No changes made")
        else:
            print(f"\nNo migrations needed")

    if session is not None:
        _run(session)
        return stats

    with session_scope() as session:
        _run(session)

    return stats


def _create_backfill_snapshot(
    run: ProductionRun, recipe: Recipe, session
) -> RecipeSnapshot:
    """Create a backfilled snapshot for a historical production run."""
    # Eagerly load ingredients to avoid lazy loading issues
    _ = recipe.recipe_ingredients
    for ri in recipe.recipe_ingredients:
        _ = ri.ingredient

    # Build recipe_data from CURRENT recipe state
    recipe_data = {
        "name": recipe.name,
        "category": recipe.category,
        "source": recipe.source,
        "yield_quantity": recipe.yield_quantity,
        "yield_unit": recipe.yield_unit,
        "yield_description": recipe.yield_description,
        "estimated_time_minutes": recipe.estimated_time_minutes,
        "notes": recipe.notes,
        "variant_name": getattr(recipe, "variant_name", None),
        "is_production_ready": getattr(recipe, "is_production_ready", False),
    }

    # Build ingredients_data from CURRENT recipe state
    ingredients_data = []
    for ri in recipe.recipe_ingredients:
        ing_data = {
            "ingredient_id": ri.ingredient_id,
            "ingredient_name": ri.ingredient.display_name if ri.ingredient else "Unknown",
            "ingredient_slug": ri.ingredient.slug if ri.ingredient else "",
            "quantity": float(ri.quantity),
            "unit": ri.unit,
            "notes": ri.notes,
        }
        ingredients_data.append(ing_data)

    # Create snapshot with is_backfilled=True
    # Use production date if available for snapshot_date
    snapshot_date = run.produced_at if run.produced_at else utc_now()

    snapshot = RecipeSnapshot(
        recipe_id=recipe.id,
        production_run_id=run.id,
        scale_factor=1.0,  # Historical runs didn't have scale_factor
        snapshot_date=snapshot_date,
        recipe_data=json.dumps(recipe_data),
        ingredients_data=json.dumps(ingredients_data),
        is_backfilled=True,  # Mark as backfilled
    )

    session.add(snapshot)
    session.flush()

    return snapshot


def verify_migration(session) -> dict:
    """Verify migration completed successfully."""
    unmigrated = (
        session.query(ProductionRun)
        .filter(ProductionRun.recipe_snapshot_id.is_(None))
        .filter(ProductionRun.recipe_id.isnot(None))
        .count()
    )

    backfilled = (
        session.query(RecipeSnapshot)
        .filter(RecipeSnapshot.is_backfilled == True)  # noqa: E712
        .count()
    )

    total_snapshots = session.query(RecipeSnapshot).count()

    return {
        "unmigrated_runs": unmigrated,
        "backfilled_snapshots": backfilled,
        "total_snapshots": total_snapshots,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Backfill RecipeSnapshots for existing ProductionRuns"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate without modifying data",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Only verify migration status (no changes)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Recipe Snapshot Migration (Feature 037)")
    print("=" * 60)

    if args.verify:
        print("\nVerifying migration status...")
        with session_scope() as session:
            status = verify_migration(session)
        print(f"Unmigrated runs: {status['unmigrated_runs']}")
        print(f"Backfilled snapshots: {status['backfilled_snapshots']}")
        print(f"Total snapshots: {status['total_snapshots']}")
        return

    if not args.dry_run:
        print("\nWARNING: This will modify the database!")
        print("Recommendation: Backup your database first.")
        try:
            response = input("Continue? [y/N]: ")
        except EOFError:
            # Non-interactive mode
            print("Non-interactive mode detected. Use --dry-run to validate first.")
            return
        if response.lower() != "y":
            print("Aborted.")
            return

    stats = migrate_production_snapshots(dry_run=args.dry_run)

    print("\n" + "=" * 60)
    print("Migration Summary")
    print("=" * 60)
    print(f"Total runs in database: {stats['total_runs']}")
    print(f"Already migrated: {stats['already_migrated']}")
    print(f"{'Would migrate' if args.dry_run else 'Migrated'}: {stats['migrated']}")
    print(f"Skipped (recipe deleted): {stats['skipped_no_recipe']}")
    print(f"Errors: {len(stats['errors'])}")

    if stats["errors"]:
        print("\nErrors:")
        for err in stats["errors"]:
            print(f"  Run {err['run_id']}: {err['error']}")

    if not args.dry_run and stats["migrated"] > 0:
        print("\nVerifying migration...")
        with session_scope() as session:
            status = verify_migration(session)
        if status["unmigrated_runs"] == 0:
            print("SUCCESS: All production runs now have snapshots")
        else:
            print(f"WARNING: {status['unmigrated_runs']} runs still unmigrated")


if __name__ == "__main__":
    main()
