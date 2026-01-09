# Work Packages: Cost Architecture Refactor

**Feature**: 045-cost-architecture-refactor
**Inputs**: Design documents from `kitty-specs/045-cost-architecture-refactor/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md

**Tests**: Testing tasks included per spec requirements (FR-015, FR-016, FR-017).

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently deliverable and testable.

**Prompt Files**: Each work package references a matching prompt file in `tasks/`. Lane status is stored in YAML frontmatter (`lane: planned|doing|for_review|done`).

## Parallelization Summary

| Work Package | Agent | Can Parallelize With | Status |
|--------------|-------|---------------------|--------|
| WP01 | Claude | WP02 | planned |
| WP02 | Gemini | WP01 | planned |
| WP03 | Sequential | After WP01+WP02 | planned |
| WP04 | Sequential | After WP03 | planned |

---

## Work Package WP01: FinishedUnit Model + UI (Priority: P1) [P]

**Goal**: Remove `unit_cost` column and related methods from FinishedUnit model; remove cost display from UI detail view.
**Independent Test**: FinishedUnit model instantiates without unit_cost; detail view renders without cost section.
**Prompt**: `tasks/WP01-finished-unit-cost-removal.md`
**Agent Assignment**: Claude (parallel with WP02)

### Included Subtasks
- [x] T001 [P] Remove `unit_cost` column from FinishedUnit model in `src/models/finished_unit.py`
- [x] T002 [P] Remove CheckConstraint `ck_finished_unit_unit_cost_non_negative`
- [x] T003 [P] Remove `calculate_recipe_cost_per_item()` method
- [x] T004 [P] Remove `update_unit_cost_from_recipe()` method
- [x] T005 [P] Update `to_dict()` to remove `unit_cost` and `recipe_cost_per_item` fields
- [x] T006 [P] Remove cost display from `src/ui/forms/finished_unit_detail.py` (lines 167, 324)

### Implementation Notes
1. Open `src/models/finished_unit.py`
2. Remove line 98: `unit_cost = Column(Numeric(10, 4), ...)`
3. Remove line 133: CheckConstraint for unit_cost
4. Remove lines 171-196: `calculate_recipe_cost_per_item()` method
5. Remove lines 198-205: `update_unit_cost_from_recipe()` method
6. Update `to_dict()` method - remove lines 253-254 (unit_cost) and line 257 (recipe_cost_per_item)
7. Open `src/ui/forms/finished_unit_detail.py`
8. Remove cost display logic at lines 167 and 324

### Parallel Opportunities
- All subtasks within this WP can proceed together (same files)
- WP01 and WP02 can run in parallel (different model files)

### Dependencies
- None (starting package, parallel with WP02)

### Risks & Mitigations
- Risk: Breaking imports if other files reference removed methods
- Mitigation: Grep for method names before removing; defer service updates to WP03

---

## Work Package WP02: FinishedGood Model + UI (Priority: P1) [P]

**Goal**: Remove `total_cost` column and related methods from FinishedGood model; remove cost display from UI detail view.
**Independent Test**: FinishedGood model instantiates without total_cost; detail view renders without cost section.
**Prompt**: `tasks/WP02-finished-good-cost-removal.md`
**Agent Assignment**: Gemini (parallel with WP01)

### Included Subtasks
- [ ] T007 [P] Remove `total_cost` column from FinishedGood model in `src/models/finished_good.py`
- [ ] T008 [P] Remove CheckConstraint `ck_finished_good_total_cost_non_negative`
- [ ] T009 [P] Remove `calculate_component_cost()` method
- [ ] T010 [P] Remove `update_total_cost_from_components()` method
- [ ] T011 [P] Update `get_component_breakdown()` to remove cost fields from output
- [ ] T012 [P] Update `to_dict()` to remove `total_cost` and `component_cost` fields
- [ ] T013 [P] Remove cost display from `src/ui/forms/finished_good_detail.py` (lines 143, 426)

### Implementation Notes
1. Open `src/models/finished_good.py`
2. Remove line 76: `total_cost = Column(Numeric(10, 4), ...)`
3. Remove line 106: CheckConstraint for total_cost
4. Remove lines 114-142: `calculate_component_cost()` method
5. Remove lines 144-151: `update_total_cost_from_components()` method
6. Update `get_component_breakdown()`: Remove cost fields (unit_cost, total_cost) from component_info dict
7. Update `to_dict()`: Remove lines 312 (total_cost) and 315 (component_cost)
8. Open `src/ui/forms/finished_good_detail.py`
9. Remove cost display logic at lines 143 and 426

### Parallel Opportunities
- All subtasks within this WP can proceed together (same files)
- WP01 and WP02 can run in parallel (different model files)

### Dependencies
- None (starting package, parallel with WP01)

### Risks & Mitigations
- Risk: `get_component_breakdown()` may be called by services expecting cost fields
- Mitigation: Service updates in WP03 will handle downstream consumers

---

## Work Package WP03: Service Layer Updates (Priority: P2)

**Goal**: Update finished_unit_service.py and finished_good_service.py to remove all references to stored cost fields.
**Independent Test**: Services operate without accessing unit_cost or total_cost; no AttributeError on model access.
**Prompt**: `tasks/WP03-service-layer-updates.md`
**Agent Assignment**: Sequential (after WP01 + WP02 complete)

### Included Subtasks
- [ ] T014 Remove cost calculation references in `src/services/finished_unit_service.py`
- [ ] T015 Remove cost assignment/retrieval in `src/services/finished_good_service.py`
- [ ] T016 Verify UI tabs don't reference removed service methods

### Implementation Notes

**finished_unit_service.py changes**:
- Line 587: Remove `fifo_cost = FinishedUnitService._calculate_fifo_unit_cost(unit)`
- Line 743: Remove `purchase_cost = FinishedUnitService._get_inventory_item_unit_cost(...)`
- Line 811: Remove `unit_cost = Decimal(str(purchase.unit_cost))`
- Line 1037: Remove `return FinishedUnitService.calculate_unit_cost(finished_unit_id)`
- Remove any private methods: `_calculate_fifo_unit_cost()`, `_get_inventory_item_unit_cost()`, `calculate_unit_cost()`

**finished_good_service.py changes**:
- Line 277: Remove `finished_good.total_cost = total_cost_with_packaging`
- Lines 1131, 1134: Remove cost retrieval from components
- Lines 1200, 1218, 1275-1276, 1294-1295: Remove cost fields from breakdown outputs
- Lines 1339, 1389, 1396, 1405, 1408, 1410, 1479, 1502: Remove assembly cost calculations

**Strategy**: Search for `.unit_cost` and `.total_cost` in these files and remove/refactor each occurrence.

### Parallel Opportunities
- T014 and T015 can run in parallel (different service files)
- T016 depends on T014/T015 completion

### Dependencies
- Depends on WP01 (FinishedUnit model changes)
- Depends on WP02 (FinishedGood model changes)

### Risks & Mitigations
- Risk: Service methods may be called from UI or other services
- Mitigation: Grep for method names across codebase; update or remove callers
- Risk: Breaking changes to return values
- Mitigation: Review all consumers of modified methods

---

## Work Package WP04: Export Version + Test Updates (Priority: P3)

**Goal**: Bump export version to 4.1; update and verify tests; validate full import/export cycle.
**Independent Test**: Export produces version 4.1; all pytest tests pass; data survives export/import cycle.
**Prompt**: `tasks/WP04-export-version-and-tests.md`
**Agent Assignment**: Sequential (after WP03 complete)

### Included Subtasks
- [ ] T017 Bump export version from "4.0" to "4.1" in `src/services/import_export_service.py:1138`
- [ ] T018 Run pytest to identify all failing tests
- [ ] T019 Update failing tests that reference unit_cost or total_cost
- [ ] T020 Verify sample data files load successfully (already compliant per research)
- [ ] T021 Verify full import/export cycle preserves data integrity

### Implementation Notes

**Version bump**:
- Open `src/services/import_export_service.py`
- Line 1138: Change `"version": "4.0"` to `"version": "4.1"`

**Test updates**:
1. Run `pytest src/tests -v` to identify failures
2. Common fixes needed:
   - Remove assertions on `unit_cost` or `total_cost` fields
   - Update test fixtures that set these fields
   - Remove tests for removed methods (calculate_recipe_cost_per_item, etc.)

**Files likely needing test updates** (from research.md):
- `src/tests/test_models.py`
- `src/tests/services/test_import_export_service.py`
- Any test file referencing FinishedUnit.unit_cost or FinishedGood.total_cost

**Validation**:
1. Export existing data: Use app's export function
2. Reset database
3. Import exported data
4. Verify all records restored correctly

### Parallel Opportunities
- T17 (version bump) can proceed immediately
- T18-T21 must be sequential (run tests, fix, verify)

### Dependencies
- Depends on WP03 (service layer must be updated first)

### Risks & Mitigations
- Risk: Hidden test dependencies on cost fields
- Mitigation: Run full test suite; grep for `unit_cost` and `total_cost` in test files
- Risk: Import/export cycle fails
- Mitigation: Test with minimal data first, then full dataset

---

## Dependency & Execution Summary

```
WP01 (FinishedUnit) ──┬──> WP03 (Services) ──> WP04 (Tests/Version)
                      │
WP02 (FinishedGood) ──┘
     [PARALLEL]           [SEQUENTIAL]        [SEQUENTIAL]
```

- **Parallel Phase**: WP01 + WP02 can execute simultaneously (different model files)
- **Sequential Phase**: WP03 depends on both WP01 and WP02; WP04 depends on WP03
- **MVP Scope**: WP01 + WP02 + WP03 (core functionality); WP04 completes the feature

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Remove unit_cost column | WP01 | P1 | Yes |
| T002 | Remove unit_cost constraint | WP01 | P1 | Yes |
| T003 | Remove calculate_recipe_cost_per_item() | WP01 | P1 | Yes |
| T004 | Remove update_unit_cost_from_recipe() | WP01 | P1 | Yes |
| T005 | Update FinishedUnit.to_dict() | WP01 | P1 | Yes |
| T006 | Remove cost from finished_unit_detail.py | WP01 | P1 | Yes |
| T007 | Remove total_cost column | WP02 | P1 | Yes |
| T008 | Remove total_cost constraint | WP02 | P1 | Yes |
| T009 | Remove calculate_component_cost() | WP02 | P1 | Yes |
| T010 | Remove update_total_cost_from_components() | WP02 | P1 | Yes |
| T011 | Update get_component_breakdown() | WP02 | P1 | Yes |
| T012 | Update FinishedGood.to_dict() | WP02 | P1 | Yes |
| T013 | Remove cost from finished_good_detail.py | WP02 | P1 | Yes |
| T014 | Update finished_unit_service.py | WP03 | P2 | Yes |
| T015 | Update finished_good_service.py | WP03 | P2 | Yes |
| T016 | Verify UI tabs | WP03 | P2 | No |
| T017 | Bump export version to 4.1 | WP04 | P3 | Yes |
| T018 | Run pytest, identify failures | WP04 | P3 | No |
| T019 | Update failing tests | WP04 | P3 | No |
| T020 | Verify sample data loads | WP04 | P3 | No |
| T021 | Verify import/export cycle | WP04 | P3 | No |

---

## Agent Assignment Summary

| Work Package | Recommended Agent | Rationale |
|--------------|-------------------|-----------|
| WP01 | Claude | Lead agent handles FinishedUnit (primary model) |
| WP02 | Gemini | Parallel execution on FinishedGood |
| WP03 | Claude | Service layer requires understanding of both models |
| WP04 | Claude | Test updates and validation require full context |
