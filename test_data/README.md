# Test Data System

This directory contains JSON test data for the Ingredient/Product architecture.

## Files

- **sample_data.json** - Comprehensive test dataset with 12 ingredients, 13 products, 5 recipes, and complete event planning data
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

The JSON format matches the new Ingredient/Product architecture:

```json
{
  "ingredients": [
    {
      "name": "All-Purpose Flour",
      "slug": "all_purpose_flour",
      "category": "Flour",
      "recipe_unit": "cup",
      "density_g_per_ml": 0.507
    }
  ],
  "products": [
    {
      "ingredient_slug": "all_purpose_flour",
      "brand": "King Arthur",
      "package_size": "25 lb bag",
      "purchase_unit": "lb",
      "purchase_quantity": 25.0,
      "preferred": true
    }
  ],
  "purchases": [
    {
      "ingredient_slug": "all_purpose_flour",
      "product_brand": "King Arthur",
      "purchased_at": "2024-10-15T00:00:00",
      "unit_cost": 18.99,
      "quantity_purchased": 1.0,
      "total_cost": 18.99
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
  "unit_conversions": [
    {
      "ingredient_slug": "all_purpose_flour",
      "from_unit": "lb",
      "from_quantity": 1.0,
      "to_unit": "cup",
      "to_quantity": 3.6
    }
  ],
  "recipes": [
    {
      "name": "Classic Chocolate Chip Cookies",
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
  "finished_goods": [...],
  "bundles": [...],
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
