---
work_package_id: WP03
title: Amendment Service
lane: "doing"
dependencies: [WP02]
base_branch: 078-plan-snapshots-amendments-WP02
base_commit: c82b5959071139d7eb17fea97e57800eb2961e33
created_at: '2026-01-28T03:46:00.229205+00:00'
subtasks:
- T010
- T011
- T012
- T013
- T014
- T015
phase: Phase 1 - Core Implementation
assignee: ''
agent: ''
shell_pid: "78810"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-28T03:25:47Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Amendment Service

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
spec-kitty implement WP03 --base WP02
```

Depends on WP02 (snapshot service must exist for amendments to make sense).

**Parallelization Note**: WP03 can run in parallel with WP04 (Amendment UI) after WP02 completes.

---

## Objectives & Success Criteria

**Objective**: Implement amendment creation service with full validation and history retrieval.

**Success Criteria**:
- [ ] `plan_amendment_service.py` exists with all amendment functions
- [ ] DROP_FG validates FG exists in current plan
- [ ] ADD_FG validates FG doesn't already exist
- [ ] MODIFY_BATCH validates batch decision exists
- [ ] All amendments require IN_PRODUCTION state
- [ ] All amendments require non-empty reason
- [ ] Amendment history retrieval works
- [ ] All tests pass: `./run-tests.sh src/tests/test_plan_amendment_service.py -v`

---

## Context & Constraints

**Feature**: F078 Plan Snapshots & Amendments
**Spec**: `kitty-specs/078-plan-snapshots-amendments/spec.md` (US-2: Record Amendments)
**Plan**: `kitty-specs/078-plan-snapshots-amendments/plan.md` (D3, D4)

**Key Constraints**:
- Only allow amendments when plan_state == IN_PRODUCTION
- Reason is required (non-empty string)
- Amendments modify live data AND create amendment record
- Append-only: amendments are never deleted or modified
- Follow session=None pattern per CLAUDE.md

**Existing Model** (from F068):
- `src/models/plan_amendment.py` - PlanAmendment model with AmendmentType enum
- AmendmentType: DROP_FG, ADD_FG, MODIFY_BATCH
- Fields: event_id, amendment_type, amendment_data (JSON), reason, created_at

**Amendment Data Schemas**:
```python
# DROP_FG
{"fg_id": 1, "fg_name": "Cookie Box", "original_quantity": 10}

# ADD_FG
{"fg_id": 2, "fg_name": "Brownie Box", "quantity": 5}

# MODIFY_BATCH
{"recipe_id": 1, "recipe_name": "Cookies", "old_batches": 5, "new_batches": 7}
```

---

## Subtasks & Detailed Guidance

### Subtask T010 – Create plan_amendment_service.py with base create_amendment()

**Purpose**: Implement base amendment creation with common validation.

**Steps**:
1. Create new file `src/services/plan_amendment_service.py`
2. Import required modules
3. Implement `_validate_amendment_allowed(event, reason)`:
   - Check plan_state == IN_PRODUCTION
   - Check reason is non-empty
   - Raise appropriate errors if validation fails
4. Implement base `create_amendment(event_id, amendment_type, amendment_data, reason, session=None)`:
   - Get event and validate
   - Create PlanAmendment record
   - Return the amendment

**File**: `src/services/plan_amendment_service.py` (NEW, ~80 lines initial)

**Implementation**:
```python
"""Plan Amendment Service for F078.

Provides functions to create and query plan amendments.
Amendments track changes made to plans during production.

Session Management Pattern (from CLAUDE.md):
- All public functions accept session=None parameter
- If session provided, use it directly
- If session is None, create a new session via session_scope()
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from src.models import Event, PlanAmendment, EventFinishedGood, BatchDecision
from src.models.plan_amendment import AmendmentType
from src.models.event import PlanState
from src.services.database import session_scope
from src.services.exceptions import ValidationError, PlanStateError


def _validate_amendment_allowed(event: Event, reason: str) -> None:
    """Validate that amendments are allowed for this event.

    Args:
        event: Event to validate
        reason: Amendment reason to validate

    Raises:
        PlanStateError: If plan is not in IN_PRODUCTION state
        ValidationError: If reason is empty
    """
    if event.plan_state != PlanState.IN_PRODUCTION:
        raise PlanStateError(
            event.id,
            event.plan_state,
            "create amendment (plan must be IN_PRODUCTION)"
        )

    if not reason or not reason.strip():
        raise ValidationError(["Amendment reason is required"])


def _get_event_or_raise(event_id: int, session: Session) -> Event:
    """Get event by ID or raise ValidationError."""
    event = session.query(Event).filter(Event.id == event_id).first()
    if event is None:
        raise ValidationError([f"Event {event_id} not found"])
    return event


def _create_amendment_impl(
    event_id: int,
    amendment_type: AmendmentType,
    amendment_data: dict,
    reason: str,
    session: Session
) -> PlanAmendment:
    """Internal implementation of create_amendment."""
    event = _get_event_or_raise(event_id, session)
    _validate_amendment_allowed(event, reason)

    amendment = PlanAmendment(
        event_id=event_id,
        amendment_type=amendment_type,
        amendment_data=amendment_data,
        reason=reason.strip(),
    )
    session.add(amendment)
    session.flush()

    return amendment


def create_amendment(
    event_id: int,
    amendment_type: AmendmentType,
    amendment_data: dict,
    reason: str,
    session: Session = None
) -> PlanAmendment:
    """Create a plan amendment record.

    Base function for creating amendments. Use specific functions
    (drop_finished_good, add_finished_good, modify_batch_decision)
    for type-specific validation and data modification.

    Args:
        event_id: Event to amend
        amendment_type: Type of amendment
        amendment_data: Amendment-specific data
        reason: User-provided reason for amendment
        session: Optional session for transaction sharing

    Returns:
        Created PlanAmendment

    Raises:
        ValidationError: If event not found or reason empty
        PlanStateError: If plan not in IN_PRODUCTION state
    """
    if session is not None:
        return _create_amendment_impl(event_id, amendment_type, amendment_data, reason, session)

    with session_scope() as session:
        return _create_amendment_impl(event_id, amendment_type, amendment_data, reason, session)
```

**Validation**:
- Base function validates state and reason
- Amendment record is created correctly

---

### Subtask T011 – Implement drop_finished_good()

**Purpose**: Drop a finished good from the plan with validation.

**Steps**:
1. Add `drop_finished_good(event_id, fg_id, reason, session=None)` to service
2. Validate FG exists in EventFinishedGood for this event
3. Capture original quantity for amendment record
4. Delete the EventFinishedGood record
5. Create amendment with DROP_FG type

**File**: `src/services/plan_amendment_service.py` (MODIFY, ~40 lines added)

**Implementation**:
```python
def _drop_finished_good_impl(
    event_id: int,
    fg_id: int,
    reason: str,
    session: Session
) -> PlanAmendment:
    """Internal implementation of drop_finished_good."""
    event = _get_event_or_raise(event_id, session)
    _validate_amendment_allowed(event, reason)

    # Find the EventFinishedGood record
    event_fg = session.query(EventFinishedGood).filter(
        EventFinishedGood.event_id == event_id,
        EventFinishedGood.finished_good_id == fg_id,
    ).first()

    if event_fg is None:
        raise ValidationError([f"Finished good {fg_id} not in event plan"])

    # Capture data for amendment
    amendment_data = {
        "fg_id": fg_id,
        "fg_name": event_fg.finished_good.display_name if event_fg.finished_good else "Unknown",
        "original_quantity": event_fg.quantity,
    }

    # Delete the EventFinishedGood
    session.delete(event_fg)

    # Create amendment record
    amendment = PlanAmendment(
        event_id=event_id,
        amendment_type=AmendmentType.DROP_FG,
        amendment_data=amendment_data,
        reason=reason.strip(),
    )
    session.add(amendment)
    session.flush()

    return amendment


def drop_finished_good(
    event_id: int,
    fg_id: int,
    reason: str,
    session: Session = None
) -> PlanAmendment:
    """Drop a finished good from the event plan.

    Removes the EventFinishedGood record and creates an amendment
    tracking the removal.

    Args:
        event_id: Event to modify
        fg_id: FinishedGood ID to remove
        reason: User-provided reason
        session: Optional session for transaction sharing

    Returns:
        Created PlanAmendment

    Raises:
        ValidationError: If FG not in plan or reason empty
        PlanStateError: If plan not in IN_PRODUCTION state
    """
    if session is not None:
        return _drop_finished_good_impl(event_id, fg_id, reason, session)

    with session_scope() as session:
        return _drop_finished_good_impl(event_id, fg_id, reason, session)
```

**Validation**:
- Rejects if FG not in plan
- EventFinishedGood record is deleted
- Amendment captures original quantity

---

### Subtask T012 – Implement add_finished_good()

**Purpose**: Add a finished good to the plan with validation.

**Steps**:
1. Add `add_finished_good(event_id, fg_id, quantity, reason, session=None)` to service
2. Validate FG doesn't already exist in EventFinishedGood
3. Validate FinishedGood exists in database
4. Create EventFinishedGood record
5. Create amendment with ADD_FG type

**File**: `src/services/plan_amendment_service.py` (MODIFY, ~45 lines added)

**Implementation**:
```python
def _add_finished_good_impl(
    event_id: int,
    fg_id: int,
    quantity: int,
    reason: str,
    session: Session
) -> PlanAmendment:
    """Internal implementation of add_finished_good."""
    from src.models import FinishedGood

    event = _get_event_or_raise(event_id, session)
    _validate_amendment_allowed(event, reason)

    # Check FG doesn't already exist in plan
    existing = session.query(EventFinishedGood).filter(
        EventFinishedGood.event_id == event_id,
        EventFinishedGood.finished_good_id == fg_id,
    ).first()

    if existing is not None:
        raise ValidationError([f"Finished good {fg_id} already in event plan"])

    # Validate FG exists
    fg = session.query(FinishedGood).filter(FinishedGood.id == fg_id).first()
    if fg is None:
        raise ValidationError([f"Finished good {fg_id} not found"])

    # Validate quantity
    if quantity <= 0:
        raise ValidationError(["Quantity must be positive"])

    # Create EventFinishedGood
    event_fg = EventFinishedGood(
        event_id=event_id,
        finished_good_id=fg_id,
        quantity=quantity,
    )
    session.add(event_fg)

    # Create amendment record
    amendment_data = {
        "fg_id": fg_id,
        "fg_name": fg.display_name,
        "quantity": quantity,
    }

    amendment = PlanAmendment(
        event_id=event_id,
        amendment_type=AmendmentType.ADD_FG,
        amendment_data=amendment_data,
        reason=reason.strip(),
    )
    session.add(amendment)
    session.flush()

    return amendment


def add_finished_good(
    event_id: int,
    fg_id: int,
    quantity: int,
    reason: str,
    session: Session = None
) -> PlanAmendment:
    """Add a finished good to the event plan.

    Creates an EventFinishedGood record and amendment tracking
    the addition.

    Args:
        event_id: Event to modify
        fg_id: FinishedGood ID to add
        quantity: Quantity to add
        reason: User-provided reason
        session: Optional session for transaction sharing

    Returns:
        Created PlanAmendment

    Raises:
        ValidationError: If FG already in plan, FG not found, or reason empty
        PlanStateError: If plan not in IN_PRODUCTION state
    """
    if session is not None:
        return _add_finished_good_impl(event_id, fg_id, quantity, reason, session)

    with session_scope() as session:
        return _add_finished_good_impl(event_id, fg_id, quantity, reason, session)
```

**Validation**:
- Rejects if FG already in plan
- Rejects if FG doesn't exist
- EventFinishedGood record is created
- Amendment captures new quantity

---

### Subtask T013 – Implement modify_batch_decision()

**Purpose**: Modify batch count for a recipe with validation.

**Steps**:
1. Add `modify_batch_decision(event_id, recipe_id, new_batches, reason, session=None)`
2. Validate BatchDecision exists for event/recipe
3. Capture old batch count
4. Update BatchDecision.batches
5. Create amendment with MODIFY_BATCH type

**File**: `src/services/plan_amendment_service.py` (MODIFY, ~45 lines added)

**Implementation**:
```python
def _modify_batch_decision_impl(
    event_id: int,
    recipe_id: int,
    new_batches: int,
    reason: str,
    session: Session
) -> PlanAmendment:
    """Internal implementation of modify_batch_decision."""
    event = _get_event_or_raise(event_id, session)
    _validate_amendment_allowed(event, reason)

    # Find batch decision
    batch_decision = session.query(BatchDecision).filter(
        BatchDecision.event_id == event_id,
        BatchDecision.recipe_id == recipe_id,
    ).first()

    if batch_decision is None:
        raise ValidationError([f"No batch decision for recipe {recipe_id} in event"])

    # Validate new_batches
    if new_batches < 0:
        raise ValidationError(["Batch count cannot be negative"])

    # Capture old value
    old_batches = batch_decision.batches

    # Update batch decision
    batch_decision.batches = new_batches

    # Create amendment record
    amendment_data = {
        "recipe_id": recipe_id,
        "recipe_name": batch_decision.recipe.name if batch_decision.recipe else "Unknown",
        "old_batches": old_batches,
        "new_batches": new_batches,
    }

    amendment = PlanAmendment(
        event_id=event_id,
        amendment_type=AmendmentType.MODIFY_BATCH,
        amendment_data=amendment_data,
        reason=reason.strip(),
    )
    session.add(amendment)
    session.flush()

    return amendment


def modify_batch_decision(
    event_id: int,
    recipe_id: int,
    new_batches: int,
    reason: str,
    session: Session = None
) -> PlanAmendment:
    """Modify batch count for a recipe in the event plan.

    Updates the BatchDecision record and creates an amendment
    tracking the change.

    Args:
        event_id: Event to modify
        recipe_id: Recipe ID to modify batch count for
        new_batches: New batch count
        reason: User-provided reason
        session: Optional session for transaction sharing

    Returns:
        Created PlanAmendment

    Raises:
        ValidationError: If batch decision not found or reason empty
        PlanStateError: If plan not in IN_PRODUCTION state
    """
    if session is not None:
        return _modify_batch_decision_impl(event_id, recipe_id, new_batches, reason, session)

    with session_scope() as session:
        return _modify_batch_decision_impl(event_id, recipe_id, new_batches, reason, session)
```

**Validation**:
- Rejects if no batch decision exists
- BatchDecision.batches is updated
- Amendment captures old and new values

---

### Subtask T014 – Implement get_amendments()

**Purpose**: Retrieve amendment history in chronological order.

**Steps**:
1. Add `get_amendments(event_id, session=None)` to service
2. Query PlanAmendment for event, ordered by created_at ascending
3. Return list of amendments

**File**: `src/services/plan_amendment_service.py` (MODIFY, ~25 lines added)

**Implementation**:
```python
def _get_amendments_impl(event_id: int, session: Session) -> List[PlanAmendment]:
    """Internal implementation of get_amendments."""
    return session.query(PlanAmendment).filter(
        PlanAmendment.event_id == event_id
    ).order_by(PlanAmendment.created_at.asc()).all()


def get_amendments(event_id: int, session: Session = None) -> List[PlanAmendment]:
    """Get all amendments for an event in chronological order.

    Args:
        event_id: Event ID to query
        session: Optional session for transaction sharing

    Returns:
        List of PlanAmendment records, oldest first
    """
    if session is not None:
        return _get_amendments_impl(event_id, session)

    with session_scope() as session:
        amendments = _get_amendments_impl(event_id, session)
        # Ensure data is loaded before session closes
        for a in amendments:
            _ = a.amendment_data
            _ = a.amendment_type
        return amendments
```

**Validation**:
- Returns empty list for event with no amendments
- Returns amendments in chronological order
- Amendment data accessible outside session

---

### Subtask T015 – Write comprehensive unit tests

**Purpose**: Verify all amendment service functions work correctly.

**Steps**:
1. Create `src/tests/test_plan_amendment_service.py`
2. Write tests for each function:
   - State validation (must be IN_PRODUCTION)
   - Reason validation (must be non-empty)
   - drop_finished_good validation and behavior
   - add_finished_good validation and behavior
   - modify_batch_decision validation and behavior
   - get_amendments ordering and completeness

**File**: `src/tests/test_plan_amendment_service.py` (NEW, ~200 lines)

**Test Structure**:
```python
"""Unit tests for plan_amendment_service."""
import pytest
from datetime import datetime

from src.models import Event, EventFinishedGood, BatchDecision, FinishedGood, Recipe
from src.models.event import PlanState
from src.models.plan_amendment import AmendmentType
from src.services import plan_amendment_service
from src.services.exceptions import ValidationError, PlanStateError
from src.services.database import session_scope


class TestAmendmentValidation:
    """Tests for amendment validation rules."""

    def test_rejects_amendment_when_not_in_production(self):
        """Amendments require IN_PRODUCTION state."""
        with session_scope() as session:
            event = Event(
                name="Draft Event",
                event_date=datetime(2026, 12, 25).date(),
                year=2026,
                plan_state=PlanState.DRAFT,
            )
            session.add(event)
            session.flush()

            with pytest.raises(PlanStateError):
                plan_amendment_service.create_amendment(
                    event.id,
                    AmendmentType.DROP_FG,
                    {"fg_id": 1},
                    "test reason",
                    session
                )

    def test_rejects_amendment_with_empty_reason(self):
        """Amendments require non-empty reason."""
        with session_scope() as session:
            event = Event(
                name="In Production",
                event_date=datetime(2026, 12, 25).date(),
                year=2026,
                plan_state=PlanState.IN_PRODUCTION,
            )
            session.add(event)
            session.flush()

            with pytest.raises(ValidationError):
                plan_amendment_service.create_amendment(
                    event.id,
                    AmendmentType.DROP_FG,
                    {"fg_id": 1},
                    "",  # Empty reason
                    session
                )


class TestDropFinishedGood:
    """Tests for drop_finished_good function."""

    def test_drops_fg_and_creates_amendment(self):
        """Successfully drops FG and records amendment."""
        with session_scope() as session:
            # Setup
            event = Event(
                name="Test",
                event_date=datetime(2026, 12, 25).date(),
                year=2026,
                plan_state=PlanState.IN_PRODUCTION,
            )
            session.add(event)
            session.flush()

            # Need a real FG
            fg = session.query(FinishedGood).first()
            if not fg:
                pytest.skip("No FinishedGood in database")

            event_fg = EventFinishedGood(
                event_id=event.id,
                finished_good_id=fg.id,
                quantity=10,
            )
            session.add(event_fg)
            session.flush()

            # Drop
            amendment = plan_amendment_service.drop_finished_good(
                event.id, fg.id, "Not needed", session
            )

            # Verify amendment
            assert amendment.amendment_type == AmendmentType.DROP_FG
            assert amendment.amendment_data["fg_id"] == fg.id
            assert amendment.amendment_data["original_quantity"] == 10
            assert amendment.reason == "Not needed"

            # Verify EventFinishedGood deleted
            remaining = session.query(EventFinishedGood).filter(
                EventFinishedGood.event_id == event.id,
                EventFinishedGood.finished_good_id == fg.id,
            ).first()
            assert remaining is None

    def test_rejects_drop_when_fg_not_in_plan(self):
        """Cannot drop FG that's not in plan."""
        with session_scope() as session:
            event = Event(
                name="Test",
                event_date=datetime(2026, 12, 25).date(),
                year=2026,
                plan_state=PlanState.IN_PRODUCTION,
            )
            session.add(event)
            session.flush()

            with pytest.raises(ValidationError):
                plan_amendment_service.drop_finished_good(
                    event.id, 99999, "Test", session
                )


class TestAddFinishedGood:
    """Tests for add_finished_good function."""

    def test_adds_fg_and_creates_amendment(self):
        """Successfully adds FG and records amendment."""
        with session_scope() as session:
            event = Event(
                name="Test",
                event_date=datetime(2026, 12, 25).date(),
                year=2026,
                plan_state=PlanState.IN_PRODUCTION,
            )
            session.add(event)
            session.flush()

            fg = session.query(FinishedGood).first()
            if not fg:
                pytest.skip("No FinishedGood in database")

            amendment = plan_amendment_service.add_finished_good(
                event.id, fg.id, 5, "Adding more", session
            )

            assert amendment.amendment_type == AmendmentType.ADD_FG
            assert amendment.amendment_data["quantity"] == 5

            # Verify EventFinishedGood created
            event_fg = session.query(EventFinishedGood).filter(
                EventFinishedGood.event_id == event.id,
                EventFinishedGood.finished_good_id == fg.id,
            ).first()
            assert event_fg is not None
            assert event_fg.quantity == 5

    def test_rejects_add_when_fg_already_in_plan(self):
        """Cannot add FG that's already in plan."""
        with session_scope() as session:
            event = Event(
                name="Test",
                event_date=datetime(2026, 12, 25).date(),
                year=2026,
                plan_state=PlanState.IN_PRODUCTION,
            )
            session.add(event)
            session.flush()

            fg = session.query(FinishedGood).first()
            if not fg:
                pytest.skip("No FinishedGood in database")

            # Add first time
            event_fg = EventFinishedGood(
                event_id=event.id,
                finished_good_id=fg.id,
                quantity=10,
            )
            session.add(event_fg)
            session.flush()

            # Try to add again
            with pytest.raises(ValidationError):
                plan_amendment_service.add_finished_good(
                    event.id, fg.id, 5, "Duplicate", session
                )


class TestModifyBatchDecision:
    """Tests for modify_batch_decision function."""

    def test_modifies_batch_and_creates_amendment(self):
        """Successfully modifies batch count and records amendment."""
        with session_scope() as session:
            event = Event(
                name="Test",
                event_date=datetime(2026, 12, 25).date(),
                year=2026,
                plan_state=PlanState.IN_PRODUCTION,
            )
            session.add(event)
            session.flush()

            recipe = session.query(Recipe).first()
            if not recipe:
                pytest.skip("No Recipe in database")

            batch_decision = BatchDecision(
                event_id=event.id,
                recipe_id=recipe.id,
                batches=5,
                yield_per_batch=24,
            )
            session.add(batch_decision)
            session.flush()

            amendment = plan_amendment_service.modify_batch_decision(
                event.id, recipe.id, 8, "Need more", session
            )

            assert amendment.amendment_type == AmendmentType.MODIFY_BATCH
            assert amendment.amendment_data["old_batches"] == 5
            assert amendment.amendment_data["new_batches"] == 8

            # Verify BatchDecision updated
            session.refresh(batch_decision)
            assert batch_decision.batches == 8


class TestGetAmendments:
    """Tests for get_amendments function."""

    def test_returns_amendments_in_chronological_order(self):
        """Amendments returned oldest first."""
        with session_scope() as session:
            event = Event(
                name="Test",
                event_date=datetime(2026, 12, 25).date(),
                year=2026,
                plan_state=PlanState.IN_PRODUCTION,
            )
            session.add(event)
            session.flush()

            # Create multiple amendments
            for i in range(3):
                plan_amendment_service.create_amendment(
                    event.id,
                    AmendmentType.DROP_FG,
                    {"fg_id": i},
                    f"Reason {i}",
                    session
                )

            amendments = plan_amendment_service.get_amendments(event.id, session)

            assert len(amendments) == 3
            # Verify chronological order
            for i in range(len(amendments) - 1):
                assert amendments[i].created_at <= amendments[i + 1].created_at

    def test_returns_empty_list_when_no_amendments(self):
        """Returns empty list for event with no amendments."""
        with session_scope() as session:
            event = Event(
                name="No Amendments",
                event_date=datetime(2026, 12, 25).date(),
                year=2026,
            )
            session.add(event)
            session.flush()

            amendments = plan_amendment_service.get_amendments(event.id, session)
            assert amendments == []
```

**Validation**:
- All tests pass: `./run-tests.sh src/tests/test_plan_amendment_service.py -v`

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session detachment | Pass session through; load data before session closes |
| Data integrity | Validate existence before modification |
| Concurrent amendments | Database handles with standard locking |
| Missing related data | Handle None gracefully in amendment_data |

---

## Definition of Done Checklist

- [ ] `src/services/plan_amendment_service.py` created
- [ ] State validation (IN_PRODUCTION only) works
- [ ] Reason validation (non-empty) works
- [ ] `drop_finished_good()` validates, deletes, and records
- [ ] `add_finished_good()` validates, creates, and records
- [ ] `modify_batch_decision()` validates, updates, and records
- [ ] `get_amendments()` returns chronological list
- [ ] All tests pass: `./run-tests.sh src/tests/test_plan_amendment_service.py -v`

---

## Review Guidance

**Key Acceptance Checkpoints**:
1. Verify state validation rejects non-IN_PRODUCTION
2. Verify reason validation rejects empty strings
3. Check DROP_FG deletes EventFinishedGood
4. Check ADD_FG creates EventFinishedGood
5. Check MODIFY_BATCH updates BatchDecision
6. Run tests: `./run-tests.sh src/tests/test_plan_amendment_service.py -v`

---

## Activity Log

- 2026-01-28T03:25:47Z – system – lane=planned – Prompt created.
