---
work_package_id: WP02
title: Builder Dialog Shell & Navigation
lane: "for_review"
dependencies: [WP01]
base_branch: 097-finished-goods-builder-ui-WP01
base_commit: ced1f690e9cc5fc09d210bb528d1f81fdc5736ba
created_at: '2026-02-07T00:15:42.235969+00:00'
subtasks:
- T005
- T006
- T007
- T008
- T009
phase: Phase A - Foundation
assignee: ''
agent: "claude-opus"
shell_pid: "26279"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-06T23:51:59Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 -- Builder Dialog Shell & Navigation

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Create `FinishedGoodBuilderDialog` as a modal CTkToplevel dialog
- Dialog contains 3 AccordionStep instances: Food Selection, Materials, Review & Save
- Only one step expanded at a time (mutual exclusion)
- Sequential progression: Step 1 must complete before Step 2 unlocks
- Cancel shows confirmation dialog if changes exist
- Start Over clears all state and returns to Step 1
- Name entry field available in dialog header
- Unit tests pass for navigation state management

**Implementation command**: `spec-kitty implement WP02 --base WP01`

## Context & Constraints

- **Feature**: 097-finished-goods-builder-ui
- **Plan**: Design Decisions D-002 (CTkToplevel), D-004 (state management)
- **Depends on**: WP01 (AccordionStep widget in `src/ui/widgets/accordion_step.py`)
- **Dialog pattern**: Follow `src/ui/forms/finished_good_form.py` (CTkToplevel, transient, grab_set, wait_window, result)
- **Dialog size**: 700x750, min 600x600, resizable
- **Result pattern**: `self.result = None` on cancel, `self.result = {...}` on save
- **New directory**: `src/ui/builders/` (create `__init__.py`)

## Subtasks & Detailed Guidance

### Subtask T005 -- Create FinishedGoodBuilderDialog class as CTkToplevel with modal behavior

- **Purpose**: Establish the dialog window with proper modal behavior matching existing patterns.

- **Steps**:
  1. Create directory `src/ui/builders/` with `__init__.py`
  2. Create `src/ui/builders/finished_good_builder.py`
  3. Define `FinishedGoodBuilderDialog(ctk.CTkToplevel)`:
     ```python
     def __init__(self, parent, finished_good=None):
         super().__init__(parent)
         self.title("Create Finished Good" if not finished_good else f"Edit: {finished_good.display_name}")
         self.geometry("700x750")
         self.minsize(600, 600)
         self.resizable(True, True)
         self.transient(parent)
         self.grab_set()

         self.result = None
         self._finished_good = finished_good  # None = create mode
         self._is_edit_mode = finished_good is not None
         self._has_changes = False  # Track unsaved changes

         self._create_widgets()
         self._center_on_parent(parent)
     ```
  4. Implement `_center_on_parent(parent)` following pattern from `finished_good_form.py` lines 250-261
  5. Implement `get_result()` method: `self.wait_window(); return self.result`
  6. Handle window close (WM_DELETE_WINDOW protocol) to call cancel logic

- **Files**: `src/ui/builders/__init__.py` (new, empty), `src/ui/builders/finished_good_builder.py` (new)

### Subtask T006 -- Wire up 3 AccordionStep instances in scrollable container

- **Purpose**: Create the visual layout with three accordion steps inside a scrollable area.

- **Steps**:
  1. In `_create_widgets()`, create main layout:
     - Top: Name entry frame (always visible, not part of accordion)
     - Middle: CTkScrollableFrame containing 3 AccordionStep instances
     - Bottom: Button frame (Cancel, outside accordion)
  2. Create name entry:
     ```python
     self.name_frame = ctk.CTkFrame(self)
     name_label = ctk.CTkLabel(self.name_frame, text="Name:", font=ctk.CTkFont(weight="bold"))
     self.name_entry = ctk.CTkEntry(self.name_frame, placeholder_text="Enter finished good name...")
     ```
  3. Create 3 AccordionStep instances:
     ```python
     self.step1 = AccordionStep(self.scroll_frame, step_number=1, title="Food Selection", on_change_click=self._on_step_change)
     self.step2 = AccordionStep(self.scroll_frame, step_number=2, title="Materials", on_change_click=self._on_step_change)
     self.step3 = AccordionStep(self.scroll_frame, step_number=3, title="Review & Save", on_change_click=self._on_step_change)
     ```
  4. Pack all three steps in order
  5. Set initial states: step1=active, step2=locked, step3=locked

- **Files**: `src/ui/builders/finished_good_builder.py`

- **Notes**:
  - Name entry is OUTSIDE the accordion — always visible at top of dialog
  - The content frames of each step will be populated by later WPs (WP03, WP04, WP05)
  - For now, add placeholder labels in each content frame: "Food selection coming in WP03", etc.

### Subtask T007 -- Implement step navigation controller

- **Purpose**: Enforce mutual exclusion (one step expanded at a time) and sequential progression.

- **Steps**:
  1. Implement `_on_step_change(step_number: int)`:
     - This is called when user clicks "Change" on a completed step
     - Collapse all steps
     - Expand the requested step (set to active)
  2. Implement `_advance_to_step(step_number: int)`:
     - Called when user clicks "Continue" in a step
     - Mark current step as completed with summary
     - Unlock next step and expand it
  3. Implement `_collapse_all_steps()`:
     - Call `collapse()` on all 3 steps
  4. Implement `_get_current_step() -> int`:
     - Return the step number that is currently active (expanded)
  5. Track step completion status:
     ```python
     self._step_completed = {1: False, 2: False, 3: False}
     ```
  6. Unlock rules:
     - Step 2 unlocked when step 1 completed
     - Step 3 unlocked when step 2 completed (or skipped)

- **Files**: `src/ui/builders/finished_good_builder.py`

- **Notes**:
  - Navigation is forward-sequential for progression, but "Change" allows backward navigation
  - When going back to a previous step, later steps remain completed (selections preserved)
  - The AccordionStep widget doesn't enforce this — the builder does

### Subtask T008 -- Implement dialog-level controls (name entry, Cancel with confirmation, Start Over)

- **Purpose**: Provide dialog-level actions that operate across all steps.

- **Steps**:
  1. Implement Cancel button in bottom button frame:
     ```python
     cancel_btn = ctk.CTkButton(self.button_frame, text="Cancel", fg_color="gray", command=self._on_cancel)
     ```
  2. Implement `_on_cancel()`:
     - If `self._has_changes`: Show confirmation dialog "Discard unsaved changes?" with "Discard" / "Keep Editing"
     - If no changes or user confirms discard: `self.result = None; self.destroy()`
  3. Implement Start Over button (visible in review step or as a dialog-level option):
     ```python
     start_over_btn = ctk.CTkButton(self.button_frame, text="Start Over", fg_color="gray", command=self._on_start_over)
     ```
  4. Implement `_on_start_over()`:
     - Clear all selection state (food_selections, material_selections)
     - Reset all steps to initial state (step1=active, step2=locked, step3=locked)
     - Clear name entry
     - Set `self._has_changes = False`
  5. Name entry change tracking:
     - Bind `<KeyRelease>` on name_entry to set `self._has_changes = True`

- **Files**: `src/ui/builders/finished_good_builder.py`

- **Notes**:
  - Use `show_confirmation()` from `src/ui/widgets/dialogs.py` for the discard confirmation
  - Start Over is a stronger action than Cancel — it resets everything but keeps the dialog open

### Subtask T009 -- Write unit tests for dialog shell navigation and state management

- **Purpose**: Verify dialog construction, navigation logic, and cancel/start-over behavior.

- **Steps**:
  1. Create `src/tests/test_finished_good_builder.py`
  2. Write tests:
     - `test_dialog_creates_in_create_mode`: Dialog opens with step1 active, step2/3 locked
     - `test_advance_to_step_2`: After step 1 completes, step 2 becomes active
     - `test_advance_to_step_3`: After step 2 completes, step 3 becomes active
     - `test_mutual_exclusion`: Only one step expanded at a time
     - `test_change_button_goes_back`: Click "Change" on step 1 from step 3, step 1 expands
     - `test_start_over_resets_all`: Start Over clears state and re-expands step 1
     - `test_cancel_with_no_changes_closes`: Cancel without changes closes immediately
     - `test_cancel_with_changes_prompts`: Cancel with changes shows confirmation (mock dialog)
  3. Mock CustomTkinter widgets as needed for headless testing

- **Files**: `src/tests/test_finished_good_builder.py` (new, ~150 lines)

- **Notes**:
  - Testing CTkToplevel requires root window; use same pattern as WP01 tests
  - May need to mock `show_confirmation` to test cancel-with-changes flow

## Risks & Mitigations

- **Risk**: CTkScrollableFrame may not resize properly with accordion steps expanding/collapsing. **Mitigation**: Test with varying step content sizes; may need to call `update_idletasks()` after state changes.
- **Risk**: `grab_set()` may interfere with confirmation dialog. **Mitigation**: Temporarily release grab when showing confirmation, re-grab after.

## Definition of Done Checklist

- [ ] `src/ui/builders/` directory created with `__init__.py`
- [ ] `FinishedGoodBuilderDialog` opens as modal with correct title (create vs edit)
- [ ] 3 AccordionStep instances displayed with correct initial states
- [ ] Step navigation: mutual exclusion, sequential progression, "Change" to go back
- [ ] Name entry field visible and functional at top of dialog
- [ ] Cancel shows confirmation when changes exist
- [ ] Start Over resets all state
- [ ] Unit tests pass
- [ ] No linting errors

## Review Guidance

- Verify dialog centers on parent correctly
- Verify only one accordion step is expanded at any time
- Verify "Change" button navigates back without losing state
- Verify Cancel confirmation appears only when changes have been made
- Test Start Over from Step 3 — all steps should reset

## Activity Log

- 2026-02-06T23:51:59Z -- system -- lane=planned -- Prompt created.
- 2026-02-07T00:15:42Z – claude-opus – shell_pid=26279 – lane=doing – Assigned agent via workflow command
- 2026-02-07T00:19:18Z – claude-opus – shell_pid=26279 – lane=for_review – Ready for review: Builder dialog shell with 3 accordion steps, navigation controller, Cancel/Start Over, 15 passing tests
