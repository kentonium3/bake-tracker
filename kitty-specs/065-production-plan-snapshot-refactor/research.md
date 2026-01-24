# Research: Production Plan Snapshot Refactor

**Feature**: 065-production-plan-snapshot-refactor
**Date**: 2025-01-24
**Status**: Complete

## Research Questions

### RQ-1: Current ProductionPlanSnapshot Architecture

**Question**: What is the current structure of ProductionPlanSnapshot and what needs to change?

**Findings**:

Location: `src/models/production_plan_snapshot.py`

**Current Fields (TO BE REMOVED)**:
- `calculation_results` (JSON) - stores recipe_batches, aggregated_ingredients, shopping_list
- `requirements_updated_at` (DateTime) - latest timestamp from targets
- `recipes_updated_at` (DateTime) - latest from recipes
- `bundles_updated_at` (DateTime) - latest from finished goods
- `is_stale` (Boolean) - staleness flag
- `stale_reason` (String) - human-readable reason

**Current Fields (TO KEEP)**:
- `event_id` (FK) - primary reference
- `calculated_at` (DateTime) - when plan was created
- `shopping_complete` (Boolean) - operational state
- `shopping_completed_at` (DateTime) - completion timestamp
- `input_hash` (String, optional) - backup staleness check

**Key Methods to Remove**:
- `get_recipe_batches()` - extracts from calculation_results
- `get_shopping_list()` - extracts from calculation_results
- `get_aggregated_ingredients()` - extracts from calculation_results
- `mark_stale()` / `mark_fresh()` - staleness management

**Decision**: Remove all cache-related fields and methods. ProductionPlanSnapshot becomes a lightweight container.

---

### RQ-2: Existing Snapshot Patterns

**Question**: What patterns do RecipeSnapshot and FinishedGoodSnapshot use that we should follow?

**Findings**:

#### RecipeSnapshot (`src/models/recipe_snapshot.py`)

```python
class RecipeSnapshot(BaseModel):
    recipe_id = ForeignKey("recipes.id", ondelete="RESTRICT")
    production_run_id = ForeignKey("production_runs.id", ondelete="CASCADE", unique=True)
    scale_factor = Float
    snapshot_date = DateTime
    recipe_data = Text  # JSON blob
    ingredients_data = Text  # JSON blob
    is_backfilled = Boolean
```

**Key Pattern**:
- `production_run_id` is currently NOT nullable - requires production context
- ON DELETE RESTRICT for catalog reference (recipe_id)
- ON DELETE CASCADE for context reference (production_run_id)
- JSON Text columns for denormalized snapshot data
- 1:1 relationship with ProductionRun (unique constraint)

**F065 Change Required**: Make `production_run_id` nullable to support planning context.

#### FinishedGoodSnapshot (`src/models/finished_good_snapshot.py`)

```python
class FinishedGoodSnapshot(BaseModel):
    finished_good_id = ForeignKey("finished_goods.id", ondelete="RESTRICT")
    planning_snapshot_id = ForeignKey("planning_snapshots.id", ondelete="CASCADE", nullable=True)
    assembly_run_id = ForeignKey("assembly_runs.id", ondelete="CASCADE", nullable=True)
    snapshot_date = DateTime
    is_backfilled = Boolean
    definition_data = Text  # JSON blob
```

**Key Pattern**:
- **Dual context FKs**: exactly one of `planning_snapshot_id` or `assembly_run_id` should be set
- Both FKs are nullable - allows either planning or assembly context
- This is the pattern RecipeSnapshot should follow

**Decision**: RecipeSnapshot should adopt the FinishedGoodSnapshot dual-context FK pattern.

---

### RQ-3: Planning Service Workflow

**Question**: How does the current planning service work and what needs to change?

**Findings**:

Location: `src/services/planning/planning_service.py`

**Current `calculate_plan()` Workflow**:
1. Validate event and output_mode
2. Get existing plan (unless force_recalculate)
3. Check staleness via `_check_staleness_impl()`
4. Calculate batch requirements
5. Get timestamp information from targets and definitions
6. Get shopping list
7. Aggregate ingredients
8. Create ProductionPlanSnapshot with `calculation_results` JSON blob
9. Return plan data

**Staleness Detection (`_check_staleness_impl()`)**:
Compares `calculated_at` against:
- Event.last_modified
- EventAssemblyTarget.updated_at (all)
- EventProductionTarget.updated_at (all)
- Recipe.last_modified (each in plan)
- FinishedGood.updated_at (each)
- Composition.created_at/updated_at (bundle contents)
- FinishedUnit.updated_at (yield changes)

**F065 Target Workflow**:
1. Validate event and output_mode
2. For each production target: create RecipeSnapshot, link to target
3. For each assembly target: create FinishedGoodSnapshot, link to target
4. Create ProductionPlanSnapshot as container (no calculation_results)
5. Return success indicator

**New `get_plan_summary()` Function**:
1. Load event with targets and linked snapshots
2. Calculate batch requirements from snapshots
3. Calculate shopping list from snapshots
4. Return calculated data (no caching)

**Decision**: Split into create_plan() (snapshot creation) and get_plan_summary() (on-demand calculation).

---

### RQ-4: Production/Assembly Snapshot Reuse

**Question**: How should production and assembly services reuse planning snapshots?

**Findings**:

#### Current Batch Production (`src/services/batch_production_service.py`)

`record_batch_production()`:
- Creates new RecipeSnapshot at production time
- No awareness of planning snapshots
- Snapshot always created fresh

#### Current Assembly (`src/services/assembly_service.py`)

`record_assembly()`:
- Creates FinishedGoodSnapshot chain at assembly time (F064)
- No awareness of planning snapshots

**F065 Target Pattern**:

```python
def record_batch_production(recipe_id, quantity, event_id=None, session=None):
    # Check if production is for a planned event target
    snapshot_id = None
    if event_id:
        target = get_production_target(event_id, recipe_id, session)
        if target and target.recipe_snapshot_id:
            # Use snapshot created during planning
            snapshot_id = target.recipe_snapshot_id

    # If no planning snapshot, create one now (backward compatibility)
    if not snapshot_id:
        recipe_snapshot = recipe_snapshot_service.create_recipe_snapshot(
            recipe_id=recipe_id,
            production_run_id=production_run.id,
            session=session
        )
        snapshot_id = recipe_snapshot["id"]

    production_run.recipe_snapshot_id = snapshot_id
```

**Decision**: Check for existing planning snapshot before creating new one. Create at execution time only for legacy/ad-hoc production.

---

### RQ-5: Target Model Changes

**Question**: What changes are needed to EventProductionTarget and EventAssemblyTarget?

**Findings**:

Location: `src/models/event.py` (lines 329-474)

**Current EventProductionTarget**:
```python
event_id = ForeignKey("events.id", ondelete="CASCADE")
recipe_id = ForeignKey("recipes.id", ondelete="RESTRICT")
target_batches = Integer
notes = Text
```

**Current EventAssemblyTarget**:
```python
event_id = ForeignKey("events.id", ondelete="CASCADE")
finished_good_id = ForeignKey("finished_goods.id", ondelete="RESTRICT")
target_quantity = Integer
notes = Text
```

**F065 Additions**:

```python
# EventProductionTarget
recipe_snapshot_id = ForeignKey(
    "recipe_snapshots.id",
    ondelete="RESTRICT",
    nullable=True  # Backward compatibility
)

# EventAssemblyTarget
finished_good_snapshot_id = ForeignKey(
    "finished_good_snapshots.id",
    ondelete="RESTRICT",
    nullable=True  # Backward compatibility
)
```

**Decision**: Add nullable snapshot FK to each target model. ON DELETE RESTRICT prevents orphaning.

---

### RQ-6: PlanningSnapshot Container (F064)

**Question**: Does the existing PlanningSnapshot container support this refactor?

**Findings**:

Location: `src/models/planning_snapshot.py`

```python
class PlanningSnapshot(BaseModel):
    event_id = ForeignKey("events.id", ondelete="SET NULL", nullable=True)
    created_at = DateTime
    notes = Text

    # Cascade relationships
    finished_unit_snapshots = relationship(cascade="all, delete-orphan")
    material_unit_snapshots = relationship(cascade="all, delete-orphan")
    finished_good_snapshots = relationship(cascade="all, delete-orphan")
```

**Analysis**:
- PlanningSnapshot is a container for finished good/unit snapshots from F064
- Does NOT include recipe snapshots
- Designed for assembly context, not production context

**Options**:
1. Extend PlanningSnapshot to include recipe snapshots
2. Keep RecipeSnapshot linked via target (no container relationship)
3. Create separate mechanism for production snapshots

**Decision**: Option 2 - Link RecipeSnapshot via EventProductionTarget.recipe_snapshot_id. This is simpler and matches the target-centric architecture. PlanningSnapshot remains for assembly context only.

---

### RQ-7: Session Management Requirements

**Question**: What session management patterns must be followed?

**Findings**:

Per CLAUDE.md Session Management section:

**Anti-Pattern (causes silent data loss)**:
```python
def outer_function():
    with session_scope() as session:
        obj = session.query(Model).first()
        inner_function()  # Nested session_scope detaches obj
        obj.field = value  # SILENTLY LOST
```

**Correct Pattern**:
```python
def outer_function():
    with session_scope() as session:
        obj = session.query(Model).first()
        inner_function(session=session)  # Pass session
        obj.field = value  # Persists correctly

def inner_function(session=None):
    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)
```

**F065 Application**:
- `planning_service.create_plan()` must pass session to:
  - `recipe_snapshot_service.create_recipe_snapshot(session=session)`
  - `finished_good_service.create_finished_good_snapshot(session=session)`
  - Target FK updates

**Decision**: All service functions must accept optional session parameter and pass it through.

---

## Summary of Decisions

| Topic | Decision | Rationale |
|-------|----------|-----------|
| ProductionPlanSnapshot | Remove cache fields, keep as container | Matches Pattern A architecture |
| RecipeSnapshot context | Make production_run_id nullable | Enables planning context |
| Target snapshot FKs | Add nullable FKs to targets | Direct reference, backward compatible |
| Snapshot creation | Create at plan time, reuse at execution | Single source of truth |
| Calculation | On-demand from snapshots | Eliminates staleness entirely |
| PlanningSnapshot role | Keep for assembly only | Simpler than extending |
| Session management | Pass session through all calls | Prevents detached object bugs |

## Files to Modify

### Models
- `src/models/production_plan_snapshot.py` - Remove cache fields
- `src/models/recipe_snapshot.py` - Make production_run_id nullable
- `src/models/event.py` - Add snapshot FKs to targets

### Services
- `src/services/planning/planning_service.py` - Create snapshots at plan time
- `src/services/batch_production_service.py` - Reuse planning snapshots
- `src/services/assembly_service.py` - Reuse planning snapshots
- `src/services/recipe_snapshot_service.py` - Support planning context

### UI
- Planning views - Remove staleness UI, use on-demand calculation
