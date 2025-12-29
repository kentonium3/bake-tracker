# Bug Fix: Remove Expiration Date from UI

**Branch**: `bugfix/remove-expiration-from-ui`  
**Priority**: LOW (cleanup, not blocking)  
**Estimated Effort**: 20 minutes

## Context

**Expiration date field is not useful at this development phase**:
- Requires manual entry for every item
- Not currently being tracked or used
- Clutters UI with empty/unused field

**Action**: Remove from UI, keep in database schema for future use.

## Current State vs Expected

### Current (Cluttered)
```
My Pantry Tab:
Ingredient | Product | Brand | Qty Remaining | Expiration | Purchased
---------- | ------- | ----- | ------------- | ---------- | ---------
Chocolate  | Chips   | Ghir  | 2.5 jars      | [blank]    | 2024-12-01

Edit Inventory Form:
Product: [________]
Quantity: [________]
Location: [________]
Expiration: [________]  ← Empty, not useful
Purchased: [________]
```

### Expected (Clean)
```
My Pantry Tab:
Ingredient | Product | Brand | Qty Remaining | Purchased
---------- | ------- | ----- | ------------- | ---------
Chocolate  | Chips   | Ghir  | 2.5 jars      | 2024-12-01

Edit Inventory Form:
Product: [________]
Quantity: [________]
Location: [________]
Purchased: [________]
(Expiration field removed)
```

## Implementation Requirements

### 1. Remove from My Pantry Tab
**File**: `src/ui/inventory_tab.py`

**Check**: Was this already done in BUG_pantry-qty-format-correction?

**If not removed**:
```python
# BEFORE (5 columns)
columns = ('ingredient', 'product', 'brand', 'qty_remaining', 'expiration', 'purchased')

# AFTER (5 columns, no expiration)
columns = ('ingredient', 'product', 'brand', 'qty_remaining', 'purchased')
```

**Verify tree population doesn't reference expiration**:
```python
# Remove any code like:
expiration_display = item.expiration_date.strftime('%Y-%m-%d') if item.expiration_date else ''
```

### 2. Remove from Edit Inventory Form
**File**: Inventory edit form (likely `src/ui/forms/inventory_edit_dialog.py`)

**Remove**:
- Expiration date label
- Expiration date entry widget
- Expiration date validation
- Expiration date save logic

**Current** (probably has this):
```python
# Remove these lines
expiration_label = ctk.CTkLabel(frame, text="Expiration Date:")
expiration_label.grid(row=N, column=0, sticky="w", padx=20, pady=5)

self.expiration_entry = ctk.CTkEntry(frame, width=200)
self.expiration_entry.grid(row=N, column=1, sticky="w", pady=5)
```

**And remove from save handler**:
```python
# Remove this
if self.expiration_entry.get():
    item.expiration_date = datetime.strptime(
        self.expiration_entry.get(), 
        "%Y-%m-%d"
    ).date()
```

### 3. Keep Database Schema
**File**: `src/models/inventory_item.py`

**DO NOT REMOVE** from model:
```python
class InventoryItem(Base):
    # ... other fields ...
    expiration_date = Column(Date, nullable=True)  # KEEP THIS
```

**Why keep it**:
- Future feature: Expiration tracking for perishables
- Data already exists in database
- No harm keeping the column
- Easy to re-add to UI later when ready

## Implementation Tasks

### Task 1: Check if Already Removed from Pantry Tab
**File**: `src/ui/inventory_tab.py`

1. Check if BUG_pantry-qty-format-correction already removed it
2. Look at columns tuple definition
3. Look at tree population code
4. If still present, remove column and references

### Task 2: Remove from Edit Form
**File**: Inventory edit form

1. Remove expiration label widget
2. Remove expiration entry widget
3. Remove from grid layout
4. Adjust row numbers if needed (other fields may shift up)
5. Remove from form load logic
6. Remove from form save logic
7. Remove any validation for expiration date

### Task 3: Remove from Any Other Views
**Files**: Search codebase

Search for "expiration" references:
- Reports or exports that show expiration?
- Filters or searches by expiration?
- Any other UI that references the field?

### Task 4: Update Comments/Documentation
**Files**: Any docs that mention expiration

1. Update any user guides or comments
2. Note that field is deferred for future implementation
3. Mark as "schema exists, UI hidden for now"

## Testing Checklist

### My Pantry Tab
- [ ] No expiration column in listing
- [ ] Columns display correctly without expiration
- [ ] Column widths adjust appropriately
- [ ] No errors when loading pantry tab

### Edit Inventory Form
- [ ] No expiration date field on form
- [ ] Form layout looks clean (no gaps)
- [ ] Other fields display correctly
- [ ] Save works without expiration field
- [ ] Load works without expiration field

### Database
- [ ] expiration_date column still exists in inventory_items table
- [ ] Existing expiration data not deleted
- [ ] No schema errors

### No Regressions
- [ ] All other pantry functionality works
- [ ] All other inventory edit functionality works
- [ ] No console errors
- [ ] No broken imports

## Success Criteria

1. **UI Cleaned Up**: Expiration field removed from all user-facing views
2. **No Gaps**: Forms and lists look properly laid out
3. **Schema Preserved**: Database column still exists for future use
4. **No Errors**: All functionality continues to work
5. **Easy to Re-Add**: Field can be easily restored when needed

## Future Considerations

**When to re-add expiration tracking**:
- When implementing perishable inventory management
- When adding expiration alerts/notifications
- When user requests expiration date filtering
- When integrating with food safety compliance

**How to re-add**:
1. Add column back to UI layouts
2. Add date picker widgets to forms
3. Add expiration-based filtering
4. Add "expiring soon" alerts
5. Add expiration date to exports/reports

## Related Issues

**Already partially done**:
- BUG_pantry-qty-format-correction.md specified removing Expiration column
- This bug completes the removal by also removing from edit form

## Related Files

**Primary Files**:
- `src/ui/inventory_tab.py` - May need expiration column removal
- `src/ui/forms/inventory_edit_dialog.py` - Remove expiration field

**Model** (DO NOT MODIFY):
- `src/models/inventory_item.py` - Keep expiration_date field in schema

## Git Workflow

```bash
git checkout -b bugfix/remove-expiration-from-ui
git commit -m "remove: expiration date column from pantry listing"
git commit -m "remove: expiration date field from inventory edit form"
git push
```

---

**Low Priority Cleanup**: Simplifies UI by removing unused field. Quick win for cleaner interface.
