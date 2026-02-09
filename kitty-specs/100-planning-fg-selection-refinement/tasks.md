# Work Packages: Planning FG Selection Refinement

**Inputs**: Design documents from `kitty-specs/100-planning-fg-selection-refinement/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md

**Tests**: Include tests for new service functions (service layer must maintain >70% coverage per constitution).

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently deliverable and testable.

**Prompt Files**: Each work package references a matching prompt file in `tasks/`.

---

## Work Package WP01: Service Layer - Filtered FG Queries (Priority: P0)

**Goal**: Add service functions for filtered FG retrieval and recipe category enumeration for events.
**Independent Test**: Unit tests pass for `get_filtered_available_fgs()` and `get_available_recipe_categories_for_event()` with various filter combinations.
**Prompt**: `tasks/WP01-service-filtered-fg-queries.md`
**Estimated Size**: ~350 lines

### Included Subtasks
- [x] T001 Add `get_filtered_available_fgs()` to `src/services/event_service.py`
- [x] T002 Add `get_available_recipe_categories_for_event()` to `src/services/event_service.py`
- [x] T003 Write tests for `get_filtered_available_fgs()` covering all filter combinations
- [x] T004 Write tests for `get_available_recipe_categories_for_event()`

### Implementation Notes
- `get_filtered_available_fgs()` builds on existing `get_available_finished_goods()` adding recipe_category, assembly_type, and yield_type filter parameters
- All filters are optional; when provided they combine with AND logic
- yield_type filter only applies to BARE FGs (BUNDLE FGs have no yield_type)
- Both functions accept `session: Session` as required parameter (inherits caller's transaction)

### Parallel Opportunities
- T003 and T004 can be written in parallel once T001 and T002 are done

### Dependencies
- None (starting package). Uses existing models and services.

### Risks & Mitigations
- Risk: Recipe.category string doesn't match RecipeCategory.name exactly → verify matching logic with existing data
- Risk: BUNDLE FGs with yield_type filter edge case → test explicitly

---

## Work Package WP02: Recipe Selection Filter-First (Priority: P1) MVP

**Goal**: Replace auto-load-all recipe selection with category-filtered blank-start pattern.
**Independent Test**: Open Planning tab, select event, verify recipe frame starts blank with category dropdown, select category, verify only matching recipes appear, change category, verify prior selections persist.
**Prompt**: `tasks/WP02-recipe-selection-filter-first.md`
**Estimated Size**: ~350 lines

### Included Subtasks
- [x] T005 Refactor `RecipeSelectionFrame` - add category filter dropdown, blank-start placeholder
- [x] T006 Add selection persistence (`_selected_recipe_ids: Set[int]`) across category changes
- [x] T007 Update `planning_tab.py` orchestration for filtered recipe selection

### Implementation Notes
- Category dropdown populated via `recipe_category_service.list_categories()` + "All Categories" option
- Blank start: scrollable frame shows placeholder "Select recipe category to see available recipes"
- On category change: call `recipe_service.get_recipes_by_category()` or `get_all_recipes()`
- Selections persist in `_selected_recipe_ids` set; checkboxes restored on re-render

### Parallel Opportunities
- T005 and T007 can be developed in parallel (frame vs orchestrator)

### Dependencies
- None (uses existing recipe_service functions)

### Risks & Mitigations
- Risk: Category dropdown initially empty if no RecipeCategories exist → handle gracefully with "No categories available" or fall back to "All"

---

## Work Package WP03: FG Selection Filter-First with Persistence (Priority: P1) MVP

**Goal**: Replace auto-load-all FG selection with three-filter blank-start pattern. Selections persist across filter changes.
**Independent Test**: Open FG selection, verify blank start with three dropdowns, apply filters in different orders, verify AND logic, check FGs, change filters, verify selections persist when returning to original filter.
**Prompt**: `tasks/WP03-fg-selection-filter-first.md`
**Estimated Size**: ~500 lines

### Included Subtasks
- [x] T008 Refactor `FGSelectionFrame` - add three filter dropdowns (recipe category, item type, yield type), blank-start placeholder
- [x] T009 Implement AND-combine filter logic calling `get_filtered_available_fgs()`
- [x] T010 Add selection persistence (`_selected_fg_ids: Set[int]`, `_fg_quantities: Dict[int, int]`) across filter changes
- [x] T011 Restore checkbox + quantity state when rendering FG list after filter change
- [x] T012 Update `planning_tab.py` orchestration for filtered FG selection

### Implementation Notes
- Three independent dropdowns: Recipe Category, Item Type (Finished Units/Assemblies/All), Yield Type (EA/SERVING/All)
- FGs load only after at least one filter is applied (FR-007)
- `_selected_fg_ids` and `_fg_quantities` survive filter changes
- When rendering after filter change, loop through displayed FGs and restore checkbox/qty from persistence dicts
- planning_tab passes event_id and session to FG frame for service calls

### Parallel Opportunities
- T008 (UI layout) and T009 (filter logic) can start in parallel
- T012 (orchestration) depends on T008-T011

### Dependencies
- Depends on WP01 (uses `get_filtered_available_fgs()` and `get_available_recipe_categories_for_event()`)

### Risks & Mitigations
- Risk: Performance with large FG catalogs → catalog is small (~100 FGs), no optimization needed
- Risk: Yield type dropdown irrelevant when item type = "Assemblies" → UI should still show the dropdown but results naturally exclude BUNDLEs when yield_type is specified

---

## Work Package WP04: Clear Buttons and Show All Selected (Priority: P2)

**Goal**: Add two-level clear buttons and "Show All Selected" toggle for cross-filter selection review.
**Independent Test**: Build plan with recipes + FGs + quantities, test each clear button scope, test Show All Selected toggle behavior.
**Prompt**: `tasks/WP04-clear-buttons-show-selected.md`
**Estimated Size**: ~400 lines

### Included Subtasks
- [x] T013 Add "Clear All" button with confirmation dialog to planning container
- [x] T014 Add "Clear Finished Goods" button with confirmation dialog to planning container
- [x] T015 Wire clear button callbacks to reset appropriate state (recipes/FGs/quantities)
- [x] T016 Add "Show All Selected" toggle button to FG frame
- [x] T017 Implement show-selected-only rendering mode
- [x] T018 Auto-exit show-selected mode on filter dropdown change

### Implementation Notes
- Clear All: confirmation → reset `_selected_recipe_ids`, `_selected_fg_ids`, `_fg_quantities`, return both frames to blank
- Clear FGs: confirmation → reset only `_selected_fg_ids` and `_fg_quantities`, recipe selections remain
- Show All Selected: toggle replaces filter-driven list with only selected FGs from `_selected_fg_ids`
- Button label changes to "Show Filtered View" when active; count indicator shows "Showing N selected items"
- Changing any filter dropdown exits show-selected mode (FR-012)

### Parallel Opportunities
- T013-T015 (clear buttons) and T016-T018 (show selected) are independent

### Dependencies
- Depends on WP02 and WP03 (needs selection persistence state to be in place)

### Risks & Mitigations
- Risk: Clear All doesn't cascade to DB during draft mode → correct, UI-only clear until Save is clicked
- Risk: Show All Selected with 0 items → display "No items selected" message

---

## Work Package WP05: Quantity Persistence and Atomic Save (Priority: P2)

**Goal**: Ensure quantities persist in UI state across step navigation and save atomically to database.
**Independent Test**: Enter quantities, navigate away and back, verify quantities preserved. Click Save with valid quantities, verify DB write. Click Save with errors, verify disabled.
**Prompt**: `tasks/WP05-quantity-persistence-atomic-save.md`
**Estimated Size**: ~300 lines

### Included Subtasks
- [ ] T019 Integrate quantity persistence with FG selection persistence (sync `_fg_quantities` dict on every qty change)
- [ ] T020 Wire Save button to `set_event_fg_quantities()` with all (fg_id, quantity) pairs from in-memory state
- [ ] T021 Validate Save button disabled when validation errors exist or no FGs selected

### Implementation Notes
- `_fg_quantities` dict already exists from WP03; this WP ensures it integrates with the Save flow
- On quantity entry change, update `_fg_quantities[fg_id]` immediately (via StringVar trace)
- Save collects `[(fg_id, qty) for fg_id, qty in _fg_quantities.items() if fg_id in _selected_fg_ids and qty > 0]`
- Save calls `set_event_fg_quantities(session, event_id, fg_quantities)` which does atomic replace
- Save button disabled when: no FGs selected, or any checked FG has invalid/empty quantity
- Validation messages: "Quantity must be greater than zero", "Whole numbers only", "Quantity must be positive", "Enter a valid number", "Quantity required"

### Parallel Opportunities
- T019, T020, and T021 are sequential (build on each other)

### Dependencies
- Depends on WP03 (needs `_selected_fg_ids` and `_fg_quantities` state)

### Risks & Mitigations
- Risk: Existing `set_event_fg_quantities()` filters invalid FGs → correct behavior, no change needed
- Risk: Plan state check prevents save when not DRAFT → existing service handles this with PlanStateError

---

## Dependency & Execution Summary

- **Sequence**: WP01 → WP03 (depends on WP01); WP02 (independent); WP04 (depends on WP02 + WP03); WP05 (depends on WP03)
- **Parallelization**: WP01 and WP02 can run in parallel. WP04 and WP05 can run in parallel after their deps.
- **MVP Scope**: WP01 + WP02 + WP03 deliver the core filter-first experience (US1, US2, US3)

```
WP01 (Service) ──────────────────┐
                                 ├──> WP03 (FG Filters) ──┬──> WP04 (Clear/Show)
WP02 (Recipe Filter) ───────────┘                         └──> WP05 (Save)
```

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Add `get_filtered_available_fgs()` | WP01 | P0 | No |
| T002 | Add `get_available_recipe_categories_for_event()` | WP01 | P0 | No |
| T003 | Tests for filtered FG query | WP01 | P0 | [P] |
| T004 | Tests for recipe categories query | WP01 | P0 | [P] |
| T005 | RecipeSelectionFrame category filter + blank start | WP02 | P1 | [P] |
| T006 | Recipe selection persistence across category changes | WP02 | P1 | No |
| T007 | planning_tab orchestration for filtered recipes | WP02 | P1 | [P] |
| T008 | FGSelectionFrame three filter dropdowns + blank start | WP03 | P1 | [P] |
| T009 | AND-combine filter logic with service call | WP03 | P1 | [P] |
| T010 | FG selection + quantity persistence state | WP03 | P1 | No |
| T011 | Restore checkbox/qty state on re-render | WP03 | P1 | No |
| T012 | planning_tab orchestration for filtered FGs | WP03 | P1 | No |
| T013 | Clear All button with confirmation | WP04 | P2 | [P] |
| T014 | Clear FGs button with confirmation | WP04 | P2 | [P] |
| T015 | Clear button callback wiring | WP04 | P2 | No |
| T016 | Show All Selected toggle button | WP04 | P2 | [P] |
| T017 | Show-selected-only rendering mode | WP04 | P2 | No |
| T018 | Auto-exit show-selected on filter change | WP04 | P2 | No |
| T019 | Quantity persistence integration | WP05 | P2 | No |
| T020 | Save button → set_event_fg_quantities() | WP05 | P2 | No |
| T021 | Save button disabled on validation errors | WP05 | P2 | No |
