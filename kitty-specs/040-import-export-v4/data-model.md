# Data Model: Import/Export v4.0 Upgrade

**Feature**: 040-import-export-v4
**Date**: 2026-01-06

## Overview

This document describes the data structures for v4.0 import/export, including JSON schemas for the three workflows and their mapping to database models.

## Part 1: Core Schema Entities

### Recipe (v4.0 Export Schema)

```json
{
  "name": "Sugar Cookie",
  "slug": "sugar_cookie",
  "category": "Cookies",
  "source": "Family recipe",
  "yield_quantity": 48,
  "yield_unit": "cookies",
  "yield_description": "2-inch cookies",
  "estimated_time_minutes": 45,
  "notes": "Best slightly underbaked",
  "is_archived": false,
  "is_production_ready": true,
  "base_recipe_slug": null,
  "variant_name": null,
  "ingredients": [
    {
      "ingredient_slug": "all_purpose_flour",
      "quantity": 2.0,
      "unit": "cup",
      "notes": "sifted"
    }
  ],
  "components": [],
  "finished_units": [
    {
      "slug": "sugar_cookie_unit",
      "name": "Sugar Cookie",
      "yield_mode": "DISCRETE_COUNT",
      "unit_yield_quantity": 1,
      "unit_yield_unit": "cookie"
    }
  ]
}
```

**Model Mapping**:
| JSON Field | Model.Field | Notes |
|------------|-------------|-------|
| base_recipe_slug | Recipe.base_recipe_id | Resolved via slug lookup |
| variant_name | Recipe.variant_name | Direct mapping |
| is_production_ready | Recipe.is_production_ready | F037 field |
| finished_units | FinishedUnit[] | Related via recipe_id |
| finished_units[].yield_mode | FinishedUnit.yield_mode | Enum: DISCRETE_COUNT, BATCH_PORTION, WEIGHT_BASED |

### Event (v4.0 Export Schema)

```json
{
  "name": "Christmas 2025",
  "slug": "christmas_2025",
  "event_date": "2025-12-25",
  "year": 2025,
  "output_mode": "bundled",
  "notes": "Annual holiday gifts",
  "event_assembly_targets": [
    {
      "finished_good_slug": "holiday_gift_bag",
      "target_quantity": 50,
      "notes": "6 cookies + 3 brownies"
    }
  ],
  "event_production_targets": []
}
```

**Model Mapping**:
| JSON Field | Model.Field | Notes |
|------------|-------------|-------|
| output_mode | Event.output_mode | Enum: bulk_count, bundled, packaged |
| event_assembly_targets | EventAssemblyTarget[] | Required if output_mode=bundled |
| event_production_targets | EventProductionTarget[] | Required if output_mode=bulk_count |

## Part 2: BT Mobile Purchase Import

### Purchase Import JSON Schema

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

**Processing Flow**:
```
Purchase JSON Record
    |
    v
UPC Lookup (Product.upc_code)
    |
    +-- Match Found --> Create Purchase + InventoryItem
    |
    +-- No Match --> Queue for Resolution Dialog
                         |
                         +-- Map to Existing --> Update Product.upc_code, Create Purchase
                         +-- Create New --> Create Product, Create Purchase
                         +-- Skip --> Log and continue
```

**Created Records**:
| Model | Fields Set |
|-------|------------|
| Purchase | product_id, supplier_id, purchase_date, unit_price, quantity_purchased, notes |
| InventoryItem | product_id, purchase_id, current_quantity (=quantity_purchased), purchase_date |

## Part 3: BT Mobile Inventory Update

### Inventory Update JSON Schema

```json
{
  "schema_version": "4.0",
  "import_type": "inventory_updates",
  "created_at": "2026-01-06T09:15:00Z",
  "source": "bt_mobile",
  "inventory_updates": [
    {
      "upc": "051000127952",
      "scanned_at": "2026-01-06T09:10:12Z",
      "remaining_percentage": 30,
      "update_method": "percentage_based",
      "notes": "Pre-production check"
    }
  ]
}
```

**Processing Flow**:
```
Inventory Update Record
    |
    v
UPC Lookup (Product.upc_code)
    |
    +-- No Match --> Error: "Product not found for UPC"
    |
    v
Find Active InventoryItems (current_quantity > 0, FIFO order)
    |
    +-- None Found --> Warning: "No active inventory"
    |
    v
Calculate Adjustment:
    original = inventory_item.purchase.quantity_purchased
    target = original * (percentage / 100)
    adjustment = target - current_quantity
    |
    v
Apply Adjustment:
    - Create InventoryDepletion record
    - Update InventoryItem.current_quantity
```

**Calculation Example**:
```
Original (from Purchase): 25 lbs
Current inventory: 18 lbs
User reports: 30% remaining

target = 25 * 0.30 = 7.5 lbs
adjustment = 7.5 - 18 = -10.5 lbs

Result: Deplete 10.5 lbs, new quantity = 7.5 lbs
```

**Created/Modified Records**:
| Model | Action | Fields |
|-------|--------|--------|
| InventoryDepletion | CREATE | inventory_item_id, quantity_depleted, depletion_date, depletion_reason="physical_count_correction", notes |
| InventoryItem | UPDATE | current_quantity |

## Entity Relationships

```
Recipe (1) ----< RecipeIngredient (N) >---- Ingredient (1)
   |
   +----< FinishedUnit (N)
   |          |
   |          +---- yield_mode
   |
   +---- base_recipe_id (self-referential for variants)

Event (1) ----< EventAssemblyTarget (N) >---- FinishedGood (1)
   |
   +----< EventProductionTarget (N) >---- Recipe (1)
   |
   +---- output_mode

Product (1) ----< Purchase (N) ----< InventoryItem (N)
   |                                       |
   +---- upc_code                          +---- current_quantity
   +---- gtin                              +---- purchase_id (for original qty)

InventoryItem (1) ----< InventoryDepletion (N)
```

## Validation Rules

### Recipe Import
1. `base_recipe_slug` must reference existing Recipe or be null
2. Import order: base recipes first, then variants
3. `ingredients[].ingredient_slug` must reference existing L2 Ingredient
4. `finished_units[].yield_mode` must be valid enum value

### Event Import
1. `output_mode` must be "bulk_count", "bundled", or "packaged"
2. If `output_mode="bundled"`, `event_assembly_targets` should be non-empty
3. If `output_mode="bulk_count"`, `event_production_targets` should be non-empty
4. `finished_good_slug` must reference existing FinishedGood
5. `recipe_name` must reference existing Recipe

### Purchase Import
1. `upc` must be non-empty string
2. `unit_price` must be positive decimal
3. `quantity_purchased` must be positive decimal
4. `supplier` (if present) is resolved via Supplier.name or created

### Inventory Update
1. `upc` must match existing Product.upc_code
2. `remaining_percentage` must be 0-100 integer
3. Target calculation must not result in negative inventory
4. InventoryItem must have linked Purchase for percentage calculation
