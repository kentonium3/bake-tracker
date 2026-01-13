---
work_package_id: "WP04"
subtasks:
  - "T022"
  - "T023"
  - "T024"
  - "T025"
  - "T026"
  - "T027"
  - "T028"
  - "T029"
  - "T030"
  - "T031"
title: "Enhanced Import Logging"
phase: "Phase 1 - Dependent Services"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-13T12:55:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - Enhanced Import Logging

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Upgrade import logging to include comprehensive structured sections with resolution suggestions.

**Success Criteria**:
- Import logs written to configurable directory (via preferences_service)
- Logs include all required sections: SOURCE, OPERATION, PREPROCESSING, SCHEMA VALIDATION, IMPORT RESULTS, ERRORS, WARNINGS, SUMMARY, METADATA
- Errors include resolution suggestions
- Plain text format with clear header separators

## Context & Constraints

**Related Documents**:
- Spec: `kitty-specs/051-import-export-ui-rationalization/spec.md` (US5 - Comprehensive Import Logging)
- Plan: `kitty-specs/051-import-export-ui-rationalization/plan.md`
- Data Model: `kitty-specs/051-import-export-ui-rationalization/data-model.md` (Import Log Structure)

**Dependencies**:
- WP02 (preferences_service) for configurable log directory

**Existing Code**:
- `src/ui/import_export_dialog.py:30-59` - current `_write_import_log()` function

## Subtasks & Detailed Guidance

### Subtask T022 - Refactor _write_import_log() for configurable directory
- **Purpose**: Use preferences_service for log directory
- **Steps**:
  1. Import `preferences_service` in `import_export_dialog.py`
  2. Update `_get_logs_dir()` to use `preferences_service.get_logs_directory()`
  3. Handle permission errors gracefully (log warning, fall back to temp)
  4. Keep existing function signature for backward compatibility
- **Files**: `src/ui/import_export_dialog.py`
- **Parallel?**: No (foundation for other subtasks)
- **Notes**: Current hardcoded path: `Path(__file__).parent.parent.parent / "docs" / "user_testing"`

### Subtask T023 - Add SOURCE section
- **Purpose**: Document the imported file details
- **Steps**:
  1. Create section builder helper or inline
  2. Include:
     - File path (absolute)
     - File size (human-readable, e.g., "12,345 bytes")
     - Detected format (from detect_format result)
  3. Format with header separator
- **Files**: `src/ui/import_export_dialog.py`
- **Parallel?**: No (first section)
- **Notes**: Get file size via `Path(file_path).stat().st_size`

### Subtask T024 - Add OPERATION section
- **Purpose**: Document import operation context
- **Steps**:
  1. Include:
     - Purpose (Backup, Catalog, Purchases, Adjustments, Context-Rich)
     - Mode (if applicable: Update Existing / Add New Only)
     - Timestamp (ISO 8601 format)
  2. Format with header separator
- **Files**: `src/ui/import_export_dialog.py`
- **Parallel?**: Yes
- **Notes**: Get mode from `result.mode` if available

### Subtask T025 - Add PREPROCESSING section (for Context-Rich)
- **Purpose**: Document Context-Rich preprocessing results
- **Steps**:
  1. Only include if purpose is Context-Rich
  2. Include:
     - Entity type (e.g., "ingredients")
     - Records extracted count
     - FK validations (passed/failed)
     - Context fields ignored (list)
  3. Format with header separator
- **Files**: `src/ui/import_export_dialog.py`
- **Parallel?**: Yes
- **Notes**: May need to pass preprocessing result to log function

### Subtask T026 - Add SCHEMA VALIDATION section
- **Purpose**: Document validation results
- **Steps**:
  1. Include:
     - Status (PASSED/FAILED)
     - Error count
     - Warning count
     - Warning details (first 5-10 with field paths)
  2. Format with header separator
- **Files**: `src/ui/import_export_dialog.py`
- **Parallel?**: Yes
- **Notes**: Validation result passed from import workflow

### Subtask T027 - Add IMPORT RESULTS section
- **Purpose**: Document per-entity import outcomes
- **Steps**:
  1. Include per-entity breakdown:
     - Entity name
     - Imported count
     - Skipped count
     - Updated count (if applicable)
  2. Use `result.entity_counts` if available
  3. Format with header separator
- **Files**: `src/ui/import_export_dialog.py`
- **Parallel?**: Yes
- **Notes**: `ImportResult.entity_counts` already has this structure

### Subtask T028 - Add ERRORS section
- **Purpose**: Document import errors with resolution suggestions
- **Steps**:
  1. For each error in `result.errors`:
     - Entity name
     - Record identifier/snippet
     - Error message
     - Expected vs actual (if available)
     - Resolution suggestion
  2. Format with indentation for readability
  3. Truncate after first 20 errors with "...and N more"
- **Files**: `src/ui/import_export_dialog.py`
- **Parallel?**: Yes
- **Notes**: Errors already have `suggestion` field

### Subtask T029 - Add WARNINGS section
- **Purpose**: Document non-fatal warnings
- **Steps**:
  1. For each warning in `result.warnings`:
     - Entity name
     - Record identifier
     - Warning message
     - Action taken
  2. Truncate after first 20 with "...and N more"
  3. Format with header separator
- **Files**: `src/ui/import_export_dialog.py`
- **Parallel?**: Yes
- **Notes**: Warnings include unexpected fields, skipped duplicates

### Subtask T030 - Add SUMMARY section
- **Purpose**: High-level outcome summary
- **Steps**:
  1. Include:
     - Total Records processed
     - Successful count
     - Skipped count
     - Failed count
  2. Format prominently (maybe with === borders)
- **Files**: `src/ui/import_export_dialog.py`
- **Parallel?**: No (after result sections)
- **Notes**: Use `result.total_records`, `result.successful`, etc.

### Subtask T031 - Add METADATA section
- **Purpose**: Technical metadata for troubleshooting
- **Steps**:
  1. Include:
     - Application name and version (`APP_NAME`, `APP_VERSION` from constants)
     - Log format version (e.g., "2.0")
     - Duration (if tracked)
  2. Format with header separator
  3. Position at end of log file
- **Files**: `src/ui/import_export_dialog.py`
- **Parallel?**: No (final section)
- **Notes**: May need to track start time for duration

## Log File Format Example

```
================================================================================
IMPORT LOG
================================================================================

--- SOURCE ---
File: /path/to/file.json
Size: 12,345 bytes
Format: Catalog (Normalized v4.0)

--- OPERATION ---
Purpose: Catalog
Mode: Add New Only
Timestamp: 2026-01-13T10:30:00Z

--- SCHEMA VALIDATION ---
Status: PASSED
Errors: 0
Warnings: 2
  - ingredients[5].notes: Field exceeds recommended length
  - ingredients[12].package_type: Unknown value 'bulk'

--- IMPORT RESULTS ---
ingredients: 20 imported, 3 skipped, 0 errors
products: 15 imported, 0 skipped, 0 errors

--- ERRORS ---
(none)

--- WARNINGS ---
- ingredients[3] 'Sugar, Granulated': Skipped (already exists)

================================================================================
SUMMARY
================================================================================
Total Records: 35
Successful: 35
Skipped: 3
Failed: 0

--- METADATA ---
Application: Bake Tracker v0.7.0
Log Version: 2.0
Duration: 1.23s
================================================================================
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Log file write failure | Catch exceptions, show user warning, continue import |
| Large files make huge logs | Truncate error/warning lists after N items |
| Missing result data | Defensive coding; show "(not available)" for missing fields |

## Definition of Done Checklist

- [ ] `_write_import_log()` uses configurable logs directory
- [ ] All 9 sections implemented (SOURCE through METADATA)
- [ ] Errors include resolution suggestions
- [ ] PREPROCESSING section only appears for Context-Rich
- [ ] Log file format matches example above
- [ ] Manual test: perform import, verify log contains all sections

## Review Guidance

**Key checkpoints**:
1. Perform an import and check log file location (should be in configured dir)
2. Verify all sections present with correct headers
3. Intentionally cause errors and verify ERRORS section has suggestions
4. Test Context-Rich import and verify PREPROCESSING section appears
5. Check file is valid plain text (no encoding issues)

## Activity Log

- 2026-01-13T12:55:00Z - system - lane=planned - Prompt created.
- 2026-01-13T18:32:05Z – codex – lane=doing – Started implementation
- 2026-01-13T18:37:47Z – claude – lane=for_review – Implemented enhanced structured logging with 9 sections
- 2026-01-13T20:57:04Z – claude – lane=done – Code review APPROVED by claude - Enhanced logging with 9 sections (SOURCE, OPERATION, PREPROCESSING, SCHEMA VALIDATION, IMPORT RESULTS, ERRORS, WARNINGS, SUMMARY, METADATA)
