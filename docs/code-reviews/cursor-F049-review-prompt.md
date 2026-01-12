# Cursor Code Review Prompt: Feature 049 - Import/Export System Phase 1

## Feature Overview

**Feature Number**: 049
**Title**: Import/Export System Phase 1
**User Goal**: Enable complete system backup/restore, materials catalog import, context-rich exports for AI augmentation, and transaction imports (purchases/adjustments) from BT Mobile companion app.

## Specification Files

Read these to understand requirements BEFORE examining implementation:

- **Primary Spec**: `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/049-import-export-phase1/kitty-specs/049-import-export-phase1/spec.md`
- **Implementation Plan**: `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/049-import-export-phase1/kitty-specs/049-import-export-phase1/plan.md`
- **Updated Documentation**: `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/049-import-export-phase1/docs/design/spec_import_export.md`

## Code Changes

These are the primary implementation files. Review should extend to any related code, dependencies, or callers as needed.

**Services (Core Implementation)**:
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/049-import-export-phase1/src/services/coordinated_export_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/049-import-export-phase1/src/services/denormalized_export_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/049-import-export-phase1/src/services/enhanced_import_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/049-import-export-phase1/src/services/transaction_import_service.py`

**UI Layer**:
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/049-import-export-phase1/src/ui/import_export_dialog.py`

**Test Files**:
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/049-import-export-phase1/src/tests/services/test_coordinated_export.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/049-import-export-phase1/src/tests/services/test_denormalized_export.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/049-import-export-phase1/src/tests/services/test_enhanced_import.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/049-import-export-phase1/src/tests/services/test_transaction_import_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/049-import-export-phase1/src/tests/services/test_catalog_import_materials.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/049-import-export-phase1/src/tests/integration/test_import_export_roundtrip.py`

## Environment Verification

**CRITICAL**: Run these commands OUTSIDE the sandbox. Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Navigate to worktree
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/049-import-export-phase1

# Verify imports work (use main repo venv)
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "
from src.services.coordinated_export_service import export_complete
from src.services.denormalized_export_service import export_ingredients_view
from src.services.enhanced_import_service import detect_format
from src.services.transaction_import_service import import_purchases, import_adjustments
from src.ui.import_export_dialog import ImportDialog, ExportDialog
print('All imports successful')
"

# Run tests (abbreviated - full suite has 286 tests)
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/pytest src/tests/services/test_transaction_import_service.py -v --tb=short -q 2>&1 | tail -20
```

If ANY command fails, STOP immediately and report as a blocker before attempting fixes.

## Report Template

Use the template at: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/TEMPLATE_code_review_report.md`

## Report Output Location

Write your review report to: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F049-review.md`

**Important**: Write to the `docs/code-reviews/` directory in the MAIN repo, NOT in the worktree.

## Review Approach

1. **Read spec first** - Understand intended behavior BEFORE examining implementation
2. **Form independent expectations** - Decide how the feature SHOULD work based on spec
3. **Compare implementation to expectations** - Note where reality differs from your mental model
4. **Explore beyond modified files** - Follow dependencies, check callers, examine related systems
5. **Look for what wasn't specified** - Edge cases, error conditions, data integrity risks
6. **Run verification commands OUTSIDE sandbox** - If ANY command fails, STOP immediately and report blocker
7. **Consider user experience** - Would this workflow feel natural? Any friction points?
8. **Write report** - Use template format and write to specified location
