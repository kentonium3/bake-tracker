# Research: F070 Finished Goods Filtering

**Date**: 2026-01-26
**Feature**: 070-finished-goods-filtering

## Model Discovery

### Decision: Recipe linkage is on FinishedUnit, not FinishedGood

**Rationale**: The codebase distinguishes between:
- **FinishedGood**: A bundle/assembly container (gift box, package)
- **FinishedUnit**: An atomic producible item linked to a single Recipe

FinishedGood does NOT have a `recipe_id` field. Instead, it contains components via the Composition junction model, which can reference:
- `finished_unit_id` → FinishedUnit (which has `recipe_id`)
- `finished_good_id` → Nested FinishedGood (recurse to find recipes)

**Alternatives considered**:
- Add `recipe_id` directly to FinishedGood → Rejected (breaks existing schema, violates constitution principle III)
- Query through Recipe → FinishedUnit path → Works but doesn't handle bundles

### Decision: Use Composition model for bundle traversal

**Rationale**: Composition is the junction table linking FinishedGood to its components. It supports polymorphic component types:
- `finished_unit_component` - Atomic item with recipe
- `finished_good_component` - Nested bundle (recurse)
- `packaging_product_id`, `material_unit_id`, `material_id` - Non-recipe components (ignore for filtering)

**Key fields**:
```python
class Composition:
    assembly_id: FK to FinishedGood  # The parent bundle
    finished_unit_id: FK to FinishedUnit (nullable)
    finished_good_id: FK to FinishedGood (nullable)  # Nested bundle
    component_quantity: Float
```

## Recursive Algorithm Patterns

### Decision: Follow BFS pattern with visited set

**Rationale**: Multiple existing implementations use this pattern:
1. `finished_good_service._get_flattened_components()` - BFS with deque
2. `batch_calculation.explode_bundle_requirements()` - Recursive with `_visited` set
3. `finished_good_service.validate_no_circular_references()` - BFS cycle detection

**Pattern chosen** (from `explode_bundle_requirements`):
```python
def get_required_recipes(fg_id, session, *, _visited=None, _depth=0):
    if _visited is None:
        _visited = set()

    if _depth > MAX_DEPTH:
        raise MaxDepthExceededError(...)

    if fg_id in _visited:
        raise CircularReferenceError(...)

    _visited.add(fg_id)

    fg = session.get(FinishedGood, fg_id)
    recipes = set()

    for comp in fg.components:
        if comp.finished_unit_id:
            recipes.add(comp.finished_unit_component.recipe_id)
        elif comp.finished_good_id:
            child_recipes = get_required_recipes(
                comp.finished_good_id, session,
                _visited=_visited, _depth=_depth + 1
            )
            recipes.update(child_recipes)

    return recipes
```

**Alternatives considered**:
- Iterative BFS with deque → More complex state management
- Memoization/caching → Premature optimization; profile first if needed

### Decision: Max depth of 10 levels

**Rationale**: Existing code uses this limit (e.g., `_get_hierarchical_components`). Deeper nesting is likely a data error.

## Session Management

### Decision: Accept optional session parameter

**Rationale**: Per CLAUDE.md guidance, service methods that may be called from other services MUST accept `session=None`. This prevents nested `session_scope()` issues that cause detached objects.

**Pattern** (from F069):
```python
def method_name(session: Session, event_id: int, ...) -> Result:
    """Method docstring."""
    # Use session directly - caller manages transaction
```

**Alternatives considered**:
- Create new session internally → Causes detachment issues when called from other services

## UI Filtering Strategy

### Decision: Hide unavailable FGs (Option A)

**Rationale**: User confirmed during discovery. Simpler UX - shows only actionable items.

**Implementation**:
1. Service returns list of available FGs
2. UI displays only those FGs
3. When recipe selection changes, re-query and re-render

## Cascade Removal

### Decision: Auto-remove invalid FG selections on recipe deselect

**Rationale**: Spec requires protecting data integrity. When a recipe is deselected:
1. Find all FGs currently selected for event
2. For each FG, check if still available with new recipe set
3. Remove FGs that are no longer available
4. Return list of removed FGs for notification

**Trigger point**: Modify `set_event_recipes()` to call removal logic after updating recipes.

## Service Location

### Decision: Add methods to event_service.py

**Rationale**:
- F069 recipe selection is in `event_service.py`
- FG availability is event-specific (depends on event's recipe selection)
- Follows existing pattern of event-related operations

**Alternatives considered**:
- New `fg_availability_service.py` → Unnecessary indirection
- Add to `finished_good_service.py` → That service doesn't know about events

## File References

| Purpose | File Path |
|---------|-----------|
| FinishedGood model | `src/models/finished_good.py` |
| FinishedUnit model | `src/models/finished_unit.py` |
| Composition model | `src/models/composition.py` |
| EventRecipe model | `src/models/event_recipe.py` |
| EventFinishedGood model | `src/models/event_finished_good.py` |
| Event service | `src/services/event_service.py` |
| Reference: BFS pattern | `src/services/finished_good_service.py:1065` |
| Reference: Recursive pattern | `src/services/planning/batch_calculation.py:149` |
