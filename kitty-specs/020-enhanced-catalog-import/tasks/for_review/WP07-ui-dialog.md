---
work_package_id: "WP07"
subtasks:
  - "T050"
  - "T051"
  - "T052"
  - "T053"
  - "T054"
  - "T055"
  - "T056"
  - "T057"
  - "T058"
  - "T059"
  - "T060"
  - "T061"
title: "UI Dialog"
phase: "Phase 3 - Interface"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "56445"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-14T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 - UI Dialog

## IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.
- **Mark as acknowledged**: Update `review_status: acknowledged` when addressing feedback.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Create CatalogImportDialog and integrate with File menu.

**Success Criteria**:
- File > Import Catalog... opens dialog
- Dialog has file picker, mode selection, entity checkboxes, dry-run option
- AUGMENT disabled when Recipes selected
- Import button changes to "Preview..." when dry-run checked
- Results dialog shows counts per entity with expandable errors
- Affected UI tabs refresh after successful import

---

## Context & Constraints

**Reference Documents**:
- `kitty-specs/020-enhanced-catalog-import/spec.md` - FR-015 through FR-021
- `src/ui/import_export_dialog.py` - Pattern reference for dialog structure
- `src/ui/main_window.py` - Menu structure reference

**Prerequisites**:
- WP05 complete (`import_catalog()` coordinator function)

**UI Framework**: CustomTkinter

---

## Subtasks & Detailed Guidance

### T050 - Create CatalogImportDialog base structure

**Purpose**: Establish dialog class following existing ImportDialog pattern.

**Steps**:
1. Create `src/ui/catalog_import_dialog.py`
2. Class structure:
   ```python
   """
   Catalog Import Dialog for importing ingredients, products, and recipes.
   """

   from tkinter import filedialog, messagebox
   import customtkinter as ctk

   from src.services.catalog_import_service import (
       import_catalog,
       CatalogImportError,
   )


   class CatalogImportDialog(ctk.CTkToplevel):
       """Dialog for importing catalog data from a JSON file."""

       def __init__(self, parent):
           super().__init__(parent)
           self.title("Import Catalog")
           self.geometry("550x500")
           self.resizable(False, False)

           self.result = None
           self.file_path = None

           self._setup_ui()

           # Modal behavior
           self.transient(parent)
           self.grab_set()

           # Center on parent
           self.update_idletasks()
           x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
           y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
           self.geometry(f"+{x}+{y}")
   ```

**Files**: `src/ui/catalog_import_dialog.py`

**Reference**: See `ImportDialog` in `src/ui/import_export_dialog.py` lines 16-103

---

### T051 - Implement file picker

**Purpose**: Allow user to select JSON file.

**Steps**:
1. In `_setup_ui()`, add file selection section:
   ```python
   # File selection frame
   file_frame = ctk.CTkFrame(self)
   file_frame.pack(fill="x", padx=20, pady=10)

   ctk.CTkLabel(file_frame, text="File:").pack(anchor="w", padx=10, pady=(10, 5))

   file_inner = ctk.CTkFrame(file_frame, fg_color="transparent")
   file_inner.pack(fill="x", padx=10, pady=(0, 10))

   self.file_entry = ctk.CTkEntry(file_inner, width=350, state="readonly")
   self.file_entry.pack(side="left", padx=(0, 10))

   browse_btn = ctk.CTkButton(
       file_inner,
       text="Browse...",
       width=80,
       command=self._browse_file,
   )
   browse_btn.pack(side="left")
   ```
2. Browse handler:
   ```python
   def _browse_file(self):
       file_path = filedialog.askopenfilename(
           title="Select Catalog File",
           filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
           parent=self,
       )
       if file_path:
           self.file_path = file_path
           self.file_entry.configure(state="normal")
           self.file_entry.delete(0, "end")
           self.file_entry.insert(0, file_path)
           self.file_entry.configure(state="readonly")
   ```

**Files**: `src/ui/catalog_import_dialog.py`

---

### T052 - Implement mode radio buttons

**Purpose**: Let user select Add Only or Augment mode.

**Steps**:
1. Add mode selection frame:
   ```python
   # Mode selection frame
   mode_frame = ctk.CTkFrame(self)
   mode_frame.pack(fill="x", padx=20, pady=10)

   ctk.CTkLabel(
       mode_frame,
       text="Import Mode:",
       font=ctk.CTkFont(weight="bold"),
   ).pack(anchor="w", padx=10, pady=(10, 5))

   self.mode_var = ctk.StringVar(value="add")

   self.add_radio = ctk.CTkRadioButton(
       mode_frame,
       text="Add Only (create new, skip existing)",
       variable=self.mode_var,
       value="add",
   )
   self.add_radio.pack(anchor="w", padx=20, pady=2)

   self.augment_radio = ctk.CTkRadioButton(
       mode_frame,
       text="Augment (update null fields on existing)",
       variable=self.mode_var,
       value="augment",
   )
   self.augment_radio.pack(anchor="w", padx=20, pady=(2, 10))
   ```

**Files**: `src/ui/catalog_import_dialog.py`

---

### T053 - Implement entity checkboxes

**Purpose**: Let user select which entity types to import.

**Steps**:
1. Add entity selection frame:
   ```python
   # Entity selection frame
   entity_frame = ctk.CTkFrame(self)
   entity_frame.pack(fill="x", padx=20, pady=10)

   ctk.CTkLabel(
       entity_frame,
       text="Entities to Import:",
       font=ctk.CTkFont(weight="bold"),
   ).pack(anchor="w", padx=10, pady=(10, 5))

   self.ingredients_var = ctk.BooleanVar(value=True)
   self.products_var = ctk.BooleanVar(value=True)
   self.recipes_var = ctk.BooleanVar(value=True)

   ctk.CTkCheckBox(
       entity_frame,
       text="Ingredients",
       variable=self.ingredients_var,
   ).pack(anchor="w", padx=20, pady=2)

   ctk.CTkCheckBox(
       entity_frame,
       text="Products",
       variable=self.products_var,
   ).pack(anchor="w", padx=20, pady=2)

   self.recipes_checkbox = ctk.CTkCheckBox(
       entity_frame,
       text="Recipes",
       variable=self.recipes_var,
       command=self._on_recipe_toggle,
   )
   self.recipes_checkbox.pack(anchor="w", padx=20, pady=(2, 10))
   ```

**Files**: `src/ui/catalog_import_dialog.py`

---

### T054 - Disable Augment when Recipes selected

**Purpose**: AUGMENT mode not supported for recipes; disable it when Recipes checked.

**Steps**:
1. Add toggle handler:
   ```python
   def _on_recipe_toggle(self):
       if self.recipes_var.get():
           # Recipes selected - force Add Only mode
           if self.mode_var.get() == "augment":
               self.mode_var.set("add")
           self.augment_radio.configure(state="disabled")
       else:
           self.augment_radio.configure(state="normal")
   ```
2. Also check at import time in case user somehow bypasses

**Files**: `src/ui/catalog_import_dialog.py`

---

### T055 - Implement dry-run checkbox with button label change

**Purpose**: Preview changes before committing.

**Steps**:
1. Add dry-run checkbox:
   ```python
   # Dry-run checkbox
   self.dry_run_var = ctk.BooleanVar(value=False)
   ctk.CTkCheckBox(
       self,
       text="Preview changes before importing (dry-run)",
       variable=self.dry_run_var,
       command=self._on_dry_run_toggle,
   ).pack(anchor="w", padx=20, pady=10)
   ```
2. Toggle handler:
   ```python
   def _on_dry_run_toggle(self):
       if self.dry_run_var.get():
           self.import_btn.configure(text="Preview...")
       else:
           self.import_btn.configure(text="Import")
   ```

**Files**: `src/ui/catalog_import_dialog.py`

---

### T056 - Implement import execution and progress indication

**Purpose**: Execute import and show progress.

**Steps**:
1. Add status label and import button:
   ```python
   # Status label
   self.status_label = ctk.CTkLabel(
       self,
       text="",
       font=ctk.CTkFont(size=11),
       text_color="gray",
   )
   self.status_label.pack(pady=5)

   # Button frame
   btn_frame = ctk.CTkFrame(self, fg_color="transparent")
   btn_frame.pack(fill="x", padx=20, pady=20)

   self.import_btn = ctk.CTkButton(
       btn_frame,
       text="Import",
       width=100,
       command=self._do_import,
   )
   self.import_btn.pack(side="right", padx=(10, 0))

   cancel_btn = ctk.CTkButton(
       btn_frame,
       text="Cancel",
       width=100,
       fg_color="gray",
       command=self.destroy,
   )
   cancel_btn.pack(side="right")
   ```
2. Import handler:
   ```python
   def _do_import(self):
       if not self.file_path:
           messagebox.showwarning("No File", "Please select a file.", parent=self)
           return

       # Build entity list
       entities = []
       if self.ingredients_var.get():
           entities.append("ingredients")
       if self.products_var.get():
           entities.append("products")
       if self.recipes_var.get():
           entities.append("recipes")

       if not entities:
           messagebox.showwarning("No Entities", "Select at least one entity type.", parent=self)
           return

       # Show progress
       action = "Previewing" if self.dry_run_var.get() else "Importing"
       self.status_label.configure(text=f"{action}... Please wait.")
       self.import_btn.configure(state="disabled")
       self.config(cursor="wait")
       self.update()

       try:
           result = import_catalog(
               self.file_path,
               mode=self.mode_var.get(),
               entities=entities,
               dry_run=self.dry_run_var.get(),
           )
           self._show_results(result)
       except CatalogImportError as e:
           messagebox.showerror("Import Error", str(e), parent=self)
       except Exception as e:
           messagebox.showerror("Error", f"Unexpected error: {e}", parent=self)
       finally:
           self.status_label.configure(text="")
           self.import_btn.configure(state="normal")
           self.config(cursor="")
   ```

**Files**: `src/ui/catalog_import_dialog.py`

---

### T057 - Create results summary dialog

**Purpose**: Display import results with counts per entity.

**Steps**:
1. Create result display method:
   ```python
   def _show_results(self, result):
       """Show import results in a message box or separate dialog."""
       title = "Preview Complete" if result.dry_run else "Import Complete"

       # Build summary
       lines = []
       for entity, counts in result.entity_counts.items():
           parts = []
           if counts.get("added", 0) > 0:
               parts.append(f"{counts['added']} added")
           if counts.get("augmented", 0) > 0:
               parts.append(f"{counts['augmented']} augmented")
           if counts.get("skipped", 0) > 0:
               parts.append(f"{counts['skipped']} skipped")
           if counts.get("failed", 0) > 0:
               parts.append(f"{counts['failed']} failed")
           if parts:
               lines.append(f"{entity.title()}: {', '.join(parts)}")

       summary = "\n".join(lines) if lines else "No records processed."

       if result.has_errors:
           error_count = sum(
               c.get("failed", 0) for c in result.entity_counts.values()
           )
           summary += f"\n\n{error_count} error(s) occurred. Check details."

       messagebox.showinfo(title, summary, parent=self)

       if not result.dry_run and not result.has_errors:
           self.result = result
           self.destroy()
   ```

**Files**: `src/ui/catalog_import_dialog.py`

---

### T058 - Add expandable Details section for errors

**Purpose**: Show full error details when requested.

**Steps**:
1. For MVP, can use separate dialog or scrollable textbox
2. Option A: Simple error listing in message box (for errors < 5)
3. Option B: Create ResultsDialog class with scrollable text area
4. Minimum viable: Show first 5 errors in message, add "See console for more"

**Simplified approach**:
```python
if result.errors:
    error_lines = []
    for i, err in enumerate(result.errors[:5]):
        error_lines.append(
            f"- {err['entity_type']}: {err['identifier']}\n"
            f"  {err['message']}"
        )
    if len(result.errors) > 5:
        error_lines.append(f"\n... and {len(result.errors) - 5} more errors")

    messagebox.showwarning(
        "Import Errors",
        "\n".join(error_lines),
        parent=self,
    )
```

**Files**: `src/ui/catalog_import_dialog.py`

---

### T059 - Modify main_window.py to add menu item

**Purpose**: Add "Import Catalog..." to File menu.

**Steps**:
1. Locate File menu creation in `main_window.py`
2. Add separator and new menu item:
   ```python
   # After existing Import Data... and Export Data... items
   file_menu.add_separator()
   file_menu.add_command(
       label="Import Catalog...",
       command=self._open_catalog_import_dialog
   )
   ```

**Files**: `src/ui/main_window.py`

---

### T060 - Wire menu item to open dialog

**Purpose**: Create handler method.

**Steps**:
1. Add import at top of file:
   ```python
   from src.ui.catalog_import_dialog import CatalogImportDialog
   ```
2. Add handler method:
   ```python
   def _open_catalog_import_dialog(self):
       dialog = CatalogImportDialog(self)
       self.wait_window(dialog)
       if dialog.result:
           self._refresh_after_import()
   ```

**Files**: `src/ui/main_window.py`

---

### T061 - Refresh affected tabs after import

**Purpose**: Update UI to show newly imported data.

**Steps**:
1. Create refresh method:
   ```python
   def _refresh_after_import(self):
       """Refresh tabs that may have been affected by catalog import."""
       # Find and refresh relevant tabs
       # This depends on the tab implementation
       # Common pattern: tabs have a refresh() method

       # Example if tabs are stored as attributes:
       if hasattr(self, 'ingredients_tab'):
           self.ingredients_tab.refresh()
       if hasattr(self, 'recipes_tab'):
           self.recipes_tab.refresh()
   ```
2. Investigate actual tab structure in main_window.py

**Files**: `src/ui/main_window.py`

---

## Test Strategy

**Manual Testing Required** (UI tests):

1. **Basic Flow**:
   - Launch app
   - File > Import Catalog...
   - Verify dialog opens centered on main window
   - Click Browse, select JSON file
   - Verify file path appears in entry
   - Click Import
   - Verify results dialog shows

2. **Mode Toggle**:
   - Check Recipes checkbox
   - Verify Augment radio becomes disabled
   - Uncheck Recipes
   - Verify Augment radio becomes enabled

3. **Dry-Run Toggle**:
   - Check "Preview changes" checkbox
   - Verify button text changes to "Preview..."
   - Uncheck
   - Verify button text changes back to "Import"

4. **Error Handling**:
   - Click Import without selecting file
   - Verify warning appears
   - Select invalid JSON file
   - Verify error message

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Tab refresh method doesn't exist | Investigate actual implementation, add if needed |
| Dialog not modal | Verify transient() and grab_set() work |
| Large error list overflows | Limit display to 5, show count |

---

## Definition of Done Checklist

- [ ] T050: CatalogImportDialog class created
- [ ] T051: File picker working
- [ ] T052: Mode radio buttons working
- [ ] T053: Entity checkboxes working
- [ ] T054: Augment disabled when Recipes selected
- [ ] T055: Dry-run checkbox changes button label
- [ ] T056: Import executes with progress
- [ ] T057: Results dialog shows counts
- [ ] T058: Error details visible
- [ ] T059: Menu item added
- [ ] T060: Menu item opens dialog
- [ ] T061: Tabs refresh after import
- [ ] Manual testing complete
- [ ] `tasks.md` updated with completion status

---

## Review Guidance

**Reviewer Checkpoints**:
1. Dialog follows ImportDialog pattern
2. AUGMENT disabled correctly for Recipes
3. Dry-run clearly indicated in button and output
4. Modal behavior works (can't interact with main window)
5. Tab refresh triggers correctly

---

## Activity Log

- 2025-12-14T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-15T03:05:59Z – claude – shell_pid=56445 – lane=doing – Started implementation
- 2025-12-15T03:08:13Z – claude – shell_pid=56445 – lane=for_review – Ready for review
