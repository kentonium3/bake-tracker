# Cursor Code Review Prompt: Feature 051 - Import/Export UI Rationalization

## Feature Overview

**Feature Number:** F051
**Title:** Import/Export UI Rationalization
**User Goal:** Consolidate three separate import menu options into a single unified Import Data dialog with 5 purpose types (Backup, Catalog, Purchases, Adjustments, Context-Rich). Adds supplier import/export capability, pre-import schema validation, comprehensive logging, and configurable directories via Preferences.

## Specification

Read the full specification before examining implementation:
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/051-import-export-ui-rationalization/kitty-specs/051-import-export-ui-rationalization/spec.md`

## Code Changes

**New Services:**
- `src/services/schema_validation_service.py` - Pre-import JSON structure validation
- `src/services/preferences_service.py` - Directory preferences management

**New UI:**
- `src/ui/preferences_dialog.py` - File > Preferences dialog

**Modified Services:**
- `src/services/import_export_service.py` - Added selective entity export via `entities` parameter
- `src/services/catalog_import_service.py` - Added supplier import with slug validation, dependency ordering

**Modified UI:**
- `src/ui/import_export_dialog.py` - Added Context-Rich purpose, schema validation integration, multi-entity display
- `src/ui/main_window.py` - Added Preferences menu, removed Import Catalog and Import View menus

**New Tests:**
- `src/tests/test_schema_validation_service.py`
- `src/tests/test_preferences_service.py`

These are the primary changes, but review should extend to any related code, dependencies, or callers as needed.

## Environment Setup

**CRITICAL: Run these commands OUTSIDE the sandbox.** Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Navigate to the worktree
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/051-import-export-ui-rationalization

# Verify imports work (uses main repo venv)
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.services.schema_validation_service import validate_import_data; print('Import OK')"

# Run a quick test to verify environment
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -m pytest src/tests/test_schema_validation_service.py -v --tb=short -q 2>&1 | head -20
```

If ANY command fails, STOP immediately and report blocker before attempting fixes.

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

Use the template at: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/TEMPLATE_code_review_report.md`

## Report Output

Write your review report to: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F051-review.md`

**Important:** Write to the `docs/code-reviews/` directory in the main repo, NOT in the worktree.
