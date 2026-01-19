# Claude Code Prompt: Populate Initial Inventory from Product Quantities

## Context

The ingredients and products catalogs have been successfully imported. However, the inventory table is empty. We need to populate initial inventory based on actual pantry quantities from Marianne's spreadsheet data.

**Data Source:** `test_data/products_incomplete_updated.csv`  
**Key Column:** `product_quantity` - represents how many packages/units are in inventory

## Product Quantity Interpretation Rules

The `product_quantity` column uses the following logic:

| Value | Meaning | Example | Inventory Action |
|-------|---------|---------|------------------|
| *blank* | 1 full package | `,` | Create 1 inventory item with full package quantity |
| `0` | Zero inventory | `0,` | Skip - do not create inventory item |
| `< 1` (decimal) | Percentage of package | `0.5,` | Create 1 inventory item with 50% of package quantity |
| `1` | 1 full package | `1,` | Create 1 inventory item with full package quantity |
| `> 1` (decimal) | N packages + fraction | `1.2,` | Create 2 inventory items: 1 full + 0.2 partial |
| `> 1` (integer) | N full packages | `2,` | Create N inventory items, each with full package quantity |

**Examples:**
- `product_quantity` blank → 1 package of sugar (4 lb)
- `product_quantity = 0` → Skip (Kerry butter, no inventory)
- `product_quantity = 0.5` → Half package (36 oz of 72 oz Nestlé chips)
- `product_quantity = 1.2` → 1 full package + 0.2 partial (Heathbar toffee bits)
- `product_quantity = 2` → 2 full packages (Penzeys vanilla beans)

## Database Schema Reference

### Products Table (already populated)
- `id` - Primary key
- `ingredient_id` - FK to ingredients
- `brand`
- `product_name`
- `gtin`
- `package_unit_quantity` - Size of package (e.g., 4 for "4 lb bag")
- `package_unit` - Unit of package (e.g., "lb")

### Inventory Items Table (needs population)
- `product_id` - FK to products (REQUIRED)
- `quantity` - Amount in inventory in package units (e.g., 2.5 lb)
- `unit` - Unit (should match product's package_unit)
- `purchase_date` - Date purchased (use today's date: 2025-12-20)
- `expiration_date` - NULL for now
- `location` - "pantry" (default)
- `notes` - NULL or descriptive

## Your Tasks

### Task 1: Create Python Script to Generate Inventory

**Script Location:** `test_data/populate_inventory.py`

**Script Requirements:**

1. **Read CSV data:** Load `test_data/products_incomplete_updated.csv`

2. **For each row where product_quantity is not "0":**
   - Look up product by: `brand`, `ingredient_slug`, `package_unit_quantity`, `package_unit`
   - If multiple products match (duplicates in CSV), skip with warning
   - If no product found, skip with warning
   - Calculate inventory items based on quantity rules above

3. **Generate inventory JSON:** Create `test_data/inventory_initial.json` in **UNIFIED IMPORT FORMAT** (v3.4):
```json
{
  "version": "3.4",
  "inventory_items": [
    {
      "product_brand": "Domino",
      "product_ingredient_slug": "sugar_granulated",
      "product_package_size": 4.0,
      "product_package_unit": "lb",
      "quantity": 4.0,
      "unit": "lb",
      "purchase_date": "2025-12-20",
      "location": "pantry",
      "notes": "Initial inventory import"
    },
    {
      "product_brand": "Heathbar",
      "product_ingredient_slug": "toffee_bits",
      "product_package_size": 8.0,
      "product_package_unit": "oz",
      "quantity": 8.0,
      "unit": "oz",
      "purchase_date": "2025-12-20",
      "location": "pantry",
      "notes": "Initial inventory import - full package"
    },
    {
      "product_brand": "Heathbar",
      "product_ingredient_slug": "toffee_bits",
      "product_package_size": 8.0,
      "product_package_unit": "oz",
      "quantity": 1.6,
      "unit": "oz",
      "purchase_date": "2025-12-20",
      "location": "pantry",
      "notes": "Initial inventory import - partial package (0.2)"
    }
  ]
}
```

4. **Handle edge cases:**
   - Multiple matches: Log warning, skip row
   - No match found: Log warning, skip row
   - Invalid quantity: Log warning, skip row
   - Missing package_unit_quantity or package_unit in CSV: Log warning, skip row

5. **Generate import report:**
   - Total rows processed
   - Total inventory items created
   - Rows skipped (with reasons)
   - Products not found (with details)

### Task 2: Verify Product Lookups

Before generating inventory JSON, run a verification pass:

1. For each unique (brand, ingredient_slug, package_unit_quantity, package_unit) in CSV
2. Query database to verify product exists
3. Report any missing products
4. If critical products are missing, stop and report issue

### Task 3: Execute Script and Review

1. Run `python test_data/populate_inventory.py`
2. Review generated `test_data/inventory_initial.json`
3. Report statistics:
   - Total products in CSV: [count]
   - Products with inventory (quantity != 0): [count]
   - Inventory items generated: [count]
   - Products not found: [count] (list them)
   - Rows skipped: [count] (with reasons)

## Important Notes

### Product Lookup Strategy

The CSV uses these fields to identify products:
- `brand` (matches Product.brand)
- `ingredient_slug` (matches Product → Ingredient.slug via FK)
- `package_unit_quantity` (matches Product.package_unit_quantity)
- `package_unit` (matches Product.package_unit)

**Some products appear multiple times in CSV with different package sizes** (e.g., McCormick peppermint extract in 1 fl oz and 2 fl oz bottles). These are DIFFERENT products and should create separate inventory items.

### Catalog Import Format

The inventory JSON should follow the **unified import format (v3.4)**, not the catalog import format. The unified import service handles transactional data like inventory items. Check `test_data/sample_data.json` for reference structure if needed.

**Key format notes:**
- `version`: "3.4" (unified import format)
- `product_package_size`: numeric value (4.0, not "4")
- Product lookup uses: brand + ingredient_slug + package_size + package_unit

### Purchase Date

Use today's date (2025-12-20) for all initial inventory items since we don't have actual purchase dates from the spreadsheet.

### Location

Default all items to "pantry" location. Users can update later if needed.

## Expected Results

After running the script and importing the generated JSON:

```bash
# Import inventory using UNIFIED import (not catalog import)
python -m src.cli.import_data test_data/inventory_initial.json
```

**Expected outcome:**
- ✅ ~150+ inventory items created (varies based on product_quantity values)
- ✅ "My Pantry" tab in UI shows populated inventory
- ✅ Products properly linked via product_id FK
- ✅ Quantities correctly calculated based on package sizes

## Verification Steps

After import, verify in the app:

1. Open "My Pantry" (Inventory) tab
2. Confirm inventory items are visible
3. Spot-check quantities:
   - Domino sugar (4 lb bag, quantity blank) → Should show 4.0 lb
   - Heathbar toffee bits (8 oz bag, quantity 1.2) → Should show 2 items: 8.0 oz + 1.6 oz
   - Kerry butter (1 oz, quantity 0) → Should NOT appear
   - Penzeys vanilla beans (3 each, quantity 2) → Should show 2 items of 3 each

## Reference Files

- **CSV Data:** `test_data/products_incomplete_updated.csv`
- **Schema Reference:** `src/models/` (Product, InventoryItem models)
- **Example Format:** `test_data/sample_data.json` (check inventory_items structure)
- **Constitution:** `.kittify/memory/constitution.md` (Section IV - data integrity)

## Questions Before Starting

1. Should I create the Python script first and wait for your approval before running?
2. Do you want me to import the inventory JSON automatically using `python -m src.cli.import_data`, or should you review it first?
3. Should items with missing package_unit_quantity or package_unit in the CSV be skipped or flagged as errors?
