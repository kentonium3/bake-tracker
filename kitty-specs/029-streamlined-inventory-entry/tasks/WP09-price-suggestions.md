---
work_package_id: WP09
title: Price Suggestions
lane: done
history:
- timestamp: '2025-12-24T23:15:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: system
assignee: claude
phase: Phase 3 - Advanced Features
review_status: ''
reviewed_by: ''
shell_pid: '33920'
subtasks:
- T060
- T061
- T062
- T063
- T064
- T065
- T066
- T067
---

# Work Package Prompt: WP09 – Price Suggestions

## Objectives & Success Criteria

**Goal**: Auto-fill price field with last purchase price and display informative hints.

**Success Criteria**:
- [ ] Price pre-fills when product AND supplier selected
- [ ] Hint shows "(last paid: $X.XX on MM/DD)" for same supplier
- [ ] Fallback shows "(last paid: $X.XX at [Supplier] on MM/DD)"
- [ ] Shows "(no purchase history)" when no history exists
- [ ] Price field remains editable
- [ ] Hint clears when user manually edits price
- [ ] Tests pass

## Context & Constraints

**References**:
- Spec: `kitty-specs/029-streamlined-inventory-entry/spec.md` (User Story 5 - Price Suggestions)
- Design: `docs/design/F029_streamlined_inventory_entry.md` (Price Suggestion section)

**Constraints**:
- Uses purchase_service from F028
- Depends on WP06/WP07 for product and supplier selection
- Price suggestions are helpful hints, not requirements
- User can always override

## Subtasks & Detailed Guidance

### Subtask T060 – Add price hint label

**Purpose**: Display suggestion context below price field.

**Steps**:
1. Add CTkLabel below price entry
2. Smaller font, gray color
3. Initially empty

**Code**:
```python
# In dialog setup, after price entry:
self.price_hint_label = ctk.CTkLabel(
    self,
    text="",
    font=("", 10),
    text_color="gray"
)
self.price_hint_label.grid(row=6, column=1, sticky="w", padx=10)
```

### Subtask T061 – Query on product+supplier select

**Purpose**: Trigger price suggestion at right moment.

**Steps**:
1. Call `_update_price_suggestion()` when both are selected
2. In product selection handler (if supplier already set)
3. In supplier selection handler (if product already set)

**Code**:
```python
def _on_product_selected(self, selected_value: str):
    # ... existing product selection logic ...

    # Trigger price suggestion if supplier selected
    if self.supplier_combo.get():
        self._update_price_suggestion()

def _on_supplier_selected(self, selected_value: str):
    # ... existing supplier selection logic ...

    # Trigger price suggestion if product selected
    if self.selected_product:
        self._update_price_suggestion()
```

### Subtask T062 – Primary price query

**Purpose**: Get last price at selected supplier.

**Steps**:
1. Query purchase_service for product+supplier combination
2. Return price and date if found
3. Return None if not found

**Code**:
```python
def _get_last_price_at_supplier(self, product_id: int, supplier_id: int):
    """Get last purchase price at specific supplier."""
    # Use purchase_service from F028
    # Expected signature may vary - check actual service
    history = self.purchase_service.get_purchase_history(
        product_id=product_id,
        supplier_id=supplier_id,
        limit=1
    )
    if history:
        return {
            'price': history[0].unit_price,
            'date': history[0].purchase_date
        }
    return None
```

### Subtask T063 – Fallback price query

**Purpose**: Get last price at any supplier if none at selected.

**Steps**:
1. Query purchase_service without supplier filter
2. Return price, date, and supplier info if found
3. Return None if no history anywhere

**Code**:
```python
def _get_last_price_any_supplier(self, product_id: int):
    """Get last purchase price at any supplier."""
    history = self.purchase_service.get_purchase_history(
        product_id=product_id,
        limit=1
    )
    if history:
        purchase = history[0]
        return {
            'price': purchase.unit_price,
            'date': purchase.purchase_date,
            'supplier_name': purchase.supplier.name,
            'supplier_city': purchase.supplier.city,
            'supplier_state': purchase.supplier.state
        }
    return None
```

### Subtask T064 – No-history display

**Purpose**: Clear indication when no history exists.

**Steps**:
1. Display "(no purchase history)" hint
2. Leave price field empty
3. User must enter price manually

**Code**:
```python
# In _update_price_suggestion, else branch:
self.price_entry.delete(0, 'end')
self.price_hint_label.configure(text="(no purchase history)")
```

### Subtask T065 – Pre-fill price field

**Purpose**: Set suggested price in entry field.

**Steps**:
1. Clear existing price
2. Insert suggested price formatted to 2 decimals
3. Price remains editable

**Code**:
```python
def _update_price_suggestion(self):
    """Update price field with suggestion from purchase history."""
    if not self.selected_product:
        return

    supplier_display = self.supplier_combo.get().replace("⭐ ", "").strip()
    supplier = self.supplier_map.get(supplier_display)
    if not supplier:
        return

    # Try primary query (same supplier)
    result = self._get_last_price_at_supplier(
        self.selected_product.id,
        supplier.id
    )

    if result:
        self.price_entry.delete(0, 'end')
        self.price_entry.insert(0, f"{result['price']:.2f}")
        date_str = result['date'].strftime('%m/%d')
        self.price_hint_label.configure(
            text=f"(last paid: ${result['price']:.2f} on {date_str})"
        )
        return

    # Try fallback (any supplier)
    fallback = self._get_last_price_any_supplier(self.selected_product.id)

    if fallback:
        self.price_entry.delete(0, 'end')
        self.price_entry.insert(0, f"{fallback['price']:.2f}")
        date_str = fallback['date'].strftime('%m/%d')
        supplier_name = f"{fallback['supplier_name']}"
        self.price_hint_label.configure(
            text=f"(last paid: ${fallback['price']:.2f} at {supplier_name} on {date_str})"
        )
        return

    # No history
    self.price_entry.delete(0, 'end')
    self.price_hint_label.configure(text="(no purchase history)")
```

### Subtask T066 – Clear hint on manual edit

**Purpose**: Remove hint when user takes over.

**Steps**:
1. Bind FocusIn or first KeyPress on price entry
2. Clear hint text
3. Optional: only clear on actual typing, not just focus

**Code**:
```python
# In dialog setup:
self.price_entry.bind('<Key>', self._on_price_key)

def _on_price_key(self, event):
    """Clear hint when user types in price field."""
    # Ignore navigation keys
    if event.keysym not in ('Tab', 'Return', 'Escape', 'Up', 'Down'):
        self.price_hint_label.configure(text="")
```

### Subtask T067 – Tests [P]

**Purpose**: Verify price suggestion scenarios.

**Test Cases**:
```python
def test_price_suggestion_same_supplier(mock_dialog, mock_purchase_service):
    """Price should pre-fill from same supplier history."""
    mock_purchase_service.get_purchase_history.return_value = [
        MockPurchase(unit_price=Decimal('8.99'), purchase_date=date(2025, 12, 15))
    ]

    dialog = create_dialog()
    dialog.selected_product = MockProduct(id=1)
    dialog.supplier_combo.set('Costco')
    dialog._update_price_suggestion()

    assert dialog.price_entry.get() == '8.99'
    assert 'last paid' in dialog.price_hint_label.cget('text')

def test_price_suggestion_fallback(mock_dialog, mock_purchase_service):
    """Price should fall back to other supplier."""
    # First query returns empty, second returns result
    mock_purchase_service.get_purchase_history.side_effect = [
        [],  # No history at selected supplier
        [MockPurchase(unit_price=Decimal('9.50'), ...)]  # History at other
    ]

    dialog = create_dialog()
    dialog._update_price_suggestion()

    assert '9.50' in dialog.price_entry.get()
    assert 'at' in dialog.price_hint_label.cget('text')  # Shows supplier name

def test_price_suggestion_no_history(mock_dialog, mock_purchase_service):
    """No history should show appropriate message."""
    mock_purchase_service.get_purchase_history.return_value = []

    dialog = create_dialog()
    dialog._update_price_suggestion()

    assert dialog.price_entry.get() == ''
    assert 'no purchase history' in dialog.price_hint_label.cget('text')
```

**Parallel?**: Yes, can be written alongside implementation

## Test Strategy

Manual testing:
1. Select product with purchase history at current supplier
2. Verify price pre-fills and hint shows date
3. Change supplier to one without history for this product
4. Verify fallback shows other supplier in hint
5. Select product with no history anywhere
6. Verify "(no purchase history)" displayed
7. Type in price field
8. Verify hint clears

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| F028 API changes | Verify purchase_service signatures |
| Performance of queries | Limit to 1 result |
| Decimal formatting | Use f-string with .2f |

## Definition of Done Checklist

- [ ] Price hint label added below price field
- [ ] Price suggestion triggers on product+supplier selection
- [ ] Primary query (same supplier) works
- [ ] Fallback query (any supplier) works with different hint
- [ ] No-history case shows appropriate message
- [ ] Price pre-fills correctly (2 decimal places)
- [ ] Hint clears on user typing
- [ ] Tests pass

## Review Guidance

**Reviewers should verify**:
1. Price pre-fills correctly formatted
2. Hint shows correct date format (MM/DD)
3. Fallback hint includes supplier name
4. Hint clears when user types
5. No errors when no purchase history

## Activity Log

- 2025-12-24T23:15:00Z – system – lane=planned – Prompt created.
- 2025-12-25T15:19:54Z – system – shell_pid= – lane=done – Moved to done
