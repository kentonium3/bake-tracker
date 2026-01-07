---
work_package_id: "WP05"
subtasks:
  - "T024"
  - "T025"
  - "T026"
  - "T027"
  - "T028"
  - "T029"
title: "UI Integration & Wiring"
phase: "Phase 2 - UI Layer (Gemini)"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: ""
history:
  - timestamp: "2026-01-07T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 - UI Integration & Wiring

## Objectives & Success Criteria

- Add [Adjust] button to each inventory item row
- Wire button to open adjustment dialog
- Connect dialog Apply to manual_adjustment() service
- Handle validation errors and display to user
- Refresh inventory list after successful adjustment
- Update depletion history view to show manual adjustments

**Success**: Full workflow works: click Adjust -> enter data -> Apply -> inventory updates and history shows new record.

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/041-manual-inventory-adjustments/spec.md` (FR-001)
- Contract: `kitty-specs/041-manual-inventory-adjustments/contracts/inventory_adjustment_service.py`
- Existing UI: `src/ui/inventory_tab.py`

**Constraints**:
- Use absolute imports from src root
- Display user-friendly error messages
- Maintain existing UI patterns

**Dependencies**:
- WP02 must be complete (service methods for wiring)
- WP04 must be complete (dialog for button to open)

## Subtasks & Detailed Guidance

### Subtask T024 - Add [Adjust] button to inventory tab [P]

**Purpose**: Provide entry point for manual adjustments.

**Steps**:
1. Open `src/ui/inventory_tab.py`
2. Locate where inventory items are rendered (likely a list or treeview)
3. Add [Adjust] button to each row:

```python
# In the item row creation/rendering code
adjust_button = ctk.CTkButton(
    row_frame,  # or appropriate parent
    text="Adjust",
    width=70,
    command=lambda item=inventory_item: self._on_adjust_click(item),
)
adjust_button.pack(side="right", padx=5)
```

**Files**: `src/ui/inventory_tab.py`
**Parallel?**: Yes - can be done parallel with T029

### Subtask T025 - Wire button to dialog

**Purpose**: Open dialog when button clicked.

**Steps**:
```python
# Add import at top
from src.ui.dialogs.adjustment_dialog import AdjustmentDialog

# Add method to class
def _on_adjust_click(self, inventory_item):
    """Handle adjust button click - open adjustment dialog."""
    dialog = AdjustmentDialog(
        parent=self,  # or self.winfo_toplevel()
        inventory_item=inventory_item,
        on_apply=self._on_adjustment_applied,
    )
    # Dialog is modal, waits for user
```

**Files**: `src/ui/inventory_tab.py`
**Parallel?**: No - depends on T024

### Subtask T026 - Wire Apply to service

**Purpose**: Call service when user applies adjustment.

**Steps**:
```python
# Add imports at top
from decimal import Decimal
from src.services.inventory_item_service import manual_adjustment
from src.models.enums import DepletionReason

def _on_adjustment_applied(
    self,
    inventory_item_id: int,
    quantity: Decimal,
    reason: DepletionReason,
    notes: str,
):
    """Handle adjustment applied from dialog."""
    try:
        # Call service
        depletion = manual_adjustment(
            inventory_item_id=inventory_item_id,
            quantity_to_deplete=quantity,
            reason=reason,
            notes=notes,
        )

        # Show success message
        self._show_success(
            f"Adjustment applied: {depletion.quantity_depleted} depleted"
        )

        # Refresh inventory list
        self._refresh_inventory_list()

    except Exception as e:
        self._show_error(str(e))
```

**Files**: `src/ui/inventory_tab.py`
**Parallel?**: No - depends on T025

### Subtask T027 - Handle ValidationError

**Purpose**: Display user-friendly error messages.

**Steps**:
```python
# Add import
from src.services.exceptions import (
    ValidationError as ServiceValidationError,
    InventoryItemNotFound,
)

def _on_adjustment_applied(self, ...):
    """Handle adjustment applied from dialog."""
    try:
        # Validate quantity before calling service
        if quantity is None or quantity <= 0:
            self._show_error("Please enter a valid positive quantity")
            return

        depletion = manual_adjustment(...)
        # ... success handling

    except ServiceValidationError as e:
        # Extract user-friendly message
        messages = e.messages if hasattr(e, 'messages') else [str(e)]
        self._show_error("\n".join(messages))

    except InventoryItemNotFound as e:
        self._show_error(f"Inventory item not found: {e}")

    except Exception as e:
        self._show_error(f"An error occurred: {e}")

def _show_error(self, message: str):
    """Show error dialog to user."""
    from tkinter import messagebox
    messagebox.showerror("Error", message)

def _show_success(self, message: str):
    """Show success dialog to user."""
    from tkinter import messagebox
    messagebox.showinfo("Success", message)
```

**Files**: `src/ui/inventory_tab.py`
**Parallel?**: No - builds on T026

### Subtask T028 - Refresh inventory after adjustment

**Purpose**: Update display to show new quantities.

**Steps**:
```python
def _refresh_inventory_list(self):
    """Reload inventory data and update display."""
    # This depends on existing inventory_tab implementation
    # Common patterns:

    # Option 1: If there's a load/refresh method
    self.load_inventory_items()

    # Option 2: If using a data source
    self.inventory_data = get_inventory_items()
    self._render_inventory_list()

    # Option 3: If parent has refresh
    self.master.refresh()
```

**Files**: `src/ui/inventory_tab.py`
**Parallel?**: No - builds on T027

### Subtask T029 - Update history view [P]

**Purpose**: Show manual adjustments in depletion history with reason and notes.

**Steps**:
1. Locate existing depletion history view in inventory_tab.py
2. Update to show depletion_reason and notes columns:

```python
def _render_depletion_history(self, depletions):
    """Render depletion history for selected item."""
    # Add reason column to display
    # Headers: Date | Reason | Quantity | Cost | Notes

    for depletion in depletions:
        date_str = depletion.depletion_date.strftime("%Y-%m-%d")
        reason_display = self._format_reason(depletion.depletion_reason)
        qty_str = f"{depletion.quantity_depleted}"
        cost_str = f"${depletion.cost:.2f}"
        notes_str = self._truncate_notes(depletion.notes)

        # Render row with all columns
        # ...

def _format_reason(self, reason_value: str) -> str:
    """Format reason enum value for display."""
    # Map enum values to display labels
    labels = {
        "production": "Production",
        "assembly": "Assembly",
        "spoilage": "Spoilage/Waste",
        "gift": "Gift/Donation",
        "correction": "Physical Count Correction",
        "ad_hoc_usage": "Ad Hoc Usage",
        "other": "Other",
    }
    return labels.get(reason_value, reason_value.replace("_", " ").title())

def _truncate_notes(self, notes: str, max_len: int = 30) -> str:
    """Truncate notes with ellipsis for display."""
    if not notes:
        return ""
    if len(notes) <= max_len:
        return notes
    return notes[:max_len-3] + "..."
```

**Files**: `src/ui/inventory_tab.py`
**Parallel?**: Yes - can be done parallel with T024-T025

## Test Strategy

Manual integration testing:
1. Run application
2. Navigate to Inventory tab
3. Verify [Adjust] button appears on each row
4. Click Adjust -> Dialog opens with correct item info
5. Enter valid quantity -> Preview shows correct values
6. Click Apply -> Success message appears
7. Verify inventory quantity updated in list
8. View depletion history -> New record appears with reason/notes
9. Test error cases: quantity > available, empty quantity, OTHER without notes

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Import path issues | ImportError | Use absolute imports from src root |
| History view doesn't exist | Missing feature | Create minimal history display if needed |
| Button placement breaks layout | Poor UX | Test in different window sizes |

## Definition of Done Checklist

- [ ] [Adjust] button added to each inventory row
- [ ] Button opens AdjustmentDialog with correct item
- [ ] Dialog Apply calls manual_adjustment() service
- [ ] ValidationError displayed as user-friendly message
- [ ] InventoryItemNotFound handled gracefully
- [ ] Inventory list refreshes after successful adjustment
- [ ] Depletion history shows reason and notes columns
- [ ] Notes truncated with ellipsis, full text on hover (if supported)
- [ ] Full workflow tested end-to-end

## Review Guidance

- Verify error messages are user-friendly, not technical
- Check inventory refreshes immediately after adjustment
- Verify history shows both automatic (production) and manual depletions
- Test validation errors display correctly

## Activity Log

- 2026-01-07T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-07T17:14:07Z – claude – shell_pid= – lane=doing – Moved to doing
