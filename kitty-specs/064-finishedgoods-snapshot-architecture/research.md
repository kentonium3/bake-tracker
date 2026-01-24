# Research: FinishedGoods Snapshot Architecture

**Feature**: 064-finishedgoods-snapshot-architecture
**Date**: 2025-01-24

## Research Questions

### RQ1: What is the established snapshot pattern in this codebase?

**Decision**: Follow RecipeSnapshot pattern exactly

**Findings**:
- RecipeSnapshot (`src/models/recipe_snapshot.py`) uses JSON Text columns for `recipe_data` and `ingredients_data`
- Service layer (`src/services/recipe_snapshot_service.py`) uses wrapper/impl pattern for session management
- Snapshot is created via `session.flush()` to get ID without committing
- Returns dict with parsed data, not ORM object
- Uses `is_backfilled` flag for migration scenarios
- FKs use `ondelete="RESTRICT"` for source entity, `ondelete="CASCADE"` for container

**Rationale**: Consistency with established patterns reduces cognitive load and ensures proven session management.

### RQ2: What fields need to be captured for each snapshot type?

**Decision**: Capture all catalog definition fields plus denormalized relationship data

**FinishedUnitSnapshot fields** (from `src/models/finished_unit.py`):
```python
{
    "slug": str,
    "display_name": str,
    "description": str | None,
    "recipe_id": int,
    "recipe_name": str,  # Denormalized from recipe
    "recipe_category": str | None,  # Denormalized
    "yield_mode": str,  # Enum value
    "items_per_batch": int | None,
    "item_unit": str | None,
    "batch_percentage": float | None,
    "portion_description": str | None,
    "category": str | None,
    "production_notes": str | None,
    "notes": str | None
}
```

**MaterialUnitSnapshot fields** (from `src/models/material_unit.py`):
```python
{
    "slug": str,
    "name": str,
    "description": str | None,
    "material_id": int,
    "material_name": str,  # Denormalized from material
    "material_category": str | None,  # Denormalized
    "quantity_per_unit": float
}
```

**FinishedGoodSnapshot fields** (from `src/models/finished_good.py` and `src/models/composition.py`):
```python
{
    "slug": str,
    "display_name": str,
    "description": str | None,
    "assembly_type": str,  # Enum value
    "packaging_instructions": str | None,
    "notes": str | None,
    "components": [  # From Composition relationships
        {
            "component_type": str,  # "finished_unit", "finished_good", "material_unit"
            "snapshot_id": int,  # Reference to component snapshot
            "original_id": int,  # Original catalog ID
            "component_slug": str,
            "component_name": str,
            "component_quantity": float,
            "component_notes": str | None,
            "sort_order": int,
            "is_generic": bool
        }
    ]
}
```

**Rationale**: Denormalized data ensures snapshot is self-contained even if source entities are deleted.

### RQ3: How should circular reference detection work?

**Decision**: Visited set tracking with max depth limit

**Implementation approach**:
1. Create snapshot function accepts optional `visited_ids: set[int]` and `depth: int` parameters
2. At start of recursive call, check if current FinishedGood ID is in visited set
3. If found, raise `CircularReferenceError` with path information
4. Add current ID to visited set before processing components
5. Increment depth counter; raise `MaxDepthExceededError` if > 10
6. Pass visited set and depth to recursive calls for nested FinishedGood components
7. Visited set is scoped to single top-level snapshot call (not global)

**Error messages**:
```python
class CircularReferenceError(Exception):
    """Raised when circular reference detected in FinishedGood hierarchy."""
    pass

class MaxDepthExceededError(Exception):
    """Raised when FinishedGood nesting exceeds maximum depth."""
    pass
```

**Rationale**: Simple, proven pattern. No database overhead. Clear error messages.

### RQ4: What is the Composition model component type coverage?

**Decision**: Support all polymorphic component types in Composition

**Component types in Composition model** (`src/models/composition.py`):
1. `finished_unit_id` → FinishedUnit component → Create FinishedUnitSnapshot
2. `finished_good_id` → FinishedGood component → Recursively create FinishedGoodSnapshot
3. `material_unit_id` → MaterialUnit component → Create MaterialUnitSnapshot
4. `material_id` → Generic Material placeholder → Store placeholder data (no snapshot, is_generic=True)
5. `packaging_product_id` → Packaging product → Out of scope (package snapshots deferred)

**Handling**:
- Types 1-3: Create corresponding snapshot, store snapshot_id in component data
- Type 4: Store material_id and is_generic=True, no MaterialUnitSnapshot created
- Type 5: Skip (package snapshots not in scope per spec)

**Rationale**: Complete coverage of FinishedGood composition. Package snapshots explicitly deferred.

### RQ5: What FK relationships should snapshot models have?

**Decision**: Dual optional FKs for planning and assembly contexts

**Model FKs**:
```python
# FinishedUnitSnapshot, FinishedGoodSnapshot, MaterialUnitSnapshot
finished_unit_id = Column(Integer, ForeignKey("finished_units.id", ondelete="RESTRICT"), nullable=False)
planning_snapshot_id = Column(Integer, ForeignKey("planning_snapshots.id", ondelete="CASCADE"), nullable=True)
assembly_run_id = Column(Integer, ForeignKey("assembly_runs.id", ondelete="CASCADE"), nullable=True)

# PlanningSnapshot
event_id = Column(Integer, ForeignKey("events.id", ondelete="SET NULL"), nullable=True)
```

**Cascade behavior**:
- `RESTRICT` on source catalog entity: Can't delete catalog item with snapshots
- `CASCADE` on container (PlanningSnapshot, AssemblyRun): Deleting container deletes snapshots
- `SET NULL` on Event: Event deletion preserves planning snapshot

**Rationale**: Matches RecipeSnapshot pattern. Protects historical data while allowing cleanup.

## Alternatives Considered

### Alternative 1: Separate snapshot models per context (Planning vs Assembly)

**Rejected because**: Would duplicate model definitions. Dual FK approach is simpler and matches how RecipeSnapshot works (one model, different contexts via FK).

### Alternative 2: Store full component snapshot data inline (no separate tables)

**Rejected because**: Would create massive JSON blobs for complex assemblies. Separate snapshot tables allow querying and joining.

### Alternative 3: Store only snapshot IDs, no denormalized data

**Rejected because**: Would require joins to reconstruct snapshot. Denormalized data ensures self-contained historical record even if referenced snapshots are somehow lost.

## Dependencies Confirmed

- RecipeSnapshot pattern: ✅ Verified in `src/models/recipe_snapshot.py`
- FinishedUnit model: ✅ Verified in `src/models/finished_unit.py`
- FinishedGood model: ✅ Verified in `src/models/finished_good.py`
- Composition model: ✅ Verified in `src/models/composition.py`
- MaterialUnit model: ✅ Verified in `src/models/material_unit.py`
- Session management pattern: ✅ Verified in `src/services/recipe_snapshot_service.py`
