# Data Model (Discovery Draft)

This feature modifies UI layer behavior and does not introduce new database entities. The data model describes the existing structures that the feature interacts with.

## Entities

### Entity: ImportError (Dataclass)

- **Description**: Structured error from catalog import operations with actionable suggestions
- **Location**: `src/services/catalog_import_service.py:106-114`
- **Attributes**:
  - `entity_type` (str) - Category: "ingredients", "products", "recipes"
  - `identifier` (str) - Unique key: slug, name, or composite key
  - `error_type` (str) - Classification: "validation", "fk_missing", "duplicate", "format"
  - `message` (str) - Human-readable error description
  - `suggestion` (str) - Actionable fix guidance (currently not displayed in UI)
- **Identifiers**: Composite of (entity_type, identifier) for deduplication
- **Lifecycle Notes**: Created during import validation, consumed by UI for display

### Entity: CatalogImportResult (Class)

- **Description**: Aggregated result of catalog import operation with per-entity tracking
- **Location**: `src/services/catalog_import_service.py:132-333`
- **Key Attributes**:
  - `entity_counts` (Dict[str, EntityImportCounts]) - Per-entity statistics
  - `errors` (List[ImportError]) - All import errors with suggestions
  - `warnings` (List[str]) - Non-blocking issues
  - `dry_run` (bool) - Whether this was a preview operation
  - `mode` (str) - "add" or "augment"
- **Key Methods**:
  - `get_summary()` - User-friendly summary for CLI/UI
  - `get_detailed_report()` - Full report with errors (needs enhancement for suggestions)
- **Lifecycle Notes**: Created by `import_catalog()`, consumed by `CatalogImportDialog`

### Entity: ImportResult (Class)

- **Description**: Result of unified import operation with dict-based errors
- **Location**: `src/services/import_export_service.py:41-165`
- **Key Attributes**:
  - `total_records` (int) - Total records processed
  - `successful` (int) - Successfully imported count
  - `skipped` (int) - Skipped (duplicate) count
  - `failed` (int) - Failed import count
  - `errors` (List[dict]) - Error dicts with record_type, record_name, message
  - `warnings` (List[dict]) - Warning dicts
  - `entity_counts` (Dict[str, Dict[str, int]]) - Per-entity breakdown
- **Key Methods**:
  - `get_summary()` - Formatted summary text for display
- **Lifecycle Notes**: Created by `import_all_from_json_v3()`, consumed by `ImportDialog`

### Entity: EntityImportCounts (Dataclass)

- **Description**: Per-entity import statistics
- **Location**: `src/services/catalog_import_service.py:117-124`
- **Attributes**:
  - `added` (int) - New records created
  - `skipped` (int) - Existing records skipped
  - `failed` (int) - Records that failed validation
  - `augmented` (int) - Records updated in AUGMENT mode

## Relationships

| Source | Relation | Target | Cardinality | Notes |
|--------|----------|--------|-------------|-------|
| CatalogImportResult | contains | ImportError | 1:N | Aggregates all errors from import |
| CatalogImportResult | contains | EntityImportCounts | 1:N | One per entity type processed |
| ImportResult | contains | error dict | 1:N | Dict-based errors (no suggestion field) |

## UI Components (Modified)

### ImportResultsDialog

- **Location**: `src/ui/import_export_dialog.py:52-166`
- **Current Usage**: Only by `ImportDialog` (unified import)
- **Feature 024 Change**: Also used by `CatalogImportDialog` (catalog import)
- **Enhancement**: Display `suggestion` field when present in error text

### CatalogImportDialog

- **Location**: `src/ui/catalog_import_dialog.py:19-333`
- **Current Behavior**: Uses `messagebox.showinfo()` + `messagebox.showwarning()`
- **Feature 024 Change**: Use `ImportResultsDialog` instead

## Validation & Governance

- **Data quality requirements**: All errors must include entity_type, identifier, and message; suggestion may be empty string but should be meaningful when populated
- **Compliance considerations**: None (no PII in error messages)
- **Source of truth**: Service layer generates errors; UI layer displays them unchanged

## Log File Structure

### Format (existing, to be preserved)

```
Import Log - {ISO timestamp}
============================================================

Source file: {path}
Import mode: {mode}

Results:
----------------------------------------
{summary text from get_summary() or get_detailed_report()}
```

### Location

- Path: `docs/user_testing/import_YYYY-MM-DD_HHMMSS.log`
- Created by: `_write_import_log()` in `src/ui/import_export_dialog.py`
- Display: Relative path in UI, absolute path in file system
