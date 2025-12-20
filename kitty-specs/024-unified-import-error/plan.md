# Implementation Plan: Unified Import Error Handling

**Branch**: `024-unified-import-error` | **Date**: 2025-12-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/024-unified-import-error/spec.md`

## Summary

Standardize error display and logging across both import systems (unified and catalog) by:
1. Reusing `ImportResultsDialog` for catalog imports (currently uses messageboxes)
2. Adding log file writing to catalog imports
3. Displaying error suggestions when available
4. Showing relative paths instead of absolute paths

This is a UI-layer refactoring that improves user experience without modifying import logic or data structures.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: CustomTkinter, SQLAlchemy 2.x, pathlib
**Storage**: SQLite with WAL mode (unchanged)
**Testing**: pytest (focus on integration tests for dialog behavior)
**Target Platform**: Desktop (macOS, Windows, Linux)
**Project Type**: Single desktop application
**Performance Goals**: N/A - UI responsiveness only concern
**Constraints**: Must not break existing unified import behavior
**Scale/Scope**: Single-user desktop application

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Improves UX by showing all errors, enabling copy, writing logs |
| II. Data Integrity & FIFO | N/A | No data layer changes |
| III. Future-Proof Schema | N/A | No schema changes |
| IV. Test-Driven Development | PASS | Will add tests for new dialog behavior |
| V. Layered Architecture | PASS | Changes only in UI layer; services unchanged |
| VI. Schema Change Strategy | N/A | No database changes |
| VII. Pragmatic Aspiration | PASS | Simple refactoring that enables future web log viewing |

**Post-Phase 1 Re-check**: All gates still pass. No new violations introduced by design.

## Project Structure

### Documentation (this feature)

```
kitty-specs/024-unified-import-error/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 research decisions
├── data-model.md        # Entity documentation
├── research/
│   ├── evidence-log.csv # Evidence audit trail
│   └── source-register.csv # Source tracking
└── tasks.md             # Phase 2 output (created by /spec-kitty.tasks)
```

### Source Code (files to modify)

```
src/
├── ui/
│   ├── import_export_dialog.py    # Modify: _write_import_log(), ImportResultsDialog
│   └── catalog_import_dialog.py   # Modify: _show_results(), remove _show_errors()
└── services/
    └── catalog_import_service.py  # Modify: get_detailed_report() to include suggestions
```

**Structure Decision**: Single project layout. All changes within existing `src/ui/` and `src/services/` directories.

## Complexity Tracking

*No constitution violations - no justification needed.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Implementation Phases

### Phase 1: Service Layer Enhancement

**Goal**: Update `CatalogImportResult.get_detailed_report()` to format suggestions

**Changes to `src/services/catalog_import_service.py`**:

```python
# In get_detailed_report() method, update error formatting:
for err in self.errors:
    lines.append(f"  - {err.entity_type}: {err.identifier}")
    lines.append(f"    {err.message}")
    if err.suggestion:  # Add suggestion display
        lines.append(f"    Suggestion: {err.suggestion}")
```

**Acceptance Criteria**:
- `get_detailed_report()` includes suggestions when present
- Suggestions are visually distinct (indented, prefixed)
- Empty suggestions produce no extra lines

### Phase 2: Log Writing Generalization

**Goal**: Enable `_write_import_log()` to work with both result types and return relative paths

**Changes to `src/ui/import_export_dialog.py`**:

1. **Update `_write_import_log()` signature and return**:
```python
def _write_import_log(file_path: str, result, summary_text: str) -> str:
    """Write import results to a log file.

    Args:
        file_path: Source file that was imported
        result: ImportResult or CatalogImportResult
        summary_text: Formatted summary text

    Returns:
        Relative path to the created log file (for display)
    """
    logs_dir = _get_logs_dir()
    # ... existing logic ...

    # Return relative path for display
    try:
        return str(log_file.relative_to(Path.cwd()))
    except ValueError:
        return str(log_file)  # Fallback to absolute if not relative
```

2. **Update mode extraction**:
```python
# Handle both result types
mode = getattr(result, 'mode', 'unknown')
```

**Acceptance Criteria**:
- Works with both `ImportResult` and `CatalogImportResult`
- Returns relative path (e.g., `docs/user_testing/import_2025-12-19_143022.log`)
- Falls back to absolute path gracefully on error

### Phase 3: Catalog Import Dialog Refactoring

**Goal**: Replace messageboxes with `ImportResultsDialog`

**Changes to `src/ui/catalog_import_dialog.py`**:

1. **Add import**:
```python
from src.ui.import_export_dialog import ImportResultsDialog, _write_import_log
```

2. **Replace `_show_results()` method**:
```python
def _show_results(self, result: CatalogImportResult):
    """Show import results in scrollable dialog with logging."""
    # Build summary text
    summary_text = result.get_detailed_report()

    if result.dry_run:
        summary_text = "DRY RUN - No changes made\n\n" + summary_text

    # Write log file
    log_path = _write_import_log(self.file_path, result, summary_text)

    # Show results dialog
    title = "Preview Complete" if result.dry_run else "Import Complete"
    results_dialog = ImportResultsDialog(
        self.master,
        title=title,
        summary_text=summary_text,
        log_path=log_path,
    )
    results_dialog.wait_window()

    # Close dialog on success (not dry-run)
    if not result.dry_run:
        self.result = result
        self.destroy()
```

3. **Remove `_show_errors()` method entirely** (no longer needed)

**Acceptance Criteria**:
- All errors visible in scrollable dialog
- Copy to clipboard works
- Log file written to `docs/user_testing/`
- Log path displayed as relative
- Dry-run mode shows "DRY RUN" indicator
- Dialog closes after successful import

### Phase 4: Unified Import Path Verification

**Goal**: Ensure unified import still works correctly with relative path change

**Changes to `src/ui/import_export_dialog.py`**:

Update `ImportDialog._do_import()` to use relative path from `_write_import_log()`:
```python
log_path = _write_import_log(self.file_path, result, summary_text)
# log_path is now relative - no changes needed to ImportResultsDialog
```

**Acceptance Criteria**:
- Unified import behavior unchanged
- Log path displayed as relative (was already absolute, now relative)
- All existing tests pass

## Testing Strategy

### Unit Tests

| Test | Location | Description |
|------|----------|-------------|
| `test_get_detailed_report_with_suggestions` | `src/tests/test_catalog_import_service.py` | Verify suggestions appear in report |
| `test_get_detailed_report_empty_suggestions` | `src/tests/test_catalog_import_service.py` | Verify empty suggestions produce no extra lines |

### Integration Tests

| Test | Description |
|------|-------------|
| Catalog import with errors | Import file with validation errors, verify all visible |
| Catalog import copy to clipboard | Verify clipboard contains all errors and suggestions |
| Catalog import log file | Verify log written with correct format |
| Unified import regression | Verify unified import unchanged |
| Dry-run mode | Verify "DRY RUN" indicator and log writing |

### Manual Testing

| Scenario | Steps | Expected |
|----------|-------|----------|
| Many errors | Import file with 20+ errors | All visible via scrolling |
| Suggestions displayed | Import file with unit validation error | Suggestion shows valid units |
| Log path | Complete import | Relative path shown in dialog |
| Copy functionality | Click "Copy to Clipboard" | All errors in clipboard |

## Files Modified Summary

| File | Changes |
|------|---------|
| `src/services/catalog_import_service.py` | Update `get_detailed_report()` to include suggestions |
| `src/ui/import_export_dialog.py` | Update `_write_import_log()` to return relative path |
| `src/ui/catalog_import_dialog.py` | Replace `_show_results()` and `_show_errors()` with `ImportResultsDialog` usage |

## Dependencies

- **Feature 019**: Unified Import v3.4 - provides `ImportResultsDialog` and `_write_import_log()`
- **Feature 020**: Catalog Import - provides `CatalogImportDialog` and `CatalogImportService`

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Break unified import | Low | High | Test unified import path after all changes |
| Path conversion fails on Windows | Low | Low | Try/except with fallback to absolute |
| Large error lists slow dialog | Low | Low | CTkTextbox handles large text well |

## Success Metrics

Per spec success criteria:
- SC-001: All catalog import errors visible (not truncated to 5)
- SC-002: Copy to clipboard works with single click
- SC-003: Catalog imports write logs to `docs/user_testing/`
- SC-004: Log files contain all errors with suggestions
- SC-005: Error suggestions displayed in UI
- SC-006: Log paths shown as relative
- SC-007: Unified import unchanged
- SC-008: Both ADD_ONLY and AUGMENT modes work
- SC-009: Dry-run mode works with new dialog

## Next Steps

Run `/spec-kitty.tasks` to generate atomic work packages from this plan.
