# Feature Specification: Recipe Variant Yield Remediation

**Feature Branch**: `066-recipe-variant-yield-remediation`
**Created**: 2025-01-24
**Status**: Draft
**Input**: User description: "See docs/func-spec/F066_recipe_variant_yield_remediation.md for inputs on this feature."

## Overview

This feature completes the F063 (Recipe Variant Yield Inheritance) implementation by adding service primitives for decoupled yield access and improving UI clarity for variant recipe handling.

**Problem Being Solved:**
- Services directly access `recipe.finished_units`, creating tight coupling to the Recipe model
- No universal primitive for accessing recipe yields that works identically for base and variant recipes
- UI terminology is inconsistent (mixes "finished unit", "yield", and "output")
- Variant creation dialog doesn't show base recipe yields as reference
- RecipeFormDialog doesn't properly handle variant recipes (no visual distinction, unclear what can be edited)

**Solution:**
- Add `get_finished_units(recipe_id)` primitive that works for any recipe type
- Add `get_base_yield_structure(recipe_id)` primitive for variant reference display
- Update all yield-consuming services to use primitives instead of direct model access
- Standardize UI terminology to use "yield" consistently
- Improve variant creation and editing dialogs with clear inheritance messaging

**Note:** Phase 1 (NULL yield fields bug) was fixed separately as a direct bug fix. Phase 4 (yield change detection) is deferred to a future feature.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Plan Production for Variant Recipes (Priority: P1)

As a production planner, when I create a production plan that includes variant recipes, the system uses the correct yield values (inherited from base) so that batch calculations are accurate.

**Why this priority**: This is the core functionality - planning must work correctly for variant recipes.

**Independent Test**: Can be tested by creating a production plan for a variant recipe and verifying batch calculations use inherited yield values.

**Acceptance Scenarios**:

1. **Given** a variant recipe with yield values inherited from its base, **When** planning service calculates batch requirements, **Then** it uses `get_finished_units()` to access the variant's yields (which are copied from base).

2. **Given** a variant recipe ID passed to any yield-consuming service, **When** the service accesses yields, **Then** it uses `recipe_service.get_finished_units(recipe_id)` instead of directly accessing `recipe.finished_units`.

---

### User Story 2 - Create Recipe Variant with Yield Reference (Priority: P1)

As a recipe manager, when I create a variant of an existing recipe, I can see the base recipe's yield structure as a reference so that I understand what yields the variant will inherit.

**Why this priority**: Critical for user understanding of the variant inheritance model.

**Independent Test**: Can be tested by opening the variant creation dialog and verifying base recipe yields are displayed.

**Acceptance Scenarios**:

1. **Given** a base recipe with defined yields (e.g., "32 cookies per batch"), **When** I open the variant creation dialog for that base, **Then** I see the base recipe's yield structure displayed as read-only reference.

2. **Given** the variant creation dialog is open, **When** I read the interface, **Then** I see consistent "yield" terminology (not "finished unit").

3. **Given** the variant creation dialog is open, **When** I review the messaging, **Then** I see a clear explanation that the variant will inherit these yields.

---

### User Story 3 - Edit Variant Recipe with Clear Constraints (Priority: P2)

As a recipe manager, when I edit a variant recipe, I can see that yield structure is inherited from the base recipe (read-only) but I can customize the display name.

**Why this priority**: Essential for usability but depends on service primitives from P1.

**Independent Test**: Can be tested by opening RecipeFormDialog for a variant and verifying yield fields are read-only except display_name.

**Acceptance Scenarios**:

1. **Given** I am editing a variant recipe, **When** RecipeFormDialog opens, **Then** I see "Base Recipe: [name]" displayed as reference.

2. **Given** I am editing a variant recipe, **When** I view the yields section, **Then** yield structure fields (items_per_batch, item_unit, yield_mode) are read-only.

3. **Given** I am editing a variant recipe, **When** I want to customize the yield display name, **Then** the display_name field is editable.

4. **Given** I am editing a base recipe, **When** RecipeFormDialog opens, **Then** all yield fields are fully editable as before.

---

### Edge Cases

- What happens when a variant's base recipe is deleted? Variants should be prevented from orphaning or should become standalone recipes.
- How does the system handle recipes with multiple FinishedUnits? Both primitives return lists supporting multiple yields.
- What happens if `get_base_yield_structure()` is called on a base recipe? It raises a ValidationError since base recipes have no base_recipe_id.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide `get_finished_units(recipe_id, session=None)` in recipe_service that returns FinishedUnits for any recipe
- **FR-002**: System MUST provide `get_base_yield_structure(recipe_id, session=None)` in recipe_service that returns base recipe yield specifications for variants
- **FR-003**: System MUST update planning_service to use `get_finished_units()` instead of direct `recipe.finished_units` access
- **FR-004**: System MUST update batch_production_service to use `get_finished_units()` instead of direct access
- **FR-005**: System MUST update assembly_service to use `get_finished_units()` if it accesses yields
- **FR-006**: System MUST update VariantCreationDialog to display base recipe yields using `get_base_yield_structure()`
- **FR-007**: System MUST update VariantCreationDialog to use consistent "yield" terminology
- **FR-008**: System MUST update RecipeFormDialog to detect variant recipes (via base_recipe_id)
- **FR-009**: System MUST update RecipeFormDialog to make yield structure read-only for variants
- **FR-010**: System MUST update RecipeFormDialog to allow display_name editing for variant yields
- **FR-011**: System MUST update RecipeFormDialog to show base recipe reference for variants
- **FR-012**: System MUST provide unit tests for both new service primitives
- **FR-013**: System MUST provide integration tests verifying services use primitives correctly

### Key Entities

- **Recipe**: Base or variant recipe; variants have `base_recipe_id` pointing to their base
- **FinishedUnit**: Yield specification tied to a recipe; variants have yields copied from base (Phase 1 fix)
- **recipe_service**: Extended with `get_finished_units()` and `get_base_yield_structure()` primitives
- **VariantCreationDialog**: UI for creating recipe variants; updated with yield reference display
- **RecipeFormDialog**: UI for editing recipes; updated with variant-aware behavior

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: No service directly accesses `recipe.finished_units` - all use `get_finished_units()` primitive
- **SC-002**: `get_finished_units(recipe_id)` works identically for base and variant recipes
- **SC-003**: `get_base_yield_structure(recipe_id)` returns correct yield specs for variant recipes
- **SC-004**: VariantCreationDialog displays base recipe yields before user creates variant
- **SC-005**: RecipeFormDialog shows read-only yield structure for variant recipes
- **SC-006**: All UI text uses "yield" terminology consistently (no "finished unit" in user-facing text)
- **SC-007**: Unit test coverage for both new primitives at 100%
- **SC-008**: Integration tests verify planning/production services use primitives correctly

## Assumptions

- Phase 1 (NULL yield fields bug) is already fixed - variants have correct yield values
- The existing `session=None` pattern for optional session parameters is established
- RecipeFormDialog and VariantCreationDialog exist and are functional for basic operations
- Services are structured to allow session parameter passing for transaction consistency

## Out of Scope

- **Phase 1 (NULL yield bug)** - Already fixed as separate bug fix
- **Phase 4 (Yield change detection)** - Deferred to future feature (F068+)
- Yield override capability for variants - Intentionally prohibited by design
- Changing the yield inheritance design from F063 - Design is correct
- Batch calculation algorithm changes - Works correctly with primitives
- cost_service updates - Only if it exists and accesses yields (verify in planning phase)
