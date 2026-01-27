# Cursor Code Review Prompt: F075 Inventory Gap Analysis

## Feature Overview

**Feature Number:** F075
**Title:** Inventory Gap Analysis
**User Goal:** Compare aggregated ingredient needs (from F074) against current inventory to generate a shopping list. The system calculates gaps (needed - on_hand) for each ingredient and categorizes results into "purchase required" vs "sufficient" lists.

## Specification

Read the feature specification first to understand intended behavior:
- `/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/075-inventory-gap-analysis/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/075-inventory-gap-analysis/plan.md`

## Code Changes

The following files were modified or created for this feature. Review should extend to any related code, dependencies, or callers as needed.

**Service Layer:**
- `src/services/inventory_gap_service.py` - New service implementing:
  - `GapItem` dataclass (ingredient_id, ingredient_name, unit, quantity_needed, quantity_on_hand, gap)
  - `GapAnalysisResult` dataclass (purchase_items, sufficient_items lists)
  - `analyze_inventory_gaps(event_id, session=None)` - Main public function
  - Gap calculation: `max(0, needed - on_hand)`
  - Missing inventory treated as zero (graceful handling)
  - Exact unit string matching (no conversion)
  - Integration with F074's `aggregate_ingredients_for_event()`
  - Integration with `get_total_quantity(slug)` from inventory_item_service

**Tests:**
- `src/tests/test_inventory_gap_service.py` - Unit tests covering:
  - Gap calculation with shortfall (6 needed, 2 on hand = 4 gap)
  - Gap calculation with sufficient inventory (gap = 0)
  - Missing inventory treated as zero
  - All items categorized into exactly one list
  - Empty event returns empty result
  - Unit mismatch treated as zero inventory

## Environment Verification

**CRITICAL: Run these commands OUTSIDE the sandbox.** Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Verify environment is functional
cd /Users/kentgale/Vaults-repos/bake-tracker

# Run inventory gap analysis tests to confirm environment works
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/pytest src/tests/test_inventory_gap_service.py -v --tb=short

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
- `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F075-review.md`

**Important:** Write to the `docs/code-reviews/` directory in the main repo, NOT in any worktree.
