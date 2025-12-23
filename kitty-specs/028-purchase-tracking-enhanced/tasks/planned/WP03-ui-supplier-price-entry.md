---
work_package_id: "WP03"
subtasks:
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
  - "T013"
  - "T014"
title: "UI Supplier Dropdown and Price Entry"
phase: "Phase 2 - UI Updates"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-22T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - UI Supplier Dropdown and Price Entry

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

**Goal**: Modify InventoryItemFormDialog to include supplier selection, price entry with suggestions, and proper validation. This completes the user-facing workflow for F028.

**Success Criteria**:
- Supplier dropdown appears in Add Inventory dialog, sorted alphabetically
- Price field with decimal validation
- Price hint shows last paid price (updates on supplier selection)
- Zero-price shows confirmation warning
- Negative price shows validation error
- Successful submission creates Purchase-linked InventoryItem

**User Stories**: US1 (Add Inventory with Supplier Selection), US2 (Price Suggestion from Purchase History)
**Functional Requirements**: FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008

---

## Context & Constraints

**Reference Documents**:
- `kitty-specs/028-purchase-tracking-enhanced/spec.md` - FR-002 through FR-008
- `kitty-specs/028-purchase-tracking-enhanced/plan.md` - Section 2.1
- `src/ui/inventory_tab.py` - Existing InventoryItemFormDialog

**Dependencies**:
- WP01: Price suggestion functions (`get_last_price_at_supplier`, `get_last_price_any_supplier`)
- WP02: Updated `add_to_inventory()` signature with supplier_id, unit_price

**UI Framework**: CustomTkinter
**Patterns**: Follow existing dialog patterns in `src/ui/`

---

## Subtasks & Detailed Guidance

### Subtask T008 - Add Supplier Dropdown

**Purpose**: Enable supplier selection (FR-002, FR-003).

**Steps**:
1. In `InventoryItemFormDialog.__init__()`, add supplier dropdown after product selection
2. Import and call `supplier_service.get_active_suppliers()` to populate options
3. Sort by display_name (already sorted by name in service)
4. Store selected supplier_id for submission

**Implementation**:
```python
from src.services import supplier_service

# In dialog initialization
self.suppliers = supplier_service.get_active_suppliers()
supplier_names = [s["display_name"] for s in self.suppliers]

self.supplier_label = ctk.CTkLabel(self, text="Supplier:")
self.supplier_label.grid(row=ROW, column=0, padx=10, pady=5, sticky="e")

self.supplier_var = ctk.StringVar(value="")
self.supplier_dropdown = ctk.CTkComboBox(
    self,
    values=supplier_names,
    variable=self.supplier_var,
    command=self._on_supplier_change,
    state="readonly"
)
self.supplier_dropdown.grid(row=ROW, column=1, padx=10, pady=5, sticky="ew")
```

**Files**: `src/ui/inventory_tab.py`
**Parallel?**: No - foundation for other UI changes

---

### Subtask T009 - Add Price Entry Field

**Purpose**: Enable price input with decimal validation.

**Steps**:
1. Add price entry field after supplier dropdown
2. Use CTkEntry with validation callback
3. Allow decimal input (0-9, single decimal point)
4. Store as Decimal for submission

**Implementation**:
```python
self.price_label = ctk.CTkLabel(self, text="Price ($):")
self.price_label.grid(row=ROW, column=0, padx=10, pady=5, sticky="e")

self.price_var = ctk.StringVar(value="")
self.price_entry = ctk.CTkEntry(
    self,
    textvariable=self.price_var,
    placeholder_text="0.00"
)
self.price_entry.grid(row=ROW, column=1, padx=10, pady=5, sticky="ew")

# Register validation
vcmd = (self.register(self._validate_price), '%P')
self.price_entry.configure(validate="key", validatecommand=vcmd)

def _validate_price(self, value):
    """Allow only valid decimal input."""
    if value == "":
        return True
    try:
        # Allow partial input like "12." during typing
        if value.endswith('.') and value.count('.') == 1:
            float(value + "0")
            return True
        float(value)
        return True
    except ValueError:
        return False
```

**Files**: `src/ui/inventory_tab.py`
**Parallel?**: No - sequential after T008

---

### Subtask T010 - Add Price Hint Label

**Purpose**: Display price suggestion context (FR-006).

**Steps**:
1. Add hint label below price entry
2. Style as secondary text (smaller, gray)
3. Update dynamically when supplier changes

**Implementation**:
```python
self.price_hint_label = ctk.CTkLabel(
    self,
    text="",
    font=("", 11),
    text_color="gray"
)
self.price_hint_label.grid(row=ROW, column=1, padx=10, pady=(0, 5), sticky="w")

def _update_price_hint(self, hint_text: str):
    """Update the price hint display."""
    self.price_hint_label.configure(text=hint_text)
```

**Hint Formats**:
- Same supplier history: `"(last paid: $8.99 on 2025-12-15)"`
- Fallback supplier: `"(last paid: $8.99 at Costco on 2025-12-15)"`
- No history: `"(no purchase history)"`

**Files**: `src/ui/inventory_tab.py`
**Parallel?**: No - sequential after T009

---

### Subtask T011 - Wire on_supplier_change Callback

**Purpose**: Fetch and display price suggestions on supplier selection.

**Steps**:
1. Create `_on_supplier_change()` callback
2. Get selected product_id and supplier_id
3. Call `get_last_price_at_supplier()` first
4. If None, call `get_last_price_any_supplier()` as fallback
5. Pre-fill price field and update hint

**Implementation**:
```python
from src.services import purchase_service

def _on_supplier_change(self, selected_value):
    """Handle supplier selection change."""
    product_id = self._get_selected_product_id()
    supplier_id = self._get_selected_supplier_id()

    if not product_id or not supplier_id:
        self._update_price_hint("")
        return

    # Try supplier-specific price first
    result = purchase_service.get_last_price_at_supplier(product_id, supplier_id)

    if result:
        # History at this supplier
        price = result["unit_price"]
        date_str = result["purchase_date"]
        self.price_var.set(price)
        self._update_price_hint(f"(last paid: ${price} on {date_str})")
    else:
        # Fallback to any supplier
        result = purchase_service.get_last_price_any_supplier(product_id)
        if result:
            price = result["unit_price"]
            date_str = result["purchase_date"]
            supplier_name = result["supplier_name"]
            self.price_var.set(price)
            self._update_price_hint(f"(last paid: ${price} at {supplier_name} on {date_str})")
        else:
            # No history
            self.price_var.set("")
            self._update_price_hint("(no purchase history)")

def _get_selected_supplier_id(self) -> Optional[int]:
    """Get supplier_id from dropdown selection."""
    selected = self.supplier_var.get()
    for supplier in self.suppliers:
        if supplier["display_name"] == selected:
            return supplier["id"]
    return None
```

**Files**: `src/ui/inventory_tab.py`
**Parallel?**: No - depends on T008, T009, T010

---

### Subtask T012 - Zero-Price Confirmation Warning

**Purpose**: Allow $0.00 but warn user (FR-007).

**Steps**:
1. In submission handler, check if price == 0
2. Show CTkMessagebox confirmation dialog
3. Only proceed if user confirms

**Implementation**:
```python
from CTkMessagebox import CTkMessagebox

def _validate_and_submit(self):
    """Validate form and submit."""
    price = self._get_price_value()

    # Zero price warning (FR-007)
    if price == Decimal("0.00"):
        result = CTkMessagebox(
            title="Confirm Zero Price",
            message="Price is $0.00. This may indicate a donation or free sample.\n\nProceed with zero price?",
            icon="warning",
            option_1="Cancel",
            option_2="Proceed"
        )
        if result.get() != "Proceed":
            return

    # Continue with submission...
```

**Files**: `src/ui/inventory_tab.py`
**Parallel?**: Yes - independent validation

---

### Subtask T013 - Negative Price Validation Error

**Purpose**: Reject negative prices (FR-008).

**Steps**:
1. In submission handler, check if price < 0
2. Show error message (inline or messagebox)
3. Prevent submission

**Implementation**:
```python
def _validate_and_submit(self):
    """Validate form and submit."""
    price = self._get_price_value()

    # Negative price error (FR-008)
    if price is not None and price < Decimal("0.00"):
        CTkMessagebox(
            title="Invalid Price",
            message="Price cannot be negative. Please enter a valid price.",
            icon="cancel"
        )
        return

    # Continue...
```

**Files**: `src/ui/inventory_tab.py`
**Parallel?**: Yes - independent validation

---

### Subtask T014 - Update Dialog Submission

**Purpose**: Call updated `add_to_inventory()` with new params.

**Steps**:
1. Validate supplier is selected (FR-002)
2. Validate price is entered
3. Get supplier_id and unit_price
4. Call `add_to_inventory()` with all params
5. Close dialog on success

**Implementation**:
```python
from decimal import Decimal
from src.services import inventory_item_service

def _submit(self):
    """Submit the form."""
    # Validate required fields
    supplier_id = self._get_selected_supplier_id()
    if not supplier_id:
        CTkMessagebox(
            title="Validation Error",
            message="Please select a supplier.",
            icon="cancel"
        )
        return

    price = self._get_price_value()
    if price is None:
        CTkMessagebox(
            title="Validation Error",
            message="Please enter a price.",
            icon="cancel"
        )
        return

    # Run validations from T012, T013...

    # Submit
    try:
        result = inventory_item_service.add_to_inventory(
            product_id=self._get_selected_product_id(),
            quantity=self._get_quantity_value(),
            supplier_id=supplier_id,
            unit_price=price,
            added_date=self._get_added_date(),
            expiration_date=self._get_expiration_date(),
            notes=self._get_notes(),
        )
        self.result = result
        self.destroy()
    except Exception as e:
        CTkMessagebox(
            title="Error",
            message=f"Failed to add inventory: {str(e)}",
            icon="cancel"
        )

def _get_price_value(self) -> Optional[Decimal]:
    """Get price as Decimal from entry field."""
    value = self.price_var.get().strip()
    if not value:
        return None
    try:
        return Decimal(value)
    except:
        return None
```

**Files**: `src/ui/inventory_tab.py`
**Parallel?**: No - depends on all prior UI subtasks

---

## Test Strategy

**Manual Testing** (no automated UI tests required):

1. Open Add Inventory dialog
2. Verify supplier dropdown appears with sorted suppliers
3. Select product with purchase history, select same supplier - verify price pre-fills
4. Select different supplier (no history at that supplier) - verify fallback hint
5. Select product with no history - verify "(no purchase history)" hint
6. Enter $0.00 - verify confirmation warning
7. Enter negative price - verify error message
8. Submit with all fields - verify success
9. Verify database has both Purchase and InventoryItem records

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| UI complexity increase | Follow existing patterns; price hints provide immediate value |
| Performance on supplier load | get_active_suppliers() already optimized |
| Decimal precision | Use Decimal throughout; format for display |

---

## Definition of Done Checklist

- [ ] Supplier dropdown populated and sorted
- [ ] Price entry field with decimal validation
- [ ] Price hint updates on supplier selection
- [ ] Zero-price confirmation warning works
- [ ] Negative price validation error works
- [ ] Supplier selection required (no blank)
- [ ] Submission calls updated add_to_inventory()
- [ ] Manual testing scenarios pass

---

## Review Guidance

**Verification Checkpoints**:
1. Dropdown shows all active suppliers, sorted
2. Price suggestion appears within 1 second
3. Hint format matches spec (date, supplier context)
4. Zero-price flow allows proceed after confirmation
5. Negative price blocks submission
6. Successful submission creates linked records

---

## Activity Log

- 2025-12-22T00:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks.
