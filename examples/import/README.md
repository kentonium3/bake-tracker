# Import Examples

This directory contains example import files for the Seasonal Baking Tracker application.

## File Descriptions

### Simple Examples

- **`simple_ingredients.json`** - Contains 5 basic ingredients (flour, sugar, butter, chocolate chips, vanilla)
  - Good for: Learning the format, quick testing
  - Use: Import this first to populate basic pantry items

- **`simple_recipes.json`** - Contains 3 cookie recipes (chocolate chip, sugar, double chocolate)
  - Good for: Testing recipe imports
  - Requirement: Import `simple_ingredients.json` first (recipes reference these ingredients)

### Combined Example

- **`combined_import.json`** - Single file with both ingredients (3) and recipes (1)
  - Good for: One-step import, understanding relationships
  - Use: All-in-one testing

### Testing Files

- **`test_errors.json`** - Contains intentional errors for validation testing
  - Good for: Testing error handling, validation logic
  - Warning: Most records will fail to import (by design)

### Template

- **`../templates/import_template.json`** - Empty template with placeholder values
  - Good for: Creating new import files, AI generation prompts
  - Use: Copy and fill in with your data

## Usage

### Option 1: Using the Application (When Implemented)

1. Launch the Seasonal Baking Tracker application
2. Navigate to **File → Import → Import All**
3. Select one of these example files
4. Review the import preview
5. Confirm the import

### Option 2: For Testing/Development

```python
from src.services import inventory_service, recipe_service
import json

# Load and import ingredients
with open('examples/import/simple_ingredients.json', 'r') as f:
    data = json.load(f)
    # Import logic here (when implemented)

# Load and import recipes
with open('examples/import/simple_recipes.json', 'r') as f:
    data = json.load(f)
    # Import logic here (when implemented)
```

## Import Order

**Important**: When importing recipes, ensure their ingredients exist first.

Recommended order:
1. Import ingredients first (`simple_ingredients.json`)
2. Then import recipes (`simple_recipes.json`)

Or use `combined_import.json` which handles dependencies automatically.

## Creating Your Own Import Files

### Using AI Tools

You can ask AI tools like ChatGPT, Claude, or GitHub Copilot to generate import files:

**Example Prompt:**
```
Generate a JSON import file for a baking tracker application using this format:
[paste template from import_template.json]

Create 10 common baking ingredients with:
- Realistic US market brands (Costco, King Arthur, etc.)
- Bulk purchase quantities and costs
- Valid categories: Flour, Sugar, Dairy, Oils/Butters, Chocolate/Candies, Nuts, Spices

Include 3 cookie recipes using those ingredients.
```

### Manual Creation

1. Copy `../templates/import_template.json`
2. Replace placeholder values with your data
3. Validate against the specification (see `docs/import_export_specification.md`)
4. Test with small file first

## Field Reference

### Ingredient Categories (Valid Values)
- Flour
- Sugar
- Dairy
- Oils/Butters
- Nuts
- Spices
- Chocolate/Candies
- Cocoa Powders
- Dried Fruits
- Extracts
- Syrups
- Alcohol
- Misc

### Recipe Categories (Valid Values)
- Cookies
- Cakes
- Candies
- Bars
- Brownies
- Breads
- Pastries
- Pies
- Tarts
- Other

### Valid Units

**Weight**: oz, lb, g, kg
**Volume**: tsp, tbsp, cup, ml, l, fl oz, pt, qt, gal
**Count**: each, count, piece, dozen
**Package**: bag, box, bar, bottle, can, jar, packet, container, package, case

## Common Errors

### "Ingredient not found"
- **Cause**: Recipe references an ingredient that doesn't exist
- **Solution**: Import ingredients first, or ensure ingredient name/brand match exactly

### "Invalid category"
- **Cause**: Category not in valid list
- **Solution**: Use one of the categories listed above (case-sensitive)

### "Invalid unit"
- **Cause**: Unit type not recognized
- **Solution**: Use one of the valid units listed above

### "Missing required field"
- **Cause**: Required field is null or missing
- **Solution**: Check that name, category, purchase_quantity, purchase_unit, quantity, unit_cost are all present

## Sample Data Sets

Want more examples? Check these resources:

- **King Arthur Baking**: Common ingredient equivalents and measurements
- **Costco Ingredient Lists**: Realistic bulk pricing and package sizes
- **Classic Recipe Collections**: Public domain recipe books for recipe ideas

## Need Help?

See the full specification: `docs/import_export_specification.md`
