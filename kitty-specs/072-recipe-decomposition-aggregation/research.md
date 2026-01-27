# Research: Recipe Decomposition & Aggregation

**Feature**: F072 | **Date**: 2026-01-27

## Objective

Document existing patterns and data structures relevant to implementing recipe decomposition and aggregation for event planning.

## Existing Patterns Found

### 1. Recursive Bundle Decomposition (F070)

**File**: `src/services/event_service.py:171-244`

The `get_required_recipes()` function provides a reference implementation for recursive bundle traversal:

```python
def get_required_recipes(
    fg_id: int,
    session: Session,
    *,
    _path: Optional[Set[int]] = None,
    _depth: int = 0,
) -> Set[int]:
    """Recursively decompose a FinishedGood to determine all required recipe IDs."""
```

**Key patterns:**
- Path-based cycle detection (`_path` tracks ancestry, not all visited nodes)
- Allows DAG patterns (same FG reused in multiple branches)
- Depth limiting via `MAX_FG_NESTING_DEPTH` constant
- Session passed explicitly (caller manages transaction)
- Returns `Set[int]` of recipe IDs (no quantities)

**Limitation for F072:** Returns only unique recipe IDs, not quantities. F072 needs quantity tracking through the decomposition.

### 2. Session Parameter Pattern

**File**: `src/services/planning_snapshot_service.py`

All service functions follow the pattern:

```python
def create_planning_snapshot(
    event_id: int = None,
    notes: str = None,
    session: Session = None,
) -> dict:
    if session is not None:
        return _impl(event_id, notes, session)
    with session_scope() as session:
        return _impl(event_id, notes, session)
```

This pattern allows:
- Standalone calls with automatic session management
- Transaction sharing when called from other services

### 3. Data Model Structure

#### EventFinishedGood (Input)
**File**: `src/models/event_finished_good.py`

- Links Event to FinishedGood with quantity
- `event_id`, `finished_good_id`, `quantity`
- Source of FG selections for an event

#### FinishedGood (Bundle)
**File**: `src/models/finished_good.py`

- Assembly/bundle containing components via `components` relationship
- Components loaded via `Composition` junction model
- Can contain FinishedUnits or other FinishedGoods (nested bundles)

#### Composition (Junction)
**File**: `src/models/composition.py`

- Polymorphic: `finished_unit_id` XOR `finished_good_id` (plus others)
- `component_quantity` - quantity of component in assembly
- `assembly_id` - parent FinishedGood

#### FinishedUnit (Atomic)
**File**: `src/models/finished_unit.py`

- Atomic item linked to a Recipe
- `recipe_id` - foreign key to Recipe
- This is what recipes produce

### 4. Data Flow

```
Event → EventFinishedGood → FinishedGood → Composition → FinishedUnit → Recipe
                                          ↓
                                    FinishedGood (nested) → Composition → ...
```

**Decomposition:**
1. Event has EventFinishedGoods with quantities
2. Each FinishedGood has Composition components
3. Components are either FinishedUnits (atomic) or FinishedGoods (recursive)
4. FinishedUnits link to Recipes via recipe_id

**Aggregation:**
- Multiple FinishedUnits may share the same recipe_id
- Quantities must be summed by recipe across all decomposed paths

## Algorithm Design

### Input
- `event_id: int`

### Output
- `Dict[Recipe, int]` - Recipe objects mapped to total quantities needed

### Steps

1. **Query EventFinishedGoods** for the event
2. **For each (FinishedGood, event_quantity):**
   - Call recursive decomposition with quantity tracking
   - Returns `Dict[Recipe, int]` for that FG path
3. **Aggregate results** - sum quantities by recipe across all FGs
4. **Return** aggregated dictionary

### Recursive Decomposition (with quantities)

```
decompose(fg_id, multiplier, session, _path, _depth) -> Dict[Recipe, int]:
    # Cycle detection
    if fg_id in _path: raise CircularReferenceError
    if _depth > MAX_DEPTH: raise MaxDepthExceededError

    _path.add(fg_id)
    try:
        fg = query FinishedGood
        result = {}

        for comp in fg.components:
            comp_qty = comp.component_quantity * multiplier

            if comp.finished_unit_id:
                # Atomic: map to recipe
                recipe = comp.finished_unit_component.recipe
                result[recipe] = result.get(recipe, 0) + comp_qty

            elif comp.finished_good_id:
                # Nested: recurse
                child_result = decompose(comp.finished_good_id, comp_qty, ...)
                for recipe, qty in child_result.items():
                    result[recipe] = result.get(recipe, 0) + qty

        return result
    finally:
        _path.discard(fg_id)
```

### Differences from F070 get_required_recipes

| Aspect | F070 | F072 |
|--------|------|------|
| Output | `Set[int]` (recipe IDs) | `Dict[Recipe, int]` (with quantities) |
| Quantity tracking | No | Yes (multiplied at each level) |
| Aggregation | Set union | Sum by recipe |
| Returns | IDs only | Full Recipe objects |

## Constitution Compliance

| Check | Status | Notes |
|-------|--------|-------|
| Service layer separation | PASS | Pure calculation in services layer |
| No UI dependencies | PASS | Returns dict, no UI code |
| Session parameter pattern | PASS | Will accept optional session |
| Test-driven development | PASS | Tests defined in spec |
| FIFO not affected | N/A | Read-only operation |

## Edge Cases Identified

1. **Empty event** - Return empty dict
2. **FG with no components** - Skip (or validate as error?)
3. **FinishedUnit without recipe** - Raise ValidationError
4. **Circular reference** - Raise CircularReferenceError (use F070 pattern)
5. **Zero-quantity components** - Skip in decomposition
6. **DAG patterns** - Allowed (same FG in multiple branches)

## Dependencies

- Existing models: Event, EventFinishedGood, FinishedGood, Composition, FinishedUnit, Recipe
- Existing service: event_service (for reference patterns)
- Constants: MAX_FG_NESTING_DEPTH from event_service

## Recommendations

1. **Place in planning_service.py** - Per user decision, aligns with PlanningService responsibility
2. **Reuse cycle detection pattern** from F070's get_required_recipes
3. **Return Recipe objects** not IDs - downstream F073 needs Recipe details
4. **Accept session parameter** - enables transaction sharing
5. **Pure calculation** - no database writes, no side effects
