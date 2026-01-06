---
work_package_id: "WP07"
subtasks:
  - "T042"
  - "T043"
  - "T044"
  - "T045"
  - "T046"
  - "T047"
  - "T048"
title: "Planning Workspace Container"
phase: "Phase 3 - UI"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "67799"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-06T03:09:20Z"
    lane: "planned"
    agent: "claude"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 - Planning Workspace Container

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Create main wizard container with sidebar + content layout
- Implement phase navigation sidebar with status indicators
- Support phase navigation with prerequisite warnings
- Wire into PLAN mode from F038

**Success Metrics (from spec):**
- SC-011: User can see shopping, production, and assembly status in one workspace
- FR-034-036: Flexible navigation with contextual warnings

---

## Context & Constraints

### Reference Documents
- **Quickstart**: `kitty-specs/039-planning-workspace/quickstart.md` - UI guidelines, wizard layout
- **Plan**: `kitty-specs/039-planning-workspace/plan.md` - UI structure decision

### Key Constraints
- Uses CustomTkinter (CTkFrame, CTkButton, CTkLabel)
- Wizard layout: sidebar (20%) + main content (80%)
- Follow existing UI patterns from other modes
- Depends on WP06 (PlanningService facade)
- NOT parallelizable (container must exist before views)

### Architectural Notes
- Located in `src/ui/planning/` module
- UI layer calls services only - no direct model access
- Event binding for phase navigation

---

## Subtasks & Detailed Guidance

### Subtask T042 - Create planning/__init__.py (UI)

- **Purpose**: Initialize UI module with exports
- **Steps**:
  1. Create directory: `src/ui/planning/`
  2. Create `__init__.py` with exports:
     ```python
     from .planning_workspace import PlanningWorkspace
     from .phase_sidebar import PhaseSidebar
     ```
  3. Add module docstring
- **Files**: `src/ui/planning/__init__.py`

### Subtask T043 - Create planning_workspace.py

- **Purpose**: Main container with wizard layout
- **Steps**:
  1. Create `src/ui/planning/planning_workspace.py`
  2. Define PlanningWorkspace class extending CTkFrame:
     ```python
     class PlanningWorkspace(ctk.CTkFrame):
         def __init__(self, parent, event_id: int, **kwargs):
             super().__init__(parent, **kwargs)
             self.event_id = event_id
             self.current_phase = PlanPhase.CALCULATE
             self._setup_layout()
             self._setup_views()
     ```
  3. Implement layout:
     - Left sidebar (20% width): PhaseSidebar
     - Right content (80% width): phase view container
  4. Implement view switching:
     ```python
     def switch_to_phase(self, phase: PlanPhase):
         self._hide_all_views()
         self._show_view(phase)
         self.sidebar.update_active_phase(phase)
     ```
- **Files**: `src/ui/planning/planning_workspace.py`
- **Notes**: Follow existing workspace patterns

### Subtask T044 - Create phase_sidebar.py

- **Purpose**: Navigation sidebar with status indicators
- **Steps**:
  1. Create `src/ui/planning/phase_sidebar.py`
  2. Define PhaseSidebar class:
     ```python
     class PhaseSidebar(ctk.CTkFrame):
         def __init__(self, parent, on_phase_select: Callable[[PlanPhase], None], **kwargs):
             super().__init__(parent, **kwargs)
             self.on_phase_select = on_phase_select
             self._setup_buttons()
     ```
  3. Create buttons for each phase:
     - Calculate
     - Shop
     - Produce
     - Assemble
  4. Add status indicator next to each button
  5. Implement `update_active_phase()` to highlight current
  6. Implement `update_phase_status()` to change indicators
- **Files**: `src/ui/planning/phase_sidebar.py`

### Subtask T045 - Implement phase status indicators

- **Purpose**: Visual status for each phase (FR-024)
- **Steps**:
  1. Define status colors:
     ```python
     STATUS_COLORS = {
         PhaseStatus.NOT_STARTED: "gray",
         PhaseStatus.IN_PROGRESS: "yellow",
         PhaseStatus.COMPLETE: "green",
         PhaseStatus.BLOCKED: "red",
     }
     ```
  2. Create indicator widget (small circle or icon):
     ```python
     class StatusIndicator(ctk.CTkLabel):
         def __init__(self, parent, status: PhaseStatus = PhaseStatus.NOT_STARTED):
             # Use unicode symbols: ○ ◐ ● ⚠
     ```
  3. Update indicator when status changes
- **Files**: `src/ui/planning/phase_sidebar.py`
- **Notes**: Use unicode symbols for cross-platform compatibility

### Subtask T046 - Implement phase navigation with warnings

- **Purpose**: Warn on incomplete prerequisites (FR-034-035)
- **Steps**:
  1. Before switching phase, check prerequisites:
     ```python
     def _check_prerequisites(self, target_phase: PlanPhase) -> Optional[str]:
         """Return warning message if prerequisites incomplete."""
         if target_phase == PlanPhase.SHOP:
             if not self._has_calculated_plan():
                 return "No plan calculated. Calculate first?"
         if target_phase == PlanPhase.PRODUCE:
             if not self._is_shopping_complete():
                 return "Shopping incomplete. Continue anyway?"
         # etc.
     ```
  2. Show warning dialog if prerequisites incomplete:
     - "Continue anyway" button
     - "Go to [prerequisite phase]" button
  3. Allow navigation regardless (guided but flexible)
- **Files**: `src/ui/planning/planning_workspace.py`
- **Notes**: Warn but don't block

### Subtask T047 - Implement stale plan banner

- **Purpose**: Show "Plan may be outdated" warning (FR-040)
- **Steps**:
  1. Add banner widget at top of content area:
     ```python
     class StalePlanBanner(ctk.CTkFrame):
         def __init__(self, parent, on_recalculate: Callable, **kwargs):
             # Yellow background
             # Message: "Plan may be outdated: [reason]"
             # Button: "Recalculate"
     ```
  2. Check staleness on workspace load:
     ```python
     def _check_staleness(self):
         is_stale, reason = planning_service.check_staleness(self.event_id)
         if is_stale:
             self.stale_banner.show(reason)
     ```
  3. Recalculate button calls `calculate_plan(force_recalculate=True)`
- **Files**: `src/ui/planning/planning_workspace.py`

### Subtask T048 - Wire into PLAN mode navigation

- **Purpose**: Connect to main app navigation (from F038)
- **Steps**:
  1. Find where F038 defined PLAN mode entry point
  2. Update to instantiate PlanningWorkspace:
     ```python
     def show_plan_mode(self, event_id: int):
         self._clear_content()
         workspace = PlanningWorkspace(self.content_frame, event_id)
         workspace.pack(fill="both", expand=True)
     ```
  3. Ensure event selection flows into planning workspace
- **Files**: Main app UI file (location from F038)
- **Notes**: Check F038 implementation for exact integration point

---

## Test Strategy

**Manual Testing Required:**
- Navigate between all phases
- Verify status indicators update correctly
- Test warning dialogs for incomplete prerequisites
- Test stale plan banner display and recalculate
- Verify layout renders correctly at different window sizes

**Run app with:**
```bash
python src/main.py
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| UI framework compatibility | Test on Windows, macOS, Linux |
| Layout issues at different sizes | Use relative sizing (grid weights) |
| Event binding conflicts | Use unique callback names |

---

## Definition of Done Checklist

- [ ] planning/__init__.py created with exports
- [ ] PlanningWorkspace container created with sidebar + content layout
- [ ] PhaseSidebar with navigation buttons created
- [ ] Status indicators display correctly for all states
- [ ] Phase navigation with warning dialogs works
- [ ] Stale plan banner shows and recalculate works
- [ ] Wired into PLAN mode from F038
- [ ] Manual testing passes on all phases
- [ ] `tasks.md` updated with status change

---

## Review Guidance

- Verify layout matches quickstart wireframe
- Check warning dialogs are non-blocking (allow continue)
- Test status indicator color changes
- Validate service calls use session correctly

---

## Activity Log

- 2026-01-06T03:09:20Z - claude - lane=planned - Prompt created.
- 2026-01-06T14:01:30Z – claude – shell_pid=67799 – lane=doing – Started implementation - Planning Workspace Container
