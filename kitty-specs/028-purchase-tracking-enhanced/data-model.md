# Data Model: Purchase Tracking & Enhanced Costing

**Feature**: F028
**Date**: 2025-12-22
**Status**: Based on codebase analysis

## Entity Overview

F027 has already created the core schema. F028 integrates these entities through service-layer changes.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Product   │────<│  Purchase   │>────│  Supplier   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           │ 1:N
                           ▼
                    ┌──────────────┐
                    │InventoryItem │
                    └──────────────┘
```

---

## Existing Entities (from F027)

### Purchase

**Location**: `src/models/purchase.py`
**Status**: Complete, no changes needed

| Field | Type | Nullable | Notes |
|-------|------|----------|-------|
| id | Integer | No | PK, auto-increment |
| uuid | String(36) | No | UUID for external refs |
| product_id | Integer | No | FK to products (RESTRICT) |
| supplier_id | Integer | No | FK to suppliers (RESTRICT) |
| purchase_date | Date | No | When purchased |
| unit_price | Numeric(10,4) | No | Price per unit |
| quantity_purchased | Integer | No | Units bought |
| notes | Text | Yes | Optional notes |
| created_at | DateTime | No | Creation timestamp |

**Constraints**:
- `ck_purchase_unit_price_non_negative`: unit_price >= 0
- `ck_purchase_quantity_positive`: quantity_purchased > 0

**Relationships**:
- `product`: Many-to-one → Product
- `supplier`: Many-to-one → Supplier
- `inventory_items`: One-to-many → InventoryItem

**Helper Functions** (already exist):
- `get_average_price(product_id, days, session)`
- `get_most_recent_price(product_id, session)`
- `get_price_trend(product_id, days, session)`

---

### Supplier

**Location**: `src/models/supplier.py`
**Status**: Complete, no changes needed

| Field | Type | Nullable | Notes |
|-------|------|----------|-------|
| id | Integer | No | PK |
| uuid | String(36) | No | UUID |
| name | String(200) | No | Store name |
| city | String(100) | No | City |
| state | String(2) | No | 2-letter code |
| zip_code | String(10) | No | ZIP |
| street_address | String(200) | Yes | Optional |
| notes | Text | Yes | Optional |
| is_active | Boolean | No | Soft delete flag |
| created_at | DateTime | No | Timestamp |
| updated_at | DateTime | No | Timestamp |

**Properties**:
- `display_name`: "{name} ({city}, {state})"
- `location`: "{city}, {state}"

**Relationships**:
- `purchases`: One-to-many → Purchase
- `products_preferred`: One-to-many → Product (via preferred_supplier_id)

---

### InventoryItem

**Location**: `src/models/inventory_item.py`
**Status**: Has purchase_id FK (nullable), needs service integration

| Field | Type | Nullable | Notes |
|-------|------|----------|-------|
| id | Integer | No | PK |
| uuid | String(36) | No | UUID |
| product_id | Integer | No | FK to products |
| quantity | Float | No | Current quantity |
| unit_cost | Float | Yes | **Cost for FIFO** |
| purchase_id | Integer | Yes | **FK to purchases** (nullable for migration) |
| added_date | Date | No | When added |
| expiration_date | Date | Yes | Optional |
| notes | Text | Yes | Optional |
| created_at | DateTime | No | Timestamp |
| updated_at | DateTime | No | Timestamp |

**Key Fields for F028**:
- `purchase_id`: Links to Purchase record (currently nullable for backward compat)
- `unit_cost`: Used by FIFO calculation, should be populated from Purchase.unit_price

**Relationships**:
- `product`: Many-to-one → Product
- `purchase`: Many-to-one → Purchase (via purchase_id)

---

### Product

**Location**: `src/models/product.py`
**Status**: Complete, has preferred_supplier_id from F027

| Field | Type | Nullable | Notes |
|-------|------|----------|-------|
| id | Integer | No | PK |
| uuid | String(36) | No | UUID |
| ingredient_id | Integer | No | FK to ingredients |
| display_name | String | No | Product name |
| brand | String | Yes | Brand name |
| package_unit | String | No | Unit type (lb, oz) |
| package_unit_quantity | Decimal | No | Quantity per package |
| preferred_supplier_id | Integer | Yes | FK to suppliers (SET NULL) |
| is_hidden | Boolean | No | Soft delete flag |
| notes | Text | Yes | Optional |

**Relationships**:
- `ingredient`: Many-to-one → Ingredient
- `preferred_supplier`: Many-to-one → Supplier
- `purchases`: One-to-many → Purchase
- `inventory_items`: One-to-many → InventoryItem

---

## Service Layer Changes

### purchase_service.py

**Current State**: Uses `store: str` parameter (needs update)
**Required Changes**:

```python
# NEW FUNCTIONS NEEDED

def get_last_price_at_supplier(
    product_id: int,
    supplier_id: int,
    session: Optional[Session] = None
) -> Optional[Dict[str, Any]]:
    """
    Get last purchase price for product at specific supplier.

    Returns:
        Dict with keys: unit_price, purchase_date, supplier_id
        None if no history
    """

def get_last_price_any_supplier(
    product_id: int,
    session: Optional[Session] = None
) -> Optional[Dict[str, Any]]:
    """
    Get last purchase price for product at any supplier.
    Fallback when no history at selected supplier.

    Returns:
        Dict with keys: unit_price, purchase_date, supplier_id, supplier_name
        None if no history
    """
```

---

### inventory_item_service.py

**Current State**: `add_to_inventory()` doesn't create Purchase or set purchase_id

**Required Changes to `add_to_inventory()`**:

```python
def add_to_inventory(
    product_id: int,
    quantity: float,
    supplier_id: int,          # NEW REQUIRED PARAM
    unit_price: Decimal,       # NEW REQUIRED PARAM
    added_date: Optional[date] = None,
    expiration_date: Optional[date] = None,
    notes: Optional[str] = None,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Add inventory item with linked Purchase record.

    ATOMIC OPERATION:
    1. Create Purchase record with product_id, supplier_id, unit_price
    2. Create InventoryItem with purchase_id set
    3. Set InventoryItem.unit_cost = unit_price (for FIFO)
    """
```

---

## Data Flow

### Add Inventory with Purchase (New Flow)

```
User Action                    Service Layer                     Database
─────────────────────────────────────────────────────────────────────────
Select Product          →
Select Supplier         →      get_last_price_at_supplier()  →   Query purchases
                        ←      Return {price, date, supplier}
Pre-fill Price         ←
User confirms/edits    →
Click "Add"            →      add_to_inventory(               →   BEGIN TRANSACTION
                                product_id,
                                quantity,
                                supplier_id,
                                unit_price,
                                ...
                              )
                              ↓
                              Create Purchase                  →   INSERT purchases
                              ↓
                              Create InventoryItem             →   INSERT inventory_items
                              (purchase_id, unit_cost)
                              ↓
                        ←      Return success                  ←   COMMIT
Update UI              ←
```

### FIFO Cost Calculation (Unchanged)

FIFO uses `InventoryItem.unit_cost`, which will be populated from `Purchase.unit_price` at creation time. No changes to `consume_fifo()` needed.

---

## Migration Requirements

### Existing InventoryItems

For InventoryItems created before F028:
1. `purchase_id` is NULL (per F027 migration)
2. `unit_cost` may be NULL or populated

### F028 Migration Script

```python
# src/services/migration/f028_migration.py

def migrate_inventory_to_purchases(session):
    """
    Create Purchase records for existing InventoryItems without purchase_id.

    Steps:
    1. Find/create "Unknown" supplier
    2. For each InventoryItem where purchase_id IS NULL:
       a. Create Purchase record:
          - product_id: from InventoryItem
          - supplier_id: "Unknown" supplier
          - purchase_date: InventoryItem.added_date
          - unit_price: InventoryItem.unit_cost or 0.00
          - quantity_purchased: 1
       b. Set InventoryItem.purchase_id to new Purchase.id
       c. Set InventoryItem.unit_cost if NULL
    3. Commit transaction
    """
```

### Validation Script

```python
# src/services/migration/f028_validation.py

def validate_purchase_linkage(session) -> bool:
    """
    Validate all InventoryItems have linked Purchase records.

    Checks:
    1. No InventoryItem has NULL purchase_id
    2. All Purchase.product_id matches InventoryItem.product_id
    3. All InventoryItem.unit_cost is populated
    4. Record counts match (pre vs post)
    """
```

---

## Constraints and Rules

1. **Purchase Required**: After F028, all new InventoryItems MUST have a linked Purchase
2. **Supplier Required**: UI must require supplier selection (no blank allowed)
3. **Price >= 0**: Allow $0.00 (with warning), reject negative
4. **RESTRICT Delete**: Cannot delete Product or Supplier with Purchase history
5. **Immutable Purchase**: Purchase records have no `updated_at` (immutable after creation)

---

## Index Strategy

Existing indexes (from F027) are sufficient:
- `idx_purchase_product`: For product-specific queries
- `idx_purchase_supplier`: For supplier-specific queries
- `idx_purchase_date`: For date range queries
- `idx_purchase_product_date`: For price history (product + date sort)
