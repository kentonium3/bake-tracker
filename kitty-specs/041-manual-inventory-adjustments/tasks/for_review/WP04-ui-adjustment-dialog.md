---
work_package_id: "WP04"
subtasks:
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
title: "UI Adjustment Dialog"
phase: "Phase 2 - UI Layer (Gemini)"
lane: "for_review"
assignee: ""
agent: "gemini"
shell_pid: ""
history:
  - timestamp: "2026-01-07T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - UI Adjustment Dialog

## Objectives & Success Criteria

- Create modal dialog for manual inventory adjustments
- Display current inventory details (product, quantity, unit cost)
- Implement reason dropdown with all DepletionReason values
- Implement live preview that updates as user types
- Preview shows new quantity and cost impact

**Success**: Dialog opens, shows current info, live preview updates within 100ms of input (SC-003).

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/041-manual-inventory-adjustments/spec.md` (FR-001 to FR-003)
- Design Doc: `docs/design/_F041_manual_inventory_adjust.md` (UI mockups)
- Quickstart: `kitty-specs/041-manual-inventory-adjustments/quickstart.md` (UI labels)
- Constitution: `.kittify/memory/constitution.md` (Principle I: User-Centric Design)

**Constraints**:
- Use CustomTkinter for modern appearance
- Dialog must be modal (blocks interaction with parent)
- Live preview must feel instant (<100ms per SC-003)
- Reason dropdown labels per quickstart.md table

**Dependencies**:
- WP01 must be complete (needs DepletionReason enum for dropdown values)

## Subtasks & Detailed Guidance

### Subtask T017 - Create dialog class

**Purpose**: Establish dialog structure and initialization.

**Steps**:
1. Create `src/ui/dialogs/adjustment_dialog.py`
2. Ensure `src/ui/dialogs/__init__.py` exists
3. Create dialog class:

```python
"""
Manual Inventory Adjustment Dialog.

Provides a modal dialog for recording manual inventory depletions
with live preview of quantity and cost impact.
"""

import customtkinter as ctk
from decimal import Decimal
from typing import Optional, Callable

from src.models.enums import DepletionReason


class AdjustmentDialog(ctk.CTkToplevel):
    """
    Modal dialog for manual inventory adjustments.

    Args:
        parent: Parent window
        inventory_item: The InventoryItem to adjust
        on_apply: Callback function when adjustment is applied
    """

    # Reason labels for dropdown
    REASON_LABELS = {
        DepletionReason.SPOILAGE: "Spoilage/Waste",
        DepletionReason.GIFT: "Gift/Donation",
        DepletionReason.CORRECTION: "Physical Count Correction",
        DepletionReason.AD_HOC_USAGE: "Ad Hoc Usage (Testing/Personal)",
        DepletionReason.OTHER: "Other (specify in notes)",
    }

    def __init__(
        self,
        parent,
        inventory_item,
        on_apply: Optional[Callable] = None,
    ):
        super().__init__(parent)
        self.inventory_item = inventory_item
        self.on_apply = on_apply

        self.title("Adjust Inventory")
        self.geometry("450x500")
        self.resizable(False, False)

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Initialize UI
        self._create_widgets()
        self._layout_widgets()
        self._bind_events()

        # Center on parent
        self.update_idletasks()
        self._center_on_parent(parent)
```

**Files**: `src/ui/dialogs/adjustment_dialog.py` (NEW)
**Parallel?**: No - foundation for T018-T023

### Subtask T018 - Implement dialog layout

**Purpose**: Display current inventory information.

**Steps**:
```python
    def _create_widgets(self):
        """Create all dialog widgets."""
        # Current inventory info section
        self.info_frame = ctk.CTkFrame(self)

        product_name = self.inventory_item.product.display_name
        purchase_date = self.inventory_item.purchase_date
        current_qty = self.inventory_item.quantity
        unit = self.inventory_item.product.package_unit or "units"
        unit_cost = self.inventory_item.unit_cost or 0

        self.product_label = ctk.CTkLabel(
            self.info_frame,
            text=f"Product: {product_name}",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.date_label = ctk.CTkLabel(
            self.info_frame,
            text=f"Purchase Date: {purchase_date}",
        )
        self.quantity_label = ctk.CTkLabel(
            self.info_frame,
            text=f"Current Quantity: {current_qty} {unit}",
        )
        self.cost_label = ctk.CTkLabel(
            self.info_frame,
            text=f"Unit Cost: ${unit_cost:.2f}/{unit}",
        )

        # Store for calculations
        self.current_quantity = Decimal(str(current_qty))
        self.unit_cost = Decimal(str(unit_cost))
        self.unit = unit
```

**Files**: `src/ui/dialogs/adjustment_dialog.py`
**Parallel?**: No - builds on T017

### Subtask T019 - Add quantity input field

**Purpose**: Allow user to enter depletion amount.

**Steps**:
```python
        # Adjustment input section
        self.input_frame = ctk.CTkFrame(self)

        self.qty_label = ctk.CTkLabel(
            self.input_frame,
            text="Reduce By:",
        )
        self.qty_entry = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="Enter amount",
            width=150,
        )
        self.qty_unit_label = ctk.CTkLabel(
            self.input_frame,
            text=self.unit,
        )
```

**Files**: `src/ui/dialogs/adjustment_dialog.py`
**Parallel?**: No - sequential with layout

### Subtask T020 - Add reason dropdown

**Purpose**: Allow user to select depletion reason.

**Steps**:
```python
        # Reason dropdown
        self.reason_label = ctk.CTkLabel(
            self.input_frame,
            text="Reason:",
        )

        # Create dropdown values from enum
        self.reason_options = list(self.REASON_LABELS.values())
        self.reason_var = ctk.StringVar(value=self.reason_options[0])

        self.reason_dropdown = ctk.CTkComboBox(
            self.input_frame,
            values=self.reason_options,
            variable=self.reason_var,
            width=250,
            state="readonly",
        )

    def _get_selected_reason(self) -> DepletionReason:
        """Get the DepletionReason enum from dropdown selection."""
        label = self.reason_var.get()
        for reason, lbl in self.REASON_LABELS.items():
            if lbl == label:
                return reason
        return DepletionReason.OTHER
```

**Files**: `src/ui/dialogs/adjustment_dialog.py`
**Parallel?**: No - sequential with layout

### Subtask T021 - Add notes text field

**Purpose**: Allow user to add explanation (required for OTHER).

**Steps**:
```python
        # Notes field
        self.notes_label = ctk.CTkLabel(
            self.input_frame,
            text="Notes (optional):",
        )
        self.notes_entry = ctk.CTkTextbox(
            self.input_frame,
            height=80,
            width=300,
        )

    def _update_notes_requirement(self):
        """Update notes label based on selected reason."""
        reason = self._get_selected_reason()
        if reason == DepletionReason.OTHER:
            self.notes_label.configure(text="Notes (required):")
        else:
            self.notes_label.configure(text="Notes (optional):")
```

**Files**: `src/ui/dialogs/adjustment_dialog.py`
**Parallel?**: No - sequential with layout

### Subtask T022 - Implement live preview

**Purpose**: Show new quantity and cost impact as user types.

**Steps**:
```python
        # Preview section
        self.preview_frame = ctk.CTkFrame(self)

        self.preview_title = ctk.CTkLabel(
            self.preview_frame,
            text="Preview:",
            font=ctk.CTkFont(weight="bold"),
        )
        self.new_qty_label = ctk.CTkLabel(
            self.preview_frame,
            text="New Quantity: --",
        )
        self.cost_impact_label = ctk.CTkLabel(
            self.preview_frame,
            text="Cost Impact: --",
        )

    def _bind_events(self):
        """Bind event handlers."""
        # Live preview on key release
        self.qty_entry.bind("<KeyRelease>", self._update_preview)
        # Update notes requirement on reason change
        self.reason_dropdown.configure(command=self._on_reason_change)

    def _on_reason_change(self, _):
        """Handle reason dropdown change."""
        self._update_notes_requirement()

    def _update_preview(self, event=None):
        """Update preview labels based on current input."""
        try:
            qty_text = self.qty_entry.get().strip()
            if not qty_text:
                self.new_qty_label.configure(text="New Quantity: --")
                self.cost_impact_label.configure(text="Cost Impact: --")
                return

            qty = Decimal(qty_text)
            if qty <= 0:
                self.new_qty_label.configure(text="New Quantity: (invalid)")
                return

            new_qty = self.current_quantity - qty
            cost_impact = qty * self.unit_cost

            if new_qty < 0:
                self.new_qty_label.configure(
                    text=f"New Quantity: ERROR (exceeds available)",
                    text_color="red",
                )
            else:
                self.new_qty_label.configure(
                    text=f"New Quantity: {new_qty} {self.unit}",
                    text_color=("gray10", "gray90"),
                )
            self.cost_impact_label.configure(
                text=f"Cost Impact: ${cost_impact:.2f}",
            )
        except (ValueError, InvalidOperation):
            self.new_qty_label.configure(text="New Quantity: (invalid input)")
```

**Files**: `src/ui/dialogs/adjustment_dialog.py`
**Parallel?**: No - depends on input fields

### Subtask T023 - Add Apply and Cancel buttons

**Purpose**: Allow user to confirm or cancel adjustment.

**Steps**:
```python
        # Button frame
        self.button_frame = ctk.CTkFrame(self)

        self.cancel_button = ctk.CTkButton(
            self.button_frame,
            text="Cancel",
            command=self._on_cancel,
            fg_color="gray",
        )
        self.apply_button = ctk.CTkButton(
            self.button_frame,
            text="Apply Adjustment",
            command=self._on_apply,
        )

    def _layout_widgets(self):
        """Layout all widgets."""
        # Info section
        self.info_frame.pack(fill="x", padx=20, pady=(20, 10))
        self.product_label.pack(anchor="w")
        self.date_label.pack(anchor="w")
        self.quantity_label.pack(anchor="w")
        self.cost_label.pack(anchor="w")

        # Input section
        self.input_frame.pack(fill="x", padx=20, pady=10)
        self.qty_label.pack(anchor="w")
        qty_row = ctk.CTkFrame(self.input_frame)
        qty_row.pack(fill="x", pady=5)
        self.qty_entry.pack(in_=qty_row, side="left")
        self.qty_unit_label.pack(in_=qty_row, side="left", padx=5)

        self.reason_label.pack(anchor="w", pady=(10, 0))
        self.reason_dropdown.pack(anchor="w", pady=5)

        self.notes_label.pack(anchor="w", pady=(10, 0))
        self.notes_entry.pack(fill="x", pady=5)

        # Preview section
        self.preview_frame.pack(fill="x", padx=20, pady=10)
        self.preview_title.pack(anchor="w")
        self.new_qty_label.pack(anchor="w")
        self.cost_impact_label.pack(anchor="w")

        # Buttons
        self.button_frame.pack(fill="x", padx=20, pady=20)
        self.cancel_button.pack(side="left", padx=5)
        self.apply_button.pack(side="right", padx=5)

    def _on_cancel(self):
        """Handle cancel button click."""
        self.destroy()

    def _on_apply(self):
        """Handle apply button click."""
        # Collect values (validation happens in WP05 when wiring to service)
        try:
            qty_text = self.qty_entry.get().strip()
            quantity = Decimal(qty_text) if qty_text else None
            reason = self._get_selected_reason()
            notes = self.notes_entry.get("1.0", "end-1c").strip() or None

            if self.on_apply:
                self.on_apply(
                    inventory_item_id=self.inventory_item.id,
                    quantity=quantity,
                    reason=reason,
                    notes=notes,
                )
            self.destroy()
        except ValueError:
            # Show error for invalid quantity
            self.new_qty_label.configure(
                text="Please enter a valid number",
                text_color="red",
            )

    def _center_on_parent(self, parent):
        """Center dialog on parent window."""
        parent.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_x(), parent.winfo_y()
        w, h = self.winfo_width(), self.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"+{x}+{y}")
```

**Files**: `src/ui/dialogs/adjustment_dialog.py`
**Parallel?**: No - completes the dialog

## Test Strategy

Manual visual testing:
1. Run app, open inventory tab
2. Click Adjust on an item (requires WP05 button)
3. Verify dialog displays correct current info
4. Type in quantity field - verify preview updates
5. Change reason - verify notes label updates for OTHER
6. Click Apply - verify callback fires
7. Click Cancel - verify dialog closes

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Live preview lag | Poor UX | Keep calculation simple; debounce if needed |
| Modal doesn't block | User confusion | Use grab_set() and transient() |
| Layout breaks on resize | Poor UX | Set resizable(False, False) |

## Definition of Done Checklist

- [ ] Dialog class created in `src/ui/dialogs/adjustment_dialog.py`
- [ ] Current inventory info displayed (product, date, quantity, cost)
- [ ] Quantity input field with validation
- [ ] Reason dropdown with all DepletionReason values
- [ ] Notes field with conditional "required" label for OTHER
- [ ] Live preview updates on key release
- [ ] Apply and Cancel buttons functional
- [ ] Dialog is modal and centered on parent

## Review Guidance

- Verify reason labels match quickstart.md table
- Check live preview updates within 100ms (feels instant)
- Verify notes label changes to "required" for OTHER reason
- Test keyboard navigation works

## Activity Log

- 2026-01-07T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-07T16:58:59Z – gemini – shell_pid= – lane=doing – Moved to doing
- 2026-01-07T17:11:09Z – gemini – shell_pid= – lane=for_review – Moved to for_review
