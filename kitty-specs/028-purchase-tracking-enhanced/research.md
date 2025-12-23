# Research: Purchase Tracking & Enhanced Costing

**Feature**: F028
**Date**: 2025-12-22
**Status**: Complete

## Executive Summary

F027 (Product Catalog Management) has already created significant infrastructure for F028. The Purchase model, Supplier model, and InventoryItem.purchase_id FK already exist. F028 needs to integrate these components and update the service layer and UI to enable purchase-aware inventory addition.

---

## Key Findings

### 1. Existing Infrastructure from F027

| Component | Status | Notes |
|-----------|--------|-------|
| `Purchase` model | Complete | Has product_id, supplier_id, purchase_date, unit_price, quantity_purchased, notes |
| `Supplier` model | Complete | Has all fields, is_active for soft delete, display_name property |
| `InventoryItem.purchase_id` | Exists | Nullable FK for migration transition |
| `InventoryItem.unit_cost` | Exists | Float field for FIFO costing |
| `supplier_service.py` | Complete | get_active_suppliers() ready for dropdown |
| `purchase_service.py` | Partial | Uses `store` string, not `supplier_id` FK |

### 2. Gap Analysis

**Service Layer Gaps:**
- `purchase_service.record_purchase()` uses `store: str` instead of `supplier_id: int`
- No function for "last price at supplier" for price suggestions
- No function for "last price any supplier" for fallback suggestions
- `inventory_item_service.add_to_inventory()` doesn't create Purchase or set purchase_id

**UI Gaps:**
- `InventoryItemFormDialog` (in `src/ui/inventory_tab.py`) lacks:
  - Supplier dropdown
  - Price field (unit_price or unit_cost)
  - Price suggestion hints

### 3. Architecture Decisions

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Hybrid service layer | Queries in purchase_service, creation in inventory_item_service | Standalone purchase_service (rejected: splits atomic operation) |
| Modify existing dialog in-place | Minimal changes, keeps code together | New dialog component (rejected: extra complexity) |
| Post-migration validation script | Simpler than dry-run, matches export/reset/import pattern | Dry-run mode (rejected: overkill for single-user app) |
| Use `supplier_id` FK not string | Referential integrity, enables joins | Store name string (rejected: F027 already uses FK pattern) |

### 4. FIFO Cost Calculation

Current implementation in `inventory_item_service.consume_fifo()` (lines 340-343):
```python
# Get unit cost from the inventory item (if available)
item_unit_cost = Decimal(str(item.unit_cost)) if item.unit_cost else Decimal("0.0")
```

**Decision**: Continue using `InventoryItem.unit_cost` for FIFO calculations. When creating inventory, copy `Purchase.unit_price` to `InventoryItem.unit_cost`. This maintains backward compatibility and keeps FIFO logic simple.

### 5. Price Suggestion Logic

Priority order for price pre-fill:
1. **Same product + same supplier**: Most accurate (last paid here)
2. **Same product + any supplier**: Fallback (last paid anywhere)
3. **No history**: Empty field with "(no purchase history)" hint

Query patterns needed:
```sql
-- Last price at specific supplier
SELECT unit_price, purchase_date
FROM purchases
WHERE product_id = ? AND supplier_id = ?
ORDER BY purchase_date DESC LIMIT 1

-- Last price at any supplier (fallback)
SELECT unit_price, purchase_date, supplier_id
FROM purchases
WHERE product_id = ?
ORDER BY purchase_date DESC LIMIT 1
```

---

## Implementation Impacts

### Files to Modify

| File | Changes |
|------|---------|
| `src/services/purchase_service.py` | Add `get_last_price_at_supplier()`, `get_last_price_any_supplier()` |
| `src/services/inventory_item_service.py` | Update `add_to_inventory()` to accept supplier_id, unit_price; create Purchase; set purchase_id and unit_cost |
| `src/ui/inventory_tab.py` | Update `InventoryItemFormDialog` with supplier dropdown, price field, price hints |
| `src/services/__init__.py` | Export new purchase_service functions if needed |

### Files to Create

| File | Purpose |
|------|---------|
| `src/services/migration/f028_migration.py` | Migration script for existing InventoryItems |
| `src/services/migration/f028_validation.py` | Post-migration validation script |

### Existing Code to Leverage

- `supplier_service.get_active_suppliers()` - Ready for dropdown
- `Purchase` model helper functions: `get_most_recent_price()`, `get_average_price()`
- `InventoryItem` already has `purchase_id` FK and `unit_cost` field
- `Supplier.display_name` property for dropdown labels

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Migration data loss | Low | High | Validation script, export before reset |
| Price suggestion latency | Low | Medium | Local SQLite queries are fast (<100ms) |
| NULL price_paid on existing records | Medium | Medium | Check for NULLs before migration |

---

## Open Questions (Resolved)

1. **Notes storage**: Confirmed - stored on InventoryItem (formerly InventoryAddition), not Purchase
2. **Unknown Supplier**: Per F027 design doc, migration creates "Unknown" supplier with:
   - name: 'Unknown', city: 'Unknown', state: 'XX', zip_code: '00000'
   - This is the fallback for migrated purchases in F028
3. **purchase_service.py signature**: Will use `supplier_id` (int FK) not `store` (string)
4. **Model naming**: Codebase uses `InventoryItem` (renamed from PantryItem), not `InventoryAddition`. F028 spec terminology should be updated.

---

## Next Steps

1. Phase 1: Create data-model.md with entity changes
2. Phase 1: Update plan.md with technical design
3. Phase 1: Run agent context update script
