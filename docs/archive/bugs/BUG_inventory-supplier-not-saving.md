# Bug Fix: Supplier Not Persisting in Edit Inventory Form

**Branch**: `bugfix/inventory-supplier-not-saving`  
**Priority**: CRITICAL (data loss bug)  
**Estimated Effort**: 1-2 hours

## Context

When editing an inventory item:
1. User selects supplier (e.g., Costco)
2. User saves the form
3. User reopens the same item
4. **BUG**: Supplier field is blank again

**Root Cause**: Supplier selection is not being saved to the database, or is being saved to the wrong field/table.

## Data Model Clarification

**Supplier should be stored on Purchase record** (Option C):
- `Purchase.supplier_id` → References `Supplier.id`
- Each inventory item links to a purchase record
- Purchase record captures the transaction: what was bought, from where, at what price

**Why this model**:
- Same product can be purchased from different suppliers
- Purchases are historical transactions
- Product has `preferred_supplier_id` (preference, not transaction fact)
- Inventory items don't directly own supplier (they come from purchases)

**Data flow**:
```
InventoryItem → Purchase → Supplier
            ↓
         product_id, purchase_id
                        ↓
                  supplier_id, unit_price, purchase_date
```

## Current State vs Expected

### Current (Broken)
```
1. Edit inventory item form shows supplier dropdown
2. User selects "Costco"
3. User clicks Save
4. Form closes
5. Reopen same item → Supplier is blank ❌
```

### Expected (Fixed)
```
1. Edit inventory item form shows supplier dropdown
2. User selects "Costco"
3. User clicks Save
4. → Create or update Purchase record with supplier_id
5. → Link InventoryItem to Purchase record
6. Reopen same item → Supplier shows "Costco" ✅
```

## Implementation Requirements

### 1. Verify Data Model
**Files**: Database models

**Check**:
- Does `InventoryItem` have `purchase_id` field?
- Does `Purchase` have `supplier_id` field?
- Is the relationship configured correctly?

**Expected schema**:
```python
# InventoryItem model
class InventoryItem(Base):
    purchase_id = Column(Integer, ForeignKey('purchases.id'), nullable=True)
    purchase = relationship('Purchase', back_populates='inventory_items')

# Purchase model  
class Purchase(Base):
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=True)
    supplier = relationship('Supplier', back_populates='purchases')
    inventory_items = relationship('InventoryItem', back_populates='purchase')
```

### 2. Fix Edit Form Save Logic
**File**: Inventory edit form (likely `src/ui/forms/inventory_edit_dialog.py`)

**Current (probably wrong)**:
```python
def _on_save(self):
    # Probably trying to save supplier_id directly on inventory item
    inventory_item.supplier_id = selected_supplier_id  # WRONG - field doesn't exist
    session.commit()
```

**Correct approach**:
```python
def _on_save(self):
    """Save inventory item with supplier via purchase record."""
    try:
        selected_supplier_id = self._get_selected_supplier_id()
        
        with session_scope() as session:
            inventory_item = session.query(InventoryItem).get(self.item_id)
            
            # Get or create purchase record
            if inventory_item.purchase_id:
                # Update existing purchase
                purchase = session.query(Purchase).get(inventory_item.purchase_id)
            else:
                # Create new purchase record for this inventory item
                purchase = Purchase(
                    product_id=inventory_item.product_id,
                    purchase_date=inventory_item.purchase_date or datetime.now().date(),
                    quantity_purchased=inventory_item.quantity_purchased,
                    # Initial values - can be updated later in purchase management
                )
                session.add(purchase)
                session.flush()  # Get purchase ID
                inventory_item.purchase_id = purchase.id
            
            # Update supplier on purchase record
            purchase.supplier_id = selected_supplier_id
            
            # Update other inventory item fields
            # ... (location, notes, etc.)
            
            session.commit()
            
        messagebox.showinfo("Success", "Inventory item updated")
        self.destroy()
        if hasattr(self.parent, 'refresh'):
            self.parent.refresh()
            
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save: {e}")
```

### 3. Fix Edit Form Load Logic
**File**: Same edit form file

**Load supplier from purchase record**:
```python
def _load_inventory_item(self):
    """Load inventory item data into form."""
    with session_scope() as session:
        item = session.query(InventoryItem).options(
            joinedload(InventoryItem.product),
            joinedload(InventoryItem.purchase).joinedload(Purchase.supplier)
        ).get(self.item_id)
        
        # Populate fields
        self.product_label.configure(text=item.product.product_name)
        self.quantity_entry.delete(0, 'end')
        self.quantity_entry.insert(0, str(item.quantity_remaining))
        
        # Load supplier from purchase record
        if item.purchase and item.purchase.supplier:
            self.supplier_dropdown.set(item.purchase.supplier.name)
        else:
            self.supplier_dropdown.set("None")
```

### 4. Handle Edge Cases
**Scenarios to handle**:

**A. Inventory item created without purchase**
- Old data or manual inventory addition
- Create purchase record when supplier is first selected
- Use inventory's purchase_date or current date

**B. Multiple inventory items from same purchase**
- Splitting a bulk purchase into multiple lots
- Should they share one purchase record? (Probably yes)
- Or each get their own? (Cleaner, allows independent tracking)
- **Decision needed**: One purchase = one inventory item, or one purchase = many items?

**C. Changing supplier after creation**
- Update purchase record's supplier_id
- Don't create new purchase record

**D. Removing supplier**
- Set purchase.supplier_id = None
- Keep purchase record (has other data like price, date)

## Implementation Tasks

### Task 1: Verify Database Schema
**Files**: Model files, migration scripts

1. Check `InventoryItem` model for `purchase_id` field
2. Check `Purchase` model for `supplier_id` field
3. Check relationships are configured
4. If fields missing, create migration to add them

### Task 2: Update Edit Form Save Handler
**File**: Inventory edit form

1. Locate `_on_save()` method
2. Implement purchase record creation/update logic
3. Link inventory item to purchase via `purchase_id`
4. Save supplier to `purchase.supplier_id`
5. Handle edge cases (no existing purchase)

### Task 3: Update Edit Form Load Handler
**File**: Inventory edit form

1. Locate form initialization code
2. Add eager loading for purchase → supplier relationship
3. Populate supplier dropdown from `item.purchase.supplier`
4. Handle cases where purchase or supplier is None

### Task 4: Test Purchase Record Creation
**File**: Test file

```python
def test_inventory_supplier_creates_purchase():
    """Test that selecting supplier creates purchase record."""
    # Create inventory item without purchase
    item = create_inventory_item(purchase_id=None)
    
    # Update with supplier
    update_inventory_with_supplier(item.id, supplier_id=1)
    
    # Verify purchase created
    assert item.purchase is not None
    assert item.purchase.supplier_id == 1

def test_inventory_supplier_persists():
    """Test that supplier persists across edit sessions."""
    # Create inventory with supplier
    item = create_inventory_with_supplier(supplier_name="Costco")
    
    # "Reopen" - load fresh from DB
    reloaded = session.query(InventoryItem).get(item.id)
    
    # Verify supplier still there
    assert reloaded.purchase.supplier.name == "Costco"
```

### Task 5: Update Pantry Tab Display (Optional)
**File**: Inventory tab

Consider showing supplier in pantry listing:
```
Ingredient | Product | Brand | Supplier | Qty Remaining | Purchased
```

Or keep it only in detail view. User's preference.

## Testing Checklist

### Data Persistence
- [ ] Select supplier, save, reopen → Supplier still selected ✅
- [ ] Change supplier, save, reopen → New supplier shown ✅
- [ ] Remove supplier (set to None), save → Supplier is None ✅
- [ ] Edit inventory item that never had purchase → Creates purchase record
- [ ] Edit inventory item with existing purchase → Updates existing purchase

### Edge Cases
- [ ] Inventory item created before purchase records existed → Handles gracefully
- [ ] Supplier dropdown shows all suppliers
- [ ] "None" option available for no supplier
- [ ] Purchase record has correct product_id
- [ ] Purchase record has correct purchase_date

### Database Integrity
- [ ] Foreign key constraints respected
- [ ] No orphaned purchase records
- [ ] Relationships load correctly (eager loading works)
- [ ] Session management correct (no uncommitted changes)

### UI Behavior
- [ ] Supplier dropdown populates on form load
- [ ] Selected supplier saves without errors
- [ ] Error messages clear if save fails
- [ ] Form closes after successful save
- [ ] Parent list refreshes after save

## Success Criteria

1. **Persistence Works**: Supplier selection saves and reloads correctly
2. **Data Model Correct**: Supplier stored on Purchase record, linked via purchase_id
3. **No Data Loss**: Existing inventory items handle supplier gracefully
4. **Clear Relationships**: InventoryItem → Purchase → Supplier chain works
5. **Edge Cases Handled**: Works for items with/without existing purchases
6. **User Validation**: Primary user confirms supplier persists

## Related Issues

**Issue #2**: Unit price shows 0.0000 after selecting supplier
- Fix: When supplier selected, look up last purchase price
- See: `_BUG_inventory-unit-price-display.md`

## Related Files

**Primary Files**:
- `src/ui/forms/inventory_edit_dialog.py` - Edit form save/load logic
- `src/models/inventory_item.py` - Verify purchase_id field exists
- `src/models/purchase.py` - Verify supplier_id field exists

**Service Layer** (may need updates):
- `src/services/inventory_item_service.py` - Update methods
- `src/services/purchase_service.py` - Get/create purchase records

## Git Workflow

```bash
git checkout -b bugfix/inventory-supplier-not-saving
git commit -m "fix: save inventory supplier to purchase record"
git commit -m "fix: load inventory supplier from purchase record"
git commit -m "feat: create purchase record when setting supplier"
git commit -m "test: add supplier persistence tests"
git push
```

---

**CRITICAL**: This is a data loss bug. Users are selecting suppliers but the data disappears. High priority fix.
