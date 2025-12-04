---
work_package_id: "WP02"
subtasks:
  - "T006"
  - "T007"
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
title: "Service Layer - Export Functions"
phase: "Phase 2 - Service Layer"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "80857"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-04T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Service Layer - Export Functions

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

- **Primary Objective**: Extend `import_export_service.py` with export functions for all v3.0 entities
- **Success Criteria**:
  - `export_all_to_json()` produces valid v3.0 JSON
  - All 16 entity types included in export
  - Export includes `version: "3.0"` header with metadata
  - `ExportResult` provides per-entity record counts
  - Unit tests cover all new export functions

## Context & Constraints

**Prerequisite Documents**:
- `kitty-specs/009-ui-import-export/spec.md` - FR-005, FR-006, FR-007
- `kitty-specs/009-ui-import-export/data-model.md` - Entity definitions
- `docs/design/import_export_specification.md` - v3.0 format (from WP01)

**Key Constraints**:
- Follow existing patterns in `import_export_service.py`
- Use `session_scope()` context manager for all DB access
- Return `List[Dict]` from entity export functions
- Datetime fields must use ISO 8601 with 'Z' suffix

**Existing Code Reference**:
- `src/services/import_export_service.py:552-890` - Current `export_all_to_json()`
- Existing export functions: `export_ingredients_to_json()`, `export_recipes_to_json()`, etc.

## Subtasks & Detailed Guidance

### Subtask T006 - ExportResult Class Enhancements

- **Purpose**: Provide detailed export statistics per entity type
- **Steps**:
  1. Locate `ExportResult` class in `src/services/import_export_service.py`
  2. Add `entity_counts: Dict[str, int]` attribute
  3. Update `get_summary()` to include per-entity breakdown
  4. Ensure backward compatibility with existing usage
- **Files**: `src/services/import_export_service.py`
- **Notes**: Model after existing `ImportResult` pattern if it has similar functionality

### Subtask T007 - Implement export_finished_units_to_json() [PARALLEL]

- **Purpose**: Export FinishedUnit records for recipe yield definitions
- **Steps**:
  1. Add function `export_finished_units_to_json() -> List[Dict]`
  2. Query all FinishedUnit records using session_scope()
  3. Map fields per data-model.md:
     - recipe_slug (from recipe relationship)
     - display_name
     - yield_mode
     - items_per_batch (conditional)
     - item_unit (conditional)
     - batch_percentage (conditional)
     - category
     - notes
  4. Return list of dicts
- **Files**: `src/services/import_export_service.py`
- **Parallel?**: Yes - can be developed alongside T008-T010
- **Notes**: Check `src/models/finished_unit.py` for actual field names

### Subtask T008 - Implement export_compositions_to_json() [PARALLEL]

- **Purpose**: Export Composition records (FinishedUnit -> FinishedGood links)
- **Steps**:
  1. Add function `export_compositions_to_json() -> List[Dict]`
  2. Query all Composition records
  3. Map fields per data-model.md:
     - finished_good_slug (from relationship)
     - finished_unit_slug (from relationship)
     - component_quantity
     - notes
  4. Return list of dicts
- **Files**: `src/services/import_export_service.py`
- **Parallel?**: Yes
- **Notes**: This replaces v2.0 "bundles" concept

### Subtask T009 - Implement export_package_finished_goods_to_json() [PARALLEL]

- **Purpose**: Export PackageFinishedGood records (Package contents)
- **Steps**:
  1. Add function `export_package_finished_goods_to_json() -> List[Dict]`
  2. Query all PackageFinishedGood records
  3. Map fields per data-model.md:
     - package_slug (from relationship)
     - finished_good_slug (from relationship)
     - quantity
  4. Return list of dicts
- **Files**: `src/services/import_export_service.py`
- **Parallel?**: Yes
- **Notes**: Check if model is `PackageFinishedGood` or similar in `src/models/`

### Subtask T010 - Implement export_production_records_to_json() [PARALLEL]

- **Purpose**: Export ProductionRecord records from Feature 008
- **Steps**:
  1. Add function `export_production_records_to_json() -> List[Dict]`
  2. Query all ProductionRecord records
  3. Map fields per data-model.md:
     - event_slug (from event relationship)
     - recipe_slug (from recipe relationship)
     - batches
     - produced_at (ISO 8601 format with 'Z')
     - actual_cost
     - notes
  4. Return list of dicts
- **Files**: `src/services/import_export_service.py`
- **Parallel?**: Yes
- **Notes**: Reference `src/models/production_record.py` for actual schema

### Subtask T011 - Update export_all_to_json() for v3.0

- **Purpose**: Produce complete v3.0 export with all entities
- **Steps**:
  1. Locate `export_all_to_json()` function
  2. Add v3.0 header fields:
     ```python
     data = {
         "version": "3.0",
         "exported_at": datetime.utcnow().isoformat() + "Z",
         "application": "bake-tracker",
         # ... entities
     }
     ```
  3. Add calls to new export functions in correct order:
     - finished_units (after recipes)
     - compositions (after finished_goods)
     - package_finished_goods (after packages)
     - production_records (last)
  4. Update ExportResult with entity counts
  5. Ensure file write handles encoding (UTF-8)
- **Files**: `src/services/import_export_service.py`
- **Notes**: Order must match data-model.md dependency order

### Subtask T012 - Add Unit Tests for Export Functions

- **Purpose**: Verify all new export functions work correctly
- **Steps**:
  1. Add tests in `src/tests/services/test_import_export_service.py`
  2. Test cases:
     - `test_export_finished_units_to_json()` - verify structure and fields
     - `test_export_compositions_to_json()` - verify relationship resolution
     - `test_export_package_finished_goods_to_json()` - verify structure
     - `test_export_production_records_to_json()` - verify datetime format
     - `test_export_all_v3_format()` - verify complete export structure
  3. Use fixtures with minimal test data
  4. Assert expected field presence and types
- **Files**: `src/tests/services/test_import_export_service.py`
- **Notes**: Follow existing test patterns in the file

## Test Strategy

- **Unit Tests**: All new export functions must have dedicated tests
- **Test Command**: `pytest src/tests/services/test_import_export_service.py -v`
- **Coverage Target**: >70% for new code
- **Fixtures**: Create minimal test data for each entity type

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Model field names differ from spec | Verify against actual models before implementing |
| Relationship traversal errors | Use joinedload for required relationships |
| Datetime serialization issues | Use `.isoformat() + "Z"` consistently |
| Large dataset performance | Consider pagination for very large tables |

## Definition of Done Checklist

- [ ] T006: ExportResult enhanced with per-entity counts
- [ ] T007: export_finished_units_to_json() implemented
- [ ] T008: export_compositions_to_json() implemented
- [ ] T009: export_package_finished_goods_to_json() implemented
- [ ] T010: export_production_records_to_json() implemented
- [ ] T011: export_all_to_json() updated with v3.0 header and new entities
- [ ] T012: Unit tests passing for all new functions
- [ ] All datetime fields use ISO 8601 with 'Z' suffix
- [ ] Export produces valid JSON

## Review Guidance

- Verify field names match v3.0 specification (WP01 output)
- Check relationship resolution is correct
- Verify datetime format consistency
- Ensure test coverage is adequate

## Activity Log

- 2025-12-04T00:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-04T19:25:25Z – claude – shell_pid=78003 – lane=doing – Started implementation
- 2025-12-04T20:11:34Z – claude – shell_pid=80857 – lane=for_review – Completed all export functions and tests - T006-T012 done
