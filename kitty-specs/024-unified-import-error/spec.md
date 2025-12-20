# Feature Specification: Unified Import Error Handling

**Feature Branch**: `024-unified-import-error`
**Created**: 2025-12-19
**Status**: Draft
**Input**: User description: "See docs/design/F024_unified_import_error_handling.md for the feature description."

## Problem Statement

Import error handling is inconsistent between the two import systems:

- **Unified Import (v3.4)**: Has scrollable `ImportResultsDialog` with copy-to-clipboard and log file writing, but uses simple dict-based errors without suggestions.
- **Catalog Import (ADD_ONLY/AUGMENT modes)**: Has structured `ImportError` dataclass with actionable suggestions, but shows errors in basic `messagebox.showwarning()` truncated to 5 errors with no scrolling, no copy-to-clipboard, and no log files.

**Example Problem**: User imports products catalog with 18 errors. Current UI shows only first 5 errors in a non-scrollable messagebox with no way to copy them. Remaining 13 errors are hidden with "... and 13 more errors" message.

## User Scenarios & Testing

### User Story 1 - View All Catalog Import Errors (Priority: P1)

When a catalog import (ingredients, products, or recipes) encounters errors, the user needs to see ALL errors in a scrollable dialog so they can identify and fix every issue in their import file.

**Why this priority**: This is the core problem - users cannot see all their errors. Without this, debugging imports is impossible for files with more than 5 errors.

**Independent Test**: Can be fully tested by importing a catalog file with 10+ errors and verifying all errors are visible in a scrollable window.

**Acceptance Scenarios**:

1. **Given** a catalog JSON file with 18 validation errors, **When** the user imports via File > Import Catalog, **Then** all 18 errors are displayed in a scrollable dialog (not truncated to 5).

2. **Given** a catalog import with errors, **When** the user views the results dialog, **Then** each error shows its entity type, identifier, error message, and suggestion (if available).

3. **Given** a catalog import completes (with or without errors), **When** the results dialog appears, **Then** the messagebox-style warnings are no longer used.

---

### User Story 2 - Copy Catalog Import Errors (Priority: P1)

Users need to copy all error details to share with support or paste into documentation for debugging.

**Why this priority**: Tied with P1 - copying errors is essential for sharing and debugging. A scrollable list you cannot copy is only half the solution.

**Independent Test**: Can be fully tested by importing a file with errors, clicking "Copy to Clipboard", and pasting to verify all errors are included.

**Acceptance Scenarios**:

1. **Given** a catalog import results dialog showing errors, **When** the user clicks "Copy to Clipboard", **Then** all errors (including suggestions) are copied to the system clipboard.

2. **Given** errors were copied to clipboard, **When** the user pastes into a text editor, **Then** the text is properly formatted and readable.

---

### User Story 3 - Log Catalog Import Results (Priority: P2)

Users need catalog imports to write log files for post-import analysis and debugging, matching the unified import behavior.

**Why this priority**: Important for debugging but secondary to seeing/copying errors in the UI. Users can work around missing logs by copying from the dialog.

**Independent Test**: Can be fully tested by performing a catalog import and verifying a log file appears in `docs/user_testing/`.

**Acceptance Scenarios**:

1. **Given** a catalog import completes, **When** the results dialog is shown, **Then** a log file is written to `docs/user_testing/import_YYYY-MM-DD_HHMMSS.log`.

2. **Given** a catalog import with 18 errors, **When** the log file is written, **Then** all 18 errors are included (not truncated).

3. **Given** a catalog import with suggestion-bearing errors, **When** the log file is written, **Then** suggestions are included for each error.

4. **Given** a log file is written, **When** the path is displayed in the dialog, **Then** it shows a relative path (e.g., `docs/user_testing/import_...`) not an absolute path.

---

### User Story 4 - Display Error Suggestions (Priority: P2)

The catalog import service already collects actionable suggestions for each error (e.g., "Valid units: cup, oz, lb..."). Users need to see these suggestions in the UI.

**Why this priority**: Suggestions exist in the data but are not displayed. This adds significant debugging value with minimal effort.

**Independent Test**: Can be fully tested by importing a file with a unit validation error and verifying the suggestion shows valid unit options.

**Acceptance Scenarios**:

1. **Given** a catalog import error with a suggestion field, **When** displayed in the results dialog, **Then** the suggestion is shown with clear visual separation (e.g., "Suggestion: ...").

2. **Given** a catalog import error without a suggestion field (unified import style), **When** displayed in the results dialog, **Then** only the error message is shown (no empty "Suggestion:" line).

---

### User Story 5 - Maintain Unified Import Compatibility (Priority: P1)

The existing unified import (v3.4) must continue to work exactly as before. Any enhancements to `ImportResultsDialog` must not break the unified import path.

**Why this priority**: Critical - cannot break working functionality.

**Independent Test**: Can be fully tested by performing a unified import and verifying behavior is unchanged.

**Acceptance Scenarios**:

1. **Given** a unified import (File > Import Data), **When** import completes, **Then** the ImportResultsDialog works exactly as before.

2. **Given** a unified import, **When** log files are written, **Then** they continue to work as before.

3. **Given** the unified import system adds suggestion fields to errors in the future, **When** displayed in ImportResultsDialog, **Then** suggestions are shown appropriately.

---

### Edge Cases

- What happens when a catalog import has 0 errors? Dialog shows success summary with log path.
- What happens when a catalog import has 100+ errors? All errors are visible via scrolling.
- What happens when the `docs/user_testing/` directory doesn't exist? It is created automatically.
- What happens during a dry-run catalog import? Results show "DRY RUN" indicator, log is still written.
- What happens if log file cannot be written (permissions)? Graceful error handling, import still succeeds.

## Requirements

### Functional Requirements

- **FR-001**: CatalogImportDialog MUST display all import errors in a scrollable dialog (not truncated to 5).
- **FR-002**: CatalogImportDialog MUST use ImportResultsDialog (or equivalent) instead of messagebox.showwarning() for error display.
- **FR-003**: CatalogImportDialog MUST provide a "Copy to Clipboard" button that copies all errors and suggestions.
- **FR-004**: CatalogImportDialog MUST write log files to `docs/user_testing/import_YYYY-MM-DD_HHMMSS.log`.
- **FR-005**: Log files MUST include all errors (not truncated), with suggestions when available.
- **FR-006**: ImportResultsDialog MUST display the `suggestion` field from ImportError dataclass when present.
- **FR-007**: ImportResultsDialog MUST display relative paths for log files (not absolute paths).
- **FR-008**: Unified import (ImportDialog) MUST continue to work unchanged.
- **FR-009**: Log file format MUST match the existing unified import log format (see design doc for example).
- **FR-010**: The `docs/user_testing/` directory MUST be created automatically if it doesn't exist.

### Key Entities

- **ImportResultsDialog**: UI component for displaying scrollable import results with copy-to-clipboard. Currently used by unified import only.
- **CatalogImportDialog**: UI component for catalog import that currently uses messageboxes. Will be modified to use ImportResultsDialog.
- **ImportError**: Structured dataclass with entity_type, identifier, error_type, message, and suggestion fields. Already exists in catalog_import_service.
- **CatalogImportResult**: Result object from catalog import service. Has get_detailed_report() method.
- **ImportResult**: Result object from unified import service. Uses dict-based errors.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All catalog import errors are visible (100% of errors, not truncated to 5).
- **SC-002**: Users can copy all error details to clipboard with a single click.
- **SC-003**: Catalog imports write log files to `docs/user_testing/` directory.
- **SC-004**: Log files contain all errors with suggestions (matching unified import format).
- **SC-005**: Error suggestions are displayed when available in the UI.
- **SC-006**: Log paths are displayed as relative paths in the dialog.
- **SC-007**: Unified import continues to function identically to current behavior.
- **SC-008**: Both ADD_ONLY and AUGMENT catalog import modes work with the new dialog.
- **SC-009**: Dry-run mode works with the new dialog and writes logs.

## Assumptions

1. The existing `_write_import_log()` function can be generalized to work with both `ImportResult` and `CatalogImportResult`.
2. The `docs/user_testing/` directory is the correct location for all import logs (production and testing).
3. Users prefer relative paths over absolute paths for log file display.
4. The `CatalogImportResult.get_detailed_report()` method can be updated to include suggestions without breaking other callers.

## Out of Scope

- Changing import logic or validation rules
- Modifying error collection mechanisms in services
- Unifying `ImportResult` and `CatalogImportResult` classes
- Adding new import modes or entity types
- Making log file location UI-configurable
- Writing logs to user Documents directory
- Adding filtering/search in ImportResultsDialog for large error lists
- Exporting errors to CSV

## Dependencies

- Feature 020: Catalog Import (original implementation) - provides CatalogImportDialog and CatalogImportService
- Feature 019: Unified Import v3.4 - provides ImportResultsDialog and _write_import_log()

## Reference Files

- **Architecture Research**: `docs/research/import_error_handling_architecture.md`
- **Design Document**: `docs/design/F024_unified_import_error_handling.md`
- **Related Feature 020**: Catalog Import original implementation
- **Related Feature 019**: Unified Import v3.4
