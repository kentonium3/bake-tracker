# Data Model: Feature 027 - Product Catalog Management

**Feature Branch**: `027-product-catalog-management`
**Date**: 2025-12-22

## Entity Overview

```
┌─────────────┐      ┌─────────────┐      ┌──────────────────┐
│  Supplier   │──┐   │   Product   │──────│    Ingredient    │
└─────────────┘  │   └─────────────┘      └──────────────────┘
       │         │          │
       │         │          │
       │         └──────────┤ preferred_supplier_id
       │                    │
       │                    │
       ▼                    ▼
┌─────────────────────────────────┐
│           Purchase              │
└─────────────────────────────────┘
                │
                │ purchase_id
                ▼
┌─────────────────────────────────┐
│       InventoryAddition         │
└─────────────────────────────────┘
```

## New Entities

### Supplier

**Purpose**: Represents a store or vendor where products are purchased.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| id | Integer | PK, auto-increment | Primary key |
| uuid | String(36) | Unique, not null | UUID for distributed scenarios |
| name | String(200) | Not null | Store/vendor name (e.g., "Costco") |
| street_address | String(200) | Nullable | Optional street address |
| city | String(100) | Not null | City name |
| state | String(2) | Not null, uppercase | Two-letter state code |
| zip_code | String(10) | Not null | 5 or 9-digit ZIP |
| notes | Text | Nullable | Optional notes |
| is_active | Boolean | Not null, default True | Soft delete flag |
| created_at | DateTime | Not null | Creation timestamp |
| updated_at | DateTime | Not null | Last update timestamp |

**Relationships**:
- One-to-Many: Supplier → Products (via Product.preferred_supplier_id)
- One-to-Many: Supplier → Purchases

**Indexes**:
- `idx_supplier_name_city` (name, city) - Common lookup pattern
- `idx_supplier_active` (is_active) - Filter active suppliers

**Constraints**:
- `ck_supplier_state_uppercase`: state = UPPER(state)
- `ck_supplier_state_length`: LENGTH(state) = 2

### Purchase

**Purpose**: Records a shopping transaction (product bought from supplier at a price).

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| id | Integer | PK, auto-increment | Primary key |
| uuid | String(36) | Unique, not null | UUID for distributed scenarios |
| product_id | Integer | FK(products.id), not null | Product purchased |
| supplier_id | Integer | FK(suppliers.id), not null | Where purchased |
| purchase_date | Date | Not null | Date of purchase |
| unit_price | Numeric(10,4) | Not null, >= 0 | Price per package unit |
| quantity_purchased | Integer | Not null, > 0 | Number of units bought |
| notes | Text | Nullable | Optional notes (sale info, etc.) |
| created_at | DateTime | Not null | Creation timestamp |

**Relationships**:
- Many-to-One: Purchase → Product
- Many-to-One: Purchase → Supplier
- One-to-Many: Purchase → InventoryAdditions

**Indexes**:
- `idx_purchase_product` (product_id)
- `idx_purchase_supplier` (supplier_id)
- `idx_purchase_date` (purchase_date)
- `idx_purchase_product_date` (product_id, purchase_date) - FIFO queries

**Constraints**:
- `ck_purchase_unit_price_non_negative`: unit_price >= 0
- `ck_purchase_quantity_positive`: quantity_purchased > 0

**FK Behavior**:
- product_id: ON DELETE RESTRICT (preserve purchase history)
- supplier_id: ON DELETE RESTRICT (preserve purchase history)

**Note**: No `updated_at` - purchases are immutable after creation.

## Modified Entities

### Product (Existing)

**New Attributes**:

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| preferred_supplier_id | Integer | FK(suppliers.id), nullable | Default supplier |
| is_hidden | Boolean | Not null, default False | Soft delete flag |

**New Relationships**:
- Many-to-One: Product → Supplier (preferred_supplier)
- One-to-Many: Product → Purchases

**New Indexes**:
- `idx_product_preferred_supplier` (preferred_supplier_id)
- `idx_product_hidden` (is_hidden)

**FK Behavior**:
- preferred_supplier_id: ON DELETE SET NULL (product remains if supplier removed)

### InventoryAddition (Existing)

**New Attributes**:

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| purchase_id | Integer | FK(purchases.id), not null | Linked purchase record |

**Deprecated Attributes**:

| Attribute | Status | Migration |
|-----------|--------|-----------|
| price_paid | Deprecated | Value migrated to Purchase.unit_price |

**New Relationship**:
- Many-to-One: InventoryAddition → Purchase

**New Index**:
- `idx_inventory_addition_purchase` (purchase_id)

**FK Behavior**:
- purchase_id: ON DELETE RESTRICT (cannot delete purchase with inventory)

## Referential Integrity Summary

| Source Table | Column | Target Table | ON DELETE |
|--------------|--------|--------------|-----------|
| Product | preferred_supplier_id | Supplier | SET NULL |
| Product | ingredient_id | Ingredient | RESTRICT (existing) |
| Purchase | product_id | Product | RESTRICT |
| Purchase | supplier_id | Supplier | RESTRICT |
| InventoryAddition | purchase_id | Purchase | RESTRICT |
| InventoryAddition | product_id | Product | RESTRICT (existing) |

## State Transitions

### Product Visibility

```
┌──────────┐     hide()      ┌──────────┐
│  Active  │ ───────────────▶│  Hidden  │
│is_hidden │                 │is_hidden │
│ = False  │ ◀───────────────│ = True   │
└──────────┘    unhide()     └──────────┘
```

### Supplier Status

```
┌──────────┐   deactivate()  ┌──────────┐
│  Active  │ ───────────────▶│ Inactive │
│is_active │                 │is_active │
│ = True   │ ◀───────────────│ = False  │
└──────────┘   reactivate()  └──────────┘
```

**Side Effect**: When supplier is deactivated, all products with `preferred_supplier_id = supplier.id` have that field set to NULL.

## Migration Data Transformation

### Input (Pre-Migration)

```json
{
  "inventory_additions": [
    {
      "id": 1,
      "product_id": 5,
      "quantity": 2,
      "addition_date": "2024-12-01",
      "price_paid": 15.99,
      ...
    }
  ]
}
```

### Output (Post-Migration)

```json
{
  "suppliers": [
    {
      "id": 1,
      "name": "Unknown",
      "city": "Unknown",
      "state": "XX",
      "zip_code": "00000",
      "is_active": true,
      "notes": "Default supplier for migrated data"
    }
  ],
  "purchases": [
    {
      "id": 1,
      "product_id": 5,
      "supplier_id": 1,
      "purchase_date": "2024-12-01",
      "unit_price": 15.99,
      "quantity_purchased": 1
    }
  ],
  "inventory_additions": [
    {
      "id": 1,
      "product_id": 5,
      "purchase_id": 1,
      "quantity": 2,
      "addition_date": "2024-12-01"
      // price_paid removed
    }
  ],
  "products": [
    {
      "id": 5,
      "preferred_supplier_id": null,
      "is_hidden": false,
      ...
    }
  ]
}
```

## Query Patterns

### Get Products with Last Purchase Price

```sql
SELECT p.*,
       (SELECT unit_price FROM purchases
        WHERE product_id = p.id
        ORDER BY purchase_date DESC LIMIT 1) as last_price
FROM products p
WHERE p.is_hidden = FALSE
```

### Get Purchase History for Product

```sql
SELECT pu.*, s.name as supplier_name
FROM purchases pu
JOIN suppliers s ON pu.supplier_id = s.id
WHERE pu.product_id = ?
ORDER BY pu.purchase_date DESC
```

### Get Products by Category (via Ingredient)

```sql
SELECT p.*
FROM products p
JOIN ingredients i ON p.ingredient_id = i.id
WHERE i.category = ?
  AND p.is_hidden = FALSE
```
