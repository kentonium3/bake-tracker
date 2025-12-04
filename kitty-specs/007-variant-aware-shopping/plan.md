# Implementation Plan: Variant-Aware Shopping List Recommendations

**Branch**: `007-variant-aware-shopping` | **Date**: 2025-12-04 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/007-variant-aware-shopping/spec.md`

## Summary

Enhance the shopping list (from Feature 006) to display variant-aware purchase recommendations. For each ingredient with a shortfall, the system will show the preferred variant (or all variants if none preferred), package size context, cost per recipe unit, minimum packages to buy, and total estimated cost. Implementation extends `VariantService` with recommendation methods and adds columns to the existing shopping list UI.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: CustomTkinter, SQLAlchemy 2.x, SQLite
**Storage**: SQLite with WAL mode
**Testing**: pytest with >70% service coverage
**Target Platform**: Desktop (macOS, Windows, Linux)
**Project Type**: Single desktop application
**Performance Goals**: Shopping list tab loads in <2 seconds (per SC-005)
**Constraints**: Single-user, offline-capable, no external API dependencies
**Scale/Scope**: Single user, ~100 ingredients, ~50 variants typical

## Engineering Alignment

| Decision | Choice |
|----------|--------|
| **Architecture** | Add variant recommendation methods to `VariantService`; `EventService` calls them |
| **Cost Data** | Use existing cost tracking infrastructure (research findings below) |
| **UI Approach** | Add columns to existing shopping list table (Variant, Package Size, Cost/Unit, Est. Cost) |

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Layered Architecture | PASS | UI calls Service, Service calls Models - no violations |
| II. Build for Today | PASS | Extends existing services, no premature optimization |
| III. FIFO Accuracy | PASS | Cost data uses actual purchase costs via existing infrastructure |
| IV. User-Centric Design | PASS | Displays actionable purchase recommendations |
| V. Test-Driven Development | PASS | Service methods will have unit tests |
| VI. Migration Safety | PASS | No schema changes required - extends ShoppingListItem data structure only |

## Project Structure

### Documentation (this feature)

```
kitty-specs/007-variant-aware-shopping/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (internal service contracts)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks command)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── ingredient.py     # Existing - Ingredient model
│   └── variant.py        # Existing - Variant model with preferred flag
├── services/
│   ├── variant_service.py   # MODIFY - Add recommendation methods
│   ├── event_service.py     # MODIFY - Call variant recommendations in shopping list
│   └── unit_converter.py    # Existing - Unit conversion utilities
├── ui/
│   └── event_planning_tab.py  # MODIFY - Add variant columns to shopping list
└── tests/
    ├── test_variant_service.py    # ADD/MODIFY - Tests for new methods
    └── test_event_service.py      # ADD - Integration tests for shopping list
```

**Structure Decision**: Single project structure following existing bake-tracker patterns. No new directories required - all changes extend existing files.

## Complexity Tracking

*No constitution violations to justify - feature follows all principles.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Research Findings Summary

See [research.md](research.md) for complete findings.

### Key Discoveries

1. **Cost Data Source**: `Variant.get_current_cost_per_unit()` provides most recent purchase price - ideal for shopping recommendations (current market price, not FIFO historical cost)

2. **Existing VariantService Methods**:
   - `get_preferred_variant(ingredient_slug)` - returns preferred variant or None
   - `get_variants_for_ingredient(ingredient_slug)` - returns all variants, preferred first

3. **Unit Conversion**: `unit_converter.convert_any_units(value, from_unit, to_unit, ingredient_name)` handles recipe-to-purchase unit conversion including cross-type (volume to weight) via ingredient density

4. **Shopping List Structure**: `EventService.get_shopping_list()` returns list of dicts with ingredient_id, ingredient_name, unit, quantity_needed, quantity_on_hand, shortfall - ready for extension

### No Schema Changes Required

All necessary data already exists in the database:
- Variant.preferred flag for recommendation selection
- Purchase.unit_cost for cost calculations
- Variant.package_size, purchase_unit, purchase_quantity for package context
- UnitConversion table for unit mapping

## Implementation Phases

### Phase 1: VariantService Extensions

**File**: `src/services/variant_service.py`

Add new method:
```python
def get_variant_recommendation(
    ingredient_slug: str,
    shortfall: Decimal,
    recipe_unit: str
) -> Dict[str, Any]:
    """
    Get variant recommendation(s) for an ingredient shortfall.

    Returns dict with:
    - variant_status: 'preferred' | 'multiple' | 'none'
    - variant_recommendation: VariantRecommendation or None
    - all_variants: List[VariantRecommendation]
    """
```

Helper method:
```python
def _calculate_variant_cost(
    variant: Variant,
    shortfall: Decimal,
    recipe_unit: str
) -> VariantRecommendation:
    """Calculate cost metrics for a variant given a shortfall."""
```

### Phase 2: EventService Extensions

**File**: `src/services/event_service.py`

Modify `get_shopping_list()` to:
1. Call `VariantService.get_variant_recommendation()` for each shortfall item
2. Add variant_status, variant_recommendation, all_variants to each item
3. Calculate total_estimated_cost across all recommended purchases
4. Return extended ShoppingListItem structure

### Phase 3: UI Extensions

**File**: `src/ui/event_planning_tab.py`

Extend shopping list table:
1. Add columns: Variant, Package Size, Cost/Unit, Est. Cost
2. Handle vertically stacked rows when variant_status='multiple'
3. Show "[preferred]" indicator for preferred variants
4. Display "No variant configured" when variant_status='none'
5. Show total estimated cost at bottom of list

### Phase 4: Testing

**Unit Tests** (`src/tests/test_variant_service.py`):
- test_get_variant_recommendation_preferred
- test_get_variant_recommendation_multiple_variants
- test_get_variant_recommendation_no_variants
- test_cost_calculation_with_unit_conversion
- test_min_packages_rounds_up

**Integration Tests** (`src/tests/test_event_service.py`):
- test_shopping_list_with_variant_recommendations
- test_total_estimated_cost_calculation

## Related Artifacts

- [spec.md](spec.md) - Feature specification
- [research.md](research.md) - Research findings
- [data-model.md](data-model.md) - Data structures
- [quickstart.md](quickstart.md) - Implementation guide
