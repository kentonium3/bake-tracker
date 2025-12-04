---
work_package_id: "WP03"
subtasks:
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T021"
  - "T022"
title: "Service Layer - Import Functions with Mode Support"
phase: "Phase 2 - Service Layer"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-04T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Service Layer - Import Functions with Mode Support

## Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- **Primary Objective**: Extend `import_export_service.py` with import functions supporting Merge and Replace modes
- **Success Criteria**:
  - `import_all_from_json()` accepts `mode` parameter ("merge" or "replace")
  - Merge mode: skips duplicates, counts skipped records
  - Replace mode: clears all tables before import
  - v3.0 version validation rejects non-v3.0 files with clear error (FR-018)
  - All 16 entity types can be imported
  - Transaction rollback on any error
  - `ImportResult` provides detailed per-entity statistics

## Context & Constraints

**Prerequisite Documents**:
- `kitty-specs/009-ui-import-export/spec.md` - FR-009 through FR-013b, FR-018
- `kitty-specs/009-ui-import-export/data-model.md` - Entity definitions and import order
- `docs/design/import_export_specification.md` - v3.0 format (from WP01)

**Key Constraints**:
- Only v3.0 format supported - reject all other versions
- Import must use database transaction - rollback entirely on any error
- Respect entity ordering for referential integrity
- Merge mode must skip duplicates without error
- Replace mode clears tables in reverse dependency order

**Existing Code Reference**:
- `src/services/import_export_service.py:1796-1960` - Current `import_all_from_json()`
- Existing import functions with duplicate detection patterns

## Subtasks & Detailed Guidance

### Subtask T013 - Add Mode Parameter to import_all_from_json()

- **Purpose**: Enable user choice between Merge and Replace import strategies
- **Steps**:
  1. Locate `import_all_from_json()` function
  2. Add parameter: `mode: str = "merge"` (default to merge for safety)
  3. Validate mode is "merge" or "replace", raise ValueError otherwise
  4. Add mode handling logic at start of function:
     ```python
     if mode == "replace":
         _clear_all_tables(session)
     ```
  5. Update docstring to document mode behavior
- **Files**: `src/services/import_export_service.py`
- **Notes**: Default to "merge" for backward compatibility

### Subtask T014 - Implement _clear_all_tables() Helper

- **Purpose**: Safely clear all data for Replace mode
- **Steps**:
  1. Create private function `_clear_all_tables(session) -> None`
  2. Clear tables in REVERSE dependency order to avoid FK violations:
     ```python
     # Reverse order from data-model.md
     tables_to_clear = [
         ProductionRecord,
         EventRecipientPackage,
         Event,
         Recipient,
         PackageFinishedGood,
         Package,
         Composition,
         FinishedGood,
         FinishedUnit,
         RecipeIngredient,
         Recipe,
         PantryItem,
         Purchase,
         Variant,
         Ingredient,
         UnitConversion,
     ]
     for table in tables_to_clear:
         session.query(table).delete()
     ```
  3. Do NOT commit - caller handles transaction
- **Files**: `src/services/import_export_service.py`
- **Notes**: Must be within same transaction as import for atomicity

### Subtask T015 - Add v3.0 Version Detection and Validation

- **Purpose**: Reject non-v3.0 files with clear error message (FR-018)
- **Steps**:
  1. Add version check at START of `import_all_from_json()`:
     ```python
     version = data.get("version", "unknown")
     if version != "3.0":
         raise ImportError(
             f"Unsupported file version: {version}. "
             "This application only supports v3.0 format. "
             "Please export a new backup from a current version."
         )
     ```
  2. This check must occur BEFORE any data operations
  3. Error message must be user-friendly (no technical jargon)
- **Files**: `src/services/import_export_service.py`
- **Notes**: Per spec clarification, v2.0 compatibility is out of scope

### Subtask T016 - Implement import_finished_units_from_json() [PARALLEL]

- **Purpose**: Import FinishedUnit records
- **Steps**:
  1. Add function `import_finished_units_from_json(data: List[Dict], session) -> ImportResult`
  2. Follow existing import pattern:
     - Iterate through records
     - Resolve recipe reference by slug
     - Check for duplicates (by recipe + display_name or similar unique key)
     - Skip or create based on duplicate status
     - Track imported/skipped/error counts
  3. Handle conditional fields (items_per_batch vs batch_percentage)
- **Files**: `src/services/import_export_service.py`
- **Parallel?**: Yes - can be developed alongside T017-T019
- **Notes**: Check actual model for unique constraints

### Subtask T017 - Implement import_compositions_from_json() [PARALLEL]

- **Purpose**: Import Composition records (FinishedUnit -> FinishedGood links)
- **Steps**:
  1. Add function `import_compositions_from_json(data: List[Dict], session) -> ImportResult`
  2. For each record:
     - Resolve finished_good by slug
     - Resolve finished_unit by slug
     - Check for duplicate by composite key
     - Create or skip
  3. Track counts
- **Files**: `src/services/import_export_service.py`
- **Parallel?**: Yes
- **Notes**: Both foreign keys must exist (imported in earlier steps)

### Subtask T018 - Implement import_package_finished_goods_from_json() [PARALLEL]

- **Purpose**: Import PackageFinishedGood records
- **Steps**:
  1. Add function `import_package_finished_goods_from_json(data: List[Dict], session) -> ImportResult`
  2. For each record:
     - Resolve package by slug
     - Resolve finished_good by slug
     - Check for duplicate by composite key
     - Create or skip
  3. Track counts
- **Files**: `src/services/import_export_service.py`
- **Parallel?**: Yes
- **Notes**: Check actual model name in `src/models/`

### Subtask T019 - Implement import_production_records_from_json() [PARALLEL]

- **Purpose**: Import ProductionRecord records from Feature 008
- **Steps**:
  1. Add function `import_production_records_from_json(data: List[Dict], session) -> ImportResult`
  2. For each record:
     - Resolve event by slug
     - Resolve recipe by slug
     - Parse `produced_at` from ISO 8601 string
     - Check for duplicate (by event + recipe + produced_at?)
     - Create with FIFO cost data
  3. Track counts
- **Files**: `src/services/import_export_service.py`
- **Parallel?**: Yes
- **Notes**: Datetime parsing: `datetime.fromisoformat(s.replace('Z', '+00:00'))`

### Subtask T020 - Update import_all_from_json() with New Entity Imports

- **Purpose**: Call all import functions in correct dependency order
- **Steps**:
  1. Add calls to new import functions in order after existing ones:
     ```python
     # After recipes import
     if "finished_units" in data:
         result.merge(import_finished_units_from_json(data["finished_units"], session))

     # After finished_goods import
     if "compositions" in data:
         result.merge(import_compositions_from_json(data["compositions"], session))

     # After packages import
     if "package_finished_goods" in data:
         result.merge(import_package_finished_goods_from_json(data["package_finished_goods"], session))

     # Last
     if "production_records" in data:
         result.merge(import_production_records_from_json(data["production_records"], session))
     ```
  2. Each call should be optional (check if key exists)
  3. Use single transaction wrapper for atomicity
- **Files**: `src/services/import_export_service.py`
- **Notes**: Order from data-model.md lines 412-430 is authoritative

### Subtask T021 - Enhance ImportResult with Per-Entity Statistics

- **Purpose**: Provide detailed import feedback for UI display
- **Steps**:
  1. Locate `ImportResult` class
  2. Add attributes if not present:
     - `entity_counts: Dict[str, Dict[str, int]]` (entity -> {imported, skipped, errors})
  3. Add method `merge(other: ImportResult)` to combine results
  4. Update `get_summary()` to show per-entity breakdown:
     ```
     Import Complete:
     - ingredients: 10 imported, 2 skipped
     - recipes: 5 imported, 0 skipped
     - production_records: 3 imported, 0 skipped
     Total: 18 imported, 2 skipped, 0 errors
     ```
- **Files**: `src/services/import_export_service.py`
- **Notes**: Summary must be user-friendly (FR-012)

### Subtask T022 - Add Unit Tests for Import Modes and Validation

- **Purpose**: Verify import functionality thoroughly
- **Steps**:
  1. Add tests in `src/tests/services/test_import_export_service.py`
  2. Test cases:
     - `test_import_merge_mode_skips_duplicates()` - existing + new data
     - `test_import_replace_mode_clears_first()` - verify data cleared
     - `test_import_rejects_v2_format()` - version validation
     - `test_import_rejects_unknown_version()` - version validation
     - `test_import_rollback_on_error()` - transaction atomicity
     - `test_import_finished_units()` - new entity
     - `test_import_compositions()` - new entity
     - `test_import_package_finished_goods()` - new entity
     - `test_import_production_records()` - new entity with datetime
  3. Use fixtures with v3.0 format test data
- **Files**: `src/tests/services/test_import_export_service.py`
- **Notes**: Test both happy path and error cases

## Test Strategy

- **Unit Tests**: All new import functions must have dedicated tests
- **Test Command**: `pytest src/tests/services/test_import_export_service.py -v`
- **Coverage Target**: >70% for new code
- **Key Scenarios**:
  - Merge mode with existing data
  - Replace mode clearing all data
  - Version rejection with clear error
  - Rollback on mid-import failure

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Foreign key violations during import | Strict dependency order enforcement |
| Data loss in Replace mode | UI confirmation required (WP04) |
| Partial import on error | Single transaction with rollback |
| Datetime parsing errors | Standardize on ISO 8601 with explicit parsing |

## Definition of Done Checklist

- [ ] T013: `mode` parameter added to import_all_from_json()
- [ ] T014: `_clear_all_tables()` implemented with reverse order
- [ ] T015: v3.0 version validation with user-friendly error
- [ ] T016: import_finished_units_from_json() implemented
- [ ] T017: import_compositions_from_json() implemented
- [ ] T018: import_package_finished_goods_from_json() implemented
- [ ] T019: import_production_records_from_json() implemented
- [ ] T020: import_all_from_json() updated with new entity imports
- [ ] T021: ImportResult enhanced with per-entity statistics
- [ ] T022: Unit tests passing for all new functionality
- [ ] Transaction rollback verified on error
- [ ] Merge mode skips duplicates correctly
- [ ] Replace mode clears all data first

## Review Guidance

- Verify dependency order is correct
- Check error messages are user-friendly
- Verify transaction handling is correct
- Test rollback behavior manually
- Check version rejection works for v2.0 files

## Activity Log

- 2025-12-04T00:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
