# Feature Specification: Recipe FIFO Cost Integration

**Feature Branch**: `005-recipe-fifo-cost`
**Created**: 2025-12-01
**Status**: Draft
**Input**: Update RecipeService to calculate recipe costs using actual pantry inventory costs via FIFO consumption logic

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Calculate Actual Recipe Cost from Pantry (Priority: P1)

Users need to know what a recipe will actually cost based on the ingredients they have in their pantry, using FIFO (oldest inventory consumed first) to determine accurate costs.

**Why this priority**: This is the core value proposition - accurate cost tracking based on real inventory is the foundation for all recipe costing. Without this, users cannot make informed decisions about baking costs.

**Independent Test**: Can be fully tested by creating pantry items with known purchase prices at different dates, then calculating recipe cost and verifying the oldest items' costs are used first. Delivers immediate value by showing true recipe costs.

**Acceptance Scenarios**:

1. **Given** a recipe requiring 2 cups of flour and pantry contains flour purchased at $0.10/cup (older) and $0.12/cup (newer), **When** actual cost is calculated, **Then** system returns total cost using $0.10/cup rate (FIFO)
2. **Given** a recipe with multiple ingredients each having pantry inventory, **When** actual cost is calculated, **Then** system sums FIFO-based costs for all ingredients and returns the total
3. **Given** a recipe requiring ingredients, **When** actual cost is calculated, **Then** pantry quantities are NOT modified (read-only operation)
4. **Given** a recipe with an ingredient that requires unit conversion (recipe uses cups, pantry tracked in grams), **When** actual cost is calculated, **Then** system correctly converts units and calculates cost

---

### User Story 2 - Calculate Estimated Recipe Cost for Planning (Priority: P2)

Users need to estimate recipe costs for planning purposes when they don't have ingredients in pantry or want to compare against current market prices.

**Why this priority**: Planning mode enables users to cost recipes before purchasing ingredients, supporting shopping decisions and budget planning. This is secondary to actual costing but essential for planning workflows.

**Independent Test**: Can be fully tested by calculating estimated cost for a recipe when pantry is empty, verifying it uses preferred variant's most recent purchase price. Delivers value for recipe planning and shopping decisions.

**Acceptance Scenarios**:

1. **Given** a recipe ingredient with no pantry inventory but a preferred variant with purchase history, **When** estimated cost is calculated, **Then** system uses the preferred variant's most recent purchase price
2. **Given** a recipe ingredient with no pantry inventory and no preferred variant set, **When** estimated cost is calculated, **Then** system uses any available variant's most recent purchase price for that ingredient
3. **Given** a recipe with multiple ingredients, **When** estimated cost is calculated, **Then** system returns total based on preferred variant pricing for all ingredients

---

### User Story 3 - Handle Partial Pantry Inventory (Priority: P3)

Users need accurate costing even when pantry inventory only partially covers recipe requirements, blending actual FIFO costs with estimated costs for the shortfall.

**Why this priority**: Partial inventory is a common real-world scenario. Users shouldn't have to choose between inaccurate costs or manual calculations when they have some but not all ingredients on hand.

**Independent Test**: Can be fully tested by creating a recipe needing 3 cups of an ingredient, adding only 2 cups to pantry, and verifying the cost calculation uses FIFO for 2 cups and falls back to preferred variant pricing for the remaining 1 cup.

**Acceptance Scenarios**:

1. **Given** a recipe requiring 3 cups of flour and pantry contains only 2 cups at $0.10/cup with preferred variant priced at $0.15/cup, **When** actual cost is calculated, **Then** system returns cost of (2 x $0.10) + (1 x $0.15) = $0.35
2. **Given** multiple recipe ingredients where some have full pantry coverage and others have partial, **When** actual cost is calculated, **Then** each ingredient is costed appropriately (full FIFO, partial FIFO + fallback, or full fallback)
3. **Given** a recipe ingredient with zero pantry inventory, **When** actual cost is calculated, **Then** system falls back entirely to preferred variant pricing for that ingredient

---

### Edge Cases

- What happens when an ingredient has no variants defined? System should return an error or flag indicating the ingredient cannot be costed.
- What happens when an ingredient's only variant has no purchase history? System should return an error or flag indicating no pricing data available.
- How does system handle density-based unit conversions (e.g., flour cups to grams)? System must use the ingredient's density value for accurate conversion.
- What happens when recipe quantity is zero for an ingredient? System should skip that ingredient (contributes $0 to total).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an "actual cost" calculation mode that uses FIFO-ordered pantry inventory to determine ingredient costs
- **FR-002**: System MUST provide an "estimated cost" calculation mode that uses preferred variant pricing regardless of pantry state
- **FR-003**: System MUST NOT modify pantry quantities during cost calculations (read-only simulation)
- **FR-004**: System MUST handle partial pantry inventory by using FIFO costs for available quantity and falling back to preferred variant pricing for shortfall
- **FR-005**: System MUST convert between recipe units and pantry/purchase units using existing unit conversion logic including density-based conversions
- **FR-006**: System MUST respect the Ingredient/Variant separation (recipes reference Ingredients, costs derived from Variants via pantry or purchase history)
- **FR-007**: System MUST return the total recipe cost as a decimal value
- **FR-008**: System MUST handle recipes with zero ingredients by returning zero cost
- **FR-009**: System MUST return an appropriate error when an ingredient cannot be costed (no variants or no pricing data)

### Key Entities *(existing entities involved)*

- **Recipe**: Contains list of RecipeIngredients with quantities and units; cost calculation target
- **RecipeIngredient**: Links Recipe to Ingredient with quantity and unit specifications
- **Ingredient**: Generic ingredient referenced by recipes; has associated Variants
- **Variant**: Brand-specific product with purchase history; source of pricing data
- **PantryItem**: Inventory record with purchase date, quantity, and cost; FIFO-ordered by purchase date
- **Purchase**: Purchase transaction record with price data for a Variant

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Actual cost calculations use FIFO ordering correctly, verified by test cases with multiple pantry lots at different prices
- **SC-002**: Cost calculations complete without modifying any pantry data, verified by comparing pantry state before and after calculation
- **SC-003**: Partial inventory scenarios correctly blend FIFO and fallback pricing, verified by test cases with known quantities and prices
- **SC-004**: Unit conversions between recipe and pantry units are accurate, verified by test cases with different unit combinations
- **SC-005**: Service layer test coverage for new cost calculation methods exceeds 70%

## Assumptions

- Existing PantryService.consume_fifo() logic correctly implements FIFO ordering and can be leveraged (possibly in read-only mode)
- Existing unit conversion infrastructure handles all required conversions including density-based conversions
- Preferred variant designation exists and is accessible via VariantService
- PurchaseService provides access to most recent purchase price for variants
- Decimal precision is used for all monetary calculations (per existing codebase patterns)

## Dependencies and Constraints

- Depends on existing PantryService FIFO logic
- Depends on existing unit conversion service
- Depends on existing VariantService for preferred variant lookup
- Depends on existing PurchaseService for price history
- Per project constitution: FIFO accuracy is NON-NEGOTIABLE

## Out of Scope

- UI changes (service layer only for this feature)
- Actual inventory depletion (deferred to Production Tracking - Phase 5)
- Shopping list generation
- Cost breakdown per ingredient (returns total only)
- Batch/scaling cost calculations
