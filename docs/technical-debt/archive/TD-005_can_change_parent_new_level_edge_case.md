# TD-005: can_change_parent() new_level Edge Case for Invalid Parent

**Created:** 2026-01-02
**Feature:** F033 (Phase 1 Ingredient Hierarchy Fixes)
**Severity:** Very Low (edge case, cosmetic)
**Status:** Closed (Won't Fix)
**Closed:** 2026-01-17

## Resolution

**Closed as Won't Fix** - The edge case exists but has zero practical impact.

Analysis on 2026-01-17 found that the `new_level` field is not consumed by the UI:

| Location | Usage |
|----------|-------|
| `ingredient_hierarchy_service.py:900-906` | Sets the field |
| `test_ingredient_hierarchy_service.py` | Tests valid scenarios only |
| `ingredients_tab.py` | **Does not use it** |

The UI computes level independently at `ingredients_tab.py:1293-1321` based on dropdown selections (L0/L1 vars), not from `can_change_parent()`. The `_check_parent_change_warnings()` method only reads `allowed`, `reason`, and `warnings` fields.

Since the field isn't consumed, the edge case cannot manifest in the application. If `new_level` is ever needed by future code, the fix is trivial.

---

## Original Description

The `can_change_parent()` function in `src/services/ingredient_hierarchy_service.py` returns `new_level: 0` when the provided `new_parent_id` does not exist in the database. This is technically incorrect - the level should be undefined/unknown when the parent is invalid.

## Current Implementation

```python
# src/services/ingredient_hierarchy_service.py
def can_change_parent(ingredient_id, new_parent_id, session=None) -> Dict[str, Any]:
    def _impl(session):
        result = {
            "allowed": True,
            "reason": "",
            "warnings": [],
            "child_count": 0,
            "product_count": 0,
            "new_level": 0  # Default to 0
        }

        # Compute new level
        if new_parent_id is None:
            result["new_level"] = 0
        else:
            parent = session.query(Ingredient).filter(
                Ingredient.id == new_parent_id
            ).first()
            if parent:
                result["new_level"] = parent.hierarchy_level + 1
            # ISSUE: If parent is None (not found), new_level stays at 0
```

## Impact

- **Very Low**: The `allowed` field will be `False` when parent is invalid (caught by `validate_hierarchy()`), so the incorrect `new_level` is unlikely to be displayed
- UI could theoretically show "Level: L0" briefly before the error message appears
- No data corruption risk - validation prevents the change

## Recommended Fix

Set `new_level` to `None` or `-1` when parent lookup fails:

```python
if new_parent_id is None:
    result["new_level"] = 0
else:
    parent = session.query(Ingredient).filter(
        Ingredient.id == new_parent_id
    ).first()
    if parent:
        result["new_level"] = parent.hierarchy_level + 1
    else:
        result["new_level"] = None  # Unknown - parent not found
```

Then update UI to handle `None`:

```python
if result["new_level"] is None:
    level_text = "Level: (Invalid parent)"
```

## Acceptance Criteria

- [ ] `new_level` returns `None` when `new_parent_id` doesn't exist
- [ ] UI displays appropriate message for unknown level
- [ ] Existing tests still pass

## Related

- `src/services/ingredient_hierarchy_service.py:860-939` - Current implementation
- `src/ui/ingredients_tab.py:_compute_and_display_level()` - Computes level independently
- Cursor F033 Code Review (2026-01-02)
