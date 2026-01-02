# Research: Ingredient Hierarchy Test Coverage Analysis

**Feature**: 036-ingredient-hierarchy-comprehensive
**Date**: 2026-01-02
**Purpose**: Analyze existing test coverage for ingredient hierarchy to identify gaps before comprehensive testing

## Decision Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Test execution approach | pytest with coverage | Standard tooling, integrates with CI |
| Manual UI testing | Checklist-based | Repeatable, documentable results |
| UAT timing | Deferred | Schedule separately with Marianne |
| Bug fix approach | Fix in this feature | Keep Phase 4 self-contained |

## Test Coverage Inventory

### Ingredient Hierarchy Service Tests

**Location**: `src/tests/services/test_ingredient_hierarchy_service.py`

| Test Class | Coverage Area | Test Count |
|------------|---------------|------------|
| `TestGetRootIngredients` | L0 retrieval | ~5 |
| `TestGetChildren` | Child navigation | ~5 |
| `TestGetAncestors` | Ancestor path | ~5 |
| `TestGetHierarchyPath` | Full path string | ~5 |
| `TestComputeHierarchyLevel` | Level calculation | ~5 |
| `TestCycleDetection` | Circular reference blocking | ~3 |
| `TestGetIngredientsByLevel` | Level filtering | ~4 |
| `TestGetProductCount` | Product reference count | ~4 |
| `TestGetRecipeUsageCount` | Recipe reference count | ~4 |

**Estimated total**: ~40 tests

### Ingredient Service Tests (Deletion Protection)

**Location**: `src/tests/services/test_ingredient_service.py`

| Test Class | Coverage Area | Lines |
|------------|---------------|-------|
| `TestDeletionBlockedByProducts` | Product reference blocking | 530-570 |
| `TestDeletionBlockedByRecipes` | Recipe reference blocking | 572-618 |
| `TestDeletionBlockedByChildren` | Child ingredient blocking | 618-660 |
| `TestCreateIngredientHierarchy` | Hierarchy creation | 410-460 |
| `TestUpdateIngredientHierarchy` | Parent change validation | 457-520 |
| `TestFieldNormalization` | name→display_name mapping | 487-510 |

### Integration Tests

**Location**: `src/tests/integration/`

| Test File | Coverage Area |
|-----------|---------------|
| `test_inventory_flow.py:249` | Deletion blocked by products |
| `test_nested_recipes_flow.py` | Recipe-ingredient relationships |
| `test_packaging_flow.py` | Packaging ingredient handling |

### Validation Rule Coverage

| Rule ID | Validation | Test Location | Status |
|---------|-----------|---------------|--------|
| VAL-ING-001 | Name required | test_services.py | Exists |
| VAL-ING-002 | Slug unique | test_models.py:142 | Exists |
| VAL-ING-003 | L2 needs L1 parent | test_ingredient_service.py | Exists |
| VAL-ING-004 | L1 needs L0 parent | test_ingredient_service.py | Exists |
| VAL-ING-005 | Cannot change parent if has children | test_ingredient_service.py | Exists |
| VAL-ING-006 | Cannot change to non-leaf if has products | test_product_catalog_service.py | Exists |
| VAL-ING-007 | Cannot change to non-leaf if in recipes | test_recipe_service.py | Exists |
| VAL-ING-008 | Cannot create cycle | test_ingredient_hierarchy_service.py | Exists |
| VAL-ING-009 | Cannot delete if has products | test_ingredient_service.py:530 | Exists |
| VAL-ING-010 | Cannot delete if in recipes | test_ingredient_service.py:572 | Exists |
| VAL-ING-011 | Cannot delete if has children | test_ingredient_service.py:618 | Exists |

## Gaps Identified

### No Gaps in Automated Tests
All 11 validation rules have corresponding tests. The F035 implementation added 9 new deletion protection tests.

### Manual UI Testing Required

These cannot be automated with pytest and require manual validation:

1. **Cascading Selector Behavior**
   - Product edit form: L0→L1→L2 cascade
   - Recipe creation form: L0→L1→L2 cascade
   - Product tab filter: cascade and reset
   - Inventory tab filter: cascade and reset

2. **Error Message Display**
   - Deletion blocked messages show correct counts
   - Validation errors are user-friendly

3. **Performance (Subjective)**
   - Cascading dropdowns feel responsive (<50ms perceived)
   - Filter updates don't lag

## Test Execution Commands

```bash
# Run all ingredient-related tests
PYTHONPATH=. pytest src/tests -v -k ingredient --tb=short

# Run hierarchy service tests specifically
PYTHONPATH=. pytest src/tests/services/test_ingredient_hierarchy_service.py -v

# Run deletion protection tests
PYTHONPATH=. pytest src/tests/services/test_ingredient_service.py -v -k "delete"

# Generate coverage report
PYTHONPATH=. pytest src/tests -v --cov=src/services --cov-report=html

# Quick smoke test (should complete in <30 seconds)
PYTHONPATH=. pytest src/tests/services/test_ingredient_service.py src/tests/services/test_ingredient_hierarchy_service.py -v --tb=short
```

## Conclusion

Test coverage for ingredient hierarchy is **comprehensive**. All 11 validation rules have automated tests. The primary work for F036 is:

1. **Execute** the existing test suite and verify 100% pass rate
2. **Document** coverage percentages
3. **Manually validate** UI cascading behavior
4. **Fix** any discovered regressions

No new test development required unless bugs are discovered.
