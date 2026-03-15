# Research: Fix Plan Mode FG and Batch Scoping

**Feature**: 103-fix-plan-mode-fg-batch-scoping
**Date**: 2026-03-15

## R1: FG Loading Data Flow

**Question**: Why does the FG selection only show 2 items when multiple recipes are selected?

**Finding**: The call chain is:
1. `fg_selection_frame.py:307` calls `event_service.get_filtered_available_fgs(event_id, session, ...)`
2. Which calls `get_available_finished_goods(event_id, session)` (line 436)
3. Which queries ALL FinishedGoods, then checks each via `check_fg_availability(fg.id, selected_recipe_ids, session)`
4. `check_fg_availability` (line 384) recursively decomposes a FG into required recipes via `get_required_recipes()`
5. A FG is "available" only if ALL required recipes are in the selected set

**Root Cause**: This logic was designed for assembly/bundle availability checking ("can I make this gift box?") where all component recipes must be present. It's wrong for recipe-level planning where a simple FG (one recipe, one finished unit) should appear whenever its recipe is selected.

**Decision**: Create a new query function that joins FinishedUnit → Recipe → EventRecipe to find FGs for selected recipes. Keep the existing availability functions for future assembly planning.

## R2: Stale EventFinishedGood Records

**Question**: Why do batch options show "Pecan Shortbread Christmas Tree" when that recipe isn't selected for Easter 2026?

**Finding**:
1. `planning_service.decompose_event_to_fu_requirements()` (line 55) queries EventFinishedGood for the event
2. It includes ALL records — no filtering by current recipe selections
3. If a recipe was previously selected, its FG was saved in EventFinishedGood with a quantity
4. When the recipe was deselected, `set_event_recipes()` calls `remove_invalid_fg_selections()`
5. But `remove_invalid_fg_selections()` uses `check_fg_availability()` — the same "all recipes" logic
6. For a simple bare FG (one recipe, one FU), the availability check correctly identifies it as unavailable when its recipe is missing and should delete it

**Root Cause**: The cleanup in `remove_invalid_fg_selections()` relies on `check_fg_availability()` which should work for simple FGs. The stale record likely predates the cleanup feature (F070) or the cleanup wasn't triggered because recipe changes went through a different code path.

**Decision**:
1. Eager cleanup: simplify `remove_invalid_fg_selections()` to directly check FinishedUnit.recipe_id membership in EventRecipe
2. Defense-in-depth: add recipe filtering to batch decomposition query

## R3: FinishedGood ↔ FinishedUnit Relationship

**Question**: How do FinishedGoods relate to FinishedUnits and Recipes?

**Finding**:
```
EventFinishedGood (event_id, finished_good_id, quantity)
  → FinishedGood
    → FinishedGoodComponent[] (via fg.components)
      → FinishedUnit (via component.finished_unit_id)  [for BARE FGs]
        → Recipe (via fu.recipe_id)
      → FinishedGood (via component.finished_good_id)  [for BUNDLE FGs, recursive]
```

For bare FGs (the common case in recipe planning):
- FinishedGood has exactly 1 component
- That component points to 1 FinishedUnit
- That FinishedUnit has a recipe_id

**Decision**: Query through FinishedUnit → Recipe → EventRecipe, then map back to FinishedGood for UI compatibility. This avoids the recursive decomposition entirely.

## R4: Cleanup Strategy — Eager vs Lazy

**Question**: Should stale EventFinishedGood records be deleted on recipe deselection (eager) or filtered at query time (lazy)?

**Alternatives Considered**:
- **Lazy filtering**: Keep records, filter in every query. Preserves quantities if recipe re-selected.
- **Eager deletion**: Delete records immediately. Simpler, prevents stale data in any query.
- **Hybrid**: Eager delete + defense-in-depth filter in batch query.

**Decision**: Hybrid approach.
- Eager: Delete EventFinishedGood records when their recipe is deselected (user confirmed quantities are NOT preserved on re-select)
- Defense: Filter batch decomposition to selected recipes as a safety net

**Rationale**: The user explicitly stated re-selecting a recipe should show FGs "fresh, without previously saved quantities." This aligns with eager deletion. The defense-in-depth filter prevents any edge case where cleanup might be missed.
