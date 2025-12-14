# Implementation Plan: Unit Conversion Simplification

**Branch**: `019-unit-conversion-simplification` | **Date**: 2025-12-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/019-unit-conversion-simplification/spec.md`

## Summary

Remove redundant unit conversion mechanisms (`Ingredient.recipe_unit` column and `UnitConversion` model/table) while retaining the 4-field density specification on Ingredient as the canonical source for all unit conversions. This simplifies the data model and import/export format (v3.2 → v3.3).

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter, pytest
**Storage**: SQLite with WAL mode
**Testing**: pytest (unit tests verify conversion math accuracy)
**Target Platform**: Desktop (Windows/macOS)
**Project Type**: Single desktop application
**Performance Goals**: N/A (refactoring, no new performance requirements)
**Constraints**: Must use export/reset/import workflow per Constitution VI
**Scale/Scope**: Single user, ~160 ingredients in catalog

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | ✅ PASS | Simplifies data entry (no separate conversion records) |
| II. Data Integrity & FIFO | ✅ PASS | Density-based conversions remain accurate |
| III. Future-Proof Schema | ✅ PASS | Removes vestigial complexity, cleaner model |
| IV. Test-Driven Development | ✅ PASS | Unit tests will verify conversion math accuracy |
| V. Layered Architecture | ✅ PASS | No architecture changes, just model simplification |
| VI. Migration Safety | ✅ PASS | Using export/reset/import workflow (no migration scripts) |
| VII. Desktop Phase | ✅ PASS | Does not block web deployment |

**Web Migration Cost**: LOW - Cleaner model is easier to expose via API

## Project Structure

### Documentation (this feature)

```
kitty-specs/019-unit-conversion-simplification/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 research findings
├── checklists/          # Quality checklists
│   └── requirements.md
└── tasks.md             # Task tracking (created by /spec-kitty.tasks)
```

### Source Code (affected files)

```
src/
├── models/
│   ├── __init__.py          # Remove UnitConversion export
│   ├── ingredient.py        # Remove recipe_unit, conversions relationship
│   └── unit_conversion.py   # DELETE entire file
├── services/
│   ├── import_export_service.py  # Remove unit_conversions handling, v3.3
│   ├── unit_converter.py         # Minor cleanup (recipe_unit param rename)
│   ├── ingredient_service.py     # Remove UnitConversion references
│   └── [other services]          # Review recipe_unit references
└── tests/
    └── [various]                 # Update for model changes
```

**Structure Decision**: Existing single-project structure maintained. This is a refactoring feature that removes code, not adds it.

## Complexity Tracking

*No violations - this feature simplifies the codebase*

## Implementation Phases

### Phase 1: Model & Schema Changes

**Goal**: Remove UnitConversion model and recipe_unit column

**Tasks**:
1. Delete `src/models/unit_conversion.py`
2. Update `src/models/__init__.py` - remove UnitConversion import/export
3. Update `src/models/ingredient.py`:
   - Remove `recipe_unit` column
   - Remove `conversions` relationship
4. Update any models that import/reference UnitConversion

**Validation**: Application starts without import errors

### Phase 2: Service Layer Updates

**Goal**: Remove all references to deleted model/column

**Tasks**:
1. Update `src/services/import_export_service.py`:
   - Remove `unit_conversions` export logic
   - Remove `unit_conversions` import logic
   - Update version check "3.2" → "3.3"
   - Remove `recipe_unit` from ingredient export/import
2. Update `src/services/unit_converter.py`:
   - Rename `recipe_unit` parameter to `target_unit` in `format_ingredient_conversion()`
   - Remove any UnitConversion model references
3. Update `src/services/ingredient_service.py`:
   - Remove UnitConversion references
4. Review and update all services referencing `recipe_unit`:
   - `recipe_service.py`
   - `product_service.py`
   - `inventory_item_service.py`
   - `ingredient_crud_service.py`
   - `finished_unit_service.py`
   - `assembly_service.py`

**Validation**: All services pass linting, no undefined references

### Phase 3: Test Updates

**Goal**: Update tests for model changes, add conversion accuracy tests

**Tasks**:
1. Remove/update tests for UnitConversion model
2. Update ingredient-related tests (remove recipe_unit expectations)
3. Add/verify unit tests for `convert_any_units()` accuracy:
   - Same-type conversions (oz→lb, cup→tbsp)
   - Cross-type conversions using density (cup→oz for flour)
4. Update import/export tests for v3.3 format
5. Add test for v3.2 import rejection

**Validation**: `pytest src/tests -v` passes with >70% coverage on affected services

### Phase 4: Test Data & Documentation

**Goal**: Update all data files and documentation

**Tasks**:
1. Convert `test_data/baking_ingredients_v32.json` to v3.3:
   - Remove `unit_conversions` array
   - Remove `recipe_unit` from ingredient objects
   - Update version to "3.3"
2. Update `test_data/sample_data.json` if applicable
3. Update `docs/import_export_specification.md` to v3.3
4. Update `docs/feature_proposal_catalog_import.md` - remove UnitConversion references
5. Update `docs/catalog_import_status.md` - note format change

**Validation**: JSON files parse correctly, documentation is consistent

### Phase 5: UI Cleanup (if needed)

**Goal**: Remove any UI references to recipe_unit

**Tasks** (assess each):
1. Review `src/ui/inventory_tab.py`
2. Review `src/ui/forms/recipe_form.py`
3. Review `src/ui/event_detail_window.py`

**Validation**: Application runs without UI errors

## Schema Change Workflow

Per Constitution VI, using export/reset/import:

1. **Before code changes**: Export current database via existing v3.2 export
2. **Make code changes**: Delete model, update services
3. **Reset database**: Delete and recreate SQLite file
4. **Transform exported data**: Remove unit_conversions, recipe_unit from JSON
5. **Import transformed data**: Use v3.3 import

**Note**: For this feature, step 4 (transform) can be done manually or via script since we're only removing fields, not migrating data.

## Key Files Reference

| File | Lines of Interest | Change Type |
|------|-------------------|-------------|
| `src/models/unit_conversion.py` | All | DELETE |
| `src/models/ingredient.py` | ~64 (recipe_unit), ~100 (conversions) | EDIT |
| `src/models/__init__.py` | UnitConversion import | EDIT |
| `src/services/import_export_service.py` | ~24, 978-1185, 2300-2330 | EDIT |
| `src/services/unit_converter.py` | ~392-410 | EDIT |

## Success Criteria Checklist

- [ ] `UnitConversion` model deleted, no import errors
- [ ] `recipe_unit` column removed from Ingredient
- [ ] Import/export uses v3.3 format
- [ ] v3.2 import rejected with clear error
- [ ] All tests pass
- [ ] Test coverage >70% on affected services
- [ ] Test data files updated to v3.3
- [ ] Documentation updated
