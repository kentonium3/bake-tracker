---
work_package_id: WP05
title: Migration – Transform Existing Data
lane: "doing"
dependencies:
- WP01
base_branch: 083-dual-yield-recipe-output-support-WP01
base_commit: ab69e594ec263da2dfdb1bfb5a310aebe407727f
created_at: '2026-01-29T17:51:36.781371+00:00'
subtasks:
- T021
- T022
- T023
- T024
phase: Phase 3 - Deployment
assignee: ''
agent: ''
shell_pid: "77182"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-29T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 – Migration – Transform Existing Data

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you begin addressing feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
# Depends on WP03 (export/import must support yield_type)
spec-kitty implement WP05 --base WP03
```

**Note**: WP05 should be the final WP to ensure all code changes are complete before migration.

---

## Objectives & Success Criteria

Create migration script and documentation for upgrading existing databases:

- [ ] Migration script transforms export JSON to add yield_type
- [ ] Migration documentation explains the process
- [ ] Full export → transform → import cycle tested
- [ ] No data loss verified (record counts, field values match)

**Success metrics**:
- All existing finished_unit records have yield_type='SERVING' after migration
- Record counts match before and after migration
- All other field values preserved exactly
- Migration script is idempotent (safe to run multiple times)

---

## Context & Constraints

**Reference documents**:
- `kitty-specs/083-dual-yield-recipe-output-support/research.md` - Migration strategy (Q6)
- `kitty-specs/083-dual-yield-recipe-output-support/data-model.md` - Transformation rule
- `.kittify/memory/constitution.md` - Principle VI: Schema Change Strategy

**Constitutional migration workflow**:
1. Export ALL data to JSON before schema change
2. Delete database, update models, recreate empty database
3. Programmatically transform JSON to match new schema if needed
4. Import transformed data to restored database

**Transformation rule** (from data-model.md):
> Add `"yield_type": "SERVING"` to all existing records (conservative default - most baked goods are counted as servings).

---

## Subtasks & Detailed Guidance

### Subtask T021 – Create migration script to transform export JSON

**Purpose**: Automate the transformation of pre-migration exports to new schema.

**Steps**:
1. Create `scripts/migrate_add_yield_type.py`:

```python
#!/usr/bin/env python3
"""
Migration script: Add yield_type field to finished_units export.

This script transforms a pre-083 export to the new schema by adding
yield_type='SERVING' to all finished_unit records.

Usage:
    python scripts/migrate_add_yield_type.py <export_dir>

The script modifies finished_units.json in place (with backup).
"""

import json
import shutil
import sys
from pathlib import Path
from datetime import datetime


def transform_finished_units(export_dir: Path) -> dict:
    """Transform finished_units.json to add yield_type field.

    Args:
        export_dir: Path to export directory

    Returns:
        dict with transformation results
    """
    fu_file = export_dir / "finished_units.json"

    if not fu_file.exists():
        return {
            "status": "skipped",
            "message": "finished_units.json not found",
            "records_processed": 0,
        }

    # Create backup
    backup_file = export_dir / f"finished_units.json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(fu_file, backup_file)

    # Load existing data
    with open(fu_file, "r", encoding="utf-8") as f:
        records = json.load(f)

    if not isinstance(records, list):
        return {
            "status": "error",
            "message": "finished_units.json is not a list",
            "records_processed": 0,
        }

    # Transform records
    transformed_count = 0
    already_has_count = 0

    for record in records:
        if "yield_type" not in record:
            record["yield_type"] = "SERVING"
            transformed_count += 1
        else:
            already_has_count += 1

    # Write back
    with open(fu_file, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    return {
        "status": "success",
        "message": f"Transformed {transformed_count} records, {already_has_count} already had yield_type",
        "records_processed": len(records),
        "transformed": transformed_count,
        "already_had_yield_type": already_has_count,
        "backup_file": str(backup_file),
    }


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/migrate_add_yield_type.py <export_dir>")
        print("\nThis script transforms finished_units.json to add yield_type field.")
        print("Run AFTER exporting from old schema, BEFORE importing to new schema.")
        sys.exit(1)

    export_dir = Path(sys.argv[1])

    if not export_dir.is_dir():
        print(f"Error: {export_dir} is not a directory")
        sys.exit(1)

    print(f"Transforming exports in: {export_dir}")
    print("-" * 50)

    result = transform_finished_units(export_dir)

    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    print(f"Records processed: {result['records_processed']}")

    if result["status"] == "success":
        print(f"Transformed: {result['transformed']}")
        print(f"Already had yield_type: {result['already_had_yield_type']}")
        print(f"Backup created: {result['backup_file']}")
        print("\nTransformation complete. You can now import to the new schema.")
    elif result["status"] == "error":
        print("\nTransformation failed. Check the error message above.")
        sys.exit(1)
    else:
        print("\nNo transformation needed.")


if __name__ == "__main__":
    main()
```

**Files**: `scripts/migrate_add_yield_type.py` (new file)

**Parallel**: Yes - can be developed alongside T022

**Notes**:
- Creates backup before modifying
- Idempotent - records that already have yield_type are skipped
- Clear output showing what was transformed
- Handles edge cases (missing file, wrong format)

---

### Subtask T022 – Document migration procedure

**Purpose**: Provide clear instructions for users upgrading to this version.

**Steps**:
1. Create `docs/migrations/083-dual-yield-migration.md`:

```markdown
# Migration Guide: 083 Dual-Yield Recipe Output Support

## Overview

Feature 083 adds a `yield_type` field to FinishedUnit records, enabling classification
of yields as either "EA" (whole unit) or "SERVING" (consumption unit).

This migration adds `yield_type='SERVING'` to all existing finished unit records.

## Prerequisites

- Bake Tracker with feature 083 code installed
- Access to your current database
- Sufficient disk space for export backup

## Migration Steps

### Step 1: Export Current Data

Before updating to the new version, export all your data:

1. Open Bake Tracker (old version)
2. Go to **Settings** → **Data Management**
3. Click **Export All Data**
4. Save to a known location (e.g., `~/bake-tracker-backup-2026-01-29/`)

**IMPORTANT**: Verify the export completed successfully and contains your data.

### Step 2: Transform Export Data

Run the migration script to add yield_type to exported data:

```bash
# From the bake-tracker directory
python scripts/migrate_add_yield_type.py ~/bake-tracker-backup-2026-01-29/
```

Expected output:
```
Transforming exports in: /Users/you/bake-tracker-backup-2026-01-29
--------------------------------------------------
Status: success
Message: Transformed 42 records, 0 already had yield_type
Records processed: 42
Transformed: 42
Already had yield_type: 0
Backup created: /Users/you/.../finished_units.json.backup.20260129_143022

Transformation complete. You can now import to the new schema.
```

### Step 3: Update Application

1. Update to the new version of Bake Tracker
2. Launch the application (this creates a fresh database with new schema)

### Step 4: Import Transformed Data

1. Go to **Settings** → **Data Management**
2. Click **Import Data**
3. Select the transformed export directory
4. Verify import completes successfully

### Step 5: Verify Migration

After import, verify your data:

1. Check recipe count matches expected
2. Check finished unit count matches expected
3. Open a few recipes and verify yield types show as "SERVING"
4. Verify you can change yield type to "EA" and save

## Rollback

If something goes wrong, you can restore from the backup:

1. The migration script created a backup file: `finished_units.json.backup.YYYYMMDD_HHMMSS`
2. Copy the backup over `finished_units.json`
3. Re-run the original import

## Troubleshooting

### "finished_units.json not found"

The export directory doesn't contain finished_units.json. Either:
- Export was incomplete
- Wrong directory specified

### Import fails with UNIQUE constraint error

This can happen if importing to a database that already has data. Solution:
- Reset the database before import
- Or use the skip-duplicates option during import

### yield_type shows as empty/null

The migration script wasn't run on the export. Re-run:
```bash
python scripts/migrate_add_yield_type.py <export_dir>
```

## Questions?

If you encounter issues, please open an issue on GitHub with:
- Error message
- Export file sample (remove sensitive data)
- Steps to reproduce
```

**Files**: `docs/migrations/083-dual-yield-migration.md` (new file)

**Parallel**: Yes - can be developed alongside T021

**Notes**:
- Step-by-step instructions
- Troubleshooting section
- Rollback procedure

---

### Subtask T023 – Test full export → transform → import cycle

**Purpose**: Verify the complete migration workflow works end-to-end.

**Steps**:
1. Create test scenario with existing data (no yield_type)
2. Export using coordinated export
3. Run migration script
4. Verify JSON has yield_type added
5. Reset database with new schema
6. Import transformed data
7. Verify all records have yield_type='SERVING'

**Test script** (add to `src/tests/migrations/test_083_migration.py`):

```python
"""Integration tests for 083 migration script."""
import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from src.models.finished_unit import FinishedUnit
from src.models.recipe import Recipe
from src.services.coordinated_export_service import export_complete, import_complete
from src.utils.db import session_scope, reset_database


class Test083Migration:
    """Test the yield_type migration workflow."""

    def test_migration_script_adds_yield_type(self, test_db):
        """Migration script adds yield_type to records missing it."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create export WITHOUT yield_type (simulating old format)
            fu_data = [
                {
                    "slug": "test-fu-1",
                    "display_name": "Test FU 1",
                    "recipe_slug": "test-recipe",
                    "yield_mode": "discrete_count",
                    # NO yield_type
                    "items_per_batch": 24,
                    "item_unit": "cookie",
                    "inventory_count": 0,
                },
                {
                    "slug": "test-fu-2",
                    "display_name": "Test FU 2",
                    "recipe_slug": "test-recipe",
                    "yield_mode": "discrete_count",
                    # NO yield_type
                    "items_per_batch": 1,
                    "item_unit": "cake",
                    "inventory_count": 0,
                },
            ]
            with open(tmp_path / "finished_units.json", "w") as f:
                json.dump(fu_data, f)

            # Run migration script
            result = subprocess.run(
                ["python", "scripts/migrate_add_yield_type.py", str(tmp_path)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"Script failed: {result.stderr}"
            assert "Transformed 2 records" in result.stdout

            # Verify transformation
            with open(tmp_path / "finished_units.json") as f:
                transformed = json.load(f)

            for record in transformed:
                assert "yield_type" in record
                assert record["yield_type"] == "SERVING"

    def test_migration_script_is_idempotent(self, test_db):
        """Running migration script twice doesn't duplicate yield_type."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            fu_data = [{
                "slug": "test-fu",
                "display_name": "Test FU",
                "recipe_slug": "test-recipe",
                "yield_mode": "discrete_count",
                "items_per_batch": 24,
                "item_unit": "cookie",
                "inventory_count": 0,
            }]
            with open(tmp_path / "finished_units.json", "w") as f:
                json.dump(fu_data, f)

            # Run twice
            subprocess.run(
                ["python", "scripts/migrate_add_yield_type.py", str(tmp_path)],
                capture_output=True,
            )
            result = subprocess.run(
                ["python", "scripts/migrate_add_yield_type.py", str(tmp_path)],
                capture_output=True,
                text=True,
            )

            assert "already had yield_type" in result.stdout

            # Verify single yield_type value
            with open(tmp_path / "finished_units.json") as f:
                transformed = json.load(f)

            assert transformed[0]["yield_type"] == "SERVING"
            assert transformed[0].get("yield_type") is not None

    def test_full_migration_cycle(self, test_db):
        """Full export → transform → import cycle preserves data."""
        # Create test data
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.flush()

            # Note: In real old schema, yield_type wouldn't exist
            # We simulate by creating data then removing yield_type from export
            fu = FinishedUnit(
                slug="test-fu",
                display_name="Test Cookies",
                recipe_id=recipe.id,
                item_unit="cookie",
                items_per_batch=24,
                yield_type="SERVING",
            )
            session.add(fu)
            session.commit()

            original_count = session.query(FinishedUnit).count()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Export
            export_complete(tmp_path)

            # Simulate old format by removing yield_type
            with open(tmp_path / "finished_units.json") as f:
                records = json.load(f)
            for record in records:
                record.pop("yield_type", None)
            with open(tmp_path / "finished_units.json", "w") as f:
                json.dump(records, f)

            # Run migration
            result = subprocess.run(
                ["python", "scripts/migrate_add_yield_type.py", str(tmp_path)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0

            # Clear database
            with session_scope() as session:
                session.query(FinishedUnit).delete()
                session.query(Recipe).delete()
                session.commit()

            # Re-create recipe for FK
            with session_scope() as session:
                recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
                session.add(recipe)
                session.commit()

            # Import transformed data
            import_complete(tmp_path)

        # Verify
        with session_scope() as session:
            new_count = session.query(FinishedUnit).count()
            assert new_count == original_count

            fu = session.query(FinishedUnit).filter_by(slug="test-fu").first()
            assert fu is not None
            assert fu.yield_type == "SERVING"
            assert fu.display_name == "Test Cookies"
            assert fu.items_per_batch == 24
```

**Files**: `src/tests/migrations/test_083_migration.py` (new file, create `migrations/` dir if needed)

**Notes**:
- Tests the script directly using subprocess
- Tests idempotency
- Tests full cycle end-to-end

---

### Subtask T024 – Verify no data loss after migration

**Purpose**: Confirm all data is preserved through the migration cycle.

**Steps**:
1. Add verification checks to migration test (included in T023)
2. Create a verification checklist:

**Verification checklist** (add to migration docs):

```markdown
## Data Verification Checklist

After migration, verify:

- [ ] **Recipe count**: Same number of recipes before and after
- [ ] **FinishedUnit count**: Same number of finished units before and after
- [ ] **Ingredient count**: Same number of ingredients
- [ ] **All yield_types set**: Every FinishedUnit has yield_type='SERVING'
- [ ] **Field values preserved**:
  - [ ] display_name unchanged
  - [ ] item_unit unchanged
  - [ ] items_per_batch unchanged
  - [ ] inventory_count unchanged
  - [ ] recipe associations intact

### Quick Verification Queries

After import, run these in the app's data explorer or via Python:

```python
from src.utils.db import session_scope
from src.models.finished_unit import FinishedUnit

with session_scope() as session:
    total = session.query(FinishedUnit).count()
    with_yield_type = session.query(FinishedUnit).filter(
        FinishedUnit.yield_type.isnot(None)
    ).count()
    serving_count = session.query(FinishedUnit).filter(
        FinishedUnit.yield_type == "SERVING"
    ).count()

    print(f"Total FinishedUnits: {total}")
    print(f"With yield_type: {with_yield_type}")
    print(f"With SERVING: {serving_count}")

    assert with_yield_type == total, "Some records missing yield_type!"
    assert serving_count == total, "Not all records defaulted to SERVING!"
    print("✓ All records have yield_type='SERVING'")
```
```

**Files**: Update `docs/migrations/083-dual-yield-migration.md`

**Notes**:
- Checklist for manual verification
- Quick queries for automated verification
- Assertions to catch issues early

---

## Test Strategy

**Required tests** (T023):
- `test_migration_script_adds_yield_type` - Script transforms data correctly
- `test_migration_script_is_idempotent` - Safe to run multiple times
- `test_full_migration_cycle` - End-to-end workflow works

**Run tests**:
```bash
./run-tests.sh src/tests/migrations/test_083_migration.py -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Data loss during migration | Script creates backup before modifying |
| Script fails mid-transformation | Backup allows restore |
| User runs on wrong directory | Clear error messages, usage instructions |
| UNIQUE constraint violations | All records get same yield_type, no conflicts |

---

## Definition of Done Checklist

- [ ] T021: Migration script created and functional
- [ ] T022: Migration documentation complete
- [ ] T023: All migration tests pass
- [ ] T024: Verification checklist added to docs
- [ ] Script is idempotent (safe to run multiple times)
- [ ] Backup created before any modifications
- [ ] Clear error messages for common issues

---

## Review Guidance

**Reviewers should verify**:
1. Script creates backup before modifying files
2. Script is idempotent (second run does nothing)
3. Documentation covers all steps including rollback
4. Tests cover the complete migration workflow
5. Verification steps are clear and actionable

---

## Activity Log

- 2026-01-29T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
