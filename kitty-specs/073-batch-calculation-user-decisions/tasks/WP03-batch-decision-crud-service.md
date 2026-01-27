---
work_package_id: WP03
title: Batch Decision CRUD Service
lane: "doing"
dependencies:
- WP01
base_branch: 073-batch-calculation-user-decisions-WP01
base_commit: 7eedb5fedcdc079a25704e92d054b4d18c98bc46
created_at: '2026-01-27T19:31:06.701223+00:00'
subtasks:
- T015
- T016
- T017
- T018
- T019
- T020
- T021
phase: Phase 1 - Core Service
assignee: ''
agent: "claude"
shell_pid: "22322"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-27T18:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Batch Decision CRUD Service

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

This WP depends on WP01 (BatchDecision schema change). Can run in parallel with WP02.

```bash
spec-kitty implement WP03
```

---

## Objectives & Success Criteria

**Primary Objective**: Implement persistence layer for batch decisions with validation and shortfall confirmation logic.

**Success Criteria**:
1. `save_batch_decision()` validates and persists a single decision
2. `get_batch_decisions(event_id)` returns all decisions for an event
3. `get_batch_decision(event_id, finished_unit_id)` returns single decision
4. `delete_batch_decisions(event_id)` clears all decisions for an event
5. Shortfall validation enforced: if `is_shortfall=True`, require `confirmed_shortfall=True`
6. All CRUD operations follow session parameter pattern

---

## Context & Constraints

**Why this is needed**: Batch decisions must be persisted so users can save their selections and reload them later. Validation ensures data integrity.

**Key Documents**:
- `kitty-specs/073-batch-calculation-user-decisions/data-model.md` - BatchDecisionInput dataclass
- `src/services/event_service.py` - CRUD patterns to follow
- `CLAUDE.md` - Session parameter pattern

**Constraints**:
- Follow existing service patterns from `event_service.py`
- Accept optional `session` parameter for transaction sharing
- Raise `ValidationError` for business rule violations
- Use `session.flush()` before return

---

## Subtasks & Detailed Guidance

### Subtask T015 – Create batch_decision_service.py module

**Purpose**: Set up the new service file with imports.

**Steps**:
1. Create `src/services/batch_decision_service.py`
2. Add standard imports:

```python
"""Service layer for batch decision CRUD operations."""
from typing import List, Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.models.batch_decision import BatchDecision
from src.models.event import Event
from src.models.finished_unit import FinishedUnit
from src.services.database import session_scope
from src.utils.errors import ValidationError


@dataclass
class BatchDecisionInput:
    """User's batch decision for one FU."""
    finished_unit_id: int
    batches: int
    is_shortfall: bool = False
    confirmed_shortfall: bool = False
```

**Files**: `src/services/batch_decision_service.py` (NEW)
**Parallel?**: No - must be first

---

### Subtask T016 – Implement save_batch_decision()

**Purpose**: Save or update a single batch decision with validation.

**Steps**:
1. Add the function:

```python
def save_batch_decision(
    event_id: int,
    decision: BatchDecisionInput,
    session: Session = None,
) -> BatchDecision:
    """
    Save or update a single batch decision.

    Args:
        event_id: The Event ID
        decision: BatchDecisionInput with FU ID, batches, and shortfall flags
        session: Optional session for transaction sharing

    Returns:
        The saved BatchDecision object

    Raises:
        ValidationError: If validation fails
    """
    if session is not None:
        return _save_batch_decision_impl(event_id, decision, session)
    with session_scope() as session:
        return _save_batch_decision_impl(event_id, decision, session)


def _save_batch_decision_impl(
    event_id: int,
    decision: BatchDecisionInput,
    session: Session,
) -> BatchDecision:
    """Implementation of save_batch_decision."""
    errors = []

    # Validate event exists
    event = session.query(Event).filter(Event.id == event_id).first()
    if event is None:
        errors.append(f"Event with id {event_id} not found")

    # Validate FU exists
    fu = session.query(FinishedUnit).filter(
        FinishedUnit.id == decision.finished_unit_id
    ).first()
    if fu is None:
        errors.append(f"FinishedUnit with id {decision.finished_unit_id} not found")

    # Validate batches > 0
    if decision.batches <= 0:
        errors.append("Batches must be greater than 0")

    # Validate shortfall confirmation
    if decision.is_shortfall and not decision.confirmed_shortfall:
        errors.append(
            "Shortfall selection requires confirmation. "
            "Set confirmed_shortfall=True to acknowledge."
        )

    if errors:
        raise ValidationError(errors)

    # Check for existing decision (upsert pattern)
    existing = session.query(BatchDecision).filter(
        BatchDecision.event_id == event_id,
        BatchDecision.finished_unit_id == decision.finished_unit_id,
    ).first()

    if existing:
        # Update existing
        existing.batches = decision.batches
        existing.recipe_id = fu.recipe_id
        batch_decision = existing
    else:
        # Create new
        batch_decision = BatchDecision(
            event_id=event_id,
            recipe_id=fu.recipe_id,
            finished_unit_id=decision.finished_unit_id,
            batches=decision.batches,
        )
        session.add(batch_decision)

    session.flush()
    return batch_decision
```

**Files**: `src/services/batch_decision_service.py`
**Parallel?**: Yes (after T015)

---

### Subtask T017 – Implement get_batch_decisions()

**Purpose**: Retrieve all batch decisions for an event.

**Steps**:
1. Add the function:

```python
def get_batch_decisions(
    event_id: int,
    session: Session = None,
) -> List[BatchDecision]:
    """
    Get all batch decisions for an event.

    Args:
        event_id: The Event ID
        session: Optional session for transaction sharing

    Returns:
        List of BatchDecision objects for the event
    """
    if session is not None:
        return _get_batch_decisions_impl(event_id, session)
    with session_scope() as session:
        return _get_batch_decisions_impl(event_id, session)


def _get_batch_decisions_impl(
    event_id: int,
    session: Session,
) -> List[BatchDecision]:
    """Implementation of get_batch_decisions."""
    return session.query(BatchDecision).filter(
        BatchDecision.event_id == event_id
    ).all()
```

**Files**: `src/services/batch_decision_service.py`
**Parallel?**: Yes (after T015)

---

### Subtask T018 – Implement get_batch_decision() single lookup

**Purpose**: Retrieve a specific batch decision by event and FU.

**Steps**:
1. Add the function:

```python
def get_batch_decision(
    event_id: int,
    finished_unit_id: int,
    session: Session = None,
) -> Optional[BatchDecision]:
    """
    Get batch decision for a specific FU in an event.

    Args:
        event_id: The Event ID
        finished_unit_id: The FinishedUnit ID
        session: Optional session for transaction sharing

    Returns:
        BatchDecision if found, None otherwise
    """
    if session is not None:
        return _get_batch_decision_impl(event_id, finished_unit_id, session)
    with session_scope() as session:
        return _get_batch_decision_impl(event_id, finished_unit_id, session)


def _get_batch_decision_impl(
    event_id: int,
    finished_unit_id: int,
    session: Session,
) -> Optional[BatchDecision]:
    """Implementation of get_batch_decision."""
    return session.query(BatchDecision).filter(
        BatchDecision.event_id == event_id,
        BatchDecision.finished_unit_id == finished_unit_id,
    ).first()
```

**Files**: `src/services/batch_decision_service.py`
**Parallel?**: Yes (after T015)

---

### Subtask T019 – Implement delete_batch_decisions()

**Purpose**: Clear all batch decisions for an event.

**Steps**:
1. Add the function:

```python
def delete_batch_decisions(
    event_id: int,
    session: Session = None,
) -> int:
    """
    Delete all batch decisions for an event.

    Args:
        event_id: The Event ID
        session: Optional session for transaction sharing

    Returns:
        Count of deleted decisions
    """
    if session is not None:
        return _delete_batch_decisions_impl(event_id, session)
    with session_scope() as session:
        return _delete_batch_decisions_impl(event_id, session)


def _delete_batch_decisions_impl(
    event_id: int,
    session: Session,
) -> int:
    """Implementation of delete_batch_decisions."""
    count = session.query(BatchDecision).filter(
        BatchDecision.event_id == event_id
    ).delete()
    session.flush()
    return count
```

**Files**: `src/services/batch_decision_service.py`
**Parallel?**: Yes (after T015)

---

### Subtask T020 – Add shortfall confirmation validation

**Purpose**: Ensure shortfall selections require explicit user confirmation.

**Steps**:
1. Review T016 implementation - shortfall validation is already included
2. Add helper function for UI layer:

```python
def is_shortfall_option(batches: int, yield_per_batch: int, quantity_needed: int) -> bool:
    """
    Determine if a batch selection results in a shortfall.

    Args:
        batches: Number of batches selected
        yield_per_batch: Items produced per batch
        quantity_needed: Items needed

    Returns:
        True if total yield < quantity needed
    """
    total_yield = batches * yield_per_batch
    return total_yield < quantity_needed
```

3. Ensure validation error message is clear and actionable

**Files**: `src/services/batch_decision_service.py`
**Parallel?**: No - refinement

---

### Subtask T021 – Write tests

**Purpose**: Comprehensive test coverage for CRUD operations.

**Steps**:
1. Create `src/tests/test_batch_decision_service.py`
2. Write tests:

```python
"""Tests for batch decision CRUD service (F073)."""
import pytest
from src.services.batch_decision_service import (
    save_batch_decision,
    get_batch_decisions,
    get_batch_decision,
    delete_batch_decisions,
    BatchDecisionInput,
    is_shortfall_option,
)
from src.models.batch_decision import BatchDecision
from src.utils.errors import ValidationError


class TestSaveBatchDecision:
    """Tests for save_batch_decision()."""

    def test_creates_new_decision(self, test_db, sample_event, sample_fu):
        """Creates new decision when none exists."""
        decision = BatchDecisionInput(
            finished_unit_id=sample_fu.id,
            batches=3,
        )
        result = save_batch_decision(sample_event.id, decision, session=test_db)

        assert result.id is not None
        assert result.event_id == sample_event.id
        assert result.finished_unit_id == sample_fu.id
        assert result.batches == 3

    def test_updates_existing_decision(self, test_db, sample_event, sample_fu):
        """Updates existing decision (upsert)."""
        # Create initial
        decision1 = BatchDecisionInput(finished_unit_id=sample_fu.id, batches=3)
        save_batch_decision(sample_event.id, decision1, session=test_db)

        # Update
        decision2 = BatchDecisionInput(finished_unit_id=sample_fu.id, batches=5)
        result = save_batch_decision(sample_event.id, decision2, session=test_db)

        assert result.batches == 5
        # Verify only one record exists
        all_decisions = get_batch_decisions(sample_event.id, session=test_db)
        assert len(all_decisions) == 1

    def test_validates_event_exists(self, test_db, sample_fu):
        """Raises ValidationError for non-existent event."""
        decision = BatchDecisionInput(finished_unit_id=sample_fu.id, batches=3)
        with pytest.raises(ValidationError) as exc:
            save_batch_decision(99999, decision, session=test_db)
        assert "Event with id 99999 not found" in str(exc.value)

    def test_validates_fu_exists(self, test_db, sample_event):
        """Raises ValidationError for non-existent FU."""
        decision = BatchDecisionInput(finished_unit_id=99999, batches=3)
        with pytest.raises(ValidationError) as exc:
            save_batch_decision(sample_event.id, decision, session=test_db)
        assert "FinishedUnit with id 99999 not found" in str(exc.value)

    def test_validates_batches_positive(self, test_db, sample_event, sample_fu):
        """Raises ValidationError for non-positive batches."""
        decision = BatchDecisionInput(finished_unit_id=sample_fu.id, batches=0)
        with pytest.raises(ValidationError) as exc:
            save_batch_decision(sample_event.id, decision, session=test_db)
        assert "Batches must be greater than 0" in str(exc.value)

    def test_shortfall_requires_confirmation(self, test_db, sample_event, sample_fu):
        """Raises ValidationError if shortfall not confirmed."""
        decision = BatchDecisionInput(
            finished_unit_id=sample_fu.id,
            batches=2,
            is_shortfall=True,
            confirmed_shortfall=False,
        )
        with pytest.raises(ValidationError) as exc:
            save_batch_decision(sample_event.id, decision, session=test_db)
        assert "Shortfall selection requires confirmation" in str(exc.value)

    def test_confirmed_shortfall_allowed(self, test_db, sample_event, sample_fu):
        """Allows shortfall when confirmed."""
        decision = BatchDecisionInput(
            finished_unit_id=sample_fu.id,
            batches=2,
            is_shortfall=True,
            confirmed_shortfall=True,
        )
        result = save_batch_decision(sample_event.id, decision, session=test_db)
        assert result.batches == 2


class TestGetBatchDecisions:
    """Tests for get_batch_decisions()."""

    def test_returns_all_for_event(self, test_db, sample_event, sample_fus):
        """Returns all decisions for an event."""
        # Create multiple decisions
        for fu in sample_fus[:3]:
            decision = BatchDecisionInput(finished_unit_id=fu.id, batches=2)
            save_batch_decision(sample_event.id, decision, session=test_db)

        results = get_batch_decisions(sample_event.id, session=test_db)
        assert len(results) == 3

    def test_returns_empty_for_no_decisions(self, test_db, sample_event):
        """Returns empty list when no decisions exist."""
        results = get_batch_decisions(sample_event.id, session=test_db)
        assert results == []


class TestGetBatchDecision:
    """Tests for get_batch_decision() single lookup."""

    def test_returns_decision_if_exists(self, test_db, sample_event, sample_fu):
        """Returns decision for specific event+FU."""
        decision = BatchDecisionInput(finished_unit_id=sample_fu.id, batches=4)
        save_batch_decision(sample_event.id, decision, session=test_db)

        result = get_batch_decision(
            sample_event.id, sample_fu.id, session=test_db
        )
        assert result is not None
        assert result.batches == 4

    def test_returns_none_if_not_exists(self, test_db, sample_event, sample_fu):
        """Returns None if no decision exists."""
        result = get_batch_decision(
            sample_event.id, sample_fu.id, session=test_db
        )
        assert result is None


class TestDeleteBatchDecisions:
    """Tests for delete_batch_decisions()."""

    def test_deletes_all_for_event(self, test_db, sample_event, sample_fus):
        """Deletes all decisions for an event."""
        # Create decisions
        for fu in sample_fus[:3]:
            decision = BatchDecisionInput(finished_unit_id=fu.id, batches=2)
            save_batch_decision(sample_event.id, decision, session=test_db)

        count = delete_batch_decisions(sample_event.id, session=test_db)
        assert count == 3

        # Verify deleted
        remaining = get_batch_decisions(sample_event.id, session=test_db)
        assert remaining == []

    def test_returns_zero_for_no_decisions(self, test_db, sample_event):
        """Returns 0 when no decisions to delete."""
        count = delete_batch_decisions(sample_event.id, session=test_db)
        assert count == 0


class TestIsShortfallOption:
    """Tests for is_shortfall_option helper."""

    def test_shortfall_detected(self):
        """Detects shortfall when yield < needed."""
        assert is_shortfall_option(batches=2, yield_per_batch=24, quantity_needed=50)

    def test_no_shortfall_when_equal(self):
        """No shortfall when yield == needed."""
        assert not is_shortfall_option(batches=2, yield_per_batch=24, quantity_needed=48)

    def test_no_shortfall_when_surplus(self):
        """No shortfall when yield > needed."""
        assert not is_shortfall_option(batches=3, yield_per_batch=24, quantity_needed=50)
```

3. Run tests: `./run-tests.sh src/tests/test_batch_decision_service.py -v`

**Files**: `src/tests/test_batch_decision_service.py` (NEW)
**Parallel?**: Yes (write alongside T016-T020)

---

## Test Strategy

**Required Tests** (in `src/tests/test_batch_decision_service.py`):
- Create new decision
- Update existing decision (upsert)
- Validate event exists
- Validate FU exists
- Validate batches > 0
- Shortfall requires confirmation
- Confirmed shortfall allowed
- Get all decisions for event
- Get single decision
- Delete all decisions
- is_shortfall_option helper

**Run Command**:
```bash
./run-tests.sh src/tests/test_batch_decision_service.py -v
```

**Expected Outcome**: All tests pass, >70% coverage

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Session management issues | Medium | Follow CLAUDE.md session patterns |
| Orphaned decisions after FG removal | Low | CASCADE delete handles this |
| Concurrent modification | Low | Single-user app, no locking needed |

---

## Definition of Done Checklist

- [ ] batch_decision_service.py created
- [ ] BatchDecisionInput dataclass defined
- [ ] save_batch_decision() with validation implemented
- [ ] get_batch_decisions() implemented
- [ ] get_batch_decision() implemented
- [ ] delete_batch_decisions() implemented
- [ ] Shortfall confirmation validation working
- [ ] is_shortfall_option() helper implemented
- [ ] All tests passing
- [ ] >70% coverage for new code

---

## Review Guidance

**Key Checkpoints**:
1. **Session management**: All functions accept optional session parameter
2. **Validation**: All business rules enforced before save
3. **Error messages**: Clear and actionable
4. **Upsert pattern**: Save updates existing or creates new

**Questions for Review**:
- Is the shortfall confirmation flow clear to the UI layer?
- Are validation error messages user-friendly?

---

## Activity Log

- 2026-01-27T18:00:00Z – system – lane=planned – Prompt created.
- 2026-01-27T19:35:17Z – gemini – shell_pid=19392 – lane=for_review – All subtasks complete (T015-T021), 33 tests passing
- 2026-01-27T19:40:14Z – claude – shell_pid=22322 – lane=doing – Started review via workflow command
