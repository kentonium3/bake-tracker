# Test Data System

This directory contains JSON test data for the Ingredient/Product architecture.

## Directory Structure

```
test_data/
  README.md                    # This file
  sample_data.json             # Main v3.4 test dataset
  sample_catalog.json          # Catalog format test data
  baking_ingredients_v32.json  # Large ingredient dataset
  *.csv                        # CSV lookup/development files
  examples/                    # Simple import examples (v3.4 format)
    simple_ingredients.json    # Basic ingredients + products
    simple_recipes.json        # Simple cookie recipes
    combined_import.json       # Combined import example
    test_errors.json           # Validation error testing
  archive/                     # Archived old-format files
    test_data_v2*.json         # Old v2.0 format files (for reference)
```

## Files

- **sample_data.json** - Comprehensive v3.4 test dataset with ingredients, products, inventory, recipes, and event planning data
- **sample_catalog.json** - Catalog format test data
- **exported_data.json** - Exported database snapshot (auto-generated, not tracked in git)

## Usage

### Loading Test Data

Load sample data into the database:

```bash
# Using Python module
python -m src.utils.load_test_data

# Or import and use programmatically
from src.utils.load_test_data import load_test_data_from_json
counts = load_test_data_from_json('test_data/sample_data.json')
```

### Exporting Current Database

Export your current database to JSON (useful for capturing manually entered test data):

```bash
# Export to default location (test_data/exported_data.json)
python -m src.utils.export_test_data

# Export to custom location
python -m src.utils.export_test_data path/to/output.json
```

### Building Up Test Data

Workflow for organically building a robust test dataset:

1. **Load initial test data**
   ```bash
   python -m src.utils.load_test_data
   ```

2. **Run the application and manually add data**
   - Add new ingredients/products through the UI
   - Create recipes
   - Record purchases
   - Update inventory
   - Plan events

3. **Export your enhanced database**
   ```bash
   python -m src.utils.export_test_data test_data/my_expanded_data.json
   ```

4. **Review and merge** the exported JSON with `sample_data.json` to create an even more comprehensive test dataset

5. **Commit the updated test data** so the team can benefit from your work

## JSON Structure

The JSON format matches v3.3+ of the import/export specification. See `docs/design/import_export_specification.md` for full details.

```json
{
  "version": "3.3",
  "exported_at": "2025-12-04T00:00:00Z",
  "application": "bake-tracker",
  "ingredients": [
    {
      "name": "All-Purpose Flour",
      "slug": "all_purpose_flour",
      "category": "Flour",
      "density_volume_value": 1.0,
      "density_volume_unit": "cup",
      "density_weight_value": 4.25,
      "density_weight_unit": "oz"
    }
  ],
  "products": [
    {
      "ingredient_slug": "all_purpose_flour",
      "brand": "King Arthur",
      "package_size": "25 lb bag",
      "package_unit": "lb",
      "package_unit_quantity": 25.0,
      "is_preferred": true
    }
  ],
  "purchases": [
    {
      "ingredient_slug": "all_purpose_flour",
      "product_brand": "King Arthur",
      "purchased_at": "2024-10-15T00:00:00Z",
      "quantity_purchased": 1,
      "unit_cost": 18.99,
      "total_cost": 18.99,
      "supplier": "Costco"
    }
  ],
  "inventory_items": [
    {
      "ingredient_slug": "all_purpose_flour",
      "product_brand": "King Arthur",
      "quantity": 1.5,
      "purchase_date": "2024-10-15",
      "location": "Main Pantry"
    }
  ],
  "recipes": [
    {
      "name": "Classic Chocolate Chip Cookies",
      "slug": "classic_chocolate_chip_cookies",
      "category": "Cookies",
      "yield_quantity": 48.0,
      "yield_unit": "cookies",
      "ingredients": [
        {
          "ingredient_slug": "all_purpose_flour",
          "quantity": 2.25,
          "unit": "cup"
        }
      ]
    }
  ],
  "finished_units": [...],
  "finished_goods": [...],
  "compositions": [...],
  "packages": [...],
  "recipients": [...],
  "events": [...]
}
```

## Key Features

- **Slug-based FK resolution** - Ingredients referenced by slug, products by (slug, brand)
- **FIFO tracking** - Inventory items include purchase dates for FIFO consumption
- **Price history** - Purchase records track unit cost over time
- **Preferred products** - Mark preferred brands for shopping recommendations
- **Complete dependency chain** - Ingredients → Products → Purchases/Inventory → Recipes → Finished Goods → Bundles → Packages → Events

## Testing

Run the comprehensive test suite to validate the architecture:

```bash
python test_ingredient_variant.py
```

This validates:
- Ingredient/Product separation
- Multiple brands per ingredient
- FIFO inventory tracking
- Price history with trend analysis
- Recipes reference generic ingredients (not products)
- Preferred product logic
- Aggregate inventory calculations
- Multiple recipes with diverse ingredients
