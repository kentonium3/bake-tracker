---
work_package_id: "WP02"
subtasks:
  - "T007"
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
  - "T013"
title: "Main Window & Mode Navigation"
phase: "Phase 0 - Setup"
lane: "done"
assignee: "claude"
agent: "claude-reviewer"
shell_pid: "41347"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-05"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Main Window & Mode Navigation

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Implement mode bar, ModeManager, and keyboard shortcuts in main_window.py.

**Success Criteria**:
- Application launches with horizontal mode bar showing 5 buttons
- Clicking mode buttons switches visible content
- Ctrl+1 through Ctrl+5 keyboard shortcuts work (FR-003)
- Tab selection is preserved when switching between modes (FR-004)
- Application defaults to OBSERVE mode on launch (FR-005)
- Active mode button is visually highlighted (FR-002)

## Context & Constraints

**Prerequisites**: WP01 (Base Classes) must be complete.

**Reference Documents**:
- `kitty-specs/038-ui-mode-restructure/spec.md` - FR-001 through FR-005
- `kitty-specs/038-ui-mode-restructure/research.md` - RQ-4, RQ-6 (shortcuts, state)
- `src/ui/main_window.py` - Existing implementation to modify

**Constraints**:
- Preserve existing application functionality during transition
- Mode bar should be prominent and easy to access
- Keyboard shortcuts must not interfere with text entry

## Subtasks & Detailed Guidance

### Subtask T007 - Create ModeManager class

**Purpose**: Coordinate mode switching and state preservation.

**Steps**:
1. Create ModeManager class (can be in main_window.py or separate file)
2. Implement mode registration and switching logic
3. Implement tab state preservation per mode

**Files**: `src/ui/main_window.py` or `src/ui/mode_manager.py`

**Implementation**:
```python
class ModeManager:
    def __init__(self):
        self.current_mode: str = "OBSERVE"
        self.modes: Dict[str, BaseMode] = {}
        self.mode_tab_state: Dict[str, int] = {
            "CATALOG": 0,
            "PLAN": 0,
            "SHOP": 0,
            "PRODUCE": 0,
            "OBSERVE": 0,
        }

    def register_mode(self, name: str, mode: BaseMode) -> None: ...
    def switch_mode(self, mode_name: str) -> None: ...
    def get_current_mode(self) -> BaseMode: ...
    def save_tab_state(self) -> None: ...
    def restore_tab_state(self) -> None: ...
```

**Parallel?**: No - foundational for other subtasks.

### Subtask T008 - Create mode bar with 5 mode buttons

**Purpose**: Provide visual navigation for mode switching (FR-001).

**Steps**:
1. Create horizontal CTkFrame for mode bar
2. Add 5 CTkButton widgets (CATALOG, PLAN, SHOP, PRODUCE, OBSERVE)
3. Position mode bar prominently (top of window)
4. Connect buttons to mode switching

**Files**: `src/ui/main_window.py`

**UI Layout**:
```
┌─────────────────────────────────────────────────────────┐
│ [CATALOG] [PLAN] [SHOP] [PRODUCE] [OBSERVE]  │ Mode Bar
├─────────────────────────────────────────────────────────┤
│                                                         │
│                   Mode Content Area                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Button Configuration**:
- Equal width buttons
- Clear labels
- Hover effect for feedback

**Parallel?**: No - depends on T007.

### Subtask T009 - Implement mode switching logic

**Purpose**: Show/hide mode frames when switching modes.

**Steps**:
1. Implement show/hide logic using pack_forget/pack or grid_remove/grid
2. Save current mode's tab state before switching
3. Restore target mode's tab state after switching
4. Trigger dashboard refresh on mode activation

**Files**: `src/ui/main_window.py`

**Implementation Pattern**:
```python
def switch_mode(self, target_mode: str):
    if self.current_mode == target_mode:
        return

    # Save current state
    current = self.modes[self.current_mode]
    current.deactivate()
    self.mode_tab_state[self.current_mode] = current.get_current_tab_index()
    current.pack_forget()  # or grid_remove()

    # Activate target
    target = self.modes[target_mode]
    target.pack(fill="both", expand=True)  # or grid()
    target.set_current_tab_index(self.mode_tab_state[target_mode])
    target.activate()

    self.current_mode = target_mode
    self._update_mode_bar_highlight()
```

**Parallel?**: No - depends on T007, T008.

### Subtask T010 - Implement keyboard shortcuts Ctrl+1-5

**Purpose**: Enable quick mode switching via keyboard (FR-003).

**Steps**:
1. Bind Ctrl+1 through Ctrl+5 to mode switching
2. Use bind_all() for global shortcuts
3. Test shortcuts don't interfere with text entry

**Files**: `src/ui/main_window.py`

**Implementation**:
```python
def _setup_keyboard_shortcuts(self):
    self.bind_all("<Control-1>", lambda e: self.switch_mode("CATALOG"))
    self.bind_all("<Control-2>", lambda e: self.switch_mode("PLAN"))
    self.bind_all("<Control-3>", lambda e: self.switch_mode("SHOP"))
    self.bind_all("<Control-4>", lambda e: self.switch_mode("PRODUCE"))
    self.bind_all("<Control-5>", lambda e: self.switch_mode("OBSERVE"))
```

**Notes**: Ctrl+Number shortcuts don't conflict with standard text editing (Ctrl+A, Ctrl+C, etc.)

**Parallel?**: Yes - after T007/T008/T009.

### Subtask T011 - Implement tab state preservation

**Purpose**: Remember last tab per mode when switching (FR-004).

**Steps**:
1. Store tab index in mode_tab_state dict when leaving mode
2. Restore tab index when returning to mode
3. Handle edge case where tab no longer exists

**Files**: `src/ui/main_window.py` (ModeManager)

**Notes**: Tab state resets on application restart (acceptable per research.md).

**Parallel?**: No - integrated with T009.

### Subtask T012 - Set default OBSERVE mode on launch

**Purpose**: Start application in OBSERVE mode (FR-005).

**Steps**:
1. Initialize current_mode to "OBSERVE"
2. Ensure OBSERVE mode is visible on startup
3. Highlight OBSERVE button on startup

**Files**: `src/ui/main_window.py`

**Implementation**:
```python
def _initialize_modes(self):
    # Create all modes
    self._create_catalog_mode()
    self._create_plan_mode()
    self._create_shop_mode()
    self._create_produce_mode()
    self._create_observe_mode()

    # Default to OBSERVE
    self.switch_mode("OBSERVE")
```

**Parallel?**: No - depends on mode creation.

### Subtask T013 - Style active mode button highlighting

**Purpose**: Visually indicate current mode (FR-002).

**Steps**:
1. Create active/inactive button styles
2. Update button styles when mode changes
3. Ensure clear visual distinction

**Files**: `src/ui/main_window.py`

**Implementation**:
```python
def _update_mode_bar_highlight(self):
    for mode_name, button in self.mode_buttons.items():
        if mode_name == self.current_mode:
            button.configure(fg_color="green", text_color="white")
        else:
            button.configure(fg_color="gray", text_color="black")
```

**Parallel?**: Yes - after T008.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Keyboard shortcuts conflict | Use Ctrl+Number which doesn't conflict with text editing |
| Mode switching performance | Use frame show/hide, not recreation |
| State loss on mode switch | Save state before hide, restore after show |

## Definition of Done Checklist

- [ ] Mode bar displays 5 mode buttons
- [ ] Clicking buttons switches modes
- [ ] Ctrl+1-5 shortcuts work
- [ ] Tab selection preserved when switching modes
- [ ] OBSERVE mode is default on launch
- [ ] Active mode button is highlighted
- [ ] No regressions in existing functionality

## Review Guidance

- Test all 5 modes can be accessed
- Verify keyboard shortcuts in different contexts (text field, button focus)
- Check tab state preservation across multiple mode switches

## Activity Log

- 2026-01-05 - system - lane=planned - Prompt created.
- 2026-01-05T22:34:21Z – system – shell_pid= – lane=doing – Moved to doing
- 2026-01-05T22:40:22Z – system – shell_pid= – lane=for_review – Moved to for_review
- 2026-01-06T01:39:54Z – claude-reviewer – shell_pid=41347 – lane=done – Code review: APPROVED - implementation verified, tests pass
