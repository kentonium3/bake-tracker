# Cursor Code Review Prompt: Feature 047 - Materials Management System

## Feature Overview

**Feature Number:** F047
**Title:** Materials Management System
**High-Level Goal:** Add a parallel inventory system for non-perishable craft/packaging materials (ribbons, boxes, bags, labels) that use weighted-average costing instead of FIFO. This supports materials that are purchased in bulk, stored indefinitely, and consumed in measured quantities during gift box assembly.

**Key Capabilities:**
1. Four-level hierarchy: Category > Subcategory > Material > Product
2. MaterialUnit definitions for standard consumption amounts (e.g., "6-inch ribbon")
3. Purchase tracking with automatic weighted-average cost recalculation
4. Integration with FinishedGood compositions (materials as assembly components)
5. Material consumption recording during assembly with inventory decrements
6. Historical consumption snapshots (preserves names/costs at consumption time)
7. Full import/export support with slug-based FK resolution

**Specification Files:**
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/047-materials-management-system/kitty-specs/047-materials-management-system/spec.md`

## Code Changes

The following files were modified as part of this feature. These are the primary changes, but review should extend to any related code, dependencies, or callers as needed.

**Models (7 new models + 1 modified):**
- `src/models/material_category.py` - NEW: Top-level category (e.g., "Ribbons", "Boxes")
- `src/models/material_subcategory.py` - NEW: Subcategory under category
- `src/models/material.py` - NEW: Generic material with base_unit_type
- `src/models/material_product.py` - NEW: Purchasable product from supplier
- `src/models/material_unit.py` - NEW: Standard consumption unit definition
- `src/models/material_purchase.py` - NEW: Purchase record with cost tracking
- `src/models/material_consumption.py` - NEW: Consumption record with snapshots
- `src/models/composition.py` - MODIFIED: Added material_id and material_unit_id FKs

**Services (6 new + 4 modified):**
- `src/services/material_catalog_service.py` - NEW: CRUD for hierarchy
- `src/services/material_purchase_service.py` - NEW: Purchase recording, weighted avg cost
- `src/services/material_unit_service.py` - NEW: Unit management, cost/inventory queries
- `src/services/material_consumption_service.py` - NEW: Consumption recording with snapshots
- `src/services/composition_service.py` - MODIFIED: Material composition support
- `src/services/assembly_service.py` - MODIFIED: Material consumption during assembly
- `src/services/catalog_import_service.py` - MODIFIED: Material entity imports
- `src/services/coordinated_export_service.py` - MODIFIED: Material entity exports

**UI (4 files):**
- `src/ui/materials_tab.py` - NEW: Materials catalog management tab
- `src/ui/modes/catalog_mode.py` - MODIFIED: Added MaterialsTab integration
- `src/ui/forms/finished_good_detail.py` - MODIFIED: Show material components
- `src/ui/forms/record_assembly_dialog.py` - MODIFIED: Material selection for assembly

**Tests (8 new + 1 modified):**
- `src/tests/test_material_catalog_service.py` - NEW
- `src/tests/test_material_purchase_service.py` - NEW
- `src/tests/test_material_unit_service.py` - NEW
- `src/tests/test_material_consumption_service.py` - NEW
- `src/tests/test_composition_materials.py` - NEW
- `src/tests/test_import_export_materials.py` - NEW
- `src/tests/test_material_consumption_history.py` - NEW
- `src/tests/services/test_coordinated_export.py` - MODIFIED

## Environment Setup

**CRITICAL: Run these commands OUTSIDE the sandbox.** Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Navigate to the worktree
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/047-materials-management-system

# Verify Python environment (use main repo's venv)
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.models import MaterialCategory, MaterialSubcategory, Material, MaterialProduct, MaterialUnit, MaterialPurchase, MaterialConsumption; print('Material models import OK')"

# Verify services import
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.services import material_catalog_service, material_purchase_service, material_unit_service, material_consumption_service; print('Material services import OK')"

# Verify tests run (quick sanity check)
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -m pytest src/tests/test_material_catalog_service.py -v --tb=short -q 2>&1 | tail -5
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
8. **Write report** - Use the format below and write to the specified location

## Report Output

Write your review report to:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F047-review.md`

**Important:** Write to the `docs/code-reviews/` directory in the main repo, NOT in the worktree.

## Report Template

Use the template at:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/TEMPLATE_code_review_report.md`

Basic structure:

```markdown
# Code Review: F047 - Materials Management System

**Reviewer:** Cursor
**Date:** [DATE]
**Commit Range:** main..047-materials-management-system

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
