# Cursor Code Review Prompt: F074 Ingredient Aggregation for Batch Decisions

## Feature Overview

**Feature Number:** F074
**Title:** Ingredient Aggregation for Batch Decisions
**User Goal:** Convert batch decisions (from F073) into total ingredient quantities needed by scaling recipe ingredients by batch count and aggregating the same ingredient across multiple recipes. This is core infrastructure for the shopping list feature (F075).

## Specification

Read the feature specification first to understand intended behavior:
- `/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/074-ingredient-aggregation/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/074-ingredient-aggregation/plan.md`

## Code Changes

The following files were modified or created for this feature. Review should extend to any related code, dependencies, or callers as needed.

**Service Layer:**
- `src/services/ingredient_aggregation_service.py` - New service implementing:
  - `IngredientTotal` dataclass for aggregated results
  - `aggregate_ingredients_for_event(event_id, session=None)` - Main public function
  - Single recipe scaling (batches × ingredient quantity)
  - Cross-recipe aggregation by (ingredient_id, unit) key
  - 3 decimal place precision maintenance

**Tests:**
- `src/tests/test_ingredient_aggregation_service.py` - Comprehensive test suite covering:
  - Single recipe aggregation
  - Multiple recipes with shared ingredients
  - Different units kept separate (no conversion)
  - Empty event handling
  - Precision verification

## Environment Verification

**CRITICAL: Run these commands OUTSIDE the sandbox.** Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Verify environment is functional
cd /Users/kentgale/Vaults-repos/bake-tracker

# Run ingredient aggregation tests to confirm environment works
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/pytest src/tests/test_ingredient_aggregation_service.py -v --tb=short

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
- `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F074-review.md`

**Important:** Write to the `docs/code-reviews/` directory in the main repo, NOT in any worktree.
