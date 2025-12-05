# Implementation Plan: User-Friendly Ingredient Density Input

**Branch**: `010-user-friendly-ingredient` | **Date**: 2025-12-04 | **Spec**: [spec.md](spec.md)

## Summary

Replace the technical `density_g_per_ml` field on ingredients with a 4-field model that allows bakers to enter density naturally (e.g., "1 cup = 4.25 oz"). Remove hardcoded `INGREDIENT_DENSITIES` fallback - if an ingredient has no density set, volume↔weight conversion is unavailable with a user-friendly warning and easy navigation to fix.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter
**Storage**: SQLite with WAL mode
**Testing**: pytest with >70% service coverage target
**Target Platform**: macOS/Windows desktop
**Project Type**: Single desktop application
**Performance Goals**: N/A (UI responsiveness only)
**Constraints**: Non-technical primary user, intuitive UI required
**Scale/Scope**: Single-user, ~100 ingredients max

## Constitution Check

*GATE: Verified before Phase 0 research.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Layered Architecture | PASS | UI→Services→Models flow maintained |
| II. Build for Today | PASS | No over-engineering; solves actual user need |
| III. FIFO Accuracy | N/A | Density doesn't affect FIFO |
| IV. User-Centric Design | PASS | Natural input format, clear errors |
| V. Test-Driven Development | PENDING | Tests required for new validation logic |
| VI. Migration Safety | PASS | Using delete+reimport strategy (user confirmed) |

## Project Structure

### Documentation (this feature)

```
kitty-specs/010-user-friendly-ingredient/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Decision log
├── data-model.md        # Schema changes
├── quickstart.md        # Code examples
└── tasks.md             # Work packages (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   └── ingredient.py        # MODIFY: Replace density field, add method
├── services/
│   ├── unit_converter.py    # MODIFY: Update conversion functions
│   ├── ingredient_service.py # MODIFY: Add density validation
│   └── import_export_service.py # MODIFY: Handle 4 density fields
├── ui/
│   └── ingredients_tab.py   # MODIFY: Add 4-field density input
└── utils/
    └── constants.py         # MODIFY: Remove INGREDIENT_DENSITIES

src/tests/
├── services/
│   ├── test_unit_converter.py    # MODIFY: Update density tests
│   └── test_ingredient_service.py # ADD: Density validation tests
└── models/
    └── test_ingredient.py        # ADD: get_density_g_per_ml tests

test_data/
└── sample_data.json             # MODIFY: Update density format
```

**Structure Decision**: Single project structure (existing), modifications only.

## Implementation Phases

### Phase 1: Model & Constants (Foundation)

**Objective**: Update Ingredient model and remove hardcoded densities

1. **Modify `src/models/ingredient.py`**:
   - Remove `density_g_per_ml` field
   - Add 4 density fields
   - Add `get_density_g_per_ml()` method
   - Add `format_density_display()` method

2. **Modify `src/utils/constants.py`**:
   - Remove `INGREDIENT_DENSITIES` dict (~60 entries)
   - Remove `get_ingredient_density()` function

3. **Tests**:
   - Test `get_density_g_per_ml()` calculation
   - Test with all fields set
   - Test with no fields set
   - Test with partial fields (should return None)

### Phase 2: Service Layer

**Objective**: Update unit converter and ingredient service

1. **Modify `src/services/unit_converter.py`**:
   - Update `convert_volume_to_weight()` to accept `ingredient` parameter
   - Update `convert_weight_to_volume()` to accept `ingredient` parameter
   - Update `convert_any_units()` similarly
   - Remove import of `get_ingredient_density`
   - User-friendly error message when density unavailable

2. **Modify `src/services/ingredient_service.py`**:
   - Add `validate_density_fields()` function
   - Update `create_ingredient()` to accept/validate 4 fields
   - Update `update_ingredient()` to accept/validate 4 fields

3. **Tests**:
   - Test conversion with ingredient having density
   - Test conversion with ingredient lacking density (expect failure with message)
   - Test density validation (all-or-nothing)
   - Test positive value validation
   - Test unit type validation

### Phase 3: Import/Export

**Objective**: Handle density in data import/export

1. **Modify `src/services/import_export_service.py`**:
   - Update `export_ingredients_to_json()` to include 4 density fields
   - Update `import_ingredients_from_json()` to read 4 density fields
   - Ignore legacy `density_g_per_ml` field on import

2. **Modify `test_data/sample_data.json`**:
   - Update ingredient records with new density format
   - Remove any `density_g_per_ml` fields

3. **Tests**:
   - Test export includes density fields
   - Test import reads density fields
   - Test import ignores legacy field

### Phase 4: UI Layer

**Objective**: Add 4-field density input to ingredients tab

1. **Modify `src/ui/ingredients_tab.py`**:
   - Create density input frame with 4 fields
   - Volume value entry + volume unit dropdown
   - "=" label
   - Weight value entry + weight unit dropdown
   - Help text example
   - Wire to service layer

2. **Add density warning in recipe UI** (if conversion fails):
   - Inline warning message
   - "Edit Ingredient" button
   - Form state preservation

3. **Manual Testing**:
   - Create ingredient with density
   - Edit ingredient density
   - Clear density (all fields empty)
   - Partial field validation
   - Recipe cost calculation with/without density

## Dependencies & Order

```
Phase 1 (Model/Constants)
    ↓
Phase 2 (Services)
    ↓
Phase 3 (Import/Export)
    ↓
Phase 4 (UI)
```

Each phase depends on the previous. Phase 1 must complete before Phase 2 can start.

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Circular import (model → converter) | Use local import in method |
| Existing tests break | Update tests as part of each phase |
| User data loss | Using delete+reimport migration (user aware) |
| Conversion errors in recipes | Clear warning message + easy fix path |

## Complexity Tracking

*No constitution violations requiring justification.*

## Definition of Done

- [ ] `density_g_per_ml` field removed from Ingredient model
- [ ] 4 density fields added to Ingredient model
- [ ] `get_density_g_per_ml()` method implemented and tested
- [ ] `INGREDIENT_DENSITIES` dict removed from constants
- [ ] Unit converter uses Ingredient object for density
- [ ] Density validation (all-or-nothing) implemented
- [ ] Import/export handles 4 density fields
- [ ] Legacy `density_g_per_ml` ignored on import
- [ ] UI shows 4-field density input
- [ ] Warning shown when conversion unavailable
- [ ] All existing tests updated and passing
- [ ] New tests for density functionality passing
- [ ] sample_data.json updated to new format
