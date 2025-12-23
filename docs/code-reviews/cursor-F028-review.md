# Cursor Code Review: Feature 028 - Purchase Tracking & Enhanced Costing

**Date:** 2025-12-23
**Reviewer:** Cursor (AI Code Review)
**Feature:** 028-purchase-tracking-enhanced
**Branch:** 028-purchase-tracking-enhanced

## Summary

Feature 028 successfully introduces **Purchase as the source of truth for unit pricing** and wires it into inventory entry and FIFO costing. The service-layer integration is solid and the **full test suite passes**. However, there is a **critical UI behavioral bug in the FIFO “Consume Ingredient” dialog** that appears to mutate inventory during “preview” (before confirmation), which should be fixed before merge.

## Verification Results

### Module Import Validation
- purchase_service.py (price suggestion functions): **PASS** (module imports; functions present)
- inventory_item_service.py (add_to_inventory update): **PASS**
- purchase.py (unit_cost property): **PASS** (`unit_cost` alias + `total_cost` computed property verified)
- inventory_tab.py (UI updates): **PASS (with warnings)** (supplier/price fields present; see Findings)
- f028_migration.py: **PASS** (script present; “Unknown” supplier behavior implemented)
- f028_validation.py: **PASS** (validations implemented)

### Test Results
- Full test suite: **1067 passed, 12 skipped, 0 failed** (1m53s)
- Purchase service tests (`src/tests/services/test_purchase_service.py`): **15 passed**
- Inventory item service tests (`src/tests/services/test_inventory_item_service.py`): **17 passed**
- Recipe service tests (`src/tests/services/test_recipe_service.py`): **75 passed**

### Service Coverage
- purchase_service: **24.68%** (unit tests cover the new price-suggestion helpers but not the broader analytics functions)
- inventory_item_service: **61.15%** (better coverage, still below the 70% target noted in the prompt)

### Code Pattern Validation
- Session parameter pattern: **present** in `get_last_price_at_supplier()`, `get_last_price_any_supplier()`, and `add_to_inventory()` (`session: Optional[Session] = None`); `consume_fifo()` uses `session=None`
- add_to_inventory signature updated: **correct** (requires `supplier_id` and `unit_price`)
- Purchase.unit_cost property: **present**
- Purchase.total_cost property: **present**
- Test fixtures: **present where needed** (`test_supplier` / supplier fixtures)

## Findings

### Critical Issues

1) **Consume Ingredient “Preview” appears to consume inventory (no dry_run)**
- In `src/ui/inventory_tab.py`, `ConsumeIngredientDialog._update_preview()` calls:
  - `inventory_item_service.consume_fifo(...)` **without** `dry_run=True`.
- This likely means:
  - inventory gets modified during preview (before confirmation),
  - and `_execute_consumption()` does not actually call a service to apply consumption (it only displays a message and closes).
- Impact: Users can unintentionally change inventory just by previewing a consumption plan; confirmation semantics are inverted.
- Suggested fix:
  - Use `dry_run=True` for preview,
  - call `consume_fifo(..., dry_run=False)` (or a dedicated “apply consumption” service) in `_execute_consumption()` after confirmation.

### Warnings

1) **UI confirmation dialog implementation differs from prompt expectation**
- The prompt calls for a CTkMessagebox-based warning for $0.00 price confirmation, but the UI uses `tkinter.messagebox.askyesno`.
- If the codebase standard is CTkMessagebox for consistency/appearance, consider switching.

2) **Supplier dropdown sorting relies on service behavior, not explicit UI sorting**
- `supplier_service.get_active_suppliers()` sorts by `Supplier.name`. This likely matches `display_name` ordering in most cases, but the prompt requirement is explicitly “sorted alphabetically by display_name.”
- If `display_name` includes location and could change ordering vs `name`, consider explicit sorting in UI (`sorted(..., key=lambda s: s["display_name"])`).

3) **Purchase service unit test has a placeholder “pass”**
- `TestGetLastPriceAtSupplier.test_works_without_session_parameter` is effectively a no-op (it passes without assertions).
- This reduces confidence that the `session_scope()` fallback path is exercised in unit tests.

4) **Quantity type coercion risks**
- `purchase_service.record_purchase()` and `inventory_item_service.add_to_inventory()` set `Purchase.quantity_purchased=int(quantity)` where `quantity` is a `Decimal`.
- Migration sets `quantity_purchased=int(item.quantity)` where `item.quantity` is a float.
- If non-integer quantities are possible, this truncates and could distort analytics/total_cost.

5) **ResourceWarnings in coverage runs**
- `pytest --cov` runs emitted “unclosed database” warnings for the in-memory SQLite tests. This usually indicates engines/connections not being fully disposed in fixtures.

### Observations

- **Atomic inventory+purchase creation is implemented well**: `add_to_inventory()` creates `Purchase` then `InventoryItem` with `purchase_id` in the same session and flushes both.
- **FIFO costing path is coherent**: `Purchase.unit_price` → `InventoryItem.unit_cost` → `consume_fifo()` aggregates cost from lots’ `unit_cost`.
- **Migration and validation are appropriately conservative**: nullable `purchase_id` supports transition; migration creates “Unknown” supplier with `state="XX"` as documented.

## Files Reviewed

| File | Status | Notes |
|------|--------|-------|
| src/services/purchase_service.py | PASS (with warnings) | Price-suggestion helpers look correct; `record_purchase` remains store-based; coverage low for broader functions |
| src/services/inventory_item_service.py | PASS | New signature + atomic Purchase creation + unit_cost population implemented; tests verify linkage |
| src/services/recipe_service.py | PASS | ValidationError list format observed in relevant spots |
| src/models/purchase.py | PASS | `unit_price` is stored; `unit_cost` alias + `total_cost` computed property present |
| src/models/inventory_item.py | PASS | `purchase_id` FK + relationship present; nullable for migration |
| src/ui/inventory_tab.py | PASS (NEEDS FIX) | Supplier/price UX present; **consume preview likely mutates inventory** |
| src/services/migration/f028_migration.py | PASS (with warnings) | Unknown supplier + purchase linkage implemented; quantity_purchased derivation may truncate |
| src/services/migration/f028_validation.py | PASS | Validates null purchase_id, orphaned purchases, product_id match, unit_cost population |
| src/tests/services/test_purchase_service.py | PASS (with warning) | Good coverage of price-suggestion behavior; placeholder test present |
| src/tests/services/test_inventory_item_service.py | PASS | Strong coverage of FIFO dry_run and purchase linkage |
| src/tests/services/test_recipe_service.py | PASS | No regressions from signature changes observed |
| test_data/sample_data.json | PASS | Version is **3.5** |

## Architecture Assessment

### Layered Architecture
UI (`inventory_tab.py`) calls into Services (`inventory_item_service`, `purchase_service`, `supplier_service`), which operate on Models (`Purchase`, `InventoryItem`). The dependency direction is appropriate.

### Session Management
The new price-suggestion helpers follow the expected “optional session” composability. `add_to_inventory()` also supports an injected session to keep Purchase+InventoryItem atomic.

### FIFO Cost Flow
The intended flow is implemented and verified in tests:
**Purchase.unit_price** → **InventoryItem.unit_cost** → **consume_fifo() total_cost/breakdown**.

### Backward Compatibility
`Purchase.unit_cost` alias and nullable `InventoryItem.purchase_id` support a safe transition + migration.

## Functional Requirements Verification

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FR-001: Supplier dropdown in Add Inventory | PASS | `InventoryItemFormDialog` includes supplier dropdown and uses `get_active_suppliers()` |
| FR-002: Supplier sorted alphabetically | PASS (with warning) | Sorted by `Supplier.name` via service; UI does not explicitly sort by `display_name` |
| FR-003: Price entry field with validation | PASS | Required on create; rejects negative; parses Decimal |
| FR-004: Price suggestion on supplier select | PASS | `_on_supplier_change()` calls `get_last_price_at_supplier()` |
| FR-005: Fallback price (any supplier) | PASS | Falls back to `get_last_price_any_supplier()` |
| FR-006: Price hint format correct | PASS | “(last paid: $X on YYYY-MM-DD)” and fallback “at Supplier” format present |
| FR-007: Zero-price confirmation warning | PASS (with warning) | Confirmation exists, uses `messagebox.askyesno` (not CTkMessagebox) |
| FR-008: Negative price validation error | PASS | UI + service both reject negative prices |
| FR-009: Purchase record created with inventory | PASS | `add_to_inventory()` creates Purchase + links `purchase_id` |
| FR-010: FIFO uses purchase-linked unit_cost | PASS | `consume_fifo()` uses `InventoryItem.unit_cost`; tests validate cost math |
| FR-011: Migration links existing inventory | PASS | `f028_migration.py` creates purchases for NULL `purchase_id` |
| FR-012: Migration creates Unknown supplier | PASS | Created with `name="Unknown"`, `state="XX"` |

## Work Package Verification

| Work Package | Status | Notes |
|--------------|--------|-------|
| WP01: Price Suggestion Functions | PASS | Functions present, correct ordering, unit tests included |
| WP02: Inventory-Purchase Integration | PASS | Signature updated; atomic purchase creation; tests verify linkage |
| WP03: UI Supplier Dropdown and Price Entry | PASS (NEEDS FIX) | Core UI present; consume dialog preview behavior is a critical bug |
| WP04: Migration and Validation Scripts | PASS | Migration + validation scripts present and aligned with intent |
| WP05: FIFO Verification and Testing | PASS | FIFO uses InventoryItem.unit_cost; full suite green |

## Test Coverage Assessment

| Test File | Tests | Coverage | Notes |
|-----------|-------|----------|-------|
| test_purchase_service.py | 15 | 24.68% (`purchase_service`) | Only exercises new helpers; many functions uncovered |
| test_inventory_item_service.py | 17 | 61.15% (`inventory_item_service`) | Good coverage of new functionality + dry_run |
| test_recipe_service.py | 75 | N/A | Not run with coverage in this review |

## Migration Script Assessment

| Check | Status | Notes |
|-------|--------|-------|
| Unknown supplier created (state=XX) | PASS | Implemented in `_get_or_create_unknown_supplier()` |
| Purchases from inventory_items | PASS | Creates Purchase for each InventoryItem missing purchase_id |
| purchase_id FK linkage | PASS | Sets `item.purchase_id = purchase.id` |
| unit_cost populated | PASS (with warning) | If missing, set to 0.00 + warning |
| Validation confirms no NULL purchase_id | PASS | `f028_validation.py` check 1 |
| FK integrity check | PASS | Validates Purchase exists and product_id matches |

## Conclusion

**NEEDS REVISION**

The backend/service-layer work is strong and fully green in tests, but the **Consume Ingredient preview/confirmation flow appears unsafe** and should be corrected before merging Feature 028.


