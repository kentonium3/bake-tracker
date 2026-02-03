# Cursor Code Review Prompt: F089 Error Handling Foundation

## Feature Information

**Feature Number:** F089
**Title:** Error Handling Foundation
**High-Level User Goal:** Establish a consistent exception hierarchy and centralized error handling pattern across the application, converting generic exception catches to specific domain exceptions with user-friendly error messages.

**Spec File:** `/Users/kentgale/Vaults-repos/bake-tracker/docs/func-spec/F089_error_handling_foundation.md`

## Code Changes

The following files were created or modified as part of this feature:

**Exception Infrastructure:**
- `src/services/exceptions.py` - Consolidated exception hierarchy with `ServiceError` base class
- `src/ui/utils/error_handler.py` - Centralized UI error handler

**UI Files Updated (three-tier exception pattern):**
- `src/ui/forms/ingredient_form.py`
- `src/ui/forms/product_form.py`
- `src/ui/forms/recipe_form.py`
- `src/ui/forms/recipe_detail_dialog.py`
- `src/ui/forms/product_detail_dialog.py`
- `src/ui/forms/inventory_item_form.py`
- `src/ui/forms/purchase_form.py`
- `src/ui/forms/material_form.py`
- `src/ui/forms/material_package_form.py`
- `src/ui/forms/package_config_form.py`
- `src/ui/forms/event_form.py`
- `src/ui/forms/event_target_form.py`
- `src/ui/forms/event_assembly_target_form.py`
- `src/ui/tabs/catalog_tab.py`
- `src/ui/tabs/inventory_tab.py`
- `src/ui/tabs/production_tab.py`
- `src/ui/tabs/packages_tab.py`
- `src/ui/tabs/shopping_tab.py`
- `src/ui/tabs/events_tab.py`
- `src/ui/tabs/dashboard_tab.py`
- `src/ui/dialogs/batch_production_dialog.py`
- `src/ui/dialogs/assembly_dialog.py`
- `src/ui/dialogs/shopping_list_dialog.py`
- `src/ui/dialogs/import_dialog.py`
- `src/ui/dialogs/export_dialog.py`
- `src/ui/utils/ui_helpers.py`
- `src/ui/components/editable_tree.py`
- `src/ui/components/inventory_table.py`
- `src/ui/components/sortable_table.py`

**Documentation:**
- `docs/design/error_handling_guide.md` - Developer documentation

**Tests:**
- `src/tests/unit/test_exceptions.py` - Exception hierarchy tests

These are the primary changes, but review should extend to any related code, dependencies, or callers as needed.

## Environment Setup

**CRITICAL: Run these commands OUTSIDE the sandbox.**

Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Navigate to project root
cd /Users/kentgale/Vaults-repos/bake-tracker

# Activate virtual environment
source venv/bin/activate

# Verify imports work
python -c "from src.services.exceptions import ServiceError; print('Exceptions OK')"
python -c "from src.ui.utils.error_handler import handle_error; print('Error handler OK')"

# Run exception tests
pytest src/tests/unit/test_exceptions.py -v
```

If ANY command fails, STOP immediately and report as a blocker before attempting fixes.

## Review Approach

1. **Read spec first** - Understand the intended behavior BEFORE examining implementation
2. **Form independent expectations** - Decide how the feature SHOULD work based on spec
3. **Compare implementation to expectations** - Note where reality differs from your mental model
4. **Explore beyond modified files** - Follow dependencies, check callers, examine related systems
5. **Look for what wasn't specified** - Edge cases, error conditions, data integrity risks
6. **Run verification commands OUTSIDE sandbox** - If ANY command fails, STOP immediately and report blocker
7. **Consider user experience** - Would this workflow feel natural? Any friction points?
8. **Write report** - Use template format and write to specified location

## Report Template

Use the template at: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/TEMPLATE_cursor_report.md`

## Report Output Location

Write your review report to: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F089-review.md`

**Important:** Write to the `docs/code-reviews/` directory, NOT in any worktree.
