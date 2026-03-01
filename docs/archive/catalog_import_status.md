# Ingredient Catalog Import - Status & Next Steps

**Last updated:** 2025-12-14
**Status:** BLOCKED - awaiting feature 019 (unit simplification)

## Goal

Import a comprehensive baking ingredient catalog (~160 ingredients) into bake-tracker to provide a solid foundation for recipe creation and inventory management.

## Current Artifacts

| File | Description |
|------|-------------|
| `test_data/baking_ingredients_v32.json` | Main catalog file (v3.2 format) |
| `docs/research/Pantry_Inventory_-_Marianne_-_2025.csv` | Reference: Marianne's actual pantry |
| `docs/research/claude_ingredient_chat_cont.md` | Claude conversation that generated the catalog |

## Validation Results (2025-12-14)

The catalog file has been validated and is structurally ready:

| Check | Result |
|-------|--------|
| JSON parses correctly | ✅ |
| Version matches importer (3.2) | ✅ |
| Total ingredients | **160** |
| All have required fields (`slug`, `display_name`, `category`) | ✅ |
| All have 4-field density format | ✅ 160/160 |
| Unit conversions | **69** (see gap below) |

### Categories (12)

Alcohol, Chocolate/Candies, Cocoa Powders, Dried Fruits, Extracts, Flour, Misc, Nuts, Oils/Butters, Spices, Sugar, Syrups

## Known Gap: Unit Conversions

**91 ingredients** lack unit conversions. These need to be generated before import:

- **Alcohol (15)**: Amaretto, Bourbon, Brandy, Chambord, Crème de Cassis, Dark Rum, Frangelico, Gold Rum, Grand Marnier, Irish Whiskey, Kahlúa, Kirsch, Peach Schnapps, Triple Sec, White Rum
- **Chocolate/Candies (11)**: Bittersweet Baking Chocolate, Candy Melts, Caramels, Cinnamon Chips, Couverture (Dark/Milk/White), Espresso Chips, Ruby Chocolate, Toffee Bits, Unsweetened Baking Chocolate
- **Dried Fruits (7)**: Crystallized Ginger, Dates, Dried Apricots, Freeze-Dried Berries (3 types), Uncrystallized Ginger
- **Extracts (13)**: All extract types (almond, vanilla, lemon, etc.) and Vanilla Bean Paste
- **Misc (23)**: Yeasts, eggs, leaveners, specialty items (Nutella, Biscoff, etc.)
- **Spices (18)**: Ground spices, salts, whole spices, vanilla beans
- **Sugar (3)**: Muscovado, Swerve, Vanilla Sugar
- **Syrups (1)**: Coffee Syrup

### Conversion patterns to apply

| Category | Pattern |
|----------|---------|
| Liquids (alcohol, syrups) | 8 fl_oz = 1 cup |
| Extracts | 3 tsp = 1 tbsp |
| Spices | oz to tsp based on density |
| Chocolates | oz to cup by form (chips, bars, etc.) |
| Eggs | each to tbsp equivalents |
| Dried fruits | lb to cup by type |

## Blocker: Feature 019

**The density/unit model is being refactored in feature 019** (`docs/feature_019_unit_simplification.md`).

This refactoring may change:
- How density is stored (4-field format may change)
- How unit conversions work
- The import format for ingredients

**Do not proceed with catalog import until feature 019 is complete.**

## Resume Checklist

When ready to continue:

1. [ ] Verify feature 019 is merged to main
2. [ ] Check if `baking_ingredients_v32.json` format needs updating for new density model
3. [ ] Generate unit conversions for the 91 missing ingredients
4. [ ] Re-validate the updated catalog file
5. [ ] Import via `import_all_from_json_v3('test_data/baking_ingredients_v32.json', mode='merge')`
6. [ ] Verify import results in application

## Import Command

Once ready:

```python
from src.services.import_export_service import import_all_from_json_v3
result = import_all_from_json_v3('test_data/baking_ingredients_v32.json', mode='merge')
print(result)
```
