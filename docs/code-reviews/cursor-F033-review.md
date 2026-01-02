# Cursor Code Review: Feature 033 - Phase 1 Ingredient Hierarchy Fixes

**Date:** 2026-01-02
**Reviewer:** Cursor (AI Code Review)
**Feature:** 033-phase-1-ingredient
**Branch:** `main` (Feature 033 changes present; `.worktrees/033-phase-1-ingredient` not present in this workspace)

## Summary

Feature 033’s deliverables (**WP01–WP04**) are present and behave as intended:
- **WP01** adds UI-friendly hierarchy helpers (`get_child_count`, `get_product_count`, `can_change_parent`) with the correct session-management pattern.
- **WP02** removes the manual level selector and computes level from parent selection; adds warning label behavior for parent changes.
- **WP03** adds a single **Hierarchy** path column in the flat list view.
- **WP04** deprecates the legacy ingredient dialog with docstrings + a runtime `DeprecationWarning`.

The full test suite is green. The main remaining concern is potential query amplification in `_build_hierarchy_path_cache()` due to per-ingredient `get_ancestors()` calls.

## Verification Results

### Module Import Validation
- `ingredient_hierarchy_service.py`: **PASS** (imports succeed)
- `ingredients_tab.py`: **PASS** (imports succeed)
- `ingredient_form.py`: **PASS** (imports succeed)

### Test Results
- **Full test suite**: **PASS** (`1443 passed, 13 skipped, 38 warnings`)
  Evidence: `PYTHONPATH=. venv/bin/pytest src/tests -q`
- **WP01 specific tests**: **PASS** (`16 passed, 58 deselected`)
  Evidence: `pytest src/tests/services/test_ingredient_hierarchy_service.py -k "TestGetChildCount or TestGetProductCount or TestCanChangeParent"`

### Code Pattern Validation
- **Session management pattern**: **correct** (`src/services/ingredient_hierarchy_service.py` uses inner `_impl(session)` + `session_scope()` fallback)
- **Level computation pattern**: **correct** (`_compute_and_display_level()` computes 0/1/2 based on dropdown selections)
- **Hierarchy path cache pattern**: **functionally correct; potential perf concerns** (per-ingredient ancestor lookup)
- **Deprecation warning pattern**: **correct** (`DeprecationWarning`, `stacklevel=2`, before `super().__init__()`)

## Findings

### Critical Issues
- None found for F033 scope.

### Warnings
- **Potential N+1 query amplification in hierarchy-path cache (WP03)**
  - `_build_hierarchy_path_cache()` calls `ingredient_hierarchy_service.get_ancestors(ing_id)` per ingredient.
  - Recommendation: prefetch parent links once (service-side) and compute paths in-memory, or add a service method that returns `hierarchy_path` for all ingredients in one shot.

- **`can_change_parent()` “new_level” may be misleading when `new_parent_id` does not exist**
  - If parent lookup fails, `new_level` remains its default (0) even if the operation is not allowed.
  - Recommendation: set `new_level = None` when parent cannot be resolved, or set `allowed=False` / `reason` immediately for missing parent.

### Observations
- **WP02 is a strong UX improvement**: it prevents inconsistent states by construction and clearly communicates the computed level.
- **WP04 deprecation is well-executed**: both documentation and runtime warning are present without changing legacy behavior.

## Files Reviewed

| File | Status | Notes |
|------|--------|-------|
| `src/services/ingredient_hierarchy_service.py` | PASS | WP01 functions present; correct session pattern; `new_level` edge case noted |
| `src/tests/services/test_ingredient_hierarchy_service.py` | PASS | 16 WP01 tests + `test_db_with_products` fixture; subset passes |
| `src/ui/ingredients_tab.py` | PASS with warnings | WP02/WP03 present; hierarchy cache may amplify queries |
| `src/ui/forms/ingredient_form.py` | PASS | WP04 deprecation docstrings + runtime warning in `__init__` |

## Architecture Assessment

### Session Management
WP01 helpers follow the established pattern: inner `_impl(session)` and optional `session` parameter with `session_scope()` fallback, which keeps functions usable from both UI and tests.

### Service Layer
`can_change_parent()` is a solid UI-focused wrapper around `validate_hierarchy()` that preserves non-blocking warnings. Consider tightening `new_level` behavior when the parent doesn’t exist.

### UI Layer
WP02 removes user-managed hierarchy level selection and computes level from parent selection, reducing invalid state. WP03’s path column is useful, but caching currently still relies on per-row ancestor lookups.

## Functional Requirements Verification

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FR-001: get_child_count returns correct count | PASS | `src/services/ingredient_hierarchy_service.py` defines `get_child_count()`; unit tests `TestGetChildCount` assert counts |
| FR-002: get_product_count returns correct count | PASS | `get_product_count()` queries `Product`; unit tests `TestGetProductCount` assert counts |
| FR-003: can_change_parent returns structured dict | PASS | Return dict includes `allowed/reason/warnings/child_count/product_count/new_level` |
| FR-004: can_change_parent blocks circular refs | PASS | Catches `CircularReferenceError`; tested in `test_circular_reference_blocked` |
| FR-005: can_change_parent blocks depth exceeded | PASS | Catches `MaxDepthExceededError`; tested in `test_depth_exceeded_blocked` |
| FR-006: can_change_parent returns warnings | PASS | Adds warnings for product/child counts; tested in `test_product_warning_included` + `test_child_warning_included` |
| FR-007: Level dropdown removed from form | PASS | Prompt grep for `ingredient_level_var|ingredient_level_dropdown` returns nothing |
| FR-008: Level computed from parent selection | PASS | `_compute_and_display_level()` uses L0/L1 selection state to compute 0/1/2 |
| FR-009: Warning label shows for existing ingredients | PASS | `_check_parent_change_warnings()` early-returns for new ingredients |
| FR-010: L0 dropdown has "(None - create root)" | PASS | `_compute_and_display_level()` treats that as L0 |
| FR-011: L1 dropdown has "(None - create L1)" | PASS | `_on_l0_change()` populates `"(None - create L1)"` |
| FR-012: Hierarchy path column shows full path | PASS | Flat grid columns include `hierarchy_path`; cache builds `L0 > L1 > L2` |
| FR-013: L0 shows just name | PASS | Cache: if `hierarchy_level == 0`, path is `ing_name` |
| FR-014: L1 shows "Parent > Name" | PASS | Cache: if `hierarchy_level == 1`, path uses `l0_name > ing_name` |
| FR-015: L2 shows "Grandparent > Parent > Name" | PASS | Cache: if `hierarchy_level == 2`, path uses `l0_name > l1_name > ing_name` |
| FR-016: Legacy form has deprecation docstring | PASS | Module + class docstrings include `.. deprecated::` |
| FR-017: Legacy form has runtime warning | PASS | `warnings.warn(..., DeprecationWarning, stacklevel=2)` in `__init__` |
| FR-018: All 16 new tests pass | PASS | `16 passed, 58 deselected` for WP01 subset |
| FR-019: No regressions in existing tests | PASS | Full suite `1443 passed, 13 skipped` |

## Work Package Verification

| Work Package | Status | Notes |
|--------------|--------|-------|
| WP01: Service Layer Functions | PASS | Functions exist, signatures correct, tests cover edge cases |
| WP02: UI Form Fix (MVP) | PASS | Level computed from parent selection; warnings shown for edits |
| WP03: Hierarchy Path Display | PASS with warnings | Works; consider performance improvements |
| WP04: Legacy Form Deprecation | PASS | Docstrings + DeprecationWarning implemented as requested |

## User Story Verification

Reference: `kitty-specs/033-phase-1-ingredient/spec.md`

| User Story | Status | Notes |
|------------|--------|-------|
| US-P1: Correct Parent Selection UX | PASS | Parent selection drives computed level; no manual level selection |
| US-P2: Validation Before Parent Change | PASS | `can_change_parent()` used for warning/blocked feedback |
| US-P3: Hierarchy Path Display | PASS | Flat list shows full hierarchy path in a single column |

### Acceptance Scenarios

| Scenario | Status | Notes |
|----------|--------|-------|
| P1-S1: No parent = L0 (Root) | PASS | L0 selection “None” maps to level 0 |
| P1-S2: L0 parent = L1 (Subcategory) | PASS | Selecting L0 with no valid L1 maps to level 1 + parent=L0 |
| P1-S3: L1 parent = L2 (Leaf) | PASS | Selecting a valid L1 maps to level 2 + parent=L1 |
| P1-S4: Only L0/L1 in parent dropdown | PASS | L1 list is derived from children of chosen L0 (and only L1) |
| P2-S1: Warning for linked products | PASS | `can_change_parent()` includes product warnings; UI shows orange text |
| P2-S2: Warning for child ingredients | PASS | `can_change_parent()` includes child warnings; UI shows orange text |
| P2-S3: Blocked circular reference | PASS | UI shows red reason when `allowed=False` |
| P2-S4: Blocked depth exceeded | PASS | UI shows red reason when `allowed=False` |
| P3-S1: L2 shows full path | PASS | Cache builds `L0 > L1 > L2` |
| P3-S2: L0 shows just name | PASS | Cache uses name only for level 0 |

## Code Quality Assessment

### Removed Code Verification
| Item | Removed | Notes |
|------|---------|-------|
| ingredient_level_var | Yes | grep found no occurrences |
| ingredient_level_dropdown | Yes | grep found no occurrences |
| _on_ingredient_level_change() | Yes | grep found no occurrences |
| _update_hierarchy_visibility() | Yes | grep found no occurrences |
| _hierarchy_cache (old tuple version) | Yes | replaced by `_hierarchy_path_cache` |
| l0_name/l1_name sort keys | Yes | flat grid no longer has `l0`/`l1` columns |

### Added Code Verification
| Item | Added | Notes |
|------|-------|-------|
| get_child_count() | Yes | `src/services/ingredient_hierarchy_service.py` |
| get_product_count() | Yes | `src/services/ingredient_hierarchy_service.py` |
| can_change_parent() | Yes | `src/services/ingredient_hierarchy_service.py` |
| level_display_var | Yes | `src/ui/ingredients_tab.py` |
| warning_label | Yes | `src/ui/ingredients_tab.py` |
| _compute_and_display_level() | Yes | `src/ui/ingredients_tab.py` |
| _check_parent_change_warnings() | Yes | `src/ui/ingredients_tab.py` |
| _get_selected_parent_id() | Yes | `src/ui/ingredients_tab.py` |
| _on_l1_change() | Yes | `src/ui/ingredients_tab.py` |
| _build_hierarchy_path_cache() | Yes | `src/ui/ingredients_tab.py` |
| hierarchy_path column | Yes | flat Treeview columns include `hierarchy_path` |

## Conclusion

**APPROVED WITH CHANGES (non-blocking)**
WP01–WP04 requirements are met and tests are green. Recommended follow-ups are performance-oriented (reduce ancestor lookups per refresh) and a small robustness tweak to `can_change_parent()`’s `new_level` when the proposed parent is invalid.


