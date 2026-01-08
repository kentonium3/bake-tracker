---
work_package_id: WP05
title: Migration - Export/Reset/Import Cycle
lane: done
history:
- timestamp: '2025-12-19T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
- timestamp: '2025-12-19T12:00:00Z'
  lane: done
  agent: claude
  shell_pid: deferred
  action: Deferred to post-merge per user decision - migration will be performed after feature merge
agent: claude
assignee: user
phase: Phase 4 - Migration
review_status: deferred - post-merge
reviewed_by: claude
shell_pid: deferred
subtasks:
- T014
- T015
- T016
- T017
---

# Work Package Prompt: WP05 - Migration - Export/Reset/Import Cycle

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

**Objective**: Execute the Constitution VI migration cycle to apply schema changes to the existing database.

**Success Criteria**:
- [ ] All existing products preserved after migration
- [ ] Product count matches before and after
- [ ] All migrated products have product_name=NULL
- [ ] Application functions normally after migration
- [ ] Export file retained as backup

## Context & Constraints

**Constitution Reference**: `.kittify/memory/constitution.md` - Section VI (Schema Change Strategy)
**Spec Reference**: `kitty-specs/023-product-name-differentiation/spec.md` - User Story 2

**Key Principle (Constitution VI)**:
> For single-user desktop apps, database migrations are unnecessary complexity.
> Schema changes handled via export -> reset -> import cycle.

**Migration Cycle**:
1. Export ALL data to JSON
2. Delete database file
3. Update models (done in WP01)
4. Restart app to recreate empty database
5. Import transformed data

**Dependencies**: WP01, WP02, WP03, WP04 must ALL be complete before migration

## Subtasks & Detailed Guidance

### Subtask T014 - Export Current Database

**Purpose**: Create a complete backup of all data before schema change.

**Steps**:
1. Launch the application: `python src/main.py`
2. Navigate to File menu
3. Select "Export Data" (or equivalent)
4. Choose export location (recommended: `data/backup_pre_migration_2025-12-19.json`)
5. Wait for export confirmation
6. Verify export file exists and is non-empty

**Alternative (CLI)**:
```python
from src.services.import_export_service import export_all_data_to_json
result = export_all_data_to_json("data/backup_pre_migration.json")
print(f"Exported {result.total_records} records")
```

**Record these values**:
- Total products exported: ____
- Total ingredients: ____
- Total recipes: ____
- Export file path: ____
- Export file size: ____

**Files**: None (operational task)
**Parallel?**: No

**Notes**:
- Keep this export file even after successful migration (backup)
- Record counts for verification in T017

### Subtask T015 - Delete Database and Recreate

**Purpose**: Remove old schema and let app create new database with updated model.

**Steps**:
1. Close the application completely
2. Locate database file:
   - Check `data/bake_tracker.db`
   - Or check application settings for path
3. Delete the database file:
   ```bash
   rm data/bake_tracker.db
   ```
4. Also delete WAL files if present:
   ```bash
   rm data/bake_tracker.db-wal data/bake_tracker.db-shm 2>/dev/null
   ```
5. Start the application: `python src/main.py`
6. Application should create new empty database with updated schema
7. Verify app launches without errors

**Files**: `data/bake_tracker.db` (deleted)
**Parallel?**: No

**Notes**:
- Database will be empty after this step
- Application should handle missing database gracefully
- New database has product_name column and unique constraint

### Subtask T016 - Import Data

**Purpose**: Restore all data into the new database schema.

**Steps**:
1. With application running, navigate to File menu
2. Select "Import Data" (or equivalent)
3. Choose the export file from T014
4. Select import options:
   - Skip duplicates: Yes (recommended)
   - Or merge/overwrite as appropriate
5. Wait for import confirmation
6. Note any errors or warnings

**Alternative (CLI)**:
```python
from src.services.import_export_service import import_all_data_from_json
result = import_all_data_from_json("data/backup_pre_migration.json", skip_duplicates=True)
print(f"Imported: {result.success_count}, Skipped: {result.skip_count}, Errors: {result.error_count}")
```

**Files**: None (operational task)
**Parallel?**: No

**Notes**:
- Old export has no product_name field - this is expected
- Import should default missing product_name to NULL
- Watch for any error messages about product_name

### Subtask T017 - Verify Migration Success

**Purpose**: Confirm all data preserved correctly with new schema.

**Verification Checklist**:

1. **Count Check**:
   - [ ] Product count matches pre-migration count from T014
   - [ ] Ingredient count matches
   - [ ] Recipe count matches

2. **Schema Check**:
   ```python
   from src.services.product_service import get_all_products
   products = get_all_products()
   for p in products:
       assert p.product_name is None, f"Product {p.id} has unexpected product_name"
   print(f"All {len(products)} products have product_name=NULL")
   ```

3. **Constraint Check**:
   - Verify unique constraint exists by attempting to create duplicate
   - Should succeed for products with NULL product_name (NULLs are distinct)

4. **UI Check**:
   - [ ] Open Add Product dialog - Product Name field visible
   - [ ] Open Edit Product dialog - Product Name field visible and empty
   - [ ] Display names look correct (no "None" showing)

5. **Functional Check**:
   - [ ] Can add new product with product_name
   - [ ] Can edit existing product to add product_name
   - [ ] Export now includes product_name field

**Files**: None (operational task)
**Parallel?**: No

**Notes**:
- If counts don't match, check import errors from T016
- If any product has non-NULL product_name, there's a data corruption issue
- Keep backup export file until fully verified

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Data loss during migration | Low | Critical | Keep backup export file |
| Import errors | Medium | Medium | Review error messages, retry |
| Schema mismatch | Low | High | Verify all code changes complete before migration |
| Application won't start | Low | High | Check for Python errors, model syntax |

## Definition of Done Checklist

- [ ] T014: Export completed successfully, file saved
- [ ] T015: Database deleted, app recreates new schema
- [ ] T016: Import completed with no errors
- [ ] T017: All verification checks pass
- [ ] Backup export file retained
- [ ] Product counts match exactly
- [ ] All products have product_name=NULL
- [ ] New product form has Product Name field

## Review Guidance

**Reviewers should verify**:
1. Backup export file exists and is complete
2. Product counts match before/after
3. No data corruption (all fields preserved)
4. product_name is NULL for all migrated products
5. UI shows new field correctly

## Activity Log

- 2025-12-19T00:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-19T12:00:00Z - claude - lane=done - Deferred to post-merge per user decision; migration will be performed after feature merge
