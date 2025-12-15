# Feature 019: Unit Conversion Simplification

**Status:** Ready for spec-kitty.specify
**Created:** 2025-12-14
**Priority:** HIGH (blocks import format finalization)

---

## Problem Statement

The current architecture has redundant unit conversion mechanisms:

1. **Ingredient.recipe_unit** - A field intended to specify the "target" unit for recipes, but recipes already declare their own units in RecipeIngredient.unit, making this redundant.

2. **UnitConversion table** - Stores explicit "1 lb = 3.6 cups" conversion records per ingredient, but these values can be dynamically derived from the 4-field density specification on Ingredient.

3. **4-field density on Ingredient** - The canonical source: `density_volume_value`, `density_volume_unit`, `density_weight_value`, `density_weight_unit` (e.g., "1 cup = 4.25 oz").

With the 4-field density model, both `recipe_unit` and `UnitConversion` are vestigial complexity from earlier architecture iterations.

---

## Proposed Solution

### Remove:
1. `Ingredient.recipe_unit` column
2. `UnitConversion` model and table entirely
3. Related service methods in `unit_conversion.py`
4. `unit_conversions` array from import/export JSON format

### Keep:
1. 4-field density specification on Ingredient (canonical source)
2. `get_density_g_per_ml()` method for internal calculations
3. `convert_any_units()` for dynamic cross-type conversions
4. Standard unit conversion tables (weight↔weight, volume↔volume)

### Impact on Other Systems:

**Import/Export (v3.2 → v3.3):**
- Remove `unit_conversions` array from schema
- Remove `recipe_unit` from ingredient records
- Breaking change to format version

**Catalog Import Proposal:**
- Update `/docs/feature_proposal_catalog_import.md` to remove UnitConversion handling
- Simplifies proposal scope

**Cost Calculation:**
- No change - already uses density-based conversion via `convert_any_units()`

---

## User Stories

**US-1:** As a developer, I want to remove redundant conversion mechanisms so the codebase is simpler to understand and maintain.

**US-2:** As a user entering ingredient data, I only need to provide the 4 density values (1 cup = X oz), not maintain separate conversion records.

**US-3:** As an AI generating ingredient catalogs, I only need to provide density values, simplifying the data format.

---

## Acceptance Criteria

1. **AC-1:** `Ingredient.recipe_unit` column removed from model and database
2. **AC-2:** `UnitConversion` model deleted, table dropped
3. **AC-3:** Import/export format v3.3 has no `unit_conversions` array
4. **AC-4:** All existing tests pass (or are updated appropriately)
5. **AC-5:** Cost calculations produce identical results (regression test)
6. **AC-6:** `feature_proposal_catalog_import.md` updated to remove UnitConversion references
7. **AC-7:** `baking_ingredients_v32.json` test data converted to v3.3 format (remove unit_conversions)

---

## Technical Approach

### Schema Change (via export/reset/import per Constitution VI)

1. Export current database state
2. Remove `recipe_unit` from Ingredient model
3. Delete UnitConversion model file
4. Update `__init__.py` imports
5. Reset database (delete and recreate)
6. Transform exported JSON (remove unit_conversions, recipe_unit)
7. Import transformed data

### Files to Modify

| File | Change |
|------|--------|
| `src/models/ingredient.py` | Remove `recipe_unit` column |
| `src/models/unit_conversion.py` | DELETE entire file |
| `src/models/__init__.py` | Remove UnitConversion import/export |
| `src/services/unit_converter.py` | Remove deprecated functions, update docstrings |
| `src/services/import_export_service.py` | Remove unit_conversions handling |
| `docs/import_export_specification.md` | Update to v3.3, remove unit_conversions section |
| `docs/feature_proposal_catalog_import.md` | Remove UnitConversion references |
| `test_data/baking_ingredients_v32.json` | Convert to v3.3 format |
| `test_data/sample_data.json` | Update if contains unit_conversions |

### Files to Delete

| File | Reason |
|------|--------|
| `src/models/unit_conversion.py` | Model no longer needed |
| Any test files specific to UnitConversion | No longer applicable |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Cost calculation regression | Low | High | Regression test comparing before/after |
| Import fails on old format | Medium | Medium | Version detection, clear error message |
| Missing conversion path | Low | Medium | `convert_any_units()` handles all cases via density |

---

## Out of Scope

- Changes to Product model (package_unit, package_unit_quantity stay)
- Changes to RecipeIngredient model (unit stays - it's the recipe's declared unit)
- Standard conversion tables (oz↔lb, cup↔tbsp) - these remain
- Density input UI (Feature 010 already complete)

---

## Dependencies

- Constitution v1.2.0 (schema change via export/reset/import) ✅ Updated
- Working import/export (v3.2) ✅ Exists
- 4-field density model (Feature 010) ✅ Complete

---

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Tests pass (70%+ coverage on affected services)
- [ ] Documentation updated
- [ ] Test data files updated to v3.3 format
- [ ] Catalog import proposal updated
- [ ] Feature branch merged to main
