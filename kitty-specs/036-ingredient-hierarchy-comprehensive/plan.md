# Implementation Plan: Ingredient Hierarchy Comprehensive Testing

**Branch**: `036-ingredient-hierarchy-comprehensive` | **Date**: 2026-01-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/036-ingredient-hierarchy-comprehensive/spec.md`

## Summary

Phase 4 of the F033-F036 ingredient hierarchy implementation. This feature focuses on comprehensive test verification of Phases 1-3 (F033, F034, F035) rather than new code implementation. The deliverable is documented evidence that all tests pass, any discovered bugs are fixed, and the ingredient hierarchy is production-ready.

**Key Activities**:
1. Run all existing ingredient hierarchy tests and verify 100% pass rate
2. Manually validate cascading selectors in UI (Product edit, Recipe creation, filters)
3. Verify deletion protection blocks correctly in all scenarios
4. Document test coverage and results
5. Fix any discovered edge cases or regressions

**UAT Status**: Deferred to separate session with Marianne

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter, pytest
**Storage**: SQLite with WAL mode
**Testing**: pytest with coverage reporting
**Target Platform**: Desktop (macOS/Windows/Linux)
**Project Type**: Single desktop application
**Performance Goals**: All tests complete in <60 seconds
**Constraints**: No new code required unless bugs discovered
**Scale/Scope**: ~1500 existing tests, ~50 ingredient-specific tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Testing validates user workflows |
| II. Data Integrity & FIFO | PASS | Deletion protection enforces referential integrity |
| III. Future-Proof Schema | N/A | No schema changes |
| IV. Test-Driven Development | PASS | This feature IS testing |
| V. Layered Architecture | PASS | Tests validate layer separation |
| VI. Schema Change Strategy | N/A | No schema changes |
| VII. Pragmatic Aspiration | PASS | Desktop testing focus |

**Constitution Gate**: PASSED - No violations

## Project Structure

### Documentation (this feature)

```
kitty-specs/036-ingredient-hierarchy-comprehensive/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0: Test coverage analysis
├── tasks.md             # Phase 2 output (from /spec-kitty.tasks)
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```
src/
├── models/
│   └── ingredient.py           # Ingredient model (verify relationships)
├── services/
│   ├── ingredient_service.py   # Core ingredient operations
│   └── ingredient_hierarchy_service.py  # Hierarchy-specific logic
├── ui/
│   ├── ingredients_tab.py      # Ingredients list view
│   └── forms/
│       └── ingredient_edit_form.py  # Edit form with cascading selectors
└── tests/
    └── services/
        ├── test_ingredient_service.py
        ├── test_ingredient_hierarchy_service.py
        └── test_ingredient_deletion.py  # F035 deletion tests
```

**Structure Decision**: Existing structure - no new directories needed. Testing feature verifies existing code.

## Complexity Tracking

*No violations - this is a testing feature with no new complexity*

## Test Execution Plan

### Phase 1: Automated Test Verification

**Run all ingredient-related tests**:
```bash
PYTHONPATH=. pytest src/tests -v -k ingredient --tb=short
```

**Expected coverage areas**:
- `test_ingredient_service.py` - CRUD operations, hierarchy level computation
- `test_ingredient_hierarchy_service.py` - Hierarchy traversal, cycle detection
- `test_ingredient_deletion.py` - Deletion protection (F035)

### Phase 2: Manual UI Validation

**Cascading Selector Tests** (4 locations):
1. Product edit form - ingredient selection
2. Recipe creation form - ingredient selection
3. Product tab filter - hierarchy filtering
4. Inventory tab filter - hierarchy filtering

**Test Protocol**:
- Select L0 → verify L1 updates
- Select L1 → verify L2 updates
- Change L0 → verify L1/L2 reset
- Clear → verify all reset

### Phase 3: Deletion Protection Validation

**Test Matrix**:
| Scenario | Expected Result | Error Message |
|----------|-----------------|---------------|
| Delete ingredient with Products | BLOCKED | "Cannot delete: X products use this ingredient" |
| Delete ingredient with Recipes | BLOCKED | "Cannot delete: X recipes use this ingredient" |
| Delete ingredient with Children | BLOCKED | "Cannot delete: X ingredients are children of this category" |
| Delete ingredient with no refs | ALLOWED | (cascade delete aliases/crosswalks) |

### Phase 4: Test Coverage Documentation

Generate coverage report:
```bash
PYTHONPATH=. pytest src/tests -v --cov=src/services --cov-report=html
```

Document results in `research.md` with:
- Total tests passed/failed
- Coverage percentage for ingredient services
- Any gaps identified

## Success Criteria Checklist

- [ ] 100% of ingredient hierarchy tests pass (zero failures)
- [ ] All 11 validation rules (VAL-ING-001 through VAL-ING-011) verified
- [ ] Cascading selectors work in all 4 UI locations
- [ ] Deletion protection blocks in all 3 scenarios
- [ ] Test coverage for ingredient services >70%
- [ ] Any discovered bugs documented and fixed

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Tests fail due to Phase 1-3 bugs | Budget time for bug fixes in task estimates |
| Manual UI testing inconsistent | Create repeatable test script |
| Coverage tools misconfigured | Verify pytest-cov installed in venv |

---

**Plan Status**: READY FOR TASKS
**Next Step**: Run `/spec-kitty.tasks` to generate work packages
