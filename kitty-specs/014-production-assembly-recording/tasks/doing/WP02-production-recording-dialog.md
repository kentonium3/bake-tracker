---
work_package_id: "WP02"
subtasks:
  - "T005"
  - "T006"
  - "T007"
  - "T008"
  - "T009"
  - "T010"
title: "Production Recording Dialog"
phase: "Phase 2 - Production Recording"
lane: "doing"
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

# Work Package Prompt: WP02 - Production Recording Dialog

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Create the Record Production dialog that allows users to record batch production with:
- Batch count input
- Adjustable actual yield
- Optional notes
- Availability check display
- Confirm/Cancel actions

**Success Criteria**:
- Dialog opens as modal over parent
- Availability check runs on dialog open
- "Refresh Availability" button re-runs check with current batch count
- Confirm button disabled when availability insufficient
- On confirm, calls `record_batch_production()` and returns result
- Proper validation of inputs

## Context & Constraints

**Reference Documents**:
- `kitty-specs/014-production-assembly-recording/contracts/ui-components.md` - Dialog contract
- `kitty-specs/014-production-assembly-recording/research.md` - Existing dialog patterns

**Dependencies**:
- WP01 must be complete (AvailabilityDisplay widget)
- Feature 013 services: `batch_production_service.check_can_produce()`, `record_batch_production()`

**Existing Patterns**:
- `src/ui/forms/finished_unit_form.py` - Modal dialog pattern
- `src/ui/service_integration.py` - UIServiceIntegrator usage

## Subtasks & Detailed Guidance

### Subtask T005 - Create RecordProductionDialog Class

**Purpose**: Establish the dialog class structure following existing patterns.

**File**: `src/ui/forms/record_production_dialog.py`

**Steps**:
1. Create new file with imports
2. Define `RecordProductionDialog(ctk.CTkToplevel)` class
3. Implement `__init__(self, parent, finished_unit)`:
   - Store finished_unit reference
   - Initialize `self.result = None`
   - Set `self._initializing = True` flag
   - Call modal setup methods
   - Set `self._initializing = False`
4. Implement `get_result(self) -> dict | None` method

**Class Structure**:
```python
import customtkinter as ctk
from typing import Optional
from src.models import FinishedUnit
from src.ui.widgets.availability_display import AvailabilityDisplay
from src.ui.widgets.dialogs import show_error, show_confirmation
from src.ui.service_integration import get_ui_service_integrator, OperationType
from src.services import batch_production_service
from src.utils.constants import PADDING_MEDIUM, PADDING_LARGE

class RecordProductionDialog(ctk.CTkToplevel):
    def __init__(self, parent, finished_unit: FinishedUnit):
        super().__init__(parent)
        self.finished_unit = finished_unit
        self.result: Optional[dict] = None
        self._initializing = True
        self.service_integrator = get_ui_service_integrator()

        self._setup_window()
        self._create_widgets()
        self._setup_modal()
        self._check_availability()

        self._initializing = False

    def get_result(self) -> Optional[dict]:
        return self.result
```

---

### Subtask T006 - Implement Dialog Layout

**Purpose**: Create the visual layout with all input fields and display areas.

**Steps**:
1. Implement `_setup_window(self)`:
   - Set title: "Record Production - {finished_unit.display_name}"
   - Set minimum size (400x500)
   - Configure grid weights
2. Implement `_create_widgets(self)`:
   - Header section with FinishedUnit name and recipe
   - Batch count input (CTkEntry with label)
   - Expected yield display (calculated, read-only)
   - Actual yield input (CTkEntry, defaults to expected)
   - Notes textarea (CTkTextbox)
   - AvailabilityDisplay widget
   - Button frame with Refresh, Confirm, Cancel

**Layout Grid**:
```
Row 0: Header (name, recipe)
Row 1: Batch Count label + entry
Row 2: Expected Yield label + display
Row 3: Actual Yield label + entry
Row 4: Notes label + textbox
Row 5: AvailabilityDisplay (expandable)
Row 6: Button frame (Refresh | Confirm | Cancel)
```

**Implementation Details**:
```python
def _setup_window(self):
    self.title(f"Record Production - {self.finished_unit.display_name}")
    self.geometry("450x550")
    self.minsize(400, 500)
    self.resizable(True, True)

    # Configure grid
    self.grid_columnconfigure(1, weight=1)
    self.grid_rowconfigure(5, weight=1)  # Availability expands

def _create_widgets(self):
    # Header
    header = ctk.CTkLabel(self, text=self.finished_unit.display_name,
                          font=ctk.CTkFont(size=18, weight="bold"))
    header.grid(row=0, column=0, columnspan=2, pady=PADDING_LARGE)

    # Recipe info
    recipe_name = self.finished_unit.recipe.name if self.finished_unit.recipe else "No recipe"
    recipe_label = ctk.CTkLabel(self, text=f"Recipe: {recipe_name}")
    recipe_label.grid(row=0, column=0, columnspan=2, pady=(40, PADDING_MEDIUM))

    # Batch count
    ctk.CTkLabel(self, text="Batch Count:").grid(row=1, column=0, sticky="e", padx=PADDING_MEDIUM)
    self.batch_entry = ctk.CTkEntry(self, width=100)
    self.batch_entry.insert(0, "1")
    self.batch_entry.grid(row=1, column=1, sticky="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)
    self.batch_entry.bind("<KeyRelease>", self._on_batch_changed)

    # Expected yield (calculated)
    ctk.CTkLabel(self, text="Expected Yield:").grid(row=2, column=0, sticky="e", padx=PADDING_MEDIUM)
    self.expected_yield_label = ctk.CTkLabel(self, text="0")
    self.expected_yield_label.grid(row=2, column=1, sticky="w", padx=PADDING_MEDIUM)

    # Actual yield
    ctk.CTkLabel(self, text="Actual Yield:").grid(row=3, column=0, sticky="e", padx=PADDING_MEDIUM)
    self.yield_entry = ctk.CTkEntry(self, width=100)
    self.yield_entry.grid(row=3, column=1, sticky="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

    # Notes
    ctk.CTkLabel(self, text="Notes:").grid(row=4, column=0, sticky="ne", padx=PADDING_MEDIUM)
    self.notes_textbox = ctk.CTkTextbox(self, height=60)
    self.notes_textbox.grid(row=4, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

    # Availability display
    self.availability_display = AvailabilityDisplay(self, title="Ingredient Availability")
    self.availability_display.grid(row=5, column=0, columnspan=2, sticky="nsew",
                                    padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

    # Buttons
    self._create_buttons()

    # Update expected yield
    self._update_expected_yield()
```

---

### Subtask T007 - Implement Availability Check on Open

**Purpose**: Run availability check when dialog opens and display results.

**Steps**:
1. Implement `_check_availability(self)` method
2. Call `check_can_produce()` via service integrator
3. Pass result to AvailabilityDisplay widget
4. Update Confirm button state based on result

**Implementation**:
```python
def _check_availability(self):
    if not self.finished_unit.recipe:
        self.availability_display.clear()
        self._can_produce = False
        self._update_confirm_button()
        return

    batch_count = self._get_batch_count()
    if batch_count < 1:
        return

    result = self.service_integrator.execute_service_operation(
        operation_name="Check Production Availability",
        operation_type=OperationType.READ,
        service_function=lambda: batch_production_service.check_can_produce(
            self.finished_unit.recipe_id,
            batch_count
        ),
        parent_widget=self,
        error_context="Checking ingredient availability"
    )

    if result:
        self.availability_display.set_availability(result)
        self._can_produce = result.get("can_produce", False)
    else:
        self._can_produce = False

    self._update_confirm_button()
```

---

### Subtask T008 - Implement Refresh Availability Button

**Purpose**: Allow user to re-run availability check after changing batch count.

**Steps**:
1. Add "Refresh Availability" button to button frame
2. Wire button to `_on_refresh_availability()` handler
3. Handler calls `_check_availability()` with current batch count

**Implementation**:
```python
def _create_buttons(self):
    button_frame = ctk.CTkFrame(self)
    button_frame.grid(row=6, column=0, columnspan=2, pady=PADDING_LARGE)

    self.refresh_btn = ctk.CTkButton(button_frame, text="Refresh Availability",
                                      command=self._on_refresh_availability, width=140)
    self.refresh_btn.pack(side="left", padx=PADDING_MEDIUM)

    self.confirm_btn = ctk.CTkButton(button_frame, text="Confirm",
                                      command=self._on_confirm, width=100)
    self.confirm_btn.pack(side="left", padx=PADDING_MEDIUM)

    cancel_btn = ctk.CTkButton(button_frame, text="Cancel",
                                command=self._on_cancel, width=100)
    cancel_btn.pack(side="left", padx=PADDING_MEDIUM)

def _on_refresh_availability(self):
    self._check_availability()
```

---

### Subtask T009 - Implement Confirm Button with Service Integration

**Purpose**: Record production when user confirms, using service integrator.

**Steps**:
1. Implement `_on_confirm(self)` method
2. Validate inputs first
3. Show confirmation dialog
4. Call `record_batch_production()` via service integrator
5. On success, set `self.result` and close dialog

**Implementation**:
```python
def _on_confirm(self):
    if not self._validate():
        return

    batch_count = self._get_batch_count()
    actual_yield = self._get_actual_yield()
    notes = self.notes_textbox.get("1.0", "end-1c").strip() or None

    # Confirmation dialog
    message = (
        f"Record {batch_count} batch(es) of {self.finished_unit.display_name}?\n\n"
        f"Expected yield: {self._calculate_expected_yield(batch_count)}\n"
        f"Actual yield: {actual_yield}\n\n"
        f"This will consume ingredients from inventory.\n"
        f"This action cannot be undone."
    )
    if not show_confirmation("Confirm Production", message, parent=self):
        return

    result = self.service_integrator.execute_service_operation(
        operation_name="Record Production",
        operation_type=OperationType.CREATE,
        service_function=lambda: batch_production_service.record_batch_production(
            recipe_id=self.finished_unit.recipe_id,
            finished_unit_id=self.finished_unit.id,
            num_batches=batch_count,
            actual_yield=actual_yield,
            notes=notes
        ),
        parent_widget=self,
        success_message=f"Recorded {batch_count} batch(es) - {actual_yield} units produced",
        error_context="Recording batch production",
        show_success_dialog=True
    )

    if result:
        self.result = {
            "recipe_id": self.finished_unit.recipe_id,
            "finished_unit_id": self.finished_unit.id,
            "num_batches": batch_count,
            "actual_yield": actual_yield,
            "notes": notes,
            "production_run_id": result.get("production_run_id")
        }
        self.destroy()
```

---

### Subtask T010 - Add Input Validation

**Purpose**: Validate batch count and yield before allowing confirm.

**Steps**:
1. Implement `_validate(self) -> bool` method
2. Check batch count >= 1
3. Check actual yield >= 0 (0 allowed for failed batches)
4. Show appropriate error messages

**Implementation**:
```python
def _validate(self) -> bool:
    # Validate batch count
    batch_count = self._get_batch_count()
    if batch_count < 1:
        show_error("Validation Error", "Batch count must be at least 1.", parent=self)
        return False

    # Validate actual yield
    actual_yield = self._get_actual_yield()
    if actual_yield < 0:
        show_error("Validation Error", "Actual yield cannot be negative.", parent=self)
        return False

    # Warn if yield is 0
    if actual_yield == 0:
        if not show_confirmation("Zero Yield",
            "Actual yield is 0. This will consume ingredients but produce no units.\n\n"
            "Continue anyway?", parent=self):
            return False

    # Check availability
    if not self._can_produce:
        show_error("Insufficient Inventory",
            "Cannot produce - some ingredients are insufficient.\n"
            "Check the availability display for details.", parent=self)
        return False

    return True

def _get_batch_count(self) -> int:
    try:
        return int(self.batch_entry.get())
    except ValueError:
        return 0

def _get_actual_yield(self) -> int:
    try:
        return int(self.yield_entry.get())
    except ValueError:
        return self._calculate_expected_yield(self._get_batch_count())

def _calculate_expected_yield(self, batch_count: int) -> int:
    items_per_batch = self.finished_unit.items_per_batch or 1
    return batch_count * items_per_batch

def _update_expected_yield(self):
    batch_count = self._get_batch_count()
    expected = self._calculate_expected_yield(batch_count)
    self.expected_yield_label.configure(text=str(expected))
    # Also update actual yield default if user hasn't changed it
    if not self._initializing:
        current = self.yield_entry.get()
        if not current or current == str(self._last_expected):
            self.yield_entry.delete(0, "end")
            self.yield_entry.insert(0, str(expected))
    self._last_expected = expected

def _on_batch_changed(self, event=None):
    if self._initializing:
        return
    self._update_expected_yield()

def _update_confirm_button(self):
    if self._can_produce:
        self.confirm_btn.configure(state="normal")
    else:
        self.confirm_btn.configure(state="disabled")
```

---

## Test Strategy

**Manual Testing**:
1. Open dialog for a FinishedUnit with recipe
2. Verify availability check runs on open
3. Change batch count and click Refresh
4. Try to confirm with insufficient inventory (should fail)
5. Try to confirm with sufficient inventory (should succeed)
6. Verify actual yield defaults correctly
7. Test zero yield warning

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Race condition: inventory changes between check and record | Service handles atomically; show error if fails |
| FinishedUnit has no recipe | Disable dialog or show error |
| Service exceptions not handled | UIServiceIntegrator provides consistent handling (FR-014). All errors like `InsufficientInventoryError` are automatically mapped to user-friendly error dialogs. |

## Definition of Done Checklist

- [ ] T005: Dialog class structure created
- [ ] T006: All UI elements laid out correctly
- [ ] T007: Availability check runs on dialog open
- [ ] T008: Refresh button works
- [ ] T009: Confirm records production via service
- [ ] T010: Validation prevents invalid input
- [ ] Dialog follows modal pattern (blocks parent)
- [ ] Confirm disabled when availability insufficient

## Review Guidance

- Test with FinishedUnit that has recipe with ingredients
- Test with insufficient inventory
- Verify confirmation dialog appears before recording
- Check error handling for edge cases
- Ensure dialog closes after successful recording

## Activity Log

- 2025-12-10T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-10T06:56:10Z – claude – shell_pid=45064 – lane=doing – Started implementation of Production Recording Dialog
