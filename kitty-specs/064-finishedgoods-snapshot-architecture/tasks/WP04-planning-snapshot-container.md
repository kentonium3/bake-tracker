---
work_package_id: WP04
title: PlanningSnapshot Container
lane: "doing"
dependencies: [WP01, WP02, WP03]
base_branch: 064-finishedgoods-snapshot-architecture-WP03
base_commit: 98fadf2cddb70706811c213f524311e10316dad5
created_at: '2026-01-24T18:19:32.379156+00:00'
subtasks:
- T019
- T020
- T021
- T022
- T023
- T024
- T025
phase: Phase 3 - Container
assignee: ''
agent: "claude-opus"
shell_pid: "62838"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2025-01-24T05:30:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – PlanningSnapshot Container

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Create the PlanningSnapshot container model and service for grouping snapshots by planning session:

- **PlanningSnapshot model** linking optional event_id to a collection of snapshots
- **Service functions** for creating, querying, and deleting planning snapshots
- **Relationships** to all three snapshot types (FinishedUnit, MaterialUnit, FinishedGood)
- **Cascade deletion** - deleting PlanningSnapshot removes all associated snapshots

**Success Criteria**:
- [ ] PlanningSnapshot model matches data-model.md specification
- [ ] Event.planning_snapshots relationship enables navigation from Event
- [ ] `get_planning_snapshot()` returns aggregated view with all linked snapshots
- [ ] `delete_planning_snapshot()` cascades to all child snapshots
- [ ] Unit tests validate CRUD operations and cascade behavior

## Context & Constraints

**Reference Documents**:
- `kitty-specs/064-finishedgoods-snapshot-architecture/data-model.md` - Entity definitions
- `src/models/event.py` - Event model for relationship addition
- WP01-03 implementations - Snapshot models that reference PlanningSnapshot

**Dependencies**:
- **WP01**: FinishedUnitSnapshot model must exist
- **WP02**: MaterialUnitSnapshot model must exist
- **WP03**: FinishedGoodSnapshot model must exist

**Important**: This WP completes the relationships defined in WP01-03. The `planning_snapshot` relationship on snapshot models references PlanningSnapshot which is created here.

**Implementation Command**:
```bash
spec-kitty implement WP04 --base WP03
```

## Subtasks & Detailed Guidance

### Subtask T019 – Create PlanningSnapshot model

**Purpose**: Define the SQLAlchemy model for planning session containers.

**File**: `src/models/planning_snapshot.py`

**Steps**:

1. Create new file with module docstring:
   ```python
   """
   PlanningSnapshot model for grouping snapshots by planning session.

   Container record that links an optional event to all snapshots created
   during plan finalization. Enables atomic cleanup and event-scoped queries.
   """
   ```

2. Add imports:
   ```python
   from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, Index
   from sqlalchemy.orm import relationship
   from .base import BaseModel
   from src.utils.datetime_utils import utc_now
   ```

3. Define model class:
   ```python
   class PlanningSnapshot(BaseModel):
       __tablename__ = "planning_snapshots"

       # Optional event linkage (SET NULL: event deletion preserves snapshot)
       event_id = Column(
           Integer,
           ForeignKey("events.id", ondelete="SET NULL"),
           nullable=True,
           index=True
       )

       # Metadata
       created_at = Column(DateTime, nullable=False, default=utc_now)
       notes = Column(Text, nullable=True)

       # Relationships to Event
       event = relationship("Event", back_populates="planning_snapshots")

       # Relationships to snapshot types (one-to-many)
       # CASCADE: deleting PlanningSnapshot deletes all child snapshots
       finished_unit_snapshots = relationship(
           "FinishedUnitSnapshot",
           back_populates="planning_snapshot",
           cascade="all, delete-orphan",
           lazy="dynamic"
       )
       finished_good_snapshots = relationship(
           "FinishedGoodSnapshot",
           back_populates="planning_snapshot",
           cascade="all, delete-orphan",
           lazy="dynamic"
       )
       material_unit_snapshots = relationship(
           "MaterialUnitSnapshot",
           back_populates="planning_snapshot",
           cascade="all, delete-orphan",
           lazy="dynamic"
       )

       __table_args__ = (
           Index("idx_planning_snapshot_event", "event_id"),
           Index("idx_planning_snapshot_created", "created_at"),
       )

       def __repr__(self) -> str:
           return f"PlanningSnapshot(id={self.id}, event_id={self.event_id})"
   ```

**Validation**:
- [ ] event_id FK uses ondelete="SET NULL"
- [ ] All three snapshot relationships have cascade="all, delete-orphan"
- [ ] Indexes present

---

### Subtask T020 – Add to models `__init__.py`

**Purpose**: Export PlanningSnapshot.

**File**: `src/models/__init__.py`

**Steps**:

1. Add import:
   ```python
   from .planning_snapshot import PlanningSnapshot
   ```

2. Add to `__all__` list

**Parallel?**: Yes - can run alongside T019

---

### Subtask T021 – Add Event.planning_snapshots relationship

**Purpose**: Enable navigation from Event to its planning snapshots.

**File**: `src/models/event.py`

**Steps**:

1. Add relationship to Event class:
   ```python
   # Planning snapshots (Feature 064)
   planning_snapshots = relationship(
       "PlanningSnapshot",
       back_populates="event",
       lazy="dynamic"
   )
   ```

2. Verify bidirectional navigation works

**Note**: This completes the bidirectional relationship defined in T019.

**Parallel?**: Yes - can run alongside T019, T020

---

### Subtask T022 – Create planning_snapshot_service.py with CRUD

**Purpose**: Implement service layer for PlanningSnapshot operations.

**File**: `src/services/planning_snapshot_service.py`

**Steps**:

1. Create new file with imports:
   ```python
   """
   PlanningSnapshot Service for F064 FinishedGoods Snapshot Architecture.

   Provides container management for grouping snapshots by planning session.
   """
   from typing import Optional
   from sqlalchemy.orm import Session
   from sqlalchemy.exc import SQLAlchemyError

   from src.models import PlanningSnapshot
   from src.services.database import session_scope
   from src.utils.datetime_utils import utc_now


   class PlanningSnapshotError(Exception):
       """Raised when PlanningSnapshot operations fail."""
       pass
   ```

2. Add create function:
   ```python
   def create_planning_snapshot(
       event_id: int = None,
       notes: str = None,
       session: Session = None
   ) -> dict:
       """
       Create empty PlanningSnapshot container.

       Args:
           event_id: Optional event to link
           notes: Optional notes
           session: Optional session for transaction sharing

       Returns:
           dict with planning_snapshot id and created_at
       """
       if session is not None:
           return _create_planning_snapshot_impl(event_id, notes, session)

       try:
           with session_scope() as session:
               return _create_planning_snapshot_impl(event_id, notes, session)
       except SQLAlchemyError as e:
           raise PlanningSnapshotError(f"Database error creating planning snapshot: {e}")


   def _create_planning_snapshot_impl(
       event_id: int,
       notes: str,
       session: Session
   ) -> dict:
       """Internal implementation."""
       ps = PlanningSnapshot(
           event_id=event_id,
           notes=notes,
       )
       session.add(ps)
       session.flush()

       return {
           "id": ps.id,
           "event_id": ps.event_id,
           "created_at": ps.created_at.isoformat(),
           "notes": ps.notes,
       }
   ```

---

### Subtask T023 – Add get_planning_snapshot() with aggregation

**Purpose**: Retrieve planning snapshot with all linked snapshots.

**File**: `src/services/planning_snapshot_service.py`

**Steps**:

1. Add aggregation function:
   ```python
   def get_planning_snapshot(
       planning_snapshot_id: int,
       include_snapshots: bool = True,
       session: Session = None
   ) -> dict | None:
       """
       Get planning snapshot with optionally all linked snapshots.

       Args:
           planning_snapshot_id: PlanningSnapshot ID
           include_snapshots: If True, include all linked snapshot data
           session: Optional session

       Returns:
           dict with planning snapshot and linked snapshots, or None
       """
       if session is not None:
           return _get_planning_snapshot_impl(
               planning_snapshot_id, include_snapshots, session
           )

       with session_scope() as session:
           return _get_planning_snapshot_impl(
               planning_snapshot_id, include_snapshots, session
           )


   def _get_planning_snapshot_impl(
       planning_snapshot_id: int,
       include_snapshots: bool,
       session: Session
   ) -> dict | None:
       ps = session.query(PlanningSnapshot).filter_by(id=planning_snapshot_id).first()

       if not ps:
           return None

       result = {
           "id": ps.id,
           "event_id": ps.event_id,
           "created_at": ps.created_at.isoformat(),
           "notes": ps.notes,
       }

       if include_snapshots:
           # Aggregate all linked snapshots
           result["finished_unit_snapshots"] = [
               {
                   "id": s.id,
                   "finished_unit_id": s.finished_unit_id,
                   "snapshot_date": s.snapshot_date.isoformat(),
                   "definition_data": s.get_definition_data(),
               }
               for s in ps.finished_unit_snapshots
           ]

           result["material_unit_snapshots"] = [
               {
                   "id": s.id,
                   "material_unit_id": s.material_unit_id,
                   "snapshot_date": s.snapshot_date.isoformat(),
                   "definition_data": s.get_definition_data(),
               }
               for s in ps.material_unit_snapshots
           ]

           result["finished_good_snapshots"] = [
               {
                   "id": s.id,
                   "finished_good_id": s.finished_good_id,
                   "snapshot_date": s.snapshot_date.isoformat(),
                   "definition_data": s.get_definition_data(),
               }
               for s in ps.finished_good_snapshots
           ]

           result["total_snapshots"] = (
               len(result["finished_unit_snapshots"]) +
               len(result["material_unit_snapshots"]) +
               len(result["finished_good_snapshots"])
           )

       return result
   ```

2. Add helper for event-based query:
   ```python
   def get_planning_snapshots_by_event(
       event_id: int,
       session: Session = None
   ) -> list[dict]:
       """Get all planning snapshots for an event."""
       if session is not None:
           return _get_ps_by_event_impl(event_id, session)

       with session_scope() as session:
           return _get_ps_by_event_impl(event_id, session)


   def _get_ps_by_event_impl(event_id: int, session: Session) -> list[dict]:
       snapshots = (
           session.query(PlanningSnapshot)
           .filter_by(event_id=event_id)
           .order_by(PlanningSnapshot.created_at.desc())
           .all()
       )

       return [
           {
               "id": ps.id,
               "event_id": ps.event_id,
               "created_at": ps.created_at.isoformat(),
               "notes": ps.notes,
           }
           for ps in snapshots
       ]
   ```

---

### Subtask T024 – Add delete_planning_snapshot()

**Purpose**: Delete planning snapshot with cascade to child snapshots.

**File**: `src/services/planning_snapshot_service.py`

**Steps**:

1. Add delete function:
   ```python
   def delete_planning_snapshot(
       planning_snapshot_id: int,
       session: Session = None
   ) -> bool:
       """
       Delete planning snapshot and all associated snapshots.

       Relies on cascade="all, delete-orphan" for cleanup.

       Args:
           planning_snapshot_id: PlanningSnapshot ID
           session: Optional session

       Returns:
           True if deleted, False if not found
       """
       if session is not None:
           return _delete_planning_snapshot_impl(planning_snapshot_id, session)

       with session_scope() as session:
           return _delete_planning_snapshot_impl(planning_snapshot_id, session)


   def _delete_planning_snapshot_impl(
       planning_snapshot_id: int,
       session: Session
   ) -> bool:
       ps = session.query(PlanningSnapshot).filter_by(id=planning_snapshot_id).first()

       if not ps:
           return False

       session.delete(ps)
       session.flush()
       return True
   ```

**Parallel?**: Yes - can run alongside T023

---

### Subtask T025 – Create unit tests

**Purpose**: Validate CRUD operations and cascade behavior.

**File**: `src/tests/test_planning_snapshot.py`

**Steps**:

1. Create test file with fixtures:
   ```python
   """Tests for PlanningSnapshot model and service functions."""
   import pytest
   from src.models import (
       Event, PlanningSnapshot,
       FinishedUnit, FinishedUnitSnapshot,
       Recipe
   )
   from src.services.planning_snapshot_service import (
       create_planning_snapshot,
       get_planning_snapshot,
       get_planning_snapshots_by_event,
       delete_planning_snapshot,
       PlanningSnapshotError,
   )
   from src.services.finished_unit_service import create_finished_unit_snapshot


   @pytest.fixture
   def sample_event(db_session):
       """Create a test event."""
       event = Event(name="Test Holiday Event")
       db_session.add(event)
       db_session.flush()
       return event
   ```

2. Test cases:
   ```python
   class TestCreatePlanningSnapshot:
       def test_creates_without_event(self, db_session):
           """Can create standalone planning snapshot."""
           result = create_planning_snapshot(session=db_session)
           assert result["id"] is not None
           assert result["event_id"] is None

       def test_creates_with_event(self, db_session, sample_event):
           """Can create planning snapshot linked to event."""
           result = create_planning_snapshot(
               event_id=sample_event.id,
               notes="Test notes",
               session=db_session
           )
           assert result["event_id"] == sample_event.id
           assert result["notes"] == "Test notes"


   class TestGetPlanningSnapshot:
       def test_returns_with_linked_snapshots(self, db_session, sample_event, sample_finished_unit):
           """Aggregates all linked snapshots."""
           # Create planning snapshot
           ps = create_planning_snapshot(
               event_id=sample_event.id,
               session=db_session
           )

           # Create linked snapshot
           create_finished_unit_snapshot(
               finished_unit_id=sample_finished_unit.id,
               planning_snapshot_id=ps["id"],
               session=db_session
           )

           # Retrieve with snapshots
           result = get_planning_snapshot(ps["id"], session=db_session)
           assert result is not None
           assert len(result["finished_unit_snapshots"]) == 1
           assert result["total_snapshots"] == 1


   class TestDeletePlanningSnapshot:
       def test_cascades_to_child_snapshots(self, db_session, sample_finished_unit):
           """Deleting PlanningSnapshot deletes all child snapshots."""
           # Create planning snapshot with linked snapshot
           ps = create_planning_snapshot(session=db_session)
           fu_snap = create_finished_unit_snapshot(
               finished_unit_id=sample_finished_unit.id,
               planning_snapshot_id=ps["id"],
               session=db_session
           )

           # Delete planning snapshot
           result = delete_planning_snapshot(ps["id"], session=db_session)
           assert result is True

           # Verify child snapshot is gone
           from src.services.finished_unit_service import get_finished_unit_snapshot
           assert get_finished_unit_snapshot(fu_snap["id"], session=db_session) is None

       def test_returns_false_for_invalid_id(self, db_session):
           """Returns False for non-existent ID."""
           result = delete_planning_snapshot(99999, session=db_session)
           assert result is False
   ```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Cascade delete not working | Test explicitly with child snapshots |
| Event deletion breaks FK | Verify SET NULL behavior |
| Orphaned snapshots | cascade="all, delete-orphan" prevents orphans |
| Circular import with Event | Use string references |

## Definition of Done Checklist

- [ ] T019: PlanningSnapshot model created with all columns, relationships
- [ ] T020: Model exported from src/models/__init__.py
- [ ] T021: Event.planning_snapshots relationship added
- [ ] T022: planning_snapshot_service.py created with CRUD
- [ ] T023: get_planning_snapshot() aggregates all linked snapshots
- [ ] T024: delete_planning_snapshot() cascades correctly
- [ ] T025: Unit tests pass including cascade behavior
- [ ] `tasks.md` updated with status change

## Review Guidance

**Reviewer Checklist**:
- [ ] PlanningSnapshot model has correct FK cascade behaviors
- [ ] All three snapshot relationships use cascade="all, delete-orphan"
- [ ] Event.planning_snapshots relationship bidirectional
- [ ] Aggregation query efficient (lazy="dynamic" for large sets)
- [ ] Cascade delete tested with actual child snapshots

## Activity Log

- 2025-01-24T05:30:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-24T18:30:47Z – unknown – shell_pid=61030 – lane=for_review – Ready for review: PlanningSnapshot model, Event relationship, service CRUD (create/get/delete), 18 unit tests all passing
- 2026-01-24T18:32:40Z – claude-opus – shell_pid=62838 – lane=doing – Started review via workflow command
