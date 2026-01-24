# Data Model: Production Plan Snapshot Refactor

**Feature**: 065-production-plan-snapshot-refactor
**Date**: 2025-01-24
**Migration Strategy**: Reset/Re-import (no Alembic scripts)

## Schema Changes Overview

This refactoring modifies 3 models and verifies 1 model (F064):

| Model | Change Type | Description |
|-------|-------------|-------------|
| ProductionPlanSnapshot | MODIFY | Remove cache/staleness fields |
| RecipeSnapshot | MODIFY | Make production_run_id nullable |
| EventProductionTarget | MODIFY | Add recipe_snapshot_id FK |
| EventAssemblyTarget | MODIFY | Add finished_good_snapshot_id FK |
| FinishedGoodSnapshot | VERIFY | Confirm planning_snapshot_id exists (F064) |

---

## 1. ProductionPlanSnapshot

**File**: `src/models/production_plan_snapshot.py`

### Fields to REMOVE

```python
# DELETE these fields
calculation_results = Column(JSON, nullable=False)
requirements_updated_at = Column(DateTime, nullable=False)
recipes_updated_at = Column(DateTime, nullable=False)
bundles_updated_at = Column(DateTime, nullable=False)
is_stale = Column(Boolean, default=False, nullable=False)
stale_reason = Column(String(200), nullable=True)
```

### Fields to KEEP

```python
# KEEP these fields
id = Column(Integer, primary_key=True)
uuid = Column(String(36), unique=True, nullable=False)
event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
calculated_at = Column(DateTime, nullable=False)
input_hash = Column(String(64), nullable=True)  # Optional backup
shopping_complete = Column(Boolean, default=False, nullable=False)
shopping_completed_at = Column(DateTime, nullable=True)
created_at = Column(DateTime, nullable=False)
updated_at = Column(DateTime, nullable=False)
```

### Methods to REMOVE

```python
# DELETE these methods
def get_recipe_batches(self) -> list
def get_shopping_list(self) -> list
def get_aggregated_ingredients(self) -> list
def mark_stale(self, reason: str) -> None
def mark_fresh(self) -> None
```

### Final Model Structure

```python
class ProductionPlanSnapshot(BaseModel):
    """Lightweight container linking an event to its planning timestamp.

    References snapshots via EventProductionTarget.recipe_snapshot_id
    and EventAssemblyTarget.finished_good_snapshot_id.

    Calculation results are computed on-demand, not cached.
    """
    __tablename__ = "production_plan_snapshots"

    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    calculated_at = Column(DateTime, nullable=False)
    input_hash = Column(String(64), nullable=True)
    shopping_complete = Column(Boolean, default=False, nullable=False)
    shopping_completed_at = Column(DateTime, nullable=True)

    # Relationships
    event = relationship("Event", back_populates="production_plan_snapshots")
```

---

## 2. RecipeSnapshot

**File**: `src/models/recipe_snapshot.py`

### Current Structure

```python
production_run_id = Column(
    Integer,
    ForeignKey("production_runs.id", ondelete="CASCADE"),
    nullable=False,  # Currently required
    unique=True
)
```

### Modified Structure

```python
# Context FKs - at least one should be set
production_run_id = Column(
    Integer,
    ForeignKey("production_runs.id", ondelete="CASCADE"),
    nullable=True,  # CHANGED: now nullable for planning context
    unique=True     # Still unique when set
)

# Optional: Add planning_snapshot_id if direct container relationship desired
# Decision: NOT adding - using target FK instead (simpler)
```

### Validation Logic

Add validation to ensure at least one context is set:

```python
@validates('production_run_id')
def validate_context(self, key, value):
    """Ensure snapshot has valid context.

    For planning snapshots: production_run_id is None,
    referenced via EventProductionTarget.recipe_snapshot_id

    For production snapshots: production_run_id is set
    """
    # Allow None for planning context
    return value
```

---

## 3. EventProductionTarget

**File**: `src/models/event.py`

### Current Structure

```python
class EventProductionTarget(BaseModel):
    __tablename__ = "event_production_targets"

    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False)
    target_batches = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
```

### Add Field

```python
# NEW: Snapshot reference created at planning time
recipe_snapshot_id = Column(
    Integer,
    ForeignKey("recipe_snapshots.id", ondelete="RESTRICT"),
    nullable=True,  # Backward compatibility for legacy events
    index=True
)

# Add relationship
recipe_snapshot = relationship("RecipeSnapshot", foreign_keys=[recipe_snapshot_id])
```

### Constraint Consideration

```python
# Unique constraint remains on (event_id, recipe_id)
__table_args__ = (
    UniqueConstraint('event_id', 'recipe_id', name='uq_event_production_target'),
)
```

---

## 4. EventAssemblyTarget

**File**: `src/models/event.py`

### Current Structure

```python
class EventAssemblyTarget(BaseModel):
    __tablename__ = "event_assembly_targets"

    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    finished_good_id = Column(Integer, ForeignKey("finished_goods.id", ondelete="RESTRICT"), nullable=False)
    target_quantity = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
```

### Add Field

```python
# NEW: Snapshot reference created at planning time (F064 complete)
finished_good_snapshot_id = Column(
    Integer,
    ForeignKey("finished_good_snapshots.id", ondelete="RESTRICT"),
    nullable=True,  # Backward compatibility for legacy events
    index=True
)

# Add relationship
finished_good_snapshot = relationship("FinishedGoodSnapshot", foreign_keys=[finished_good_snapshot_id])
```

---

## 5. FinishedGoodSnapshot (Verify F064)

**File**: `src/models/finished_good_snapshot.py`

### Expected Structure (F064)

```python
class FinishedGoodSnapshot(BaseModel):
    __tablename__ = "finished_good_snapshots"

    finished_good_id = Column(
        Integer,
        ForeignKey("finished_goods.id", ondelete="RESTRICT"),
        nullable=False
    )
    planning_snapshot_id = Column(
        Integer,
        ForeignKey("planning_snapshots.id", ondelete="CASCADE"),
        nullable=True  # Planning context
    )
    assembly_run_id = Column(
        Integer,
        ForeignKey("assembly_runs.id", ondelete="CASCADE"),
        nullable=True  # Assembly context
    )
    snapshot_date = Column(DateTime, nullable=False)
    is_backfilled = Column(Boolean, default=False)
    definition_data = Column(Text, nullable=False)  # JSON blob
```

### Verification Checklist

- [ ] `planning_snapshot_id` FK exists and is nullable
- [ ] `assembly_run_id` FK exists and is nullable
- [ ] Both can be null (validation ensures at least one context)
- [ ] ON DELETE CASCADE for both context FKs
- [ ] ON DELETE RESTRICT for finished_good_id

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                           Event                                  │
│  - id, name, date, output_mode, etc.                            │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         │ 1:N                │ 1:N                │ 1:N
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐
│ EventProduction │  │ EventAssembly   │  │ ProductionPlanSnapshot  │
│ Target          │  │ Target          │  │ (lightweight container) │
├─────────────────┤  ├─────────────────┤  ├─────────────────────────┤
│ event_id (FK)   │  │ event_id (FK)   │  │ event_id (FK)           │
│ recipe_id (FK)  │  │ finished_good_id│  │ calculated_at           │
│ target_batches  │  │ target_quantity │  │ shopping_complete       │
│ NEW: recipe_    │  │ NEW: finished_  │  └─────────────────────────┘
│   snapshot_id   │  │   good_snapshot │
└────────┬────────┘  │   _id           │
         │           └────────┬────────┘
         │ N:1                │ N:1
         ▼                    ▼
┌─────────────────┐  ┌─────────────────────┐
│ RecipeSnapshot  │  │ FinishedGoodSnapshot│
├─────────────────┤  ├─────────────────────┤
│ recipe_id (FK)  │  │ finished_good_id    │
│ NULLABLE:       │  │ planning_snapshot_id│
│   production_   │  │ assembly_run_id     │
│   run_id        │  │ definition_data     │
│ scale_factor    │  └─────────────────────┘
│ recipe_data     │
│ ingredients_data│
└─────────────────┘
```

---

## Foreign Key Behaviors

| Source | Target | ON DELETE | Rationale |
|--------|--------|-----------|-----------|
| ProductionPlanSnapshot.event_id | Event | CASCADE | Delete plan when event deleted |
| EventProductionTarget.event_id | Event | CASCADE | Delete targets with event |
| EventProductionTarget.recipe_id | Recipe | RESTRICT | Prevent deletion of used recipes |
| EventProductionTarget.recipe_snapshot_id | RecipeSnapshot | RESTRICT | Preserve snapshot integrity |
| EventAssemblyTarget.event_id | Event | CASCADE | Delete targets with event |
| EventAssemblyTarget.finished_good_id | FinishedGood | RESTRICT | Prevent deletion of used FGs |
| EventAssemblyTarget.finished_good_snapshot_id | FinishedGoodSnapshot | RESTRICT | Preserve snapshot integrity |
| RecipeSnapshot.recipe_id | Recipe | RESTRICT | Preserve catalog reference |
| RecipeSnapshot.production_run_id | ProductionRun | CASCADE | Delete orphan snapshots |

---

## Index Recommendations

```python
# EventProductionTarget
Index('ix_event_production_target_snapshot', 'recipe_snapshot_id')

# EventAssemblyTarget
Index('ix_event_assembly_target_snapshot', 'finished_good_snapshot_id')

# RecipeSnapshot (if not already indexed)
Index('ix_recipe_snapshot_recipe', 'recipe_id')
```

---

## Migration Notes

### Reset/Re-import Strategy

Per constitution Principle VI, this uses export → reset → import cycle:

1. **Export**: `python -m src.services.import_export_service export all_data.json`
2. **Reset**: Delete database, update models, recreate empty database
3. **Transform** (if needed): JSON transformation script for schema changes
4. **Import**: `python -m src.services.import_export_service import all_data.json`

### Data Transformation

For existing data:
- `ProductionPlanSnapshot.calculation_results` - Not migrated (recalculated on-demand)
- `ProductionPlanSnapshot` staleness fields - Not migrated (removed)
- `EventProductionTarget.recipe_snapshot_id` - Null for legacy data
- `EventAssemblyTarget.finished_good_snapshot_id` - Null for legacy data

### Backward Compatibility

Legacy events (no snapshots) continue to work:
- Production service creates snapshot at execution time if target has no snapshot
- Assembly service creates snapshot at execution time if target has no snapshot
- Null FK values are valid for legacy data
