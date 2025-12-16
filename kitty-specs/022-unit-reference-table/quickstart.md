# Quickstart: Unit Reference Table & UI Dropdowns

**Feature**: 022-unit-reference-table
**Date**: 2025-12-16

## Overview

This feature adds a database-backed unit reference table and replaces free-form unit text entry with dropdown selection in UI forms.

## What Gets Built

1. **New Model**: `src/models/unit.py` - Unit reference table
2. **New Service**: `src/services/unit_service.py` - Helper functions for querying units
3. **Modified**: `src/services/database.py` - Add unit seeding to initialization
4. **Modified**: `src/ui/forms/ingredient_form.py` - Use unit dropdowns
5. **Modified**: `src/ui/forms/recipe_form.py` - Use unit dropdown for RecipeIngredient
6. **New Tests**: Unit model and seeding tests

## Implementation Order

### Phase 1: Model & Seeding
1. Create `src/models/unit.py` with Unit class
2. Update `src/models/__init__.py` to export Unit
3. Add `seed_units()` function to database.py
4. Call seed_units() in init_database()
5. Write tests for Unit model and seeding

### Phase 2: Service Layer
1. Create `src/services/unit_service.py` with helper functions:
   - `get_all_units()` - all units
   - `get_units_by_category(category)` - filter by category
   - `get_units_for_dropdown(categories)` - formatted for CTkComboBox

### Phase 3: UI Integration
1. Modify ingredient_form.py:
   - Replace density_volume_unit text with dropdown (VOLUME only)
   - Replace density_weight_unit text with dropdown (WEIGHT only)
2. Modify recipe_form.py:
   - Replace RecipeIngredient unit with dropdown (WEIGHT + VOLUME + COUNT)
3. Test all forms work correctly

## Key Code Patterns

### Unit Model
```python
class Unit(BaseModel):
    __tablename__ = "units"

    code = Column(String(20), unique=True, nullable=False, index=True)
    display_name = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False)
    category = Column(String(20), nullable=False, index=True)
    un_cefact_code = Column(String(10), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
```

### Dropdown Values with Category Headers
```python
def get_units_for_dropdown(categories: List[str]) -> List[str]:
    """Return unit codes with category headers for CTkComboBox."""
    values = []
    for category in categories:
        values.append(f"-- {category.title()} --")
        units = get_units_by_category(category)
        values.extend([u.code for u in units])
    return values
```

### Seeding Pattern
```python
def seed_units():
    """Seed unit reference table if empty."""
    with session_scope() as session:
        if session.query(Unit).count() == 0:
            # Seed from constants.py
            ...
```

## Testing Checklist

- [ ] Unit model creates correctly
- [ ] Seeding populates all 27 units
- [ ] Seeding is idempotent (no duplicates on restart)
- [ ] get_units_by_category returns correct units
- [ ] Dropdowns display with category headers
- [ ] Selected unit is stored correctly
- [ ] Existing data with valid units still works
- [ ] All existing tests pass

## Acceptance Criteria Reference

From spec.md:
- SC-001: Users can select units in <3 seconds
- SC-002: Zero unit entry errors via UI
- SC-003: 100% existing valid data unchanged
- SC-004: All 27 units available in appropriate dropdowns
- SC-005: All existing tests pass
- SC-006: Import/export unchanged
