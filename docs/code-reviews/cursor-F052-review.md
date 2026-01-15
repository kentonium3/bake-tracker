# Code Review Report: F052 - Ingredient & Material Hierarchy Admin

**Reviewer:** Cursor (Independent Review)
**Date:** 2026-01-15
**Feature Spec:** `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/052-ingredient-material-hierarchy-admin/kitty-specs/052-ingredient-material-hierarchy-admin/spec.md`

## Executive Summary
Feature delivers leaf-only listings for Ingredients and Materials with hierarchy context and adds a unified Hierarchy Admin UI for add/rename/reparent operations. Core tests pass after fixing a missing import. Biggest gap: Hierarchy Admin shows usage counts only for leaf items, so selecting L0/L1/category/subcategory provides no usage visibility, missing spec acceptance for aggregated counts. Also, the “optimized” leaf retrieval still performs N+1 ancestor lookups.

## Review Scope

**Primary Files Modified:**
- `.worktrees/052-ingredient-material-hierarchy-admin/src/services/ingredient_hierarchy_service.py`
- `.worktrees/052-ingredient-material-hierarchy-admin/src/services/material_hierarchy_service.py`
- `.worktrees/052-ingredient-material-hierarchy-admin/src/services/hierarchy_admin_service.py`
- `.worktrees/052-ingredient-material-hierarchy-admin/src/ui/hierarchy_admin_window.py`
- `.worktrees/052-ingredient-material-hierarchy-admin/src/ui/ingredients_tab.py`
- `.worktrees/052-ingredient-material-hierarchy-admin/src/ui/materials_tab.py`
- `.worktrees/052-ingredient-material-hierarchy-admin/src/ui/main_window.py`
- Tests under `src/tests/services/test_ingredient_hierarchy_service.py`, `.../test_material_hierarchy_service.py`, `.../test_hierarchy_admin_service.py`

**Additional Code Examined:**
- Models: `src/models/ingredient.py`, `src/models/recipe.py` (RecipeIngredient), `src/models/material*.py`
- Menu wiring in `main_window.py` for admin entry points

## Environment Verification

**Setup Process:**
```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/052-ingredient-material-hierarchy-admin
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.services.ingredient_hierarchy_service import get_ingredient_tree; print('Imports OK')"
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/pytest src/tests/services/test_ingredient_hierarchy_service.py src/tests/services/test_material_hierarchy_service.py -v --tb=short 2>&1 | tail -20
```

**Results:**
- Initial pytest run failed: `ModuleNotFoundError: No module named 'src.models.recipe_ingredient'` in `ingredient_hierarchy_service.get_usage_counts`. Fixed by importing `RecipeIngredient` from `src.models.recipe`.
- Re-run: all specified tests pass (171 total across the two files).
- Import smoke test passes.

---

## Findings

### Major Concerns

**Usage counts missing for non-leaf selections in Hierarchy Admin**
- **Location:** `src/ui/hierarchy_admin_window.py` (`_update_usage_counts`)
- **Problem:** Usage counts display only when an ingredient is level 2 or a material node of type `material`. Selecting L0/L1/category/subcategory shows “select leaf” placeholder, so admins cannot see aggregated product/recipe usage for higher-level nodes. This fails User Story 7 acceptance (usage counts when item is selected) and leaves admins blind to impact before renames/reparents.
- **Recommendation:** When a non-leaf node is selected, aggregate child usage (sum of descendant product/recipe counts for ingredients; product counts for materials) and display it. Consider a “leaf-only” hint but still provide totals to satisfy FR-011/US7.

### Minor Issues

**Leaf retrieval still performs N+1 ancestor lookups**
- **Location:** `ingredient_hierarchy_service.get_all_leaf_ingredients_with_ancestors`
- **Problem:** Function advertises pre-computed ancestor context to avoid N+1, but it queries all leaves then dereferences `parent` and `parent.parent` lazily, issuing additional queries per leaf. On larger catalogs this can regress the performance gains sought by FR-001/FR-002.
- **Recommendation:** Eager-load parent/grandparent (e.g., `joinedload(Ingredient.parent).joinedload(Ingredient.parent.parent)`) or fetch ancestors via a single join to keep the call truly O(1) queries.

### Positive Observations
- Leaf-only listings for Ingredients and Materials include L0/L1 (or Category/Subcategory) columns and respect existing filters; flat view uses pre-resolved context to avoid UI joins.
- Hierarchy Admin window is shared across ingredients/materials with clear add/rename/reparent dialogs and sibling-uniqueness + whitespace validation.
- Services for add/rename/reparent enforce level constraints (e.g., L2 → L1 only, L1 → L0 only) and sibling uniqueness; slug regeneration handles collisions.
- Comprehensive unit tests for hierarchy services cover add/rename/reparent, validation, and usage counts; fixing the import restored a green test run.

## Spec Compliance Analysis
- **Display (FR-001–FR-007):** Ingredients tab flat view shows only L2 with L0/L1 columns and filters; Materials tab shows only materials with Category/Subcategory columns. Tree mode remains available but is not default.
- **Admin UI (FR-008–FR-010):** Menu entries present; Hierarchy Admin shows trees for ingredients/materials with add/rename/reparent dialogs.
- **Usage counts (FR-011 / User Story 7):** Partial. Counts show only for ingredient L2 and material leaf nodes; selecting L1/category/subcategory shows no counts, failing acceptance scenarios requiring visibility at higher levels.
- **Add/Rename/Reparent (FR-012–FR-026):** Add paths enforce sibling uniqueness and correct levels; rename enforces uniqueness; reparent enforces level compatibility and cycle checks (ingredients) plus duplicate-name prevention. Product/recipe FKs remain unchanged on reparent as operations adjust parent IDs only.
- **Edge cases:** Empty/whitespace names rejected; duplicate sibling names blocked; unit type for materials validated. Performance optimization for leaf retrieval remains unfulfilled (N+1).

## Code Quality Assessment
- **Consistency:** Reuses existing service patterns (session_scope, validation helpers). UI follows established CustomTkinter patterns for dialogs and menu wiring.
- **Maintainability:** Shared Hierarchy Admin window reduces duplication across ingredients/materials. Some logic (usage aggregation) is centralized in services but missing for non-leaf nodes; adding aggregation there would keep UI thin.
- **Test Coverage:** Good coverage for hierarchy services and utilities; admin window behavior is untested (UI-level). Missing test for usage counts on non-leaf selections and for eager-loaded leaf retrieval.
- **Dependencies & Integration:** Admin actions refresh main tabs on window close; service changes are localized to hierarchy operations. No data model migrations required.

## Recommendations Priority

**Must Fix Before Merge:**
1. Provide usage counts for non-leaf selections in Hierarchy Admin (aggregate descendants) to satisfy FR-011/US7.

**Should Fix Soon:**
1. Make `get_all_leaf_ingredients_with_ancestors` truly O(1) queries via eager loading or joins to avoid N+1 on leaf listings.

**Consider for Future:**
1. Add UI tests (or service-level aggregation tests) to lock in usage-count expectations for L0/L1/category/subcategory selections.
2. Consider refreshing affected tabs immediately after admin operations (not only on window close) for better UX responsiveness.

## Overall Assessment
Needs revision. Core functionality and tests are solid, but the lack of usage counts for non-leaf selections misses a key admin requirement and should be addressed before release. After adding aggregated counts (and ideally optimizing leaf retrieval), the feature would be ready to ship.
