---
work_package_id: "WP04"
subtasks:
  - "T016"
  - "T017"
  - "T018"
  - "T019"
title: "Shopping List CSV Export"
phase: "Phase 4 - CSV Export"
lane: "for_review"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-11T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - Shopping List CSV Export

## Objectives & Success Criteria

**Objective**: Enable CSV export of shopping list from Event Detail window (User Story 3).

**Success Criteria**:
- "Export CSV" button appears on Shopping tab (FR-007)
- CSV contains columns: Ingredient, Quantity Needed, Unit, Preferred Brand, Est. Cost (FR-008)
- Default filename is event-slug-shopping-list.csv (FR-009)
- Errors handled gracefully with user notification (FR-010)
- Exported CSV is readable in Excel/Google Sheets (SC-002)

## Context & Constraints

**Reference Documents**:
- Plan: `kitty-specs/017-event-reporting-production/plan.md`
- Spec: `kitty-specs/017-event-reporting-production/spec.md`
- Research: `kitty-specs/017-event-reporting-production/research.md` (Decision D3)

**Architectural Constraints**:
- CSV generation logic in service layer (WP01)
- UI only handles button, dialog, and notifications
- Use tkinter.filedialog for save dialog
- Use tkinter.messagebox for notifications

**Dependencies**:
- WP01 must be complete (`export_shopping_list_csv()` service method)

## Subtasks & Detailed Guidance

### Subtask T016 - Add "Export CSV" button to Shopping tab

**Purpose**: Provide UI trigger for CSV export.

**Steps**:
1. Open `src/ui/event_detail_window.py`
2. Find the Shopping tab creation code (likely in a method like `_create_shopping_tab()` or similar)
3. Add export button near the top of the tab:
   ```python
   # Shopping tab header with export button
   header_frame = ctk.CTkFrame(shopping_frame)
   header_frame.pack(fill="x", padx=10, pady=5)

   ctk.CTkLabel(
       header_frame,
       text=f"Shopping List for {self.event.name}",
       font=ctk.CTkFont(size=16, weight="bold")
   ).pack(side="left")

   self.export_csv_button = ctk.CTkButton(
       header_frame,
       text="Export CSV",
       command=self._export_shopping_list_csv,
       width=100
   )
   self.export_csv_button.pack(side="right", padx=5)
   ```

**Files**: `src/ui/event_detail_window.py`
**Parallel?**: No (must complete before T017)
**Notes**: Check existing structure - may need to add header_frame or integrate with existing layout.

---

### Subtask T017 - Implement file save dialog with default filename

**Purpose**: Allow user to choose save location with sensible default.

**Steps**:
1. Add import at top of file:
   ```python
   from tkinter import filedialog
   ```

2. Create helper to generate default filename:
   ```python
   def _get_default_csv_filename(self) -> str:
       """Generate default CSV filename from event name."""
       # Convert event name to slug: "Christmas 2025" -> "christmas-2025"
       import re
       slug = re.sub(r'[^a-zA-Z0-9]+', '-', self.event.name.lower()).strip('-')
       return f"{slug}-shopping-list.csv"
   ```

3. Add file dialog method:
   ```python
   def _show_save_dialog(self) -> str:
       """Show file save dialog and return selected path."""
       default_filename = self._get_default_csv_filename()

       file_path = filedialog.asksaveasfilename(
           defaultextension=".csv",
           filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
           initialfile=default_filename,
           title="Export Shopping List",
           parent=self
       )

       return file_path  # Returns empty string if cancelled
   ```

**Files**: `src/ui/event_detail_window.py`
**Parallel?**: No (builds on T016)

---

### Subtask T018 - Call export service method and handle errors

**Purpose**: Execute the export and catch any errors.

**Steps**:
1. Add import:
   ```python
   from src.services import event_service
   ```

2. Create export handler method:
   ```python
   def _export_shopping_list_csv(self):
       """Handle CSV export button click."""
       # Get save location from user
       file_path = self._show_save_dialog()

       if not file_path:
           # User cancelled
           return

       try:
           # Call service method
           success = event_service.export_shopping_list_csv(self.event.id, file_path)

           if success:
               self._show_export_success(file_path)
           else:
               self._show_export_error("Export completed but file may be empty.")

       except IOError as e:
           self._show_export_error(f"Could not write file: {str(e)}")
       except Exception as e:
           self._show_export_error(f"Export failed: {str(e)}")
   ```

**Files**: `src/ui/event_detail_window.py`
**Parallel?**: No (builds on T017)

---

### Subtask T019 - Show success/failure notification

**Purpose**: Provide clear feedback to user about export result.

**Steps**:
1. Add import:
   ```python
   from tkinter import messagebox
   ```

2. Add notification methods:
   ```python
   def _show_export_success(self, file_path: str):
       """Show success message after export."""
       messagebox.showinfo(
           "Export Complete",
           f"Shopping list exported successfully to:\n\n{file_path}",
           parent=self
       )

   def _show_export_error(self, message: str):
       """Show error message if export fails."""
       messagebox.showerror(
           "Export Failed",
           f"Could not export shopping list.\n\n{message}\n\n"
           "Please check:\n"
           "- You have write permission to the location\n"
           "- The file is not open in another program",
           parent=self
       )
   ```

**Files**: `src/ui/event_detail_window.py`
**Parallel?**: No (builds on T018)

---

## Test Strategy

**Manual Testing**:
1. Open Event Detail window for an event with shopping list items
2. Navigate to Shopping tab
3. Click "Export CSV" button
4. Verify file dialog appears with default filename like `christmas-2025-shopping-list.csv`
5. Save to desktop or known location
6. Open CSV in Excel - verify columns and data
7. Test error case: try to save to read-only location (expect error message)
8. Test cancel: click Cancel in file dialog (nothing should happen)

**CSV Verification**:
- Open exported file in Excel or Google Sheets
- Verify header row: Ingredient, Quantity Needed, On Hand, To Buy, Unit, Preferred Brand, Estimated Cost
- Verify data rows match what's shown in Shopping tab
- Verify no encoding issues (special characters display correctly)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| File permissions | Catch IOError, show helpful message |
| User cancels dialog | Check for empty string return |
| Special characters in filename | Use regex to create safe slug |
| File open in Excel | Suggest closing file in error message |

## Definition of Done Checklist

- [ ] T016: "Export CSV" button visible on Shopping tab
- [ ] T017: File dialog shows with correct default filename
- [ ] T018: Export service method called correctly
- [ ] T019: Success/error notifications display
- [ ] Exported CSV opens correctly in Excel
- [ ] Error handling works for permission issues
- [ ] Cancel in dialog does not cause error
- [ ] `tasks.md` updated with completion status

## Review Guidance

**Key Checkpoints**:
1. Button placement is intuitive (near shopping list header)
2. Default filename follows slug pattern
3. CSV opens correctly in Excel with proper encoding
4. Error messages are user-friendly (not technical)
5. Cancel behavior is clean (no errors, no partial files)

## Activity Log

- 2025-12-11T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-12T03:30:19Z – system – shell_pid= – lane=doing – Moved to doing
- 2025-12-12T03:40:24Z – system – shell_pid= – lane=for_review – Moved to for_review
