# Production Database Table Wipe Investigation

**Date**: 2026-02-08
**Reported by**: User (Kent)
**Investigated by**: Claude Code (Opus 4.6)
**Status**: Root cause identified, remediation recommendations provided

## Symptom

After closing the app normally at end of user testing session, upon reopening:
- **Empty tables**: ingredients, products, recipes, recipe_ingredients, finished_units, finished_goods, inventory_items, purchases, events, recipients, packages, suppliers, compositions, production_runs, assembly_runs
- **Tables with data**: material_categories (4), material_subcategories (9), materials (21), material_products (26), material_units (28), units (35), recipe_categories (7)
- This is a **repeating problem** across multiple development sessions

## Root Cause: `_clear_all_tables()` Inconsistency

### The Fingerprint

The empty-vs-populated pattern is the **exact fingerprint** of `_clear_all_tables()` in `src/services/import_export_service.py` (lines 2094-2149):

**What `_clear_all_tables()` deletes:**
- ProductionRecord, EventRecipientPackage, PlanAmendment, BatchDecision
- EventFinishedGood, EventRecipe, Event, Recipient
- PackageFinishedGood, Package, Composition
- FinishedGood, FinishedUnit, RecipeIngredient, Recipe, **RecipeCategory**
- InventoryItem, Purchase, Product, Supplier, Ingredient

**What `_clear_all_tables()` does NOT delete (the bug):**
- MaterialCategory, MaterialSubcategory, Material, MaterialProduct, MaterialUnit
- MaterialPurchase, MaterialUnitSnapshot, MaterialInventoryItem
- Unit (reference/seed table)
- RecipeSnapshot, FinishedGoodSnapshot, FinishedUnitSnapshot

### Why Material Tables Survive

Material tables were added in Feature 047 (Materials Management System) but were **never added** to `_clear_all_tables()`. This is a maintenance gap, not intentional design.

The coordinated export service (`coordinated_export_service.py` lines 1576-1607) DOES clear material tables. Only the single-file import path has this gap.

## Evidence

### Database Forensics (Production DB)

```
Location: ~/Library/Application Support/BakeTracker/bake_tracker.db
File size: 2,220,032 bytes (2.2 MB)
Page count: 542 | Free pages: 90 | Page size: 4096
Integrity check: OK
WAL file: 0 bytes (truncated/checkpointed)
```

The **90 free pages** (17% of database) confirm data was DELETED from existing tables, not that this is a fresh database. A fresh DB would have 0 free pages.

### Timestamp Analysis

| Table | created_at (UTC) | Interpretation |
|-------|-------------------|----------------|
| units | 2026-02-07 22:37:25 | DB initialized (units seeded) |
| material_categories | 2026-02-07 22:40:25 | Coordinated backup restored |
| material_units | 2026-02-07 22:40:25 | Same restore |
| recipe_categories | **2026-02-08 20:21:32** | **Re-seeded on next app start** |

Recipe categories were cleared by `_clear_all_tables()` (they ARE in the list), then re-seeded by `seed_recipe_categories()` on the next app startup (~3:21 PM on Feb 8).

### Import Log History

Last import log: `import_2026-02-07_174025.log`
- Source: `backup_2026-02-07_165341/manifest.json` (coordinated backup)
- Result: 938 records imported successfully (413 ingredients, 156 products, 21 recipes, etc.)
- No errors, no warnings

**No import logs exist after this timestamp.** The data loss occurred after 5:40 PM Feb 7 but was not logged.

## Structural Vulnerabilities Found

### V1: `_clear_all_tables()` Missing Material Tables (CRITICAL)

**File**: `src/services/import_export_service.py:2122-2145`

The `tables_to_clear` list is incomplete. Material tables added in F047 were never added to this list. This creates an inconsistency between:
- **Single-file import** (`import_all_from_json_v4` mode="replace"): Clears core tables only
- **Coordinated import** (`import_complete`): Clears ALL tables including materials

### V2: Non-Atomic Clear + Import Pattern (CRITICAL)

**File**: `src/services/import_export_service.py:3312-3369`

```python
with session_scope() as session:
    if mode == "replace":
        _clear_all_tables(session)    # Step 1: DELETE all core data

    if "ingredients" in data:
        for ing in data["ingredients"]:
            try:
                # ... import logic ...
            except (ServiceError, Exception) as e:
                result.add_error(...)    # Step 2: Per-record errors are SWALLOWED
```

Per-record import errors are caught and counted but **never re-raised**. If ALL imports fail (bad format, missing keys, schema mismatch), the transaction still COMMITS with tables empty. The clear is permanent even if 0 records were imported.

**Failure scenario:**
1. User selects a file for "replace" import
2. `_clear_all_tables()` deletes all core data
3. File has wrong format / missing entity keys / schema mismatch
4. 0 records imported (all fail silently)
5. Transaction commits - core tables permanently empty
6. Material tables untouched (not in clear list)

### V3: CLI Import Path Has No Log Output (MODERATE)

**File**: `src/utils/import_export_cli.py:987`

```python
result = import_all_from_json_v4(input_file, mode=mode)
print(result.get_summary())
```

CLI imports don't write log files (only the UI path does via `_write_import_log()`). If someone runs a CLI import with `mode=replace`, there's no persistent record.

### V4: Traceback Debug Output Goes to stdout (MODERATE)

**Files**:
- `src/services/import_export_service.py:2107-2111`
- `src/services/database.py:481-485`
- `src/services/coordinated_export_service.py:1546-1550`

```python
print("=" * 60)
print("WARNING: _clear_all_tables called!")
traceback.print_stack()
print("=" * 60)
```

The debug traceback prints to stdout, which is only visible if the terminal is being watched. It's not logged to a file.

## Negative Findings (Ruled Out)

### Test Suite: SAFE
- All tests use `sqlite:///:memory:` databases (verified in `conftest.py:24`)
- `get_session_factory()` is monkey-patched per-test to use in-memory sessions
- Tests cannot affect the production database

### App Startup: SAFE
- `initialize_app_database()` calls `Base.metadata.create_all()` which only creates missing tables
- `seed_units()` and `seed_recipe_categories()` are idempotent (skip if data exists)
- No destructive operations at startup

### WAL Durability: SAFE
- `PRAGMA synchronous=FULL` ensures WAL writes are synced to disk
- `PRAGMA wal_checkpoint(TRUNCATE)` is crash-safe per SQLite documentation
- Post-import verification code exists in coordinated import path (lines 1479-1495)

### Scripts: SAFE
- `scripts/generate_bare_finished_goods.py` - only creates records
- `scripts/fix_bare_fg_compositions.py` - only deletes orphaned bare FGs

### Config Singleton: SAFE
- Once created, environment can't be changed
- Defaults to "production" which is the intended behavior for the app

## Recommended Fixes

### Fix 1: Add Safety Check to Replace Import (Priority: HIGH)

After `_clear_all_tables()` runs AND the import loop completes, verify that critical tables have data before committing:

```python
# After all imports complete, before session_scope commits:
if mode == "replace":
    critical_tables = [Ingredient, Recipe, Product]
    for table in critical_tables:
        count = session.query(table).count()
        if count == 0 and any(data.get(key) for key in ["ingredients", "recipes", "products"]):
            raise ImportError(
                f"Replace import would leave {table.__name__} empty. "
                f"Rolling back to preserve existing data."
            )
```

### Fix 2: Update `_clear_all_tables()` to Include Material Tables (Priority: HIGH)

Add material tables to the `tables_to_clear` list for consistency with the coordinated import path.

### Fix 3: Write Import Audit Log to File (Priority: MEDIUM)

Replace the `print()` + `traceback.print_stack()` debug output with a persistent audit log file:

```python
import logging
audit_logger = logging.getLogger("baketracker.audit")
# Configure to write to ~/Library/Application Support/BakeTracker/audit.log
```

### Fix 4: CLI Import Should Write Log Files (Priority: MEDIUM)

Have the CLI import path also write structured log files to the configured logs directory.

### Fix 5: Add Pre-Import Data Checkpoint (Priority: LOW)

Before any replace-mode import, automatically export current data as a safety backup.

## Recovery Steps

To restore the production database from the most recent backup:

```bash
# The latest backup with data is from Feb 7:
# ~/Documents/BakeTracker/backups/backup_2026-02-07_165341/

# Option 1: Use the app's import dialog
# Open app > Import/Export > Backup Restore > Select manifest.json from above directory

# Option 2: Use CLI
cd /Users/kentgale/Vaults-repos/bake-tracker
python -m src.utils.import_export_cli import-backup \
    ~/Documents/BakeTracker/backups/backup_2026-02-07_165341/
```

## Audit Trap Deployed

Persistent audit logging was added to all three destructive operations:
- `_clear_all_tables()` in `import_export_service.py`
- Coordinated import `clear_existing` block in `coordinated_export_service.py`
- `reset_database()` in `database.py`

Each writes to `destructive_ops_audit.log` alongside the production DB AND in `data/` (catches test-time calls). Entries include timestamp, PID, CWD, session bind, and full stack trace.

**Initial test run confirmed**: All 8 `_clear_all_tables()` calls during the test suite showed `Session bind: Engine(sqlite:///:memory:)` — tests ARE properly isolated.

### Audit Logging Bug Fix (2026-02-08)

The initial audit logging introduced a Python scoping bug: `from pathlib import Path` and `from datetime import datetime, timezone` inside function bodies shadowed module-level imports. In `coordinated_export_service.py`, the import inside an `if clear_existing:` block made `Path` a local variable for the entire function scope, causing `UnboundLocalError` when `clear_existing=False`. Fixed by removing redundant local imports (using module-level `Path` and `datetime`, only importing `timezone` locally).

## Related Previous Work

- DB moved from `~/Documents` to `~/Library/Application Support` (iCloud corruption prevention)
- WAL durability measures: `PRAGMA synchronous=FULL`, explicit `checkpoint_wal()` on close
- Post-import verification added to coordinated import path
- Debug traceback prints added to `_clear_all_tables()` and `reset_database()`
