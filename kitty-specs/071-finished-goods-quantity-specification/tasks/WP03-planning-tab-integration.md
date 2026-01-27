---
work_package_id: WP03
title: Planning Tab Integration
lane: "for_review"
dependencies:
- WP01
base_branch: 071-finished-goods-quantity-specification-WP02
base_commit: 0244f2cd4e749e76f8098dd94849525c13bf0dd7
created_at: '2026-01-27T14:37:59.378395+00:00'
subtasks:
- T009
- T010
- T011
- T012
phase: Phase 3 - Integration
assignee: ''
agent: ''
shell_pid: "80449"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-27T12:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Planning Tab Integration

## Implementation Command

```bash
spec-kitty implement WP03 --base WP02
```

**Note**: Uses `--base WP02` because this work package depends on both WP01 and WP02 (WP02 includes WP01).

---

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged` in frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – This section is empty initially.

---

## Objectives & Success Criteria

Wire up service layer to UI component; complete end-to-end quantity workflow.

**Success Criteria:**
- [ ] Quantities load when event is opened (pre-populated in UI)
- [ ] Quantities save when user clicks Save (persisted to database)
- [ ] Status bar shows save feedback ("Saved X finished goods" or error)
- [ ] End-to-end flow works: enter quantities → save → close → reopen → quantities preserved
- [ ] User Stories 1, 2, 3 from spec.md pass acceptance tests

## Context & Constraints

### Referenced Documents
- **Spec**: `kitty-specs/071-finished-goods-quantity-specification/spec.md` (acceptance scenarios)
- **Plan**: `kitty-specs/071-finished-goods-quantity-specification/plan.md`
- **Data Model**: `kitty-specs/071-finished-goods-quantity-specification/data-model.md` (data flow diagrams)

### Current Planning Tab Structure

**File**: `src/ui/planning_tab.py`

Key methods (from research.md):
```python
def _show_fg_selection(self, event_id: int) -> None:
    """Load and show FG selection."""
    with session_scope() as session:
        available_fgs = event_service.get_available_finished_goods(event_id, session)
        selected_ids = event_service.get_event_finished_good_ids(session, event_id)

    self._fg_selection_frame.populate_finished_goods(available_fgs, event_name)
    self._fg_selection_frame.set_selected(selected_ids)
    # ... show frame

def _on_fg_selection_save(self, selected_ids: List[int]) -> None:
    """Save FG selections."""
    with session_scope() as session:
        count = event_service.set_event_finished_goods(session, event_id, selected_ids)
        session.commit()
    self._update_status(f"Saved {count} finished goods")
```

### Target Integration

**Load flow**:
```
_show_fg_selection(event_id)
    │
    ├── get_available_finished_goods(event_id, session)
    ├── get_event_fg_quantities(session, event_id)  ← NEW
    │
    ├── populate_finished_goods(available_fgs, event_name)
    └── set_selected_with_quantities(fg_quantities)  ← NEW
```

**Save flow**:
```
_on_fg_selection_save()
    │
    ├── get_selected() → List[(fg_id, quantity)]  ← UPDATED
    ├── set_event_fg_quantities(session, event_id, fg_quantities)  ← NEW
    │
    └── _update_status("Saved X finished goods")
```

---

## Subtasks & Detailed Guidance

### Subtask T009 – Update _show_fg_selection() to Load Quantities

**Purpose**: Load existing quantities when displaying FG selection for an event.

**File**: `src/ui/planning_tab.py`

**Steps**:

1. **Find `_show_fg_selection()` method** (around line 387-434 per research.md).

2. **Update the session scope to also fetch quantities**:
   ```python
   def _show_fg_selection(self, event_id: int) -> None:
       """Load and show FG selection with quantities."""
       with session_scope() as session:
           # Get event name for header
           event = session.query(Event).filter(Event.id == event_id).first()
           if not event:
               self._update_status("Event not found", is_error=True)
               return
           event_name = event.name

           # Get available FGs
           available_fgs = event_service.get_available_finished_goods(event_id, session)

           # Get existing quantities (NEW)
           fg_quantities = event_service.get_event_fg_quantities(session, event_id)

       # Populate UI
       self._fg_selection_frame.populate_finished_goods(available_fgs, event_name)

       # Set quantities (NEW - replaces set_selected)
       qty_tuples = [(fg.id, qty) for fg, qty in fg_quantities]
       self._fg_selection_frame.set_selected_with_quantities(qty_tuples)

       # Show frame
       self._fg_selection_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
   ```

3. **Add import** if not present:
   ```python
   from src.services import event_service
   ```

4. **Handle empty quantities gracefully** (new event with no FGs selected).

**Validation**:
- Existing quantities appear in entry fields
- New events show empty quantity fields
- Available FGs list still displays correctly

---

### Subtask T010 – Update _on_fg_selection_save() to Save Quantities

**Purpose**: Save quantities using the new service method.

**File**: `src/ui/planning_tab.py`

**Steps**:

1. **Find `_on_fg_selection_save()` method** or the save callback handler.

2. **Update to use new service method and return type**:
   ```python
   def _on_fg_selection_save(self) -> None:
       """Save FG selections with quantities."""
       # Get selected FGs with quantities from UI
       fg_quantities = self._fg_selection_frame.get_selected()

       # Validate before saving (optional - service handles most validation)
       if self._fg_selection_frame.has_validation_errors():
           self._update_status("Please fix invalid quantities", is_error=True)
           return

       try:
           with session_scope() as session:
               count = event_service.set_event_fg_quantities(
                   session,
                   self._current_event_id,
                   fg_quantities
               )
               session.commit()

           self._update_status(f"Saved {count} finished goods")
           self._hide_fg_selection()
           self._refresh_event_data()  # Refresh display if needed

       except Exception as e:
           self._update_status(f"Error saving: {str(e)}", is_error=True)
   ```

3. **Ensure `_current_event_id` is available** (should already be tracked).

4. **Handle validation errors** from the UI component.

**Validation**:
- Quantities are saved to database
- Status shows success message with count
- Error handling works for database errors

---

### Subtask T011 – Add Status Bar Feedback

**Purpose**: Show clear feedback for save success or errors.

**File**: `src/ui/planning_tab.py`

**Steps**:

1. **Use existing `_update_status()` method** (from research.md, lines 507-525):
   ```python
   def _update_status(self, message: str, is_error: bool = False) -> None:
       """Update status bar with feedback."""
       color = "red" if is_error else ("gray60", "gray40")
       self.status_label.configure(text=message, text_color=color)

       if message and not is_error:
           self.after(5000, lambda: self._clear_status_if_unchanged(message))
   ```

2. **Ensure appropriate messages** are used:
   - Success: `f"Saved {count} finished goods"` (green/neutral)
   - Validation error: `"Please fix invalid quantities"` (red)
   - Database error: `f"Error saving: {error_message}"` (red)

3. **Add validation error case** if not already handled:
   ```python
   # In _on_fg_selection_save():
   if self._fg_selection_frame.has_validation_errors():
       self._update_status("Please fix invalid quantities before saving", is_error=True)
       return
   ```

**Validation**:
- Success message appears after save
- Error message appears on validation failure
- Error message is red, success is normal color
- Messages auto-clear after 5 seconds (success only)

---

### Subtask T012 – End-to-End Validation

**Purpose**: Manually verify the complete workflow matches acceptance criteria.

**Steps**:

1. **Test User Story 1 - Specify Quantities** (Priority P1):
   ```
   Scenario 1.1:
   Given: Event is open with available FGs displayed
   When: Enter "24" in a FG's quantity field
   Then: Value is accepted and displayed

   Scenario 1.2:
   Given: Event with FGs displayed
   When: Enter quantities for multiple FGs and save
   Then: All quantities are persisted (verify in database)

   Scenario 1.3:
   Given: Enter invalid value (0, -5, "abc")
   When: Try to save
   Then: See validation error, invalid value not saved
   ```

2. **Test User Story 2 - Load Existing Quantities** (Priority P2):
   ```
   Scenario 2.1:
   Given: Event has saved quantities
   When: Open that event
   Then: Quantity fields are pre-populated with saved values

   Scenario 2.2:
   Given: Event has some FGs with quantities, some without
   When: Open event
   Then: FGs with quantities show values, others show empty
   ```

3. **Test User Story 3 - Modify Quantities** (Priority P3):
   ```
   Scenario 3.1:
   Given: Event with saved quantity of 24
   When: Change to 36 and save
   Then: Database reflects new quantity of 36

   Scenario 3.2:
   Given: Event with saved quantity
   When: Clear the quantity field and save
   Then: FG is removed from event (no database record)

   Scenario 3.3:
   Given: Event where FG has no quantity
   When: Add quantity and save
   Then: New record created in database
   ```

4. **Test Edge Cases**:
   ```
   - Leading zeros ("007") → accepts as 7
   - Decimal ("24.5") → shows validation error
   - Pasted text → shows validation error
   - Tab through fields without entering → empty fields valid
   ```

5. **Database Verification**:
   ```bash
   # Open SQLite browser or use CLI
   sqlite3 data/bake_tracker.db
   SELECT * FROM event_finished_goods WHERE event_id = <test_event_id>;
   ```

**Validation**:
- All acceptance scenarios from spec.md pass
- Edge cases handled correctly
- No data loss on save/reload cycle

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Data loss on save | Use replace pattern - all current values saved |
| UX confusion | Clear status messages for success/error |
| Session issues | Follow session scope pattern strictly |
| Breaking existing functionality | Test FG selection still works without quantities |

---

## Definition of Done Checklist

- [ ] `_show_fg_selection()` loads quantities from database
- [ ] `_on_fg_selection_save()` saves quantities to database
- [ ] Status bar shows success/error messages
- [ ] User Story 1 acceptance scenarios pass
- [ ] User Story 2 acceptance scenarios pass
- [ ] User Story 3 acceptance scenarios pass
- [ ] Edge cases handled (leading zeros, decimals, text)
- [ ] No regressions in existing Planning Tab functionality

---

## Review Guidance

**Key Acceptance Checkpoints**:
1. Quantities load correctly when opening event?
2. Quantities save correctly when clicking Save?
3. Round-trip works (enter → save → close → open → values preserved)?
4. Validation errors prevent save with clear message?
5. Status bar feedback is visible and appropriate?

**Manual Testing Protocol**:
1. Start app fresh
2. Create/select test event
3. Enter quantities for 2-3 FGs
4. Save and verify status message
5. Navigate away, then return to event
6. Verify quantities are preserved
7. Modify one quantity, clear another
8. Save and verify changes persisted

---

## Activity Log

- 2026-01-27T12:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-27T14:41:56Z – unknown – shell_pid=80449 – lane=for_review – All subtasks complete. 61 tests passing (10 planning tab FG + 36 FGSelectionFrame + 15 event service). End-to-end quantity workflow implemented: load, save, validate, cancel.
