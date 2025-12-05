# Feature Specification: User-Friendly Ingredient Density Input

**Feature Branch**: `010-user-friendly-ingredient`
**Created**: 2025-12-04
**Status**: Draft
**Input**: Replace density_g_per_ml with 4-field density model for natural baker input

## Problem Statement

The current density handling requires users to enter `density_g_per_ml` values (e.g., 0.507 for flour), which:
- Requires metric conversion knowledge
- Is unintuitive for home bakers who think in cups and ounces
- Falls back to a hardcoded `INGREDIENT_DENSITIES` dict with unclear provenance

Home bakers naturally think: "1 cup of flour weighs 4.25 oz" - not "flour has a density of 0.507 g/ml."

## Solution Overview

Replace the single `density_g_per_ml` field with a 4-field density model that accepts natural baker input:

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| density_volume_value | Float | 1.0 | Volume amount |
| density_volume_unit | String | cup | Volume unit |
| density_weight_value | Float | 4.25 | Weight amount |
| density_weight_unit | String | oz | Weight unit |

**User enters:** "1 cup of flour weighs 4.25 oz"
**System calculates:** density in standard units for internal conversions

## User Scenarios & Testing

### User Story 1 - Enter Ingredient Density (Priority: P1)

A baker creates a new ingredient and wants to specify its density so the system can convert between volume and weight measurements in recipes.

**Why this priority**: This is the core functionality - without density entry, the feature has no value.

**Independent Test**: Can be tested by creating an ingredient with density fields and verifying the values are stored and displayed correctly.

**Acceptance Scenarios**:

1. **Given** the Ingredients tab is open, **When** user creates a new ingredient and enters "1 cup = 4.25 oz" in the density fields, **Then** the system stores all four density values and displays them correctly.

2. **Given** an ingredient edit form, **When** user fills only some density fields (e.g., volume but not weight), **Then** the system shows a validation error requiring all four fields.

3. **Given** an ingredient edit form, **When** user leaves all density fields empty, **Then** the ingredient is saved without density (conversion unavailable).

---

### User Story 2 - Recipe Cost Calculation Uses Density (Priority: P1)

When a recipe specifies an ingredient by volume (e.g., "2 cups flour") but the pantry tracks by weight, the system uses the ingredient's density to convert and calculate accurate costs.

**Why this priority**: This is the primary use case for density - enabling accurate cost calculations across unit types.

**Independent Test**: Can be tested by creating a recipe with volume-based ingredients, ensuring pantry has weight-based inventory, and verifying cost calculation works.

**Acceptance Scenarios**:

1. **Given** an ingredient with density "1 cup = 4.25 oz" and pantry inventory in ounces, **When** a recipe uses 2 cups of that ingredient, **Then** the system converts to 8.5 oz for cost calculation.

2. **Given** an ingredient without density set, **When** a recipe uses volume units and pantry has weight units, **Then** the system indicates conversion is unavailable (no silent fallback).

---

### User Story 3 - Import/Export Density Data (Priority: P2)

Users can export their ingredient data including density specifications and import it on a fresh database.

**Why this priority**: Essential for data portability but depends on P1 functionality working first.

**Independent Test**: Can be tested by exporting ingredients with density, clearing database, reimporting, and verifying density values match.

**Acceptance Scenarios**:

1. **Given** ingredients with density values, **When** user exports data, **Then** the JSON includes all four density fields per ingredient.

2. **Given** a JSON file with 4-field density data, **When** user imports, **Then** density values are correctly stored for each ingredient.

3. **Given** a JSON file with old `density_g_per_ml` field, **When** user imports, **Then** the old field is ignored (no automatic conversion).

---

### Edge Cases

- What happens when user enters zero or negative density values? System rejects with validation error.
- What happens when density units are invalid? System rejects with validation error.
- What happens when ingredient has no density and recipe needs conversion? System reports conversion unavailable; no silent fallback to hardcoded values.

## Requirements

### Functional Requirements

- **FR-001**: System MUST replace `density_g_per_ml` field with four fields: `density_volume_value`, `density_volume_unit`, `density_weight_value`, `density_weight_unit`
- **FR-002**: System MUST validate that if any density field is provided, all four must be provided
- **FR-003**: System MUST validate that density values are positive numbers (> 0)
- **FR-004**: System MUST validate that density units are valid volume/weight units from the existing unit lists
- **FR-005**: System MUST calculate internal density (g/ml) from the 4-field specification for conversion operations
- **FR-006**: System MUST display density in user-friendly format (e.g., "1 cup = 4.25 oz") in the UI
- **FR-007**: System MUST allow ingredients without density (all four fields null)
- **FR-008**: System MUST return conversion unavailable when ingredient lacks density and conversion is requested
- **FR-009**: System MUST remove the hardcoded `INGREDIENT_DENSITIES` dictionary and `get_ingredient_density()` function
- **FR-010**: System MUST export all four density fields in JSON export
- **FR-011**: System MUST import all four density fields from JSON import
- **FR-012**: System MUST ignore legacy `density_g_per_ml` field during import (no backward compatibility)

### Key Entities

- **Ingredient**: Extended with four density fields replacing the single `density_g_per_ml`. Includes method `get_density_g_per_ml()` to calculate internal density from the 4-field specification.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can enter density as "X [volume_unit] = Y [weight_unit]" without needing to know metric conversions
- **SC-002**: Recipe cost calculations using density complete correctly when density is specified
- **SC-003**: Import/export round-trip preserves all four density fields with 100% accuracy
- **SC-004**: No hardcoded density values remain in the codebase after implementation
- **SC-005**: Validation errors for incomplete density entry are clear and actionable

## Assumptions

- Migration will be handled by deleting the database and reimporting data (no in-place migration needed)
- Users will re-enter density values in the new format after migration
- The existing `VOLUME_UNITS` and `WEIGHT_UNITS` constants define valid unit options
- The UI will use dropdown/combobox for unit selection to prevent invalid unit entry

## Out of Scope

- Automatic conversion of legacy `density_g_per_ml` values to new format
- Backward compatibility with old export files containing `density_g_per_ml`
- Suggested density values or lookup from external sources
- Unit conversion validation (e.g., preventing "1 cup = 5 cups" - both volume)
