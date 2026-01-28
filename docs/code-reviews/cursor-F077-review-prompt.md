# Cursor Code Review Prompt: F077 Plan State Management

## Feature Overview

**Feature Number:** F077
**Title:** Plan State Management
**User Goal:** Implement a plan lifecycle state machine for events with four states (DRAFT -> LOCKED -> IN_PRODUCTION -> COMPLETED). Allow users to lock plans to prevent accidental recipe/FG changes during production, track production status, and enforce modification rules based on plan state.

## Specification

Read the feature specification first to understand intended behavior:
- `/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/077-plan-state-management/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/077-plan-state-management/plan.md`

## Code Changes

The following files were modified or created for this feature. Review should extend to any related code, dependencies, or callers as needed.

**Service Layer:**
- `src/services/plan_state_service.py` - New service implementing:
  - `lock_plan(event_id, session=None)` - Transition DRAFT -> LOCKED
  - `start_production(event_id, session=None)` - Transition LOCKED -> IN_PRODUCTION
  - `complete_production(event_id, session=None)` - Transition IN_PRODUCTION -> COMPLETED
  - State validation and error handling for invalid transitions

- `src/services/event_service.py` - Modified to add state guards:
  - `set_event_recipes()` - Block when not in DRAFT state
  - `set_event_fg_quantities()` - Block when not in DRAFT state

- `src/services/batch_decision_service.py` - Modified to add state guards:
  - Allow batch decision modifications in DRAFT and LOCKED states
  - Block modifications in IN_PRODUCTION and COMPLETED states

**Exceptions:**
- `src/utils/exceptions.py` - Added `PlanStateError` exception class for state-related violations

**UI Layer:**
- `src/ui/planning_tab.py` - Modified to:
  - Display current plan state prominently
  - Show contextual transition buttons (Lock Plan / Start Production / Complete Production)
  - Enable/disable buttons based on current state
  - Wire buttons to service calls with error handling

**Tests:**
- `src/tests/test_plan_state_service.py` - Unit tests covering:
  - Valid state transitions
  - Invalid transition rejection
  - Modification guard behavior
- `src/tests/integration/test_plan_state_integration.py` - Integration tests for full workflow

## Environment Verification

**CRITICAL: Run these commands OUTSIDE the sandbox.** Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Verify environment is functional
cd /Users/kentgale/Vaults-repos/bake-tracker

# Run plan state tests to confirm environment works
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/pytest src/tests/test_plan_state_service.py -v --tb=short

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
- `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F077-review.md`

**Important:** Write to the `docs/code-reviews/` directory in the main repo, NOT in any worktree.
