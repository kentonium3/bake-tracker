# Feature Specification: Dual-Yield Recipe Output Support

**Feature Branch**: `083-dual-yield-recipe-output-support`
**Created**: 2026-01-29
**Status**: Draft
**Input**: F084 Dual-Yield Support - Enable recipes to define both EA (whole unit) and SERVING yields

## Overview

Add `yield_type` classification to FinishedUnit records, enabling planning services to distinguish between whole-unit (EA) and serving-based (SERVING) yields for the same recipe output. This separates user-facing descriptions from calculation semantics.

**Key Data Model Change:**

Current FinishedUnit:
- `unit` (text) - free text like "cookie" or "slice"
- `quantity` (decimal) - yield amount

New FinishedUnit:
- `unit_description` (text) - user-facing name ("mini cookie", "large cake")
- `yield_type` (text) - calculation semantic ('EA' or 'SERVING')
- `quantity` (decimal) - yield amount for this definition

**Example - Cookie Recipe (3 FinishedUnits, all SERVING):**

| unit_description | yield_type | quantity |
|------------------|------------|----------|
| mini cookie | SERVING | 48 |
| standard cookie | SERVING | 24 |
| large cookie | SERVING | 12 |

**Example - Cake Recipe (6 FinishedUnits):**

| unit_description | yield_type | quantity |
|------------------|------------|----------|
| small cake | EA | 1 |
| medium cake | EA | 1 |
| large cake | EA | 1 |
| small cake | SERVING | 4 |
| medium cake | SERVING | 8 |
| large cake | SERVING | 16 |

## User Scenarios & Testing

### User Story 1 - Add Yield Type to Existing Recipe (Priority: P1)

As a baker, I want to classify my recipe outputs as either whole units (EA) or servings (SERVING) so that planning services can calculate correctly based on context.

**Why this priority**: This is the core capability - without yield_type classification, the entire feature has no value. Every other story depends on this.

**Independent Test**: Can be tested by editing any recipe to add yield_type to its finished units. Delivers immediate classification value.

**Acceptance Scenarios**:

1. **Given** a recipe with a finished unit "large cookie" quantity 12, **When** I edit the finished unit to set yield_type="SERVING", **Then** the finished unit is saved with unit_description="large cookie", yield_type="SERVING", quantity=12.

2. **Given** a recipe with no finished units, **When** I add a finished unit with unit_description="whole cake", yield_type="EA", quantity=1, **Then** the finished unit is saved and associated with the recipe.

3. **Given** a recipe with finished unit yield_type="SERVING", **When** I change yield_type to "EA", **Then** the change is persisted and displayed correctly.

---

### User Story 2 - Add Multiple Yield Definitions Per Recipe (Priority: P1)

As a baker, I want to define multiple yield outputs for the same recipe (e.g., small/medium/large cakes with both EA and SERVING yields) so that I can track different output variants from the same recipe.

**Why this priority**: Multiple yields per recipe is equally essential - a cake recipe needs both EA (for delivery) and SERVING (for consumption planning) yields.

**Independent Test**: Can be tested by adding multiple finished units to a single recipe. Delivers immediate multi-yield capability.

**Acceptance Scenarios**:

1. **Given** a cake recipe with finished unit (small cake, EA, 1), **When** I add another finished unit (small cake, SERVING, 4), **Then** both finished units are saved and displayed.

2. **Given** a recipe, **When** I add finished units (small, EA, 1), (medium, EA, 1), (large, EA, 1), (small, SERVING, 4), (medium, SERVING, 8), (large, SERVING, 16), **Then** all six finished units are saved correctly.

3. **Given** a recipe with finished units (mini cookie, SERVING, 48), (standard cookie, SERVING, 24), **When** I add (large cookie, SERVING, 12), **Then** all three SERVING yields exist on the recipe.

---

### User Story 3 - Export/Import Dual-Yield Recipes (Priority: P2)

As a user, I want to export recipes with their yield_type classifications and import them on a fresh database so that I can migrate data during schema changes.

**Why this priority**: Export/import is critical for the constitutional schema change strategy, but depends on the data model being defined first.

**Independent Test**: Can be tested by exporting a recipe with multiple finished units, resetting database, and importing. Delivers data portability.

**Acceptance Scenarios**:

1. **Given** a recipe with multiple finished units including yield_type, **When** I export all recipes, **Then** the JSON includes all finished_units with unit_description, yield_type, and quantity fields.

2. **Given** a JSON export with recipe finished_units containing yield_type, **When** I import to a fresh database, **Then** all finished_units are created with correct yield_type values.

3. **Given** an export with invalid yield_type value "INVALID", **When** I import, **Then** the import fails with a clear validation error.

4. **Given** an export with duplicate (recipe_id, unit_description, yield_type) combinations, **When** I import, **Then** the import fails with a clear uniqueness error.

---

### User Story 4 - View Yield Types in Recipe UI (Priority: P2)

As a baker, I want to see which of my recipe outputs are EA vs SERVING so that I understand what each yield represents.

**Why this priority**: UI display is important for usability but depends on the data model changes being in place first.

**Independent Test**: Can be tested by viewing recipe detail for a recipe with multiple finished units. Delivers clarity on yield classifications.

**Acceptance Scenarios**:

1. **Given** a recipe with finished units (small cake, EA, 1) and (small cake, SERVING, 4), **When** I view the recipe detail, **Then** I see both finished units clearly labeled with their yield_type.

2. **Given** a recipe with only SERVING yields, **When** I view the recipe detail, **Then** all finished units show "SERVING" as their yield_type.

---

### User Story 5 - Migrate Existing Data (Priority: P3)

As an existing user, I want my current finished_unit data automatically migrated to the new schema so that I don't lose any recipe information.

**Why this priority**: Migration is required but is a one-time operation. Constitutional workflow (export → schema change → import) handles this.

**Independent Test**: Can be tested by exporting current data, transforming, and importing. Delivers seamless upgrade path.

**Acceptance Scenarios**:

1. **Given** existing finished_unit with unit="cookie" and quantity=24, **When** migration runs, **Then** finished_unit has unit_description="cookie", yield_type="SERVING", quantity=24.

2. **Given** multiple existing recipes with various finished_units, **When** migration runs, **Then** all finished_units have yield_type="SERVING" (conservative default) and unit_description preserves original unit text.

---

### Edge Cases

- What happens when user tries to save a finished unit without yield_type? → Validation error, yield_type is required.
- What happens when user creates duplicate (unit_description, yield_type) on same recipe? → Validation error due to uniqueness constraint.
- What happens when importing old export format without yield_type field? → Import service should handle gracefully (apply SERVING default or reject with clear error - design decision for planning phase).

## Requirements

### Functional Requirements

- **FR-001**: System MUST add `yield_type` field to FinishedUnit with values constrained to 'EA' or 'SERVING'
- **FR-002**: System MUST rename `unit` field to `unit_description` on FinishedUnit
- **FR-003**: System MUST enforce UNIQUE constraint on (recipe_id, unit_description, yield_type)
- **FR-004**: System MUST allow unlimited FinishedUnit records per recipe
- **FR-005**: System MUST validate yield_type is not empty/null when saving FinishedUnit
- **FR-006**: Recipe service MUST validate yield_type values during create/update operations
- **FR-007**: Export service MUST include unit_description and yield_type in finished_units array
- **FR-008**: Import service MUST validate yield_type values during import
- **FR-009**: Import service MUST enforce uniqueness constraint during import
- **FR-010**: Recipe UI MUST display yield_type for each finished unit
- **FR-011**: Recipe UI MUST allow editing yield_type for finished units
- **FR-012**: Migration MUST set yield_type='SERVING' for all existing finished_units
- **FR-013**: Migration MUST copy existing `unit` value to `unit_description`

### Key Entities

- **FinishedUnit**: Represents one yield definition for a recipe. Contains unit_description (user-facing name), yield_type (EA or SERVING classification), and quantity (yield amount). Multiple FinishedUnits can exist per recipe. Uniqueness enforced on (recipe_id, unit_description, yield_type).

- **Recipe**: Parent entity that has many FinishedUnits. No changes to Recipe entity itself, only to the relationship.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All existing recipes retain their finished unit data after migration with no data loss
- **SC-002**: Users can create recipes with 6+ finished units (multiple variants with both EA and SERVING yields)
- **SC-003**: Export/import cycle preserves all yield_type classifications round-trip
- **SC-004**: Recipe UI clearly distinguishes EA yields from SERVING yields
- **SC-005**: Invalid yield_type values are rejected with clear error messages before data is persisted

## Out of Scope

- Planning service yield selection logic (deferred to planning module)
- Category-driven smart defaults for yield_type
- Automatic serving calculation from EA yield
- UI for choosing yield during event recipe selection
- Learning user's preferred unit descriptions
