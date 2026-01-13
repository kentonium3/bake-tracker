# TD-004: Hierarchy Path Cache N+1 Query Performance

**Created:** 2026-01-02
**Feature:** F033 (Phase 1 Ingredient Hierarchy Fixes)
**Severity:** Low (performance optimization)
**Status:** Open

## Description

The `_build_hierarchy_path_cache()` method in `src/ui/ingredients_tab.py` makes a separate `get_ancestors()` call for each non-L0 ingredient when building the hierarchy path cache. This results in N+1 query behavior where N is the number of L1/L2 ingredients.

## Current Implementation

```python
# src/ui/ingredients_tab.py:285-334
def _build_hierarchy_path_cache(self) -> Dict[int, str]:
    cache = {}
    for ingredient in self.ingredients:
        # ...
        if hierarchy_level == 1:
            ancestors = ingredient_hierarchy_service.get_ancestors(ing_id)  # DB call
            # ...
        else:  # L2
            ancestors = ingredient_hierarchy_service.get_ancestors(ing_id)  # DB call
            # ...
    return cache
```

Each `get_ancestors()` call opens its own session when called from UI without a passed session.

## Impact

- For small ingredient lists (<100), impact is negligible
- For larger lists, this could cause noticeable UI lag on refresh
- Each refresh rebuilds the cache, triggering all ancestor queries again

## Recommended Solutions

### Option A: Bulk Ancestor Prefetch (Preferred)

Add a service function that returns all ingredients with precomputed paths in one query:

```python
def get_all_ingredients_with_paths() -> List[Dict]:
    """Return all ingredients with hierarchy_path precomputed."""
    # Single query with self-join to get ancestor names
    # Return list with 'hierarchy_path' field already populated
```

### Option B: In-Memory Path Building

Since `get_all_ingredients()` already returns all ingredients with `parent_ingredient_id`, build paths in-memory without additional DB calls:

```python
def _build_hierarchy_path_cache(self) -> Dict[int, str]:
    # Build lookup: id -> ingredient
    id_to_ing = {ing["id"]: ing for ing in self.ingredients}

    cache = {}
    for ingredient in self.ingredients:
        path_parts = []
        current = ingredient
        while current:
            path_parts.insert(0, current.get("display_name", ""))
            parent_id = current.get("parent_ingredient_id")
            current = id_to_ing.get(parent_id) if parent_id else None
        cache[ingredient["id"]] = " > ".join(path_parts)
    return cache
```

### Option C: Lazy Path Computation

Only compute paths for visible rows (virtualized list), not entire dataset.

## Acceptance Criteria

- [ ] Hierarchy path cache builds without per-ingredient DB calls
- [ ] Refresh performance scales linearly with ingredient count
- [ ] No visible UI lag with 500+ ingredients

## Related

- `src/ui/ingredients_tab.py:285-334` - Current implementation
- `src/services/ingredient_hierarchy_service.py:get_ancestors()` - Called per ingredient
- Cursor F033 Code Review (2026-01-02)
