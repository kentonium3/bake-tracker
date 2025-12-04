# Quickstart: Variant-Aware Shopping List Recommendations

**Feature**: 007-variant-aware-shopping
**Date**: 2025-12-04

## Overview

This feature enhances the shopping list to show variant-aware purchase recommendations with cost information.

## Prerequisites

- Feature 006 (Event Planning Restoration) complete
- Working EventService.get_shopping_list() method
- Ingredients with configured Variants in database

## Implementation Order

### Phase 1: Service Layer

1. **VariantService Extensions** (`src/services/variant_service.py`)
   - Add `get_variant_recommendation(ingredient_slug, shortfall, recipe_unit)` method
   - Returns VariantRecommendation with cost calculations
   - Handles preferred vs multiple variants logic

2. **EventService Extensions** (`src/services/event_service.py`)
   - Modify `get_shopping_list()` to call VariantService for each shortfall item
   - Add variant_recommendation, all_variants, variant_status fields
   - Calculate total_estimated_cost across all items

### Phase 2: UI Layer

3. **Shopping List Table** (`src/ui/event_planning_tab.py`)
   - Add columns: Variant, Package Size, Cost/Unit, Est. Cost
   - Handle vertically stacked rows for multiple variants
   - Display total estimated cost at bottom

### Phase 3: Testing

4. **Unit Tests** (`src/tests/test_variant_service.py`)
   - Test get_variant_recommendation with preferred variant
   - Test get_variant_recommendation with multiple variants
   - Test get_variant_recommendation with no variants
   - Test cost calculations and unit conversions

5. **Integration Tests** (`src/tests/test_event_service.py`)
   - Test full shopping list with variant recommendations
   - Test total cost calculation

## Key Functions to Implement

```python
# VariantService
def get_variant_recommendation(
    ingredient_slug: str,
    shortfall: Decimal,
    recipe_unit: str
) -> Dict[str, Any]:
    """
    Get variant recommendation for an ingredient shortfall.

    Returns:
        {
            'variant_status': 'preferred' | 'multiple' | 'none',
            'variant_recommendation': VariantRecommendation or None,
            'all_variants': List[VariantRecommendation]
        }
    """
    pass
```

```python
# Helper function
def calculate_variant_cost(
    variant: Variant,
    shortfall: Decimal,
    recipe_unit: str
) -> VariantRecommendation:
    """
    Calculate cost metrics for a variant given a shortfall.

    Steps:
    1. Get cost_per_purchase_unit from variant.get_current_cost_per_unit()
    2. Convert shortfall from recipe_unit to purchase_unit
    3. Calculate min_packages = ceil(shortfall_in_purchase_units / package_quantity)
    4. Calculate total_cost = min_packages * package_quantity * cost_per_purchase_unit
    5. Calculate cost_per_recipe_unit using unit conversion
    """
    pass
```

## Test Data Setup

```python
# Example test fixture
def setup_test_data():
    # Ingredient
    flour = Ingredient(name="All-Purpose Flour", slug="all-purpose-flour", recipe_unit="cup")

    # Variants
    king_arthur = Variant(
        ingredient=flour,
        brand="King Arthur",
        package_size="25 lb bag",
        purchase_unit="lb",
        purchase_quantity=25.0,
        preferred=True
    )

    generic = Variant(
        ingredient=flour,
        brand="Store Brand",
        package_size="5 lb bag",
        purchase_unit="lb",
        purchase_quantity=5.0,
        preferred=False
    )

    # Purchase history (for cost)
    Purchase(variant=king_arthur, unit_cost=0.72, purchase_date=date.today())
    Purchase(variant=generic, unit_cost=0.48, purchase_date=date.today())
```

## Acceptance Criteria Checklist

- [ ] FR-001: Preferred variant shown as recommendation
- [ ] FR-002: All variants listed when no preferred
- [ ] FR-003: "No variant configured" for missing variants
- [ ] FR-004: Cost per recipe unit displayed
- [ ] FR-005: Package size context displayed
- [ ] FR-006: Minimum packages calculated correctly
- [ ] FR-007: Total estimated cost calculated
- [ ] FR-008: Unit conversion between recipe/purchase units
- [ ] FR-009: Existing shopping list functionality preserved
- [ ] FR-010: "Cost unknown" for variants without purchases
