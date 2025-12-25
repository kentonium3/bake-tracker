---
work_package_id: "WP10"
subtasks:
  - "T068"
  - "T069"
  - "T070"
  - "T071"
  - "T072"
  - "T073"
  - "T074"
title: "Validation Warnings"
phase: "Phase 4 - Polish"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-24T23:15:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP10 – Validation Warnings

## Objectives & Success Criteria

**Goal**: Add validation warnings for high prices and decimal quantities.

**Success Criteria**:
- [ ] Warning dialog appears when price > $100
- [ ] User can confirm or cancel high price
- [ ] Negative prices blocked with error
- [ ] Warning for decimal quantities on count-based units
- [ ] User can confirm or cancel decimal quantity
- [ ] Tests pass

## Context & Constraints

**References**:
- Spec: `kitty-specs/029-streamlined-inventory-entry/spec.md` (User Story 6 - Smart Defaults and Validation)
- Design: `docs/design/F029_streamlined_inventory_entry.md` (Validation section)

**Constraints**:
- Depends on complete dialog structure (WP06-09)
- Warnings are confirmable (not blocking errors)
- Negative prices are blocking errors
- $100 threshold is reasonable for baking supplies

## Subtasks & Detailed Guidance

### Subtask T068 – Price validation on FocusOut

**Purpose**: Validate price when user leaves field.

**Steps**:
1. Bind FocusOut event to price entry
2. Implement `_validate_price()` method
3. Return True/False for valid/invalid

**Code**:
```python
# In dialog setup:
self.price_entry.bind('<FocusOut>', self._on_price_focus_out)

def _on_price_focus_out(self, event):
    """Validate price when focus leaves field."""
    self._validate_price()

def _validate_price(self) -> bool:
    """Validate price value."""
    price_str = self.price_entry.get().strip()
    if not price_str:
        return True  # Empty is OK, will be caught on submit

    try:
        price = Decimal(price_str)
    except InvalidOperation:
        return True  # Invalid format caught on submit

    # Check for negative
    if price < 0:
        self._show_error("Price cannot be negative")
        self.price_entry.focus_set()
        return False

    # Check for high price
    if price > 100:
        if not self._confirm_high_price(price):
            self.price_entry.focus_set()
            return False

    return True
```

### Subtask T069 – High price warning dialog

**Purpose**: Confirmation for prices over $100.

**Steps**:
1. Use messagebox.askyesno for confirmation
2. Return True if user confirms, False if cancels
3. Include price in message

**Code**:
```python
from tkinter import messagebox

def _confirm_high_price(self, price: Decimal) -> bool:
    """Ask user to confirm high price."""
    return messagebox.askyesno(
        "Confirm High Price",
        f"Price is ${price:.2f} (over $100).\n\nIs this correct?",
        parent=self
    )
```

### Subtask T070 – Block negative prices

**Purpose**: Prevent invalid negative prices.

**Steps**:
1. Check if price < 0
2. Show error message (not confirmation)
3. Focus returns to price field

**Notes**: Already covered in T068 implementation.

### Subtask T071 – Quantity validation on FocusOut

**Purpose**: Validate quantity when user leaves field.

**Steps**:
1. Bind FocusOut event to quantity entry
2. Implement `_validate_quantity()` method
3. Check for decimal on count-based units

**Code**:
```python
# In dialog setup:
self.quantity_entry.bind('<FocusOut>', self._on_quantity_focus_out)

def _on_quantity_focus_out(self, event):
    """Validate quantity when focus leaves field."""
    self._validate_quantity()

def _validate_quantity(self) -> bool:
    """Validate quantity value."""
    qty_str = self.quantity_entry.get().strip()
    if not qty_str:
        return True  # Empty OK, caught on submit

    try:
        qty = Decimal(qty_str)
    except InvalidOperation:
        return True  # Invalid format caught on submit

    # Check for count-based unit with decimal
    if self.selected_product and self._is_count_based_unit():
        if qty != qty.to_integral_value():
            if not self._confirm_decimal_quantity(qty):
                self.quantity_entry.focus_set()
                return False

    return True
```

### Subtask T072 – Decimal quantity warning

**Purpose**: Confirmation for fractional counts.

**Steps**:
1. Check if quantity has decimal places
2. Use messagebox for confirmation
3. Allow user to proceed or correct

**Code**:
```python
def _confirm_decimal_quantity(self, qty: Decimal) -> bool:
    """Ask user to confirm decimal quantity for count-based unit."""
    return messagebox.askyesno(
        "Confirm Decimal Quantity",
        f"Package quantities are usually whole numbers.\n\n"
        f"You entered {qty}. Continue?",
        parent=self
    )
```

### Subtask T073 – Define count-based units

**Purpose**: Identify units where decimals are unusual.

**Steps**:
1. Define list of count-based units
2. Implement helper method to check

**Code**:
```python
COUNT_BASED_UNITS = ['count', 'bag', 'box', 'package', 'bottle', 'can', 'jar', 'carton']

def _is_count_based_unit(self) -> bool:
    """Check if selected product uses count-based unit."""
    if not self.selected_product:
        return False
    unit = self.selected_product.package_unit.lower()
    return unit in COUNT_BASED_UNITS
```

### Subtask T074 – Tests [P]

**Purpose**: Verify validation scenarios.

**Test Cases**:
```python
from unittest.mock import patch

def test_price_validation_blocks_negative():
    """Negative price should be blocked."""
    dialog = create_dialog()
    dialog.price_entry.insert(0, "-5.00")

    result = dialog._validate_price()

    assert result == False

@patch('tkinter.messagebox.askyesno', return_value=True)
def test_high_price_confirmation_accepted(mock_confirm):
    """User can confirm high price."""
    dialog = create_dialog()
    dialog.price_entry.insert(0, "150.00")

    result = dialog._validate_price()

    assert result == True
    mock_confirm.assert_called_once()

@patch('tkinter.messagebox.askyesno', return_value=False)
def test_high_price_confirmation_rejected(mock_confirm):
    """User can reject high price."""
    dialog = create_dialog()
    dialog.price_entry.insert(0, "150.00")

    result = dialog._validate_price()

    assert result == False

@patch('tkinter.messagebox.askyesno', return_value=False)
def test_decimal_quantity_warning(mock_confirm):
    """Decimal quantity on count unit shows warning."""
    dialog = create_dialog()
    dialog.selected_product = MockProduct(package_unit='bag')
    dialog.quantity_entry.insert(0, "1.5")

    result = dialog._validate_quantity()

    assert result == False
    mock_confirm.assert_called_once()

def test_decimal_quantity_ok_for_weight():
    """Decimal quantity OK for weight-based units."""
    dialog = create_dialog()
    dialog.selected_product = MockProduct(package_unit='lb')
    dialog.quantity_entry.insert(0, "1.5")

    result = dialog._validate_quantity()

    assert result == True
```

**Parallel?**: Yes, can be written alongside implementation

## Test Strategy

Manual testing:
1. Enter price $150 - verify confirmation dialog appears
2. Confirm high price - verify accepted
3. Reject high price - verify focus returns to field
4. Enter negative price - verify error message
5. Enter 1.5 quantity for "bag" unit - verify warning
6. Enter 1.5 quantity for "lb" unit - verify no warning

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Annoying UX | $100 threshold reasonable |
| Modal dialog blocking | Proper parent window |
| Focus management | Return focus on rejection |

## Definition of Done Checklist

- [ ] Price validation on FocusOut implemented
- [ ] High price ($100+) shows confirmation dialog
- [ ] Negative prices show error message
- [ ] Quantity validation on FocusOut implemented
- [ ] Decimal quantity on count units shows warning
- [ ] Count-based units list defined
- [ ] Tests pass

## Review Guidance

**Reviewers should verify**:
1. $100 threshold triggers warning (not $99.99)
2. Negative price is blocked (not confirmable)
3. Decimal warning only for count-based units
4. Focus returns to field on rejection
5. Valid prices/quantities don't trigger warnings

## Activity Log

- 2025-12-24T23:15:00Z – system – lane=planned – Prompt created.
