# Cursor Code Review Prompt - Feature 044: Finished Units Yield Type Management

## Your Role

You are a senior software engineer performing an independent code review. Approach this as if discovering the feature for the first time. Read the spec first, form your own expectations, then evaluate the implementation.

## Feature Context

**Feature:** 044 - Finished Units Yield Type Management
**User Goal:** Define what finished products each recipe produces (yield types) directly within the Recipe Edit form, with a read-only catalog view in the Finished Units tab for browsing all yield types across recipes.
**Spec File:** `kitty-specs/044-finished-units-yield-type-management/spec.md`

## Files to Review

**Model Layer:**
```
src/models/finished_unit.py (FK constraint changed to CASCADE)
```

**Service Layer:**
```
src/services/finished_unit_service.py (name uniqueness validation added)
```

**UI Components:**
```
src/ui/forms/recipe_form.py (YieldTypeRow class, Yield Types section added)
src/ui/recipes_tab.py (_save_yield_types method added)
src/ui/finished_units_tab.py (converted to read-only catalog)
```

These are the primary changes, but review should extend to any related code, dependencies, or callers as needed.

## Spec Files (Read First)

```
kitty-specs/044-finished-units-yield-type-management/spec.md
kitty-specs/044-finished-units-yield-type-management/plan.md
kitty-specs/044-finished-units-yield-type-management/data-model.md
kitty-specs/044-finished-units-yield-type-management/research.md
```

## Verification Commands

**CRITICAL: Run these commands OUTSIDE the sandbox.**

Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

Run from worktree: `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/044-finished-units-yield-type-management`

```bash
source /Users/kentgale/Vaults-repos/bake-tracker/venv/bin/activate

# Verify imports
PYTHONPATH=. python3 -c "
from src.models.finished_unit import FinishedUnit
from src.services.finished_unit_service import FinishedUnitService
from src.ui.forms.recipe_form import RecipeFormDialog, YieldTypeRow
from src.ui.recipes_tab import RecipesTab
from src.ui.finished_units_tab import FinishedUnitsTab
print('All imports successful')
"

# Verify model change (CASCADE)
PYTHONPATH=. python3 -c "
from src.models.finished_unit import FinishedUnit
from sqlalchemy import inspect
# Should show CASCADE
print('Model loaded successfully')
"

# Run relevant tests
PYTHONPATH=. python3 -m pytest src/tests -k "finished" -v --tb=short

# Run full test suite (should pass ~1774 tests)
PYTHONPATH=. python3 -m pytest src/tests -v --tb=short 2>&1 | tail -30
```

**If ANY verification fails, STOP and report as blocking issue.**

## Review Instructions

1. **Read the spec** (`spec.md`) to understand intended behavior
2. **Form expectations** about how this SHOULD work before reading code
3. **Run verification commands** - stop if failures
4. **Review implementation** comparing against your expectations
5. **Write report** to `docs/code-reviews/cursor-F044-review.md`

## Key Review Areas

- **Cascade Delete**: When recipe is deleted, its yield types should auto-delete (ondelete="CASCADE")
- **Name Uniqueness**: Yield type names must be unique within the same recipe (case-insensitive)
- **Inline Row Entry**: YieldTypeRow widget pattern following RecipeIngredientRow
- **Read-Only Tab**: Finished Units tab should have no Add/Edit/Delete buttons
- **Double-Click Navigation**: Double-click in Finished Units tab should open Recipe Edit
- **Persistence**: Yield types should persist when recipe is saved (create/update/delete)
- **Warning Validation**: Save without yield types should show warning but not block

## Report Template

Use the template at: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/TEMPLATE_code_review_report.md`

Write your report to: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F044-review.md`

**Important**: Write to `docs/code-reviews/` directory in the main repo, NOT in the worktree.

## Context Notes

- SQLAlchemy 2.x, CustomTkinter UI, pytest
- This feature moves yield type management INTO the Recipe Edit form (inline)
- Finished Units tab becomes a read-only catalog for browsing all yield types
- Session management pattern: functions accepting `session=None` parameter (see CLAUDE.md)
- Per-recipe uniqueness means same name CAN exist in different recipes
- Validation uses `func.lower()` for case-insensitive comparison
- Recipe filter dropdown added to Finished Units tab for filtering by recipe
- Info label explains that yield types are managed in Recipe Edit
