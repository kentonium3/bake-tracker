---
work_package_id: "WP07"
subtasks:
  - "T043"
  - "T044"
  - "T045"
  - "T046"
  - "T047"
  - "T048"
  - "T049"
  - "T050"
  - "T051"
title: "Unified Import Dialog with Context-Rich Purpose"
phase: "Phase 2 - Integration"
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

# Work Package Prompt: WP07 - Unified Import Dialog with Context-Rich Purpose

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Add Context-Rich as 5th purpose type and integrate schema validation into the unified import dialog.

**Success Criteria**:
- Context-Rich appears as 5th radio button option
- aug_*.json files auto-detected as Context-Rich
- Schema validation runs before import (after preprocessing for Context-Rich)
- Validation errors displayed with record numbers and actionable info
- Modal summary shows per-entity counts after import
- All 5 purposes work correctly

## Context & Constraints

**Related Documents**:
- Spec: `kitty-specs/051-import-export-ui-rationalization/spec.md` (US1, US3, US4)
- Plan: `kitty-specs/051-import-export-ui-rationalization/plan.md`

**Dependencies**:
- WP01 (schema_validation_service) for validation
- WP04 (enhanced logging) for comprehensive logs

**Existing Code**:
- `src/ui/import_export_dialog.py` - ImportDialog class (lines 178-731)
- `src/services/enhanced_import_service.py` - detect_format(), import_context_rich_view()

**MVP Note**: This work package is the core of the feature. Completing WP01 → WP02 → WP04 → WP07 delivers the minimum viable product.

## Subtasks & Detailed Guidance

### Subtask T043 - Add Context-Rich radio button as 5th purpose
- **Purpose**: Enable Context-Rich selection in ImportDialog
- **Steps**:
  1. Open `src/ui/import_export_dialog.py`, find ImportDialog._setup_ui()
  2. Current purposes (lines 286-291): backup, catalog, purchases, adjustments
  3. Add 5th tuple: `("context_rich", "Context-Rich", "Import AI-augmented files (aug_*.json)")`
  4. Ensure radio button appears in purpose selection area
  5. Update `_on_purpose_changed()` to handle "context_rich"
- **Files**: `src/ui/import_export_dialog.py`
- **Parallel?**: No (foundation)
- **Notes**: Value should be snake_case: "context_rich"

### Subtask T044 - Add Context-Rich description text
- **Purpose**: Help user understand Context-Rich purpose
- **Steps**:
  1. Description should explain: "Import AI-augmented files (aug_*.json) with preprocessing"
  2. This appears next to radio button like other purposes
  3. Could also add tooltip or info icon
- **Files**: `src/ui/import_export_dialog.py`
- **Parallel?**: No (part of T043)
- **Notes**: Keep concise; longer explanation can be in help docs

### Subtask T045 - Mode selection for Context-Rich
- **Purpose**: Allow add/augment mode for Context-Rich imports
- **Steps**:
  1. When Context-Rich selected, show mode selection options
  2. Reuse `_setup_catalog_options()` or create similar
  3. Options: "Update Existing" (augment), "Add New Only" (add)
  4. Ensure mode passed to import handler
- **Files**: `src/ui/import_export_dialog.py`
- **Parallel?**: No (after T043)
- **Notes**: Context-Rich behaves like Catalog for mode selection

### Subtask T046 - Auto-detect aug_*.json files as Context-Rich
- **Purpose**: Automatically suggest Context-Rich for augmented files
- **Steps**:
  1. In `_detect_format()`, check for aug_*.json filename pattern
  2. Also check for `_meta.editable_fields` in JSON (existing detection)
  3. If detected as context_rich, set `self.purpose_var.set("context_rich")`
  4. Call `_on_purpose_changed()` to update UI
- **Files**: `src/ui/import_export_dialog.py`
- **Parallel?**: No (after T043)
- **Notes**: Filename pattern: `aug_*.json` (e.g., aug_ingredients.json)

### Subtask T047 - Route Context-Rich in _do_import()
- **Purpose**: Handle Context-Rich purpose in import execution
- **Steps**:
  1. Find `_do_import()` method
  2. Add case for `purpose == "context_rich"`
  3. Call new method `_do_context_rich_import()` or similar
  4. This method should:
     - Run preprocessing (existing enhanced_import_service.import_context_rich_view)
     - Pass mode from mode_var
     - Handle result display
- **Files**: `src/ui/import_export_dialog.py`
- **Parallel?**: No (after T045, T046)
- **Notes**: Existing context-rich logic in `_do_catalog_import()` checks detected_format

### Subtask T048 - Integrate schema_validation_service
- **Purpose**: Run schema validation before import
- **Steps**:
  1. Import `schema_validation_service` at top of file
  2. Before executing import, call `validate_import_file(data)`
  3. For Context-Rich: validate AFTER preprocessing (on normalized output)
  4. For other purposes: validate on raw JSON data
  5. If `result.valid == False`, show error dialog and abort
  6. If warnings only, proceed with import
- **Files**: `src/ui/import_export_dialog.py`
- **Parallel?**: Yes (can start once WP01 complete)
- **Notes**: Validation should not block on warnings, only errors

### Subtask T049 - Display validation errors with record numbers
- **Purpose**: Show actionable validation error dialog
- **Steps**:
  1. Create or update error dialog to show:
     - Error count
     - List of errors with: record number, field path, message, expected vs actual
     - Truncate if >10 errors with "...and N more"
  2. Use messagebox.showerror() or custom dialog
  3. Include suggestion to fix errors in source file
- **Files**: `src/ui/import_export_dialog.py`
- **Parallel?**: No (after T048)
- **Notes**: Make errors copy-able for user to share/fix

### Subtask T050 - Modal summary with per-entity counts
- **Purpose**: Show detailed import results in ImportResultsDialog
- **Steps**:
  1. ImportResultsDialog already exists (line 62)
  2. Ensure it displays `result.entity_counts` breakdown
  3. Format: "ingredients: 20 imported, 3 skipped, 0 errors"
  4. Show for each entity type in result
  5. Make sure this dialog is used consistently after all imports
- **Files**: `src/ui/import_export_dialog.py`
- **Parallel?**: Yes (independent of validation)
- **Notes**: Check `ImportResult.get_summary()` for existing formatting

### Subtask T051 - Verify mode selection for both Catalog and Context-Rich
- **Purpose**: Ensure consistent mode UI for both purposes
- **Steps**:
  1. When Catalog selected, mode options appear
  2. When Context-Rich selected, same mode options appear
  3. When other purposes selected, mode options hidden
  4. Test switching between purposes, verify UI updates
- **Files**: `src/ui/import_export_dialog.py`
- **Parallel?**: No (integration test)
- **Notes**: May need to refactor options frame management

## Import Flow Diagram

```
User opens Import Data dialog
    │
    ▼
User clicks Browse, selects file
    │
    ▼
detect_format() analyzes JSON ───► Auto-select purpose
    │
    ▼
User confirms/overrides purpose
    │
    ├─► Backup: _do_backup_restore()
    ├─► Catalog: _do_catalog_import()
    ├─► Purchases: _do_purchases_import()
    ├─► Adjustments: _do_adjustments_import()
    └─► Context-Rich: _do_context_rich_import()
            │
            ▼
        Preprocessing (FK validation)
            │
            ▼
        Schema validation ──► If errors: show dialog, abort
            │
            ▼
        Execute import
            │
            ▼
        Show ImportResultsDialog with counts
            │
            ▼
        Write enhanced log
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Regression in existing purposes | Test all 5 purposes after changes |
| Context-Rich preprocessing fails | Existing logic should handle; add clear error message |
| Validation too strict | Warnings don't block; only errors abort |
| UI state management bugs | Test purpose switching extensively |

## Definition of Done Checklist

- [ ] Context-Rich radio button appears as 5th option
- [ ] Context-Rich description explains the purpose
- [ ] aug_*.json files auto-detected as Context-Rich
- [ ] Mode selection appears for Context-Rich (like Catalog)
- [ ] _do_import() routes to Context-Rich handler
- [ ] Schema validation runs before import execution
- [ ] Validation errors show record numbers and field paths
- [ ] Validation warnings don't block import
- [ ] ImportResultsDialog shows per-entity counts
- [ ] All 5 purposes work correctly (manual testing)

## Review Guidance

**Key checkpoints**:
1. Open Import dialog, verify 5 radio buttons
2. Select aug_ingredients.json, verify auto-detects Context-Rich
3. Import valid Context-Rich file, verify preprocesses and imports
4. Import malformed file, verify validation error with record numbers
5. Check ImportResultsDialog shows per-entity breakdown
6. Test all 5 purposes to ensure no regression

## Activity Log

- 2026-01-13T12:55:00Z - system - lane=planned - Prompt created.
- 2026-01-13T18:40:45Z – claude – lane=doing – Starting implementation of Unified Import Dialog
- 2026-01-13T18:48:18Z – claude – lane=for_review – Implemented unified import dialog with Context-Rich as 5th purpose, schema validation integration, and per-entity result display
- 2026-01-13T20:57:15Z – claude – lane=done – Code review APPROVED by claude - Context-Rich as 5th purpose, aug_*.json auto-detection, schema validation integration, modal summary with per-entity counts
