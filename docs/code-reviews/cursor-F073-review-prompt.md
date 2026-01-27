# Cursor Code Review Prompt: F073 Batch Calculation & User Decisions

## Feature Overview

**Feature Number:** F073
**Title:** Batch Calculation & User Decisions
**User Goal:** Replace error-prone manual batch calculations with automatic calculation and informed user decisions. The system calculates floor/ceil batch options for each recipe, presents trade-offs (shortfall vs excess), and persists user decisions for downstream features.

## Specification

Read the feature specification first to understand intended behavior:
- `/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/073-batch-calculation-user-decisions/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/073-batch-calculation-user-decisions/plan.md`

## Code Changes

The following files were modified or created for this feature. Review should extend to any related code, dependencies, or callers as needed.

**Model Layer:**
- `src/models/batch_decision.py` - BatchDecision model for persisting user batch choices (event_id, recipe_id, finished_unit_id, batches)
- `src/models/__init__.py` - Export of BatchDecision model

**Service Layer:**
- `src/services/planning_service.py` - Updated to support FU-level decomposition (calculate_fu_requirements)
- `src/services/batch_decision_service.py` - CRUD service for batch decisions with validation

**UI Layer:**
- `src/ui/widgets/batch_options_frame.py` - New widget displaying floor/ceil options with shortfall warnings
- `src/ui/planning_tab.py` - Integration of batch options into planning workflow

**Tests:**
- `src/tests/test_batch_calculation.py` - Unit tests for batch calculation logic
- `src/tests/test_batch_decision_service.py` - Tests for CRUD operations and validation

## Environment Verification

**CRITICAL: Run these commands OUTSIDE the sandbox.** Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Verify environment is functional
cd /Users/kentgale/Vaults-repos/bake-tracker

# Run batch calculation tests to confirm environment works
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/pytest src/tests/test_batch_calculation.py src/tests/test_batch_decision_service.py -v --tb=short

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
- `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F073-review.md`

**Important:** Write to the `docs/code-reviews/` directory in the main repo, NOT in any worktree.
