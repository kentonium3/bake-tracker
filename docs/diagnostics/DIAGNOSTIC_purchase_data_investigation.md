# Diagnostic Investigation: Missing Purchase Data and Price Display Issues

## Context

An AI-assisted price augmentation script successfully added prices to `view_inventory_augmented.json` and `view_purchases_augmented.json`. These files were reported as successfully imported into the database. However:

1. **Unit prices show as 0.0000** in Edit Inventory form when supplier is selected
2. **Edit form still shows quantity_purchased (2.0)** instead of quantity_remaining (0.7)
3. **No way to verify purchase data** exists (no Purchase Management UI yet)

## Objectives

Investigate and document:
1. Do Purchase records exist in the database?
2. Do they have unit_price values populated?
3. Are InventoryItems linked to their Purchases?
4. Which field is the Edit Inventory form actually displaying?

## Task 1: Database Diagnostic Queries

Run these SQL queries and save results to a file called `diagnostic_results.txt`:

```sql
-- Query 1: Count total purchases
SELECT COUNT(*) as total_purchases FROM purchases;

-- Query 2: Count purchases with prices
SELECT 
    COUNT(*) as purchases_with_price,
    MIN(unit_price) as min_price,
    MAX(unit_price) as max_price,
    AVG(unit_price) as avg_price
FROM purchases 
WHERE unit_price IS NOT NULL AND unit_price > 0;

-- Query 3: Count inventory items linked to purchases
SELECT 
    COUNT(*) as total_inventory_items,
    COUNT(purchase_id) as items_with_purchase_link,
    COUNT(*) - COUNT(purchase_id) as items_without_purchase_link
FROM inventory_items;

-- Query 4: Sample of purchase data (first 10 records)
SELECT 
    p.id,
    prod.product_name,
    prod.brand,
    p.purchase_date,
    p.quantity_purchased,
    p.unit_price,
    p.total_cost,
    p.supplier_id,
    s.name as supplier_name
FROM purchases p
JOIN products prod ON p.product_id = prod.id
LEFT JOIN suppliers s ON p.supplier_id = s.id
ORDER BY p.purchase_date DESC
LIMIT 10;

-- Query 5: Costco Almonds specific investigation
SELECT 
    p.product_name,
    p.brand,
    i.quantity_remaining,
    i.quantity_purchased,
    i.purchase_id,
    pur.unit_price,
    pur.total_cost,
    pur.purchase_date,
    s.name as supplier
FROM inventory_items i
JOIN products p ON i.product_id = p.id
LEFT JOIN purchases pur ON i.purchase_id = pur.id
LEFT JOIN suppliers s ON pur.supplier_id = s.id
WHERE p.product_name LIKE '%Almond%'
  AND (p.brand LIKE '%Costco%' OR p.brand LIKE '%Kirkland%');

-- Query 6: Check for orphaned purchases (purchases without inventory links)
SELECT COUNT(*) as orphaned_purchases
FROM purchases p
WHERE NOT EXISTS (
    SELECT 1 FROM inventory_items i WHERE i.purchase_id = p.id
);
```

**Save all query results** to `diagnostic_results.txt` with clear section headers.

## Task 2: Identify Edit Form File and Quantity Field

1. **Find the Edit Inventory form file**:
   - Search for files with "inventory" and "edit" or "dialog" in the name
   - Check `src/ui/forms/` directory
   - Likely named something like `inventory_edit_dialog.py`

2. **Examine the quantity field loading**:
   - Find the form load/initialization method
   - Identify which field is being loaded into the quantity entry
   - Look for lines like: `self.quantity_entry.insert(0, str(item._____))`
   
3. **Document findings** in `diagnostic_results.txt`:
   ```
   EDIT FORM ANALYSIS
   ==================
   File: [path/to/file.py]
   Method: [method name]
   Line: [line number]
   Code: self.quantity_entry.insert(0, str(item.FIELD_NAME))
   
   Currently loading: quantity_purchased | quantity_remaining
   Should be loading: quantity_remaining
   ```

## Task 3: Check Import Service

1. **Locate the import service** that processes view files:
   - Search for files related to import in `src/services/`
   - Look for methods like `import_inventory_view()` or `import_purchases_view()`

2. **Verify what fields are being imported**:
   - Check if `unit_price` is being imported from JSON to Purchase table
   - Check if `purchase_id` is being set on InventoryItem
   - Check if `supplier_id` is being set on Purchase

3. **Document in `diagnostic_results.txt`**:
   ```
   IMPORT SERVICE ANALYSIS
   =======================
   File: [path/to/import_service.py]
   
   Imports unit_price: YES | NO
   Sets purchase_id on inventory: YES | NO
   Sets supplier_id on purchase: YES | NO
   
   Code excerpt: [relevant lines showing what's imported]
   ```

## Task 4: Sample the Augmented JSON Files

If the original `view_inventory_augmented.json` and `view_purchases_augmented.json` files still exist:

1. **Show sample records** from each file (first 2-3 records)
2. **Verify prices are present** in the JSON
3. **Document in `diagnostic_results.txt`**

## Task 5: Consolidate Findings

Create a summary section in `diagnostic_results.txt`:

```
SUMMARY OF FINDINGS
===================

Purchase Records:
- Total purchases in DB: [number]
- Purchases with prices: [number]
- Sample unit_price values: [show a few]

Inventory Links:
- Total inventory items: [number]
- Items linked to purchases: [number]
- Items without purchase link: [number]

Edit Form Issue:
- File: [path]
- Currently loads: [field name]
- Should load: quantity_remaining

Import Service:
- Imports prices: [YES/NO]
- Links purchases: [YES/NO]
- Issue identified: [description if found]

ROOT CAUSE HYPOTHESIS:
[Based on data, what's the most likely cause of the issues]

RECOMMENDED FIX:
[What needs to be done]
```

## Expected Outputs

1. **File**: `diagnostic_results.txt` containing all query results and analysis
2. **Console summary** of key findings
3. **Recommendation** for what needs to be fixed

## Notes

- Use session_scope() context manager for database queries
- Handle potential NULL values in query results gracefully
- If files don't exist, note that in the diagnostic
- Focus on data integrity issues, not UI fixes (those come after we understand the data)

## Success Criteria

- Clear understanding of whether Purchase data exists
- Clear understanding of whether prices are populated
- Clear understanding of whether inventory↔purchase links exist
- Identification of which field Edit form is loading
- Actionable recommendation for next steps
