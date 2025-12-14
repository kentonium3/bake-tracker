# Feature Specification: Unit Conversion Simplification

**Feature Branch**: `019-unit-conversion-simplification`
**Created**: 2025-12-14
**Status**: Draft
**Input**: Remove redundant unit conversion mechanisms (recipe_unit column and UnitConversion table) - keep 4-field density as canonical source for all conversions

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Simplified Data Entry (Priority: P1)

As a user entering ingredient data, I only need to provide the 4 density values (e.g., "1 cup = 4.25 oz") rather than maintaining separate conversion records.

**Why this priority**: This is the primary user-facing benefit - reduced complexity when adding or editing ingredients.

**Independent Test**: Can be fully tested by adding a new ingredient with only density values and verifying all unit conversions work correctly.

**Acceptance Scenarios**:

1. **Given** a new ingredient with density values (1 cup = 4.25 oz), **When** the system needs to convert between weight and volume units, **Then** the conversion is calculated dynamically from the density specification.
2. **Given** an existing ingredient with density values, **When** viewing ingredient details, **Then** no separate "unit conversions" section appears (only density specification).

---

### User Story 2 - Cleaner Import/Export Format (Priority: P2)

As a user importing or exporting data, the JSON format no longer includes a separate `unit_conversions` array, simplifying the data structure.

**Why this priority**: Directly impacts data interchange and catalog import workflows.

**Independent Test**: Can be tested by exporting data and verifying the v3.3 format has no `unit_conversions` array, then re-importing successfully.

**Acceptance Scenarios**:

1. **Given** a database with ingredients, **When** exporting to JSON, **Then** the output is v3.3 format with no `unit_conversions` array.
2. **Given** a v3.3 JSON file with ingredients (density only), **When** importing, **Then** all ingredients import successfully with working unit conversions.
3. **Given** a v3.2 JSON file (old format with unit_conversions), **When** attempting to import, **Then** the system rejects it with a clear version error message.

---

### User Story 3 - Consistent Cost Calculations (Priority: P1)

As a user tracking recipe costs, the cost calculations continue to work identically after this refactoring.

**Why this priority**: Critical regression prevention - cost calculation accuracy is a core application promise.

**Independent Test**: Can be tested by comparing cost calculations before and after the change for a set of known recipes.

**Acceptance Scenarios**:

1. **Given** a recipe with ingredients requiring unit conversion, **When** calculating recipe cost, **Then** the result matches the pre-refactoring calculation exactly.
2. **Given** an ingredient with density specified, **When** converting from weight to volume (or vice versa), **Then** `convert_any_units()` produces correct results using only density data.

---

### Edge Cases

- What happens when an ingredient has no density specified? System falls back to standard conversions (weight-to-weight, volume-to-volume) and fails gracefully for cross-type conversions with a clear message.
- How does system handle importing old v3.2 format files? Rejects with clear error: "Unsupported file version: 3.2. This application requires v3.3 format."
- What if a recipe references an ingredient that was deleted? Existing FK constraints and application behavior remain unchanged (this feature doesn't affect that logic).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST remove the `recipe_unit` column from the Ingredient model
- **FR-002**: System MUST delete the UnitConversion model and database table entirely
- **FR-003**: System MUST update import/export format from v3.2 to v3.3, removing the `unit_conversions` array
- **FR-004**: System MUST derive all unit conversions dynamically from the 4-field density specification on Ingredient
- **FR-005**: System MUST reject imports of v3.2 (or older) format files with a clear error message
- **FR-006**: System MUST produce identical cost calculation results after refactoring (regression safety)
- **FR-007**: All existing tests MUST pass (or be appropriately updated for removed functionality)

### Key Entities

- **Ingredient**: Retains 4-field density specification (`density_volume_value`, `density_volume_unit`, `density_weight_value`, `density_weight_unit`). Loses `recipe_unit` column.
- **UnitConversion**: DELETED - no longer exists as a model or table.
- **Import/Export JSON**: Version bumped to 3.3, `unit_conversions` array removed from schema.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero `unit_conversions` records exist in the database after migration
- **SC-002**: No `recipe_unit` column exists on the ingredients table after migration
- **SC-003**: Cost calculations for all existing recipes produce identical results before and after the change
- **SC-004**: All test data files are updated to v3.3 format with no `unit_conversions` array
- **SC-005**: Import of v3.2 format files fails with a clear, user-friendly error message
- **SC-006**: Test coverage remains at or above 70% for affected services

## Assumptions

- The existing 4-field density data on all 160 ingredients in the catalog is accurate and sufficient for all conversion needs.
- The `convert_any_units()` function already handles all necessary conversion logic via density - no new conversion code is needed.
- The export/reset/import workflow (Constitution VI) is the approved approach for schema changes in the desktop phase.

## Out of Scope

- Changes to Product model (purchase_unit, purchase_quantity remain)
- Changes to RecipeIngredient model (unit field remains - it's the recipe's declared unit)
- Standard conversion tables (oz to lb, cup to tbsp) - these remain in unit_converter.py
- Density input UI (Feature 010 already complete)
- Any migration scripts (using export/reset/import workflow instead)

## Dependencies

- Constitution v1.2.0 (schema change via export/reset/import workflow)
- Working import/export (v3.2) - needed to export before schema change
- 4-field density model (Feature 010) - already complete

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Cost calculation regression | Low | High | Regression test comparing before/after results |
| Import fails on old format | Medium | Medium | Version detection with clear error message |
| Missing conversion path | Low | Medium | `convert_any_units()` handles all cases via density |
