# Feature Specification: Ingredient Hierarchy Comprehensive Testing

**Feature Branch**: `036-ingredient-hierarchy-comprehensive`
**Created**: 2026-01-02
**Status**: Draft
**Input**: Phase 4 of F033-F036 ingredient hierarchy implementation - comprehensive testing and user acceptance validation

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Validate All Hierarchy Tests Pass (Priority: P1)

As a developer, I need to verify that all unit tests, integration tests, and validation rule tests pass for the ingredient hierarchy implementation to confirm Phases 1-3 work correctly.

**Why this priority**: Tests are the foundation for confidence that the implementation is correct. Without passing tests, we cannot proceed with user acceptance.

**Independent Test**: Run `pytest src/tests -v -k ingredient` and verify all tests pass with zero failures.

**Acceptance Scenarios**:

1. **Given** the test suite exists, **When** running all ingredient-related tests, **Then** 100% of tests pass with zero failures or errors
2. **Given** hierarchy level computation tests exist, **When** testing L0/L1/L2 computation, **Then** level is correctly computed from parent position
3. **Given** slug generation tests exist, **When** testing uniqueness handling, **Then** conflicts are resolved with -2, -3 suffix pattern
4. **Given** cycle detection tests exist, **When** attempting to create circular references, **Then** validation blocks the operation
5. **Given** deletion protection tests exist, **When** deleting ingredients with references, **Then** deletion is blocked with appropriate error message

---

### User Story 2 - Validate Cascading Selector Integration (Priority: P1)

As a baker, I need the cascading selectors (L0 -> L1 -> L2) to work correctly across all tabs so I can efficiently navigate and select ingredients.

**Why this priority**: Cascading selectors are the primary navigation mechanism for the hierarchy. If broken, the entire feature is unusable.

**Independent Test**: Manually test cascading behavior in Product edit form, Recipe creation, Product tab filter, and Inventory tab filter.

**Acceptance Scenarios**:

1. **Given** Product edit form is open, **When** I select an L0 category, **Then** the L1 dropdown updates to show only children of that L0
2. **Given** L0 and L1 are selected, **When** I change L0 selection, **Then** L1 resets and L2 clears
3. **Given** Recipe creation form is open, **When** I use cascading selector, **Then** only L2 ingredients can be selected
4. **Given** Product tab filter has selections, **When** I click Clear/Reset, **Then** all filter levels reset to default

---

### User Story 3 - Validate Deletion Protection Works (Priority: P1)

As a baker, I need the system to prevent accidental deletion of ingredients that would break my products, recipes, or hierarchy so my data stays consistent.

**Why this priority**: Data integrity is critical. Broken references can corrupt the entire database and require manual repair.

**Independent Test**: Attempt to delete ingredients with products, recipes, and children, verifying each is blocked with proper error message.

**Acceptance Scenarios**:

1. **Given** an ingredient has 3 products assigned, **When** I try to delete it, **Then** I see "Cannot delete: 3 products use this ingredient"
2. **Given** an ingredient is used in 2 recipes, **When** I try to delete it, **Then** I see "Cannot delete: 2 recipes use this ingredient"
3. **Given** an L1 ingredient has 4 L2 children, **When** I try to delete it, **Then** I see "Cannot delete: 4 ingredients are children of this category"
4. **Given** an ingredient has no references, **When** I delete it, **Then** deletion succeeds and aliases/crosswalks are cascade-deleted

---

### User Story 4 - User Acceptance Testing with Marianne (Priority: P2)

As the primary end user (Marianne), I need to verify the ingredient hierarchy works intuitively for my baking workflow so the app meets my actual needs.

**Why this priority**: Real-world user validation ensures the implementation solves actual problems, not just theoretical requirements.

**Independent Test**: Marianne performs key workflows and provides feedback on usability, clarity, and any pain points.

**Acceptance Scenarios**:

1. **Given** Marianne opens the Ingredients tab, **When** she views the list, **Then** she can understand the hierarchy display without explanation
2. **Given** Marianne creates a new ingredient, **When** selecting parents, **Then** the parent selection process feels intuitive
3. **Given** Marianne filters products by ingredient, **When** using cascading selectors, **Then** she finds the products she expects
4. **Given** Marianne attempts an invalid operation, **When** seeing an error message, **Then** she understands what went wrong and how to fix it

---

### User Story 5 - Validate Slug Auto-Generation (Priority: P2)

As a baker, I need slugs to be automatically generated from ingredient names so I don't have to think about unique identifiers.

**Why this priority**: Slug generation is a usability feature that reduces friction when creating new ingredients.

**Independent Test**: Create multiple ingredients with similar names and verify unique slugs are generated.

**Acceptance Scenarios**:

1. **Given** I create an ingredient named "Chocolate Chips", **When** saved, **Then** slug `chocolate-chips` is generated
2. **Given** `chocolate-chips` slug exists, **When** I create another "Chocolate Chips", **Then** slug `chocolate-chips-2` is generated
3. **Given** I edit an ingredient name, **When** saved, **Then** the slug is preserved (not regenerated)

---

### Edge Cases

- What happens when a parent ingredient is changed while products are being edited concurrently?
- How does the system handle very long ingredient names (100+ characters) for slug generation?
- What if the database has orphaned records from before deletion protection was implemented?
- How does cascading filter behave when ingredient hierarchy has only L0 (no L1/L2)?
- What happens if import data has circular references?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST pass all existing unit tests for ingredient hierarchy (hierarchy level computation, slug generation, cycle detection)
- **FR-002**: System MUST pass all validation rule tests (VAL-ING-001 through VAL-ING-011)
- **FR-003**: System MUST pass all deletion protection tests (blocks when Products/Recipes/Children reference ingredient)
- **FR-004**: System MUST pass all cascading selector integration tests across Product, Recipe, and Inventory tabs
- **FR-005**: System MUST demonstrate slug auto-generation with conflict resolution
- **FR-006**: System MUST demonstrate snapshot denormalization (ingredient names preserved in historical records)
- **FR-007**: System MUST pass user acceptance testing with primary user (Marianne)
- **FR-008**: Any discovered edge case failures MUST be documented and fixed before acceptance

### Key Entities *(include if feature involves data)*

- **Ingredient**: Hierarchical entity with L0/L1/L2 levels, slug, display_name, parent_ingredient_id
- **Product**: Entity with ingredient_id FK, requires valid L2 ingredient
- **RecipeIngredient**: Junction table linking recipes to L2 ingredients
- **IngredientAlias**: Supporting table with cascade delete on ingredient deletion
- **IngredientCrosswalk**: Supporting table with cascade delete on ingredient deletion

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of ingredient hierarchy tests pass (zero failures, zero errors)
- **SC-002**: All 11 validation rules (VAL-ING-001 through VAL-ING-011) are verified with tests
- **SC-003**: Cascading selectors work correctly in all 4 locations (Product edit, Recipe creation, Product filter, Inventory filter)
- **SC-004**: Deletion protection correctly blocks in all 3 scenarios (Products, Recipes, Children)
- **SC-005**: Marianne completes user acceptance testing and signs off on usability
- **SC-006**: Any edge cases discovered during testing are documented and resolved
- **SC-007**: Test coverage for ingredient services exceeds 70%

## Test Matrix *(mandatory for this feature)*

### Unit Tests (from req_ingredients.md Section 13.1)

| Test ID | Test Description | Status |
|---------|------------------|--------|
| UT-001 | Hierarchy level computation logic (L0/L1/L2 from parent position) | Pending |
| UT-002 | Slug generation uniqueness (conflict resolution with -2, -3) | Pending |
| UT-003 | Cycle detection algorithm (prevent circular references) | Pending |
| UT-004 | Validation rule enforcement (all 11 VAL-ING rules) | Pending |

### Integration Tests (from req_ingredients.md Section 13.1)

| Test ID | Test Description | Status |
|---------|------------------|--------|
| IT-001 | Cascading selector behavior (L0 -> L1 -> L2 updates) | Pending |
| IT-002 | Product auto-update on ingredient change | Pending |
| IT-003 | Recipe validation when ingredient changes | Pending |
| IT-004 | Import/export round-trip with hierarchy | Pending |

### User Acceptance Tests (from req_ingredients.md Section 13.1)

| Test ID | Test Description | Status |
|---------|------------------|--------|
| UAT-001 | Create L2 ingredient workflow | Pending |
| UAT-002 | Edit ingredient parentage workflow | Pending |
| UAT-003 | Filter products by ingredient hierarchy | Pending |
| UAT-004 | Select ingredients in recipe creation | Pending |

### Deletion Protection Tests (from F035)

| Test ID | Test Description | Status |
|---------|------------------|--------|
| DT-001 | Block deletion when Products reference ingredient | Pending |
| DT-002 | Block deletion when Recipes reference ingredient | Pending |
| DT-003 | Block deletion when Children exist | Pending |
| DT-004 | Allow deletion when no references (cascade aliases/crosswalks) | Pending |
| DT-005 | Snapshot denormalization preserves names | Pending |

## Assumptions

1. Phases 1-3 (F033, F034, F035) are correctly implemented and merged
2. Test data exists with sufficient hierarchy depth (L0/L1/L2) and breadth
3. Marianne is available for user acceptance testing
4. No schema changes are required for this testing phase
5. Existing test infrastructure (pytest) is sufficient

## Dependencies

- **Upstream**: F033 (Phase 1), F034 (Phase 2), F035 (Phase 3) must be merged
- **Test Data**: `test_data/sample_data.json` contains valid hierarchy structure
- **User Availability**: Marianne available for UAT session

## Risks

1. **UAT Scheduling**: Marianne may not be available during development window
   - Mitigation: Schedule UAT session in advance, prepare test script
2. **Edge Case Discovery**: Testing may reveal bugs in Phase 1-3 implementations
   - Mitigation: Budget time for bug fixes, prioritize by severity
3. **Test Data Gaps**: Existing test data may not cover all scenarios
   - Mitigation: Create additional test fixtures as needed

---

**END OF SPECIFICATION**
