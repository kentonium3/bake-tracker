# Feature Specification: Variant Yield Inheritance

**Feature Branch**: `063-variant-yield-inheritance`
**Created**: 2025-01-24
**Status**: Draft
**Input**: User description: "See docs/func-spec/F063_recipe_variant_yield_inheritance.md for the feature inputs."
**Source**: `docs/func-spec/F063_recipe_variant_yield_inheritance.md`

## Overview

Variant recipes (e.g., "Raspberry Thumbprint Cookies" as a variant of "Plain Thumbprint Cookies") have their own FinishedUnit records for display purposes, but yield specifications (items_per_batch, item_unit) are defined only on base recipe FinishedUnits and inherited by variants through service primitives.

This feature adds service primitives for transparent yield access, enabling Planning/Production services to work identically for base and variant recipes without variant-specific logic.

---

## User Scenarios & Testing

### User Story 1 - Batch Calculations for Variant Recipes (Priority: P1)

Services performing batch calculations need to access variant yields transparently without checking whether a recipe is a variant or base.

**Why this priority**: Production planning is a core user workflow. If batch calculations fail for variants, production tracking is broken.

**Independent Test**: Can be tested by running batch calculations for both a base recipe and its variant, verifying both return correct items_per_batch from the base recipe.

**Acceptance Scenarios**:

1. **Given** a variant recipe "Raspberry Thumbprint Cookies" with base recipe "Plain Thumbprint Cookies", **When** a service calls `get_base_yield_structure(variant_id)`, **Then** it returns the base recipe's yield specifications (items_per_batch, item_unit).

2. **Given** a base recipe "Plain Thumbprint Cookies", **When** a service calls `get_base_yield_structure(base_id)`, **Then** it returns its own yield specifications.

3. **Given** any recipe (base or variant), **When** a service calls `get_finished_units(recipe_id)`, **Then** it returns that recipe's own FinishedUnits (for display_name access).

---

### User Story 2 - Creating a Variant Recipe with FinishedUnits (Priority: P1)

When creating a variant of an existing recipe, the user needs to set up FinishedUnits for the variant with distinct display names while inheriting yield structure from the base.

**Why this priority**: This is the core workflow. Without this, variants cannot be created with proper FinishedUnit records.

**Independent Test**: Can be fully tested by creating a variant recipe and verifying its FinishedUnits are created with user-provided display_name while yield info comes from base.

**Acceptance Scenarios**:

1. **Given** a base recipe "Plain Thumbprint Cookies" with a FinishedUnit (display_name: "Plain Cookie", items_per_batch: 24, item_unit: "cookie"), **When** the user creates a variant "Raspberry Thumbprint Cookies", **Then** the system prompts for variant FinishedUnit display_name only.

2. **Given** the variant creation form, **When** the user enters display_name "Raspberry Thumbprint Cookie" and saves, **Then** the variant FinishedUnit is created with the variant's recipe_id and the provided display_name (no items_per_batch/item_unit stored on variant FinishedUnit).

3. **Given** a base recipe with two FinishedUnits, **When** creating a variant, **Then** the system requires display_name entry for both FinishedUnits.

---

### User Story 3 - Display Variant Yield Information (Priority: P2)

When viewing a variant recipe's production details, the system must display the correct yield information from the base recipe.

**Why this priority**: Important for user understanding but less critical than core calculation functionality.

**Independent Test**: Can be tested by viewing a variant recipe and verifying displayed yield info matches base recipe.

**Acceptance Scenarios**:

1. **Given** a variant recipe "Raspberry Thumbprint Cookies", **When** viewing its production details, **Then** the yield shows "24 cookies per batch" (from base recipe).

2. **Given** a variant recipe, **When** displaying its FinishedUnit list, **Then** it shows the variant's display_name (e.g., "Raspberry Thumbprint Cookie") with yield info from base.

---

### Edge Cases

- What happens when a base recipe has no FinishedUnits?
  - Variant creation proceeds without FinishedUnit setup; `get_base_yield_structure()` returns empty list.

- What happens when a base recipe's yield changes after variants exist?
  - Variants automatically use the updated base yield (no flagging or review needed - yield is always read from base).

- How does the system handle a recipe that is not a variant?
  - `get_base_yield_structure(recipe_id)` returns the recipe's own yields.
  - `get_finished_units(recipe_id)` returns the recipe's own FinishedUnits.

- What if a variant FinishedUnit has items_per_batch/item_unit fields populated?
  - These fields should be NULL for variant FinishedUnits; primitives always use base recipe values.

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST provide a `get_base_yield_structure(recipe_id)` primitive in recipe_service that returns the base recipe's yield specifications (items_per_batch, item_unit) when given a variant recipe_id, or the recipe's own yields when given a base recipe_id.

- **FR-002**: System MUST provide a `get_finished_units(recipe_id)` primitive in recipe_service that returns a recipe's own FinishedUnits for any recipe type.

- **FR-003**: Variant FinishedUnits MUST NOT store items_per_batch or item_unit values; these are inherited from base recipe via primitives.

- **FR-004**: Variant FinishedUnits MUST have display_name values that differ from the base recipe's FinishedUnits.

- **FR-005**: System MUST extend the variant creation workflow to include FinishedUnit setup with display_name input only.

- **FR-006**: Planning and Production services MUST use `get_base_yield_structure(recipe_id)` for all batch calculations.

- **FR-007**: Services MUST NOT perform variant-specific logic or check base_recipe_id when accessing yields; the primitives handle abstraction.

### Key Entities

- **Recipe**: Existing model. Variants reference base recipe via `base_recipe_id`. No changes needed.

- **FinishedUnit**: Existing model. For variants, `items_per_batch` and `item_unit` are NULL; only `display_name`, `slug`, and `recipe_id` are populated. Yield info obtained via `get_base_yield_structure()`.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: Batch calculations for variant recipes produce correct results using the base recipe's yield specifications.

- **SC-002**: Variant creation workflow includes FinishedUnit setup with 100% of variants having corresponding FinishedUnit records.

- **SC-003**: Planning and Production services work identically for base and variant recipes without variant-specific code paths.

- **SC-004**: Users can complete the variant creation workflow (including FinishedUnit display_name entry) in a single session without errors.

---

## Assumptions

- No backward compatibility required; existing data will be transformed via import files to comply with new schema.
- Variants of variants are not supported (per existing requirements).
- The number of variant FinishedUnits must match the number of base recipe FinishedUnits.

---

## Out of Scope

- Flagging/review mechanism for base yield changes (not needed - variants inherit automatically)
- Yield validation between variant and base (variants don't store yields)
- Variant-of-variant support
- Historical tracking of yield changes
