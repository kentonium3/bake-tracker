# Import Examples

This directory contains example import files for the Seasonal Baking Tracker application using the **v3.4 format**.

## File Descriptions

### Simple Examples

- **`simple_ingredients.json`** - Contains 5 basic ingredients and their products
  - Good for: Learning the format, quick testing
  - Contents: flour, sugar, butter, chocolate chips, vanilla (ingredients + products)

- **`simple_recipes.json`** - Contains 3 cookie recipes
  - Good for: Testing recipe imports
  - Requirement: Import `simple_ingredients.json` first (recipes reference these ingredients by slug)

### Combined Example

- **`combined_import.json`** - Single file with ingredients, products, and a recipe
  - Good for: One-step import, understanding relationships
  - Contents: 3 ingredients, 3 products, 1 recipe

### Testing Files

- **`test_errors.json`** - Contains intentional errors for validation testing
  - Good for: Testing error handling, validation logic
  - Warning: Most records will fail to import (by design)
  - Error types: missing fields, invalid categories, bad references, invalid values

## v3.4 Format Structure

The current import format separates concerns into distinct entity arrays:

```json
{
  "version": "3.4",
  "exported_at": "2025-12-16T00:00:00Z",
  "application": "bake-tracker",
  "ingredients": [...],
  "products": [...],
  "purchases": [...],
  "inventory_items": [...],
  "recipes": [...]
}
```

### Key Concepts

1. **Ingredients** - Generic ingredient types (e.g., "All-Purpose Flour")
   - Have `name`, `slug`, `category`
   - Optional density fields for unit conversion

2. **Products** - Brand-specific products linked to ingredients
   - Reference ingredients by `ingredient_slug`
   - Have `brand`, `package_unit`, `package_unit_quantity`

3. **Recipes** - Recipe definitions
   - Have `name`, `slug`, `category`
   - Ingredients referenced by `ingredient_slug` (not by name)

## Usage

### Using the Import Service

```python
from src.services.import_export_service import import_all_from_json

# Import from a JSON file
result = import_all_from_json("test_data/examples/combined_import.json")
print(result.summary())
```

## Import Order

When importing separate files, follow this order for referential integrity:

1. `simple_ingredients.json` (creates ingredients + products)
2. `simple_recipes.json` (references existing ingredients)

Or use `combined_import.json` which includes everything in one file.

## Field Reference

### Ingredient Categories
```
Flour, Sugar, Dairy, Oils/Butters, Nuts, Spices, Chocolate/Candies,
Cocoa Powders, Dried Fruits, Extracts, Syrups, Alcohol, Misc
```

### Recipe Categories
```
Cookies, Cakes, Candies, Bars, Brownies, Breads, Pastries, Pies, Tarts, Other
```

### Valid Units

**Weight**: oz, lb, g, kg
**Volume**: tsp, tbsp, cup, ml, l, fl oz, pt, qt, gal
**Count**: each, count, piece, dozen

## Common Errors

### "Ingredient not found"
- **Cause**: Recipe references an ingredient slug that doesn't exist
- **Solution**: Import ingredients first, or ensure ingredient slug matches exactly

### "Invalid category"
- **Cause**: Category not in valid list
- **Solution**: Use one of the categories listed above (case-sensitive)

### "Invalid unit"
- **Cause**: Unit type not recognized
- **Solution**: Use one of the valid units listed above

### "Missing required field"
- **Cause**: Required field is null or missing
- **Solution**: Check that name, slug, category are present for ingredients; ingredient_slug, brand for products

## Full Specification

See `docs/design/import_export_specification.md` for the complete v3.4 format documentation.
