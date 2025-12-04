# Quickstart: UI Import/Export Implementation

**Feature**: 009-ui-import-export
**Date**: 2025-12-04

## Overview

This guide provides implementation steps for adding File menu Import/Export functionality with v3.0 schema support.

## Prerequisites

- Features 001-008 complete (stable schema)
- Existing `import_export_service.py` service layer
- CustomTkinter UI framework

## Implementation Steps

### Step 1: Archive v2.0 Specification

```bash
mkdir -p docs/archive
mv docs/design/import_export_specification.md docs/archive/import_export_specification_v2.md
```

### Step 2: Create v3.0 Specification

Create `docs/design/import_export_specification.md` with:
- Version 3.0 header with changelog from v2.0
- All 15 entity definitions (see data-model.md)
- Import dependency order
- JSON examples for each entity
- Validation rules
- v2.0 compatibility notes

### Step 3: Update Service Layer

**File**: `src/services/import_export_service.py`

#### 3.1 Add Mode Parameter

```python
def import_all_from_json(
    file_path: str,
    mode: str = "merge",  # NEW: "merge" or "replace"
    skip_duplicates: bool = True
) -> ImportResult:
    """
    Import all data from JSON file.

    Args:
        file_path: Path to JSON file
        mode: "merge" (skip duplicates) or "replace" (clear then import)
        skip_duplicates: Skip duplicate records (merge mode only)
    """
    if mode == "replace":
        _clear_all_tables()  # NEW: implement table clearing

    # ... existing import logic
```

#### 3.2 Add New Entity Functions

```python
# Export functions
def export_finished_units_to_json() -> List[Dict]:
    """Export all finished units."""

def export_compositions_to_json() -> List[Dict]:
    """Export all compositions."""

def export_production_records_to_json() -> List[Dict]:
    """Export all production records."""

# Import functions
def import_finished_units_from_json(data: List[Dict]) -> ImportResult:
    """Import finished units."""

def import_compositions_from_json(data: List[Dict]) -> ImportResult:
    """Import compositions."""

def import_production_records_from_json(data: List[Dict]) -> ImportResult:
    """Import production records."""
```

#### 3.3 Update Master Export Function

```python
def export_all_to_json(file_path: str) -> ExportResult:
    """Export all data to v3.0 format."""
    data = {
        "version": "3.0",
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "application": "bake-tracker",
        "unit_conversions": export_unit_conversions_to_json(),
        "ingredients": export_ingredients_to_json(),
        "variants": export_variants_to_json(),
        "purchases": export_purchases_to_json(),
        "pantry_items": export_pantry_items_to_json(),
        "recipes": export_recipes_to_json(),
        "finished_units": export_finished_units_to_json(),  # NEW
        "finished_goods": export_finished_goods_to_json(),
        "compositions": export_compositions_to_json(),  # NEW (was bundles)
        "packages": export_packages_to_json(),
        "package_finished_goods": export_package_finished_goods_to_json(),  # NEW
        "recipients": export_recipients_to_json(),
        "events": export_events_to_json(),
        "event_recipient_packages": export_event_recipient_packages_to_json(),
        "production_records": export_production_records_to_json(),  # NEW
    }
    # ... write to file
```

#### 3.4 Add v2.0 Detection

```python
def detect_version(data: Dict) -> str:
    """Detect import file version."""
    if "version" in data:
        return data["version"]
    if "bundles" in data:  # v2.0 had bundles, v3.0 has compositions
        return "2.0"
    return "unknown"

def import_all_from_json(file_path: str, mode: str = "merge") -> ImportResult:
    with open(file_path, 'r') as f:
        data = json.load(f)

    version = detect_version(data)
    if version == "2.0":
        result.add_warning("File is v2.0 format. Some features may not import correctly.")
        data = _migrate_v2_to_v3(data)  # Best-effort migration

    # ... continue with import
```

### Step 4: Add Menu Bar to Main Window

**File**: `src/ui/main_window.py`

```python
import tkinter as tk
from tkinter import filedialog, messagebox

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self._setup_menu_bar()  # NEW
        # ... existing setup

    def _setup_menu_bar(self):
        """Create the application menu bar."""
        self.menu_bar = tk.Menu(self)
        self.config(menu=self.menu_bar)

        # File menu
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="Import Data...", command=self._show_import_dialog)
        file_menu.add_command(label="Export Data...", command=self._show_export_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_exit)
        self.menu_bar.add_cascade(label="File", menu=file_menu)

        # Help menu (existing)
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)

    def _show_import_dialog(self):
        """Show import dialog."""
        from src.ui.import_export_dialog import ImportDialog
        dialog = ImportDialog(self)
        dialog.wait_window()
        if dialog.result:
            self._refresh_all_tabs()

    def _show_export_dialog(self):
        """Show export dialog."""
        from src.ui.import_export_dialog import ExportDialog
        dialog = ExportDialog(self)
        dialog.wait_window()
```

### Step 5: Create Import/Export Dialogs

**File**: `src/ui/import_export_dialog.py` (NEW)

```python
import customtkinter as ctk
from tkinter import filedialog, messagebox
from src.services import import_export_service

class ImportDialog(ctk.CTkToplevel):
    """Dialog for importing data."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Import Data")
        self.geometry("400x300")
        self.result = None

        self._setup_ui()
        self.transient(parent)
        self.grab_set()

    def _setup_ui(self):
        # File selection
        self.file_frame = ctk.CTkFrame(self)
        self.file_frame.pack(fill="x", padx=20, pady=10)

        self.file_label = ctk.CTkLabel(self.file_frame, text="No file selected")
        self.file_label.pack(side="left", fill="x", expand=True)

        self.browse_btn = ctk.CTkButton(
            self.file_frame, text="Browse...", command=self._browse_file
        )
        self.browse_btn.pack(side="right")

        # Mode selection
        self.mode_frame = ctk.CTkFrame(self)
        self.mode_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(self.mode_frame, text="Import Mode:").pack(anchor="w")

        self.mode_var = ctk.StringVar(value="merge")

        ctk.CTkRadioButton(
            self.mode_frame, text="Merge (add new, skip duplicates)",
            variable=self.mode_var, value="merge"
        ).pack(anchor="w", pady=2)

        ctk.CTkRadioButton(
            self.mode_frame, text="Replace (clear all data first)",
            variable=self.mode_var, value="replace"
        ).pack(anchor="w", pady=2)

        # Buttons
        self.btn_frame = ctk.CTkFrame(self)
        self.btn_frame.pack(fill="x", padx=20, pady=20)

        self.import_btn = ctk.CTkButton(
            self.btn_frame, text="Import", command=self._do_import, state="disabled"
        )
        self.import_btn.pack(side="right", padx=5)

        self.cancel_btn = ctk.CTkButton(
            self.btn_frame, text="Cancel", command=self.destroy
        )
        self.cancel_btn.pack(side="right")

    def _browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Import File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            self.file_path = file_path
            self.file_label.configure(text=file_path.split("/")[-1])
            self.import_btn.configure(state="normal")

    def _do_import(self):
        mode = self.mode_var.get()

        if mode == "replace":
            if not messagebox.askyesno(
                "Confirm Replace",
                "This will DELETE all existing data before importing.\n\nAre you sure?",
                parent=self
            ):
                return

        try:
            result = import_export_service.import_all_from_json(
                self.file_path, mode=mode
            )
            messagebox.showinfo("Import Complete", result.get_summary(), parent=self)
            self.result = result
            self.destroy()
        except Exception as e:
            messagebox.showerror("Import Failed", str(e), parent=self)


class ExportDialog(ctk.CTkToplevel):
    """Dialog for exporting data."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Export Data")
        self.geometry("400x200")
        self.result = None

        self._setup_ui()
        self.transient(parent)
        self.grab_set()

    def _setup_ui(self):
        ctk.CTkLabel(
            self, text="Export all data to a JSON file for backup.",
            font=ctk.CTkFont(size=14)
        ).pack(pady=20)

        self.btn_frame = ctk.CTkFrame(self)
        self.btn_frame.pack(fill="x", padx=20, pady=20)

        self.export_btn = ctk.CTkButton(
            self.btn_frame, text="Choose Location & Export...",
            command=self._do_export
        )
        self.export_btn.pack(side="right", padx=5)

        self.cancel_btn = ctk.CTkButton(
            self.btn_frame, text="Cancel", command=self.destroy
        )
        self.cancel_btn.pack(side="right")

    def _do_export(self):
        from datetime import datetime
        default_name = f"bake-tracker-backup-{datetime.now().strftime('%Y-%m-%d')}.json"

        file_path = filedialog.asksaveasfilename(
            title="Export Data",
            defaultextension=".json",
            initialfile=default_name,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            result = import_export_service.export_all_to_json(file_path)
            messagebox.showinfo(
                "Export Complete",
                f"Exported {result.record_count} records to:\n{file_path}",
                parent=self
            )
            self.result = result
            self.destroy()
        except Exception as e:
            messagebox.showerror("Export Failed", str(e), parent=self)
```

### Step 6: Update Sample Data

**File**: `test_data/sample_data.json`

Update to v3.0 format:
1. Add `version: "3.0"` header
2. Rename `bundles` to `compositions`
3. Add `finished_units` array
4. Add `production_records` array
5. Update `packages` to use `package_finished_goods`
6. Add `status` field to event assignments

### Step 7: Add Tests

**File**: `src/tests/services/test_import_export_service.py`

```python
def test_export_v3_format():
    """Verify export produces v3.0 format."""

def test_import_merge_mode():
    """Verify merge mode skips duplicates."""

def test_import_replace_mode():
    """Verify replace mode clears data first."""

def test_import_v2_compatibility():
    """Verify v2.0 files import with warnings."""

def test_round_trip():
    """Verify export -> import preserves data."""
```

## Testing Checklist

- [ ] File menu appears with Import/Export options
- [ ] Export creates valid JSON file with all entities
- [ ] Import Merge mode adds new records, skips duplicates
- [ ] Import Replace mode clears data first
- [ ] v2.0 files import with deprecation warnings
- [ ] Error messages are user-friendly
- [ ] Round-trip test passes (export -> clear -> import -> verify)
- [ ] sample_data.json imports with zero errors

## Key Files Modified

| File | Change |
|------|--------|
| `src/services/import_export_service.py` | Add mode param, new entities, v2.0 detection |
| `src/ui/main_window.py` | Add menu bar |
| `src/ui/import_export_dialog.py` | NEW: Import/Export dialogs |
| `docs/design/import_export_specification.md` | v3.0 spec |
| `docs/archive/import_export_specification_v2.md` | Archived v2.0 |
| `test_data/sample_data.json` | v3.0 format |
