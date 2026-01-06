---
work_package_id: "WP07"
subtasks:
  - "T036"
  - "T037"
  - "T038"
  - "T039"
  - "T040"
  - "T041"
title: "PRODUCE Mode"
phase: "Phase 2 - Mode Implementation"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "35871"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-05"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 - PRODUCE Mode

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Implement PRODUCE mode with Production (merged), Assembly, Packaging (new), and Recipients tabs.

**Success Criteria**:
- PRODUCE mode dashboard shows pending production, assembly checklist, packaging checklist (FR-010)
- Production Runs tab consolidates production and dashboard views
- Assembly tab shows assembleable finished goods checklist (FR-025)
- Packaging tab shows items ready for final packaging (FR-026)
- Recipients tab accessible from PRODUCE mode

**User Story**: US6 - PRODUCE Mode for Execution (Priority P3)

## Context & Constraints

**Prerequisites**: WP01 (Base Classes), WP02 (Main Window Navigation)

**Reference Documents**:
- `kitty-specs/038-ui-mode-restructure/spec.md` - User Story 6, FR-010, FR-024, FR-025, FR-026
- `kitty-specs/038-ui-mode-restructure/data-model.md` - ProduceMode definition

**Existing Tabs**:
- `src/ui/production_tab.py` (30KB)
- `src/ui/production_dashboard_tab.py` (21KB) - To be merged
- `src/ui/recipients_tab.py` (18KB)

**Services Available**:
- `assembly_service.check_can_assemble()`, `record_assembly()`, `get_assembly_history()`
- `packaging_service.get_pending_requirements()`, `assign_materials()`, `get_assignment_summary()`
- `batch_production_service` - Production operations

## Subtasks & Detailed Guidance

### Subtask T036 - Create ProduceDashboard

**Purpose**: Show pending production, assembly checklist, packaging checklist (FR-010).

**Steps**:
1. Create `src/ui/dashboards/produce_dashboard.py`
2. Extend BaseDashboard
3. Display pending production batches count
4. Show assembly checklist summary
5. Show packaging checklist summary

**Files**: `src/ui/dashboards/produce_dashboard.py`

**Implementation**:
```python
class ProduceDashboard(BaseDashboard):
    def __init__(self, master):
        super().__init__(master)
        self._create_stats()
        self._create_checklists()

    def _create_stats(self):
        self.add_stat("Pending Batches", "0")
        self.add_stat("Ready to Assemble", "0")
        self.add_stat("Ready to Package", "0")

    def _create_checklists(self):
        # Quick checklist summaries
        self.today_frame = ctk.CTkFrame(self.stats_frame)
        ctk.CTkLabel(self.today_frame, text="Today's Production").pack()
        self.today_frame.pack(fill="x", pady=5)

    def refresh(self):
        from services.batch_production_service import get_pending_batches
        from services.assembly_service import get_assembleable_items
        from services.packaging_service import get_pending_requirements
        # Update all stats
```

**Parallel?**: No - needed for T037.

### Subtask T037 - Create ProduceMode

**Purpose**: Container for PRODUCE mode with dashboard and tabs.

**Steps**:
1. Create `src/ui/modes/produce_mode.py`
2. Extend BaseMode
3. Set up dashboard and CTkTabview with 4 tabs

**Files**: `src/ui/modes/produce_mode.py`

**Implementation**:
```python
class ProduceMode(BaseMode):
    def __init__(self, master):
        super().__init__(master, name="PRODUCE")
        self.dashboard = ProduceDashboard(self)
        self.dashboard.pack(fill="x", padx=10, pady=5)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=5)

        self.tabview.add("Production Runs")
        self.tabview.add("Assembly")
        self.tabview.add("Packaging")
        self.tabview.add("Recipients")

        self._setup_tabs()
```

**Parallel?**: No - needed before tab setup.

### Subtask T038 - Merge production tabs [P]

**Purpose**: Consolidate production_tab.py and production_dashboard_tab.py into single Production Runs view.

**Steps**:
1. Review both `production_tab.py` (30KB) and `production_dashboard_tab.py` (21KB)
2. Identify overlapping/complementary functionality
3. Create unified Production Runs tab in ProduceMode
4. Ensure all functionality preserved

**Files**:
- `src/ui/modes/produce_mode.py` (modify)
- `src/ui/production_tab.py` (may need adjustments)
- `src/ui/production_dashboard_tab.py` (may be deprecated or merged)

**Merge Strategy**:
1. Production dashboard shows overview/stats at top
2. Production runs list/grid below
3. Actions (record batch, complete batch) available
4. Filter by event, recipe, status

**Verification**: Test all production operations:
- View pending production
- Record batch production
- Complete batches
- Filter and search

**Parallel?**: Yes - after T036/T037.

### Subtask T039 - Create assembly_tab.py (NEW) [P]

**Purpose**: Show checklist of assembleable finished goods (FR-025).

**Steps**:
1. Create `src/ui/tabs/assembly_tab.py`
2. Display finished goods that can be assembled
3. Show component availability status
4. Allow recording assembly completion

**Files**: `src/ui/tabs/assembly_tab.py`

**Implementation**:
```python
class AssemblyTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self._create_action_bar()
        self._create_assembly_list()

    def _create_action_bar(self):
        bar = ctk.CTkFrame(self)
        bar.pack(fill="x", pady=5)

        self.assemble_btn = ctk.CTkButton(bar, text="Record Assembly", command=self._record_assembly)
        self.assemble_btn.pack(side="left", padx=5)

        self.refresh_btn = ctk.CTkButton(bar, text="Refresh", command=self.refresh)
        self.refresh_btn.pack(side="right", padx=5)

    def _create_assembly_list(self):
        # Checklist style display
        columns = ("finished_good", "qty_available", "components_ready", "event")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
        self.tree.pack(fill="both", expand=True)

    def _record_assembly(self):
        selected = self.tree.selection()
        if not selected:
            return
        # Open assembly dialog
        from services.assembly_service import record_assembly

    def refresh(self):
        from services.assembly_service import check_can_assemble, get_assembleable_items
        # Show items ready for assembly with component status
```

**Service Integration**:
- `assembly_service.check_can_assemble(finished_good_id, quantity)` - Check availability
- `assembly_service.record_assembly(...)` - Record completion
- `assembly_service.get_assembly_history(...)` - View history

**Parallel?**: Yes - after T036/T037.

### Subtask T040 - Create packaging_tab.py (NEW) [P]

**Purpose**: Show items ready for final packaging (FR-026).

**Steps**:
1. Create `src/ui/tabs/packaging_tab.py`
2. Display packaging requirements by event
3. Show assignment status
4. Allow assigning materials to packages

**Files**: `src/ui/tabs/packaging_tab.py`

**Implementation**:
```python
class PackagingTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self._create_action_bar()
        self._create_packaging_list()

    def _create_action_bar(self):
        bar = ctk.CTkFrame(self)
        bar.pack(fill="x", pady=5)

        self.assign_btn = ctk.CTkButton(bar, text="Assign Materials", command=self._assign_materials)
        self.assign_btn.pack(side="left", padx=5)

        self.complete_btn = ctk.CTkButton(bar, text="Mark Complete", command=self._mark_complete)
        self.complete_btn.pack(side="left", padx=5)

    def _create_packaging_list(self):
        columns = ("package", "event", "recipient", "items", "status")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col.title())
        self.tree.pack(fill="both", expand=True)

    def refresh(self):
        from services.packaging_service import get_pending_requirements, get_assignment_summary
        # Display pending packaging with status
```

**Service Integration**:
- `packaging_service.get_pending_requirements(event_id)` - What needs packaging
- `packaging_service.assign_materials(...)` - Assign items to packages
- `packaging_service.get_assignment_summary(...)` - Status overview

**Parallel?**: Yes - after T036/T037.

### Subtask T041 - Integrate recipients_tab.py [P]

**Purpose**: Add Recipients tab to PRODUCE mode.

**Steps**:
1. Review existing `recipients_tab.py` structure (18KB)
2. Instantiate RecipientsTab in ProduceMode
3. Add to "Recipients" tab in tabview
4. Verify all functionality works

**Files**:
- `src/ui/modes/produce_mode.py` (modify)
- `src/ui/recipients_tab.py` (may need minor adjustments)

**Verification**: Test recipient CRUD operations.

**Notes**: Recipients were clarified to belong in PRODUCE mode per user feedback.

**Parallel?**: Yes - after T036/T037.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Production tab merge complexity | Review both tabs carefully; test all operations |
| Assembly/packaging service methods | Services exist; verify method signatures |
| Recipients tab integration | Minimal changes expected |

## Definition of Done Checklist

- [ ] ProduceDashboard shows production, assembly, packaging stats
- [ ] ProduceMode contains all 4 tabs
- [ ] Production Runs tab: All production operations work
- [ ] Production Runs tab: Dashboard and list merged
- [ ] Assembly tab: Shows assembleable items
- [ ] Assembly tab: Record assembly works
- [ ] Packaging tab: Shows pending packaging
- [ ] Packaging tab: Assign materials works
- [ ] Recipients tab: All CRUD operations work
- [ ] Tab switching within mode works

## Review Guidance

- Test production workflow end-to-end
- Verify assembly checklist accuracy
- Check packaging status updates correctly
- Ensure recipients data displays properly

## Activity Log

- 2026-01-05 - system - lane=planned - Prompt created.
- 2026-01-06T00:36:04Z – system – shell_pid= – lane=doing – Moved to doing
- 2026-01-06T01:02:22Z – claude – shell_pid=35871 – lane=for_review – Implementation complete - PRODUCE mode with dashboard, Production Runs, Assembly, Packaging, Recipients tabs
