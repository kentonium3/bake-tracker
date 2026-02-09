# Research: Planning FG Selection Refinement

**Feature**: 100-planning-fg-selection-refinement
**Date**: 2026-02-09

## R1: Existing Recipe-FG Relationship Chain

**Question**: How do recipes connect to finished goods for availability filtering?

**Finding**: The chain is: Recipe -> FinishedUnit (via `recipe_id` FK) -> Composition (via `finished_unit_id`) -> FinishedGood (via `assembly_id`). BARE FGs have exactly one FinishedUnit component. BUNDLE FGs can have multiple FinishedUnit and/or FinishedGood components.

**Decision**: FG availability for an event is determined by `get_available_finished_goods()` in `event_service.py:435`, which checks if all required recipes for a FG are selected. The new filtered query will extend this by adding filter parameters.

**Alternatives considered**: Building a denormalized view — rejected because the catalog is small (~100 FGs) and the existing traversal pattern works well.

## R2: Recipe Category Data Source

**Question**: Which field to use for recipe categorization in filters?

**Finding**: Two category representations exist:
1. `Recipe.category` (String field on recipe model, e.g., "Cookies", "Brownies")
2. `RecipeCategory` model (separate table with name, slug, sort_order) from F096

The `RecipeCategory` model is the normalized source. `Recipe.category` stores the category name string directly. They are not FK-linked — `Recipe.category` contains the category name as a plain string.

**Decision**: Use `recipe_category_service.list_categories()` to populate dropdown options. When filtering recipes, match `Recipe.category` against the selected `RecipeCategory.name`.

**Alternatives considered**: Adding a FK from Recipe.category to RecipeCategory.id — rejected as a schema change not needed for this feature.

## R3: Yield Type Filter Applicability

**Question**: How does yield_type filtering work for BUNDLE FGs?

**Finding**: `yield_type` is a field on `FinishedUnit`, not on `FinishedGood`. BUNDLE FGs don't have a direct yield_type. Yield type filtering only makes sense for BARE FGs (which wrap a single FinishedUnit).

**Decision**: When yield_type filter is active:
- BARE FGs: Filter by their single FinishedUnit's yield_type
- BUNDLE FGs: Excluded when a specific yield_type is selected (they don't have one)
- When yield_type is "All": Both BARE and BUNDLE FGs shown (yield_type filter not applied)

**Alternatives considered**: Deriving yield_type for BUNDLEs from majority component type — rejected as confusing and semantically wrong.

## R4: Existing Filter-First Pattern (F099 Reference)

**Question**: What UX patterns from F099's FG Builder should be reused?

**Finding**: The FG Builder (`src/ui/builders/finished_good_builder.py`) implements:
- Blank start with placeholder text
- Filter controls always visible at top
- Items render only after filter selection
- Confirmation dialog when filter change would clear selections
- Search with debounce (300ms)

**Decision**: Adapt the blank-start + filter-controls-at-top pattern. Skip the confirmation dialog for filter changes because F100 explicitly requires selection persistence (FR-008) — selections are NOT cleared on filter change, making the confirmation unnecessary.

**Alternatives considered**: Copying F099's "confirm before clearing" pattern — rejected because F100's core innovation is that selections persist across filter changes.

## R5: Atomic Save Pattern

**Question**: How should the final save work?

**Finding**: `set_event_fg_quantities()` in `event_service.py:3439` already implements the atomic save pattern:
1. Validates event exists and is in DRAFT state
2. Filters to available FGs only
3. Deletes all existing EventFinishedGood records for the event
4. Inserts new records with quantities
5. All within a single session/transaction

**Decision**: Reuse `set_event_fg_quantities()` directly. The UI collects all (fg_id, quantity) pairs from the in-memory state and passes them in one call.

**Alternatives considered**: Incremental saves (save each FG individually) — rejected because the replace-all pattern is simpler and already proven.

## R6: Planning Tab Orchestration

**Question**: How does the planning_tab.py currently wire recipe and FG selection?

**Finding**: The planning tab (`src/ui/planning_tab.py`, 1877 lines) uses:
- `_show_recipe_selection(event_id)` at line 549: Loads all non-archived recipes, populates RecipeSelectionFrame
- `_show_fg_selection(event_id)` at line 652: Gets available FGs via `get_available_finished_goods()`, populates FGSelectionFrame
- Save callbacks cascade: recipe save -> refresh FG availability -> FG save -> refresh downstream

**Decision**: The orchestration flow stays the same. The recipe/FG frames gain internal filtering but the planning_tab interaction points (show, save callbacks) remain compatible.

**Alternatives considered**: Refactoring planning_tab.py into smaller modules — deferred (out of scope for F100).
