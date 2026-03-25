# Work Packages: Fix Plan Mode FG and Batch Scoping

**Inputs**: Design documents from `kitty-specs/103-fix-plan-mode-fg-batch-scoping/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md

**Tests**: Service layer changes require unit/integration tests per constitution (Principle IV).

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package must be independently deliverable and testable.

**Prompt Files**: Each work package references a matching prompt file in `tasks/`.

---

## Work Package WP01: Service Layer Fixes (Priority: P1) MVP

**Goal**: Fix the three service-layer bugs: FG query, stale record cleanup, and batch decomposition scoping.
**Independent Test**: Unit tests verify (1) FGs returned match selected recipes, (2) stale EventFinishedGood records are deleted on recipe deselection, (3) batch decomposition excludes deselected recipes.
**Prompt**: `tasks/WP01-service-layer-fixes.md`
**Estimated size**: ~400 lines

### Included Subtasks
- [x] T001 Create `get_finished_units_for_event_recipes()` in `src/services/event_service.py`
- [x] T002 Create wrapper `get_fgs_for_selected_recipes()` that maps FinishedUnits back to FinishedGoods
- [x] T003 Simplify `remove_invalid_fg_selections()` to use direct recipe_id check
- [x] T004 Add recipe-scoping filter to `decompose_event_to_fu_requirements()` in `src/services/planning_service.py`
- [x] T005 Write tests for all three fixes

### Implementation Notes
- T001: Join FinishedUnit -> Recipe -> EventRecipe, with optional category/yield_type filters
- T002: Query FUs, then look up their corresponding bare FinishedGoods to preserve EventFinishedGood save flow
- T003: Instead of recursive `check_fg_availability()`, directly check if the FU's recipe_id is in EventRecipe
- T004: After querying EventFinishedGood records, filter FURequirements where recipe is not in EventRecipe
- T005: Test each function independently with fixture data

### Parallel Opportunities
- T001 and T004 can be developed in parallel (different files)

### Dependencies
- None (starting package)

### Risks & Mitigations
- **Risk**: Breaking existing assembly/bundle logic. **Mitigation**: Keep existing `get_available_finished_goods()` and `check_fg_availability()` intact — they may be needed for future assembly planning. New function is additive.
- **Risk**: FinishedGood lookup from FinishedUnit misses edge cases. **Mitigation**: Query through FinishedGoodComponent junction table, handle case where FU has no bare FG.

---

## Work Package WP02: UI Integration (Priority: P1)

**Goal**: Wire the service fixes into the FG selection frame UI so the planner sees correct finished goods and batch options.
**Independent Test**: Launch app, select recipes for an event, verify FG selection shows correct items. Deselect a recipe, verify its FGs and batch options disappear.
**Prompt**: `tasks/WP02-ui-integration.md`
**Estimated size**: ~250 lines

### Included Subtasks
- [x] T006 Update `fg_selection_frame.py` to call `get_fgs_for_selected_recipes()` instead of `get_filtered_available_fgs()`
- [x] T007 Verify filter dropdowns (category, item type, yield type) work with new service call
- [x] T008 Manual verification checklist: end-to-end planning flow with Easter 2026 event

### Implementation Notes
- T006: Replace `event_service.get_filtered_available_fgs()` call in `_on_filter_change()` with new function
- T007: Ensure filter parameters are passed correctly to new service function
- T008: Verify against production DB with real event data

### Parallel Opportunities
- None (depends on WP01)

### Dependencies
- Depends on WP01

### Risks & Mitigations
- **Risk**: UI expects FinishedGood objects but new function returns different shape. **Mitigation**: WP01 T002 provides a wrapper that returns FinishedGood objects, preserving the existing UI contract.

---

## Dependency & Execution Summary

- **Sequence**: WP01 (service fixes + tests) -> WP02 (UI integration)
- **Parallelization**: WP01 subtasks T001 and T004 can be parallelized. WP02 must wait for WP01.
- **MVP Scope**: Both WPs are required for the fix. WP01 alone fixes the data layer; WP02 wires it into the UI.

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001       | Create `get_finished_units_for_event_recipes()` | WP01 | P1 | Yes |
| T002       | Create `get_fgs_for_selected_recipes()` wrapper | WP01 | P1 | No |
| T003       | Simplify `remove_invalid_fg_selections()` | WP01 | P1 | No |
| T004       | Add recipe filter to batch decomposition | WP01 | P1 | Yes |
| T005       | Write service layer tests | WP01 | P1 | No |
| T006       | Update `fg_selection_frame.py` service call | WP02 | P1 | No |
| T007       | Verify filter dropdowns with new service | WP02 | P1 | No |
| T008       | Manual verification checklist | WP02 | P1 | No |

<!-- status-model:start -->
## Canonical Status (Generated)
- WP01: done
- WP02: done
<!-- status-model:end -->
