# Ingredient/Variant Refactoring - Status Report

**Branch:** `feature/product-pantry-refactor`
**Started:** 2025-11-06
**Status:** ⏸️ PAUSED - Planning Complete, Implementation Deferred
**Terminology:** Using "Ingredient/Variant" (not Product/ProductVariant)

> **NOTE:** This document was created with "Product" terminology but has been conceptually updated to "Ingredient/Variant". When resuming, models will be renamed:
> - Product → Ingredient
> - ProductVariant → Variant
> - ProductAlias → IngredientAlias
> - ProductCrosswalk → IngredientCrosswalk
>
> **See `PAUSE_POINT.md` for current status and next steps.**

---

## ✅ Phase 1: New Models Created (COMPLETE)

### Models Implemented

#### 1. Product Model (`src/models/product.py`)
**Purpose:** Generic ingredient definitions - the "platonic ideal" of an ingredient

**Key Features:**
- Brand-agnostic definition (e.g., "All-Purpose Flour")
- Multiple variants per product
- Recipe unit specification
- Category-based organization
- Conversion factors via UnitConversion table

**Relationships:**
- One-to-many with ProductVariant
- One-to-many with UnitConversion
- One-to-many with RecipeIngredient (recipes reference products, not variants)

---

#### 2. ProductVariant Model (`src/models/product_variant.py`)
**Purpose:** Specific purchasable versions with brand, package size, supplier

**Key Features:**
- Brand and package information (e.g., "King Arthur 25 lb bag")
- UPC code support (for future mobile scanning)
- Preferred variant flag
- Purchase unit and quantity tracking
- Supplier/SKU tracking

**Calculated Properties:**
- `display_name` - Formatted name (e.g., "King Arthur 25 lb bag")
- `get_most_recent_purchase()` - Latest purchase for price
- `get_average_price(days)` - Average cost over time period
- `get_current_cost_per_unit()` - Most recent unit cost
- `get_total_pantry_quantity()` - Sum across all pantry items

**Relationships:**
- Many-to-one with Product
- One-to-many with PurchaseHistory
- One-to-many with PantryItem

---

#### 3. PurchaseHistory Model (`src/models/purchase_history.py`)
**Purpose:** Track all purchase transactions for price trend analysis

**Key Features:**
- Purchase date, quantity, unit cost, total cost
- Supplier and receipt number tracking
- Price trend analysis functions

**Module-Level Functions:**
- `get_average_price(variant_id, days)` - Calculate average over time
- `get_most_recent_price(variant_id)` - Latest purchase price
- `get_price_trend(variant_id, days)` - Trend analysis (increasing/decreasing/stable)

**Returns trend data:**
```python
{
    "average": 15.99,
    "min": 14.99,
    "max": 17.99,
    "trend": "increasing",  # or "decreasing" or "stable"
    "percent_change": 8.5   # % change from oldest to newest
}
```

---

#### 4. PantryItem Model (`src/models/pantry_item.py`)
**Purpose:** Actual inventory tracking with FIFO support

**Key Features:**
- Quantity on hand (in purchase units)
- Purchase date (for FIFO ordering)
- Expiration date tracking
- Opened date tracking
- Location tracking (e.g., "Main Pantry", "Garage Shelf 2")
- FIFO consumption methods

**Calculated Properties:**
- `is_expired` - Check if past expiration
- `is_opened` - Check if package opened
- `days_until_expiration` - Days remaining
- `is_expiring_soon(days)` - Check if expiring within threshold

**Instance Methods:**
- `update_quantity(new_quantity)` - Set quantity
- `consume(quantity)` - FIFO consumption from this item
- `add_quantity(quantity)` - Add to this item

**Module-Level FIFO Functions:**
- `get_pantry_items_fifo(product_id, session)` - Get items ordered by purchase date
- `consume_fifo(product_id, quantity, session)` - Consume across multiple items using FIFO
- `get_expiring_soon(days, session)` - All items expiring soon
- `get_total_quantity_for_product(product_id, session)` - Aggregate by product

**FIFO Consumption Example:**
```python
# Recipe needs 10 cups flour
consumed, breakdown = consume_fifo(product_id=1, quantity_needed=10.0, session=session)

# Returns:
# consumed = 10.0 (total consumed)
# breakdown = [
#     {"item_id": 5, "variant_id": 12, "quantity": 8.0, "cost": 1.42, "purchase_date": "2024-10-01"},
#     {"item_id": 6, "variant_id": 12, "quantity": 2.0, "cost": 0.40, "purchase_date": "2024-11-01"}
# ]
```

---

#### 5. UnitConversion Model (`src/models/unit_conversion.py`)
**Purpose:** Product-specific conversion factors

**Key Features:**
- From/to unit conversion specifications
- Multiple conversions per product (e.g., lb→cup, kg→cup)
- Notes for context (e.g., "sifted", "packed")

**Module-Level Functions:**
- `get_conversion(product_id, from_unit, to_unit, session)` - Find conversion
- `convert_quantity(product_id, quantity, from_unit, to_unit, session)` - Convert
- `create_standard_conversions(product_id, name, session)` - Auto-create from density data

**Example:**
```python
# All-Purpose Flour conversion
{
    "from_unit": "lb",
    "from_quantity": 1.0,
    "to_unit": "cup",
    "to_quantity": 3.6,
    "notes": "Unsifted, spooned and leveled"
}

# Conversion factor: 1 lb = 3.6 cups
```

---

### RecipeIngredient Updates

**Added Fields:**
- `product_id` (Integer, FK to Product) - NEW: brand-agnostic reference
- `ingredient_id` (nullable) - LEGACY: kept for migration compatibility

**Relationships:**
- `product` - Many-to-one with Product (NEW)
- `ingredient` - Many-to-one with Ingredient (LEGACY)

**Migration Strategy:**
- Both FKs exist during transition
- Migration script will populate product_id from ingredient_id
- After migration complete, ingredient_id will be removed

---

## Design Decisions Implemented

### 1. FIFO Costing Strategy ✅

**Decision:** Use FIFO (First In, First Out) for both consumption and cost calculation

**Rationale:**
- Matches physical inventory flow (use oldest first)
- Natural fit for lot tracking (each lot has purchase date and cost)
- Accurate recipe costing when prices fluctuate
- Standard in food/manufacturing industries

**Implementation:**
```python
# When recipe consumes ingredients:
1. Get pantry items ordered by purchase_date (oldest first)
2. Consume from each item in order
3. Track cost per item consumed
4. Return total cost breakdown by lot
```

**Benefits for Future:**
- When lot tracking added, each PantryItem becomes a lot
- No refactoring needed - FIFO logic already in place
- Expiration tracking works naturally with FIFO

---

### 2. Recipes Reference Products (Not Variants) ✅

**Decision:** RecipeIngredient links to Product, not ProductVariant

**Rationale:**
- Recipes should be brand-agnostic
- "2 cups All-Purpose Flour" doesn't care about brand
- User can switch brands without updating recipes
- Shopping lists suggest variants based on preferences

**Example:**
```python
# Recipe says: "2 cups All-Purpose Flour"
recipe_ingredient = {
    "product_id": 1,  # All-Purpose Flour (generic)
    "quantity": 2.0,
    "unit": "cup"
}

# Cost calculation uses preferred or FIFO from pantry
# Shopping list recommends: "King Arthur 25 lb bag (preferred)"
```

---

### 3. Separate Product and Pantry Tabs ✅

**Decision:** Two separate tabs in UI

**Benefits:**
- "My Products" tab: Manage product catalog, variants, conversions
- "My Pantry" tab: View/manage actual inventory, locations, expiration
- Cleaner separation of concerns
- Easier to add features (e.g., pantry locations, expiration alerts)
- Reduces cognitive load (cataloging vs inventory management)

---

### 4. Deferred Features ✅

**Mobile App:** Deferred until commercial product decision
**Supplier APIs:** Deferred - "Brand" field sufficient for now
**Store Concept:** Future enhancement - stores treated as brands for now

---

## Database Schema Summary

```
Product (Generic ingredient)
├─ name, category, recipe_unit
├─ ProductVariant (Specific brand/package)
│  ├─ brand, package_size, package_type, preferred
│  ├─ PurchaseHistory (Price tracking)
│  │  └─ purchase_date, unit_cost, quantity, supplier
│  └─ PantryItem (Actual inventory)
│     └─ quantity, purchase_date, expiration_date, location
└─ UnitConversion (Product-specific conversions)
   └─ from_unit, to_unit, conversion_factor

Recipe
└─ RecipeIngredient
   ├─ product_id (NEW - brand-agnostic)
   └─ ingredient_id (LEGACY - migration only)
```

---

## Next Steps

### Phase 2: Migration Script (Up Next)

**Goal:** Convert existing Ingredient records to new schema

**Script location:** `src/utils/migrate_to_product_pantry.py`

**Logic:**
```python
for each Ingredient:
    1. Create Product (generic ingredient)
    2. Create ProductVariant (current brand/package as "preferred")
    3. Create PantryItem (if quantity > 0)
    4. Create UnitConversion (from conversion_factor)
    5. Create PurchaseHistory (if unit_cost > 0)
    6. Update RecipeIngredient.product_id
```

**Validation:**
- Verify all Ingredients migrated
- Confirm RecipeIngredient references updated
- Test cost calculations match old vs new
- Ensure shopping lists produce same results

---

### Phase 3: Service Layer

**New Services to Create:**

1. **ProductService** - Product catalog CRUD
2. **ProductVariantService** - Variant management
3. **PantryService** - Inventory operations with FIFO
4. **PurchaseService** - Purchase history tracking

**Services to Update:**

1. **RecipeService** - Use FIFO costing for calculate_recipe_cost()
2. **EventService** - Update generate_shopping_list() for variants

---

### Phase 4: UI Updates

**New Tabs:**
- "My Products" tab (replaces "Inventory")
- "My Pantry" tab (new)

**Updated Forms:**
- Product form (name, category, recipe unit)
- Product variant form (brand, package, UPC, preferred)
- Pantry item form (variant, quantity, location, expiration)
- Recipe ingredient selector (products, not variants)

**Updated Views:**
- Shopping list (show variant recommendations)
- Dashboard (aggregate inventory by product)

---

## Cost Calculation Strategy

### FIFO Costing Implementation

**Primary Strategy:** FIFO (First In, First Out)

**How It Works:**
1. When calculating recipe cost, query pantry items by purchase date
2. Consume from oldest items first
3. Track cost from each item's variant's most recent purchase
4. Sum costs across all items consumed

**Fallback:** If insufficient inventory, use preferred variant price

**Code Example:**
```python
def calculate_recipe_cost_fifo(recipe_id):
    total_cost = 0

    for recipe_ingredient in recipe.ingredients:
        product_id = recipe_ingredient.product_id
        quantity_needed = recipe_ingredient.quantity

        # Consume using FIFO and get cost breakdown
        consumed, cost_breakdown = consume_fifo(
            product_id=product_id,
            quantity_needed=quantity_needed,
            session=session
        )

        # Sum costs from each lot consumed
        for item_cost in cost_breakdown:
            total_cost += item_cost["cost"]

        # If insufficient inventory, estimate remaining
        if consumed < quantity_needed:
            remaining = quantity_needed - consumed
            preferred_variant = get_preferred_variant(product_id)
            fallback_cost = remaining * preferred_variant.get_current_cost_per_unit()
            total_cost += fallback_cost

    return total_cost
```

---

## Testing Strategy

### Unit Tests Needed

**Model Tests:**
- Product CRUD operations
- ProductVariant preferred flag logic
- PurchaseHistory price trend calculations
- PantryItem FIFO consumption
- UnitConversion conversion accuracy

**Service Tests:**
- ProductService CRUD
- PantryService FIFO operations
- FIFO cost calculation accuracy
- Shopping list variant recommendations

**Migration Tests:**
- Ingredient → Product/Variant/Pantry migration
- RecipeIngredient product_id population
- Cost calculation equivalence (old vs new)

---

## Branch Strategy

**Main Branch (`main`):**
- v0.3.0 stable
- Ready for Marianne's testing
- Bug fixes and minor improvements only

**Feature Branch (`feature/product-pantry-refactor`):**
- Product/Pantry refactoring
- New models, services, UI
- Parallel development during v0.3.x testing
- Merge when v0.3.x stabilizes
- Release as v0.4.0

**Workflow:**
```
main (v0.3.x) ───────────────────→ v0.3.1 → v0.3.2 → merge
                                                           ↓
feature/product-pantry ──→ models → services → UI → v0.4.0
```

---

## File Structure

```
src/
├── models/
│   ├── product.py                    # NEW
│   ├── product_variant.py            # NEW
│   ├── purchase_history.py           # NEW
│   ├── pantry_item.py                # NEW
│   ├── unit_conversion.py            # NEW
│   ├── ingredient.py                 # LEGACY (for migration)
│   ├── recipe.py                     # UPDATED (product_id added)
│   └── __init__.py                   # UPDATED
├── services/
│   ├── product_service.py            # TODO
│   ├── product_variant_service.py    # TODO
│   ├── pantry_service.py             # TODO
│   ├── purchase_service.py           # TODO
│   ├── recipe_service.py             # TODO (update for FIFO)
│   └── inventory_service.py          # LEGACY (keep for migration)
├── ui/
│   ├── tabs/
│   │   ├── my_products_tab.py        # TODO
│   │   ├── my_pantry_tab.py          # TODO
│   │   └── inventory_tab.py          # LEGACY (hide after migration)
│   └── forms/
│       ├── product_form.py           # TODO
│       ├── product_variant_form.py   # TODO
│       └── pantry_item_form.py       # TODO
└── utils/
    └── migrate_to_product_pantry.py  # TODO
```

---

## Commit History

**Commit 1 (aab0160):** Complete v0.3.0 - Full import/export and naming fixes
- Main branch stable, ready for testing

**Commit 2 (d475e18):** Add Product/Pantry models for inventory refactoring
- Feature branch with new models
- RecipeIngredient updated for dual FK support
- FIFO logic implemented in pantry_item module
- Price trend analysis in purchase_history module

---

## Questions & Decisions

### Resolved ✅

1. **Migration timing?** → Start in parallel with v0.3.x testing
2. **Cost calculation strategy?** → FIFO (matches consumption, extends to lots)
3. **Tab organization?** → Separate "My Products" and "My Pantry" tabs
4. **Mobile priority?** → Defer until commercial product decision
5. **Supplier API?** → Defer, treat stores as brands for now

### Resolved Decisions (2025-11-06) ✅

1. **Pantry item merging:** → **Option A: Always create separate items (lots)**
   - Each purchase creates new PantryItem record
   - FIFO works properly with distinct purchase dates
   - UI groups by variant but shows individual items with quantities
   - Matches physical reality in pantry

2. **Location field:** → **Add to DB, hide in UI (future feature)**
   - PantryItem.location field exists in database
   - Default value: "Main Pantry"
   - Not exposed in UI initially
   - Will be added as future feature with location management

3. **Multiple conversion paths:** → **Yes, support chained conversions**
   - Enable lb→oz→cup type conversions
   - UnitConversion service will support multi-step paths
   - Fallback to standard conversions when product-specific not available

### Open Questions ❓

1. **Price alerts:** Notify when price changes significantly? What threshold?
2. **Food industry standard fields:** PENDING - Additional Product table specifications coming

---

**Next Session:** Create migration script (`migrate_to_product_pantry.py`)

**Status:** ✅ Phase 1 Complete - Models ready for testing and service implementation

**Last Updated:** 2025-11-06
