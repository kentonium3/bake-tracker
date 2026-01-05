# Work Packages: UI Mode Restructure

**Inputs**: Design documents from `/kitty-specs/038-ui-mode-restructure/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md, quickstart.md

**Tests**: Not explicitly requested - focus on functional implementation.

**Organization**: 47 subtasks (`Txxx`) rolled into 8 work packages (`WPxx`). Each work package is independently deliverable.

**Prompt Files**: Each work package references a matching prompt file in `tasks/planned/`.

## Subtask Format: `[Txxx] [P?] Description`
- **[P]** indicates the subtask can proceed in parallel (different files/components).
- All paths relative to `src/ui/` unless otherwise noted.

---

## Work Package WP01: Base Classes & Directory Structure (Priority: P0)

**Goal**: Create foundational base classes (BaseMode, StandardTabLayout, BaseDashboard) that all modes depend on.
**Independent Test**: Base classes import successfully; directory structure exists.
**Prompt**: `tasks/planned/WP01-base-classes.md`

### Included Subtasks
- [ ] T001 Create directory structure: `src/ui/base/`, `src/ui/modes/`, `src/ui/dashboards/`, `src/ui/tabs/`
- [ ] T002 Create `src/ui/base/__init__.py` with exports
- [ ] T003 Implement `StandardTabLayout` in `src/ui/base/standard_tab_layout.py`
- [ ] T004 Implement `BaseMode` in `src/ui/base/base_mode.py`
- [ ] T005 Implement `BaseDashboard` in `src/ui/dashboards/base_dashboard.py`
- [ ] T006 Create `src/ui/modes/__init__.py`, `src/ui/dashboards/__init__.py`, `src/ui/tabs/__init__.py`

### Implementation Notes
1. StandardTabLayout provides consistent regions: action_bar, refresh_area, filter_bar, content_area, status_bar
2. BaseMode is abstract - provides activate/deactivate, tab state management
3. BaseDashboard provides collapse/expand and refresh interface
4. See `data-model.md` for entity definitions

### Parallel Opportunities
- T003, T004, T005 can be developed in parallel after T001/T002 complete

### Dependencies
- None (starting package)

### Risks & Mitigations
- Risk: Base class design may need iteration; Mitigation: Keep interfaces minimal initially

---

## Work Package WP02: Main Window & Mode Navigation (Priority: P0)

**Goal**: Implement mode bar, ModeManager, and keyboard shortcuts in main_window.py.
**Independent Test**: Application launches with mode bar; clicking modes switches content; Ctrl+1-5 shortcuts work.
**Prompt**: `tasks/planned/WP02-main-window-navigation.md`

### Included Subtasks
- [ ] T007 Create `ModeManager` class in `src/ui/main_window.py` or separate file
- [ ] T008 Create mode bar frame with 5 mode buttons (CATALOG, PLAN, SHOP, PRODUCE, OBSERVE)
- [ ] T009 Implement mode switching logic (show/hide mode frames)
- [ ] T010 Implement keyboard shortcuts Ctrl+1 through Ctrl+5
- [ ] T011 Implement mode tab state preservation (remember last tab per mode)
- [ ] T012 Set default mode to OBSERVE on application launch (FR-005)
- [ ] T013 Style active mode button highlighting (FR-002)

### Implementation Notes
1. Mode bar should be horizontal, prominent placement
2. Use `bind_all()` for keyboard shortcuts
3. ModeManager tracks current_mode, mode_tab_state dict
4. Per research.md: mode switching uses frame visibility (pack/pack_forget)

### Parallel Opportunities
- T010 (shortcuts) can be done after T008/T009

### Dependencies
- Depends on WP01 (needs BaseMode class)

### Risks & Mitigations
- Risk: Keyboard shortcuts may conflict with text entry; Mitigation: Ctrl+Number doesn't conflict with typing

---

## Work Package WP03: CATALOG Mode (Priority: P1) [P]

**Goal**: Implement CATALOG mode with dashboard and 6 existing tabs migrated.
**Independent Test**: CATALOG mode shows dashboard with entity counts; all 6 tabs accessible and functional.
**Prompt**: `tasks/planned/WP03-catalog-mode.md`

### Included Subtasks
- [ ] T014 Create `CatalogDashboard` in `src/ui/dashboards/catalog_dashboard.py`
- [ ] T015 Create `CatalogMode` in `src/ui/modes/catalog_mode.py`
- [ ] T016 [P] Integrate `ingredients_tab.py` into CATALOG mode
- [ ] T017 [P] Integrate `products_tab.py` into CATALOG mode
- [ ] T018 [P] Integrate `recipes_tab.py` into CATALOG mode
- [ ] T019 [P] Integrate `finished_units_tab.py` into CATALOG mode
- [ ] T020 [P] Integrate `finished_goods_tab.py` into CATALOG mode
- [ ] T021 [P] Integrate `packages_tab.py` into CATALOG mode

### Implementation Notes
1. CatalogDashboard shows counts: ingredients, products, recipes, finished units, finished goods (FR-007)
2. Use existing service methods for counts (e.g., `ingredient_service.get_all_ingredients()`)
3. Existing tabs require minimal modification - add to mode's CTkTabview
4. Verify all CRUD operations still work after integration

### Parallel Opportunities
- T16-T21 can all proceed in parallel (different files)
- CATALOG mode is independent of OBSERVE mode - safe for Gemini delegation

### Dependencies
- Depends on WP01, WP02

### Risks & Mitigations
- Risk: Large tab files (ingredients_tab.py is 58KB); Mitigation: Test thoroughly after integration

---

## Work Package WP04: OBSERVE Mode (Priority: P1) [P]

**Goal**: Implement OBSERVE mode with enhanced dashboard, Event Status tab, and Reports placeholder.
**Independent Test**: OBSERVE mode shows event readiness progress; Event Status tab shows per-event details.
**Prompt**: `tasks/planned/WP04-observe-mode.md`

### Included Subtasks
- [ ] T022 Create `ObserveDashboard` in `src/ui/dashboards/observe_dashboard.py`
- [ ] T023 Create `ObserveMode` in `src/ui/modes/observe_mode.py`
- [ ] T024 Enhance `dashboard_tab.py` for OBSERVE mode context
- [ ] T025 Create `event_status_tab.py` in `src/ui/tabs/` (NEW)
- [ ] T026 Create placeholder `reports_tab.py` in `src/ui/tabs/`

### Implementation Notes
1. ObserveDashboard shows event readiness: shopping %, production %, assembly %, packaging % (FR-011)
2. Use `event_service.get_event_overall_progress()` for progress data
3. Event Status tab shows per-event breakdown with progress bars
4. Reports tab is placeholder - basic structure, functionality TBD

### Parallel Opportunities
- T24-T26 can proceed in parallel
- OBSERVE mode is independent of CATALOG mode

### Dependencies
- Depends on WP01, WP02

### Risks & Mitigations
- Risk: Progress calculation may be slow; Mitigation: Cache dashboard data, use progressive loading

---

## Work Package WP05: PLAN Mode (Priority: P2)

**Goal**: Implement PLAN mode with Events tab migration and new Planning Workspace tab.
**Independent Test**: PLAN mode shows upcoming events; Planning Workspace shows batch calculations.
**Prompt**: `tasks/planned/WP05-plan-mode.md`

### Included Subtasks
- [ ] T027 Create `PlanDashboard` in `src/ui/dashboards/plan_dashboard.py`
- [ ] T028 Create `PlanMode` in `src/ui/modes/plan_mode.py`
- [ ] T029 Integrate `events_tab.py` into PLAN mode
- [ ] T030 Create `planning_workspace_tab.py` in `src/ui/tabs/` (NEW)

### Implementation Notes
1. PlanDashboard shows upcoming events with status indicators (FR-008)
2. Planning Workspace shows calculated batch requirements for events (FR-021)
3. Use `event_service` for event data and calculations

### Parallel Opportunities
- T29 and T30 can proceed in parallel after T27/T28

### Dependencies
- Depends on WP01, WP02

### Risks & Mitigations
- Risk: Batch calculation logic may be complex; Mitigation: Services already exist, focus on UI

---

## Work Package WP06: SHOP Mode (Priority: P2)

**Goal**: Implement SHOP mode with Shopping Lists, Purchases (new tabs), and Inventory migration.
**Independent Test**: SHOP mode shows shopping lists by store; Purchases tab records purchases; Inventory works.
**Prompt**: `tasks/planned/WP06-shop-mode.md`

### Included Subtasks
- [ ] T031 Create `ShopDashboard` in `src/ui/dashboards/shop_dashboard.py`
- [ ] T032 Create `ShopMode` in `src/ui/modes/shop_mode.py`
- [ ] T033 Create `shopping_lists_tab.py` in `src/ui/tabs/` (NEW)
- [ ] T034 Create `purchases_tab.py` in `src/ui/tabs/` (NEW)
- [ ] T035 Integrate `inventory_tab.py` into SHOP mode

### Implementation Notes
1. ShopDashboard shows shopping lists by store and inventory alerts (FR-009)
2. Shopping Lists tab uses `event_service.get_shopping_list()` (FR-023)
3. Purchases tab uses `purchase_service` for CRUD operations
4. inventory_tab.py is 103KB - verify all functionality preserved

### Parallel Opportunities
- T33, T34, T35 can proceed in parallel

### Dependencies
- Depends on WP01, WP02

### Risks & Mitigations
- Risk: Large inventory_tab.py integration; Mitigation: Minimal changes, thorough testing

---

## Work Package WP07: PRODUCE Mode (Priority: P2)

**Goal**: Implement PRODUCE mode with Production (merged), Assembly, Packaging (new), and Recipients tabs.
**Independent Test**: PRODUCE mode shows pending production; Assembly/Packaging checklists work.
**Prompt**: `tasks/planned/WP07-produce-mode.md`

### Included Subtasks
- [ ] T036 Create `ProduceDashboard` in `src/ui/dashboards/produce_dashboard.py`
- [ ] T037 Create `ProduceMode` in `src/ui/modes/produce_mode.py`
- [ ] T038 Merge `production_tab.py` and `production_dashboard_tab.py` into single Production Runs tab
- [ ] T039 Create `assembly_tab.py` in `src/ui/tabs/` (NEW)
- [ ] T040 Create `packaging_tab.py` in `src/ui/tabs/` (NEW)
- [ ] T041 Integrate `recipients_tab.py` into PRODUCE mode

### Implementation Notes
1. ProduceDashboard shows pending production, assembly checklist, packaging checklist (FR-010)
2. Assembly tab uses `assembly_service.check_can_assemble()`, `record_assembly()` (FR-025)
3. Packaging tab uses `packaging_service.get_pending_requirements()`, `assign_materials()` (FR-026)
4. Recipients tab moved from flat navigation per user clarification

### Parallel Opportunities
- T38, T39, T40, T41 can proceed in parallel after T36/T37

### Dependencies
- Depends on WP01, WP02

### Risks & Mitigations
- Risk: Production tab merge complexity; Mitigation: Review both tabs, plan merge strategy

---

## Work Package WP08: Integration & Polish (Priority: P3)

**Goal**: Final integration, remove old navigation, test full workflow, handle edge cases.
**Independent Test**: Full workflow works end-to-end; no regressions; edge cases handled.
**Prompt**: `tasks/planned/WP08-integration-polish.md`

### Included Subtasks
- [ ] T042 Remove old flat tab navigation from `main_window.py`
- [ ] T043 Test mode switching and tab state preservation
- [ ] T044 Implement unsaved changes confirmation dialog (edge case)
- [ ] T045 Implement empty state handling for new users
- [ ] T046 Verify dashboard loading performance (< 1 second per SC-005)
- [ ] T047 Final code cleanup and organization

### Implementation Notes
1. Big-bang replacement - old navigation removed completely (FR-031)
2. Test all acceptance scenarios from spec
3. Verify keyboard shortcuts don't interfere with text entry
4. Add loading indicators for dashboard data

### Parallel Opportunities
- T44, T45 can proceed in parallel

### Dependencies
- Depends on WP01-WP07 (all modes must be complete)

### Risks & Mitigations
- Risk: Integration issues between modes; Mitigation: Incremental testing during development

---

## Dependency & Execution Summary

```
WP01 (Base Classes)
  ↓
WP02 (Main Window)
  ↓
┌─────────────────────────────────────────────┐
│  WP03 (CATALOG) ──┬── WP04 (OBSERVE)  [P]  │
│        ↓          │          ↓              │
│  WP05 (PLAN)      │    (independent)        │
│        ↓          │                         │
│  WP06 (SHOP)      │                         │
│        ↓          │                         │
│  WP07 (PRODUCE)   │                         │
└─────────────────────────────────────────────┘
  ↓
WP08 (Integration & Polish)
```

**Sequence**: WP01 → WP02 → (WP03-WP07 with parallelization) → WP08

**Parallelization**:
- WP03 (CATALOG) and WP04 (OBSERVE) are fully independent - **safe for parallel agents**
- Within each mode WP, tab migrations are parallelizable
- Recommended: Claude handles WP01, WP02, WP07, WP08; Gemini handles WP03, WP04

**MVP Scope**: WP01 + WP02 + WP03 + WP04 delivers core navigation with CATALOG and OBSERVE modes.

---

## Subtask Index (Reference)

| Subtask | Summary | Work Package | Priority | Parallel? |
|---------|---------|--------------|----------|-----------|
| T001 | Create directory structure | WP01 | P0 | No |
| T002 | Create base __init__.py | WP01 | P0 | No |
| T003 | Implement StandardTabLayout | WP01 | P0 | Yes |
| T004 | Implement BaseMode | WP01 | P0 | Yes |
| T005 | Implement BaseDashboard | WP01 | P0 | Yes |
| T006 | Create package __init__.py files | WP01 | P0 | No |
| T007 | Create ModeManager | WP02 | P0 | No |
| T008 | Create mode bar | WP02 | P0 | No |
| T009 | Implement mode switching | WP02 | P0 | No |
| T010 | Implement keyboard shortcuts | WP02 | P0 | Yes |
| T011 | Implement tab state preservation | WP02 | P0 | No |
| T012 | Set default OBSERVE mode | WP02 | P0 | No |
| T013 | Style active mode button | WP02 | P0 | Yes |
| T014 | Create CatalogDashboard | WP03 | P1 | No |
| T015 | Create CatalogMode | WP03 | P1 | No |
| T016 | Integrate ingredients_tab | WP03 | P1 | Yes |
| T017 | Integrate products_tab | WP03 | P1 | Yes |
| T018 | Integrate recipes_tab | WP03 | P1 | Yes |
| T019 | Integrate finished_units_tab | WP03 | P1 | Yes |
| T020 | Integrate finished_goods_tab | WP03 | P1 | Yes |
| T021 | Integrate packages_tab | WP03 | P1 | Yes |
| T022 | Create ObserveDashboard | WP04 | P1 | No |
| T023 | Create ObserveMode | WP04 | P1 | No |
| T024 | Enhance dashboard_tab | WP04 | P1 | Yes |
| T025 | Create event_status_tab | WP04 | P1 | Yes |
| T026 | Create reports placeholder | WP04 | P1 | Yes |
| T027 | Create PlanDashboard | WP05 | P2 | No |
| T028 | Create PlanMode | WP05 | P2 | No |
| T029 | Integrate events_tab | WP05 | P2 | Yes |
| T030 | Create planning_workspace_tab | WP05 | P2 | Yes |
| T031 | Create ShopDashboard | WP06 | P2 | No |
| T032 | Create ShopMode | WP06 | P2 | No |
| T033 | Create shopping_lists_tab | WP06 | P2 | Yes |
| T034 | Create purchases_tab | WP06 | P2 | Yes |
| T035 | Integrate inventory_tab | WP06 | P2 | Yes |
| T036 | Create ProduceDashboard | WP07 | P2 | No |
| T037 | Create ProduceMode | WP07 | P2 | No |
| T038 | Merge production tabs | WP07 | P2 | Yes |
| T039 | Create assembly_tab | WP07 | P2 | Yes |
| T040 | Create packaging_tab | WP07 | P2 | Yes |
| T041 | Integrate recipients_tab | WP07 | P2 | Yes |
| T042 | Remove old navigation | WP08 | P3 | No |
| T043 | Test mode switching | WP08 | P3 | No |
| T044 | Unsaved changes dialog | WP08 | P3 | Yes |
| T045 | Empty state handling | WP08 | P3 | Yes |
| T046 | Verify dashboard performance | WP08 | P3 | No |
| T047 | Final cleanup | WP08 | P3 | No |
