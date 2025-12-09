---
work_package_id: "WP07"
subtasks:
  - "T043"
  - "T044"
  - "T045"
  - "T046"
  - "T047"
  - "T048"
title: "Integration & Polish"
phase: "Phase 4 - Validation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-09T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 – Integration & Polish

## Objectives & Success Criteria

- Run full test suite and fix any regressions
- Validate all quickstart.md scenarios
- Test 3-level nesting end-to-end
- Test import/export round-trip
- Verify backward compatibility
- Update affected documentation

**Definition of Done**: All tests pass, all acceptance scenarios verified, documentation updated.

## Context & Constraints

**Reference Documents**:
- `kitty-specs/012-nested-recipes/quickstart.md` - Testing checklist
- `kitty-specs/012-nested-recipes/spec.md` - Acceptance scenarios and edge cases
- `CLAUDE.md` - Project conventions

**Success Criteria from Spec**:
- SC-001: Users can create a 3-level nested recipe structure in under 5 minutes
- SC-002: Cost calculation for a 3-level nested recipe completes instantly (<100ms)
- SC-003: Shopping list generation includes 100% of required ingredients
- SC-004: Circular reference attempts blocked with clear error message in 100% of cases
- SC-005: Existing recipes without sub-recipes function identically (backward compatibility)
- SC-006: Import/export round-trip preserves all recipe component relationships

## Subtasks & Detailed Guidance

### Subtask T043 – Run full test suite, fix any regressions

**Purpose**: Ensure all existing tests still pass after feature additions.

**Steps**:
1. Run full test suite: `pytest src/tests -v`
2. Identify any failures
3. Determine if failures are regressions or need test updates
4. Fix issues or update tests as needed

**Files**: `src/tests/`

**Commands**:
```bash
# Run all tests
pytest src/tests -v

# Run with coverage
pytest src/tests -v --cov=src --cov-report=term-missing

# Run specific test files if needed
pytest src/tests/services/test_recipe_service.py -v
```

**Expected Results**:
- All existing tests should pass
- New tests from WP02-WP05 should pass
- Service coverage should be >70%

---

### Subtask T044 – Validate quickstart.md testing checklist

**Purpose**: Verify all manual testing scenarios work as expected.

**Steps**:
1. Open application
2. Follow quickstart.md checklist
3. Document any issues found
4. Fix issues or document as known limitations

**Files**: `kitty-specs/012-nested-recipes/quickstart.md`

**Checklist from quickstart.md**:
```
- [ ] Create two simple recipes (A and B)
- [ ] Add recipe B as component of recipe A with quantity 2
- [ ] Verify cost shows B's cost × 2
- [ ] Try adding A as component of B (should fail: circular reference)
- [ ] Create recipe C, add B as component, then try adding C to A (should fail: circular reference)
- [ ] Create 3-level hierarchy: A → B → C, then try A → D → E → F (should fail: depth exceeded)
- [ ] Delete recipe B (should fail: used in A)
- [ ] Remove B from A, then delete B (should succeed)
- [ ] Export recipe with components, reimport to fresh database
```

**Document Results**:
- Pass/Fail for each item
- Screenshots if helpful
- Error messages received
- Any unexpected behavior

---

### Subtask T045 – Test 3-level nesting end-to-end

**Purpose**: Verify deep nesting works correctly throughout the system.

**Steps**:
1. Create hierarchy: Grandchild → Child → Parent
2. Verify UI displays all levels
3. Verify cost calculation includes all levels
4. Verify shopping list aggregates all ingredients
5. Test depth limit enforcement

**Test Scenario**:
```
Recipe: "Grandchild" (makes 1 batch)
- Ingredients: 1 cup flour, 0.5 cup sugar

Recipe: "Child" (makes 1 batch)
- Ingredients: 1 cup butter
- Components: 1x Grandchild

Recipe: "Parent" (makes 1 batch)
- Ingredients: 2 cups milk
- Components: 2x Child
```

**Expected Results**:
- Parent cost = milk cost + 2 × (butter cost + 1 × (flour cost + sugar cost))
- Shopping list:
  - 2 cups milk (direct)
  - 2 cups butter (1 × 2)
  - 2 cups flour (1 × 1 × 2)
  - 1 cup sugar (0.5 × 1 × 2)

---

### Subtask T046 – Test import/export round-trip

**Purpose**: Verify data portability is maintained.

**Steps**:
1. Create complex recipe hierarchy
2. Export to JSON
3. Clear database (or use fresh database)
4. Import from JSON
5. Verify all relationships restored
6. Verify costs match original

**Files**: Export/import test data

**Test Procedure**:
```python
# 1. Create test hierarchy
grandchild = create_recipe("Grandchild", ingredients=[...])
child = create_recipe("Child", ingredients=[...])
parent = create_recipe("Parent", ingredients=[...])
add_component(child, grandchild, qty=1)
add_component(parent, child, qty=2)

# 2. Record original data
original_parent_cost = calculate_cost(parent)
original_components = get_components(parent)

# 3. Export
export_to_json("test_export.json")

# 4. Clear database (backup first!)
# 5. Import
import_from_json("test_export.json")

# 6. Verify
imported_parent = get_recipe_by_name("Parent")
imported_cost = calculate_cost(imported_parent)
imported_components = get_components(imported_parent)

assert imported_cost == original_parent_cost
assert len(imported_components) == len(original_components)
```

---

### Subtask T047 – Verify backward compatibility

**Purpose**: Ensure existing recipes without components still work.

**Steps**:
1. Load existing database with recipes (no components)
2. Verify recipes display correctly
3. Verify cost calculation works
4. Verify recipe CRUD operations work
5. Verify import/export works for component-less recipes

**Tests**:
```python
def test_existing_recipe_still_works():
    """Recipe without components behaves identically."""
    # Create recipe without components
    recipe = create_recipe("Simple", ingredients=[...])

    # All existing operations should work
    assert get_recipe(recipe.id) is not None
    assert calculate_cost(recipe.id) >= 0
    assert len(get_components(recipe.id)) == 0

    # Update should work
    update_recipe(recipe.id, {"name": "Updated"})

    # Delete should work
    delete_recipe(recipe.id)


def test_recipe_cost_without_components():
    """Cost calculation unchanged for recipes without components."""
    recipe = create_recipe_with_priced_ingredients("NoComponents", [
        ("Flour", 2.0, "cups", 0.50),  # $1.00
    ])

    # Old method
    old_cost = recipe.calculate_cost()

    # New method
    new_cost = calculate_total_cost_with_components(recipe.id)

    assert old_cost == new_cost["direct_ingredient_cost"]
    assert new_cost["total_component_cost"] == 0
    assert old_cost == new_cost["total_cost"]
```

---

### Subtask T048 – Update affected documentation

**Purpose**: Keep documentation in sync with implementation.

**Steps**:
1. Update CLAUDE.md if any new patterns were introduced
2. Update any affected README or user documentation
3. Ensure spec.md and plan.md reflect final implementation
4. Add any post-implementation notes

**Files to Review**:
- `CLAUDE.md` - Project conventions
- `docs/` - Any user-facing documentation
- `kitty-specs/012-nested-recipes/spec.md` - Mark status as "Complete"
- `kitty-specs/012-nested-recipes/plan.md` - Add implementation notes

**Documentation Updates**:
```markdown
# In CLAUDE.md (if needed)

## Key Design Decisions

- **Recipes and Sub-Recipes**: Recipes can include other recipes as components via RecipeComponent junction table. Maximum 3 levels of nesting. Circular references are prevented.
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Regression in existing functionality | Full test suite run before sign-off |
| Edge case not covered | Follow spec.md edge cases section |
| Documentation out of sync | Review all docs before marking complete |

## Definition of Done Checklist

- [ ] All tests pass (pytest src/tests -v)
- [ ] Service coverage >70%
- [ ] All quickstart.md scenarios verified
- [ ] 3-level nesting works correctly
- [ ] Import/export round-trip preserves data
- [ ] Existing recipes work identically (backward compat)
- [ ] Documentation updated
- [ ] spec.md status changed to "Complete"

## Review Guidance

- Run test suite and verify all green
- Perform manual testing per quickstart checklist
- Review documentation changes
- Confirm no regressions in existing features
- Check error messages are user-friendly

## Activity Log

- 2025-12-09T00:00:00Z – system – lane=planned – Prompt created.
