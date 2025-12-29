# Bug Fix: Format Qty Remaining with 1 Decimal Place

**Branch**: `bugfix/qty-remaining-precision`  
**Priority**: MEDIUM (display quality issue)  
**Estimated Effort**: 15 minutes

## Context

**Problem**: Qty Remaining displays with excessive decimal precision
- Current: `0.666667 bags (2 lb)` ← Too precise, looks sloppy
- Expected: `0.7 bags (2 lb)` ← Clean, readable

**User preference**: 1 decimal place is close enough for inventory tracking.

## Current State vs Expected

### Examples of Current (Bad)
```
0.666667 bags (2 lb)      ← 6 decimal places
1.333333 jars (37.33 oz)  ← 6 decimal places
2.500000 cans (70 oz)     ← Unnecessary trailing zeros
```

### Examples of Expected (Good)
```
0.7 bags (2 lb)       ← 1 decimal place
1.3 jars (36.4 oz)    ← 1 decimal place
2.5 cans (70 oz)      ← 1 decimal place, no trailing zero
```

## Implementation Requirements

### 1. Update format_qty_remaining Function
**File**: Likely in `src/ui/inventory_tab.py` or utility module

**Current** (from BUG_pantry-qty-format-correction.md):
```python
def format_qty_remaining(qty_remaining, product):
    """Format quantity remaining for display."""
    
    # ... setup code ...
    
    # Current formatting (probably uses :g or :.2f)
    qty_display = f"{qty_remaining:g}"  # ← Produces 0.666667
    total_display = f"{total_amount:g}"
    
    return f"{qty_display} {pkg_type_display} ({total_display} {pkg_unit})"
```

**Updated** (1 decimal place):
```python
def format_qty_remaining(qty_remaining, product):
    """
    Format quantity remaining for display.
    
    Format: {qty} {package_type}(s) ({total} {unit})
    Quantities rounded to 1 decimal place.
    
    Examples:
        0.7 bags (2 lb)
        1.3 jars (36.4 oz)
        2.5 cans (70 oz)
    """
    # Get product package details
    pkg_qty = product.package_unit_quantity or 1
    pkg_unit = product.package_unit or "unit"
    pkg_type = product.package_type or "pkg"
    
    # Calculate total amount
    total_amount = qty_remaining * pkg_qty
    
    # Handle singular/plural for package type
    if qty_remaining == 1:
        pkg_type_display = pkg_type
    else:
        pkg_type_display = f"{pkg_type}s"
    
    # Format with 1 decimal place, remove trailing zeros
    qty_display = f"{qty_remaining:.1f}".rstrip('0').rstrip('.')
    
    # Total amount: 1 decimal for small amounts, 0 decimals for large
    if total_amount > 100:
        total_display = f"{total_amount:.0f}"
    else:
        total_display = f"{total_amount:.1f}".rstrip('0').rstrip('.')
    
    return f"{qty_display} {pkg_type_display} ({total_display} {pkg_unit})"
```

### 2. Formatting Logic Explained

**For quantity (package count)**:
```python
qty_display = f"{qty_remaining:.1f}".rstrip('0').rstrip('.')

# Examples:
# 0.666667 → "0.7" (rounded to 1 decimal)
# 2.0 → "2" (trailing .0 removed)
# 2.5 → "2.5" (kept as-is)
# 1.333333 → "1.3" (rounded to 1 decimal)
```

**For total amount (actual units)**:
```python
# Small amounts (<100): 1 decimal place
f"{total_amount:.1f}".rstrip('0').rstrip('.')
# 2.0 → "2"
# 36.4 → "36.4"

# Large amounts (≥100): No decimals
f"{total_amount:.0f}"
# 307.5 → "308"
# 450.0 → "450"
```

## Implementation Tasks

### Task 1: Locate format_qty_remaining Function
**Files**: Search for the function

1. Check `src/ui/inventory_tab.py`
2. Check utility modules
3. Or wherever it was implemented from BUG_pantry-qty-format-correction

### Task 2: Update Formatting Logic
**File**: Where function is located

1. Change quantity formatting to `:.1f`
2. Add `.rstrip('0').rstrip('.')` to remove trailing zeros
3. Update total amount formatting (1 decimal for small, 0 for large)
4. Update docstring with new examples

### Task 3: Test with Various Values
**File**: Test file or manual testing

Test cases:
```python
# Fractional quantities
assert format_qty(Decimal("0.666667"), product) == "0.7 bags (2 lb)"
assert format_qty(Decimal("1.333333"), product) == "1.3 jars (36.4 oz)"

# Whole numbers
assert format_qty(Decimal("2.0"), product) == "2 cans (56 oz)"
assert format_qty(Decimal("3.0"), product) == "3 bags (75 lb)"

# Halfway rounding
assert format_qty(Decimal("0.75"), product) == "0.8 bags (2.1 lb)"
assert format_qty(Decimal("0.25"), product) == "0.3 bags (0.7 lb)"

# Edge cases
assert format_qty(Decimal("0.1"), product) == "0.1 jars (2.8 oz)"
assert format_qty(Decimal("0.05"), product) == "0.1 jars (1.4 oz)"
```

### Task 4: Verify Across All Views
**Files**: All places that display Qty Remaining

Check these locations:
- [ ] My Pantry tab - Detail view
- [ ] My Pantry tab - Aggregate view
- [ ] Edit Inventory form - Current quantity display
- [ ] Anywhere else that shows inventory quantities

## Testing Checklist

### Display Formatting
- [ ] Quantities show 1 decimal place max
- [ ] No excessive decimals (0.7 not 0.666667)
- [ ] Trailing zeros removed (2 not 2.0)
- [ ] Decimal point removed when whole (2 not 2.)
- [ ] Parentheses spacing correct ("bags (2 lb)" not "bags(2 lb)")

### Rounding Behavior
- [ ] 0.666667 → 0.7 (rounds up)
- [ ] 0.333333 → 0.3 (rounds down)
- [ ] 0.75 → 0.8 (rounds up from halfway)
- [ ] 0.25 → 0.3 (rounds up from halfway)
- [ ] 2.0 → 2 (trailing zero removed)

### Total Amount Formatting
- [ ] Small totals (< 100): 1 decimal place
- [ ] Large totals (≥ 100): No decimals
- [ ] Trailing zeros removed from small totals
- [ ] Examples: "36.4 oz" not "36.40 oz", "2 lb" not "2.0 lb"

### All Display Locations
- [ ] Pantry tab listing shows new format
- [ ] Aggregate view shows new format
- [ ] Edit form current quantity shows new format
- [ ] Calculator preview shows new format

## Success Criteria

1. **Clean Display**: Quantities show 1 decimal place, no excessive precision
2. **Trailing Zeros Gone**: Whole numbers display without .0
3. **Consistent**: Same format everywhere quantities appear
4. **Readable**: Numbers are easy to scan and understand
5. **User Validation**: Primary user confirms display looks professional

## Examples of Final Output

All these should display correctly:

| qty_remaining | package_type | package_qty | package_unit | Display |
|--------------|--------------|-------------|--------------|---------|
| 0.666667 | bag | 3 | lb | `0.7 bags (2.1 lb)` |
| 1.333333 | jar | 28 | oz | `1.3 jars (36.4 oz)` |
| 2.5 | can | 28 | oz | `2.5 cans (70 oz)` |
| 2.0 | bag | 25 | lb | `2 bags (50 lb)` |
| 0.1 | bottle | 32 | fl oz | `0.1 bottles (3.2 fl oz)` |
| 12.3 | bag | 25 | lb | `12.3 bags (308 lb)` |

## Related Files

**Primary File**:
- `src/ui/inventory_tab.py` - Contains format_qty_remaining function

**Also Check**:
- `src/ui/forms/inventory_edit_dialog.py` - May use same function
- Any utility module that has formatting helpers

## Git Workflow

```bash
git checkout -b bugfix/qty-remaining-precision
git commit -m "fix: format quantity remaining to 1 decimal place"
git commit -m "refactor: remove trailing zeros from quantity display"
git push
```

---

**Quick Fix**: Small change, big improvement in display quality. Makes the app look more professional.
