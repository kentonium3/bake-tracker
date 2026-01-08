# Code Review Request: F042 - UI Polish & Layout Fixes

## Feature Overview

**Feature Number**: 042
**Title**: UI Polish & Layout Fixes
**User Goal**: Fix critical UI/UX issues identified during user testing that make the application functional but difficult to use effectively

**Key Issues Addressed**:
1. Headers consume 8-12 lines of vertical space, leaving only 2-3 data rows visible
2. Stats display "0" even when data exists (e.g., 413 ingredients shows as "0 ingredients")
3. Inventory hierarchy displayed as concatenated "L0|L1|L2" string (unreadable)
4. Filter UI inconsistent across tabs
5. Mode names ambiguous ("Shop" and "Produce" unclear)

**Spec File**: `kitty-specs/042-ui-polish-layout/spec.md`

## Code Changes

**Primary Files Modified**:

Dashboard layer:
- `src/ui/dashboards/__init__.py`
- `src/ui/dashboards/base_dashboard.py`
- `src/ui/dashboards/catalog_dashboard.py`
- `src/ui/dashboards/observe_dashboard.py`
- `src/ui/dashboards/plan_dashboard.py`
- `src/ui/dashboards/purchase_dashboard.py` (renamed from shop_dashboard.py)
- `src/ui/dashboards/make_dashboard.py` (renamed from produce_dashboard.py)

Mode layer:
- `src/ui/modes/__init__.py`
- `src/ui/modes/purchase_mode.py` (renamed from shop_mode.py)
- `src/ui/modes/make_mode.py` (renamed from produce_mode.py)
- `src/ui/mode_manager.py`
- `src/ui/main_window.py`

Tab layer:
- `src/ui/ingredients_tab.py`
- `src/ui/inventory_tab.py`
- `src/ui/products_tab.py`

These are the primary changes, but review should extend to any related code, dependencies, or callers as needed.

## Environment Verification

**CRITICAL: Run these commands OUTSIDE the sandbox.**

Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Navigate to project root
cd /Users/kentgale/Vaults-repos/bake-tracker

# Activate virtual environment and run tests
source venv/bin/activate && python -m pytest src/tests -v -q 2>&1 | tail -20
```

Expected: Tests pass (approximately 1744 passed, 14 skipped)

If this fails, STOP and report as a blocker before proceeding with the review.

## Review Approach

1. **Read the spec first** - Understand the intended behavior BEFORE examining implementation
2. **Form independent expectations** - Decide how the feature SHOULD work based on spec
3. **Compare implementation to expectations** - Note where reality differs from your mental model
4. **Explore beyond modified files** - Follow dependencies, check callers, examine related systems
5. **Look for what wasn't specified** - Edge cases, error conditions, data integrity risks
6. **Run verification commands OUTSIDE sandbox** - If ANY command fails, STOP immediately and report blocker
7. **Consider user experience** - Would this workflow feel natural? Any friction points?
8. **Write report** - Use template format and write to specified location

## Report Template

Use the template at: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/TEMPLATE_code_review_report.md`

## Report Output Location

Write your completed review to: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F042-review.md`

**Important**: Write to `docs/code-reviews/` directory in the main repo, NOT in the worktree.
