---
work_package_id: WP05
title: Assembly Recording Dialog
lane: done
history:
- timestamp: '2025-12-10T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: system
assignee: ''
phase: Phase 3 - Assembly Recording
review_status: ''
reviewed_by: ''
shell_pid: ''
subtasks:
- T023
- T024
- T025
- T026
- T027
- T028
---

# Work Package Prompt: WP05 - Assembly Recording Dialog

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Create the Record Assembly dialog that allows users to record assembly of FinishedGoods:
- Quantity input
- Optional notes
- Availability check for components (FinishedUnits, packaging)
- Confirm/Cancel actions

**Success Criteria**:
- Dialog opens as modal over parent
- Availability check shows component status (FUs and packaging)
- Confirm disabled when components insufficient
- On confirm, calls `record_assembly()` and returns result

## Context & Constraints

**Dependencies**:
- WP01: AvailabilityDisplay widget

**Services Used**:
- `assembly_service.check_can_assemble()`
- `assembly_service.record_assembly()`

**Similar To**: WP02 (RecordProductionDialog) - follow same patterns

## Subtasks & Detailed Guidance

### Subtask T023 - Create RecordAssemblyDialog Class

**File**: `src/ui/forms/record_assembly_dialog.py`

**Implementation**:
```python
import customtkinter as ctk
from typing import Optional
from src.models import FinishedGood
from src.ui.widgets.availability_display import AvailabilityDisplay
from src.ui.widgets.dialogs import show_error, show_confirmation
from src.ui.service_integration import get_ui_service_integrator, OperationType
from src.services import assembly_service
from src.utils.constants import PADDING_MEDIUM, PADDING_LARGE

class RecordAssemblyDialog(ctk.CTkToplevel):
    def __init__(self, parent, finished_good: FinishedGood):
        super().__init__(parent)
        self.finished_good = finished_good
        self.result: Optional[dict] = None
        self._can_assemble = False
        self.service_integrator = get_ui_service_integrator()

        self._setup_window()
        self._create_widgets()
        self._setup_modal()
        self._check_availability()

    def get_result(self) -> Optional[dict]:
        return self.result
```

---

### Subtask T024 - Implement Dialog Layout

**Layout**:
```
Row 0: Header (FinishedGood name)
Row 1: Quantity label + entry
Row 2: Notes label + textbox
Row 3: AvailabilityDisplay (expandable)
Row 4: Button frame (Refresh | Confirm | Cancel)
```

**Implementation**:
```python
def _setup_window(self):
    self.title(f"Record Assembly - {self.finished_good.display_name}")
    self.geometry("450x500")
    self.minsize(400, 450)

    self.grid_columnconfigure(1, weight=1)
    self.grid_rowconfigure(3, weight=1)

def _create_widgets(self):
    # Header
    header = ctk.CTkLabel(self, text=self.finished_good.display_name,
                          font=ctk.CTkFont(size=18, weight="bold"))
    header.grid(row=0, column=0, columnspan=2, pady=PADDING_LARGE)

    # Quantity
    ctk.CTkLabel(self, text="Quantity:").grid(row=1, column=0, sticky="e", padx=PADDING_MEDIUM)
    self.quantity_entry = ctk.CTkEntry(self, width=100)
    self.quantity_entry.insert(0, "1")
    self.quantity_entry.grid(row=1, column=1, sticky="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

    # Notes
    ctk.CTkLabel(self, text="Notes:").grid(row=2, column=0, sticky="ne", padx=PADDING_MEDIUM)
    self.notes_textbox = ctk.CTkTextbox(self, height=60)
    self.notes_textbox.grid(row=2, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

    # Availability display
    self.availability_display = AvailabilityDisplay(self, title="Component Availability")
    self.availability_display.grid(row=3, column=0, columnspan=2, sticky="nsew",
                                    padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

    self._create_buttons()
```

---

### Subtask T025 - Implement Availability Check on Open

**Implementation**:
```python
def _check_availability(self):
    quantity = self._get_quantity()
    if quantity < 1:
        return

    result = self.service_integrator.execute_service_operation(
        operation_name="Check Assembly Availability",
        operation_type=OperationType.READ,
        service_function=lambda: assembly_service.check_can_assemble(
            self.finished_good.id,
            quantity
        ),
        parent_widget=self,
        error_context="Checking component availability"
    )

    if result:
        self.availability_display.set_availability(result)
        self._can_assemble = result.get("can_assemble", False)
    else:
        self._can_assemble = False

    self._update_confirm_button()
```

**Note**: Assembly availability returns different component types:
- `finished_unit` - FinishedUnit components
- `finished_good` - Nested FinishedGood components
- `packaging` - Packaging products

Ensure AvailabilityDisplay handles all three types.

---

### Subtask T026 - Implement Refresh Button

**Implementation**:
```python
def _create_buttons(self):
    button_frame = ctk.CTkFrame(self)
    button_frame.grid(row=4, column=0, columnspan=2, pady=PADDING_LARGE)

    self.refresh_btn = ctk.CTkButton(button_frame, text="Refresh Availability",
                                      command=self._check_availability, width=140)
    self.refresh_btn.pack(side="left", padx=PADDING_MEDIUM)

    self.confirm_btn = ctk.CTkButton(button_frame, text="Confirm",
                                      command=self._on_confirm, width=100)
    self.confirm_btn.pack(side="left", padx=PADDING_MEDIUM)

    cancel_btn = ctk.CTkButton(button_frame, text="Cancel",
                                command=self._on_cancel, width=100)
    cancel_btn.pack(side="left", padx=PADDING_MEDIUM)

def _update_confirm_button(self):
    state = "normal" if self._can_assemble else "disabled"
    self.confirm_btn.configure(state=state)

def _on_cancel(self):
    self.result = None
    self.destroy()
```

---

### Subtask T027 - Implement Confirm with Service

**Implementation**:
```python
def _on_confirm(self):
    if not self._validate():
        return

    quantity = self._get_quantity()
    notes = self.notes_textbox.get("1.0", "end-1c").strip() or None

    message = (
        f"Assemble {quantity} {self.finished_good.display_name}?\n\n"
        f"This will consume components from inventory.\n"
        f"This action cannot be undone."
    )
    if not show_confirmation("Confirm Assembly", message, parent=self):
        return

    result = self.service_integrator.execute_service_operation(
        operation_name="Record Assembly",
        operation_type=OperationType.CREATE,
        service_function=lambda: assembly_service.record_assembly(
            finished_good_id=self.finished_good.id,
            quantity=quantity,
            notes=notes
        ),
        parent_widget=self,
        success_message=f"Assembled {quantity} {self.finished_good.display_name}",
        error_context="Recording assembly",
        show_success_dialog=True
    )

    if result:
        self.result = {
            "finished_good_id": self.finished_good.id,
            "quantity": quantity,
            "notes": notes,
            "assembly_run_id": result.get("assembly_run_id")
        }
        self.destroy()
```

---

### Subtask T028 - Add Validation

**Implementation**:
```python
def _validate(self) -> bool:
    quantity = self._get_quantity()
    if quantity < 1:
        show_error("Validation Error", "Quantity must be at least 1.", parent=self)
        return False

    if not self._can_assemble:
        show_error("Insufficient Components",
            "Cannot assemble - some components are insufficient.\n"
            "Check the availability display for details.", parent=self)
        return False

    return True

def _get_quantity(self) -> int:
    try:
        return int(self.quantity_entry.get())
    except ValueError:
        return 0
```

---

## Test Strategy

**Manual Testing**:
1. Open dialog for FinishedGood with defined composition
2. Verify availability shows FU and packaging status
3. Try confirm with insufficient components
4. Try confirm with sufficient components
5. Verify inventory updates after success

**Error Handling Note (FR-014)**: UIServiceIntegrator automatically handles service exceptions and displays user-friendly error dialogs. All errors like `InsufficientInventoryError` are mapped to appropriate messages - no additional error handling code needed.

## Definition of Done Checklist

- [ ] T023: Dialog class created
- [ ] T024: Layout implemented
- [ ] T025: Availability check on open
- [ ] T026: Refresh button works
- [ ] T027: Confirm calls service
- [ ] T028: Validation prevents invalid input
- [ ] Dialog follows modal pattern
- [ ] Handles all component types (FU, FG, packaging)

## Activity Log

- 2025-12-10T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-10T07:14:00Z – system – shell_pid= – lane=doing – Moved to doing
- 2025-12-10T07:15:21Z – system – shell_pid= – lane=for_review – Moved to for_review
- 2025-12-10T15:25:21Z – system – shell_pid= – lane=done – Code review approved - Assembly recording dialog implements all requirements
