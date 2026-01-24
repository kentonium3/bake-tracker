# Recipes - Requirements Document

**Component:** Recipes (Recipe Definition Management)  
**Version:** 0.3 (BASELINE + VARIANT YIELD INHERITANCE)  
**Last Updated:** 2025-01-24  
**Status:** Active - Baseline for Refactoring  
**Owner:** Kent Gale

---

## 1. Purpose & Function

### 1.1 Overview

Recipes are a **definition entity** within the bake-tracker application that define how to transform ingredients into finished goods. Recipes are catalog data, not transactional data. Production instances (ProductionRun) use recipes as templates but are separate entities.

### 1.2 Business Purpose

The Recipe definition system serves multiple business functions:

1. **Production Templates:** Defines ingredient lists and quantities needed to produce finished goods
2. **Recipe Management:** Provides CRUD operations for recipe catalog with validation
3. **Hierarchical Recipes:** Supports sub-recipes (nested recipes) with cycle detection and depth limits
4. **Recipe Variants:** Enables recipe variations (e.g., "Raspberry Thumbprint" variant of "Thumbprint Cookies")
5. **Production Integration:** Links to FinishedUnit for yield specifications and ProductionRun for production tracking

### 1.3 Design Rationale

**Definition vs Instance Separation:** Recipes are definitions (templates). Production instances (ProductionRun, AssemblyRun) reference recipes but track actual production separately. This separation enables:
- Recipe modifications without affecting historical production data
- Recipe deletion protection based only on definition dependencies (ingredients, finished units)
- Cost tracking on production instances, not definitions

**Catalog Data Classification:** Recipes are catalog data (like ingredients and products), not transactional data. This allows safe catalog expansion and AI-assisted recipe generation without risking user production history.

**Yield via FinishedUnit:** Recipe yield information is defined in associated FinishedUnit records, not on Recipe itself. This supports multiple yield types per recipe (e.g., "Large Cookie" and "Small Cookie" from same recipe).

---

## 2. Recipe Structure

### 2.1 Core Components

**Recipe Entity (Definition):**
- Recipe metadata (name, category, source, notes)
- Estimated prep/bake time
- Production readiness flag (experimental vs production-ready)
- Archival status (soft-delete flag)
- Variant support (base_recipe_id, variant_name)

**Recipe Ingredients (RecipeIngredient):**
- Link to leaf ingredient (hierarchy level 2 only)
- Quantity and unit specification (measurement units: weight, volume, count)
- Optional notes (e.g., "sifted", "melted")

**Recipe Components (RecipeComponent - Sub-recipes):**
- Hierarchical recipe structure (recipes containing other recipes)
- Quantity (batch multiplier for component recipe)
- Maximum nesting depth: 3 levels
- Cycle detection prevents circular references
- Optional notes and sort order

**Finished Units (Yield Specifications):**
- One or more FinishedUnit records define yields for a recipe
- Each FinishedUnit specifies: display_name, item_unit, items_per_batch
- Supports multiple yield types per recipe (e.g., "Large Cookie", "Small Cookie")
- **Variant recipes:** Each variant defines its own FinishedUnits but must match base recipe yield structure (same items_per_batch and item_unit, distinct display_name)

**Recipe Snapshots:**
- Historical record of recipe state at time of production
- Preserves ingredient lists and quantities for production instances
- Enables recipe modification without affecting historical production data

### 2.2 Key Relationships

```
Recipe (Definition)
  ├─ recipe_ingredients (many) → RecipeIngredient
  │    └─ ingredient_id → Ingredient (L2 leaf only)
  ├─ recipe_components (many) → RecipeComponent
  │    └─ component_recipe_id → Recipe (sub-recipe)
  ├─ finished_units (many) → FinishedUnit (yield specifications)
  ├─ snapshots (many) → RecipeSnapshot (historical states)
  ├─ production_runs (many) → ProductionRun (instances)
  └─ base_recipe / variants → Recipe (self-referential for variants)
```

---

## 3. Scope & Boundaries

### 3.1 In Scope

**Recipe Management:**
- ✅ Create recipes with name, category, source, prep time, notes
- ✅ Edit recipe metadata and ingredients
- ✅ Soft-delete recipes with archival flag (is_archived)
- ✅ Link recipes to leaf ingredients only (hierarchy level 2)
- ✅ Recipe import/export for AI-assisted catalog expansion
- ✅ Production readiness flag (experimental vs production-ready)
- ✅ Recipe variants (base_recipe_id, variant_name relationships)

**Ingredient Integration:**
- ✅ Leaf ingredient validation (hierarchy level 2 only)
- ✅ Hierarchical ingredient tree browsing in UI
- ✅ Quantity and unit specification (weight, volume, count units from DB)
- ✅ Validation preventing use of non-leaf ingredients

**Sub-Recipes (Nested Recipes):**
- ✅ Add recipes as components of other recipes
- ✅ Batch multiplier (quantity) for component recipes
- ✅ Circular reference detection and prevention
- ✅ Maximum nesting depth enforcement (3 levels)
- ✅ Ingredient aggregation across recipe hierarchy

**Yield Specifications:**
- ✅ Multiple yield types per recipe via FinishedUnit records
- ✅ Yield validation (at least one FinishedUnit required)
- ✅ Items per batch tracking for discrete count items

**Production Integration:**
- ✅ Recipe snapshots for production instance tracking
- ✅ Link to ProductionRun for actual production tracking
- ✅ Recipe modifications don't affect historical production data

### 3.2 Out of Scope (Managed by Other Services)

**Cost Calculations (ARCHITECTURAL DEBT):**
- ❌ Recipe cost calculations should NOT be in recipe_service
- ❌ Cost calculations belong in planning/production/purchasing/reporting services
- ❌ Costs should be calculated on production instances, not definitions
- ⚠️ **REFACTORING NEEDED:** Current implementation has cost methods in Recipe model and recipe_service that should be removed

**Production Tracking:**
- ❌ Inventory depletion (production_service responsibility)
- ❌ Batch multiplier UI (production planning responsibility)
- ❌ Loss tracking and remake workflows (production_service responsibility)

**Event Management:**
- ❌ Event linkage and fulfillment (event_service responsibility)

### 3.3 Legacy Functionality (To Be Removed)

**Deletion Protection Based on Instances:**
- ⚠️ **LEGACY:** Current implementation prevents recipe deletion if ProductionRun instances exist
- ⚠️ **CORRECT BEHAVIOR:** Recipe deletion protection should only extend to definition dependencies (ingredients, finished units)
- ⚠️ **REFACTORING NEEDED:** Remove soft-delete/archival based on production history

---

## 4. User Stories & Use Cases

### 4.1 Primary User Stories

**As a baker, I want to:**
1. Create recipe templates with ingredient lists for reuse across multiple events
2. Organize recipes by category and mark them as production-ready or experimental
3. See which ingredients I need and in what quantities for a recipe
4. Create recipe variants (e.g., Raspberry Thumbprint, Strawberry Thumbprint from base Thumbprint recipe)
5. Build complex recipes from simpler component recipes (e.g., Frosted Layer Cake = Cake + Frosting)

**As a recipe manager, I want to:**
1. Import recipe templates from external sources (AI-assisted)
2. Edit recipe metadata without affecting historical production
3. Browse ingredients hierarchically when adding to recipes
4. Specify multiple yield types for a single recipe (e.g., large and small cookies)
5. Archive recipes that are no longer used

**As a production planner, I want to:**
1. Use recipes as templates for production runs
2. Know that recipe modifications won't affect historical production data
3. Access recipe snapshots that preserve the recipe state at time of production

### 4.2 Use Case: Create Recipe with Nested Sub-Recipes

**Actor:** Baker  
**Preconditions:** Base recipes exist (e.g., "Chocolate Cake", "Vanilla Frosting")  
**Main Flow:**
1. User opens Recipes tab, clicks "Add Recipe"
2. Enters recipe name: "Frosted Chocolate Layer Cake"
3. Enters category: "Cakes"
4. Marks as "Production Ready"
5. Adds sub-recipes:
   - Chocolate Cake (2.0 batches)
   - Vanilla Frosting (1.0 batch)
6. Adds direct ingredients:
   - Chocolate shavings: 2 oz
7. Defines yield types:
   - "9-inch Round Cake": 1 per batch
8. System validates:
   - No circular references
   - Nesting depth ≤ 3 levels
   - At least one yield type exists
9. User saves

**Postconditions:**
- Recipe created with sub-recipes and direct ingredients
- Available for production planning
- Ingredient aggregation includes nested recipe ingredients

### 4.3 Use Case: Create Recipe Variant

**Actor:** Baker  
**Preconditions:** Base recipe "Thumbprint Cookies" exists with FinishedUnit "Plain Thumbprint Cookie" (32 per batch)  
**Main Flow:**
1. User views base recipe details
2. Clicks "Create Variant"
3. Enters variant name: "Raspberry"
4. System auto-generates name: "Thumbprint Cookies - Raspberry"
5. System copies ingredients from base recipe
6. User modifies ingredients:
   - Changes "Any Jam" to "Raspberry Jam"
7. System prompts for yield specification:
   - Detects base recipe has FinishedUnit: "Plain Thumbprint Cookie", 32 per batch, unit "cookie"
   - Pre-fills variant FinishedUnit form: items_per_batch = 32, item_unit = "cookie"
   - User enters display_name: "Raspberry Thumbprint Cookie"
8. System validates yield consistency with base recipe (items_per_batch and item_unit match)
9. Marks as "Experimental" initially
10. User saves

**Postconditions:**
- Variant recipe created with base_recipe_id link
- Variant inherits category from base
- Variant has own FinishedUnit with same yield structure as base (32 cookies per batch)
- Variant FinishedUnit has distinct display_name ("Raspberry Thumbprint Cookie")
- Variant marked as experimental (is_production_ready = False)

---

## 5. Functional Requirements

### 5.1 Recipe Management

**REQ-RCP-001:** System shall support recipe creation with name, category, source, estimated_time_minutes, notes, and is_production_ready flag  
**REQ-RCP-002:** System shall allow ingredient addition with quantities and units (measurement units only: weight, volume, count)  
**REQ-RCP-003:** System shall restrict recipe ingredients to leaf ingredients only (hierarchy level 2)  
**REQ-RCP-004:** System shall validate unique recipe names  
**REQ-RCP-005:** System shall support recipe editing (metadata and ingredients)  
**REQ-RCP-006:** System shall support recipe archival via is_archived flag (soft delete)  
**REQ-RCP-007:** System shall support hard deletion of recipes with validation (no definition dependencies)

### 5.2 Ingredient Selection

**REQ-RCP-008:** Recipe creation shall use hierarchical ingredient tree widget for browsing  
**REQ-RCP-009:** System shall prevent selection of non-leaf ingredients in recipes  
**REQ-RCP-010:** System shall allow multiple ingredients per recipe  
**REQ-RCP-011:** System shall validate ingredient quantities are positive numbers  
**REQ-RCP-012:** System shall load measurement units from database (weight, volume, count categories)

### 5.3 Yield Management via FinishedUnit

**REQ-RCP-013:** System shall require at least one FinishedUnit record per recipe for yield specification  
**REQ-RCP-014:** Each FinishedUnit shall specify display_name, item_unit, and items_per_batch  
**REQ-RCP-015:** System shall validate FinishedUnit completeness before allowing recipe use in production  
**REQ-RCP-016:** System shall support multiple FinishedUnit records per recipe (multiple yield types)  
**REQ-RCP-017:** Yield information shall NOT be stored on Recipe model (F056 removal complete)

### 5.4 Sub-Recipes (Nested Recipes / Recipe Components)

**REQ-RCP-018:** System shall support adding recipes as components of other recipes  
**REQ-RCP-019:** Each component shall have a quantity (batch multiplier) ≥ 1.0  
**REQ-RCP-020:** System shall prevent circular references (cycle detection)  
**REQ-RCP-021:** System shall enforce maximum nesting depth of 3 levels  
**REQ-RCP-022:** System shall aggregate ingredients across all nested recipe levels  
**REQ-RCP-023:** System shall allow component removal with validation (no production instances)  
**REQ-RCP-024:** System shall support component quantity updates

### 5.5 Recipe Variants

**REQ-RCP-025:** System shall support recipe variants via base_recipe_id and variant_name fields  
**REQ-RCP-026:** Variant creation shall optionally copy ingredients from base recipe  
**REQ-RCP-027:** Variant names shall default to "{base_name} - {variant_name}" format  
**REQ-RCP-028:** Variants shall inherit category from base recipe  
**REQ-RCP-029:** Variants shall default to is_production_ready = False (experimental)  
**REQ-RCP-030:** System shall prevent self-referential variants (base_recipe_id != id)

### 5.6 Variant Yield Inheritance

**REQ-RCP-031:** Variant recipes SHALL define their own FinishedUnit records (not share base recipe FinishedUnits)  
**REQ-RCP-032:** Variant FinishedUnits SHALL reference yield structure from base recipe  
**REQ-RCP-033:** The number and type of yield outputs SHALL match between base recipe and variants  
**REQ-RCP-034:** Variant FinishedUnit items_per_batch SHALL equal base recipe FinishedUnit items_per_batch  
**REQ-RCP-035:** Variant FinishedUnit item_unit SHALL match base recipe FinishedUnit item_unit  
**REQ-RCP-036:** System SHALL validate variant yield consistency with base recipe at variant creation time  
**REQ-RCP-037:** System SHALL provide primitive `get_base_yield_structure(recipe_id)` that returns yield specifications from base recipe for variants  
**REQ-RCP-038:** If base recipe FinishedUnit changes (items_per_batch, item_unit), system SHALL flag variants as requiring yield review  
**REQ-RCP-039:** Variant FinishedUnit display_name SHALL be distinct from base (e.g., "Raspberry Sugar Cookie" vs "Plain Sugar Cookie")  
**REQ-RCP-040:** Variant recipe MAY have different FinishedUnit slug from base recipe FinishedUnit

### 5.6a Yield Primitives for Services

**REQ-RCP-041:** System SHALL provide primitive `get_finished_units(recipe_id)` that returns all FinishedUnit records for a recipe (base or variant)  
**REQ-RCP-042:** Services performing batch calculations SHALL use recipe's own FinishedUnits, not base recipe FinishedUnits, when recipe is a variant  
**REQ-RCP-043:** The `get_finished_units(recipe_id)` primitive SHALL return the same structure for base recipes and variant recipes (no special case handling required by callers)  
**REQ-RCP-044:** Planning, Production, and Cost services SHALL use `get_finished_units(recipe_id)` to retrieve yield data for calculations

### 5.7 Production Integration

**REQ-RCP-045:** System shall create RecipeSnapshot when recipe is used in production  
**REQ-RCP-046:** RecipeSnapshot shall preserve ingredient list and quantities  
**REQ-RCP-047:** Recipe modifications shall NOT affect existing RecipeSnapshot instances  
**REQ-RCP-048:** System shall link recipes to ProductionRun instances

### 5.8 Recipe Deletion Protection

**REQ-RCP-049:** System shall prevent deletion if recipe is used as component in other recipes  
**REQ-RCP-050:** System shall prevent deletion if recipe has active FinishedUnit records  
**REQ-RCP-051:** System shall allow deletion even if ProductionRun instances exist (definitions independent of instances)  
**REQ-RCP-052:** Deletion validation shall check only definition dependencies, not production history

### 5.9 Import/Export

**REQ-RCP-053:** System shall export recipes in JSON format (normalized and denormalized)  
**REQ-RCP-054:** System shall import recipes with automatic ingredient resolution  
**REQ-RCP-055:** System shall handle missing ingredients during import with user prompt  
**REQ-RCP-056:** System shall validate recipe integrity after import (all ingredients exist)  
**REQ-RCP-057:** Export shall include recipe_components (sub-recipes) and finished_units

---

## 6. Non-Functional Requirements

### 6.1 Usability

**REQ-RCP-NFR-001:** Recipe creation shall require max 5 clicks for single-ingredient recipe  
**REQ-RCP-NFR-002:** Ingredient selection shall use hierarchical tree widget with search  
**REQ-RCP-NFR-003:** Ingredient quantity entry shall support measurement units from database  
**REQ-RCP-NFR-004:** Error messages shall clearly explain validation failures  
**REQ-RCP-NFR-005:** Recipe form shall support sub-recipe addition via dropdown with validation feedback

### 6.2 Data Integrity

**REQ-RCP-NFR-006:** No orphaned recipe ingredients (all must link to valid leaf ingredient)  
**REQ-RCP-NFR-007:** Recipe deletion shall prevent orphaning of FinishedUnit records  
**REQ-RCP-NFR-008:** Ingredient hierarchy changes shall not break existing recipes  
**REQ-RCP-NFR-009:** Recipe components shall enforce acyclic graph (no circular references)  
**REQ-RCP-NFR-010:** Recipe variants shall prevent self-referential relationships

### 6.3 Performance

**REQ-RCP-NFR-011:** Recipe list loading shall complete in <100ms for 100+ recipes  
**REQ-RCP-NFR-012:** Ingredient aggregation across nested recipes shall complete in <500ms for 3-level deep recipes  
**REQ-RCP-NFR-013:** Hierarchical tree widget shall load incrementally (lazy loading for large hierarchies)

### 6.4 Architectural Compliance

**REQ-RCP-NFR-014:** Recipe service shall NOT perform cost calculations (architectural debt exists)  
**REQ-RCP-NFR-015:** Recipe model shall NOT store cost data (costs belong on production instances)  
**REQ-RCP-NFR-016:** Recipe deletion logic shall check only definition dependencies, not production instances  
**REQ-RCP-NFR-017:** Session management shall use shared session for multi-step operations (prevent detached instances)

---

## 7. Data Model Summary

### 7.1 Recipe Table Structure

```
Recipe
├─ id (PK)
├─ uuid (unique)
├─ name (unique, indexed)
├─ category (indexed)
├─ source (optional)
├─ estimated_time_minutes (optional)
├─ notes (text, optional)
├─ is_archived (boolean, default False, indexed)
├─ is_production_ready (boolean, default False, indexed)
├─ base_recipe_id (FK → Recipe, self-referential, optional)
├─ variant_name (optional)
├─ date_added (datetime)
└─ last_modified (datetime)
```

**Constraints:**
- name must be unique
- base_recipe_id must not equal id (no self-referential variants)
- is_archived defaults to False

**Indexes:**
- idx_recipe_name (name)
- idx_recipe_category (category)
- idx_recipe_archived (is_archived)
- idx_recipe_production_ready (is_production_ready)
- idx_recipe_base_recipe (base_recipe_id)

### 7.2 Recipe Ingredient Structure

```
RecipeIngredient
├─ id (PK)
├─ recipe_id (FK → Recipe, cascade delete)
├─ ingredient_id (FK → Ingredient, restrict delete)
├─ quantity (float, > 0)
├─ unit (string, measurement units only)
└─ notes (optional)
```

**Constraints:**
- quantity must be > 0
- ingredient_id must reference leaf ingredient (hierarchy_level = 2)
- unit must be from valid measurement units (weight, volume, count)

**Indexes:**
- idx_recipe_ingredient_recipe (recipe_id)
- idx_recipe_ingredient_ingredient (ingredient_id)

### 7.3 Recipe Component Structure (Sub-Recipes)

```
RecipeComponent
├─ id (PK)
├─ recipe_id (FK → Recipe, cascade delete)
├─ component_recipe_id (FK → Recipe, restrict delete)
├─ quantity (float, default 1.0, > 0)
├─ notes (optional)
└─ sort_order (int, default 0)
```

**Constraints:**
- quantity must be > 0
- recipe_id must not equal component_recipe_id (no self-reference)
- (recipe_id, component_recipe_id) must be unique
- Maximum nesting depth: 3 levels (enforced by service)
- Circular references prevented (enforced by service)

**Indexes:**
- idx_recipe_component_recipe (recipe_id)
- idx_recipe_component_component (component_recipe_id)
- idx_recipe_component_sort (recipe_id, sort_order)

### 7.4 Recipe Snapshot Structure

```
RecipeSnapshot
├─ id (PK)
├─ recipe_id (FK → Recipe)
├─ snapshot_data (JSON, contains ingredients, components, metadata)
├─ production_run_id (FK → ProductionRun, optional)
└─ created_at (datetime)
```

**Purpose:** Preserves recipe state at time of production for historical accuracy

### 7.5 Finished Unit Structure (Yield Specifications)

```
FinishedUnit
├─ id (PK)
├─ slug (unique, indexed)
├─ display_name (string, required)
├─ recipe_id (FK → Recipe, cascade delete)
├─ yield_mode (enum: DISCRETE_COUNT, BATCH_PORTION)
├─ items_per_batch (int, > 0 for DISCRETE_COUNT)
├─ item_unit (string, required for DISCRETE_COUNT)
├─ batch_percentage (decimal, 0-100 for BATCH_PORTION)
└─ portion_description (string, optional for BATCH_PORTION)
```

**Relationship:** Recipe.finished_units → FinishedUnit (one-to-many)  
**Validation:** Recipe must have at least one complete FinishedUnit for production use

---

## 8. UI Requirements

### 8.1 Recipes Tab

**Display:**
- List view with columns: Name | Category | Readiness | Ingredients Count | Actions
- Filter: Search by name, category dropdown, readiness dropdown (All/Production Ready/Experimental)
- Sort: Alphabetical by name
- Visual indicators: Production-ready badge, archived status

**Actions:**
- Add Recipe
- Edit Recipe
- Delete Recipe (with validation)
- View Details (shows ingredients, yield types, cost breakdown, sub-recipes)

### 8.2 Recipe Edit Form

**Layout Sections:**

1. **Basic Information:**
   - Recipe Name* (required, max 200 chars)
   - Category* (dropdown, populated from DB)
   - Production Ready checkbox (default: checked)
   - Source (optional, text)
   - Prep Time (optional, integer minutes)
   - Notes (optional, multiline text)

2. **Yield Information (FinishedUnits):**
   - At least one yield type required*
   - Each row: Description | Unit | Qty/batch
   - Add/Remove yield type buttons
   - Cannot remove last yield type (validation)

3. **Recipe Ingredients:**
   - Ingredient rows: Quantity | Unit | Ingredient | Browse | Remove
   - Unit dropdown from database (weight, volume, count categories)
   - Ingredient dropdown (leaf ingredients only)
   - Browse button opens hierarchical tree dialog
   - Add Ingredient button
   - Validation: Density required for cross-type conversions (volume↔weight)

4. **Sub-Recipes (Components):**
   - Recipe dropdown (excludes current recipe and existing components)
   - Quantity entry (batch multiplier, default 1.0)
   - Add button
   - Component list with Remove buttons
   - Validation messages: circular reference, depth limit, duplicate

5. **Save/Cancel buttons**

**Behavior:**
- Hierarchical tree dialog for ingredient selection (search, breadcrumb navigation)
- Real-time validation feedback
- Confirmation dialogs for removal operations
- Ingredient tree shows only leaf nodes as selectable

### 8.3 Recipe Details View

**Display:**
- Recipe metadata (name, category, source, prep time, production readiness)
- Yield types (from FinishedUnits)
- Ingredients list with quantities
- Sub-recipes (if any) with batch multipliers
- Aggregated ingredients (flattened from nested recipes)
- Cost breakdown (⚠️ LEGACY - to be moved to production/planning services)
- Notes

### 8.4 Recipe Variant Management

**UI Elements:**
- "Create Variant" button on recipe details
- Variant creation dialog:
  - Variant name entry (required)
  - Auto-generated full name preview
  - "Copy ingredients from base" checkbox (default: checked)
  - Production ready defaults to unchecked
- Recipe list shows variants indented under base recipe
- Visual indicator for variant relationships

---

## 9. Validation Rules

### 9.1 Creation Validation

| Rule ID | Validation | Error Message |
|---------|-----------|---------------|
| VAL-RCP-001 | Recipe name required | "Recipe name cannot be empty" |
| VAL-RCP-002 | Recipe name must be unique | "A recipe with this name already exists" |
| VAL-RCP-003 | Recipe name max 200 characters | "Name must be 200 characters or less" |
| VAL-RCP-004 | Category required | "Category is required" |
| VAL-RCP-005 | At least one complete yield type (FinishedUnit) required | "At least one complete yield type required" |
| VAL-RCP-006 | Yield type must have display_name, item_unit, items_per_batch | "Yield type missing required fields" |
| VAL-RCP-007 | All ingredients must be leaf (hierarchy level 2) | "Only leaf ingredients can be used in recipes" |
| VAL-RCP-008 | Ingredient quantities must be positive | "Ingredient quantity must be greater than zero" |
| VAL-RCP-009 | Ingredient units must be valid measurement units | "Invalid unit selected" |
| VAL-RCP-010 | Density required for cross-type conversions | "Density data required for [unit type] conversion" |

### 9.2 Sub-Recipe Validation

| Rule ID | Validation | Error Message |
|---------|-----------|---------------|
| VAL-RCP-011 | Component quantity must be > 0 | "Batch quantity must be greater than 0" |
| VAL-RCP-012 | Cannot add self as component | "Recipes cannot contain themselves" |
| VAL-RCP-013 | No circular references allowed | "Cannot add: would create circular reference" |
| VAL-RCP-014 | Maximum nesting depth 3 levels | "Cannot add: would exceed maximum nesting depth of 3 levels" |
| VAL-RCP-015 | Cannot add duplicate component | "Recipe is already a component" |

### 9.3 Variant Validation

| Rule ID | Validation | Error Message |
|---------|-----------|---------------|
| VAL-RCP-016 | Variant name required | "Variant name is required" |
| VAL-RCP-017 | Base recipe must exist | "Base recipe not found" |
| VAL-RCP-018 | Cannot create variant of variant | "Variants of variants not supported" |
| VAL-RCP-019 | base_recipe_id must not equal id | "Recipe cannot be variant of itself" |
| VAL-RCP-020 | Variant yield must match base recipe yield structure | "Variant yield (items_per_batch, item_unit) must match base recipe" |
| VAL-RCP-021 | Variant must have same number of FinishedUnits as base | "Variant must have {count} FinishedUnit(s) to match base recipe" |

### 9.4 Deletion Validation

| Rule ID | Validation | Error Message |
|---------|-----------|---------------|
| VAL-RCP-022 | Cannot delete if used as component in other recipes | "Cannot delete: used as component in [recipe names]" |
| VAL-RCP-023 | Cannot delete if has active FinishedUnit records | "Cannot delete: has active finished units" |
| VAL-RCP-024 | CAN delete even if ProductionRun instances exist | (No error - definitions independent of instances) |

---

## 10. Acceptance Criteria

### 10.1 Current Implementation Acceptance

**Must Have (Implemented):**
- ✅ Recipe creation with ingredient selection via hierarchical tree widget
- ✅ Recipe editing (metadata and ingredients)
- ✅ Validation preventing non-leaf ingredient use
- ✅ Recipe list view with search, category filter, and readiness filter
- ✅ Import/export supporting recipe catalog expansion
- ✅ Sub-recipe (nested recipe) support with cycle detection and depth limits
- ✅ Recipe variants with base_recipe_id linkage
- ✅ Production readiness flag (experimental vs production-ready)
- ✅ Multiple yield types per recipe via FinishedUnit records
- ✅ Recipe snapshots for production instance tracking
- ✅ Soft-delete via is_archived flag

**Architectural Debt (To Be Refactored):**
- ⚠️ Cost calculation methods exist in Recipe model and recipe_service
- ⚠️ Deletion protection extends to production instances (should only check definition dependencies)
- ⚠️ Soft-delete/archival based on production history (legacy behavior)

**Should Have (Future Enhancements):**
- [ ] Recipe versioning with change tracking
- [ ] Recipe cost calculations moved to production/planning services
- [ ] Recipe deletion logic corrected (definition dependencies only)
- [ ] Bulk recipe operations (duplicate, bulk delete, bulk category change)

**Nice to Have:**
- [ ] Recipe cloning (duplicate with new name)
- [ ] Recipe tags/labels (in addition to categories)
- [ ] Recipe instructions text area with rich formatting
- [ ] Recipe photos/images
- [ ] Nutrition calculation via ingredient aggregation

---

## 11. Dependencies

### 11.1 Upstream Dependencies (Blocks This)

- ✅ Ingredient hierarchy (recipes require leaf ingredients - hierarchy level 2)
- ✅ Import/export system (for recipe catalog management)
- ✅ FinishedUnit model (for yield specifications)
- ✅ ProductionRun model (for production instance tracking)
- ✅ Unit service (for measurement unit management)

### 11.2 Downstream Dependencies (This Blocks)

- Production planning (requires recipes for ingredient aggregation)
- Shopping list generation (requires recipes for purchase planning)
- Event management (requires recipes for fulfillment planning)
- Cost analysis (requires recipes for cost estimation - should use production instances, not definitions)
- Inventory depletion (requires recipes for FIFO consumption - via production instances)

### 11.3 Cross-Service Dependencies

**Services that currently depend on recipe_service:**
- production_service (uses recipes as templates for ProductionRun)
- finished_unit_service (validates recipe has FinishedUnit records)
- import_export_service (serializes/deserializes recipes)
- ingredient_hierarchy_service (provides leaf ingredients for recipe creation)

**Services that should NOT depend on recipe cost methods (architectural debt):**
- planning_service (should calculate costs on production plans, not recipe definitions)
- production_service (should calculate costs on ProductionRun instances)
- purchasing_service (should calculate costs based on purchase history)
- reporting_service (should aggregate costs from production instances)

---

## 12. Testing Requirements

### 12.1 Test Coverage

**Unit Tests (recipe_service):**
- Recipe CRUD operations (create, read, update, delete)
- Leaf ingredient validation (hierarchy level 2 enforcement)
- Recipe component management (add, remove, update)
- Circular reference detection
- Nesting depth validation (max 3 levels)
- Ingredient aggregation across nested recipes
- Recipe variant creation and linking
- Deletion protection validation (definition dependencies only)

**Unit Tests (Recipe model):**
- Model field validation (constraints)
- Relationship loading (ingredients, components, finished_units, snapshots)
- Variant self-referential prevention
- FinishedUnit yield validation

**Integration Tests:**
- Recipe creation workflow with ingredients and sub-recipes
- Hierarchical tree widget ingredient selection
- Recipe snapshot creation on production
- Recipe modification preserves existing snapshots
- Recipe deletion with component dependency check
- Import/export round-trip (recipes with components and finished_units)

**UI Tests:**
- Recipe form validation (required fields, data types)
- Ingredient tree widget (search, breadcrumb, leaf-only selection)
- Sub-recipe addition with validation feedback
- Yield type management (add, remove, validation)
- Production readiness flag toggle
- Category and readiness filtering

**User Acceptance Tests:**
- Create recipe with multiple ingredients and sub-recipes
- Edit recipe and verify snapshots preserve old state
- Create recipe variant and verify base linkage
- Delete recipe with component dependencies (blocked)
- Delete recipe with production history (allowed)
- Aggregate ingredients across 3-level nested recipes

---

## 13. Open Questions & Future Considerations

### 13.1 Architectural Refactoring Needed

**Q1:** How should recipe cost calculations be refactored from recipe_service?  
**A1:** Cost calculations should be moved to:
- `planning_service`: Cost estimates for production planning (uses recipes + current inventory/pricing)
- `production_service`: Actual costs calculated on ProductionRun instances (FIFO consumption tracking)
- `reporting_service`: Cost aggregation from production history (not recipe definitions)

**Q2:** How should recipe deletion protection be corrected?  
**A2:** Remove soft-delete/archival based on production history. Deletion protection should check ONLY:
- Recipe used as component in other recipes (block deletion)
- Recipe has active FinishedUnit records (block deletion)
- Recipe has ProductionRun instances (allow deletion - definitions independent of instances)

**Q3:** Should RecipeSnapshot creation be automatic or explicit?  
**A3:** Current implementation: Automatic on ProductionRun creation. This is correct behavior.

### 13.2 Future Enhancements

**Recipe Versioning:**
- Track recipe changes over time with version numbers
- Allow rollback to previous recipe versions
- Display change history in UI

**Recipe Categories vs Tags:**
- Current: Single category per recipe
- Future: Consider tag-based system for multi-dimensional categorization

**Recipe Instructions:**
- Current: Notes field only
- Future: Structured step-by-step instructions with timing and temperature

**Recipe Photos:**
- Visual reference for finished products
- Gallery of production examples

**Recipe Nutrition:**
- Calculate nutrition facts from ingredient data
- Support dietary restriction tagging (gluten-free, vegan, etc.)

**Recipe Scaling:**
- UI for batch multiplier calculation
- Automatic unit conversions for scaled quantities
- Ingredient availability checks before scaling

**Recipe Sharing:**
- Export recipes for sharing with other users
- Import community recipes
- Recipe rating and feedback system

---

## 14. Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2025-01-04 | Kent Gale | Initial seeded draft from documented knowledge |
| 0.2 | 2025-01-24 | Kent Gale | Baseline update reflecting current implementation: Added sub-recipes, variants, snapshots, FinishedUnit integration; Marked cost calculations and soft-delete as architectural debt |
| 0.3 | 2025-01-24 | Kent Gale | Added variant yield inheritance requirements (REQ-RCP-031 through REQ-RCP-044): Variants must define own FinishedUnits matching base recipe yield structure; Added get_base_yield_structure and get_finished_units primitives; Updated use case 4.3, validation rules 9.3, and section 2.1 |

---

## 15. Approval & Sign-off

**Document Owner:** Kent Gale  
**Last Review Date:** 2025-01-24  
**Next Review Date:** After architectural refactoring (cost calculations, deletion protection)  
**Status:** 📋 ACTIVE - BASELINE FOR REFACTORING

---

## 16. Related Documents

- **Design Specs:** 
  - `/docs/design/schema_v0.6_design.md` (Event-centric production model)
  - `/docs/design/session_management_remediation_spec.md` (Session handling patterns)
- **Functional Specs:**
  - `/docs/func-spec/F062_service_session_consistency_hardening.md` (Session management)
  - `/docs/func-spec/F063_recipe_variant_yield_inheritance.md` (Variant yield implementation)
  - Feature 031: Leaf ingredient validation
  - Feature 037: Recipe variants and production readiness
  - Feature 056: FinishedUnit yield specifications
- **Requirements:**
  - `/docs/requirements/req_ingredients.md` (Ingredient hierarchy dependency)
  - `/docs/requirements/req_finished_goods.md` (FinishedUnit/yield relationship)
- **Constitution:** 
  - `/.kittify/memory/constitution.md` (Architectural principles: definitions vs instances)
- **Testing:** 
  - `/tests/test_recipe_service.py` (Recipe service unit tests)
  - `/tests/test_recipe_model.py` (Recipe model unit tests)

---

## 17. Architectural Debt Register

This section documents known architectural issues that need to be addressed in future refactoring.

### DEBT-RCP-001: Cost Calculations in Recipe Service

**Issue:** Recipe model and recipe_service contain cost calculation methods that violate the "definitions vs instances" principle.

**Impact:** 
- Cost calculations should operate on production instances, not recipe definitions
- Current implementation couples recipe definitions to transient cost data
- Prevents proper cost tracking on production instances

**Methods to Refactor:**
- `Recipe.calculate_cost()` → Remove from model
- `RecipeIngredient.calculate_cost()` → Remove from model
- `recipe_service.calculate_recipe_cost()` → Move to production_service
- `recipe_service.calculate_actual_cost()` → Move to production_service (FIFO)
- `recipe_service.calculate_estimated_cost()` → Move to planning_service
- `recipe_service.get_recipe_with_costs()` → Move to planning_service

**Proposed Solution:**
- Move FIFO-based cost calculations to `production_service.calculate_production_cost(production_run_id)`
- Move estimated cost calculations to `planning_service.estimate_recipe_cost(recipe_id, batch_multiplier)`
- Remove all cost methods from Recipe model and recipe_service
- Update UI to call appropriate service based on context (planning vs production)

**Priority:** High (violates core architectural principle)

### DEBT-RCP-002: Deletion Protection Based on Production Instances

**Issue:** Recipe deletion logic prevents deletion if ProductionRun instances exist, violating the "definitions independent of instances" principle.

**Impact:**
- Recipe definitions cannot be deleted even when only instance dependencies exist
- Soft-delete/archival adds complexity for catalog management
- Inconsistent with architectural principle that definitions and instances are independent

**Methods to Refactor:**
- `recipe_service.delete_recipe()` → Remove production instance checks
- `recipe_service.check_recipe_dependencies()` → Check only definition dependencies

**Proposed Solution:**
- Deletion protection should check ONLY:
  - Recipe used as component in other recipes (definition dependency)
  - Recipe has active FinishedUnit records (definition dependency)
- Remove archival logic based on production history
- Allow hard deletion if no definition dependencies exist
- ProductionRun instances retain RecipeSnapshot for historical data

**Priority:** Medium (reduces catalog management complexity)

### DEBT-RCP-003: UI Cost Display Coupled to Recipe Service

**Issue:** Recipe details view calls `recipe_service.get_recipe_with_costs()` for cost display, tightly coupling UI to deprecated service methods.

**Impact:**
- UI will break when cost methods are removed from recipe_service
- Cost display shows definition-based estimates, not instance-based actuals
- Confuses users about whether costs are estimates or actuals

**UI Components to Update:**
- `RecipesTab._view_details()` → Update to call planning_service for cost estimates
- `RecipeFormDialog` → Remove cost display or clarify as "estimated"

**Proposed Solution:**
- Add context parameter to details view: "planning" vs "production"
- Planning context: Call `planning_service.estimate_recipe_cost()`
- Production context: Show costs from ProductionRun instances
- Clearly label costs as "Estimated" or "Actual from [Production Run]"

**Priority:** Medium (tied to DEBT-RCP-001 refactoring)

---

**END OF REQUIREMENTS DOCUMENT (ACTIVE BASELINE)**
