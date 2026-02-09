---
work_package_id: WP05
title: Quantity Persistence and Atomic Save
lane: "for_review"
dependencies:
- WP01
- WP02
- WP03
base_branch: 100-planning-fg-selection-refinement-WP03
base_commit: 363711d4de2a48bd1f05a085f599e79586555c78
created_at: '2026-02-09T22:58:48.551008+00:00'
subtasks:
- T019
- T020
- T021
phase: Phase 4 - Save Integration
assignee: ''
agent: "claude-opus"
shell_pid: "34708"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-09T21:25:52Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 -- Quantity Persistence and Atomic Save

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP05 --base WP03
```

Depends on WP03 (uses `_selected_fg_ids` and `_fg_quantities` persistence state).

---

## Objectives & Success Criteria

Ensure quantities persist in UI state across navigation and save atomically to database on final Save. This implements User Story 6 from the spec.

**Success Criteria:**
- Quantity entries update `_fg_quantities` dict in real-time
- Navigating away from FG selection and back preserves quantities
- Save button collects all (fg_id, quantity) pairs and calls `set_event_fg_quantities()`
- Save button disabled when: no FGs selected, or any checked FG has invalid quantity
- Validation messages match spec exactly (5 distinct messages)
- Database write is atomic (all-or-nothing via existing service function)

## Context & Constraints

- **Spec**: US6 (11 acceptance scenarios)
- **Plan**: Phase 5, Design Decision D5
- **Existing service**: `set_event_fg_quantities()` at `src/services/event_service.py:3439` handles atomic replace
- **Existing validation**: F071 validation pattern in `fg_selection_frame.py` (lines 311-339)
- **WP03 state**: `_selected_fg_ids: Set[int]`, `_fg_quantities: Dict[int, int]`

**Key Constraints:**
- `set_event_fg_quantities()` validates event exists and is in DRAFT state
- It filters to only available FGs (silently drops invalid IDs)
- It uses replace pattern: DELETE all existing, INSERT new
- Quantities must be positive integers (DB constraint: `quantity > 0`)
- The existing `_validate_quantity()` method handles per-field validation display

## Subtasks & Detailed Guidance

### Subtask T019 -- Integrate quantity persistence with FG selection persistence

- **Purpose**: Ensure every quantity change immediately updates `_fg_quantities` dict so quantities survive filter changes and navigation.
- **Files**: `src/ui/components/fg_selection_frame.py`
- **Parallel?**: No

**Steps**:

1. **Verify quantity trace callback** updates `_fg_quantities` (from WP03 T010):
   - The `_on_quantity_change(fg_id)` method should already update `_fg_quantities[fg_id]`
   - Verify it handles all cases:
     - Valid positive integer: store in dict
     - Zero, negative, decimal, non-numeric: do NOT update dict (keep previous valid value)
     - Empty string: do NOT remove from dict (preserve for re-display)

2. **Verify restore behavior** in `_render_finished_goods()`:
   - When a FG is rendered and `fg_id in self._fg_quantities`, pre-fill the quantity entry
   - This should already work from WP03 T011

3. **Add edge case handling**:
   - When user unchecks a FG, its quantity should stay in `_fg_quantities` so re-checking restores it
   - When user clears quantity field on a checked FG, `_fg_quantities` should NOT be cleared (to avoid data loss on accidental clear)

4. **Update validation messages** to match spec exactly:
```python
def _validate_quantity(self, fg_id: int) -> None:
    """Validate quantity and show spec-mandated error messages."""
    qty_var = self._quantity_vars.get(fg_id)
    feedback_label = self._feedback_labels.get(fg_id)
    checkbox_var = self._checkbox_vars.get(fg_id)

    if qty_var is None or feedback_label is None:
        return

    qty_text = qty_var.get().strip()
    is_checked = checkbox_var.get() if checkbox_var else False

    # If not checked, no validation needed
    if not is_checked:
        feedback_label.configure(text="", text_color=("gray60", "gray40"))
        return

    # Empty quantity on checked item
    if not qty_text:
        feedback_label.configure(text="Quantity required", text_color="orange")
        return

    # Try parsing
    try:
        value = float(qty_text)
    except ValueError:
        feedback_label.configure(text="Enter a valid number", text_color="orange")
        return

    # Check for decimal
    if value != int(value):
        feedback_label.configure(text="Whole numbers only", text_color="orange")
        return

    int_value = int(value)

    # Check for negative
    if int_value < 0:
        feedback_label.configure(text="Quantity must be positive", text_color="orange")
        return

    # Check for zero
    if int_value == 0:
        feedback_label.configure(
            text="Quantity must be greater than zero", text_color="orange"
        )
        return

    # Valid
    feedback_label.configure(text="", text_color=("gray60", "gray40"))
    self._fg_quantities[fg_id] = int_value
```

### Subtask T020 -- Wire Save button to `set_event_fg_quantities()` with in-memory state

- **Purpose**: When Save is clicked, collect all selected FG/quantity pairs and write atomically to database.
- **Files**: `src/ui/planning_tab.py`, `src/ui/components/fg_selection_frame.py`
- **Parallel?**: No (depends on T019)

**Steps**:

1. **Ensure the FG frame's save callback** returns the complete selection state:
   - The existing `_handle_save()` calls `self._on_save(self.get_selected())`
   - `get_selected()` should return `List[Tuple[int, int]]` from persistence state (implemented in WP03)
   - Verify this returns ALL selected FGs with valid quantities, not just visible ones

2. **Verify planning_tab save callback** calls `set_event_fg_quantities()`:
   - The existing save callback in planning_tab.py should already call `set_event_fg_quantities()`
   - Verify it passes the full list from `get_selected()`
   - The service function handles:
     - Event validation
     - Plan state check (DRAFT only)
     - Available FG filtering
     - Atomic delete + insert

3. **Handle save result**: If save succeeds, refresh downstream views (shopping summary, assembly status, batch options).

4. **Handle save errors**: Catch `PlanStateError` if event is no longer DRAFT. Show user-friendly error.

### Subtask T021 -- Validate Save button disabled state

- **Purpose**: Disable Save button when no FGs are selected or when any checked FG has a validation error.
- **Files**: `src/ui/components/fg_selection_frame.py`
- **Parallel?**: No (depends on T019, T020)

**Steps**:

1. **Add save button state management**:
```python
def _update_save_button_state(self) -> None:
    """Enable/disable Save button based on validation state."""
    if not self._selected_fg_ids:
        # No FGs selected
        self._save_button.configure(state="disabled")
        return

    if self.has_validation_errors():
        self._save_button.configure(state="disabled")
        return

    self._save_button.configure(state="normal")
```

2. **Update `has_validation_errors()`** to check persistence state:
```python
def has_validation_errors(self) -> bool:
    """Check if any selected FG has invalid quantity."""
    for fg_id in self._selected_fg_ids:
        qty = self._fg_quantities.get(fg_id, 0)
        if qty <= 0:
            return True
    return False
```

3. **Call `_update_save_button_state()`** from:
   - `_on_checkbox_toggle()` (selection change)
   - `_on_quantity_change()` (quantity change)
   - `_on_filter_change()` (after re-render)
   - `clear_selections()` (after clear)
   - `set_selected_with_quantities()` (after restore)

4. **Add tooltip or visual indicator** when Save is disabled:
   - If no FGs selected: count label already shows "0 selected"
   - If validation errors: individual feedback labels show per-field errors

5. **Edge case**: Save with no FGs selected should not be possible (button disabled). But if somehow triggered, service function returns 0 records created.

## Risks & Mitigations

- **Risk**: `has_validation_errors()` checks visible FGs only, not hidden selected ones
  - **Mitigation**: Check `_fg_quantities` dict against `_selected_fg_ids` set (checks ALL selected)
- **Risk**: Race condition between qty_var trace and save button state update
  - **Mitigation**: Both run on main thread (Tkinter is single-threaded); no race possible
- **Risk**: `set_event_fg_quantities()` silently drops unavailable FGs
  - **Mitigation**: This is correct behavior — if recipes changed and FG is no longer available, it should be dropped

## Definition of Done Checklist

- [ ] Quantities update `_fg_quantities` on every valid change
- [ ] Quantities persist across filter changes
- [ ] Quantities persist across step navigation (back to recipe selection and forward again)
- [ ] Validation messages match spec:
  - [ ] "Quantity must be greater than zero" for 0
  - [ ] "Whole numbers only" for decimals
  - [ ] "Quantity must be positive" for negatives
  - [ ] "Enter a valid number" for non-numeric
  - [ ] "Quantity required" for empty on checked FG
- [ ] Save button disabled when no FGs selected
- [ ] Save button disabled when validation errors exist
- [ ] Save calls `set_event_fg_quantities()` with all selected FG/qty pairs
- [ ] Save is atomic (all-or-nothing)
- [ ] Downstream views refresh after save
- [ ] All existing tests still pass

## Review Guidance

- **US6 Acceptance Scenarios**: Walk through all 11 scenarios from spec
- Verify all 5 validation messages appear correctly
- Verify Save button enabled/disabled transitions
- Verify quantities survive: enter qty → change filter → change back → qty still there
- Verify atomic save: check DB after save has all records
- Verify edge case: uncheck FG, re-check → quantity restored from `_fg_quantities`

## Activity Log

- 2026-02-09T21:25:52Z -- system -- lane=planned -- Prompt created.
- 2026-02-09T22:58:49Z – claude-opus – shell_pid=34708 – lane=doing – Assigned agent via workflow command
- 2026-02-09T23:11:06Z – claude-opus – shell_pid=34708 – lane=for_review – Ready for review: T019 validation messages, T020 save wiring verified, T021 save button state management
