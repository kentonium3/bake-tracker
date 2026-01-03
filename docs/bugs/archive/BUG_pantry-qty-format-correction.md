# Bug Fix: Correct Pantry Qty Remaining Format and Remove Incorrect Columns

**Branch**: `bugfix/pantry-qty-format-correction`  
**Priority**: High (fixes incorrectly implemented spec)  
**Estimated Effort**: 30-45 minutes

## Context

The previous spec `BUG_ui-cleanup-user-testing.md` was implemented with errors. This document corrects those errors and specifies the proper implementation.

**This is a CORRECTION spec** - it removes incorrectly added columns and fixes the Qty Remaining format.

## What Was Implemented Incorrectly

### Pantry Tab Errors
1. ❌ **Location column added** - Should NOT exist, remove it
2. ❌ **Separate Unit column added** - Should NOT exist, remove it  
3. ❌ **Qty Remaining format incorrect** - Does not show proper format

### Ingredients Tab Errors
1. ❌ **Type column added** - Should NOT exist, remove it

## Correct Implementation Required

### My Pantry Tab - CORRECT Column Structure

**Exactly 5 columns** (in this order):
1. **Ingredient** - Ingredient name
2. **Product** - Product name
3. **Brand** - Brand name
4. **Qty Remaining** - Formatted as `{qty} {package_type}(s) ({total} {unit})`
5. **Purchased** - Purchase date

**Columns that MUST NOT exist**:
- ❌ Location
- ❌ Unit (as separate column)
- ❌ Expiration

### Qty Remaining Format Specification

**Format**: `{qty} {package_type}(s) ({total} {unit})`

**Purpose**: Show "how much is left" at a glance - both package count and total usable quantity.

**Examples**:
- `2.5 jars (70 oz)` - Shows 2.5 packages = 70 oz total
- `1 can (28 oz)` - Singular package type
- `3 bags (75 lb)` - Multiple whole packages
- `0.5 bottle (16 fl oz)` - Partial package
- `12.3 bags (307 lb)` - Large count, total rounded

**Calculation**: 
```
total = quantity_remaining × package_unit_quantity
display = "{qty:g} {package_type} ({total} {package_unit})"
```

**Rules**:
1. **Singular/Plural**: Use singular when qty=1 ("1 can"), plural otherwise ("2.5 jars")
2. **Rounding**: For totals >100, round to whole numbers (307.5 → 307)
3. **Format specifier**: Use `:g` to remove trailing zeros (2.0 → 2, 2.5 → 2.5)

### My Ingredients Tab - CORRECT Column Structure

**DO NOT include a Type column**

If a Type column was added, remove it completely.

## Implementation Tasks

### Task 1: Remove Incorrect Columns from Pantry Tab
**File**: `src/ui/inventory_tab.py`

1. **Remove Location column** (if present)
   - Remove from columns tuple
   - Remove heading configuration
   - Remove from tree population

2. **Remove separate Unit column** (if present)
   - Remove from columns tuple
   - Remove heading configuration
   - Remove from tree population

3. **Verify final columns are exactly**:
   ```python
   columns = ('ingredient', 'product', 'brand', 'qty_remaining', 'purchased')
   ```

### Task 2: Implement Correct Qty Remaining Format
**File**: `src/ui/inventory_tab.py`

Create formatting function:

```python
def format_qty_remaining(qty_remaining, product):
    """
    Format quantity remaining for display.
    
    Format: {qty} {package_type}(s) ({total} {package_unit})
    
    Examples:
        2.5 jars (70 oz)
        1 can (28 oz)
        3 bags (75 lb)
        0.5 bottle (16 fl oz)
    
    Args:
        qty_remaining: Decimal quantity remaining (e.g., 2.5)
        product: Product object with package_unit_quantity, package_unit, package_type
    
    Returns:
        Formatted string for display
    """
    # Get product package details with fallbacks
    pkg_qty = product.package_unit_quantity or 1
    pkg_unit = product.package_unit or "unit"
    pkg_type = product.package_type or "pkg"
    
    # Calculate total amount
    total_amount = qty_remaining * pkg_qty
    
    # Handle singular/plural for package type
    if qty_remaining == 1:
        pkg_type_display = pkg_type
    else:
        # Simple pluralization (jar→jars, can→cans, bag→bags)
        pkg_type_display = f"{pkg_type}s"
    
    # Format with sensible rounding
    # Use :g to remove trailing zeros (2.0 → 2, 2.5 → 2.5)
    # For large amounts (>100), round to whole numbers
    if total_amount > 100:
        total_display = f"{total_amount:.0f}"
    else:
        total_display = f"{total_amount:g}"
    
    qty_display = f"{qty_remaining:g}"
    
    return f"{qty_display} {pkg_type_display} ({total_display} {pkg_unit})"


# Example usage in tree population
for item in inventory_items:
    product = item.product
    ingredient_name = product.ingredient.name if product.ingredient else "Unknown"
    
    # Use the format function
    qty_display = format_qty_remaining(item.quantity_remaining, product)
    
    purchased_display = item.purchase_date.strftime('%Y-%m-%d') if item.purchase_date else ''
    
    tree.insert('', 'end', values=(
        ingredient_name,
        product.product_name,
        product.brand or '',
        qty_display,  # Formatted quantity
        purchased_display
    ))
```

### Task 3: Remove Type Column from Ingredients Tab
**File**: `src/ui/ingredients_tab.py`

1. **Check if Type column exists**
2. **If it exists, remove it**:
   - Remove from columns tuple
   - Remove heading configuration
   - Remove from tree population
3. **Verify ingredient columns are correct** (per original design)

### Task 4: Verify Column Headers
**File**: `src/ui/inventory_tab.py`

Ensure column headings are exactly:
```python
tree.heading('ingredient', text='Ingredient')
tree.heading('product', text='Product')
tree.heading('brand', text='Brand')
tree.heading('qty_remaining', text='Qty Remaining')  # NOT "Quantity"
tree.heading('purchased', text='Purchased')
```

## Testing Checklist

### My Pantry Tab - Structure
- [ ] Exactly 5 columns visible
- [ ] Columns in order: Ingredient, Product, Brand, Qty Remaining, Purchased
- [ ] **NO Location column** (verify completely removed)
- [ ] **NO separate Unit column** (verify completely removed)
- [ ] **NO Expiration column** (verify removed)
- [ ] Column header says "Qty Remaining" (not "Quantity")

### My Pantry Tab - Qty Remaining Format
- [ ] Format matches: `2.5 jars (70 oz)` style
- [ ] Singular when qty=1: "1 can (28 oz)" NOT "1 cans"
- [ ] Plural when qty≠1: "2.5 jars (70 oz)" NOT "2.5 jar"
- [ ] Total calculated correctly: qty × package_unit_quantity
- [ ] Large totals rounded: "12.3 bags (307 lb)" NOT "307.5 lb"
- [ ] No trailing zeros: "2 jars (56 oz)" NOT "2.0 jars (56.0 oz)"
- [ ] Parentheses present: "(70 oz)" format
- [ ] Space before parentheses: "jars (70 oz)" NOT "jars(70 oz)"

### My Ingredients Tab
- [ ] **NO Type column** (verify removed if it was added)
- [ ] Only expected columns present

### Data Integrity
- [ ] All inventory items display correctly
- [ ] Calculations are accurate (spot check several items)
- [ ] No missing data or errors
- [ ] Sorting works on all columns
- [ ] Double-click to edit still works

## Success Criteria

1. **Exact Column Count**: Pantry has exactly 5 columns, no more, no less
2. **Correct Format**: Qty Remaining shows package count + total amount in parentheses
3. **No Extraneous Columns**: Location, Unit, Expiration, Type all removed
4. **Readable Display**: Format is scannable and answers "how much is left?"
5. **Accurate Math**: Total amounts calculated correctly
6. **Proper Grammar**: Singular/plural handled correctly
7. **User Validation**: Primary user confirms this is what they need

## Format Examples Reference

All these should render correctly:

| qty_remaining | pkg_type | pkg_qty | pkg_unit | Expected Output |
|--------------|----------|---------|----------|-----------------|
| 2.5 | jar | 28 | oz | `2.5 jars (70 oz)` |
| 1 | can | 28 | oz | `1 can (28 oz)` |
| 1.0 | can | 28 | oz | `1 can (28 oz)` |
| 3 | bag | 25 | lb | `3 bags (75 lb)` |
| 0.5 | bottle | 32 | fl oz | `0.5 bottles (16 fl oz)` |
| 12.3 | bag | 25 | lb | `12.3 bags (307 lb)` |
| 0.75 | jar | 16 | oz | `0.75 jars (12 oz)` |

## Related Files

**Primary Files**:
- `src/ui/inventory_tab.py` - Main corrections needed here
- `src/ui/ingredients_tab.py` - Remove Type column if present

**Service Layer** (should not need changes):
- `src/services/inventory_item_service.py`
- `src/services/product_catalog_service.py`

## Git Workflow

```bash
# Create bug fix branch
git checkout -b bugfix/pantry-qty-format-correction

# Commit changes
git commit -m "fix: remove incorrectly added Location and Unit columns from pantry"
git commit -m "fix: implement correct qty remaining format with package type and total"
git commit -m "fix: remove Type column from ingredients tab if present"

# Test thoroughly
# Merge to main
```

## Critical Reminders for Implementation

1. **This is a CORRECTION** - Previous implementation was wrong
2. **Remove first, then fix** - Remove incorrect columns, then implement correct format
3. **5 columns only** in Pantry - If you count more or less, something is wrong
4. **Format is non-negotiable** - Must match `{qty} {type}(s) ({total} {unit})` exactly
5. **Test the math** - Spot check calculations to ensure accuracy

---

**CORRECTION SPEC**: This supersedes the previous implementation of `BUG_ui-cleanup-user-testing.md`. Remove what was incorrectly added, implement what's specified here.
