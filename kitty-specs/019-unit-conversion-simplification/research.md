# Research: Unit Conversion Simplification

**Feature**: 019-unit-conversion-simplification
**Date**: 2025-12-14

## Current State Analysis

### UnitConversion Model (`src/models/unit_conversion.py`)

**Decision**: DELETE entirely

**Current Structure**:
- Stores explicit conversion records: `from_unit`, `to_unit`, `from_quantity`, `to_quantity`, `notes`
- Foreign key to `ingredient_id`
- Module-level helper functions: `get_conversion()`, `convert_quantity()`, `create_standard_conversions()` (already deprecated)

**Why Removable**:
- `create_standard_conversions()` already returns empty list and is marked DEPRECATED
- `convert_any_units()` in `unit_converter.py` handles all conversions via density
- No unique data - density values on Ingredient can derive same conversions

### Ingredient.recipe_unit Column

**Decision**: DELETE

**Current Usage (40 files reference it)**:
- Used inconsistently across services
- Recipes already declare their own units via `RecipeIngredient.unit`
- Redundant with `RecipeIngredient.unit` which is the actual unit used in recipes

### unit_converter.py (`src/services/unit_converter.py`)

**Decision**: KEEP (with minor cleanup)

**Retained Functions**:
- `convert_standard_units()` - weight↔weight, volume↔volume via base units
- `convert_any_units()` - universal conversion using density from Ingredient.get_density_g_per_ml()
- `convert_volume_to_weight()`, `convert_weight_to_volume()` - density-based cross-type
- Cost calculation utilities
- Standard conversion tables (WEIGHT_TO_GRAMS, VOLUME_TO_ML, COUNT_TO_ITEMS)

**Cleanup Needed**:
- `format_ingredient_conversion()` references `recipe_unit` parameter - rename to generic `target_unit`
- Remove any references to UnitConversion model

### Import/Export Service

**Decision**: UPDATE to v3.3

**Current v3.2 Structure**:
```json
{
  "version": "3.2",
  "ingredients": [...],
  "unit_conversions": [...]  // REMOVE
}
```

**New v3.3 Structure**:
```json
{
  "version": "3.3",
  "ingredients": [...]  // No recipe_unit field
  // No unit_conversions array
}
```

**Changes Required**:
- Remove `unit_conversions` export logic (lines ~1020, 1185, 1325, 1349)
- Remove `unit_conversions` import logic (lines ~2300-2330)
- Update version check from "3.2" to "3.3"
- Remove `recipe_unit` from ingredient export/import

## Files to Modify

| File | Action | Scope |
|------|--------|-------|
| `src/models/unit_conversion.py` | DELETE | Entire file |
| `src/models/__init__.py` | EDIT | Remove UnitConversion import/export |
| `src/models/ingredient.py` | EDIT | Remove `recipe_unit` column, `conversions` relationship |
| `src/services/import_export_service.py` | EDIT | Remove unit_conversions handling, bump version |
| `src/services/unit_converter.py` | EDIT | Rename `recipe_unit` param, remove UnitConversion refs |
| `src/services/ingredient_service.py` | EDIT | Remove UnitConversion references |
| `docs/import_export_specification.md` | EDIT | Update to v3.3 spec |
| `test_data/baking_ingredients_v32.json` | EDIT | Convert to v3.3 format |
| `test_data/sample_data.json` | EDIT | Convert to v3.3 format if applicable |

## Files with recipe_unit References (Assessment Required)

Services needing review:
- `src/services/recipe_service.py`
- `src/services/product_service.py`
- `src/services/inventory_item_service.py`
- `src/services/ingredient_crud_service.py`
- `src/services/finished_unit_service.py`
- `src/services/assembly_service.py`

UI files needing review:
- `src/ui/inventory_tab.py`
- `src/ui/forms/recipe_form.py`
- `src/ui/event_detail_window.py`

Test files: Will need updates to match model changes

## Testing Strategy

**Decision**: Unit tests verify conversion math accuracy (not regression comparison)

**Test Focus**:
1. `convert_any_units()` produces correct results for:
   - Same-type conversions (oz→lb, cup→tbsp)
   - Cross-type conversions using density (cup→oz for flour)
2. Import rejects v3.2 format with clear error
3. Export produces v3.3 format without unit_conversions
4. Cost calculations remain accurate

**Manual Verification**:
- Spot check conversions against known baking references (King Arthur, USDA)

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Cost calculation breaks | Unit tests verify `convert_any_units()` math |
| Old v3.2 files won't import | Clear error message directs user to re-export |
| Missing density causes conversion failure | `convert_any_units()` already handles gracefully with error message |
