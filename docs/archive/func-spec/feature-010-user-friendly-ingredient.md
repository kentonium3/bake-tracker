# Feature 012: User-Friendly Density Input

**Created:** 2025-12-04
**Status:** Ready for Implementation
**Priority:** HIGH

---

## Problem Statement

The current density handling requires users to enter density_g_per_ml values (e.g., 0.507 for flour), which:
- Requires metric conversion knowledge
- Is unintuitive for home bakers
- Falls back to hardcoded INGREDIENT_DENSITIES dict when not provided

A previous implementation used 4 intuitive fields that allowed entry like 1 cup = 4.5 oz, which is how bakers naturally think about ingredient weights.

---

## Solution: 4-Field Density Model

Replace single density_g_per_ml with:

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| density_volume_value | Float | 1.0 | Volume amount |
| density_volume_unit | String | cup | Volume unit |
| density_weight_value | Float | 4.25 | Weight amount |
| density_weight_unit | String | oz | Weight unit |

**User enters:** 1 cup of flour weighs 4.25 oz
**System calculates:** density in standard units for internal conversions

---

## Current State Analysis

### Ingredient Model (src/models/ingredient.py)
- density_g_per_ml = Column(Float, nullable=True)

### Unit Converter (src/services/unit_converter.py)
- convert_volume_to_weight() - uses density_g_per_cup from constants or override
- convert_weight_to_volume() - uses density_g_per_cup from constants or override
- convert_any_units() - handles cross-type conversions

### Constants (src/utils/constants.py)
- INGREDIENT_DENSITIES dict with ~60 hardcoded g/cup values
- get_ingredient_density() function for name-based lookup

---

## Implementation Tasks

### Task 1: Model Changes (src/models/ingredient.py)

Remove:
- density_g_per_ml

Add:
- density_volume_value = Column(Float, nullable=True)
- density_volume_unit = Column(String(20), nullable=True)
- density_weight_value = Column(Float, nullable=True)
- density_weight_unit = Column(String(20), nullable=True)

Add method:
- get_density_g_per_ml() - Calculate density from 4-field specification

### Task 2: Density Calculator Utility

Create helper in src/services/unit_converter.py:

calculate_density_g_per_ml(volume_value, volume_unit, weight_value, weight_unit)
- Calculate density in g/ml from user-provided volume/weight pair
- Example: (1, cup, 4.25, oz) -> 0.507 g/ml
- Returns: Tuple of (success, density_g_per_ml, error_message)

format_density_for_display(density_g_per_ml, preferred_volume_unit, preferred_weight_unit)
- Format density for user display
- Example: 0.507 g/ml -> 1 cup = 4.25 oz

### Task 3: Update Unit Converter Integration

Modify convert_volume_to_weight() and convert_weight_to_volume() to:
1. Accept Ingredient object directly (preferred)
2. Call ingredient.get_density_g_per_ml()
3. Fall back to INGREDIENT_DENSITIES if no density specified

### Task 4: UI Changes (src/ui/ingredients_tab.py)

Replace density_g_per_ml input with 4-field layout:

Density (optional):
[ value ] [ unit v ] = [ value ] [ unit v ]

Components:
- volume_value: CTkEntry (float)
- volume_unit: CTkComboBox (VOLUME_UNITS)
- weight_value: CTkEntry (float)
- weight_unit: CTkComboBox (WEIGHT_UNITS)
- = label between pairs

Validation:
- All 4 fields required if any is filled
- volume_value and weight_value must be positive
- Show calculated g/ml as read-only hint (optional)

### Task 5: Service Layer (src/services/ingredient_service.py)

Update create/update methods:
- Accept 4 density fields
- Validate as a group (all or none)
- Store in model

### Task 6: Import/Export Support

Update sample_data.json format for ingredients:
- density_volume_value: 1.0
- density_volume_unit: cup
- density_weight_value: 4.25
- density_weight_unit: oz

Update import_export_service.py:
- Export: Include 4 density fields
- Import: Read 4 fields, support legacy density_g_per_ml for backward compatibility

### Task 7: Update Constants (Optional)

Keep INGREDIENT_DENSITIES as g/cup for simpler fallback (less work).
The lookup functions can convert on the fly when needed.

---

## Validation Rules

1. Density fields are optional (some ingredients do not need volume/weight conversion)
2. If any density field is provided, all 4 must be provided
3. Volume units must be valid VOLUME_UNITS
4. Weight units must be valid WEIGHT_UNITS
5. Both values must be positive (> 0)

---

## Migration Strategy

1. Export existing data
2. Update models (add 4 fields, remove density_g_per_ml)
3. Update sample_data.json with new field format
4. Delete database
5. Restart app
6. Reimport data

---

## Testing Checklist

- [ ] Create ingredient with density 1 cup = 4.25 oz
- [ ] Verify density stored correctly in database
- [ ] Recipe cost calculation uses density for volume-to-weight conversion
- [ ] Import/export round-trips density correctly
- [ ] UI displays density in user-friendly format
- [ ] Ingredients without density still work (no conversion available)
- [ ] Legacy INGREDIENT_DENSITIES fallback works

---

## Files to Modify

| File | Changes |
|------|---------|
| src/models/ingredient.py | Replace density_g_per_ml with 4 fields, add get_density_g_per_ml() |
| src/services/unit_converter.py | Add calculate_density_g_per_ml(), update conversion functions |
| src/services/ingredient_service.py | Handle 4 density fields in create/update |
| src/services/import_export_service.py | Export/import 4 density fields |
| src/ui/ingredients_tab.py | UI for 4-field density input |
| src/utils/constants.py | Optional: update INGREDIENT_DENSITIES format |
| test_data/sample_data.json | Update ingredient records with new fields |

---

## Open Questions

1. Should we convert existing INGREDIENT_DENSITIES to 4-field format, or keep g/cup for simpler fallback?
   - Recommendation: Keep g/cup for fallback, calculate on the fly when needed

2. Display format preference?
   - Recommendation: 1 cup = 4.25 oz (more natural for bakers)
