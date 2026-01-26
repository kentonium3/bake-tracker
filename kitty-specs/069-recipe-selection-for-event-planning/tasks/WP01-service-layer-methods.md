---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
title: "Service Layer Methods"
phase: "Phase 1 - Service Layer"
lane: "doing"
assignee: ""
agent: "claude-opus-4-5"
shell_pid: "14143"
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-01-26T22:57:43Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Service Layer Methods

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged`.
- **Report progress**: As you address each feedback item, update the Activity Log.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

No dependencies - start from main:

```bash
spec-kitty implement WP01
```

---

## Objectives & Success Criteria

**Goal**: Implement recipe selection service methods in `event_service.py` that allow:
1. Retrieving the list of recipe IDs currently selected for an event
2. Replacing all recipe selections for an event with a new list

**Success Criteria**:
- `get_event_recipe_ids(session, event_id)` returns list of recipe IDs for an event
- `set_event_recipes(session, event_id, recipe_ids)` replaces selections atomically
- Both methods handle validation (event exists, recipes exist)
- Unit tests achieve >70% coverage of new methods
- All existing tests continue to pass

## Context & Constraints

**Reference Documents**:
- `.kittify/memory/constitution.md` - Core principles (Layered Architecture, Test-Driven)
- `kitty-specs/069-recipe-selection-for-event-planning/plan.md` - Architecture decisions
- `kitty-specs/069-recipe-selection-for-event-planning/data-model.md` - Service signatures and queries
- `kitty-specs/069-recipe-selection-for-event-planning/research.md` - Implementation patterns

**Key Constraints**:
- Use existing `EventRecipe` model from F068 (no schema changes)
- Follow session management guidelines from CLAUDE.md (accept optional `session` parameter)
- Use delete-then-insert pattern for atomic replacement
- Raise `ValidationError` for invalid inputs (consistent with existing patterns)

**Existing Code References**:
- `src/models/event_recipe.py` - Junction table model
- `src/services/event_service.py` - Add new methods here
- `src/tests/test_event_planning.py` - Existing F068 tests

---

## Subtasks & Detailed Guidance

### Subtask T001 – Implement `get_event_recipe_ids` Method

**Purpose**: Retrieve the list of recipe IDs currently selected for a given event.

**Steps**:
1. Open `src/services/event_service.py`
2. Add the following method (place near other event query methods):

```python
def get_event_recipe_ids(
    session: Session,
    event_id: int,
) -> List[int]:
    """
    Get IDs of all recipes selected for an event.

    Args:
        session: Database session
        event_id: Target event ID

    Returns:
        List of selected recipe IDs (empty if none)

    Raises:
        ValidationError: If event not found
    """
    # Validate event exists
    event = session.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValidationError("Event not found")

    # Query recipe IDs
    result = (
        session.query(EventRecipe.recipe_id)
        .filter(EventRecipe.event_id == event_id)
        .all()
    )
    return [r[0] for r in result]
```

3. Add required imports at top of file if not present:
   - `from typing import List`
   - `from src.models.event_recipe import EventRecipe`

**Files**:
- `src/services/event_service.py` (modify)

**Validation**:
- [ ] Method returns empty list for event with no selections
- [ ] Method returns correct IDs for event with selections
- [ ] Method raises ValidationError for non-existent event

---

### Subtask T002 – Implement `set_event_recipes` Method

**Purpose**: Replace all recipe selections for an event with a new list (atomic operation).

**Steps**:
1. Open `src/services/event_service.py`
2. Add the following method:

```python
def set_event_recipes(
    session: Session,
    event_id: int,
    recipe_ids: List[int],
) -> int:
    """
    Replace all recipe selections for an event.

    Args:
        session: Database session
        event_id: Target event ID
        recipe_ids: List of recipe IDs to select (empty list clears all)

    Returns:
        Number of recipes now selected

    Raises:
        ValidationError: If event not found or recipe ID invalid
    """
    # Validate event exists
    event = session.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValidationError("Event not found")

    # Validate all recipe IDs exist (if any provided)
    if recipe_ids:
        from src.models.recipe import Recipe
        existing_ids = set(
            r[0] for r in session.query(Recipe.id)
            .filter(Recipe.id.in_(recipe_ids))
            .all()
        )
        invalid_ids = set(recipe_ids) - existing_ids
        if invalid_ids:
            raise ValidationError(f"Recipe {min(invalid_ids)} not found")

    # Delete existing selections
    session.query(EventRecipe).filter(
        EventRecipe.event_id == event_id
    ).delete()

    # Insert new selections
    for recipe_id in recipe_ids:
        session.add(EventRecipe(event_id=event_id, recipe_id=recipe_id))

    session.flush()
    return len(recipe_ids)
```

**Files**:
- `src/services/event_service.py` (modify)

**Notes**:
- Import Recipe inside method to avoid circular imports
- Use `session.flush()` to ensure changes are visible within transaction
- Delete-then-insert is simpler than diff-based and equally efficient for typical use

**Validation**:
- [ ] Empty list clears all selections
- [ ] New list replaces existing selections completely
- [ ] Returns correct count
- [ ] Raises ValidationError for non-existent event
- [ ] Raises ValidationError for invalid recipe ID

---

### Subtask T003 – Add Validation Logic

**Purpose**: Ensure robust error handling and input validation.

**Steps**:
1. Verify both methods validate event existence before any operation
2. Verify `set_event_recipes` validates all recipe IDs before making changes
3. Ensure error messages are consistent with existing patterns in event_service.py

**Validation Rules** (from data-model.md):
| Rule | Location | Error |
|------|----------|-------|
| Event must exist | Both methods | ValidationError("Event not found") |
| Recipe must exist | set_event_recipes | ValidationError("Recipe {id} not found") |

**Files**:
- `src/services/event_service.py` (verify within T001/T002 implementation)

**Notes**:
- Validation happens before any database modifications
- For invalid recipe IDs, report the first invalid ID found (consistent with existing patterns)

---

### Subtask T004 – Write Unit Tests [P]

**Purpose**: Achieve >70% coverage of new service methods.

**Steps**:
1. Create or modify `src/tests/test_recipe_selection.py`
2. Add test fixtures for events and recipes
3. Write tests for all scenarios

**Test Cases**:

```python
"""Tests for recipe selection service methods (F069)."""
import pytest
from src.services import event_service
from src.services.recipe_service import create_recipe
from src.utils.db import session_scope
from src.utils.error import ValidationError


class TestGetEventRecipeIds:
    """Tests for get_event_recipe_ids."""

    def test_returns_empty_list_when_no_selections(self, planning_event):
        """Event with no recipe selections returns empty list."""
        with session_scope() as session:
            result = event_service.get_event_recipe_ids(session, planning_event.id)
            assert result == []

    def test_returns_selected_recipe_ids(self, planning_event, test_recipes):
        """Returns IDs of selected recipes."""
        with session_scope() as session:
            # Select some recipes
            event_service.set_event_recipes(
                session, planning_event.id, [test_recipes[0].id, test_recipes[1].id]
            )
            session.commit()

        with session_scope() as session:
            result = event_service.get_event_recipe_ids(session, planning_event.id)
            assert set(result) == {test_recipes[0].id, test_recipes[1].id}

    def test_raises_for_nonexistent_event(self):
        """Raises ValidationError for non-existent event."""
        with session_scope() as session:
            with pytest.raises(ValidationError, match="Event not found"):
                event_service.get_event_recipe_ids(session, 99999)


class TestSetEventRecipes:
    """Tests for set_event_recipes."""

    def test_sets_recipe_selections(self, planning_event, test_recipes):
        """Sets recipe selections for an event."""
        with session_scope() as session:
            count = event_service.set_event_recipes(
                session, planning_event.id, [test_recipes[0].id]
            )
            session.commit()
            assert count == 1

        with session_scope() as session:
            result = event_service.get_event_recipe_ids(session, planning_event.id)
            assert result == [test_recipes[0].id]

    def test_replaces_existing_selections(self, planning_event, test_recipes):
        """Replaces all existing selections with new list."""
        with session_scope() as session:
            event_service.set_event_recipes(
                session, planning_event.id, [test_recipes[0].id]
            )
            session.commit()

        with session_scope() as session:
            event_service.set_event_recipes(
                session, planning_event.id, [test_recipes[1].id, test_recipes[2].id]
            )
            session.commit()

        with session_scope() as session:
            result = event_service.get_event_recipe_ids(session, planning_event.id)
            assert set(result) == {test_recipes[1].id, test_recipes[2].id}

    def test_empty_list_clears_selections(self, planning_event, test_recipes):
        """Empty list clears all selections."""
        with session_scope() as session:
            event_service.set_event_recipes(
                session, planning_event.id, [test_recipes[0].id]
            )
            session.commit()

        with session_scope() as session:
            count = event_service.set_event_recipes(session, planning_event.id, [])
            session.commit()
            assert count == 0

        with session_scope() as session:
            result = event_service.get_event_recipe_ids(session, planning_event.id)
            assert result == []

    def test_raises_for_nonexistent_event(self, test_recipes):
        """Raises ValidationError for non-existent event."""
        with session_scope() as session:
            with pytest.raises(ValidationError, match="Event not found"):
                event_service.set_event_recipes(session, 99999, [test_recipes[0].id])

    def test_raises_for_invalid_recipe_id(self, planning_event):
        """Raises ValidationError for invalid recipe ID."""
        with session_scope() as session:
            with pytest.raises(ValidationError, match="Recipe .* not found"):
                event_service.set_event_recipes(session, planning_event.id, [99999])

    def test_validates_all_recipes_before_modifying(self, planning_event, test_recipes):
        """Validates all recipe IDs before making any changes."""
        # First set some recipes
        with session_scope() as session:
            event_service.set_event_recipes(
                session, planning_event.id, [test_recipes[0].id]
            )
            session.commit()

        # Try to set with one invalid ID - should fail without changing anything
        with session_scope() as session:
            with pytest.raises(ValidationError):
                event_service.set_event_recipes(
                    session, planning_event.id, [test_recipes[1].id, 99999]
                )

        # Original selection should still be intact
        with session_scope() as session:
            result = event_service.get_event_recipe_ids(session, planning_event.id)
            assert result == [test_recipes[0].id]
```

4. Add fixtures to `conftest.py` if not present:

```python
@pytest.fixture
def planning_event(db_session):
    """Create a planning event for testing."""
    from src.services import event_service
    from datetime import date
    event = event_service.create_planning_event(
        db_session,
        name="Test Planning Event",
        event_date=date(2026, 6, 15),
    )
    db_session.commit()
    return event


@pytest.fixture
def test_recipes(db_session):
    """Create test recipes for selection testing."""
    from src.services.recipe_service import create_recipe
    recipes = []
    for i in range(3):
        recipe = create_recipe(
            session=db_session,
            name=f"Test Recipe {i+1}",
            instructions="Test instructions",
        )
        recipes.append(recipe)
    db_session.commit()
    return recipes
```

**Files**:
- `src/tests/test_recipe_selection.py` (create)
- `src/tests/conftest.py` (modify if fixtures needed)

**Run Tests**:
```bash
./run-tests.sh src/tests/test_recipe_selection.py -v
```

---

## Test Strategy

**Required Tests**:
- All test cases in T004 must pass
- Run full test suite to ensure no regressions

**Commands**:
```bash
# Run new tests
./run-tests.sh src/tests/test_recipe_selection.py -v

# Run with coverage
./run-tests.sh src/tests/test_recipe_selection.py -v --cov=src/services/event_service

# Run full suite
./run-tests.sh -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session detachment issues | Follow CLAUDE.md session guidelines; use single session per operation |
| Import ordering issues | Import Recipe inside method to avoid circular imports |
| Test isolation | Use proper fixtures with session scope |

---

## Definition of Done Checklist

- [ ] `get_event_recipe_ids` implemented and working
- [ ] `set_event_recipes` implemented and working
- [ ] Both methods validate inputs and raise appropriate errors
- [ ] Unit tests written and passing
- [ ] All existing tests continue to pass
- [ ] No linting or type errors

---

## Review Guidance

**Key checkpoints for reviewer**:
1. Verify method signatures match data-model.md exactly
2. Verify validation happens before any database changes
3. Verify error messages are consistent with existing patterns
4. Verify tests cover all scenarios from data-model.md
5. Run full test suite to check for regressions

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-01-26T22:57:43Z – system – lane=planned – Prompt generated via /spec-kitty.tasks

---

### Updating Lane Status

To change this work package's lane:
```bash
spec-kitty agent tasks move-task WP01 --to <lane> --note "message"
```

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
- 2026-01-26T23:02:49Z – claude-opus-4-5 – shell_pid=11706 – lane=doing – Started implementation via workflow command
- 2026-01-26T23:18:36Z – claude-opus-4-5 – shell_pid=11706 – lane=for_review – Ready for review: Service methods implemented with 11 passing tests
- 2026-01-26T23:20:46Z – claude-opus-4-5 – shell_pid=14143 – lane=doing – Started review via workflow command
