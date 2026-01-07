---
work_package_id: "WP03"
subtasks:
  - "T012"
  - "T013"
  - "T014"
  - "T015"
title: "Event Export/Import v4.0"
phase: "Phase 1 - Core Schema Upgrade"
lane: "for_review"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-06T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Event Export/Import v4.0

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Add `output_mode` field to event export
- Add `output_mode` field to event import
- Validate output_mode matches target types (bundled needs assembly_targets, bulk_count needs production_targets)
- Unit tests verify export/import and validation

**Success Criteria**:
- Export event with output_mode="bundled", verify field in JSON
- Import event with output_mode, verify field in database
- Import event with mismatched mode/targets, verify warning logged

## Context & Constraints

**Related Documents**:
- `kitty-specs/040-import-export-v4/spec.md` - User Story 2 acceptance criteria
- `kitty-specs/040-import-export-v4/data-model.md` - Event export schema
- `kitty-specs/040-import-export-v4/research.md` - Key decision D2

**Key Constraints**:
- Event.output_mode is nullable enum: bulk_count, bundled, packaged
- EventAssemblyTarget and EventProductionTarget already exported in v3.6
- Validation should warn (not error) for mismatches

**File to Modify**: `src/services/import_export_service.py`

## Subtasks & Detailed Guidance

### Subtask T012 - Export output_mode for events

**Purpose**: Include F039 output_mode field in event export.

**Steps**:
1. Locate event export function (likely `export_events_to_json()` or within `export_all_to_json()`)
2. Add to event dict:
   ```python
   event_dict["output_mode"] = event.output_mode.value if event.output_mode else None
   ```
3. Handle null case gracefully

**Files**: `src/services/import_export_service.py`
**Parallel?**: Yes - independent of import

**Notes**:
- Check `src/models/event.py` for OutputMode enum definition
- Enum values: "bulk_count", "bundled", "packaged"

### Subtask T013 - Import output_mode for events

**Purpose**: Read output_mode from JSON and set on Event model.

**Steps**:
1. Locate event import function
2. Read and validate output_mode:
   ```python
   from src.models.event import OutputMode

   output_mode_str = event_data.get("output_mode")
   if output_mode_str:
       try:
           event.output_mode = OutputMode(output_mode_str)
       except ValueError:
           result.add_error("event", event_data.get("name"),
               f"Invalid output_mode: {output_mode_str}")
           continue
   else:
       event.output_mode = None  # Keep as null if not specified
   ```

**Files**: `src/services/import_export_service.py`
**Parallel?**: Yes - independent of export

### Subtask T014 - Validation: output_mode vs targets

**Purpose**: Warn if output_mode doesn't match the type of targets present.

**Steps**:
1. After importing event and its targets:
2. Validation logic:
   ```python
   if event.output_mode == OutputMode.BUNDLED:
       if not event_data.get("event_assembly_targets"):
           result.add_warning("event", event_data.get("name"),
               "output_mode='bundled' but no event_assembly_targets provided")

   if event.output_mode == OutputMode.BULK_COUNT:
       if not event_data.get("event_production_targets"):
           result.add_warning("event", event_data.get("name"),
               "output_mode='bulk_count' but no event_production_targets provided")
   ```
3. Use warnings, not errors - allow import to continue

**Files**: `src/services/import_export_service.py`
**Parallel?**: No - depends on T013

**Notes**:
- Check if ImportResult has `add_warning()` method, if not add it or use `add_error()` with lower severity

### Subtask T015 - Unit tests for event export/import

**Purpose**: Verify output_mode export/import and validation work correctly.

**Steps**:
1. Create test class `TestEventExportImportV4` in test file
2. Test cases:
   - `test_export_event_with_output_mode`: Create event with output_mode=bundled, verify export
   - `test_export_event_without_output_mode`: Event with null output_mode exports correctly
   - `test_import_event_with_output_mode`: Import JSON with output_mode, verify database
   - `test_import_event_invalid_output_mode`: Import with bad value, verify error
   - `test_import_event_bundled_without_targets`: Verify warning logged
   - `test_import_event_roundtrip`: Export then import, verify identical

**Files**: `src/tests/services/test_import_export_service.py`
**Parallel?**: No - tests after implementation

## Test Strategy

**Required Tests**:
```bash
pytest src/tests/services/test_import_export_service.py::TestEventExportImportV4 -v
```

**Test Data**:
- Create Event with output_mode=OutputMode.BUNDLED and assembly_targets
- Create Event with output_mode=OutputMode.BULK_COUNT and production_targets
- Create Event with null output_mode

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Existing events have null output_mode | Handle gracefully, export as null |
| Missing warning method on ImportResult | Add method or use existing error mechanism |
| Enum case sensitivity | Use enum value directly, validate before conversion |

## Definition of Done Checklist

- [x] T012: output_mode exported for events
- [x] T013: output_mode imported for events
- [x] T014: Validation warns on mode/target mismatch
- [x] T015: All unit tests pass
- [x] Round-trip export -> import preserves output_mode

## Review Guidance

- Verify null handling for existing events without output_mode
- Check warning messages are informative
- Confirm enum values match exactly: "bulk_count", "bundled" (Note: no "packaged" value in OutputMode enum)

## Activity Log

- 2026-01-06T12:00:00Z - system - lane=planned - Prompt created.
- 2026-01-07T03:12:46Z – system – shell_pid= – lane=doing – Moved to doing
- 2026-01-07T03:25:00Z – claude – shell_pid=89028 – lane=doing – Completed T012-T015: Added output_mode export/import, validation warnings for mismatched mode/targets, and 6 unit tests. All tests passing.
- 2026-01-07T03:16:03Z – system – shell_pid= – lane=for_review – Moved to for_review
