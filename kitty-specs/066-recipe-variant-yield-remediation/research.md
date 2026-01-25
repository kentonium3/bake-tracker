# Research: Recipe Variant Yield Remediation

**Feature**: 066-recipe-variant-yield-remediation
**Date**: 2025-01-24

## Summary

Research completed during planning phase. Key findings documented below.

## Service Primitive Status

**Decision**: Primitives already exist and are correctly implemented.

**Rationale**: `get_finished_units()` and `get_base_yield_structure()` were implemented as part of F063 and exist at `src/services/recipe_service.py:1941-2054`.

**Post-Phase-1 Update Needed**: Docstrings reference outdated behavior (NULL yield fields for variants). Phase 1 bug fix changed this - variants now have copied yield values.

## Service Decoupling Audit

**Decision**: Focus decoupling on planning/calculation services only.

**Audit Results**:

| Service | File | Lines | Current Access | Action |
|---------|------|-------|----------------|--------|
| Planning | `planning_service.py` | 505-506 | `recipe.finished_units` | REPLACE |
| Planning | `planning_service.py` | 686-687 | `recipe.finished_units` | REPLACE |
| Batch Calc | `batch_calculation.py` | 296-297 | `recipe.finished_units` | REPLACE |
| Recipe | `recipe_service.py` | 285 | Eager loading | KEEP - internal |
| Recipe | `recipe_service.py` | 725-726 | Recipe display | KEEP - internal |
| Recipe | `recipe_service.py` | 1148 | Variant creation | KEEP - internal |
| Recipe | `recipe_service.py` | 1866-1867 | Recipe listing | KEEP - internal |
| Snapshot | `recipe_snapshot_service.py` | 96-97 | Snapshot capture | KEEP - raw data |
| Export | `denormalized_export_service.py` | 1187-1188 | Export serialization | KEEP - raw data |
| Import | `import_export_service.py` | 1491 | Import iteration | KEEP - raw data |

**Alternatives Considered**:
1. Decouple ALL services - Rejected because export/snapshot services serialize raw data, not perform calculations
2. Only decouple planning - Rejected because batch_calculation is also a yield consumer

## UI Dialog Status

### VariantCreationDialog

**Location**: `src/ui/forms/variant_creation_dialog.py`

**Current State**:
- Uses "Yield Type Names:" header (line 130)
- Shows base finished units with editable display names
- Does NOT show base recipe yield values (items_per_batch, item_unit) as reference

**Updates Needed**:
- Change terminology to "Variant Yields:"
- Add read-only display of base recipe yield values
- Add explanatory text about inheritance

### RecipeFormDialog

**Location**: `src/ui/forms/recipe_form.py`

**Current State**:
- No variant detection (no check for `base_recipe_id`)
- All yield fields fully editable regardless of recipe type
- No base recipe reference shown

**Updates Needed**:
- Detect variants via `recipe.base_recipe_id`
- For variants: show base recipe banner, make yield structure read-only
- For base recipes: no changes

## Testing Status

**Existing Tests**: `src/tests/test_recipe_yield_primitives.py`
- Tests for `get_base_yield_structure()` - 6 tests
- Tests for `get_finished_units()` - 5 tests
- Tests were updated during Phase 1 fix to expect copied (not NULL) yields

**New Tests Needed**:
- Integration tests verifying planning/batch_calculation use primitives
- Can use mocking to verify primitive calls

## Terminology Research

**Decision**: Use "yield" consistently in user-facing text.

**Rationale**:
- "Finished unit" is a technical/model term
- "Yield" is more intuitive for users (what the recipe produces)
- Constitution Principle I requires intuitive UI for non-technical users

**Search Results**:
- `src/ui/forms/variant_creation_dialog.py:130` - "Yield Type Names:" (close, but should just be "Yields")
- No other user-facing "finished unit" terminology found in UI layer
