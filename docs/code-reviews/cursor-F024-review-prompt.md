# Cursor Code Review Prompt - Feature 024: Unified Import Error Handling

## Role

You are a senior software engineer performing an independent code review of Feature 024 (unified-import-error). This feature standardizes error display and logging across both import systems (unified and catalog) by replacing messageboxes with scrollable dialogs, adding log writing, and displaying error suggestions.

## Feature Summary

**Core Changes:**
1. `CatalogImportResult.get_detailed_report()` now includes error suggestions when present
2. `_write_import_log()` returns relative paths instead of absolute paths
3. `CatalogImportDialog._show_results()` replaced to use `ImportResultsDialog`
4. `CatalogImportDialog._show_errors()` method removed entirely
5. Catalog imports now write log files to `docs/user_testing/`

**Scope:**
- Service layer: `catalog_import_service.py` - conditional suggestion formatting
- UI layer: `import_export_dialog.py` - relative path return in `_write_import_log()`
- UI layer: `catalog_import_dialog.py` - `ImportResultsDialog` integration

## Files to Review

### Service Layer (WP01)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/024-unified-import-error/src/services/catalog_import_service.py`
  - `get_summary()` (~line 284-292) - conditional suggestion display
  - `get_detailed_report()` (~line 307-335) - conditional suggestion display

### UI Layer - Log Writing (WP02)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/024-unified-import-error/src/ui/import_export_dialog.py`
  - `_write_import_log()` (~line 29-58) - relative path return with fallback

### UI Layer - Catalog Dialog (WP03)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/024-unified-import-error/src/ui/catalog_import_dialog.py`
  - Import statement (~line 17) - `ImportResultsDialog`, `_write_import_log`
  - `_show_results()` (~line 279-306) - new implementation using ImportResultsDialog
  - Verify `_show_errors()` method is REMOVED

### Specification Documents
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/024-unified-import-error/kitty-specs/024-unified-import-error/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/024-unified-import-error/kitty-specs/024-unified-import-error/plan.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/024-unified-import-error/kitty-specs/024-unified-import-error/data-model.md`

### Architecture Reference
- `/Users/kentgale/Vaults-repos/bake-tracker/docs/design/F024_unified_import_error_handling.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/docs/research/import_error_handling_architecture.md`

## Review Checklist

### 1. Service Layer - Suggestion Formatting (WP01)
- [ ] `get_summary()` only shows suggestion when `error.suggestion` is truthy
- [ ] `get_summary()` formats suggestion as `    Suggestion: {err.suggestion}`
- [ ] `get_detailed_report()` only shows suggestion when `error.suggestion` is truthy
- [ ] `get_detailed_report()` formats suggestion as `    Suggestion: {err.suggestion}`
- [ ] Empty suggestions produce no extra lines in output
- [ ] Indentation matches existing pattern (4 spaces for details)

### 2. Log Writing - Relative Paths (WP02)
- [ ] `_write_import_log()` docstring updated to document relative path return
- [ ] Function uses `getattr(result, 'mode', 'unknown')` for mode extraction (works with both result types)
- [ ] Return statement uses `log_file.relative_to(Path.cwd())`
- [ ] Try/except wraps the relative path conversion
- [ ] Fallback to absolute path on `ValueError`
- [ ] Log file format unchanged (timestamp, source, mode, results)

### 3. Catalog Dialog - ImportResultsDialog Integration (WP03)
- [ ] Import added: `from src.ui.import_export_dialog import ImportResultsDialog, _write_import_log`
- [ ] `_show_results()` uses `result.get_detailed_report()` for summary text
- [ ] `_show_results()` prepends "DRY RUN - No changes made\n\n" when `result.dry_run` is True
- [ ] `_show_results()` calls `_write_import_log()` to write log
- [ ] `_show_results()` creates `ImportResultsDialog` with correct parameters
- [ ] `_show_results()` uses `self.master` as parent (not `self`)
- [ ] `_show_results()` calls `results_dialog.wait_window()`
- [ ] `_show_results()` only destroys dialog when NOT dry-run
- [ ] `_show_errors()` method is COMPLETELY REMOVED
- [ ] No remaining `messagebox.showinfo()` or `messagebox.showwarning()` calls for results

### 4. Functional Requirements Verification
- [ ] FR-001: All catalog import errors visible in scrollable dialog (not truncated to 5)
- [ ] FR-002: CatalogImportDialog uses ImportResultsDialog instead of messagebox
- [ ] FR-003: "Copy to Clipboard" button available (via ImportResultsDialog)
- [ ] FR-004: Log files written to `docs/user_testing/import_YYYY-MM-DD_HHMMSS.log`
- [ ] FR-005: Log files include all errors with suggestions
- [ ] FR-006: Suggestions displayed in UI when present
- [ ] FR-007: Relative paths displayed for log files
- [ ] FR-008: Unified import continues unchanged
- [ ] FR-009: Log file format matches existing format
- [ ] FR-010: `docs/user_testing/` directory created automatically

### 5. Architecture Compliance
- [ ] No business logic added to UI layer
- [ ] No UI imports in service layer
- [ ] Layered architecture preserved (UI -> Services -> Models)
- [ ] No new `session_scope()` calls that could cause nesting issues

## Verification Commands

Run these commands to verify the implementation:

```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/024-unified-import-error

# Verify modules import correctly
python3 -c "
from src.services.catalog_import_service import CatalogImportResult, ImportError
from src.ui.import_export_dialog import ImportResultsDialog, _write_import_log
from src.ui.catalog_import_dialog import CatalogImportDialog
print('All modules import successfully')
"

# Verify suggestion conditional in get_summary()
grep -A 10 "if self.errors:" src/services/catalog_import_service.py | head -15

# Verify suggestion conditional in get_detailed_report()
grep -A 5 "if len(self.errors) > 10:" src/services/catalog_import_service.py

# Verify relative path return in _write_import_log()
grep -A 5 "Return relative path" src/ui/import_export_dialog.py

# Verify ImportResultsDialog import in catalog_import_dialog
grep "from src.ui.import_export_dialog" src/ui/catalog_import_dialog.py

# Verify _show_errors is REMOVED
grep -n "_show_errors" src/ui/catalog_import_dialog.py && echo "ERROR: _show_errors still exists!" || echo "OK: _show_errors removed"

# Verify no messagebox.showinfo/showwarning in _show_results
grep -n "messagebox.show" src/ui/catalog_import_dialog.py

# Run all tests
python3 -m pytest src/tests -v

# Test suggestion formatting
python3 -c "
from src.services.catalog_import_service import CatalogImportResult, ImportError, ImportMode

result = CatalogImportResult()
result.mode = ImportMode.ADD_ONLY

# Error with suggestion
result.add_error('recipe', 'Test Recipe', 'validation', 'Invalid unit', 'Valid units: cup, oz, lb')
# Error without suggestion
result.add_error('recipe', 'No Suggestion', 'validation', 'Another error', '')

report = result.get_summary()
print('=== Summary Report ===')
print(report)

# Verify suggestion appears for first error
assert 'Suggestion: Valid units' in report, 'Suggestion should appear'
# Verify no empty suggestion line for second error
lines = report.split('\n')
suggestion_lines = [l for l in lines if l.strip().startswith('Suggestion:')]
assert len(suggestion_lines) == 1, f'Expected 1 suggestion line, got {len(suggestion_lines)}'
print('\nSuggestion formatting: PASS')
"

# Test relative path return
python3 -c "
from pathlib import Path
import os

# Simulate the relative path logic
log_file = Path('docs/user_testing/test.log')
cwd = Path.cwd()

try:
    relative = str(log_file.relative_to(cwd))
    print(f'Relative path works: {relative}')
except ValueError:
    print('Fallback to absolute path')
"
```

## Key Implementation Patterns

### Conditional Suggestion Pattern (Service Layer)
```python
if error.suggestion:  # Only show suggestion if non-empty
    lines.append(f"    Suggestion: {error.suggestion}")
```

### Relative Path Pattern (UI Layer)
```python
# Return relative path for display
try:
    return str(log_file.relative_to(Path.cwd()))
except ValueError:
    return str(log_file)  # Fallback to absolute if not relative
```

### ImportResultsDialog Usage Pattern (Catalog Dialog)
```python
def _show_results(self, result: CatalogImportResult):
    """Show import results in scrollable dialog with logging."""
    summary_text = result.get_detailed_report()

    if result.dry_run:
        summary_text = "DRY RUN - No changes made\n\n" + summary_text

    log_path = _write_import_log(self.file_path, result, summary_text)

    title = "Preview Complete" if result.dry_run else "Import Complete"
    results_dialog = ImportResultsDialog(
        self.master,  # Use main window as parent, not this dialog
        title=title,
        summary_text=summary_text,
        log_path=log_path,
    )
    results_dialog.wait_window()

    if not result.dry_run:
        self.result = result
        self.destroy()
```

## Output Format

Please output your findings to:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F024-review.md`

Use this format:

```markdown
# Cursor Code Review: Feature 024 - Unified Import Error Handling

**Date:** [DATE]
**Reviewer:** Cursor (AI Code Review)
**Feature:** 024-unified-import-error
**Branch:** 024-unified-import-error

## Summary

[Brief overview of findings]

## Verification Results

### Module Import Validation
- catalog_import_service: [PASS/FAIL]
- import_export_dialog: [PASS/FAIL]
- catalog_import_dialog: [PASS/FAIL]

### Test Results
- pytest result: [PASS/FAIL - X passed, Y skipped, Z failed]

### Code Pattern Validation
- Suggestion conditional (get_summary): [present/missing]
- Suggestion conditional (get_detailed_report): [present/missing]
- Relative path return: [present/missing]
- Try/except fallback: [present/missing]
- ImportResultsDialog integration: [present/missing]
- _show_errors removed: [yes/no]

## Findings

### Critical Issues
[Any blocking issues that must be fixed]

### Warnings
[Non-blocking concerns]

### Observations
[General observations about code quality]

## Files Reviewed

| File | Status | Notes |
|------|--------|-------|
| src/services/catalog_import_service.py | [status] | [notes] |
| src/ui/import_export_dialog.py | [status] | [notes] |
| src/ui/catalog_import_dialog.py | [status] | [notes] |

## Architecture Assessment

### Layered Architecture
[Assessment of UI -> Services -> Models dependency flow]

### Backward Compatibility
[Assessment of unified import path - should be unchanged]

### Error Handling
[Assessment of try/except patterns and edge case handling]

### Session Management
[Assessment of any session_scope patterns - should be none added]

## Functional Requirements Verification

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FR-001: All errors visible | [PASS/FAIL] | [evidence] |
| FR-002: ImportResultsDialog used | [PASS/FAIL] | [evidence] |
| FR-003: Copy to clipboard | [PASS/FAIL] | [evidence] |
| FR-004: Log file written | [PASS/FAIL] | [evidence] |
| FR-005: Log includes all errors | [PASS/FAIL] | [evidence] |
| FR-006: Suggestions displayed | [PASS/FAIL] | [evidence] |
| FR-007: Relative paths | [PASS/FAIL] | [evidence] |
| FR-008: Unified import unchanged | [PASS/FAIL] | [evidence] |
| FR-009: Log format correct | [PASS/FAIL] | [evidence] |
| FR-010: Directory created | [PASS/FAIL] | [evidence] |

## Success Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| SC-001: All errors visible (not truncated to 5) | [PASS/FAIL] | [evidence] |
| SC-002: Copy to clipboard works | [PASS/FAIL] | [evidence] |
| SC-003: Logs written to docs/user_testing/ | [PASS/FAIL] | [evidence] |
| SC-004: Logs contain all errors with suggestions | [PASS/FAIL] | [evidence] |
| SC-005: Suggestions displayed in UI | [PASS/FAIL] | [evidence] |
| SC-006: Log paths shown as relative | [PASS/FAIL] | [evidence] |
| SC-007: Unified import unchanged | [PASS/FAIL] | [evidence] |
| SC-008: ADD_ONLY and AUGMENT modes work | [PASS/FAIL] | [evidence] |
| SC-009: Dry-run mode works | [PASS/FAIL] | [evidence] |

## Conclusion

[APPROVED / APPROVED WITH CHANGES / NEEDS REVISION]

[Final summary and any recommendations]
```

## Additional Context

- The project uses SQLAlchemy 2.x with type hints
- CustomTkinter for UI (CTkTextbox for scrollable text)
- pytest for testing
- The worktree is isolated from main branch
- Layered architecture: UI -> Services -> Models -> Database
- This feature does NOT modify any database schema
- This feature does NOT change import logic or validation rules
- The `_show_errors()` method (truncated to 5 errors, messagebox-based) should be COMPLETELY REMOVED
- Unified import path should be unchanged - only the log path display changes from absolute to relative
- `ImportResultsDialog` is a pre-existing component from Feature 019
- `_write_import_log()` is a pre-existing function from Feature 019
- SQLite unique constraint behavior and session management are NOT relevant to this feature
