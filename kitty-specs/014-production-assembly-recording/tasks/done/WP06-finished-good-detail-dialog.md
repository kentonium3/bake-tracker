---
work_package_id: "WP06"
subtasks:
  - "T029"
  - "T030"
  - "T031"
  - "T032"
  - "T033"
  - "T034"
  - "T035"
  - "T036"
title: "FinishedGood Detail Dialog"
phase: "Phase 3 - Assembly Recording"
lane: "done"
assignee: ""
agent: "system"
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

# Work Package Prompt: WP06 - FinishedGood Detail Dialog

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Create the FinishedGood detail modal dialog that:
- Displays FinishedGood information (name, inventory, cost)
- Shows composition (components list)
- Shows assembly history using AssemblyHistoryTable
- Provides "Record Assembly" button
- Refreshes data after successful assembly

**Success Criteria**:
- Dialog displays all FinishedGood details
- Composition lists all components with quantities
- Assembly history loads and displays
- Record Assembly opens recording dialog
- Data refreshes after recording

## Context & Constraints

**Dependencies**:
- WP01: AssemblyHistoryTable widget
- WP05: RecordAssemblyDialog

**Services Used**:
- `assembly_service.get_assembly_history()`
- `finished_good_service.get_finished_good_by_id()`

## Subtasks & Detailed Guidance

### Subtask T029 - Create FinishedGoodDetailDialog Class

**File**: `src/ui/forms/finished_good_detail.py`

**Implementation**:
```python
import customtkinter as ctk
from typing import Optional, Callable
from src.models import FinishedGood
from src.ui.widgets.assembly_history_table import AssemblyHistoryTable
from src.ui.service_integration import get_ui_service_integrator, OperationType
from src.services import assembly_service
from src.utils.constants import PADDING_MEDIUM, PADDING_LARGE

class FinishedGoodDetailDialog(ctk.CTkToplevel):
    def __init__(
        self,
        parent,
        finished_good: FinishedGood,
        on_inventory_changed: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent)
        self.finished_good = finished_good
        self._on_inventory_changed = on_inventory_changed
        self.service_integrator = get_ui_service_integrator()

        self._setup_window()
        self._create_widgets()
        self._load_data()
        self._setup_modal()

    def _setup_window(self):
        self.title(f"Details - {self.finished_good.display_name}")
        self.geometry("550x650")
        self.minsize(500, 550)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)  # History expands

    def _setup_modal(self):
        self.transient(self.master)
        self.wait_visibility()
        self.grab_set()
        self.focus_force()
        self._center_on_parent()
```

---

### Subtask T030 - Implement Header Section

**Implementation**:
```python
def _create_header(self):
    header_frame = ctk.CTkFrame(self, fg_color="transparent")
    header_frame.grid(row=0, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)

    name_label = ctk.CTkLabel(
        header_frame,
        text=self.finished_good.display_name,
        font=ctk.CTkFont(size=20, weight="bold")
    )
    name_label.pack(anchor="w")
```

---

### Subtask T031 - Implement Info Section

**Implementation**:
```python
def _create_info_section(self):
    info_frame = ctk.CTkFrame(self)
    info_frame.grid(row=1, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_MEDIUM)
    info_frame.grid_columnconfigure(1, weight=1)

    # Inventory count
    ctk.CTkLabel(info_frame, text="In Stock:").grid(row=0, column=0, sticky="e", padx=PADDING_MEDIUM)
    self.inventory_label = ctk.CTkLabel(
        info_frame,
        text=str(self.finished_good.inventory_count or 0),
        font=ctk.CTkFont(size=16, weight="bold")
    )
    self.inventory_label.grid(row=0, column=1, sticky="w", padx=PADDING_MEDIUM)

    # Total cost
    ctk.CTkLabel(info_frame, text="Total Cost:").grid(row=1, column=0, sticky="e", padx=PADDING_MEDIUM)
    cost = self.finished_good.total_cost or 0
    self.cost_label = ctk.CTkLabel(info_frame, text=f"${cost:.2f}")
    self.cost_label.grid(row=1, column=1, sticky="w", padx=PADDING_MEDIUM)
```

---

### Subtask T032 - Implement Composition Display Section

**Purpose**: Show the BOM (components) for this FinishedGood.

**Implementation**:
```python
def _create_composition_section(self):
    # Section header
    comp_header = ctk.CTkLabel(
        self,
        text="Composition",
        font=ctk.CTkFont(size=14, weight="bold")
    )
    comp_header.grid(row=2, column=0, sticky="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_MEDIUM))

    # Composition frame (scrollable for many components)
    comp_frame = ctk.CTkScrollableFrame(self, height=120)
    comp_frame.grid(row=3, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_MEDIUM)

    # Load and display components
    self._populate_composition(comp_frame)

def _populate_composition(self, parent_frame):
    # Get composition from relationships
    compositions = getattr(self.finished_good, 'compositions', [])

    if not compositions:
        no_comp = ctk.CTkLabel(parent_frame, text="No components defined", text_color="gray")
        no_comp.pack(anchor="w")
        self._has_composition = False
        return

    self._has_composition = True

    for comp in compositions:
        row_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        row_frame.pack(fill="x", pady=2)

        # Determine component name
        if comp.finished_unit_id and comp.finished_unit:
            name = f"[FU] {comp.finished_unit.display_name}"
        elif comp.finished_good_id and comp.finished_good:
            name = f"[FG] {comp.finished_good.display_name}"
        elif comp.packaging_product_id and comp.packaging_product:
            name = f"[Pkg] {comp.packaging_product.display_name}"
        else:
            name = "Unknown component"

        qty = comp.component_quantity or 0

        ctk.CTkLabel(row_frame, text=f"  {qty}x {name}").pack(side="left")
```

---

### Subtask T033 - Integrate AssemblyHistoryTable

**Implementation**:
```python
def _create_history_section(self):
    history_header = ctk.CTkLabel(
        self,
        text="Assembly History",
        font=ctk.CTkFont(size=14, weight="bold")
    )
    history_header.grid(row=4, column=0, sticky="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_MEDIUM))

    self.history_table = AssemblyHistoryTable(
        self,
        on_row_select=self._on_history_select,
        height=150
    )
    self.history_table.grid(row=5, column=0, sticky="nsew", padx=PADDING_LARGE, pady=PADDING_MEDIUM)

def _load_history(self):
    history = self.service_integrator.execute_service_operation(
        operation_name="Load Assembly History",
        operation_type=OperationType.READ,
        service_function=lambda: assembly_service.get_assembly_history(
            finished_good_id=self.finished_good.id,
            limit=50,
            include_consumptions=False
        ),
        parent_widget=self,
        error_context="Loading assembly history"
    )

    if history:
        self.history_table.set_data(history)
    else:
        self.history_table.clear()

def _on_history_select(self, run):
    pass  # Optional: show selection
```

---

### Subtask T034 - Implement Record Assembly Button

**Implementation**:
```python
def _create_buttons(self):
    button_frame = ctk.CTkFrame(self, fg_color="transparent")
    button_frame.grid(row=6, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)

    self.record_btn = ctk.CTkButton(
        button_frame,
        text="Record Assembly",
        command=self._open_record_assembly,
        width=150
    )
    self.record_btn.pack(side="left", padx=PADDING_MEDIUM)

    # Disable if no composition
    if not getattr(self, '_has_composition', True):
        self.record_btn.configure(state="disabled")
        note = ctk.CTkLabel(button_frame, text="(No components defined)", text_color="gray")
        note.pack(side="left", padx=PADDING_MEDIUM)

    close_btn = ctk.CTkButton(
        button_frame,
        text="Close",
        command=self.destroy,
        width=100
    )
    close_btn.pack(side="right", padx=PADDING_MEDIUM)

def _open_record_assembly(self):
    from src.ui.forms.record_assembly_dialog import RecordAssemblyDialog

    dialog = RecordAssemblyDialog(self, self.finished_good)
    self.wait_window(dialog)

    result = dialog.get_result()
    if result:
        self._after_assembly_success()
```

---

### Subtask T035 - Implement Refresh After Assembly

**Implementation**:
```python
def _after_assembly_success(self):
    self._reload_finished_good()
    self._load_history()

    if self._on_inventory_changed:
        self._on_inventory_changed()

def _reload_finished_good(self):
    from src.services import finished_good_service

    updated = self.service_integrator.execute_service_operation(
        operation_name="Reload FinishedGood",
        operation_type=OperationType.READ,
        service_function=lambda: finished_good_service.get_finished_good_by_id(
            self.finished_good.id
        ),
        parent_widget=self,
        error_context="Reloading finished good data"
    )

    if updated:
        self.finished_good = updated
        self._update_info_display()

def _update_info_display(self):
    self.inventory_label.configure(text=str(self.finished_good.inventory_count or 0))
    cost = self.finished_good.total_cost or 0
    self.cost_label.configure(text=f"${cost:.2f}")
```

---

### Subtask T036 - Add Callback Support

Same pattern as WP03 - callback passed in constructor, called after assembly success.

---

## Definition of Done Checklist

- [ ] T029: Dialog class created
- [ ] T030: Header section
- [ ] T031: Info section with inventory and cost
- [ ] T032: Composition display shows all components
- [ ] T033: Assembly history table integrated
- [ ] T034: Record Assembly button works
- [ ] T035: Data refreshes after assembly
- [ ] T036: Parent callback fires on inventory change
- [ ] Handles missing composition gracefully

## Activity Log

- 2025-12-10T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-10T07:15:51Z – system – shell_pid= – lane=doing – Moved to doing
- 2025-12-10T07:17:15Z – system – shell_pid= – lane=for_review – Moved to for_review
- 2025-12-10T15:25:21Z – system – shell_pid= – lane=done – Code review approved - FinishedGoodDetailDialog with composition and history display
