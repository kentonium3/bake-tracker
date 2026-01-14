# Price Research Workflow: Export for Google Sheets Processing

## Objective

Export current purchase data to CSV format that allows manual price research in Google Sheets, then re-import augmented prices back into the database.

## Requirements

Create a Python script that exports purchase data to CSV with these specifications:

### CSV Output Format

**Filename**: `purchases_for_price_research.csv`

**Required Columns** (in this order):
1. `purchase_id` - Purchase record ID (for re-matching on import)
2. `product_slug` - Product identifier (backup matching key)
3. `ingredient_name` - For context during research
4. `product_name` - Full product name
5. `brand` - Brand name
6. `package_size` - Package size description
7. `package_unit_quantity` - Numeric size (e.g., 28)
8. `package_unit` - Unit (e.g., "oz", "lb")
9. `package_type` - Type (e.g., "jar", "can", "bag")
10. `current_unit_price` - Current price in DB (likely 0)
11. `supplier_name` - Preferred or current supplier
12. `quantity_purchased` - How many packages
13. `purchase_date` - When purchased
14. `unit_price_NEW` - BLANK - for manual entry
15. `total_cost_NEW` - BLANK - for manual entry (will calculate)
16. `research_url` - BLANK - for tracking where price found
17. `notes` - BLANK - for research notes

### Data Requirements

**Include**:
- All 156 purchase records
- Join to products table for product details
- Join to ingredients table for ingredient name
- Join to suppliers table for supplier name
- Format dates as YYYY-MM-DD
- Format prices as decimal (e.g., 18.99 not $18.99)

**Sort by**:
- Primary: ingredient_name (alphabetical)
- Secondary: product_name (alphabetical)

### Export Script Structure

```python
#!/usr/bin/env python3
"""
Export purchases for manual price research.

Outputs CSV that can be imported to Google Sheets for manual price entry,
then re-imported back to update purchase prices.
"""
import csv
import sys
from pathlib import Path
from decimal import Decimal

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.database import session_scope
from src.models.purchase import Purchase
from src.models.product import Product
from src.models.ingredient import Ingredient
from src.models.supplier import Supplier

def export_purchases_for_research(output_path: str):
    """Export purchases to CSV for manual price research."""
    
    with session_scope() as session:
        # Query with all necessary joins
        purchases = session.query(Purchase).join(
            Product, Purchase.product_id == Product.id
        ).outerjoin(
            Ingredient, Product.ingredient_id == Ingredient.id
        ).outerjoin(
            Supplier, Purchase.supplier_id == Supplier.id
        ).order_by(
            Ingredient.name,
            Product.product_name
        ).all()
        
        # Build CSV rows
        rows = []
        for p in purchases:
            product = p.product
            ingredient = product.ingredient
            supplier = p.supplier
            
            rows.append({
                'purchase_id': p.id,
                'product_slug': product.product_slug,
                'ingredient_name': ingredient.name if ingredient else '',
                'product_name': product.product_name,
                'brand': product.brand or '',
                'package_size': product.package_size or '',
                'package_unit_quantity': product.package_unit_quantity or '',
                'package_unit': product.package_unit or '',
                'package_type': product.package_type or '',
                'current_unit_price': float(p.unit_price or 0),
                'supplier_name': supplier.name if supplier else '',
                'quantity_purchased': float(p.quantity_purchased or 0),
                'purchase_date': p.purchase_date.strftime('%Y-%m-%d') if p.purchase_date else '',
                'unit_price_NEW': '',  # For manual entry
                'total_cost_NEW': '',  # For manual entry
                'research_url': '',    # For tracking sources
                'notes': ''            # For research notes
            })
        
        # Write CSV
        fieldnames = [
            'purchase_id', 'product_slug', 'ingredient_name', 'product_name',
            'brand', 'package_size', 'package_unit_quantity', 'package_unit',
            'package_type', 'current_unit_price', 'supplier_name',
            'quantity_purchased', 'purchase_date', 'unit_price_NEW',
            'total_cost_NEW', 'research_url', 'notes'
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"✅ Exported {len(rows)} purchases to {output_path}")
        print(f"\nNext steps:")
        print(f"1. Import CSV to Google Sheets")
        print(f"2. Research prices and fill in unit_price_NEW column")
        print(f"3. total_cost_NEW will auto-calculate if you use: =M2*L2")
        print(f"4. Export from Sheets as CSV")
        print(f"5. Run import script to update database")

if __name__ == "__main__":
    output = "data/exports/purchases_for_price_research.csv"
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    export_purchases_for_research(output)
```

**Save as**: `scripts/export_purchases_for_research.py`

### Import Script Structure

After prices are researched, create import script:

```python
#!/usr/bin/env python3
"""
Import researched prices from CSV back to database.

Reads purchases_for_price_research.csv with filled-in prices
and updates Purchase records in database.
"""
import csv
import sys
from pathlib import Path
from decimal import Decimal

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.database import session_scope
from src.models.purchase import Purchase

def import_researched_prices(csv_path: str, dry_run: bool = True):
    """Import researched prices from CSV."""
    
    updates = []
    errors = []
    
    # Read CSV
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            purchase_id = int(row['purchase_id'])
            new_price = row['unit_price_NEW'].strip()
            
            # Skip if no new price entered
            if not new_price:
                continue
            
            try:
                unit_price = Decimal(new_price)
                updates.append({
                    'purchase_id': purchase_id,
                    'unit_price': unit_price,
                    'product': row['product_name'],
                    'brand': row['brand']
                })
            except (ValueError, Exception) as e:
                errors.append(f"Row {purchase_id}: Invalid price '{new_price}'")
    
    # Preview
    print(f"Found {len(updates)} prices to update")
    if errors:
        print(f"\n❌ Errors found:")
        for error in errors:
            print(f"  {error}")
        return
    
    # Show sample
    print(f"\nSample updates:")
    for update in updates[:5]:
        print(f"  {update['product']} ({update['brand']}): ${update['unit_price']}")
    
    if dry_run:
        print(f"\n⚠️  DRY RUN - No changes made")
        print(f"Run with dry_run=False to apply changes")
        return
    
    # Apply updates
    with session_scope() as session:
        for update in updates:
            purchase = session.query(Purchase).get(update['purchase_id'])
            if purchase:
                old_price = purchase.unit_price
                purchase.unit_price = update['unit_price']
                # Optionally update total_cost too
                purchase.total_cost = update['unit_price'] * purchase.quantity_purchased
        
        session.commit()
    
    print(f"\n✅ Updated {len(updates)} purchase prices")

if __name__ == "__main__":
    csv_path = "data/exports/purchases_for_price_research.csv"
    
    # Run dry run first
    print("=" * 70)
    print("DRY RUN")
    print("=" * 70)
    import_researched_prices(csv_path, dry_run=True)
    
    # Ask for confirmation
    response = input("\nProceed with actual import? (yes/no): ")
    if response.lower() == 'yes':
        print("\n" + "=" * 70)
        print("IMPORTING")
        print("=" * 70)
        import_researched_prices(csv_path, dry_run=False)
```

**Save as**: `scripts/import_researched_prices.py`

## Workflow Steps

1. **Export**: Run `python scripts/export_purchases_for_research.py`
2. **Import to Sheets**: Open CSV in Google Sheets
3. **Research Prices**: Fill in `unit_price_NEW` column manually
4. **Calculate Totals**: Add formula in `total_cost_NEW`: `=N2*L2` (drag down)
5. **Export from Sheets**: Download as CSV (same filename)
6. **Import Back**: Run `python scripts/import_researched_prices.py`

## Google Sheets Research Tips

**Formula for total_cost_NEW** (Column O):
```
=IF(N2<>"", N2*L2, "")
```

**Conditional formatting** to highlight:
- Rows where unit_price_NEW is empty (needs research)
- Rows where unit_price_NEW is filled (researched)

**Filter views** to work by:
- Supplier (research Costco items together)
- Ingredient category
- Brand

## Success Criteria

- [ ] Export script creates CSV with all 156 purchases
- [ ] CSV opens correctly in Google Sheets
- [ ] All required columns present
- [ ] Data is accurate and complete
- [ ] Import script successfully updates database
- [ ] Prices display correctly in Edit Inventory form

## Expected Timeline

- **Script creation**: 15 minutes
- **Export/import setup**: 5 minutes
- **Price research**: 2-4 hours (depends on how thorough)
- **Import and verify**: 10 minutes

**Total**: ~3-5 hours including research time
