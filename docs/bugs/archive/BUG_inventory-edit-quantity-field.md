# Bug Fix: Inventory Edit Form Shows Wrong Quantity Field

**Branch**: `bugfix/inventory-edit-quantity-field`  
**Priority**: CRITICAL (users will accidentally reset inventory quantities)  
**Estimated Effort**: 30 minutes

## Context

**Bug**: Edit Inventory form shows `quantity_purchased` (original purchase amount) instead of `quantity_remaining` (current stock level).

**Example**:
- Pantry tab shows: `0.666667 bags` (what's left after using some)
- Edit form shows: `2.0` (what was originally purchased)

**Problem**: When user saves the form, they'll accidentally reset remaining quantity to purchased quantity, losing usage history.

## Current State vs Expected

### Current (Broken)
```
Pantry:      0.67 bags (2 lb) remaining
Edit Form:   Quantity: [2.0___]  ← WRONG - showing quantity_purchased
User saves → quantity_remaining reset to 2.0 ❌
```

### Expected (Fixed)
```
Pantry:      0.67 bags (2 lb) remaining
Edit Form:   Quantity: [0.67___]  ← CORRECT - showing quantity_remaining
User saves → quantity_remaining stays 0.67 ✅
```

## Root Cause

**Edit form is loading wrong field**:
```python
# WRONG
self.quantity_entry.insert(0, str(item.quantity_purchased))

# CORRECT
self.quantity_entry.insert(0, str(item.quantity_remaining))
```

## Implementation Requirements

### 1. Fix Form Load Logic
**File**: Inventory edit form (likely `src/ui/forms/inventory_edit_dialog.py`)

**Change**:
```python
def _load_inventory_item(self):
    """Load inventory item into form."""
    with session_scope() as session:
        item = session.query(InventoryItem).get(self.item_id)
        
        # BEFORE (WRONG)
        self.quantity_entry.delete(0, 'end')
        self.quantity_entry.insert(0, str(item.quantity_purchased))  # ❌
        
        # AFTER (CORRECT)
        self.quantity_entry.delete(0, 'end')
        self.quantity_entry.insert(0, str(item.quantity_remaining))  # ✅
```

### 2. Fix Form Save Logic
**File**: Same edit form file

**Ensure saves to correct field**:
```python
def _on_save(self):
    """Save inventory item."""
    try:
        new_quantity = Decimal(self.quantity_entry.get())
        
        with session_scope() as session:
            item = session.query(InventoryItem).get(self.item_id)
            
            # Save to quantity_remaining, NOT quantity_purchased
            item.quantity_remaining = new_quantity  # ✅
            # item.quantity_purchased should NOT be changed here ❌
            
            session.commit()
            
    except ValueError:
        messagebox.showerror("Error", "Invalid quantity")
```

### 3. Verify Field Usage Throughout Form
**File**: Same edit form file

**Check all references to quantity**:
- Form label: Should say "Quantity Remaining" or "Current Quantity"
- Calculator section: Uses `quantity_remaining` (already correct from BUG_inventory-quantity-calculator)
- Display text: Shows current stock level
- Validation: Checks `quantity_remaining >= 0`

## Implementation Tasks

### Task 1: Locate and Fix Load Method
**File**: Inventory edit form

1. Find form initialization/load method
2. Change `item.quantity_purchased` to `item.quantity_remaining`
3. Verify no other places load quantity_purchased
4. Update field label if it says "Quantity Purchased"

### Task 2: Verify Save Method
**File**: Same file

1. Confirm save method updates `quantity_remaining`
2. Confirm it does NOT update `quantity_purchased`
3. Ensure calculator updates also use `quantity_remaining`

### Task 3: Update Field Label
**File**: Same file

**Change label to be clear**:
```python
# BEFORE (ambiguous)
quantity_label = ctk.CTkLabel(frame, text="Quantity:")

# AFTER (clear)
quantity_label = ctk.CTkLabel(frame, text="Quantity Remaining:")
# or
quantity_label = ctk.CTkLabel(frame, text="Current Quantity:")
```

### Task 4: Add Validation
**File**: Same file

```python
def _validate_quantity(self):
    """Validate quantity input."""
    try:
        qty = Decimal(self.quantity_entry.get())
        
        # Quantity remaining must be >= 0
        if qty < 0:
            raise ValidationError("Quantity cannot be negative")
        
        # Optionally: quantity remaining should not exceed quantity purchased
        if qty > self.original_quantity_purchased:
            # Warning, not error - user might have received more
            result = messagebox.askyesno(
                "Confirm Quantity",
                f"Quantity ({qty}) exceeds original purchase ({self.original_quantity_purchased}). Continue?"
            )
            if not result:
                return False
        
        return True
        
    except (ValueError, InvalidOperation):
        messagebox.showerror("Error", "Invalid quantity format")
        return False
```

## Testing Checklist

### Form Load
- [ ] Edit form shows correct current quantity (0.67, not 2.0)
- [ ] Field label says "Quantity Remaining" or "Current Quantity"
- [ ] Value matches what's shown in Pantry tab listing
- [ ] Decimal precision matches (0.67 not 0.666667)

### Form Save
- [ ] Changing quantity updates `quantity_remaining`
- [ ] `quantity_purchased` is not changed
- [ ] New quantity persists after save
- [ ] Pantry tab shows updated quantity after refresh

### Edge Cases
- [ ] Increasing quantity above purchased works (received more)
- [ ] Decreasing quantity to 0 works (used all)
- [ ] Validation prevents negative quantities
- [ ] Decimal quantities save correctly

### Integration
- [ ] Calculator section uses same quantity field
- [ ] All three calculator methods update `quantity_remaining`
- [ ] No confusion between purchased vs remaining

## Success Criteria

1. **Correct Field**: Edit form shows and updates `quantity_remaining`
2. **No Data Loss**: Users can't accidentally reset quantity to purchased amount
3. **Clear Labeling**: Field label clearly indicates "remaining" not "purchased"
4. **Validation Works**: Prevents invalid quantities
5. **Consistency**: Pantry tab and edit form show same value
6. **User Validation**: Primary user confirms quantities behave correctly

## Important Notes

**The two quantity fields serve different purposes**:
- `quantity_purchased`: Historical record - how much was originally bought (rarely changes)
- `quantity_remaining`: Current stock level - how much is left now (changes with usage)

**Edit form should**:
- Display: `quantity_remaining`
- Update: `quantity_remaining`
- Never touch: `quantity_purchased` (unless specifically editing purchase history)

## Related Issues

This bug is closely related to the calculator feature (BUG_inventory-quantity-calculator.md) which also works with `quantity_remaining`.

## Related Files

**Primary File**:
- `src/ui/forms/inventory_edit_dialog.py` - Edit form logic

**Models** (reference):
- `src/models/inventory_item.py` - InventoryItem model with both fields

## Git Workflow

```bash
git checkout -b bugfix/inventory-edit-quantity-field
git commit -m "fix: edit form loads quantity_remaining instead of quantity_purchased"
git commit -m "fix: edit form saves to quantity_remaining only"
git commit -m "refactor: update field label to 'Quantity Remaining'"
git push
```

---

**CRITICAL**: This is a data corruption bug. Users editing inventory will accidentally reset their remaining quantities. Fix immediately.
