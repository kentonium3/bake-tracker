# Work Packages: Unified Import Error Handling

**Inputs**: Design documents from `kitty-specs/024-unified-import-error/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md

**Tests**: No explicit testing work requested. Manual verification included in WP04.

**Organization**: 9 subtasks (`T001`-`T009`) roll up into 4 work packages (`WP01`-`WP04`). Each work package is independently deliverable and aligned with a plan phase.

**Prompt Files**: Each work package references a matching prompt file in `kitty-specs/024-unified-import-error/tasks/planned/`.

## Subtask Format: `[Txxx] [P?] Description`
- **[P]** indicates the subtask can proceed in parallel (different files/components).
- Paths relative to project root.

---

## Work Package WP01: Service Layer - Suggestion Formatting (Priority: P1)

**Goal**: Update `CatalogImportResult.get_detailed_report()` to include suggestion text in error output.
**Independent Test**: Call `get_detailed_report()` on a result with errors that have suggestions; verify suggestions appear in output with "Suggestion:" prefix.
**Prompt**: `kitty-specs/024-unified-import-error/tasks/planned/WP01-service-suggestion-formatting.md`
**User Stories**: US4 (Display Error Suggestions)

### Included Subtasks
- [x] T001 Update `get_detailed_report()` error formatting to include suggestions in `src/services/catalog_import_service.py`

### Implementation Notes
1. Locate `get_detailed_report()` method in `CatalogImportResult` class
2. In the error loop, after appending the error message, add conditional suggestion formatting:
   ```python
   if err.suggestion:
       lines.append(f"    Suggestion: {err.suggestion}")
   ```
3. Ensure empty suggestions produce no extra output lines

### Parallel Opportunities
- None - single file change.

### Dependencies
- None (starting package).

### Risks & Mitigations
- **Risk**: Breaking existing callers of `get_detailed_report()`
- **Mitigation**: Method signature unchanged; only output format enhanced

---

## Work Package WP02: Log Writing - Relative Path Support (Priority: P1)

**Goal**: Update `_write_import_log()` to return relative paths for UI display and work with both result types.
**Independent Test**: Call `_write_import_log()` and verify returned path is relative (e.g., `docs/user_testing/import_...`), not absolute.
**Prompt**: `kitty-specs/024-unified-import-error/tasks/planned/WP02-log-writing-relative-paths.md`
**User Stories**: US3 (Log Catalog Import Results)

### Included Subtasks
- [x] T002 Update `_write_import_log()` return value to relative path in `src/ui/import_export_dialog.py`
- [x] T003 [P] Add try/except fallback for path conversion edge cases

### Implementation Notes
1. After writing log file, convert absolute path to relative:
   ```python
   try:
       return str(log_file.relative_to(Path.cwd()))
   except ValueError:
       return str(log_file)  # Fallback to absolute
   ```
2. Update docstring to document return type as "relative path for display"
3. Existing callers (`ImportDialog`) will automatically receive relative paths

### Parallel Opportunities
- T003 (fallback handling) can be done alongside T002 as they're in the same function.

### Dependencies
- None - can proceed in parallel with WP01.

### Risks & Mitigations
- **Risk**: Path conversion fails on Windows with different drives
- **Mitigation**: Try/except with fallback to absolute path

---

## Work Package WP03: Catalog Dialog - ImportResultsDialog Integration (Priority: P1) MVP

**Goal**: Replace messageboxes in `CatalogImportDialog` with `ImportResultsDialog` for scrollable, copyable error display with log writing.
**Independent Test**: Import a catalog file with 10+ errors; verify all errors visible in scrollable dialog, copy works, log file written, relative path displayed.
**Prompt**: `kitty-specs/024-unified-import-error/tasks/planned/WP03-catalog-dialog-integration.md`
**User Stories**: US1 (View All Errors), US2 (Copy Errors), US3 (Log Results), US5 (Maintain Compatibility)

### Included Subtasks
- [x] T004 Add imports for `ImportResultsDialog` and `_write_import_log` from `import_export_dialog`
- [x] T005 Replace `_show_results()` method with `ImportResultsDialog` usage
- [x] T006 Remove `_show_errors()` method (no longer needed)
- [x] T007 Handle dry-run mode with "DRY RUN" indicator prefix

### Implementation Notes
1. Add import at top of `src/ui/catalog_import_dialog.py`:
   ```python
   from src.ui.import_export_dialog import ImportResultsDialog, _write_import_log
   ```
2. Replace `_show_results()` method body:
   - Build summary using `result.get_detailed_report()`
   - Prepend "DRY RUN - No changes made\n\n" if `result.dry_run`
   - Call `_write_import_log()` to get log path
   - Create `ImportResultsDialog` with title, summary, log_path
   - Handle dialog close and window destruction
3. Delete `_show_errors()` method entirely
4. Remove `messagebox` usage for results display

### Parallel Opportunities
- T004, T006 can be done in parallel with T005, T007.

### Dependencies
- Depends on WP01 (for suggestion formatting in `get_detailed_report()`)
- Depends on WP02 (for relative path from `_write_import_log()`)

### Risks & Mitigations
- **Risk**: Dialog ownership issues (parent window reference)
- **Mitigation**: Use `self.master` as parent (matches existing `ImportDialog` pattern)

---

## Work Package WP04: Verification and Polish (Priority: P1)

**Goal**: Verify unified import still works, run manual test scenarios, ensure no regressions.
**Independent Test**: Perform unified import via File > Import Data; verify behavior identical to before.
**Prompt**: `kitty-specs/024-unified-import-error/tasks/planned/WP04-verification-and-polish.md`
**User Stories**: US5 (Maintain Unified Import Compatibility)

### Included Subtasks
- [x] T008 Verify unified import path still works with relative path change
- [x] T009 Run manual test scenarios per spec (many errors, copy, suggestions, log paths, dry-run)

### Implementation Notes
1. **Unified Import Verification**:
   - Launch app, File > Import Data
   - Import a valid backup file
   - Confirm `ImportResultsDialog` appears as before
   - Confirm log path now shows as relative
   - Confirm copy-to-clipboard works

2. **Manual Test Scenarios**:
   - Import catalog with 20+ errors → all visible via scrolling
   - Import catalog with suggestion-bearing errors → suggestions displayed
   - Click "Copy to Clipboard" → all errors in clipboard
   - Verify log file in `docs/user_testing/` with all errors
   - Test dry-run mode → "DRY RUN" indicator visible
   - Test both ADD_ONLY and AUGMENT modes

### Parallel Opportunities
- T008 and T009 can run in parallel as independent verification activities.

### Dependencies
- Depends on WP01, WP02, WP03 (all implementation complete).

### Risks & Mitigations
- **Risk**: Subtle regression in unified import
- **Mitigation**: Explicit verification step before marking feature complete

---

## Dependency & Execution Summary

```
WP01 (Service) ──┐
                 ├──> WP03 (Dialog Integration) ──> WP04 (Verification)
WP02 (Logging) ──┘
```

- **Sequence**: WP01 and WP02 can run in parallel → WP03 depends on both → WP04 is final verification
- **Parallelization**: WP01 and WP02 are fully independent (different files)
- **MVP Scope**: WP01 + WP02 + WP03 = minimum viable feature; WP04 = verification/polish

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Update get_detailed_report() for suggestions | WP01 | P1 | No |
| T002 | Update _write_import_log() return to relative | WP02 | P1 | No |
| T003 | Add try/except fallback for path conversion | WP02 | P1 | Yes |
| T004 | Add imports for ImportResultsDialog | WP03 | P1 | Yes |
| T005 | Replace _show_results() method | WP03 | P1 | No |
| T006 | Remove _show_errors() method | WP03 | P1 | Yes |
| T007 | Handle dry-run mode indicator | WP03 | P1 | No |
| T008 | Verify unified import regression | WP04 | P1 | Yes |
| T009 | Run manual test scenarios | WP04 | P1 | Yes |

---

## Success Criteria Mapping

| Success Criterion | Work Package | Subtask(s) |
|-------------------|--------------|------------|
| SC-001: All errors visible | WP03 | T005 |
| SC-002: Copy to clipboard | WP03 | T005 |
| SC-003: Log files written | WP03 | T005 |
| SC-004: Suggestions in logs | WP01 | T001 |
| SC-005: Suggestions in UI | WP01, WP03 | T001, T005 |
| SC-006: Relative log paths | WP02 | T002, T003 |
| SC-007: Unified import unchanged | WP04 | T008 |
| SC-008: ADD_ONLY/AUGMENT work | WP04 | T009 |
| SC-009: Dry-run works | WP03 | T007 |
