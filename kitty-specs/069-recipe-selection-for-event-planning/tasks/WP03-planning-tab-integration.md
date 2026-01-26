---
work_package_id: WP03
title: Planning Tab Integration
lane: "doing"
dependencies: [WP01, WP02]
base_branch: 069-recipe-selection-for-event-planning-WP02
base_commit: 49d3dc12c87a5b392c48f27e69bda3334cc50258
created_at: '2026-01-26T23:32:36.811462+00:00'
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
phase: Phase 3 - Integration
assignee: ''
agent: "claude-opus-4-5"
shell_pid: "18836"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-26T22:57:43Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Planning Tab Integration

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

This WP depends on WP01 and WP02. Branch from WP02 (which includes WP01):

```bash
spec-kitty implement WP03 --base WP02
```

---

## Objectives & Success Criteria

**Goal**: Embed `RecipeSelectionFrame` in `PlanningTab` with full event lifecycle integration - show/hide on event selection, load existing selections, save changes.

**Success Criteria**:
- Recipe selection frame appears below event table when event is selected
- Frame is hidden when no event is selected
- Existing selections load automatically when event is selected (FR-009)
- Save button persists selections via service method (FR-008)
- Cancel button reverts to last saved state
- Full workflow: select event → check recipes → save → close/reopen → selections persist (US-005)

**Acceptance from spec.md**:
- FR-008: System MUST persist recipe selections to the event_recipes table
- FR-009: System MUST load and pre-check existing selections when an event is opened
- FR-010: System MUST replace (not append) selections when saving
- US-005: Returning user sees prior selections pre-checked

## Context & Constraints

**Reference Documents**:
- `kitty-specs/069-recipe-selection-for-event-planning/research.md` - RQ-005 (layout), RQ-008 (session management)
- `kitty-specs/069-recipe-selection-for-event-planning/plan.md` - Embedded UI decision
- `src/ui/planning_tab.py` - Existing PlanningTab implementation

**Key Constraints**:
- Follow session_scope() patterns from CLAUDE.md
- Frame embedded in PlanningTab (not modal dialog per AD-001)
- Must integrate with existing event selection mechanism

**Layout from research.md**:
```
PlanningTab
├─ Row 0: Action buttons (Create, Edit, Delete, Refresh)
├─ Row 1: PlanningEventDataTable (events list)
├─ Row 2: RecipeSelectionFrame (NEW - shown when event selected)
│   ├─ Header: "Recipe Selection for [Event Name]"
│   ├─ Counter: "X of Y recipes selected"
│   ├─ Scrollable checkbox list
│   └─ Save/Cancel buttons
└─ Row 3: Status bar (if exists)
```

---

## Subtasks & Detailed Guidance

### Subtask T011 – Embed `RecipeSelectionFrame` in `PlanningTab` Layout

**Purpose**: Add the recipe selection frame to the PlanningTab UI.

**Steps**:
1. Open `src/ui/planning_tab.py`
2. Add import at top:

```python
from src.ui.components.recipe_selection_frame import RecipeSelectionFrame
```

3. In `__init__` or `_setup_ui` method, create the frame (initially hidden):

```python
# Recipe selection frame (below event table)
self._recipe_selection_frame = RecipeSelectionFrame(
    self,
    on_save=self._on_recipe_selection_save,
    on_cancel=self._on_recipe_selection_cancel,
)
# Don't pack yet - will be shown when event is selected
```

4. Ensure frame can be packed in Row 2 position (adjust existing layout if needed)

**Files**:
- `src/ui/planning_tab.py` (modify)

**Notes**:
- Frame starts hidden (`pack_forget()` or not packed initially)
- Will be packed/unpacked based on event selection

---

### Subtask T012 – Wire Event Selection Callback

**Purpose**: Show recipe selection frame when an event is selected, hide when deselected.

**Steps**:
1. Find the event selection callback in PlanningTab (likely `_on_event_selected` or similar)
2. Modify to show/populate recipe selection frame:

```python
def _on_event_selected(self, event_id: Optional[int]) -> None:
    """Handle event selection from the table."""
    self._selected_event_id = event_id

    if event_id is None:
        # No event selected - hide recipe selection
        self._hide_recipe_selection()
        return

    # Event selected - show and populate recipe selection
    self._show_recipe_selection(event_id)
```

3. Add helper methods:

```python
def _show_recipe_selection(self, event_id: int) -> None:
    """Show and populate recipe selection for an event."""
    from src.services import recipe_service, event_service
    from src.utils.db import session_scope

    with session_scope() as session:
        # Get event name
        event = event_service.get_planning_event(session, event_id)
        event_name = event.name if event else ""

        # Get all recipes for selection
        recipes = recipe_service.get_all_recipes(include_archived=False)

        # Get existing selections
        selected_ids = event_service.get_event_recipe_ids(session, event_id)

    # Populate frame
    self._recipe_selection_frame.populate_recipes(recipes, event_name)
    self._recipe_selection_frame.set_selected(selected_ids)

    # Store for cancel functionality
    self._original_selection = selected_ids.copy()

    # Show frame
    self._recipe_selection_frame.pack(fill="x", padx=10, pady=10)

def _hide_recipe_selection(self) -> None:
    """Hide the recipe selection frame."""
    self._recipe_selection_frame.pack_forget()
```

4. Add instance variable to track original selection:

```python
# In __init__
self._selected_event_id: Optional[int] = None
self._original_selection: List[int] = []
```

**Files**:
- `src/ui/planning_tab.py` (modify)

**Notes**:
- Store `_original_selection` to support Cancel functionality
- Use single `session_scope()` for all queries (event, recipes, selections)

---

### Subtask T013 – Implement Save Button Handler

**Purpose**: Persist recipe selections when user clicks Save.

**Steps**:
1. Add the save handler method:

```python
def _on_recipe_selection_save(self, selected_ids: List[int]) -> None:
    """Handle recipe selection save."""
    if self._selected_event_id is None:
        return

    from src.services import event_service
    from src.utils.db import session_scope

    try:
        with session_scope() as session:
            count = event_service.set_event_recipes(
                session,
                self._selected_event_id,
                selected_ids,
            )
            session.commit()

        # Update original selection (for future cancel)
        self._original_selection = selected_ids.copy()

        # Show success feedback
        self._show_status_message(f"Saved {count} recipe selections")

    except Exception as e:
        # Show error but keep UI state
        self._show_status_message(f"Error saving: {str(e)}", error=True)
```

2. Add status message helper if not exists:

```python
def _show_status_message(self, message: str, error: bool = False) -> None:
    """Show a status message to the user."""
    # Implementation depends on existing status bar
    # Could use a toast, label, or print for now
    print(f"{'ERROR: ' if error else ''}{message}")
```

**Files**:
- `src/ui/planning_tab.py` (modify)

**Notes**:
- On success: update `_original_selection` so Cancel reverts to new state
- On error: keep current UI selection state (don't lose user's work)
- Use try/except to handle ValidationError gracefully

---

### Subtask T014 – Implement Cancel Button Handler

**Purpose**: Revert to last saved state when user clicks Cancel.

**Steps**:
1. Add the cancel handler method:

```python
def _on_recipe_selection_cancel(self) -> None:
    """Handle recipe selection cancel - revert to last saved state."""
    self._recipe_selection_frame.set_selected(self._original_selection)
```

**Files**:
- `src/ui/planning_tab.py` (modify)

**Notes**:
- Simply restores the selection state that was loaded (or last saved)
- Does not hide the frame - user might want to try again

---

### Subtask T015 – Handle Edge Cases

**Purpose**: Gracefully handle edge conditions.

**Edge Cases**:

1. **No event selected**: Frame should be hidden
   - Already handled in T012

2. **Empty recipe list**: Show "No recipes available" message
   - Already handled in RecipeSelectionFrame.populate_recipes

3. **Save failure**: Show error, maintain UI state
   - Already handled in T013

4. **Event deleted while editing**: Handle gracefully

```python
def _on_recipe_selection_save(self, selected_ids: List[int]) -> None:
    """Handle recipe selection save."""
    if self._selected_event_id is None:
        self._show_status_message("No event selected", error=True)
        return

    from src.services import event_service
    from src.utils.db import session_scope
    from src.utils.error import ValidationError

    try:
        with session_scope() as session:
            count = event_service.set_event_recipes(
                session,
                self._selected_event_id,
                selected_ids,
            )
            session.commit()

        self._original_selection = selected_ids.copy()
        self._show_status_message(f"Saved {count} recipe selections")

    except ValidationError as e:
        # Event or recipe not found
        self._show_status_message(str(e), error=True)
    except Exception as e:
        self._show_status_message(f"Error saving: {str(e)}", error=True)
```

5. **Refresh event table**: Re-select current event to reload selections

```python
def _on_refresh(self) -> None:
    """Handle refresh button click."""
    # Refresh event table
    self._refresh_event_table()

    # Re-load recipe selection if event is selected
    if self._selected_event_id:
        self._show_recipe_selection(self._selected_event_id)
```

**Files**:
- `src/ui/planning_tab.py` (modify)

---

### Subtask T016 – Add Integration Tests [P]

**Purpose**: Verify end-to-end workflow with integration tests.

**Steps**:
1. Add integration tests to `src/tests/test_recipe_selection.py`:

```python
"""Integration tests for recipe selection workflow."""


class TestRecipeSelectionIntegration:
    """Integration tests for full recipe selection workflow."""

    def test_select_event_loads_empty_selections(self, planning_event, test_recipes):
        """Selecting an event with no selections shows unchecked recipes."""
        with session_scope() as session:
            # No selections yet
            result = event_service.get_event_recipe_ids(session, planning_event.id)
            assert result == []

    def test_save_and_reload_selections(self, planning_event, test_recipes):
        """Selections persist through save and reload cycle."""
        selected = [test_recipes[0].id, test_recipes[2].id]

        # Save selections
        with session_scope() as session:
            event_service.set_event_recipes(session, planning_event.id, selected)
            session.commit()

        # Reload and verify
        with session_scope() as session:
            loaded = event_service.get_event_recipe_ids(session, planning_event.id)
            assert set(loaded) == set(selected)

    def test_replace_behavior_not_append(self, planning_event, test_recipes):
        """Saving replaces selections, not appends (FR-010)."""
        # Initial selection
        with session_scope() as session:
            event_service.set_event_recipes(
                session, planning_event.id, [test_recipes[0].id]
            )
            session.commit()

        # Replace with different selection
        with session_scope() as session:
            event_service.set_event_recipes(
                session, planning_event.id, [test_recipes[1].id]
            )
            session.commit()

        # Verify only new selection exists
        with session_scope() as session:
            result = event_service.get_event_recipe_ids(session, planning_event.id)
            assert result == [test_recipes[1].id]

    def test_multiple_events_independent(self, test_recipes):
        """Selections for different events are independent."""
        from datetime import date

        with session_scope() as session:
            event1 = event_service.create_planning_event(
                session, name="Event 1", event_date=date(2026, 7, 1)
            )
            event2 = event_service.create_planning_event(
                session, name="Event 2", event_date=date(2026, 7, 2)
            )
            session.commit()
            event1_id, event2_id = event1.id, event2.id

        # Set different selections
        with session_scope() as session:
            event_service.set_event_recipes(session, event1_id, [test_recipes[0].id])
            event_service.set_event_recipes(session, event2_id, [test_recipes[1].id, test_recipes[2].id])
            session.commit()

        # Verify independence
        with session_scope() as session:
            result1 = event_service.get_event_recipe_ids(session, event1_id)
            result2 = event_service.get_event_recipe_ids(session, event2_id)
            assert result1 == [test_recipes[0].id]
            assert set(result2) == {test_recipes[1].id, test_recipes[2].id}
```

**Files**:
- `src/tests/test_recipe_selection.py` (modify)

**Run Tests**:
```bash
./run-tests.sh src/tests/test_recipe_selection.py -v
```

---

## Test Strategy

**Integration Tests**:
- All tests in T016 must pass
- Run full test suite for regression check

**Manual Testing**:
1. Launch app: `python src/main.py`
2. Go to Planning tab
3. Select an event - recipe selection should appear
4. Check some recipes - count should update
5. Click Save - should show success message
6. Select different event, then back - selections should persist
7. Check Cancel - should revert to saved state

**Commands**:
```bash
# Run integration tests
./run-tests.sh src/tests/test_recipe_selection.py -v

# Run full suite
./run-tests.sh -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session detachment | Use single session_scope per operation |
| Layout conflicts | Test with different window sizes |
| Event table callback issues | Trace existing selection mechanism |
| Race conditions on rapid clicks | Disable Save during save operation (optional enhancement) |

---

## Definition of Done Checklist

- [ ] RecipeSelectionFrame embedded in PlanningTab
- [ ] Frame shows when event selected, hides when none selected
- [ ] Existing selections load on event selection
- [ ] Save button persists selections
- [ ] Cancel button reverts to last saved state
- [ ] Edge cases handled gracefully
- [ ] Integration tests passing
- [ ] All existing tests continue to pass
- [ ] Manual testing confirms full workflow

---

## Review Guidance

**Key checkpoints for reviewer**:
1. Test the full workflow: select event → check recipes → save → reopen → verify
2. Verify save uses replace behavior (not append)
3. Verify cancel reverts to last saved state (not initial state)
4. Test edge cases: no event, empty recipe list, save failure
5. Check layout on different window sizes

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-01-26T22:57:43Z – system – lane=planned – Prompt generated via /spec-kitty.tasks

---

### Updating Lane Status

To change this work package's lane:
```bash
spec-kitty agent tasks move-task WP03 --to <lane> --note "message"
```

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
- 2026-01-26T23:43:55Z – unknown – shell_pid=16206 – lane=for_review – Ready for review: PlanningTab integration complete with save/cancel functionality and integration tests
- 2026-01-26T23:48:23Z – claude-opus-4-5 – shell_pid=18836 – lane=doing – Started review via workflow command
