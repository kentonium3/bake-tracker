# Work Packages: Event Management & Planning Data Model

**Feature**: 068-event-management-planning-data-model
**Inputs**: Design documents from `/kitty-specs/068-event-management-planning-data-model/`
**Prerequisites**: plan.md, spec.md, data-model.md, research.md

**Multi-Agent Strategy**: Claude (lead), Gemini (parallel worker), Codex (parallel worker)
- WP01-WP02: Sequential (Claude lead)
- WP03-WP04: Parallel after WP02 (Gemini + Codex)
- WP05: Sequential after WP03-WP04 (Claude lead)

**Tests**: Unit tests required for service layer per Constitution Principle IV (>70% coverage).

---

## Work Package WP01: Planning Models Foundation (Priority: P0)

**Goal**: Create all new planning model files and extend existing Event/PlanningSnapshot models with new fields.
**Independent Test**: Models import without error; SQLAlchemy creates tables correctly.
**Prompt**: `tasks/WP01-planning-models-foundation.md`
**Agent Assignment**: Claude (lead) - Foundation must be correct before parallel work.
**Estimated Size**: ~450 lines (7 subtasks)

### Included Subtasks
- [x] T001 [P] Add PlanState enum to `src/models/event.py`
- [x] T002 Add expected_attendees field to Event model
- [x] T003 Add plan_state field to Event model (uses PlanState enum)
- [x] T004 Add planning relationships to Event model (4 new relationships)
- [x] T005 [P] Create EventRecipe model in `src/models/event_recipe.py`
- [x] T006 [P] Create EventFinishedGood model in `src/models/event_finished_good.py`
- [x] T007 [P] Create BatchDecision model in `src/models/batch_decision.py`

### Implementation Notes
- Follow SQLAlchemy patterns from existing models (EventProductionTarget)
- All new models inherit from BaseModel
- Use CASCADE delete for event_id, RESTRICT for recipe_id/finished_good_id/finished_unit_id
- Composite unique constraints on (event_id, recipe_id) or (event_id, finished_good_id)

### Parallel Opportunities
- T001 (enum) and T005-T007 (new model files) can be written in parallel
- T002-T004 (Event model changes) should be sequential within the file

### Dependencies
- None (starting package)

### Risks & Mitigations
- **Circular imports**: Follow existing pattern of importing models in `__init__.py`
- **FK ordering**: Define models in dependency order in `__init__.py`

---

## Work Package WP02: Remaining Models & Service Layer (Priority: P0)

**Goal**: Complete model layer (PlanAmendment, PlanningSnapshot updates, __init__.py) and extend EventService with planning CRUD.
**Independent Test**: Service methods work; unit tests pass with >70% coverage.
**Prompt**: `tasks/WP02-service-layer-extension.md`
**Agent Assignment**: Claude (lead) - Service patterns critical for UI work.
**Estimated Size**: ~500 lines (7 subtasks)

### Included Subtasks
- [ ] T008 [P] Create PlanAmendment model with AmendmentType enum in `src/models/plan_amendment.py`
- [ ] T009 [P] Add SnapshotType enum and fields to `src/models/planning_snapshot.py`
- [ ] T010 Update `src/models/__init__.py` with new exports
- [ ] T011 Add planning CRUD methods to `src/services/event_service.py`
- [ ] T012 Add validation for expected_attendees (positive integer or None)
- [ ] T013 Ensure plan_state is display-only (no direct transitions in F068)
- [ ] T014 Write unit tests in `src/tests/test_event_planning.py`

### Implementation Notes
- EventService already has 1900+ lines; add new methods in clearly marked section
- Follow existing session management pattern (session passed to methods)
- Plan_state transitions are implemented in F077; F068 just stores the field

### Parallel Opportunities
- T008-T009 (model files) can be written in parallel
- T011-T014 (service work) should be sequential

### Dependencies
- Depends on WP01 (models must exist before service can use them)

### Risks & Mitigations
- **Service size**: Add methods at end of file with clear section marker
- **Test isolation**: Use fresh session for each test

---

## Work Package WP03: Planning Tab UI (Priority: P1) 🔀 PARALLELIZABLE

**Goal**: Create Planning workspace tab with event list view and action buttons.
**Independent Test**: Tab displays in application; event list shows existing events.
**Prompt**: `tasks/WP03-planning-tab-ui.md`
**Agent Assignment**: Gemini - Can run parallel with WP04 after WP02.
**Estimated Size**: ~400 lines (6 subtasks)

### Included Subtasks
- [ ] T015 Create Planning tab skeleton in `src/ui/planning_tab.py`
- [ ] T016 Implement event list view using DataTable widget
- [ ] T017 Add columns: Name, Date, Expected Attendees, Plan State
- [ ] T018 Implement event selection handling
- [ ] T019 Add action buttons: Create, Edit, Delete
- [ ] T020 Add status bar and refresh functionality

### Implementation Notes
- Follow recipes_tab.py pattern for structure
- Use DataTable widget (already exists in codebase)
- Sort events by date (most recent first)
- Display NULL expected_attendees as "-"

### Parallel Opportunities
- This entire WP can run parallel with WP04 (different files)

### Dependencies
- Depends on WP02 (service layer must exist)

### Risks & Mitigations
- **DataTable compatibility**: Study existing usage in recipes_tab.py
- **Event loading**: Use service layer, not direct DB access

---

## Work Package WP04: Event CRUD Dialogs (Priority: P1) 🔀 PARALLELIZABLE

**Goal**: Create Create/Edit/Delete dialogs for event management.
**Independent Test**: User can create, edit, and delete events from Planning tab.
**Prompt**: `tasks/WP04-event-crud-dialogs.md`
**Agent Assignment**: Codex - Can run parallel with WP03 after WP02.
**Estimated Size**: ~450 lines (6 subtasks)

### Included Subtasks
- [ ] T021 Create event planning form base in `src/ui/forms/event_planning_form.py`
- [ ] T022 Implement Create Event dialog with name, date picker, attendees
- [ ] T023 Implement Edit Event dialog (pre-populated fields)
- [ ] T024 Implement Delete confirmation dialog
- [ ] T025 Add validation feedback (name required, date required, attendees positive)
- [ ] T026 Wire dialogs to Planning tab action buttons

### Implementation Notes
- Follow recipe_form.py pattern for dialog structure
- Use CTkInputDialog or custom CTkToplevel for dialogs
- DatePicker: Use tkcalendar or simple entry with validation
- Callback pattern: Pass on_save/on_cancel callbacks

### Parallel Opportunities
- This entire WP can run parallel with WP03 (different files)

### Dependencies
- Depends on WP02 (service layer must exist)

### Risks & Mitigations
- **Date picker**: May need external library (tkcalendar) or use text entry with validation
- **Dialog focus**: Ensure dialogs are modal and grab focus

---

## Work Package WP05: Integration & Import/Export (Priority: P2)

**Goal**: Wire Planning tab into app, update import/export, validate full workflow.
**Independent Test**: Full CRUD flow works; export/import preserves planning data.
**Prompt**: `tasks/WP05-integration-import-export.md`
**Agent Assignment**: Claude (lead) - Integration requires coordination.
**Estimated Size**: ~350 lines (5 subtasks)

### Included Subtasks
- [ ] T027 Add Planning tab to main application window
- [ ] T028 Add new planning tables to import/export service
- [ ] T029 Integration test: Create event → Edit → Delete with cascade
- [ ] T030 Validate import/export preserves all planning fields
- [ ] T031 Final UI polish and edge case handling

### Implementation Notes
- Add import/export in dependency order: event_recipes, event_finished_goods, batch_decisions, plan_amendments
- Test cascade: Delete event should remove all associations
- Follow Constitution Principle VI: Export/Reset/Import for schema validation

### Parallel Opportunities
- None - this is integration/finalization work

### Dependencies
- Depends on WP03 AND WP04 (both UI components must be complete)

### Risks & Mitigations
- **Import order**: Tables must be imported after their FK targets
- **Cascade testing**: Ensure foreign key constraints work correctly

---

## Dependency & Execution Summary

```
WP01 (Models) ─────────────────────────────────────────────┐
    │                                                       │
    ▼                                                       │
WP02 (Service) ────────────────────────────────────────────┤
    │                                                       │
    ├──────────────┬───────────────────────────────────────┤
    │              │                                        │
    ▼              ▼                                        │
WP03 (Tab)     WP04 (Dialogs)     ← PARALLEL (Gemini/Codex)│
    │              │                                        │
    └──────────────┴───────────────────────────────────────┘
                   │
                   ▼
              WP05 (Integration) ← Claude (lead)
```

**Parallelization Strategy**:
- **Sequential (Claude lead)**: WP01 → WP02 (Foundation must be solid)
- **Parallel (Gemini + Codex)**: WP03 ∥ WP04 (Independent files, same dependencies)
- **Sequential (Claude lead)**: WP05 (Integration after parallel work merges)

**MVP Scope**: WP01-WP04 delivers functional event management in Planning workspace.

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Add PlanState enum | WP01 | P0 | Yes |
| T002 | Add expected_attendees field | WP01 | P0 | No |
| T003 | Add plan_state field | WP01 | P0 | No |
| T004 | Add planning relationships | WP01 | P0 | No |
| T005 | Create EventRecipe model | WP01 | P0 | Yes |
| T006 | Create EventFinishedGood model | WP01 | P0 | Yes |
| T007 | Create BatchDecision model | WP01 | P0 | Yes |
| T008 | Create PlanAmendment model | WP02 | P0 | Yes |
| T009 | Update PlanningSnapshot | WP02 | P0 | Yes |
| T010 | Update models/__init__.py | WP02 | P0 | No |
| T011 | Add planning CRUD to EventService | WP02 | P0 | No |
| T012 | Add expected_attendees validation | WP02 | P0 | No |
| T013 | Ensure plan_state display-only | WP02 | P0 | No |
| T014 | Write unit tests | WP02 | P0 | No |
| T015 | Create Planning tab skeleton | WP03 | P1 | Yes |
| T016 | Implement event list view | WP03 | P1 | No |
| T017 | Add list columns | WP03 | P1 | No |
| T018 | Implement selection handling | WP03 | P1 | No |
| T019 | Add action buttons | WP03 | P1 | No |
| T020 | Add status bar and refresh | WP03 | P1 | No |
| T021 | Create event form base | WP04 | P1 | No |
| T022 | Implement Create dialog | WP04 | P1 | No |
| T023 | Implement Edit dialog | WP04 | P1 | No |
| T024 | Implement Delete dialog | WP04 | P1 | No |
| T025 | Add validation feedback | WP04 | P1 | No |
| T026 | Wire dialogs to tab | WP04 | P1 | No |
| T027 | Add Planning tab to app | WP05 | P2 | No |
| T028 | Update import/export service | WP05 | P2 | No |
| T029 | Integration test CRUD flow | WP05 | P2 | No |
| T030 | Validate import/export | WP05 | P2 | No |
| T031 | Final UI polish | WP05 | P2 | No |
