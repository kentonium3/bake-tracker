---
work_package_id: WP03
title: Catalog Dialog - ImportResultsDialog Integration
lane: done
history:
- timestamp: '2025-12-19T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude-reviewer
assignee: claude
phase: Phase 3 - Catalog Import Dialog Refactoring
review_status: ''
reviewed_by: ''
shell_pid: '77979'
subtasks:
- T004
- T005
- T006
- T007
---

# Work Package Prompt: WP03 - Catalog Dialog - ImportResultsDialog Integration

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Replace messageboxes in `CatalogImportDialog` with `ImportResultsDialog` for scrollable, copyable error display with log writing.

**Success Criteria**:
- All catalog import errors visible in scrollable dialog (not truncated to 5)
- Copy to clipboard button works
- Log file written to `docs/user_testing/`
- Log path displayed as relative
- Dry-run mode shows "DRY RUN" indicator
- Dialog closes after successful import (not dry-run)
- Both ADD_ONLY and AUGMENT modes work with new dialog

## Context & Constraints

**Reference Documents**:
- Feature Spec: `kitty-specs/024-unified-import-error/spec.md` (User Stories 1, 2, 3, 5)
- Implementation Plan: `kitty-specs/024-unified-import-error/plan.md` (Phase 3)
- Data Model: `kitty-specs/024-unified-import-error/data-model.md`

**Architectural Constraints**:
- Must import from `import_export_dialog.py` (same UI layer - acceptable)
- Must use `self.master` as parent for `ImportResultsDialog` (matches existing pattern)
- Must preserve existing dialog close behavior

**Dependencies**:
- **WP01**: `get_detailed_report()` must include suggestions
- **WP02**: `_write_import_log()` must return relative paths

**Current State**:
`CatalogImportDialog` uses two separate messageboxes:
- `messagebox.showinfo()` for summary (line 303)
- `messagebox.showwarning()` for errors, truncated to 5 (lines 318-333)

## Subtasks & Detailed Guidance

### Subtask T004 - Add Imports for ImportResultsDialog

**Purpose**: Import the shared dialog and log writing function from `import_export_dialog.py`.

**File**: `src/ui/catalog_import_dialog.py`

**Steps**:

1. **Add import at top of file** (after existing imports):
   ```python
   from src.ui.import_export_dialog import ImportResultsDialog, _write_import_log
   ```

2. **Verify no circular imports**: Both files are in `src/ui/` - no circular dependency issue.

**Parallel?**: Yes - can be done independently.

### Subtask T005 - Replace _show_results() Method

**Purpose**: Replace the messagebox-based implementation with `ImportResultsDialog`.

**File**: `src/ui/catalog_import_dialog.py`

**Steps**:

1. **Locate `_show_results()` method** (around line 278-316).

2. **Replace the entire method body**:
   ```python
   def _show_results(self, result: CatalogImportResult):
       """Show import results in scrollable dialog with logging."""
       # Build summary text using the enhanced get_detailed_report()
       summary_text = result.get_detailed_report()

       # Prepend dry-run indicator if applicable
       if result.dry_run:
           summary_text = "DRY RUN - No changes made\n\n" + summary_text

       # Write log file and get relative path for display
       log_path = _write_import_log(self.file_path, result, summary_text)

       # Determine dialog title
       title = "Preview Complete" if result.dry_run else "Import Complete"

       # Show results in scrollable dialog
       results_dialog = ImportResultsDialog(
           self.master,  # Use main window as parent, not this dialog
           title=title,
           summary_text=summary_text,
           log_path=log_path,
       )
       results_dialog.wait_window()

       # Close catalog import dialog on successful import (not dry-run)
       if not result.dry_run:
           self.result = result
           self.destroy()
   ```

3. **Key implementation notes**:
   - Use `self.master` as parent (the main window), not `self` (the catalog dialog)
   - This matches the pattern in `ImportDialog._do_import()` (line 340-341)
   - The `wait_window()` call blocks until results dialog is closed
   - Only destroy catalog dialog on non-dry-run success

**Parallel?**: No - main implementation work.

### Subtask T006 - Remove _show_errors() Method

**Purpose**: Delete the now-unused `_show_errors()` method.

**File**: `src/ui/catalog_import_dialog.py`

**Steps**:

1. **Locate `_show_errors()` method** (around line 318-333).

2. **Delete the entire method**:
   ```python
   # DELETE THIS ENTIRE METHOD:
   def _show_errors(self, errors):
       """Show error details in a warning dialog."""
       error_lines = []
       for i, err in enumerate(errors[:5]):
           error_lines.append(
               f"- {err.entity_type}: {err.identifier}\n"
               f"  {err.message}"
           )
       if len(errors) > 5:
           error_lines.append(f"\n... and {len(errors) - 5} more errors")

       messagebox.showwarning(
           f"Import Errors ({len(errors)} total)",
           "\n".join(error_lines),
           parent=self,
       )
   ```

3. **Verify no other callers**: Search for `_show_errors` - should only be called from `_show_results()` which we just replaced.

**Parallel?**: Yes - can be done alongside T004.

### Subtask T007 - Handle Dry-Run Mode

**Purpose**: Ensure dry-run imports show "DRY RUN" indicator and don't close the dialog.

**File**: `src/ui/catalog_import_dialog.py`

**Steps**:

1. **Verify dry-run indicator** (already in T005):
   ```python
   if result.dry_run:
       summary_text = "DRY RUN - No changes made\n\n" + summary_text
   ```

2. **Verify dialog behavior** (already in T005):
   ```python
   # Only close on successful non-dry-run import
   if not result.dry_run:
       self.result = result
       self.destroy()
   ```

3. **Test dry-run mode**:
   - Check "Preview changes before importing (dry-run)" checkbox
   - Click "Preview..."
   - Verify "DRY RUN - No changes made" appears at top
   - Verify dialog shows "Preview Complete" as title
   - Verify catalog import dialog stays open after closing results

**Parallel?**: No - part of T005 implementation.

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Dialog ownership issues | Low | Medium | Use `self.master` as parent (proven pattern) |
| Messagebox import still present | Low | Low | Clean up unused imports after removal |
| Dry-run behavior changes | Low | Medium | Explicit check preserves existing behavior |

## Definition of Done Checklist

- [ ] T004: Imports added for ImportResultsDialog and _write_import_log
- [ ] T005: _show_results() replaced with ImportResultsDialog usage
- [ ] T006: _show_errors() method removed
- [ ] T007: Dry-run mode shows indicator and keeps dialog open
- [ ] Messagebox-based warnings removed
- [ ] All catalog import errors visible (not truncated)
- [ ] Copy to clipboard works
- [ ] Log file written with relative path displayed
- [ ] `tasks.md` updated with status change

## Review Guidance

**Key Checkpoints**:
1. Import a catalog file with 10+ errors - verify all visible via scrolling
2. Click "Copy to Clipboard" - paste and verify all errors included
3. Check log file in `docs/user_testing/` - verify all errors present
4. Verify log path in dialog is relative (not absolute)
5. Test dry-run mode - verify indicator and dialog behavior
6. Test both ADD_ONLY and AUGMENT modes

**Test Approach**:
```bash
# Create a test catalog file with intentional errors
# (e.g., invalid units, missing foreign keys)
# Import via File > Import Catalog
# Verify behavior matches success criteria
```

## Activity Log

- 2025-12-19T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-20T04:50:31Z – claude – shell_pid=75982 – lane=doing – Started implementation
- 2025-12-20T04:52:04Z – claude – shell_pid=76238 – lane=for_review – Ready for review - T004-T007 complete
- 2025-12-20T05:02:37Z – claude-reviewer – shell_pid=77979 – lane=done – Approved: All T004-T007 success criteria met - imports added, _show_results replaced, _show_errors removed, dry-run handling correct
