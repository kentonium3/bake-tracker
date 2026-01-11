# Data Model: Materials Management System

**Feature**: 047-materials-management-system
**Date**: 2026-01-10
**Status**: Complete

## Entity Relationship Overview

```
MaterialCategory (1) ──< MaterialSubcategory (1) ──< Material (1) ──< MaterialProduct
                                                         │                    │
                                                         │                    ├──< MaterialPurchase
                                                         │                    │
                                                         ▼                    │
                                                    MaterialUnit ─────────────┘
                                                         │
                                                         ▼
                                                    Composition ──> FinishedGood
                                                         │
                                                         ▼
                                                    AssemblyRun ──< MaterialConsumption
```

## Entities

### MaterialCategory

Top-level grouping for materials (e.g., "Ribbons", "Boxes", "Bags", "Tags").

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | PK, auto | Primary key |
| uuid | String(36) | Unique, Not Null | UUID identifier |
| name | String(100) | Unique, Not Null | Category display name |
| slug | String(100) | Unique, Not Null | URL-friendly identifier |
| description | Text | Nullable | Optional description |
| sort_order | Integer | Not Null, Default 0 | Display ordering |
| created_at | DateTime | Not Null | Creation timestamp |
| updated_at | DateTime | Not Null | Last modified |

**Relationships**:
- `subcategories`: One-to-Many with MaterialSubcategory (cascade delete)

**Indexes**:
- `idx_material_category_name` on name
- `idx_material_category_slug` on slug

---

### MaterialSubcategory

Second-level grouping within a category (e.g., "Satin Ribbon" under "Ribbons").

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | PK, auto | Primary key |
| uuid | String(36) | Unique, Not Null | UUID identifier |
| category_id | Integer | FK, Not Null | Parent MaterialCategory |
| name | String(100) | Not Null | Subcategory display name |
| slug | String(100) | Unique, Not Null | URL-friendly identifier |
| description | Text | Nullable | Optional description |
| sort_order | Integer | Not Null, Default 0 | Display ordering |
| created_at | DateTime | Not Null | Creation timestamp |
| updated_at | DateTime | Not Null | Last modified |

**Relationships**:
- `category`: Many-to-One with MaterialCategory
- `materials`: One-to-Many with Material (cascade delete)

**Indexes**:
- `idx_material_subcategory_category` on category_id
- `idx_material_subcategory_slug` on slug

**Constraints**:
- `uq_material_subcategory_name_category`: Unique(category_id, name)

---

### Material

Abstract material definition (e.g., "Red Satin Ribbon", "6-inch Cellophane Bag").

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | PK, auto | Primary key |
| uuid | String(36) | Unique, Not Null | UUID identifier |
| subcategory_id | Integer | FK, Not Null | Parent MaterialSubcategory |
| name | String(200) | Not Null | Material display name |
| slug | String(200) | Unique, Not Null | URL-friendly identifier |
| description | Text | Nullable | Optional description |
| base_unit_type | String(20) | Not Null | 'each', 'linear_inches', 'square_inches' |
| notes | Text | Nullable | User notes |
| created_at | DateTime | Not Null | Creation timestamp |
| updated_at | DateTime | Not Null | Last modified |

**Relationships**:
- `subcategory`: Many-to-One with MaterialSubcategory
- `products`: One-to-Many with MaterialProduct (cascade delete)
- `units`: One-to-Many with MaterialUnit

**Indexes**:
- `idx_material_subcategory` on subcategory_id
- `idx_material_slug` on slug
- `idx_material_name` on name

**Constraints**:
- `ck_material_base_unit_type`: base_unit_type IN ('each', 'linear_inches', 'square_inches')

---

### MaterialProduct

Specific purchasable item from a supplier (e.g., "Michaels Red Satin 100ft Roll").

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | PK, auto | Primary key |
| uuid | String(36) | Unique, Not Null | UUID identifier |
| material_id | Integer | FK, Not Null | Parent Material |
| supplier_id | Integer | FK, Nullable | Preferred Supplier |
| name | String(200) | Not Null | Product display name |
| brand | String(100) | Nullable | Brand name |
| sku | String(100) | Nullable | Supplier SKU |
| package_quantity | Float | Not Null | Quantity per package |
| package_unit | String(20) | Not Null | Unit of package (e.g., 'feet', 'yards', 'each') |
| quantity_in_base_units | Float | Not Null | Converted quantity in base units |
| current_inventory | Float | Not Null, Default 0 | Current inventory in base units |
| weighted_avg_cost | Numeric(10,4) | Not Null, Default 0 | Weighted average cost per base unit |
| is_hidden | Boolean | Not Null, Default False | Hide from selection lists |
| notes | Text | Nullable | User notes |
| created_at | DateTime | Not Null | Creation timestamp |
| updated_at | DateTime | Not Null | Last modified |

**Relationships**:
- `material`: Many-to-One with Material
- `supplier`: Many-to-One with Supplier (existing table)
- `purchases`: One-to-Many with MaterialPurchase

**Indexes**:
- `idx_material_product_material` on material_id
- `idx_material_product_supplier` on supplier_id
- `idx_material_product_hidden` on is_hidden

**Constraints**:
- `ck_material_product_quantity_positive`: package_quantity > 0
- `ck_material_product_base_units_positive`: quantity_in_base_units > 0
- `ck_material_product_inventory_non_negative`: current_inventory >= 0
- `ck_material_product_cost_non_negative`: weighted_avg_cost >= 0

---

### MaterialUnit

Atomic consumption unit defining quantity per use (e.g., "6-inch ribbon" = 6 inches per unit).

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | PK, auto | Primary key |
| uuid | String(36) | Unique, Not Null | UUID identifier |
| material_id | Integer | FK, Not Null | Parent Material |
| name | String(200) | Not Null | Unit display name (e.g., "6-inch Red Ribbon") |
| slug | String(200) | Unique, Not Null | URL-friendly identifier |
| quantity_per_unit | Float | Not Null | Base units consumed per use |
| description | Text | Nullable | Optional description |
| created_at | DateTime | Not Null | Creation timestamp |
| updated_at | DateTime | Not Null | Last modified |

**Relationships**:
- `material`: Many-to-One with Material

**Indexes**:
- `idx_material_unit_material` on material_id
- `idx_material_unit_slug` on slug

**Constraints**:
- `ck_material_unit_quantity_positive`: quantity_per_unit > 0

**Computed Properties**:
- `available_inventory`: Sum of (product.current_inventory / quantity_per_unit) across all products for this material
- `current_cost`: weighted_avg_cost * quantity_per_unit (aggregated across products)

---

### MaterialPurchase

Purchase transaction with immutable cost snapshot.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | PK, auto | Primary key |
| uuid | String(36) | Unique, Not Null | UUID identifier |
| product_id | Integer | FK, Not Null | MaterialProduct purchased |
| supplier_id | Integer | FK, Not Null | Supplier where purchased |
| purchase_date | Date | Not Null | Date of purchase |
| packages_purchased | Integer | Not Null | Number of packages bought |
| package_price | Numeric(10,4) | Not Null | Price per package |
| units_added | Float | Not Null | Total base units added to inventory |
| unit_cost | Numeric(10,4) | Not Null | Cost per base unit (immutable snapshot) |
| notes | Text | Nullable | Purchase notes |
| created_at | DateTime | Not Null | Creation timestamp |

**Note**: No `updated_at` - purchases are immutable.

**Relationships**:
- `product`: Many-to-One with MaterialProduct
- `supplier`: Many-to-One with Supplier

**Indexes**:
- `idx_material_purchase_product` on product_id
- `idx_material_purchase_supplier` on supplier_id
- `idx_material_purchase_date` on purchase_date

**Constraints**:
- `ck_material_purchase_packages_positive`: packages_purchased > 0
- `ck_material_purchase_price_non_negative`: package_price >= 0
- `ck_material_purchase_units_positive`: units_added > 0
- `ck_material_purchase_unit_cost_non_negative`: unit_cost >= 0

---

### MaterialConsumption

Assembly consumption record with full denormalized snapshot.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | PK, auto | Primary key |
| uuid | String(36) | Unique, Not Null | UUID identifier |
| assembly_run_id | Integer | FK, Not Null | Parent AssemblyRun |
| product_id | Integer | FK, Nullable | MaterialProduct consumed (ref only) |
| quantity_consumed | Float | Not Null | Base units consumed |
| unit_cost | Numeric(10,4) | Not Null | Cost per base unit at consumption |
| total_cost | Numeric(10,4) | Not Null | Total cost (quantity * unit_cost) |
| product_name | String(200) | Not Null | Snapshot: product name |
| material_name | String(200) | Not Null | Snapshot: material name |
| subcategory_name | String(100) | Not Null | Snapshot: subcategory name |
| category_name | String(100) | Not Null | Snapshot: category name |
| supplier_name | String(200) | Nullable | Snapshot: supplier name |
| created_at | DateTime | Not Null | Creation timestamp |

**Note**: No `updated_at` - consumption records are immutable snapshots.

**Relationships**:
- `assembly_run`: Many-to-One with AssemblyRun (existing table)
- `product`: Many-to-One with MaterialProduct (nullable for historical reference)

**Indexes**:
- `idx_material_consumption_assembly_run` on assembly_run_id
- `idx_material_consumption_product` on product_id

**Constraints**:
- `ck_material_consumption_quantity_positive`: quantity_consumed > 0
- `ck_material_consumption_cost_non_negative`: total_cost >= 0

---

## Composition Model Extension

The existing `Composition` model needs extension for material support:

### New Columns

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| material_unit_id | Integer | FK, Nullable | Specific MaterialUnit assignment |
| material_id | Integer | FK, Nullable | Generic Material placeholder |

### Updated XOR Constraint

Replace `ck_composition_exactly_one_component` with 5-way XOR:

```sql
(finished_unit_id IS NOT NULL AND finished_good_id IS NULL AND packaging_product_id IS NULL AND material_unit_id IS NULL AND material_id IS NULL) OR
(finished_unit_id IS NULL AND finished_good_id IS NOT NULL AND packaging_product_id IS NULL AND material_unit_id IS NULL AND material_id IS NULL) OR
(finished_unit_id IS NULL AND finished_good_id IS NULL AND packaging_product_id IS NOT NULL AND material_unit_id IS NULL AND material_id IS NULL) OR
(finished_unit_id IS NULL AND finished_good_id IS NULL AND packaging_product_id IS NULL AND material_unit_id IS NOT NULL AND material_id IS NULL) OR
(finished_unit_id IS NULL AND finished_good_id IS NULL AND packaging_product_id IS NULL AND material_unit_id IS NULL AND material_id IS NOT NULL)
```

### New Relationships

```python
material_unit_component = relationship("MaterialUnit", foreign_keys=[material_unit_id], lazy="joined")
material_component = relationship("Material", foreign_keys=[material_id], lazy="joined")
```

---

## State Transitions

### MaterialProduct Inventory States

```
[New Product] → current_inventory = 0
      │
      ▼ (Purchase recorded)
[Has Inventory] → current_inventory > 0, weighted_avg_cost calculated
      │
      ├──▶ (Assembly consumes) → current_inventory decreases
      │
      ├──▶ (Purchase adds) → current_inventory increases, weighted_avg_cost recalculated
      │
      └──▶ (Manual adjustment) → current_inventory updated, cost unchanged
```

### Generic Material Resolution

```
[Generic Placeholder] → Composition.material_id set, is_generic = True
      │
      ▼ (During assembly recording)
[Resolution Required] → UI shows dropdown per unresolved material
      │
      ▼ (User selects specific product)
[Resolved] → MaterialConsumption created with selected product
```

---

## Validation Rules

### Material Hierarchy
- Category cannot be deleted if it has subcategories
- Subcategory cannot be deleted if it has materials
- Material cannot be deleted if it has products with inventory > 0
- Material cannot be deleted if used in any Composition

### Purchases
- Package quantity must be positive
- Package price must be non-negative
- Units added calculated from package_quantity * quantity_in_base_units

### Assembly
- All generic material placeholders must be resolved before save
- Inventory must be sufficient for all material consumptions
- Consumption records created atomically with inventory decrements

### Unit Conversion
- Linear units (feet, yards, inches) → stored as inches
- Area units (square feet, square inches) → stored as square inches
- "Each" items → no conversion needed
