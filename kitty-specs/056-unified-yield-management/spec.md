# Feature Specification: Unified Yield Management

**Feature Branch**: `056-unified-yield-management`
**Created**: 2026-01-16
**Status**: Draft
**Input**: User feedback on redundant yield data in Recipe edit form requiring consolidation into unified FinishedUnit-based yield types.

## Summary

The Recipe model and UI currently have redundant yield information in two separate locations: top-level `yield_quantity`/`yield_unit` fields and FinishedUnit yield types with `display_name`/`items_per_batch`. This creates confusion and data duplication. This feature unifies yield tracking into a single location (FinishedUnit yield types) with a complete 3-field structure: description (what is produced), unit (measurement type), and quantity per batch (how many). This aligns data structure with actual workflow and eliminates the legacy redundancy.

**Critical**: At least one FinishedUnit with complete yield data is REQUIRED per recipe for event planning batch calculations to function. Without this data, the system cannot determine how many batches are needed to fulfill event requirements.

## User Scenarios & Testing

### User Story 1 - Define Primary Recipe Yield (Priority: P1)

As a baker entering a new recipe, I want to specify what the recipe produces (e.g., "24 large cookies") in a single, clear location so that the recipe has complete yield information for future planning workflows.

**Why this priority**: FOUNDATIONAL REQUIREMENT. Every recipe must have at least one complete yield type (FinishedUnit with display_name, item_unit, and items_per_batch). Future event planning workflows depend on this data being present and accurate.

**Independent Test**: Can be fully tested by creating a new recipe with one yield type row containing description ("Large Cookie"), unit ("cookie"), and quantity (24), verifying the FinishedUnit is created correctly, and confirming validation prevents saving recipes without complete yield data.

**Acceptance Scenarios**:

1. **Given** I'm creating a new recipe, **When** I add yield information, **Then** I see one yield type row with three fields: Description, Unit, and Quantity per batch
2. **Given** I fill in all three yield fields (Description: "Large Cookie", Unit: "cookie", Quantity: 24), **When** I save the recipe, **Then** the recipe saves successfully with one FinishedUnit record
3. **Given** I'm editing an existing recipe, **When** I leave the description field blank, **Then** validation prevents saving and shows "At least one complete yield type required"
4. **Given** I'm editing an existing recipe, **When** I leave the unit field blank, **Then** validation prevents saving and shows "Unit required for yield type"
5. **Given** I'm editing an existing recipe, **When** I leave the quantity field blank, **Then** validation prevents saving and shows "Quantity required for yield type"
6. **Given** I attempt to save a recipe with no complete yield types, **Then** validation prevents saving and shows "Recipe must have at least one complete yield type"

---

### User Story 2 - Define Multiple Yield Options (Priority: P1)

As a baker working with flexible recipes, I want to specify multiple yield types for a single recipe (e.g., "1 full 9-inch cake" OR "12 cupcakes from the same batter") so that I have production options documented for future use.

**Why this priority**: FOUNDATIONAL DATA STRUCTURE. Many recipes can produce different finished goods from the same base recipe (full cakes vs cupcakes, large cookies vs small cookies). Each yield option creates a different FinishedUnit that can be selected independently during event planning. This capability is essential for the data model to support future planning workflows correctly.

**Independent Test**: Can be fully tested by adding 2+ yield type rows to a recipe (Row 1: "Full 9-inch Cake", "cake", 1; Row 2: "Cupcakes", "cupcake", 12), verifying separate FinishedUnit records are created, and confirming each has complete and independent yield data.

**Acceptance Scenarios**:

1. **Given** I'm editing a recipe, **When** I click "Add Yield Type", **Then** a new yield type row appears with empty Description, Unit, and Quantity fields
2. **Given** I have multiple yield type rows, **When** I fill in different values (Row 1: "Full Cake", "cake", 1; Row 2: "Cupcakes", "cupcake", 12), **Then** both yield types save to separate FinishedUnit records
3. **Given** a recipe has multiple FinishedUnits, **When** I query the recipe, **Then** I can retrieve all associated FinishedUnit records with their complete yield data
4. **Given** I have multiple yield type rows, **When** I delete all but one complete row, **Then** the recipe saves successfully with one FinishedUnit
5. **Given** I have multiple yield type rows with only one complete, **When** I try to save, **Then** validation warns about incomplete rows but allows saving

---

### User Story 3 - Transform Import Data for New Schema (Priority: P1)

As a developer implementing this feature, I need to create a transformation script that converts existing recipe export data to the new schema structure so that all recipes have the required FinishedUnit yield data after import.

**Why this priority**: Data preservation is critical per Constitution principle II (Data Integrity). The transformation ensures all recipes have at least one FinishedUnit with complete yield data after the schema change.

**Implementation Note**: This is NOT an in-app migration. The transformation is performed during development as part of this feature's implementation. The workflow is:
1. Export current data using existing backup functionality
2. Developer runs transformation script to convert `recipes.json` structure
3. User imports the transformed data after schema change

**Independent Test**: Can be tested by running the transformation script on test export files (e.g., `sample_data_min.json`, `sample_data_all.json`) and verifying all yield data is correctly converted to FinishedUnit records.

**Acceptance Scenarios**:

1. **Given** an export file with recipes containing yield_description, **When** the transformation script runs, **Then** each recipe creates one FinishedUnit with display_name from yield_description, item_unit from yield_unit, items_per_batch from yield_quantity, and a unique slug
2. **Given** an export file with recipes WITHOUT yield_description, **When** the transformation script runs, **Then** each recipe creates one FinishedUnit with display_name as "Standard {recipe_name}", item_unit from yield_unit, items_per_batch from yield_quantity, and a unique slug
3. **Given** slug collision would occur, **When** the transformation script runs, **Then** it appends numeric suffix (_2, _3, etc.) to ensure uniqueness
4. **Given** transformation is complete, **When** the transformed file is imported, **Then** 100% of recipes have at least one associated FinishedUnit record
5. **Given** `sample_data_min.json` and `sample_data_all.json`, **When** transformation script runs, **Then** both files are successfully converted and importable

---

### User Story 4 - Remove Legacy Yield Fields from UI (Priority: P2)

As a user editing recipes, I want to see only the unified yield type section so that the interface is clear and I don't get confused about which fields to use.

**Why this priority**: UI simplification improves usability, but the underlying data transformation (P1) must happen first.

**Independent Test**: Can be visually verified by opening the recipe edit form and confirming no yield_quantity/yield_unit fields appear at the top of the Yield Information section.

**Acceptance Scenarios**:

1. **Given** I open the recipe edit form, **When** I view the Yield Information section, **Then** I see only "Yield Types" with add/remove row controls
2. **Given** I'm editing a recipe, **When** I look for yield_quantity and yield_unit fields, **Then** they do not appear in the UI
3. **Given** I have an existing recipe with one FinishedUnit, **When** I open it for editing, **Then** the yield type row shows the FinishedUnit's display_name, item_unit, and items_per_batch
4. **Given** I have an existing recipe with multiple FinishedUnits, **When** I open it for editing, **Then** multiple yield type rows appear, one per FinishedUnit

---

### User Story 5 - Verify Generated Yield Types in Finished Units Catalog (Priority: P1)

As a user reviewing my recipe data after import, I want to see all generated yield types in the Finished Units catalog so I can verify the data transformation was successful and edit any auto-generated descriptions if needed.

**Why this priority**: The Finished Units tab (Catalog > Recipes > Finished Units) is the primary view for verifying that FinishedUnit records were correctly created during import. This validates that the transformation and import worked correctly.

**Independent Test**: Can be tested by importing transformed data and navigating to Catalog > Recipes > Finished Units to verify all expected records appear with correct data.

**Acceptance Scenarios**:

1. **Given** data has been imported with transformed recipes, **When** I navigate to Catalog > Recipes > Finished Units, **Then** I see one row per FinishedUnit with columns showing Name (display_name), Unit (item_unit), Quantity (items_per_batch), and Recipe
2. **Given** a recipe had yield_description "Large Sugar Cookie", **When** I view the Finished Units tab, **Then** I see a row with display_name "Large Sugar Cookie"
3. **Given** a recipe had NO yield_description, **When** I view the Finished Units tab, **Then** I see a row with display_name "Standard {recipe_name}" (e.g., "Standard Chocolate Chip Cookie")
4. **Given** I double-click a Finished Unit row, **When** the action completes, **Then** the parent Recipe edit form opens with the yield type row visible and editable
5. **Given** 50 recipes were imported, **When** I view the Finished Units tab, **Then** I see at least 50 FinishedUnit records (one per recipe minimum)

---

### Edge Cases

- **What happens when a recipe has yield_quantity/yield_unit but no FinishedUnits?** Transformation script creates a FinishedUnit from the legacy data using display_name generation logic.
- **What happens when a recipe has both legacy yield fields AND existing FinishedUnits?** Legacy fields are ignored; existing FinishedUnits are preserved (no duplicates created).
- **What happens when importing a recipe with no yield data at all?** Import validation requires at least one complete yield type before creating the recipe.
- **What happens to batch_percentage and portion_description fields in FinishedUnit?** These are part of the BATCH_PORTION yield mode and are not affected by this feature. They remain available for cake/portion-based yields.
- **What if user tries to delete the last yield type row?** Validation prevents deletion and shows "At least one yield type required per recipe".
- **What if user adds 10 yield type rows but only completes 2?** Validation allows saving; only complete rows create FinishedUnit records. Incomplete rows are discarded with a warning.
- **How is display_name generated when yield_description is missing?** Uses pattern "Standard {recipe_name}" to create a sensible default that can be edited later.

## Requirements

### Functional Requirements

#### Data Model Changes

- **FR-001**: Recipe model MUST deprecate `yield_quantity`, `yield_unit`, and `yield_description` fields (mark nullable for transition phase)
- **FR-002**: FinishedUnit model MUST have `item_unit` field to store the unit type (e.g., "cookie", "cake", "slice")
- **FR-003**: FinishedUnit model MUST retain `display_name` field for yield description
- **FR-004**: FinishedUnit model MUST retain `items_per_batch` field for quantity per recipe batch

#### Validation Rules

- **FR-005**: System MUST require at least one complete FinishedUnit (display_name + item_unit + items_per_batch) per Recipe
- **FR-006**: System MUST validate that `items_per_batch` is a positive integer greater than zero
- **FR-007**: System MUST validate that `item_unit` is not empty when `yield_mode` is DISCRETE_COUNT
- **FR-008**: System MUST validate that `display_name` is not empty for all FinishedUnits
- **FR-009**: System MUST allow deleting yield type rows only if at least one complete row remains

#### UI Changes

- **FR-010**: Recipe edit form MUST remove top-level yield_quantity and yield_unit fields from the Yield Information section
- **FR-011**: Recipe edit form MUST display yield type rows with three fields: Description (display_name), Unit (item_unit), Quantity (items_per_batch)
- **FR-012**: Recipe edit form MUST provide "Add Yield Type" button to create new yield type rows
- **FR-013**: Recipe edit form MUST provide "Remove" button on each yield type row (disabled if only one row exists)
- **FR-014**: Recipe edit form MUST pre-populate yield type rows from existing FinishedUnit records when editing a recipe

#### Import/Export Changes

- **FR-015**: Export service MUST include `item_unit` in FinishedUnit exports
- **FR-016**: Import service MUST create FinishedUnit records from yield type data (display_name, item_unit, items_per_batch)
- **FR-017**: Import service MUST validate at least one complete yield type exists before creating Recipe
- **FR-018**: Import service MUST handle legacy recipe exports with yield_quantity/yield_unit by creating appropriate FinishedUnit records
- **FR-019**: Import service MUST generate display_name for recipes without yield_description using pattern "Standard {recipe_name}"
- **FR-020**: Import service MUST preserve yield_description as display_name when present in legacy data

#### Data Transformation Strategy

- **FR-021**: Catalog import files MUST be transformed to new structure via developer script (no automatic migration in app)
- **FR-022**: Transformation script MUST map legacy yield data to FinishedUnit structure:
  - yield_description -> display_name (if present)
  - "Standard {recipe_name}" -> display_name (if yield_description absent)
  - yield_unit -> item_unit
  - yield_quantity -> items_per_batch
- **FR-023**: After transformation and import, Recipe model MAY remove yield_quantity/yield_unit columns entirely (no backward compatibility required)
- **FR-024**: Transformation script MUST generate unique `slug` for each FinishedUnit using pattern `{recipe_slug}_{yield_type_suffix}` where recipe_slug = slugify(recipe_name) and yield_type_suffix = slugify(yield_description) if present, else "standard"
- **FR-025**: Transformation script MUST handle slug collisions by appending numeric suffix (_2, _3, etc.) to ensure uniqueness
- **FR-026**: Transformation script MUST process `sample_data_min.json` and `sample_data_all.json` as primary test cases

### Key Entities

- **Recipe**: Main recipe model; yield fields (yield_quantity, yield_unit, yield_description) will be deprecated
- **FinishedUnit**: Enhanced to be the single source of truth for recipe yields with three key fields:
  - `display_name`: Description of what is produced (e.g., "Large Sugar Cookie", "Standard Chocolate Chip Cookie", "9-inch Cake")
  - `item_unit`: Unit type (e.g., "cookie", "cake", "slice", "bar")
  - `items_per_batch`: Quantity this recipe produces (e.g., 24, 1, 12)
- **YieldTypeRow**: UI widget representing one yield type in the recipe form (maps to one FinishedUnit)

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of recipes have at least one FinishedUnit with complete yield data (display_name, item_unit, items_per_batch)
- **SC-002**: Recipe edit form shows zero top-level yield fields (yield_quantity/yield_unit removed)
- **SC-003**: Recipe edit form shows all existing FinishedUnits as editable yield type rows
- **SC-004**: Import service successfully creates recipes with yield types from new export format
- **SC-005**: Transformed recipes retain 100% of original yield data in FinishedUnit structure
- **SC-006**: User can create multi-yield recipes (e.g., "1 cake" OR "12 cupcakes") in single edit session
- **SC-007**: All FinishedUnit records have non-null display_name, item_unit, and items_per_batch values
- **SC-008**: Transformed recipes without yield_description have sensible auto-generated display_name (e.g., "Standard Chocolate Chip Cookie")
- **SC-009**: Finished Units tab (Catalog > Recipes > Finished Units) displays all generated FinishedUnit records after import
- **SC-010**: Finished Units tab shows display_name, item_unit, items_per_batch, and parent Recipe columns correctly populated
- **SC-011**: Double-click on Finished Unit row navigates to parent Recipe edit form with yield type row visible

## Out of Scope

- Changing FinishedUnit's `yield_mode`, `batch_percentage`, or `portion_description` fields (these support BATCH_PORTION mode for cakes/portions)
- Event planning workflow implementation (how users select FinishedGoods/FinishedUnits for events)
- Batch calculation logic in event planning (separate feature, assumes this data exists)
- UI for selecting yield types during event planning (separate feature)
- Displaying batch calculation results in event planning (separate feature)
- Adding new yield types beyond DISCRETE_COUNT and BATCH_PORTION
- Implementing automatic in-app migration (per Constitution VI, use export/transform/import)
- Changing Recipe categories or other unrelated Recipe fields
- Modifying RecipeIngredient or RecipeComponent models

## Assumptions

- User is willing to run export/transform/import cycle for schema change (per Constitution VI)
- Transformation script will be developed as part of this feature implementation (not a separate deliverable)
- Transformation script will process `sample_data_min.json`, `sample_data_all.json`, and user backup files
- Future event planning workflows will query FinishedUnit records to determine available finished goods
- Future batch calculations will use FinishedUnit.items_per_batch for determining batches needed
- FinishedUnit model supports multiple records per recipe (1:many relationship exists)
- Recipe form UI uses a widget pattern that supports dynamic row addition/removal
- Import/export services have established patterns for handling nested data structures
- Current FinishedUnit records (if any) use DISCRETE_COUNT mode primarily; BATCH_PORTION mode is rare
- No recipes currently have FinishedUnits associated; all yield data is in legacy Recipe fields
- `item_unit` field already exists in FinishedUnit model (currently nullable, will be required for DISCRETE_COUNT mode)
