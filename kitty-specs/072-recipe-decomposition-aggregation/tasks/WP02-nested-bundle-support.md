---
work_package_id: WP02
title: Nested Bundle Support
lane: "for_review"
dependencies: [WP01]
base_branch: 072-recipe-decomposition-aggregation-WP01
base_commit: f0556ed2280479fb06fd6f005a5cde6bd1642677
created_at: '2026-01-27T16:49:52.806213+00:00'
subtasks:
- T007
- T008
- T009
- T010
phase: Phase 2 - Nested Bundles
assignee: ''
agent: ''
shell_pid: "99034"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-27T16:30:47Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 - Nested Bundle Support

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
spec-kitty implement WP02 --base WP01
```

This work package depends on WP01 (core implementation must exist).

---

## Objectives & Success Criteria

Add comprehensive tests for multi-level nested bundle decomposition:

1. **2-Level Nesting**: Bundle containing bundles with correct quantity multiplication
2. **3+ Level Nesting**: Deep hierarchies traverse correctly
3. **DAG Patterns**: Same FG appearing in multiple branches doesn't raise false circular reference errors
4. **Mixed Events**: Events with both atomic FGs and bundles process correctly

**Success Metrics**:
- All 4 test subtasks pass
- DAG test confirms path-based (not global) cycle detection
- Tests cover User Story 2 acceptance scenarios

---

## Context & Constraints

### Reference Documents
- **Spec**: `kitty-specs/072-recipe-decomposition-aggregation/spec.md` (User Story 2)
- **Plan**: `kitty-specs/072-recipe-decomposition-aggregation/plan.md`
- **Research**: `kitty-specs/072-recipe-decomposition-aggregation/research.md`

### Prerequisite
- WP01 must be complete (core `calculate_recipe_requirements()` exists)
- Test file `src/tests/test_planning_service.py` exists from WP01

### Key Concept: DAG vs Circular Reference

**DAG (Allowed)**:
```
BundleA → BundleB → FU1
       ↘ BundleC → FU1  (same FU1 reused - OK!)
```
Both paths lead to FU1, but it's not circular. Path-based detection allows this.

**Circular Reference (Error)**:
```
BundleA → BundleB → BundleA  (BundleA in own ancestry - ERROR!)
```

---

## Subtasks & Detailed Guidance

### Subtask T007 - Write unit tests for 2-level nested bundles

**Purpose**: Verify quantity multiplication works through two levels of nesting.

**Steps**:
1. Create test fixtures for 2-level structure:
   ```
   OuterBundle (quantity 5 in event)
   └── InnerBundle (quantity 3 in outer)
       └── FinishedUnit (quantity 2 in inner) → Recipe
   ```

2. Expected calculation:
   - Event quantity: 5
   - Inner bundle per outer: 3
   - FU per inner: 2
   - Total recipe quantity: 5 × 3 × 2 = 30

3. Write test:
   ```python
   def test_2_level_nested_bundle_multiplies_correctly(session):
       """
       Given a bundle containing another bundle (2-level nesting) with quantity 5
       When decomposed
       Then quantities are correctly multiplied through both levels
       """
       # Create Recipe
       recipe = Recipe(name="Test Recipe", ...)
       session.add(recipe)

       # Create FinishedUnit linked to Recipe
       fu = FinishedUnit(slug="test-fu", recipe_id=recipe.id, ...)
       session.add(fu)

       # Create InnerBundle containing 2 of the FU
       inner_bundle = FinishedGood(slug="inner-bundle", ...)
       session.add(inner_bundle)
       session.flush()

       inner_comp = Composition(
           assembly_id=inner_bundle.id,
           finished_unit_id=fu.id,
           component_quantity=2,
       )
       session.add(inner_comp)

       # Create OuterBundle containing 3 of InnerBundle
       outer_bundle = FinishedGood(slug="outer-bundle", ...)
       session.add(outer_bundle)
       session.flush()

       outer_comp = Composition(
           assembly_id=outer_bundle.id,
           finished_good_id=inner_bundle.id,
           component_quantity=3,
       )
       session.add(outer_comp)

       # Create Event with 5 of OuterBundle
       event = Event(name="Test Event", ...)
       session.add(event)
       session.flush()

       efg = EventFinishedGood(
           event_id=event.id,
           finished_good_id=outer_bundle.id,
           quantity=5,
       )
       session.add(efg)
       session.flush()

       # Execute
       result = calculate_recipe_requirements(event.id, session=session)

       # Verify: 5 × 3 × 2 = 30
       assert len(result) == 1
       assert result[recipe] == 30
   ```

**Files**:
- `src/tests/test_planning_service.py` (~60 lines)

**Parallel?**: Yes - can run with T008, T009, T010

**Notes**:
- Match acceptance scenario 1 from User Story 2

---

### Subtask T008 - Write unit tests for 3+ level nested bundles

**Purpose**: Verify deep hierarchies (up to MAX_FG_NESTING_DEPTH) work correctly.

**Steps**:
1. Create test fixture with 3-level structure:
   ```
   Level1Bundle (quantity 2 in event)
   └── Level2Bundle (quantity 3 in level1)
       └── Level3Bundle (quantity 4 in level2)
           └── FinishedUnit (quantity 5 in level3) → Recipe
   ```

2. Expected: 2 × 3 × 4 × 5 = 120

3. Write test:
   ```python
   def test_3_level_nested_bundle_traverses_all_levels(session):
       """
       Given a bundle with 3+ levels of nesting
       When decomposed
       Then all levels are traversed and final atomic quantities are correct
       """
       # Create deep structure: L1 → L2 → L3 → FU
       # Quantities: 2 × 3 × 4 × 5 = 120

       result = calculate_recipe_requirements(event.id, session=session)

       assert len(result) == 1
       assert result[recipe] == 120
   ```

4. Optional: Add test for 5-level nesting (max supported per SC-001)

**Files**:
- `src/tests/test_planning_service.py` (~70 lines)

**Parallel?**: Yes

**Notes**:
- Match acceptance scenario 2 from User Story 2
- Consider creating a helper function to build N-level bundle structures

---

### Subtask T009 - Write unit tests for DAG patterns (same FG in multiple branches)

**Purpose**: Verify that path-based cycle detection allows DAG patterns (same FG reused in multiple branches).

**Steps**:
1. Create DAG structure:
   ```
   MainBundle
   ├── BranchA (quantity 2)
   │   └── SharedFU (quantity 3) → RecipeA
   └── BranchB (quantity 4)
       └── SharedFU (quantity 5) → RecipeA  (SAME FU!)
   ```

2. Expected: (2 × 3) + (4 × 5) = 6 + 20 = 26 for RecipeA

3. Write test:
   ```python
   def test_dag_pattern_same_fg_multiple_branches_allowed(session):
       """
       Given a bundle structure where the same FG appears in multiple branches (DAG)
       When decomposed
       Then no circular reference error is raised and quantities aggregate correctly
       """
       # Create SharedFU used in both branches
       shared_fu = FinishedUnit(...)

       # Create BranchA containing SharedFU (qty 3)
       # Create BranchB containing SharedFU (qty 5)
       # Create MainBundle containing BranchA (qty 2) and BranchB (qty 4)

       result = calculate_recipe_requirements(event.id, session=session)

       # Should NOT raise CircularReferenceError
       # Should aggregate: (2×3) + (4×5) = 26
       assert result[recipe] == 26
   ```

**Files**:
- `src/tests/test_planning_service.py` (~70 lines)

**Parallel?**: Yes

**Notes**:
- This test validates the path-based (not global visited set) approach
- If this test fails with CircularReferenceError, the implementation is wrong

---

### Subtask T010 - Write unit tests for mixed atomic/bundle events

**Purpose**: Verify events with both direct FG selections and bundle selections work.

**Steps**:
1. Create mixed structure:
   ```
   Event contains:
   - AtomicFG (qty 10) → direct FinishedUnit → RecipeA
   - BundleFG (qty 5)
     └── FinishedUnit (qty 2) → RecipeB
   ```

2. Expected: RecipeA = 10, RecipeB = 10 (5 × 2)

3. Write test:
   ```python
   def test_mixed_atomic_and_bundle_fgs_process_correctly(session):
       """
       Given a mix of atomic FGs and bundles in the same event
       When decomposed
       Then atomic FGs pass through unchanged while bundles are expanded
       """
       # Create atomic FG (single FU component)
       # Create bundle FG (FU component with qty 2)
       # Event has: atomic (qty 10), bundle (qty 5)

       result = calculate_recipe_requirements(event.id, session=session)

       assert result[recipe_a] == 10  # Atomic: 10 × 1
       assert result[recipe_b] == 10  # Bundle: 5 × 2
   ```

**Files**:
- `src/tests/test_planning_service.py` (~60 lines)

**Parallel?**: Yes

**Notes**:
- Match acceptance scenario 3 from User Story 2
- Atomic FGs are just bundles with a single component (qty 1)

---

## Test Strategy

**Test File**: `src/tests/test_planning_service.py`

**Run Tests**:
```bash
./run-tests.sh src/tests/test_planning_service.py -v -k "nested or dag or mixed"
```

**Fixture Factory Pattern**:
Consider creating a helper for building nested structures:
```python
def create_nested_bundle(session, depth, quantities):
    """Create a bundle structure with specified nesting depth and quantities."""
    # Build from inside out...
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Complex fixture setup | Create reusable factory functions |
| Test isolation | Each test creates own fixtures, flushes session |
| Quantity math errors | Document expected calculations in test docstrings |

---

## Definition of Done Checklist

- [ ] Test for 2-level nesting passes (T007)
- [ ] Test for 3+ level nesting passes (T008)
- [ ] Test for DAG patterns passes (T009) - confirms path-based detection
- [ ] Test for mixed atomic/bundle passes (T010)
- [ ] All tests in `src/tests/test_planning_service.py`
- [ ] Tests match User Story 2 acceptance scenarios

---

## Review Guidance

**Reviewers should verify**:
1. DAG test (T009) confirms correct cycle detection behavior
2. Quantity math is documented and correct
3. Tests are independent (no shared state)
4. Fixture setup is clear and maintainable

---

## Activity Log

- 2026-01-27T16:30:47Z - system - lane=planned - Prompt generated via /spec-kitty.tasks
- 2026-01-27T16:52:50Z – unknown – shell_pid=99034 – lane=for_review – Ready for review: 8 new tests for nested bundles (2-level, 3+ level, DAG patterns, mixed atomic/bundle), all 15 tests pass
