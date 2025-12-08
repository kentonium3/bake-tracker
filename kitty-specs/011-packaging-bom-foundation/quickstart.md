# Quickstart: Packaging & BOM Foundation

**Feature**: 011-packaging-bom-foundation
**Date**: 2025-12-08

## Overview

This feature adds packaging material support to the Bake Tracker, allowing users to:
1. Track packaging supplies (bags, boxes, ribbon) as inventory items
2. Define packaging requirements for FinishedGoods and Packages
3. See packaging on shopping lists alongside food ingredients

## Key Concepts

### Packaging Ingredients
- Regular Ingredient with `is_packaging=True`
- Use packaging categories: Bags, Boxes, Ribbon, Labels, Tissue Paper, Wrapping, Other Packaging
- Create Products for specific brands/sizes (same as food ingredients)
- Track inventory via InventoryItem (same as food ingredients)

### Packaging Compositions
- Composition records link packaging Products to FinishedGoods or Packages
- Supports decimal quantities (e.g., 0.5 yards ribbon)
- Separate from food component compositions (XOR constraint)

## Database Setup

After implementing the model changes, delete the existing database and let SQLAlchemy auto-create:

```bash
# Backup existing data
python -c "from src.services.import_export_service import export_all_data; export_all_data('backup.json')"

# Delete database
rm data/bake_tracker.db

# Run app to recreate
python src/main.py

# Import data
python -c "from src.services.import_export_service import import_all_data; import_all_data('backup.json')"
```

## Testing the Feature

### 1. Create Packaging Ingredient

```python
from src.services.ingredient_service import create_ingredient

bag = create_ingredient(
    display_name="Cellophane Cookie Bags",
    category="Bags",
    is_packaging=True
)
```

### 2. Create Packaging Product

```python
from src.services.product_service import create_product

product = create_product(
    ingredient_id=bag.id,
    brand="Amazon Basics",
    package_size="100 count",
    purchase_unit="pack",
    purchase_quantity=100
)
```

### 3. Add Inventory

```python
from src.services.inventory_item_service import add_inventory

item = add_inventory(
    product_id=product.id,
    quantity=100,
    unit_cost=12.99,
    purchase_date=date.today()
)
```

### 4. Add Packaging to FinishedGood

```python
from src.services.composition_service import add_packaging_to_assembly

comp = add_packaging_to_assembly(
    assembly_id=finished_good.id,
    packaging_product_id=product.id,
    quantity=1.0,
    notes="One bag per dozen cookies"
)
```

### 5. Add Packaging to Package

```python
from src.services.composition_service import add_packaging_to_package

comp = add_packaging_to_package(
    package_id=package.id,
    packaging_product_id=tissue_product.id,
    quantity=3.0,
    notes="Three sheets tissue paper"
)
```

### 6. Get Shopping List

```python
from src.services.event_service import get_event_shopping_list

shopping_list = get_event_shopping_list(event_id)

print("Ingredients:")
for item in shopping_list["ingredients"]:
    print(f"  {item['ingredient_name']}: buy {item['to_buy']} {item['unit']}")

print("Packaging:")
for item in shopping_list["packaging"]:
    print(f"  {item['ingredient_name']}: buy {item['to_buy']} {item['unit']}")
```

## Files Changed

### Models
- `src/models/ingredient.py` - Add `is_packaging` column
- `src/models/composition.py` - Add `package_id`, `packaging_product_id`, change quantity to Float
- `src/models/package.py` - Add `packaging_compositions` relationship

### Services
- `src/services/ingredient_service.py` - Packaging filtering methods
- `src/services/composition_service.py` - Packaging composition methods
- `src/services/event_service.py` - Shopping list packaging aggregation
- `src/services/import_export_service.py` - Handle new fields

### UI (minimal)
- FinishedGood dialog - Add "Packaging" section
- Package dialog - Add "Packaging" section
- Shopping list view - Add "Packaging" section after ingredients

## Common Issues

### "Product is not a packaging product"
- Ensure the product's ingredient has `is_packaging=True`
- Use `ingredient_service.is_packaging_ingredient(ingredient_id)` to check

### "Cannot delete product"
- Product is referenced in a packaging composition
- Remove the composition first, then delete product

### Quantity validation error
- Quantities must be > 0
- Use float values (1.0 not 1) for consistency
