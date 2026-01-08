---
work_package_id: WP05
title: Sample Data & Integration Testing
lane: done
history:
- timestamp: '2025-12-04T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude-reviewer
assignee: claude
phase: Phase 4 - Testing & Polish
review_status: approved
reviewed_by: claude-reviewer
shell_pid: '85685'
subtasks:
- T033
- T034
- T035
- T036
- T037
- T038
---

# Work Package Prompt: WP05 - Sample Data & Integration Testing

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

- **Primary Objective**: Update sample data to v3.0 format and verify complete round-trip data integrity
- **Success Criteria**:
  - `test_data/sample_data.json` updated to v3.0 format
  - Sample data imports with zero errors on fresh database (SC-004)
  - Round-trip test achieves 100% data integrity (SC-003)
  - Import completes in under 60 seconds for typical dataset (SC-002)
  - Export completes in under 30 seconds for typical dataset (SC-001)
  - All 16 entity types have realistic test data

## Context & Constraints

**Prerequisite Documents**:
- `kitty-specs/009-ui-import-export/spec.md` - Success criteria SC-001 through SC-007
- `kitty-specs/009-ui-import-export/data-model.md` - v3.0 entity schema
- `docs/design/import_export_specification.md` - v3.0 format (from WP01)

**Key Constraints**:
- Sample data must be realistic holiday baking scenario
- All entity types must have test data
- Data must respect referential integrity
- Performance targets apply to typical datasets (<1000 records)

**Existing File**:
- `test_data/sample_data.json` - Current v2.0 format (needs update)

## Subtasks & Detailed Guidance

### Subtask T033 - Update sample_data.json to v3.0 Format

- **Purpose**: Convert existing sample data to v3.0 schema
- **Steps**:
  1. Read current `test_data/sample_data.json`
  2. Add v3.0 header:
     ```json
     {
       "version": "3.0",
       "exported_at": "2025-12-04T00:00:00Z",
       "application": "bake-tracker",
       ...
     }
     ```
  3. Rename/restructure deprecated fields:
     - `bundles` -> `compositions` (restructure relationships)
     - Add `finished_units` array (may need to create from recipe yields)
     - Add `production_records` array (new for Feature 008)
     - Add `package_finished_goods` array (from packages.bundles)
  4. Add `status` field to event assignments (default "pending")
  5. Verify all entity keys match v3.0 specification
- **Files**: `test_data/sample_data.json`
- **Notes**: Reference data-model.md for exact field names

### Subtask T034 - Add Realistic Test Data for All 16 Entity Types

- **Purpose**: Ensure sample data covers complete holiday baking scenario
- **Steps**:
  1. Review existing data and identify gaps
  2. Ensure each entity type has 2-5 records minimum:
     - `unit_conversions`: Common baking conversions (flour, sugar, butter)
     - `ingredients`: Flour, sugar, butter, eggs, chocolate, vanilla, etc.
     - `variants`: King Arthur flour, Domino sugar, etc.
     - `purchases`: Recent purchases with realistic prices
     - `pantry_items`: Current inventory with FIFO dates
     - `recipes`: Chocolate chip cookies, brownies, fudge, etc.
     - `finished_units`: Cookie (per recipe yield), brownie square, etc.
     - `finished_goods`: Holiday cookie box, candy assortment, etc.
     - `compositions`: Link finished units to finished goods
     - `packages`: Holiday gift boxes (small, medium, large)
     - `package_finished_goods`: Package contents
     - `recipients`: Family members (Mom, Dad, Sister, etc.)
     - `events`: Christmas 2025, New Year's 2026
     - `event_recipient_packages`: Gift assignments with status
     - `production_records`: Batch production history
  3. Ensure data tells a coherent story (holiday baking season)
- **Files**: `test_data/sample_data.json`
- **Notes**: Data should be usable for user acceptance testing

### Subtask T035 - Add Integration Test for Sample Data Import

- **Purpose**: Verify sample data imports cleanly (SC-004)
- **Steps**:
  1. Add test in `src/tests/services/test_import_export_service.py`:
     ```python
     def test_sample_data_imports_cleanly():
         """SC-004: Sample data file imports with zero errors."""
         # Setup: Fresh database
         _clear_test_database()

         # Act: Import sample data
         result = import_export_service.import_all_from_json(
             "test_data/sample_data.json",
             mode="replace"
         )

         # Assert: Zero errors
         assert result.error_count == 0
         assert result.imported_count > 0

         # Verify all entity types populated
         for entity in EXPECTED_ENTITIES:
             assert entity in result.entity_counts
             assert result.entity_counts[entity]["imported"] > 0
     ```
  2. Add fixture for clean database state
  3. Run test to verify sample data validity
- **Files**: `src/tests/services/test_import_export_service.py`
- **Notes**: Test should fail if sample_data.json has issues

### Subtask T036 - Add Round-Trip Integrity Test

- **Purpose**: Verify export -> import preserves all data (SC-003)
- **Steps**:
  1. Add test:
     ```python
     def test_round_trip_data_integrity():
         """SC-003: Round-trip achieves 100% data integrity."""
         # Setup: Import sample data
         import_export_service.import_all_from_json(
             "test_data/sample_data.json",
             mode="replace"
         )

         # Get baseline counts
         baseline_counts = _get_all_entity_counts()

         # Export to temp file
         export_path = "/tmp/round_trip_test.json"
         export_result = import_export_service.export_all_to_json(export_path)

         # Clear and re-import
         result = import_export_service.import_all_from_json(
             export_path,
             mode="replace"
         )

         # Verify counts match
         final_counts = _get_all_entity_counts()
         assert baseline_counts == final_counts

         # Verify key field values (spot check)
         _verify_key_records_intact()
     ```
  2. Implement helper functions for count verification
  3. Add spot-check verification for important fields
- **Files**: `src/tests/services/test_import_export_service.py`
- **Notes**: This is a critical data integrity test

### Subtask T037 - Add Performance Test

- **Purpose**: Verify performance meets targets (SC-001, SC-002)
- **Steps**:
  1. Add performance test:
     ```python
     import time

     def test_export_performance_under_30_seconds():
         """SC-001: Export completes in under 30 seconds."""
         # Setup: Ensure some data exists
         _seed_typical_dataset()  # ~1000 records

         start = time.time()
         result = import_export_service.export_all_to_json("/tmp/perf_test.json")
         elapsed = time.time() - start

         assert elapsed < 30, f"Export took {elapsed:.1f}s, expected <30s"

     def test_import_performance_under_60_seconds():
         """SC-002: Import completes in under 60 seconds."""
         start = time.time()
         result = import_export_service.import_all_from_json(
             "test_data/sample_data.json",
             mode="replace"
         )
         elapsed = time.time() - start

         assert elapsed < 60, f"Import took {elapsed:.1f}s, expected <60s"
     ```
  2. Mark as `@pytest.mark.slow` if needed
- **Files**: `src/tests/services/test_import_export_service.py`
- **Notes**: Tests should pass with typical dataset; may skip in CI

### Subtask T038 - Validate All Success Criteria

- **Purpose**: Formal verification of all success criteria
- **Steps**:
  1. Create validation checklist/test:
     ```python
     def test_all_success_criteria():
         """Verify all SC-001 through SC-007 success criteria."""
         # SC-001: Export <30s - covered by test_export_performance
         # SC-002: Import <60s - covered by test_import_performance
         # SC-003: Round-trip 100% - covered by test_round_trip
         # SC-004: Sample data zero errors - covered by test_sample_data
         # SC-005: Non-technical user can backup/restore - manual test
         # SC-006: Error messages user-friendly - manual test
         # SC-007: v3.0 spec covers 100% entities - verify spec completeness

         # Verify SC-007: All entities in spec
         with open("docs/design/import_export_specification.md") as f:
             spec = f.read()

         for entity in EXPECTED_ENTITIES:
             assert entity in spec.lower(), f"Entity {entity} not in spec"
     ```
  2. Document manual test procedures for SC-005, SC-006
  3. Add README or test plan document if needed
- **Files**: `src/tests/services/test_import_export_service.py`
- **Notes**: Some criteria require manual verification

## Test Strategy

- **Automated Tests**: T035-T038 add integration tests
- **Test Command**: `pytest src/tests/services/test_import_export_service.py -v`
- **Manual Tests**:
  - SC-005: Have non-technical user attempt backup/restore
  - SC-006: Intentionally cause errors, verify messages
- **Performance**: Run on representative hardware

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Sample data has referential integrity issues | Import test catches early |
| Performance varies by hardware | Document test hardware specs |
| Round-trip loses precision (floats, dates) | Use exact comparison in tests |

## Definition of Done Checklist

- [ ] T033: sample_data.json updated to v3.0 format
- [ ] T034: All 16 entity types have realistic test data
- [ ] T035: Sample data import test passing
- [ ] T036: Round-trip integrity test passing
- [ ] T037: Performance tests passing (<30s export, <60s import)
- [ ] T038: All success criteria validated
- [ ] Sample data represents realistic holiday baking scenario
- [ ] Tests added to CI pipeline (excluding slow tests if needed)

## Review Guidance

- Verify sample data is realistic and coherent
- Run all integration tests
- Spot-check round-trip integrity
- Review error handling in edge cases

## Activity Log

- 2025-12-04T00:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-04T20:28:43Z – claude – shell_pid=83554 – lane=doing – Started implementation
- 2025-12-04T20:48:01Z – claude – shell_pid=84357 – lane=for_review – Completed all integration tests - T033-T038 done. 39 tests passing.
- 2025-12-04T20:56:57Z – claude-reviewer – shell_pid=85685 – lane=done – Code review APPROVED: sample_data.json v3.0 with all 15 entities, referential integrity verified, performance tests pass, 8 integration tests passing
