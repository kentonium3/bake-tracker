---
work_package_id: "WP04"
subtasks:
  - "T014"
  - "T015"
  - "T016"
  - "T017"
title: "Migration Script"
phase: "Phase 1 - Core Snapshot System"
lane: "doing"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-03T06:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - Migration Script

## Objectives & Success Criteria

Backfill snapshots for existing ProductionRuns with is_backfilled=True flag.

**Success Criteria**:
- All existing ProductionRuns with recipe_id get snapshots created
- Backfilled snapshots marked with is_backfilled=True
- ProductionRun.recipe_snapshot_id populated
- Dry-run mode validates without modifying data
- Migration script idempotent (can run multiple times safely)

## Context & Constraints

**Key Decision** (from research.md):
- Backfill with is_backfilled flag
- Use current recipe data (best approximation for historical runs)
- UI will show "(approximated)" badge for backfilled snapshots

**Constraints**:
- Must handle deleted recipes gracefully (skip with warning)
- Must not re-migrate already-migrated runs
- Support --dry-run for validation
- Backup recommendation before running

## Subtasks & Detailed Guidance

### Subtask T014 - Create Migration Script

**Purpose**: Backfill snapshots for all existing ProductionRuns.

**File**: `scripts/migrate_production_snapshots.py`

**Implementation**:
```python
#!/usr/bin/env python3
"""
Migration script: Backfill RecipeSnapshots for existing ProductionRuns.

This script creates snapshots for historical production runs that were
created before the snapshot system existed. These snapshots use CURRENT
recipe data (best approximation) and are marked with is_backfilled=True.

Usage:
    python scripts/migrate_production_snapshots.py --dry-run  # Validate
    python scripts/migrate_production_snapshots.py            # Execute

IMPORTANT: Backup your database before running without --dry-run!
"""

import argparse
import json
import sys
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, ".")

from src.utils.db import session_scope
from src.models import ProductionRun, Recipe, RecipeSnapshot
from src.utils.datetime_utils import utc_now


def migrate_production_snapshots(dry_run: bool = True) -> dict:
    """
    Backfill snapshots for existing ProductionRuns.

    Args:
        dry_run: If True, validate without modifying data

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

    with session_scope() as session:
        # Find all ProductionRuns without snapshots
        runs = (
            session.query(ProductionRun)
            .filter(ProductionRun.recipe_snapshot_id.is_(None))
            .all()
        )

        stats["total_runs"] = len(runs)
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

        if not dry_run:
            session.commit()
            print(f"\nCommitted {stats['migrated']} migrations")
        else:
            print(f"\nDRY RUN - No changes made")

    return stats


def _create_backfill_snapshot(run: ProductionRun, recipe: Recipe, session) -> RecipeSnapshot:
    """Create a backfilled snapshot for a historical production run."""
    # Eagerly load ingredients
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
    snapshot = RecipeSnapshot(
        recipe_id=recipe.id,
        production_run_id=run.id,
        scale_factor=1.0,  # Historical runs didn't have scale_factor
        snapshot_date=run.produced_at or utc_now(),  # Use production date if available
        recipe_data=json.dumps(recipe_data),
        ingredients_data=json.dumps(ingredients_data),
        is_backfilled=True  # Mark as backfilled
    )

    session.add(snapshot)
    session.flush()

    return snapshot


def main():
    parser = argparse.ArgumentParser(
        description="Backfill RecipeSnapshots for existing ProductionRuns"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate without modifying data"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Recipe Snapshot Migration")
    print("=" * 60)

    if not args.dry_run:
        print("\nWARNING: This will modify the database!")
        print("Recommendation: Backup your database first.")
        response = input("Continue? [y/N]: ")
        if response.lower() != "y":
            print("Aborted.")
            return

    stats = migrate_production_snapshots(dry_run=args.dry_run)

    print("\n" + "=" * 60)
    print("Migration Summary")
    print("=" * 60)
    print(f"Total runs processed: {stats['total_runs']}")
    print(f"Already migrated: {stats['already_migrated']}")
    print(f"{'Would migrate' if args.dry_run else 'Migrated'}: {stats['migrated']}")
    print(f"Skipped (no recipe): {stats['skipped_no_recipe']}")
    print(f"Errors: {len(stats['errors'])}")

    if stats["errors"]:
        print("\nErrors:")
        for err in stats["errors"]:
            print(f"  Run {err['run_id']}: {err['error']}")


if __name__ == "__main__":
    main()
```

---

### Subtask T015 - Handle is_backfilled Flag

**Purpose**: Ensure backfilled snapshots are clearly marked.

**Already Covered**: The migration script sets `is_backfilled=True` for all migrated snapshots.

**UI Implication**: WP08 (Recipe History View) will display "(approximated)" badge for these.

---

### Subtask T016 - Add Dry-Run Mode and Validation

**Purpose**: Allow safe validation before actual migration.

**Already Covered**: The script supports `--dry-run` flag.

**Additional Validation**:
- Check database connection
- Verify models are up to date (RecipeSnapshot exists)
- Report any orphaned ProductionRuns (recipe deleted)

---

### Subtask T017 - Test Migration with Sample Data

**Purpose**: Verify migration works with test_data/sample_data.json.

**Steps**:
1. Load sample_data.json into test database
2. Run migration with --dry-run
3. Verify counts match expectations
4. Run migration for real
5. Verify all runs have snapshots
6. Verify is_backfilled=True for all migrated snapshots

**Test Script** (add to script or separate test file):
```python
def test_migration_with_sample_data():
    """Test migration against sample data."""
    # 1. Reset database with sample data
    # 2. Run dry-run
    stats = migrate_production_snapshots(dry_run=True)

    # 3. Verify expected counts
    assert stats["migrated"] > 0, "Should have runs to migrate"
    assert stats["errors"] == [], "Should have no errors"

    # 4. Run actual migration
    stats = migrate_production_snapshots(dry_run=False)

    # 5. Verify all runs migrated
    with session_scope() as session:
        unmigrated = (
            session.query(ProductionRun)
            .filter(ProductionRun.recipe_snapshot_id.is_(None))
            .count()
        )
        assert unmigrated == 0, "All runs should be migrated"

        # 6. Verify is_backfilled
        backfilled = (
            session.query(RecipeSnapshot)
            .filter(RecipeSnapshot.is_backfilled == True)
            .count()
        )
        assert backfilled == stats["migrated"], "All should be backfilled"
```

## Test Strategy

- Run: `python scripts/migrate_production_snapshots.py --dry-run`
- Run: `pytest src/tests/test_migration.py -v` (if test file created)
- Manual verification after migration

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Data corruption | Backup before migration, dry-run mode |
| Recipe deleted | Skip with warning, log for review |
| Duplicate runs | Check recipe_snapshot_id is None before migrating |

## Definition of Done Checklist

- [ ] Migration script created at scripts/migrate_production_snapshots.py
- [ ] --dry-run mode works correctly
- [ ] is_backfilled=True for all migrated snapshots
- [ ] Handles missing recipes gracefully
- [ ] Idempotent (safe to run multiple times)
- [ ] Tested with sample_data.json

## Review Guidance

- Verify dry-run makes no changes
- Check is_backfilled flag is set correctly
- Confirm script handles edge cases (deleted recipes)

## Activity Log

- 2026-01-03T06:30:00Z - system - lane=planned - Prompt created.
- 2026-01-04T19:08:51Z – system – shell_pid= – lane=doing – Moved to doing
