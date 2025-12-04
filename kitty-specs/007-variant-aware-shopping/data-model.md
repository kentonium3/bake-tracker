# Data Model: Variant-Aware Shopping List Recommendations

**Feature**: 007-variant-aware-shopping
**Date**: 2025-12-04

## Overview

This feature extends the shopping list with variant recommendations. No new database tables are required - the feature uses existing models and extends the shopping list data structure returned by services.

## Existing Entities (Referenced)

### Ingredient

**Table**: `products` (via Ingredient model)
**File**: `src/models/ingredient.py`

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| name | String | Display name (e.g., "All-Purpose Flour") |
| slug | String | URL-safe identifier |
| category | String | Category for grouping |
| recipe_unit | String | Default unit in recipes (e.g., "cup") |
| density_g_per_ml | Float | For volume-to-weight conversion |

**Relationships**:
- `variants` (1:N) - All brand/package variants for this ingredient

### Variant

**Table**: `product_variants` (via Variant model)
**File**: `src/models/variant.py`

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| ingredient_id | Integer | FK to Ingredient |
| brand | String | Brand name (e.g., "King Arthur") |
| package_size | String | Human-readable size (e.g., "25 lb bag") |
| package_type | String | Package type (bag, box, jar) |
| purchase_unit | String | Unit purchased in (e.g., "lb") |
| purchase_quantity | Float | Quantity per package (e.g., 25.0) |
| preferred | Boolean | Is this the preferred variant? |
| supplier | String | Where to buy (optional) |

**Key Methods**:
- `get_current_cost_per_unit()` -> Float: Most recent purchase price per purchase_unit
- `get_most_recent_purchase()` -> Purchase: Most recent purchase record

### Purchase

**Table**: `purchases` (via Purchase model)
**File**: `src/models/purchase.py`

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| variant_id | Integer | FK to Variant |
| purchase_date | Date | When purchased |
| unit_cost | Float | Cost per purchase_unit |
| quantity_purchased | Float | Number of units bought |
| total_cost | Float | Total purchase cost |

## Extended Data Structures (Service Layer)

### ShoppingListItem (Extended)

**Source**: `EventService.get_shopping_list()` return value
**Type**: Dict (Python dictionary, not a model)

```python
@dataclass
class VariantRecommendation:
    """Recommendation for a single variant."""
    variant_id: int
    brand: str
    package_size: str           # e.g., "25 lb bag"
    package_quantity: float     # e.g., 25.0
    purchase_unit: str          # e.g., "lb"
    cost_per_purchase_unit: Decimal  # e.g., 0.72 ($/lb)
    cost_per_recipe_unit: Decimal    # e.g., 0.18 ($/cup)
    min_packages: int           # Minimum packages to cover shortfall
    total_cost: Decimal         # min_packages * package_quantity * cost_per_purchase_unit
    is_preferred: bool          # True if this is the preferred variant


@dataclass
class ShoppingListItem:
    """Extended shopping list item with variant recommendations."""
    # Existing fields (from Feature 006)
    ingredient_id: int
    ingredient_name: str
    unit: str                   # recipe_unit
    quantity_needed: Decimal
    quantity_on_hand: Decimal
    shortfall: Decimal          # max(0, needed - on_hand)

    # New fields (Feature 007)
    variant_status: str         # 'preferred' | 'multiple' | 'none'
    variant_recommendation: Optional[VariantRecommendation]  # Primary recommendation
    all_variants: List[VariantRecommendation]  # All options (when status='multiple')
```

### ShoppingListSummary

**New structure for aggregated totals**

```python
@dataclass
class ShoppingListSummary:
    """Summary totals for shopping list."""
    total_items: int                    # Number of ingredients with shortfall
    items_with_recommendations: int     # Items that have variant data
    items_without_variants: int         # Items with 'none' status
    total_estimated_cost: Decimal       # Sum of all recommended purchase costs
```

## Calculations

### Cost Per Recipe Unit

```
cost_per_recipe_unit = cost_per_purchase_unit / conversion_factor

Where:
- cost_per_purchase_unit = Variant.get_current_cost_per_unit()
- conversion_factor = UnitConversion(purchase_unit -> recipe_unit)

Example:
- Flour costs $0.72/lb
- 1 lb = 4 cups (conversion factor = 4)
- cost_per_recipe_unit = $0.72 / 4 = $0.18/cup
```

### Minimum Packages

```
min_packages = ceil(shortfall_in_purchase_units / package_quantity)

Where:
- shortfall_in_purchase_units = convert(shortfall, recipe_unit, purchase_unit)
- package_quantity = Variant.purchase_quantity

Example:
- Shortfall: 10 cups
- Convert to purchase unit: 10 cups = 2.5 lb
- Package: 25 lb bag
- min_packages = ceil(2.5 / 25) = 1
```

### Total Cost

```
total_cost = min_packages * package_quantity * cost_per_purchase_unit

Example:
- min_packages = 1
- package_quantity = 25 lb
- cost_per_purchase_unit = $0.72/lb
- total_cost = 1 * 25 * $0.72 = $18.00
```

## State Transitions

```
variant_status determination:

    IF ingredient has variants:
        IF any variant has preferred=True:
            status = 'preferred'
            recommendation = preferred variant
            all_variants = [preferred variant]
        ELSE:
            status = 'multiple'
            recommendation = None
            all_variants = [all variants sorted by cost]
    ELSE:
        status = 'none'
        recommendation = None
        all_variants = []
```

## UI Display Mapping

| variant_status | Display Behavior |
|----------------|------------------|
| `preferred` | Single row with recommended variant, "[preferred]" indicator |
| `multiple` | Vertically stacked rows, one per variant, no highlight |
| `none` | "No variant configured" in recommendation column |

## No Schema Changes Required

This feature does not require database migrations. All changes are:
1. Service layer logic (VariantService, EventService)
2. Data structure extensions (dictionaries/dataclasses)
3. UI display logic
