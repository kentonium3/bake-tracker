# Research: Finished Units Yield Type Management

**Feature**: 044-finished-units-yield-type-management
**Date**: 2026-01-09
**Status**: Complete

## Executive Summary

Significant existing infrastructure supports this feature. The FinishedUnit model, service, and a CRUD tab already exist. Implementation primarily requires:
1. Adding a Yield Types section to the Recipe Edit form
2. Converting the existing FinishedUnitsTab to read-only catalog mode
3. Fixing cascade delete behavior on the model
4. Adding yield type validation to recipe save

## Existing Infrastructure Analysis

### Model Layer (`src/models/finished_unit.py`)

**Decision**: Use existing FinishedUnit model with minor modification

**Rationale**: Model already has all required fields:
- `display_name` (String 200, not null)
- `items_per_batch` (Integer, nullable, with positive check constraint)
- `recipe_id` (FK to recipes, not null)
- `yield_mode` (Enum: DISCRETE_COUNT, BATCH_PORTION)
- `slug` (unique identifier)

**Required Change**: Line 84 has `ondelete="RESTRICT"` but clarification requires CASCADE:
```python
# Current
recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False)
# Required
recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
```

**Alternatives Considered**:
- Create new YieldType model: Rejected - duplicates existing functionality
- Use FinishedGood model: Rejected - deprecated, FinishedUnit is the successor

### Service Layer (`src/services/finished_unit_service.py`)

**Decision**: Use existing FinishedUnitService

**Rationale**: Already provides:
- `create_finished_unit(display_name, recipe_id, **kwargs)`
- `update_finished_unit(finished_unit_id, **updates)`
- `delete_finished_unit(finished_unit_id)`
- `get_units_by_recipe(recipe_id)` - exactly what Recipe Edit needs
- `get_all_finished_units(name_search, category, recipe_id)` - filtering for catalog
- Validation: non-empty name, positive items_per_batch

**Required Change**: Add validation for name uniqueness within recipe:
- FR-019 requires "Yield type name MUST be unique within the same recipe"
- Service currently generates unique slug but doesn't validate name uniqueness per recipe

### UI Layer - Recipe Form (`src/ui/forms/recipe_form.py`)

**Decision**: Add new Yield Types section after Recipe Ingredients section

**Rationale**:
- User preference: "below ingredients list"
- Form already uses consistent pattern (section label + container frame + add button)
- Can reuse `RecipeIngredientRow` pattern for `YieldTypeRow`

**Current Section Order** (lines 497-793):
1. Basic Information (row 0-3)
2. Yield Information (row 4-7)
3. Recipe Ingredients (row 8-10)
4. Sub-Recipes (row 11-14)
5. Cost Summary (row 15-17)
6. Notes (row 18)

**New Section Order** (insert at row 11):
1. Basic Information
2. Yield Information
3. Recipe Ingredients
4. **Yield Types (NEW)** ← Insert here
5. Sub-Recipes
6. Cost Summary
7. Notes

### UI Layer - Finished Units Tab (`src/ui/finished_units_tab.py`)

**Decision**: Convert existing tab from full CRUD to read-only catalog

**Rationale**:
- Tab already exists with search and filter functionality
- Per spec FR-016: "Tab MUST be read-only (no Add/Edit/Delete buttons)"
- Per spec FR-017: "Tab MUST display a message indicating yield types are edited via Recipe Edit"
- Per spec FR-015: "Double-clicking a row MUST navigate to the parent Recipe Edit form"

**Required Changes**:
1. Remove Add, Edit, Delete buttons from `_create_action_buttons()` (lines 201-254)
2. Add info label per FR-017
3. Change double-click behavior to open parent Recipe Edit form instead of detail dialog
4. Add Recipe column to data table (currently shows Name only)

## Parallelization Analysis

### Safe to Parallelize (Different Files/Modules)

| Task | Files Affected | Assigned Agent |
|------|----------------|----------------|
| Recipe Edit - Yield Types Section | `src/ui/forms/recipe_form.py` | Claude (lead) |
| Finished Units Tab - Read-only Conversion | `src/ui/finished_units_tab.py` | Gemini |
| Service Layer - Name Validation | `src/services/finished_unit_service.py` | Gemini |
| Model - Cascade Delete | `src/models/finished_unit.py` | Gemini |
| Unit Tests | `src/tests/test_finished_unit_*.py` | Gemini (after implementation) |

### Must Be Sequential

| Task | Depends On | Reason |
|------|------------|--------|
| Integration testing | All UI/Service changes | Need complete implementation |
| Recipe form validation | Service validation | UI calls service for uniqueness check |

## Technical Decisions

### Inline Row Entry Pattern

**Decision**: Use inline entry row (like RecipeIngredientRow) not modal dialog

**Rationale**: User explicitly stated preference for inline approach - "I prefer that the FinishedUnit be part of the Recipe edit form"

**Pattern Reference**: `RecipeIngredientRow` class (lines 168-388 of recipe_form.py)

### Yield Type Minimum Requirement

**Decision**: Warn on save if no yield types defined (soft enforcement)

**Rationale**: User chose Option B - "Allow editing but warn on save"

**Implementation**: Add validation in `RecipeFormDialog._validate_form()` similar to existing ingredient warning (lines 1218-1227)

### Recipe Filter Dropdown for Catalog Tab

**Decision**: Add recipe dropdown filter using existing ComboBox pattern

**Rationale**: FR-014 requires "A recipe dropdown MUST filter yield types by parent recipe"

**Pattern Reference**: SearchBar already supports categories, add recipe filter similarly

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Cascade delete breaks existing recipes | Low | High | Add migration to verify no orphaned FU records |
| Name uniqueness validation conflicts | Medium | Medium | Service validates before create, UI shows error |
| Double-click navigation doesn't work | Low | Medium | Test with fresh recipe |

## Dependencies Verified

- **F037 (Recipe Redesign)**: COMPLETED - Recipe model has `finished_units` relationship (line 99 of recipe.py)
- **F042 (UI Polish)**: COMPLETED - Tab patterns established

## Outstanding Questions Resolved

All critical questions resolved during planning interrogation:
1. Yield Types section placement: Below ingredients list ✓
2. Minimum yield types: Warn on save (soft enforcement) ✓
3. Cascade delete behavior: CASCADE (from /clarify) ✓
