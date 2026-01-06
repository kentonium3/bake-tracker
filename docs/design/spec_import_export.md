# Import/Export Specification for Bake Tracker

**Version:** 4.0
**Status:** Current

> **NOTE**: This application only accepts v4.0 format files. Older format versions
> are no longer supported. Export your data using the current version before importing.

## Changelog

### v4.0 (2026-01-06 - Feature 040)
- **Breaking**: v3.5 compatibility removed - only v4.0 files accepted
- **Changed**: Recipe schema redesigned for F037 (yield modes, variants, template/snapshot)
  - Added `yield_mode` field: "fixed" or "scaled"
  - Added `base_yield` and `scaling_factor` fields
  - Changed `ingredients` to `base_ingredients` with `is_base` flag
  - Added `variants` array for recipe variations linked to finished units
- **Changed**: Event schema updated for F039 Planning Workspace
  - Added `output_mode` field: "bulk_count", "bundled", or "packaged"
  - EventAssemblyTarget required when output_mode="bundled"
  - EventProductionTarget required when output_mode="bulk_count"
- **Added**: BT Mobile purchase import workflow (`import_type: "purchases"`)
  - UPC-based product matching
  - Unknown UPC resolution flow
  - Auto-creates Purchase + InventoryItem records
- **Added**: BT Mobile inventory update workflow (`import_type: "inventory_updates"`)
  - Percentage-based inventory corrections
  - FIFO inventory item selection
  - Creates InventoryDepletion records
- **Changed**: Function names updated: `*_v3()` → `*_v4()`

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
  "version": "4.0",
  "exported_at": "2026-01-06T10:30:00Z",
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
| `version` | string | **Yes** | Must be "4.0" |
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

**Purpose**: Recipe definitions with yield modes, base ingredients, and optional variants (F037).

**Schema** (v4.0):

```json
{
  "name": "Sugar Cookie",
  "slug": "sugar_cookie",
  "category": "Cookies",
  "description": "Classic sugar cookie base with variants",
  "instructions": "1. Cream butter and sugar...",
  "prep_time_minutes": 15,
  "cook_time_minutes": 12,
  "yield_mode": "scaled",
  "base_yield": 48,
  "scaling_factor": 1.0,
  "yield_unit": "cookies",
  "source": "Family recipe",
  "notes": "Best when slightly underbaked",
  "base_ingredients": [
    {
      "ingredient_slug": "all_purpose_flour",
      "quantity": 2.0,
      "unit": "cup",
      "is_base": true,
      "notes": "sifted"
    }
  ],
  "variants": [
    {
      "name": "Chocolate Chip",
      "finished_unit_slug": "chocolate_chip_cookie",
      "ingredient_changes": [
        {
          "action": "add",
          "ingredient_slug": "chocolate_chips_semi_sweet",
          "quantity": 0.5,
          "unit": "cup"
        }
      ]
    },
    {
      "name": "Plain",
      "finished_unit_slug": "plain_sugar_cookie",
      "ingredient_changes": []
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
| `yield_mode` | string | **Yes** | "fixed" or "scaled" |
| `base_yield` | integer | Conditional | Base yield quantity (required if yield_mode="scaled") |
| `scaling_factor` | decimal | No | Scaling multiplier (default 1.0) |
| `yield_unit` | string | No | Yield unit (e.g., "cookies", "servings") |
| `source` | string | No | Recipe source |
| `notes` | string | No | User notes |
| `base_ingredients` | array | **Yes** | Base recipe ingredients |
| `variants` | array | No | Recipe variants linked to finished units |
| `components` | array | No | Sub-recipes used in this recipe (nested recipes) |

**Yield Mode Values**:
- **fixed**: Recipe produces a fixed quantity regardless of ingredient amounts
- **scaled**: Recipe yield scales proportionally with ingredient amounts

**Recipe Base Ingredient Sub-Schema**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ingredient_slug` | string | **Yes** | Reference to ingredient (must be L2/leaf ingredient) |
| `quantity` | decimal | **Yes** | Amount needed |
| `unit` | string | **Yes** | Measurement unit |
| `is_base` | boolean | No | True for base ingredients (default true) |
| `notes` | string | No | Prep notes (sifted, melted, etc.) |

**Recipe Variant Sub-Schema** (F037):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | **Yes** | Variant name (e.g., "Chocolate Chip") |
| `finished_unit_slug` | string | **Yes** | Reference to finished unit |
| `ingredient_changes` | array | **Yes** | Changes from base recipe (can be empty) |

**Variant Ingredient Change Sub-Schema**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | string | **Yes** | "add", "remove", or "modify" |
| `ingredient_slug` | string | **Yes** | Reference to ingredient |
| `quantity` | decimal | Conditional | Amount (required for add/modify) |
| `unit` | string | Conditional | Unit (required for add/modify) |

**Recipe Component Sub-Schema** (nested recipes):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `recipe_name` | string | **Yes** | Name of the component recipe |
| `quantity` | decimal | **Yes** | Batch multiplier (must be > 0) |
| `notes` | string | No | Usage notes for this component |

**Recipe Validation Rules**:
- `yield_mode` must be "fixed" or "scaled"
- `base_yield` required if yield_mode="scaled"
- All `ingredient_slug` values must reference existing L2 (leaf) ingredients
- All `finished_unit_slug` values must reference existing FinishedUnits
- `ingredient_changes.action` must be "add", "remove", or "modify"
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

**Purpose**: Holiday/occasion events with output mode configuration (F039).

**Schema** (v4.0):

```json
{
  "name": "Christmas 2025",
  "slug": "christmas_2025",
  "event_date": "2025-12-25",
  "year": 2025,
  "output_mode": "bundled",
  "notes": "Annual Christmas gift giving"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | **Yes** | Event name |
| `slug` | string | **Yes** | Unique identifier |
| `event_date` | date | **Yes** | Event date (ISO 8601) |
| `year` | integer | **Yes** | Event year |
| `output_mode` | string | **Yes** | "bulk_count", "bundled", or "packaged" |
| `notes` | string | No | User notes |

**Output Mode Values** (F039):
- **bulk_count**: Production-focused - track batches produced for the event
- **bundled**: Assembly-focused - track finished goods assembled for the event
- **packaged**: Package-focused - track packages assigned to recipients

**Output Mode Validation**:
- If `output_mode="bundled"`, the event should have `event_assembly_targets`
- If `output_mode="bulk_count"`, the event should have `event_production_targets`
- If `output_mode="packaged"`, the event should have `event_recipient_packages`

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
  "version": "4.0",
  "exported_at": "2026-01-06T00:00:00Z",
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
| `version` | string | **Yes** | Must be "4.0" |
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

1. `version` field must be present and equal to "4.0"
2. If version is missing or not "4.0", import is rejected with error:
   > "Unsupported file version: [version]. This application only supports v4.0 format."

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
| Wrong version | "Unsupported file version: [X]. This application only supports v4.0 format. Please export a new backup from a current version." |
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
  "version": "4.0",
  "exported_at": "2026-01-06T10:30:00Z",
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
      "yield_mode": "scaled",
      "base_yield": 48,
      "scaling_factor": 1.0,
      "yield_unit": "cookies",
      "base_ingredients": [
        {
          "ingredient_slug": "all_purpose_flour",
          "quantity": 2.25,
          "unit": "cup",
          "is_base": true
        },
        {
          "ingredient_slug": "chocolate_chips_semi_sweet",
          "quantity": 2.0,
          "unit": "cup",
          "is_base": true
        }
      ],
      "variants": []
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
      "year": 2025,
      "output_mode": "packaged"
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

## Appendix D: Coordinated Export System

The coordinated export system provides individual entity files with a manifest for database backup, migration, and integrity verification.

### D.1 Coordinated Export Manifest

**Service**: `src.services.coordinated_export_service`
**Function**: `export_complete(output_dir, create_zip=False)`

The manifest file (`manifest.json`) coordinates the export set:

```json
{
  "version": "1.0",
  "export_date": "2025-12-24T12:00:00Z",
  "source": "bake-tracker v0.6.0",
  "files": [
    {
      "filename": "01_suppliers.json",
      "entity_type": "suppliers",
      "record_count": 5,
      "sha256": "abc123...",
      "dependencies": [],
      "import_order": 1
    },
    {
      "filename": "02_ingredients.json",
      "entity_type": "ingredients",
      "record_count": 343,
      "sha256": "def456...",
      "dependencies": [],
      "import_order": 2
    }
  ]
}
```

### D.2 Entity Export Files

Each entity exports to its own file with FK resolution fields (both ID and slug/name):

| File | Entity | Dependencies | Import Order |
|------|--------|--------------|--------------|
| `01_suppliers.json` | Supplier | None | 1 |
| `02_ingredients.json` | Ingredient | None | 2 |
| `03_products.json` | Product | ingredients, suppliers | 3 |
| `04_purchases.json` | Purchase | products, suppliers | 4 |
| `05_inventory_items.json` | InventoryItem | products, purchases | 5 |
| `06_recipes.json` | Recipe + RecipeIngredient + RecipeComponent | ingredients | 6 |

### D.3 Entity File Format

Each entity file includes metadata and records:

```json
{
  "entity_type": "products",
  "export_date": "2025-12-24T12:00:00Z",
  "record_count": 152,
  "records": [
    {
      "id": 42,
      "uuid": "abc123...",
      "ingredient_id": 15,
      "ingredient_slug": "all_purpose_flour",
      "brand": "King Arthur",
      "product_name": "Unbleached All-Purpose Flour",
      "preferred_supplier_id": 3,
      "preferred_supplier_name": "Costco"
    }
  ]
}
```

---

## Appendix E: Denormalized View Exports

Denormalized views provide AI-friendly exports with context fields for external augmentation workflows.

### E.1 Overview

**Service**: `src.services.denormalized_export_service`

Views eliminate FK lookups by including related entity fields directly. Each view includes a `_meta` section documenting which fields are editable vs readonly for import.

### E.2 Products View

**Function**: `export_products_view(output_path)`
**Output**: `view_products.json`

Contains products with ingredient, supplier, purchase, and inventory context:

```json
{
  "view_type": "products",
  "export_date": "2025-12-24T12:00:00Z",
  "record_count": 152,
  "_meta": {
    "editable_fields": ["brand", "product_name", "package_size", "package_type",
                        "package_unit", "package_unit_quantity", "upc_code", "gtin",
                        "notes", "preferred", "is_hidden"],
    "readonly_fields": ["id", "uuid", "ingredient_id", "ingredient_slug",
                        "ingredient_name", "ingredient_category", "preferred_supplier_id",
                        "preferred_supplier_name", "last_purchase_price",
                        "last_purchase_date", "inventory_quantity"]
  },
  "records": [
    {
      "id": 42,
      "uuid": "abc123...",
      "ingredient_slug": "all_purpose_flour",
      "ingredient_name": "All-Purpose Flour",
      "ingredient_category": "Flours & Meals",
      "brand": "King Arthur",
      "product_name": "Unbleached All-Purpose Flour",
      "package_unit": "lb",
      "package_unit_quantity": 5.0,
      "preferred_supplier_name": "Costco",
      "last_purchase_price": 6.99,
      "last_purchase_date": "2025-11-15",
      "inventory_quantity": 4.5
    }
  ]
}
```

### E.3 Inventory View

**Function**: `export_inventory_view(output_path)`
**Output**: `view_inventory.json`

Contains inventory items with product and purchase context:

```json
{
  "view_type": "inventory",
  "export_date": "2025-12-24T12:00:00Z",
  "record_count": 180,
  "_meta": {
    "editable_fields": ["quantity", "location", "expiration_date", "notes"],
    "readonly_fields": ["id", "uuid", "product_id", "purchase_id", "product_name",
                        "brand", "ingredient_name", "unit_cost", "purchase_date"]
  },
  "records": [...]
}
```

### E.4 Purchases View

**Function**: `export_purchases_view(output_path)`
**Output**: `view_purchases.json`

Contains purchases with product and supplier context:

```json
{
  "view_type": "purchases",
  "export_date": "2025-12-24T12:00:00Z",
  "record_count": 156,
  "_meta": {
    "editable_fields": ["unit_price", "quantity_purchased", "notes"],
    "readonly_fields": ["id", "uuid", "product_id", "supplier_id", "product_name",
                        "brand", "ingredient_name", "supplier_name", "purchase_date"]
  },
  "records": [...]
}
```

### E.5 Export All Views

**Function**: `export_all_views(output_dir)`

Exports all views to a directory in a single operation.

---

## Appendix F: Enhanced Import Service

The enhanced import service supports importing denormalized views back with FK resolution, merge modes, and error handling.

### F.1 Overview

**Service**: `src.services.enhanced_import_service`
**Function**: `import_view(file_path, mode='merge', dry_run=False, skip_on_error=False)`

### F.2 Import Modes

| Mode | Behavior |
|------|----------|
| `merge` | Update existing records (by UUID), add new records |
| `skip_existing` | Add new records only, skip records that exist |

### F.3 FK Resolution

The enhanced import resolves foreign keys by slug/name rather than ID:

- `ingredient_slug` → resolves to `ingredient_id`
- `supplier_name` → resolves to `supplier_id`
- `product_slug` (ingredient_slug + brand + product_name) → resolves to `product_id`

### F.4 Dry Run Mode

With `dry_run=True`, the import validates all records and reports what would change without modifying the database.

### F.5 Skip-on-Error Mode

With `skip_on_error=True`, valid records are imported while invalid records are logged to a timestamped file (`import_skipped_YYYY-MM-DD_HHMMSS.json`).

### F.6 Usage Example

```python
from src.services.enhanced_import_service import import_view

# Preview changes without modifying DB
result = import_view("view_purchases_augmented.json", mode="merge", dry_run=True)
print(result.get_summary())

# Import with merge (update existing + add new)
result = import_view("view_purchases_augmented.json", mode="merge")
print(f"Imported: {result.successful}, Skipped: {result.skipped}")

# Import valid records, log failures
result = import_view("view_products.json", mode="merge", skip_on_error=True)
if result.skipped_records_path:
    print(f"Skipped records logged to: {result.skipped_records_path}")
```

---

## Appendix G: AI Augmentation Workflow

The denormalized views are designed for AI-assisted data augmentation workflows.

### G.1 Workflow Pattern

1. **Export**: Use `export_*_view()` to create denormalized JSON
2. **Augment**: AI assistant reviews and enriches data (e.g., price research)
3. **Save**: AI saves augmented file (e.g., `view_purchases_augmented.json`)
4. **Import**: Use `import_view()` with `mode='merge'` to apply changes

### G.2 Editable vs Readonly Fields

The `_meta` section in each view defines:
- **editable_fields**: Can be modified by AI and imported back
- **readonly_fields**: Context only, ignored on import

### G.3 Example: Price Enrichment

```python
# 1. Export purchases for price research
from src.services.denormalized_export_service import export_purchases_view
export_purchases_view("view_purchases.json")

# 2. AI enriches unit_price field in view_purchases_augmented.json

# 3. Import enriched prices
from src.services.enhanced_import_service import import_view
result = import_view("view_purchases_augmented.json", mode="merge")
```

---

## Appendix H: Entity Dependency Graph

```
Level 0 (No dependencies):
  - Supplier
  - Ingredient
  - Recipient

Level 1 (Single dependency):
  - Product → Ingredient, Supplier (optional)
  - Recipe → Ingredient (via RecipeIngredient)
  - FinishedGood (standalone)
  - Package (standalone)

Level 2 (Multiple dependencies):
  - Purchase → Product, Supplier
  - FinishedUnit → Recipe
  - Event (standalone)

Level 3 (Complex dependencies):
  - InventoryItem → Product, Purchase
  - Composition → FinishedGood, FinishedUnit
  - EventRecipientPackage → Event, Recipient, Package
  - EventProductionTarget → Event, Recipe
  - EventAssemblyTarget → Event, FinishedGood

Level 4 (Transactional):
  - ProductionRun → Event (optional), Recipe
  - AssemblyRun → Event (optional), FinishedGood
```

---

## Appendix I: BT Mobile Purchase Import (F040)

The BT Mobile purchase import workflow enables importing purchases from a mobile app using UPC barcode scanning.

### I.1 Purchase Import JSON Schema

```json
{
  "schema_version": "4.0",
  "import_type": "purchases",
  "created_at": "2026-01-06T14:30:00Z",
  "source": "bt_mobile",
  "supplier": "Costco Waltham MA",
  "purchases": [
    {
      "upc": "051000127952",
      "gtin": "00051000127952",
      "scanned_at": "2026-01-06T14:15:23Z",
      "unit_price": 7.99,
      "quantity_purchased": 1.0,
      "supplier": "Costco Waltham MA",
      "notes": "Weekly shopping"
    }
  ]
}
```

### I.2 Purchase Import Header Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | **Yes** | Must be "4.0" |
| `import_type` | string | **Yes** | Must be "purchases" |
| `created_at` | datetime | **Yes** | ISO 8601 timestamp |
| `source` | string | **Yes** | Source application (e.g., "bt_mobile") |
| `supplier` | string | No | Default supplier for all purchases |
| `purchases` | array | **Yes** | Array of purchase records |

### I.3 Purchase Record Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `upc` | string | **Yes** | UPC barcode (used for product matching) |
| `gtin` | string | No | GTIN barcode (GS1 standard) |
| `scanned_at` | datetime | **Yes** | When the barcode was scanned |
| `unit_price` | decimal | **Yes** | Price per package |
| `quantity_purchased` | decimal | **Yes** | Number of packages |
| `supplier` | string | No | Supplier name (overrides top-level default) |
| `notes` | string | No | User notes |

### I.4 UPC Matching Algorithm

1. For each purchase record, attempt to match `upc` against `products.upc_code`
2. If match found: Create Purchase + InventoryItem records
3. If no match: Collect for Unknown UPC Resolution

### I.5 Unknown UPC Resolution

When a UPC cannot be matched, the user is prompted to:

1. **Map to existing product**: Select from product dropdown
2. **Create new product**: Fill out product form (ingredient, brand, name, etc.)
3. **Skip this purchase**: Ignore and continue

Resolution auto-assigns the UPC to the selected/created product for future imports.

### I.6 Service Function

```python
from src.services.import_export_service import import_purchases_from_bt_mobile

result = import_purchases_from_bt_mobile("purchases_20260106.json")
print(f"Imported: {result.success_count}, Errors: {result.error_count}")
```

### I.7 CLI Usage

```bash
bake-tracker import-purchases purchases_20260106_143000.json
```

---

## Appendix J: BT Mobile Inventory Update Import (F040)

The BT Mobile inventory update workflow enables percentage-based inventory corrections from physical counts.

### J.1 Inventory Update JSON Schema

```json
{
  "schema_version": "4.0",
  "import_type": "inventory_updates",
  "created_at": "2026-01-06T09:15:00Z",
  "source": "bt_mobile",
  "inventory_updates": [
    {
      "upc": "051000127952",
      "gtin": "00051000127952",
      "scanned_at": "2026-01-06T09:10:12Z",
      "remaining_percentage": 30,
      "update_method": "percentage_based",
      "notes": "Pre-production check"
    }
  ]
}
```

### J.2 Inventory Update Header Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | **Yes** | Must be "4.0" |
| `import_type` | string | **Yes** | Must be "inventory_updates" |
| `created_at` | datetime | **Yes** | ISO 8601 timestamp |
| `source` | string | **Yes** | Source application (e.g., "bt_mobile") |
| `inventory_updates` | array | **Yes** | Array of update records |

### J.3 Inventory Update Record Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `upc` | string | **Yes** | UPC barcode (used for product matching) |
| `gtin` | string | No | GTIN barcode (GS1 standard) |
| `scanned_at` | datetime | **Yes** | When the inventory was checked |
| `remaining_percentage` | integer | **Yes** | Percentage of original quantity remaining (0-100) |
| `update_method` | string | **Yes** | Must be "percentage_based" |
| `notes` | string | No | User notes |

### J.4 Percentage Calculation Algorithm

1. Lookup Product by UPC
2. Find active inventory items (current_quantity > 0) in FIFO order
3. For each item:
   - Get original quantity from linked Purchase
   - Calculate target: `original * (percentage / 100)`
   - Calculate adjustment: `target - current`
4. Create InventoryDepletion record and update current_quantity

**Example**:
- Original purchase: 25 lbs flour
- Current inventory: 18 lbs (user has been using it)
- User scans: "30% remaining"
- Target: 25 × 0.30 = 7.5 lbs
- Adjustment: 7.5 - 18 = -10.5 lbs
- System depletes 10.5 lbs and creates audit record

### J.5 Multiple Inventory Items

When multiple inventory items exist for the same product:
- Default behavior: Apply to oldest (FIFO)
- Future enhancement: Prompt user to select which item

### J.6 Service Function

```python
from src.services.import_export_service import import_inventory_updates_from_bt_mobile

result = import_inventory_updates_from_bt_mobile("inventory_update_20260106.json")
print(f"Updated: {result.success_count}, Errors: {result.error_count}")
```

### J.7 CLI Usage

```bash
bake-tracker import-inventory-update inventory_update_20260106_091500.json

# Auto-detect import type
bake-tracker import-bt-mobile <file.json>
```

---

**Document Status**: Current
**Version**: 4.0
**Last Updated**: 2026-01-06
