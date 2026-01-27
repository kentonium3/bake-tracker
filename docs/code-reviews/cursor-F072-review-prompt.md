# Cursor Code Review Prompt: F072 Recipe Decomposition & Aggregation

## Feature Overview

**Feature Number:** F072
**Title:** Recipe Decomposition & Aggregation
**User Goal:** Convert event FG (Finished Good) quantities into aggregated recipe requirements by recursively decomposing bundles that may contain other bundles or atomic items. This is core infrastructure that enables downstream production planning features (batch calculation, shopping lists).

## Specification

Read the feature specification first to understand intended behavior:
- `/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/072-recipe-decomposition-aggregation/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/072-recipe-decomposition-aggregation/plan.md`

## Code Changes

The following files were modified or created for this feature. Review should extend to any related code, dependencies, or callers as needed.

**Service Layer:**
- `src/services/planning_service.py` - New service implementing `calculate_recipe_requirements()` with recursive bundle decomposition, path-based cycle detection, and quantity aggregation

**Tests:**
- `src/tests/test_planning_service.py` - Comprehensive test suite covering:
  - Single atomic FG to recipe mapping (T004)
  - Bundle decomposition with quantity multiplication (T005)
  - Recipe aggregation across multiple FGs (T006)
  - 2-level nested bundles (T007)
  - 3+ level nested bundles (T008)
  - DAG patterns - same FG in multiple branches (T009)
  - Mixed atomic/bundle events (T010)
  - Circular reference detection (T011)
  - Empty event handling (T012)
  - Missing recipe validation (T013)
  - Zero-quantity component handling (T014)

## Environment Verification

**CRITICAL: Run these commands OUTSIDE the sandbox.** Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Verify environment is functional
cd /Users/kentgale/Vaults-repos/bake-tracker

# Run planning service tests to confirm environment works
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/pytest src/tests/test_planning_service.py -v --tb=short

# If the above command fails, STOP and report blocker before proceeding
```

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
- `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/TEMPLATE_code_review_report.md`

## Report Output

Write your review report to:
- `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F072-review.md`

**Important:** Write to the `docs/code-reviews/` directory in the main repo, NOT in any worktree.
