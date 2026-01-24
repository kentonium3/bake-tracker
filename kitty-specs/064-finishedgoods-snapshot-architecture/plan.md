# Implementation Plan: FinishedGoods Snapshot Architecture

**Branch**: `064-finishedgoods-snapshot-architecture` | **Date**: 2025-01-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/064-finishedgoods-snapshot-architecture/spec.md`

## Summary

Implement immutable snapshot capture for FinishedUnit, FinishedGood, and MaterialUnit definitions at planning/assembly time, following the established RecipeSnapshot pattern. This completes the definition/instantiation separation principle across all catalog entities, ensuring historical accuracy for production records.

**Approach**: Primitives-first - deliver snapshot models and service primitives; defer Assembly/Planning service orchestration to later work packages.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter (UI - not affected by this feature)
**Storage**: SQLite with WAL mode
**Testing**: pytest with >70% service layer coverage target
**Target Platform**: Desktop (macOS/Windows)
**Project Type**: Single desktop application
**Performance Goals**: <5 seconds for complex snapshot trees (up to 50 components)
**Constraints**: Single-user, no migration scripts (reset/re-import strategy)
**Scale/Scope**: Dozens of FinishedGoods, max 10 nesting levels

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | ✅ PASS | Preserves historical accuracy for audit/cost tracking |
| II. Data Integrity & FIFO | ✅ PASS | Snapshots capture exact state at production time |
| III. Future-Proof Schema | ✅ PASS | JSON fields allow schema evolution without migrations |
| IV. Test-Driven Development | ✅ PASS | All primitives will have unit tests |
| V. Layered Architecture | ✅ PASS | Catalog services own snapshot creation (Pattern A) |
| VI. Schema Change Strategy | ✅ PASS | No migration needed - reset/re-import for schema changes |
| VII. Pragmatic Aspiration | ✅ PASS | Clean service layer supports future API wrapping |
| Desktop Phase Checks | ✅ PASS | Service layer UI-independent, supports JSON import |

**No violations requiring justification.**

## Project Structure

### Documentation (this feature)

```
kitty-specs/064-finishedgoods-snapshot-architecture/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
└── tasks/               # Work package prompts (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── finished_unit_snapshot.py    # NEW: FinishedUnitSnapshot model
│   ├── finished_good_snapshot.py    # NEW: FinishedGoodSnapshot model
│   ├── material_unit_snapshot.py    # NEW: MaterialUnitSnapshot model
│   ├── planning_snapshot.py         # NEW: PlanningSnapshot container
│   ├── __init__.py                  # UPDATE: Export new models
│   └── [existing models unchanged]
├── services/
│   ├── finished_unit_service.py     # UPDATE: Add create_finished_unit_snapshot()
│   ├── finished_good_service.py     # UPDATE: Add create_finished_good_snapshot()
│   ├── material_unit_service.py     # UPDATE: Add create_material_unit_snapshot()
│   ├── planning_snapshot_service.py # NEW: PlanningSnapshot container operations
│   └── [existing services unchanged]
└── tests/
    ├── test_finished_unit_snapshot.py   # NEW
    ├── test_finished_good_snapshot.py   # NEW
    ├── test_material_unit_snapshot.py   # NEW
    ├── test_planning_snapshot.py        # NEW
    └── [existing tests unchanged]
```

**Structure Decision**: Single project layout following existing patterns. New snapshot models mirror existing RecipeSnapshot structure. Service primitives added to existing catalog services per Pattern A (Catalog Service Ownership).

## Engineering Decisions

### Decision 1: Snapshot Data Storage

**Choice**: JSON Text columns (matching RecipeSnapshot pattern)

**Rationale**:
- Consistent with established RecipeSnapshot implementation
- Allows schema evolution without migration scripts
- SQLite compatible (no native JSON type)
- Sufficient for query needs (snapshot retrieval by ID/FK)

**Alternatives Rejected**:
- Mirrored relational tables: More complex, requires maintenance of parallel schema
- Binary serialization: Not human-readable, harder to debug

### Decision 2: Component Snapshot Structure

**Choice**: Store component snapshots as nested references in FinishedGoodSnapshot.definition_data JSON

**Structure**:
```python
{
    "slug": "holiday-cookie-box",
    "display_name": "Holiday Cookie Box",
    "assembly_type": "gift_box",
    "components": [
        {
            "component_type": "finished_unit",
            "snapshot_id": 123,  # Reference to FinishedUnitSnapshot
            "original_id": 45,   # Original catalog ID (for audit trail)
            "component_slug": "chocolate-chip-cookie",
            "component_name": "Chocolate Chip Cookie",
            "component_quantity": 6,
            "sort_order": 1
        },
        {
            "component_type": "material_unit",
            "snapshot_id": 456,  # Reference to MaterialUnitSnapshot
            "original_id": 78,
            "component_slug": "6-inch-red-ribbon",
            "component_name": "6-inch Red Ribbon",
            "component_quantity": 1,
            "sort_order": 2
        },
        {
            "component_type": "finished_good",
            "snapshot_id": 789,  # Reference to nested FinishedGoodSnapshot
            "original_id": 12,
            "component_slug": "cookie-sampler",
            "component_name": "Cookie Sampler",
            "component_quantity": 1,
            "sort_order": 3
        }
    ]
}
```

**Rationale**: Denormalized component data provides self-contained snapshot while snapshot_id references enable joining to full component details when needed.

### Decision 3: Circular Reference Prevention

**Choice**: Visited set tracking during recursive snapshot creation

**Implementation**:
- Pass `visited_ids: set[int]` through recursive calls
- Check before creating nested FinishedGood snapshot
- Raise `CircularReferenceError` with descriptive message
- Maximum depth counter (10 levels) as secondary safeguard

**Rationale**: Matches recipe component validation pattern. Simple, effective, no additional database structures needed.

### Decision 4: PlanningSnapshot Container

**Choice**: New model linking event_id to a collection of snapshots

**Structure**:
- `event_id` (FK, nullable - planning can exist without event)
- `created_at` timestamp
- Snapshots reference `planning_snapshot_id` (nullable FK)
- Enables querying all snapshots for a planning session

**Rationale**: Provides single point of reference for event planning operations. Enables atomic cleanup if plan is cancelled.

### Decision 5: Snapshot Linkage Strategy

**Choice**: Dual optional FKs on snapshot models

Each snapshot model has:
- `planning_snapshot_id` (nullable) - for planning-time snapshots
- `assembly_run_id` (nullable) - for assembly-time snapshots (future WP)

**Rationale**: Allows same snapshot model to serve both planning and assembly use cases. One will be set based on context.

## Work Package Overview

| WP | Name | Dependencies | Scope |
|----|------|--------------|-------|
| WP01 | FinishedUnitSnapshot Model + Service | None | Model, service primitive, tests |
| WP02 | MaterialUnitSnapshot Model + Service | None | Model, service primitive, tests |
| WP03 | FinishedGoodSnapshot Model + Service | WP01, WP02 | Model, recursive snapshot, circular detection, tests |
| WP04 | PlanningSnapshot Container | WP01, WP02, WP03 | Model, basic CRUD, tests |
| WP05 | Assembly Service Integration | WP03, WP04 | AssemblyRun FK, orchestration (deferred) |
| WP06 | Planning Service Integration | WP03, WP04 | Event planning orchestration (deferred) |

**Note**: WP05 and WP06 are deferred per engineering alignment (primitives-first approach).

## Reference Patterns

### RecipeSnapshot Model Pattern (to copy)

```python
# From src/models/recipe_snapshot.py
class RecipeSnapshot(BaseModel):
    __tablename__ = "recipe_snapshots"

    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False)
    production_run_id = Column(Integer, ForeignKey("production_runs.id", ondelete="CASCADE"), nullable=False, unique=True)
    scale_factor = Column(Float, nullable=False, default=1.0)
    snapshot_date = Column(DateTime, nullable=False, default=utc_now)
    recipe_data = Column(Text, nullable=False)  # JSON
    ingredients_data = Column(Text, nullable=False)  # JSON
    is_backfilled = Column(Boolean, nullable=False, default=False)
```

### Recipe Snapshot Service Pattern (to copy)

```python
# From src/services/recipe_snapshot_service.py
def create_recipe_snapshot(recipe_id, scale_factor, production_run_id, session=None):
    if session is not None:
        return _create_recipe_snapshot_impl(...)
    try:
        with session_scope() as session:
            return _create_recipe_snapshot_impl(...)
    except SQLAlchemyError as e:
        raise SnapshotCreationError(...)

def _create_recipe_snapshot_impl(recipe_id, scale_factor, production_run_id, session):
    # 1. Load entity with relationships
    # 2. Eagerly load nested relationships
    # 3. Build JSON data dict
    # 4. Create snapshot model
    # 5. session.add() and session.flush()
    # 6. Return dict with id and data
```

## Complexity Tracking

*No constitution violations requiring justification.*

| Pattern | Why Used | Simpler Alternative |
|---------|----------|---------------------|
| Recursive snapshot | Required for nested FinishedGoods | N/A - spec requirement |
| Visited set tracking | Circular reference prevention | N/A - safety requirement |
| JSON Text columns | Match RecipeSnapshot pattern | N/A - established pattern |
