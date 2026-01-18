# Cursor Code Review Prompt: F057 Purchase Management with Provisional Products

## Feature Overview

**Feature Number:** F057
**Title:** Purchase Management with Provisional Products
**User Goal:** Enable purchase recording regardless of product catalog state by allowing provisional product creation during purchase entry. Users can record purchases for products not yet in the catalog, with those products flagged for later review.

## Specification

Read the feature specification first to understand intended behavior:
- `/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/057-purchase-management-provisional-products/spec.md`

## Code Changes

The following files were modified or created for this feature. Review should extend to any related code, dependencies, or callers as needed.

**Model Layer:**
- `src/models/product.py` - Added `is_provisional` boolean field with index

**Service Layer:**
- `src/services/product_service.py` - Added `create_provisional_product()` function
- `src/services/product_catalog_service.py` - Added `get_provisional_products()`, `get_provisional_count()`, `mark_product_reviewed()`
- `src/services/coordinated_export_service.py` - Added `is_provisional` to product export/import
- `src/services/import_export_service.py` - Added `provisional_products_created` to ImportResult
- `src/services/transaction_import_service.py` - Added provisional product creation for unknown items

**UI Layer:**
- `src/ui/dialogs/add_purchase_dialog.py` - Added inline provisional product creation form
- `src/ui/products_tab.py` - Added "Needs Review" filter, badge, and "Mark as Reviewed" context menu

**Tests:**
- `src/tests/services/test_product_catalog_service.py` - Added tests for provisional product methods

## Environment Verification

**CRITICAL: Run these commands OUTSIDE the sandbox.** Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Verify environment is functional
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/057-purchase-management-provisional-products-WP01

# Run a quick test to confirm environment works
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/pytest src/tests/services/test_product_catalog_service.py -v -k "Provisional" --tb=short

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
- `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F057-review.md`

**Important:** Write to the `docs/code-reviews/` directory in the main repo, NOT in the worktree.
