---
work_package_id: WP02
title: Availability Checking + Cascade Removal
lane: "doing"
dependencies: [WP01]
base_branch: 070-finished-goods-filtering-WP01
base_commit: 95b1d964956e408331a6b3c63d533cf0c63fbe3e
created_at: '2026-01-27T01:21:03.541955+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
- T012
phase: Phase 1 - Service Layer
assignee: ''
agent: "claude"
shell_pid: "30418"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-26T19:45:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Availability Checking + Cascade Removal

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

**Depends on WP01** – Use `--base` flag:

```bash
spec-kitty implement WP02 --base WP01 --agent claude
```

---

## Objectives & Success Criteria

**Objective**: Implement FG availability checking and automatic removal of invalid FG selections when recipes are deselected.

**Success Criteria**:
- [ ] `check_fg_availability()` correctly identifies available/unavailable FGs
- [ ] `get_available_finished_goods()` returns only FGs whose recipes are all selected
- [ ] `remove_invalid_fg_selections()` removes FGs that are no longer available
- [ ] `set_event_recipes()` automatically triggers cascade removal
- [ ] All unit tests pass (availability + cascade removal)
- [ ] No session detachment issues

---

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/070-finished-goods-filtering/spec.md` (FR-001, FR-003, FR-004, FR-006, FR-007)
- Data Model: `kitty-specs/070-finished-goods-filtering/data-model.md` (Availability Check Flow, Cascade Removal Flow)
- Research: `kitty-specs/070-finished-goods-filtering/research.md` (Cascade Removal section)
- Constitution: `.kittify/memory/constitution.md` (Principle II: Data Integrity)

**Dependencies**:
- WP01: `get_required_recipes()` function (must be complete)

**Session Management**: All service methods MUST accept `session` parameter. Follow F069 pattern in existing `event_service.py` methods.

---

## Subtasks & Detailed Guidance

### Subtask T006 – Create DTO Dataclasses

**Purpose**: Define data transfer objects for availability results and removed FG info.

**Steps**:
1. Add to `src/services/event_service.py` after exception classes:

```python
from dataclasses import dataclass
from typing import Set, List


@dataclass
class AvailabilityResult:
    """Result of checking FG availability against selected recipes."""
    fg_id: int
    fg_name: str
    is_available: bool
    required_recipe_ids: Set[int]
    missing_recipe_ids: Set[int]


@dataclass
class RemovedFGInfo:
    """Info about an FG that was auto-removed due to recipe deselection."""
    fg_id: int
    fg_name: str
    missing_recipes: List[str]  # Recipe names for user notification
```

**Files**: `src/services/event_service.py`
**Parallel?**: No (foundational for T007-T009)
**Notes**: `RemovedFGInfo.missing_recipes` contains recipe names (not IDs) for human-readable notifications.

---

### Subtask T007 – Implement check_fg_availability()

**Purpose**: Check if a single FG is available given the selected recipe IDs.

**Steps**:
1. Add function to `src/services/event_service.py`:

```python
def check_fg_availability(
    fg_id: int,
    selected_recipe_ids: Set[int],
    session: Session,
) -> AvailabilityResult:
    """
    Check if a FinishedGood is available given selected recipes.

    Args:
        fg_id: The FinishedGood ID to check
        selected_recipe_ids: Set of recipe IDs currently selected for the event
        session: Database session

    Returns:
        AvailabilityResult with availability status and missing recipe details

    Raises:
        ValidationError: If fg_id not found
    """
    # Get FG for name (for result)
    fg = session.query(FinishedGood).filter(FinishedGood.id == fg_id).first()
    if fg is None:
        raise ValidationError([f"FinishedGood {fg_id} not found"])

    # Decompose to required recipes
    try:
        required = get_required_recipes(fg_id, session)
    except (CircularReferenceError, MaxDepthExceededError):
        # Treat problematic FGs as unavailable
        return AvailabilityResult(
            fg_id=fg_id,
            fg_name=fg.display_name,
            is_available=False,
            required_recipe_ids=set(),
            missing_recipe_ids=set(),
        )

    # Calculate missing recipes
    missing = required - selected_recipe_ids

    return AvailabilityResult(
        fg_id=fg_id,
        fg_name=fg.display_name,
        is_available=len(missing) == 0,
        required_recipe_ids=required,
        missing_recipe_ids=missing,
    )
```

**Files**: `src/services/event_service.py`
**Parallel?**: No (depends on T006)
**Notes**:
- Uses `get_required_recipes()` from WP01
- Circular/depth errors treated as "unavailable" (not raised)
- Empty `selected_recipe_ids` → all FGs with recipes are unavailable

---

### Subtask T008 – Implement get_available_finished_goods()

**Purpose**: Get all FGs that are available for an event based on its selected recipes.

**Steps**:
1. Add function to `src/services/event_service.py`:

```python
def get_available_finished_goods(
    event_id: int,
    session: Session,
) -> List[FinishedGood]:
    """
    Get all FinishedGoods that are available for an event.

    A FG is available if all its required recipes are selected for the event.

    Args:
        event_id: The event to check availability for
        session: Database session

    Returns:
        List of FinishedGood objects that are available

    Raises:
        ValidationError: If event_id not found
    """
    # Validate event exists
    event = session.query(Event).filter(Event.id == event_id).first()
    if event is None:
        raise ValidationError([f"Event {event_id} not found"])

    # Get selected recipe IDs for this event
    selected_recipe_ids = set(get_event_recipe_ids(session, event_id))

    # If no recipes selected, no FGs are available
    if not selected_recipe_ids:
        return []

    # Get all FGs
    all_fgs = session.query(FinishedGood).all()

    # Filter to available FGs
    available_fgs = []
    for fg in all_fgs:
        result = check_fg_availability(fg.id, selected_recipe_ids, session)
        if result.is_available:
            available_fgs.append(fg)

    return available_fgs
```

**Files**: `src/services/event_service.py`
**Parallel?**: No (depends on T007)
**Notes**:
- Uses `get_event_recipe_ids()` from F069
- Uses `check_fg_availability()` from T007
- Returns full FG objects (needed for UI display)

---

### Subtask T009 – Implement remove_invalid_fg_selections()

**Purpose**: Remove FG selections that are no longer valid after recipe deselection.

**Steps**:
1. Add imports at top of file:
```python
from src.models.event_finished_good import EventFinishedGood
from src.models.recipe import Recipe
```

2. Add function to `src/services/event_service.py`:

```python
def remove_invalid_fg_selections(
    event_id: int,
    session: Session,
) -> List[RemovedFGInfo]:
    """
    Remove FG selections that are no longer valid for an event.

    Called after recipe selection changes to maintain data integrity.

    Args:
        event_id: The event to clean up
        session: Database session

    Returns:
        List of RemovedFGInfo for FGs that were removed (for notification)

    Raises:
        ValidationError: If event_id not found
    """
    # Validate event exists
    event = session.query(Event).filter(Event.id == event_id).first()
    if event is None:
        raise ValidationError([f"Event {event_id} not found"])

    # Get current selected recipe IDs
    selected_recipe_ids = set(get_event_recipe_ids(session, event_id))

    # Get current FG selections for this event
    current_fg_selections = (
        session.query(EventFinishedGood)
        .filter(EventFinishedGood.event_id == event_id)
        .all()
    )

    removed_fgs: List[RemovedFGInfo] = []

    for efg in current_fg_selections:
        result = check_fg_availability(efg.finished_good_id, selected_recipe_ids, session)

        if not result.is_available:
            # Get recipe names for notification
            missing_recipe_names = []
            if result.missing_recipe_ids:
                recipes = (
                    session.query(Recipe)
                    .filter(Recipe.id.in_(result.missing_recipe_ids))
                    .all()
                )
                missing_recipe_names = [r.name for r in recipes]

            removed_fgs.append(
                RemovedFGInfo(
                    fg_id=result.fg_id,
                    fg_name=result.fg_name,
                    missing_recipes=missing_recipe_names,
                )
            )

            # Delete the selection
            session.delete(efg)

    # Flush to persist deletions
    session.flush()

    return removed_fgs
```

**Files**: `src/services/event_service.py`
**Parallel?**: No (depends on T007)
**Notes**:
- Returns `RemovedFGInfo` list for UI notification
- `missing_recipes` contains human-readable recipe names
- Uses `session.delete()` then `session.flush()` (caller commits)

---

### Subtask T010 – Modify set_event_recipes() for Cascade Removal

**Purpose**: Automatically remove invalid FG selections when recipes are changed.

**Steps**:
1. Find existing `set_event_recipes()` in `src/services/event_service.py` (~line 2725)
2. Add cascade removal call after updating recipes:

```python
def set_event_recipes(
    session: Session,
    event_id: int,
    recipe_ids: List[int],
) -> Tuple[int, List[RemovedFGInfo]]:
    """
    Replace all recipe selections for an event.

    MODIFIED for F070: Now also removes invalid FG selections and returns
    info about removed FGs for notification.

    Args:
        session: Database session
        event_id: Event to update
        recipe_ids: New list of recipe IDs to select

    Returns:
        Tuple of (count of recipes set, list of removed FG info)

    Raises:
        ValidationError: If event or any recipe not found
    """
    # ... existing validation code ...

    # Validate event exists
    event = session.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValidationError(["Event not found"])

    # Validate all recipe IDs exist
    if recipe_ids:
        existing_ids = set(
            r[0] for r in session.query(Recipe.id).filter(Recipe.id.in_(recipe_ids)).all()
        )
        invalid_ids = set(recipe_ids) - existing_ids
        if invalid_ids:
            raise ValidationError([f"Recipe {min(invalid_ids)} not found"])

    # Delete existing selections
    session.query(EventRecipe).filter(EventRecipe.event_id == event_id).delete()

    # Insert new selections
    for recipe_id in recipe_ids:
        session.add(EventRecipe(event_id=event_id, recipe_id=recipe_id))

    session.flush()

    # F070: Remove invalid FG selections after recipe change
    removed_fgs = remove_invalid_fg_selections(event_id, session)

    return len(recipe_ids), removed_fgs
```

**Files**: `src/services/event_service.py`
**Parallel?**: No (modifies existing function)
**Notes**:
- **BREAKING CHANGE**: Return type changes from `int` to `Tuple[int, List[RemovedFGInfo]]`
- Update callers in `planning_tab.py` (WP04 handles this)
- Cascade removal happens AFTER recipe update, BEFORE commit

---

### Subtask T011 – Write Availability Checking Tests

**Purpose**: Tests for `check_fg_availability()` and `get_available_finished_goods()`.

**Steps**:
1. Add to `src/tests/test_fg_availability.py`:

```python
class TestCheckFgAvailability:
    """Tests for check_fg_availability."""

    def test_available_when_all_recipes_selected(
        self, test_db, atomic_fg_with_recipe
    ):
        """FG is available when its recipe is in selected set."""
        selected = {atomic_fg_with_recipe.expected_recipe_id}
        result = check_fg_availability(atomic_fg_with_recipe.id, selected, test_db)

        assert result.is_available is True
        assert result.missing_recipe_ids == set()

    def test_unavailable_when_recipe_missing(
        self, test_db, atomic_fg_with_recipe
    ):
        """FG is unavailable when its recipe is not selected."""
        selected = set()  # No recipes selected
        result = check_fg_availability(atomic_fg_with_recipe.id, selected, test_db)

        assert result.is_available is False
        assert atomic_fg_with_recipe.expected_recipe_id in result.missing_recipe_ids

    def test_bundle_available_when_all_component_recipes_selected(
        self, test_db, simple_bundle
    ):
        """Bundle is available when all component recipes selected."""
        result = check_fg_availability(
            simple_bundle.id,
            simple_bundle.expected_recipe_ids,
            test_db
        )

        assert result.is_available is True
        assert result.missing_recipe_ids == set()

    def test_bundle_unavailable_when_partial_recipes_selected(
        self, test_db, simple_bundle
    ):
        """Bundle is unavailable when only some recipes selected."""
        partial = set(list(simple_bundle.expected_recipe_ids)[:1])
        result = check_fg_availability(simple_bundle.id, partial, test_db)

        assert result.is_available is False
        assert len(result.missing_recipe_ids) > 0

    def test_raises_for_nonexistent_fg(self, test_db):
        """Raises ValidationError for non-existent FG."""
        with pytest.raises(ValidationError):
            check_fg_availability(99999, set(), test_db)


class TestGetAvailableFinishedGoods:
    """Tests for get_available_finished_goods."""

    def test_returns_empty_when_no_recipes_selected(
        self, test_db, planning_event, atomic_fg_with_recipe
    ):
        """No FGs available when no recipes selected."""
        result = get_available_finished_goods(planning_event.id, test_db)
        assert result == []

    def test_returns_fgs_with_selected_recipes(
        self, test_db, planning_event, atomic_fg_with_recipe
    ):
        """Returns FGs whose recipes are all selected."""
        # Select the recipe
        set_event_recipes(
            test_db,
            planning_event.id,
            [atomic_fg_with_recipe.expected_recipe_id],
        )
        test_db.flush()

        result = get_available_finished_goods(planning_event.id, test_db)
        fg_ids = [fg.id for fg in result]
        assert atomic_fg_with_recipe.id in fg_ids

    def test_raises_for_nonexistent_event(self, test_db):
        """Raises ValidationError for non-existent event."""
        with pytest.raises(ValidationError, match="Event .* not found"):
            get_available_finished_goods(99999, test_db)
```

**Files**: `src/tests/test_fg_availability.py`
**Parallel?**: Yes (can write alongside T012)
**Notes**: Uses fixtures from WP01 (T005)

---

### Subtask T012 – Write Cascade Removal Tests

**Purpose**: Tests for `remove_invalid_fg_selections()` and modified `set_event_recipes()`.

**Steps**:
1. Add to `src/tests/test_fg_availability.py`:

```python
class TestRemoveInvalidFgSelections:
    """Tests for remove_invalid_fg_selections."""

    def test_removes_fg_when_recipe_deselected(
        self, test_db, planning_event, atomic_fg_with_recipe
    ):
        """Removes FG selection when its recipe is deselected."""
        # Setup: select recipe and FG
        set_event_recipes(
            test_db,
            planning_event.id,
            [atomic_fg_with_recipe.expected_recipe_id],
        )
        # Add FG selection
        efg = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=atomic_fg_with_recipe.id,
            quantity=1,
        )
        test_db.add(efg)
        test_db.flush()

        # Deselect recipe (set empty list)
        set_event_recipes(test_db, planning_event.id, [])
        test_db.flush()

        # Verify FG selection was removed
        remaining = (
            test_db.query(EventFinishedGood)
            .filter(EventFinishedGood.event_id == planning_event.id)
            .all()
        )
        assert len(remaining) == 0

    def test_returns_removed_fg_info(
        self, test_db, planning_event, atomic_fg_with_recipe
    ):
        """Returns info about removed FGs for notification."""
        # Setup: select recipe and FG
        set_event_recipes(
            test_db,
            planning_event.id,
            [atomic_fg_with_recipe.expected_recipe_id],
        )
        efg = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=atomic_fg_with_recipe.id,
            quantity=1,
        )
        test_db.add(efg)
        test_db.flush()

        # Deselect recipe
        count, removed = set_event_recipes(test_db, planning_event.id, [])

        assert count == 0
        assert len(removed) == 1
        assert removed[0].fg_id == atomic_fg_with_recipe.id

    def test_keeps_fg_when_recipe_still_selected(
        self, test_db, planning_event, atomic_fg_with_recipe, test_recipes
    ):
        """Keeps FG selection when its recipe remains selected."""
        # Setup: select recipe and FG
        set_event_recipes(
            test_db,
            planning_event.id,
            [atomic_fg_with_recipe.expected_recipe_id],
        )
        efg = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=atomic_fg_with_recipe.id,
            quantity=1,
        )
        test_db.add(efg)
        test_db.flush()

        # Add another recipe but keep original
        set_event_recipes(
            test_db,
            planning_event.id,
            [atomic_fg_with_recipe.expected_recipe_id, test_recipes[1].id],
        )
        test_db.flush()

        # Verify FG selection still exists
        remaining = (
            test_db.query(EventFinishedGood)
            .filter(EventFinishedGood.event_id == planning_event.id)
            .all()
        )
        assert len(remaining) == 1


class TestSetEventRecipesWithCascade:
    """Tests for modified set_event_recipes with cascade removal."""

    def test_returns_tuple_with_removed_fgs(
        self, test_db, planning_event, test_recipes
    ):
        """Returns tuple of (count, removed_fgs)."""
        count, removed = set_event_recipes(
            test_db,
            planning_event.id,
            [test_recipes[0].id],
        )

        assert count == 1
        assert isinstance(removed, list)

    def test_cascade_happens_atomically(
        self, test_db, planning_event, atomic_fg_with_recipe
    ):
        """Recipe update and cascade removal happen in same transaction."""
        # Setup
        set_event_recipes(
            test_db,
            planning_event.id,
            [atomic_fg_with_recipe.expected_recipe_id],
        )
        efg = EventFinishedGood(
            event_id=planning_event.id,
            finished_good_id=atomic_fg_with_recipe.id,
            quantity=1,
        )
        test_db.add(efg)
        test_db.commit()

        # Deselect recipe
        set_event_recipes(test_db, planning_event.id, [])
        # Don't commit yet

        # Rollback
        test_db.rollback()

        # Both recipe and FG selection should be restored
        recipes = get_event_recipe_ids(test_db, planning_event.id)
        fgs = (
            test_db.query(EventFinishedGood)
            .filter(EventFinishedGood.event_id == planning_event.id)
            .all()
        )
        assert len(recipes) == 1
        assert len(fgs) == 1
```

**Files**: `src/tests/test_fg_availability.py`
**Parallel?**: Yes (can write alongside T011)
**Notes**:
- Add import: `from src.models.event_finished_good import EventFinishedGood`
- Uses `planning_event` fixture from F069 tests

---

## Test Strategy

**Run tests**:
```bash
./run-tests.sh src/tests/test_fg_availability.py -v
```

**Expected results**: ~20 tests pass (8 from WP01 + 12 from WP02)

**Critical test scenarios**:
- Availability with full/partial/no recipe selection
- Cascade removal on recipe deselect
- Transaction atomicity (rollback restores both)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking change in set_event_recipes() | Update callers in WP04 |
| Performance on large FG catalogs | Defer optimization; profile if slow |
| Session detachment | All methods accept session parameter |

---

## Definition of Done Checklist

- [ ] T006: DTO dataclasses created
- [ ] T007: `check_fg_availability()` implemented
- [ ] T008: `get_available_finished_goods()` implemented
- [ ] T009: `remove_invalid_fg_selections()` implemented
- [ ] T010: `set_event_recipes()` modified with cascade
- [ ] T011: Availability tests pass
- [ ] T012: Cascade removal tests pass
- [ ] All ~20 tests pass
- [ ] No session management issues

---

## Review Guidance

**Key acceptance checkpoints**:
1. Verify `set_event_recipes()` return type change is documented
2. Verify cascade removal happens AFTER recipe update in same transaction
3. Verify `RemovedFGInfo.missing_recipes` contains names (not IDs)
4. Run full test suite to ensure no regressions in F069
5. Check that `get_event_recipe_ids()` still works (F069 compatibility)

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

**Initial entry**:
- 2026-01-26T19:45:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2026-01-27T01:24:41Z – unknown – shell_pid=29057 – lane=for_review – Ready for review: FG availability checking, cascade removal, and modified set_event_recipes() with 21 passing tests
- 2026-01-27T01:25:29Z – claude – shell_pid=30418 – lane=doing – Started review via workflow command
