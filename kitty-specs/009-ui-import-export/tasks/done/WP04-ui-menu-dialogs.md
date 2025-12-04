---
work_package_id: "WP04"
subtasks:
  - "T023"
  - "T024"
  - "T025"
  - "T026"
  - "T027"
  - "T028"
  - "T029"
  - "T030"
  - "T031"
  - "T032"
title: "UI - Menu Bar and Dialogs"
phase: "Phase 3 - UI Layer"
lane: "done"
assignee: "claude"
agent: "claude-reviewer"
shell_pid: "85463"
review_status: "approved"
reviewed_by: "claude-reviewer"
history:
  - timestamp: "2025-12-04T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - UI - Menu Bar and Dialogs

## Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- **Primary Objective**: Add File menu with Import/Export dialogs to the main window
- **Success Criteria**:
  - File menu visible in application menu bar
  - "Import Data..." opens import dialog with mode selection
  - "Export Data..." opens export dialog with file save
  - Import mode selection: Merge or Replace (FR-013)
  - Replace mode shows confirmation dialog (FR-013b)
  - Success/error messages are user-friendly (SC-006)
  - Progress indication for large datasets
  - Application tabs refresh after successful import

## Context & Constraints

**Prerequisite Documents**:
- `kitty-specs/009-ui-import-export/spec.md` - FR-001 through FR-013b
- `kitty-specs/009-ui-import-export/quickstart.md` - UI code examples
- `kitty-specs/009-ui-import-export/research.md` - Menu implementation decision

**Key Constraints**:
- Use tkinter `Menu` widget for menu bar (compatible with CustomTkinter)
- Use `CTkToplevel` for dialogs
- Architecture: UI layer must NOT contain business logic
- Error messages must be user-friendly (no stack traces)
- Primary user is non-technical

**Existing Code Reference**:
- `src/ui/main_window.py` - Main application window
- `src/ui/migration_wizard_dialog.py` - Dialog pattern to follow
- `src/services/import_export_service.py` - Service functions to call

## Subtasks & Detailed Guidance

### Subtask T023 - Add Menu Bar to main_window.py

- **Purpose**: Create application menu bar with File menu (FR-001)
- **Steps**:
  1. Open `src/ui/main_window.py`
  2. Add imports: `import tkinter as tk`
  3. In `__init__` or setup method, add menu bar:
     ```python
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
     ```
  4. Call `_setup_menu_bar()` from `__init__`
  5. Add stub methods `_show_import_dialog()` and `_show_export_dialog()`
- **Files**: `src/ui/main_window.py`
- **Notes**: Menu bar uses native tkinter, not CustomTkinter (per research.md)

### Subtask T024 - Create ImportDialog Class [PARALLEL]

- **Purpose**: Dialog for importing data with mode selection (FR-002, FR-013)
- **Steps**:
  1. Create new file `src/ui/import_export_dialog.py`
  2. Add `ImportDialog(ctk.CTkToplevel)` class:
     ```python
     class ImportDialog(ctk.CTkToplevel):
         def __init__(self, parent):
             super().__init__(parent)
             self.title("Import Data")
             self.geometry("450x350")
             self.result = None
             self.file_path = None

             self._setup_ui()
             self.transient(parent)
             self.grab_set()
     ```
  3. Implement `_setup_ui()` with:
     - File selection frame with Browse button
     - Mode selection radio buttons (Merge/Replace)
     - Import and Cancel buttons
  4. Add `_browse_file()` method using `filedialog.askopenfilename()`
- **Files**: `src/ui/import_export_dialog.py` (NEW)
- **Parallel?**: Yes - can be developed alongside T025
- **Notes**: See quickstart.md for detailed code example

### Subtask T025 - Create ExportDialog Class [PARALLEL]

- **Purpose**: Dialog for exporting data with file selection (FR-003)
- **Steps**:
  1. In same file `src/ui/import_export_dialog.py`
  2. Add `ExportDialog(ctk.CTkToplevel)` class:
     ```python
     class ExportDialog(ctk.CTkToplevel):
         def __init__(self, parent):
             super().__init__(parent)
             self.title("Export Data")
             self.geometry("400x200")
             self.result = None

             self._setup_ui()
             self.transient(parent)
             self.grab_set()
     ```
  3. Implement `_setup_ui()` with:
     - Informational text about export
     - "Choose Location & Export..." button
     - Cancel button
  4. Add `_do_export()` method using `filedialog.asksaveasfilename()`
- **Files**: `src/ui/import_export_dialog.py`
- **Parallel?**: Yes
- **Notes**: Default filename should be `bake-tracker-backup-YYYY-MM-DD.json`

### Subtask T026 - File Dialogs with JSON Filter

- **Purpose**: Filter file dialogs to JSON files (FR-004)
- **Steps**:
  1. In `ImportDialog._browse_file()`:
     ```python
     file_path = filedialog.askopenfilename(
         title="Select Import File",
         filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
     )
     ```
  2. In `ExportDialog._do_export()`:
     ```python
     file_path = filedialog.asksaveasfilename(
         title="Export Data",
         defaultextension=".json",
         initialfile=default_name,
         filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
     )
     ```
- **Files**: `src/ui/import_export_dialog.py`
- **Notes**: JSON should be first in filetypes list

### Subtask T027 - Mode Selection in ImportDialog

- **Purpose**: Allow user to choose Merge or Replace mode (FR-013)
- **Steps**:
  1. Add mode selection frame to `ImportDialog._setup_ui()`:
     ```python
     self.mode_frame = ctk.CTkFrame(self)
     self.mode_frame.pack(fill="x", padx=20, pady=10)

     ctk.CTkLabel(self.mode_frame, text="Import Mode:").pack(anchor="w")

     self.mode_var = ctk.StringVar(value="merge")

     ctk.CTkRadioButton(
         self.mode_frame,
         text="Merge (add new records, skip duplicates)",
         variable=self.mode_var,
         value="merge"
     ).pack(anchor="w", pady=2)

     ctk.CTkRadioButton(
         self.mode_frame,
         text="Replace (clear all existing data first)",
         variable=self.mode_var,
         value="replace"
     ).pack(anchor="w", pady=2)
     ```
  2. Pass `mode=self.mode_var.get()` to import service
- **Files**: `src/ui/import_export_dialog.py`
- **Notes**: Merge should be default (safer option)

### Subtask T028 - Replace Mode Confirmation Dialog

- **Purpose**: Warn user before clearing data (FR-013b)
- **Steps**:
  1. In `ImportDialog._do_import()`, check mode:
     ```python
     if self.mode_var.get() == "replace":
         if not messagebox.askyesno(
             "Confirm Replace",
             "This will DELETE all existing data before importing.\n\n"
             "Are you sure you want to continue?",
             icon="warning",
             parent=self
         ):
             return  # User cancelled
     ```
  2. Only proceed with import if confirmed
- **Files**: `src/ui/import_export_dialog.py`
- **Notes**: Use warning icon for emphasis

### Subtask T029 - Progress Indication for Large Datasets

- **Purpose**: Show user that import/export is in progress
- **Steps**:
  1. Add progress indicator to dialogs:
     - Option A: Simple "Processing..." label that shows during operation
     - Option B: CTkProgressBar in indeterminate mode
  2. Disable Import/Export button during operation
  3. Update cursor to busy:
     ```python
     self.config(cursor="wait")
     self.update()
     # ... operation ...
     self.config(cursor="")
     ```
  4. For large operations, consider `self.after()` to keep UI responsive
- **Files**: `src/ui/import_export_dialog.py`
- **Notes**: Full progress bar with percentages is P2 enhancement

### Subtask T030 - Success/Error Message Dialogs

- **Purpose**: Inform user of operation results (FR-007, FR-008, FR-012)
- **Steps**:
  1. After successful export:
     ```python
     messagebox.showinfo(
         "Export Complete",
         f"Successfully exported {result.record_count} records to:\n{file_path}",
         parent=self
     )
     ```
  2. After successful import:
     ```python
     messagebox.showinfo(
         "Import Complete",
         result.get_summary(),  # Uses ImportResult.get_summary()
         parent=self
     )
     ```
  3. On error:
     ```python
     messagebox.showerror(
         "Import Failed",
         f"Could not import file:\n{user_friendly_message}",
         parent=self
     )
     ```
  4. Convert technical exceptions to user-friendly messages
- **Files**: `src/ui/import_export_dialog.py`
- **Notes**: Never show stack traces to user (SC-006)

### Subtask T031 - Wire Dialogs to Service Layer

- **Purpose**: Connect UI to business logic (architecture compliance)
- **Steps**:
  1. In `ImportDialog._do_import()`:
     ```python
     from src.services import import_export_service

     try:
         result = import_export_service.import_all_from_json(
             self.file_path,
             mode=self.mode_var.get()
         )
         messagebox.showinfo("Import Complete", result.get_summary(), parent=self)
         self.result = result
         self.destroy()
     except Exception as e:
         messagebox.showerror("Import Failed", self._format_error(e), parent=self)
     ```
  2. In `ExportDialog._do_export()`:
     ```python
     try:
         result = import_export_service.export_all_to_json(file_path)
         messagebox.showinfo("Export Complete", f"Exported {result.record_count} records", parent=self)
         self.result = result
         self.destroy()
     except Exception as e:
         messagebox.showerror("Export Failed", self._format_error(e), parent=self)
     ```
  3. Add `_format_error(self, e: Exception) -> str` helper to convert exceptions
- **Files**: `src/ui/import_export_dialog.py`
- **Notes**: UI must not contain business logic - delegate to service

### Subtask T032 - Tab Refresh After Import

- **Purpose**: Update all tabs to show newly imported data
- **Steps**:
  1. In `MainWindow._show_import_dialog()`:
     ```python
     def _show_import_dialog(self):
         from src.ui.import_export_dialog import ImportDialog
         dialog = ImportDialog(self)
         dialog.wait_window()
         if dialog.result:
             self._refresh_all_tabs()
     ```
  2. Implement `_refresh_all_tabs()` if not exists:
     ```python
     def _refresh_all_tabs(self):
         """Refresh all tab views after data change."""
         # Call refresh method on each tab
         for tab in self.tabs:
             if hasattr(tab, 'refresh'):
                 tab.refresh()
     ```
- **Files**: `src/ui/main_window.py`
- **Notes**: Check existing refresh patterns in the codebase

## Test Strategy

- **Manual Testing**: UI components require manual verification
- **Test Scenarios**:
  1. File menu appears with Import/Export options
  2. Export creates valid JSON file at selected location
  3. Import shows file browser, mode selection works
  4. Merge mode adds data without clearing
  5. Replace mode shows warning, clears data on confirm
  6. Cancel in Replace confirmation aborts import
  7. Error messages are understandable
  8. Tabs refresh after successful import

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Menu bar styling doesn't match theme | Accept native styling (research decision) |
| Long operations freeze UI | Use progress indication and busy cursor |
| User accidentally clears data | Require explicit Replace confirmation |
| Technical errors shown to user | Wrap all exceptions in user-friendly messages |

## Definition of Done Checklist

- [ ] T023: Menu bar added with File menu
- [ ] T024: ImportDialog class created with file selection
- [ ] T025: ExportDialog class created with save dialog
- [ ] T026: File dialogs filter for JSON files
- [ ] T027: Mode selection (Merge/Replace) in ImportDialog
- [ ] T028: Replace mode confirmation dialog
- [ ] T029: Progress indication during operations
- [ ] T030: User-friendly success/error messages
- [ ] T031: Dialogs wired to service layer
- [ ] T032: Tabs refresh after successful import
- [ ] No business logic in UI layer
- [ ] All error messages are user-friendly

## Review Guidance

- Verify menu bar is visible and functional
- Test both import modes end-to-end
- Verify Replace confirmation appears
- Check error messages for user-friendliness
- Verify architecture compliance (no business logic in UI)

## Activity Log

- 2025-12-04T00:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-04T20:16:44Z – claude – shell_pid=82440 – lane=doing – Started implementation
- 2025-12-04T20:28:24Z – claude – shell_pid=83429 – lane=for_review – Completed all UI tasks - T023-T032 done
- 2025-12-04T20:56:05Z – claude-reviewer – shell_pid=85463 – lane=done – Code review APPROVED: Menu bar with File/Tools/Help, ImportDialog with mode selection, ExportDialog with save, Replace confirmation, _refresh_all_tabs, all syntax verified
