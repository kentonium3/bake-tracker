# Research: User-Friendly Ingredient Density Input

**Feature**: 010-user-friendly-ingredient
**Date**: 2025-12-04

## Research Summary

This feature replaces the technical `density_g_per_ml` field with a 4-field model that allows bakers to enter density naturally (e.g., "1 cup = 4.25 oz").

## Decision Log

### Decision 1: Field Names and Types

**Decision**: Use four fields on the Ingredient model:
- `density_volume_value` (Float, nullable)
- `density_volume_unit` (String(20), nullable)
- `density_weight_value` (Float, nullable)
- `density_weight_unit` (String(20), nullable)

**Rationale**:
- Mirrors how bakers naturally express density
- Allows any volume-weight pair (not just cup/oz)
- All nullable to allow ingredients without density

**Alternatives Considered**:
- Single `density_specification` JSON field - rejected due to validation complexity
- Two fields (volume string, weight string) - rejected due to parsing complexity

### Decision 2: Internal Density Calculation

**Decision**: Add `get_density_g_per_ml()` method to Ingredient model that calculates density from the 4 fields.

**Rationale**:
- Keeps conversion logic close to the data
- Existing converter functions can call this method
- Returns None if density not set (clean null handling)

**Implementation**:
```python
def get_density_g_per_ml(self) -> Optional[float]:
    """Calculate density in g/ml from 4-field specification."""
    if not all([self.density_volume_value, self.density_volume_unit,
                self.density_weight_value, self.density_weight_unit]):
        return None

    # Convert volume to ml
    success, ml, _ = convert_standard_units(
        self.density_volume_value, self.density_volume_unit, "ml"
    )
    if not success:
        return None

    # Convert weight to grams
    success, grams, _ = convert_standard_units(
        self.density_weight_value, self.density_weight_unit, "g"
    )
    if not success:
        return None

    return grams / ml if ml > 0 else None
```

### Decision 3: Removing Hardcoded Densities

**Decision**: Remove `INGREDIENT_DENSITIES` dict and `get_ingredient_density()` function from `constants.py`.

**Rationale**:
- User confirmed no fallback behavior wanted
- Hardcoded values have unclear provenance
- Cleaner architecture with single source of truth (ingredient record)

**Impact**:
- `unit_converter.py` must be updated to not call `get_ingredient_density()`
- Conversion functions should accept Ingredient object or explicit density

### Decision 4: Unit Converter Interface Changes

**Decision**: Modify `convert_volume_to_weight()` and `convert_weight_to_volume()` to:
1. Accept optional `ingredient: Ingredient` parameter
2. Use `ingredient.get_density_g_per_ml()` if provided
3. Fall back to `density_override` parameter (for backward compatibility)
4. Remove `ingredient_name` parameter (no more name-based lookup)

**Rationale**:
- Cleaner interface passing the model directly
- Removes dependency on hardcoded constants
- Preserves `density_override` for testing and edge cases

### Decision 5: UI Layout for Density Input

**Decision**: Use horizontal 4-field layout:
```
Density (optional):
[ value ] [ unit v ] = [ value ] [ unit v ]
```

**Components**:
- Two CTkEntry fields for numeric values
- Two CTkComboBox dropdowns for unit selection (VOLUME_UNITS, WEIGHT_UNITS)
- "=" label as visual separator

**Rationale**:
- Matches natural reading order ("1 cup = 4.25 oz")
- Dropdowns prevent invalid unit entry
- Compact single-row layout

### Decision 6: Validation Strategy

**Decision**: All-or-nothing validation for density fields.

**Rules**:
1. If all 4 fields are empty: valid (no density)
2. If all 4 fields are filled with valid data: valid
3. If partially filled: validation error "All density fields must be provided together"
4. Values must be > 0
5. Units must be from VOLUME_UNITS and WEIGHT_UNITS respectively

**Rationale**:
- Prevents incomplete/unusable density data
- Clear error message guides user

### Decision 7: Error Handling When Conversion Unavailable

**Decision**: Show inline warning with "Edit Ingredient" action button.

**Behavior**:
- When recipe needs volume↔weight conversion but ingredient has no density:
  - Display warning: "Density required for conversion"
  - Show button/link: "Edit Ingredient"
  - Do NOT block user from continuing
  - Preserve all form state during navigation

**Rationale**:
- User confirmed this approach
- Non-blocking allows workflow to continue
- Easy fix without losing work

### Decision 8: Import/Export Format

**Decision**: Export all 4 density fields as separate JSON keys under each ingredient.

**Format**:
```json
{
  "slug": "all-purpose-flour",
  "name": "All-Purpose Flour",
  "density_volume_value": 1.0,
  "density_volume_unit": "cup",
  "density_weight_value": 4.25,
  "density_weight_unit": "oz",
  ...
}
```

**Import Behavior**:
- Read all 4 fields if present
- Ignore legacy `density_g_per_ml` field completely
- No automatic conversion of old format

**Rationale**:
- Clean break from legacy format
- User confirmed no backward compatibility needed

## Files Requiring Changes

| File | Change Type | Description |
|------|-------------|-------------|
| `src/models/ingredient.py` | Modify | Replace `density_g_per_ml` with 4 fields, add `get_density_g_per_ml()` |
| `src/utils/constants.py` | Modify | Remove `INGREDIENT_DENSITIES` dict and `get_ingredient_density()` |
| `src/services/unit_converter.py` | Modify | Update conversion functions to use Ingredient object |
| `src/services/ingredient_service.py` | Modify | Handle 4 density fields in create/update |
| `src/services/import_export_service.py` | Modify | Export/import 4 density fields |
| `src/ui/ingredients_tab.py` | Modify | Add 4-field density input UI |
| `test_data/sample_data.json` | Modify | Update format for density fields |
| Tests | Modify | Update tests referencing density |

## Open Items

None - all decisions confirmed during planning.
