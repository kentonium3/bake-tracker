# Feature Specification: Recipe Template & Snapshot System

**Feature Branch**: `037-recipe-template-snapshot`
**Created**: 2026-01-03
**Status**: Draft
**Input**: Design document: `docs/design/_F037_recipe_redesign.md`

## Problem Statement

The current recipe system has four critical issues:

1. **No Recipe Versioning**: Recipe changes retroactively corrupt historical production costs. If a recipe is modified after production, historical reports show incorrect costs.

2. **No Base/Variant Relationships**: Creating recipe variants (e.g., Raspberry vs Strawberry Thumbprint Cookies) requires full duplication with no way to track relationships or aggregate reporting.

3. **No Batch Scaling**: Users cannot efficiently scale production. Making 144 cookies requires either 4 separate production runs OR no way to express "2 batches at double size" for equipment constraints.

4. **No Production Readiness Flag**: Experimental and proven recipes appear together in production planning, requiring users to remember which are safe for events.

## Solution Overview

Implement a **Template/Snapshot Architecture**:

- **Recipe (Template)**: Mutable definition that can be edited over time. Used for planning, browsing, and editing.
- **Recipe Snapshot (Instance)**: Immutable capture of recipe state at production time. Used for historical costing and reporting.

Additionally:
- Self-referential variants via `base_recipe_id`
- Two-parameter scaling: `num_batches` (repetition) + `scale_factor` (size per batch)
- Production readiness flag for filtering

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recipe Snapshot for Historical Accuracy (Priority: P1)

As a baker, I want my historical production costs to remain accurate even after I modify a recipe, so that my expense tracking and cost reports reflect what actually happened.

**Why this priority**: This is the core problem that motivated the redesign. Without snapshots, all historical data is corrupted when recipes change. This is the foundation for all other features.

**Independent Test**: Create a recipe, run production, modify the recipe, verify historical cost unchanged.

**Acceptance Scenarios**:

1. **Given** a recipe with 2 cups flour costing $0.50/cup, **When** I run production and later change the recipe to 3 cups flour, **Then** historical reports still show $1.00 flour cost for the original production.

2. **Given** a production run linked to a snapshot, **When** I view production details, **Then** I see the ingredient quantities and costs from when production occurred, not current recipe values.

3. **Given** multiple production runs of the same recipe over time, **When** I view recipe history, **Then** I can see how the recipe evolved through its snapshots.

4. **Given** a recipe snapshot, **When** I attempt to edit it, **Then** the system prevents modification (immutability enforced).

---

### User Story 2 - Production Run with Automatic Snapshot (Priority: P1)

As a baker, I want the system to automatically capture a snapshot when I start production, so that I don't have to manually track recipe versions.

**Why this priority**: This is the mechanism that enables historical accuracy. Without automatic snapshot creation, users would need to manually version recipes.

**Independent Test**: Start a production run, verify snapshot is created with current recipe data.

**Acceptance Scenarios**:

1. **Given** a recipe template, **When** I start a production run, **Then** a snapshot is automatically created capturing the current recipe state.

2. **Given** a production run, **When** I query its associated snapshot, **Then** I receive the denormalized recipe data (name, ingredients, quantities) as it was at production time.

3. **Given** a snapshot with scale_factor > 1, **When** costs are calculated, **Then** ingredient quantities are multiplied by the scale factor.

---

### User Story 3 - Batch Scaling with Equipment Constraints (Priority: P2)

As a baker, I want to specify both how many batches to make AND the scale of each batch, so that I can optimize production for my equipment constraints (e.g., mixer capacity).

**Why this priority**: Real-world baking has equipment constraints. The ability to express "2 doubled batches" vs "4 normal batches" enables efficient production planning.

**Independent Test**: Create production with 2 batches at 2x scale, verify correct total yield and ingredient consumption.

**Acceptance Scenarios**:

1. **Given** a recipe yielding 36 cookies with 2 cups flour, **When** I produce 2 batches at 2x scale, **Then** expected yield is 144 cookies (36 x 2 x 2) and flour needed is 8 cups (2 x 2 x 2).

2. **Given** a recipe yielding 36 cookies, **When** I produce 4 batches at 1x scale, **Then** expected yield is 144 cookies (36 x 1 x 4) - same output, different batch count.

3. **Given** the production UI, **When** I select batch count and scale factor, **Then** the UI shows per-batch yield, total yield, and ingredient requirements.

4. **Given** a completed production run, **When** I view its details, **Then** I see both num_batches and scale_factor that were used.

---

### User Story 4 - Recipe Variants (Priority: P2)

As a baker, I want to create variants of base recipes (e.g., different jam flavors for thumbprint cookies), so that I can track recipe families and aggregate production reports.

**Why this priority**: Variants reduce duplication and enable family-level reporting. This is valuable but not blocking core functionality.

**Independent Test**: Create a variant from a base recipe, verify the relationship is tracked and both can be produced independently.

**Acceptance Scenarios**:

1. **Given** a base recipe "Thumbprint Cookies", **When** I create a variant "Raspberry Thumbprint", **Then** the variant is linked to the base via base_recipe_id.

2. **Given** a base recipe with variants, **When** I view the recipe list, **Then** variants are displayed grouped under their base recipe.

3. **Given** a variant recipe, **When** the base recipe is deleted, **Then** the variant becomes a standalone recipe (orphaned but functional).

4. **Given** a base recipe, **When** I query its variants, **Then** I receive a list of all recipes with matching base_recipe_id.

---

### User Story 5 - Production Readiness Filter (Priority: P3)

As a baker, I want to mark recipes as "production ready" vs "experimental", so that I can filter out test recipes when planning events.

**Why this priority**: Quality-of-life improvement. Important for usability but not blocking core production functionality.

**Independent Test**: Mark a recipe as production ready, filter recipe list, verify only ready recipes appear.

**Acceptance Scenarios**:

1. **Given** a recipe, **When** I toggle its production readiness flag, **Then** the change is persisted.

2. **Given** recipes with mixed readiness states, **When** I filter by "Production Ready", **Then** only ready recipes appear.

3. **Given** the production planning UI, **When** I select a recipe, **Then** experimental recipes are either hidden or clearly marked.

4. **Given** a new recipe, **When** it is created, **Then** it defaults to experimental (not production ready).

---

### User Story 6 - Recipe Version History (Priority: P3)

As a baker, I want to view the history of a recipe through its production snapshots, so that I can see how it evolved and optionally restore a previous version.

**Why this priority**: Useful for recipe development but not required for core production tracking.

**Independent Test**: View recipe history, see list of snapshots with dates and key differences.

**Acceptance Scenarios**:

1. **Given** a recipe with multiple production snapshots, **When** I view its history, **Then** I see a chronological list of snapshots with dates.

2. **Given** a snapshot in history, **When** I click "View Details", **Then** I see the full ingredient list as captured at that time.

3. **Given** a snapshot in history, **When** I click "Restore as New Recipe", **Then** a new recipe template is created with the snapshot's data.

---

### Edge Cases

- **Snapshot with no ingredients**: System allows creating snapshot but flags warning (recipe may be incomplete)
- **Delete recipe with snapshots**: Recipe deletion blocked if snapshots exist (ON DELETE RESTRICT); orphaned snapshots preserve historical data
- **Scale factor edge cases**: Must be > 0; values like 0.5x (half batch) are valid
- **Circular variant references**: Prevented - a recipe cannot be its own base (enforced by CHECK constraint)
- **Variant of variant**: Schema allows but UI should discourage (single-level variants recommended for Phase 2)
- **RecipeComponent (nested recipes)**: Snapshots capture direct ingredients only; nested recipe snapshots deferred to Phase 3

---

## Requirements *(mandatory)*

### Functional Requirements

**Snapshot System**:
- **FR-001**: System MUST create an immutable snapshot when a production run is started
- **FR-002**: Snapshots MUST capture denormalized recipe data (name, category, yield, notes) and ingredient data (name, quantity, unit) as JSON
- **FR-003**: Snapshots MUST NOT be editable after creation
- **FR-004**: System MUST calculate production costs using snapshot data, not current recipe data
- **FR-005**: System MUST store scale_factor with each snapshot (default 1.0)

**Production Runs**:
- **FR-006**: Production runs MUST link to snapshots (recipe_snapshot_id), not directly to recipes
- **FR-007**: System MUST support num_batches (repetition count) and scale_factor (size multiplier) as separate parameters
- **FR-008**: Expected yield calculation MUST be: base_yield x scale_factor x num_batches
- **FR-009**: Ingredient consumption MUST be: base_quantity x scale_factor x num_batches

**Variant Management**:
- **FR-010**: System MUST support base_recipe_id (nullable, self-referential FK) for variant relationships
- **FR-011**: System MUST support variant_name field to distinguish variants
- **FR-012**: When base recipe is deleted, variants MUST become standalone (ON DELETE SET NULL)
- **FR-013**: System MUST prevent self-referential variants (base_recipe_id != id)

**Production Readiness**:
- **FR-014**: System MUST support is_production_ready boolean flag (default false)
- **FR-015**: Recipe list MUST be filterable by production readiness state
- **FR-016**: New recipes MUST default to experimental (not production ready)

**Recipe History**:
- **FR-017**: System MUST provide access to snapshot history for any recipe
- **FR-018**: System MUST allow creating a new recipe from historical snapshot data

**Ingredient Validation**:
- **FR-019**: Recipes MUST only allow leaf-level ingredients (hierarchy_level = 2)
- **FR-020**: System MUST validate ingredient hierarchy level when adding to recipe

### Key Entities

- **Recipe**: Mutable template with name, category, yield, ingredients, base_recipe_id (variant relationship), variant_name, is_production_ready flag. Can be edited over time.

- **RecipeSnapshot**: Immutable capture of recipe state at production time. Contains recipe_id (source), production_run_id (1:1), scale_factor, snapshot_date, recipe_data (JSON), ingredients_data (JSON).

- **RecipeIngredient**: Junction table linking recipes to ingredients. ingredient_id must reference hierarchy_level=2 (leaf) ingredients only.

- **ProductionRun**: Links to recipe_snapshot_id (not recipe_id). Contains num_batches, scale_factor (via snapshot), event_id, actual_yield, total_ingredient_cost.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Historical production costs remain unchanged when recipes are modified (100% accuracy verified by comparing pre/post modification reports)

- **SC-002**: Users can create a production run with batch configuration in under 30 seconds (recipe selection + batch/scale entry + confirmation)

- **SC-003**: Recipe variants are correctly grouped in the UI, with base recipes showing their variant count

- **SC-004**: Production readiness filtering reduces visible recipes to only those marked ready (no false positives/negatives)

- **SC-005**: Recipe history view loads within 2 seconds for recipes with up to 100 snapshots

- **SC-006**: All snapshot creation, cost calculation, and variant operations complete without error for existing production data after migration

- **SC-007**: 100% of recipe service tests pass, including new snapshot and variant functionality

---

## Assumptions

- Ingredient Hierarchy (F031-F036) is complete - recipes can use hierarchical ingredient selection
- Existing production runs have recipe_id which will be migrated to recipe_snapshot_id
- For historical production runs, snapshots will be backfilled using current recipe data (best approximation)
- RecipeComponent (nested recipes) support in snapshots is explicitly deferred to Phase 3
- User has validated the template/snapshot mental model (Marianne validation complete)

---

## Out of Scope

- Nested recipe (RecipeComponent) snapshot capture - snapshots capture direct ingredients only
- Non-linear scaling (e.g., adjustments that don't scale proportionally)
- Multi-level variants (variants of variants) - schema supports but UI discourages
- Recipe version comparison (diff view) - deferred to future enhancement
- Recipe sharing between users - single-user desktop app phase

---

## Dependencies

- **Requires**: F031-F036 Ingredient Hierarchy (complete) - for leaf-only ingredient validation
- **Blocks**: F039 Planning Workspace - requires recipe scaling and variant support
