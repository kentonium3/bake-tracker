# Cursor Code Review Prompt - Feature 043: Purchases Tab CRUD Operations

## Your Role

You are a senior software engineer performing an independent code review. Approach this as if discovering the feature for the first time. Read the spec first, form your own expectations, then evaluate the implementation.

## Feature Context

**Feature:** 043 - Purchases Tab CRUD Operations
**User Goal:** Manage purchase history with full CRUD operations - view, filter, add, edit, and delete purchases with FIFO inventory tracking and validation
**Spec File:** `kitty-specs/042-purchases-tab-crud-operations/spec.md`

## Files to Review

**Service Layer:**
```
src/services/purchase_service.py (extended with 6 new CRUD methods)
src/tests/services/test_purchase_service.py (30 new tests, 45 total)
```

**UI Components:**
```
src/ui/tabs/purchases_tab.py (full implementation replacing placeholder)
src/ui/dialogs/add_purchase_dialog.py (NEW)
src/ui/dialogs/edit_purchase_dialog.py (NEW)
src/ui/dialogs/purchase_details_dialog.py (NEW)
src/ui/modes/purchase_mode.py (lazy loading added)
```

These are the primary changes, but review should extend to any related code, dependencies, or callers as needed.

## Spec Files (Read First)

```
kitty-specs/042-purchases-tab-crud-operations/spec.md
kitty-specs/042-purchases-tab-crud-operations/data-model.md
kitty-specs/042-purchases-tab-crud-operations/plan.md
docs/func-spec/F043_purchases_tab_implementation.md
```

## Verification Commands

**CRITICAL: Run these commands OUTSIDE the sandbox.**

Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

Run from worktree: `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/042-purchases-tab-crud-operations`

```bash
source /Users/kentgale/Vaults-repos/bake-tracker/venv/bin/activate

# Verify imports
PYTHONPATH=. python3 -c "
from src.services.purchase_service import (
    get_purchases_filtered,
    get_remaining_inventory,
    can_edit_purchase,
    can_delete_purchase,
    update_purchase,
    get_purchase_usage_history
)
from src.ui.tabs.purchases_tab import PurchasesTab
from src.ui.dialogs.add_purchase_dialog import AddPurchaseDialog
from src.ui.dialogs.edit_purchase_dialog import EditPurchaseDialog
from src.ui.dialogs.purchase_details_dialog import PurchaseDetailsDialog
print('All imports successful')
"

# Run purchase service tests
PYTHONPATH=. python3 -m pytest src/tests/services/test_purchase_service.py -v --tb=short

# Run full test suite (should pass 1774 tests)
PYTHONPATH=. python3 -m pytest src/tests -v --tb=short 2>&1 | tail -30
```

**If ANY verification fails, STOP and report as blocking issue.**

## Review Instructions

1. **Read the spec** (`spec.md`) to understand intended behavior
2. **Form expectations** about how this SHOULD work before reading code
3. **Run verification commands** - stop if failures
4. **Review implementation** comparing against your expectations
5. **Write report** to `docs/code-reviews/cursor-F043-review.md`

## Key Review Areas

- **FIFO Integrity**: Quantity validation on edit (new_qty >= consumed_qty), delete blocking when consumed
- **Session Management**: See CLAUDE.md - functions accepting `session=None` parameter pattern
- **Validation Completeness**: Future dates rejected, zero/negative quantities rejected, product read-only on edit
- **UI/UX Flow**: Double-click opens details, context menu operations, keyboard shortcuts (Delete, Ctrl+N)
- **Error Handling**: Purchase not found, database errors, race conditions
- **Data Consistency**: Cascade deletes, FIFO cost recalculation on price change

## Report Template

Use the template at: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/TEMPLATE_code_review_report.md`

Write your report to: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F043-review.md`

**Important**: Write to `docs/code-reviews/` directory in the main repo, NOT in the worktree.

## Context Notes

- SQLAlchemy 2.x, CustomTkinter UI, pytest
- This feature adds CRUD operations to the existing Purchases Tab placeholder
- Uses service layer pattern - UI calls services, services manage database
- FIFO (First In, First Out) inventory tracking is critical for cost accuracy
- Purchase cannot change product (would break FIFO chain)
- Quantity cannot be reduced below consumed amount
- Price changes trigger unit_cost recalculation on linked InventoryItems
- Delete is blocked if any inventory has been consumed (depletions exist)
- All dialogs are modal (transient + grab_set)
- Decimal precision for quantities (1 decimal place) and prices
