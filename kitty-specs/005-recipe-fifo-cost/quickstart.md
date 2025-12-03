# Quickstart: Recipe FIFO Cost Integration

**Feature**: 005-recipe-fifo-cost
**Date**: 2025-12-02

## Overview

This feature adds FIFO-based cost calculation to RecipeService, enabling accurate recipe costing based on actual pantry inventory costs.

## New Methods

### RecipeService

```python
# Calculate actual cost using FIFO pantry inventory
total_cost = recipe_service.calculate_actual_cost(recipe_id=42)

# Calculate estimated cost using preferred variant pricing
total_cost = recipe_service.calculate_estimated_cost(recipe_id=42)
```

### PantryService (Modified)

```python
# Existing usage (actual consumption)
result = pantry_service.consume_fifo(ingredient_slug="flour", quantity_needed=Decimal("2.0"))

# New: dry-run mode for cost calculation (no database changes)
result = pantry_service.consume_fifo(
    ingredient_slug="flour",
    quantity_needed=Decimal("2.0"),
    dry_run=True  # NEW PARAMETER
)
```

## Usage Examples

### Example 1: Get Actual Recipe Cost

```python
from src.services.recipe_service import recipe_service

# Returns total cost based on FIFO pantry inventory
cost = recipe_service.calculate_actual_cost(recipe_id=42)
print(f"Recipe will cost ${cost:.2f} using pantry inventory")
```

### Example 2: Get Estimated Recipe Cost (Planning)

```python
from src.services.recipe_service import recipe_service

# Returns estimated cost based on preferred variant pricing
cost = recipe_service.calculate_estimated_cost(recipe_id=42)
print(f"Recipe estimated at ${cost:.2f} using current prices")
```

### Example 3: Simulate FIFO Consumption (Read-Only)

```python
from src.services.pantry_service import pantry_service
from decimal import Decimal

# Simulate consumption without modifying pantry
result = pantry_service.consume_fifo(
    ingredient_slug="all-purpose-flour",
    quantity_needed=Decimal("3.0"),
    dry_run=True
)

print(f"Would consume: {result['consumed']} units")
print(f"Shortfall: {result['shortfall']} units")
print(f"Fully satisfied: {result['satisfied']}")

# Breakdown shows FIFO order
for lot in result['breakdown']:
    print(f"  Lot {lot['lot_date']}: {lot['quantity_consumed']} {lot['unit']}")
```

## Error Handling

```python
from src.services.exceptions import RecipeNotFound, IngredientNotFound, ValidationError

try:
    cost = recipe_service.calculate_actual_cost(recipe_id=999)
except RecipeNotFound:
    print("Recipe does not exist")
except IngredientNotFound as e:
    print(f"Ingredient missing: {e}")
except ValidationError as e:
    print(f"Cannot cost recipe: {e}")
    # e.g., missing variant, no pricing data, missing density
```

## Costing Modes

| Mode | Method | When to Use | Data Source |
|------|--------|-------------|-------------|
| Actual | `calculate_actual_cost()` | Before baking | FIFO pantry + fallback to preferred variant |
| Estimated | `calculate_estimated_cost()` | Planning/shopping | Preferred variant most recent price |

## Key Behaviors

1. **FIFO Ordering**: Oldest pantry items (by purchase_date) are costed first
2. **Read-Only**: Cost calculations never modify pantry inventory
3. **Partial Inventory**: When pantry is insufficient, shortfall uses preferred variant pricing
4. **Unit Conversion**: Automatic conversion between recipe units and pantry/purchase units
5. **Fail Fast**: Raises exception if any ingredient cannot be costed (no partial results)

## Prerequisites

Before using recipe costing:

1. **Ingredients** must have at least one Variant defined
2. **Variants** must have at least one Purchase with pricing
3. **Density** required for volume/weight conversions (via `INGREDIENT_DENSITIES` constants)

Missing any of these will raise a `ValidationError` with a descriptive message.
