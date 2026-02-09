# Data Model: Planning FG Selection Refinement

**Feature**: 100-planning-fg-selection-refinement
**Date**: 2026-02-09

## Existing Models (No Schema Changes)

This feature requires **no new models and no schema changes**. All data structures already exist. This document maps the spec requirements to existing models and identifies new service query patterns.

### Models Used

| Model | Table | Role in F100 |
|-------|-------|-------------|
| Recipe | `recipes` | `.category` field used for recipe category filtering |
| RecipeCategory | `recipe_categories` | Populates category filter dropdown options |
| FinishedGood | `finished_goods` | `.assembly_type` used for item type filtering (BARE/BUNDLE) |
| FinishedUnit | `finished_units` | `.yield_type` used for yield type filtering (EA/SERVING); `.recipe_id` links to Recipe |
| Composition | `compositions` | Links FinishedUnits to FinishedGoods (component relationship) |
| EventRecipe | `event_recipes` | Tracks which recipes are selected for an event |
| EventFinishedGood | `event_finished_goods` | Stores FG selections with quantities (atomic save target) |
| Event | `events` | Container; `.plan_state` must be DRAFT for modifications |

### Key Relationships for Filtering

```
RecipeCategory.name ─matches─> Recipe.category
Recipe.id ───FK───> FinishedUnit.recipe_id
FinishedUnit.id ───FK───> Composition.finished_unit_id
Composition.assembly_id ───FK───> FinishedGood.id

Event.id ───FK───> EventRecipe.event_id
Event.id ───FK───> EventFinishedGood.event_id
```

### Filter Dimension Mapping

| Filter | Source Model | Field | Values |
|--------|-------------|-------|--------|
| Recipe Category | RecipeCategory | `.name` (matched to `Recipe.category`) | Dynamic from `list_categories()` + "All Categories" |
| Item Type | FinishedGood | `.assembly_type` | "Finished Units" (BARE), "Assemblies" (BUNDLE), "All" |
| Yield Type | FinishedUnit | `.yield_type` | "EA", "SERVING", "All" |

## New Service Functions

### `get_filtered_available_fgs()`

**Location**: `src/services/event_service.py`

```python
def get_filtered_available_fgs(
    event_id: int,
    session: Session,
    recipe_category: Optional[str] = None,   # RecipeCategory.name or None for all
    assembly_type: Optional[str] = None,      # "bare" or "bundle" or None for all
    yield_type: Optional[str] = None,         # "EA" or "SERVING" or None for all
) -> List[FinishedGood]:
```

**Query logic**:
1. Start with `get_available_finished_goods(event_id, session)` to get event-scoped FGs
2. Apply recipe_category filter: Keep FGs whose component FinishedUnits have `recipe.category == recipe_category`
3. Apply assembly_type filter: Keep FGs where `fg.assembly_type == AssemblyType(assembly_type)`
4. Apply yield_type filter: For BARE FGs, check single FinishedUnit's `yield_type`; BUNDLE FGs excluded when yield_type is specified

**Transaction boundary**: Inherits session from caller (required parameter).

### `get_available_recipe_categories_for_event()`

**Location**: `src/services/event_service.py`

```python
def get_available_recipe_categories_for_event(
    event_id: int,
    session: Session,
) -> List[str]:
```

Returns distinct recipe categories that have at least one available FG for the event. Used to populate the FG-level recipe category filter with relevant options only.

## UI State Model (In-Memory Only)

These are not persisted to the database. They exist as Python data structures on UI frame instances.

### RecipeSelectionFrame State

```python
_selected_recipe_ids: Set[int]        # Persists across category filter changes
_current_category: Optional[str]      # Currently selected category filter
```

### FGSelectionFrame State

```python
_selected_fg_ids: Set[int]            # Persists across all filter changes
_fg_quantities: Dict[int, int]        # FG ID -> quantity, persists across filter changes
_current_recipe_category: Optional[str]  # Current recipe category filter
_current_assembly_type: Optional[str]    # Current item type filter
_current_yield_type: Optional[str]       # Current yield type filter
_show_selected_only: bool                # "Show All Selected" mode toggle
```

### Save Payload

On Save, the UI constructs:
```python
fg_quantities: List[Tuple[int, int]] = [
    (fg_id, quantity) for fg_id, quantity in _fg_quantities.items()
    if fg_id in _selected_fg_ids and quantity > 0
]
```

This is passed to `set_event_fg_quantities(session, event_id, fg_quantities)` which handles atomic replace.
