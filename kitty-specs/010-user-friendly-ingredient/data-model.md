# Data Model: User-Friendly Ingredient Density Input

**Feature**: 010-user-friendly-ingredient
**Date**: 2025-12-04

## Schema Changes

### Ingredient Model

**Location**: `src/models/ingredient.py`

#### Fields to Remove

```python
# REMOVE THIS:
density_g_per_ml = Column(Float, nullable=True)
```

#### Fields to Add

```python
# ADD THESE (in Physical properties section):
# User-friendly density specification (4-field model)
density_volume_value = Column(Float, nullable=True)  # e.g., 1.0
density_volume_unit = Column(String(20), nullable=True)  # e.g., "cup"
density_weight_value = Column(Float, nullable=True)  # e.g., 4.25
density_weight_unit = Column(String(20), nullable=True)  # e.g., "oz"
```

#### Method to Add

```python
def get_density_g_per_ml(self) -> Optional[float]:
    """
    Calculate density in g/ml from the 4-field specification.

    Returns:
        Density in grams per milliliter, or None if density not specified
        or fields are incomplete/invalid.
    """
    # Check all fields are present
    if not all([
        self.density_volume_value,
        self.density_volume_unit,
        self.density_weight_value,
        self.density_weight_unit
    ]):
        return None

    # Import here to avoid circular dependency
    from src.services.unit_converter import convert_standard_units

    # Convert volume to ml
    success, ml, _ = convert_standard_units(
        self.density_volume_value,
        self.density_volume_unit,
        "ml"
    )
    if not success or ml <= 0:
        return None

    # Convert weight to grams
    success, grams, _ = convert_standard_units(
        self.density_weight_value,
        self.density_weight_unit,
        "g"
    )
    if not success or grams <= 0:
        return None

    return grams / ml
```

### Updated Field Summary

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| density_volume_value | Float | Yes | Volume amount (e.g., 1.0) |
| density_volume_unit | String(20) | Yes | Volume unit (e.g., "cup") |
| density_weight_value | Float | Yes | Weight amount (e.g., 4.25) |
| density_weight_unit | String(20) | Yes | Weight unit (e.g., "oz") |

## Validation Rules

### Density Field Group Validation

The 4 density fields are validated as a group:

1. **All empty**: Valid - ingredient has no density specification
2. **All filled**: Valid if:
   - `density_volume_value > 0`
   - `density_weight_value > 0`
   - `density_volume_unit` is in `VOLUME_UNITS`
   - `density_weight_unit` is in `WEIGHT_UNITS`
3. **Partially filled**: Invalid - error message: "All density fields must be provided together"

### Validation Implementation

```python
def validate_density_fields(
    volume_value: Optional[float],
    volume_unit: Optional[str],
    weight_value: Optional[float],
    weight_unit: Optional[str]
) -> Tuple[bool, str]:
    """
    Validate density field group.

    Returns:
        Tuple of (is_valid, error_message)
    """
    from src.utils.constants import VOLUME_UNITS, WEIGHT_UNITS

    fields = [volume_value, volume_unit, weight_value, weight_unit]
    filled_count = sum(1 for f in fields if f is not None and f != "")

    # All empty is valid
    if filled_count == 0:
        return True, ""

    # Partially filled is invalid
    if filled_count < 4:
        return False, "All density fields must be provided together"

    # All filled - validate values
    if volume_value <= 0:
        return False, "Volume value must be positive"

    if weight_value <= 0:
        return False, "Weight value must be positive"

    if volume_unit.lower() not in [u.lower() for u in VOLUME_UNITS]:
        return False, f"Invalid volume unit: {volume_unit}"

    if weight_unit.lower() not in [u.lower() for u in WEIGHT_UNITS]:
        return False, f"Invalid weight unit: {weight_unit}"

    return True, ""
```

## Import/Export Format

### JSON Structure (per ingredient)

```json
{
  "slug": "all-purpose-flour",
  "name": "All-Purpose Flour",
  "category": "Flour",
  "recipe_unit": "cup",
  "density_volume_value": 1.0,
  "density_volume_unit": "cup",
  "density_weight_value": 4.25,
  "density_weight_unit": "oz",
  "description": null,
  "notes": null
}
```

### Legacy Field Handling

The `density_g_per_ml` field in old exports is **ignored** during import. No automatic conversion is performed.

## Database Migration

**Strategy**: Delete database and reimport

Since this is a breaking schema change and no in-place migration is required:

1. Export existing data (optional - density values will need re-entry anyway)
2. Delete `bake_tracker.db`
3. Restart application (creates fresh schema)
4. Import data (density fields will be null)
5. User enters density values in new format

## Relationships

No relationship changes. The density fields are standalone attributes on the Ingredient model.

## Constants Changes

### Remove from `src/utils/constants.py`

```python
# REMOVE ENTIRE SECTION:
# ============================================================================
# Ingredient Density Data (for volume-to-weight conversions)
# ============================================================================

INGREDIENT_DENSITIES: Dict[str, float] = {
    # ... ~60 entries ...
}

def get_ingredient_density(ingredient_name: str) -> float:
    # ... function body ...
```

These are replaced by the per-ingredient density specification.
