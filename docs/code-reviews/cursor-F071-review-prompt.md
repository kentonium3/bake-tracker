# Cursor Code Review Prompt: F071 - Finished Goods Quantity Specification

## Your Role
You are a senior software engineer performing an independent code review. This is your first time seeing this feature. Read the spec first to understand what was intended, form your own expectations, then examine the implementation to see if reality matches.

## Feature Overview
**Feature**: F071 - Finished Goods Quantity Specification
**User Goal**: When planning an event, specify how many of each finished good to produce. Quantities should persist, load when reopening an event, and support modification. Invalid entries (zero, negative, non-integer) should show validation errors.

## Specification
Read the full spec before examining code:
- `/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/071-finished-goods-quantity-specification/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/071-finished-goods-quantity-specification/plan.md`

## Code Changes
These are the primary files modified for this feature. Your review should extend to any related code, dependencies, or callers as needed.

**Service Layer:**
- `src/services/event_service.py` - Added `get_event_fg_quantities()` and `set_event_fg_quantities()` methods

**UI Layer:**
- `src/ui/components/fg_selection_frame.py` - Added quantity input fields, live validation, `set_selected_with_quantities()`, updated `get_selected()` return type
- `src/ui/planning_tab.py` - Integration of quantity load/save workflow, validation error handling, cancel revert

**Tests:**
- `src/tests/test_event_fg_quantities.py` - NEW: Tests for service layer quantity methods
- `src/tests/test_fg_selection_frame.py` - Updated with quantity input and validation tests
- `src/tests/test_planning_tab_fg.py` - Updated for quantity-based API

## Environment Verification

**CRITICAL: Run these commands OUTSIDE the sandbox.** Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Navigate to project
cd /Users/kentgale/Vaults-repos/bake-tracker

# Verify venv and service imports work
./venv/bin/python -c "from src.services.event_service import get_event_fg_quantities, set_event_fg_quantities; print('Service imports OK')"

# Verify UI imports work
./venv/bin/python -c "from src.ui.components.fg_selection_frame import FGSelectionFrame; print('UI imports OK')"

# Run F071-related tests
./venv/bin/pytest src/tests/test_event_fg_quantities.py src/tests/test_fg_selection_frame.py src/tests/test_planning_tab_fg.py -v --tb=short
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

- **API Change**: `FGSelectionFrame.get_selected()` now returns `List[Tuple[int, int]]` (fg_id, quantity) instead of `List[int]`
- **Replace Pattern**: `set_event_fg_quantities()` uses DELETE + INSERT (not UPDATE) to sync database state
- **Validation**: Live validation with colored feedback labels (orange for errors)
- **Session Management**: This project has strict rules about SQLAlchemy session passing - see CLAUDE.md
- **Layered Architecture**: UI -> Services -> Models (UI should not contain business logic)

## Report Template
Use the template at:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/TEMPLATE_cursor_report.md`

## Report Output
Write your review report to:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F071-review.md`

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
