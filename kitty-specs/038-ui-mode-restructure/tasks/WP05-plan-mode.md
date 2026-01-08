---
work_package_id: WP05
title: PLAN Mode
lane: done
history:
- timestamp: '2026-01-05'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude-reviewer
assignee: claude
phase: Phase 2 - Mode Implementation
review_status: ''
reviewed_by: ''
shell_pid: '41347'
subtasks:
- T027
- T028
- T029
- T030
---

# Work Package Prompt: WP05 - PLAN Mode

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Implement PLAN mode with Events tab migration and new Planning Workspace tab.

**Success Criteria**:
- PLAN mode shows upcoming events in dashboard (FR-008)
- Events tab accessible and functional (FR-020)
- Planning Workspace shows calculated batch requirements (FR-021)

**User Story**: US8 - PLAN Mode for Event Planning (Priority P3)

## Context & Constraints

**Prerequisites**: WP01 (Base Classes), WP02 (Main Window Navigation)

**Reference Documents**:
- `kitty-specs/038-ui-mode-restructure/spec.md` - User Story 8, FR-008, FR-020, FR-021
- `kitty-specs/038-ui-mode-restructure/data-model.md` - PlanMode definition

**Existing Tab**:
- `src/ui/events_tab.py` (11KB)

**Services Available**:
- `event_service` - Event CRUD and calculations

## Subtasks & Detailed Guidance

### Subtask T027 - Create PlanDashboard

**Purpose**: Show upcoming events with status indicators (FR-008).

**Steps**:
1. Create `src/ui/dashboards/plan_dashboard.py`
2. Extend BaseDashboard
3. Display upcoming events count and next event date
4. Show events needing attention

**Files**: `src/ui/dashboards/plan_dashboard.py`

**Implementation**:
```python
class PlanDashboard(BaseDashboard):
    def __init__(self, master):
        super().__init__(master)
        self._create_stats()
        self._create_upcoming_list()

    def _create_stats(self):
        self.add_stat("Upcoming Events", "0")
        self.add_stat("Next Event", "N/A")
        self.add_stat("Events Needing Attention", "0")

    def _create_upcoming_list(self):
        # Simple list of next 3-5 events
        self.upcoming_frame = ctk.CTkFrame(self.stats_frame)
        self.upcoming_frame.pack(fill="x", pady=5)

    def refresh(self):
        from services.event_service import get_upcoming_events
        events = get_upcoming_events(limit=5)
        # Update stats and list
```

**Parallel?**: No - needed for T028.

### Subtask T028 - Create PlanMode

**Purpose**: Container for PLAN mode with dashboard and tabs.

**Steps**:
1. Create `src/ui/modes/plan_mode.py`
2. Extend BaseMode
3. Set up dashboard and CTkTabview with 2 tabs

**Files**: `src/ui/modes/plan_mode.py`

**Implementation**:
```python
class PlanMode(BaseMode):
    def __init__(self, master):
        super().__init__(master, name="PLAN")
        self.dashboard = PlanDashboard(self)
        self.dashboard.pack(fill="x", padx=10, pady=5)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=5)

        self.tabview.add("Events")
        self.tabview.add("Planning Workspace")

        self._setup_tabs()
```

**Parallel?**: No - needed before tab setup.

### Subtask T029 - Integrate events_tab.py [P]

**Purpose**: Add Events tab to PLAN mode.

**Steps**:
1. Review existing `events_tab.py` structure
2. Instantiate EventsTab in PlanMode
3. Add to "Events" tab in tabview
4. Verify all functionality works

**Files**:
- `src/ui/modes/plan_mode.py` (modify)
- `src/ui/events_tab.py` (may need minor adjustments)

**Verification**: Test Add, Edit, Delete events; date selection; bundle requirements.

**Parallel?**: Yes - after T027/T028.

### Subtask T030 - Create planning_workspace_tab.py (NEW) [P]

**Purpose**: Show calculated batch requirements for events (FR-021).

**Steps**:
1. Create `src/ui/tabs/planning_workspace_tab.py`
2. Display event selector
3. Show calculated production requirements (batches needed)
4. Show ingredient requirements aggregated from recipes

**Files**: `src/ui/tabs/planning_workspace_tab.py`

**Implementation**:
```python
class PlanningWorkspaceTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self._create_event_selector()
        self._create_requirements_view()

    def _create_event_selector(self):
        self.event_combo = ctk.CTkComboBox(self, values=[], command=self._on_event_selected)
        self.event_combo.pack(fill="x", pady=10)

    def _create_requirements_view(self):
        # Two sections: Production Requirements, Ingredient Requirements
        self.production_frame = ctk.CTkFrame(self)
        self.production_frame.pack(fill="both", expand=True)

        self.ingredients_frame = ctk.CTkFrame(self)
        self.ingredients_frame.pack(fill="both", expand=True)

    def _on_event_selected(self, event_name: str):
        from services.event_service import get_shopping_list, get_production_requirements
        # Load and display requirements

    def refresh(self):
        from services.event_service import get_upcoming_events
        events = get_upcoming_events()
        self.event_combo.configure(values=[e.name for e in events])
```

**Service Integration**:
- `event_service.get_upcoming_events()` - Populate event selector
- `event_service.get_shopping_list(event_id)` - Ingredient requirements
- Production requirements from event targets

**Parallel?**: Yes - after T027/T028.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Batch calculation complexity | Services already exist; focus on UI |
| Event data dependencies | Ensure event service methods are available |

## Definition of Done Checklist

- [ ] PlanDashboard shows upcoming events and stats
- [ ] PlanMode contains both tabs
- [ ] Events tab: Add, Edit, Delete, bundle requirements work
- [ ] Planning Workspace: Event selector works
- [ ] Planning Workspace: Shows production requirements
- [ ] Planning Workspace: Shows ingredient requirements
- [ ] Tab switching within mode works

## Review Guidance

- Test event CRUD operations
- Verify batch calculations match expected values
- Check ingredient aggregation accuracy

## Activity Log

- 2026-01-05 - system - lane=planned - Prompt created.
- 2026-01-06T00:35:50Z – system – shell_pid= – lane=doing – Moved to doing
- 2026-01-06T01:01:52Z – claude – shell_pid=35642 – lane=for_review – Implementation complete - PLAN mode with dashboard and tabs
- 2026-01-06T01:39:56Z – claude-reviewer – shell_pid=41347 – lane=done – Code review: APPROVED - implementation verified, tests pass
