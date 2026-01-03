---
work_package_id: "WP03"
subtasks:
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
title: "Deletion Protection Validation"
phase: "Phase 2 - Manual Testing"
lane: "done"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-02T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Deletion Protection Validation

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Verify deletion protection blocks correctly in all 3 blocking scenarios
- Verify deletion succeeds when no references exist
- Confirm error messages include correct counts
- Document all deletion test results

**Success Metrics**:
- Deletion blocked by Products shows correct message with count
- Deletion blocked by Recipes shows correct message with count
- Deletion blocked by Children shows correct message with count
- Deletion allowed when no references (aliases/crosswalks cascade deleted)

## Context & Constraints

- **Depends on**: WP01 (automated tests verify service layer)
- **Reference**: `kitty-specs/036-ingredient-hierarchy-comprehensive/spec.md` - User Story 3
- **F035 Implementation**: `src/services/ingredient_service.py` - `can_delete_ingredient()` function

The deletion protection was implemented in F035. This work package verifies it works correctly in the UI.

**Expected Error Messages** (from VAL-ING-009 through VAL-ING-011):
- "Cannot delete: X products use this ingredient"
- "Cannot delete: X recipes use this ingredient"
- "Cannot delete: X ingredients are children of this category"

## Subtasks & Detailed Guidance

### Subtask T013 - Test deletion blocked when Products reference ingredient
- **Purpose**: Verify cannot delete an ingredient that has products assigned.
- **Steps**:
  1. Start app: `python src/main.py`
  2. Navigate to Ingredients tab
  3. Find an L2 ingredient that has products (check Products column or navigate to Products tab to confirm)
  4. Select the ingredient
  5. Click Delete button
  6. Verify:
     - Deletion is blocked
     - Error message appears
     - Message includes product count
     - Message matches pattern: "Cannot delete: X products use this ingredient"
  7. Record exact message shown
- **Files**: Testing `src/ui/ingredients_tab.py`, `src/services/ingredient_service.py`
- **Parallel?**: No
- **Notes**: If no ingredient with products exists, create one first via Products tab

### Subtask T014 - Test deletion blocked when Recipes reference ingredient
- **Purpose**: Verify cannot delete an ingredient used in recipes.
- **Steps**:
  1. Navigate to Ingredients tab
  2. Find an L2 ingredient used in a recipe (may need to check Recipes tab)
  3. Select the ingredient
  4. Click Delete button
  5. Verify:
     - Deletion is blocked
     - Error message includes recipe count
     - Message matches pattern: "Cannot delete: X recipes use this ingredient"
  6. Record exact message shown
- **Files**: Testing `src/ui/ingredients_tab.py`
- **Parallel?**: No
- **Notes**: Create a recipe using an ingredient if none exists

### Subtask T015 - Test deletion blocked when Children exist
- **Purpose**: Verify cannot delete an L0 or L1 ingredient that has children.
- **Steps**:
  1. Navigate to Ingredients tab
  2. Change view/filter to show L0 or L1 ingredients (if available)
  3. Find an L0 or L1 ingredient that has children
  4. Select the ingredient
  5. Click Delete button
  6. Verify:
     - Deletion is blocked
     - Error message includes child count
     - Message matches pattern: "Cannot delete: X ingredients are children of this category"
  7. Record exact message shown
- **Files**: Testing `src/ui/ingredients_tab.py`
- **Parallel?**: No
- **Notes**: The hierarchy structure should already have L0/L1 with children

### Subtask T016 - Test deletion allowed when no references
- **Purpose**: Verify deletion succeeds for ingredient with no products, recipes, or children.
- **Steps**:
  1. Create a new L2 ingredient (Add Ingredient button)
  2. Give it a unique name like "Test Delete Ingredient"
  3. Save the ingredient
  4. Verify it has no products, no recipes, no children
  5. Select it and click Delete
  6. Verify:
     - Deletion succeeds (no error)
     - Ingredient is removed from list
     - If ingredient had aliases/crosswalks, verify they were cascade deleted (check database if needed)
  7. Record result
- **Files**: Testing `src/ui/ingredients_tab.py`
- **Parallel?**: No
- **Notes**: This confirms the happy path of deletion works

### Subtask T017 - Verify error messages include correct counts
- **Purpose**: Ensure error messages show accurate counts, not just "some" or "multiple".
- **Steps**:
  1. For the ingredient tested in T013 (Products):
     - Count the actual products in Products tab
     - Compare to the count in the error message
  2. For the ingredient tested in T014 (Recipes):
     - Count the actual recipes using the ingredient
     - Compare to the count in the error message
  3. For the ingredient tested in T015 (Children):
     - Count the actual children
     - Compare to the count in the error message
  4. Record if counts match
- **Files**: Various UI files
- **Parallel?**: No - depends on T013-T015
- **Notes**: Counts must be accurate for good user experience

### Subtask T018 - Document deletion test results
- **Purpose**: Create permanent record of deletion protection testing.
- **Steps**:
  1. Update `kitty-specs/036-ingredient-hierarchy-comprehensive/research.md`
  2. Add "Deletion Protection Test Results" section with:
     - Test matrix for each blocking scenario
     - Exact error messages captured
     - Count accuracy verification
     - Pass/fail status for each test
  3. Commit the update
- **Files**: `kitty-specs/036-ingredient-hierarchy-comprehensive/research.md`
- **Parallel?**: No - depends on T013-T017

## Test Strategy

Deletion test matrix:

| Scenario | Ingredient Tested | Expected Block | Actual Result | Count Accurate |
|----------|------------------|----------------|---------------|----------------|
| Has Products | [name] | Yes, show count | [pass/fail] | [yes/no] |
| Has Recipes | [name] | Yes, show count | [pass/fail] | [yes/no] |
| Has Children | [name] | Yes, show count | [pass/fail] | [yes/no] |
| No References | [Test ingredient] | No, allow delete | [pass/fail] | N/A |

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| No test data for scenarios | Create test ingredients/products/recipes as needed |
| Error message not shown | Check for dialog vs status bar vs console |
| Count mismatch | Debug `can_delete_ingredient()` if counts wrong |
| Cascade delete fails | Check database directly if aliases remain |

## Definition of Done Checklist

- [ ] Deletion blocked by Products tested (T013)
- [ ] Deletion blocked by Recipes tested (T014)
- [ ] Deletion blocked by Children tested (T015)
- [ ] Deletion allowed (no refs) tested (T016)
- [ ] Error message counts verified (T017)
- [ ] Results documented in research.md (T018)
- [ ] All scenarios pass or issues documented

## Review Guidance

- Verify all 4 deletion scenarios were tested
- Check that error messages match expected patterns
- Confirm counts in error messages are accurate
- Verify deletion with no references actually succeeds

## Activity Log

- 2026-01-02T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-03T01:28:29Z – system – shell_pid= – lane=done – Moved to done
