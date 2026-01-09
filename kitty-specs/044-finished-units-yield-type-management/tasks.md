# Work Packages: Finished Units Yield Type Management

**Inputs**: Design documents from `/kitty-specs/044-finished-units-yield-type-management/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md, quickstart.md

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently deliverable.

**Parallelization**: WP01, WP02, and WP04 can execute in parallel (different files). WP03 depends on WP02 for validation. WP05 depends on all implementation packages.

---

## Work Package WP01: Model - Cascade Delete (Priority: P0) [PARALLEL]

**Goal**: Enable cascade deletion of FinishedUnits when parent Recipe is deleted.
**Independent Test**: Delete a recipe with yield types; verify yield types are also deleted.
**Prompt**: `tasks/WP01-model-cascade-delete.md`
**Assigned Agent**: Gemini

### Included Subtasks
- [x] T001 [P] Change FK ondelete RESTRICT → CASCADE in `src/models/finished_unit.py` line 84

### Implementation Notes
- Single line change: `ondelete="RESTRICT"` → `ondelete="CASCADE"`
- No migration needed for SQLite (behavioral change only)
- Verify no orphaned FinishedUnit records exist before change

### Parallel Opportunities
- Can run in parallel with WP02 and WP04 (different files)

### Dependencies
- None (foundational change)

### Risks & Mitigations
- Risk: Accidental data loss if recipe deleted
- Mitigation: This is desired behavior per clarification session

---

## Work Package WP02: Service - Name Uniqueness Validation (Priority: P0) [PARALLEL]

**Goal**: Prevent duplicate yield type names within the same recipe.
**Independent Test**: Try to create two yield types with same name in one recipe; second should fail.
**Prompt**: `tasks/WP02-service-name-validation.md`
**Assigned Agent**: Gemini

### Included Subtasks
- [x] T002 [P] Add `_validate_name_unique_in_recipe()` helper method to FinishedUnitService
- [x] T003 Integrate uniqueness check into `create_finished_unit()`
- [x] T004 Integrate uniqueness check into `update_finished_unit()` (for renames)

### Implementation Notes
- Check for existing FinishedUnit with same display_name AND recipe_id
- On update, exclude current record from uniqueness check
- Raise ValidationError with user-friendly message

### Parallel Opportunities
- Can run in parallel with WP01 and WP04 (different files)

### Dependencies
- None (foundational change)

### Risks & Mitigations
- Risk: Case sensitivity issues ("Large Cookie" vs "large cookie")
- Mitigation: Use case-insensitive comparison

---

## Work Package WP03: Recipe Edit Form - Yield Types Section (Priority: P1) 🎯 MVP

**Goal**: Add inline yield type management to the Recipe Edit form.
**Independent Test**: Open recipe edit, add/edit/delete yield types, save; verify persistence.
**Prompt**: `tasks/WP03-recipe-edit-yield-types.md`
**Assigned Agent**: Claude (Lead)

### Included Subtasks
- [x] T005 Create `YieldTypeRow` inline widget class following `RecipeIngredientRow` pattern
- [x] T006 Add Yield Types section header and container frame after ingredients section
- [x] T007 Implement `_add_yield_type_row()` and `_remove_yield_type_row()` methods
- [x] T008 Persist yield types when recipe is saved (create/update/delete via service)
- [x] T009 Load existing yield types when editing a recipe (`_populate_form()`)
- [x] T010 Add warning validation for recipes with no yield types defined

### Implementation Notes
- Insert section after Recipe Ingredients (around line 660 of recipe_form.py)
- Follow RecipeIngredientRow pattern exactly for consistency
- YieldTypeRow needs: name entry, items_per_batch entry, remove button
- Track pending changes locally; persist only on Save Recipe

### Parallel Opportunities
- None within this package (sequential UI development)

### Dependencies
- Depends on WP02 for validation (service must validate before UI persists)

### Risks & Mitigations
- Risk: Form layout becomes too tall
- Mitigation: Use collapsible section or scrollable frame (already in place)

---

## Work Package WP04: Finished Units Tab - Read-Only Catalog (Priority: P1) [PARALLEL]

**Goal**: Convert existing CRUD tab to read-only catalog with navigation to Recipe Edit.
**Independent Test**: Open tab; see all yield types; double-click navigates to parent recipe.
**Prompt**: `tasks/WP04-tab-readonly-catalog.md`
**Assigned Agent**: Gemini

### Included Subtasks
- [x] T011 [P] Remove Add, Edit, Delete buttons from `_create_action_buttons()`
- [x] T012 [P] Add info label: "Yield types are managed in Recipe Edit"
- [x] T013 [P] Add Recipe column to data table display
- [x] T014 [P] Change double-click behavior to open Recipe Edit form (not detail dialog)
- [x] T015 [P] Add recipe filter dropdown to search bar area

### Implementation Notes
- Keep Refresh button and search functionality
- Double-click should find recipe by ID and open RecipeFormDialog
- Recipe dropdown should load from recipe_service.get_all_recipes()

### Parallel Opportunities
- All subtasks modify different methods/sections; can be developed incrementally
- Can run in parallel with WP01 and WP02 (different files)

### Dependencies
- None (works with existing service layer)

### Risks & Mitigations
- Risk: RecipeFormDialog import circular dependency
- Mitigation: Use deferred import pattern

---

## Work Package WP05: Integration & Acceptance Validation (Priority: P2)

**Goal**: Verify all acceptance scenarios from spec.md pass.
**Independent Test**: Run application; execute all acceptance scenarios.
**Prompt**: `tasks/WP05-integration-validation.md`
**Assigned Agent**: Claude (Lead)

### Included Subtasks
- [x] T016 Run application and test all User Story 1 scenarios (Define Yield Types)
- [x] T017 Run application and test all User Story 2 scenarios (Browse Finished Units)
- [x] T018 Run application and test all User Story 3 scenarios (Validation)

### Implementation Notes
- Manual testing against spec.md acceptance criteria
- Document any issues found for remediation

### Parallel Opportunities
- None (sequential validation)

### Dependencies
- Depends on WP01, WP02, WP03, WP04 (all implementation complete)

### Risks & Mitigations
- Risk: Regressions in existing functionality
- Mitigation: Test Recipe Edit without yield types first

---

## Dependency & Execution Summary

```
Phase 1 - Parallel Foundation (WP01, WP02, WP04):
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ WP01        │  │ WP02        │  │ WP04        │
│ Model       │  │ Service     │  │ Tab         │
│ (Gemini)    │  │ (Gemini)    │  │ (Gemini)    │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       └────────────────┴────────────────┘
                        │
                        ▼
Phase 2 - Core UI (WP03):
                 ┌─────────────┐
                 │ WP03        │
                 │ Recipe Form │
                 │ (Claude)    │
                 └──────┬──────┘
                        │
                        ▼
Phase 3 - Validation (WP05):
                 ┌─────────────┐
                 │ WP05        │
                 │ Acceptance  │
                 │ (Claude)    │
                 └─────────────┘
```

- **MVP Scope**: WP01 + WP02 + WP03 = Recipe Edit yield type management works
- **Full Feature**: All 5 work packages complete

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Change FK ondelete to CASCADE | WP01 | P0 | Yes |
| T002 | Add name uniqueness validation helper | WP02 | P0 | Yes |
| T003 | Integrate into create_finished_unit | WP02 | P0 | No |
| T004 | Integrate into update_finished_unit | WP02 | P0 | No |
| T005 | Create YieldTypeRow widget | WP03 | P1 | No |
| T006 | Add Yield Types section UI | WP03 | P1 | No |
| T007 | Implement add/remove row methods | WP03 | P1 | No |
| T008 | Persist yield types on save | WP03 | P1 | No |
| T009 | Load yield types when editing | WP03 | P1 | No |
| T010 | Add no-yield-types warning | WP03 | P1 | No |
| T011 | Remove CRUD buttons from tab | WP04 | P1 | Yes |
| T012 | Add info label | WP04 | P1 | Yes |
| T013 | Add Recipe column | WP04 | P1 | Yes |
| T014 | Implement double-click navigation | WP04 | P1 | Yes |
| T015 | Add recipe filter dropdown | WP04 | P1 | Yes |
| T016 | Test User Story 1 scenarios | WP05 | P2 | No |
| T017 | Test User Story 2 scenarios | WP05 | P2 | No |
| T018 | Test User Story 3 scenarios | WP05 | P2 | No |
