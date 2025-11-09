# Data Model: Service Layer for Ingredient/Variant Architecture

**Feature**: 002-service-layer-for
**Date**: 2025-11-08
**Status**: Design Complete

## Overview

This document defines the data entities, relationships, validation rules, and core algorithms for the service layer implementation. All entities are defined in Phase 4 Items 1-6 (database models already exist). This document focuses on how services interact with these entities.

## Entity Definitions

### Ingredient (Generic Ingredient Catalog)

**Purpose**: Represents a generic ingredient concept, independent of brand or package.

**Key Attributes**:
- `id` (Integer, PK, auto-increment)
- `slug` (String, unique, indexed) - URL-safe identifier (e.g., "all_purpose_flour")
- `name` (String, required) - Human-readable name (e.g., "All-Purpose Flour")
- `category` (String, required) - Classification (e.g., "Flour", "Sugar", "Dairy")
- `recipe_unit` (String, required) - Default unit for recipes (e.g., "cup", "oz", "tsp")
- `density_g_per_ml` (Float, nullable) - For volume-weight conversions
- `foodon_id` (String, nullable) - Industry standard: FoodOn taxonomy ID
- `fdc_id` (String, nullable) - Industry standard: USDA FoodData Central ID
- `gtin` (String, nullable) - Global Trade Item Number (barcode)
- `allergens` (JSON, nullable) - List of allergen codes
- `created_at` (DateTime, auto)
- `updated_at` (DateTime, auto)

**Relationships**:
- `variants` → List[Variant] (one-to-many)
- `unit_conversions` → List[UnitConversion] (one-to-many)
- `recipe_ingredients` → List[RecipeIngredient] (one-to-many)

**Validation Rules**:
1. `name`: Required, 1-200 characters, unique recommended (but not enforced)
2. `slug`: Required, unique, lowercase alphanumeric + underscores only, auto-generated from name
3. `category`: Required, 1-100 characters
4. `recipe_unit`: Required, must be valid unit from unit_converter.py
5. `density_g_per_ml`: If provided, must be positive float
6. `foodon_id`, `fdc_id`, `gtin`: Optional, string format
7. Slug cannot be changed after creation (foreign key stability)

**Business Rules**:
- Cannot delete if referenced by recipes, variants, or pantry items
- Slug must be unique across all ingredients
- recipe_unit determines default unit for recipe ingredient entries

---

### Variant (Brand-Specific Product)

**Purpose**: Represents a specific purchasable product with brand and package details.

**Key Attributes**:
- `id` (Integer, PK, auto-increment)
- `ingredient_slug` (String, FK to Ingredient.slug, indexed)
- `brand` (String, required) - Brand name (e.g., "King Arthur", "Bob's Red Mill")
- `package_size` (String, nullable) - Human-readable size (e.g., "25 lb bag", "5 lb box")
- `purchase_unit` (String, required) - Unit purchased in (e.g., "lb", "kg", "bag")
- `purchase_quantity` (Decimal, required) - Quantity in package (e.g., 25.0)
- `upc` (String, nullable) - Universal Product Code (12-14 digits)
- `gtin` (String, nullable) - Global Trade Item Number (8-14 digits)
- `supplier` (String, nullable) - Where to buy (e.g., "Costco", "Whole Foods")
- `preferred` (Boolean, default False) - Is this the preferred variant for this ingredient?
- `net_content_value` (Decimal, nullable) - Industry standard: package content amount
- `net_content_uom` (String, nullable) - Industry standard: package content unit
- `created_at` (DateTime, auto)
- `updated_at` (DateTime, auto)

**Calculated Properties**:
- `display_name`: `f"{brand} - {package_size}"` (e.g., "King Arthur - 25 lb bag")

**Relationships**:
- `ingredient` → Ingredient (many-to-one via ingredient_slug FK)
- `pantry_items` → List[PantryItem] (one-to-many)
- `purchases` → List[Purchase] (one-to-many)

**Validation Rules**:
1. `ingredient_slug`: Required, must reference existing Ingredient
2. `brand`: Required, 1-200 characters
3. `purchase_unit`: Required, must be valid unit from unit_converter.py
4. `purchase_quantity`: Required, must be positive Decimal (>0)
5. `upc`: Optional, if provided must be 12-14 digit string
6. `gtin`: Optional, if provided must be 8-14 digit string
7. `preferred`: Boolean, only one variant per ingredient can be preferred

**Business Rules**:
- Cannot delete if referenced by pantry items or purchases
- When setting preferred=True, all other variants for same ingredient must be set to preferred=False
- display_name is auto-calculated, not stored

---

### PantryItem (Actual Inventory)

**Purpose**: Represents a specific lot of inventory in the pantry.

**Key Attributes**:
- `id` (Integer, PK, auto-increment)
- `variant_id` (Integer, FK to Variant.id, indexed)
- `quantity` (Decimal, required) - Amount remaining in this lot
- `unit` (String, required) - Unit of quantity (e.g., "lb", "oz", "cup")
- `purchase_date` (Date, required, indexed) - When this lot was purchased (for FIFO)
- `expiration_date` (Date, nullable) - When this lot expires
- `location` (String, nullable) - Where stored (e.g., "Main Pantry", "Basement Storage")
- `notes` (Text, nullable) - User notes
- `created_at` (DateTime, auto)
- `updated_at` (DateTime, auto)

**Relationships**:
- `variant` → Variant (many-to-one)
- `ingredient` → Ingredient (via variant.ingredient_slug)

**Validation Rules**:
1. `variant_id`: Required, must reference existing Variant
2. `quantity`: Required, must be non-negative Decimal (>=0)
3. `unit`: Required, must be valid unit from unit_converter.py
4. `purchase_date`: Required, must be valid date, cannot be future date
5. `expiration_date`: Optional, if provided must be >= purchase_date

**Business Rules**:
- Quantity can be reduced to 0 (depleted lot), but never negative
- FIFO consumption orders by purchase_date ASC (oldest first)
- When quantity reaches 0, item may be soft-deleted or kept for history

---

### Purchase (Price History)

**Purpose**: Records purchase transactions for price tracking and trend analysis.

**Key Attributes**:
- `id` (Integer, PK, auto-increment)
- `variant_id` (Integer, FK to Variant.id, indexed)
- `purchase_date` (Date, required, indexed)
- `quantity` (Decimal, required) - Amount purchased
- `unit` (String, required) - Unit of quantity
- `unit_cost` (Decimal, required) - Cost per unit
- `total_cost` (Decimal, required) - Total purchase cost (quantity * unit_cost)
- `store` (String, nullable) - Where purchased
- `notes` (Text, nullable) - User notes
- `created_at` (DateTime, auto)

**Relationships**:
- `variant` → Variant (many-to-one)

**Validation Rules**:
1. `variant_id`: Required, must reference existing Variant
2. `purchase_date`: Required, valid date
3. `quantity`: Required, must be positive Decimal (>0)
4. `unit`: Required, must be valid unit
5. `unit_cost`: Required, must be non-negative Decimal (>=0, allow zero for free/donated items)
6. `total_cost`: Required, should equal quantity * unit_cost (auto-calculated or validated)

**Business Rules**:
- Purchase records are historical data; typically not deleted
- total_cost can be manually adjusted if needed (e.g., discount applied)
- Most recent purchase for a variant determines "current price" for that variant

---

### UnitConversion (Ingredient-Specific Conversions)

**Purpose**: Stores ingredient-specific unit conversion factors.

**Key Attributes**:
- `id` (Integer, PK, auto-increment)
- `ingredient_slug` (String, FK to Ingredient.slug, indexed)
- `from_unit` (String, required)
- `from_quantity` (Decimal, required)
- `to_unit` (String, required)
- `to_quantity` (Decimal, required)
- `notes` (Text, nullable) - Context (e.g., "sifted", "packed")

**Relationships**:
- `ingredient` → Ingredient (many-to-one via ingredient_slug FK)

**Validation Rules**:
1. `ingredient_slug`: Required, must reference existing Ingredient
2. `from_unit`, `to_unit`: Required, must be valid units
3. `from_quantity`, `to_quantity`: Required, must be positive Decimals (>0)
4. Unique constraint on (ingredient_slug, from_unit, to_unit)

**Business Rules**:
- Conversion factor = to_quantity / from_quantity
- Example: 1 lb All-Purpose Flour = 3.6 cups → from_quantity=1, from_unit="lb", to_quantity=3.6, to_unit="cup"
- Falls back to standard conversions in unit_converter.py if ingredient-specific not found

---

## Algorithms

### FIFO Consumption Algorithm

**Purpose**: Consume pantry inventory using First-In, First-Out logic to accurately track costs and match physical reality.

**Input**:
- `ingredient_slug` (str): Identifier for ingredient to consume
- `quantity_needed` (Decimal): Amount to consume in ingredient's recipe_unit

**Output**:
- `consumed` (Decimal): Actual amount consumed (may be less than needed if insufficient inventory)
- `breakdown` (List[Dict]): Detailed consumption per lot
- `shortfall` (Decimal): Amount still needed (quantity_needed - consumed)

**Pseudocode**:
```
function consume_fifo(session, ingredient_slug, quantity_needed):
    # Step 1: Query all pantry items for this ingredient, ordered by purchase date (oldest first)
    pantry_items = query(PantryItem)
        .join(Variant)
        .join(Ingredient)
        .filter(Ingredient.slug == ingredient_slug)
        .filter(PantryItem.quantity > 0)
        .order_by(PantryItem.purchase_date.asc())
        .all()

    # Step 2: Initialize tracking variables
    consumed = Decimal('0')
    breakdown = []
    remaining_needed = quantity_needed

    # Step 3: Iterate through lots in chronological order
    for pantry_item in pantry_items:
        if remaining_needed <= 0:
            break  # Satisfied demand, stop consuming

        # Determine how much to consume from this lot
        available_in_lot = pantry_item.quantity
        to_consume = min(available_in_lot, remaining_needed)

        # Update pantry item quantity
        pantry_item.quantity -= to_consume
        consumed += to_consume
        remaining_needed -= to_consume

        # Record consumption in breakdown
        breakdown.append({
            "pantry_item_id": pantry_item.id,
            "variant_id": pantry_item.variant_id,
            "lot_date": pantry_item.purchase_date,
            "quantity_consumed": to_consume,
            "unit": pantry_item.unit,
            "remaining_in_lot": pantry_item.quantity,
            "cost": to_consume * pantry_item.unit_cost_at_purchase  # If tracked
        })

        # Flush changes to database (still in transaction)
        session.flush()

    # Step 4: Calculate shortfall
    shortfall = quantity_needed - consumed

    # Step 5: Return results
    return {
        "consumed": consumed,
        "breakdown": breakdown,
        "shortfall": shortfall,
        "satisfied": shortfall == 0
    }
```

**Edge Cases Handled**:
1. **No inventory**: Returns consumed=0, shortfall=quantity_needed
2. **Insufficient inventory**: Consumes all available, returns shortfall > 0
3. **Partial lot consumption**: Updates lot quantity, keeps lot in database
4. **Exact match**: Consumes from lots until quantity_needed satisfied
5. **Multiple lots needed**: Iterates through lots, accumulating consumption

**Transaction Safety**:
- All pantry_item.quantity updates happen within single transaction (session_scope)
- If error occurs mid-consumption, session.rollback() reverts ALL quantity changes
- Breakdown includes partial consumption from last lot if applicable

**Cost Calculation** (if purchase price tracked):
```
total_cost = sum(item["cost"] for item in breakdown)
avg_cost_per_unit = total_cost / consumed if consumed > 0 else 0
```

---

### Preferred Variant Toggle Algorithm

**Purpose**: Ensure only one variant per ingredient is marked as preferred.

**Input**:
- `variant_id` (int): ID of variant to mark as preferred

**Output**:
- `variant` (Variant): Updated variant object with preferred=True

**Pseudocode**:
```
function set_preferred_variant(session, variant_id):
    # Step 1: Fetch the variant
    variant = query(Variant).filter_by(id=variant_id).first()
    if not variant:
        raise VariantNotFound(variant_id)

    # Step 2: Get ingredient_slug for this variant
    ingredient_slug = variant.ingredient_slug

    # Step 3: Clear preferred flag on all other variants for this ingredient
    query(Variant)
        .filter(Variant.ingredient_slug == ingredient_slug)
        .filter(Variant.id != variant_id)
        .update({"preferred": False})

    # Step 4: Set preferred flag on selected variant
    variant.preferred = True

    # Step 5: Flush changes (commits within session_scope transaction)
    session.flush()

    # Step 6: Return updated variant
    return variant
```

**Transaction Safety**:
- Both UPDATE (clear others) and SET (mark selected) happen in single transaction
- If error occurs, session.rollback() reverts both changes
- No race condition in single-user desktop app

---

### Slug Generation Algorithm

**Purpose**: Generate unique, URL-safe slugs from ingredient names.

**Input**:
- `name` (str): Ingredient name (e.g., "Confectioner's Sugar")
- `session` (Session, optional): For uniqueness check

**Output**:
- `slug` (str): URL-safe identifier (e.g., "confectioners_sugar")

**Pseudocode**:
```
function create_slug(name, session=None):
    # Step 1: Normalize Unicode (decompose accented characters)
    normalized = unicodedata.normalize('NFD', name)

    # Step 2: Convert to ASCII, lowercase
    slug = normalized.encode('ascii', 'ignore').decode('ascii').lower()

    # Step 3: Replace spaces and hyphens with underscores
    slug = regex_replace(r'[\s\-]+', '_', slug)

    # Step 4: Remove non-alphanumeric except underscores
    slug = regex_replace(r'[^a-z0-9_]', '', slug)

    # Step 5: Collapse multiple underscores to single
    slug = regex_replace(r'_+', '_', slug)

    # Step 6: Strip leading/trailing underscores
    slug = slug.strip('_')

    # Step 7: Handle empty slug
    if slug == '':
        slug = 'ingredient'

    # Step 8: Ensure uniqueness if session provided
    if session:
        original_slug = slug
        counter = 1
        while query(Ingredient).filter_by(slug=slug).exists():
            slug = f"{original_slug}_{counter}"
            counter += 1

    return slug
```

**Examples**:
- "All-Purpose Flour" → "all_purpose_flour"
- "Confectioner's Sugar" → "confectioners_sugar"
- "Semi-Sweet Chocolate Chips" → "semi_sweet_chocolate_chips"
- "Café au Lait" → "cafe_au_lait"
- "100% Pure Vanilla Extract" → "100_pure_vanilla_extract"

---

### Dependency Checking Algorithm

**Purpose**: Check if ingredient or variant can be safely deleted.

**Input**:
- `slug` (str): Ingredient slug to check

**Output**:
- `dependencies` (Dict[str, int]): Count of references per entity type

**Pseudocode**:
```
function check_ingredient_dependencies(session, slug):
    # Step 1: Verify ingredient exists
    ingredient = query(Ingredient).filter_by(slug=slug).first()
    if not ingredient:
        raise IngredientNotFoundBySlug(slug)

    # Step 2: Count references in each related entity
    dependencies = {
        "recipes": query(RecipeIngredient)
            .filter_by(ingredient_slug=slug)
            .count(),

        "variants": query(Variant)
            .filter_by(ingredient_slug=slug)
            .count(),

        "pantry_items": query(PantryItem)
            .join(Variant)
            .filter(Variant.ingredient_slug == slug)
            .count(),

        "unit_conversions": query(UnitConversion)
            .filter_by(ingredient_slug=slug)
            .count()
    }

    # Step 3: Return dependency counts
    return dependencies
```

**Usage**:
```
deps = check_ingredient_dependencies(session, "all_purpose_flour")
if sum(deps.values()) > 0:
    raise IngredientInUse(slug, dependencies=deps)
# Safe to delete
```

---

## Validation Rules Summary

### Ingredient Validation
- **Required**: name, slug, category, recipe_unit
- **Unique**: slug
- **Format**: slug (lowercase alphanumeric + underscores only)
- **Range**: name (1-200 chars), category (1-100 chars)
- **Business**: recipe_unit must be valid unit, density_g_per_ml must be positive

### Variant Validation
- **Required**: ingredient_slug, brand, purchase_unit, purchase_quantity
- **Foreign Key**: ingredient_slug must reference existing Ingredient
- **Format**: UPC (12-14 digits), GTIN (8-14 digits)
- **Range**: brand (1-200 chars)
- **Business**: purchase_quantity must be > 0, preferred toggle enforces single preferred per ingredient

### PantryItem Validation
- **Required**: variant_id, quantity, unit, purchase_date
- **Foreign Key**: variant_id must reference existing Variant
- **Range**: quantity >= 0, purchase_date cannot be future
- **Business**: expiration_date must be >= purchase_date

### Purchase Validation
- **Required**: variant_id, purchase_date, quantity, unit, unit_cost, total_cost
- **Foreign Key**: variant_id must reference existing Variant
- **Range**: quantity > 0, unit_cost >= 0 (allow zero for free items)
- **Business**: total_cost should equal quantity * unit_cost (with tolerance for rounding)

### UnitConversion Validation
- **Required**: ingredient_slug, from_unit, from_quantity, to_unit, to_quantity
- **Foreign Key**: ingredient_slug must reference existing Ingredient
- **Unique**: (ingredient_slug, from_unit, to_unit) combination
- **Range**: from_quantity > 0, to_quantity > 0

---

## Data Integrity Constraints

### Referential Integrity
1. **Variant.ingredient_slug** → **Ingredient.slug** (ON DELETE RESTRICT)
2. **PantryItem.variant_id** → **Variant.id** (ON DELETE RESTRICT)
3. **Purchase.variant_id** → **Variant.id** (ON DELETE CASCADE or RESTRICT - TBD)
4. **UnitConversion.ingredient_slug** → **Ingredient.slug** (ON DELETE CASCADE)
5. **RecipeIngredient.ingredient_slug** → **Ingredient.slug** (ON DELETE RESTRICT)

### Business Rule Constraints
1. **Only one preferred variant per ingredient**: Enforced by service layer (application-level)
2. **Non-negative pantry quantities**: Enforced by service layer (FIFO consumption stops at 0)
3. **Unique ingredient slugs**: Enforced by database UNIQUE constraint + service layer uniqueness check
4. **Valid units**: Enforced by service layer validation (check against unit_converter.py known units)

---

**Data Model Status**: ✅ **COMPLETE** - All entities documented, algorithms defined, validation rules specified. Ready for Phase 1 contracts generation.
