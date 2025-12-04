---
work_package_id: "WP07"
subtasks:
  - "T028"
  - "T029"
  - "T030"
  - "T031"
  - "T032"
  - "T033"
  - "T034"
title: "Validation & Polish"
phase: "Phase 4 - Integration & Polish"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "62373"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-04T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 - Validation & Polish

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Add confirmation dialog before destructive FIFO consumption
- Implement over-production warning
- Handle all edge cases gracefully
- Pass code quality checks (black, flake8, mypy)
- Complete end-to-end validation against all acceptance scenarios
- Feature is production-ready

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/008-production-tracking/spec.md` (Edge Cases section)
- Constitution: `.kittify/memory/constitution.md` (Quality Standards)

**Edge Cases to Handle**:
1. Production exceeds planned quantities -> warn but allow
2. Insufficient pantry inventory -> prevent with clear error
3. Event with no packages -> show "No packages planned"
4. All packages delivered -> show "Complete" status
5. Recipe modified after production started -> existing records retain original cost

---

## Subtasks & Detailed Guidance

### Subtask T028 - Add Confirmation Dialog for FIFO Consumption [P]

**Purpose**: Protect user from accidental destructive operations.

**Steps**:
1. Before calling `record_production()` in UI, show confirmation
2. Dialog should explain: "This will consume pantry inventory. This action cannot be undone."
3. Show what will be consumed (optional preview)
4. Require explicit confirmation before proceeding

```python
def _confirm_production(self, event_id: int, recipe_id: int, batches: int):
    """Show confirmation before recording production."""
    # Build confirmation message
    message = (
        f"Record {batches} batch(es) of production?\n\n"
        f"This will consume pantry inventory via FIFO.\n"
        f"This action cannot be undone."
    )

    # Use messagebox or custom dialog
    from tkinter import messagebox
    result = messagebox.askyesno(
        "Confirm Production",
        message,
        icon="warning"
    )

    if result:
        self._record_production_confirmed(event_id, recipe_id, batches)


def _record_production_confirmed(self, event_id: int, recipe_id: int, batches: int):
    """Actually record production after confirmation."""
    try:
        record = production_service.record_production(
            event_id=event_id,
            recipe_id=recipe_id,
            batches=batches
        )
        # Success handling...
    except Exception as e:
        # Error handling...
```

**Files**: `src/ui/production_tab.py` (MODIFY)

---

### Subtask T029 - Implement Over-Production Warning [P]

**Purpose**: Warn user when producing more than planned.

**Steps**:
1. Before recording, check if this would exceed required batches
2. Show warning dialog: "You are producing more than planned. Continue?"
3. Allow user to proceed if they confirm
4. Log the over-production in notes (optional)

```python
def _check_over_production(self, event_id: int, recipe_id: int, new_batches: int) -> bool:
    """Check if production would exceed planned amount."""
    try:
        progress = production_service.get_production_progress(event_id)

        for recipe in progress['recipes']:
            if recipe['recipe_id'] == recipe_id:
                already_produced = recipe['batches_produced']
                required = recipe['batches_required']
                total_would_be = already_produced + new_batches

                if total_would_be > required:
                    # Show warning
                    from tkinter import messagebox
                    result = messagebox.askyesno(
                        "Over-Production Warning",
                        f"This will produce {total_would_be} batches total, "
                        f"but only {required} are planned.\n\n"
                        f"Continue anyway?",
                        icon="warning"
                    )
                    return result

        return True  # No warning needed

    except Exception:
        return True  # Proceed on error (service will handle)
```

**Files**: `src/ui/production_tab.py` (ADD)

---

### Subtask T030 - Add Insufficient Inventory Error Handling [P]

**Purpose**: Clear, actionable error when pantry lacks ingredients.

**Steps**:
1. Catch InsufficientInventoryError in UI
2. Show detailed message: which ingredient, how much needed, how much available
3. Suggest user add to pantry or reduce batch count

```python
def _handle_production_error(self, error: Exception):
    """Handle production errors with user-friendly messages."""
    from tkinter import messagebox

    if isinstance(error, production_service.InsufficientInventoryError):
        messagebox.showerror(
            "Insufficient Inventory",
            f"Not enough {error.ingredient_slug} in pantry.\n\n"
            f"Needed: {error.needed}\n"
            f"Available: {error.available}\n\n"
            f"Add more to the pantry or reduce batch count."
        )

    elif isinstance(error, production_service.InvalidStatusTransitionError):
        messagebox.showerror(
            "Invalid Status Change",
            f"Cannot change status from '{error.current.value}' to '{error.target.value}'.\n\n"
            f"Packages must progress: pending -> assembled -> delivered"
        )

    elif isinstance(error, production_service.IncompleteProductionError):
        missing_names = ", ".join(r['recipe_name'] for r in error.missing_recipes)
        messagebox.showerror(
            "Cannot Assemble Package",
            f"Some recipes are not fully produced:\n{missing_names}\n\n"
            f"Complete production before marking as assembled."
        )

    else:
        messagebox.showerror("Error", str(error))
```

**Files**: `src/ui/production_tab.py` (ADD)

---

### Subtask T031 - Handle "No Packages" Edge Case [P]

**Purpose**: Graceful handling when event has no package assignments.

**Steps**:
1. In dashboard, check if event has 0 packages
2. Display "No packages planned" instead of progress
3. Still allow viewing the event, just show empty state

```python
# In _create_event_card
if summary['packages_total'] == 0:
    no_pkg_label = ctk.CTkLabel(
        card,
        text="No packages planned",
        text_color="gray",
        font=ctk.CTkFont(size=11, slant="italic")
    )
    no_pkg_label.pack(anchor="w", padx=10)
```

**Files**: `src/ui/production_tab.py` (MODIFY)

---

### Subtask T032 - Mark Event Complete When Delivered [P]

**Purpose**: Clear visual indicator when event is fully complete.

**Steps**:
1. When all packages are delivered, show "COMPLETE" badge
2. Optionally move completed events to bottom of list
3. Use distinct color (green) for complete events

```python
# Already partially implemented in event cards
# Ensure is_complete logic is correct:
# is_complete = all packages delivered AND total > 0

# In service (verify):
"is_complete": delivered == total_packages and total_packages > 0

# In UI, highlight completed events
if summary['is_complete']:
    card.configure(border_color="green", border_width=2)
    complete_badge = ctk.CTkLabel(
        card,
        text="COMPLETE",
        text_color="white",
        fg_color="green",
        corner_radius=5
    )
    complete_badge.pack(anchor="e", padx=10, pady=5)
```

**Files**: `src/ui/production_tab.py` (MODIFY), `src/services/production_service.py` (VERIFY)

---

### Subtask T033 - Run Code Quality Checks [P]

**Purpose**: Ensure code meets project quality standards.

**Steps**:
1. Run black on all new/modified files:
   ```bash
   black src/models/package_status.py src/models/production_record.py
   black src/models/event.py src/services/production_service.py
   black src/ui/production_tab.py src/ui/main_window.py
   black src/tests/services/test_production_service.py
   ```

2. Run flake8:
   ```bash
   flake8 src/models/package_status.py src/models/production_record.py
   flake8 src/services/production_service.py
   flake8 src/ui/production_tab.py
   flake8 src/tests/services/test_production_service.py
   ```

3. Run mypy:
   ```bash
   mypy src/models/package_status.py src/models/production_record.py
   mypy src/services/production_service.py
   ```

4. Fix any issues found

**Files**: All new/modified files

---

### Subtask T034 - End-to-End Manual Validation

**Purpose**: Verify feature against all acceptance scenarios from spec.

**Steps**:

**User Story 1 - Record Recipe Production**:
- [ ] Create event with packages requiring 3 batches
- [ ] Record 2 batches -> verify pantry depleted
- [ ] Verify actual cost captured (not estimate)
- [ ] Try recording with insufficient pantry -> verify error

**User Story 2 - Track Package Assembly**:
- [ ] Try marking pending package as assembled with incomplete production -> verify blocked
- [ ] Complete all production -> mark as assembled -> verify success
- [ ] View multiple packages -> verify status shown correctly

**User Story 3 - Track Package Delivery**:
- [ ] Mark assembled package as delivered -> verify success
- [ ] Try marking pending as delivered -> verify blocked
- [ ] Add delivery note -> verify saved

**User Story 4 - Production Dashboard**:
- [ ] Create 2 events with packages -> verify both appear
- [ ] Verify progress shows X of Y batches
- [ ] Click event -> verify detail loads

**User Story 5 - Cost Comparison**:
- [ ] Record production -> verify actual cost displayed
- [ ] View event summary -> verify actual vs planned
- [ ] Open recipe breakdown -> verify variance calculated

**Edge Cases**:
- [ ] Record more than planned -> verify warning shown
- [ ] Event with no packages -> verify handled gracefully
- [ ] All packages delivered -> verify "Complete" shown

**Files**: Manual testing checklist

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Missed edge case | Systematic testing against spec |
| Code quality regressions | Run full test suite after polish |
| User confusion on warnings | Use clear, simple language |

---

## Definition of Done Checklist

- [ ] Confirmation dialog before FIFO consumption
- [ ] Over-production warning implemented
- [ ] Insufficient inventory shows clear error
- [ ] No-packages edge case handled
- [ ] Complete events marked clearly
- [ ] All code passes black formatting
- [ ] All code passes flake8 linting
- [ ] All code passes mypy type checking
- [ ] All acceptance scenarios validated manually
- [ ] Full test suite passes
- [ ] `tasks.md` updated with completion status

---

## Review Guidance

- Verify all edge cases from spec are handled
- Run code quality tools and check output
- Manually test the happy path end-to-end
- Verify error messages are helpful for non-technical users

---

## Activity Log

- 2025-12-04T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-04T16:53:46Z – claude – shell_pid=62373 – lane=doing – Started implementation
