---
work_package_id: WP05
title: Integration with Planning Tab
lane: "doing"
dependencies:
- WP03
- WP04
base_branch: 073-batch-calculation-user-decisions-WP04
base_commit: 6591083eeac42a33f259d8561fbaf979d9d25e05
created_at: '2026-01-27T19:47:59.918508+00:00'
subtasks:
- T030
- T031
- T032
- T033
- T034
- T035
- T036
phase: Phase 3 - Integration
assignee: ''
agent: ''
shell_pid: "24352"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-27T18:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 – Integration with Planning Tab

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

This WP depends on WP03 (CRUD service) and WP04 (UI widget).

```bash
spec-kitty implement WP05
```

---

## Objectives & Success Criteria

**Primary Objective**: Wire up the complete flow: load batch options → user selection → shortfall confirmation → save decisions.

**Success Criteria**:
1. BatchOptionsFrame appears in planning_tab.py after FG quantities section
2. Options load automatically when event is selected
3. Shortfall confirmation dialog appears when user selects shortfall option
4. Decisions save correctly via batch_decision_service
5. Existing decisions load and pre-select on event open
6. Modifications trigger re-save

---

## Context & Constraints

**Why this is needed**: This is the integration point that brings all F073 components together into a working feature.

**Key Documents**:
- `src/ui/planning_tab.py` - Existing planning tab to modify
- `src/ui/widgets/dialogs.py` - show_confirmation() for shortfall dialog
- `kitty-specs/073-batch-calculation-user-decisions/plan.md` - Data flow diagram

**Constraints**:
- Follow existing planning_tab.py patterns
- Use show_confirmation() for shortfall warning
- Maintain clean separation of UI and service logic

---

## Subtasks & Detailed Guidance

### Subtask T030 – Add BatchOptionsFrame to planning_tab.py layout

**Purpose**: Add the widget to the planning tab UI.

**Steps**:
1. Open `src/ui/planning_tab.py`
2. Add import at top:

```python
from src.ui.widgets.batch_options_frame import BatchOptionsFrame
```

3. Find the layout section (likely in `__init__` or `_create_widgets`)
4. Add BatchOptionsFrame after the FG quantities section:

```python
# Batch Options Section (F073)
self._batch_options_label = ctk.CTkLabel(
    self._planning_frame,  # or appropriate parent
    text="Batch Options",
    font=ctk.CTkFont(weight="bold", size=16),
)
self._batch_options_label.pack(anchor="w", padx=10, pady=(20, 5))

self._batch_options_frame = BatchOptionsFrame(
    self._planning_frame,
    on_selection_change=self._on_batch_selection_change,
    height=300,
)
self._batch_options_frame.pack(fill="x", padx=10, pady=5)

# Save button for batch decisions
self._save_batches_button = ctk.CTkButton(
    self._planning_frame,
    text="Save Batch Decisions",
    command=self._save_batch_decisions,
)
self._save_batches_button.pack(anchor="e", padx=10, pady=10)
```

**Note**: Exact placement depends on existing layout structure. Review planning_tab.py first.

**Files**: `src/ui/planning_tab.py`
**Parallel?**: No - must be first

---

### Subtask T031 – Implement _load_batch_options()

**Purpose**: Load and display batch options when event is selected.

**Steps**:
1. Add import:

```python
from src.services.planning_service import calculate_batch_options
```

2. Add the method:

```python
def _load_batch_options(self) -> None:
    """Load batch options for the currently selected event."""
    if self._current_event_id is None:
        self._batch_options_frame.clear()
        return

    try:
        # Calculate options from F073
        options_results = calculate_batch_options(self._current_event_id)

        # Populate the widget
        self._batch_options_frame.populate(options_results)

        # Load existing decisions and pre-select
        self._load_existing_decisions()

    except Exception as e:
        # Show error in status bar or dialog
        self._show_error(f"Failed to load batch options: {e}")
```

3. Call `_load_batch_options()` when event is selected (find existing event selection handler)

**Files**: `src/ui/planning_tab.py`
**Parallel?**: No - depends on T030

---

### Subtask T032 – Implement shortfall confirmation dialog

**Purpose**: Show confirmation dialog when user selects a shortfall option.

**Steps**:
1. Add import:

```python
from src.ui.widgets.dialogs import show_confirmation
```

2. Add the method:

```python
def _on_batch_selection_change(self, fu_id: int, batches: int) -> None:
    """
    Handle batch selection change.

    Shows confirmation dialog if shortfall option selected.

    Args:
        fu_id: FinishedUnit ID
        batches: Number of batches selected
    """
    # Check if this is a shortfall selection
    selections = self._batch_options_frame.get_selection_with_shortfall_info()
    selection = next((s for s in selections if s["finished_unit_id"] == fu_id), None)

    if selection and selection["is_shortfall"]:
        # Show confirmation dialog
        confirmed = show_confirmation(
            "Shortfall Warning",
            f"This selection will produce fewer items than needed.\n\n"
            f"You will be short. Do you want to proceed with this selection?",
            parent=self,
        )

        if not confirmed:
            # User cancelled - need to revert selection
            # Could clear selection or revert to previous
            self._batch_options_frame.set_selection(fu_id, 0)  # Clear
            return

        # Mark as confirmed for save
        self._confirmed_shortfalls.add(fu_id)
    else:
        # Not a shortfall, remove from confirmed set if present
        self._confirmed_shortfalls.discard(fu_id)
```

3. Initialize tracking set in `__init__`:

```python
self._confirmed_shortfalls: set = set()
```

**Files**: `src/ui/planning_tab.py`
**Parallel?**: No - depends on T030, T031

---

### Subtask T033 – Implement _save_batch_decisions()

**Purpose**: Save user's batch selections.

**Steps**:
1. Add import:

```python
from src.services.batch_decision_service import (
    save_batch_decision,
    BatchDecisionInput,
    delete_batch_decisions,
)
```

2. Add the method:

```python
def _save_batch_decisions(self) -> None:
    """Save all batch decisions for the current event."""
    if self._current_event_id is None:
        return

    selections = self._batch_options_frame.get_selection_with_shortfall_info()

    if not selections:
        self._show_info("No batch selections to save.")
        return

    try:
        # Clear existing decisions first (replace pattern)
        delete_batch_decisions(self._current_event_id)

        # Save each decision
        for selection in selections:
            decision = BatchDecisionInput(
                finished_unit_id=selection["finished_unit_id"],
                batches=selection["batches"],
                is_shortfall=selection["is_shortfall"],
                confirmed_shortfall=selection["finished_unit_id"] in self._confirmed_shortfalls,
            )
            save_batch_decision(self._current_event_id, decision)

        self._show_success("Batch decisions saved successfully.")

    except ValidationError as e:
        self._show_error(f"Validation error: {e}")
    except Exception as e:
        self._show_error(f"Failed to save batch decisions: {e}")
```

**Files**: `src/ui/planning_tab.py`
**Parallel?**: No - depends on T032

---

### Subtask T034 – Implement load existing decisions on event open

**Purpose**: Pre-select radio buttons when opening an event with existing decisions.

**Steps**:
1. Add import:

```python
from src.services.batch_decision_service import get_batch_decisions
```

2. Add the method:

```python
def _load_existing_decisions(self) -> None:
    """Load existing batch decisions and pre-select options."""
    if self._current_event_id is None:
        return

    try:
        decisions = get_batch_decisions(self._current_event_id)

        for decision in decisions:
            self._batch_options_frame.set_selection(
                decision.finished_unit_id,
                decision.batches,
            )

    except Exception as e:
        # Log but don't fail - just means no pre-selection
        print(f"Warning: Could not load existing decisions: {e}")
```

3. Call from `_load_batch_options()` (already added in T031)

**Files**: `src/ui/planning_tab.py`
**Parallel?**: No - depends on T031

---

### Subtask T035 – Wire up modification flow

**Purpose**: Handle changes to existing decisions.

**Steps**:
1. The modification flow is already handled by T032 and T033:
   - User changes selection → `_on_batch_selection_change()` fires
   - User clicks save → `_save_batch_decisions()` replaces all decisions

2. Optional: Add auto-save on selection change (debounced):

```python
def _on_batch_selection_change(self, fu_id: int, batches: int) -> None:
    """..."""
    # ... (existing shortfall confirmation code from T032)

    # Optional: Auto-save after confirmation
    # Consider debouncing if this causes performance issues
    # self._save_batch_decisions()
```

3. Add visual indicator for unsaved changes:

```python
def _on_batch_selection_change(self, fu_id: int, batches: int) -> None:
    """..."""
    # ... (existing code)

    # Mark as having unsaved changes
    self._has_unsaved_batch_changes = True
    self._update_save_button_state()

def _update_save_button_state(self) -> None:
    """Update save button to indicate unsaved changes."""
    if self._has_unsaved_batch_changes:
        self._save_batches_button.configure(text="Save Batch Decisions *")
    else:
        self._save_batches_button.configure(text="Save Batch Decisions")

def _save_batch_decisions(self) -> None:
    """..."""
    # ... (existing code)

    # Reset unsaved indicator on success
    self._has_unsaved_batch_changes = False
    self._update_save_button_state()
```

**Files**: `src/ui/planning_tab.py`
**Parallel?**: No - depends on T033, T034

---

### Subtask T036 – End-to-end testing and validation

**Purpose**: Verify the complete flow works correctly.

**Test Scenarios**:

1. **Fresh event (no existing decisions)**:
   - Open planning tab
   - Select an event with FG selections
   - Verify batch options display
   - Make selections
   - Click save
   - Verify success message
   - Refresh/reopen event
   - Verify selections preserved

2. **Shortfall confirmation flow**:
   - Select a shortfall option (floor with shortage)
   - Verify confirmation dialog appears
   - Cancel → verify selection cleared
   - Select again, confirm → verify selection stays
   - Save → verify saved successfully

3. **Modify existing decisions**:
   - Open event with saved decisions
   - Verify pre-selected options
   - Change a selection
   - Save
   - Verify new selection saved

4. **Edge cases**:
   - Event with no FG selections → batch options should be empty
   - Event with bundles → verify bundle decomposition works
   - Multiple FUs from same recipe → verify both can be saved

**Validation Steps**:
1. Run the app: `python src/main.py`
2. Navigate to Planning tab
3. Execute each test scenario above
4. Document any issues found

**Files**: Manual testing (no code changes)
**Parallel?**: No - final validation

---

## Test Strategy

**Manual Testing** (UI integration is tested manually):

| Scenario | Expected Result | Pass/Fail |
|----------|-----------------|-----------|
| Open event with FGs | Batch options display | |
| Select non-shortfall option | No confirmation dialog | |
| Select shortfall option | Confirmation dialog appears | |
| Cancel shortfall confirmation | Selection cleared | |
| Confirm shortfall | Selection stays | |
| Save decisions | Success message | |
| Reopen event | Decisions pre-selected | |
| Event with no FGs | Empty batch options | |
| Event with bundles | Decomposed options display | |

**Automated Tests** (optional, for regression):

```python
# Integration test for service layer
def test_end_to_end_batch_flow(test_db, sample_event_with_fgs):
    """Test complete flow: calculate → save → retrieve."""
    # Calculate options
    options = calculate_batch_options(sample_event_with_fgs.id, session=test_db)
    assert len(options) > 0

    # Save decisions
    for result in options:
        if result.options:
            decision = BatchDecisionInput(
                finished_unit_id=result.finished_unit_id,
                batches=result.options[0].batches,
            )
            save_batch_decision(sample_event_with_fgs.id, decision, session=test_db)

    # Retrieve and verify
    saved = get_batch_decisions(sample_event_with_fgs.id, session=test_db)
    assert len(saved) == len(options)
```

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| State synchronization issues | Medium | Clear state on event change |
| Save on every selection slow | Low | Use explicit save button, not auto-save |
| Confirmation dialog blocking | Low | Standard modal pattern |
| Layout conflicts | Medium | Test with various window sizes |

---

## Definition of Done Checklist

- [ ] BatchOptionsFrame added to planning_tab.py
- [ ] Options load when event selected
- [ ] Shortfall confirmation dialog works
- [ ] Save button saves decisions
- [ ] Existing decisions pre-selected on event open
- [ ] Modification flow works
- [ ] All test scenarios pass
- [ ] No regressions in existing planning tab functionality

---

## Review Guidance

**Key Checkpoints**:
1. **User flow**: Complete flow from event selection to saved decisions
2. **State management**: Clean handling of event changes, unsaved state
3. **Error handling**: Graceful handling of failures
4. **UI responsiveness**: No blocking operations on main thread

**Questions for Review**:
- Is the shortfall confirmation flow intuitive?
- Should auto-save be implemented or explicit save button?
- Are all edge cases handled?

---

## Activity Log

- 2026-01-27T18:00:00Z – system – lane=planned – Prompt created.
