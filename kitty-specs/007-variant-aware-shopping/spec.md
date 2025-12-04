# Feature Specification: Variant-Aware Shopping List Recommendations

**Feature Branch**: `007-variant-aware-shopping`
**Created**: 2025-12-04
**Status**: Draft
**Input**: Enhance shopping list to include variant-aware purchase recommendations with preferred variant logic, cost per unit, package size context, and total estimated cost

## Clarifications

### Session 2025-12-04

- Q: When no preferred variant is marked and all available variants must be listed, how should they be displayed? → A: Vertically stacked rows under the ingredient (each variant on its own line).

## Problem Statement

After Feature 006, the shopping list shows basic "needs vs inventory" (ingredients needed minus what's on hand = shortfall). However, it doesn't leverage the Ingredient/Variant architecture to recommend which brand/package to buy. Users must manually determine which variant to purchase and calculate quantities.

## Solution Overview

Enhance the shopping list to display variant-aware purchase recommendations. For each ingredient with a shortfall, the system will show:
- The shortfall in recipe units (e.g., "Need 10 cups")
- The minimum packages to buy (e.g., "1 bag minimum")
- Recommended variant details (brand, package size, cost per recipe unit)
- Total estimated cost for all recommended purchases

## User Scenarios & Testing

### User Story 1 - View Recommended Purchases (Priority: P1)

As a baker planning an event, I want to see which specific products to buy for ingredients I'm short on, so I can shop efficiently without manual calculations.

**Why this priority**: This is the core value proposition - transforming a generic shortfall list into actionable purchase recommendations.

**Independent Test**: Can be fully tested by opening an event's shopping list with ingredients that have configured variants and verifying recommendations appear with correct variant details.

**Acceptance Scenarios**:

1. **Given** an event with recipe needs requiring 10 cups of flour, **When** the user has 5 cups on hand and views the shopping list, **Then** the system displays "Need 10 cups, Have 5 cups, To Buy 5 cups" with the preferred flour variant recommendation including package size and cost per cup.

2. **Given** an ingredient with a preferred variant marked, **When** the shopping list is generated, **Then** the preferred variant is shown as the recommendation with "[preferred]" indicator.

3. **Given** an ingredient shortfall of 10 cups and a variant package containing 90 cups, **When** viewing the shopping list, **Then** the display shows "Need 10 cups -> 1 bag minimum" indicating the minimum whole packages needed.

---

### User Story 2 - View Multiple Variant Options (Priority: P2)

As a baker who hasn't designated a preferred variant, I want to see all available variants for an ingredient, so I can choose which brand to purchase based on the displayed information.

**Why this priority**: Provides flexibility when users haven't yet established preferences or want to compare options.

**Independent Test**: Can be tested by viewing shopping list for an ingredient that has multiple variants but none marked as preferred.

**Acceptance Scenarios**:

1. **Given** an ingredient with 3 variants but none marked as preferred, **When** viewing the shopping list, **Then** all 3 variants are listed with their package sizes and cost per recipe unit, without a single recommendation highlighted.

2. **Given** an ingredient with variants listed, **When** the user views the list, **Then** each variant shows: brand name, package size, cost per recipe unit, and total purchase cost if bought.

---

### User Story 3 - View Total Estimated Cost (Priority: P2)

As a baker planning an event budget, I want to see the total estimated cost for all recommended purchases, so I can understand the shopping expense before going to the store.

**Why this priority**: Budget visibility is essential for event planning but depends on recommendations being available first.

**Independent Test**: Can be tested by viewing a shopping list with multiple ingredients having shortfalls and verifying the total cost calculation.

**Acceptance Scenarios**:

1. **Given** a shopping list with 3 ingredients each having a recommended variant, **When** viewing the shopping list, **Then** a total estimated cost is displayed summing all recommended purchase costs.

2. **Given** some ingredients have no variants configured, **When** calculating total cost, **Then** only ingredients with valid variant recommendations are included in the total.

---

### User Story 4 - Handle Missing Variant Configuration (Priority: P3)

As a baker with incomplete ingredient setup, I want graceful handling when variants aren't configured, so the shopping list remains useful even with partial data.

**Why this priority**: Error handling and edge cases - important for robustness but not the primary use case.

**Independent Test**: Can be tested by viewing shopping list for an ingredient that has no variants configured.

**Acceptance Scenarios**:

1. **Given** an ingredient with no variants configured, **When** viewing the shopping list, **Then** the ingredient row shows "No variant configured" in the recommendation column instead of crashing or showing empty data.

2. **Given** a mix of ingredients (some with variants, some without), **When** viewing the shopping list, **Then** all ingredients display correctly with appropriate recommendations or fallback messages.

---

### Edge Cases

- What happens when a variant has no purchase history (no cost data)? Display variant info with "Cost unknown" message.
- What happens when unit conversion fails between recipe_unit and purchase_unit? Display shortfall in recipe units with warning "Unit conversion unavailable."
- What happens when the shortfall is zero or negative? No recommendation needed; row shows "Sufficient stock."
- What happens when package size would result in significant overbuy (e.g., need 1 cup, package has 100 cups)? Still show minimum packages (1) with the full package size context so user can decide.

## Requirements

### Functional Requirements

- **FR-001**: System MUST display the recommended variant for each ingredient with a shortfall when a preferred variant is configured.
- **FR-002**: System MUST list all available variants as vertically stacked rows under the ingredient when no preferred variant is marked, without highlighting a single recommendation.
- **FR-003**: System MUST display "No variant configured" for ingredients that have no variants in the system.
- **FR-004**: System MUST show cost per recipe unit for each variant (e.g., "$0.18/cup").
- **FR-005**: System MUST show package size context for each variant (e.g., "25 lb bag = 90 cups").
- **FR-006**: System MUST display minimum packages to purchase based on shortfall (e.g., "Need 10 cups -> 1 bag minimum").
- **FR-007**: System MUST calculate and display total estimated cost for all recommended purchases.
- **FR-008**: System MUST perform unit conversion between recipe_unit (shortfall) and purchase_unit (variant) using UnitConverter.
- **FR-009**: System MUST preserve existing shopping list functionality (ingredient, needed, on_hand, to_buy columns).
- **FR-010**: System MUST handle variants with no purchase history by showing "Cost unknown."

### Key Entities

- **Ingredient**: Generic concept (e.g., "All-Purpose Flour") with recipe_unit for measurements.
- **Variant**: Specific brand/package (e.g., "King Arthur 25 lb bag") with purchase_unit, package_size, and preferred flag.
- **ShoppingListItem**: Extended to include variant recommendations, cost_per_unit, package_context, and purchase_cost.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Shopping list displays variant recommendations for 100% of ingredients that have configured variants.
- **SC-002**: Cost per recipe unit calculations are accurate within $0.01 precision.
- **SC-003**: Minimum package calculations correctly round up to cover shortfall (never under-recommend).
- **SC-004**: Total estimated cost equals the sum of individual recommended purchase costs.
- **SC-005**: Shopping list tab loads in under 2 seconds with variant recommendations (consistent with Feature 006 performance requirements).
- **SC-006**: All existing shopping list tests continue to pass (no regression).

## Assumptions

- Variant.preferred flag exists and is functional from the Phase 4 Ingredient/Variant architecture.
- UnitConverter service exists and can convert between recipe_unit and purchase_unit for the same ingredient.
- PurchaseService or similar can retrieve the most recent purchase for cost data.
- EventService.generate_shopping_list() is the correct extension point for this enhancement.

## Out of Scope

- Multiple purchase options / comparison view (future enhancement)
- Auto-selecting cheapest vs preferred (use preferred, user decides)
- Purchase order generation or supplier integration
- Barcode/UPC features
- Modifying variant preferences from the shopping list view

## Dependencies

- **Requires**: Feature 006 complete (working EventService shopping list)
- **Uses**: VariantService, PantryService, UnitConverter, existing cost-per-unit calculations
