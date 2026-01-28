---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
title: "PlanSnapshot Model Foundation"
phase: "Phase 0 - Foundation"
lane: "for_review"
assignee: ""
agent: "claude-opus"
shell_pid: "76120"
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-01-28T03:25:47Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – PlanSnapshot Model Foundation

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP01
```

No dependencies - this is the foundation work package.

---

## Objectives & Success Criteria

**Objective**: Create the PlanSnapshot database model for storing complete plan state as JSON when production starts.

**Success Criteria**:
- [ ] PlanSnapshot model exists with correct schema
- [ ] Event model has one-to-one relationship to PlanSnapshot
- [ ] Model is exported from `src/models/__init__.py`
- [ ] Unit tests verify model creation, persistence, and queries
- [ ] All tests pass: `./run-tests.sh src/tests/test_plan_snapshot_model.py -v`

---

## Context & Constraints

**Feature**: F078 Plan Snapshots & Amendments
**Spec**: `kitty-specs/078-plan-snapshots-amendments/spec.md`
**Plan**: `kitty-specs/078-plan-snapshots-amendments/plan.md`
**Data Model**: `kitty-specs/078-plan-snapshots-amendments/data-model.md`

**Key Constraints**:
- Follow existing model patterns (inherit from BaseModel)
- Use SQLAlchemy 2.x patterns
- JSON storage via `sqlalchemy.dialects.sqlite.JSON`
- One snapshot per event (unique constraint)
- Cascade delete when event is deleted

**Reference Models**:
- `src/models/plan_amendment.py` - Similar JSON column pattern
- `src/models/production_plan_snapshot.py` - Similar event relationship pattern

---

## Subtasks & Detailed Guidance

### Subtask T001 – Create PlanSnapshot model

**Purpose**: Define the database model for storing plan snapshots.

**Steps**:
1. Create new file `src/models/plan_snapshot.py`
2. Import required SQLAlchemy components and BaseModel
3. Define PlanSnapshot class with:
   - `event_id`: Integer FK to events.id, unique, CASCADE delete
   - `snapshot_data`: JSON column (non-nullable)
   - `created_at`: DateTime with utc_now default
4. Add relationship to Event
5. Add appropriate indexes

**File**: `src/models/plan_snapshot.py` (NEW, ~60 lines)

**Reference Implementation** (from data-model.md):
```python
"""
PlanSnapshot model for capturing plan state at production start.

Feature 078: Plan Snapshots & Amendments
"""

from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship

from .base import BaseModel
from src.utils.datetime_utils import utc_now


class PlanSnapshot(BaseModel):
    """
    Captures complete plan state when production starts.

    Created automatically when start_production() transitions
    an event from LOCKED to IN_PRODUCTION state. Stores the
    original plan as JSON for later comparison.

    Attributes:
        event_id: Foreign key to Event (CASCADE delete)
        snapshot_data: JSON containing recipes, FGs, batch decisions
        created_at: When snapshot was created
    """

    __tablename__ = "plan_snapshots"

    # Foreign keys
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One snapshot per event
        index=True,
    )

    # Snapshot data
    snapshot_data = Column(JSON, nullable=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=utc_now)

    # Relationships
    event = relationship("Event", back_populates="plan_snapshot")

    # Indexes and constraints
    __table_args__ = (
        Index("idx_plan_snapshot_event", "event_id"),
        UniqueConstraint("event_id", name="uq_plan_snapshot_event"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"PlanSnapshot(id={self.id}, event_id={self.event_id})"
```

**Validation**:
- Model can be imported without errors
- Correct table name: `plan_snapshots`
- JSON column type is correct for SQLite

---

### Subtask T002 – Add Event relationship

**Purpose**: Enable Event to access its snapshot via relationship.

**Steps**:
1. Open `src/models/event.py`
2. Add relationship to PlanSnapshot:
   ```python
   # Plan snapshot (F078)
   plan_snapshot = relationship(
       "PlanSnapshot",
       back_populates="event",
       uselist=False,  # One-to-one
       cascade="all, delete-orphan",
       lazy="selectin",
   )
   ```
3. Place after existing `plan_amendments` relationship (around line 195-200)

**File**: `src/models/event.py` (MODIFY, ~5 lines added)

**Notes**:
- `uselist=False` makes this a one-to-one relationship
- `cascade="all, delete-orphan"` ensures snapshot deleted with event
- `lazy="selectin"` for efficient loading

**Validation**:
- Event can access `event.plan_snapshot`
- PlanSnapshot can access `snapshot.event`

---

### Subtask T003 – Update model exports

**Purpose**: Make PlanSnapshot importable from `src.models`.

**Steps**:
1. Open `src/models/__init__.py`
2. Add import: `from .plan_snapshot import PlanSnapshot`
3. Add `"PlanSnapshot"` to `__all__` list

**File**: `src/models/__init__.py` (MODIFY, ~2 lines added)

**Validation**:
- `from src.models import PlanSnapshot` works without error

---

### Subtask T004 – Write model unit tests

**Purpose**: Verify model works correctly with database.

**Steps**:
1. Create `src/tests/test_plan_snapshot_model.py`
2. Write tests for:
   - Creating a PlanSnapshot with valid JSON data
   - Unique constraint prevents duplicate snapshots per event
   - Cascade delete removes snapshot when event deleted
   - Event relationship works bidirectionally
   - JSON data is stored and retrieved correctly

**File**: `src/tests/test_plan_snapshot_model.py` (NEW, ~80 lines)

**Test Structure**:
```python
"""Unit tests for PlanSnapshot model."""
import pytest
from datetime import datetime

from src.models import Event, PlanSnapshot
from src.services.database import session_scope


class TestPlanSnapshotModel:
    """Tests for PlanSnapshot model."""

    def test_create_snapshot_with_valid_data(self):
        """Snapshot can be created with valid JSON data."""
        with session_scope() as session:
            # Create event first
            event = Event(
                name="Test Event",
                event_date=datetime(2026, 12, 25).date(),
                year=2026,
            )
            session.add(event)
            session.flush()

            # Create snapshot
            snapshot_data = {
                "snapshot_version": "1.0",
                "recipes": [],
                "finished_goods": [],
                "batch_decisions": [],
            }
            snapshot = PlanSnapshot(
                event_id=event.id,
                snapshot_data=snapshot_data,
            )
            session.add(snapshot)
            session.flush()

            assert snapshot.id is not None
            assert snapshot.event_id == event.id
            assert snapshot.snapshot_data == snapshot_data
            assert snapshot.created_at is not None

    def test_unique_constraint_prevents_duplicate_snapshots(self):
        """Only one snapshot allowed per event."""
        with session_scope() as session:
            event = Event(
                name="Test Event",
                event_date=datetime(2026, 12, 25).date(),
                year=2026,
            )
            session.add(event)
            session.flush()

            # First snapshot succeeds
            snapshot1 = PlanSnapshot(
                event_id=event.id,
                snapshot_data={"snapshot_version": "1.0"},
            )
            session.add(snapshot1)
            session.flush()

            # Second snapshot should fail
            snapshot2 = PlanSnapshot(
                event_id=event.id,
                snapshot_data={"snapshot_version": "1.0"},
            )
            session.add(snapshot2)

            with pytest.raises(Exception):  # IntegrityError
                session.flush()

    def test_cascade_delete_removes_snapshot(self):
        """Deleting event deletes snapshot."""
        with session_scope() as session:
            event = Event(
                name="Test Event",
                event_date=datetime(2026, 12, 25).date(),
                year=2026,
            )
            session.add(event)
            session.flush()

            snapshot = PlanSnapshot(
                event_id=event.id,
                snapshot_data={"snapshot_version": "1.0"},
            )
            session.add(snapshot)
            session.flush()
            snapshot_id = snapshot.id

            # Delete event
            session.delete(event)
            session.flush()

            # Snapshot should be gone
            result = session.query(PlanSnapshot).filter(
                PlanSnapshot.id == snapshot_id
            ).first()
            assert result is None

    def test_event_relationship_bidirectional(self):
        """Event and snapshot can access each other."""
        with session_scope() as session:
            event = Event(
                name="Test Event",
                event_date=datetime(2026, 12, 25).date(),
                year=2026,
            )
            session.add(event)
            session.flush()

            snapshot = PlanSnapshot(
                event_id=event.id,
                snapshot_data={"snapshot_version": "1.0"},
            )
            session.add(snapshot)
            session.flush()

            # Refresh to load relationships
            session.refresh(event)
            session.refresh(snapshot)

            assert event.plan_snapshot == snapshot
            assert snapshot.event == event
```

**Validation**:
- All tests pass: `./run-tests.sh src/tests/test_plan_snapshot_model.py -v`

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| JSON column compatibility | Use `sqlalchemy.dialects.sqlite.JSON` explicitly |
| Circular import | Import Event via string in relationship |
| Unique constraint syntax | Follow existing patterns in codebase |

---

## Definition of Done Checklist

- [ ] `src/models/plan_snapshot.py` created with PlanSnapshot class
- [ ] Event model has `plan_snapshot` relationship
- [ ] `src/models/__init__.py` exports PlanSnapshot
- [ ] Unit tests in `src/tests/test_plan_snapshot_model.py` pass
- [ ] No import errors when running application
- [ ] Code follows existing model patterns

---

## Review Guidance

**Key Acceptance Checkpoints**:
1. Verify model follows BaseModel inheritance pattern
2. Check JSON column type is correct for SQLite
3. Verify unique constraint on event_id
4. Check cascade delete behavior
5. Run tests: `./run-tests.sh src/tests/test_plan_snapshot_model.py -v`

---

## Activity Log

- 2026-01-28T03:25:47Z – system – lane=planned – Prompt created.
- 2026-01-28T03:34:20Z – claude-opus – shell_pid=76120 – lane=doing – Started implementation via workflow command
- 2026-01-28T03:40:29Z – claude-opus – shell_pid=76120 – lane=for_review – Ready for review: PlanSnapshot model with tests, Event relationship, exports
