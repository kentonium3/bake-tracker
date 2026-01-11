# Cursor Code Review Prompt: Feature 048 - Materials UI Rebuild

## Feature Overview

**Feature Number:** F048
**Title:** Materials UI Rebuild
**High-Level Goal:** Rebuild the Materials tab to match the established Ingredients tab pattern - using a 3-tab structure (Materials Catalog, Material Products, Material Units) with flat grid views, cascading dropdown filters, and modal dialogs for CRUD operations. This replaces the previous tree-based UI with a more consistent, user-friendly interface.

**Key Capabilities:**
1. Three sub-tabs: Materials Catalog | Material Products | Material Units
2. Flat grid views (no tree view) with ttk.Treeview for performance
3. Cascading L0/L1 category filters on Materials Catalog tab
4. Material filter dropdown on Products and Units tabs
5. Column header sorting (click to sort, toggle ascending/descending)
6. Modal dialogs matching Ingredients tab patterns (MaterialFormDialog, MaterialProductFormDialog, etc.)
7. Record Purchase dialog with auto-calculation of total units and unit cost
8. Adjust Inventory dialog with set-to-value or set-to-percentage modes
9. Inventory formatted as "4,724.5 inches", cost formatted as "$0.0016"

**Specification Files:**
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/048-materials-ui-rebuild/kitty-specs/048-materials-ui-rebuild/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/048-materials-ui-rebuild/kitty-specs/048-materials-ui-rebuild/plan.md`

## Code Changes

The following files were modified as part of this feature. These are the primary changes, but review should extend to any related code, dependencies, or callers as needed.

**UI (1 new + 1 archived):**
- `src/ui/materials_tab.py` - REWRITTEN: Complete rebuild with 3-tab structure (~2,935 lines)
- `src/ui/materials_tab_old.py` - PRESERVED: Original tree-based implementation for reference

**New Dialog Classes in materials_tab.py:**
- `MaterialFormDialog` - Add/edit materials with cascading L0/L1 dropdowns
- `MaterialProductFormDialog` - Add/edit products with material/supplier selection
- `RecordPurchaseDialog` - Record purchases with auto-calculation of units and cost
- `AdjustInventoryDialog` - Set inventory to value or percentage
- `MaterialUnitFormDialog` - Add/edit material units

**Inner Tab Classes in materials_tab.py:**
- `MaterialsTab` - Parent container with CTkTabview
- `MaterialsCatalogTab` - Grid view of materials with L0/L1 filters
- `MaterialProductsTab` - Grid view of products with material filter
- `MaterialUnitsTab` - Grid view of units with material filter

**Services Used (not modified, but should verify correct usage):**
- `src/services/material_catalog_service.py` - Category/subcategory/material CRUD
- `src/services/material_purchase_service.py` - Purchase recording, inventory queries
- `src/services/material_unit_service.py` - Unit management, cost/inventory queries
- `src/services/supplier_service.py` - Supplier list for dropdowns

## Environment Setup

**CRITICAL: Run these commands OUTSIDE the sandbox.** Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Navigate to the worktree
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/048-materials-ui-rebuild

# Verify Python environment (use main repo's venv)
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.ui.materials_tab import MaterialsTab, MaterialFormDialog, MaterialProductFormDialog, RecordPurchaseDialog, AdjustInventoryDialog, MaterialUnitFormDialog; print('Materials UI imports OK')"

# Verify services import
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.services import material_catalog_service, material_purchase_service, material_unit_service, supplier_service; print('Material services import OK')"

# Verify tests run (quick sanity check)
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -m pytest src/tests -v --tb=short -q 2>&1 | tail -10
```

If ANY verification command fails, STOP immediately and report the failure as a blocker before attempting any fixes.

## Review Approach

1. **Read spec first** - Understand intended behavior BEFORE examining implementation
2. **Form independent expectations** - Decide how the feature SHOULD work based on spec
3. **Compare implementation to expectations** - Note where reality differs from your mental model
4. **Explore beyond modified files** - Follow dependencies, check callers, examine related systems
5. **Look for what wasn't specified** - Edge cases, error conditions, data integrity risks
6. **Run verification commands OUTSIDE sandbox** - If ANY command fails, STOP immediately and report blocker
7. **Consider user experience** - Would this workflow feel natural? Any friction points?
8. **Compare to Ingredients tab** - Since this should match the Ingredients pattern, verify consistency with `src/ui/ingredients_tab.py`
9. **Write report** - Use the format below and write to the specified location

## Report Output

Write your review report to:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F048-review.md`

**Important:** Write to the `docs/code-reviews/` directory in the main repo, NOT in the worktree.

## Report Template

Use the template at:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/TEMPLATE_code_review_report.md`

Basic structure:

```markdown
# Code Review: F048 - Materials UI Rebuild

**Reviewer:** Cursor
**Date:** [DATE]
**Commit Range:** main..048-materials-ui-rebuild

## Executive Summary
[1-2 sentence overview of findings]

## Blockers
[Issues that MUST be fixed before merge - empty if none]

## Critical Issues
[Serious bugs, data integrity risks, security concerns]

## Major Concerns
[Issues affecting core functionality or maintainability]

## Minor Issues
[Code quality, style, optimization opportunities]

## Positive Observations
[What was done well]

## Recommendations
[Suggested improvements, non-blocking concerns]

## Questions for Implementer
[Clarifications needed, design decisions to discuss]

## Verification Results
[Output of environment verification commands]

## Files Reviewed
[List of files examined with brief notes]

## Overall Assessment
[Pass/Pass with minor fixes/Needs revision/Major rework needed]
```
