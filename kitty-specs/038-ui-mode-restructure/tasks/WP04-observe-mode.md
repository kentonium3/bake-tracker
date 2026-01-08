---
work_package_id: WP04
title: OBSERVE Mode
lane: done
history:
- timestamp: '2026-01-05'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude-reviewer
assignee: claude
phase: Phase 1 - Mode Implementation
review_status: ''
reviewed_by: ''
shell_pid: '41347'
subtasks:
- T022
- T023
- T024
- T025
- T026
---

# Work Package Prompt: WP04 - OBSERVE Mode

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Implement OBSERVE mode with enhanced dashboard, Event Status tab, and Reports placeholder.

**Success Criteria**:
- OBSERVE mode shows event readiness with progress percentages (FR-011)
- Event Status tab shows per-event progress tracking (FR-028)
- Dashboard tab shows overall activity summary (FR-027)
- Reports tab exists as placeholder

**User Story**: US5 - OBSERVE Mode for Progress Tracking (Priority P2)

## Context & Constraints

**Prerequisites**: WP01 (Base Classes), WP02 (Main Window Navigation)

**Reference Documents**:
- `kitty-specs/038-ui-mode-restructure/spec.md` - User Story 5, FR-011, FR-027, FR-028
- `kitty-specs/038-ui-mode-restructure/data-model.md` - ObserveMode definition

**Services Available**:
- `event_service.get_event_overall_progress(event_id)` - Returns shopping/production/assembly/packaging %
- `event_service.get_production_progress(event_id)` - Production target progress
- `event_service.get_assembly_progress(event_id)` - Assembly target progress

**Existing Tab**:
- `src/ui/dashboard_tab.py` (9KB) - To be enhanced

**Parallelization**: This work package can be done in parallel with WP03 (CATALOG Mode).

## Subtasks & Detailed Guidance

### Subtask T022 - Create ObserveDashboard

**Purpose**: Show event readiness with progress percentages (FR-011).

**Steps**:
1. Create `src/ui/dashboards/observe_dashboard.py`
2. Extend BaseDashboard
3. Display event readiness: shopping %, production %, assembly %, packaging %
4. Show upcoming events with status indicators

**Files**: `src/ui/dashboards/observe_dashboard.py`

**Implementation**:
```python
class ObserveDashboard(BaseDashboard):
    def __init__(self, master):
        super().__init__(master)
        self._create_progress_section()
        self._create_upcoming_events()

    def _create_progress_section(self):
        # Overall progress bars
        self.shopping_progress = self._create_progress_bar("Shopping")
        self.production_progress = self._create_progress_bar("Production")
        self.assembly_progress = self._create_progress_bar("Assembly")
        self.packaging_progress = self._create_progress_bar("Packaging")

    def _create_progress_bar(self, label: str) -> CTkProgressBar:
        frame = ctk.CTkFrame(self.stats_frame)
        ctk.CTkLabel(frame, text=label).pack(side="left")
        bar = ctk.CTkProgressBar(frame)
        bar.pack(side="left", fill="x", expand=True)
        frame.pack(fill="x", pady=2)
        return bar

    def refresh(self):
        from services.event_service import get_upcoming_events, get_event_overall_progress
        events = get_upcoming_events()
        # Aggregate progress across events
        # Update progress bars
```

**Parallel?**: No - needed for T023.

### Subtask T023 - Create ObserveMode

**Purpose**: Container for OBSERVE mode with dashboard and tabs.

**Steps**:
1. Create `src/ui/modes/observe_mode.py`
2. Extend BaseMode
3. Set up dashboard and CTkTabview with 3 tabs

**Files**: `src/ui/modes/observe_mode.py`

**Implementation**:
```python
class ObserveMode(BaseMode):
    def __init__(self, master):
        super().__init__(master, name="OBSERVE")
        self.dashboard = ObserveDashboard(self)
        self.dashboard.pack(fill="x", padx=10, pady=5)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=5)

        self.tabview.add("Dashboard")
        self.tabview.add("Event Status")
        self.tabview.add("Reports")

        self._setup_tabs()
```

**Parallel?**: No - needed before tab setup.

### Subtask T024 - Enhance dashboard_tab.py [P]

**Purpose**: Adapt existing dashboard tab for OBSERVE mode context.

**Steps**:
1. Review existing `dashboard_tab.py` structure
2. Ensure it works within ObserveMode tabview
3. Enhance with quick stats and activity summary
4. Add to "Dashboard" tab in OBSERVE mode

**Files**:
- `src/ui/modes/observe_mode.py` (modify)
- `src/ui/dashboard_tab.py` (may need enhancements)

**Verification**: Dashboard shows activity summary, quick stats.

**Parallel?**: Yes - after T022/T023.

### Subtask T025 - Create event_status_tab.py (NEW) [P]

**Purpose**: Show per-event progress tracking (FR-028).

**Steps**:
1. Create `src/ui/tabs/event_status_tab.py`
2. Display list of events with progress columns
3. Show progress bars for each stage per event
4. Allow drill-down to event details

**Files**: `src/ui/tabs/event_status_tab.py`

**Implementation**:
```python
class EventStatusTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self._create_event_list()

    def _create_event_list(self):
        # Treeview with columns: Event, Date, Shopping, Production, Assembly, Packaging
        columns = ("event", "date", "shopping", "production", "assembly", "packaging")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")

        for col in columns:
            self.tree.heading(col, text=col.title())

        self.tree.pack(fill="both", expand=True)

    def refresh(self):
        from services.event_service import get_all_events, get_event_overall_progress
        events = get_all_events()
        for event in events:
            progress = get_event_overall_progress(event.id)
            self.tree.insert("", "end", values=(
                event.name,
                event.event_date,
                f"{progress['shopping_pct']}%",
                f"{progress['production_pct']}%",
                f"{progress['assembly_pct']}%",
                f"{progress['packaging_pct']}%"
            ))
```

**Service Integration**:
- `event_service.get_all_events()` - List events
- `event_service.get_event_overall_progress(event_id)` - Per-event progress

**Parallel?**: Yes - after T022/T023.

### Subtask T026 - Create reports placeholder tab [P]

**Purpose**: Placeholder for future reports functionality.

**Steps**:
1. Create `src/ui/tabs/reports_tab.py`
2. Basic frame with "Reports coming soon" message
3. Add to "Reports" tab in OBSERVE mode

**Files**: `src/ui/tabs/reports_tab.py`

**Implementation**:
```python
class ReportsTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        label = ctk.CTkLabel(
            self,
            text="Reports\n\nReporting features are not yet defined.\nThis tab will be expanded in a future release.",
            font=("", 14)
        )
        label.pack(expand=True)

    def refresh(self):
        pass  # No data to refresh
```

**Notes**: Per user clarification, reports are not yet defined.

**Parallel?**: Yes - simple placeholder.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Progress calculation may be slow | Cache aggregated progress, refresh on demand |
| Large number of events | Paginate or limit displayed events |

## Definition of Done Checklist

- [ ] ObserveDashboard shows progress percentages for all stages
- [ ] ObserveMode contains all 3 tabs
- [ ] Dashboard tab shows activity summary
- [ ] Event Status tab lists events with per-event progress
- [ ] Reports placeholder tab exists
- [ ] Progress bars update correctly when data changes
- [ ] Tab switching within mode works

## Review Guidance

- Verify progress percentages match actual data
- Test with events at different completion stages
- Check dashboard performance (should load < 1 second)

## Activity Log

- 2026-01-05 - system - lane=planned - Prompt created.
- 2026-01-05T22:43:31Z – system – shell_pid= – lane=doing – Moved to doing
- 2026-01-05T22:45:50Z – system – shell_pid= – lane=for_review – Moved to for_review
- 2026-01-06T01:39:55Z – claude-reviewer – shell_pid=41347 – lane=done – Code review: APPROVED - implementation verified, tests pass
