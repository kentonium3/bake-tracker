---
work_package_id: "WP04"
subtasks:
  - "T021"
  - "T022"
  - "T023"
  - "T024"
  - "T025"
title: "Service Layer Validation Updates"
phase: "Phase 2 - Services"
lane: "done"
assignee: ""
agent: "claude-reviewer"
shell_pid: "4288"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-30T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – Service Layer Validation Updates

## Objectives & Success Criteria

**Goal**: Enforce leaf-only constraints in existing services.

**Success Criteria**:
- Recipe services reject non-leaf ingredients with helpful errors
- Product services reject non-leaf ingredients with helpful errors
- Ingredient service validates hierarchy on create/update
- Error messages suggest leaf alternatives (top 3 descendants)
- All existing tests continue to pass
- New validation tests achieve coverage

## Context & Constraints

**References**:
- Constitution: `.kittify/memory/constitution.md` - Principle III (Layered Architecture)
- Plan: `kitty-specs/031-ingredient-hierarchy-taxonomy/plan.md`
- Data Model: `kitty-specs/031-ingredient-hierarchy-taxonomy/data-model.md` - Validation Rule VR-004

**Constraints**:
- Must not break existing functionality
- Error messages must be user-friendly and actionable
- Run full test suite after each service update
- Follow session pattern per CLAUDE.md

## Subtasks & Detailed Guidance

### Subtask T021 – Update ingredient_service.py for hierarchy validation
- **Purpose**: Validate hierarchy fields on ingredient create/update.
- **Steps**:
  1. Open `src/services/ingredient_service.py`
  2. In create_ingredient():
     - If parent_ingredient_id provided, validate parent exists
     - Calculate hierarchy_level from parent (parent.level + 1)
     - Validate level doesn't exceed 2
     - If no parent, default hierarchy_level to 2 (leaf) for backwards compatibility
  3. In update_ingredient():
     - If parent_ingredient_id is being changed, validate new parent
     - Use move_ingredient() logic or call it directly
     - Validate level constraints
  4. Import hierarchy service functions as needed
- **Files**: `src/services/ingredient_service.py`
- **Parallel?**: No
- **Notes**: Existing ingredients without parent default to level 2 (leaf)

### Subtask T022 – Update recipe_service.py for leaf-only validation
- **Purpose**: Enforce only leaf ingredients can be added to recipes.
- **Steps**:
  1. Open `src/services/recipe_service.py`
  2. Find function(s) that add ingredients to recipes (e.g., add_ingredient_to_recipe, create_recipe_with_ingredients)
  3. Add validation:
     ```python
     from src.services.ingredient_hierarchy_service import is_leaf, get_leaf_ingredients

     if not is_leaf(ingredient_id, session=session):
         suggestions = get_leaf_ingredients(parent_id=ingredient_id, session=session)[:3]
         suggestion_names = [s['display_name'] for s in suggestions]
         raise ValidationError(
             f"Cannot add category ingredient to recipe. "
             f"Please select a specific ingredient. "
             f"Suggestions: {', '.join(suggestion_names)}"
         )
     ```
  4. Ensure session is passed to hierarchy service calls
- **Files**: `src/services/recipe_service.py`
- **Parallel?**: Yes (different file from T021)
- **Notes**: Validation happens before adding to junction table

### Subtask T023 – Update product_service.py for leaf-only validation
- **Purpose**: Enforce only leaf ingredients can be linked to products.
- **Steps**:
  1. Open `src/services/product_service.py`
  2. Find function(s) that create products or link to ingredients
  3. Add same validation pattern as T022
  4. Error message should mention "product" instead of "recipe"
- **Files**: `src/services/product_service.py`
- **Parallel?**: Yes (different file from T021, T022)
- **Notes**: Products map to specific ingredients, not categories

### Subtask T024 – Update product_catalog_service.py for leaf-only validation
- **Purpose**: Enforce leaf-only in catalog operations.
- **Steps**:
  1. Open `src/services/product_catalog_service.py`
  2. Find functions that link products to ingredients
  3. Add validation similar to T022/T023
  4. May need to handle bulk operations differently
- **Files**: `src/services/product_catalog_service.py`
- **Parallel?**: Yes (different file)
- **Notes**: Catalog may have import/batch operations that need validation

### Subtask T025 – Update service tests for hierarchy validation [PARALLEL SAFE]
- **Purpose**: Add tests verifying leaf-only enforcement.
- **Steps**:
  1. Update `src/tests/services/test_ingredient_service.py`:
     - Test create with valid parent
     - Test create with invalid parent (not found)
     - Test create exceeding max depth
  2. Update `src/tests/services/test_recipe_service.py`:
     - Test adding leaf ingredient succeeds
     - Test adding non-leaf ingredient fails with helpful error
     - Verify suggestions in error message
  3. Update `src/tests/services/test_product_service.py`:
     - Similar tests for product creation
  4. Update `src/tests/services/test_product_catalog_service.py`:
     - Similar tests for catalog operations
- **Files**: `src/tests/services/test_*.py`
- **Parallel?**: Yes (once function changes are defined)
- **Notes**: May need hierarchy fixtures in conftest.py

## Test Strategy

- **Unit Tests**:
  - Test each service independently
  - Verify error messages contain suggestions
  - Test edge cases: leaf with no siblings, empty suggestions

- **Integration Tests**:
  - Verify existing functionality still works
  - Test full workflow: create ingredient, add to recipe

- **Commands**:
  ```bash
  # After each service update, run its tests
  pytest src/tests/services/test_ingredient_service.py -v
  pytest src/tests/services/test_recipe_service.py -v
  pytest src/tests/services/test_product_service.py -v
  pytest src/tests/services/test_product_catalog_service.py -v

  # Full test suite
  pytest src/tests -v
  ```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing tests | Run full test suite after each file change |
| Circular import issues | Import hierarchy service inside functions if needed |
| Session not passed correctly | Audit all calls to hierarchy service for session parameter |

## Definition of Done Checklist

- [ ] T021: ingredient_service validates hierarchy on create/update
- [ ] T022: recipe_service enforces leaf-only with suggestions
- [ ] T023: product_service enforces leaf-only with suggestions
- [ ] T024: product_catalog_service enforces leaf-only
- [ ] T025: Tests cover all validation scenarios
- [ ] All existing tests pass
- [ ] Error messages are user-friendly with suggestions

## Review Guidance

- Verify session is passed through all hierarchy service calls
- Verify error messages include actionable suggestions
- Check for consistent error message format across services
- Ensure existing tests weren't broken

## Activity Log

- 2025-12-30T12:00:00Z – system – lane=planned – Prompt created.
- 2025-12-31T14:32:19Z – claude – shell_pid=33615 – lane=doing – Started implementation
- 2025-12-31T15:32:03Z – claude – shell_pid=37805 – lane=for_review – T025 complete - 16 hierarchy validation tests passing
- 2025-12-31T19:41:44Z – claude-reviewer – shell_pid=4288 – lane=done – Code review passed: Leaf-only validation in recipe/product/catalog services, 16/16 WP04-specific tests pass. Note: 17 pre-existing test failures due to category fixture issues unrelated to WP04
