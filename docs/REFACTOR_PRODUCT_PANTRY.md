# Ingredient/Variant Model Refactoring Plan

**Document Purpose:** Architecture plan for separating conflated Ingredient model into Ingredient catalog and Pantry inventory

**Created:** 2025-11-06
**Status:** ⏸️ PAUSED - Planning complete, implementation deferred
**Terminology Update:** 2025-11-06 - Changed from "Product/ProductVariant" to "Ingredient/Variant"

> **NOTE:** This document uses "Product" terminology but has been conceptually updated to "Ingredient/Variant":
> - Product → Ingredient (generic ingredient concept)
> - ProductVariant → Variant (specific brand/source)
> - "My Products" → "My Ingredients"
>
> **Rationale:** "Ingredient" handles both commercial products (Domino Sugar) AND non-commercial sources (farm stand tomatoes, butcher's chicken). More domain-appropriate for baking application.
>
> **See `PAUSE_POINT.md` for current pause point and resumption plan.**

---

## Executive Summary

### Current Problem

The existing `Ingredient` model conflates multiple concerns:
- **Product definition** - What is the ingredient? (e.g., "All-Purpose Flour")
- **Brand/package specifics** - Which brand? What size? (e.g., "King Arthur 25 lb bag")
- **Purchase information** - Cost, supplier, when/where bought
- **Current inventory** - Quantity on hand, location
- **Recipe usage** - How it's measured in recipes (cups, oz, etc.)

### Limitations This Creates

1. ❌ Cannot have multiple brands of same ingredient
2. ❌ Cannot have multiple package sizes simultaneously
3. ❌ No price history tracking
4. ❌ Cannot track location of items in pantry
5. ❌ No support for UPC/barcode scanning
6. ❌ No expiration date tracking
7. ❌ Cannot connect to supplier APIs
8. ❌ No FIFO inventory management

### Proposed Solution

**Separate into two core concepts:**

1. **"My Products"** - Catalog of purchasable ingredients
   - Generic ingredient definitions
   - Multiple brands, package sizes, suppliers
   - Price history tracking
   - Preferred product variants

2. **"My Pantry"** - Current inventory of purchased items
   - Specific product instances
   - Quantity on hand
   - Purchase/expiration dates
   - Location tracking
   - FIFO consumption

---

## New Data Architecture

### Entity Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         MY PRODUCTS                              │
│  (What can I buy?)                                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐         ┌──────────────────┐                 │
│  │   Product    │◄────────│ ProductVariant   │                 │
│  │              │         │                  │                 │
│  │ • Name       │         │ • Brand          │                 │
│  │ • Category   │         │ • Package size   │                 │
│  │ • Recipe unit│         │ • UPC code       │                 │
│  │              │         │ • Supplier       │                 │
│  │              │         │ • Preferred?     │                 │
│  └──────────────┘         └──────────────────┘                 │
│         ▲                         │                             │
│         │                         │                             │
│         │                         ▼                             │
│  ┌──────────────┐         ┌──────────────────┐                 │
│  │UnitConversion│         │ PurchaseHistory  │                 │
│  │              │         │                  │                 │
│  │ • From unit  │         │ • Date           │                 │
│  │ • To unit    │         │ • Cost           │                 │
│  │ • Factor     │         │ • Store          │                 │
│  └──────────────┘         │ • Quantity       │                 │
│                           └──────────────────┘                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         MY PANTRY                                │
│  (What do I have?)                                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐                                           │
│  │   PantryItem     │◄─────────(references ProductVariant)      │
│  │                  │                                           │
│  │ • Quantity       │                                           │
│  │ • Purchase date  │                                           │
│  │ • Expiration     │                                           │
│  │ • Location       │                                           │
│  │ • Opened date    │                                           │
│  │ • Notes          │                                           │
│  └──────────────────┘                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         RECIPES                                  │
│  (What am I making?)                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐                                           │
│  │ RecipeIngredient │◄─────────(references Product, NOT variant)│
│  │                  │                                           │
│  │ • Quantity       │           "2 cups All-Purpose Flour"      │
│  │ • Unit           │           (doesn't care about brand)       │
│  └──────────────────┘                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Detailed Schema Design

### 1. Product Table

**Purpose:** Generic ingredient definition - the "platonic ideal" of an ingredient

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK, Auto | Unique identifier |
| `name` | String(200) | NOT NULL, Indexed, Unique | Product name (e.g., "All-Purpose Flour") |
| `category` | String(100) | NOT NULL, Indexed | Category (Flour, Sugar, Dairy, etc.) |
| `recipe_unit` | String(50) | NOT NULL | Default unit for recipes (cup, oz, g, etc.) |
| `description` | Text | | Optional description |
| `notes` | Text | | Additional notes |
| `date_added` | DateTime | NOT NULL | When created |
| `last_modified` | DateTime | NOT NULL | Last update |

**Relationships:**
- `variants` - One-to-many with ProductVariant
- `conversions` - One-to-many with UnitConversion
- `recipe_ingredients` - One-to-many with RecipeIngredient

**Example:**
```python
{
  "name": "All-Purpose Flour",
  "category": "Flour",
  "recipe_unit": "cup",
  "description": "General purpose wheat flour for baking"
}
```

---

### 2. ProductVariant Table

**Purpose:** Specific purchasable version of a product (brand, size, package)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK, Auto | Unique identifier |
| `product_id` | Integer | FK → Product, NOT NULL, Indexed | Parent product |
| `brand` | String(200) | Indexed | Brand name (e.g., "King Arthur") |
| `package_size` | String(100) | | Size description (e.g., "25 lb", "5 kg") |
| `package_type` | String(50) | | Package type (bag, box, jar, bottle, etc.) |
| `purchase_unit` | String(50) | NOT NULL | Unit purchased in (bag, lb, oz, etc.) |
| `purchase_quantity` | Float | NOT NULL, > 0 | Quantity per package |
| `upc_code` | String(20) | Indexed | UPC/barcode for scanning (future) |
| `supplier` | String(200) | | Supplier/store name |
| `supplier_sku` | String(100) | | Supplier's SKU/product code |
| `preferred` | Boolean | Default: False | Is this the preferred variant? |
| `notes` | Text | | Additional notes |
| `date_added` | DateTime | NOT NULL | When created |
| `last_modified` | DateTime | NOT NULL | Last update |

**Relationships:**
- `product` - Many-to-one with Product
- `purchases` - One-to-many with PurchaseHistory
- `pantry_items` - One-to-many with PantryItem

**Indexes:**
- `idx_variant_product` on `product_id`
- `idx_variant_brand` on `brand`
- `idx_variant_upc` on `upc_code`

**Example:**
```python
{
  "product_id": 1,  # All-Purpose Flour
  "brand": "King Arthur",
  "package_size": "25 lb",
  "package_type": "bag",
  "purchase_unit": "bag",
  "purchase_quantity": 25.0,
  "upc_code": "071012003008",
  "supplier": "Costco",
  "preferred": True
}
```

---

### 3. PurchaseHistory Table

**Purpose:** Track price history and purchase events for cost analysis

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK, Auto | Unique identifier |
| `product_variant_id` | Integer | FK → ProductVariant, NOT NULL, Indexed | Which variant |
| `purchase_date` | Date | NOT NULL, Indexed | When purchased |
| `unit_cost` | Float | NOT NULL, >= 0 | Cost per purchase unit |
| `quantity_purchased` | Float | NOT NULL, > 0 | How many units purchased |
| `total_cost` | Float | NOT NULL, >= 0 | Total cost (quantity × unit_cost) |
| `supplier` | String(200) | | Where purchased (can differ from variant default) |
| `receipt_number` | String(100) | | Optional receipt reference |
| `notes` | Text | | Additional notes |

**Relationships:**
- `product_variant` - Many-to-one with ProductVariant

**Indexes:**
- `idx_purchase_variant` on `product_variant_id`
- `idx_purchase_date` on `purchase_date`

**Methods:**
- `get_average_price(product_variant_id, days=90)` - Average price over time period
- `get_most_recent_price(product_variant_id)` - Latest purchase price
- `get_price_trend(product_variant_id)` - Price change over time

**Example:**
```python
{
  "product_variant_id": 5,  # King Arthur 25 lb bag
  "purchase_date": "2025-11-01",
  "unit_cost": 15.99,
  "quantity_purchased": 2.0,
  "total_cost": 31.98,
  "supplier": "Costco",
  "receipt_number": "12345678"
}
```

---

### 4. PantryItem Table

**Purpose:** Current inventory - what's actually in the pantry right now

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK, Auto | Unique identifier |
| `product_variant_id` | Integer | FK → ProductVariant, NOT NULL, Indexed | Which variant |
| `quantity` | Float | NOT NULL, >= 0 | Quantity on hand (in purchase units) |
| `purchase_date` | Date | Indexed | When this item was purchased |
| `expiration_date` | Date | Indexed | When it expires (if applicable) |
| `opened_date` | Date | | When opened (if applicable) |
| `location` | String(100) | Indexed | Where stored ("Main Pantry", "Garage Shelf 2", etc.) |
| `notes` | Text | | Additional notes |
| `last_updated` | DateTime | NOT NULL | Last modification timestamp |

**Relationships:**
- `product_variant` - Many-to-one with ProductVariant

**Indexes:**
- `idx_pantry_variant` on `product_variant_id`
- `idx_pantry_location` on `location`
- `idx_pantry_expiration` on `expiration_date`

**Methods:**
- `get_total_quantity_for_product(product_id)` - Sum all pantry items for a product
- `get_expiring_soon(days=30)` - Items expiring within X days
- `get_items_by_location(location)` - All items in a location
- `apply_fifo_consumption(product_variant_id, quantity)` - Consume oldest first

**Example:**
```python
{
  "product_variant_id": 5,  # King Arthur 25 lb bag
  "quantity": 1.5,  # 1.5 bags remaining
  "purchase_date": "2025-10-15",
  "expiration_date": "2026-10-15",
  "opened_date": "2025-10-20",
  "location": "Main Pantry - Shelf 2"
}
```

---

### 5. UnitConversion Table

**Purpose:** Product-specific conversion factors (replaces hardcoded conversion_factor in Ingredient)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | PK, Auto | Unique identifier |
| `product_id` | Integer | FK → Product, NOT NULL, Indexed | Which product |
| `from_unit` | String(50) | NOT NULL | Purchase unit (lb, oz, kg, etc.) |
| `from_quantity` | Float | NOT NULL, > 0 | Amount in from_unit (e.g., 1 lb) |
| `to_unit` | String(50) | NOT NULL | Recipe unit (cup, oz, g, etc.) |
| `to_quantity` | Float | NOT NULL, > 0 | Equivalent in to_unit (e.g., 3.6 cups) |
| `notes` | Text | | Additional notes (e.g., "sifted", "packed") |

**Relationships:**
- `product` - Many-to-one with Product

**Indexes:**
- `idx_conversion_product` on `product_id`

**Methods:**
- `convert(product_id, quantity, from_unit, to_unit)` - Convert between units

**Example:**
```python
{
  "product_id": 1,  # All-Purpose Flour
  "from_unit": "lb",
  "from_quantity": 1.0,
  "to_unit": "cup",
  "to_quantity": 3.6,  # 1 lb flour ≈ 3.6 cups
  "notes": "Unsifted, spooned and leveled"
}
```

---

## Key Design Decisions

### 1. Recipes Reference Products, NOT Variants

**Rationale:** Recipes should be brand-agnostic

```python
# RecipeIngredient
recipe_ingredient = {
  "recipe_id": 42,
  "product_id": 1,      # All-Purpose Flour (generic)
  "quantity": 2.0,
  "unit": "cup"
}
```

**Benefits:**
- Recipe works with any brand of flour
- User can switch brands without updating recipes
- Shopping list aggregates by product, user chooses which variant to buy

### 2. Inventory Aggregates by Product

**When showing inventory:**
```python
# "How much All-Purpose Flour do I have?"
total_flour = sum(
    pantry_item.quantity * product_variant.purchase_quantity
    for pantry_item in PantryItem
    where pantry_item.product_variant.product_id == 1
)

# Breakdown:
# - King Arthur 25 lb bag: 1.5 bags = 37.5 lb
# - Bob's Red Mill 5 lb bag: 2 bags = 10 lb
# Total: 47.5 lb
```

### 3. Cost Calculations Use Preferred Variant

**Strategy options:**
1. **Preferred variant** - Use most recent price for preferred variant (default)
2. **Weighted average** - Average across all variants weighted by purchase frequency
3. **Cheapest** - Always use cheapest variant
4. **Most recent** - Most recent purchase regardless of variant

**Implementation:**
```python
def get_product_cost_per_recipe_unit(product_id: int, strategy: str = "preferred"):
    if strategy == "preferred":
        variant = get_preferred_variant(product_id)
        latest_price = get_most_recent_price(variant.id)
        conversion = get_conversion(product_id, variant.purchase_unit, product.recipe_unit)
        return latest_price.unit_cost / conversion.to_quantity
    # ... other strategies
```

### 4. Shopping Lists Recommend Variants

**When generating shopping list:**
```python
# Need: 10 cups All-Purpose Flour
# On hand: 3 cups (across all variants)
# To buy: 7 cups

# Recommendation:
# Option 1: King Arthur 25 lb bag ($15.99) = 90 cups = $0.178/cup (preferred)
# Option 2: Bob's Red Mill 5 lb bag ($5.99) = 18 cups = $0.333/cup
# Option 3: Generic 10 lb bag ($8.99) = 36 cups = $0.250/cup

# Suggest: "Buy 1x King Arthur 25 lb bag (preferred)"
```

---

## Migration Strategy

### Phase 1: Schema Creation (Feature Branch)

**Goal:** Create new tables alongside existing schema

**Tasks:**
1. Create new SQLAlchemy models:
   - `Product`
   - `ProductVariant`
   - `PurchaseHistory`
   - `PantryItem`
   - `UnitConversion`

2. Update `RecipeIngredient` to reference `Product` (add new FK, keep old for migration)

3. Create database migration script

**Branch:** `feature/product-pantry-refactor`

---

### Phase 2: Data Migration Script

**Goal:** Convert existing Ingredient records to new schema

**Logic:**
```python
def migrate_ingredient_to_new_schema(ingredient: Ingredient):
    """
    Each existing Ingredient becomes:
    - 1 Product (generic ingredient)
    - 1 ProductVariant (the specific brand/package currently in system)
    - 1 PantryItem (current inventory)
    - 1 UnitConversion (purchase → recipe unit conversion)
    """

    # 1. Create Product
    product = Product(
        name=ingredient.name,
        category=ingredient.category,
        recipe_unit=ingredient.recipe_unit,
        notes=ingredient.notes
    )

    # 2. Create ProductVariant
    variant = ProductVariant(
        product_id=product.id,
        brand=ingredient.brand,
        package_size=ingredient.purchase_unit_size,
        package_type=ingredient.package_type,
        purchase_unit=ingredient.purchase_unit,
        purchase_quantity=ingredient.purchase_quantity,
        preferred=True  # Mark as preferred since it's the only one
    )

    # 3. Create PantryItem (if quantity > 0)
    if ingredient.quantity > 0:
        pantry_item = PantryItem(
            product_variant_id=variant.id,
            quantity=ingredient.quantity,
            purchase_date=ingredient.last_updated,  # Best guess
            location="Main Pantry"  # Default
        )

    # 4. Create UnitConversion
    # Old: conversion_factor (purchase units → recipe units)
    # New: from_quantity / to_quantity
    conversion = UnitConversion(
        product_id=product.id,
        from_unit=ingredient.purchase_unit,
        from_quantity=1.0,
        to_unit=ingredient.recipe_unit,
        to_quantity=ingredient.conversion_factor
    )

    # 5. Create PurchaseHistory entry (if unit_cost > 0)
    if ingredient.unit_cost > 0:
        purchase = PurchaseHistory(
            product_variant_id=variant.id,
            purchase_date=ingredient.last_updated,
            unit_cost=ingredient.unit_cost,
            quantity_purchased=ingredient.quantity,
            total_cost=ingredient.unit_cost * ingredient.quantity
        )

    # 6. Update RecipeIngredient references
    for recipe_ing in ingredient.recipe_ingredients:
        recipe_ing.product_id = product.id
        # Keep old ingredient_id for rollback capability
```

**Validation:**
- Ensure all Ingredients migrated
- Verify RecipeIngredient references updated
- Confirm cost calculations match old vs new
- Test shopping list generation produces same results

---

### Phase 3: Service Layer Refactoring

**Goal:** Update all business logic to work with new model

**New Services:**

#### `ProductService`
Replaces: Part of `InventoryService` (CRUD for products)
- `create_product(data)` - Create generic product
- `get_product(product_id)` - Get product by ID
- `search_products(name, category)` - Search product catalog
- `update_product(product_id, data)` - Update product
- `delete_product(product_id)` - Delete product (checks dependencies)

#### `ProductVariantService`
New service for managing variants
- `create_variant(product_id, data)` - Add variant to product
- `get_variants_for_product(product_id)` - Get all variants
- `set_preferred_variant(variant_id)` - Mark as preferred
- `update_variant(variant_id, data)` - Update variant
- `delete_variant(variant_id)` - Delete variant

#### `PantryService`
Replaces: Part of `InventoryService` (inventory management)
- `add_to_pantry(variant_id, quantity, purchase_date, location)` - Add item
- `get_pantry_items(product_id=None, location=None)` - Get pantry items
- `get_total_quantity(product_id)` - Aggregate by product
- `consume_quantity(product_id, quantity)` - FIFO consumption
- `get_expiring_soon(days=30)` - Expiration tracking
- `update_pantry_item(item_id, data)` - Update item

#### `PurchaseService`
New service for purchase history
- `record_purchase(variant_id, data)` - Record purchase
- `get_purchase_history(variant_id, days=90)` - Get history
- `get_price_trend(product_id)` - Analyze price trends
- `get_average_price(product_id, days=90)` - Calculate average

#### Updated Services:

#### `RecipeService`
- Update `calculate_recipe_cost()` to use Product-based pricing
- Update ingredient validation to use Product IDs

#### `EventService`
- Update `generate_shopping_list()` to:
  - Aggregate by Product (not ProductVariant)
  - Recommend preferred or cheapest variant
  - Show purchase options

---

### Phase 4: UI Updates

**Goal:** Update all UI to reflect new Product/Pantry separation

#### New Tabs:

**"My Products" Tab** (replaces "Inventory" tab)
- Product catalog management
- CRUD for products and variants
- View/edit variants per product
- Set preferred variants
- View price history

**"My Pantry" Tab** (new)
- Current inventory view
- Aggregate by product or show by variant
- Filter by location, expiration date
- Add/remove pantry items
- FIFO consumption tracking
- Low stock alerts

#### Updated Forms:

**Product Form:**
```
┌─────────────────────────────────────────┐
│ Add/Edit Product                        │
├─────────────────────────────────────────┤
│ Name: [All-Purpose Flour           ]   │
│ Category: [Flour                   ▼]   │
│ Recipe Unit: [cup                  ▼]   │
│ Description: [                      ]   │
│                                         │
│ [Save]  [Cancel]                        │
└─────────────────────────────────────────┘
```

**Product Variant Form:**
```
┌─────────────────────────────────────────┐
│ Add/Edit Variant for All-Purpose Flour  │
├─────────────────────────────────────────┤
│ Brand: [King Arthur                 ]   │
│ Package Size: [25 lb                ]   │
│ Package Type: [bag                  ▼]  │
│ Purchase Unit: [bag                 ▼]  │
│ Purchase Qty: [25.0                 ]   │
│ UPC Code: [071012003008             ]   │
│ Supplier: [Costco                   ]   │
│ ☑ Preferred variant                     │
│                                         │
│ [Save]  [Cancel]                        │
└─────────────────────────────────────────┘
```

**Pantry Item Form:**
```
┌─────────────────────────────────────────┐
│ Add to Pantry                           │
├─────────────────────────────────────────┤
│ Product: [All-Purpose Flour         ▼]  │
│ Variant: [King Arthur 25 lb bag     ▼]  │
│ Quantity: [2.0                      ]   │
│ Purchase Date: [2025-11-01          ]   │
│ Expiration: [2026-11-01             ]   │
│ Location: [Main Pantry - Shelf 2   ▼]  │
│ Notes: [                             ]   │
│                                         │
│ [Add to Pantry]  [Cancel]               │
└─────────────────────────────────────────┘
```

#### Recipe Form Updates:

**Ingredient Selection:**
```
When adding ingredient to recipe:

  ┌─────────────────────────────────────────┐
  │ Select ingredient:                      │
  │ [All-Purpose Flour               ▼]    │  ← Search products, not variants
  │                                         │
  │ Quantity: [2.0                    ]     │
  │ Unit: [cup                        ▼]    │
  │                                         │
  │ Cost estimate:                          │
  │ $0.36 (using King Arthur, preferred)    │  ← Shows preferred variant price
  │                                         │
  │ [Add]  [Cancel]                         │
  └─────────────────────────────────────────┘
```

#### Shopping List Updates:

**Event Detail - Shopping List Tab:**
```
┌──────────────────────────────────────────────────────────────────┐
│ Shopping List for Christmas 2025                                 │
├──────────────────────────────────────────────────────────────────┤
│ Product              Need    Have    Buy    Recommended          │
│                                                                   │
│ All-Purpose Flour    15 lb   5 lb   10 lb  King Arthur 25 lb    │
│                                             ($15.99) [preferred]  │
│                                             └─ Cost: $15.99       │
│                                                                   │
│ White Sugar          10 lb   2 lb    8 lb  Costco 25 lb bag     │
│                                             ($16.99) [cheapest]   │
│                                             └─ Cost: $16.99       │
│                                                                   │
│ Chocolate Chips      4 cups  0      4 cups  Nestle 72 oz        │
│                                             ($12.99) [preferred]  │
│                                             └─ Cost: $12.99       │
│                                                                   │
│ Total Estimated Cost: $45.97                                     │
│                                                                   │
│ [View Alternatives] [Export to Mobile] [Print]                   │
└──────────────────────────────────────────────────────────────────┘
```

---

### Phase 5: Import/Export Updates

**Goal:** Update import/export to handle new schema

**Export Format:**
```json
{
  "products": [
    {
      "id": 1,
      "name": "All-Purpose Flour",
      "category": "Flour",
      "recipe_unit": "cup",
      "variants": [
        {
          "id": 5,
          "brand": "King Arthur",
          "package_size": "25 lb",
          "package_type": "bag",
          "purchase_unit": "bag",
          "purchase_quantity": 25.0,
          "upc_code": "071012003008",
          "preferred": true
        }
      ],
      "conversions": [
        {
          "from_unit": "lb",
          "from_quantity": 1.0,
          "to_unit": "cup",
          "to_quantity": 3.6
        }
      ]
    }
  ],
  "pantry_items": [
    {
      "product_name": "All-Purpose Flour",
      "variant_brand": "King Arthur",
      "quantity": 1.5,
      "purchase_date": "2025-10-15",
      "location": "Main Pantry"
    }
  ],
  "purchase_history": [
    {
      "product_name": "All-Purpose Flour",
      "variant_brand": "King Arthur",
      "purchase_date": "2025-10-15",
      "unit_cost": 15.99,
      "quantity_purchased": 2.0,
      "supplier": "Costco"
    }
  ]
}
```

**Migration Tool:**
```bash
# Export old format from v0.3.x
venv/Scripts/python.exe src/utils/import_export_cli.py export old_data.json

# Import to new schema (auto-detects old format and migrates)
venv/Scripts/python.exe src/utils/import_export_cli.py import-migrated old_data.json
```

---

## Testing Strategy

### Unit Tests

**New test files:**
- `test_product_service.py`
- `test_product_variant_service.py`
- `test_pantry_service.py`
- `test_purchase_service.py`

**Test coverage:**
- CRUD operations for all new models
- Migration script (old → new schema)
- Cost calculation strategies
- FIFO consumption logic
- Inventory aggregation
- Shopping list generation

### Integration Tests

**Scenarios:**
1. Create product with 2 variants, add to pantry, check aggregation
2. Create recipe referencing product, calculate cost with different strategies
3. Generate shopping list, verify variant recommendations
4. Migrate old data, verify data integrity
5. Export/import cycle with new format

### UI Testing

**Manual test scenarios:**
1. Create new product and add variants
2. Add items to pantry for different variants
3. View inventory aggregated by product
4. Create recipe using products (not variants)
5. Generate shopping list for event
6. Test variant recommendation logic
7. Track price history over multiple purchases

---

## Rollout Strategy

### Phase Timeline

**Phase 1-3: Development (6-8 weeks)**
- Schema design and model creation
- Migration script development
- Service layer refactoring
- Unit/integration test coverage

**Phase 4: UI Development (4-6 weeks)**
- New tabs and forms
- Updated shopping list UI
- User testing with mock data

**Phase 5: Testing (3-4 weeks)**
- Comprehensive testing
- Data migration validation
- Performance testing
- User acceptance testing

**Phase 6: Deployment (1-2 weeks)**
- Backup existing data
- Run migration
- Deploy new version
- Monitor for issues

### Deployment Options

**Option A: Big Bang (Recommended for small user base)**
1. Backup v0.3.x database
2. Run migration script
3. Deploy new version
4. Provide rollback capability

**Option B: Gradual Migration (For larger user base)**
1. Deploy dual-schema version (supports both old and new)
2. Migrate data in background
3. Switch to new schema
4. Remove old schema in next release

### Rollback Plan

**If migration fails:**
1. Restore from backup
2. Continue using v0.3.x
3. Fix migration issues
4. Retry migration

**Data preserved during rollback:**
- All v0.3.x data (from backup)
- Migration logs for debugging

---

## Future Enhancements (Post-Refactor)

### Phase 7: Mobile Integration
- Mobile app for UPC barcode scanning
- Add to pantry via mobile
- Shopping list on mobile
- Sync with desktop app

### Phase 8: Supplier Integrations
- Connect to grocery store APIs (Costco, Walmart, Amazon)
- Real-time price updates
- Auto-populate product variants from UPC
- Price comparison across suppliers
- One-click online ordering

### Phase 9: Recipe Ingestion
- Import recipes from websites
- Auto-match ingredients to products
- Recipe scaling
- Nutritional information
- Attribution and source tracking

### Phase 10: Multi-User & Collaboration
- User accounts and authentication
- Shared pantries (family members)
- Recipe sharing
- Event planning collaboration
- Permission levels

### Phase 11: Advanced Analytics
- Cost trends over time
- Seasonal pricing insights
- Bulk buying recommendations
- Waste tracking (expired items)
- Recipe cost optimization

---

## Benefits Summary

### Immediate Benefits (Post-Refactor)

✅ **Multiple brands/packages** - Buy different brands without conflicts
✅ **Price history** - Track costs over time, identify trends
✅ **Better inventory** - Know exactly what you have and where
✅ **Location tracking** - Find items in pantry, garage, etc.
✅ **Expiration tracking** - Reduce waste, use oldest first
✅ **FIFO consumption** - Automatic oldest-first usage
✅ **Flexible recipes** - Brand-agnostic recipes work with any variant
✅ **Smart shopping lists** - Recommends best variant to buy

### Future Benefits (Aspirational Features)

🔮 **UPC scanning** - Quick pantry updates via mobile
🔮 **Supplier integrations** - Real-time pricing, online ordering
🔮 **Recipe import** - Auto-populate from websites
🔮 **Multi-user** - Family sharing and collaboration
🔮 **API access** - Third-party integrations
🔮 **MCP integration** - AI-powered meal planning
🔮 **Advanced analytics** - Cost optimization, waste reduction

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-11-06 | Separate Product and Pantry | Conflated model limits scalability |
| 2025-11-06 | Recipes reference Product (not Variant) | Brand-agnostic recipes |
| 2025-11-06 | Use ProductVariant for purchase specifics | Multiple brands per product |
| 2025-11-06 | Add PurchaseHistory for price tracking | Cost trends and analysis |
| 2025-11-06 | Add PantryItem for inventory | Location, FIFO, expiration tracking |
| 2025-11-06 | Feature branch during v0.3.x testing | Parallel development |

---

## Questions for Discussion

1. **Unit conversion flexibility**: Should we support multiple conversion paths per product? (e.g., lb→cup AND lb→oz→cup)

2. **Default variant selection**: When creating recipe, should we prompt to select variant or always use preferred?

3. **Cost calculation strategy**: Which should be default? Preferred, weighted average, cheapest, or most recent?

4. **Pantry item merging**: When adding same variant to pantry, create new item or update existing?

5. **Price alerts**: Should we notify user when price changes significantly? Threshold?

6. **Supplier API priorities**: Which supplier APIs are highest priority? Costco, Amazon, Walmart, local stores?

7. **Mobile app scope**: Read-only or full CRUD? Sync strategy?

8. **Migration timing**: Run migration during user testing phase or wait until v0.4.0?

---

**Next Steps:**
1. Review and approve refactoring plan
2. Create feature branch: `feature/product-pantry-refactor`
3. Begin Phase 1: Schema design and model creation
4. Continue v0.3.x testing in parallel on main branch

**Document Status:** Planning - awaiting approval
**Last Updated:** 2025-11-06
