---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
title: "Base Classes & Directory Structure"
phase: "Phase 0 - Setup"
lane: "done"
assignee: "claude"
agent: "claude-reviewer"
shell_pid: "41107"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-05"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Base Classes & Directory Structure

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Create foundational base classes (BaseMode, StandardTabLayout, BaseDashboard) that all modes depend on.

**Success Criteria**:
- Directory structure exists: `src/ui/base/`, `src/ui/modes/`, `src/ui/dashboards/`, `src/ui/tabs/`
- All base classes import successfully
- StandardTabLayout provides consistent layout regions
- BaseMode provides mode container functionality
- BaseDashboard provides dashboard interface

## Context & Constraints

**Prerequisites**: None - this is the starting package.

**Reference Documents**:
- `kitty-specs/038-ui-mode-restructure/data-model.md` - Entity definitions
- `kitty-specs/038-ui-mode-restructure/research.md` - Design decisions
- `.kittify/memory/constitution.md` - Architecture principles

**Constraints**:
- No business logic in UI layer (Constitution V)
- Use CustomTkinter (CTkFrame, CTkLabel, CTkButton, etc.)
- Python 3.10+ type hints

## Subtasks & Detailed Guidance

### Subtask T001 - Create directory structure

**Purpose**: Establish new directories for mode architecture components.

**Steps**:
1. Create `src/ui/base/` for base classes
2. Create `src/ui/modes/` for mode implementations
3. Create `src/ui/dashboards/` for dashboard widgets
4. Create `src/ui/tabs/` for new tab implementations

**Files**:
- `src/ui/base/`
- `src/ui/modes/`
- `src/ui/dashboards/`
- `src/ui/tabs/`

**Parallel?**: No - must complete before other subtasks.

### Subtask T002 - Create base __init__.py

**Purpose**: Export base classes from the base package.

**Steps**:
1. Create `src/ui/base/__init__.py`
2. Export StandardTabLayout and BaseMode

**Files**: `src/ui/base/__init__.py`

**Expected Content**:
```python
from .standard_tab_layout import StandardTabLayout
from .base_mode import BaseMode

__all__ = ["StandardTabLayout", "BaseMode"]
```

**Parallel?**: No - depends on T001.

### Subtask T003 - Implement StandardTabLayout

**Purpose**: Provide consistent layout pattern for all tabs (FR-012 through FR-017).

**Steps**:
1. Create `src/ui/base/standard_tab_layout.py`
2. Implement CTkFrame subclass with layout regions
3. Provide methods for setting action buttons, filters, content, status

**Files**: `src/ui/base/standard_tab_layout.py`

**Implementation Requirements**:
```
Layout Regions (grid):
Row 0: [action_bar (col 0-1, sticky W)] [refresh_area (col 2, sticky E)]
Row 1: [filter_bar (col 0-2, sticky EW)]
Row 2: [content_area (col 0-2, sticky NSEW, weight=1)]
Row 3: [status_bar (col 0-2, sticky EW)]
```

**Key Methods**:
- `set_action_buttons(buttons: List[Dict])` - Add/Edit/Delete buttons
- `set_refresh_callback(callback: Callable)` - Set refresh button action
- `set_filters(filters: List[Widget])` - Add filter widgets
- `set_content(widget: Widget)` - Set main content widget
- `set_status(text: str)` - Update status bar text
- `get_search_text() -> str` - Get search input value

**Parallel?**: Yes - after T001/T002.

### Subtask T004 - Implement BaseMode

**Purpose**: Abstract base class for mode containers.

**Steps**:
1. Create `src/ui/base/base_mode.py`
2. Implement CTkFrame subclass with dashboard and tabview
3. Provide activate/deactivate and tab state management

**Files**: `src/ui/base/base_mode.py`

**Key Attributes**:
- `name: str` - Mode identifier (CATALOG, PLAN, etc.)
- `dashboard: BaseDashboard` - Mode-specific dashboard
- `tabview: CTkTabview` - Tab container
- `current_tab_index: int` - Currently selected tab

**Key Methods**:
- `activate() -> None` - Called when mode becomes active
- `deactivate() -> None` - Called when mode becomes inactive
- `get_current_tab_index() -> int` - Returns current tab selection
- `set_current_tab_index(index: int) -> None` - Restores tab selection
- `refresh_dashboard() -> None` - Updates dashboard statistics
- `add_tab(name: str, tab_widget: Widget) -> None` - Add a tab to the mode

**Parallel?**: Yes - after T001/T002.

### Subtask T005 - Implement BaseDashboard

**Purpose**: Abstract base class for mode dashboards.

**Steps**:
1. Create `src/ui/dashboards/base_dashboard.py`
2. Implement CTkFrame subclass with collapse/expand
3. Provide abstract refresh method

**Files**: `src/ui/dashboards/base_dashboard.py`

**Key Attributes**:
- `is_collapsed: bool` - Dashboard visibility state
- `stats_frame: CTkFrame` - Container for statistics
- `actions_frame: CTkFrame` - Container for quick actions

**Key Methods**:
- `refresh() -> None` - Abstract, updates dashboard data
- `collapse() -> None` - Hides dashboard content
- `expand() -> None` - Shows dashboard content
- `toggle() -> None` - Toggle collapsed state
- `add_stat(label: str, value: str) -> CTkLabel` - Add stat widget
- `add_action(text: str, callback: Callable) -> CTkButton` - Add action button

**Parallel?**: Yes - after T001.

### Subtask T006 - Create package __init__.py files

**Purpose**: Set up Python packages for new directories.

**Steps**:
1. Create `src/ui/modes/__init__.py`
2. Create `src/ui/dashboards/__init__.py`
3. Create `src/ui/tabs/__init__.py`

**Files**:
- `src/ui/modes/__init__.py`
- `src/ui/dashboards/__init__.py`
- `src/ui/tabs/__init__.py`

**Notes**: Initially empty or with basic docstrings. Will be populated as mode implementations are added.

**Parallel?**: No - straightforward, do after T001.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Base class design may need iteration | Keep interfaces minimal; add methods as needed during mode implementation |
| CustomTkinter API compatibility | Reference existing tabs for working patterns |

## Definition of Done Checklist

- [ ] Directory structure exists
- [ ] All __init__.py files created
- [ ] StandardTabLayout implements all layout regions
- [ ] BaseMode provides tab management
- [ ] BaseDashboard provides collapse/expand
- [ ] All classes import without errors
- [ ] Code follows project conventions (type hints, docstrings)

## Review Guidance

- Verify base classes are abstract enough for all 5 modes
- Check that StandardTabLayout regions match FR-012 through FR-017
- Ensure no business logic leaked into UI classes

## Activity Log

- 2026-01-05 - system - lane=planned - Prompt created.
- 2026-01-05T22:29:48Z – claude – shell_pid=26809 – lane=doing – Started implementation
- 2026-01-05T22:33:47Z – claude – shell_pid=26809 – lane=for_review – Moved to for_review
- 2026-01-06T01:39:13Z – claude-reviewer – shell_pid=41107 – lane=done – Code review: APPROVED - all base classes implemented correctly, imports verified
