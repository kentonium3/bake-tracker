# Implementation Plan: Nested Recipes (Sub-Recipe Components)

**Branch**: `012-nested-recipes` | **Date**: 2025-12-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/012-nested-recipes/spec.md`

## Summary

Add hierarchical recipe support where parent recipes can include other recipes as components with batch multiplier quantities. Key capabilities:
- **RecipeComponent** junction model linking parent recipe to child recipe
- **Circular reference detection** via tree traversal on save
- **Recursive cost calculation** summing direct ingredients + (sub-recipe cost x quantity)
- **Shopping list aggregation** collecting all ingredients across hierarchy
- **Maximum 3 levels** of nesting enforced at validation time

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter
**Storage**: SQLite with WAL mode
**Testing**: pytest (>70% service coverage required)
**Target Platform**: Desktop (macOS, Windows)
**Project Type**: Single desktop application
**Performance Goals**: Cost calculation and shopping list generation instant for typical recipes (<100ms)
**Constraints**: Max 3-level nesting depth, no circular references
**Scale/Scope**: Single user, ~100 recipes max

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Nested recipes solve real user problem (complex baked goods like layer cakes) |
| II. Data Integrity & FIFO Accuracy | PASS | Cost calculations will use existing FIFO logic; no changes to FIFO behavior |
| III. Future-Proof Schema, Present-Simple | PASS | RecipeComponent is minimal; no unused fields added |
| IV. Test-Driven Development | PASS | Service methods will have comprehensive tests |
| V. Layered Architecture | PASS | Logic in recipe_service.py; UI only calls services |
| VI. Migration Safety | PASS | New table only; no existing data modified |
| VII. Pragmatic Aspiration | PASS | Service-layer logic easily wraps to API for web phase |

**Web Migration Cost**: LOW - Recipe aggregation logic is in service layer, stateless, easily exposed as API endpoints.

## Project Structure

### Documentation (this feature)

```
kitty-specs/012-nested-recipes/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (internal API contracts)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── recipe.py           # MODIFY: Add RecipeComponent class and Recipe relationships
│   └── __init__.py         # MODIFY: Export RecipeComponent
├── services/
│   ├── recipe_service.py   # MODIFY: Add component management, aggregation methods
│   └── import_export_service.py  # MODIFY: Handle recipe components in export/import
├── ui/
│   └── recipe_form.py      # MODIFY: Add sub-recipes section to form
└── tests/
    └── services/
        └── test_recipe_service.py  # MODIFY: Add tests for nested recipe functionality
```

**Structure Decision**: Single project structure (existing). All changes are modifications to existing files plus one new model class.

## Complexity Tracking

*No constitution violations - no complexity justifications needed.*

## Engineering Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Circular reference detection | Check on save (tree traversal) | Single-user desktop app with <100 recipes; O(n) traversal is instant |
| Shopping list aggregation | Recipe Service method | Keeps recipe logic centralized; existing pattern |
| Recipe form UI | Single scrollable form with two sections | Matches existing UI patterns |
| Sub-recipe quantity | Batch multiplier (float) | User confirmed; simpler than volume/weight units |
| Max nesting depth | 3 levels | User confirmed; enforced during circular reference check |
| Import/export identifier | Recipe name (existing pattern) | Recipes don't have slugs; use name like existing import_export_service |

## Implementation Phases

### Phase 0: Research (Complete)

Findings documented in [research.md](./research.md):
- Existing `Composition` model provides pattern for junction tables with XOR constraints
- `Recipe` model has `recipe_ingredients` relationship pattern to follow
- `recipe_service.py` has CRUD + cost calculation patterns to extend
- Import/export uses recipe name as identifier (not slug)

### Phase 1: Design

1. **Data Model** ([data-model.md](./data-model.md))
   - RecipeComponent junction table
   - Recipe model relationship additions
   - Validation constraints

2. **Service Contracts** ([contracts/recipe_service.md](./contracts/recipe_service.md))
   - `add_recipe_component(recipe_id, component_recipe_id, quantity, notes)`
   - `remove_recipe_component(recipe_id, component_recipe_id)`
   - `get_aggregated_ingredients(recipe_id)` - returns all ingredients with quantities
   - `calculate_total_cost(recipe_id)` - recursive cost calculation
   - `validate_component_addition(recipe_id, component_recipe_id)` - circular ref + depth check

3. **UI Flow** ([quickstart.md](./quickstart.md))
   - Recipe form with two sections: Ingredients, Sub-Recipes
   - Sub-recipe dropdown, quantity input, add/remove buttons

### Phase 2: Tasks (via /spec-kitty.tasks)

Work packages will be generated covering:
- WP01: RecipeComponent model and migrations
- WP02: Service layer - component CRUD
- WP03: Service layer - validation (circular refs, depth)
- WP04: Service layer - cost calculation and aggregation
- WP05: Import/export support
- WP06: UI - recipe form sub-recipes section
- WP07: Integration tests

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Circular reference not detected | HIGH | Comprehensive test suite; traverse full tree before save |
| Cost calculation incorrect | HIGH | Unit tests with known costs; compare to manual calculation |
| Depth limit bypassed | MEDIUM | Check depth at validation time, not just on add |
| Import fails on missing sub-recipe | LOW | Graceful handling with warning (spec requirement) |

## Dependencies

- Feature 011 (Packaging & BOM Foundation) - Complete
- Existing `recipe_service.py` patterns
- Existing `Composition` model as reference pattern
