# Data Model: Materials FIFO Foundation

**Feature**: 058-materials-fifo-foundation
**Date**: 2026-01-18
**Version**: 1.0

## Overview

This document defines the schema changes required to implement FIFO inventory tracking for materials, paralleling the food/ingredients system.

---

## New Entity: MaterialInventoryItem

**Purpose**: Track individual lots of material inventory for FIFO consumption.

### Schema Definition

```python
class MaterialInventoryItem(BaseModel):
    """
    Tracks a specific lot of material inventory from a purchase.

    Parallels InventoryItem (for food) exactly.

    Key patterns:
    - quantity_purchased: Immutable snapshot at creation
    - quantity_remaining: Mutable, decremented on consumption
    - cost_per_unit: Immutable snapshot from purchase
    - purchase_date: Indexed for FIFO ordering
    """
    __tablename__ = "material_inventory_items"

    # Foreign Keys
    material_product_id = Column(
        Integer,
        ForeignKey("material_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    material_purchase_id = Column(
        Integer,
        ForeignKey("material_purchases.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Quantity Tracking (in base units - cm for linear/area, count for each)
    quantity_purchased = Column(Float, nullable=False)   # Immutable snapshot
    quantity_remaining = Column(Float, nullable=False)   # Mutable

    # Cost Tracking
    cost_per_unit = Column(Numeric(10, 4), nullable=False)  # Immutable snapshot

    # Date Tracking
    purchase_date = Column(Date, nullable=False, index=True)  # For FIFO ordering

    # Optional Fields
    location = Column(String(100), nullable=True, index=True)
    notes = Column(Text, nullable=True)

    # Relationships
    product = relationship("MaterialProduct", back_populates="inventory_items")
    purchase = relationship("MaterialPurchase", back_populates="inventory_item")
    consumptions = relationship("MaterialConsumption", back_populates="inventory_item")

    # Table constraints
    __table_args__ = (
        CheckConstraint("quantity_purchased > 0", name="ck_mat_inv_qty_purchased_positive"),
        CheckConstraint("quantity_remaining >= 0", name="ck_mat_inv_qty_remaining_non_negative"),
        CheckConstraint("cost_per_unit >= 0", name="ck_mat_inv_cost_non_negative"),
        Index("idx_material_inventory_product", "material_product_id"),
        Index("idx_material_inventory_purchase_date", "purchase_date"),
        Index("idx_material_inventory_purchase", "material_purchase_id"),
        Index("idx_material_inventory_location", "location"),
    )
```

### Validation Rules

| Field | Rule | Error Message |
|-------|------|---------------|
| quantity_purchased | > 0 | "Quantity purchased must be positive" |
| quantity_remaining | >= 0 | "Quantity remaining cannot be negative" |
| cost_per_unit | >= 0 | "Cost per unit cannot be negative" |
| material_product_id | Must exist | "Material product not found" |
| material_purchase_id | Must exist | "Material purchase not found" |

### Immutability Rules

| Field | Immutable | Notes |
|-------|-----------|-------|
| quantity_purchased | Yes | Set at creation, never changed |
| cost_per_unit | Yes | Snapshot from purchase, never changed |
| purchase_date | Yes | Copied from purchase, never changed |
| quantity_remaining | No | Decremented on consumption |
| location | No | Can be updated |
| notes | No | Can be updated |

---

## Modified Entity: MaterialProduct

**Change**: Remove `current_inventory` and `weighted_avg_cost` fields.

### Fields to Remove

```python
# REMOVE these fields
current_inventory = Column(Float, nullable=False, default=0.0)
weighted_avg_cost = Column(Numeric(10, 4), nullable=False, default=0)
```

### Constraints to Remove

```python
# REMOVE these constraints
CheckConstraint("current_inventory >= 0", name="ck_material_product_inventory_non_negative"),
CheckConstraint("weighted_avg_cost >= 0", name="ck_material_product_cost_non_negative"),
```

### Property to Remove

```python
# REMOVE this property
@property
def inventory_value(self) -> Decimal:
    return Decimal(str(self.current_inventory)) * self.weighted_avg_cost
```

### Relationship to Add

```python
# ADD this relationship
inventory_items = relationship(
    "MaterialInventoryItem",
    back_populates="product",
    cascade="all, delete-orphan",
    lazy="select",
)
```

---

## Modified Entity: MaterialConsumption

**Change**: Add `inventory_item_id` FK for FIFO traceability.

### Field to Add

```python
inventory_item_id = Column(
    Integer,
    ForeignKey("material_inventory_items.id", ondelete="RESTRICT"),
    nullable=True,  # Nullable for backward compatibility with existing records
    index=True,
)
```

### Relationship to Add

```python
inventory_item = relationship("MaterialInventoryItem", back_populates="consumptions")
```

---

## Modified Entity: Material

**Change**: Update `base_unit_type` allowed values to metric.

### Field Change

```python
# CHANGE allowed values
base_unit_type = Column(
    String(20),
    nullable=False,
    default="each",
)

# CHECK constraint update
CheckConstraint(
    "base_unit_type IN ('each', 'linear_cm', 'square_cm')",
    name="ck_material_base_unit_type",
)
```

### Migration for Existing Data

```python
# Convert existing imperial base_unit_type values
UNIT_TYPE_MIGRATION = {
    "linear_inches": "linear_cm",
    "square_inches": "square_cm",
    "each": "each",  # No change
}
```

---

## Modified Entity: MaterialPurchase

**Change**: Add relationship to MaterialInventoryItem (1:1).

### Relationship to Add

```python
# One purchase creates exactly one inventory item
inventory_item = relationship(
    "MaterialInventoryItem",
    back_populates="purchase",
    uselist=False,  # 1:1 relationship
)
```

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          DEFINITION LAYER                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐         ┌──────────────────┐                          │
│  │  Material   │ 1     * │  MaterialProduct │                          │
│  │  (category) │─────────│  (definition)    │                          │
│  │             │         │                  │                          │
│  │ base_unit_  │         │ - name           │                          │
│  │ type:       │         │ - brand          │                          │
│  │ linear_cm   │         │ - package_unit   │                          │
│  │ square_cm   │         │ - supplier_id    │                          │
│  │ each        │         │                  │                          │
│  └─────────────┘         │ NO cost/inventory│                          │
│                          └────────┬─────────┘                          │
│                                   │                                     │
└───────────────────────────────────┼─────────────────────────────────────┘
                                    │ 1
                                    │
┌───────────────────────────────────┼─────────────────────────────────────┐
│                          │ INSTANTIATION LAYER                         │
├───────────────────────────────────┼─────────────────────────────────────┤
│                                   │ *                                   │
│  ┌──────────────────┐    ┌───────┴────────────┐    ┌─────────────────┐ │
│  │ MaterialPurchase │ 1  │ MaterialInventory  │ 1  │ MaterialConsump │ │
│  │ (transaction)    │────│ Item (lot)         │────│ tion (audit)    │ │
│  │                  │    │                    │  * │                 │ │
│  │ - packages_      │    │ - qty_purchased    │    │ - quantity      │ │
│  │   purchased      │    │ - qty_remaining    │    │ - cost          │ │
│  │ - unit_cost      │    │ - cost_per_unit    │    │ - inventory_    │ │
│  │ - purchase_date  │    │ - purchase_date    │    │   item_id (NEW) │ │
│  └──────────────────┘    └────────────────────┘    └─────────────────┘ │
│                                                                         │
│  IMMUTABLE: purchase record, qty_purchased, cost_per_unit              │
│  MUTABLE: qty_remaining                                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Purchase → Inventory

```
User records MaterialPurchase
    │
    ├─ packages_purchased: 2
    ├─ package_price: $15.00
    ├─ units_added: 200 (feet)
    └─ unit_cost: $0.15 per foot
            │
            ▼
    Convert to base units
            │
            ├─ 200 feet × 30.48 = 6096 cm
            └─ $0.15/foot ÷ 30.48 = $0.00492/cm
                    │
                    ▼
    Create MaterialInventoryItem
            │
            ├─ quantity_purchased: 6096 (cm)
            ├─ quantity_remaining: 6096 (cm)
            ├─ cost_per_unit: 0.00492 ($/cm)
            └─ purchase_date: 2026-01-18
```

---

## Data Flow: FIFO Consumption

```
Assembly needs 1000 cm of ribbon
            │
            ▼
Query MaterialInventoryItem
    WHERE material_product_id = X
    AND quantity_remaining > 0
    ORDER BY purchase_date ASC
            │
            ▼
┌─────────────────────────────────────┐
│ Lot A (oldest): 500 cm @ $0.005/cm │
│ Lot B (newer):  800 cm @ $0.006/cm │
└─────────────────────────────────────┘
            │
            ▼
Consume 500 from Lot A (depleted)
Consume 500 from Lot B (300 remaining)
            │
            ▼
Create MaterialConsumption records:
    - 500 cm from Lot A, cost $2.50
    - 500 cm from Lot B, cost $3.00
            │
            ▼
Return: consumed=1000, total_cost=$5.50
```

---

## Schema Migration Script

```sql
-- Step 1: Add MaterialInventoryItem table
CREATE TABLE material_inventory_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid VARCHAR(36) UNIQUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    material_product_id INTEGER NOT NULL REFERENCES material_products(id) ON DELETE CASCADE,
    material_purchase_id INTEGER NOT NULL REFERENCES material_purchases(id) ON DELETE RESTRICT,

    quantity_purchased FLOAT NOT NULL,
    quantity_remaining FLOAT NOT NULL,
    cost_per_unit DECIMAL(10,4) NOT NULL,
    purchase_date DATE NOT NULL,
    location VARCHAR(100),
    notes TEXT,

    CHECK (quantity_purchased > 0),
    CHECK (quantity_remaining >= 0),
    CHECK (cost_per_unit >= 0)
);

CREATE INDEX idx_material_inventory_product ON material_inventory_items(material_product_id);
CREATE INDEX idx_material_inventory_purchase_date ON material_inventory_items(purchase_date);
CREATE INDEX idx_material_inventory_purchase ON material_inventory_items(material_purchase_id);
CREATE INDEX idx_material_inventory_location ON material_inventory_items(location);

-- Step 2: Add inventory_item_id to MaterialConsumption
ALTER TABLE material_consumptions ADD COLUMN inventory_item_id INTEGER REFERENCES material_inventory_items(id);
CREATE INDEX idx_material_consumption_inventory ON material_consumptions(inventory_item_id);

-- Step 3: Remove fields from MaterialProduct (SQLite requires table rebuild)
-- Export data, drop table, recreate without current_inventory/weighted_avg_cost, reimport

-- Step 4: Update Material.base_unit_type values
UPDATE materials SET base_unit_type = 'linear_cm' WHERE base_unit_type = 'linear_inches';
UPDATE materials SET base_unit_type = 'square_cm' WHERE base_unit_type = 'square_inches';
```
