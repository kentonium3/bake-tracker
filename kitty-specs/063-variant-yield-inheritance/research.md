# Research: Variant Yield Inheritance

**Feature**: 063-variant-yield-inheritance
**Date**: 2025-01-24

## Executive Summary

This feature has minimal research requirements. The existing codebase already supports:
- Variant recipes via `base_recipe_id` field
- Nullable yield fields on FinishedUnit (`items_per_batch`, `item_unit`)
- Session management pattern (`session=None`)

The implementation adds two service primitives and extends the variant creation workflow.

## Research Findings

### 1. Existing Variant Support

**Decision**: Use existing `base_recipe_id` relationship for yield inheritance

**Rationale**: The Recipe model already has a self-referential FK (`base_recipe_id`) that establishes the variant→base relationship. No schema changes needed.

**Alternatives Considered**:
- Adding a separate yield inheritance table → Rejected: unnecessary complexity
- Storing yield on variant with "inherited" flag → Rejected: data duplication risk

### 2. FinishedUnit Nullable Fields

**Decision**: FinishedUnit `items_per_batch` and `item_unit` are already nullable

**Rationale**: Existing model at `src/models/finished_unit.py:93-94`:
```python
items_per_batch = Column(Integer, nullable=True)
item_unit = Column(String(50), nullable=True)
```

No model changes required. Variant FinishedUnits will simply have NULL values.

### 3. Session Management Pattern

**Decision**: Follow existing `session=None` pattern per CLAUDE.md

**Rationale**: Multiple service functions already implement this pattern:
- `get_aggregated_ingredients(recipe_id, multiplier, session=None)`
- `get_recipe_variants(base_recipe_id, session=None)`
- `create_recipe_variant(..., session=None)`

New primitives will follow the same pattern to support transactional consistency.

### 4. Variant Creation UI

**Decision**: Extend existing recipe detail form (no variant creation dialog exists)

**Research Finding**: Grep search for variant UI components returned no results. The variant creation workflow will need to be added to `src/ui/forms/recipe_detail.py`.

**Alternatives Considered**:
- Separate variant wizard → Rejected: user clarification specified inline integration
- Modal dialog → Rejected: adds friction; inline preferred

### 5. Yield Display Pattern

**Decision**: Primitives return `List[Dict]` not ORM objects

**Rationale**:
- Avoids session detachment issues
- Supports JSON serialization for future API
- Consistent with `get_all_recipes_grouped` return pattern

**Return Structure**:
```python
[
    {
        "slug": "chocolate-chip-cookie",
        "display_name": "Chocolate Chip Cookie",
        "items_per_batch": 24,
        "item_unit": "cookie"
    }
]
```

## Open Questions

None. All technical decisions confirmed through codebase analysis.

## References

- `src/models/recipe.py` - Recipe model with `base_recipe_id`
- `src/models/finished_unit.py` - FinishedUnit model with nullable yield fields
- `src/services/recipe_service.py` - Existing variant functions
- `CLAUDE.md` - Session management guidance
