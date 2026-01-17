# Code Review Report: F056 - Unified Yield Management

**Reviewer:** Cursor (independent)
**Date:** 2026-01-16
**Spec:** `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/056-unified-yield-management/kitty-specs/056-unified-yield-management/spec.md`

## Verification
- Imports: `FinishedUnit`, `YieldMode` ✅
- Tests: `pytest src/tests/services/test_coordinated_export.py -v --tb=short -q` ✅ (exit 0; SAWarning only)

## Findings (ordered by severity)

### 1) Yield type persistence drops required `item_unit` (FR-002/FR-007/FR-011/FR-012)
Saving yield rows via Recipes tab or Finished Units tab calls `finished_unit_service.create_finished_unit` / `update_finished_unit` with `display_name` and `items_per_batch` only; `item_unit` is never persisted. Result: saved FinishedUnits lack unit, violating core requirement that a yield type has Description + Unit + Quantity and breaking import/export correctness.
```443:487:src/ui/recipes_tab.py
finished_unit_service.create_finished_unit(
    display_name=data["display_name"],
    recipe_id=recipe_id,
    items_per_batch=data["items_per_batch"],
)
...
finished_unit_service.update_finished_unit(
    data["id"],
    display_name=data["display_name"],
    items_per_batch=data["items_per_batch"],
)
```
Same omission in Catalog > Finished Units edit path.
```443:479:src/ui/finished_units_tab.py
finished_unit_service.create_finished_unit(
    display_name=data["display_name"],
    recipe_id=recipe_id,
    items_per_batch=data["items_per_batch"],
)
...
finished_unit_service.update_finished_unit(
    data["id"],
    display_name=data["display_name"],
    items_per_batch=data["items_per_batch"],
)
```

### 2) Backend recipe creation/edit still relies on deprecated yield fields; does not enforce/attach FinishedUnits (FR-001, FR-005)
`recipe_service.create_recipe` accepts/stores `yield_quantity`/`yield_unit` and never persists or validates FinishedUnits; the new validation helper `validate_recipe_has_finished_unit` is not invoked anywhere. Backend allows recipes with zero FinishedUnits, undermining the “single source of truth” goal and contradicting the “at least one complete yield type required” rule.
```106:118:src/services/recipe_service.py
recipe = Recipe(
    name=recipe_data["name"],
    category=recipe_data["category"],
    yield_quantity=recipe_data["yield_quantity"],
    yield_unit=recipe_data["yield_unit"],
    yield_description=recipe_data.get("yield_description"),
    ...
)
```
```1095:1157:src/services/recipe_service.py
def validate_recipe_has_finished_unit(...):
    ...
    if not finished_units:
        return ["Recipe must have at least one yield type"]
    ...
```

### 3) Legacy transform script fails to guarantee FinishedUnit creation for all recipes (FR-018/FR-021/FR-022/FR-025)
`transform_yield_data.py` only creates a FinishedUnit when BOTH `yield_quantity` and `yield_unit` are present. Recipes with description-only yields (or quantity with missing unit) produce zero FinishedUnits, violating the spec’s requirement that 100% of recipes emerge with at least one FinishedUnit post-transform. Also, display_name fallback and slug collision handling never run for those cases.
```55:103:scripts/transform_yield_data.py
yield_quantity = recipe.get('yield_quantity')
yield_unit = recipe.get('yield_unit')
...
if yield_quantity is not None and yield_unit:
    ...
    display_name = yield_description or f"Standard {recipe_name}"
    finished_unit = { ... 'items_per_batch': int(yield_quantity) if yield_quantity else None,
                      'item_unit': yield_unit or 'each', ... }
...
transformed_recipe['yield_quantity'] = None
transformed_recipe['yield_unit'] = None
transformed_recipe['yield_description'] = None
```

### 4) UI still surfaces deprecated yield fields in recipe detail view
Recipe detail dialog in `recipes_tab` reports legacy `yield_quantity`/`yield_unit` and “cost per {yield_unit}”, even though the feature makes FinishedUnits the source of truth. This risks user confusion and incorrect cost-per-unit messaging.
```505:518:src/ui/recipes_tab.py
details.append(f"Yields: {recipe.yield_quantity} {recipe.yield_unit}")
...
details.append(f"  Cost per {recipe.yield_unit}: ${recipe_data['cost_per_unit']:.4f}")
```

## Recommendations
- Pass `item_unit` (and `yield_mode` where applicable) through all yield-type persistence paths; ensure validation blocks saving incomplete units.
- Wire service-layer create/update flows to persist FinishedUnits and invoke `validate_recipe_has_finished_unit` on save; stop accepting deprecated yield fields as authoritative.
- Update the transformation script to always emit at least one FinishedUnit per recipe (use “Standard {recipe_name}” and default unit when missing) and retain collision handling.
- Refresh recipe detail display to surface FinishedUnits or remove deprecated yield lines to align with the unified model.

## Overall Assessment
Feature is not production-ready. Core data integrity is broken by missing `item_unit` persistence and backend ignoring FinishedUnits; transformation script leaves some recipes without yields. Requires fixes above before ship.
