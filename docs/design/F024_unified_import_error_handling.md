# Feature 024: Unified Import Error Handling

**Status:** Ready for Implementation  
**Created:** 2025-12-19  
**Priority:** High (affects heavily-used migration/testing workflows)

---

## Problem Statement

Import error handling is inconsistent between the two import systems:

**Unified Import (v3.4):**
- ✅ Scrollable `ImportResultsDialog` with copy-to-clipboard
- ✅ Writes log files to `docs/user_testing/import_YYYY-MM-DD_HHMMSS.log`
- ❌ Uses simple dict-based errors (no `suggestion` field)

**Catalog Import (ADD_ONLY/AUGMENT modes):**
- ✅ Uses structured `ImportError` dataclass with `suggestion` field
- ❌ Shows errors in basic `messagebox.showwarning()` - truncated to 5 errors
- ❌ No scrolling, no copy-to-clipboard, no log files
- ❌ Doesn't display the `suggestion` field despite collecting it

This makes catalog imports (heavily used for migration/testing) difficult to debug and share errors.

**Example Problem:** User imports products catalog with 18 errors. Current UI shows only first 5 errors in a non-scrollable messagebox with no way to copy them. Remaining 13 errors are hidden with "... and 13 more errors" message. User cannot see full error details or share them for debugging.

---

## Goal

Standardize error display and logging across both import systems to match the best features of each:
- Use `ImportResultsDialog` pattern (scrollable, copyable, logged) everywhere
- Display structured error suggestions when available
- Write consistent log files for all import types
- Show relative paths (not absolute) for log file locations

---

## Technical Context

### Current Architecture

**Two Import Paths:**

1. **Unified Import:** `import_export_service.py` → `ImportDialog` → `ImportResultsDialog`
   - Uses `ImportResult` with dict-based errors
   - Already has logging via `_write_import_log()`
   - Displays results in scrollable dialog with copy button

2. **Catalog Import:** `catalog_import_service.py` → `CatalogImportDialog` → messageboxes
   - Uses `CatalogImportResult` with `ImportError` dataclass
   - No logging, truncated display
   - Shows only first 5 errors in basic messagebox

**Error Structures:**

```python
# catalog_import_service.py (lines 106-114)
@dataclass
class ImportError:
    entity_type: str
    identifier: str
    error_type: str
    message: str
    suggestion: str  # ← Rich, actionable guidance

# import_export_service.py (dict in ImportResult.errors list)
{
    "record_type": str,
    "record_name": str,
    "error_type": "import_error",
    "message": str
    # No suggestion field
}
```

**Reference:** See `docs/research/import_error_handling_architecture.md` for complete technical analysis.

---

## Requirements

### 1. Refactor CatalogImportDialog to Use ImportResultsDialog

**Current code (catalog_import_dialog.py:303-333):**
```python
def _show_results(self, result):
    messagebox.showinfo(title, summary, parent=self)  # Basic modal
    if result.errors:
        self._show_errors(result.errors)  # Separate warning modal

def _show_errors(self, errors):
    for i, err in enumerate(errors[:5]):  # ← TRUNCATED TO 5
        error_lines.append(...)
    messagebox.showwarning(...)  # ← NO SCROLL, NO COPY
```

**Required change:**
- Replace `_show_results()` and `_show_errors()` with call to `ImportResultsDialog`
- Pass `CatalogImportResult` to dialog
- Display **all** errors (not truncated to 5)
- Include full `suggestion` text for each error

---

### 2. Add Log File Writing to Catalog Import

**Reuse existing function:** `_write_import_log()` from `import_export_dialog.py:29-49`

**Log File Location Requirements:**
- Write to `docs/user_testing/import_YYYY-MM-DD_HHMMSS.log` (relative to repo root)
- **Do not** write to user's Documents directory (future UI-configurable setting)
- Display **relative path** in dialog, not absolute path
  - Good: `docs/user_testing/import_2025-12-19_135927.log`
  - Bad: `/Users/kentgale/Vaults-repos/bake-tracker/docs/user_testing/import_2025-12-19_135927.log`

**Log Format Requirements:**

Match the format from unified import (see example below). Include:
- ISO timestamp
- Source file path
- Import mode (add, augment, etc.)
- Summary statistics per entity type
- **All** errors with full context and suggestions
- All warnings

**Example Log Format:**
```
Import Log - 2025-12-19T13:59:27.457897
============================================================

Source file: /Users/kentgale/Vaults-repos/bake-tracker/test_data/sample_data.json
Import mode: augment

Results:
----------------------------------------
============================================================
Import Summary
============================================================
  product: 165 imported, 8 skipped
  recipe: 5 imported, 18 errors

Total Records: 196
Successful:    170
Skipped:       8
Failed:        18

Errors:
  - recipe: Almond Biscotti
    Invalid unit 'whole' for recipe 'Almond Biscotti'.ingredient 'eggs_whole' unit.
    Valid units: count, cup, dozen, each, fl oz, g, gal, kg, l, lb, ml, oz, piece, pt, qt, tbsp, tsp

  - recipe: Butterscotch Pumpkin Cake
    Invalid unit 'whole' for recipe 'Butterscotch Pumpkin Cake'.ingredient 'eggs_whole' unit.
    Valid units: count, cup, dozen, each, fl oz, g, gal, kg, l, lb, ml, oz, piece, pt, qt, tbsp, tsp

Warnings:
  - product: Domino
    Already exists
  - product: Hershey's
    Already exists
============================================================
```

**Implementation notes:**
- The `_write_import_log()` function should return **relative** path for display
- May need to use `pathlib.Path.relative_to()` or store project root reference
- Ensure `_get_logs_dir()` points to `docs/user_testing/` directory

---

### 3. Extend ImportResultsDialog to Display Suggestions

**Current dialog (import_export_dialog.py:52-166):**
- Displays summary text as single string
- No special handling for structured errors with suggestions

**Required enhancement:**

When errors contain `suggestion` field (from `ImportError` dataclass), format them clearly:

```
Error: Invalid unit 'whole' for recipe 'Almond Biscotti'.ingredient 'eggs_whole' unit.
Suggestion: Valid units: count, cup, dozen, each, fl oz, g, gal, kg, l, lb, ml, oz, piece, pt, qt, tbsp, tsp
```

**Implementation approach:**
- Option A: Add optional `format_mode` parameter to `ImportResultsDialog.__init__()`
- Option B: Detect error structure automatically from result object
- Render suggestions with visual separation (indentation, blank line, or prefixing with "Suggestion:")

---

### 4. Optional: Unify Error Structures (Future Enhancement)

**Not required for Feature 024**, but document for future consideration:
- Migrate `ImportResult.errors` from dict to `ImportError` dataclass
- Add `suggestion` field to all error paths in `import_export_service.py`
- This would make both services use identical error structures

**Rationale for deferring:** This is a larger refactoring that touches the unified import service layer. Feature 024 focuses on making catalog import match the UI/logging quality of unified import without breaking the unified import path.

---

## Implementation Plan

### Phase 1: Catalog Import Logging

1. **Extract/generalize `_write_import_log()`** to work with `CatalogImportResult`
   - May need to accept either `ImportResult` or `CatalogImportResult`
   - Ensure it formats suggestions from `ImportError` dataclass
   
2. **Call log writing from `CatalogImportDialog._do_import()`** after import completes
   - Store log path for display in results dialog
   - Ensure path is relative to project root

3. **Update `_get_logs_dir()`** if needed
   - Confirm it returns `docs/user_testing/` path
   - Ensure directory is created if it doesn't exist

### Phase 2: Replace Messageboxes with ImportResultsDialog

1. **Modify `CatalogImportDialog._show_results()`:**
   - Build summary text from `CatalogImportResult.get_detailed_report()`
   - Call `ImportResultsDialog` with summary and log path
   - Remove `messagebox.showinfo()` and `_show_errors()` calls
   - Pass relative log path (not absolute)

2. **Update `CatalogImportResult.get_detailed_report()`:**
   - Format errors to include `suggestion` field
   - Match log file format for consistency
   - Ensure all errors are included (not truncated)

### Phase 3: Enhance ImportResultsDialog for Suggestions

1. **Add logic to detect and format `suggestion` fields**
   - Check if errors have suggestion attribute/key
   - Format with clear visual separation

2. **Apply consistent formatting for both import types**
   - Works with `ImportResult` (dict errors, no suggestions)
   - Works with `CatalogImportResult` (dataclass errors with suggestions)

3. **Test with both import types**
   - Verify unified import still works correctly
   - Verify catalog import shows suggestions
   - Verify copy-to-clipboard includes suggestions

---

## Success Criteria

### Catalog Import:
✅ Shows **all** errors in scrollable dialog (not truncated to 5)  
✅ "Copy to Clipboard" button works  
✅ Writes log file to `docs/user_testing/import_YYYY-MM-DD_HHMMSS.log`  
✅ Displays `suggestion` field from `ImportError` dataclass  
✅ No more `messagebox.showwarning()` calls for errors  
✅ Dialog displays relative path to log file  

### Unified Import:
✅ Continues to work as before  
✅ If suggestions are added to errors in future, dialog displays them  
✅ Displays relative path to log file (not absolute)  

### Log Files:
✅ Same format and location for both import types  
✅ Written to `docs/user_testing/` directory in repo structure (not user Documents)  
✅ Includes all errors (not truncated)  
✅ Includes suggestions when available  
✅ Easily shareable for debugging  

### User Experience:
✅ Consistent look and feel across import types  
✅ All errors visible and copyable  
✅ Easy to find and share log files  
✅ Actionable suggestions displayed when available  

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/ui/catalog_import_dialog.py` | Replace `_show_results()` + `_show_errors()` with `ImportResultsDialog` call; add log writing; pass relative log path |
| `src/ui/import_export_dialog.py` | Enhance `ImportResultsDialog` to format suggestions; update `_write_import_log()` to return relative path; possibly extract to shared utility; ensure `_get_logs_dir()` points to `docs/user_testing/` |
| `src/services/catalog_import_service.py` | Update `CatalogImportResult.get_detailed_report()` to format suggestions for display |

---

## Out of Scope

- Changing import logic or validation rules
- Modifying error collection mechanisms in services
- Unifying `ImportResult` and `CatalogImportResult` classes (future work)
- Adding new import modes or entity types
- Making log file location UI-configurable (future enhancement)
- Writing logs to user Documents directory (deferred until UI config is available)

---

## Testing Checklist

### Catalog Import Testing:
- [ ] Import with 0 errors - shows success dialog with log path
- [ ] Import with 1-5 errors - shows all errors (not truncated)
- [ ] Import with >5 errors - shows all errors in scrollable window
- [ ] Import with suggestions - displays suggestions clearly
- [ ] Copy to clipboard - includes all errors and suggestions
- [ ] Log file written to correct location (`docs/user_testing/`)
- [ ] Log file contains all errors (not truncated)
- [ ] Dialog shows relative path (not absolute)
- [ ] ADD_ONLY mode works with new dialog
- [ ] AUGMENT mode works with new dialog
- [ ] Dry-run mode works with new dialog

### Unified Import Testing:
- [ ] Unified import still works correctly
- [ ] Log files still written to same location
- [ ] Dialog still shows relative path
- [ ] Copy to clipboard still works
- [ ] No regressions in error display

### Log File Testing:
- [ ] Timestamp format is ISO 8601
- [ ] Source file path is included
- [ ] Import mode is included
- [ ] Summary statistics are correct
- [ ] All errors are logged (not truncated)
- [ ] Suggestions are included in log
- [ ] Warnings are included in log
- [ ] Log file is UTF-8 encoded
- [ ] Log path displayed is relative to project root

---

## Reference Files

- **Architecture Research:** `docs/research/import_error_handling_architecture.md`
- **Example Log File:** `docs/user_testing/import_2025-12-19_135927.log` (or similar)
- **Related Feature:** Feature 020 (Catalog Import - original implementation)
- **Related Feature:** Feature 019 (Unified Import v3.4)

---

## Notes for Implementation

1. **Backward Compatibility:** The unified import path must continue to work exactly as before. Only enhance it to support suggestion display if present.

2. **Error Structure Detection:** The dialog should gracefully handle both error structures:
   - Dict-based errors (unified import)
   - Dataclass-based errors with suggestions (catalog import)

3. **Path Handling:** Use `pathlib.Path` for all path operations. Convert to relative paths before displaying to user.

4. **Log Directory Creation:** Ensure `docs/user_testing/` directory exists before writing logs. Create if missing.

5. **Code Reuse:** Look for opportunities to share code between the two import paths, but don't force premature abstraction. The goal is consistent UX, not necessarily identical implementation.

6. **UI Consistency:** The `ImportResultsDialog` appearance should be identical whether called from unified or catalog import.

---

## Future Enhancements (Not Part of F024)

- Add UI configuration for log file location
- Support writing logs to user Documents directory as option
- Unify `ImportResult` and `CatalogImportResult` classes
- Add `suggestion` field to all unified import errors
- Add filtering/search capability in ImportResultsDialog for large error lists
- Support exporting errors to CSV for analysis
