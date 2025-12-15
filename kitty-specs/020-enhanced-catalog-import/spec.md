# Feature Specification: Enhanced Catalog Import

**Feature Branch**: `020-enhanced-catalog-import`
**Created**: 2025-12-14
**Status**: Draft
**Input**: User description: "Feature 020: Enhanced Data Import - Separate catalog import pathway for ingredients, products, and recipes with ADD_ONLY and AUGMENT modes"

## Problem Statement

The current unified import/export system (v3.3) conflates two fundamentally different data types:

1. **Reference/Catalog Data** - Ingredients, Products, Recipes
   - Slowly changing, potentially shared across users
   - Candidates for pre-populated libraries
   - Large metadata sets that are burdensome to enter manually

2. **Transactional Data** - Purchases, Inventory Items, Event Assignments, Production Records
   - User-specific, frequently changing
   - Represents actual user activity and inventory state

This conflation prevents safe catalog expansion without risking user data. A 160-ingredient catalog is waiting to be imported, and AI-generated recipe collections cannot be imported incrementally.

## Solution Overview

Create a separate **Catalog Import** pathway that handles ingredients, products, and recipes with safe modes (ADD_ONLY, AUGMENT), while preserving the existing unified import/export for development workflows.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Import New Ingredients via CLI (Priority: P1)

A user has a JSON file containing 160 new baking ingredients with density data. They want to add these to their database without affecting their existing recipes or pantry data.

**Why this priority**: This is the primary use case driving the feature - importing the pending ingredient catalog. CLI import is the foundational capability all other stories depend on.

**Independent Test**: Can be fully tested by running `python -m src.utils.import_catalog ingredients.json` and verifying new ingredients appear in the database while existing data remains unchanged.

**Acceptance Scenarios**:

1. **Given** an empty database, **When** user runs `python -m src.utils.import_catalog catalog.json`, **Then** all ingredients, products, and recipes from the file are created.

2. **Given** a database with existing ingredients, **When** user imports a file with some overlapping slugs, **Then** new ingredients are added and existing ones are skipped with a logged message.

3. **Given** a file with only ingredients, **When** user runs `python -m src.utils.import_catalog ingredients.json --entity=ingredients`, **Then** only ingredients are processed.

---

### User Story 2 - Augment Ingredient Metadata (Priority: P2)

A user has existing ingredients but many have null density values. They obtain a file with density data for these ingredients and want to fill in the missing values without overwriting any existing data.

**Why this priority**: Metadata enrichment is a key value-add after initial catalog population. Enables incremental improvement of data quality.

**Independent Test**: Can be fully tested by running `python -m src.utils.import_catalog density_data.json --entity=ingredients --mode=augment` and verifying only null fields are updated.

**Acceptance Scenarios**:

1. **Given** an ingredient with null `density_volume_value`, **When** user imports augment data with a density value for that slug, **Then** the density field is populated.

2. **Given** an ingredient with existing `density_volume_value=0.55`, **When** user imports augment data with `density_volume_value=0.60` for that slug, **Then** the original value (0.55) is preserved unchanged.

3. **Given** an ingredient that doesn't exist in the database, **When** user imports augment data for that slug, **Then** a new ingredient record is created with all provided fields.

---

### User Story 3 - Preview Changes with Dry-Run (Priority: P2)

A user wants to see what an import would do before committing any changes. They run a dry-run to review adds, skips, and potential errors.

**Why this priority**: Risk mitigation for user data. Users need confidence before modifying their database.

**Independent Test**: Can be fully tested by running `python -m src.utils.import_catalog catalog.json --dry-run` and verifying no database changes occur but a complete preview is displayed.

**Acceptance Scenarios**:

1. **Given** any import file, **When** user adds `--dry-run` flag, **Then** the system reports what would be added/skipped/failed without modifying the database.

2. **Given** a dry-run that shows 5 adds, 3 skips, **When** user runs the same import without `--dry-run`, **Then** the actual results match the preview.

---

### User Story 4 - Import Recipes with FK Validation (Priority: P2)

A user has AI-generated recipes that reference ingredients. The import validates that all referenced ingredients exist before creating any recipes.

**Why this priority**: Recipes depend on ingredients; FK validation ensures data integrity.

**Independent Test**: Can be fully tested by importing a recipe file and verifying validation errors are reported with actionable messages.

**Acceptance Scenarios**:

1. **Given** recipes referencing ingredients that all exist, **When** user imports the recipe file, **Then** all recipes are created successfully.

2. **Given** a recipe referencing `organic_vanilla` which doesn't exist, **When** user imports that recipe, **Then** the import fails for that recipe with error: "Recipe 'Vanilla Cake' references missing ingredient: 'organic_vanilla'. Import the ingredient first or remove from recipe."

3. **Given** a recipe with slug `chocolate-chip-cookies` that already exists with different content, **When** user imports, **Then** the import fails for that recipe with error: "Recipe slug 'chocolate-chip-cookies' already exists. Existing recipe: 'Chocolate Chip Cookies' (yields 24). Import recipe: 'Chocolate Chip Cookies' (yields 36). To import, rename the slug or delete the existing recipe."

---

### User Story 5 - Import Catalog via UI (Priority: P3)

A non-technical user wants to import a catalog file using the graphical interface rather than command line.

**Why this priority**: UI access is important for the primary user (non-technical), but CLI must work first.

**Independent Test**: Can be fully tested by opening File > Import Catalog..., selecting a file, and verifying the import completes with a results dialog.

**Acceptance Scenarios**:

1. **Given** the application is running, **When** user clicks File > Import Catalog..., **Then** a file picker dialog opens filtered to .json files.

2. **Given** the CatalogImportDialog is open, **When** user selects a file and clicks Import, **Then** the import executes and shows a results summary.

3. **Given** the user checks "Preview changes before importing", **When** user clicks Preview, **Then** a scrollable preview of changes is shown before confirming.

---

### User Story 6 - Partial Success with Actionable Errors (Priority: P3)

An import file contains some valid and some invalid records. The system commits valid records and reports failures with clear, actionable error messages.

**Why this priority**: Partial success maximizes value from imperfect import files while maintaining data integrity.

**Independent Test**: Can be fully tested by importing a file with mixed valid/invalid records and verifying valid ones are committed while failures are clearly reported.

**Acceptance Scenarios**:

1. **Given** 10 ingredients where 8 are valid and 2 have FK errors, **When** user imports, **Then** 8 are added, 2 fail, and report lists each failure with specific reason.

2. **Given** partial success import completes, **When** user views the report, **Then** each failure includes: entity type, identifier, specific error, and suggested fix.

---

### Edge Cases

- What happens when the file is not valid JSON? System reports "Invalid JSON format" with parse error location.
- What happens when the file has `version: "3.3"` instead of `catalog_version`? System routes to unified import (existing behavior preserved).
- What happens when a recipe references another recipe that doesn't exist (nested recipes)? Validation fails with actionable error listing the missing component.
- What happens when import would create a circular recipe reference? Validation fails before any records are created.
- How does system handle very large files (10,000+ records)? Process in batches with progress indication; memory-efficient streaming if possible.
- What happens when AUGMENT mode is requested for recipes? Error: "AUGMENT mode is not supported for recipes. Use ADD_ONLY mode."

---

## Requirements *(mandatory)*

### Functional Requirements

**Service Layer**

- **FR-001**: System MUST provide independent entity-specific import functions: `import_ingredients()`, `import_products()`, `import_recipes()` - each callable standalone for future integrations.
- **FR-002**: System MUST provide a coordinator function `import_catalog()` that dispatches to entity-specific functions in dependency order (ingredients -> products -> recipes).
- **FR-003**: System MUST support ADD_ONLY mode (default): create new records, skip existing (by unique key).
- **FR-004**: System MUST support AUGMENT mode for ingredients and products: update NULL fields on existing records, add new records.
- **FR-005**: System MUST reject AUGMENT mode for recipes with a clear error message.
- **FR-006**: System MUST validate all FK references before creating any records (fail-fast).
- **FR-007**: System MUST support dry-run mode that reports what would happen without modifying the database.
- **FR-008**: System MUST support partial success: commit valid records and report failures with actionable error messages.
- **FR-009**: System MUST accept optional `session` parameter for transactional composition with other services.

**CLI**

- **FR-010**: System MUST provide `python -m src.utils.import_catalog <file>` CLI command.
- **FR-011**: CLI MUST support `--mode=add` (default) and `--mode=augment` flags.
- **FR-012**: CLI MUST support `--entity=ingredients|products|recipes` flag to filter import to specific entity type.
- **FR-013**: CLI MUST support `--dry-run` flag for preview mode.
- **FR-014**: CLI MUST support `--verbose` flag for detailed output showing all decisions.

**UI**

- **FR-015**: System MUST add "Import Catalog..." menu item to File menu (below existing Import/Export items, with separator).
- **FR-016**: CatalogImportDialog MUST provide file picker, mode selection (radio: Add Only/Augment), entity checkboxes, and dry-run checkbox.
- **FR-017**: When Recipes checkbox is selected, AUGMENT mode radio button MUST be disabled with tooltip explaining why.
- **FR-018**: When dry-run checkbox is checked, Import button label MUST change to "Preview...".
- **FR-019**: After import completes, results dialog MUST show counts (added/skipped/failed) per entity type.
- **FR-020**: Results dialog MUST include expandable "Details" section for error messages.
- **FR-021**: After successful import, affected UI tabs (Ingredients, Recipes) MUST refresh their data.

**Validation & Error Handling**

- **FR-022**: Product import MUST validate `ingredient_slug` FK exists before creating product.
- **FR-023**: Recipe import MUST validate all `ingredient_slug` references in recipe ingredients exist.
- **FR-024**: Recipe import MUST validate all nested recipe component references exist (no circular references).
- **FR-025**: Recipe import MUST reject slug collisions with existing recipes, providing detailed error: existing recipe info vs import recipe info.
- **FR-026**: All validation errors MUST include: entity type, identifier, specific error, and suggested fix.

**Format & Compatibility**

- **FR-027**: System MUST detect format by presence of `catalog_version` (catalog import) vs `version: "3.3"` (unified import).
- **FR-028**: Catalog import format MUST use `catalog_version: "1.0"` with `ingredients`, `products`, `recipes` arrays.
- **FR-029**: Existing unified import/export functionality MUST remain unchanged (Constitution v1.2.0 compliance).

**Protected vs Augmentable Fields**

- **FR-030**: Ingredient protected fields (never modified): `slug`, `display_name`.
- **FR-031**: Ingredient augmentable fields: `density_volume_value`, `density_volume_unit`, `density_weight_value`, `density_weight_unit`, `foodon_id`, `fdc_ids`, `foodex2_code`, `langual_terms`, `allergens`, `description` (only if null).
- **FR-032**: Product protected fields: `ingredient_slug`, `brand`.
- **FR-033**: Product augmentable fields: `upc_code`, `package_size`, `package_type`, `purchase_unit`, `purchase_quantity` (only if null), `is_preferred` (only if null).

### Key Entities

- **Ingredient**: Reference data for baking ingredients. Unique key: `slug`. Supports both ADD_ONLY and AUGMENT modes.
- **Product**: Links ingredients to purchasable items with brand/package info. Unique key: `(ingredient_slug, brand)`. Supports both modes.
- **Recipe**: User-authored content with ingredients and optional nested recipe components. Unique key: `slug`. ADD_ONLY mode only.
- **CatalogImportResult**: Result object containing counts (added/skipped/failed) per entity and list of error details.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: User can import 160 new ingredients without affecting existing recipes or pantry data.
- **SC-002**: User can augment existing ingredients with density values, with only null fields being updated.
- **SC-003**: User can preview all changes via dry-run before committing any modifications.
- **SC-004**: All validation errors include specific entity, identifier, error description, and actionable fix suggestion.
- **SC-005**: Recipe slug collisions provide enough detail for user to understand the conflict (both existing and import recipe info).
- **SC-006**: Development workflow (export -> DB reset -> import) continues to work exactly as before.
- **SC-007**: Catalog import accessible via both CLI and File menu UI.
- **SC-008**: Non-technical user can complete catalog import via UI without command-line knowledge.
- **SC-009**: Partial import success: valid records are committed even when some records fail validation.
- **SC-010**: Import of 160 ingredients completes in under 30 seconds.

---

## Assumptions

1. Import format v3.3 schema is stable and will not change during this feature's development.
2. The 160-ingredient catalog file (`test_data/baking_ingredients_v33.json`) exists and is valid.
3. Feature 009's File menu structure with Import/Export items exists and can be extended.
4. Existing `import_export_service` patterns provide guidance for result reporting.
5. All ingredient density data uses the 4-field format established in Feature 019.

---

## Out of Scope

- Catalog-specific export (export remains unified only)
- Web scraping, API integration, or barcode scanning import pathways (future features enabled by architecture)
- Data import for transactional entities (purchases, inventory, events) - handled by existing unified import
- Automatic conflict resolution for recipe slug collisions (user must resolve manually)
- `--create-stubs` flag for auto-creating minimal ingredient records (future enhancement)

---

## References

- [Enhanced Data Import Proposal](../../../docs/enhanced_data_import.md)
- [Import/Export Specification v3.3](../../../docs/import_export_specification.md)
- [Project Constitution v1.2.0](../../../.kittify/memory/constitution.md)
- [Feature 019: Unit Conversion Simplification](../../../docs/archive/feature_019_unit_simplification.md)
