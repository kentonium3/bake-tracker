---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
title: "Run Automated Test Suite"
phase: "Phase 1 - Automated Testing"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "33367"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-02T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Run Automated Test Suite

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Execute all ingredient hierarchy automated tests
- Achieve 100% pass rate (zero failures, zero errors)
- Generate coverage report showing >70% coverage for ingredient services
- Document results in research.md

**Success Metrics**:
- All tests in `test_ingredient_hierarchy_service.py` pass
- All tests in `test_ingredient_service.py` pass
- All leaf-only validation tests pass
- Coverage report generated and saved

## Context & Constraints

- **Reference**: `kitty-specs/036-ingredient-hierarchy-comprehensive/plan.md`
- **Research**: `kitty-specs/036-ingredient-hierarchy-comprehensive/research.md`
- **Constitution**: `.kittify/memory/constitution.md` (Principle IV: Test-Driven Development)

This is Phase 4 of the F033-F036 ingredient hierarchy implementation. Phases 1-3 have been merged:
- F033: Fixed ingredient edit form mental model, hierarchy display
- F034: Fixed cascading filters across all tabs
- F035: Added deletion protection, slug auto-generation

## Subtasks & Detailed Guidance

### Subtask T001 - Run ingredient hierarchy service tests
- **Purpose**: Verify all hierarchy navigation and computation logic works correctly.
- **Steps**:
  1. Activate virtual environment: `source venv/bin/activate`
  2. Run tests: `PYTHONPATH=. pytest src/tests/services/test_ingredient_hierarchy_service.py -v --tb=short`
  3. Capture output and pass/fail count
- **Files**: `src/tests/services/test_ingredient_hierarchy_service.py`
- **Parallel?**: No - run first to establish baseline
- **Expected**: ~40 tests pass

### Subtask T002 - Run ingredient service tests including deletion protection
- **Purpose**: Verify CRUD operations and F035 deletion protection.
- **Steps**:
  1. Run tests: `PYTHONPATH=. pytest src/tests/services/test_ingredient_service.py -v --tb=short`
  2. Capture output
  3. Note especially: deletion blocked tests (lines 530-660)
- **Files**: `src/tests/services/test_ingredient_service.py`
- **Parallel?**: No - run sequentially
- **Expected**: All deletion protection tests pass

### Subtask T003 - Run recipe leaf-only validation tests
- **Purpose**: Verify recipes can only use L2 (leaf) ingredients.
- **Steps**:
  1. Run tests: `PYTHONPATH=. pytest src/tests/services/test_recipe_service.py -v -k "leaf" --tb=short`
  2. Capture output
- **Files**: `src/tests/services/test_recipe_service.py`
- **Parallel?**: Yes - can run alongside T004
- **Expected**: Tests for `test_create_recipe_with_leaf_ingredient_succeeds`, `test_create_recipe_with_non_leaf_ingredient_fails`, etc. pass

### Subtask T004 - Run product catalog leaf-only tests
- **Purpose**: Verify products can only be assigned to L2 (leaf) ingredients.
- **Steps**:
  1. Run tests: `PYTHONPATH=. pytest src/tests/services/test_product_catalog_service.py -v -k "leaf" --tb=short`
  2. Capture output
- **Files**: `src/tests/services/test_product_catalog_service.py`
- **Parallel?**: Yes - can run alongside T003
- **Expected**: Tests for leaf-only product assignment pass

### Subtask T005 - Generate coverage report for ingredient services
- **Purpose**: Document test coverage percentage.
- **Steps**:
  1. Run with coverage: `PYTHONPATH=. pytest src/tests -v --cov=src/services --cov-report=html --cov-report=term`
  2. Check terminal output for coverage percentage
  3. Open `htmlcov/index.html` to review detailed coverage
  4. Note coverage for `ingredient_service.py` and `ingredient_hierarchy_service.py`
- **Files**: `htmlcov/` (generated), terminal output
- **Parallel?**: No - run after individual tests
- **Expected**: >70% coverage for ingredient services

### Subtask T006 - Document test results in research.md
- **Purpose**: Create permanent record of test verification.
- **Steps**:
  1. Update `kitty-specs/036-ingredient-hierarchy-comprehensive/research.md`
  2. Add "Test Execution Results" section with:
     - Total tests run
     - Pass/fail counts
     - Coverage percentage
     - Any notable findings
  3. Commit the update
- **Files**: `kitty-specs/036-ingredient-hierarchy-comprehensive/research.md`
- **Parallel?**: No - depends on T001-T005

## Test Strategy

This work package IS the test execution. Commands:

```bash
# Full ingredient test suite
PYTHONPATH=. pytest src/tests -v -k ingredient --tb=short

# Specific test files
PYTHONPATH=. pytest src/tests/services/test_ingredient_hierarchy_service.py -v
PYTHONPATH=. pytest src/tests/services/test_ingredient_service.py -v

# With coverage
PYTHONPATH=. pytest src/tests -v --cov=src/services --cov-report=html
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Test failures | If any test fails, investigate and fix before proceeding |
| Missing dependencies | Run `pip install -r requirements.txt` first |
| Database state pollution | Tests use fixtures - verify no cross-test contamination |
| Coverage tool missing | Install with `pip install pytest-cov` |

## Definition of Done Checklist

- [ ] All hierarchy service tests pass (T001)
- [ ] All ingredient service tests pass (T002)
- [ ] All leaf-only recipe tests pass (T003)
- [ ] All leaf-only product tests pass (T004)
- [ ] Coverage report generated (T005)
- [ ] Results documented in research.md (T006)
- [ ] Zero test failures overall

## Review Guidance

- Verify test output shows 0 failures, 0 errors
- Check coverage percentage meets >70% threshold
- Confirm research.md has been updated with results
- Any skipped tests should have documented reason

## Activity Log

- 2026-01-02T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-02T21:53:41Z – claude – shell_pid=33367 – lane=doing – Started implementation
