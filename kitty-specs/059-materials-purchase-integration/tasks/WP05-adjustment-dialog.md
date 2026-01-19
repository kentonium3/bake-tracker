---
work_package_id: "WP05"
subtasks:
  - "T025"
  - "T026"
  - "T027"
  - "T028"
  - "T029"
  - "T030"
  - "T031"
title: "Manual Adjustment Dialog"
phase: "Wave 1 - Core UI"
lane: "doing"
assignee: ""
agent: "claude-opus"
shell_pid: "84672"
review_status: ""
reviewed_by: ""
dependencies:
  - "WP02"
history:
  - timestamp: "2026-01-18T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 - Manual Adjustment Dialog

## Important: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
# Depends on WP02 (needs adjust_inventory service method)
spec-kitty implement WP05
```

---

## Objectives & Success Criteria

Create MaterialAdjustmentDialog for manual inventory adjustments. This enables users to:
- Adjust "each" materials using Add/Subtract/Set operations
- Adjust "variable" materials (linear_cm, square_cm) using percentage input
- See live preview of the new quantity before confirming
- Record adjustment notes for audit trail

**Success Criteria**:
- [ ] Dialog displays appropriate UI based on material type
- [ ] Live preview shows calculated new quantity
- [ ] Validation prevents invalid adjustments (negative result)
- [ ] Notes are recorded with adjustment
- [ ] Service method called correctly on save
- [ ] All tests pass

---

## Context & Constraints

**Feature**: F059 - Materials Purchase Integration & Workflows
**Reference Documents**:
- Spec: `kitty-specs/059-materials-purchase-integration/spec.md`
- Plan: `kitty-specs/059-materials-purchase-integration/plan.md`
- Research: `kitty-specs/059-materials-purchase-integration/research.md`

**Dialog Pattern** (from research.md):
```python
# CTkToplevel modal setup order (CRITICAL)
dialog = ctk.CTkToplevel(parent)
dialog.transient(parent)
dialog.grab_set()
dialog.wait_visibility()
dialog.focus_force()
```

**Key Design Decision** (from spec clarification):
- "each" materials: Add/Subtract/Set operations with direct quantity input
- "variable" materials (linear_cm, square_cm): Percentage input representing "what percentage remains"
- 50% means keep half, 0% means fully depleted

**Key Files**:
- `src/ui/dialogs/material_adjustment_dialog.py` (NEW file)
- `src/services/material_inventory_service.py` (consume - adjust_inventory)
- `src/ui/dialogs/` (reference existing dialogs for patterns)

---

## Subtasks & Detailed Guidance

### Subtask T025 - Create MaterialAdjustmentDialog Class

**Purpose**: Set up the dialog shell with modal behavior.

**Steps**:
1. Create new file `src/ui/dialogs/material_adjustment_dialog.py`
2. Implement basic dialog structure:

```python
import customtkinter as ctk
from typing import Optional, Dict, Any
from decimal import Decimal


class MaterialAdjustmentDialog(ctk.CTkToplevel):
    """Dialog for adjusting material inventory quantities."""

    def __init__(
        self,
        parent,
        inventory_item: Dict[str, Any],
        on_save: Optional[callable] = None
    ):
        """Initialize the adjustment dialog.

        Args:
            parent: Parent window
            inventory_item: Dict with inventory item data including:
                - id: Item ID
                - product_name: Display name
                - quantity_remaining: Current quantity
                - base_unit_type: "each", "linear_cm", or "square_cm"
            on_save: Callback when adjustment is saved
        """
        super().__init__(parent)

        self._inventory_item = inventory_item
        self._on_save = on_save
        self._result = None

        # Store values for calculations
        self._current_qty = Decimal(str(inventory_item.get("quantity_remaining", 0)))
        self._base_unit_type = inventory_item.get("base_unit_type", "each")

        self._setup_window()
        self._create_widgets()
        self._setup_modal()

    def _setup_window(self):
        """Configure window properties."""
        self.title("Adjust Inventory")
        self.geometry("400x350")
        self.resizable(False, False)

        # Center on parent
        self.update_idletasks()
        parent_x = self.master.winfo_rootx()
        parent_y = self.master.winfo_rooty()
        parent_w = self.master.winfo_width()
        parent_h = self.master.winfo_height()

        x = parent_x + (parent_w - 400) // 2
        y = parent_y + (parent_h - 350) // 2
        self.geometry(f"+{x}+{y}")

    def _setup_modal(self):
        """Set up modal behavior (CRITICAL ORDER)."""
        self.transient(self.master)
        self.grab_set()
        self.wait_visibility()
        self.focus_force()

    def _create_widgets(self):
        """Create all dialog widgets."""
        # Header with item info
        self._create_header()

        # Adjustment controls (type-specific)
        if self._base_unit_type == "each":
            self._create_each_controls()
        else:
            self._create_variable_controls()

        # Preview section
        self._create_preview()

        # Notes field
        self._create_notes()

        # Action buttons
        self._create_buttons()

    def wait_for_result(self) -> Optional[Dict[str, Any]]:
        """Block until dialog closes and return result."""
        self.wait_window()
        return self._result
```

**Files**:
- `src/ui/dialogs/material_adjustment_dialog.py` (NEW)

**Validation**:
- [ ] Dialog opens as modal
- [ ] Dialog centers on parent window
- [ ] Close button/X works correctly
- [ ] No interaction with parent while open

---

### Subtask T026 - Implement "each" Materials UI

**Purpose**: Create adjustment controls for discrete materials.

**Steps**:
1. Add the "each" controls method:

```python
def _create_each_controls(self):
    """Create controls for 'each' material adjustments."""
    self._controls_frame = ctk.CTkFrame(self)
    self._controls_frame.pack(fill="x", padx=20, pady=10)

    # Adjustment type selection
    ctk.CTkLabel(
        self._controls_frame,
        text="Adjustment Type:",
        font=ctk.CTkFont(weight="bold")
    ).pack(anchor="w")

    self._adjustment_type_var = ctk.StringVar(value="add")

    types_frame = ctk.CTkFrame(self._controls_frame)
    types_frame.pack(fill="x", pady=5)

    for value, label in [("add", "Add"), ("subtract", "Subtract"), ("set", "Set To")]:
        ctk.CTkRadioButton(
            types_frame,
            text=label,
            variable=self._adjustment_type_var,
            value=value,
            command=self._update_preview
        ).pack(side="left", padx=10)

    # Quantity input
    ctk.CTkLabel(
        self._controls_frame,
        text="Quantity:",
        font=ctk.CTkFont(weight="bold")
    ).pack(anchor="w", pady=(10, 0))

    self._quantity_var = ctk.StringVar(value="0")
    self._quantity_var.trace_add("write", lambda *args: self._update_preview())

    self._quantity_entry = ctk.CTkEntry(
        self._controls_frame,
        textvariable=self._quantity_var,
        width=100
    )
    self._quantity_entry.pack(anchor="w", pady=5)

    # Unit label
    ctk.CTkLabel(
        self._controls_frame,
        text=f"(in {self._base_unit_type})",
        text_color="gray"
    ).pack(anchor="w")
```

2. Add calculation method for "each":

```python
def _calculate_each_adjustment(self) -> Optional[Decimal]:
    """Calculate new quantity for 'each' adjustment."""
    try:
        value = Decimal(self._quantity_var.get() or "0")
    except:
        return None

    adj_type = self._adjustment_type_var.get()

    if adj_type == "add":
        return self._current_qty + value
    elif adj_type == "subtract":
        return self._current_qty - value
    elif adj_type == "set":
        return value
    return None
```

**Files**:
- `src/ui/dialogs/material_adjustment_dialog.py` (extend)

**Parallel?**: Yes - can develop alongside T027

**Validation**:
- [ ] Radio buttons select adjustment type
- [ ] Quantity input accepts numbers
- [ ] Preview updates as type/value changes

---

### Subtask T027 - Implement "variable" Materials UI

**Purpose**: Create percentage-based adjustment for linear/area materials.

**Steps**:
1. Add the "variable" controls method:

```python
def _create_variable_controls(self):
    """Create controls for 'variable' material adjustments (percentage)."""
    self._controls_frame = ctk.CTkFrame(self)
    self._controls_frame.pack(fill="x", padx=20, pady=10)

    # Explanation
    unit_label = "cm" if self._base_unit_type == "linear_cm" else "cm²"
    ctk.CTkLabel(
        self._controls_frame,
        text=f"Current: {self._current_qty:.2f} {unit_label}",
        font=ctk.CTkFont(weight="bold")
    ).pack(anchor="w")

    ctk.CTkLabel(
        self._controls_frame,
        text="Enter percentage remaining (0-100):",
        text_color="gray"
    ).pack(anchor="w", pady=(5, 0))

    # Percentage input
    percentage_frame = ctk.CTkFrame(self._controls_frame)
    percentage_frame.pack(fill="x", pady=10)

    self._percentage_var = ctk.StringVar(value="100")
    self._percentage_var.trace_add("write", lambda *args: self._update_preview())

    self._percentage_entry = ctk.CTkEntry(
        percentage_frame,
        textvariable=self._percentage_var,
        width=80
    )
    self._percentage_entry.pack(side="left")

    ctk.CTkLabel(percentage_frame, text="%").pack(side="left", padx=5)

    # Quick preset buttons
    presets_frame = ctk.CTkFrame(self._controls_frame)
    presets_frame.pack(fill="x", pady=5)

    for pct in [100, 75, 50, 25, 0]:
        ctk.CTkButton(
            presets_frame,
            text=f"{pct}%",
            width=50,
            command=lambda p=pct: self._set_percentage(p)
        ).pack(side="left", padx=2)

def _set_percentage(self, pct: int):
    """Set percentage to a preset value."""
    self._percentage_var.set(str(pct))
```

2. Add calculation method for "variable":

```python
def _calculate_variable_adjustment(self) -> Optional[Decimal]:
    """Calculate new quantity for percentage adjustment."""
    try:
        pct = Decimal(self._percentage_var.get() or "0")
    except:
        return None

    if pct < 0 or pct > 100:
        return None

    new_qty = (self._current_qty * pct) / Decimal("100")
    return new_qty.quantize(Decimal("0.01"))
```

**Files**:
- `src/ui/dialogs/material_adjustment_dialog.py` (extend)

**Parallel?**: Yes - can develop alongside T026

**Validation**:
- [ ] Percentage input accepts 0-100
- [ ] Preset buttons set correct values
- [ ] Preview shows calculated quantity

---

### Subtask T028 - Add Live Preview Calculation

**Purpose**: Show real-time preview of adjustment result.

**Steps**:
1. Create preview section:

```python
def _create_preview(self):
    """Create the preview display section."""
    self._preview_frame = ctk.CTkFrame(self)
    self._preview_frame.pack(fill="x", padx=20, pady=10)

    ctk.CTkLabel(
        self._preview_frame,
        text="Preview:",
        font=ctk.CTkFont(weight="bold")
    ).pack(anchor="w")

    # Current → New display
    self._preview_label = ctk.CTkLabel(
        self._preview_frame,
        text="",
        font=ctk.CTkFont(size=14)
    )
    self._preview_label.pack(anchor="w", pady=5)

    # Warning label (for invalid adjustments)
    self._warning_label = ctk.CTkLabel(
        self._preview_frame,
        text="",
        text_color="red"
    )
    self._warning_label.pack(anchor="w")
```

2. Implement update method:

```python
def _update_preview(self):
    """Update the preview display based on current inputs."""
    if self._base_unit_type == "each":
        new_qty = self._calculate_each_adjustment()
    else:
        new_qty = self._calculate_variable_adjustment()

    unit = self._base_unit_type
    if unit == "linear_cm":
        unit = "cm"
    elif unit == "square_cm":
        unit = "cm²"

    if new_qty is None:
        self._preview_label.configure(
            text=f"{self._current_qty:.2f} → ???",
            text_color="gray"
        )
        self._warning_label.configure(text="Invalid input")
        self._save_btn.configure(state="disabled")
        return

    # Determine color based on change
    if new_qty < 0:
        color = "red"
        self._warning_label.configure(text="Cannot result in negative quantity!")
        self._save_btn.configure(state="disabled")
    elif new_qty < self._current_qty:
        color = "red"  # Decrease
        self._warning_label.configure(text="")
        self._save_btn.configure(state="normal")
    elif new_qty > self._current_qty:
        color = "green"  # Increase
        self._warning_label.configure(text="")
        self._save_btn.configure(state="normal")
    else:
        color = "gray"  # No change
        self._warning_label.configure(text="")
        self._save_btn.configure(state="normal")

    self._preview_label.configure(
        text=f"{self._current_qty:.2f} {unit} → {new_qty:.2f} {unit}",
        text_color=color
    )
```

**Files**:
- `src/ui/dialogs/material_adjustment_dialog.py` (extend)

**Validation**:
- [ ] Preview updates in real-time as values change
- [ ] Color coding: gray (no change), green (increase), red (decrease)
- [ ] Negative result shows error, disables save
- [ ] Invalid input shows appropriate message

---

### Subtask T029 - Add Notes Field

**Purpose**: Allow user to record reason for adjustment.

**Steps**:
1. Create notes section:

```python
def _create_notes(self):
    """Create the notes input field."""
    notes_frame = ctk.CTkFrame(self)
    notes_frame.pack(fill="x", padx=20, pady=10)

    ctk.CTkLabel(
        notes_frame,
        text="Reason (optional):",
        font=ctk.CTkFont(weight="bold")
    ).pack(anchor="w")

    self._notes_var = ctk.StringVar()
    self._notes_entry = ctk.CTkEntry(
        notes_frame,
        textvariable=self._notes_var,
        placeholder_text="e.g., Physical inventory count, damaged goods...",
        width=350
    )
    self._notes_entry.pack(fill="x", pady=5)
```

**Files**:
- `src/ui/dialogs/material_adjustment_dialog.py` (extend)

**Validation**:
- [ ] Notes field accepts text input
- [ ] Placeholder text provides guidance
- [ ] Notes are optional (empty allowed)

---

### Subtask T030 - Wire to Service on Save

**Purpose**: Connect dialog to MaterialInventoryService.adjust_inventory().

**Steps**:
1. Create action buttons:

```python
def _create_buttons(self):
    """Create Save and Cancel buttons."""
    buttons_frame = ctk.CTkFrame(self)
    buttons_frame.pack(fill="x", padx=20, pady=20)

    self._cancel_btn = ctk.CTkButton(
        buttons_frame,
        text="Cancel",
        command=self._on_cancel,
        fg_color="gray"
    )
    self._cancel_btn.pack(side="right", padx=5)

    self._save_btn = ctk.CTkButton(
        buttons_frame,
        text="Save Adjustment",
        command=self._on_save_click
    )
    self._save_btn.pack(side="right", padx=5)

def _create_header(self):
    """Create header with item info."""
    header_frame = ctk.CTkFrame(self)
    header_frame.pack(fill="x", padx=20, pady=10)

    ctk.CTkLabel(
        header_frame,
        text=self._inventory_item.get("product_name", "Unknown Product"),
        font=ctk.CTkFont(size=16, weight="bold")
    ).pack(anchor="w")

    ctk.CTkLabel(
        header_frame,
        text=f"Item ID: {self._inventory_item.get('id')}",
        text_color="gray"
    ).pack(anchor="w")
```

2. Implement save handler:

```python
def _on_save_click(self):
    """Handle save button click."""
    from src.services.material_inventory_service import adjust_inventory

    item_id = self._inventory_item["id"]
    notes = self._notes_var.get().strip() or None

    try:
        if self._base_unit_type == "each":
            # Determine adjustment type and value
            adj_type = self._adjustment_type_var.get()
            value = Decimal(self._quantity_var.get() or "0")

            result = adjust_inventory(
                inventory_item_id=item_id,
                adjustment_type=adj_type,
                value=value,
                notes=notes
            )
        else:
            # Variable material - percentage
            percentage = Decimal(self._percentage_var.get() or "100")

            result = adjust_inventory(
                inventory_item_id=item_id,
                adjustment_type="percentage",
                value=percentage,
                notes=notes
            )

        self._result = result

        # Call callback if provided
        if self._on_save:
            self._on_save(result)

        self.destroy()

    except Exception as e:
        # Show error in dialog
        self._warning_label.configure(text=f"Error: {str(e)}")

def _on_cancel(self):
    """Handle cancel button click."""
    self._result = None
    self.destroy()
```

**Files**:
- `src/ui/dialogs/material_adjustment_dialog.py` (complete)

**Validation**:
- [ ] Save calls adjust_inventory with correct parameters
- [ ] Cancel closes without calling service
- [ ] Errors display in warning label
- [ ] Dialog closes on successful save

---

### Subtask T031 - Handle Validation

**Purpose**: Ensure all inputs are validated before save.

**Steps**:
1. Add validation to save handler (already partially in T028):

```python
def _validate_inputs(self) -> tuple[bool, str]:
    """Validate all inputs before saving.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if self._base_unit_type == "each":
        # Validate quantity is a valid number
        try:
            value = Decimal(self._quantity_var.get() or "0")
            if value < 0:
                return False, "Quantity cannot be negative"
        except:
            return False, "Invalid quantity value"

        # Validate result won't be negative
        new_qty = self._calculate_each_adjustment()
        if new_qty is None:
            return False, "Unable to calculate new quantity"
        if new_qty < 0:
            return False, f"Adjustment would result in negative quantity ({new_qty})"

    else:
        # Validate percentage
        try:
            pct = Decimal(self._percentage_var.get() or "0")
            if pct < 0 or pct > 100:
                return False, "Percentage must be between 0 and 100"
        except:
            return False, "Invalid percentage value"

    return True, ""
```

2. Update save handler to use validation:

```python
def _on_save_click(self):
    """Handle save button click."""
    # Validate first
    is_valid, error = self._validate_inputs()
    if not is_valid:
        self._warning_label.configure(text=error)
        return

    # ... rest of save logic from T030 ...
```

3. Disable save button when invalid (already in T028's _update_preview)

**Files**:
- `src/ui/dialogs/material_adjustment_dialog.py` (extend)

**Validation**:
- [ ] Invalid number input shows error
- [ ] Negative result prevents save
- [ ] Out-of-range percentage (>100) shows error
- [ ] Save button disabled when invalid

---

## Test Strategy

Run tests with:
```bash
./run-tests.sh src/tests/ui/dialogs/test_material_adjustment_dialog.py -v
```

Manual testing:
1. Open adjustment dialog for an "each" material
2. Test Add/Subtract/Set operations
3. Test preview color coding
4. Test validation (negative result)
5. Test notes recording
6. Repeat for "variable" material (percentage)
7. Verify percentage presets work
8. Test 0% (fully depleted) scenario

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Wrong unit type detection | Pass base_unit_type from inventory item dict |
| Modal not blocking | Follow exact CTkToplevel setup order |
| Decimal precision issues | Use Decimal throughout, quantize for display |

---

## Definition of Done Checklist

- [ ] T025: Dialog class created with modal behavior
- [ ] T026: "each" materials UI (Add/Subtract/Set) working
- [ ] T027: "variable" materials UI (percentage) working
- [ ] T028: Live preview with color coding
- [ ] T029: Notes field captures adjustment reason
- [ ] T030: Save calls adjust_inventory service correctly
- [ ] T031: Validation prevents invalid adjustments
- [ ] Manual testing passes all scenarios
- [ ] tasks.md updated with status change

---

## Review Guidance

- Verify modal setup order: transient → grab_set → wait_visibility → focus_force
- Check percentage logic: 50% means keep half (not remove half)
- Ensure preview updates on every keystroke
- Verify service is called with correct parameters

---

## Activity Log

- 2026-01-18T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-19T01:34:29Z – claude-opus – shell_pid=84672 – lane=doing – Started implementation via workflow command
