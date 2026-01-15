# Cursor Review Prompt: F053 - Context-Rich Export Fixes

## Your Role
You are a senior software engineer performing an independent code review. You are discovering this feature for the first time. Your fresh perspective is valuable for finding issues the implementer might have missed.

## Feature Overview
**Feature Number:** 053
**Title:** Context-Rich Export Fixes
**User Goal:** Enable users to export multiple entity types as context-rich JSON files for AI augmentation, with cleaner terminology and comprehensive entity coverage.

**Key Changes:**
1. Rename all "view" terminology to "context-rich" throughout the codebase
2. Change file prefix from `view_*.json` to `aug_*.json`
3. Add export methods for 4 new entity types (Products, Material Products, Finished Units, Finished Goods)
4. Replace radio buttons with checkboxes in the UI for multi-select export
5. Add "All" checkbox to select/deselect all entities at once

## Specification File
Full spec at: `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/053-context-rich-export-fixes/kitty-specs/053-context-rich-export-fixes/spec.md`

Work packages:
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/053-context-rich-export-fixes/kitty-specs/053-context-rich-export-fixes/tasks/WP01-service-layer-refactoring.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/053-context-rich-export-fixes/kitty-specs/053-context-rich-export-fixes/tasks/WP02-service-layer-new-exports.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/053-context-rich-export-fixes/kitty-specs/053-context-rich-export-fixes/tasks/WP03-ui-layer-multi-select.md`

## Primary Files Modified

**Service Layer:**
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/053-context-rich-export-fixes/src/services/denormalized_export_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/053-context-rich-export-fixes/src/services/enhanced_import_service.py`

**UI Layer:**
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/053-context-rich-export-fixes/src/ui/import_export_dialog.py`

**Tests:**
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/053-context-rich-export-fixes/src/tests/services/test_denormalized_export.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/053-context-rich-export-fixes/src/tests/services/test_enhanced_import.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/053-context-rich-export-fixes/src/tests/integration/test_import_export_roundtrip.py`

**Note:** These are the primary changes. Review should extend to any related code, dependencies, or callers as needed.

## Environment Verification

**CRITICAL: Run these commands OUTSIDE the sandbox.** Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Navigate to worktree
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/053-context-rich-export-fixes

# Verify imports work (use main repo's venv)
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "
from src.services.denormalized_export_service import (
    export_products_context_rich,
    export_material_products_context_rich,
    export_finished_units_context_rich,
    export_finished_goods_context_rich,
    PRODUCTS_CONTEXT_RICH_EDITABLE,
    MATERIAL_PRODUCTS_CONTEXT_RICH_EDITABLE,
)
from src.ui.import_export_dialog import ExportDialog
print('All imports successful')
"

# Run a subset of tests to verify environment
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/pytest /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/053-context-rich-export-fixes/src/tests/services/test_denormalized_export.py -v -k "test_export_empty" 2>&1 | head -30
```

**If ANY verification command fails, STOP immediately and report the blocker before proceeding.**

## Review Approach

1. **Read spec first** - Understand intended behavior BEFORE examining implementation
2. **Form independent expectations** - Decide how the feature SHOULD work based on spec
3. **Compare implementation to expectations** - Note where reality differs from your mental model
4. **Explore beyond modified files** - Follow dependencies, check callers, examine related systems
5. **Look for what wasn't specified** - Edge cases, error conditions, data integrity risks
6. **Run verification commands OUTSIDE sandbox** - If ANY command fails, STOP and report blocker
7. **Consider user experience** - Would this workflow feel natural? Any friction points?
8. **Write report** - Use template format and write to specified location

## Report Template
Use the template at: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/TEMPLATE_code_review_report.md`

## Report Output Location
Write your report to: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F053-review.md`

**Important:** Write to `docs/code-reviews/` directory in the MAIN repo, NOT in the worktree.

## Areas of Interest (Not Prescriptive)

These are areas that might warrant attention, but form your own review priorities:
- Consistency of terminology changes (no remaining "view" references in export-related code)
- New export methods follow established patterns
- UI checkbox behavior (All toggle, individual sync)
- Export handler correctly processes multiple selections
- Field definitions (editable vs readonly) are appropriate for each entity type
- JSON structure consistency across all export types
