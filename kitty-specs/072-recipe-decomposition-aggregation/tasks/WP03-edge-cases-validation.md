---
work_package_id: "WP03"
subtasks:
  - "T011"
  - "T012"
  - "T013"
  - "T014"
title: "Edge Cases & Validation"
phase: "Phase 2 - Edge Cases"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-27T16:30:47Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Edge Cases & Validation

## Important: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP03 --base WP01
```

This work package depends on WP01 (core implementation must exist).

---

## Objectives & Success Criteria

Implement and test all edge case handling to ensure system robustness:

1. **Circular Reference Detection**: Raise `CircularReferenceError` when bundle references itself
2. **Empty Event Handling**: Return empty dict `{}` without error
3. **Missing Recipe Validation**: Raise `ValidationError` with clear message
4. **Zero-Quantity Components**: Skip during decomposition

**Success Metrics**:
- All 4 edge case tests pass
- Error messages are clear and actionable
- Tests cover User Story 3 acceptance scenarios

---

## Context & Constraints

### Reference Documents
- **Spec**: `kitty-specs/072-recipe-decomposition-aggregation/spec.md` (User Story 3)
- **Plan**: `kitty-specs/072-recipe-decomposition-aggregation/plan.md` (Edge Case Handling table)
- **Research**: `kitty-specs/072-recipe-decomposition-aggregation/research.md`

### Prerequisite
- WP01 must be complete (core `calculate_recipe_requirements()` exists)
- Test file `src/tests/test_planning_service.py` exists from WP01

### Edge Case Summary (from spec)

| Edge Case | Expected Behavior |
|-----------|-------------------|
| Empty event (no FG selections) | Return `{}` |
| Circular reference in bundle | Raise `CircularReferenceError` |
| FinishedUnit without recipe | Raise `ValidationError` |
| Zero-quantity component | Skip (don't add to result) |
| Event not found | Raise `ValidationError` |

---

## Subtasks & Detailed Guidance

### Subtask T011 - Implement and test circular reference detection

**Purpose**: Verify that circular bundle structures are detected and raise appropriate errors.

**Steps**:
1. Create a circular structure (requires bypassing normal validation):
   ```
   BundleA → BundleB → BundleA (circular!)
   ```

2. Note: You may need to create the structure directly via session to bypass constraints:
   ```python
   # Create BundleA and BundleB first
   bundle_a = FinishedGood(slug="bundle-a", ...)
   bundle_b = FinishedGood(slug="bundle-b", ...)
   session.add_all([bundle_a, bundle_b])
   session.flush()

   # Create compositions that form a cycle
   # BundleA contains BundleB
   comp_a_to_b = Composition(
       assembly_id=bundle_a.id,
       finished_good_id=bundle_b.id,
       component_quantity=1,
   )
   # BundleB contains BundleA (creates cycle)
   comp_b_to_a = Composition(
       assembly_id=bundle_b.id,
       finished_good_id=bundle_a.id,
       component_quantity=1,
   )
   session.add_all([comp_a_to_b, comp_b_to_a])
   session.flush()
   ```

3. Write test:
   ```python
   def test_circular_reference_raises_error(session):
       """
       Given a bundle that references itself (directly or indirectly)
       When decomposition is attempted
       Then a circular reference error is raised
       """
       # Create circular structure A → B → A
       # ...

       with pytest.raises(CircularReferenceError) as exc_info:
           calculate_recipe_requirements(event.id, session=session)

       # Optionally verify error details
       assert bundle_a.id in exc_info.value.path or bundle_b.id in exc_info.value.path
   ```

4. Also test direct self-reference:
   ```python
   def test_direct_self_reference_raises_error(session):
       """Bundle directly containing itself should raise CircularReferenceError."""
       # BundleA → BundleA
   ```

**Files**:
- `src/tests/test_planning_service.py` (~80 lines for both tests)

**Parallel?**: Yes

**Notes**:
- Match acceptance scenario 1 from User Story 3
- The database constraint `ck_composition_no_self_reference` prevents direct self-reference at DB level, but indirect cycles are still possible
- May need to test indirect cycle (A → B → A) rather than direct

---

### Subtask T012 - Implement and test empty event handling

**Purpose**: Verify that events with no FG selections return empty dict without error.

**Steps**:
1. Create event with no EventFinishedGoods:
   ```python
   event = Event(name="Empty Event", ...)
   session.add(event)
   session.flush()
   # No EventFinishedGood records created
   ```

2. Write test:
   ```python
   def test_empty_event_returns_empty_dict(session):
       """
       Given an event with no FG selections
       When recipe requirements are calculated
       Then an empty dictionary is returned
       """
       event = Event(name="Empty Event", event_date=date.today())
       session.add(event)
       session.flush()

       result = calculate_recipe_requirements(event.id, session=session)

       assert result == {}
       assert isinstance(result, dict)
   ```

3. Also test event that doesn't exist:
   ```python
   def test_nonexistent_event_raises_validation_error(session):
       """Event ID that doesn't exist should raise ValidationError."""
       with pytest.raises(ValidationError):
           calculate_recipe_requirements(99999, session=session)
   ```

**Files**:
- `src/tests/test_planning_service.py` (~40 lines)

**Parallel?**: Yes

**Notes**:
- Match acceptance scenario 3 from User Story 3
- This is the simplest edge case

---

### Subtask T013 - Implement and test missing recipe validation

**Purpose**: Verify that FinishedUnits without recipes raise clear errors.

**Steps**:
1. The core implementation in T002 should already handle this:
   ```python
   if fu and fu.recipe:
       recipe = fu.recipe
       result[recipe] = result.get(recipe, 0) + effective_qty
   else:
       raise ValidationError([f"FinishedUnit {fu.id} has no recipe"])
   ```

2. Create test fixture with FU missing recipe:
   ```python
   # FinishedUnit requires recipe_id, so we may need to:
   # Option A: Create FU, then set recipe_id = None manually
   # Option B: Mock the relationship to return None

   fu = FinishedUnit(slug="no-recipe-fu", recipe_id=recipe.id, ...)
   session.add(fu)
   session.flush()
   # Now break the relationship
   fu.recipe_id = None  # This might violate FK constraint

   # Alternative: Delete the recipe after creating the FU
   # This depends on ondelete behavior
   ```

3. Write test:
   ```python
   def test_finished_unit_without_recipe_raises_validation_error(session):
       """
       Given an FG without a linked recipe
       When mapping to recipe is attempted
       Then an appropriate validation error is raised
       """
       # This test may need special setup to create invalid state
       # Consider using mocking if FK constraints prevent it

       with pytest.raises(ValidationError) as exc_info:
           calculate_recipe_requirements(event.id, session=session)

       assert "no recipe" in str(exc_info.value).lower()
   ```

**Files**:
- `src/tests/test_planning_service.py` (~50 lines)

**Parallel?**: Yes

**Notes**:
- Match acceptance scenario 2 from User Story 3
- May need to use mocking or carefully construct invalid state
- The FinishedUnit model has `recipe_id` as NOT NULL with ondelete=CASCADE, so normal operation shouldn't create this state
- This test validates defensive coding

---

### Subtask T014 - Implement and test zero-quantity component handling

**Purpose**: Verify that components with zero (or negative) quantities are skipped.

**Steps**:
1. The core implementation in T002 should already handle this:
   ```python
   effective_qty = int(comp.component_quantity * multiplier)
   if effective_qty <= 0:
       continue  # Skip zero-quantity components
   ```

2. Create test with zero-quantity component:
   ```python
   # Bundle with two components: qty 5 and qty 0
   bundle = FinishedGood(...)
   comp_normal = Composition(..., component_quantity=5)
   comp_zero = Composition(..., component_quantity=0)  # Should be skipped
   ```

3. Write test:
   ```python
   def test_zero_quantity_components_skipped(session):
       """
       Given a bundle containing zero-quantity components
       When decomposed
       Then zero-quantity components are skipped in decomposition
       """
       # Create bundle with:
       # - Component A (qty 2) → RecipeA
       # - Component B (qty 0) → RecipeB (should be skipped)

       result = calculate_recipe_requirements(event.id, session=session)

       assert recipe_a in result
       assert recipe_b not in result  # Skipped due to zero qty
   ```

4. Also test that DB constraint may prevent qty <= 0:
   ```python
   # The Composition model has:
   # CheckConstraint("component_quantity > 0", name="ck_composition_component_quantity_positive")
   # So we may need to bypass this for testing
   ```

**Files**:
- `src/tests/test_planning_service.py` (~50 lines)

**Parallel?**: Yes

**Notes**:
- From spec edge cases: "What happens when a bundle contains zero-quantity components? Skip them in decomposition."
- The DB constraint `ck_composition_component_quantity_positive` prevents qty <= 0, but the code should still handle it defensively
- May need to use raw SQL or disable constraint for test

---

## Test Strategy

**Test File**: `src/tests/test_planning_service.py`

**Run Tests**:
```bash
./run-tests.sh src/tests/test_planning_service.py -v -k "circular or empty or missing or zero"
```

**Testing Invalid States**:
Some edge cases require creating "impossible" database states:
- Circular references (bypasses validation)
- Missing recipes (bypasses FK constraint)
- Zero quantities (bypasses check constraint)

Options:
1. **Raw SQL**: `session.execute(text("INSERT ..."))`
2. **Mocking**: Mock the relationship/attribute
3. **Constraint deferral**: If SQLite supports it
4. **Accept limitations**: Document that some states are protected at DB level

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| FK constraints prevent invalid test data | Use mocking or raw SQL |
| Test may be testing DB constraints not code | Document what's being tested |
| Error messages may not match expected | Use flexible assertions (contains rather than exact match) |

---

## Definition of Done Checklist

- [ ] Test for circular reference detection passes (T011)
- [ ] Test for empty event handling passes (T012)
- [ ] Test for missing recipe validation passes (T013)
- [ ] Test for zero-quantity skipping passes (T014)
- [ ] All tests in `src/tests/test_planning_service.py`
- [ ] Tests cover User Story 3 acceptance scenarios
- [ ] Error messages are clear and actionable

---

## Review Guidance

**Reviewers should verify**:
1. Circular reference test actually tests the code path (not just DB constraint)
2. Error messages include enough context for debugging
3. Tests don't leave invalid data in session
4. Edge case handling is defensive (doesn't assume valid input)

---

## Activity Log

- 2026-01-27T16:30:47Z - system - lane=planned - Prompt generated via /spec-kitty.tasks
