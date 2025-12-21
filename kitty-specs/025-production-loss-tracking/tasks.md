# Work Packages: Production Loss Tracking

**Inputs**: Design documents from `/kitty-specs/025-production-loss-tracking/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md

**Tests**: Included per Constitution Principle IV (Test-Driven Development) requiring >70% service layer coverage.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently deliverable and testable.

**Prompt Files**: Each work package references a matching prompt file in `kitty-specs/025-production-loss-tracking/tasks/planned/`.

## Subtask Format: `[Txxx] [P?] Description`
- **[P]** indicates the subtask can proceed in parallel (different files/components).
- Paths are relative to repository root.

---

## Work Package WP01: Models & Enums (Priority: P0)

**Goal**: Create ProductionStatus/LossCategory enums and ProductionLoss entity with all relationships.
**Independent Test**: Models can be imported and instantiated; database creates tables without errors.
**Prompt**: `kitty-specs/025-production-loss-tracking/tasks/planned/WP01-models-and-enums.md`

### Included Subtasks
- [x] T001 [P] Create ProductionStatus enum in `src/models/enums.py`
- [x] T002 [P] Create LossCategory enum in `src/models/enums.py`
- [x] T003 Add production_status column to ProductionRun in `src/models/production_run.py`
- [x] T004 Add loss_quantity column to ProductionRun in `src/models/production_run.py`
- [x] T005 Add constraints and index for loss tracking fields on ProductionRun
- [x] T006 Create ProductionLoss model in `src/models/production_loss.py`
- [x] T007 Add losses relationship backref to ProductionRun
- [x] T008 Update `src/models/__init__.py` to export new model and enums

### Implementation Notes
1. Create or enhance `src/models/enums.py` with both enum classes
2. Modify ProductionRun model to add new columns with defaults for backward compatibility
3. Create ProductionLoss as new model file following existing patterns (BaseModel, UUID support)
4. Add bidirectional relationship between ProductionRun and ProductionLoss
5. Ensure models/__init__.py exports all new symbols

### Parallel Opportunities
- T001 and T002 can be done simultaneously (different enum classes)
- All other subtasks are sequential (dependency chain)

### Dependencies
- None (foundational package)

### Risks & Mitigations
- Session management: Follow CLAUDE.md patterns for session passing
- Import cycle: Keep relationship imports in TYPE_CHECKING block if needed

---

## Work Package WP02: Service Layer - Core Loss Recording (Priority: P1) MVP

**Goal**: Enhance `record_batch_production()` with loss validation, status calculation, and ProductionLoss creation.
**Independent Test**: Service function accepts loss parameters, validates actual <= expected, creates ProductionLoss records, returns loss data.
**Prompt**: `kitty-specs/025-production-loss-tracking/tasks/planned/WP02-service-loss-recording.md`

### Included Subtasks
- [x] T009 Add loss_category and loss_notes parameters to `record_batch_production()`
- [x] T010 Add validation: actual_yield <= expected_yield (raise ValueError if exceeded)
- [x] T011 Calculate loss_quantity and determine production_status from enum
- [x] T012 Create ProductionLoss record when loss_quantity > 0
- [x] T013 Return loss data (loss_quantity, production_status, loss record id) in result dict
- [x] T014 Update `get_production_history()` to include production_status and loss_quantity
- [x] T015 Add optional eager-loading of losses relationship in history queries

### Implementation Notes
1. Add parameters to function signature: `loss_category: Optional[LossCategory] = None`, `loss_notes: Optional[str] = None`
2. Validation before FIFO consumption (fail fast)
3. Status determination: COMPLETE if loss_quantity=0, TOTAL_LOSS if actual_yield=0, else PARTIAL_LOSS
4. ProductionLoss creation uses same per_unit_cost calculated for good units
5. Update `_production_run_to_dict()` helper to include new fields

### Parallel Opportunities
- T014 and T015 (history query updates) can proceed after T009-T013 complete

### Dependencies
- Depends on WP01 (models must exist)

### Risks & Mitigations
- Session detachment: Use session passing pattern per CLAUDE.md
- Cost accuracy: Snapshot per_unit_cost at creation time, not later recalculation

---

## Work Package WP03: UI - Record Production Dialog (Priority: P1) MVP

**Goal**: Enhance RecordProductionDialog with loss detection, expandable details section, and cost breakdown display.
**Independent Test**: Dialog shows loss quantity auto-calculated, loss section expands on loss detection, cost breakdown updates in real-time.
**Prompt**: `kitty-specs/025-production-loss-tracking/tasks/planned/WP03-ui-record-production.md`

### Included Subtasks
- [x] T016 Add loss_quantity calculation on actual_yield entry change
- [x] T017 Add read-only loss_quantity display label
- [x] T018 Create expandable loss details frame (collapsed by default)
- [x] T019 Add loss category dropdown (CTkOptionMenu) with LossCategory values
- [x] T020 Add loss notes textbox (CTkTextbox) in expandable section
- [x] T021 Implement auto-expand behavior when loss_quantity > 0
- [x] T022 Add cost breakdown display (good units vs lost units with $ amounts)
- [x] T023 Update real-time cost calculation as actual_yield changes
- [x] T024 Add validation: prevent actual_yield > expected_yield with error message
- [x] T025 Update confirmation dialog to include loss information summary

### Implementation Notes
1. Add new widgets after existing notes field, before availability display
2. Use CTkFrame for expandable section with grid_remove()/grid() for collapse/expand
3. Loss category dropdown uses enum display values with mapping to enum
4. Cost breakdown shows: "Good units (N): $X.XX" and "Lost units (N): $X.XX" when applicable
5. Validation shows error dialog and prevents confirm action
6. Pass loss_category and loss_notes to service on confirm

### Parallel Opportunities
- T016-T017 (calculation/display) can proceed with T18-T21 (expandable section) in parallel
- T22-T23 (cost display) independent of T24-T25 (validation/confirmation)

### Dependencies
- Depends on WP02 (service layer must accept loss parameters)

### Risks & Mitigations
- UI clutter: Expandable section keeps default view clean
- User confusion: Clear labeling and auto-expand guides user to loss details

---

## Work Package WP04: UI - Production History (Priority: P1)

**Goal**: Add loss visibility to production history table with status indicators.
**Independent Test**: History table shows loss quantity and status columns with visual differentiation.
**Prompt**: `kitty-specs/025-production-loss-tracking/tasks/planned/WP04-ui-production-history.md`

### Included Subtasks
- [x] T026 Add "Loss" column to production history table
- [x] T027 Add "Status" column to production history table
- [x] T028 Implement status-based visual indicators (color/styling)
- [x] T029 Handle display of "-" for records with no losses

### Implementation Notes
1. Identify history table location in production_dashboard_tab.py
2. Add columns after existing yield columns
3. Status indicators: Complete (default/green), Partial Loss (yellow/warning), Total Loss (red/error)
4. Loss column shows integer or "-" for 0
5. Map production_status enum values to display labels

### Parallel Opportunities
- T026 and T027 can be added simultaneously (adjacent columns)

### Dependencies
- Depends on WP02 (history query must return status/loss data)

### Risks & Mitigations
- Table width: May need column width adjustments for readability

---

## Work Package WP05: Service Layer - Export/Import (Priority: P2)

**Goal**: Update export/import for v1.1 schema with loss data and backward compatibility.
**Independent Test**: Export includes loss fields; import handles both v1.0 and v1.1 data correctly.
**Prompt**: `kitty-specs/025-production-loss-tracking/tasks/planned/WP05-service-export-import.md`

### Included Subtasks
- [x] T030 Update `export_production_history()` for v1.1 schema with loss fields
- [x] T031 Add losses array to export with ProductionLoss data
- [x] T032 Update `import_production_history()` to handle loss records
- [x] T033 Add v1.0 import transform: set production_status="complete", loss_quantity=0

### Implementation Notes
1. Bump version to "1.1" in export
2. Add production_status, loss_quantity to exported runs
3. Include losses array with each run's ProductionLoss records
4. Import: detect version and apply transform for v1.0 data
5. Import: create ProductionLoss records from losses array

### Parallel Opportunities
- T030-T031 (export) can proceed with T032-T033 (import) in parallel

### Dependencies
- Depends on WP01 (models) and WP02 (service layer)

### Risks & Mitigations
- Data loss on v1.0 import: Transform adds sensible defaults, no actual loss
- Version detection: Use explicit version field, default to "1.0" if missing

---

## Work Package WP06: Unit Tests (Priority: P1)

**Goal**: Comprehensive unit tests for loss recording functionality per Constitution TDD principle.
**Independent Test**: All tests pass with >70% coverage on modified service functions.
**Prompt**: `kitty-specs/025-production-loss-tracking/tasks/planned/WP06-unit-tests.md`

### Included Subtasks
- [x] T034 Test complete production (no loss) - verify status=COMPLETE, no ProductionLoss
- [x] T035 Test partial loss recording - verify status=PARTIAL_LOSS, ProductionLoss created
- [x] T036 Test total loss recording - verify status=TOTAL_LOSS, inventory unchanged
- [x] T037 Test validation: actual_yield > expected_yield raises ValueError
- [x] T038 Test loss record creation with specific category
- [x] T039 Test loss record creation with notes
- [x] T040 Test cost calculations: total_loss_cost = loss_quantity * per_unit_cost
- [x] T041 Test ProductionLoss model creation and relationships

### Implementation Notes
1. Extend existing test file: `src/tests/services/test_batch_production_service.py`
2. Use existing test fixtures for recipes, finished units, inventory
3. Each test should be independent with fresh database state
4. Verify both service return values and database state
5. Test edge cases: 0 actual yield, exact expected yield, over expected yield

### Parallel Opportunities
- All test cases can be written in parallel (independent test functions)

### Dependencies
- Depends on WP01 and WP02 (code to test must exist)

### Risks & Mitigations
- Fixture complexity: Reuse existing test fixtures where possible

---

## Work Package WP07: Data Migration & Documentation (Priority: P2)

**Goal**: Enable migration of existing data to new schema and document procedure.
**Independent Test**: Export/transform/import cycle preserves all existing data with new defaults.
**Prompt**: `kitty-specs/025-production-loss-tracking/tasks/planned/WP07-data-migration.md`

### Included Subtasks
- [x] T042 Create migration transform script for existing exported data
- [x] T043 Test export/transform/import cycle with sample data
- [x] T044 Document migration procedure in feature documentation

### Implementation Notes
1. Transform adds: production_status="complete", loss_quantity=0, losses=[]
2. Script can be Python or integrated into import function
3. Document: (1) Export all data, (2) Run transform, (3) Reset DB, (4) Import
4. Constitution Principle VI - no Alembic migrations needed

### Parallel Opportunities
- T42 (script) and T44 (docs) can proceed in parallel

### Dependencies
- Depends on WP05 (export/import must be complete)

### Risks & Mitigations
- Data loss: Full export before any schema change is mandatory

---

## Dependency & Execution Summary

```
WP01 (Models)
    |
    v
WP02 (Service Core) -----> WP06 (Tests) [can start after WP02]
    |
    +---> WP03 (UI Dialog)
    |
    +---> WP04 (UI History)
    |
    +---> WP05 (Export/Import) --> WP07 (Migration)
```

- **Sequence**: WP01 -> WP02 -> (WP03, WP04, WP05, WP06 in parallel) -> WP07
- **Parallelization**: After WP02 completes, WP03-WP06 can all proceed in parallel
- **MVP Scope**: WP01 + WP02 + WP03 + WP04 + WP06 (core recording and visibility with tests)

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Create ProductionStatus enum | WP01 | P0 | Yes |
| T002 | Create LossCategory enum | WP01 | P0 | Yes |
| T003 | Add production_status column to ProductionRun | WP01 | P0 | No |
| T004 | Add loss_quantity column to ProductionRun | WP01 | P0 | No |
| T005 | Add constraints and index for loss tracking | WP01 | P0 | No |
| T006 | Create ProductionLoss model | WP01 | P0 | No |
| T007 | Add losses relationship to ProductionRun | WP01 | P0 | No |
| T008 | Update models/__init__.py exports | WP01 | P0 | No |
| T009 | Add loss parameters to record_batch_production() | WP02 | P1 | No |
| T010 | Add yield validation | WP02 | P1 | No |
| T011 | Calculate loss_quantity and production_status | WP02 | P1 | No |
| T012 | Create ProductionLoss record | WP02 | P1 | No |
| T013 | Return loss data in result dict | WP02 | P1 | No |
| T014 | Update get_production_history() with loss fields | WP02 | P1 | Yes |
| T015 | Add eager-loading for losses relationship | WP02 | P1 | Yes |
| T016 | Add loss_quantity calculation on yield change | WP03 | P1 | Yes |
| T017 | Add read-only loss_quantity display | WP03 | P1 | Yes |
| T018 | Create expandable loss details frame | WP03 | P1 | Yes |
| T019 | Add loss category dropdown | WP03 | P1 | Yes |
| T020 | Add loss notes textbox | WP03 | P1 | Yes |
| T021 | Implement auto-expand on loss detection | WP03 | P1 | Yes |
| T022 | Add cost breakdown display | WP03 | P1 | Yes |
| T023 | Update real-time cost calculation | WP03 | P1 | Yes |
| T024 | Add yield validation in UI | WP03 | P1 | Yes |
| T025 | Update confirmation dialog with loss info | WP03 | P1 | Yes |
| T026 | Add Loss column to history table | WP04 | P1 | Yes |
| T027 | Add Status column to history table | WP04 | P1 | Yes |
| T028 | Implement status visual indicators | WP04 | P1 | No |
| T029 | Handle "-" display for no-loss records | WP04 | P1 | No |
| T030 | Update export for v1.1 schema | WP05 | P2 | Yes |
| T031 | Add losses array to export | WP05 | P2 | Yes |
| T032 | Update import to handle loss records | WP05 | P2 | Yes |
| T033 | Add v1.0 import transform | WP05 | P2 | Yes |
| T034 | Test complete production | WP06 | P1 | Yes |
| T035 | Test partial loss | WP06 | P1 | Yes |
| T036 | Test total loss | WP06 | P1 | Yes |
| T037 | Test yield validation | WP06 | P1 | Yes |
| T038 | Test loss with category | WP06 | P1 | Yes |
| T039 | Test loss with notes | WP06 | P1 | Yes |
| T040 | Test cost calculations | WP06 | P1 | Yes |
| T041 | Test ProductionLoss model | WP06 | P1 | Yes |
| T042 | Create migration transform script | WP07 | P2 | Yes |
| T043 | Test export/transform/import cycle | WP07 | P2 | No |
| T044 | Document migration procedure | WP07 | P2 | Yes |
