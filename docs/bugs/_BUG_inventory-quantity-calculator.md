# Bug Fix: Smart Calculator for Inventory Quantity Updates

**Branch**: `bugfix/inventory-quantity-calculator`  
**Priority**: High (core workflow improvement)  
**Estimated Effort**: 2-3 hours

## Context

Recording inventory usage needs better UI/UX to support two common use cases:
1. **Physical Inventory**: "This jar is about 40% full"
2. **Recipe Consumption**: "I used 2 cups for a recipe"

Currently, Record Usage is a separate function that's awkward for manual input. Moving it into the Edit form with a smart calculator interface makes it more accessible and flexible for both manual and AI-assisted workflows.

## Proposed Solution: Unified Calculator

**Smart calculator that works like Wolfram Alpha or financial calculators**:
- Fill in any field you know
- System calculates the rest using precedence rules
- Live calculation with real-time feedback
- Compact, collapsible UI

### Design Specifications

**Location**: Collapsible section in Edit Inventory Item dialog

**Fields** (3 input methods):
1. **Remaining %** - Physical inventory use case
2. **New Quantity** - Direct entry
3. **Amount Used** - Recipe consumption (with unit dropdown)

**Precedence Rules** (highest to lowest):
1. If **Remaining %** has value → use this to calculate new quantity
2. Else if **New Quantity** has value → use this directly
3. Else if **Amount Used** has value → calculate: current - used = new

**UI Behavior**:
- **Live calculation**: Type in any field → others update immediately
- **Show calculated values**: Auto-calculated fields display grayed out (not editable)
- **Unit dropdown**: Package units only (jars, oz, lb, etc.) - no exotic cooking units for now

## UI Mockup

```
┌─ Edit Inventory Item ──────────────────────────────────┐
│ Product: Ghirardelli 60% Cacao Bittersweet Chips      │
│ Brand: Ghirardelli                                     │
│ Purchased: 2024-12-01                                  │
│ Location: Pantry                                       │
│                                                         │
│ Current Quantity: 2.5 jars (70 oz)                     │
│                                                         │
│ ▼ Update Quantity                                      │
│   ┌─────────────────────────────────────────────────┐ │
│   │                                                  │ │
│   │ Remaining %:  [40___]%                          │ │
│   │                  ↓ calculates                    │ │
│   │ New Quantity: [1.0] jars (disabled/grayed)      │ │
│   │                  ↓ calculates                    │ │
│   │ Amount Used:  [1.5] jars (disabled/grayed)      │ │
│   │                                                  │ │
│   │ → New quantity will be: 1.0 jar (28 oz)         │ │
│   │                                                  │ │
│   └─────────────────────────────────────────────────┘ │
│                                                         │
│ [Save]  [Delete]  [Cancel]                             │
└─────────────────────────────────────────────────────────┘
```

**Collapsed state** (default):
```
│ Current Quantity: 2.5 jars (70 oz)                     │
│ ▶ Update Quantity                                      │
```

## Calculation Examples

### Example 1: Physical Inventory (Percentage)
```
User types: 40 (in Remaining % field)

Live calculation:
→ New Quantity: 1.0 jars (40% of 2.5 = 1.0)
→ Amount Used: 1.5 jars (60% consumed = 1.5)
→ Preview: "New quantity will be: 1.0 jar (28 oz)"
```

### Example 2: Direct Entry (New Quantity)
```
User types: 1.5 (in New Quantity field)

Live calculation:
→ Remaining %: 60% (1.5 / 2.5 = 60%)
→ Amount Used: 1.0 jars (2.5 - 1.5 = 1.0)
→ Preview: "New quantity will be: 1.5 jars (42 oz)"
```

### Example 3: Recipe Consumption (Amount Used)
```
User types: 16 (in Amount Used field)
User selects: oz (from unit dropdown)

Live calculation:
→ Convert: 16 oz ÷ 28 oz/jar = 0.57 jars
→ New Quantity: 1.93 jars (2.5 - 0.57 = 1.93)
→ Remaining %: 77% (1.93 / 2.5 = 77%)
→ Preview: "New quantity will be: 1.93 jars (54 oz)"
```

## Implementation Tasks

### Task 1: Create Service Layer Method
**File**: `src/services/inventory_item_service.py`

Create flexible update method supporting all three input modes:

```python
from typing import Optional
from decimal import Decimal

def update_inventory_quantity(
    session,
    inventory_item_id: int,
    *,
    remaining_percentage: Optional[float] = None,
    new_quantity: Optional[Decimal] = None,
    amount_used: Optional[Decimal] = None,
    amount_used_unit: Optional[str] = None,
) -> InventoryItem:
    """
    Update inventory quantity using any of three methods.
    
    Precedence (if multiple values provided):
    1. remaining_percentage
    2. new_quantity  
    3. amount_used + amount_used_unit
    
    Args:
        session: Database session
        inventory_item_id: ID of inventory item to update
        remaining_percentage: Percentage remaining (0-100)
        new_quantity: New quantity in package units
        amount_used: Amount consumed
        amount_used_unit: Unit for amount_used
    
    Returns:
        Updated InventoryItem
        
    Raises:
        ValidationError: If no update method provided or invalid values
        InventoryItemNotFound: If item doesn't exist
    """
    item = session.query(InventoryItem).get(inventory_item_id)
    if not item:
        raise InventoryItemNotFound(f"Inventory item {inventory_item_id} not found")
    
    product = item.product
    current_qty = item.quantity_remaining
    
    # Apply precedence rules
    if remaining_percentage is not None:
        # Method 1: Percentage
        if not 0 <= remaining_percentage <= 100:
            raise ValidationError("Percentage must be between 0 and 100")
        new_qty = current_qty * (Decimal(remaining_percentage) / 100)
        
    elif new_quantity is not None:
        # Method 2: Direct quantity
        if new_quantity < 0:
            raise ValidationError("New quantity cannot be negative")
        new_qty = new_quantity
        
    elif amount_used is not None and amount_used_unit is not None:
        # Method 3: Amount consumed
        if amount_used < 0:
            raise ValidationError("Amount used cannot be negative")
        
        # Convert amount_used to package units
        used_in_pkg_units = _convert_to_package_units(
            amount_used, 
            amount_used_unit,
            product.package_unit_quantity,
            product.package_unit
        )
        
        new_qty = current_qty - used_in_pkg_units
        if new_qty < 0:
            raise ValidationError(
                f"Amount used ({amount_used} {amount_used_unit}) exceeds "
                f"current quantity ({current_qty} {product.package_type}s)"
            )
    else:
        raise ValidationError("Must provide remaining_percentage, new_quantity, or amount_used")
    
    # Update the item
    item.quantity_remaining = new_qty
    item.updated_at = datetime.now()
    
    session.commit()
    return item


def _convert_to_package_units(
    amount: Decimal,
    from_unit: str,
    package_qty: Decimal,
    package_unit: str
) -> Decimal:
    """
    Convert amount in arbitrary unit to package units.
    
    Example: 16 oz → 0.57 jars (if package is 28 oz jar)
    """
    # If units match package unit, divide by package quantity
    if from_unit == package_unit:
        return amount / package_qty
    
    # If from_unit is package type (jar, can, bag), return directly
    # This handles "2 jars" style input
    if from_unit in ['jar', 'jars', 'can', 'cans', 'bag', 'bags', 
                     'bottle', 'bottles', 'package', 'packages']:
        return amount
    
    # Future: Add unit conversion table if needed
    # For now, if units don't match, assume user knows what they're doing
    raise ValidationError(
        f"Cannot convert {from_unit} to {package_unit}. "
        f"Please use {package_unit} or package units (jars, cans, etc.)"
    )
```

### Task 2: Create Calculator UI Component
**File**: `src/ui/forms/inventory_edit_dialog.py` (or wherever edit form lives)

Add collapsible calculator section to existing edit form:

```python
def _create_calculator_section(self):
    """Create the quantity update calculator section."""
    # Collapsible frame
    self.calc_frame = ctk.CTkFrame(self)
    self.calc_frame.grid(row=N, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
    
    # Header with collapse/expand button
    header_frame = ctk.CTkFrame(self.calc_frame, fg_color="transparent")
    header_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
    
    self.calc_collapsed = True
    self.calc_toggle_btn = ctk.CTkButton(
        header_frame,
        text="▶ Update Quantity",
        command=self._toggle_calculator,
        width=150,
        fg_color="transparent",
        hover_color=("gray80", "gray30"),
    )
    self.calc_toggle_btn.pack(side="left", pady=5)
    
    # Calculator inputs (hidden by default)
    self.calc_inputs_frame = ctk.CTkFrame(self.calc_frame)
    # Don't grid yet - will grid on expand
    
    # Current quantity display
    self.current_qty_label = ctk.CTkLabel(
        self.calc_inputs_frame,
        text=f"Current: {self.current_quantity_display}",
        font=ctk.CTkFont(weight="bold")
    )
    self.current_qty_label.grid(row=0, column=0, columnspan=2, pady=(10, 15))
    
    # Field 1: Remaining %
    remaining_label = ctk.CTkLabel(self.calc_inputs_frame, text="Remaining %:")
    remaining_label.grid(row=1, column=0, sticky="w", padx=(20, 10), pady=5)
    
    self.remaining_pct_var = ctk.StringVar()
    self.remaining_pct_var.trace_add("write", self._on_remaining_pct_change)
    self.remaining_pct_entry = ctk.CTkEntry(
        self.calc_inputs_frame,
        textvariable=self.remaining_pct_var,
        width=100
    )
    self.remaining_pct_entry.grid(row=1, column=1, sticky="w", pady=5)
    
    pct_suffix = ctk.CTkLabel(self.calc_inputs_frame, text="%")
    pct_suffix.grid(row=1, column=2, sticky="w", padx=(5, 20), pady=5)
    
    # Field 2: New Quantity
    new_qty_label = ctk.CTkLabel(self.calc_inputs_frame, text="New Quantity:")
    new_qty_label.grid(row=2, column=0, sticky="w", padx=(20, 10), pady=5)
    
    self.new_qty_var = ctk.StringVar()
    self.new_qty_var.trace_add("write", self._on_new_qty_change)
    self.new_qty_entry = ctk.CTkEntry(
        self.calc_inputs_frame,
        textvariable=self.new_qty_var,
        width=100,
        state="normal"  # Will be disabled when calculated
    )
    self.new_qty_entry.grid(row=2, column=1, sticky="w", pady=5)
    
    qty_suffix = ctk.CTkLabel(
        self.calc_inputs_frame, 
        text=self.package_type + "s"
    )
    qty_suffix.grid(row=2, column=2, sticky="w", padx=(5, 20), pady=5)
    
    # Field 3: Amount Used
    used_label = ctk.CTkLabel(self.calc_inputs_frame, text="Amount Used:")
    used_label.grid(row=3, column=0, sticky="w", padx=(20, 10), pady=5)
    
    used_frame = ctk.CTkFrame(self.calc_inputs_frame, fg_color="transparent")
    used_frame.grid(row=3, column=1, columnspan=2, sticky="w", pady=5)
    
    self.amount_used_var = ctk.StringVar()
    self.amount_used_var.trace_add("write", self._on_amount_used_change)
    self.amount_used_entry = ctk.CTkEntry(
        used_frame,
        textvariable=self.amount_used_var,
        width=100
    )
    self.amount_used_entry.pack(side="left", padx=(0, 5))
    
    # Unit dropdown - package units only
    unit_options = self._get_package_unit_options()
    self.amount_used_unit_var = ctk.StringVar(value=self.package_unit)
    self.amount_used_unit_dropdown = ctk.CTkOptionMenu(
        used_frame,
        variable=self.amount_used_unit_var,
        values=unit_options,
        command=self._on_amount_used_unit_change,
        width=100
    )
    self.amount_used_unit_dropdown.pack(side="left")
    
    # Preview/result display
    self.result_label = ctk.CTkLabel(
        self.calc_inputs_frame,
        text="",
        font=ctk.CTkFont(size=12, weight="bold"),
        text_color=("green", "lightgreen")
    )
    self.result_label.grid(row=4, column=0, columnspan=3, pady=(15, 10))


def _get_package_unit_options(self):
    """Get valid unit options for amount used dropdown."""
    options = []
    
    # Add package type (singular and plural)
    pkg_type = self.package_type
    options.append(pkg_type)
    if not pkg_type.endswith('s'):
        options.append(pkg_type + 's')
    
    # Add package unit
    options.append(self.package_unit)
    
    # Remove duplicates, preserve order
    seen = set()
    unique_options = []
    for opt in options:
        if opt not in seen:
            seen.add(opt)
            unique_options.append(opt)
    
    return unique_options


def _toggle_calculator(self):
    """Toggle calculator section collapsed/expanded."""
    if self.calc_collapsed:
        # Expand
        self.calc_inputs_frame.grid(row=1, column=0, columnspan=2, pady=10)
        self.calc_toggle_btn.configure(text="▼ Update Quantity")
        self.calc_collapsed = False
    else:
        # Collapse
        self.calc_inputs_frame.grid_forget()
        self.calc_toggle_btn.configure(text="▶ Update Quantity")
        self.calc_collapsed = True


def _on_remaining_pct_change(self, *args):
    """Handle remaining percentage input change."""
    if self._calculating:
        return  # Prevent recursive calls
    
    try:
        pct_str = self.remaining_pct_var.get().strip()
        if not pct_str:
            self._clear_calculated_fields()
            return
        
        pct = float(pct_str)
        if not 0 <= pct <= 100:
            return
        
        # Calculate new quantity
        self._calculating = True
        new_qty = self.current_quantity * (Decimal(pct) / 100)
        amount_used = self.current_quantity - new_qty
        
        # Update other fields (disabled/grayed)
        self.new_qty_entry.configure(state="disabled", text_color="gray")
        self.new_qty_var.set(f"{new_qty:.2f}")
        
        self.amount_used_entry.configure(state="disabled", text_color="gray")
        self.amount_used_var.set(f"{amount_used:.2f}")
        
        # Update preview
        total_oz = new_qty * self.package_unit_quantity
        self.result_label.configure(
            text=f"→ New quantity will be: {new_qty:.2f} {self.package_type}s ({total_oz:.1f} {self.package_unit})"
        )
        
    except ValueError:
        pass
    finally:
        self._calculating = False


def _on_new_qty_change(self, *args):
    """Handle new quantity input change."""
    if self._calculating:
        return
    
    try:
        qty_str = self.new_qty_var.get().strip()
        if not qty_str:
            self._clear_calculated_fields()
            return
        
        new_qty = Decimal(qty_str)
        if new_qty < 0:
            return
        
        # Calculate percentage and amount used
        self._calculating = True
        pct = (new_qty / self.current_quantity) * 100
        amount_used = self.current_quantity - new_qty
        
        # Update other fields (disabled/grayed)
        self.remaining_pct_entry.configure(state="disabled", text_color="gray")
        self.remaining_pct_var.set(f"{pct:.1f}")
        
        self.amount_used_entry.configure(state="disabled", text_color="gray")
        self.amount_used_var.set(f"{amount_used:.2f}")
        
        # Update preview
        total_oz = new_qty * self.package_unit_quantity
        self.result_label.configure(
            text=f"→ New quantity will be: {new_qty:.2f} {self.package_type}s ({total_oz:.1f} {self.package_unit})"
        )
        
    except (ValueError, InvalidOperation):
        pass
    finally:
        self._calculating = False


def _on_amount_used_change(self, *args):
    """Handle amount used input change."""
    if self._calculating:
        return
    
    try:
        used_str = self.amount_used_var.get().strip()
        if not used_str:
            self._clear_calculated_fields()
            return
        
        amount_used = Decimal(used_str)
        unit = self.amount_used_unit_var.get()
        
        # Convert to package units
        if unit == self.package_unit:
            used_in_pkg = amount_used / self.package_unit_quantity
        elif unit in [self.package_type, self.package_type + 's']:
            used_in_pkg = amount_used
        else:
            return  # Can't convert
        
        new_qty = self.current_quantity - used_in_pkg
        if new_qty < 0:
            return
        
        # Calculate percentage
        self._calculating = True
        pct = (new_qty / self.current_quantity) * 100
        
        # Update other fields (disabled/grayed)
        self.remaining_pct_entry.configure(state="disabled", text_color="gray")
        self.remaining_pct_var.set(f"{pct:.1f}")
        
        self.new_qty_entry.configure(state="disabled", text_color="gray")
        self.new_qty_var.set(f"{new_qty:.2f}")
        
        # Update preview
        total_oz = new_qty * self.package_unit_quantity
        self.result_label.configure(
            text=f"→ New quantity will be: {new_qty:.2f} {self.package_type}s ({total_oz:.1f} {self.package_unit})"
        )
        
    except (ValueError, InvalidOperation):
        pass
    finally:
        self._calculating = False


def _clear_calculated_fields(self):
    """Clear and re-enable all fields when primary field is cleared."""
    self._calculating = True
    
    # Re-enable all fields
    self.remaining_pct_entry.configure(state="normal", text_color=("black", "white"))
    self.new_qty_entry.configure(state="normal", text_color=("black", "white"))
    self.amount_used_entry.configure(state="normal", text_color=("black", "white"))
    
    # Clear result
    self.result_label.configure(text="")
    
    self._calculating = False
```

### Task 3: Update Save Logic
**File**: Same edit form file

Modify save handler to use calculated new quantity:

```python
def _on_save(self):
    """Save inventory item with updated quantity if changed."""
    try:
        # Get new quantity from calculator if used
        new_qty = None
        if not self.calc_collapsed and self.result_label.cget("text"):
            # Calculator was used - get new quantity
            new_qty_str = self.new_qty_var.get().strip()
            if new_qty_str:
                new_qty = Decimal(new_qty_str)
        
        # Update inventory item
        with session_scope() as session:
            if new_qty is not None:
                # Use quantity update service method
                inventory_item_service.update_inventory_quantity(
                    session,
                    self.item_id,
                    new_quantity=new_qty
                )
            else:
                # Regular edit - update other fields
                # ... existing save logic for other fields
        
        messagebox.showinfo("Success", "Inventory item updated")
        self.destroy()
        if hasattr(self.parent, 'refresh'):
            self.parent.refresh()
        
    except ValidationError as e:
        messagebox.showerror("Validation Error", str(e))
    except Exception as e:
        messagebox.showerror("Error", f"Failed to update: {e}")
```

### Task 4: Remove Old Record Usage Function
**Files**: Search codebase for existing "Record Usage" implementation

1. Find existing Record Usage button/dialog
2. Remove old implementation
3. Update any references to use new calculator

### Task 5: Add Tests
**File**: `src/tests/services/test_inventory_item_service.py`

Add comprehensive tests for all three update modes:

```python
def test_update_quantity_by_percentage():
    """Test updating quantity using remaining percentage."""
    # Create inventory item with 2.5 jars
    item = create_test_inventory_item(quantity=Decimal("2.5"))
    
    # Update to 40% remaining
    with session_scope() as session:
        updated = update_inventory_quantity(
            session,
            item.id,
            remaining_percentage=40
        )
    
    assert updated.quantity_remaining == Decimal("1.0")


def test_update_quantity_direct():
    """Test updating quantity directly."""
    item = create_test_inventory_item(quantity=Decimal("2.5"))
    
    with session_scope() as session:
        updated = update_inventory_quantity(
            session,
            item.id,
            new_quantity=Decimal("1.5")
        )
    
    assert updated.quantity_remaining == Decimal("1.5")


def test_update_quantity_by_amount_used():
    """Test updating quantity by amount consumed."""
    # Product: 28 oz jar
    item = create_test_inventory_item(
        quantity=Decimal("2.5"),
        package_unit_qty=Decimal("28"),
        package_unit="oz"
    )
    
    # Used 16 oz
    with session_scope() as session:
        updated = update_inventory_quantity(
            session,
            item.id,
            amount_used=Decimal("16"),
            amount_used_unit="oz"
        )
    
    # 16 oz = 0.57 jars, so 2.5 - 0.57 = 1.93
    assert abs(updated.quantity_remaining - Decimal("1.93")) < Decimal("0.01")


def test_precedence_percentage_wins():
    """Test that percentage takes precedence over other methods."""
    item = create_test_inventory_item(quantity=Decimal("2.5"))
    
    with session_scope() as session:
        updated = update_inventory_quantity(
            session,
            item.id,
            remaining_percentage=40,  # Should use this
            new_quantity=Decimal("1.5"),  # Should ignore
            amount_used=Decimal("1.0"),  # Should ignore
        )
    
    # 40% of 2.5 = 1.0
    assert updated.quantity_remaining == Decimal("1.0")
```

## Testing Checklist

### Service Layer
- [ ] Update by percentage works correctly
- [ ] Update by new quantity works correctly
- [ ] Update by amount used works correctly
- [ ] Precedence rules applied correctly
- [ ] Validation prevents negative quantities
- [ ] Validation prevents invalid percentages (< 0 or > 100)
- [ ] Unit conversion works for package units
- [ ] Error messages are clear and helpful

### UI Calculator
- [ ] Section is collapsed by default
- [ ] Toggle button expands/collapses section
- [ ] Current quantity displays correctly
- [ ] Remaining % field calculates live
- [ ] New Quantity field calculates live
- [ ] Amount Used field calculates live
- [ ] Calculated fields show grayed out
- [ ] Cleared field re-enables all fields
- [ ] Unit dropdown shows correct options
- [ ] Preview shows correct "New quantity will be" message
- [ ] Save applies the calculated quantity

### Integration
- [ ] Calculator works with real inventory items
- [ ] Multiple edits in sequence work correctly
- [ ] Pantry list refreshes after save
- [ ] No regressions in other edit form fields
- [ ] Works with different product types (jars, cans, bags)
- [ ] Works with different units (oz, lb, fl oz, g)

### Edge Cases
- [ ] Handles Decimal precision correctly
- [ ] Handles very small quantities (0.01)
- [ ] Handles very large quantities (100+)
- [ ] Handles items with no package info gracefully
- [ ] Clear error if amount used > current quantity

## Success Criteria

1. **Flexible Input**: All three input methods work correctly
2. **Live Calculation**: Real-time feedback as user types
3. **Smart UI**: Calculated fields show grayed, non-editable
4. **Precedence Works**: Correct precedence when multiple fields filled
5. **Compact Design**: Collapsible, doesn't clutter edit form
6. **AI-Ready**: Service layer supports AI voice/vision inputs
7. **User Testing**: Primary user confirms it's easier than old method

## Future Enhancements (Out of Scope)

- Cooking unit conversions (cups, tbsp, tsp)
- Smart unit conversion table
- Usage history tracking
- Recipe consumption tracking with event linkage

## Related Files

**Primary Files**:
- `src/services/inventory_item_service.py` - New update method
- `src/ui/forms/inventory_edit_dialog.py` - Calculator UI
- `src/tests/services/test_inventory_item_service.py` - Tests

**Files to Update/Remove**:
- Old Record Usage dialog/function (find and remove)

## Git Workflow

```bash
git checkout -b bugfix/inventory-quantity-calculator
git commit -m "feat: add flexible update_inventory_quantity service method"
git commit -m "feat: add smart calculator UI to inventory edit form"
git commit -m "remove: old Record Usage function"
git commit -m "test: add comprehensive tests for quantity updates"
git push
```

---

**Core Workflow Improvement**: Makes manual inventory updates significantly easier while setting foundation for AI-assisted workflows.
