# Export Script Status - v0.4.0 Update

## Summary

The database export script (`src/services/import_export_service.py`) has been partially updated for v0.4.0 architecture compatibility.

## Changes Made

### ✅ Added Model Imports
```python
from src.models.pantry_item import PantryItem
from src.models.purchase import Purchase
from src.models.unit_conversion import UnitConversion
```

### ✅ Updated Export Data Structure
Added new sections to `export_all_to_json()`:
- `pantry_items` - Actual inventory lots
- `purchases` - Price history
- `unit_conversions` - Custom unit conversions

### ✅ Added Export Logic
- Pantry items export (lines ~686-708)
- Purchases export (lines ~710-730)
- Unit conversions export (lines ~732-748)

### ✅ Updated Total Records Calculation
Includes counts from new tables in the final record count.

## Known Issue

**SQLAlchemy Session Error:**
```
Parent instance <RecipeIngredient> is not bound to a Session;
lazy load operation of attribute 'ingredient_new' cannot proceed
```

**Root Cause:** Recipe ingredients are being accessed outside of the session scope, causing lazy-loading failures.

**Impact:** Export fails when trying to export recipes with ingredients.

## Fix Needed

The recipe export section (around line 686-718) needs to use proper eager loading:

```python
# Current (broken):
recipes = recipe_service.get_all_recipes()

# Need to change to:
with session_scope() as session:
    recipes = session.query(Recipe).options(
        joinedload(Recipe.recipe_ingredients).joinedload(RecipeIngredient.ingredient_new)
    ).all()
    # Force load all relationships before leaving session
    for recipe in recipes:
        _ = recipe.recipe_ingredients
        for ri in recipe.recipe_ingredients:
            _ = ri.ingredient_new
```

## Workaround

Until the session issue is fixed, you can:

1. **Export individual sections** using the specific export functions:
   - `export_ingredients_to_json()` (may use old schema)
   - `export_recipes_to_json()` (may work)
   - etc.

2. **Use the load_test_data.py script** for importing, which is fully compatible with v0.4.0

## Test Data Export

The current database can be manually exported using:
```bash
# NOTE: This will currently fail due to session issue
cd bake-tracker
python -c "from src.services.import_export_service import export_all_to_json; export_all_to_json('backup.json')"
```

## Recommended Next Steps

1. Fix the SQLAlchemy session handling in `export_all_to_json()`
2. Add eager loading for all relationships
3. Test export with current database
4. Verify import/export round-trip works correctly

## Files Modified

- `src/services/import_export_service.py` (lines 19-21, 600-612, 686-748, 880-884)

## Related Documentation

- `INTEGRATION_GUIDE.md` - v0.4.0 architecture documentation
- `src/utils/load_test_data.py` - Import script (fully working)
- `examples/test_data_v2.json` - Sample test data for v0.4.0
