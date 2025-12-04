# Import/Export Specification for Bake Tracker

> **ARCHIVED** - This document has been superseded by v3.0 specification.
> See `docs/design/import_export_specification.md` for the current version.
> Archived: 2025-12-04

**Version:** 2.0
**Date:** 2025-11-08
**Status:** ARCHIVED - Superseded by v3.0

## Purpose

This specification defines the working import/export format for the Bake Tracker application. The primary goals are:

1. **Testing Efficiency**: Load comprehensive test data quickly for development
2. **AI Generation**: Enable AI tools to generate bulk recipe and ingredient data
3. **Data Augmentation**: Support AI-assisted expansion of the test dataset
4. **Data Portability**: Backup and restore complete application state

## Overview

The Bake Tracker uses an **Ingredient/Variant architecture** that separates:
- **Generic Ingredients** (e.g., "All-Purpose Flour") - used in recipes
- **Brand Variants** (e.g., "King Arthur All-Purpose Flour") - purchased and tracked in inventory

This separation allows recipes to reference generic ingredients while tracking specific brands in inventory.

## JSON Structure

The import/export format is a single JSON file containing multiple top-level arrays:

```json
{
  "ingredients": [...],
  "variants": [...],
  "purchases": [...],
  "pantry_items": [...],
  "unit_conversions": [...],
  "recipes": [...],
  "finished_goods": [...],
  "bundles": [...],
  "packages": [...],
  "recipients": [...],
  "events": [...]
}
```

All arrays are optional, but order matters for referential integrity (see Import Order section).

---

## 1. Ingredients

**Purpose**: Define generic ingredient types used in recipes.

**Schema**:

```json
{
  "name": "All-Purpose Flour",
  "slug": "all_purpose_flour",
  "category": "Flour",
  "recipe_unit": "cup",
  "description": "Standard all-purpose wheat flour",
  "notes": "Store in airtight container in cool, dry place",
  "density_g_per_ml": 0.507
}
```

**Field Specifications**:

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `name` | string | **Yes** | Max 200 chars | Display name (e.g., "All-Purpose Flour") |
| `slug` | string | **Yes** | Max 100 chars, lowercase, underscores | **Primary key** - must be unique |
| `category` | string | **Yes** | Valid category | See Appendix A for valid categories |
| `recipe_unit` | string | **Yes** | Valid unit | Default unit for recipes (cup, tsp, oz, etc.) |
| `description` | string | No | Max 500 chars | Detailed description |
| `notes` | string | No | Max 2000 chars | Storage instructions, substitutions |
| `density_g_per_ml` | number | No | > 0 | Density for volume-to-weight conversion |

**Important Notes**:
- `slug` is the **primary identifier** used in all foreign key references
- Use lowercase with underscores (e.g., `semi_sweet_chocolate_chips`)
- Recipes reference ingredients by slug, not by name

**Example**:

```json
{
  "name": "Semi-Sweet Chocolate Chips",
  "slug": "semi_sweet_chocolate_chips",
  "category": "Chocolate/Candies",
  "recipe_unit": "cup",
  "description": "Semi-sweet chocolate chips for baking"
}
```

---

## 2. Variants

**Purpose**: Define specific brand products that can be purchased and tracked in inventory.

**Schema**:

```json
{
  "ingredient_slug": "all_purpose_flour",
  "brand": "King Arthur",
  "package_size": "25 lb bag",
  "package_type": "bag",
  "purchase_unit": "lb",
  "purchase_quantity": 25.0,
  "preferred": true,
  "upc": "071012345678",
  "supplier": "Costco",
  "notes": "Premium quality, higher protein content"
}
```

**Field Specifications**:

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `ingredient_slug` | string | **Yes** | Must reference existing ingredient | Foreign key to ingredients |
| `brand` | string | **Yes** | Max 200 chars | Brand name (e.g., "King Arthur") |
| `package_size` | string | No | Max 100 chars | Human-readable size (e.g., "25 lb bag") |
| `package_type` | string | No | Valid type | bag, box, jar, bottle, can, etc. |
| `purchase_unit` | string | **Yes** | Valid unit | Unit for purchasing (lb, oz, kg, etc.) |
| `purchase_quantity` | number | **Yes** | > 0 | Quantity per package |
| `preferred` | boolean | No | true/false | Mark as preferred brand (default: false) |
| `upc` | string | No | Max 50 chars | UPC/barcode |
| `supplier` | string | No | Max 200 chars | Where to buy (Costco, Amazon, etc.) |
| `notes` | string | No | Max 2000 chars | Product-specific notes |

**Important Notes**:
- Primary key is the combination of `(ingredient_slug, brand)`
- This allows multiple brands per ingredient
- Purchases and pantry items reference variants by both fields

**Example**:

```json
{
  "ingredient_slug": "unsalted_butter",
  "brand": "Kirkland",
  "package_size": "4 sticks (1 lb)",
  "package_type": "box",
  "purchase_unit": "lb",
  "purchase_quantity": 1.0,
  "preferred": true,
  "supplier": "Costco",
  "notes": "Good quality, cheaper than name brands"
}
```

---

## 3. Purchases

**Purpose**: Track historical purchases for price history and inventory reconciliation.

**Schema**:

```json
{
  "variant_brand": "King Arthur",
  "ingredient_slug": "all_purpose_flour",
  "purchased_at": "2024-10-15T10:30:00",
  "unit_cost": 18.99,
  "quantity_purchased": 1.0,
  "total_cost": 18.99,
  "supplier": "Costco",
  "notes": "Stock up purchase"
}
```

**Field Specifications**:

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `variant_brand` | string | **Yes** | Must reference existing variant | Foreign key (with ingredient_slug) |
| `ingredient_slug` | string | **Yes** | Must reference existing variant | Foreign key (with variant_brand) |
| `purchased_at` | string | **Yes** | ISO 8601 format | Purchase timestamp (e.g., "2024-10-15T10:30:00") |
| `unit_cost` | number | **Yes** | >= 0 | Cost per package |
| `quantity_purchased` | number | **Yes** | > 0 | Number of packages purchased |
| `total_cost` | number | **Yes** | >= 0 | unit_cost × quantity_purchased |
| `supplier` | string | No | Max 200 chars | Where purchased |
| `notes` | string | No | Max 2000 chars | Purchase notes |

**Important Notes**:
- Tracks price history over time for cost analysis
- Supports FIFO inventory valuation
- `purchased_at` can be just a date if time is unknown

---

## 4. Pantry Items

**Purpose**: Current inventory of ingredients on hand.

**Schema**:

```json
{
  "variant_brand": "King Arthur",
  "ingredient_slug": "all_purpose_flour",
  "quantity": 1.5,
  "purchase_date": "2024-10-15",
  "location": "Main Pantry",
  "notes": "Half bag remaining, opened 2024-11-01"
}
```

**Field Specifications**:

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `variant_brand` | string | **Yes** | Must reference existing variant | Foreign key (with ingredient_slug) |
| `ingredient_slug` | string | **Yes** | Must reference existing variant | Foreign key (with variant_brand) |
| `quantity` | number | **Yes** | >= 0 | Quantity in purchase_unit from variant |
| `purchase_date` | string | **Yes** | ISO 8601 date | For FIFO tracking (e.g., "2024-10-15") |
| `location` | string | No | Max 200 chars | Storage location (Main Pantry, Freezer, etc.) |
| `notes` | string | No | Max 2000 chars | Condition notes, expiration, etc. |

**Important Notes**:
- Each pantry item represents a specific purchase/batch
- Multiple pantry items can exist for same variant (different purchase dates)
- Supports FIFO consumption tracking
- `quantity` is in the `purchase_unit` specified in the variant

---

## 5. Unit Conversions

**Purpose**: Define ingredient-specific conversion factors between units.

**Schema**:

```json
{
  "ingredient_slug": "all_purpose_flour",
  "from_unit": "lb",
  "from_quantity": 1.0,
  "to_unit": "cup",
  "to_quantity": 3.6,
  "notes": "Unsifted, spooned and leveled"
}
```

**Field Specifications**:

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `ingredient_slug` | string | **Yes** | Must reference existing ingredient | Foreign key |
| `from_unit` | string | **Yes** | Valid unit | Source unit |
| `from_quantity` | number | **Yes** | > 0 | Source quantity |
| `to_unit` | string | **Yes** | Valid unit | Target unit |
| `to_quantity` | number | **Yes** | > 0 | Target quantity |
| `notes` | string | No | Max 500 chars | Measurement method notes |

**Important Notes**:
- Enables conversion between purchase units (lb) and recipe units (cup)
- Ingredient-specific (flour vs sugar have different densities)
- System auto-creates reverse conversions

**Example**:

```json
{
  "ingredient_slug": "unsalted_butter",
  "from_unit": "lb",
  "from_quantity": 1.0,
  "to_unit": "cup",
  "to_quantity": 2.0,
  "notes": "4 sticks = 1 lb = 2 cups"
}
```

---

## 6. Recipes

**Purpose**: Define baking recipes with ingredient lists.

**Schema**:

```json
{
  "name": "Classic Chocolate Chip Cookies",
  "category": "Cookies",
  "source": "SG-Binder",
  "yield_quantity": 48.0,
  "yield_unit": "cookies",
  "yield_description": "2-inch cookies",
  "estimated_time_minutes": 45,
  "notes": "Family favorite recipe. Bake at 350°F for 10-12 minutes.",
  "ingredients": [
    {
      "ingredient_slug": "all_purpose_flour",
      "quantity": 2.25,
      "unit": "cup",
      "notes": "Spoon and level, don't pack"
    },
    {
      "ingredient_slug": "white_granulated_sugar",
      "quantity": 0.75,
      "unit": "cup"
    }
  ]
}
```

**Recipe Field Specifications**:

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `name` | string | **Yes** | Max 200 chars | Recipe name (must be unique) |
| `category` | string | **Yes** | Valid category | See Appendix A for categories |
| `source` | string | No | Max 500 chars | Recipe origin (cookbook, website, etc.) |
| `yield_quantity` | number | **Yes** | > 0 | Amount produced |
| `yield_unit` | string | **Yes** | Max 50 chars | cookies, cakes, servings, pieces, etc. |
| `yield_description` | string | No | Max 200 chars | Size details (e.g., "2-inch cookies") |
| `estimated_time_minutes` | integer | No | >= 0 | Total prep + bake time |
| `notes` | string | No | Max 2000 chars | Instructions, tips, temperature |
| `ingredients` | array | **Yes** | Min 1 item | Ingredient list |

**Recipe Ingredient Sub-Schema**:

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `ingredient_slug` | string | **Yes** | Must reference existing ingredient | Foreign key |
| `quantity` | number | **Yes** | > 0 | Amount needed |
| `unit` | string | **Yes** | Valid unit | Recipe measurement unit |
| `notes` | string | No | Max 500 chars | Prep notes (sifted, melted, room temp, etc.) |

**Important Notes**:
- Recipes reference **generic ingredients** (by slug), not specific brands
- This allows flexibility in choosing brands when baking
- System can check if any variant of the ingredient is available

---

## 7. Finished Goods

**Purpose**: Define products created from recipes for inventory tracking and gift planning.

**Schema**:

```json
{
  "name": "Chocolate Chip Cookie Dozen",
  "recipe_name": "Classic Chocolate Chip Cookies",
  "category": "Cookies",
  "yield_mode": "DISCRETE_COUNT",
  "items_per_batch": 48,
  "item_unit": "cookies",
  "notes": "Classic family recipe cookies"
}
```

**Field Specifications**:

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `name` | string | **Yes** | Max 200 chars | Finished good name (must be unique) |
| `recipe_name` | string | **Yes** | Must reference existing recipe | Foreign key |
| `category` | string | **Yes** | Valid category | Usually matches recipe category |
| `yield_mode` | string | **Yes** | DISCRETE_COUNT or CONTINUOUS | How the recipe yields products |
| `items_per_batch` | integer | Conditional | > 0 | Required if yield_mode=DISCRETE_COUNT |
| `item_unit` | string | **Yes** | Max 50 chars | cookies, brownies, pieces, servings |
| `notes` | string | No | Max 2000 chars | Product description |

**Yield Mode Values**:

- **DISCRETE_COUNT**: Recipe produces countable items (cookies, brownies, pieces)
  - Requires `items_per_batch` (e.g., 48 cookies per batch)
  - Used for items that are individually packaged or counted

- **CONTINUOUS**: Recipe produces bulk quantity (fudge by weight, dough, batter)
  - `items_per_batch` not used
  - Measured by weight or volume

**Important Notes**:
- **AI agents should create finished goods for all recipes that produce discrete items**
- This enables gift planning and inventory tracking
- One recipe can have multiple finished goods (different packaging sizes)

**Examples**:

```json
// Discrete count example
{
  "name": "Brownie Square",
  "recipe_name": "Fudgy Brownies",
  "category": "Brownies",
  "yield_mode": "DISCRETE_COUNT",
  "items_per_batch": 16,
  "item_unit": "brownies",
  "notes": "2-inch square brownies"
}

// Continuous example (if needed)
{
  "name": "Chocolate Fudge",
  "recipe_name": "Chocolate Walnut Fudge",
  "category": "Candies",
  "yield_mode": "CONTINUOUS",
  "item_unit": "lb",
  "notes": "Cut to desired size when serving"
}
```

---

## 8. Bundles

**Purpose**: Group finished goods into gift packages.

**Schema**:

```json
{
  "name": "Cookie Assortment",
  "finished_good_name": "Chocolate Chip Cookie Dozen",
  "quantity": 12,
  "notes": "One dozen chocolate chip cookies"
}
```

**Field Specifications**:

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `name` | string | **Yes** | Max 200 chars | Bundle name (must be unique) |
| `finished_good_name` | string | **Yes** | Must reference existing finished good | Foreign key |
| `quantity` | number | **Yes** | > 0 | Number of items in bundle |
| `notes` | string | No | Max 2000 chars | Bundle description |

**Important Notes**:
- Bundles are the smallest gift unit
- Multiple bundles combine to make packages
- Example: "Cookie Assortment" = 12 cookies

---

## 9. Packages

**Purpose**: Combine multiple bundles into complete gift boxes.

**Schema**:

```json
{
  "name": "Holiday Cookie Box",
  "description": "Assorted cookie gift box with variety",
  "bundles": [
    {
      "bundle_name": "Cookie Assortment",
      "quantity": 1.0
    },
    {
      "bundle_name": "Snickerdoodle Bundle",
      "quantity": 1.0
    }
  ]
}
```

**Field Specifications**:

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `name` | string | **Yes** | Max 200 chars | Package name (must be unique) |
| `description` | string | No | Max 500 chars | Package description |
| `bundles` | array | **Yes** | Min 1 item | List of bundles in package |

**Package Bundle Sub-Schema**:

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `bundle_name` | string | **Yes** | Must reference existing bundle | Foreign key |
| `quantity` | number | **Yes** | > 0 | Number of bundles included |

---

## 10. Recipients

**Purpose**: Track gift recipients for event planning.

**Schema**:

```json
{
  "name": "Alice Johnson",
  "household_name": "Johnson Family",
  "address": "123 Main St, Anytown, USA",
  "notes": "Loves chocolate chip cookies. Email: alice@example.com, Phone: 555-0101"
}
```

**Field Specifications**:

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `name` | string | **Yes** | Max 200 chars | Recipient name (must be unique) |
| `household_name` | string | No | Max 200 chars | Family/household name |
| `address` | string | No | Max 500 chars | Delivery address |
| `notes` | string | No | Max 2000 chars | Preferences, dietary restrictions, contact info |

---

## 11. Events

**Purpose**: Plan seasonal baking events and track gift assignments.

**Schema**:

```json
{
  "name": "Holiday Baking 2024",
  "year": 2024,
  "event_date": "2024-12-15",
  "notes": "Annual holiday gift baking",
  "assignments": [
    {
      "recipient_name": "Alice Johnson",
      "package_name": "Holiday Cookie Box",
      "quantity": 1.0,
      "notes": "Deliver by Dec 20"
    }
  ]
}
```

**Event Field Specifications**:

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `name` | string | **Yes** | Max 200 chars | Event name (must be unique per year) |
| `year` | integer | **Yes** | >= 2000 | Event year |
| `event_date` | string | No | ISO 8601 date | Target event date |
| `notes` | string | No | Max 2000 chars | Event notes |
| `assignments` | array | No | - | Gift assignments |

**Event Assignment Sub-Schema**:

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `recipient_name` | string | **Yes** | Must reference existing recipient | Foreign key |
| `package_name` | string | **Yes** | Must reference existing package | Foreign key |
| `quantity` | number | **Yes** | > 0 | Number of packages |
| `notes` | string | No | Max 500 chars | Delivery instructions, preferences |

---

## Import Order and Dependencies

**Critical**: Records must be imported in dependency order to maintain referential integrity.

**Correct Import Order**:

1. **Ingredients** (no dependencies)
2. **Variants** (requires: ingredients)
3. **Purchases** (requires: variants)
4. **Pantry Items** (requires: variants)
5. **Unit Conversions** (requires: ingredients)
6. **Recipes** (requires: ingredients)
7. **Finished Goods** (requires: recipes)
8. **Bundles** (requires: finished_goods)
9. **Packages** (requires: bundles)
10. **Recipients** (no dependencies)
11. **Events** (requires: recipients, packages)

**The import service processes arrays in this order automatically.**

---

## Validation Rules

### Required Foreign Key Validation

The import service validates all foreign key references:

- `variants.ingredient_slug` → must exist in `ingredients`
- `purchases.ingredient_slug + variant_brand` → must exist in `variants`
- `pantry_items.ingredient_slug + variant_brand` → must exist in `variants`
- `unit_conversions.ingredient_slug` → must exist in `ingredients`
- `recipes.ingredients[].ingredient_slug` → must exist in `ingredients`
- `finished_goods.recipe_name` → must exist in `recipes`
- `bundles.finished_good_name` → must exist in `finished_goods`
- `packages.bundles[].bundle_name` → must exist in `bundles`
- `events.assignments[].recipient_name` → must exist in `recipients`
- `events.assignments[].package_name` → must exist in `packages`

### Duplicate Handling

By default, the import service:
- **Skips** existing ingredients/variants/recipes (by name/slug)
- **Warns** about duplicates in the import report
- **Allows** multiple purchases/pantry items (not duplicates)

---

## Usage Instructions

### Loading Test Data

```bash
# Load sample data
python -m src.utils.load_test_data

# Load custom file
python -m src.utils.load_test_data path/to/custom_data.json
```

### Exporting Current Data

```bash
# Export to default location (test_data/exported_data.json)
python -m src.utils.export_test_data

# Export to custom location
python -m src.utils.export_test_data path/to/output.json
```

### Import Result Summary

After import, you'll see a summary like:

```
============================================================
Import Summary
============================================================
Total Records: 150
Successful:    145
Skipped:       3
Failed:        2

Errors:
  - recipe: Chocolate Cake
    Ingredient 'dutch_cocoa' not found in database

Warnings:
  - ingredient: All-Purpose Flour
    Ingredient already exists. Skipped.
============================================================
```

---

## Guidelines for AI Data Generation

When AI agents generate data for this system:

### 1. Create Complete Ingredient Sets

For each ingredient, create:
- The generic ingredient (with slug)
- At least one variant (preferably 2-3 common brands)
- Optional: unit conversions if commonly measured by volume

**Example Set**:

```json
{
  "ingredients": [
    {
      "name": "All-Purpose Flour",
      "slug": "all_purpose_flour",
      "category": "Flour",
      "recipe_unit": "cup",
      "density_g_per_ml": 0.507
    }
  ],
  "variants": [
    {
      "ingredient_slug": "all_purpose_flour",
      "brand": "King Arthur",
      "package_size": "25 lb bag",
      "purchase_unit": "lb",
      "purchase_quantity": 25.0,
      "preferred": true
    },
    {
      "ingredient_slug": "all_purpose_flour",
      "brand": "Gold Medal",
      "package_size": "5 lb bag",
      "purchase_unit": "lb",
      "purchase_quantity": 5.0
    }
  ],
  "unit_conversions": [
    {
      "ingredient_slug": "all_purpose_flour",
      "from_unit": "lb",
      "from_quantity": 1.0,
      "to_unit": "cup",
      "to_quantity": 3.6,
      "notes": "Unsifted, spooned and leveled"
    }
  ]
}
```

### 2. Create Realistic Recipes

- Use only ingredients that exist in the ingredients array
- Include 4-12 ingredients per recipe
- Use realistic quantities and units
- Include helpful notes (temperature, timing, techniques)
- Vary yield quantities (12-72 items typical for cookies)

### 3. Always Create Finished Goods for Discrete Recipes

**This is critical for the gift planning system.**

For every recipe that produces countable items (cookies, brownies, candies):

```json
{
  "recipes": [
    {
      "name": "Snickerdoodles",
      "category": "Cookies",
      "yield_quantity": 36,
      "yield_unit": "cookies",
      // ... ingredients ...
    }
  ],
  "finished_goods": [
    {
      "name": "Snickerdoodle Cookies",
      "recipe_name": "Snickerdoodles",
      "category": "Cookies",
      "yield_mode": "DISCRETE_COUNT",
      "items_per_batch": 36,
      "item_unit": "cookies",
      "notes": "Classic cinnamon sugar cookies"
    }
  ]
}
```

### 4. Slug Naming Conventions

**Important**: Use consistent slug naming:

- Lowercase only
- Use underscores for spaces
- Be descriptive but concise
- Examples:
  - ✅ `semi_sweet_chocolate_chips`
  - ✅ `unsalted_butter`
  - ✅ `dark_brown_sugar`
  - ❌ `chocolate` (too vague)
  - ❌ `SemiSweet-Chips` (wrong case/separator)

### 5. Recipe Variety

Include diverse recipe types:
- **Cookies**: Chocolate chip, sugar, oatmeal, peanut butter, snickerdoodles
- **Brownies**: Fudgy, cakey, with nuts, swirled
- **Bars**: Lemon bars, blondies, magic bars, rice crispy treats
- **Candies**: Fudge, truffles, bark, brittles, caramels
- **Cakes**: Pound cake, coffee cake, bundt cakes
- **Other**: Biscotti, scones, muffins

### 6. Optional Sections

You can optionally include:
- **Purchases**: Historical purchase data for price tracking
- **Pantry Items**: Current inventory state
- **Bundles/Packages**: Pre-defined gift combinations
- **Recipients**: Common gift recipients
- **Events**: Seasonal baking events

These are useful for a more complete test dataset but not required.

---

## Example: Complete Cookie Recipe

Here's a complete example showing all related entities:

```json
{
  "ingredients": [
    {
      "name": "All-Purpose Flour",
      "slug": "all_purpose_flour",
      "category": "Flour",
      "recipe_unit": "cup",
      "density_g_per_ml": 0.507
    },
    {
      "name": "White Granulated Sugar",
      "slug": "white_granulated_sugar",
      "category": "Sugar",
      "recipe_unit": "cup",
      "density_g_per_ml": 0.845
    }
  ],
  "variants": [
    {
      "ingredient_slug": "all_purpose_flour",
      "brand": "King Arthur",
      "package_size": "25 lb bag",
      "purchase_unit": "lb",
      "purchase_quantity": 25.0,
      "preferred": true
    },
    {
      "ingredient_slug": "white_granulated_sugar",
      "brand": "Domino",
      "package_size": "25 lb bag",
      "purchase_unit": "lb",
      "purchase_quantity": 25.0,
      "preferred": true
    }
  ],
  "unit_conversions": [
    {
      "ingredient_slug": "all_purpose_flour",
      "from_unit": "lb",
      "from_quantity": 1.0,
      "to_unit": "cup",
      "to_quantity": 3.6
    },
    {
      "ingredient_slug": "white_granulated_sugar",
      "from_unit": "lb",
      "from_quantity": 1.0,
      "to_unit": "cup",
      "to_quantity": 2.25
    }
  ],
  "recipes": [
    {
      "name": "Simple Sugar Cookies",
      "category": "Cookies",
      "source": "Family Recipe",
      "yield_quantity": 24,
      "yield_unit": "cookies",
      "yield_description": "3-inch round cookies",
      "estimated_time_minutes": 30,
      "notes": "Roll to 1/4 inch thickness. Bake at 350°F for 8-10 minutes.",
      "ingredients": [
        {
          "ingredient_slug": "all_purpose_flour",
          "quantity": 2.5,
          "unit": "cup"
        },
        {
          "ingredient_slug": "white_granulated_sugar",
          "quantity": 1.0,
          "unit": "cup"
        }
      ]
    }
  ],
  "finished_goods": [
    {
      "name": "Sugar Cookie",
      "recipe_name": "Simple Sugar Cookies",
      "category": "Cookies",
      "yield_mode": "DISCRETE_COUNT",
      "items_per_batch": 24,
      "item_unit": "cookies",
      "notes": "Classic cut-out sugar cookies"
    }
  ]
}
```

---

## Appendix A: Valid Categories

### Ingredient Categories

```python
INGREDIENT_CATEGORIES = [
    "Flour",
    "Sugar",
    "Dairy",
    "Oils/Butters",
    "Nuts",
    "Spices",
    "Chocolate/Candies",
    "Cocoa Powders",
    "Dried Fruits",
    "Extracts",
    "Syrups",
    "Alcohol",
    "Misc"
]
```

### Recipe/Finished Good Categories

```python
RECIPE_CATEGORIES = [
    "Cookies",
    "Cakes",
    "Candies",
    "Bars",
    "Brownies",
    "Breads",
    "Pastries",
    "Pies",
    "Tarts",
    "Other"
]
```

---

## Appendix B: Valid Units

### Weight Units
```python
["oz", "lb", "g", "kg"]
```

### Volume Units
```python
["tsp", "tbsp", "cup", "ml", "l", "fl oz", "pt", "qt", "gal"]
```

### Count Units
```python
["each", "count", "piece", "dozen"]
```

### Package Types
```python
["bag", "box", "jar", "bottle", "can", "packet", "container", "case"]
```

---

## Appendix C: Current Test Data

The working test dataset is located at:
- **File**: `test_data/sample_data.json`
- **Contents**: 12 ingredients, 13 variants, 5 recipes, 5 finished goods, 5 bundles, 3 packages, 2 recipients, 1 event
- **Use as reference**: This file demonstrates the complete working schema

---

**Document Status**: Implemented and Working
**Version**: 2.0 - Updated to reflect Ingredient/Variant architecture
**Last Updated**: 2025-11-08

**Key Changes from v1.0**:
- Ingredient/Variant separation (breaking change)
- Slug-based foreign keys
- Added Finished Goods, Bundles, Packages, Recipients, Events
- Removed volume_equivalents (replaced by unit_conversions table)
- Removed version/export_date metadata (simplified format)
- Updated to match actual working implementation
