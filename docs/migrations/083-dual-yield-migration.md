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
2. Go to **Settings** > **Data Management**
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

1. Go to **Settings** > **Data Management**
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
    print("All records have yield_type='SERVING'")
```

## Questions?

If you encounter issues, please open an issue on GitHub with:
- Error message
- Export file sample (remove sensitive data)
- Steps to reproduce
