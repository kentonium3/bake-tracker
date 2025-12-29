# Bug Fix: Re-Import Augmented Purchase Prices

**Branch**: `bugfix/reimport-purchase-prices`  
**Priority**: CRITICAL (blocks price display feature)  
**Estimated Effort**: 15 minutes

## Context

**Root Cause Identified**: AI-augmented purchase prices exist in JSON files but were never imported into the database.

**Evidence from Diagnostic**:
- 156 Purchase records exist in database
- 155 have `unit_price = 0` (never updated)
- 1 has `unit_price = 3.99` (manually added later)
- JSON files (`view_purchases_augmented.json`) have correct prices ($2.25, $5.49, etc.)
- Import service supports merge mode but was likely run in skip_existing mode or before augmentation

**Result**: Edit Inventory form shows 0.0000 because database has unit_price = 0.

## Solution

Re-run the import in **MERGE mode** to update existing Purchase records with prices from augmented JSON files.

## Implementation Requirements

### Option A: Python Script (Recommended)

Create a script to re-import with merge mode:

```python
#!/usr/bin/env python3
"""
Re-import augmented purchase prices in merge mode.
Updates existing Purchase records with unit_price from JSON.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.enhanced_import_service import import_view

def reimport_prices():
    """Re-import purchase prices in merge mode."""
    
    json_path = "test_data/view_purchases_augmented.json"
    
    # Dry run first to verify
    print("=" * 70)
    print("DRY RUN - Previewing changes")
    print("=" * 70)
    result = import_view(
        json_path,
        mode="merge",  # Update existing records
        dry_run=True   # Preview only
    )
    print(result.get_summary())
    
    # Ask for confirmation
    response = input("\nProceed with actual import? (yes/no): ")
    if response.lower() != 'yes':
        print("Import cancelled.")
        return
    
    # Actual import
    print("\n" + "=" * 70)
    print("ACTUAL IMPORT - Updating database")
    print("=" * 70)
    result = import_view(
        json_path,
        mode="merge",
        dry_run=False
    )
    print(result.get_summary())
    
    # Verify
    print("\n" + "=" * 70)
    print("Verification")
    print("=" * 70)
    
    from src.services.database import session_scope
    from src.models.purchase import Purchase
    
    with session_scope() as session:
        total = session.query(Purchase).count()
        with_price = session.query(Purchase).filter(
            Purchase.unit_price > 0
        ).count()
        
        print(f"Total purchases: {total}")
        print(f"Purchases with price > 0: {with_price}")
        print(f"Purchases with price = 0: {total - with_price}")
        
        if with_price > 100:
            print("\n✅ SUCCESS! Prices imported.")
        else:
            print("\n❌ WARNING: Most prices still 0. Check import results above.")

if __name__ == "__main__":
    reimport_prices()
```

**Save as**: `scripts/reimport_purchase_prices.py`

### Option B: CLI Command (If Available)

If import CLI exists:
```bash
python -m src.utils.import_cli \
    --file test_data/view_purchases_augmented.json \
    --mode merge \
    --dry-run  # Preview first

# Then run for real:
python -m src.utils.import_cli \
    --file test_data/view_purchases_augmented.json \
    --mode merge
```

### Option C: UI Import (If Available)

Use Import dialog in application:
1. File → Import → Import Purchases View
2. Select `test_data/view_purchases_augmented.json`
3. **Important**: Choose "Merge" mode (update existing)
4. Review preview
5. Confirm import

## Expected Results

**Before**:
```sql
SELECT COUNT(*) FROM purchases WHERE unit_price > 0;
-- Result: 1
```

**After**:
```sql
SELECT COUNT(*) FROM purchases WHERE unit_price > 0;
-- Result: 156 (or close to it)
```

**Sample prices should appear**:
```sql
SELECT product_name, unit_price 
FROM purchases p
JOIN products prod ON p.product_id = prod.id
WHERE product_name LIKE '%Corn Starch%'
   OR product_name LIKE '%Baking Soda%'
   OR product_name LIKE '%Almond%'
LIMIT 5;

-- Expected:
-- 100% Pure Corn Starch | 2.25
-- Pure Baking Soda      | 5.49
-- Almonds               | 18.99 (or similar)
```

## Implementation Tasks

### Task 1: Create Re-Import Script
**File**: `scripts/reimport_purchase_prices.py`

1. Copy the script code above
2. Save to scripts directory
3. Make executable: `chmod +x scripts/reimport_purchase_prices.py`

### Task 2: Run Dry Run
**Command**: `python scripts/reimport_purchase_prices.py`

1. Review dry run output
2. Verify it shows ~155 updates
3. Check sample prices in preview
4. Confirm no errors

### Task 3: Execute Actual Import
**Command**: Answer "yes" when prompted

1. Watch for errors during import
2. Review import summary
3. Check verification counts

### Task 4: Verify in UI
**Steps**:
1. Open Edit Inventory form for Costco Almonds
2. Select supplier "Costco"
3. **Expected**: Unit Price shows actual price (e.g., $18.99)
4. **Not**: Unit Price shows 0.0000

### Task 5: Verify Database Directly
**Query**:
```sql
-- Should show mostly populated prices
SELECT 
    COUNT(*) as total,
    COUNT(CASE WHEN unit_price > 0 THEN 1 END) as with_price,
    AVG(unit_price) as avg_price,
    MIN(unit_price) as min_price,
    MAX(unit_price) as max_price
FROM purchases;

-- Should show variety of prices
SELECT unit_price, COUNT(*) as count
FROM purchases
WHERE unit_price > 0
GROUP BY unit_price
ORDER BY count DESC
LIMIT 10;
```

## Testing Checklist

### Before Import
- [ ] Verify JSON file exists: `test_data/view_purchases_augmented.json`
- [ ] Verify JSON has prices: Check a few sample records
- [ ] Backup database (optional but recommended)
- [ ] Confirm current state: 155 purchases with unit_price = 0

### After Import
- [ ] 150+ purchases have unit_price > 0
- [ ] Price variety exists (not all same price)
- [ ] Sample prices match JSON (Corn Starch = $2.25, etc.)
- [ ] No errors in import log
- [ ] Edit form now shows prices when supplier selected

### Edge Cases
- [ ] PAM cooking spray ($3.99) still has its price
- [ ] No duplicate purchases created
- [ ] All inventory items still linked to purchases
- [ ] Supplier data still intact

## Success Criteria

1. **Database Updated**: 150+ purchases have unit_price > 0
2. **Prices Correct**: Sample verification shows correct prices from JSON
3. **UI Works**: Edit Inventory form displays prices
4. **No Data Loss**: All existing data intact (purchases, links, suppliers)
5. **Reproducible**: Script can be run again if needed

## Troubleshooting

### If import fails:
```python
# Check import service configuration
from src.services.enhanced_import_service import import_view
help(import_view)  # See available parameters

# Check if JSON file is valid
import json
with open('test_data/view_purchases_augmented.json') as f:
    data = json.load(f)
    print(f"Records: {len(data.get('records', []))}")
    print(f"Sample: {data['records'][0]}")
```

### If prices still 0 after import:
1. Check import mode was "merge" not "skip_existing"
2. Verify JSON field name is "unit_price" not "price"
3. Check import logs for skipped records
4. Verify import service handles unit_price field

### If some prices missing:
- Check which records have unit_price in JSON
- Some products might legitimately be $0 (free samples)
- Import summary should show count of updated records

## Related Issues

**Unblocks**:
- `_BUG_inventory-unit-price-display.md` - Prices will now display

**Related Files**:
- `test_data/view_purchases_augmented.json` - Source data
- `src/services/enhanced_import_service.py` - Import logic
- `scripts/reimport_purchase_prices.py` - Re-import script

## Git Workflow

```bash
git checkout -b bugfix/reimport-purchase-prices
git add scripts/reimport_purchase_prices.py
git commit -m "feat: add script to re-import augmented purchase prices"
# Run the script
git add .  # If database is in git (probably not)
git commit -m "data: import augmented purchase prices from JSON"
git push
```

---

**CRITICAL FIX**: This unblocks price display feature. The code is correct; the data just needs to be imported.
