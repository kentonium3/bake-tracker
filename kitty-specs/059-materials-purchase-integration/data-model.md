# F059 Data Model Reference

**Feature**: 059-materials-purchase-integration
**Created**: 2026-01-18
**Source**: F058 schema (existing models)

## Overview

F059 uses entities established in F058. This document provides a reference for UI implementation. No schema changes required except potentially adding `is_provisional` to MaterialProduct.

---

## Entity: Material

**File**: `src/models/material.py`
**Purpose**: Defines a category of material (e.g., "Red Satin Ribbon", "Snowflake Gift Bags")

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | Integer | PK | Auto-increment |
| uuid | UUID | No | Future distributed use |
| slug | String(100) | Yes | Unique identifier (e.g., "red-satin-ribbon") |
| name | String(200) | Yes | Display name |
| description | Text | No | Optional description |
| base_unit_type | Enum | Yes | "each", "linear_cm", or "square_cm" |
| category_id | FK(MaterialCategory) | Yes | Parent category |
| created_at | DateTime | Yes | Auto-set |
| updated_at | DateTime | Yes | Auto-updated |

**Relationships**:
- `category` → MaterialCategory (many-to-one)
- `products` → MaterialProduct (one-to-many)
- `units` → MaterialUnit (one-to-many)

**F059 Usage**: Read-only (dropdown population, unit type display)

---

## Entity: MaterialProduct

**File**: `src/models/material_product.py`
**Purpose**: Specific purchasable product (e.g., "Snowflake Bags 50-pack" from Amazon)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | Integer | PK | Auto-increment |
| uuid | UUID | No | Future distributed use |
| slug | String(100) | Yes | Unique identifier |
| name | String(200) | Yes | Display name |
| material_id | FK(Material) | Yes | Parent material |
| brand | String(100) | No | Brand name |
| sku | String(50) | No | Product SKU |
| supplier_id | FK(Supplier) | No | Preferred supplier |
| package_quantity | Decimal | Yes | Units per package |
| package_unit | String(50) | Yes | Package unit (e.g., "each", "cm") |
| quantity_in_base_units | Decimal | Yes | Converted to base units |
| notes | Text | No | Optional notes |
| is_hidden | Boolean | No | Soft-delete flag (default: False) |
| **is_provisional** | Boolean | No | **F059: Provisional flag (default: False)** |
| created_at | DateTime | Yes | Auto-set |
| updated_at | DateTime | Yes | Auto-updated |

**Relationships**:
- `material` → Material (many-to-one)
- `supplier` → Supplier (many-to-one, optional)
- `purchases` → MaterialPurchase (one-to-many)
- `inventory_items` → MaterialInventoryItem (one-to-many)

**F059 Usage**:
- Purchase form dropdown (filtered by is_hidden=False)
- Provisional creation via CLI
- Enrichment (update + clear is_provisional)

**F059 Completeness Check**:
Product is complete when ALL of these are non-null:
- name
- brand
- slug
- package_quantity
- package_unit
- material_id

---

## Entity: MaterialPurchase

**File**: `src/models/material_purchase.py`
**Purpose**: Record of a purchase transaction

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | Integer | PK | Auto-increment |
| uuid | UUID | No | Future distributed use |
| product_id | FK(MaterialProduct) | Yes | Product purchased |
| supplier_id | FK(Supplier) | No | Where purchased |
| purchased_at | Date | Yes | Purchase date |
| quantity | Decimal | Yes | Number of packages |
| total_cost | Decimal | Yes | Total amount paid |
| unit_cost | Decimal | Yes | Cost per base unit (calculated) |
| notes | Text | No | Optional notes |
| created_at | DateTime | Yes | Auto-set |

**Relationships**:
- `product` → MaterialProduct (many-to-one)
- `supplier` → Supplier (many-to-one, optional)
- `inventory_items` → MaterialInventoryItem (one-to-many)

**F059 Usage**: Created by purchase form and CLI

---

## Entity: MaterialInventoryItem

**File**: `src/models/material_inventory_item.py`
**Purpose**: Individual inventory lot with FIFO tracking

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | Integer | PK | Auto-increment |
| uuid | UUID | No | Future distributed use |
| product_id | FK(MaterialProduct) | Yes | Product |
| purchase_id | FK(MaterialPurchase) | No | Source purchase |
| purchased_at | Date | Yes | For FIFO ordering |
| quantity_purchased | Decimal | Yes | Original quantity (base units) |
| quantity_remaining | Decimal | Yes | Current quantity (base units) |
| cost_per_unit | Decimal | Yes | Cost per base unit |
| notes | Text | No | Optional (e.g., adjustment reason) |
| created_at | DateTime | Yes | Auto-set |
| updated_at | DateTime | Yes | Auto-updated |

**Relationships**:
- `product` → MaterialProduct (many-to-one)
- `purchase` → MaterialPurchase (many-to-one, optional)

**F059 Usage**:
- Inventory display (list lots, show remaining)
- Manual adjustment (update quantity_remaining directly)

**FIFO Note**: Display order is purchased_at DESC (newest first for user visibility). Consumption order (FIFO) is oldest first (handled by F058 service).

---

## Entity: MaterialUnit

**File**: `src/models/material_unit.py`
**Purpose**: Predefined consumption unit (e.g., "6-inch Ribbon Bow" = 15.24 cm)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | Integer | PK | Auto-increment |
| uuid | UUID | No | Future distributed use |
| slug | String(100) | Yes | Unique identifier |
| name | String(200) | Yes | Display name |
| material_id | FK(Material) | Yes | Parent material |
| quantity_per_unit | Decimal | Yes | Base units consumed per use |
| description | Text | No | Optional description |
| created_at | DateTime | Yes | Auto-set |
| updated_at | DateTime | Yes | Auto-updated |

**Relationships**:
- `material` → Material (many-to-one)

**F059 Usage**:
- UI enhancement: Display inherited unit type from Material.base_unit_type
- Lock quantity to 1 for "each" materials

---

## Entity Relationships Diagram

```
MaterialCategory
    └── Material (base_unit_type: each|linear_cm|square_cm)
            ├── MaterialProduct (is_provisional, is_hidden)
            │       ├── MaterialPurchase
            │       │       └── MaterialInventoryItem (FIFO lot)
            │       └── MaterialInventoryItem (direct, for adjustments)
            └── MaterialUnit (quantity_per_unit inherits unit type)

Supplier ──────────┬── MaterialProduct (preferred)
                   └── MaterialPurchase (actual)
```

---

## Service Method Signatures

### MaterialInventoryService (F058 existing + F059 addition)

```python
# Existing (F058)
def list_inventory_items(
    product_id: Optional[int] = None,
    include_depleted: bool = False,
    session: Optional[Session] = None
) -> List[Dict]

# NEW (F059) - Manual adjustment
def adjust_inventory(
    inventory_item_id: int,
    new_quantity: Decimal,  # For "each" materials
    percentage: Optional[Decimal] = None,  # For variable materials (0-100)
    notes: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict
```

### MaterialCatalogService (F058 existing + F059 addition)

```python
# Existing (F058)
def create_product(
    material_id: int,
    name: str,
    package_quantity: Decimal,
    package_unit: str,
    brand: Optional[str] = None,
    is_provisional: bool = False,  # F059: Add this parameter
    session: Optional[Session] = None
) -> Dict

def update_product(
    product_id: int,
    name: Optional[str] = None,
    brand: Optional[str] = None,
    # ... other fields
    session: Optional[Session] = None
) -> Dict

# NEW (F059) - Completeness check
def check_provisional_completeness(
    product_id: int,
    session: Optional[Session] = None
) -> Tuple[bool, List[str]]  # (is_complete, missing_fields)
```

---

## Validation Rules

### MaterialProduct (Provisional)

| Rule | Validation |
|------|------------|
| Minimum for provisional | name, material_id, package_quantity, package_unit |
| Complete (non-provisional) | name, brand, slug, package_quantity, package_unit, material_id |

### MaterialInventoryItem (Adjustment)

| Rule | Validation |
|------|------------|
| Quantity non-negative | new_quantity >= 0 |
| Percentage valid | 0 <= percentage <= 100 |
| Cannot exceed original | new_quantity <= quantity_purchased (warning only) |

### Purchase Form

| Rule | Validation |
|------|------------|
| Product required | MaterialProduct must be selected |
| Quantity positive | packages_purchased > 0 |
| Package count positive | package_unit_count > 0 |
| Cost non-negative | total_cost >= 0 |
| Date valid | Not future date |
