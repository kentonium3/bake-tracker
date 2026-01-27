# Cursor Code Review Prompt: F069 - Recipe Selection for Event Planning

## Your Role

You are a senior software engineer performing an independent code review. You are discovering this feature for the first time. Your fresh perspective is valuable for finding issues that the implementer may have missed.

## Feature Overview

**Feature Number**: F069
**Title**: Recipe Selection for Event Planning
**User Goal**: Enable bakers planning an event to select which recipes they want to make, with selections persisting to the database and driving downstream planning features (finished goods, quantities, batch calculations).

## Specification

Read the full requirements here before examining any code:
- **Spec file**: `/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/069-recipe-selection-for-event-planning/spec.md`
- **Func spec**: `/Users/kentgale/Vaults-repos/bake-tracker/docs/func-spec/F069_recipe_selection_ui.md`
- **Plan file**: `/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/069-recipe-selection-for-event-planning/plan.md`

## Files Modified

These are the primary changes. Your review should extend to any related code, dependencies, or callers as needed.

**Services**:
- `src/services/event_service.py` (modified - added `get_event_recipe_ids()` and `set_event_recipes()`)

**UI Components**:
- `src/ui/components/__init__.py` (new - package exports)
- `src/ui/components/recipe_selection_frame.py` (new - RecipeSelectionFrame widget)
- `src/ui/planning_tab.py` (modified - integrated RecipeSelectionFrame)

**Tests**:
- `src/tests/test_recipe_selection.py` (new - service layer tests, 14 tests)
- `src/tests/test_recipe_selection_frame.py` (new - UI component tests, 13 tests)

## Environment Verification

**CRITICAL: Run these commands OUTSIDE the sandbox.** Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Navigate to project root
cd /Users/kentgale/Vaults-repos/bake-tracker

# Verify imports work (tests that models and services load)
./run-tests.sh -v -k "test_returns_empty_list_when_no_selections" 2>&1 | tail -20

# Run all recipe selection tests (27 tests total)
./run-tests.sh src/tests/test_recipe_selection.py src/tests/test_recipe_selection_frame.py -v 2>&1 | tail -40
```

If ANY verification command fails, STOP immediately and report as a blocker before attempting any fixes.

## Review Approach

1. **Read spec first** - Understand intended behavior BEFORE examining implementation
2. **Form independent expectations** - Decide how the feature SHOULD work based on spec
3. **Compare implementation to expectations** - Note where reality differs from your mental model
4. **Explore beyond modified files** - Follow dependencies, check callers, examine related systems
5. **Look for what wasn't specified** - Edge cases, error conditions, data integrity risks
6. **Run verification commands OUTSIDE sandbox** - If ANY command fails, STOP and report blocker
7. **Consider user experience** - Would this workflow feel natural? Any friction points?
8. **Write report** - Use the format below and write to specified location

## Report Output

Write your review report to:
**`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F069-review.md`**

Important: Write to the `docs/code-reviews/` directory in the main repo, NOT in any worktree.

## Report Format

Use this structure for your report:

```markdown
# Code Review Report: F069 - Recipe Selection for Event Planning

**Reviewer**: Cursor
**Date**: [date]
**Verdict**: [APPROVE / APPROVE WITH SUGGESTIONS / REQUEST CHANGES / BLOCKER]

## Executive Summary

[2-3 sentences summarizing your overall assessment]

## Verification Results

[Results of running the verification commands - did they pass?]

## Findings

### Critical Issues (must fix)

[List any issues that would block approval]

### Suggestions (should consider)

[List improvements that would strengthen the implementation]

### Observations (informational)

[Any other notes, questions, or observations]

## Areas Reviewed

[List the areas you examined and your confidence level in each]

## Recommendation

[Your final recommendation with rationale]
```

## Begin Review

Start by reading the spec file, then form your own expectations before examining the implementation.
