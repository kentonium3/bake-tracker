# Research: Variant-Aware Shopping List Recommendations

**Feature**: 007-variant-aware-shopping
**Date**: 2025-12-04
**Status**: Complete

## Research Questions

### Q1: How does cost tracking work in bake-tracker?

**Decision**: Use existing `Variant.get_current_cost_per_unit()` method

**Rationale**: The codebase already has a robust cost tracking system:
- `Purchase` model stores `unit_cost` per purchase transaction
- `PantryItem` model stores `unit_cost` at time of acquisition (for FIFO)
- `Variant.get_current_cost_per_unit()` returns most recent purchase price
- `Variant.get_average_price(days)` returns rolling average

For shopping recommendations, most recent purchase price is appropriate (user will pay current market price, not FIFO historical cost).

**Alternatives Considered**:
- Average price over N days - rejected (current price more relevant for shopping)
- FIFO pantry cost - rejected (FIFO is for consumption tracking, not purchase planning)

### Q2: How are variants queried and which is preferred?

**Decision**: Use existing `VariantService` methods

**Rationale**: VariantService already provides:
- `get_preferred_variant(ingredient_slug)` - returns preferred or None
- `get_variants_for_ingredient(ingredient_slug)` - returns all, sorted with preferred first

These methods directly support the spec's requirements:
- FR-001: Show preferred variant recommendation
- FR-002: List all variants when no preferred is marked

**Alternatives Considered**:
- Query variants directly from Ingredient model - works but VariantService provides better abstraction
- Add new query methods - unnecessary, existing methods sufficient

### Q3: How does unit conversion between recipe_unit and purchase_unit work?

**Decision**: Use existing `unit_converter.convert_any_units()` function

**Rationale**: The unit converter already handles:
- Weight-to-weight conversions (lb, oz, g, kg)
- Volume-to-volume conversions (cup, tbsp, tsp, ml, L)
- Cross-type conversions using ingredient density (`density_g_per_ml`)
- Custom ingredient-specific conversions via `UnitConversion` table

Key function: `convert_any_units(value, from_unit, to_unit, ingredient_name)` returns `(success, converted_value, message)`

**Alternatives Considered**:
- Hardcode common conversions - rejected (existing system more comprehensive)
- Require purchase_unit = recipe_unit - rejected (too restrictive)

### Q4: What is the current shopping list structure?

**Decision**: Extend `get_shopping_list()` return structure with variant data

**Rationale**: Current return format from `EventService.get_shopping_list()`:
```python
{
    'ingredient_id': int,
    'ingredient_name': str,
    'unit': str,
    'quantity_needed': Decimal,
    'quantity_on_hand': Decimal,
    'shortfall': Decimal
}
```

Extension adds variant recommendation fields:
```python
{
    # ... existing fields ...
    'variant_recommendation': {
        'variant_id': int,
        'brand': str,
        'package_size': str,
        'package_quantity': float,  # e.g., 25 for "25 lb bag"
        'purchase_unit': str,
        'cost_per_purchase_unit': Decimal,
        'cost_per_recipe_unit': Decimal,
        'min_packages': int,
        'total_cost': Decimal,
        'is_preferred': bool
    },
    'all_variants': List[...],  # When no preferred, list all options
    'variant_status': str  # 'preferred', 'multiple', 'none'
}
```

**Alternatives Considered**:
- Return flat structure - rejected (variant data is complex, nesting clearer)
- Create separate endpoint - rejected (shopping list and recommendations are one view)

### Q5: What UI components exist for the shopping list?

**Decision**: Extend existing shopping list table in `event_planning_tab.py`

**Rationale**: Feature 006 created the shopping list tab with columns:
- Ingredient, Needed, On Hand, To Buy

New columns to add:
- Variant (brand + package description)
- Package Size (e.g., "25 lb = 90 cups")
- Cost/Unit (e.g., "$0.18/cup")
- Est. Cost (total purchase cost)

For multiple variants (no preferred), display as vertically stacked rows under the ingredient per clarification from spec.

**Alternatives Considered**:
- Expandable accordion - rejected (user preferred simple stacked rows)
- Tooltip on hover - rejected (important info should be visible without interaction)

## Key Code Locations

| Component | File | Key Methods/Classes |
|-----------|------|---------------------|
| Variant model | `src/models/variant.py` | `get_current_cost_per_unit()`, `get_most_recent_purchase()` |
| Purchase model | `src/models/purchase.py` | `unit_cost` field, `get_most_recent_price()` |
| VariantService | `src/services/variant_service.py` | `get_preferred_variant()`, `get_variants_for_ingredient()` |
| EventService | `src/services/event_service.py` | `get_shopping_list()` |
| Unit converter | `src/services/unit_converter.py` | `convert_any_units()`, `calculate_cost_per_recipe_unit()` |
| Shopping list UI | `src/ui/event_planning_tab.py` | Shopping list table (to be extended) |

## Research Artifacts

- [evidence-log.csv](research/evidence-log.csv) - Code snippets and decisions
- [source-register.csv](research/source-register.csv) - Files consulted

## Summary

The existing bake-tracker codebase provides all necessary infrastructure for variant-aware shopping:

1. **Cost data**: `Variant.get_current_cost_per_unit()` returns most recent purchase price
2. **Preferred variant**: `VariantService.get_preferred_variant()` returns preferred or None
3. **All variants**: `VariantService.get_variants_for_ingredient()` returns all options
4. **Unit conversion**: `unit_converter.convert_any_units()` handles recipe-to-purchase conversion
5. **Shopping list base**: `EventService.get_shopping_list()` provides shortfall calculation

Implementation requires:
- Adding variant recommendation methods to VariantService (new)
- Extending EventService.get_shopping_list() to include variant data
- Adding columns to shopping list UI table
- Calculating total estimated cost
