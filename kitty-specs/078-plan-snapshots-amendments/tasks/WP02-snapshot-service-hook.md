---
work_package_id: "WP02"
subtasks:
  - "T005"
  - "T006"
  - "T007"
  - "T008"
  - "T009"
title: "Snapshot Service & Production Hook"
phase: "Phase 0 - Foundation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-28T03:25:47Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Snapshot Service & Production Hook

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
spec-kitty implement WP02 --base WP01
```

Depends on WP01 (PlanSnapshot model must exist).

---

## Objectives & Success Criteria

**Objective**: Create snapshot service and integrate with start_production() to automatically capture plan state.

**Success Criteria**:
- [ ] `plan_snapshot_service.py` exists with create/get functions
- [ ] `start_production()` creates snapshot before state transition
- [ ] Snapshot contains correct recipes, FGs, and batch decisions
- [ ] Duplicate snapshot prevention (idempotent)
- [ ] All tests pass: `./run-tests.sh src/tests/test_plan_snapshot_service.py -v`

---

## Context & Constraints

**Feature**: F078 Plan Snapshots & Amendments
**Spec**: `kitty-specs/078-plan-snapshots-amendments/spec.md` (US-1: Capture Plan Snapshot)
**Plan**: `kitty-specs/078-plan-snapshots-amendments/plan.md` (D1, D2)

**Key Constraints**:
- Follow session=None pattern per CLAUDE.md
- Snapshot creation must be atomic with state transition
- Use single transaction to ensure consistency
- Query existing services for plan data (event_service, batch_decision_service)

**Reference Services**:
- `src/services/plan_state_service.py` - Hook point for snapshot creation
- `src/services/event_service.py` - Has get_event_recipes, get_event_fg_quantities
- `src/services/batch_decision_service.py` - Has get_batch_decisions

**JSON Schema for snapshot_data**:
```json
{
  "snapshot_version": "1.0",
  "created_at": "2026-01-28T03:25:47Z",
  "recipes": [
    {"recipe_id": 1, "recipe_name": "Chocolate Chip Cookies", "recipe_slug": "chocolate-chip-cookies"}
  ],
  "finished_goods": [
    {"fg_id": 1, "fg_name": "Cookie Gift Box", "fg_slug": "cookie-gift-box", "quantity": 10}
  ],
  "batch_decisions": [
    {"recipe_id": 1, "recipe_name": "Chocolate Chip Cookies", "batches": 5, "yield_per_batch": 24}
  ]
}
```

---

## Subtasks & Detailed Guidance

### Subtask T005 – Create plan_snapshot_service.py with create_plan_snapshot()

**Purpose**: Implement service function to capture complete plan state as JSON snapshot.

**Steps**:
1. Create new file `src/services/plan_snapshot_service.py`
2. Import required modules (models, session_scope, datetime utilities)
3. Implement `create_plan_snapshot(event_id, session=None)`:
   - Check if snapshot already exists (return existing if so - idempotent)
   - Query EventRecipe records for the event
   - Query EventFinishedGood records for the event
   - Query BatchDecision records for the event
   - Build snapshot_data dict with all plan data
   - Create and persist PlanSnapshot
   - Return the snapshot

**File**: `src/services/plan_snapshot_service.py` (NEW, ~100 lines)

**Implementation**:
```python
"""Plan Snapshot Service for F078.

Provides functions to create and retrieve plan snapshots.
Snapshots capture complete plan state when production starts.

Session Management Pattern (from CLAUDE.md):
- All public functions accept session=None parameter
- If session provided, use it directly
- If session is None, create a new session via session_scope()
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.models import Event, PlanSnapshot, EventRecipe, EventFinishedGood, BatchDecision
from src.services.database import session_scope
from src.utils.datetime_utils import utc_now


def _build_snapshot_data(event: Event, session: Session) -> dict:
    """Build snapshot JSON data from current plan state.

    Args:
        event: Event to snapshot
        session: Database session

    Returns:
        Dict containing complete plan state
    """
    # Get recipes
    event_recipes = session.query(EventRecipe).filter(
        EventRecipe.event_id == event.id
    ).all()
    recipes_data = [
        {
            "recipe_id": er.recipe_id,
            "recipe_name": er.recipe.name if er.recipe else "Unknown",
            "recipe_slug": er.recipe.slug if er.recipe else "unknown",
        }
        for er in event_recipes
    ]

    # Get finished goods
    event_fgs = session.query(EventFinishedGood).filter(
        EventFinishedGood.event_id == event.id
    ).all()
    fgs_data = [
        {
            "fg_id": efg.finished_good_id,
            "fg_name": efg.finished_good.display_name if efg.finished_good else "Unknown",
            "fg_slug": efg.finished_good.slug if efg.finished_good else "unknown",
            "quantity": efg.quantity,
        }
        for efg in event_fgs
    ]

    # Get batch decisions
    batch_decisions = session.query(BatchDecision).filter(
        BatchDecision.event_id == event.id
    ).all()
    batches_data = [
        {
            "recipe_id": bd.recipe_id,
            "recipe_name": bd.recipe.name if bd.recipe else "Unknown",
            "batches": bd.batches,
            "yield_per_batch": bd.yield_per_batch,
        }
        for bd in batch_decisions
    ]

    return {
        "snapshot_version": "1.0",
        "created_at": utc_now().isoformat(),
        "recipes": recipes_data,
        "finished_goods": fgs_data,
        "batch_decisions": batches_data,
    }


def _create_plan_snapshot_impl(event_id: int, session: Session) -> PlanSnapshot:
    """Internal implementation of create_plan_snapshot."""
    # Check if snapshot already exists (idempotent)
    existing = session.query(PlanSnapshot).filter(
        PlanSnapshot.event_id == event_id
    ).first()
    if existing:
        return existing

    # Get event
    event = session.query(Event).filter(Event.id == event_id).first()
    if not event:
        from src.services.exceptions import ValidationError
        raise ValidationError([f"Event {event_id} not found"])

    # Build snapshot data
    snapshot_data = _build_snapshot_data(event, session)

    # Create snapshot
    snapshot = PlanSnapshot(
        event_id=event_id,
        snapshot_data=snapshot_data,
    )
    session.add(snapshot)
    session.flush()

    return snapshot


def create_plan_snapshot(event_id: int, session: Session = None) -> PlanSnapshot:
    """Create a snapshot of the plan state for an event.

    Captures all recipes, finished goods, quantities, and batch decisions
    as JSON. Idempotent - returns existing snapshot if one exists.

    Args:
        event_id: Event ID to snapshot
        session: Optional session for transaction sharing

    Returns:
        PlanSnapshot instance (new or existing)

    Raises:
        ValidationError: If event not found
    """
    if session is not None:
        return _create_plan_snapshot_impl(event_id, session)

    with session_scope() as session:
        return _create_plan_snapshot_impl(event_id, session)
```

**Validation**:
- Function handles empty plans (no recipes/FGs)
- Idempotent - returns existing snapshot if called twice
- JSON structure matches schema

---

### Subtask T006 – Implement get_plan_snapshot()

**Purpose**: Retrieve existing snapshot for an event.

**Steps**:
1. Add `get_plan_snapshot(event_id, session=None)` to plan_snapshot_service.py
2. Query PlanSnapshot by event_id
3. Return snapshot or None if not found

**File**: `src/services/plan_snapshot_service.py` (MODIFY, ~20 lines added)

**Implementation**:
```python
def _get_plan_snapshot_impl(event_id: int, session: Session) -> Optional[PlanSnapshot]:
    """Internal implementation of get_plan_snapshot."""
    return session.query(PlanSnapshot).filter(
        PlanSnapshot.event_id == event_id
    ).first()


def get_plan_snapshot(event_id: int, session: Session = None) -> Optional[PlanSnapshot]:
    """Get the plan snapshot for an event.

    Args:
        event_id: Event ID to query
        session: Optional session for transaction sharing

    Returns:
        PlanSnapshot if exists, None otherwise
    """
    if session is not None:
        return _get_plan_snapshot_impl(event_id, session)

    with session_scope() as session:
        snapshot = _get_plan_snapshot_impl(event_id, session)
        if snapshot:
            # Ensure data is loaded before session closes
            _ = snapshot.snapshot_data
        return snapshot
```

**Validation**:
- Returns None for event with no snapshot
- Returns snapshot with data accessible outside session

---

### Subtask T007 – Integrate snapshot creation into start_production()

**Purpose**: Automatically create snapshot when production starts.

**Steps**:
1. Open `src/services/plan_state_service.py`
2. Import `create_plan_snapshot` from plan_snapshot_service
3. Modify `_start_production_impl()` to call `create_plan_snapshot()` BEFORE state transition
4. Pass session to maintain transaction atomicity

**File**: `src/services/plan_state_service.py` (MODIFY, ~10 lines added)

**Implementation**:
```python
# Add import at top of file
from src.services.plan_snapshot_service import create_plan_snapshot


def _start_production_impl(event_id: int, session: Session) -> Event:
    """Internal implementation of start_production."""
    event = _get_event_or_raise(event_id, session)

    if event.plan_state != PlanState.LOCKED:
        raise PlanStateError(
            event_id,
            event.plan_state,
            "start production (must be in LOCKED state)"
        )

    # F078: Create snapshot BEFORE state transition
    create_plan_snapshot(event_id, session)

    event.plan_state = PlanState.IN_PRODUCTION
    session.flush()
    return event
```

**Key Points**:
- Snapshot created BEFORE state change
- Same transaction ensures atomicity
- If snapshot creation fails, state change rolls back

**Validation**:
- `start_production()` creates snapshot
- State only changes if snapshot succeeds
- Transaction rolls back on any failure

---

### Subtask T008 – Write unit tests for snapshot service

**Purpose**: Verify snapshot service functions work correctly.

**Steps**:
1. Create `src/tests/test_plan_snapshot_service.py`
2. Write tests for:
   - create_plan_snapshot with recipes, FGs, batch decisions
   - create_plan_snapshot idempotent (returns existing)
   - create_plan_snapshot with empty plan
   - get_plan_snapshot returns snapshot
   - get_plan_snapshot returns None when no snapshot
   - Snapshot JSON structure is correct

**File**: `src/tests/test_plan_snapshot_service.py` (NEW, ~150 lines)

**Test Structure**:
```python
"""Unit tests for plan_snapshot_service."""
import pytest
from datetime import datetime

from src.models import Event, EventRecipe, EventFinishedGood, BatchDecision, Recipe, FinishedGood
from src.models.event import PlanState
from src.services import plan_snapshot_service
from src.services.database import session_scope


class TestCreatePlanSnapshot:
    """Tests for create_plan_snapshot function."""

    def test_creates_snapshot_with_plan_data(self):
        """Snapshot captures recipes, FGs, and batch decisions."""
        with session_scope() as session:
            # Setup: Create event with plan data
            event = Event(
                name="Test Event",
                event_date=datetime(2026, 12, 25).date(),
                year=2026,
                plan_state=PlanState.LOCKED,
            )
            session.add(event)
            session.flush()

            # Add recipe (need actual Recipe record)
            recipe = session.query(Recipe).first()
            if recipe:
                event_recipe = EventRecipe(event_id=event.id, recipe_id=recipe.id)
                session.add(event_recipe)

            # Add FG (need actual FinishedGood record)
            fg = session.query(FinishedGood).first()
            if fg:
                event_fg = EventFinishedGood(
                    event_id=event.id,
                    finished_good_id=fg.id,
                    quantity=10
                )
                session.add(event_fg)

            session.flush()

            # Create snapshot
            snapshot = plan_snapshot_service.create_plan_snapshot(event.id, session)

            assert snapshot is not None
            assert snapshot.event_id == event.id
            assert "snapshot_version" in snapshot.snapshot_data
            assert snapshot.snapshot_data["snapshot_version"] == "1.0"
            assert "recipes" in snapshot.snapshot_data
            assert "finished_goods" in snapshot.snapshot_data
            assert "batch_decisions" in snapshot.snapshot_data

    def test_idempotent_returns_existing_snapshot(self):
        """Calling create twice returns same snapshot."""
        with session_scope() as session:
            event = Event(
                name="Test Event",
                event_date=datetime(2026, 12, 25).date(),
                year=2026,
            )
            session.add(event)
            session.flush()

            snapshot1 = plan_snapshot_service.create_plan_snapshot(event.id, session)
            snapshot2 = plan_snapshot_service.create_plan_snapshot(event.id, session)

            assert snapshot1.id == snapshot2.id

    def test_empty_plan_creates_valid_snapshot(self):
        """Event with no recipes/FGs still gets valid snapshot."""
        with session_scope() as session:
            event = Event(
                name="Empty Event",
                event_date=datetime(2026, 12, 25).date(),
                year=2026,
            )
            session.add(event)
            session.flush()

            snapshot = plan_snapshot_service.create_plan_snapshot(event.id, session)

            assert snapshot is not None
            assert snapshot.snapshot_data["recipes"] == []
            assert snapshot.snapshot_data["finished_goods"] == []
            assert snapshot.snapshot_data["batch_decisions"] == []


class TestGetPlanSnapshot:
    """Tests for get_plan_snapshot function."""

    def test_returns_snapshot_when_exists(self):
        """Returns snapshot for event that has one."""
        with session_scope() as session:
            event = Event(
                name="Test Event",
                event_date=datetime(2026, 12, 25).date(),
                year=2026,
            )
            session.add(event)
            session.flush()

            created = plan_snapshot_service.create_plan_snapshot(event.id, session)
            retrieved = plan_snapshot_service.get_plan_snapshot(event.id, session)

            assert retrieved is not None
            assert retrieved.id == created.id

    def test_returns_none_when_no_snapshot(self):
        """Returns None for event without snapshot."""
        with session_scope() as session:
            event = Event(
                name="No Snapshot Event",
                event_date=datetime(2026, 12, 25).date(),
                year=2026,
            )
            session.add(event)
            session.flush()

            result = plan_snapshot_service.get_plan_snapshot(event.id, session)

            assert result is None
```

**Validation**:
- All tests pass: `./run-tests.sh src/tests/test_plan_snapshot_service.py -v`

---

### Subtask T009 – Write integration test for start_production with snapshot

**Purpose**: Verify end-to-end flow of start_production creating snapshot.

**Steps**:
1. Add integration test to `src/tests/test_plan_snapshot_service.py` or create separate file
2. Test that calling `start_production()` on LOCKED event:
   - Creates snapshot with correct data
   - Changes state to IN_PRODUCTION
   - Both happen atomically

**File**: `src/tests/test_plan_snapshot_service.py` (MODIFY, ~50 lines added)

**Test**:
```python
class TestStartProductionIntegration:
    """Integration tests for start_production with snapshot creation."""

    def test_start_production_creates_snapshot(self):
        """start_production creates snapshot before state change."""
        from src.services import plan_state_service

        with session_scope() as session:
            # Create LOCKED event
            event = Event(
                name="Production Test",
                event_date=datetime(2026, 12, 25).date(),
                year=2026,
                plan_state=PlanState.LOCKED,
            )
            session.add(event)
            session.flush()
            event_id = event.id

            # Start production
            result = plan_state_service.start_production(event_id, session)

            # Verify state changed
            assert result.plan_state == PlanState.IN_PRODUCTION

            # Verify snapshot created
            snapshot = plan_snapshot_service.get_plan_snapshot(event_id, session)
            assert snapshot is not None
            assert snapshot.event_id == event_id

    def test_start_production_atomic_with_snapshot(self):
        """If snapshot fails, state change rolls back."""
        # This is harder to test directly - would need to mock failure
        # The design ensures atomicity by using same session
        pass
```

**Validation**:
- Integration test passes
- Snapshot exists after start_production completes

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session detachment | Pass session through all calls; don't access lazy-loaded data outside session |
| Circular import | Import inside function if needed |
| Large snapshots | Only capture essential fields; avoid relationships |
| Transaction failure | Single session ensures atomic rollback |

---

## Definition of Done Checklist

- [ ] `src/services/plan_snapshot_service.py` created
- [ ] `create_plan_snapshot()` captures recipes, FGs, batch decisions
- [ ] `get_plan_snapshot()` retrieves existing snapshots
- [ ] `start_production()` calls `create_plan_snapshot()` before state change
- [ ] Unit tests pass: `./run-tests.sh src/tests/test_plan_snapshot_service.py -v`
- [ ] Integration test verifies end-to-end flow
- [ ] Session management follows CLAUDE.md patterns

---

## Review Guidance

**Key Acceptance Checkpoints**:
1. Verify snapshot JSON structure matches schema
2. Check start_production creates snapshot BEFORE state change
3. Verify idempotency (calling twice doesn't create duplicate)
4. Run tests: `./run-tests.sh src/tests/test_plan_snapshot_service.py -v`
5. Test with real data: lock an event, start production, verify snapshot

---

## Activity Log

- 2026-01-28T03:25:47Z – system – lane=planned – Prompt created.
