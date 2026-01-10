# Cursor Code Review Prompt: Feature 046 - Finished Goods, Bundles & Assembly Tracking

## Feature Overview

**Feature Number:** F046
**Title:** Finished Goods, Bundles & Assembly Tracking
**High-Level Goal:** Fix broken cost calculation methods that were left incomplete after F045's cost architecture refactor. F045 removed stored cost fields (`unit_cost`, `total_cost`) from definition models but left placeholder code (`Decimal("0.0000")`) throughout the codebase. F046 implements dynamic cost calculation methods to replace the removed stored fields, following the "Costs on Instances, Not Definitions" principle.

**Key Changes:**
1. Added `calculate_current_cost()` methods to FinishedUnit and FinishedGood models
2. Fixed Composition model methods to use dynamic calculation instead of removed attributes
3. Fixed Package model methods to use dynamic calculation instead of removed attributes
4. Fixed assembly_service to capture actual costs at assembly time instead of zeros

**Specification Files:**
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/046-finished-goods-bundles-assembly/kitty-specs/046-finished-goods-bundles-assembly/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/046-finished-goods-bundles-assembly/kitty-specs/046-finished-goods-bundles-assembly/plan.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/046-finished-goods-bundles-assembly/kitty-specs/046-finished-goods-bundles-assembly/research/research.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/046-finished-goods-bundles-assembly/kitty-specs/046-finished-goods-bundles-assembly/research/data-model.md`

## Code Changes

The following files were modified as part of this feature. These are the primary changes, but review should extend to any related code, dependencies, or callers as needed.

**Models:**
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/046-finished-goods-bundles-assembly/src/models/finished_unit.py` - Added `calculate_current_cost()` method
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/046-finished-goods-bundles-assembly/src/models/finished_good.py` - Added `calculate_current_cost()` method
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/046-finished-goods-bundles-assembly/src/models/composition.py` - Fixed `get_component_cost()` to use `calculate_current_cost()`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/046-finished-goods-bundles-assembly/src/models/package.py` - Fixed `calculate_cost()`, `get_cost_breakdown()`, `get_line_cost()`, and `to_dict()`

**Services:**
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/046-finished-goods-bundles-assembly/src/services/assembly_service.py` - Fixed `_record_assembly_impl()` to capture actual costs

## Environment Setup

**CRITICAL: Run these commands OUTSIDE the sandbox.** Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Navigate to the worktree
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/046-finished-goods-bundles-assembly

# Verify Python environment (use main repo's venv)
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.models import FinishedUnit, FinishedGood, Composition, Package; print('Models import OK')"

# Verify new methods exist
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.models import FinishedUnit, FinishedGood; assert hasattr(FinishedUnit, 'calculate_current_cost'); assert hasattr(FinishedGood, 'calculate_current_cost'); print('New methods exist OK')"

# Verify tests run (quick sanity check)
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -m pytest src/tests/test_assembly_service.py -v --tb=short -q 2>&1 | tail -5
```

If ANY verification command fails, STOP immediately and report the failure as a blocker before attempting any fixes.

## Review Approach

1. **Read spec first** - Understand intended behavior BEFORE examining implementation
2. **Form independent expectations** - Decide how the feature SHOULD work based on spec
3. **Compare implementation to expectations** - Note where reality differs from your mental model
4. **Explore beyond modified files** - Follow dependencies, check callers, examine related systems
5. **Look for what wasn't specified** - Edge cases, error conditions, data integrity risks
6. **Run verification commands OUTSIDE sandbox** - If ANY command fails, STOP immediately and report blocker
7. **Consider user experience** - Would this workflow feel natural? Any friction points?
8. **Write report** - Use the format below and write to the specified location

## Report Output

Write your review report to:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F046-review.md`

**Important:** Write to the `docs/code-reviews/` directory in the main repo, NOT in the worktree.

## Report Format

Use the following structure for your report:

```markdown
# Code Review: F046 - Finished Goods, Bundles & Assembly Tracking

**Reviewer:** Cursor
**Date:** [DATE]
**Commit Range:** main..046-finished-goods-bundles-assembly

## Executive Summary
[1-2 sentence overview of findings]

## Blockers
[Issues that MUST be fixed before merge - empty if none]

## Critical Issues
[Serious bugs, data integrity risks, security concerns]

## Recommendations
[Suggested improvements, non-blocking concerns]

## Questions for Implementer
[Clarifications needed, design decisions to discuss]

## Verification Results
[Output of environment verification commands]

## Files Reviewed
[List of files examined with brief notes]
```
