# Import/Export Specification for Bake Tracker

**Version:** 3.5
**Status:** Current

> **NOTE**: This application only accepts v3.5 format files. Older format versions
> are no longer supported. Export your data using the current version before importing.

## Changelog

### v3.5 (2025-12-19 - Feature 023)
- **Added**: `product_name` field on products - enables product variant differentiation (e.g., "70% Cacao" vs "85% Cacao")
- **Changed**: Product unique constraint now includes product_name: `(ingredient_slug, brand, product_name, package_size, package_unit)`
- **Added**: Full schemas for `production_runs`, `assembly_runs`, `event_production_targets`, `event_assembly_targets` (previously undocumented)
- **Note**: USDA FoodData Central naming conventions recommended for ingredient slugs (e.g., `extract_vanilla` not `vanilla_extract`)

### v3.4 (2025-12-16)
- **Fixed**: `purchases` field names corrected to match code: `purchased_at`, `quantity_purchased`, `unit_cost`, `total_cost`, `supplier`
- **Fixed**: `inventory_items` field names corrected to match code: `purchase_date` (was `acquisition_date`), `location` added, removed unused `unit` and `unit_cost`
- **Fixed**: Documentation version references updated to 3.4

### v3.3 (2025-12-14 - Feature 019)
- **Removed**: `unit_conversions` entity - no longer needed
- **Removed**: `recipe_unit` field from ingredients - unit conversion uses 4-field density model
- **Changed**: Unit conversion now uses ingredient density fields (density_volume_value, density_volume_unit, density_weight_value, density_weight_unit)

### v3.2 (2025-12-11 - Feature 016)
- **Added**: `event_production_targets` entity for event production planning
- **Added**: `event_assembly_targets` entity for event assembly planning
- **Added**: `event_id` field on ProductionRun and AssemblyRun records
- **Added**: `fulfillment_status` field on EventRecipientPackage (pending/ready/delivered)
- **Changed**: Export uses "products" key (aliased from internal Product model)

### v3.1 (2025-12-08 - Feature 014)
- **Added**: Production and assembly run export with event linkage support

### v3.0 (2025-12-04)
- **Breaking**: v2.0 compatibility removed - only v3.0 files accepted
- **Added**: `version: "3.0"` header required in all export files
- **Added**: `exported_at` timestamp with ISO 8601 format
- **Added**: `finished_units` entity (replaces embedded recipe yield)
- **Added**: `compositions` entity (replaces v2.0 `bundles`)
- **Added**: `package_finished_goods` entity (explicit junction table)
- **Added**: `production_records` entity (Feature 008)
- **Added**: `status` field on event assignments (pending/assembled/delivered)
- **Changed**: Import requires explicit mode selection: Merge or Replace
- **Changed**: All entities use slug-based references for foreign keys
- **Removed**: `bundles` entity (replaced by `compositions`)

### v2.0 (2025-11-08)
- See `docs/archive/import_export_specification_v2.md`

## Purpose

This specification defines the import/export format for the Bake Tracker application. The primary goals are:

1. **Data Backup**: Allow users to backup and restore complete application state
2. **Testing**: Load comprehensive test data for development and QA
3. **Data Portability**: Enable data migration between installations

## Overview

The Bake Tracker uses an **Ingredient/Product architecture** that separates:
- **Generic Ingredients** (e.g., "All-Purpose Flour") - used in recipes
- **Brand Products** (e.g., "King Arthur All-Purpose Flour") - purchased and tracked in inventory

This separation allows recipes to reference generic ingredients while tracking specific brands in inventory.

## JSON Structure

The export format is a single JSON file with a required header and entity arrays:

```json
{
  "version": "3.5",
  "exported_at": "2025-12-20T10:30:00Z",
  "application": "bake-tracker",
  "ingredients": [...],
  "products": [...],
  "purchases": [...],
  "inventory_items": [...],
  "recipes": [...],
  "finished_units": [...],
  "finished_goods": [...],
  "compositions": [...],
  "packages": [...],
  "package_finished_goods": [...],
  "recipients": [...],
  "events": [...],
  "event_recipient_packages": [...],
  "event_production_targets": [...],
  "event_assembly_targets": [...],
  "production_records": [...],
  "production_runs": [...],
  "assembly_runs": [...]
}
```

### Header Fields (Required)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | **Yes** | Must be "3.5" |
| `exported_at` | string | **Yes** | ISO 8601 timestamp with 'Z' suffix |
| `application` | string | **Yes** | Must be "bake-tracker" |

All entity arrays are optional, but when present, they must follow the dependency order for successful import.

---

## Entity Definitions

### 1. ingredients

**Purpose**: Define generic ingredient types used in recipes.

**Schema**:

```json
{
  "display_name": "All-Purpose Flour",
  "slug": "all_purpose_flour",
  "category": "Flour",
  "description": "Standard all-purpose wheat flour",
  "density_volume_value": 1.0,
  "density_volume_unit": "cup",
  "density_weight_value": 4.25,
  "density_weight_unit": "oz",
  "notes": "Store in airtight container",
  "is_packaging": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `display_name` | string | **Yes** | Display name (max 200 chars) |
| `slug` | string | **Yes** | Unique identifier (lowercase, underscores, max 100 chars) |
| `category` | string | **Yes** | Category (see Appendix A) |
| `description` | string | No | Detailed description |
| `density_volume_value` | decimal | No | Volume amount for density conversion |
| `density_volume_unit` | string | No | Volume unit (cup, ml, tbsp, tsp, l) |
| `density_weight_value` | decimal | No | Weight amount for density conversion |
| `density_weight_unit` | string | No | Weight unit (oz, g, lb, kg) |
| `notes` | string | No | User notes |
| `is_packaging` | boolean | No | True if packaging material, false for food |

**Notes**:
- `slug` is the **primary identifier** used in all foreign key references
- Use lowercase with underscores (e.g., `semi_sweet_chocolate_chips`)
- **USDA FoodData Central naming conventions recommended**: Primary descriptor first (e.g., `extract_vanilla` not `vanilla_extract`, `chocolate_chips_dark` not `dark_chocolate_chips`)
- Density fields must be all-or-nothing (all 4 or none)
- Density enables volume ↔ weight conversion (e.g., "1 cup = 4.25 oz")

---

### 2. products

**Purpose**: Define brand-specific products for purchase and inventory tracking.

**Schema**:

```json
{
  "ingredient_slug": "all_purpose_flour",
  "brand": "King Arthur",
  "product_name": "Unbleached All-Purpose Flour",
  "package_size": "5 lb bag",
  "package_type": "bag",
  "package_unit": "lb",
  "package_unit_quantity": 5.0,
  "upc_code": "071012000012",
  "gtin": "00071012000012",
  "is_preferred": true,
  "notes": "Premium quality flour"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ingredient_slug` | string | **Yes** | Reference to ingredient |
| `brand` | string | **Yes** | Brand name (max 200 chars) |
| `product_name` | string | No | Product variant name (e.g., "70% Cacao", "Organic") - enables differentiation of products with same packaging |
| `package_size` | string | No | Human-readable package size |
| `package_type` | string | No | Package type (bag, box, jar, etc.) |
| `package_unit` | string | **Yes** | Unit of measure for package contents |
| `package_unit_quantity` | decimal | **Yes** | Amount in package (e.g., 25 for a 25 lb bag) |
| `upc_code` | string | No | UPC barcode (legacy field) |
| `gtin` | string | No | GTIN barcode (GS1 standard, preferred) |
| `is_preferred` | boolean | No | Preferred product for shopping lists |
| `notes` | string | No | User notes |

**Notes**:
- Primary key is composite: `(ingredient_slug, brand, product_name, package_unit_quantity, package_unit)`
- `product_name` allows differentiation of variants (e.g., Lindt "70% Cacao" vs "85% Cacao" both in 3.5oz bars)
- Multiple brands per ingredient are supported
- `gtin` is preferred over `upc_code` for barcode scanning (supports mobile inventory workflow)

---

### 3. purchases

**Purpose**: Track historical purchases for price history.

**Schema**:

```json
{
  "ingredient_slug": "all_purpose_flour",
  "product_brand": "King Arthur",
  "purchased_at": "2025-11-15T00:00:00Z",
  "quantity_purchased": 2,
  "unit_cost": 8.99,
  "total_cost": 17.98,
  "supplier": "Costco",
  "notes": "Stock up purchase"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ingredient_slug` | string | **Yes** | Reference to ingredient |
| `product_brand` | string | **Yes** | Reference to product (with ingredient_slug) |
| `purchased_at` | datetime | **Yes** | Date purchased (ISO 8601 with 'Z' suffix) |
| `quantity_purchased` | integer | **Yes** | Number of packages |
| `unit_cost` | decimal | **Yes** | Price per package |
| `total_cost` | decimal | No | Total purchase cost |
| `supplier` | string | No | Store/supplier name |
| `notes` | string | No | User notes |

---

### 4. inventory_items

**Purpose**: Current inventory with FIFO lots.

**Schema**:

```json
{
  "ingredient_slug": "all_purpose_flour",
  "product_brand": "King Arthur",
  "quantity": 4.5,
  "purchase_date": "2025-11-15",
  "expiration_date": "2026-06-15",
  "location": "Pantry",
  "notes": "From Costco bulk purchase"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ingredient_slug` | string | **Yes** | Reference to ingredient |
| `product_brand` | string | **Yes** | Reference to product |
| `quantity` | decimal | **Yes** | Current quantity (in product's package units) |
| `purchase_date` | date | No | Date acquired (for FIFO ordering) |
| `expiration_date` | date | No | Expiration date |
| `location` | string | No | Storage location (e.g., "Pantry", "Freezer") |
| `notes` | string | No | User notes |

**Notes**:
- Each inventory item represents a specific purchase/batch (FIFO lot)
- Multiple inventory items can exist for same product (different purchase dates)
- Quantity is tracked in the product's `package_unit` (e.g., lb, oz)

---

### 5. recipes

**Purpose**: Recipe definitions with embedded ingredient list.

**Schema**:

```json
{
  "name": "Chocolate Chip Cookies",
  "slug": "chocolate_chip_cookies",
  "category": "Cookies",
  "description": "Classic chocolate chip cookies",
  "instructions": "1. Cream butter and sugar...",
  "prep_time_minutes": 15,
  "cook_time_minutes": 12,
  "yield_quantity": 24,
  "yield_unit": "cookies",
  "source": "Family recipe",
  "notes": "Best when slightly underbaked",
  "ingredients": [
    {
      "ingredient_slug": "all_purpose_flour",
      "quantity": 2.25,
      "unit": "cup",
      "notes": "sifted"
    }
  ],
  "components": [
    {
      "recipe_name": "Vanilla Extract Base",
      "quantity": 1.0,
      "notes": "Use homemade if available"
    }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | **Yes** | Recipe name (max 200 chars) |
| `slug` | string | **Yes** | Unique identifier |
| `category` | string | **Yes** | Category (Cookies, Cakes, etc.) |
| `description` | string | No | Description |
| `instructions` | text | No | Cooking instructions |
| `prep_time_minutes` | integer | No | Prep time |
| `cook_time_minutes` | integer | No | Cook time |
| `yield_quantity` | decimal | No | Yield amount |
| `yield_unit` | string | No | Yield unit |
| `source` | string | No | Recipe source |
| `notes` | string | No | User notes |
| `ingredients` | array | **Yes** | Recipe ingredients (embedded) |
| `components` | array | No | Sub-recipes used in this recipe (nested recipes) |

**Recipe Ingredient Sub-Schema**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ingredient_slug` | string | **Yes** | Reference to ingredient |
| `quantity` | decimal | **Yes** | Amount needed |
| `unit` | string | **Yes** | Measurement unit |
| `notes` | string | No | Prep notes (sifted, melted, etc.) |

**Recipe Component Sub-Schema** (nested recipes):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `recipe_name` | string | **Yes** | Name of the component recipe |
| `quantity` | decimal | **Yes** | Batch multiplier (must be > 0) |
| `notes` | string | No | Usage notes for this component |

**Recipe Component Validation Rules**:
- Component recipes must exist in the same import file or already exist in the database
- Circular references are rejected (Recipe A cannot contain Recipe B if B contains A)
- Maximum nesting depth: 3 levels
- A recipe cannot be added as a component of itself

---

### 6. finished_units

**Purpose**: Yield definitions for recipes (how many items per batch).

**Schema**:

```json
{
  "slug": "chocolate_chip_cookie",
  "recipe_slug": "chocolate_chip_cookies",
  "display_name": "Chocolate Chip Cookie",
  "yield_mode": "discrete_count",
  "items_per_batch": 24,
  "item_unit": "cookie",
  "category": "Cookies",
  "notes": "Standard size cookies"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | **Yes** | Unique identifier |
| `recipe_slug` | string | **Yes** | Reference to recipe |
| `display_name` | string | **Yes** | Display name for the finished item |
| `yield_mode` | string | **Yes** | "discrete_count" or "batch_portion" |
| `items_per_batch` | integer | Conditional | Items per batch (if discrete_count) |
| `item_unit` | string | Conditional | Unit name (if discrete_count) |
| `batch_percentage` | decimal | Conditional | Portion of batch (if batch_portion) |
| `category` | string | No | Category |
| `notes` | string | No | User notes |

**Yield Mode Values**:
- **discrete_count**: Recipe produces countable items (cookies, truffles)
- **batch_portion**: Recipe produces bulk quantity (cakes, fudge)

---

### 7. finished_goods

**Purpose**: Composite finished products (assemblies containing finished units).

**Schema**:

```json
{
  "display_name": "Holiday Cookie Box",
  "slug": "holiday_cookie_box",
  "category": "Gift Items",
  "description": "Assorted holiday cookies",
  "notes": "Mix of 3 cookie types"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `display_name` | string | **Yes** | Product name |
| `slug` | string | **Yes** | Unique identifier |
| `category` | string | No | Category |
| `description` | string | No | Description |
| `notes` | string | No | User notes |

---

### 8. compositions

**Purpose**: Links finished units (or sub-assemblies) to finished goods.

**Schema**:

```json
{
  "assembly_slug": "holiday_cookie_box",
  "component_type": "finished_unit",
  "component_slug": "chocolate_chip_cookie",
  "component_quantity": 6,
  "sort_order": 1,
  "notes": "First layer"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `assembly_slug` | string | **Yes** | Reference to finished good (parent) |
| `component_type` | string | **Yes** | "finished_unit" or "finished_good" |
| `component_slug` | string | **Yes** | Reference to component |
| `component_quantity` | integer | **Yes** | Quantity of this component |
| `sort_order` | integer | No | Display order (default 0) |
| `notes` | string | No | Assembly notes |

**Notes**:
- Replaces v2.0 "bundles" concept
- Supports recursive assemblies (finished goods containing other finished goods)

---

### 9. packages

**Purpose**: Gift package definitions.

**Schema**:

```json
{
  "name": "Holiday Gift Box - Large",
  "slug": "holiday_gift_box_large",
  "is_template": false,
  "description": "Large gift box with assorted treats",
  "notes": "For close family members"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | **Yes** | Package name |
| `slug` | string | **Yes** | Unique identifier |
| `is_template` | boolean | No | Whether this is a template |
| `description` | string | No | Description |
| `notes` | string | No | User notes |

---

### 10. package_finished_goods

**Purpose**: Links finished goods to packages (package contents).

**Schema**:

```json
{
  "package_slug": "holiday_gift_box_large",
  "finished_good_slug": "holiday_cookie_box",
  "quantity": 1
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `package_slug` | string | **Yes** | Reference to package |
| `finished_good_slug` | string | **Yes** | Reference to finished good |
| `quantity` | integer | **Yes** | Quantity |

---

### 11. recipients

**Purpose**: Gift recipients.

**Schema**:

```json
{
  "name": "Mom",
  "household": "Parents",
  "address": "123 Main St, Anytown, USA",
  "notes": "Loves chocolate, allergic to nuts"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | **Yes** | Recipient name (unique) |
| `household` | string | No | Household grouping |
| `address` | string | No | Delivery address |
| `notes` | string | No | User notes (preferences, allergies) |

---

### 12. events

**Purpose**: Holiday/occasion events.

**Schema**:

```json
{
  "name": "Christmas 2025",
  "slug": "christmas_2025",
  "event_date": "2025-12-25",
  "year": 2025,
  "notes": "Annual Christmas gift giving"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | **Yes** | Event name |
| `slug` | string | **Yes** | Unique identifier |
| `event_date` | date | **Yes** | Event date (ISO 8601) |
| `year` | integer | **Yes** | Event year |
| `notes` | string | No | User notes |

---

### 13. event_recipient_packages

**Purpose**: Package assignments for events with production status.

**Schema**:

```json
{
  "event_slug": "christmas_2025",
  "recipient_name": "Mom",
  "package_slug": "holiday_gift_box_large",
  "quantity": 1,
  "status": "pending",
  "delivered_to": null,
  "notes": "Deliver by Dec 23"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_slug` | string | **Yes** | Reference to event |
| `recipient_name` | string | **Yes** | Reference to recipient |
| `package_slug` | string | **Yes** | Reference to package |
| `quantity` | integer | **Yes** | Number of packages |
| `status` | string | No | "pending", "assembled", or "delivered" |
| `delivered_to` | string | No | Delivery confirmation |
| `notes` | string | No | User notes |

**Status Values**:
- **pending**: Not yet assembled (default)
- **assembled**: Package assembled, ready for delivery
- **delivered**: Package delivered to recipient

---

### 14. event_production_targets

**Purpose**: Define production targets for recipes within an event.

**Schema**:

```json
{
  "event_slug": "christmas_2025",
  "recipe_slug": "chocolate_chip_cookies",
  "target_batches": 3,
  "notes": "Need extra for unexpected guests"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_slug` | string | **Yes** | Reference to event |
| `recipe_slug` | string | **Yes** | Reference to recipe |
| `target_batches` | integer | **Yes** | Target number of batches to produce |
| `notes` | string | No | User notes |

**Notes**:
- Defines production goals for event planning
- Used to track progress toward event completion
- Primary key: `(event_slug, recipe_slug)`

---

### 15. event_assembly_targets

**Purpose**: Define assembly targets for finished goods within an event.

**Schema**:

```json
{
  "event_slug": "christmas_2025",
  "finished_good_slug": "holiday_cookie_box",
  "target_quantity": 15,
  "notes": "One per family plus extras"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_slug` | string | **Yes** | Reference to event |
| `finished_good_slug` | string | **Yes** | Reference to finished good |
| `target_quantity` | integer | **Yes** | Target number of units to assemble |
| `notes` | string | No | User notes |

**Notes**:
- Defines assembly goals for event planning
- Used to track progress toward event completion
- Primary key: `(event_slug, finished_good_slug)`

---

### 16. production_runs

**Purpose**: Track individual recipe production runs with FIFO cost capture and event linkage.

**Schema**:

```json
{
  "recipe_slug": "chocolate_chip_cookies",
  "event_slug": "christmas_2025",
  "batches_produced": 2,
  "units_produced": 96,
  "produced_at": "2025-12-20T14:30:00Z",
  "actual_cost": 12.50,
  "notes": "Double batch for extra gifts"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `recipe_slug` | string | **Yes** | Reference to recipe |
| `event_slug` | string | No | Reference to event (nullable - can produce without event) |
| `batches_produced` | integer | **Yes** | Number of batches produced |
| `units_produced` | integer | **Yes** | Total units produced (batches × items_per_batch) |
| `produced_at` | datetime | **Yes** | Production timestamp (ISO 8601 with 'Z') |
| `actual_cost` | decimal | **Yes** | Actual FIFO cost at production time |
| `notes` | string | No | User notes |

**Notes**:
- Captures actual production runs with FIFO cost
- Links production to events for progress tracking
- Multiple production runs can target same event
- Replaces older `production_records` concept (both supported for backward compatibility)

---

### 17. assembly_runs

**Purpose**: Track assembly of finished goods from finished units with cost capture and event linkage.

**Schema**:

```json
{
  "finished_good_slug": "holiday_cookie_box",
  "event_slug": "christmas_2025",
  "quantity_assembled": 15,
  "assembled_at": "2025-12-22T10:00:00Z",
  "actual_cost": 187.50,
  "notes": "All boxes completed"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `finished_good_slug` | string | **Yes** | Reference to finished good |
| `event_slug` | string | No | Reference to event (nullable - can assemble without event) |
| `quantity_assembled` | integer | **Yes** | Number of units assembled |
| `assembled_at` | datetime | **Yes** | Assembly timestamp (ISO 8601 with 'Z') |
| `actual_cost` | decimal | **Yes** | Actual cost based on consumed finished units |
| `notes` | string | No | User notes |

**Notes**:
- Captures assembly of finished goods from finished units
- Links assembly to events for progress tracking
- Cost calculated from FIFO costs of consumed finished units
- Multiple assembly runs can target same event

---

### 14. production_records (Legacy)

**Purpose**: Track historical batch production records (v3.0-3.4 format, maintained for backward compatibility).

**Note**: Newer exports use `production_runs` instead. Both are supported on import.

**Purpose**: Batch production records with FIFO cost capture.

**Schema**:

```json
{
  "event_slug": "christmas_2025",
  "recipe_slug": "chocolate_chip_cookies",
  "batches": 2,
  "produced_at": "2025-12-20T14:30:00Z",
  "actual_cost": 12.50,
  "notes": "Double batch for extra gifts"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_slug` | string | **Yes** | Reference to event |
| `recipe_slug` | string | **Yes** | Reference to recipe |
| `batches` | integer | **Yes** | Number of batches produced |
| `produced_at` | datetime | **Yes** | Production timestamp (ISO 8601 with 'Z') |
| `actual_cost` | decimal | **Yes** | Actual FIFO cost at production time |
| `notes` | string | No | User notes |

---

## Import Dependency Order

**CRITICAL**: Entities must be imported in this order for referential integrity.

1. `ingredients` - No dependencies
2. `products` - Requires: ingredients
3. `purchases` - Requires: products
4. `inventory_items` - Requires: products
5. `recipes` - Requires: ingredients
6. `finished_units` - Requires: recipes
7. `finished_goods` - No direct dependencies
8. `compositions` - Requires: finished_units, finished_goods
9. `packages` - No direct dependencies
10. `package_finished_goods` - Requires: packages, finished_goods
11. `recipients` - No dependencies
12. `events` - No direct dependencies
13. `event_recipient_packages` - Requires: events, recipients, packages
14. `event_production_targets` - Requires: events, recipes
15. `event_assembly_targets` - Requires: events, finished_goods
16. `production_runs` - Requires: recipes, events (optional)
17. `assembly_runs` - Requires: finished_goods, events (optional)
18. `production_records` - Requires: events, recipes (legacy - use production_runs)

**The import service processes arrays in this order automatically.**

---

## Catalog Import (Subset Format)

The **catalog import** is a streamlined import path for adding ingredients, products, and recipes without affecting transactional data (purchases, inventory, events, etc.). This is useful for expanding the ingredient catalog from external sources.

### Catalog Import JSON Structure

```json
{
  "version": "3.5",
  "exported_at": "2025-12-20T00:00:00Z",
  "application": "bake-tracker",
  "description": "Optional description of the catalog",
  "ingredients": [...],
  "products": [...],
  "recipes": [...]
}
```

### Catalog Import Header Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | **Yes** | Must be "3.5" |
| `exported_at` | string | No | ISO 8601 timestamp |
| `application` | string | No | Should be "bake-tracker" |
| `description` | string | No | Human-readable description |

### Supported Entities

Only these entities are supported in catalog import:

| Entity | Description |
|--------|-------------|
| `ingredients` | Generic ingredient definitions |
| `products` | Brand-specific products |
| `recipes` | Recipe definitions with ingredients |

### Catalog Import Modes

| Mode | Behavior |
|------|----------|
| **ADD_ONLY** | Create new records, skip existing (by slug) |
| **AUGMENT** | Create new records, update null fields on existing |

**AUGMENT mode field behavior:**
- **Protected fields** (never modified): `slug`, `display_name`, `id`, `date_added`, `category`
- **Augmentable fields** (updated only if current value is NULL): density fields, FoodOn ID, descriptions, notes

### Catalog Import Usage

```python
from src.services.catalog_import_service import import_catalog

# Add new ingredients only
result = import_catalog("catalog.json", mode="add", dry_run=False)

# Add new + fill in missing data on existing
result = import_catalog("catalog.json", mode="augment", dry_run=False)
```

---

## Import Modes

### Merge Mode (Default)

- Add new records that don't exist
- Skip records that match existing data (by unique key)
- Preserve all existing data
- Report skipped count in summary

**Use case**: Adding new recipes without affecting existing data

### Replace Mode

- Clear all existing data first
- Import all records from file
- **WARNING**: This deletes all existing data

**Use case**: Restoring from backup, fresh installation

---

## Validation Rules

### Header Validation

The import service first validates the header:

1. `version` field must be present and equal to "3.5"
2. If version is missing or not "3.5", import is rejected with error:
   > "Unsupported file version: [version]. This application only supports v3.5 format."

### Foreign Key Validation

All foreign key references are validated:

- `products.ingredient_slug` -> must exist in `ingredients`
- `purchases.(ingredient_slug, product_brand)` -> must exist in `products`
- `inventory_items.(ingredient_slug, product_brand)` -> must exist in `products`
- `recipes.ingredients[].ingredient_slug` -> must exist in `ingredients`
- `finished_units.recipe_slug` -> must exist in `recipes`
- `compositions.assembly_slug` -> must exist in `finished_goods`
- `compositions.component_slug` -> must exist in `finished_units` or `finished_goods`
- `package_finished_goods.package_slug` -> must exist in `packages`
- `package_finished_goods.finished_good_slug` -> must exist in `finished_goods`
- `event_recipient_packages.event_slug` -> must exist in `events`
- `event_recipient_packages.recipient_name` -> must exist in `recipients`
- `event_recipient_packages.package_slug` -> must exist in `packages`
- `production_records.event_slug` -> must exist in `events`
- `production_records.recipe_slug` -> must exist in `recipes`

### Duplicate Handling (Merge Mode)

By default in Merge mode:
- Existing records are **skipped** (identified by unique key/slug)
- Duplicate count is included in import summary
- No error is raised for duplicates

---

## Error Messages

All error messages are designed to be user-friendly (no stack traces):

| Scenario | Message |
|----------|---------|
| Wrong version | "Unsupported file version: [X]. This application only supports v3.5 format. Please export a new backup from a current version." |
| Invalid JSON | "The selected file is not valid JSON. Please select a valid backup file." |
| Missing entity | "[Entity type] '[name]' not found. It may be missing from the import file or listed in the wrong order." |
| File not readable | "Could not read file: [path]. Please check file permissions." |
| Write error | "Could not save to: [path]. Please check if the location is writable." |

---

## Usage

### Export via UI

1. Click **File > Export Data...**
2. Choose save location
3. Default filename: `bake-tracker-backup-YYYY-MM-DD.json`

### Import via UI

1. Click **File > Import Data...**
2. Select JSON file
3. Choose mode: **Merge** or **Replace**
4. If Replace: Confirm data deletion
5. Review summary on completion

### Import Result Summary

After import, you'll see a summary like:

```
Import Complete

ingredients: 12 imported, 2 skipped
products: 15 imported, 0 skipped
recipes: 8 imported, 1 skipped
finished_units: 8 imported, 0 skipped
finished_goods: 5 imported, 0 skipped
...

Total: 85 imported, 3 skipped, 0 errors
```

---

## Appendix A: Valid Categories

### Ingredient Categories

```
Flours & Meals, Sugars & Sweeteners, Fats & Oils, Dairy & Eggs,
Leaveners, Chocolate & Cocoa, Candies & Decorations, Nuts & Seeds,
Spices & Flavorings, Additives & Thickeners, Liquids, Fruits, Misc
```

### Recipe/Finished Good Categories

```
Cookies, Cakes, Candies, Bars, Brownies,
Breads, Pastries, Pies, Tarts, Other
```

---

## Appendix B: Valid Units

### Weight Units
```
oz, lb, g, kg
```

### Volume Units
```
tsp, tbsp, cup, ml, l, fl oz, pt, qt, gal
```

### Count Units
```
each, count, piece, dozen
```

### Package Types
```
bag, box, jar, bottle, can, packet, container, case
```

---

## Appendix C: Complete Example

```json
{
  "version": "3.5",
  "exported_at": "2025-12-20T10:30:00Z",
  "application": "bake-tracker",
  "ingredients": [
    {
      "display_name": "All-Purpose Flour",
      "slug": "all_purpose_flour",
      "category": "Flour",
      "density_volume_value": 1.0,
      "density_volume_unit": "cup",
      "density_weight_value": 4.25,
      "density_weight_unit": "oz"
    },
    {
      "display_name": "Semi-Sweet Chocolate Chips",
      "slug": "chocolate_chips_semi_sweet",
      "category": "Chocolate & Cocoa"
    }
  ],
  "products": [
    {
      "ingredient_slug": "all_purpose_flour",
      "brand": "King Arthur",
      "product_name": "Unbleached All-Purpose Flour",
      "package_size": "5 lb bag",
      "package_unit": "lb",
      "package_unit_quantity": 5.0,
      "gtin": "00071012000012",
      "is_preferred": true
    }
  ],
  "recipes": [
    {
      "name": "Classic Chocolate Chip Cookies",
      "slug": "classic_chocolate_chip_cookies",
      "category": "Cookies",
      "yield_quantity": 48,
      "yield_unit": "cookies",
      "ingredients": [
        {
          "ingredient_slug": "all_purpose_flour",
          "quantity": 2.25,
          "unit": "cup"
        },
        {
          "ingredient_slug": "chocolate_chips_semi_sweet",
          "quantity": 2.0,
          "unit": "cup"
        }
      ]
    }
  ],
  "finished_units": [
    {
      "slug": "chocolate_chip_cookie",
      "recipe_slug": "classic_chocolate_chip_cookies",
      "display_name": "Chocolate Chip Cookie",
      "yield_mode": "discrete_count",
      "items_per_batch": 48,
      "item_unit": "cookie",
      "category": "Cookies"
    }
  ],
  "finished_goods": [
    {
      "display_name": "Cookie Assortment Box",
      "slug": "cookie_assortment_box",
      "category": "Gift Items"
    }
  ],
  "compositions": [
    {
      "assembly_slug": "cookie_assortment_box",
      "component_type": "finished_unit",
      "component_slug": "chocolate_chip_cookie",
      "component_quantity": 12,
      "sort_order": 1
    }
  ],
  "packages": [
    {
      "name": "Standard Cookie Gift",
      "slug": "standard_cookie_gift",
      "is_template": true
    }
  ],
  "package_finished_goods": [
    {
      "package_slug": "standard_cookie_gift",
      "finished_good_slug": "cookie_assortment_box",
      "quantity": 1
    }
  ],
  "recipients": [
    {
      "name": "Mom",
      "household": "Parents",
      "notes": "Loves chocolate chip cookies"
    }
  ],
  "events": [
    {
      "name": "Christmas 2025",
      "slug": "christmas_2025",
      "event_date": "2025-12-25",
      "year": 2025
    }
  ],
  "event_recipient_packages": [
    {
      "event_slug": "christmas_2025",
      "recipient_name": "Mom",
      "package_slug": "standard_cookie_gift",
      "quantity": 1,
      "status": "pending"
    }
  ],
  "production_records": [
    {
      "event_slug": "christmas_2025",
      "recipe_slug": "classic_chocolate_chip_cookies",
      "batches": 2,
      "produced_at": "2025-12-20T14:30:00Z",
      "actual_cost": 15.75,
      "notes": "Double batch for gifts"
    }
  ]
}
```

---

## Appendix D: Future Enhancement Roadmap

> **Status**: PLANNED - Not yet implemented. This section documents requirements for future export/import enhancements.

### Overview

Future enhancements to support:
1. Coordinated export sets that can fully rebuild the database
2. AI-assisted augmentation workflows (price enrichment, purchase record creation)
3. Denormalized views optimized for external AI processing

### D.1 Coordinated Export Set with Manifest

Create a manifest file that coordinates export sets:

```json
{
  "manifest_version": "1.0",
  "export_id": "uuid-v4",
  "exported_at": "2025-12-24T12:00:00Z",
  "application": "bake-tracker",
  "app_version": "0.6.0",
  "schema_version": "3.5",
  "files": [
    {
      "filename": "01_suppliers.json",
      "entity_type": "suppliers",
      "record_count": 5,
      "checksum_sha256": "abc123...",
      "import_order": 1,
      "dependencies": []
    }
  ],
  "import_modes_supported": ["replace", "merge"]
}
```

**Entity Export Files:**

| File | Entity | Dependencies | Import Order |
|------|--------|--------------|--------------|
| `01_suppliers.json` | Supplier | None | 1 |
| `02_ingredients.json` | Ingredient | None | 2 |
| `03_products.json` | Product | ingredients, suppliers | 3 |
| `04_purchases.json` | Purchase | products, suppliers | 4 |
| `05_inventory_items.json` | InventoryItem | products, purchases | 5 |
| `06_recipes.json` | Recipe + RecipeIngredient | ingredients | 6 |
| `07_finished_units.json` | FinishedUnit | recipes | 7 |
| `08_finished_goods.json` | FinishedGood | None | 8 |
| `09_compositions.json` | Composition | finished_goods, finished_units | 9 |
| `10_packages.json` | Package | finished_goods | 10 |
| `11_recipients.json` | Recipient | None | 11 |
| `12_events.json` | Event + Targets | recipients, packages | 12 |
| `13_production_runs.json` | ProductionRun | events, recipes | 13 |
| `14_assembly_runs.json` | AssemblyRun | events, finished_goods | 14 |

### D.2 AI-Assisted Augmentation Workflows

**Use Cases:**

| Use Case | Input | AI Task | Output |
|----------|-------|---------|--------|
| Price enrichment | Products without prices | Look up current prices | Products with `suggested_price`, `price_source` |
| Purchase creation | Inventory without purchases | Generate purchase records | New purchase records |
| Ingredient matching | Raw product list | Match to canonical ingredients | Products with `ingredient_slug` |

**AI-Friendly Export Format (Denormalized):**

```json
{
  "purpose": "AI price enrichment",
  "instructions": "Research current retail price for each product",
  "products": [
    {
      "product_id": 42,
      "ingredient_name": "All-Purpose Flour",
      "brand": "King Arthur",
      "product_name": "Unbleached All-Purpose Flour",
      "package_size": "5 lb",
      "current_unit_price": null,
      "last_purchase_price": 6.99,
      "supplier_name": "Costco",
      "suggested_unit_price": null,
      "price_source": null
    }
  ]
}
```

### D.3 Denormalized View Exports

| View | Purpose | Contents |
|------|---------|----------|
| `view_products_complete.json` | Full product context | Product + Ingredient + Last purchase + Inventory |
| `view_inventory_status.json` | Current inventory | InventoryItem + Product + Ingredient + Purchase |
| `view_recipes_costed.json` | Recipes with costs | Recipe + Ingredients + Current costs |
| `view_shopping_needs.json` | Shopping requirements | Shortage analysis + Preferred products |

### D.4 Proposed API Functions

```python
# Coordinated export
def export_complete_set(output_dir: Path, include_transactional: bool = True) -> ExportManifest

# Denormalized view exports
def export_view(view_name: str, output_path: Path) -> ExportResult

# AI workflow exports
def export_for_ai_augmentation(workflow: str, output_path: Path) -> ExportResult

# AI augmentation import
def import_ai_augmentation(augmentation_file: Path) -> ImportResult

# Validation
def validate_export_set(manifest_path: Path) -> ValidationResult
```

### D.5 Entity Dependency Graph

```
Level 0 (No dependencies):
  - Supplier, Ingredient, Recipient, Unit

Level 1 (Single dependency):
  - Product → Ingredient, Supplier
  - Recipe → Ingredient
  - FinishedGood, Package (standalone)

Level 2 (Multiple dependencies):
  - Purchase → Product, Supplier
  - FinishedUnit → Recipe
  - Event (standalone but links many)

Level 3 (Complex dependencies):
  - InventoryItem → Product, Purchase
  - Composition → FinishedGood, FinishedUnit
  - EventRecipientPackage → Event, Recipient, Package

Level 4 (Transactional):
  - ProductionRun → Event, Recipe
  - AssemblyRun → Event, FinishedGood
```

### D.6 File Organization (Proposed)

```
exports/
├── manifest.json
├── 01_suppliers.json
├── 02_ingredients.json
├── ...
└── views/
    ├── products_complete.json
    └── inventory_status.json
└── ai/
    ├── products_for_pricing.json
    └── augmentation_response.json
```

---

**Document Status**: Current
**Version**: 3.5
**Last Updated**: 2025-12-29
