---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
  - "T008"
  - "T009"
title: "Model Layer - Schema Changes"
phase: "Phase 1 - Model Layer"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "78906"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-10T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Model Layer - Schema Changes

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Add all schema changes for event-centric production: new models, FK additions, and relationships.

**Success Criteria**:
- FulfillmentStatus enum exists with values: pending, ready, delivered
- EventProductionTarget model exists with unique constraint on (event_id, recipe_id)
- EventAssemblyTarget model exists with unique constraint on (event_id, finished_good_id)
- ProductionRun and AssemblyRun have nullable event_id FK with RESTRICT on delete
- EventRecipientPackage has fulfillment_status column with default 'pending'
- Event model has relationships to all new/modified models
- All new classes exported from `src/models/__init__.py`
- Database creates successfully with new schema

## Context & Constraints

**Reference Documents**:
- `kitty-specs/016-event-centric-production/spec.md` - FR-001 through FR-010
- `kitty-specs/016-event-centric-production/data-model.md` - Full entity specifications
- `kitty-specs/016-event-centric-production/research.md` - Codebase analysis

**Architectural Constraints**:
- Use SQLAlchemy 2.x patterns
- Follow existing BaseModel pattern (uuid, created_at, updated_at)
- Use string references for forward declarations to avoid circular imports
- RESTRICT cascade for ProductionRun/AssemblyRun event_id FK
- CASCADE delete for target tables when Event deleted

---

## Subtasks & Detailed Guidance

### Subtask T001 - Add FulfillmentStatus enum to src/models/event.py

**Purpose**: Define the enum for package workflow states before other models use it.

**Steps**:
1. Open `src/models/event.py`
2. Add import: `from enum import Enum`
3. Add FulfillmentStatus class before EventRecipientPackage:
   ```python
   class FulfillmentStatus(str, Enum):
       PENDING = "pending"
       READY = "ready"
       DELIVERED = "delivered"
   ```

**Files**: `src/models/event.py`
**Parallel?**: No (other subtasks depend on this)
**Notes**: Inheriting from `str` allows direct string comparison and JSON serialization.

---

### Subtask T002 - Add EventProductionTarget model to src/models/event.py

**Purpose**: Store recipe batch targets for events with unique constraint.

**Steps**:
1. Add model class after Event class:
   ```python
   class EventProductionTarget(BaseModel):
       __tablename__ = "event_production_target"

       event_id = Column(Integer, ForeignKey("event.id", ondelete="CASCADE"), nullable=False, index=True)
       recipe_id = Column(Integer, ForeignKey("recipe.id", ondelete="RESTRICT"), nullable=False, index=True)
       target_batches = Column(Integer, nullable=False)
       notes = Column(Text)

       # Relationships
       event = relationship("Event", back_populates="production_targets")
       recipe = relationship("Recipe")

       __table_args__ = (
           UniqueConstraint("event_id", "recipe_id", name="uq_event_recipe_target"),
           CheckConstraint("target_batches > 0", name="ck_target_batches_positive"),
       )
   ```
2. Add required imports: `from sqlalchemy import UniqueConstraint, CheckConstraint`

**Files**: `src/models/event.py`
**Parallel?**: Yes (T003 can proceed concurrently)
**Notes**: Use string reference for relationship if Recipe not yet imported.

---

### Subtask T003 - Add EventAssemblyTarget model to src/models/event.py

**Purpose**: Store finished good quantity targets for events with unique constraint.

**Steps**:
1. Add model class after EventProductionTarget:
   ```python
   class EventAssemblyTarget(BaseModel):
       __tablename__ = "event_assembly_target"

       event_id = Column(Integer, ForeignKey("event.id", ondelete="CASCADE"), nullable=False, index=True)
       finished_good_id = Column(Integer, ForeignKey("finished_good.id", ondelete="RESTRICT"), nullable=False, index=True)
       target_quantity = Column(Integer, nullable=False)
       notes = Column(Text)

       # Relationships
       event = relationship("Event", back_populates="assembly_targets")
       finished_good = relationship("FinishedGood")

       __table_args__ = (
           UniqueConstraint("event_id", "finished_good_id", name="uq_event_fg_target"),
           CheckConstraint("target_quantity > 0", name="ck_target_quantity_positive"),
       )
   ```

**Files**: `src/models/event.py`
**Parallel?**: Yes (T002 can proceed concurrently)
**Notes**: Use string reference for FinishedGood relationship.

---

### Subtask T004 - Add event_id FK column to src/models/production_run.py

**Purpose**: Enable linking production runs to events for progress tracking.

**Steps**:
1. Open `src/models/production_run.py`
2. Add column after existing columns:
   ```python
   event_id = Column(Integer, ForeignKey("event.id", ondelete="RESTRICT"), nullable=True, index=True)
   ```
3. Add relationship:
   ```python
   event = relationship("Event", back_populates="production_runs")
   ```

**Files**: `src/models/production_run.py`
**Parallel?**: No (T005 is parallel, but T004 must complete before T007)
**Notes**: RESTRICT prevents deleting events with attributed production.

---

### Subtask T005 - Add event_id FK column to src/models/assembly_run.py

**Purpose**: Enable linking assembly runs to events for progress tracking.

**Steps**:
1. Open `src/models/assembly_run.py`
2. Add column after existing columns:
   ```python
   event_id = Column(Integer, ForeignKey("event.id", ondelete="RESTRICT"), nullable=True, index=True)
   ```
3. Add relationship:
   ```python
   event = relationship("Event", back_populates="assembly_runs")
   ```

**Files**: `src/models/assembly_run.py`
**Parallel?**: Yes (can proceed with T004)
**Notes**: RESTRICT prevents deleting events with attributed assembly.

---

### Subtask T006 - Add fulfillment_status column to EventRecipientPackage

**Purpose**: Track package workflow state (pending/ready/delivered).

**Steps**:
1. In `src/models/event.py`, find EventRecipientPackage class
2. Add column:
   ```python
   fulfillment_status = Column(
       String(20),
       nullable=False,
       default=FulfillmentStatus.PENDING.value
   )
   ```

**Files**: `src/models/event.py`
**Parallel?**: No (depends on T001)
**Notes**: Default to 'pending' for new and existing records after migration.

---

### Subtask T007 - Add relationships to Event model

**Purpose**: Enable navigation from Event to production runs, assembly runs, and targets.

**Steps**:
1. In `src/models/event.py`, find Event class
2. Add relationships:
   ```python
   # New relationships for v0.6
   production_runs = relationship("ProductionRun", back_populates="event")
   assembly_runs = relationship("AssemblyRun", back_populates="event")
   production_targets = relationship("EventProductionTarget", back_populates="event", cascade="all, delete-orphan")
   assembly_targets = relationship("EventAssemblyTarget", back_populates="event", cascade="all, delete-orphan")
   ```

**Files**: `src/models/event.py`
**Parallel?**: No (depends on T002, T003, T004, T005)
**Notes**: Use cascade="all, delete-orphan" for targets to enable cascade delete.

---

### Subtask T008 - Update src/models/__init__.py to export new classes

**Purpose**: Make new models importable from the models package.

**Steps**:
1. Open `src/models/__init__.py`
2. Add imports:
   ```python
   from .event import FulfillmentStatus, EventProductionTarget, EventAssemblyTarget
   ```
3. Add to `__all__` list:
   ```python
   "FulfillmentStatus",
   "EventProductionTarget",
   "EventAssemblyTarget",
   ```

**Files**: `src/models/__init__.py`
**Parallel?**: No (must be last)
**Notes**: Verify import order doesn't cause circular import issues.

---

### Subtask T009 - Update to_dict() methods in ProductionRun and AssemblyRun

**Purpose**: Include event_id and event_name in serialization for export/import.

**Steps**:
1. In `src/models/production_run.py`, update `to_dict()`:
   ```python
   def to_dict(self, include_relationships=False):
       d = {
           # ... existing fields ...
           "event_id": self.event_id,
       }
       if include_relationships:
           d["event_name"] = self.event.name if self.event else None
       return d
   ```
2. Apply same pattern to `src/models/assembly_run.py`

**Files**: `src/models/production_run.py`, `src/models/assembly_run.py`
**Parallel?**: No
**Notes**: Check if to_dict method exists; create if needed following existing patterns.

---

## Test Strategy

**Model Tests** (create `src/tests/models/test_event_models.py` if needed):
1. Test FulfillmentStatus enum values
2. Test EventProductionTarget creation and unique constraint
3. Test EventAssemblyTarget creation and unique constraint
4. Test ProductionRun with event_id set/null
5. Test cascade behavior: delete Event with targets (should cascade)
6. Test restrict behavior: delete Event with production (should fail)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Circular imports | Use string references for relationships across files |
| Existing data migration | Document: export data before recreating database |
| Missing imports | Run `python -c "from src.models import *"` to verify |

---

## Definition of Done Checklist

- [ ] FulfillmentStatus enum defined
- [ ] EventProductionTarget model with unique constraint
- [ ] EventAssemblyTarget model with unique constraint
- [ ] ProductionRun.event_id FK added
- [ ] AssemblyRun.event_id FK added
- [ ] EventRecipientPackage.fulfillment_status added
- [ ] Event relationships updated
- [ ] __init__.py exports updated
- [ ] to_dict() methods updated
- [ ] Models import without error: `python -c "from src.models import *"`
- [ ] Database creates with new schema (delete and recreate to test)
- [ ] `tasks.md` updated with status change

---

## Review Guidance

**Reviewers should verify**:
1. All FK constraints have correct ondelete behavior (RESTRICT vs CASCADE)
2. Unique constraints have meaningful names
3. CheckConstraints enforce positive values
4. Relationships use back_populates correctly
5. All new classes exported from __init__.py
6. No circular import issues when importing models

---

## Activity Log

- 2025-12-10T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-11T02:42:44Z – claude – shell_pid=78906 – lane=doing – Started implementation of model layer schema changes
