# Cursor Code Review Prompt: Feature 056 - Unified Yield Management

## Feature Overview

**Feature Number:** 056
**Title:** Unified Yield Management
**User Goal:** Eliminate redundant yield tracking by deprecating Recipe-level yield fields (`yield_quantity`, `yield_unit`, `yield_description`) in favor of FinishedUnit as the single source of truth for yield data.

## Specification

Read the full specification before examining implementation:
- **Spec:** `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/056-unified-yield-management/kitty-specs/056-unified-yield-management/spec.md`
- **Data Model:** `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/056-unified-yield-management/kitty-specs/056-unified-yield-management/data-model.md`
- **Plan:** `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/056-unified-yield-management/kitty-specs/056-unified-yield-management/plan.md`

## Code Changes

**Modified Files:**
- `src/models/finished_unit.py` - Validation methods added
- `src/models/recipe.py` - Yield fields made nullable
- `src/services/catalog_import_service.py` - FinishedUnit import with legacy handling
- `src/services/coordinated_export_service.py` - FinishedUnit export functionality
- `src/services/recipe_service.py` - Recipe validation updates
- `src/ui/forms/recipe_form.py` - YieldTypeRow updated with item_unit, legacy fields removed
- `src/tests/services/test_coordinated_export.py` - Export tests added
- `src/tests/services/test_recipe_service.py` - Recipe validation tests
- `src/tests/test_catalog_import_service.py` - Import tests added
- `src/tests/integration/test_import_export_roundtrip.py` - Updated assertions

**New Files:**
- `scripts/transform_yield_data.py` - Transforms legacy yield data to FinishedUnit structure
- `test_data/sample_data_min_transformed.json` - Transformed test data
- `test_data/sample_data_all_transformed.json` - Transformed test data

These are the primary changes, but review should extend to any related code, dependencies, or callers as needed.

## Environment Setup

**CRITICAL: Run these commands OUTSIDE the sandbox.** Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Navigate to worktree
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/056-unified-yield-management

# Verify imports work (use main repo's venv)
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.models.finished_unit import FinishedUnit, YieldMode; print('Imports OK')"

# Verify tests run
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -m pytest src/tests/services/test_coordinated_export.py -v --tb=short -q 2>&1 | tail -5
```

If ANY command fails, STOP immediately and report the failure as a blocker before attempting any fixes.

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

Write your review report to: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F056-review.md`

**Important:** Write to the `docs/code-reviews/` directory in the main repo, NOT in the worktree.
