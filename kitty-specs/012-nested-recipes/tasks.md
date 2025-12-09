# Work Packages: Nested Recipes (Sub-Recipe Components)

**Feature**: 012-nested-recipes
**Inputs**: Design documents from `kitty-specs/012-nested-recipes/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/recipe_service.md, quickstart.md

**Tests**: Service layer tests required per constitution (>70% coverage).

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently deliverable and testable.

**Prompt Files**: Each work package references a matching prompt file in `tasks/planned/`.

---

## Work Package WP01: Schema & Model (Priority: P0)

**Goal**: Create RecipeComponent model with database constraints and Recipe relationship extensions.
**Independent Test**: Model can be instantiated, schema creates successfully, constraints enforce validation rules.
**Prompt**: `tasks/planned/WP01-schema-model.md`

### Included Subtasks
- [X] T001 Create RecipeComponent class in `src/models/recipe.py`
- [X] T002 Add database constraints (quantity > 0, no self-reference, unique combo)
- [X] T003 Add indexes for recipe_id, component_recipe_id, sort_order
- [X] T004 Add `recipe_components` relationship to Recipe model
- [X] T005 Add `used_in_recipes` relationship to Recipe model
- [X] T006 Export RecipeComponent from `src/models/__init__.py`
- [X] T007 Verify schema auto-creates correctly (run app or test)

### Implementation Notes
- Follow RecipeIngredient pattern in same file
- CASCADE on parent delete, RESTRICT on component delete
- Float quantity for batch multipliers (0.5, 1.0, 2.0, etc.)

### Parallel Opportunities
- T001-T005 are sequential (model definition)
- T006-T007 can proceed after T005

### Dependencies
- None (foundational work package)

### Risks & Mitigations
- FK constraint naming conflicts → Use unique constraint names with `ck_recipe_component_` prefix
- Circular import → RecipeComponent in same file as Recipe

---

## Work Package WP02: Service Layer - Component CRUD (Priority: P0)

**Goal**: Implement add, remove, update, get operations for recipe components in recipe_service.py.
**Independent Test**: Can add/remove/update components via service functions; operations persist correctly.
**Prompt**: `tasks/planned/WP02-service-crud.md`

### Included Subtasks
- [X] T008 Implement `add_recipe_component()` function
- [X] T009 Implement `remove_recipe_component()` function
- [X] T010 Implement `update_recipe_component()` function
- [X] T011 Implement `get_recipe_components()` function
- [X] T012 Implement `get_recipes_using_component()` function
- [X] T013 [P] Add unit tests for all CRUD operations

### Implementation Notes
- Follow existing `add_ingredient_to_recipe` pattern
- Use session_scope context manager
- Validate recipe exists before operations
- Sort by sort_order in get operations

### Parallel Opportunities
- T008-T012 are interdependent
- T013 (tests) can be developed in parallel after T008-T009 are sketched

### Dependencies
- Depends on WP01

### Risks & Mitigations
- Eager loading issues → Follow existing recipe_ingredients loading pattern

---

## Work Package WP03: Service Layer - Validation (Priority: P0)

**Goal**: Implement circular reference detection and depth limit enforcement.
**Independent Test**: Circular references blocked at all depths; depth > 3 rejected; clear error messages.
**Prompt**: `tasks/planned/WP03-service-validation.md`

### Included Subtasks
- [X] T014 Implement `_would_create_cycle()` helper function
- [X] T015 Implement `_get_recipe_depth()` helper function
- [X] T016 Implement `_would_exceed_depth()` helper function
- [X] T017 Integrate validation into `add_recipe_component()`
- [X] T018 Modify `delete_recipe()` to check for component usage
- [X] T019 [P] Add unit tests for circular reference detection
- [X] T020 [P] Add unit tests for depth limit enforcement
- [X] T021 [P] Add unit tests for deletion protection

### Implementation Notes
- Cycle detection: BFS/DFS traversal of component tree
- Depth calculation: Recursive max depth of subtrees
- Error messages per contracts/recipe_service.md

### Parallel Opportunities
- T14-T16 helper functions can be developed together
- T19-T21 tests can proceed in parallel after helpers exist

### Dependencies
- Depends on WP02

### Risks & Mitigations
- Performance on deep trees → Max depth of 3 limits recursion
- Edge case: A→B→C, try add C→A → Must detect full cycle path

---

## Work Package WP04: Service Layer - Cost & Aggregation (Priority: P1)

**Goal**: Implement recursive cost calculation and ingredient aggregation for shopping lists.
**Independent Test**: Cost includes sub-recipe costs × quantities; aggregated ingredients sum correctly across hierarchy.
**Prompt**: `tasks/planned/WP04-service-cost-aggregation.md`

### Included Subtasks
- [X] T022 Implement `get_aggregated_ingredients()` function
- [X] T023 Implement `calculate_total_cost_with_components()` function
- [X] T024 Modify `Recipe.calculate_cost()` to include components (or keep separate)
- [X] T025 Modify `get_recipe_with_costs()` to include component breakdown
- [X] T026 [P] Add unit tests for ingredient aggregation
- [X] T027 [P] Add unit tests for cost calculation with 1, 2, 3 level hierarchies

### Implementation Notes
- Aggregation: Group by (ingredient_id, unit), sum quantities
- Cost: Recursive calculation, multiply by batch quantity
- Return structure per contracts/recipe_service.md

### Parallel Opportunities
- T022-T023 can be developed in parallel (different algorithms)
- T026-T027 tests can proceed after respective functions

### Dependencies
- Depends on WP02, WP03

### Risks & Mitigations
- Ingredient unit mismatch → Only aggregate same units (spec limitation)
- Cost of 0 for missing prices → Document partial cost indicator

---

## Work Package WP05: Import/Export Support (Priority: P2)

**Goal**: Extend import_export_service to handle recipe components.
**Independent Test**: Export recipe with components produces correct JSON; import restores relationships.
**Prompt**: `tasks/planned/WP05-import-export.md`

### Included Subtasks
- [X] T028 Modify `export_recipes_to_json()` to include components array
- [X] T029 Modify `export_all_to_json()` to include components in recipe export
- [X] T030 Modify `import_recipes_from_json()` to process components
- [X] T031 Handle missing component recipes gracefully (warn, skip)
- [X] T032 [P] Add unit tests for export with components
- [X] T033 [P] Add unit tests for import with/without existing components

### Implementation Notes
- Export format per data-model.md: `{ "recipe_name": str, "quantity": float, "notes": str }`
- Import order: Recipes first pass (no components), then link components
- Warning log for missing component references

### Parallel Opportunities
- T028-T029 (export) and T030-T031 (import) can proceed in parallel
- T032-T033 tests after respective implementations

### Dependencies
- Depends on WP02

### Risks & Mitigations
- Import ordering → Two-pass import or topological sort
- Circular in import data → Validation will catch on component add

---

## Work Package WP06: UI - Recipe Form (Priority: P1)

**Goal**: Add sub-recipes section to recipe form with add/remove/edit functionality.
**Independent Test**: User can add, view, edit, remove sub-recipes in recipe form; changes persist.
**Prompt**: `tasks/planned/WP06-ui-recipe-form.md`

### Included Subtasks
- [X] T034 Add "Sub-Recipes" section label and frame in recipe form
- [X] T035 Add recipe selection dropdown (filtered to exclude self + parents)
- [X] T036 Add quantity input field (batch multiplier)
- [X] T037 Add "Add Sub-Recipe" button with click handler
- [X] T038 Display existing sub-recipes in list format
- [X] T039 Add remove button for each sub-recipe row
- [X] T040 Add cost summary section showing component costs
- [X] T041 Wire form to service layer for save/load
- [X] T042 Handle validation errors (circular ref, depth) with user-friendly messages

### Implementation Notes
- Follow existing ingredients section pattern
- Use CTkComboBox for recipe selection
- Show sub-recipe name, quantity (Nx), cost
- Error dialogs via CTkMessagebox

### Parallel Opportunities
- T034-T036 (UI scaffolding) sequential
- T038-T40 (display) can proceed after T37
- T42 can be developed alongside T41

### Dependencies
- Depends on WP02, WP03, WP04

### Risks & Mitigations
- Recipe dropdown performance → Lazy load or limit to 100
- Circular reference error UX → Clear message explaining the cycle

---

## Work Package WP07: Integration & Polish (Priority: P2)

**Goal**: End-to-end validation, edge case handling, and documentation updates.
**Independent Test**: All quickstart.md scenarios pass; no regressions in existing tests.
**Prompt**: `tasks/planned/WP07-integration-polish.md`

### Included Subtasks
- [X] T043 Run full test suite, fix any regressions
- [X] T044 Validate quickstart.md testing checklist
- [X] T045 Test 3-level nesting end-to-end
- [X] T046 Test import/export round-trip
- [X] T047 Verify backward compatibility (recipes without components)
- [X] T048 Update any affected documentation

### Implementation Notes
- Use quickstart.md checklist as acceptance test
- Verify cost calculations match manual calculations
- Check all error messages match contracts

### Parallel Opportunities
- T043-T047 can be distributed across multiple passes
- T048 after all functional work complete

### Dependencies
- Depends on WP01-WP06

### Risks & Mitigations
- Regression in existing recipe functionality → Run existing tests first
- Missing edge case → Follow spec edge cases section

---

## Dependency & Execution Summary

```
WP01 (Schema & Model)
  ↓
WP02 (Service CRUD)
  ↓
WP03 (Validation) ←──────────────────┐
  ↓                                   │
WP04 (Cost & Aggregation)            │
  ↓                                   │
WP05 (Import/Export) ────────────────┘
  ↓
WP06 (UI)
  ↓
WP07 (Integration & Polish)
```

**Sequence**: WP01 → WP02 → WP03 → WP04 → WP05 (can parallel with WP04) → WP06 → WP07

**Parallelization**:
- WP04 and WP05 can proceed in parallel after WP03
- Within work packages, tests can run parallel to implementation

**MVP Scope**: WP01 + WP02 + WP03 + WP04 + WP06 = Core nested recipe functionality with UI

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Create RecipeComponent class | WP01 | P0 | No |
| T002 | Add database constraints | WP01 | P0 | No |
| T003 | Add indexes | WP01 | P0 | No |
| T004 | Add recipe_components relationship | WP01 | P0 | No |
| T005 | Add used_in_recipes relationship | WP01 | P0 | No |
| T006 | Export from __init__.py | WP01 | P0 | No |
| T007 | Verify schema creates | WP01 | P0 | No |
| T008 | Implement add_recipe_component | WP02 | P0 | No |
| T009 | Implement remove_recipe_component | WP02 | P0 | No |
| T010 | Implement update_recipe_component | WP02 | P0 | No |
| T011 | Implement get_recipe_components | WP02 | P0 | No |
| T012 | Implement get_recipes_using_component | WP02 | P0 | No |
| T013 | Unit tests for CRUD | WP02 | P0 | Yes |
| T014 | Implement _would_create_cycle | WP03 | P0 | No |
| T015 | Implement _get_recipe_depth | WP03 | P0 | No |
| T016 | Implement _would_exceed_depth | WP03 | P0 | No |
| T017 | Integrate validation into add | WP03 | P0 | No |
| T018 | Modify delete_recipe | WP03 | P0 | No |
| T019 | Tests for circular reference | WP03 | P0 | Yes |
| T020 | Tests for depth limit | WP03 | P0 | Yes |
| T021 | Tests for deletion protection | WP03 | P0 | Yes |
| T022 | Implement get_aggregated_ingredients | WP04 | P1 | No |
| T023 | Implement calculate_total_cost_with_components | WP04 | P1 | No |
| T024 | Modify Recipe.calculate_cost | WP04 | P1 | No |
| T025 | Modify get_recipe_with_costs | WP04 | P1 | No |
| T026 | Tests for ingredient aggregation | WP04 | P1 | Yes |
| T027 | Tests for cost calculation | WP04 | P1 | Yes |
| T028 | Modify export_recipes_to_json | WP05 | P2 | No |
| T029 | Modify export_all_to_json | WP05 | P2 | No |
| T030 | Modify import_recipes_from_json | WP05 | P2 | No |
| T031 | Handle missing component gracefully | WP05 | P2 | No |
| T032 | Tests for export | WP05 | P2 | Yes |
| T033 | Tests for import | WP05 | P2 | Yes |
| T034 | Add Sub-Recipes section frame | WP06 | P1 | No |
| T035 | Add recipe selection dropdown | WP06 | P1 | No |
| T036 | Add quantity input field | WP06 | P1 | No |
| T037 | Add "Add Sub-Recipe" button | WP06 | P1 | No |
| T038 | Display existing sub-recipes | WP06 | P1 | No |
| T039 | Add remove button per row | WP06 | P1 | No |
| T040 | Add cost summary section | WP06 | P1 | No |
| T041 | Wire form to service layer | WP06 | P1 | No |
| T042 | Handle validation errors | WP06 | P1 | No |
| T043 | Run full test suite | WP07 | P2 | No |
| T044 | Validate quickstart checklist | WP07 | P2 | No |
| T045 | Test 3-level nesting e2e | WP07 | P2 | No |
| T046 | Test import/export round-trip | WP07 | P2 | No |
| T047 | Verify backward compatibility | WP07 | P2 | No |
| T048 | Update documentation | WP07 | P2 | No |
