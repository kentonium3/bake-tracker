# Cursor Code Review Prompt: F070 - Finished Goods Filtering for Event Planning

## Your Role
You are a senior software engineer performing an independent code review. This is your first time seeing this feature. Read the spec first to understand what was intended, form your own expectations, then examine the implementation to see if reality matches.

## Feature Overview
**Feature**: F070 - Finished Goods Filtering for Event Planning
**User Goal**: When planning an event, only show Finished Goods that can actually be produced based on the selected recipes. If recipes are deselected, automatically remove any FG selections that are no longer valid and notify the user.

## Specification
Read the full spec before examining code:
- `/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/070-finished-goods-filtering/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/070-finished-goods-filtering/plan.md`

## Code Changes
These are the primary files modified for this feature. Your review should extend to any related code, dependencies, or callers as needed.

**Service Layer:**
- `src/services/event_service.py` - Added bundle decomposition, availability checking, cascade removal, and FG selection functions

**UI Layer:**
- `src/ui/components/fg_selection_frame.py` - NEW: FGSelectionFrame component (checkbox list with save/cancel)
- `src/ui/components/__init__.py` - Export FGSelectionFrame
- `src/ui/planning_tab.py` - Integration of FGSelectionFrame, recipe-FG wiring, notifications

**Tests:**
- `src/tests/test_fg_availability.py` - NEW: Tests for bundle decomposition, availability, cascade removal
- `src/tests/test_fg_selection_frame.py` - NEW: Tests for FGSelectionFrame component
- `src/tests/test_planning_tab_fg.py` - NEW: Tests for Planning Tab FG integration
- `src/tests/test_recipe_selection.py` - Updated to handle `set_event_recipes()` return type change

## Environment Verification

**CRITICAL: Run these commands OUTSIDE the sandbox.** Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Navigate to project
cd /Users/kentgale/Vaults-repos/bake-tracker

# Verify venv and imports work
./venv/bin/python -c "from src.services.event_service import get_required_recipes, check_fg_availability, get_available_finished_goods, set_event_finished_goods; print('Service imports OK')"

# Verify UI imports work
./venv/bin/python -c "from src.ui.components.fg_selection_frame import FGSelectionFrame; print('UI imports OK')"

# Run F070 tests
./venv/bin/pytest src/tests/test_fg_availability.py src/tests/test_fg_selection_frame.py src/tests/test_planning_tab_fg.py -v --tb=short
```

If ANY command fails, STOP immediately and report as a blocker before attempting any fixes.

## Review Approach

1. **Read spec first** - Understand the intended behavior BEFORE examining implementation
2. **Form independent expectations** - Decide how the feature SHOULD work based on the spec
3. **Compare implementation to expectations** - Note where reality differs from your mental model
4. **Explore beyond modified files** - Follow dependencies, check callers, examine related systems
5. **Look for what wasn't specified** - Edge cases, error conditions, data integrity risks
6. **Consider user experience** - Would this workflow feel natural? Any friction points?
7. **Run verification commands OUTSIDE sandbox** - If ANY command fails, STOP and report blocker

## Key Technical Details to Be Aware Of

- **Bundle Decomposition**: FinishedGood → Composition → FinishedUnit → recipe_id (recursive traversal)
- **Breaking Change**: `set_event_recipes()` now returns `Tuple[int, List[RemovedFGInfo]]` instead of `int`
- **Session Management**: This project has strict rules about SQLAlchemy session passing - see CLAUDE.md
- **Layered Architecture**: UI → Services → Models (UI should not contain business logic)

## Report Template
Use the template at:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/TEMPLATE_cursor_report.md`

## Report Output
Write your review report to:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F070-review.md`

**Important**: Write to the `docs/code-reviews/` directory, NOT in any worktree.

## What to Evaluate (Use Your Own Judgment)

Don't follow a prescriptive checklist. As a senior engineer, determine independently:
- What edge cases might cause problems?
- Are there data integrity risks?
- Does the code follow the project's established patterns?
- What could go wrong in production?
- Is the user experience intuitive?
- Are there any architectural concerns?

Your fresh perspective is valuable precisely because you're approaching this without preconceptions about what issues to find.
