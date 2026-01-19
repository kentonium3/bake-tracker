# Bug Fix: Unit Price Shows 0.0000 - Database Has No Prices

**Branch**: `bugfix/inventory-unit-price-display`  
**Priority**: HIGH (dependent on price re-import)  
**Estimated Effort**: 5 minutes (verification only)

## Status Update

**Root cause identified**: Database has unit_price = 0, not the UI code.

**This bug is actually TWO issues**:
1. ✅ **UI Code**: Already fixed - correctly queries Purchase.unit_price
2. ❌ **Data**: Prices never imported - see `_BUG_reimport-purchase-prices.md`

## What Was Already Fixed

The Edit Inventory form correctly:
- Queries `Purchase.unit_price` when supplier selected
- Makes field read-only (display only)
- Shows fallback 0.00 when price is NULL or 0

**Code is working as designed** - it displays what's in the database.

## What Needs to be Fixed

**Re-import purchase prices** from augmented JSON files.

**See**: `_BUG_reimport-purchase-prices.md` for complete solution.

## Verification After Price Import

Once prices are re-imported, verify this bug is resolved:

### Test Steps

1. **Re-import prices** using script from `_BUG_reimport-purchase-prices.md`
2. **Open Edit Inventory form** for Costco Almonds
3. **Select supplier** "Costco" from dropdown
4. **Verify Unit Price** shows actual price (e.g., $18.99)
5. **Verify field is read-only** (grayed out, can't edit)

### Expected Results

```
Before price import:
- Select Costco → Unit Price: 0.0000 ❌

After price import:
- Select Costco → Unit Price: 18.99 ✅
```

### Test Cases

**Various products**:
- Corn Starch → $2.25
- Baking Soda → $5.49  
- Almonds → $18.99
- PAM Cooking Spray → $3.99 (already had price)

**Edge cases**:
- Supplier = "None" → Unit Price: 0.00
- Supplier with no purchases → Unit Price: 0.00
- Product never purchased from selected supplier → Unit Price: 0.00

## Success Criteria

1. **Prices Display**: Shows actual prices from database
2. **Supplier Selection Works**: Price updates when supplier changes
3. **Read-Only Enforced**: Cannot edit price in inventory view
4. **Fallbacks Work**: Shows 0.00 when no price data exists

## Implementation Notes

**No code changes needed** - UI already works correctly.

**Only action needed**: Verify after price re-import.

## Related Issues

**Depends on**:
- `_BUG_reimport-purchase-prices.md` - Must be completed first

**Original spec**:
- This bug was originally about UI implementation
- Diagnostic revealed it's actually a data issue
- UI implementation was already correct

## Testing Checklist

- [ ] Prices re-imported successfully
- [ ] Database has unit_price values > 0
- [ ] Edit form displays prices when supplier selected
- [ ] Prices match expected values from JSON
- [ ] Read-only field behavior works
- [ ] No errors in console

## Git Workflow

No code changes needed - just verification:

```bash
# After running price re-import script:
# 1. Test UI manually
# 2. If working, close this bug
# 3. If issues found, investigate further
```

---

**VERIFICATION ONLY**: This bug fix just confirms the UI works after data is fixed. Real fix is in `_BUG_reimport-purchase-prices.md`.
