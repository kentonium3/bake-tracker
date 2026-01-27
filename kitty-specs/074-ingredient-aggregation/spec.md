# Feature Specification: Ingredient Aggregation for Batch Decisions

**Feature Branch**: `074-ingredient-aggregation`
**Created**: 2026-01-27
**Status**: Draft
**Input**: see docs/func-spec/F074_ingredient_aggregation.md

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Aggregate Ingredients for Single Recipe (Priority: P1)

When a user has made batch decisions for an event containing a single recipe, the system calculates total ingredient quantities needed by multiplying recipe ingredient quantities by the number of batches.

**Why this priority**: This is the foundational calculation - all other scenarios build on this.

**Independent Test**: Can be tested with a single recipe, single FU, and a batch decision. Verifies base ingredient scaling works correctly.

**Acceptance Scenarios**:

1. **Given** a recipe with 2 cups flour per batch and a batch decision of 3 batches, **When** ingredients are aggregated, **Then** the result shows 6 cups flour needed.
2. **Given** a recipe with multiple ingredients, **When** aggregation runs, **Then** all ingredients are scaled by the batch count with precision maintained to 3 decimal places.

---

### User Story 2 - Aggregate Ingredients Across Multiple Recipes (Priority: P1)

When batch decisions span multiple recipes that share common ingredients, the system aggregates the same ingredient from different recipes into a single total.

**Why this priority**: Critical for shopping list generation - users need combined totals, not per-recipe lists.

**Independent Test**: Can be tested with two recipes sharing an ingredient (e.g., both use flour). Verifies cross-recipe aggregation.

**Acceptance Scenarios**:

1. **Given** Recipe A needs 2 cups flour (2 batches = 4 cups) and Recipe B needs 1 cup flour (3 batches = 3 cups), **When** aggregated, **Then** total flour shows 7 cups.
2. **Given** same ingredient in different units (e.g., cups vs tablespoons), **When** aggregated, **Then** they remain separate entries (no unit conversion).

---

### User Story 3 - Handle Recipe Variants with Proportional Allocation (Priority: P2)

When a recipe has variants (e.g., Raspberry Thumbprint vs Strawberry Thumbprint), and multiple FUs from the same recipe are in batch decisions, ingredient quantities are allocated proportionally based on how the batches split across variants.

**Why this priority**: Important for accurate ingredient planning when recipes have flavor/style variants that share base ingredients.

**Independent Test**: Can be tested with a base recipe and two variant FUs with different batch counts.

**Acceptance Scenarios**:

1. **Given** a Thumbprint Cookie recipe with 3 batches for Raspberry variant and 2 batches for Strawberry variant, **When** base ingredients are aggregated, **Then** base ingredients are scaled by total 5 batches.
2. **Given** variant-specific ingredients (raspberry jam for Raspberry variant), **When** aggregated, **Then** variant ingredients are scaled only by that variant's batch count.

---

### Edge Cases

- What happens when quantity_needed is zero? Return empty aggregation.
- What happens when a recipe has no ingredients? Skip that recipe in aggregation.
- How does system handle floating point precision? Round to 3 decimal places.
- What if same ingredient appears multiple times in same recipe? Aggregate within recipe first.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST calculate total ingredients for a single recipe by multiplying each ingredient quantity by the batch count from BatchDecision
- **FR-002**: System MUST aggregate same (ingredient_id, unit) pairs across different recipes into a single total quantity
- **FR-003**: System MUST keep different units for the same ingredient separate (no automatic unit conversion)
- **FR-004**: System MUST maintain precision to 3 decimal places throughout calculations
- **FR-005**: System MUST return ingredient totals keyed by (ingredient_id, unit) tuple
- **FR-006**: System MUST handle recipes with variants by calculating proportional allocation when multiple FUs from the same base recipe exist
- **FR-007**: System MUST be a pure calculation service with no side effects (no database writes)
- **FR-008**: System MUST accept event_id and return aggregated ingredients for all batch decisions in that event

### Key Entities

- **BatchDecision**: User's choice of how many batches to make for each FinishedUnit in an event
- **Recipe**: Production template containing base ingredients via RecipeIngredient
- **RecipeIngredient**: Junction linking Recipe to Ingredient with quantity and unit
- **Ingredient**: Brand-agnostic ingredient reference
- **FinishedUnit**: Specific product variant linked to a recipe with yield mode (discrete_count or batch_portion)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System correctly calculates ingredient totals for 100% of test cases including single-recipe, multi-recipe, and variant scenarios
- **SC-002**: Aggregation produces identical results when run multiple times with same inputs (deterministic)
- **SC-003**: All ingredient quantities maintain 3 decimal place precision without cumulative rounding errors
- **SC-004**: Aggregation completes for events with up to 50 batch decisions in under 1 second

## Assumptions

- Batch decisions already exist (created via F073 workflow) before aggregation is called
- No unit conversion is needed - different units are kept separate
- Recipe variants share base_recipe_id relationship in Recipe model
- The existing RecipeIngredient model provides all base ingredient data needed
