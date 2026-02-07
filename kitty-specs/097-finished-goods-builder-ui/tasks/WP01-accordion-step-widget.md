---
work_package_id: WP01
title: AccordionStep Widget
lane: "doing"
dependencies: []
base_branch: main
base_commit: e16f536c3b9ac0cbab64ca424daa36776536ed63
created_at: '2026-02-07T00:00:07.731463+00:00'
subtasks:
- T001
- T002
- T003
- T004
phase: Phase A - Foundation
assignee: ''
agent: "claude-opus"
shell_pid: "23922"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-06T23:51:59Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 -- AccordionStep Widget

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Create a reusable `AccordionStep` widget for multi-step wizard UIs
- Widget supports 3 states: `locked`, `active`, `completed`
- Header displays step number, title, status icon, summary text, and "Change" button
- Content frame shows/hides cleanly using pack/pack_forget
- Widget emits callbacks when user clicks to expand (via "Change" button)
- All state transitions work correctly and visual indicators update
- Unit tests pass for all state transitions

**Implementation command**: `spec-kitty implement WP01`

## Context & Constraints

- **Feature**: 097-finished-goods-builder-ui (Finished Goods Builder UI)
- **Plan**: `kitty-specs/097-finished-goods-builder-ui/plan.md` (Design Decision D-001)
- **Constitution**: `.kittify/memory/constitution.md` (Principle V: Layered Architecture)
- **Pattern reference**: `src/ui/dialogs/add_purchase_dialog.py` lines 531-560 (pack/pack_forget toggle)
- **No existing accordion widget** in the codebase — this is the first one
- CustomTkinter provides CTkFrame, CTkLabel, CTkButton — use these as building blocks
- Use Unicode characters for status icons (no image assets): lock, checkmark, right-arrow
- Widget must work with the existing dark/light theme system

## Subtasks & Detailed Guidance

### Subtask T001 -- Create AccordionStep widget class with header and content frames

- **Purpose**: Establish the widget's class structure, constructor API, and frame hierarchy.

- **Steps**:
  1. Create new file `src/ui/widgets/accordion_step.py`
  2. Define `AccordionStep(ctk.CTkFrame)` class with constructor:
     ```python
     def __init__(
         self,
         parent,
         step_number: int,        # 1, 2, 3
         title: str,              # "Food Selection", "Materials", "Review & Save"
         on_change_click=None,    # Callback when "Change" button clicked
         **kwargs
     ):
     ```
  3. Create header frame (`self.header_frame`) as a CTkFrame containing:
     - Step number label (e.g., "1")
     - Title label (e.g., "Food Selection")
     - Status icon label (will be updated by state changes)
     - Summary label (collapsed summary text, initially empty)
     - "Change" button (initially hidden, shown only in `completed` state)
  4. Create content frame (`self.content_frame`) as a CTkFrame — this is where step-specific widgets will be added by the caller
  5. Pack header frame at top; content frame below (initially visible for `active`, hidden for others)
  6. Expose `self.content_frame` publicly so the builder dialog can add child widgets to it

- **Files**: `src/ui/widgets/accordion_step.py` (new, ~150 lines)

- **Notes**:
  - Header layout: Use pack with `side="left"` for horizontal arrangement
  - Step number in a small fixed-width label (e.g., width=30, bold font)
  - Title in a label with weight="bold", font size 14
  - Status icon in a small label (width=25) to the right
  - Summary label takes remaining space (pack with `expand=True`, `fill="x"`)
  - "Change" button on far right (pack with `side="right"`)

### Subtask T002 -- Implement state machine (locked, active, completed) with visual indicators

- **Purpose**: Enable the widget to visually represent its current state and transition between states.

- **Steps**:
  1. Define state enum or string constants: `"locked"`, `"active"`, `"completed"`
  2. Store current state in `self._state` (default: `"locked"`)
  3. Implement `set_state(state: str)` method that:
     - Updates `self._state`
     - Calls `_update_visual_state()` to refresh all visual elements
  4. Implement `_update_visual_state()`:
     - **locked**: Header greyed out (fg_color dim), status icon = lock char, content hidden, "Change" button hidden, header NOT clickable
     - **active**: Header highlighted (fg_color accent/blue), status icon = right-arrow char, content VISIBLE, "Change" button hidden
     - **completed**: Header normal color, status icon = checkmark char, content HIDDEN, "Change" button VISIBLE, summary label shows text
  5. Implement `set_summary(text: str)` to update the summary label text (e.g., "3 items selected")
  6. Implement read-only property `state` to return current state

- **Files**: `src/ui/widgets/accordion_step.py`

- **Notes**:
  - Unicode icons: Lock = "\U0001F512" or simpler "🔒", Checkmark = "\u2713" or "✓", Arrow = "\u25B6" or "▶"
  - Test with both light and dark themes to ensure readability
  - Use `configure()` to update colors/text dynamically
  - Locked state should make header look disabled but not be interactive

### Subtask T003 -- Implement content show/hide via pack/pack_forget with "Change" button callback

- **Purpose**: Enable expanding/collapsing the content area and handling user interaction to revisit completed steps.

- **Steps**:
  1. Implement `expand()` method:
     - Pack content frame after header: `self.content_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))`
     - Set state to `"active"`
  2. Implement `collapse()` method:
     - Hide content frame: `self.content_frame.pack_forget()`
     - State remains whatever it was (caller controls whether it becomes `"completed"` or stays `"locked"`)
  3. Wire "Change" button to `on_change_click` callback:
     - When clicked, invoke `self._on_change_click(self.step_number)` so the parent dialog knows which step wants to re-expand
  4. Implement `is_expanded` read-only property (returns True if content frame is currently packed)
  5. Implement `mark_completed(summary: str)` convenience method:
     - Calls `collapse()`, `set_state("completed")`, `set_summary(summary)`

- **Files**: `src/ui/widgets/accordion_step.py`

- **Notes**:
  - The parent dialog (builder) is responsible for mutual exclusion — when one step expands, others must collapse
  - The AccordionStep itself does NOT enforce mutual exclusion; it just provides expand/collapse/state API
  - The "Change" button is only clickable in `completed` state

### Subtask T004 -- Write unit tests for AccordionStep state transitions and rendering

- **Purpose**: Verify all state transitions, visual updates, and expand/collapse behavior.

- **Steps**:
  1. Create new test file `src/tests/test_accordion_step.py`
  2. Write tests:
     - `test_initial_state_is_locked`: Verify default state is locked, content not visible
     - `test_set_state_active`: Verify active state shows content, hides Change button
     - `test_set_state_completed`: Verify completed state hides content, shows Change button and summary
     - `test_set_state_locked`: Verify locked state hides content and Change button
     - `test_expand_shows_content`: Verify expand() makes content visible
     - `test_collapse_hides_content`: Verify collapse() hides content
     - `test_mark_completed_convenience`: Verify mark_completed() sets state, summary, and collapses
     - `test_set_summary_updates_label`: Verify summary text appears in header
     - `test_change_button_callback`: Verify Change button fires on_change_click with step_number
  3. Use `ctk.CTk()` as root window for tests (required for CustomTkinter widgets)

- **Files**: `src/tests/test_accordion_step.py` (new, ~120 lines)

- **Notes**:
  - CustomTkinter tests require a root window: `root = ctk.CTk()` then `root.withdraw()`
  - Check widget state via configure/cget methods or inspect internal attributes
  - For callback testing, use a mock or flag variable
  - Clean up root window in teardown: `root.destroy()`

## Risks & Mitigations

- **Risk**: CustomTkinter widget rendering may behave differently across platforms. **Mitigation**: Test on macOS; document any platform-specific quirks.
- **Risk**: pack/pack_forget may cause layout shifts in the parent. **Mitigation**: Use consistent padx/pady and test with varying content sizes.

## Definition of Done Checklist

- [ ] `src/ui/widgets/accordion_step.py` created with AccordionStep class
- [ ] Three states (locked, active, completed) work with correct visual indicators
- [ ] Expand/collapse works via pack/pack_forget
- [ ] "Change" button fires callback in completed state
- [ ] `mark_completed(summary)` convenience method works
- [ ] Unit tests pass (`src/tests/test_accordion_step.py`)
- [ ] No linting errors

## Review Guidance

- Verify all 3 states have distinct visual appearance
- Check that expand/collapse doesn't leak content (content frame fully hidden when collapsed)
- Verify "Change" button only appears in completed state
- Confirm widget works as a child of CTkScrollableFrame (this is how it'll be used in the builder)

## Activity Log

- 2026-02-06T23:51:59Z -- system -- lane=planned -- Prompt created.
- 2026-02-07T00:00:08Z – claude-opus – shell_pid=23922 – lane=doing – Assigned agent via workflow command
