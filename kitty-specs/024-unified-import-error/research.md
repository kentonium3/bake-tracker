# Research Decision Log

Document the outcomes of Phase 0 discovery work. Capture every clarification resolved and the supporting evidence that backs each decision.

## Summary

- **Feature**: 024-unified-import-error
- **Date**: 2025-12-19
- **Researchers**: Claude Code (lead agent)
- **Open Questions**: None - all decisions confirmed during planning interrogation

## Decisions & Rationale

| Decision | Rationale | Evidence | Status |
|----------|-----------|----------|--------|
| Reuse `ImportResultsDialog` for catalog import | Dialog already has scrolling, copy-to-clipboard, log path display - no need to create new component | E1: `src/ui/import_export_dialog.py:52-166` | final |
| Generalize `_write_import_log()` in place | Both dialogs are in same UI layer; simpler than extracting to utility module | E2: Design doc recommendation, Section 2 | final |
| Display relative paths for log files | User-friendly, avoids exposing system-specific absolute paths | E3: FR-007 in spec, user feedback | final |
| Format suggestions with "Suggestion:" prefix | Clear visual separation without requiring UI changes | E4: Design doc Section 3 | final |
| Defer error structure unification | Focus on UX consistency, not service refactoring; out of scope per spec | E5: Spec "Out of Scope" section | final |
| Log to `docs/user_testing/` directory | Matches existing unified import behavior; relative to project root | E6: Existing `_get_logs_dir()` function | final |

## Evidence Highlights

### E1: ImportResultsDialog Already Has Required Features

From `src/ui/import_export_dialog.py:52-166`:
- Scrollable `CTkTextbox` with word wrap
- Copy to Clipboard button with `clipboard_append()`
- Log file path display with gray styling
- Modal behavior, escape key closes, resizable

### E2: Log Writing Function Is Simple and Suitable for Extension

From `src/ui/import_export_dialog.py:29-49`:
- `_write_import_log()` takes `file_path`, `result`, `summary_text`
- Uses `getattr(result, 'mode', 'unknown')` - already handles different result types
- Returns absolute path string - needs update to return relative path

### E3: CatalogImportResult Has Rich Error Structure

From `src/services/catalog_import_service.py:106-114`:
```python
@dataclass
class ImportError:
    entity_type: str   # "ingredients", "products", "recipes"
    identifier: str    # slug, name, or composite key
    error_type: str    # "validation", "fk_missing", "duplicate", "format"
    message: str       # Human-readable error
    suggestion: str    # Actionable fix suggestion  <-- NOT DISPLAYED
```

### E4: Current Catalog Import Truncates Errors

From `src/ui/catalog_import_dialog.py:321-333`:
- `errors[:5]` - Only shows first 5 errors
- `messagebox.showwarning()` - No scrolling, no copy
- Suggestion field is ignored in display

### E5: CatalogImportResult Has get_detailed_report() Method

From `src/services/catalog_import_service.py` - this method exists but doesn't include suggestions. Will need update to format suggestions.

### E6: Unified Import Already Writes Logs Correctly

Log format from existing logs:
```
Import Log - 2025-12-19T13:59:27.457897
============================================================

Source file: /path/to/file.json
Import mode: augment

Results:
----------------------------------------
[summary text here]
```

## Risks / Concerns

1. **Regression Risk**: Changes to `ImportResultsDialog` could break unified import path
   - **Mitigation**: All changes are additive (optional suggestion display); test both paths

2. **Path Conversion Edge Cases**: `Path.relative_to()` may fail if paths are on different drives (Windows)
   - **Mitigation**: Use try/except with fallback to absolute path; document limitation

## Next Actions

1. Update `CatalogImportResult.get_detailed_report()` to include suggestions in output
2. Modify `_write_import_log()` to accept either result type and return relative path
3. Replace `CatalogImportDialog._show_results()` to use `ImportResultsDialog`
4. Test both import paths end-to-end

> Research complete. All decisions validated during planning interrogation with user.
