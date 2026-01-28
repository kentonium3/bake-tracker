---
work_package_id: WP04
title: Amendment UI Controls
lane: "doing"
dependencies:
- WP02
- WP03
base_branch: 078-plan-snapshots-amendments-WP03
base_commit: 72e4d69c1103a2a81579acab0503751940d337c3
created_at: '2026-01-28T03:59:21.139147+00:00'
subtasks:
- T016
- T017
- T018
- T019
- T020
phase: Phase 1 - Core Implementation
assignee: ''
agent: ''
shell_pid: "80435"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-28T03:25:47Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – Amendment UI Controls

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP04 --base WP02
```

Depends on WP02 (snapshot service must exist).

**Parallelization Note**: WP04 can run in parallel with WP03 (Amendment Service) after WP02 completes. The UI can be developed against the service interface while WP03 implements the actual service.

---

## Objectives & Success Criteria

**Objective**: Add amendment controls and history panel to the Planning Tab UI.

**Success Criteria**:
- [ ] Amendment controls panel visible when plan_state == IN_PRODUCTION
- [ ] DROP_FG dialog allows FG selection and reason entry
- [ ] ADD_FG dialog allows FG selection, quantity, and reason entry
- [ ] MODIFY_BATCH dialog allows batch adjustment and reason entry
- [ ] Amendment history panel shows all amendments chronologically
- [ ] UI refreshes after each amendment
- [ ] Application runs without errors: `python src/main.py`

---

## Context & Constraints

**Feature**: F078 Plan Snapshots & Amendments
**Spec**: `kitty-specs/078-plan-snapshots-amendments/spec.md` (US-2, US-3)
**Plan**: `kitty-specs/078-plan-snapshots-amendments/plan.md`

**Key Constraints**:
- Amendment controls only visible/enabled when plan_state == IN_PRODUCTION
- Follow existing planning_tab.py patterns
- Use CustomTkinter components
- Wire to plan_amendment_service functions
- Refresh UI after each amendment

**Reference Files**:
- `src/ui/planning_tab.py` - Main file to modify
- `src/ui/components/` - Example component patterns
- `src/services/plan_amendment_service.py` - Service to call (from WP03)

**UI Framework**: CustomTkinter (CTk)

---

## Subtasks & Detailed Guidance

### Subtask T016 – Add amendment controls panel frame

**Purpose**: Create the container frame for amendment controls in planning_tab.py.

**Steps**:
1. Open `src/ui/planning_tab.py`
2. Add new frame for amendment controls (after assembly status or at appropriate location)
3. Frame should be collapsible/expandable like other planning sections
4. Add visibility control based on plan_state
5. Include header with "Amendments" label and collapse toggle

**File**: `src/ui/planning_tab.py` (MODIFY, ~40 lines added)

**Implementation Pattern**:
```python
# In _create_widgets method, after existing panels:

# Amendment controls frame (F078)
self.amendment_frame = ctk.CTkFrame(self.scrollable_frame)
self.amendment_frame.pack(fill="x", padx=10, pady=5)

# Header
self.amendment_header = ctk.CTkFrame(self.amendment_frame)
self.amendment_header.pack(fill="x", padx=5, pady=5)

ctk.CTkLabel(
    self.amendment_header,
    text="Plan Amendments",
    font=ctk.CTkFont(size=14, weight="bold")
).pack(side="left", padx=5)

# Buttons container
self.amendment_buttons = ctk.CTkFrame(self.amendment_frame)
self.amendment_buttons.pack(fill="x", padx=5, pady=5)

# Add buttons (implemented in T017-T019)
self.drop_fg_btn = ctk.CTkButton(
    self.amendment_buttons,
    text="Drop FG",
    command=self._on_drop_fg_click,
    width=100
)
self.drop_fg_btn.pack(side="left", padx=5)

self.add_fg_btn = ctk.CTkButton(
    self.amendment_buttons,
    text="Add FG",
    command=self._on_add_fg_click,
    width=100
)
self.add_fg_btn.pack(side="left", padx=5)

self.modify_batch_btn = ctk.CTkButton(
    self.amendment_buttons,
    text="Modify Batch",
    command=self._on_modify_batch_click,
    width=100
)
self.modify_batch_btn.pack(side="left", padx=5)


def _update_amendment_controls_visibility(self):
    """Show/hide amendment controls based on plan state."""
    if self.selected_event and self.selected_event.plan_state == PlanState.IN_PRODUCTION:
        self.amendment_frame.pack(fill="x", padx=10, pady=5)
    else:
        self.amendment_frame.pack_forget()
```

**Key Points**:
- Call `_update_amendment_controls_visibility()` when event selection changes
- Call after state transitions
- Frame hidden when not IN_PRODUCTION

**Validation**:
- Panel visible only when plan_state == IN_PRODUCTION
- Panel hidden in DRAFT, LOCKED, COMPLETED states

---

### Subtask T017 – Implement DROP_FG dialog

**Purpose**: Create dialog for dropping a finished good with reason.

**Steps**:
1. Add `_on_drop_fg_click()` method
2. Create dialog showing current FGs in plan
3. Add dropdown/listbox for FG selection
4. Add text entry for reason (required)
5. Call `plan_amendment_service.drop_finished_good()` on confirm
6. Refresh UI and show success/error message

**File**: `src/ui/planning_tab.py` (MODIFY, ~50 lines added)

**Implementation**:
```python
def _on_drop_fg_click(self):
    """Handle Drop FG button click."""
    if not self.selected_event:
        return

    # Get current FGs in plan
    from src.services.database import session_scope
    from src.models import EventFinishedGood

    with session_scope() as session:
        event_fgs = session.query(EventFinishedGood).filter(
            EventFinishedGood.event_id == self.selected_event.id
        ).all()

        if not event_fgs:
            CTkMessagebox(
                title="No Finished Goods",
                message="No finished goods in plan to drop.",
                icon="info"
            )
            return

        fg_options = {
            f"{efg.finished_good.display_name} (qty: {efg.quantity})": efg.finished_good_id
            for efg in event_fgs
        }

    # Create dialog
    dialog = DropFGDialog(self, fg_options)
    result = dialog.get_result()

    if result:
        fg_id, reason = result
        try:
            from src.services import plan_amendment_service
            plan_amendment_service.drop_finished_good(
                self.selected_event.id,
                fg_id,
                reason
            )
            self._refresh_event_data()
            self._refresh_amendment_history()
            CTkMessagebox(
                title="Success",
                message="Finished good dropped successfully.",
                icon="check"
            )
        except Exception as e:
            CTkMessagebox(
                title="Error",
                message=str(e),
                icon="cancel"
            )


class DropFGDialog(ctk.CTkToplevel):
    """Dialog for dropping a finished good."""

    def __init__(self, parent, fg_options: dict):
        super().__init__(parent)
        self.title("Drop Finished Good")
        self.geometry("400x250")
        self.fg_options = fg_options
        self.result = None

        self.transient(parent)
        self.grab_set()

        # FG selection
        ctk.CTkLabel(self, text="Select Finished Good:").pack(pady=(10, 5))
        self.fg_var = ctk.StringVar()
        self.fg_dropdown = ctk.CTkOptionMenu(
            self,
            variable=self.fg_var,
            values=list(fg_options.keys()),
            width=350
        )
        self.fg_dropdown.pack(pady=5)

        # Reason entry
        ctk.CTkLabel(self, text="Reason (required):").pack(pady=(10, 5))
        self.reason_entry = ctk.CTkTextbox(self, height=60, width=350)
        self.reason_entry.pack(pady=5)

        # Buttons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Drop", command=self._on_confirm).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)

        self.wait_window()

    def _on_confirm(self):
        reason = self.reason_entry.get("1.0", "end-1c").strip()
        if not reason:
            CTkMessagebox(title="Error", message="Reason is required.", icon="cancel")
            return

        selected = self.fg_var.get()
        if not selected:
            CTkMessagebox(title="Error", message="Select a finished good.", icon="cancel")
            return

        self.result = (self.fg_options[selected], reason)
        self.destroy()

    def get_result(self):
        return self.result
```

**Validation**:
- Dialog shows only FGs currently in plan
- Reason is required
- Service is called on confirm
- UI refreshes after success

---

### Subtask T018 – Implement ADD_FG dialog

**Purpose**: Create dialog for adding a finished good with quantity and reason.

**Steps**:
1. Add `_on_add_fg_click()` method
2. Create dialog showing available FGs (not already in plan)
3. Add dropdown for FG selection
4. Add quantity entry (positive integer)
5. Add text entry for reason (required)
6. Call `plan_amendment_service.add_finished_good()` on confirm
7. Refresh UI

**File**: `src/ui/planning_tab.py` (MODIFY, ~60 lines added)

**Implementation Pattern** (similar to T017):
```python
def _on_add_fg_click(self):
    """Handle Add FG button click."""
    if not self.selected_event:
        return

    # Get FGs not already in plan
    from src.services.database import session_scope
    from src.models import FinishedGood, EventFinishedGood

    with session_scope() as session:
        # Get IDs already in plan
        existing_ids = set(
            efg.finished_good_id
            for efg in session.query(EventFinishedGood).filter(
                EventFinishedGood.event_id == self.selected_event.id
            ).all()
        )

        # Get available FGs
        available_fgs = session.query(FinishedGood).filter(
            ~FinishedGood.id.in_(existing_ids) if existing_ids else True
        ).all()

        if not available_fgs:
            CTkMessagebox(
                title="No Available FGs",
                message="All finished goods are already in the plan.",
                icon="info"
            )
            return

        fg_options = {fg.display_name: fg.id for fg in available_fgs}

    dialog = AddFGDialog(self, fg_options)
    result = dialog.get_result()

    if result:
        fg_id, quantity, reason = result
        try:
            from src.services import plan_amendment_service
            plan_amendment_service.add_finished_good(
                self.selected_event.id,
                fg_id,
                quantity,
                reason
            )
            self._refresh_event_data()
            self._refresh_amendment_history()
            CTkMessagebox(title="Success", message="Finished good added.", icon="check")
        except Exception as e:
            CTkMessagebox(title="Error", message=str(e), icon="cancel")


class AddFGDialog(ctk.CTkToplevel):
    """Dialog for adding a finished good."""
    # Similar structure to DropFGDialog
    # Add quantity entry field
    # Validate quantity is positive integer
```

**Validation**:
- Dialog shows only FGs not already in plan
- Quantity must be positive
- Reason is required
- Service is called on confirm

---

### Subtask T019 – Implement MODIFY_BATCH dialog

**Purpose**: Create dialog for modifying batch count with reason.

**Steps**:
1. Add `_on_modify_batch_click()` method
2. Create dialog showing recipes with batch decisions
3. Add dropdown for recipe selection
4. Show current batch count
5. Add entry for new batch count
6. Add text entry for reason (required)
7. Call `plan_amendment_service.modify_batch_decision()` on confirm

**File**: `src/ui/planning_tab.py` (MODIFY, ~60 lines added)

**Implementation Pattern**:
```python
def _on_modify_batch_click(self):
    """Handle Modify Batch button click."""
    if not self.selected_event:
        return

    from src.services.database import session_scope
    from src.models import BatchDecision

    with session_scope() as session:
        batch_decisions = session.query(BatchDecision).filter(
            BatchDecision.event_id == self.selected_event.id
        ).all()

        if not batch_decisions:
            CTkMessagebox(
                title="No Batch Decisions",
                message="No batch decisions to modify.",
                icon="info"
            )
            return

        # Format: "Recipe Name (current: X batches)"
        recipe_options = {
            f"{bd.recipe.name} (current: {bd.batches} batches)": (bd.recipe_id, bd.batches)
            for bd in batch_decisions
        }

    dialog = ModifyBatchDialog(self, recipe_options)
    result = dialog.get_result()

    if result:
        recipe_id, new_batches, reason = result
        try:
            from src.services import plan_amendment_service
            plan_amendment_service.modify_batch_decision(
                self.selected_event.id,
                recipe_id,
                new_batches,
                reason
            )
            self._refresh_event_data()
            self._refresh_amendment_history()
            CTkMessagebox(title="Success", message="Batch count modified.", icon="check")
        except Exception as e:
            CTkMessagebox(title="Error", message=str(e), icon="cancel")


class ModifyBatchDialog(ctk.CTkToplevel):
    """Dialog for modifying batch decision."""
    # Similar structure
    # Show current batch count
    # Entry for new batch count
    # Validate new_batches is non-negative integer
```

**Validation**:
- Dialog shows recipes with batch decisions
- Shows current batch count
- New batch count validated
- Reason required

---

### Subtask T020 – Add amendment history panel

**Purpose**: Display amendment history in chronological order.

**Steps**:
1. Add history frame below amendment buttons
2. Implement `_refresh_amendment_history()` method
3. Query amendments via `plan_amendment_service.get_amendments()`
4. Display each amendment with type, summary, reason, timestamp
5. Use scrollable frame for long history
6. Call refresh when event selected and after amendments

**File**: `src/ui/planning_tab.py` (MODIFY, ~60 lines added)

**Implementation**:
```python
# In _create_widgets, after amendment_buttons:

# Amendment history
self.amendment_history_frame = ctk.CTkScrollableFrame(
    self.amendment_frame,
    height=150
)
self.amendment_history_frame.pack(fill="x", padx=5, pady=5)

ctk.CTkLabel(
    self.amendment_history_frame,
    text="Amendment History",
    font=ctk.CTkFont(size=12, weight="bold")
).pack(anchor="w", padx=5, pady=5)

self.history_content = ctk.CTkFrame(self.amendment_history_frame)
self.history_content.pack(fill="x")


def _refresh_amendment_history(self):
    """Refresh the amendment history display."""
    # Clear existing
    for widget in self.history_content.winfo_children():
        widget.destroy()

    if not self.selected_event:
        return

    from src.services import plan_amendment_service
    amendments = plan_amendment_service.get_amendments(self.selected_event.id)

    if not amendments:
        ctk.CTkLabel(
            self.history_content,
            text="No amendments recorded.",
            text_color="gray"
        ).pack(anchor="w", padx=10, pady=5)
        return

    for amendment in amendments:
        frame = ctk.CTkFrame(self.history_content)
        frame.pack(fill="x", padx=5, pady=2)

        # Type and summary
        type_text = amendment.amendment_type.value.upper().replace("_", " ")
        summary = self._format_amendment_summary(amendment)

        ctk.CTkLabel(
            frame,
            text=f"[{type_text}] {summary}",
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=5)

        # Reason
        ctk.CTkLabel(
            frame,
            text=f"Reason: {amendment.reason}",
            text_color="gray"
        ).pack(anchor="w", padx=15)

        # Timestamp
        timestamp = amendment.created_at.strftime("%Y-%m-%d %H:%M")
        ctk.CTkLabel(
            frame,
            text=timestamp,
            text_color="gray",
            font=ctk.CTkFont(size=10)
        ).pack(anchor="w", padx=15)


def _format_amendment_summary(self, amendment) -> str:
    """Format amendment data as readable summary."""
    data = amendment.amendment_data
    if amendment.amendment_type.value == "drop_fg":
        return f"Dropped {data.get('fg_name', 'Unknown')} (was qty {data.get('original_quantity', '?')})"
    elif amendment.amendment_type.value == "add_fg":
        return f"Added {data.get('fg_name', 'Unknown')} (qty {data.get('quantity', '?')})"
    elif amendment.amendment_type.value == "modify_batch":
        return f"{data.get('recipe_name', 'Unknown')}: {data.get('old_batches', '?')} → {data.get('new_batches', '?')} batches"
    return "Unknown amendment"
```

**Validation**:
- History shows all amendments
- Chronological order (oldest first)
- Clear formatting for each type
- Updates after each amendment

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Dialog blocking main thread | Dialogs are modal, blocking is expected |
| Service not implemented | Can develop UI shell first; mock service calls |
| Long history list | Use scrollable frame with max height |
| UI refresh performance | Only refresh affected sections |

---

## Definition of Done Checklist

- [ ] Amendment controls panel exists in planning_tab.py
- [ ] Panel visible only when plan_state == IN_PRODUCTION
- [ ] DROP_FG dialog works with FG selection and reason
- [ ] ADD_FG dialog works with FG selection, quantity, and reason
- [ ] MODIFY_BATCH dialog works with recipe selection and batch count
- [ ] Amendment history panel displays all amendments
- [ ] UI refreshes after each amendment
- [ ] Application runs without errors

---

## Review Guidance

**Key Acceptance Checkpoints**:
1. Verify amendment panel only visible in IN_PRODUCTION state
2. Test each dialog type with valid inputs
3. Test validation (empty reason, invalid inputs)
4. Verify history updates after amendments
5. Run application: `python src/main.py`

---

## Activity Log

- 2026-01-28T03:25:47Z – system – lane=planned – Prompt created.
