---
work_package_id: "WP03"
subtasks:
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
title: "FinishedUnit Detail Dialog"
phase: "Phase 2 - Production Recording"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: "45064"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-10T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - FinishedUnit Detail Dialog

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Create the FinishedUnit detail modal dialog that:
- Displays FinishedUnit information (name, recipe, inventory, cost)
- Shows production history using ProductionHistoryTable
- Provides "Record Production" button to open RecordProductionDialog
- Refreshes data after successful production recording
- Notifies parent when inventory changes via callback

**Success Criteria**:
- Dialog displays all FinishedUnit details correctly
- Production history loads and displays properly
- Record Production button opens recording dialog
- After recording, both dialog data and parent list refresh
- Dialog follows modal pattern

## Context & Constraints

**Dependencies**:
- WP01: ProductionHistoryTable widget
- WP02: RecordProductionDialog

**Reference Documents**:
- `kitty-specs/014-production-assembly-recording/contracts/ui-components.md` - Dialog contract
- `kitty-specs/014-production-assembly-recording/data-model.md` - FinishedUnit entity

**Services Used**:
- `batch_production_service.get_production_history(finished_unit_id=...)`

## Subtasks & Detailed Guidance

### Subtask T011 - Create FinishedUnitDetailDialog Class

**Purpose**: Establish the dialog class with proper modal behavior and callback support.

**File**: `src/ui/forms/finished_unit_detail.py`

**Steps**:
1. Create file with imports
2. Define `FinishedUnitDetailDialog(ctk.CTkToplevel)` class
3. Accept `parent`, `finished_unit`, and optional `on_inventory_changed` callback
4. Store references and set up modal behavior

**Implementation**:
```python
import customtkinter as ctk
from typing import Optional, Callable
from src.models import FinishedUnit
from src.ui.widgets.production_history_table import ProductionHistoryTable
from src.ui.service_integration import get_ui_service_integrator, OperationType
from src.services import batch_production_service
from src.utils.constants import PADDING_MEDIUM, PADDING_LARGE

class FinishedUnitDetailDialog(ctk.CTkToplevel):
    def __init__(
        self,
        parent,
        finished_unit: FinishedUnit,
        on_inventory_changed: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent)
        self.finished_unit = finished_unit
        self._on_inventory_changed = on_inventory_changed
        self.service_integrator = get_ui_service_integrator()

        self._setup_window()
        self._create_widgets()
        self._load_data()
        self._setup_modal()

    def _setup_window(self):
        self.title(f"Details - {self.finished_unit.display_name}")
        self.geometry("500x600")
        self.minsize(450, 500)
        self.resizable(True, True)

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)  # History table expands

    def _setup_modal(self):
        self.transient(self.master)
        self.wait_visibility()
        self.grab_set()
        self.focus_force()

        # Center on parent
        self.update_idletasks()
        parent_x = self.master.winfo_rootx()
        parent_y = self.master.winfo_rooty()
        parent_w = self.master.winfo_width()
        parent_h = self.master.winfo_height()
        dialog_w = self.winfo_width()
        dialog_h = self.winfo_height()
        x = parent_x + (parent_w - dialog_w) // 2
        y = parent_y + (parent_h - dialog_h) // 2
        self.geometry(f"+{x}+{y}")
```

---

### Subtask T012 - Implement Header Section

**Purpose**: Display the FinishedUnit name and category prominently.

**Steps**:
1. Create header frame at row 0
2. Add display name with large bold font
3. Add category label if present

**Implementation**:
```python
def _create_header(self):
    header_frame = ctk.CTkFrame(self, fg_color="transparent")
    header_frame.grid(row=0, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)

    name_label = ctk.CTkLabel(
        header_frame,
        text=self.finished_unit.display_name,
        font=ctk.CTkFont(size=20, weight="bold")
    )
    name_label.pack(anchor="w")

    if self.finished_unit.category:
        category_label = ctk.CTkLabel(
            header_frame,
            text=f"Category: {self.finished_unit.category}",
            text_color="gray"
        )
        category_label.pack(anchor="w")
```

---

### Subtask T013 - Implement Info Section

**Purpose**: Display recipe link, inventory count, and unit cost.

**Steps**:
1. Create info frame at row 1
2. Add recipe name (or "No recipe assigned")
3. Add inventory count with label
4. Add unit cost formatted as currency

**Implementation**:
```python
def _create_info_section(self):
    info_frame = ctk.CTkFrame(self)
    info_frame.grid(row=1, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_MEDIUM)
    info_frame.grid_columnconfigure(1, weight=1)

    # Recipe
    ctk.CTkLabel(info_frame, text="Recipe:").grid(row=0, column=0, sticky="e", padx=PADDING_MEDIUM)
    recipe_name = self.finished_unit.recipe.name if self.finished_unit.recipe else "No recipe assigned"
    self.recipe_label = ctk.CTkLabel(info_frame, text=recipe_name)
    self.recipe_label.grid(row=0, column=1, sticky="w", padx=PADDING_MEDIUM)

    # Inventory count
    ctk.CTkLabel(info_frame, text="In Stock:").grid(row=1, column=0, sticky="e", padx=PADDING_MEDIUM)
    self.inventory_label = ctk.CTkLabel(
        info_frame,
        text=str(self.finished_unit.inventory_count or 0),
        font=ctk.CTkFont(size=16, weight="bold")
    )
    self.inventory_label.grid(row=1, column=1, sticky="w", padx=PADDING_MEDIUM)

    # Unit cost
    ctk.CTkLabel(info_frame, text="Unit Cost:").grid(row=2, column=0, sticky="e", padx=PADDING_MEDIUM)
    cost = self.finished_unit.unit_cost or 0
    self.cost_label = ctk.CTkLabel(info_frame, text=f"${cost:.2f}")
    self.cost_label.grid(row=2, column=1, sticky="w", padx=PADDING_MEDIUM)

    # Items per batch
    if self.finished_unit.items_per_batch:
        ctk.CTkLabel(info_frame, text="Items/Batch:").grid(row=3, column=0, sticky="e", padx=PADDING_MEDIUM)
        ctk.CTkLabel(info_frame, text=str(self.finished_unit.items_per_batch)).grid(
            row=3, column=1, sticky="w", padx=PADDING_MEDIUM
        )
```

---

### Subtask T014 - Integrate ProductionHistoryTable Widget

**Purpose**: Display production history for this FinishedUnit.

**Steps**:
1. Add section header "Production History"
2. Create ProductionHistoryTable widget
3. Load history data via service

**Implementation**:
```python
def _create_history_section(self):
    # Section header
    history_header = ctk.CTkLabel(
        self,
        text="Production History",
        font=ctk.CTkFont(size=14, weight="bold")
    )
    history_header.grid(row=2, column=0, sticky="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_MEDIUM))

    # History table
    self.history_table = ProductionHistoryTable(
        self,
        on_row_select=self._on_history_select,
        on_row_double_click=self._on_history_double_click,
        height=200
    )
    self.history_table.grid(row=3, column=0, sticky="nsew", padx=PADDING_LARGE, pady=PADDING_MEDIUM)

def _load_history(self):
    history = self.service_integrator.execute_service_operation(
        operation_name="Load Production History",
        operation_type=OperationType.READ,
        service_function=lambda: batch_production_service.get_production_history(
            finished_unit_id=self.finished_unit.id,
            limit=50,
            include_consumptions=False
        ),
        parent_widget=self,
        error_context="Loading production history"
    )

    if history:
        self.history_table.set_data(history)
    else:
        self.history_table.clear()

def _on_history_select(self, run):
    # Optional: show selection info
    pass

def _on_history_double_click(self, run):
    # Optional: show run detail dialog
    pass
```

---

### Subtask T015 - Implement Record Production Button

**Purpose**: Button that opens RecordProductionDialog for this FinishedUnit.

**Steps**:
1. Create button frame at bottom of dialog
2. Add "Record Production" button
3. Disable if no recipe assigned
4. Add "Close" button

**Implementation**:
```python
def _create_buttons(self):
    button_frame = ctk.CTkFrame(self, fg_color="transparent")
    button_frame.grid(row=4, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)

    # Record Production button
    self.record_btn = ctk.CTkButton(
        button_frame,
        text="Record Production",
        command=self._open_record_production,
        width=150
    )
    self.record_btn.pack(side="left", padx=PADDING_MEDIUM)

    # Disable if no recipe
    if not self.finished_unit.recipe:
        self.record_btn.configure(state="disabled")
        # Add tooltip or note
        note = ctk.CTkLabel(button_frame, text="(No recipe assigned)", text_color="gray")
        note.pack(side="left", padx=PADDING_MEDIUM)

    # Close button
    close_btn = ctk.CTkButton(
        button_frame,
        text="Close",
        command=self.destroy,
        width=100
    )
    close_btn.pack(side="right", padx=PADDING_MEDIUM)

def _open_record_production(self):
    from src.ui.forms.record_production_dialog import RecordProductionDialog

    dialog = RecordProductionDialog(self, self.finished_unit)
    self.wait_window(dialog)

    result = dialog.get_result()
    if result:
        self._after_recording_success()
```

---

### Subtask T016 - Implement Inventory Refresh After Recording

**Purpose**: Update displayed data after successful production recording.

**Steps**:
1. Reload FinishedUnit from database to get updated inventory_count
2. Update inventory label
3. Reload production history
4. Call parent callback if provided

**Implementation**:
```python
def _after_recording_success(self):
    # Refresh FinishedUnit data
    self._reload_finished_unit()

    # Refresh history table
    self._load_history()

    # Notify parent
    if self._on_inventory_changed:
        self._on_inventory_changed()

def _reload_finished_unit(self):
    from src.services import finished_unit_service

    updated = self.service_integrator.execute_service_operation(
        operation_name="Reload FinishedUnit",
        operation_type=OperationType.READ,
        service_function=lambda: finished_unit_service.get_finished_unit_by_id(
            self.finished_unit.id
        ),
        parent_widget=self,
        error_context="Reloading finished unit data"
    )

    if updated:
        self.finished_unit = updated
        self._update_info_display()

def _update_info_display(self):
    self.inventory_label.configure(text=str(self.finished_unit.inventory_count or 0))
    cost = self.finished_unit.unit_cost or 0
    self.cost_label.configure(text=f"${cost:.2f}")
```

---

### Subtask T017 - Add Callback Support

**Purpose**: Allow parent to be notified when inventory changes so it can refresh its list.

**Implementation Notes**:
- Callback is passed in constructor
- Called in `_after_recording_success()`
- Parent typically passes a method like `self._refresh_list`

**Usage from Parent Tab**:
```python
# In FinishedUnitsTab
def _show_detail_dialog(self):
    if not self.selected_finished_unit:
        return

    dialog = FinishedUnitDetailDialog(
        self,
        self.selected_finished_unit,
        on_inventory_changed=self.refresh  # Refresh the list
    )
    self.wait_window(dialog)
```

---

## Test Strategy

**Manual Testing**:
1. Open detail dialog for a FinishedUnit
2. Verify all info displays correctly
3. Verify production history loads
4. Click Record Production, complete recording
5. Verify inventory count updates
6. Verify history table updates
7. Close dialog and verify parent list refreshed

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| FinishedUnit data stale after recording | Force reload from database |
| History table empty | Show empty state message |
| No recipe assigned | Disable Record Production button |

## Definition of Done Checklist

- [ ] T011: Dialog class created with modal behavior
- [ ] T012: Header displays name and category
- [ ] T013: Info section shows recipe, inventory, cost
- [ ] T014: Production history table integrated
- [ ] T015: Record Production button works
- [ ] T016: Data refreshes after recording
- [ ] T017: Parent callback fires on inventory change
- [ ] Dialog follows modal pattern
- [ ] Graceful handling of missing recipe

## Review Guidance

- Verify all FinishedUnit fields display correctly
- Test with FinishedUnit that has production history
- Test with FinishedUnit that has no history
- Verify inventory updates after recording
- Check parent list refreshes via callback

## Activity Log

- 2025-12-10T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-10T06:59:02Z – claude – shell_pid=45064 – lane=doing – Started implementation of FinishedUnit Detail Dialog
- 2025-12-10T07:00:40Z – claude – shell_pid=45064 – lane=for_review – Completed implementation - T011-T017 all done
- 2025-12-10T15:23:28Z – claude – shell_pid=45064 – lane=done – Code review approved - FinishedUnitDetailDialog implements all requirements
