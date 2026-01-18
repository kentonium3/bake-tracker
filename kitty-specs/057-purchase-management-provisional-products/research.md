# Research: F057 Purchase Management with Provisional Products

**Date**: 2026-01-17
**Feature**: 057-purchase-management-provisional-products
**Purpose**: Discover actual service interfaces and patterns before implementation

## Executive Summary

Codebase research confirms that all required services exist with appropriate interfaces. The key gap is the missing `is_provisional` field on the Product model. Service boundaries are well-established with consistent patterns for session management and delegation.

## Service Interface Discovery

### 1. Product Service (`src/services/product_service.py`)

**Status**: ✅ Exists with appropriate methods

**Key Methods Discovered**:

| Method | Signature | Purpose |
|--------|-----------|---------|
| `create_product` | `(ingredient_slug, product_data, session=None) -> Product` | Creates product with auto-calculated display_name |
| `get_product` | `(product_id, session=None) -> Product` | Retrieves with eager-loaded relationships |
| `get_products_for_ingredient` | `(ingredient_slug) -> List[Product]` | Returns all products for ingredient |
| `search_products_by_upc` | `(upc) -> List[Product]` | Exact UPC match |
| `update_product` | `(product_id, product_data) -> Product` | Partial update supported |

**Relevant Patterns**:
- Products can only be created on leaf ingredients (hierarchy_level == 2)
- Auto-generates display_name from brand, product_name, package_size
- Validates slug uniqueness via constraint (ingredient_id, brand, product_name, package_size, package_unit)
- Session parameter pattern: `session: Optional[Session] = None`

**Gap**: No `is_provisional` field support - must be added

### 2. Product Catalog Service (`src/services/product_catalog_service.py`)

**Status**: ✅ Exists with dict-based interface

**Key Methods Discovered**:

| Method | Signature | Purpose |
|--------|-----------|---------|
| `get_products` | `(include_hidden, ingredient_id, category, supplier_id, search) -> List[Dict]` | Filtered product list |
| `create_product` | `(product_name, ingredient_id, package_unit, ...) -> Dict` | Creates product, returns dict |
| `hide_product` | `(product_id) -> Dict` | Soft delete |
| `unhide_product` | `(product_id) -> Dict` | Restore hidden |

**Relevant Patterns**:
- Returns dicts instead of ORM objects (good for UI binding)
- Supports `is_hidden` field for soft delete
- Existing filter infrastructure can be extended for `is_provisional`

**Gap**: No provisional product methods - must be added

### 3. Purchase Service (`src/services/purchase_service.py`)

**Status**: ✅ Exists with atomic transaction pattern

**Key Methods Discovered**:

| Method | Signature | Purpose |
|--------|-----------|---------|
| `record_purchase` | `(product_id, quantity, total_cost, purchase_date, store, ..., session=None) -> Purchase` | Creates Purchase + InventoryItem atomically |
| `get_purchase_history` | `(product_id, ingredient_slug, start_date, end_date, store, limit) -> List[Purchase]` | Filtered history |
| `get_purchases_filtered` | `(date_range, supplier_id, search_query, session=None) -> List[Dict]` | UI-ready filtered list |

**Relevant Patterns**:
- `record_purchase` already creates both Purchase and InventoryItem in single transaction
- Creates or finds Supplier from store name automatically
- Price tracking and duplicate detection built-in

**Decision**: No changes needed to `record_purchase` - provisional products are valid products

### 4. Inventory Item Service (`src/services/inventory_item_service.py`)

**Status**: ✅ Exists with FIFO support

**Key Methods Discovered**:

| Method | Signature | Purpose |
|--------|-----------|---------|
| `add_to_inventory` | `(product_id, quantity, supplier_id, unit_price, ..., session=None) -> InventoryItem` | Creates inventory with optional Purchase |
| `consume_fifo` | `(ingredient_slug, quantity_needed, target_unit, dry_run, session) -> Dict` | FIFO consumption |
| `get_inventory_items` | `(ingredient_slug, product_id, location, min_quantity) -> List[InventoryItem]` | Filtered inventory |

**Decision**: No changes needed - works with any valid product

### 5. Supplier Service (`src/services/supplier_service.py`)

**Status**: ✅ Exists with auto-slug generation

**Key Methods Discovered**:

| Method | Signature | Purpose |
|--------|-----------|---------|
| `create_supplier` | `(name, city, state, zip_code, ..., session=None) -> Dict` | Creates with auto-slug |
| `generate_supplier_slug` | `(name, supplier_type, city, state, session=None) -> str` | Unique slug generation |
| `get_active_suppliers` | `(session=None) -> List[Dict]` | For dropdowns |

**Decision**: No changes needed - `record_purchase` already handles supplier lookup/creation

### 6. Import Services

**Status**: ✅ Multiple services exist

**Services Found**:
- `src/services/import_export_service.py` - Main import/export
- `src/services/coordinated_export_service.py` - Full backup import/export
- `src/services/transaction_import_service.py` - Purchase/inventory transactions
- `src/services/catalog_import_service.py` - Catalog data import

**Relevant Patterns**:
- Import services validate and create records transactionally
- Support for skip-on-error, dry-run modes
- Return detailed results with success/skip/error counts

**Gap**: Need to enhance to create provisional products for unknown items

## Model Analysis

### Product Model (`src/models/product.py`)

**Current Fields** (relevant subset):
```python
class Product(BaseModel):
    ingredient_id: int (FK, required)
    brand: str (200 chars, nullable, indexed)
    product_name: str (200 chars, nullable)
    package_size: str (100 chars, nullable)
    package_unit: str (50 chars, required)
    package_unit_quantity: float (required)
    upc_code: str (20 chars, indexed)
    gtin: str (20 chars, unique, indexed)
    is_hidden: bool (default=False, indexed)  # Soft delete
    preferred: bool (default=False)
    # ... other fields
```

**Gap**: No `is_provisional` field

**Recommendation**: Add `is_provisional = Column(Boolean, default=False, nullable=False, index=True)`

### Session Management Pattern

**Critical Pattern** (from CLAUDE.md):
```python
def service_method(..., session: Optional[Session] = None) -> Result:
    """All service methods accept optional session parameter."""
    if session is not None:
        return _impl(..., session)
    with session_scope() as session:
        return _impl(..., session)
```

**Rationale**: Prevents nested `session_scope()` calls that cause silent data loss.

**Decision**: All new methods will follow this pattern.

## UI Component Discovery

### Add Purchase Dialog

**Location**: Likely `src/ui/dialogs/add_purchase_dialog.py` or similar

**Research Needed**: Verify exact file and current structure

**Enhancement Plan**: Add collapsible "Create Provisional Product" section

### Products Tab

**Location**: Likely `src/ui/tabs/inventory_tab.py` or `products_tab.py`

**Research Needed**: Verify exact file and current filtering implementation

**Enhancement Plan**: Add "Needs Review" filter option and provisional count badge

## Conclusions

### Ready to Implement

1. **Product Model**: Add `is_provisional` field
2. **product_service**: Add `create_provisional_product()` method
3. **product_catalog_service**: Add `get_provisional_products()`, `get_provisional_count()`, `mark_product_reviewed()`
4. **Import services**: Enhance to create provisional products for unknown items

### No Changes Needed

1. **purchase_service**: Already works with any valid product
2. **inventory_item_service**: Already works with any valid product
3. **supplier_service**: Already auto-creates suppliers during purchase recording

### UI Research Deferred

Exact UI file paths and structures will be verified during implementation. The patterns are well-established in the codebase.

## Alternatives Considered

### Alternative 1: Separate ProvisionalProduct Model

**Rejected Because**: Adds complexity; a provisional product IS a product, just flagged for review.

### Alternative 2: Use `is_hidden` for Provisional

**Rejected Because**: Different semantics; hidden products are intentionally excluded, provisional products are actively usable.

### Alternative 3: Modal Dialog for Provisional Creation

**Rejected Because**: User preference for inline expansion; keeps user in purchase context.
