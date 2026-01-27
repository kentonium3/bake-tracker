---
work_package_id: WP02
title: Modification Guards
lane: "for_review"
dependencies:
- WP01
base_branch: 077-plan-state-management-WP01
base_commit: a6cfd406f35e89c0d0f113dbe562f6cfcab55113
created_at: '2026-01-27T22:43:46.167060+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
phase: Phase 2 - Service Layer Guards
assignee: ''
agent: "gemini"
shell_pid: "56450"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-28T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Modification Guards

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

## Objectives & Success Criteria

Add state-based modification guards to existing service functions that prevent changes based on plan state.

**Success Criteria**:
- [ ] Recipe modifications (set_event_recipes) blocked when plan_state != DRAFT
- [ ] FG modifications (set_event_fg_quantities) blocked when plan_state != DRAFT
- [ ] Batch decision modifications allowed when plan_state is DRAFT or LOCKED
- [ ] Batch decision modifications blocked when plan_state is IN_PRODUCTION or COMPLETED
- [ ] All guards raise PlanStateError with clear message
- [ ] Integration tests verify guard behavior
- [ ] UI error handling updated to catch PlanStateError

## Context & Constraints

**Reference Documents**:
- `kitty-specs/077-plan-state-management/spec.md` - FR-005 through FR-008
- `kitty-specs/077-plan-state-management/plan.md` - D2 (inline state checks)

**Modification Rules by State** (from plan.md):

| Operation | DRAFT | LOCKED | IN_PRODUCTION | COMPLETED |
|-----------|-------|--------|---------------|-----------|
| Add/remove recipes | ✅ | ❌ | ❌ | ❌ |
| Add/remove FGs | ✅ | ❌ | ❌ | ❌ |
| Change FG quantities | ✅ | ❌ | ❌ | ❌ |
| Modify batch decisions | ✅ | ✅ | ❌ | ❌ |

**Key Files to Modify**:
- `src/services/event_service.py` - set_event_recipes(), set_event_fg_quantities()
- `src/services/batch_decision_service.py` - save_batch_decisions()
- `src/ui/planning_tab.py` - Error handling in save callbacks

## Subtasks & Detailed Guidance

### Subtask T006 – Guard set_event_recipes()

**Purpose**: Prevent recipe modifications when plan is not in DRAFT state.

**Steps**:
1. Open `src/services/event_service.py`
2. Find the `set_event_recipes()` function (around line 3039)
3. Add import at top of file (if not present):
```python
from src.services.exceptions import PlanStateError
```

4. Add state check at the beginning of the function, after event validation:

```python
def set_event_recipes(
    session: Session,
    event_id: int,
    recipe_ids: List[int],
) -> Tuple[int, List[RemovedFGInfo]]:
    """
    Set the recipes for an event...
    """
    # Validate event exists
    event = session.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValidationError([f"Event {event_id} not found"])

    # F077: Check plan state - only DRAFT allows recipe modifications
    if event.plan_state != PlanState.DRAFT:
        raise PlanStateError(
            event_id,
            event.plan_state,
            "modify recipes"
        )

    # ... rest of existing implementation
```

**Files**: `src/services/event_service.py`

**Validation**:
- [ ] Calling set_event_recipes() on DRAFT event works normally
- [ ] Calling set_event_recipes() on LOCKED event raises PlanStateError
- [ ] Calling set_event_recipes() on IN_PRODUCTION event raises PlanStateError
- [ ] Calling set_event_recipes() on COMPLETED event raises PlanStateError

---

### Subtask T007 – Guard set_event_fg_quantities()

**Purpose**: Prevent FG modifications when plan is not in DRAFT state.

**Steps**:
1. In `src/services/event_service.py`, find `set_event_fg_quantities()` (around line 3216)
2. Add state check after event validation:

```python
def set_event_fg_quantities(
    session: Session,
    event_id: int,
    fg_quantities: List[Tuple[int, int]],
) -> int:
    """
    Set finished goods quantities for an event...
    """
    # Validate event exists
    event = session.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValidationError([f"Event {event_id} not found"])

    # F077: Check plan state - only DRAFT allows FG modifications
    if event.plan_state != PlanState.DRAFT:
        raise PlanStateError(
            event_id,
            event.plan_state,
            "modify finished goods"
        )

    # ... rest of existing implementation
```

**Files**: `src/services/event_service.py`

**Validation**:
- [ ] Calling set_event_fg_quantities() on DRAFT event works normally
- [ ] Calling set_event_fg_quantities() on LOCKED event raises PlanStateError
- [ ] Calling set_event_fg_quantities() on IN_PRODUCTION event raises PlanStateError
- [ ] Calling set_event_fg_quantities() on COMPLETED event raises PlanStateError

---

### Subtask T008 – Guard save_batch_decisions()

**Purpose**: Allow batch decision modifications in DRAFT and LOCKED states only.

**Steps**:
1. Open `src/services/batch_decision_service.py`
2. Add import:
```python
from src.models.event import PlanState
from src.services.exceptions import PlanStateError
```

3. Find `save_batch_decisions()` function and add state check:

```python
def save_batch_decisions(
    event_id: int,
    decisions: List[BatchDecisionInput],
    session: Session = None,
) -> List[BatchDecision]:
    """Save batch decisions for an event..."""

    def _save_impl(session: Session) -> List[BatchDecision]:
        # Validate event
        event = _validate_event_exists(event_id, session)

        # F077: Check plan state - DRAFT and LOCKED allow batch decision modifications
        if event.plan_state not in (PlanState.DRAFT, PlanState.LOCKED):
            raise PlanStateError(
                event_id,
                event.plan_state,
                "modify batch decisions"
            )

        # ... rest of existing implementation
```

Note: The exact structure depends on how save_batch_decisions is currently implemented. The key is to add the state check after validating the event exists.

**Files**: `src/services/batch_decision_service.py`

**Validation**:
- [ ] save_batch_decisions() on DRAFT event works normally
- [ ] save_batch_decisions() on LOCKED event works normally
- [ ] save_batch_decisions() on IN_PRODUCTION event raises PlanStateError
- [ ] save_batch_decisions() on COMPLETED event raises PlanStateError

---

### Subtask T009 – Write Integration Tests

**Purpose**: Test guard behavior with actual database transactions.

**Steps**:
1. Create `src/tests/integration/test_plan_state_guards.py`:

```python
"""Integration tests for plan state modification guards (F077).

Tests verify that modification guards correctly block operations
based on event plan state.
"""

import pytest
from datetime import date

from src.models.event import Event, PlanState
from src.models.recipe import Recipe
from src.models.finished_good import FinishedGood
from src.services.database import session_scope
from src.services.event_service import set_event_recipes, set_event_fg_quantities
from src.services.batch_decision_service import save_batch_decisions, BatchDecisionInput
from src.services.plan_state_service import lock_plan, start_production, complete_production
from src.services.exceptions import PlanStateError


@pytest.fixture
def event_with_recipe():
    """Create an event with a recipe in DRAFT state."""
    with session_scope() as session:
        # Create a minimal recipe
        recipe = Recipe(name="Test Recipe", slug="test_recipe")
        session.add(recipe)
        session.flush()
        recipe_id = recipe.id

        # Create event
        event = Event(
            name="Test Event",
            date=date(2026, 12, 25),
            plan_state=PlanState.DRAFT,
        )
        session.add(event)
        session.flush()
        event_id = event.id

    return {"event_id": event_id, "recipe_id": recipe_id}


class TestRecipeGuards:
    """Tests for set_event_recipes() guard."""

    def test_draft_allows_modification(self, event_with_recipe):
        """DRAFT state should allow recipe modifications."""
        event_id = event_with_recipe["event_id"]
        recipe_id = event_with_recipe["recipe_id"]

        with session_scope() as session:
            count, _ = set_event_recipes(session, event_id, [recipe_id])
            assert count >= 0  # No error raised

    def test_locked_blocks_modification(self, event_with_recipe):
        """LOCKED state should block recipe modifications."""
        event_id = event_with_recipe["event_id"]
        recipe_id = event_with_recipe["recipe_id"]

        lock_plan(event_id)

        with pytest.raises(PlanStateError) as exc_info:
            with session_scope() as session:
                set_event_recipes(session, event_id, [recipe_id])

        assert "recipes" in str(exc_info.value).lower()
        assert exc_info.value.current_state == PlanState.LOCKED

    def test_in_production_blocks_modification(self, event_with_recipe):
        """IN_PRODUCTION state should block recipe modifications."""
        event_id = event_with_recipe["event_id"]
        recipe_id = event_with_recipe["recipe_id"]

        lock_plan(event_id)
        start_production(event_id)

        with pytest.raises(PlanStateError):
            with session_scope() as session:
                set_event_recipes(session, event_id, [recipe_id])

    def test_completed_blocks_modification(self, event_with_recipe):
        """COMPLETED state should block recipe modifications."""
        event_id = event_with_recipe["event_id"]
        recipe_id = event_with_recipe["recipe_id"]

        lock_plan(event_id)
        start_production(event_id)
        complete_production(event_id)

        with pytest.raises(PlanStateError):
            with session_scope() as session:
                set_event_recipes(session, event_id, [recipe_id])


class TestFGGuards:
    """Tests for set_event_fg_quantities() guard."""

    def test_draft_allows_modification(self, event_with_recipe):
        """DRAFT state should allow FG modifications."""
        event_id = event_with_recipe["event_id"]

        with session_scope() as session:
            # Empty list is valid - just testing no PlanStateError
            count = set_event_fg_quantities(session, event_id, [])
            assert count >= 0

    def test_locked_blocks_modification(self, event_with_recipe):
        """LOCKED state should block FG modifications."""
        event_id = event_with_recipe["event_id"]

        lock_plan(event_id)

        with pytest.raises(PlanStateError) as exc_info:
            with session_scope() as session:
                set_event_fg_quantities(session, event_id, [])

        assert "finished goods" in str(exc_info.value).lower()


class TestBatchDecisionGuards:
    """Tests for save_batch_decisions() guard."""

    def test_draft_allows_modification(self, event_with_recipe):
        """DRAFT state should allow batch decision modifications."""
        event_id = event_with_recipe["event_id"]

        # Empty list is valid
        result = save_batch_decisions(event_id, [])
        assert isinstance(result, list)

    def test_locked_allows_modification(self, event_with_recipe):
        """LOCKED state should allow batch decision modifications."""
        event_id = event_with_recipe["event_id"]

        lock_plan(event_id)

        # Should not raise - LOCKED allows batch decisions
        result = save_batch_decisions(event_id, [])
        assert isinstance(result, list)

    def test_in_production_blocks_modification(self, event_with_recipe):
        """IN_PRODUCTION state should block batch decision modifications."""
        event_id = event_with_recipe["event_id"]

        lock_plan(event_id)
        start_production(event_id)

        with pytest.raises(PlanStateError) as exc_info:
            save_batch_decisions(event_id, [])

        assert "batch decisions" in str(exc_info.value).lower()

    def test_completed_blocks_modification(self, event_with_recipe):
        """COMPLETED state should block batch decision modifications."""
        event_id = event_with_recipe["event_id"]

        lock_plan(event_id)
        start_production(event_id)
        complete_production(event_id)

        with pytest.raises(PlanStateError):
            save_batch_decisions(event_id, [])
```

2. Run tests:
```bash
pytest src/tests/integration/test_plan_state_guards.py -v
```

**Files**: `src/tests/integration/test_plan_state_guards.py` (new file)

**Validation**:
- [ ] All integration tests pass
- [ ] Tests cover all state combinations for each operation
- [ ] Tests use actual database transactions

---

### Subtask T010 – Update UI Error Handling

**Purpose**: Ensure planning_tab.py save handlers catch and display PlanStateError gracefully.

**Steps**:
1. Open `src/ui/planning_tab.py`
2. Add import at top:
```python
from src.services.exceptions import PlanStateError
```

3. Find `_on_recipe_selection_save()` method and update error handling:
```python
def _on_recipe_selection_save(self, selected_recipe_ids: List[int]) -> None:
    """Handle save from recipe selection frame."""
    if self._selected_event_id is None:
        return

    try:
        with session_scope() as session:
            # ... existing save logic ...
    except PlanStateError as e:
        # F077: User-friendly message for state violations
        self._update_status(f"Cannot save: {e.attempted_action} not allowed (plan is {e.current_state.value})")
        messagebox.showwarning(
            "Plan Locked",
            f"Cannot modify recipes.\n\nThe plan is currently '{e.current_state.value}'.\n"
            "Recipe changes are only allowed when the plan is in 'draft' state."
        )
    except Exception as e:
        # ... existing error handling ...
```

4. Find `_on_fg_selection_save()` method and add similar handling:
```python
def _on_fg_selection_save(self, ...) -> None:
    """Handle save from FG selection frame."""
    try:
        # ... existing save logic ...
    except PlanStateError as e:
        self._update_status(f"Cannot save: {e.attempted_action} not allowed")
        messagebox.showwarning(
            "Plan Locked",
            f"Cannot modify finished goods.\n\nThe plan is currently '{e.current_state.value}'.\n"
            "Finished goods changes are only allowed when the plan is in 'draft' state."
        )
    except Exception as e:
        # ... existing error handling ...
```

5. Find `_save_batch_decisions()` method and add handling:
```python
def _save_batch_decisions(self) -> None:
    """Save batch decisions..."""
    try:
        # ... existing save logic ...
    except PlanStateError as e:
        self._update_status(f"Cannot save: {e.attempted_action} not allowed")
        messagebox.showwarning(
            "Plan Locked",
            f"Cannot modify batch decisions.\n\nThe plan is currently '{e.current_state.value}'.\n"
            "Batch decision changes are only allowed when the plan is in 'draft' or 'locked' state."
        )
    except Exception as e:
        # ... existing error handling ...
```

**Files**: `src/ui/planning_tab.py`

**Validation**:
- [ ] Recipe save on locked plan shows warning dialog
- [ ] FG save on locked plan shows warning dialog
- [ ] Batch decision save on in_production plan shows warning dialog
- [ ] Status bar updates with user-friendly message
- [ ] App doesn't crash on state violations

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing tests | Run full test suite after each change |
| Import cycles | Import PlanStateError from exceptions, not plan_state_service |
| Missing error paths | Test manually with locked events |

## Definition of Done Checklist

- [ ] set_event_recipes() has state guard
- [ ] set_event_fg_quantities() has state guard
- [ ] save_batch_decisions() has state guard (DRAFT/LOCKED allowed)
- [ ] All integration tests pass
- [ ] UI catches PlanStateError and shows user-friendly message
- [ ] Existing tests still pass
- [ ] No linting errors

## Review Guidance

- Verify guards check state AFTER validating event exists
- Verify batch decisions allow both DRAFT and LOCKED states
- Verify UI messages are user-friendly, not technical
- Test with actual UI if possible (manual testing)

## Activity Log

- 2026-01-28T00:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-27T22:49:33Z – gemini – shell_pid=56450 – lane=for_review – Implementation complete - all guards added and tested
