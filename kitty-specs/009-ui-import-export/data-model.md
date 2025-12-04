# Data Model: v3.0 Import/Export Schema

**Feature**: 009-ui-import-export
**Version**: 3.0
**Date**: 2025-12-04

## Overview

This document defines the JSON structure for bake-tracker data import/export. Version 3.0 reflects schema changes from Features 001-008.

## JSON Structure

```json
{
  "version": "3.0",
  "exported_at": "2025-12-04T10:30:00Z",
  "application": "bake-tracker",
  "unit_conversions": [...],
  "ingredients": [...],
  "variants": [...],
  "purchases": [...],
  "pantry_items": [...],
  "recipes": [...],
  "finished_units": [...],
  "finished_goods": [...],
  "compositions": [...],
  "packages": [...],
  "package_finished_goods": [...],
  "recipients": [...],
  "events": [...],
  "event_recipient_packages": [...],
  "production_records": [...]
}
```

## Entity Definitions

### 1. unit_conversions

Unit conversion factors between purchase and recipe units.

```json
{
  "ingredient_slug": "all_purpose_flour",
  "from_unit": "lb",
  "to_unit": "cup",
  "factor": 3.6
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ingredient_slug` | string | Yes | Reference to ingredient |
| `from_unit` | string | Yes | Source unit |
| `to_unit` | string | Yes | Target unit |
| `factor` | decimal | Yes | Conversion multiplier |

### 2. ingredients

Generic ingredient definitions (not brand-specific).

```json
{
  "name": "All-Purpose Flour",
  "slug": "all_purpose_flour",
  "category": "Flour",
  "recipe_unit": "cup",
  "description": "Standard all-purpose wheat flour",
  "density_g_per_ml": 0.507,
  "notes": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Display name |
| `slug` | string | Yes | Unique identifier (lowercase, underscores) |
| `category` | string | Yes | Category (Flour, Sugar, Dairy, etc.) |
| `recipe_unit` | string | Yes | Unit used in recipes |
| `description` | string | No | Description |
| `density_g_per_ml` | decimal | No | Density for volume/weight conversion |
| `notes` | string | No | User notes |

### 3. variants

Brand-specific variants of ingredients.

```json
{
  "ingredient_slug": "all_purpose_flour",
  "brand": "King Arthur",
  "package_size": "5 lb bag",
  "package_type": "bag",
  "purchase_unit": "lb",
  "purchase_quantity": 5.0,
  "upc_code": "071012000012",
  "is_preferred": true,
  "notes": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ingredient_slug` | string | Yes | Reference to ingredient |
| `brand` | string | Yes | Brand name |
| `package_size` | string | No | Human-readable package size |
| `package_type` | string | No | Package type (bag, box, jar) |
| `purchase_unit` | string | Yes | Unit when purchased |
| `purchase_quantity` | decimal | Yes | Quantity per package |
| `upc_code` | string | No | UPC barcode |
| `is_preferred` | boolean | No | Preferred variant for shopping lists |
| `notes` | string | No | User notes |

### 4. purchases

Purchase history for cost tracking.

```json
{
  "ingredient_slug": "all_purpose_flour",
  "variant_brand": "King Arthur",
  "purchase_date": "2025-11-15",
  "quantity": 2,
  "unit_price": 8.99,
  "store": "Costco",
  "notes": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ingredient_slug` | string | Yes | Reference to ingredient |
| `variant_brand` | string | Yes | Reference to variant (with ingredient_slug) |
| `purchase_date` | date | Yes | Date purchased |
| `quantity` | integer | Yes | Number of packages |
| `unit_price` | decimal | Yes | Price per package |
| `store` | string | No | Store name |
| `notes` | string | No | User notes |

### 5. pantry_items

Current inventory with FIFO lots.

```json
{
  "ingredient_slug": "all_purpose_flour",
  "variant_brand": "King Arthur",
  "quantity": 4.5,
  "unit": "lb",
  "acquisition_date": "2025-11-15",
  "expiration_date": "2026-06-15",
  "unit_cost": 1.80,
  "notes": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ingredient_slug` | string | Yes | Reference to ingredient |
| `variant_brand` | string | Yes | Reference to variant |
| `quantity` | decimal | Yes | Current quantity |
| `unit` | string | Yes | Unit of measure |
| `acquisition_date` | date | Yes | Date acquired (for FIFO ordering) |
| `expiration_date` | date | No | Expiration date |
| `unit_cost` | decimal | No | Cost per unit |
| `notes` | string | No | User notes |

### 6. recipes

Recipe definitions with ingredients.

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
  "notes": null,
  "ingredients": [
    {
      "ingredient_slug": "all_purpose_flour",
      "quantity": 2.25,
      "unit": "cup",
      "notes": "sifted"
    }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Recipe name |
| `slug` | string | Yes | Unique identifier |
| `category` | string | Yes | Category (Cookies, Cakes, etc.) |
| `description` | string | No | Description |
| `instructions` | text | No | Cooking instructions |
| `prep_time_minutes` | integer | No | Prep time |
| `cook_time_minutes` | integer | No | Cook time |
| `yield_quantity` | decimal | No | Yield amount |
| `yield_unit` | string | No | Yield unit |
| `source` | string | No | Recipe source |
| `notes` | string | No | User notes |
| `ingredients` | array | Yes | Recipe ingredients (embedded) |

### 7. finished_units

Yield definitions for recipes (how many items per batch).

```json
{
  "recipe_slug": "chocolate_chip_cookies",
  "display_name": "Chocolate Chip Cookie",
  "yield_mode": "discrete_count",
  "items_per_batch": 24,
  "item_unit": "cookie",
  "category": "Cookies",
  "notes": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `recipe_slug` | string | Yes | Reference to recipe |
| `display_name` | string | Yes | Display name for the finished item |
| `yield_mode` | string | Yes | "discrete_count" or "batch_portion" |
| `items_per_batch` | integer | Conditional | Items per batch (if discrete_count) |
| `item_unit` | string | Conditional | Unit name (if discrete_count) |
| `batch_percentage` | decimal | Conditional | Portion of batch (if batch_portion) |
| `category` | string | No | Category |
| `notes` | string | No | User notes |

### 8. finished_goods

Composite finished products.

```json
{
  "name": "Holiday Cookie Box",
  "slug": "holiday_cookie_box",
  "category": "Gift Items",
  "description": "Assorted holiday cookies",
  "notes": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Product name |
| `slug` | string | Yes | Unique identifier |
| `category` | string | No | Category |
| `description` | string | No | Description |
| `notes` | string | No | User notes |

### 9. compositions

Links finished units to finished goods (what goes in each product).

```json
{
  "finished_good_slug": "holiday_cookie_box",
  "finished_unit_slug": "chocolate_chip_cookies",
  "component_quantity": 6,
  "notes": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `finished_good_slug` | string | Yes | Reference to finished good |
| `finished_unit_slug` | string | Yes | Reference to finished unit |
| `component_quantity` | integer | Yes | Quantity of this item |
| `notes` | string | No | User notes |

### 10. packages

Gift package definitions.

```json
{
  "name": "Holiday Gift Box - Large",
  "slug": "holiday_gift_box_large",
  "is_template": false,
  "description": "Large gift box with assorted treats",
  "notes": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Package name |
| `slug` | string | Yes | Unique identifier |
| `is_template` | boolean | No | Whether this is a template |
| `description` | string | No | Description |
| `notes` | string | No | User notes |

### 11. package_finished_goods

Links finished goods to packages.

```json
{
  "package_slug": "holiday_gift_box_large",
  "finished_good_slug": "holiday_cookie_box",
  "quantity": 1
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `package_slug` | string | Yes | Reference to package |
| `finished_good_slug` | string | Yes | Reference to finished good |
| `quantity` | integer | Yes | Quantity |

### 12. recipients

Gift recipients.

```json
{
  "name": "Mom",
  "household": "Parents",
  "address": "123 Main St",
  "notes": "Loves chocolate"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Recipient name |
| `household` | string | No | Household grouping |
| `address` | string | No | Delivery address |
| `notes` | string | No | User notes |

### 13. events

Holiday/occasion events.

```json
{
  "name": "Christmas 2025",
  "slug": "christmas_2025",
  "event_date": "2025-12-25",
  "description": "Christmas gift giving",
  "notes": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Event name |
| `slug` | string | Yes | Unique identifier |
| `event_date` | date | No | Event date |
| `description` | string | No | Description |
| `notes` | string | No | User notes |

### 14. event_recipient_packages

Package assignments for events (includes Feature 008 status fields).

```json
{
  "event_slug": "christmas_2025",
  "recipient_name": "Mom",
  "package_slug": "holiday_gift_box_large",
  "quantity": 1,
  "status": "pending",
  "delivered_to": null,
  "notes": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_slug` | string | Yes | Reference to event |
| `recipient_name` | string | Yes | Reference to recipient |
| `package_slug` | string | Yes | Reference to package |
| `quantity` | integer | Yes | Number of this package |
| `status` | string | No | "pending", "assembled", "delivered" |
| `delivered_to` | string | No | Delivery confirmation |
| `notes` | string | No | User notes |

### 15. production_records

Batch production records with FIFO cost capture (Feature 008).

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
| `event_slug` | string | Yes | Reference to event |
| `recipe_slug` | string | Yes | Reference to recipe |
| `batches` | integer | Yes | Number of batches produced |
| `produced_at` | datetime | Yes | Production timestamp |
| `actual_cost` | decimal | Yes | Actual FIFO cost |
| `notes` | string | No | User notes |

## Import Dependency Order

Entities must be imported in this order for referential integrity:

1. `unit_conversions`
2. `ingredients`
3. `variants`
4. `purchases`
5. `pantry_items`
6. `recipes`
7. `finished_units`
8. `finished_goods`
9. `compositions`
10. `packages`
11. `package_finished_goods`
12. `recipients`
13. `events`
14. `event_recipient_packages`
15. `production_records`

## v2.0 Compatibility

When importing v2.0 files:

| v2.0 Field | v3.0 Mapping | Notes |
|------------|--------------|-------|
| `bundles` | `compositions` | Restructure required |
| `packages.bundles[]` | `package_finished_goods` | Relationship changed |
| Missing `status` | Default to "pending" | New field |
| Missing `finished_units` | Skip | Not in v2.0 |
| Missing `production_records` | Skip | Not in v2.0 |

Detection: If `version` field is missing or < "3.0", treat as v2.0 format.
