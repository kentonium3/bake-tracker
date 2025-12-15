# Data Model (Discovery Draft)

## Entities

### Entity: Product

- **Description**: Brand-specific product representing a purchasable package of an ingredient
- **Attributes**:
  - `id` (Integer, PK) - Auto-generated primary key
  - `uuid` (String) - Universal unique identifier for future distributed scenarios
  - `ingredient_id` (Integer, FK) - Reference to parent Ingredient
  - `brand` (String, 200) - Brand name (e.g., "King Arthur")
  - `package_size` (String, 100) - Human-readable size (e.g., "5 lb bag")
  - `package_type` (String, 50) - Package format (bag, box, jar, etc.)
  - ~~`purchase_unit`~~ `package_unit` (String, 50, required) - **RENAMED** Unit of measure for package contents
  - ~~`purchase_quantity`~~ `package_unit_quantity` (Float, required) - **RENAMED** Quantity per package
  - `upc_code` (String, 20) - UPC barcode (legacy)
  - `gtin` (String, 20) - GS1 GTIN (preferred over upc_code)
  - `supplier` (String, 200) - Where to buy
  - `supplier_sku` (String, 100) - Supplier's product code
  - `preferred` (Boolean) - Is this the preferred product for this ingredient?
  - `notes` (Text) - Additional notes
  - `date_added` (DateTime) - Creation timestamp
  - `last_modified` (DateTime) - Last modification timestamp
- **Identifiers**: `id` (PK), `uuid` (unique), `gtin` (unique if present)
- **Lifecycle Notes**: Created when user adds a product; updated via forms; deleted cascades from ingredient

### Entity: InventoryItem

- **Description**: FIFO lot tracking current inventory quantities by product (already correctly named)
- **Attributes**:
  - `id` (Integer, PK) - Auto-generated primary key
  - `uuid` (String) - Universal unique identifier
  - `product_id` (Integer, FK) - Reference to Product
  - `quantity` (Float, required) - Current quantity in package units
  - `unit` (String, 50, required) - Unit of measure
  - `acquisition_date` (Date, required) - Date acquired (for FIFO ordering)
  - `expiration_date` (Date) - Optional expiration date
  - `unit_cost` (Float) - Cost per unit at acquisition
  - `notes` (Text) - Additional notes
- **Identifiers**: `id` (PK), `uuid` (unique)
- **Lifecycle Notes**: Created on purchase; quantity decremented on consumption (FIFO); deleted when quantity reaches zero

## Relationships

| Source | Relation | Target | Cardinality | Notes |
|--------|----------|--------|-------------|-------|
| Product | belongs_to | Ingredient | N:1 | Multiple products per ingredient |
| InventoryItem | belongs_to | Product | N:1 | Multiple lots per product (FIFO) |
| Product | has_many | Purchase | 1:N | Purchase history for price tracking |
| Product | has_many | InventoryItem | 1:N | Current inventory lots |

## Schema Changes Summary

### Renamed Fields (Product model)

| Old Name | New Name | Type | Notes |
|----------|----------|------|-------|
| `purchase_unit` | `package_unit` | String(50) | Unit of measure for package contents |
| `purchase_quantity` | `package_unit_quantity` | Float | Quantity per package |

### Unchanged Entities

- **InventoryItem**: Already correctly named (not `PantryItem`)
- **All other models**: No terminology changes required

## Validation & Governance

- **Data quality requirements**:
  - `package_unit` required, non-empty
  - `package_unit_quantity` required, must be > 0
- **Compliance considerations**: N/A for this refactor
- **Source of truth**: SQLAlchemy models in `src/models/`

## Import/Export Field Mapping

### Products (v3.4)

```json
{
  "ingredient_slug": "all_purpose_flour",
  "brand": "King Arthur",
  "package_size": "5 lb bag",
  "package_type": "bag",
  "package_unit": "lb",           // Renamed from purchase_unit
  "package_unit_quantity": 5.0,   // Renamed from purchase_quantity
  "upc_code": "071012000012",
  "is_preferred": true,
  "notes": "Premium quality flour"
}
```
