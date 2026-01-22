# Work Packages: Finished Goods Inventory Service

**Feature**: 061-finished-goods-inventory-service
**Inputs**: Design documents from `/kitty-specs/061-finished-goods-inventory-service/`
**Prerequisites**: plan.md, spec.md, data-model.md, research.md

**Tests**: Unit and integration tests are included per Constitution Principle IV (TDD).

**Organization**: Fine-grained subtasks (Txxx) roll up into work packages (WPxx). Each work package is independently deliverable and testable.

**Prompt Files**: Each work package references a matching prompt file in `tasks/`.

---

## Work Package WP01: Foundation - Model and Constants (Priority: P0)

**Goal**: Create the FinishedGoodsAdjustment model, add relationships to existing models, add constants, and create the service module skeleton.
**Independent Test**: New model can be imported; relationships work; constants are accessible.
**Prompt**: `tasks/WP01-foundation-model-constants.md`

### Included Subtasks
- [x] T001 Create FinishedGoodsAdjustment model in `src/models/finished_goods_adjustment.py`
- [x] T002 [P] Add inventory_adjustments relationship to FinishedUnit in `src/models/finished_unit.py`
- [x] T003 [P] Add inventory_adjustments relationship to FinishedGood in `src/models/finished_good.py`
- [x] T004 [P] Add inventory constants to `src/utils/constants.py`
- [x] T005 Create service module skeleton in `src/services/finished_goods_inventory_service.py`

### Implementation Notes
- Follow data-model.md for exact schema definition
- Use helper function session pattern per research.md
- Model inherits from BaseModel
- Add CHECK constraints for XOR, count consistency, non-negative

### Parallel Opportunities
- T002, T003, T004 can proceed in parallel once T001 is complete

### Dependencies
- None (starting package)

### Risks & Mitigations
- Model import ordering issues → ensure __init__.py updates in WP06
- CHECK constraint syntax → follow existing model patterns (FinishedUnit)

---

## Work Package WP02: Core Service - Query Functions (Priority: P1)

**Goal**: Implement the three query functions: get_inventory_status, get_low_stock_items, get_total_inventory_value.
**Independent Test**: Queries return correct data for test fixtures; session parameter works correctly.
**Prompt**: `tasks/WP02-core-service-queries.md`

### Included Subtasks
- [x] T006 Implement get_inventory_status() with filtering by item_type, item_id, exclude_zero
- [ ] T007 Implement get_low_stock_items() with configurable threshold and item_type filter
- [ ] T008 Implement get_total_inventory_value() aggregating costs across both item types

### Implementation Notes
- All functions use helper function session pattern
- Return dicts (not ORM objects) to avoid detachment
- Use eager loading (joinedload) for relationships
- get_inventory_status returns: id, slug, display_name, inventory_count, current_cost, total_value

### Parallel Opportunities
- All three functions can be implemented in parallel

### Dependencies
- Depends on WP01 (service skeleton and model)

### Risks & Mitigations
- Cost calculation null handling → treat null costs as Decimal("0.0000")
- Large result sets → pagination not required for desktop app scale

---

## Work Package WP03: Core Service - Validation and Mutation (Priority: P1) 🎯 MVP

**Goal**: Implement check_availability, validate_consumption, and the critical adjust_inventory function with audit trail.
**Independent Test**: Availability checks return correct results; adjustments create audit records; negative inventory prevented.
**Prompt**: `tasks/WP03-core-service-validation-mutation.md`

### Included Subtasks
- [ ] T009 Implement check_availability() for checking if quantity is available
- [ ] T010 Implement validate_consumption() for pre-validation without modification
- [ ] T011 Implement adjust_inventory() with audit record creation and validation

### Implementation Notes
- adjust_inventory is the core function - all inventory changes flow through it
- Creates FinishedGoodsAdjustment record for every change
- Validates quantity won't result in negative inventory BEFORE modification
- Returns previous_count, new_count, quantity_change, adjustment_id
- Validate reason is in FINISHED_GOODS_ADJUSTMENT_REASONS
- Require notes when reason is "adjustment"

### Parallel Opportunities
- T009 and T010 can proceed in parallel; T011 depends on validation logic pattern

### Dependencies
- Depends on WP01 (model for audit records)
- Depends on WP02 (query patterns established)

### Risks & Mitigations
- Race conditions → session isolation handles within transaction; DB constraint is backup
- Audit record consistency → create record AFTER successful update, same session

---

## Work Package WP04: Integration - Assembly Service (Priority: P1)

**Goal**: Update assembly_service.py to use the new inventory service for all FU/FG inventory operations.
**Independent Test**: Assembly operations use inventory service; audit records created for all inventory changes.
**Prompt**: `tasks/WP04-integration-assembly-service.md`

### Included Subtasks
- [ ] T012 Update check_can_assemble to optionally use inventory service for availability
- [ ] T013 Update _record_assembly_impl FU consumption to use adjust_inventory
- [ ] T014 Update _record_assembly_impl nested FG consumption to use adjust_inventory
- [ ] T015 Update _record_assembly_impl FG creation to use adjust_inventory

### Implementation Notes
- Import finished_goods_inventory_service at top of file
- Replace `fu.inventory_count -= needed` with `adjust_inventory("finished_unit", fu.id, -needed, "assembly", notes=..., session=session)`
- Replace `finished_good.inventory_count += quantity` with `adjust_inventory("finished_good", fg.id, +quantity, "assembly", notes=..., session=session)`
- Pass session to all inventory service calls (F060 compliance)
- Preserve existing session threading pattern

### Parallel Opportunities
- T013, T014, T015 are in same function - must be done together

### Dependencies
- Depends on WP03 (adjust_inventory function)

### Risks & Mitigations
- Breaking assembly flow → comprehensive integration testing in WP08
- Line number references from research may shift → use grep to find exact locations

---

## Work Package WP05: Integration - Production and Other Callers (Priority: P1)

**Goal**: Update batch_production_service to use inventory service; find and update all other callers of deprecated model methods.
**Independent Test**: Production runs update inventory via service; no direct model method calls remain.
**Prompt**: `tasks/WP05-integration-production-other-callers.md`

### Included Subtasks
- [ ] T016 Update batch_production_service to use adjust_inventory after production completion
- [ ] T017 Find and update all callers of .is_available() to use check_availability
- [ ] T018 Find and update all callers of .update_inventory() to use adjust_inventory

### Implementation Notes
- Run grep to find all callers: `grep -rn "\.is_available(" src/` and `grep -rn "\.update_inventory(" src/`
- For production: add adjust_inventory call after actual_yield is recorded
- For other callers: may be in tests, UI, or other services
- Document all locations found and changes made

### Parallel Opportunities
- T016 is independent; T017 and T018 should be done together (same search)

### Dependencies
- Depends on WP03 (service functions available)

### Risks & Mitigations
- Unknown callers → thorough grep search; test suite will catch missed callers
- Production service structure may differ from research → verify current code

---

## Work Package WP06: Model Cleanup (Priority: P2)

**Goal**: Remove deprecated business logic methods from models; register new model in __init__.py.
**Independent Test**: Deprecated methods removed; new model properly exported; no import errors.
**Prompt**: `tasks/WP06-model-cleanup.md`

### Included Subtasks
- [ ] T019 Remove is_available() method from FinishedUnit model
- [ ] T020 Remove update_inventory() method from FinishedUnit model
- [ ] T021 Remove is_available() method from FinishedGood model
- [ ] T022 Remove update_inventory() method from FinishedGood model
- [ ] T023 Register FinishedGoodsAdjustment in `src/models/__init__.py`

### Implementation Notes
- KEEP: calculate_current_cost(), calculate_batches_needed(), can_assemble(), get_component_breakdown()
- REMOVE: is_available(), update_inventory() from both models
- Update __init__.py to export FinishedGoodsAdjustment
- Run tests after removal to catch any missed callers

### Parallel Opportunities
- T019-T022 can proceed in parallel

### Dependencies
- Depends on WP04, WP05 (all callers updated first)

### Risks & Mitigations
- Removing methods that are still called → ensure WP04, WP05 complete first
- Import cycle risks → careful ordering in __init__.py

---

## Work Package WP07: Unit Tests (Priority: P2)

**Goal**: Comprehensive unit tests for all service methods achieving >70% coverage.
**Independent Test**: All tests pass; coverage meets target.
**Prompt**: `tasks/WP07-unit-tests.md`

### Included Subtasks
- [ ] T024 Unit tests for get_inventory_status (all filtering scenarios)
- [ ] T025 Unit tests for check_availability and validate_consumption
- [ ] T026 Unit tests for adjust_inventory (positive, negative, audit record, prevents negative, session handling)
- [ ] T027 Unit tests for get_low_stock_items and get_total_inventory_value

### Implementation Notes
- Create `src/tests/services/test_finished_goods_inventory_service.py`
- Use existing test fixtures for FinishedUnit and FinishedGood
- Test with and without session parameter
- Test all filtering combinations
- Test error cases (nonexistent item, insufficient inventory, invalid reason)

### Parallel Opportunities
- All test subtasks can be written in parallel

### Dependencies
- Depends on WP03 (all service functions implemented)

### Risks & Mitigations
- Fixture complexity → reuse existing patterns from test_assembly_service.py
- Session testing → use mock session or actual session_scope

---

## Work Package WP08: Integration Tests and Verification (Priority: P2)

**Goal**: Integration tests for assembly and production flows; verify export/import preserves inventory.
**Independent Test**: All integration tests pass; export/import round-trip successful.
**Prompt**: `tasks/WP08-integration-tests-verification.md`

### Included Subtasks
- [ ] T028 Integration test for assembly service with inventory service (full flow)
- [ ] T029 Integration test for production service with inventory service (full flow)
- [ ] T030 Session atomicity tests (multi-step operations with rollback)
- [ ] T031 [P] Verify export includes inventory_count (add explicit test)
- [ ] T032 [P] Verify import restores inventory_count (add explicit test)

### Implementation Notes
- Assembly test: create components, assemble, verify audit records and counts
- Production test: create production run, verify inventory incremented
- Atomicity test: start assembly, fail mid-way, verify rollback
- Export/import tests: verify existing behavior, add explicit assertions

### Parallel Opportunities
- T031 and T032 can proceed in parallel with other tests

### Dependencies
- Depends on WP04, WP05 (integration complete)
- Depends on WP06 (cleanup complete)
- Depends on WP07 (unit tests establish patterns)

### Risks & Mitigations
- Complex fixture setup → use existing integration test patterns
- Export/import may already have tests → verify and extend rather than duplicate

---

## Dependency & Execution Summary

```
WP01 (Foundation)
  │
  ├──► WP02 (Queries)
  │       │
  │       └──► WP03 (Validation/Mutation) 🎯 MVP
  │               │
  │               ├──► WP04 (Assembly Integration)
  │               │       │
  │               └──► WP05 (Production Integration)
  │                       │
  │                       └──► WP06 (Model Cleanup)
  │                               │
  │                               └──► WP07 (Unit Tests)
  │                                       │
  │                                       └──► WP08 (Integration Tests)
```

**Sequence**: WP01 → WP02 → WP03 → WP04/WP05 (parallel) → WP06 → WP07 → WP08

**Parallelization**:
- After WP03: WP04 and WP05 can proceed in parallel
- Within WPs: Many subtasks marked [P] can be parallelized

**MVP Scope**: WP01 + WP02 + WP03 = Core service with all primitives. MVP is independently testable at WP03 completion.

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Create FinishedGoodsAdjustment model | WP01 | P0 | No |
| T002 | Add relationship to FinishedUnit | WP01 | P0 | Yes |
| T003 | Add relationship to FinishedGood | WP01 | P0 | Yes |
| T004 | Add inventory constants | WP01 | P0 | Yes |
| T005 | Create service module skeleton | WP01 | P0 | No |
| T006 | Implement get_inventory_status | WP02 | P1 | Yes |
| T007 | Implement get_low_stock_items | WP02 | P1 | Yes |
| T008 | Implement get_total_inventory_value | WP02 | P1 | Yes |
| T009 | Implement check_availability | WP03 | P1 | Yes |
| T010 | Implement validate_consumption | WP03 | P1 | Yes |
| T011 | Implement adjust_inventory | WP03 | P1 | No |
| T012 | Update check_can_assemble | WP04 | P1 | No |
| T013 | Update FU consumption in assembly | WP04 | P1 | No |
| T014 | Update nested FG consumption | WP04 | P1 | No |
| T015 | Update FG creation in assembly | WP04 | P1 | No |
| T016 | Update production service | WP05 | P1 | Yes |
| T017 | Find/update is_available callers | WP05 | P1 | No |
| T018 | Find/update update_inventory callers | WP05 | P1 | No |
| T019 | Remove FU.is_available | WP06 | P2 | Yes |
| T020 | Remove FU.update_inventory | WP06 | P2 | Yes |
| T021 | Remove FG.is_available | WP06 | P2 | Yes |
| T022 | Remove FG.update_inventory | WP06 | P2 | Yes |
| T023 | Register model in __init__.py | WP06 | P2 | No |
| T024 | Unit tests for get_inventory_status | WP07 | P2 | Yes |
| T025 | Unit tests for availability functions | WP07 | P2 | Yes |
| T026 | Unit tests for adjust_inventory | WP07 | P2 | Yes |
| T027 | Unit tests for low stock and value | WP07 | P2 | Yes |
| T028 | Integration test: assembly flow | WP08 | P2 | No |
| T029 | Integration test: production flow | WP08 | P2 | No |
| T030 | Session atomicity tests | WP08 | P2 | No |
| T031 | Verify export includes inventory | WP08 | P2 | Yes |
| T032 | Verify import restores inventory | WP08 | P2 | Yes |
