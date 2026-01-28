# Feature Specification: Recipe Slug Support

**Feature Branch**: `080-recipe-slug-support`
**Created**: 2026-01-28
**Status**: Draft
**Input**: User description: "F080 Recipe Slug Support - Add unique slug field to Recipe model and update all FK resolution to use slugs for data portability."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Export and Import Recipes Across Environments (Priority: P1)

As a user managing data across development and production databases, I need recipes to have portable identifiers (slugs) so that when I export my complete data and import it into a fresh database, all recipe references remain intact.

**Why this priority**: This is the core problem being solved. Recipes are central to the application - they are referenced by FinishedUnit, ProductionRun, EventProductionTarget, and RecipeComponent. Without portable recipe identification, cross-environment data migration fails.

**Independent Test**: Can be fully tested by exporting data with recipes, importing into empty database, and verifying all recipe records are recreated with correct associations.

**Acceptance Scenarios**:

1. **Given** a database with existing recipes, **When** I export all data, **Then** each recipe in the export includes a unique slug field
2. **Given** an export file with recipes containing slugs, **When** I import into a fresh database, **Then** all recipes are created with their original slugs preserved
3. **Given** a recipe named "Chocolate Chip Cookies", **When** the system generates its slug, **Then** the slug is "chocolate-chip-cookies" (lowercase, hyphens)
4. **Given** two recipes with the same name, **When** slugs are generated, **Then** the second receives a numeric suffix (e.g., "chocolate-chip-cookies-2")

---

### User Story 2 - Recipe FK References Preserved on Import (Priority: P1)

As a user importing finished goods, production runs, and event targets, I need these records that reference recipes to correctly resolve those references by slug, so that my production data survives the import process.

**Why this priority**: FinishedUnit, ProductionRun, EventProductionTarget, and RecipeComponent all reference recipes. If these references break on import, production tracking and event planning data is lost.

**Independent Test**: Can be tested by exporting finished_units.json and production_runs.json with recipe associations, importing into fresh database (with recipes imported first), and verifying all records point to correct recipes.

**Acceptance Scenarios**:

1. **Given** a FinishedUnit with recipe_slug "chocolate-chip-cookies" in import file, **When** I import the finished unit, **Then** its recipe_id is set to the matching recipe's ID
2. **Given** a ProductionRun referencing a recipe slug that doesn't exist, **When** I import the production run, **Then** an error is logged and the record is skipped
3. **Given** an EventProductionTarget with recipe_slug in import file, **When** I import, **Then** the target correctly references the recipe
4. **Given** a RecipeComponent with component_recipe_slug, **When** I import, **Then** nested recipe references are correctly resolved
5. **Given** a legacy export file with recipe_name but no recipe_slug, **When** I import, **Then** the system falls back to name-based matching (backward compatibility)

---

### User Story 3 - Migrate Existing Recipes with Generated Slugs (Priority: P1)

As a system administrator, I need all existing recipes in my database to receive auto-generated slugs during the reset/re-import cycle, so that they can participate in slug-based import/export immediately.

**Why this priority**: Existing data must receive slugs before any slug-based operations can work. This is a prerequisite for all other functionality.

**Independent Test**: Can be tested by exporting existing recipes, re-importing, and verifying all have unique, correctly-formatted slugs.

**Acceptance Scenarios**:

1. **Given** an export from database with recipes without slugs, **When** I import into fresh database, **Then** all recipes have unique slugs generated from their names
2. **Given** two recipes with identical names in import file, **When** import generates slugs, **Then** each has a unique slug (numeric suffix differentiates them)
3. **Given** a potential slug conflict during import, **When** collision is detected, **Then** the conflicting recipe gets a numeric suffix (e.g., "-2", "-3")

---

### User Story 4 - Recipe Rename Preserves Import Compatibility (Priority: P2)

As a user who renames recipes, I need the system to maintain a reference to the previous slug so that exports made before the rename can still be imported successfully.

**Why this priority**: This provides a one-rename grace period for data portability. Users who rename a recipe and then try to import an older export will have their data resolve correctly.

**Independent Test**: Can be tested by creating a recipe, exporting, renaming the recipe, then importing the original export and verifying the recipe resolves via previous_slug.

**Acceptance Scenarios**:

1. **Given** a recipe with slug "old-name", **When** the recipe is renamed to "New Name", **Then** slug becomes "new-name" and previous_slug stores "old-name"
2. **Given** an import file with recipe_slug "old-name", **When** the database has a recipe with previous_slug "old-name", **Then** the import resolves to that recipe
3. **Given** a recipe that has been renamed twice, **When** the second rename occurs, **Then** only the most recent previous slug is preserved (one-rename grace period)
4. **Given** import resolution, **When** searching for recipe, **Then** resolution order is: slug -> previous_slug -> name

---

### User Story 5 - Slug Auto-Generation on Recipe Creation (Priority: P1)

As a user creating new recipes, I need the system to automatically generate a unique slug from the recipe name, so that I don't have to manage slugs manually.

**Why this priority**: Manual slug management would be error-prone and burden users. Auto-generation ensures all recipes have valid, portable identifiers.

**Independent Test**: Can be tested by creating recipes through the service layer and verifying slugs are generated correctly.

**Acceptance Scenarios**:

1. **Given** I create a recipe named "Grandma's Apple Pie", **When** the recipe is saved, **Then** it automatically receives slug "grandmas-apple-pie"
2. **Given** a recipe named "Test Recipe" already exists with slug "test-recipe", **When** I create another recipe named "Test Recipe", **Then** the new recipe receives slug "test-recipe-2"
3. **Given** a recipe name with special characters "Crème Brûlée!", **When** slug is generated, **Then** the result is "creme-brulee" (normalized)

---

### Edge Cases

- What happens when a recipe slug is empty or null at creation time? (Validation rejects it - auto-generation ensures this never happens)
- What happens when slug contains invalid characters? (Normalization removes them during generation)
- How does system handle identical recipe names? (Numeric suffix conflict resolution: -2, -3, etc.)
- What happens when importing a recipe that already exists by slug? (Update the existing recipe)
- How does nested recipe import handle missing component references? (Error logged, import fails for that component)
- What happens when both slug and previous_slug match different recipes? (Prefer exact slug match)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST add a `slug` field to Recipe model (String, max 200 chars, unique, indexed, non-nullable)
- **FR-002**: System MUST add a `previous_slug` field to Recipe model (String, max 200 chars, nullable, indexed) to support one-rename grace period
- **FR-003**: System MUST auto-generate slug on recipe creation using pattern: lowercase, hyphens for spaces, alphanumeric-and-hyphens only
- **FR-004**: System MUST resolve slug conflicts by appending numeric suffixes (`-2`, `-3`, etc.) matching existing Supplier/Product/Ingredient patterns
- **FR-005**: System MUST regenerate slug when recipe name changes, preserving old slug in previous_slug field
- **FR-006**: System MUST validate slug uniqueness before saving
- **FR-007**: System MUST export recipes in JSON format including both slug and previous_slug fields
- **FR-008**: System MUST import recipes with resolution order: slug -> previous_slug -> name (with logging on fallback)
- **FR-009**: System MUST add `recipe_slug` to FinishedUnit export (alongside existing recipe_name)
- **FR-010**: System MUST add `recipe_slug` to ProductionRun export (alongside existing recipe_name)
- **FR-011**: System MUST add `recipe_slug` to EventProductionTarget export (alongside existing recipe_name)
- **FR-012**: System MUST add `component_recipe_slug` to RecipeComponent export (alongside existing component_recipe_name)
- **FR-013**: System MUST resolve `recipe_slug` to `recipe_id` during FinishedUnit import with name fallback
- **FR-014**: System MUST resolve `recipe_slug` to `recipe_id` during ProductionRun import with name fallback
- **FR-015**: System MUST resolve `recipe_slug` to `recipe_id` during EventProductionTarget import with name fallback
- **FR-016**: System MUST resolve `component_recipe_slug` to `component_recipe_id` during RecipeComponent import with name fallback
- **FR-017**: System MUST log when fallback to previous_slug or name occurs during import (migration tracking)
- **FR-018**: System MUST fail import with clear error message when neither slug, previous_slug, nor name resolves

### Key Entities *(include if feature involves data)*

- **Recipe**: Existing entity enhanced with `slug` field (String, unique, indexed, non-nullable) and `previous_slug` field (String, nullable, indexed). Represents a recipe for producing baked goods.
- **FinishedUnit**: Existing entity with `recipe_id` FK. Export enhanced to include `recipe_slug`. Import enhanced to resolve recipe references by slug.
- **ProductionRun**: Existing entity with `recipe_id` FK. Export enhanced to include `recipe_slug`. Import enhanced to resolve recipe references by slug.
- **EventProductionTarget**: Existing entity with `recipe_id` FK. Export enhanced to include `recipe_slug`. Import enhanced to resolve recipe references by slug.
- **RecipeComponent**: Existing entity with `component_recipe_id` FK for nested recipes. Export enhanced to include `component_recipe_slug`. Import enhanced to resolve recipe references by slug.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All recipes have unique slugs after data re-import with zero null values
- **SC-002**: Recipe export creates complete recipes.json with slug and previous_slug fields
- **SC-003**: Round-trip test succeeds: export all data -> fresh database -> import -> all recipe associations verified intact
- **SC-004**: Legacy import files (without recipe slugs) continue to import successfully with fallback to name resolution
- **SC-005**: Recipe FK associations (FinishedUnit, ProductionRun, EventProductionTarget, RecipeComponent) are correctly resolved by slug on import with 100% accuracy for valid references
- **SC-006**: Slug generation follows existing Supplier/Product/Ingredient patterns exactly (code consistency)
- **SC-007**: Recipe rename correctly updates slug and preserves previous_slug for backward compatibility
- **SC-008**: Import with previous_slug fallback resolves correctly when current slug doesn't match
