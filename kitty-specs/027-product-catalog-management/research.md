# Research: Feature 027 - Product Catalog Management

**Feature Branch**: `027-product-catalog-management`
**Date**: 2025-12-22
**Status**: Complete

## Executive Summary

This research phase validates the technical approach for Product Catalog Management, focusing on schema design, service layer patterns, and migration strategy. All major decisions align with the Constitution and existing codebase patterns.

## Decisions & Rationale

### D-001: New Entities (Supplier, Purchase)

**Decision**: Create two new SQLAlchemy models: `Supplier` and `Purchase`.

**Rationale**:
- Supplier enables tracking where products are purchased (price history by store)
- Purchase centralizes transaction data (replaces `InventoryAddition.price_paid`)
- Both follow existing BaseModel pattern with UUID support

**Alternatives Considered**:
- Embedding supplier info in Purchase (rejected: violates normalization, no supplier management)
- Keeping price_paid on InventoryAddition (rejected: no supplier tracking, no purchase history)

**Evidence**: See `docs/design/F027_product_catalog_management.md` Section: Technical Design

### D-002: Product Table Extensions

**Decision**: Add `preferred_supplier_id` (FK, nullable) and `is_hidden` (boolean, default False) to existing Product model.

**Rationale**:
- `preferred_supplier_id`: Enables "where do I usually buy this?" queries
- `is_hidden`: Soft delete preserves purchase history while removing from active views

**Alternatives Considered**:
- Separate ProductStatus table (rejected: over-engineering for single flag)
- Hard delete with archive table (rejected: complex, referential integrity issues)

**Evidence**: Design doc Section: Product Table Updates

### D-003: InventoryAddition Modification

**Decision**: Add `purchase_id` (FK, required), deprecate `price_paid` column.

**Rationale**:
- Single source of truth for pricing (Purchase.unit_price)
- Enables purchase history queries without scanning inventory additions
- RESTRICT on delete prevents orphaned inventory records

**Alternatives Considered**:
- Keep both columns (rejected: dual tracking, data inconsistency risk)
- Make purchase_id optional (rejected: breaks FIFO costing integrity)

**Evidence**: Design doc Section: InventoryAddition Table Updates

### D-004: Session Management Pattern

**Decision**: All new service functions accept `session: Optional[Session] = None` parameter.

**Rationale**:
- Per CLAUDE.md Session Management rules
- Prevents detached object issues in nested operations
- Enables transactional atomicity across service calls

**Evidence**: CLAUDE.md Section: Session Management (CRITICAL)

### D-005: Migration Strategy

**Decision**: Use export/reset/import cycle per Constitution VI.

**Rationale**:
- Single-user desktop app, no migration script complexity needed
- Transform existing InventoryAddition.price_paid to Purchase records during import
- Create "Unknown" supplier for historical data

**Migration Steps**:
1. Export all data via `import_export_service.export_all_to_json_v3()`
2. Transform JSON: create suppliers, convert inventory additions to purchases
3. Reset database (delete and recreate with new schema)
4. Import transformed data

**Evidence**: Constitution VI: Schema Change Strategy

### D-006: UI Placement

**Decision**: New "Products" tab in main window tab bar.

**Rationale**:
- Products are first-class entities needing dedicated management
- Consistent with existing tab-based navigation (Pantry, Recipes, Events, etc.)
- Separate from inventory (Products = catalog, Inventory = stock on hand)

**Evidence**: Design doc Section: UI Changes

### D-007: Supplier Management UI

**Decision**: Inline supplier management within Products tab (not separate tab).

**Rationale**:
- Suppliers are secondary to products (exist to support product tracking)
- Reduces tab clutter
- Access via "Manage Suppliers" button or within Add Product dialog

**Evidence**: User Story 3 acceptance scenarios

## Codebase Analysis

### Existing Patterns to Follow

| Pattern | Location | Applies To |
|---------|----------|------------|
| BaseModel inheritance | `src/models/base.py` | Supplier, Purchase models |
| session_scope() context manager | `src/services/database.py` | All new service functions |
| Optional session parameter | `src/services/*_service.py` | product_service, supplier_service |
| Service exceptions | `src/services/exceptions.py` | ProductNotFoundError, SupplierNotFoundError |
| CTkToplevel dialogs | `src/ui/forms/*.py` | AddProductDialog, ProductDetailDialog |
| Tab frame pattern | `src/ui/*_tab.py` | ProductsTab |

### Files to Modify

| File | Modification |
|------|--------------|
| `src/models/__init__.py` | Export Supplier, Purchase |
| `src/models/product.py` | Add preferred_supplier_id, is_hidden |
| `src/models/inventory_addition.py` | Add purchase_id, deprecate price_paid |
| `src/services/__init__.py` | Export product_service, supplier_service |
| `src/services/import_export_service.py` | Update export/import for new entities |
| `src/ui/main_window.py` | Add Products tab |

### New Files to Create

| File | Purpose |
|------|---------|
| `src/models/supplier.py` | Supplier SQLAlchemy model |
| `src/models/purchase.py` | Purchase SQLAlchemy model |
| `src/services/product_catalog_service.py` | Product CRUD with purchase history |
| `src/services/supplier_service.py` | Supplier CRUD |
| `src/ui/products_tab.py` | Products tab UI |
| `src/ui/forms/add_product_dialog.py` | Add/Edit product dialog |
| `src/ui/forms/product_detail_dialog.py` | Product detail with purchase history |
| `src/tests/services/test_product_catalog_service.py` | Unit tests |
| `src/tests/services/test_supplier_service.py` | Unit tests |
| `src/tests/integration/test_product_catalog.py` | Integration tests |

## Risk Assessment

### Low Risk
- **New models**: Isolated, follow established patterns
- **Service functions**: Testable, no UI dependencies
- **Tab UI**: Follows existing tab pattern

### Medium Risk
- **Migration data transformation**: Must handle edge cases (null prices, orphaned additions)
- **Existing test compatibility**: Schema changes may break fixtures

### Mitigation
- Create comprehensive migration transformation tests
- Update test fixtures before running full test suite
- Backup production database before migration

## Open Questions

None - all major decisions resolved during specification phase.

## Evidence Log

See `research/evidence-log.csv` for detailed source tracking.
