# Cursor Review Prompt: F055 Workflow-Aligned Navigation Cleanup

## Your Role
You are a senior software engineer discovering this feature for the first time. Perform an independent code review using your fresh perspective to find issues that might be missed when the implementer reviews their own work.

## Feature Overview
**Feature Number:** F055
**Title:** Workflow-Aligned Navigation Cleanup
**User Goal:** Reorganize UI navigation to match the user's natural workflow: Observe (check status) → Catalog (manage items) → Plan (events) → Purchase (supplies) → Make (produce) → Deliver (distribute).

## Specification Files
Read these first to understand intended behavior BEFORE examining implementation:
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/055-workflow-aligned-navigation-cleanup/kitty-specs/055-workflow-aligned-navigation-cleanup/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/055-workflow-aligned-navigation-cleanup/kitty-specs/055-workflow-aligned-navigation-cleanup/plan.md`

## Files Modified
These are the primary changes, but your review should extend to any related code, dependencies, or callers as needed:

**Mode Navigation:**
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/055-workflow-aligned-navigation-cleanup/src/ui/mode_manager.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/055-workflow-aligned-navigation-cleanup/src/ui/main_window.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/055-workflow-aligned-navigation-cleanup/src/ui/modes/deliver_mode.py` (NEW)

**Catalog Restructure:**
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/055-workflow-aligned-navigation-cleanup/src/ui/modes/catalog_mode.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/055-workflow-aligned-navigation-cleanup/src/ui/tabs/ingredients_group_tab.py` (NEW)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/055-workflow-aligned-navigation-cleanup/src/ui/tabs/recipes_group_tab.py` (NEW)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/055-workflow-aligned-navigation-cleanup/src/ui/tabs/packaging_group_tab.py` (NEW)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/055-workflow-aligned-navigation-cleanup/src/ui/tabs/__init__.py`

**Purchase Mode:**
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/055-workflow-aligned-navigation-cleanup/src/ui/modes/purchase_mode.py`

**Tree View Removal:**
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/055-workflow-aligned-navigation-cleanup/src/ui/ingredients_tab.py`

## Environment Verification

**CRITICAL: Run these commands OUTSIDE the sandbox.** Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Change to worktree directory
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/055-workflow-aligned-navigation-cleanup

# Verify Python imports work (uses main repo venv)
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.ui.mode_manager import ModeManager; from src.ui.modes.deliver_mode import DeliverMode; print('Imports OK')"

# Verify tests run (a few seconds max)
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/pytest src/tests/services/test_ingredient_service.py -v --ignore=src/tests/migration -x 2>&1 | head -20
```

If ANY command fails, STOP immediately and report as a blocker before attempting any fixes.

## Review Approach

1. **Read spec first** - Understand intended behavior BEFORE examining implementation
2. **Form independent expectations** - Decide how the feature SHOULD work based on spec
3. **Compare implementation to expectations** - Note where reality differs from your mental model
4. **Explore beyond modified files** - Follow dependencies, check callers, examine related systems
5. **Look for what wasn't specified** - Edge cases, error conditions, data integrity risks
6. **Run verification commands OUTSIDE sandbox** - If ANY command fails, STOP and report blocker
7. **Consider user experience** - Would this workflow feel natural? Any friction points?
8. **Write report** - Use template format and write to specified location

## Report Template
Use the template at: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/TEMPLATE_cursor_report.md`

## Report Output
Write your review report to: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F055-review.md`

**Important:** Write to the docs/code-reviews/ directory in the MAIN repo, NOT in the worktree.
