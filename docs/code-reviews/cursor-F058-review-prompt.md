# Cursor Code Review Prompt: F058 Materials FIFO Foundation

## Feature Overview

**Feature Number:** F058
**Title:** Materials FIFO Foundation
**User Goal:** Implement FIFO (First In, First Out) inventory tracking for materials, paralleling the existing ingredient FIFO system. Materials purchased earlier are consumed first, enabling accurate cost tracking across multiple purchase lots with different unit costs.

## Specification

Read the feature specification first to understand intended behavior:
- `/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/058-materials-fifo-foundation/spec.md`

## Code Changes

The following files were modified or created for this feature. Review should extend to any related code, dependencies, or callers as needed.

**Model Layer:**
- `src/models/material_inventory_item.py` - New model for FIFO lot tracking (parallels InventoryItem)
- `src/models/material_product.py` - Removed deprecated `current_inventory`, `weighted_avg_cost` fields
- `src/models/material_consumption.py` - Added `inventory_item_id` FK for FIFO traceability
- `src/models/material.py` - Updated `base_unit_type` constraint from imperial to metric
- `src/models/material_purchase.py` - Added relationship to MaterialInventoryItem
- `src/models/__init__.py` - Export new MaterialInventoryItem model

**Service Layer:**
- `src/services/material_inventory_service.py` - New service for FIFO consumption operations
- `src/services/material_unit_converter.py` - New service for metric unit conversions
- `src/services/material_purchase_service.py` - Updated to create MaterialInventoryItem on purchase
- `src/services/material_catalog_service.py` - Updated to compute inventory from MaterialInventoryItem
- `src/services/material_consumption_service.py` - Updated to use FIFO consumption
- `src/services/material_unit_service.py` - Updated to use MaterialInventoryItem for inventory
- `src/services/denormalized_export_service.py` - Updated for deprecated field removal
- `src/services/import_export_service.py` - Updated for deprecated field removal
- `src/services/catalog_import_service.py` - Updated for metric base units
- `src/services/coordinated_export_service.py` - Updated for schema changes

**UI Layer:**
- `src/ui/materials_tab.py` - Removed deprecated inventory columns

**Tests:**
- `src/tests/test_material_fifo_integration.py` - New integration tests for FIFO behavior
- `src/tests/test_material_inventory_service.py` - New tests for inventory service
- `src/tests/test_material_unit_converter.py` - New tests for unit converter
- `src/tests/test_material_purchase_integration.py` - Updated purchase tests
- `src/tests/test_material_catalog_service.py` - Updated for deprecated field removal
- `src/tests/test_material_consumption_service.py` - Updated for FIFO consumption
- `src/tests/test_material_consumption_history.py` - Updated for metric units
- `src/tests/test_material_unit_service.py` - Updated for MaterialInventoryItem
- `src/tests/test_composition_materials.py` - Updated for metric units
- `src/tests/test_import_export_materials.py` - Updated for schema changes
- `src/tests/test_material_purchase_service.py` - Updated for FIFO inventory
- `src/tests/services/test_catalog_import_materials.py` - Updated for metric units
- `src/tests/services/test_denormalized_export.py` - Updated for deprecated fields
- `src/tests/services/test_material_hierarchy_service.py` - Updated for metric units

## Environment Verification

**CRITICAL: Run these commands OUTSIDE the sandbox.** Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Verify environment is functional
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/058-materials-fifo-foundation-WP01

# Run FIFO integration tests to confirm environment works
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/pytest src/tests/test_material_fifo_integration.py -v --tb=short

# If the above command fails, STOP and report blocker before proceeding
```

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

Use the template at:
- `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/TEMPLATE_cursor_report.md`

## Report Output

Write your review report to:
- `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F058-review.md`

**Important:** Write to the `docs/code-reviews/` directory in the main repo, NOT in the worktree.
