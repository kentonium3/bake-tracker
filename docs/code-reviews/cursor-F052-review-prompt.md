# Cursor Review Prompt: Feature 052 - Ingredient & Material Hierarchy Admin

## Feature Overview

**Feature Number:** 052
**Title:** Ingredient & Material Hierarchy Admin
**User Goal:** Enable power users to manage the ingredient and material hierarchies through a dedicated admin interface, including adding new items, renaming existing items, and moving items between parents in the hierarchy.

## Specification

Read the feature specification first to understand requirements:
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/052-ingredient-material-hierarchy-admin/kitty-specs/052-ingredient-material-hierarchy-admin/spec.md`

## Code Changes

The following files were modified or created for this feature:

**New Service Files:**
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/052-ingredient-material-hierarchy-admin/src/services/ingredient_hierarchy_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/052-ingredient-material-hierarchy-admin/src/services/material_hierarchy_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/052-ingredient-material-hierarchy-admin/src/services/hierarchy_admin_service.py`

**New UI Files:**
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/052-ingredient-material-hierarchy-admin/src/ui/hierarchy_admin_window.py`

**Modified UI Files:**
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/052-ingredient-material-hierarchy-admin/src/ui/ingredients_tab.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/052-ingredient-material-hierarchy-admin/src/ui/materials_tab.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/052-ingredient-material-hierarchy-admin/src/ui/main_window.py`

**New Test Files:**
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/052-ingredient-material-hierarchy-admin/src/tests/services/test_ingredient_hierarchy_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/052-ingredient-material-hierarchy-admin/src/tests/services/test_material_hierarchy_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/052-ingredient-material-hierarchy-admin/src/tests/services/test_hierarchy_admin_service.py`

These are the primary changes, but review should extend to any related code, dependencies, or callers as needed.

## Environment Setup

**CRITICAL: Run these commands OUTSIDE the sandbox.** Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Navigate to worktree
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/052-ingredient-material-hierarchy-admin

# Verify imports work (using main repo venv)
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.services.ingredient_hierarchy_service import get_ingredient_tree; print('Imports OK')"

# Run hierarchy service tests
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/pytest src/tests/services/test_ingredient_hierarchy_service.py src/tests/services/test_material_hierarchy_service.py -v --tb=short 2>&1 | tail -20
```

If ANY command fails, STOP immediately and report as a blocker before attempting any fixes.

## Review Approach

1. **Read spec first** - Understand intended behavior BEFORE examining implementation
2. **Form independent expectations** - Decide how the feature SHOULD work based on spec
3. **Compare implementation to expectations** - Note where reality differs from your mental model
4. **Explore beyond modified files** - Follow dependencies, check callers, examine related systems
5. **Look for what wasn't specified** - Edge cases, error conditions, data integrity risks
6. **Run verification commands OUTSIDE sandbox** - If ANY command fails, STOP immediately and report blocker
7. **Consider user experience** - Would this workflow feel natural? Any friction points?
8. **Write report** - Use template format and write to specified location

## Report Template

Use the template at:
- `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/TEMPLATE_cursor_report.md`

## Report Output

Write your review report to:
- `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F052-review.md`

**Important:** Write to the `docs/code-reviews/` directory in the main repo, NOT in the worktree.
