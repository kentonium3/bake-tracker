# Code Review Report: F043 - Purchases Tab CRUD Operations

**Reviewer:** Cursor (Independent Review)
**Date:** 2026-01-09
**Feature Spec:** `kitty-specs/042-purchases-tab-crud-operations/spec.md` (+ `data-model.md`, `plan.md`, and `docs/func-spec/F043_purchases_tab_implementation.md`)

## Executive Summary
This feature implements a real Purchases tab UI (filters/sorting/context menu) and adds a set of CRUD-oriented service functions with solid unit test coverage. Verification passed cleanly, but there are a few high-impact data/ORM/session consistency issues that are very likely to break core workflows at runtime (dialogs) and/or violate the “Purchases drive Inventory” behavior required by the spec.

## Review Scope

**Primary Files Modified / Added (per prompt + worktree status):**
- `src/services/purchase_service.py`
- `src/tests/services/test_purchase_service.py`
- `src/ui/tabs/purchases_tab.py`
- `src/ui/dialogs/add_purchase_dialog.py` (NEW)
- `src/ui/dialogs/edit_purchase_dialog.py` (NEW)
- `src/ui/dialogs/purchase_details_dialog.py` (NEW)
- `src/ui/modes/purchase_mode.py`

**Additional Code Examined:**
- `src/models/purchase.py`
- `src/models/inventory_item.py`
- `src/models/inventory_depletion.py`
- `src/services/database.py` (to confirm session lifecycle / detachment behavior)
- `src/services/inventory_item_service.py` (to sanity-check how `InventoryDepletion.depletion_reason` is populated in practice)

## Environment Verification

**Setup Process (OUTSIDE sandbox, from worktree `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/042-purchases-tab-crud-operations`):**
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

**Results:**
- Import verification: **PASS** (“All imports successful”)
- `src/tests/services/test_purchase_service.py`: **PASS** (45 passed)
- Full `src/tests`: **PASS** (1774 passed, 14 skipped)

---

## Findings

### Critical Issues

**Detached ORM objects likely break Edit/Delete/Details dialogs at runtime**
- **Location:** `src/services/purchase_service.py` (`get_purchase`)
- **Problem:** `get_purchase()` returns a `Purchase` ORM object from inside `session_scope()` without eager-loading `purchase.product` / `purchase.supplier`. Because `session_scope()` closes the session and `expire_on_commit=False` does not enable lazy loading after close, any later access to relationships is likely to raise a `DetachedInstanceError`.
- **Impact:** Core UI flows that access `purchase.product...` after calling `get_purchase()` appear brittle:
  - `EditPurchaseDialog` builds its internal dict from `purchase.product.*`
  - `PurchaseDetailsDialog` renders `self.purchase.product.display_name`, `self.purchase.supplier.name`, etc.
  - `PurchasesTab` delete dialogs include `purchase.product.display_name`
- **Recommendation:** Make `get_purchase()` return a fully usable object outside the session by eager-loading required relationships, e.g. `joinedload(Purchase.product)`, `joinedload(Purchase.supplier)`, and (for details) `joinedload(Purchase.inventory_items).joinedload(InventoryItem.depletions)`. Alternatively, return a pure dict DTO rather than an ORM entity.

**“Add Purchase” does not appear to drive Inventory as required by the spec**
- **Location:** `src/ui/dialogs/add_purchase_dialog.py` + `src/services/purchase_service.py` (`record_purchase`)
- **Problem:** `AddPurchaseDialog` calls `record_purchase(...)`, which (as currently implemented) creates a `Purchase` row but does not create any `InventoryItem` records. The dialog UI even shows an “Inventory: +X …” preview, implying inventory is affected.
- **Impact:** This violates the spec’s core problem statement (“Purchases drive Inventory, not vice versa”) and can lead to:
  - Purchases being recorded without any inventory increase
  - “Remaining” showing as 0 for newly created purchases (since it’s derived from linked `InventoryItem.quantity`)
  - Edit quantity logic being a no-op for inventory when no `InventoryItem` rows exist
- **Recommendation:** Introduce/route through a purchase-creation service that atomically:
  - creates the `Purchase`
  - creates the associated `InventoryItem` (or items) with correct `quantity` and `unit_cost`
  - links via `purchase_id`
  - validates business rules at the service layer (not only in the UI)

**Delete path likely fails for unconsumed purchases due to FK constraints / missing cascade**
- **Location:** `src/services/purchase_service.py` (`delete_purchase`) + `src/models/inventory_item.py` (`purchase_id` FK is `ondelete="RESTRICT"`)
- **Problem:** The UI uses `can_delete_purchase()` to gate deletion, but actual deletion is done via `delete_purchase()`, which just `session.delete(purchase)` and does not remove linked `InventoryItem` rows. With `purchase_id` set to `RESTRICT`, this is expected to fail for purchases that have inventory rows.
- **Impact:** Users may be told they can delete a purchase (no depletions), confirm deletion, and then hit a database error instead of a successful delete.
- **Recommendation:** Implement a CRUD-safe delete that:
  - blocks deletion if any depletions exist (current behavior)
  - when allowed, deletes (or unlinks) all associated `InventoryItem` rows before deleting the `Purchase`, within a single transaction
  - ensures the UI calls this new delete implementation (and tests cover it)

### Major Concerns

**Quantity precision: spec/UI allow 1 decimal, but model/service are effectively integer-only**
- **Location:** `src/models/purchase.py` (`quantity_purchased: Integer`), `src/services/purchase_service.py` (`record_purchase` casts `int(quantity)`), and both dialogs validate “1 decimal place”
- **Problem:** The dialogs validate up to 1 decimal place, and the spec explicitly notes “spec now allows 1 decimal”, but the persisted model field is still `Integer` and `record_purchase` truncates decimals.
- **Impact:** Entering fractional package quantities can silently corrupt stored totals (e.g., `quantity_purchased` truncates but `unit_price` remains computed from the original quantity), leading to incorrect totals and downstream FIFO calculations.
- **Recommendation:** Align the storage and service layer with the spec:
  - either migrate `Purchase.quantity_purchased` to `Numeric` and consistently use `Decimal` throughout, or
  - constrain the UI/spec to integer package counts and remove 1-decimal validation + update the spec/docs accordingly.

**Supplier selection mismatch: dialog selects supplier, but service API is store-name based**
- **Location:** `src/ui/dialogs/add_purchase_dialog.py` → `record_purchase(..., store=supplier["name"])`
- **Problem:** The dialog is built around selecting a supplier entity, but `record_purchase` uses a string “store” and will create a placeholder supplier if one isn’t found by name.
- **Impact:** Risks duplicate suppliers, inconsistent supplier identity, and conflicts with a service-layer contract that should be `supplier_id` driven.
- **Recommendation:** Add a supplier-id-based create/record purchase API and use it from the dialog.

**Usage history assumes `InventoryDepletion.depletion_reason` is a recipe name**
- **Location:** `src/services/purchase_service.py` (`get_purchase_usage_history`, `can_delete_purchase`) + UI dialogs/tabs that display “recipe name”
- **Problem:** The feature (and tests) interpret `depletion_reason` as a recipe name, but the existing `inventory_item_service` writes `depletion_reason=reason.value` (i.e., enum-ish reasons like “spoilage/correction/…”). Production flows may not store recipe names there.
- **Impact:** Details/blocked-delete dialogs may show non-recipe strings (or meaningless reasons) instead of the required “recipe name”.
- **Recommendation:** Confirm the real source of recipe context for consumption:
  - if depletions truly link to production runs/recipes, query/join that data
  - otherwise, store/display a structured recipe reference in depletions rather than overloading `depletion_reason`.

**Keyboard shortcut binding may not fire depending on focus**
- **Location:** `src/ui/tabs/purchases_tab.py` (`self.bind("<Control-n>", ...)`)
- **Problem:** Binding to the frame may not receive keystrokes unless the frame has focus; this is a common Tk quirk.
- **Impact:** “Ctrl+N / Cmd+N” may appear broken for users.
- **Recommendation:** Consider `bind_all` (with care) or binding on the top-level window.

### Minor Issues

**Redundant query in `can_delete_purchase`**
- **Location:** `src/services/purchase_service.py` (`can_delete_purchase`)
- **Problem:** After eager-loading depletions, it re-queries `InventoryDepletion` by IDs to read `depletion_reason`.
- **Impact:** Minor performance/complexity cost.
- **Recommendation:** Reuse the already-loaded depletion objects.

**Mixed terminology in comments/docstrings (“Feature 042”)**
- **Location:** Several new module docstrings say “Feature 042” while this review prompt is “Feature 043”.
- **Impact:** Minor confusion for future maintainers.
- **Recommendation:** Normalize to the correct feature number/title for this implementation.

### Positive Observations
- **Solid test coverage** for the new service methods (filters, remaining inventory calculation, edit/delete validation, update behavior, usage history ordering).
- **Good session-sharing pattern**: new CRUD functions consistently accept `session: Optional[Session]=None` and delegate to `_impl` helpers.
- **UI ergonomics**: date-range dropdown, supplier filter, incremental search, sortable headings, double-click to details, and a right-click context menu are all present and align with the spec intent.

## Spec Compliance Analysis

- **Meets (mostly):**
  - Purchase list view with filters and search (`PurchasesTab` + `get_purchases_filtered`)
  - Sortable columns in the list UI
  - View Details dialog with inventory/usage sections (structure aligns with requirements)
  - Edit dialog shows product read-only and validates “cannot reduce below consumed” (logic exists in both UI and service)
  - Delete is blocked when consumed (service check exists; UI shows explanatory dialog)

- **At risk / missing relative to the spec:**
  - **Add purchase should increase inventory**: current flow appears to create only a `Purchase`, not any `InventoryItem` rows.
  - **Delete unconsumed purchase should succeed and remove remaining inventory**: current delete implementation likely fails due to FK RESTRICT unless inventory rows are handled.
  - **Quantity precision**: spec explicitly mentions 1 decimal place, but persistence is integer-only and truncates.
  - **Usage history “recipe name”**: implementation assumes `depletion_reason` contains recipe names, which may not match how depletions are produced in the application.

## Code Quality Assessment

**Consistency with Codebase:**
- Service functions mostly follow the `session=None` pattern used elsewhere (good).
- Some older purchase-service APIs (`record_purchase`, `delete_purchase`, `get_purchase`) are out of alignment with what the new UI expects (DTO-friendly objects, supplier_id flow, inventory linkage).

**Maintainability:**
- `PurchasesTab` is fairly self-contained and readable.
- The dialog implementations are straightforward, but currently depend on service semantics that appear inconsistent (supplier identity, inventory creation, ORM detachment).

**Test Coverage:**
- Strong for the new service methods.
- Gaps around end-to-end UI flows (especially “Add Purchase creates inventory” and “Delete purchase succeeds”).

**Dependencies & Integration:**
- This feature touches “purchase ↔ inventory ↔ depletion” boundaries where referential integrity and session lifecycle matter; the highest risk issues are at these boundaries.

## Recommendations Priority

**Must Fix Before Merge:**
1. Fix `get_purchase()` to return usable data outside a closed session (eager-load or return dict DTO) so dialogs don’t crash.
2. Implement a proper “delete purchase” operation that handles linked `InventoryItem` rows (and respects FIFO/depletion constraints).
3. Align Add Purchase with the spec: creating a purchase must also create the associated inventory record(s), or the spec/UI must be updated to match reality.

**Should Fix Soon:**
1. Resolve quantity precision mismatch (spec/UI vs `Integer` storage + `int()` truncation).
2. Switch to supplier-id-based purchase creation rather than “store name” string matching/auto-creating suppliers.
3. Confirm recipe-name sourcing for usage history; don’t rely on `depletion_reason` unless that is truly the app’s convention.
4. Improve key binding reliability for “Ctrl/Cmd+N”.

**Consider for Future:**
1. Reduce redundant queries in `can_delete_purchase` and standardize formatting of quantities/units in messages.
2. Add integration tests covering the full CRUD loop via services (create→inventory linkage→edit quantity/price→delete) to protect FIFO invariants.

## Overall Assessment
**Needs revision**.

The UI scaffolding and the new CRUD-supporting service methods are a strong foundation and the test suite is in great shape, but a few integration-layer mismatches (session detachment, delete FK behavior, and purchase→inventory linkage) are likely to break core CRUD workflows in real usage and/or violate the feature’s stated goals. I would not ship this to users until the “Must Fix Before Merge” items are addressed.

