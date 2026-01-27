---
work_package_id: WP03
title: UI Integration
lane: "done"
dependencies:
- WP01
- WP02
base_branch: 077-plan-state-management-WP02
base_commit: a6cfd406f35e89c0d0f113dbe562f6cfcab55113
created_at: '2026-01-27T22:44:48.031371+00:00'
subtasks:
- T011
- T012
- T013
- T014
- T015
phase: Phase 3 - UI Integration
assignee: ''
agent: "claude"
shell_pid: "56995"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-01-28T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – UI Integration

## Implementation Command

```bash
spec-kitty implement WP03 --base WP02
```

## Objectives & Success Criteria

Add state display and transition controls to the Planning Tab UI.

**Success Criteria**:
- [ ] Current plan state displayed prominently when event selected
- [ ] "Lock Plan" button visible and functional for DRAFT events
- [ ] "Start Production" button visible and functional for LOCKED events
- [ ] "Complete Production" button visible and functional for IN_PRODUCTION events
- [ ] No transition buttons shown for COMPLETED events
- [ ] Buttons disabled for invalid transitions
- [ ] State updates immediately after successful transition
- [ ] Error messages shown for failed transitions

## Context & Constraints

**Reference Documents**:
- `kitty-specs/077-plan-state-management/spec.md` - User Story 3, FR-009, FR-010
- `kitty-specs/077-plan-state-management/plan.md` - D4 (UI state display)

**UI State Controls** (from plan.md):

| Current State | Visible Button | Action |
|---------------|----------------|--------|
| DRAFT | "Lock Plan" | Calls lock_plan() |
| LOCKED | "Start Production" | Calls start_production() |
| IN_PRODUCTION | "Complete Production" | Calls complete_production() |
| COMPLETED | (none) | Read-only |

**Current Planning Tab Layout** (from F076):
```
Row 0: Action buttons
Row 1: Data table (event list)
Row 2: Recipe selection frame
Row 3: FG selection frame
Row 4: Batch options frame
Row 5: Shopping summary frame
Row 6: Assembly status frame
Row 7: Status bar
```

**Target Layout** (add state controls before shopping summary):
```
Row 0: Action buttons
Row 1: Data table (event list)
Row 2: Recipe selection frame
Row 3: FG selection frame
Row 4: Batch options frame
Row 5: Plan state controls frame (NEW)
Row 6: Shopping summary frame (shifted)
Row 7: Assembly status frame (shifted)
Row 8: Status bar (shifted)
```

## Subtasks & Detailed Guidance

### Subtask T011 – Add State Indicator Frame

**Purpose**: Create a frame that displays the current plan state prominently.

**Steps**:
1. Open `src/ui/planning_tab.py`
2. Add imports at top:
```python
from src.services.plan_state_service import (
    get_plan_state,
    lock_plan,
    start_production,
    complete_production,
)
from src.models.event import PlanState
```

3. Update grid row configuration in `__init__` (add row 5 for state controls, shift others):
```python
        # Configure grid (update row weights for F077)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Action buttons
        self.grid_rowconfigure(1, weight=1)  # Data table
        self.grid_rowconfigure(2, weight=0)  # Recipe selection frame
        self.grid_rowconfigure(3, weight=0)  # FG selection frame
        self.grid_rowconfigure(4, weight=0)  # Batch options frame
        self.grid_rowconfigure(5, weight=0)  # Plan state controls (F077)
        self.grid_rowconfigure(6, weight=0)  # Shopping summary frame
        self.grid_rowconfigure(7, weight=0)  # Assembly status frame
        self.grid_rowconfigure(8, weight=0)  # Status bar
```

4. Add creation method for state controls frame:
```python
    def _create_plan_state_frame(self) -> None:
        """Create the plan state controls frame (F077)."""
        self._plan_state_frame = ctk.CTkFrame(self)

        # State label (shows current state)
        self._state_label = ctk.CTkLabel(
            self._plan_state_frame,
            text="Plan State: --",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self._state_label.pack(side="left", padx=(10, 20), pady=8)

        # Transition buttons (created but visibility controlled by state)
        self._lock_btn = ctk.CTkButton(
            self._plan_state_frame,
            text="Lock Plan",
            command=self._on_lock_plan,
            width=120,
        )
        self._lock_btn.pack(side="left", padx=5, pady=8)

        self._start_production_btn = ctk.CTkButton(
            self._plan_state_frame,
            text="Start Production",
            command=self._on_start_production,
            width=140,
        )
        self._start_production_btn.pack(side="left", padx=5, pady=8)

        self._complete_btn = ctk.CTkButton(
            self._plan_state_frame,
            text="Complete Production",
            command=self._on_complete_production,
            width=160,
        )
        self._complete_btn.pack(side="left", padx=5, pady=8)

        # Frame starts hidden
```

5. Call creation method in `__init__` after batch options frame:
```python
        self._create_batch_options_frame()
        self._create_plan_state_frame()  # F077
        self._create_shopping_summary_frame()
```

6. Update `_layout_widgets` to shift rows for shopping summary, assembly status, and status bar:
```python
        # Shopping summary at row 6 (shifted for F077)
        # Assembly status at row 7 (shifted for F077)
        # Status bar at row 8 (shifted for F077)
```

**Files**: `src/ui/planning_tab.py`

**Validation**:
- [ ] Plan state frame created without errors
- [ ] State label shows "Plan State: --" initially
- [ ] All three buttons created (visibility controlled separately)

---

### Subtask T012 – Add Transition Buttons

**Purpose**: Create the buttons for state transitions with proper styling.

Note: Buttons were created in T011. This subtask ensures proper styling and tooltips.

**Steps**:
1. Add visual feedback for button states:

```python
    def _update_plan_state_buttons(self, state: PlanState) -> None:
        """Update button visibility and state based on current plan state.

        Args:
            state: Current PlanState of the selected event
        """
        # Hide all buttons first
        self._lock_btn.pack_forget()
        self._start_production_btn.pack_forget()
        self._complete_btn.pack_forget()

        # Update state label with color coding
        state_colors = {
            PlanState.DRAFT: ("#2d5a27", "Draft"),  # Green
            PlanState.LOCKED: ("#5a4827", "Locked"),  # Orange/Yellow
            PlanState.IN_PRODUCTION: ("#27455a", "In Production"),  # Blue
            PlanState.COMPLETED: ("#5a2727", "Completed"),  # Red
        }
        color, display_name = state_colors.get(state, ("#333333", str(state)))
        self._state_label.configure(text=f"Plan State: {display_name}")

        # Show appropriate button based on state
        if state == PlanState.DRAFT:
            self._lock_btn.pack(side="left", padx=5, pady=8)
        elif state == PlanState.LOCKED:
            self._start_production_btn.pack(side="left", padx=5, pady=8)
        elif state == PlanState.IN_PRODUCTION:
            self._complete_btn.pack(side="left", padx=5, pady=8)
        # COMPLETED: no buttons shown
```

**Files**: `src/ui/planning_tab.py`

**Validation**:
- [ ] Only one button visible at a time based on state
- [ ] State label updates with human-readable state name
- [ ] COMPLETED state shows no buttons

---

### Subtask T013 – Wire Button Handlers

**Purpose**: Connect button clicks to plan_state_service calls.

**Steps**:
1. Add handler methods:

```python
    def _on_lock_plan(self) -> None:
        """Handle Lock Plan button click."""
        if self._selected_event_id is None:
            return

        try:
            event = lock_plan(self._selected_event_id)
            self._update_status(f"Plan locked successfully")
            self._refresh_plan_state_display()
            # Refresh other panels that may be affected
            self._update_shopping_summary()
            self._update_assembly_status()
        except PlanStateError as e:
            self._update_status(f"Cannot lock plan: {e}")
            messagebox.showerror("Lock Failed", str(e))
        except Exception as e:
            self._update_status(f"Error: {e}")
            messagebox.showerror("Error", f"Failed to lock plan: {e}")

    def _on_start_production(self) -> None:
        """Handle Start Production button click."""
        if self._selected_event_id is None:
            return

        try:
            event = start_production(self._selected_event_id)
            self._update_status(f"Production started")
            self._refresh_plan_state_display()
            self._update_shopping_summary()
            self._update_assembly_status()
        except PlanStateError as e:
            self._update_status(f"Cannot start production: {e}")
            messagebox.showerror("Start Production Failed", str(e))
        except Exception as e:
            self._update_status(f"Error: {e}")
            messagebox.showerror("Error", f"Failed to start production: {e}")

    def _on_complete_production(self) -> None:
        """Handle Complete Production button click."""
        if self._selected_event_id is None:
            return

        # Confirm completion (this is a significant action)
        if not messagebox.askyesno(
            "Complete Production",
            "Are you sure you want to mark production as complete?\n\n"
            "This will make the plan read-only. No further changes will be allowed."
        ):
            return

        try:
            event = complete_production(self._selected_event_id)
            self._update_status(f"Production completed")
            self._refresh_plan_state_display()
            self._update_shopping_summary()
            self._update_assembly_status()
        except PlanStateError as e:
            self._update_status(f"Cannot complete production: {e}")
            messagebox.showerror("Complete Production Failed", str(e))
        except Exception as e:
            self._update_status(f"Error: {e}")
            messagebox.showerror("Error", f"Failed to complete production: {e}")
```

2. Add helper method to refresh state display:

```python
    def _refresh_plan_state_display(self) -> None:
        """Refresh the plan state display after a transition."""
        if self._selected_event_id is None:
            return

        try:
            state = get_plan_state(self._selected_event_id)
            self._update_plan_state_buttons(state)
        except Exception as e:
            print(f"Warning: Could not refresh plan state: {e}")
```

**Files**: `src/ui/planning_tab.py`

**Validation**:
- [ ] Lock Plan button calls lock_plan() and updates display
- [ ] Start Production button calls start_production() and updates display
- [ ] Complete Production shows confirmation dialog
- [ ] Errors display in message box
- [ ] Status bar updates on success/failure

---

### Subtask T014 – Implement Button Enable/Disable Logic

**Purpose**: Ensure buttons are correctly enabled/disabled based on state.

Note: The current design shows/hides buttons rather than enable/disable. This subtask verifies that logic is working correctly.

**Steps**:
1. Verify the `_update_plan_state_buttons()` method correctly shows only the valid button for each state.

2. Add handling for edge cases:

```python
    def _update_plan_state_buttons(self, state: PlanState) -> None:
        """Update button visibility and state based on current plan state."""
        # ... existing code ...

        # Disable all buttons if state is None or invalid
        if state is None:
            self._state_label.configure(text="Plan State: --")
            self._lock_btn.pack_forget()
            self._start_production_btn.pack_forget()
            self._complete_btn.pack_forget()
            return

        # ... rest of existing code ...
```

**Files**: `src/ui/planning_tab.py`

**Validation**:
- [ ] DRAFT shows only "Lock Plan" button
- [ ] LOCKED shows only "Start Production" button
- [ ] IN_PRODUCTION shows only "Complete Production" button
- [ ] COMPLETED shows no buttons
- [ ] Invalid/None state shows no buttons

---

### Subtask T015 – Show/Hide State Controls Based on Event Selection

**Purpose**: Integrate state controls with event selection flow.

**Steps**:
1. Add show/hide methods:

```python
    def _show_plan_state_controls(self) -> None:
        """Show and update plan state controls frame."""
        if self._selected_event_id is None:
            return

        try:
            state = get_plan_state(self._selected_event_id)
            self._update_plan_state_buttons(state)
            self._plan_state_frame.grid(
                row=5, column=0, sticky="ew",
                padx=PADDING_LARGE, pady=PADDING_MEDIUM
            )
        except Exception as e:
            print(f"Warning: Could not show plan state controls: {e}")

    def _hide_plan_state_controls(self) -> None:
        """Hide the plan state controls frame."""
        self._plan_state_frame.grid_forget()
        self._state_label.configure(text="Plan State: --")
```

2. Update `_on_row_select()` to show/hide state controls:

```python
    def _on_row_select(self, event: Optional[Event]) -> None:
        """Handle row selection."""
        # ... existing code ...

        if self.selected_event:
            self._update_status(f"Selected: {self.selected_event.name}")
            self._selected_event_id = self.selected_event.id
            self._show_recipe_selection(self.selected_event.id)
            self._show_fg_selection(self.selected_event.id)
            self._show_batch_options(self.selected_event.id)
            self._show_plan_state_controls()  # F077
            self._show_shopping_summary()
            self._show_assembly_status()
        else:
            self._update_status("Ready")
            self._selected_event_id = None
            self._hide_recipe_selection()
            self._hide_fg_selection()
            self._hide_batch_options()
            self._hide_plan_state_controls()  # F077
            self._hide_shopping_summary()
            self._hide_assembly_status()
```

3. Update `refresh()` to hide state controls:

```python
    def refresh(self) -> None:
        """Refresh the event list from database."""
        # ... existing code ...

        # Clear selection and hide all panels
        self.selected_event = None
        self._selected_event_id = None
        self._hide_recipe_selection()
        self._hide_fg_selection()
        self._hide_batch_options()
        self._hide_plan_state_controls()  # F077
        self._hide_shopping_summary()
        self._hide_assembly_status()
        self._update_button_states()
```

**Files**: `src/ui/planning_tab.py`

**Validation**:
- [ ] Selecting an event shows plan state controls
- [ ] Deselecting event hides plan state controls
- [ ] Refresh hides plan state controls
- [ ] State controls appear at correct grid position (row 5)
- [ ] Other panels (shopping, assembly) shifted to correct rows

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Grid row conflicts | Double-check row numbers; shift all downstream rows |
| State sync issues | Always re-query state after transitions |
| UI freeze on errors | Wrap all service calls in try/except |

## Definition of Done Checklist

- [ ] Plan state frame created and positioned at row 5
- [ ] State label shows current state when event selected
- [ ] Lock Plan button works for DRAFT events
- [ ] Start Production button works for LOCKED events
- [ ] Complete Production button works (with confirmation) for IN_PRODUCTION events
- [ ] No buttons shown for COMPLETED events
- [ ] Frame hides when no event selected
- [ ] Frame shows when event selected
- [ ] Errors display user-friendly messages
- [ ] Shopping/Assembly panels still work (shifted rows)
- [ ] No linting errors

## Review Guidance

- Test full state transition flow via UI
- Verify grid layout looks correct
- Check that shopping/assembly panels still work after row shift
- Verify confirmation dialog appears for Complete Production
- Test error handling by attempting invalid transitions

## Activity Log

- 2026-01-28T00:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-27T22:50:12Z – claude – shell_pid=56995 – lane=for_review – Implementation complete: Plan state UI controls added
- 2026-01-27T22:52:19Z – claude – shell_pid=56995 – lane=done – Review passed: UI controls implemented, all subtasks complete
