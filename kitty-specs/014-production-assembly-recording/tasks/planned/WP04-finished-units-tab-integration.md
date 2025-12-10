---
work_package_id: "WP04"
subtasks:
  - "T018"
  - "T019"
  - "T020"
  - "T021"
  - "T022"
title: "FinishedUnits Tab Integration"
phase: "Phase 2 - Production Recording"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-10T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - FinishedUnits Tab Integration

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Wire the FinishedUnitsTab to open the detail dialog:
- Add "View Details" button to action bar
- Open detail dialog on button click or row double-click
- Pass callback to refresh list after inventory changes
- Update form exports

**Success Criteria**:
- "View Details" button appears in action bar
- Button is disabled when no row selected
- Double-clicking a row opens detail dialog
- List refreshes after recording production in detail dialog

## Context & Constraints

**Dependencies**:
- WP03: FinishedUnitDetailDialog must be complete

**File to Modify**: `src/ui/finished_units_tab.py`

**Existing Patterns**:
- Tab already has Edit/Delete buttons with selection validation
- `_on_row_select()` manages button states
- `refresh()` method reloads data

## Subtasks & Detailed Guidance

### Subtask T018 - Add View Details Button

**Purpose**: Add a button to the action bar that opens the detail dialog.

**File**: `src/ui/finished_units_tab.py`

**Steps**:
1. Locate `_create_action_buttons()` method
2. Add "View Details" button alongside existing buttons
3. Set initial state to "disabled"
4. Wire to `_show_detail_dialog()` command

**Implementation**:
```python
def _create_action_buttons(self):
    # ... existing buttons ...

    # Add View Details button
    self.details_btn = ctk.CTkButton(
        self.button_frame,
        text="View Details",
        command=self._show_detail_dialog,
        width=ButtonWidths.DETAILS_BUTTON,
        state="disabled"
    )
    self.details_btn.pack(side="left", padx=PADDING_MEDIUM)

    # ... rest of buttons ...
```

---

### Subtask T019 - Implement Show Detail Dialog Method

**Purpose**: Create method that opens the detail dialog for selected FinishedUnit.

**Steps**:
1. Create `_show_detail_dialog(self)` method
2. Validate selection exists
3. Create and show FinishedUnitDetailDialog
4. Pass callback for inventory changes

**Implementation**:
```python
def _show_detail_dialog(self):
    """Open detail dialog for selected FinishedUnit."""
    if not self._validate_selected_unit():
        return

    from src.ui.forms.finished_unit_detail import FinishedUnitDetailDialog

    dialog = FinishedUnitDetailDialog(
        self,
        self.selected_finished_unit,
        on_inventory_changed=self.refresh
    )
    self.wait_window(dialog)
```

---

### Subtask T020 - Wire Double-Click Handler

**Purpose**: Open detail dialog when user double-clicks a row.

**Steps**:
1. Locate where DataTable is created
2. Pass `_show_detail_dialog` as `on_row_double_click` callback
3. Alternatively, modify existing double-click behavior

**Implementation**:
```python
def _create_data_table(self):
    self.data_table = FinishedUnitDataTable(
        self.table_frame,
        on_row_select=self._on_row_select,
        on_row_double_click=self._on_row_double_click,  # Add this
        height=500
    )
    # ... rest of setup ...

def _on_row_double_click(self, finished_unit):
    """Handle double-click on data table row."""
    self.selected_finished_unit = finished_unit
    self._show_detail_dialog()
```

**Note**: If double-click already exists (e.g., opens Edit form), consider if View Details should replace it or be separate. Based on spec, View Details should be the double-click action.

---

### Subtask T021 - Pass Callback for List Refresh

**Purpose**: Ensure list refreshes when inventory changes in detail dialog.

**Implementation Notes**:
- `self.refresh` method already exists and reloads data
- Pass as `on_inventory_changed` callback to detail dialog
- This is already done in T019 implementation

**Verification**:
1. Record production in detail dialog
2. Close detail dialog
3. Verify list shows updated inventory count

---

### Subtask T022 - Update Form Exports

**Purpose**: Export new dialogs from the forms package.

**File**: `src/ui/forms/__init__.py`

**Steps**:
1. Add import for FinishedUnitDetailDialog
2. Add import for RecordProductionDialog
3. Add to `__all__` if present

**Implementation**:
```python
# Add these imports
from src.ui.forms.finished_unit_detail import FinishedUnitDetailDialog
from src.ui.forms.record_production_dialog import RecordProductionDialog

# If __all__ exists, add:
__all__ = [
    # ... existing exports ...
    "FinishedUnitDetailDialog",
    "RecordProductionDialog",
]
```

---

### Button State Management

Ensure View Details button enables/disables with selection:

```python
def _on_row_select(self, finished_unit):
    """Handle row selection in data table."""
    self.selected_finished_unit = finished_unit
    self._update_button_states()

def _update_button_states(self):
    """Update button states based on selection."""
    if self.selected_finished_unit:
        self.edit_btn.configure(state="normal")
        self.delete_btn.configure(state="normal")
        self.details_btn.configure(state="normal")  # Add this line
    else:
        self.edit_btn.configure(state="disabled")
        self.delete_btn.configure(state="disabled")
        self.details_btn.configure(state="disabled")  # Add this line
```

---

## Test Strategy

**Manual Testing**:
1. Open FinishedUnits tab
2. Verify "View Details" button is disabled
3. Select a row - verify button enables
4. Click button - verify detail dialog opens
5. Double-click a row - verify detail dialog opens
6. Record production in dialog
7. Close dialog - verify list shows updated inventory

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Double-click conflicts with Edit | Decide: View Details replaces Edit as double-click |
| Button state not updating | Add to existing `_update_button_states()` method |
| Import circular dependency | Use local import in method |

## Definition of Done Checklist

- [ ] T018: View Details button added to action bar
- [ ] T019: `_show_detail_dialog()` method implemented
- [ ] T020: Double-click opens detail dialog
- [ ] T021: List refreshes via callback
- [ ] T022: Form exports updated
- [ ] Button disables when no selection
- [ ] Integration tested end-to-end

## Review Guidance

- Verify button state changes with selection
- Test double-click behavior
- Verify list refresh after recording
- Check for any console errors on dialog operations

## Activity Log

- 2025-12-10T00:00:00Z - system - lane=planned - Prompt created.
