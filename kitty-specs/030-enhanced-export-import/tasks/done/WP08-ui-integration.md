---
work_package_id: "WP08"
subtasks:
  - "T037"
  - "T038"
  - "T039"
  - "T040"
  - "T041"
title: "UI Integration"
phase: "Phase 3 - UI Integration"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-25T14:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 - UI Integration

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Integrate import view functionality into main application UI.

**Success Criteria**:
1. File > Import > Import View menu item added
2. Import dialog with file chooser and mode selection
3. FK resolution wizard integrates with import flow
4. Results summary dialog shows after import
5. Complete import flow tested manually

## Context & Constraints

**Owner**: Claude (Track B - Import)

**References**:
- `kitty-specs/030-enhanced-export-import/spec.md`: FR-031 through FR-034
- `src/ui/main_window.py`: Main application window
- `src/ui/import_export_dialog.py`: Existing import/export dialogs
- WP05: enhanced_import_service.py
- WP07: fk_resolution_dialog.py

**Constraints**:
- MUST use existing menu patterns
- MUST reuse ImportResultsDialog for results display
- Interactive FK resolution is default for UI (per FR-016)

**Dependencies**: WP05 (Enhanced Import Service), WP07 (FK Resolution Dialog)

## Subtasks & Detailed Guidance

### Subtask T037 - Add menu item

**Purpose**: Add File > Import > Import View menu item.

**Steps**:
1. Open `src/ui/main_window.py`
2. Locate existing File menu setup
3. Add Import submenu if not exists:
   ```python
   import_menu = tk.Menu(file_menu, tearoff=0)
   file_menu.add_cascade(label="Import", menu=import_menu)
   ```
4. Add Import View item:
   ```python
   import_menu.add_command(
       label="Import View...",
       command=self._on_import_view
   )
   ```
5. Implement `_on_import_view()` callback to open dialog

**Files**: `src/ui/main_window.py`
**Parallel?**: No

### Subtask T038 - Create import view dialog

**Purpose**: Dialog with file chooser and mode selection.

**Steps**:
1. Add ImportViewDialog to `src/ui/import_export_dialog.py`:
   ```python
   class ImportViewDialog(ctk.CTkToplevel):
       def __init__(self, parent):
           super().__init__(parent)
           self.title("Import View")
           self.geometry("450x300")

           self.file_path: Optional[str] = None
           self.mode: str = "merge"
           self.confirmed: bool = False

           self._setup_ui()

       def _setup_ui(self):
           # File selection
           file_frame = ctk.CTkFrame(self)
           file_frame.pack(fill="x", pady=10, padx=20)

           self.file_label = ctk.CTkLabel(file_frame, text="No file selected")
           self.file_label.pack(side="left")

           browse_btn = ctk.CTkButton(file_frame, text="Browse...", command=self._browse)
           browse_btn.pack(side="right")

           # Mode selection
           mode_frame = ctk.CTkFrame(self)
           mode_frame.pack(fill="x", pady=10, padx=20)

           ctk.CTkLabel(mode_frame, text="Import Mode:").pack(anchor="w")

           self.mode_var = ctk.StringVar(value="merge")
           ctk.CTkRadioButton(
               mode_frame, text="Merge (update existing, add new)",
               variable=self.mode_var, value="merge"
           ).pack(anchor="w")
           ctk.CTkRadioButton(
               mode_frame, text="Skip Existing (add new only)",
               variable=self.mode_var, value="skip_existing"
           ).pack(anchor="w")

           # Buttons
           btn_frame = ctk.CTkFrame(self)
           btn_frame.pack(pady=20)

           ctk.CTkButton(btn_frame, text="Import", command=self._on_import).pack(side="left", padx=5)
           ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)

       def _browse(self):
           file_path = filedialog.askopenfilename(
               filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
           )
           if file_path:
               self.file_path = file_path
               self.file_label.configure(text=Path(file_path).name)
   ```

**Files**: `src/ui/import_export_dialog.py`
**Parallel?**: No

### Subtask T039 - Integrate FK resolution wizard

**Purpose**: Connect FK resolution dialog to import flow.

**Steps**:
1. Create UIFKResolver implementing FKResolverCallback:
   ```python
   class UIFKResolver:
       def __init__(self, parent_window):
           self.parent = parent_window

       def resolve(self, missing: MissingFK) -> Resolution:
           dialog = FKResolutionDialog(self.parent, missing)
           self.parent.wait_window(dialog)

           if dialog.result:
               return dialog.result
           else:
               # Dialog closed without selection - treat as skip
               return Resolution(
                   choice=ResolutionChoice.SKIP,
                   entity_type=missing.entity_type,
                   missing_value=missing.missing_value
               )
   ```
2. In ImportViewDialog._on_import():
   ```python
   def _on_import(self):
       if not self.file_path:
           messagebox.showerror("Error", "Please select a file")
           return

       self.confirmed = True
       self.mode = self.mode_var.get()
       self.destroy()
   ```
3. In main_window._on_import_view():
   ```python
   def _on_import_view(self):
       dialog = ImportViewDialog(self)
       self.wait_window(dialog)

       if dialog.confirmed:
           resolver = UIFKResolver(self)
           result = enhanced_import_service.import_view(
               dialog.file_path,
               mode=dialog.mode,
               resolver=resolver
           )
           self._show_import_results(result)
   ```

**Files**: `src/ui/import_export_dialog.py`, `src/ui/main_window.py`
**Parallel?**: No

### Subtask T040 - Show results summary dialog

**Purpose**: Display import results after completion.

**Steps**:
1. Reuse existing ImportResultsDialog:
   ```python
   def _show_import_results(self, result: EnhancedImportResult):
       summary_text = result.get_summary()

       # Write log file
       log_path = _write_import_log(self.file_path, result, summary_text)

       # Show results dialog
       ImportResultsDialog(
           self,
           title="Import Complete",
           summary_text=summary_text,
           log_path=log_path
       )

       # Refresh any relevant tabs
       self._refresh_data()
   ```
2. Ensure EnhancedImportResult.get_summary() includes:
   - Record counts (added, updated, skipped, failed)
   - FK resolution summary (created, mapped, skipped)
   - Any errors or warnings

**Files**: `src/ui/main_window.py`
**Parallel?**: No

### Subtask T041 - Manual UI testing

**Purpose**: Verify complete import flow works.

**Steps**:
1. Test scenarios:
   - Import valid view file with no missing FKs
   - Import file with missing supplier → create new
   - Import file with missing supplier → map to existing
   - Import file with missing supplier → skip records
   - Cancel mid-import → verify keep/rollback options
   - Large file import (100+ records)
2. Verify:
   - File chooser works
   - Mode selection works
   - FK resolution dialogs appear correctly
   - Results dialog shows accurate counts
   - Data appears in relevant tabs after import
3. Document any issues found

**Files**: N/A (manual testing)
**Parallel?**: No

## Test Strategy

- Manual testing of complete UI flow
- Verify dialog interactions
- Verify data persistence
- Verify tab refresh after import

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Tab refresh issues | Use existing refresh patterns |
| Modal stacking | Careful wait_window usage |

## Definition of Done Checklist

- [ ] All subtasks completed and validated
- [ ] File > Import > Import View menu item works
- [ ] Import dialog with file chooser and mode selection works
- [ ] FK resolution wizard integrates correctly
- [ ] Results summary dialog displays correctly
- [ ] Manual UI testing complete
- [ ] Data persists correctly after import
- [ ] tasks.md updated with status change

## Review Guidance

- Verify menu item in correct location
- Verify dialog follows existing patterns
- Verify FK resolution wizard triggers on missing FKs
- Verify results dialog shows accurate counts
- Verify data appears in tabs after import

## Activity Log

- 2025-12-25T14:00:00Z - system - lane=planned - Prompt created.
- 2025-12-26T02:59:42Z – system – shell_pid= – lane=doing – Moved to doing
- 2025-12-26T03:04:27Z – system – shell_pid= – lane=for_review – Moved to for_review
- 2025-12-26T03:38:42Z – system – shell_pid= – lane=done – Code review passed: Menu item, dialog, FK resolver integration all work
