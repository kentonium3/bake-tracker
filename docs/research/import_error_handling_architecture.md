# Import Error Handling Architecture Research

**Created:** 2025-12-19
**Purpose:** Technical analysis for Feature 025 (Unified Import Error Handling)
**Status:** Research complete

---

## 1. ImportError Structure Location

**File:** `src/services/catalog_import_service.py:106-114`

```python
@dataclass
class ImportError:
    """Structured error for import failures."""
    entity_type: str  # "ingredients", "products", "recipes"
    identifier: str   # slug, name, or composite key
    error_type: str   # "validation", "fk_missing", "duplicate", "format"
    message: str      # Human-readable error
    suggestion: str   # Actionable fix suggestion
```

This is a **dataclass in the service layer**. Only used by `CatalogImportService` - not shared with the unified import service.

---

## 2. Error Handling Paths

### 2.1 Unified Import (v3.4 - Full Data Import)

| Aspect | Details |
|--------|---------|
| **Entry point** | `src/ui/main_window.py:211` -> `_show_import_dialog()` |
| **Dialog** | `src/ui/import_export_dialog.py:168` -> `ImportDialog` |
| **Service** | `src/services/import_export_service.py` -> `import_all_from_json_v3()` |
| **Error structure** | `ImportResult` class (dict-based errors) |
| **Display** | `ImportResultsDialog` (scrollable, copy-to-clipboard) |
| **Log file** | **YES** - `docs/user_testing/import_YYYY-MM-DD_HHMMSS.log` |

**Error dict structure in ImportResult:**
```python
{
    "record_type": str,
    "record_name": str,
    "error_type": "import_error",
    "message": str
}
```

### 2.2 Catalog Import (Ingredients/Products/Recipes)

| Aspect | Details |
|--------|---------|
| **Entry point** | `src/ui/main_window.py:233` -> `_show_catalog_import_dialog()` |
| **Dialog** | `src/ui/catalog_import_dialog.py:19` -> `CatalogImportDialog` |
| **Service** | `src/services/catalog_import_service.py` -> `import_catalog()` |
| **Error structure** | `ImportError` dataclass (structured with `suggestion` field) |
| **Display** | `messagebox.showinfo()` + `messagebox.showwarning()` (basic) |
| **Log file** | **NO** - errors only shown in messagebox, truncated to 5 |

---

## 3. ImportResultsDialog Details

**File:** `src/ui/import_export_dialog.py:52-166`

### Features
- Scrollable text area (`CTkTextbox` with word wrap)
- Copy to Clipboard button
- Log file path display
- Modal behavior (centered on parent)
- Read-only text widget
- Escape key closes dialog
- Monospace font (Courier)
- Resizable (min 400x300)

### Usage
- **Used by:** Only `ImportDialog` (unified v3.4 import)
- **NOT used by:** `CatalogImportDialog`

### Key Code
```python
class ImportResultsDialog(ctk.CTkToplevel):
    """Dialog for displaying import results with scrolling, copy, and logging."""

    def __init__(self, parent, title: str, summary_text: str, log_path: str = None):
        # ...
        self.text_widget = ctk.CTkTextbox(
            text_frame,
            wrap="word",
            font=ctk.CTkFont(family="Courier", size=12),
        )
```

---

## 4. CatalogImportDialog Details

**File:** `src/ui/catalog_import_dialog.py:19-333`

### Modes Supported
- `ADD_ONLY ("add")` - Create new, skip existing
- `AUGMENT ("augment")` - Update null fields on existing (disabled if Recipes selected)

### Entity Selection Checkboxes
- Ingredients
- Products
- Recipes (disables AUGMENT mode when selected)

### Other Options
- Dry-run preview checkbox

### Current Error Display (Problematic)

```python
def _show_results(self, result):
    # Shows basic summary in messagebox.showinfo()
    messagebox.showinfo(title, summary, parent=self)  # Line 303

    if result.errors:
        self._show_errors(result.errors)  # Separate warning dialog

def _show_errors(self, errors):
    # Limited to first 5 errors, uses messagebox.showwarning()
    for i, err in enumerate(errors[:5]):  # Line 321 - TRUNCATED
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
    )  # Line 329 - NO SCROLL, NO COPY
```

### Problems Identified
1. Errors truncated to first 5 (rest hidden)
2. No scrolling for long error lists
3. No copy-to-clipboard functionality
4. No log file written
5. Suggestion field from ImportError not displayed
6. Two separate messageboxes (info + warning) for results

---

## 5. Error Log Writing

### Unified Import: YES

**Function:** `_write_import_log()` in `src/ui/import_export_dialog.py:29-49`

```python
def _write_import_log(file_path: str, result, summary_text: str) -> str:
    """Write import results to a log file."""
    logs_dir = _get_logs_dir()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    log_file = logs_dir / f"import_{timestamp}.log"

    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"Import Log - {datetime.now().isoformat()}\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Source file: {file_path}\n")
        f.write(f"Import mode: {getattr(result, 'mode', 'unknown')}\n\n")
        f.write("Results:\n")
        f.write("-" * 40 + "\n")
        f.write(summary_text)
        f.write("\n")

    return str(log_file)
```

**Location:** `docs/user_testing/import_YYYY-MM-DD_HHMMSS.log`

### Catalog Import: NO

No log writing functionality exists.

---

## 6. Service Layer Architecture

### Two Separate Services

| Service | File | Purpose |
|---------|------|---------|
| `import_export_service.py` | `src/services/import_export_service.py` | **Full data import/export** - handles inventory, purchases, production runs, events, etc. |
| `catalog_import_service.py` | `src/services/catalog_import_service.py` | **Catalog-only import** - ingredients, products, recipes only (no transactional data) |

### Result Classes Comparison

#### ImportResult (Unified Import)
**File:** `src/services/import_export_service.py:41-165`

```python
class ImportResult:
    """Result of an import operation with per-entity tracking."""

    def __init__(self):
        self.total_records = 0
        self.successful = 0
        self.skipped = 0
        self.failed = 0
        self.errors = []      # List of dicts
        self.warnings = []    # List of dicts
        self.entity_counts: Dict[str, Dict[str, int]] = {}

    def add_error(self, record_type: str, record_name: str, error: str):
        """Record a failed import."""
        self.errors.append({
            "record_type": record_type,
            "record_name": record_name,
            "error_type": "import_error",
            "message": error,
        })

    def get_summary(self) -> str:
        """Get a user-friendly summary string."""
        # Returns formatted text for display
```

#### CatalogImportResult (Catalog Import)
**File:** `src/services/catalog_import_service.py:132-333`

```python
class CatalogImportResult:
    """Result of a catalog import operation with per-entity tracking."""

    def __init__(self):
        self.entity_counts: Dict[str, EntityImportCounts] = {...}
        self.errors: List[ImportError] = []  # List of dataclass instances
        self.warnings: List[str] = []
        self.dry_run: bool = False
        self.mode: str = "add"
        self._augment_details: List[Dict] = []

    def add_error(self, entity_type, identifier, error_type, message, suggestion):
        """Record a failed import with structured error details."""
        self.errors.append(ImportError(
            entity_type=entity_type,
            identifier=identifier,
            error_type=error_type,
            message=message,
            suggestion=suggestion,  # UNIQUE - not in unified import
        ))

    def get_summary(self) -> str:
        """Generate user-friendly summary for CLI/UI display."""

    def get_detailed_report(self) -> str:
        """Generate detailed report with all errors and warnings."""
```

### Error Collection Location

Both services collect errors during import and return them in the result object. The **dialog layer** is responsible for displaying them.

---

## 7. Summary of Gaps (Feature 025 Targets)

| Issue | Unified Import | Catalog Import |
|-------|----------------|----------------|
| Scrollable results | YES | NO (messagebox) |
| Copy to clipboard | YES | NO |
| Log file | YES | NO |
| Shows all errors | YES | NO (truncated to 5) |
| Structured errors with suggestions | NO (dict) | YES (dataclass) |
| Shows suggestions | N/A | NO (field exists but not displayed) |

### Root Cause

The unified import was built with `ImportResultsDialog` from the start. The catalog import was added later (Feature 020) and used basic messageboxes as a shortcut, not applying the same UI pattern.

---

## 8. Recommended Unification Strategy

### Option A: Extend ImportResultsDialog
Modify `ImportResultsDialog` to accept either `ImportResult` or `CatalogImportResult` and render appropriately. Add suggestion display for catalog errors.

### Option B: Create Shared Base Dialog
Create a new `BaseResultsDialog` that both import types use, with configurable rendering for different error structures.

### Option C: Unify Error Structures First
Migrate `ImportResult` to use the `ImportError` dataclass, then use a single dialog implementation.

### Key Requirements for Any Approach
1. All errors visible (scrollable)
2. Copy-to-clipboard for all import types
3. Log file written for all import types
4. Suggestions displayed when available
5. Consistent look and feel across import types

---

## 9. File References

| Component | File Path | Line Numbers |
|-----------|-----------|--------------|
| ImportError dataclass | `src/services/catalog_import_service.py` | 106-114 |
| CatalogImportResult | `src/services/catalog_import_service.py` | 132-333 |
| ImportResult | `src/services/import_export_service.py` | 41-165 |
| ImportResultsDialog | `src/ui/import_export_dialog.py` | 52-166 |
| ImportDialog | `src/ui/import_export_dialog.py` | 168-399 |
| CatalogImportDialog | `src/ui/catalog_import_dialog.py` | 19-333 |
| _write_import_log | `src/ui/import_export_dialog.py` | 29-49 |
| Main window entry points | `src/ui/main_window.py` | 211, 233 |
