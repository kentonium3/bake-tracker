---
work_package_id: WP04
title: Planning Tab Integration + Notifications
lane: "doing"
dependencies:
- WP01
- WP03
base_branch: 070-finished-goods-filtering-WP03
base_commit: fee6e89e66ea265e4767035836373b0a4dd6ca0e
created_at: '2026-01-27T01:38:13.565166+00:00'
subtasks:
- T019
- T020
- T021
- T022
- T023
- T024
- T025
- T026
phase: Phase 2 - UI Layer
assignee: ''
agent: "claude"
shell_pid: "35025"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-26T19:45:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – Planning Tab Integration + Notifications

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

**Depends on WP03** – Use `--base` flag:

```bash
spec-kitty implement WP04 --base WP03 --agent codex
```

---

## Objectives & Success Criteria

**Objective**: Integrate `FGSelectionFrame` into Planning Tab, wire recipe selection changes to trigger FG list refresh, and show notifications when FGs are auto-removed.

**Success Criteria**:
- [ ] `FGSelectionFrame` embedded in Planning Tab below recipe selection
- [ ] Recipe selection save triggers FG list refresh
- [ ] FG selection save/cancel handled correctly
- [ ] Notification shown when FGs auto-removed
- [ ] All integration tests pass

---

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/070-finished-goods-filtering/spec.md` (FR-005, FR-006, FR-007)
- Plan: `kitty-specs/070-finished-goods-filtering/plan.md` (WP04 section)
- Constitution: `.kittify/memory/constitution.md` (Principle I: User-Centric Design)

**Pattern to Follow**: F069 recipe selection integration in `planning_tab.py`

**Dependencies**:
- WP01 + WP02: Service layer methods (complete)
- WP03: `FGSelectionFrame` component (complete)

**File Boundaries**:
- **Codex (this WP)**: `src/ui/planning_tab.py`, `src/tests/test_planning_tab_fg.py`
- Do NOT modify: `fg_selection_frame.py` (WP03/Gemini), `event_service.py` (WP01-02/Claude)

**BREAKING CHANGE**: `set_event_recipes()` now returns `Tuple[int, List[RemovedFGInfo]]` instead of `int`. Update callers.

---

## Subtasks & Detailed Guidance

### Subtask T019 – Add Imports and Instance Variables

**Purpose**: Set up imports and instance variables for FG selection.

**Steps**:
1. Open `src/ui/planning_tab.py`
2. Add imports at top:

```python
from typing import List, Optional
from src.ui.components.fg_selection_frame import FGSelectionFrame
from src.services.event_service import (
    get_available_finished_goods,
    RemovedFGInfo,
)
```

3. Add instance variables in `__init__()` after existing variables:

```python
# F070: FG selection state
self._fg_selection_frame: Optional[FGSelectionFrame] = None
self._selected_fg_ids: List[int] = []
self._original_fg_selection: List[int] = []
```

**Files**: `src/ui/planning_tab.py`
**Parallel?**: No (foundational)
**Notes**:
- `_selected_fg_ids` tracks current UI state
- `_original_fg_selection` tracks last-saved state (for cancel/revert)

---

### Subtask T020 – Create _create_fg_selection_frame() Method

**Purpose**: Factory method to create and configure the FG selection frame.

**Steps**:
1. Add method to `PlanningTab` class (after `_create_recipe_selection_frame()`):

```python
def _create_fg_selection_frame(self) -> FGSelectionFrame:
    """Create the FG selection frame component."""
    frame = FGSelectionFrame(
        self,
        on_save=self._on_fg_selection_save,
        on_cancel=self._on_fg_selection_cancel,
    )
    return frame
```

2. Call from `_create_widgets()` after recipe selection frame creation:

```python
# F070: Create FG selection frame
self._fg_selection_frame = self._create_fg_selection_frame()
# Note: Don't grid yet - shown when event selected
```

**Files**: `src/ui/planning_tab.py`
**Parallel?**: No (depends on T019)
**Notes**: Frame is created but not shown initially (hidden until event selected)

---

### Subtask T021 – Embed FGSelectionFrame in Grid Layout

**Purpose**: Position FG selection frame in the tab layout.

**Steps**:
1. Review current grid layout in `planning_tab.py`:
   - Row 0: Event list (treeview)
   - Row 1: Event form
   - Row 2: Recipe selection frame (F069)
   - Row 3: Status bar

2. Adjust layout to add FG selection:
   - Row 2: Recipe selection frame
   - Row 3: FG selection frame (NEW)
   - Row 4: Status bar (moved from row 3)

3. Update `_create_widgets()` grid configuration:

```python
# Adjust row weights
self.grid_rowconfigure(3, weight=0)  # FG selection frame
self.grid_rowconfigure(4, weight=0)  # Status bar (moved from row 3)
```

4. Update status bar grid position:

```python
# Move status bar to row 4
self._status_bar.grid(row=4, ...)  # Update from row 3
```

5. Add method to show/hide FG selection:

```python
def _show_fg_selection(self, event_id: int) -> None:
    """Show and populate FG selection for an event."""
    try:
        with session_scope() as session:
            event = event_service.get_event_by_id(event_id, session=session)
            event_name = event.name if event else ""
            available_fgs = get_available_finished_goods(event_id, session)
            # TODO: Get current FG selections for this event
            selected_fg_ids = []  # Implement in T022

        self._fg_selection_frame.populate_finished_goods(available_fgs, event_name)
        self._fg_selection_frame.set_selected(selected_fg_ids)
        self._original_fg_selection = selected_fg_ids.copy()

        self._fg_selection_frame.grid(
            row=3, column=0, sticky="ew",
            padx=PADDING_LARGE, pady=PADDING_MEDIUM
        )
    except Exception as e:
        self._update_status(f"Error loading finished goods: {e}", is_error=True)

def _hide_fg_selection(self) -> None:
    """Hide the FG selection frame."""
    self._fg_selection_frame.grid_remove()
    self._selected_fg_ids = []
    self._original_fg_selection = []
```

**Files**: `src/ui/planning_tab.py`
**Parallel?**: No (depends on T020)
**Notes**:
- FG selection appears below recipe selection
- Status bar moves down one row
- Frame hidden initially, shown when event selected

---

### Subtask T022 – Wire Recipe Selection Save to FG Refresh

**Purpose**: When recipe selection is saved, refresh the FG list to show newly available/unavailable FGs.

**Steps**:
1. Find `_on_recipe_selection_save()` method (from F069)
2. Update to handle the new return type from `set_event_recipes()`:

```python
def _on_recipe_selection_save(self, selected_ids: List[int]) -> None:
    """Handle recipe selection save."""
    if self._selected_event_id is None:
        self._update_status("No event selected", is_error=True)
        return

    try:
        with session_scope() as session:
            # F070: set_event_recipes now returns (count, removed_fgs)
            count, removed_fgs = event_service.set_event_recipes(
                session, self._selected_event_id, selected_ids
            )
            session.commit()

        self._original_selection = selected_ids.copy()
        self._update_status(f"Saved {count} recipe selection(s)")

        # F070: Refresh FG list after recipe change
        self._refresh_fg_selection()

        # F070: Show notification if FGs were auto-removed
        if removed_fgs:
            self._show_removed_fgs_notification(removed_fgs)

    except Exception as e:
        self._update_status(f"Error saving: {e}", is_error=True)
```

3. Add method to refresh FG selection:

```python
def _refresh_fg_selection(self) -> None:
    """Refresh FG selection list after recipe changes."""
    if self._selected_event_id is None:
        return

    try:
        with session_scope() as session:
            available_fgs = get_available_finished_goods(
                self._selected_event_id, session
            )
            event = event_service.get_event_by_id(
                self._selected_event_id, session=session
            )
            event_name = event.name if event else ""

        # Keep current selections that are still available
        available_ids = {fg.id for fg in available_fgs}
        still_selected = [
            fg_id for fg_id in self._selected_fg_ids
            if fg_id in available_ids
        ]

        self._fg_selection_frame.populate_finished_goods(available_fgs, event_name)
        self._fg_selection_frame.set_selected(still_selected)
        self._selected_fg_ids = still_selected
        self._original_fg_selection = still_selected.copy()

    except Exception as e:
        self._update_status(f"Error refreshing FG list: {e}", is_error=True)
```

**Files**: `src/ui/planning_tab.py`
**Parallel?**: No (depends on T021)
**Notes**:
- Must handle breaking change in `set_event_recipes()` return type
- Preserve valid FG selections after recipe change
- Chain: recipe save → cascade removal → FG refresh

---

### Subtask T023 – Implement _on_fg_selection_save() Callback

**Purpose**: Handle FG selection save button click.

**Steps**:
1. Add callback method:

```python
def _on_fg_selection_save(self, selected_fg_ids: List[int]) -> None:
    """Handle FG selection save."""
    if self._selected_event_id is None:
        self._update_status("No event selected", is_error=True)
        return

    try:
        with session_scope() as session:
            # Save FG selections to database
            count = event_service.set_event_finished_goods(
                session, self._selected_event_id, selected_fg_ids
            )
            session.commit()

        self._selected_fg_ids = selected_fg_ids.copy()
        self._original_fg_selection = selected_fg_ids.copy()
        self._update_status(f"Saved {count} finished good selection(s)")

    except Exception as e:
        self._update_status(f"Error saving FG selections: {e}", is_error=True)
```

**Note**: `set_event_finished_goods()` may not exist yet. If not, add to event_service.py:

```python
def set_event_finished_goods(
    session: Session,
    event_id: int,
    fg_ids: List[int],
) -> int:
    """
    Replace all FG selections for an event.

    Args:
        session: Database session
        event_id: Event to update
        fg_ids: New list of FG IDs to select

    Returns:
        Count of FGs selected
    """
    # Validate event exists
    event = session.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValidationError(["Event not found"])

    # Validate all FG IDs exist
    if fg_ids:
        existing_ids = set(
            fg[0] for fg in session.query(FinishedGood.id).filter(
                FinishedGood.id.in_(fg_ids)
            ).all()
        )
        invalid_ids = set(fg_ids) - existing_ids
        if invalid_ids:
            raise ValidationError([f"FinishedGood {min(invalid_ids)} not found"])

    # Delete existing selections
    session.query(EventFinishedGood).filter(
        EventFinishedGood.event_id == event_id
    ).delete()

    # Insert new selections
    for fg_id in fg_ids:
        session.add(EventFinishedGood(
            event_id=event_id,
            finished_good_id=fg_id,
            quantity=1,  # Default quantity, F071 will handle specific quantities
        ))

    session.flush()
    return len(fg_ids)
```

**Files**: `src/ui/planning_tab.py`, `src/services/event_service.py` (if needed)
**Parallel?**: No (depends on T022)
**Notes**:
- Follows same pattern as `_on_recipe_selection_save()`
- Default quantity=1 for now (F071 will add quantity UI)

---

### Subtask T024 – Implement _on_fg_selection_cancel() Callback

**Purpose**: Handle FG selection cancel button click.

**Steps**:
1. Add callback method:

```python
def _on_fg_selection_cancel(self) -> None:
    """Handle FG selection cancel - revert to saved state."""
    self._fg_selection_frame.set_selected(self._original_fg_selection)
    self._selected_fg_ids = self._original_fg_selection.copy()
    self._update_status("Reverted to saved FG selections")
```

**Files**: `src/ui/planning_tab.py`
**Parallel?**: No (depends on T023)
**Notes**: Simply restores `_original_fg_selection` state

---

### Subtask T025 – Show Notification for Auto-Removed FGs

**Purpose**: Display user notification when FGs are automatically removed due to recipe deselection.

**Steps**:
1. Add notification method:

```python
def _show_removed_fgs_notification(self, removed_fgs: List[RemovedFGInfo]) -> None:
    """Show notification about automatically removed FG selections."""
    if not removed_fgs:
        return

    # Build message
    if len(removed_fgs) == 1:
        fg = removed_fgs[0]
        missing = ", ".join(fg.missing_recipes[:3])
        if len(fg.missing_recipes) > 3:
            missing += f" (+{len(fg.missing_recipes) - 3} more)"
        msg = f"Removed '{fg.fg_name}' - missing recipe(s): {missing}"
    else:
        fg_names = ", ".join(fg.fg_name for fg in removed_fgs[:3])
        if len(removed_fgs) > 3:
            fg_names += f" (+{len(removed_fgs) - 3} more)"
        msg = f"Removed {len(removed_fgs)} finished goods: {fg_names}"

    self._update_status(msg, is_error=False)
```

**Files**: `src/ui/planning_tab.py`
**Parallel?**: No (depends on T022)
**Notes**:
- Uses existing `_update_status()` for display
- Truncates long lists for readability
- Not an error (informational)

---

### Subtask T026 – Write Integration Tests

**Purpose**: Tests for Planning Tab FG integration.

**Steps**:
1. Create `src/tests/test_planning_tab_fg.py`:

```python
"""
Integration tests for Planning Tab FG selection (F070).
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import date


class TestPlanningTabFGIntegration:
    """Integration tests for FG selection in Planning Tab."""

    def test_fg_frame_created(self, test_db, planning_tab):
        """Planning Tab creates FG selection frame."""
        assert planning_tab._fg_selection_frame is not None

    def test_fg_frame_hidden_initially(self, planning_tab):
        """FG selection frame is hidden until event selected."""
        # Check that frame is not visible (grid_info empty)
        assert not planning_tab._fg_selection_frame.winfo_ismapped()

    def test_fg_frame_shown_on_event_select(
        self, test_db, planning_tab, planning_event
    ):
        """FG selection frame appears when event is selected."""
        planning_tab._selected_event_id = planning_event.id
        planning_tab._show_fg_selection(planning_event.id)

        # Frame should be visible
        assert planning_tab._fg_selection_frame.winfo_ismapped()

    def test_recipe_save_refreshes_fg_list(
        self, test_db, planning_tab, planning_event, test_recipes
    ):
        """Saving recipe selection refreshes available FG list."""
        planning_tab._selected_event_id = planning_event.id
        planning_tab._show_fg_selection(planning_event.id)

        # Mock the refresh method to verify it's called
        with patch.object(planning_tab, '_refresh_fg_selection') as mock_refresh:
            planning_tab._on_recipe_selection_save([test_recipes[0].id])
            mock_refresh.assert_called_once()

    def test_removed_fgs_notification_shown(
        self, test_db, planning_tab, planning_event
    ):
        """Notification shown when FGs auto-removed."""
        planning_tab._selected_event_id = planning_event.id

        removed = [
            MagicMock(fg_id=1, fg_name="Test FG", missing_recipes=["Recipe A"])
        ]

        with patch.object(planning_tab, '_update_status') as mock_status:
            planning_tab._show_removed_fgs_notification(removed)
            mock_status.assert_called_once()
            call_args = mock_status.call_args[0][0]
            assert "Test FG" in call_args


class TestFGSelectionCallbacks:
    """Tests for FG selection callbacks."""

    def test_save_persists_selections(
        self, test_db, planning_tab, planning_event
    ):
        """FG save callback persists selections to database."""
        planning_tab._selected_event_id = planning_event.id

        # This would need actual FGs - simplified test
        planning_tab._on_fg_selection_save([])

        assert planning_tab._selected_fg_ids == []
        assert planning_tab._original_fg_selection == []

    def test_cancel_reverts_to_original(
        self, test_db, planning_tab, planning_event
    ):
        """FG cancel callback reverts to saved state."""
        planning_tab._selected_event_id = planning_event.id
        planning_tab._original_fg_selection = [1, 2, 3]
        planning_tab._selected_fg_ids = [1, 2, 3, 4]  # User added one

        with patch.object(planning_tab._fg_selection_frame, 'set_selected'):
            planning_tab._on_fg_selection_cancel()

        assert planning_tab._selected_fg_ids == [1, 2, 3]


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def planning_tab(mock_ctk_root):
    """Create Planning Tab for testing."""
    with patch("src.ui.planning_tab.session_scope"):
        from src.ui.planning_tab import PlanningTab
        tab = PlanningTab(mock_ctk_root)
        return tab


@pytest.fixture
def mock_ctk_root():
    """Create mock CTk root."""
    root = MagicMock()
    return root


@pytest.fixture
def planning_event(test_db):
    """Create a planning event."""
    from src.services import event_service
    event = event_service.create_planning_event(
        test_db,
        name="Test Event",
        event_date=date(2026, 6, 15),
    )
    test_db.commit()
    return event


@pytest.fixture
def test_recipes(test_db):
    """Create test recipes."""
    from src.models.recipe import Recipe
    recipes = []
    for i in range(3):
        recipe = Recipe(name=f"Recipe {i+1}", category="Test")
        test_db.add(recipe)
        recipes.append(recipe)
    test_db.flush()
    return recipes
```

**Files**: `src/tests/test_planning_tab_fg.py` (NEW)
**Parallel?**: Yes (can write alongside implementation)
**Notes**:
- Uses mocking for UI tests
- Integration tests verify wiring, not visual appearance
- Reuses fixtures where possible

---

## Test Strategy

**Run tests**:
```bash
./run-tests.sh src/tests/test_planning_tab_fg.py -v
```

**Expected results**: ~8 tests pass

**Manual validation**:
1. Launch app, go to Planning Tab
2. Create/select an event
3. Select recipes → verify FG list appears
4. Check FGs → verify count updates
5. Save FGs → verify persisted
6. Deselect a recipe → verify notification if FGs removed
7. Cancel → verify selections revert

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Grid layout conflicts with F069 | Carefully adjust row indices (2→3→4) |
| Breaking change in set_event_recipes() | Update to handle Tuple return type |
| set_event_finished_goods() missing | Add to event_service.py if needed |
| Race conditions on rapid toggles | Service layer is stateless; debounce if needed |

---

## Definition of Done Checklist

- [ ] T019: Imports and instance variables added
- [ ] T020: `_create_fg_selection_frame()` implemented
- [ ] T021: FG frame embedded in grid layout
- [ ] T022: Recipe save triggers FG refresh
- [ ] T023: `_on_fg_selection_save()` implemented
- [ ] T024: `_on_fg_selection_cancel()` implemented
- [ ] T025: Auto-removal notification shown
- [ ] T026: All integration tests pass
- [ ] Grid layout works (recipe → FG → status bar)
- [ ] No regressions in F069 recipe selection

---

## Review Guidance

**Key acceptance checkpoints**:
1. Verify grid layout: row 2 (recipe) → row 3 (FG) → row 4 (status bar)
2. Verify `set_event_recipes()` return type handled correctly
3. Verify FG refresh happens AFTER recipe save
4. Verify notification is user-friendly (truncated, informative)
5. Run full test suite: `./run-tests.sh src/tests/ -v`

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

**Initial entry**:
- 2026-01-26T19:45:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2026-01-27T01:48:48Z – unknown – shell_pid=32702 – lane=for_review – Ready for review: Integrated FGSelectionFrame into Planning Tab with recipe-FG wiring and notifications. All 59 tests pass (45 F070 + 14 F069).
- 2026-01-27T01:49:54Z – claude – shell_pid=35025 – lane=doing – Started review via workflow command
