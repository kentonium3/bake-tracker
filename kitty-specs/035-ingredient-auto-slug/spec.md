# Feature Specification: Ingredient Auto-Slug & Deletion Protection

**Feature Branch**: `035-ingredient-auto-slug`
**Created**: 2026-01-02
**Status**: Draft
**Input**: Phase 3 of ingredient hierarchy gap analysis (docs/design/_F033-F036_ingredient_hierarchy_gap_analysis.md)

## Clarifications

### Session 2026-01-02

- Q: When denormalizing ingredient data into historical snapshot records, should the system store just the name, full hierarchy path, or both as separate fields? → A: Both name and parent names as separate fields
- Q: Should Clear Filters button be added to Recipes tab in addition to Products and Inventory? → A: No, only Products and Inventory as specified

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create Ingredient with Auto-Generated Slug (Priority: P1)

As a user creating a new ingredient, I want the system to automatically generate a unique slug from the ingredient name so that I don't have to manually create or manage slugs.

**Why this priority**: Slug generation is foundational - every new ingredient needs a unique slug for the system to function correctly. Without this, users must manually ensure uniqueness, which is error-prone.

**Independent Test**: Can be fully tested by creating ingredients via UI and verifying slugs are auto-generated without user intervention.

**Acceptance Scenarios**:

1. **Given** I am creating a new ingredient named "Brown Sugar", **When** I save the ingredient, **Then** the system auto-generates slug "brown-sugar" without requiring my input.

2. **Given** an ingredient with slug "flour" already exists, **When** I create a new ingredient named "Flour", **Then** the system generates slug "flour-2" (or next available number).

3. **Given** slugs "vanilla" and "vanilla-2" exist, **When** I create an ingredient named "Vanilla", **Then** the system generates slug "vanilla-3".

4. **Given** I am creating an ingredient with special characters "All-Purpose Flour (Bleached)", **When** I save, **Then** the system generates a clean slug like "all-purpose-flour-bleached".

---

### User Story 2 - Delete Ingredient Blocked by Catalog References (Priority: P1)

As a user managing the ingredient hierarchy, I want the system to prevent me from deleting ingredients that are still used by Products or Recipes so that I don't accidentally break catalog data integrity.

**Why this priority**: Deletion protection for catalog entities is critical - accidentally deleting an ingredient used by products or recipes would corrupt the catalog and require manual data repair.

**Independent Test**: Can be fully tested by attempting to delete ingredients with/without product and recipe references.

**Acceptance Scenarios**:

1. **Given** ingredient "All-Purpose Flour" is referenced by 3 Products, **When** I attempt to delete it, **Then** the system blocks deletion and displays "Cannot delete: 3 products reference this ingredient. Reassign products first."

2. **Given** ingredient "Vanilla Extract" is used in 5 Recipes, **When** I attempt to delete it, **Then** the system blocks deletion and displays "Cannot delete: 5 recipes use this ingredient. Update recipes first."

3. **Given** ingredient "Cocoa Powder" is referenced by 2 Products AND used in 3 Recipes, **When** I attempt to delete it, **Then** the system blocks deletion and displays both counts.

4. **Given** ingredient "Unused Ingredient" has no Product or Recipe references, **When** I attempt to delete it, **Then** deletion proceeds (after handling historical records per User Story 3).

---

### User Story 3 - Delete Ingredient Preserves Historical Data (Priority: P2)

As a user deleting an ingredient, I want historical records (like inventory snapshots) to preserve the ingredient name/details so that historical reports remain meaningful after deletion.

**Why this priority**: Historical data preservation enables ingredient hierarchy evolution over time without losing the ability to understand past inventory states. Lower priority than P1 because it's about data quality, not data integrity.

**Independent Test**: Can be tested by deleting an ingredient that appears in historical snapshots and verifying the snapshot data remains readable.

**Acceptance Scenarios**:

1. **Given** ingredient "Old Flour Brand" appears in 2 InventorySnapshots, **When** I delete the ingredient, **Then** the snapshot records retain the ingredient name in a denormalized field and the FK is nullified.

2. **Given** ingredient "Discontinued Item" has IngredientAlias records, **When** I delete the ingredient, **Then** the alias records are cascade-deleted.

3. **Given** ingredient "Mapped Item" has IngredientCrosswalk records (external ID mappings), **When** I delete the ingredient, **Then** the crosswalk records are cascade-deleted.

4. **Given** historical records exist, **When** I view an old inventory snapshot after ingredient deletion, **Then** I can still see the original ingredient name that was recorded.

---

### User Story 4 - Clear Hierarchy Filters (Priority: P3) - ALREADY COMPLETE

**Status**: COMPLETE - Implemented in F034 (verified during planning research)

As a user browsing Products or Inventory with hierarchy filters applied, I want a clear/reset button so that I can quickly remove all filter selections and see the full list again.

**Implementation**: `src/ui/products_tab.py:194-198` and `src/ui/inventory_tab.py:189-193`

**Acceptance Scenarios** (all verified working):

1. **Given** I have selected L0="Baking", L1="Flour", L2="All-Purpose" filters on Products tab, **When** I click "Clear Filters", **Then** all three dropdowns reset to "All" and the full product list displays.

2. **Given** I have selected only L0="Dairy" filter on Inventory tab, **When** I click "Clear Filters", **Then** the L0 dropdown resets and full inventory displays.

3. **Given** no filters are currently applied, **When** I click "Clear Filters", **Then** nothing changes (button is no-op or disabled).

---

### Edge Cases

- What happens when slug generation encounters database constraint violation? (Retry with incremented suffix)
- How does system handle deletion attempt during active transaction? (Block with appropriate error)
- What if historical denormalization fails mid-delete? (Roll back entire transaction)
- What happens if user tries to delete an L0/L1 ingredient with children? (Existing child validation from Phase 1 should block this)

## Requirements *(mandatory)*

### Functional Requirements

**Slug Auto-Generation:**

- **FR-001**: System MUST auto-generate a slug from display_name when creating an ingredient via UI
- **FR-002**: System MUST convert display_name to lowercase, replace spaces with hyphens, and remove special characters for slug generation
- **FR-003**: System MUST detect slug conflicts and append numeric suffix (-2, -3, etc.) to ensure uniqueness
- **FR-004**: System MUST NOT require user input for slug field during ingredient creation

**Deletion Protection - Catalog Entities:**

- **FR-005**: System MUST block ingredient deletion if any Product references the ingredient
- **FR-006**: System MUST block ingredient deletion if any RecipeIngredient references the ingredient
- **FR-007**: System MUST display count of referencing Products when blocking deletion
- **FR-008**: System MUST display count of referencing Recipes when blocking deletion
- **FR-009**: System MUST provide clear error message explaining why deletion is blocked and what action user must take

**Deletion - Historical Data Preservation:**

- **FR-010**: System MUST denormalize ingredient name and parent names into InventorySnapshotIngredient records before nullifying FK
- **FR-011**: System MUST add three snapshot fields to InventorySnapshotIngredient model: `ingredient_name_snapshot` (L2 name), `parent_l1_name_snapshot` (L1 parent name, nullable), `parent_l0_name_snapshot` (L0 root name, nullable)
- **FR-012**: System MUST cascade-delete IngredientAlias records when ingredient is deleted
- **FR-013**: System MUST cascade-delete IngredientCrosswalk records when ingredient is deleted
- **FR-014**: System MUST perform denormalization and deletion in single atomic transaction

**Clear/Reset Filters:** (ALREADY COMPLETE - F034)

- **FR-015**: ~~System MUST provide "Clear Filters" button on Products tab hierarchy filter area~~ DONE
- **FR-016**: ~~System MUST provide "Clear Filters" button on Inventory tab hierarchy filter area~~ DONE
- **FR-017**: ~~Clear button MUST reset all hierarchy level dropdowns (L0, L1, L2) to default "All" state~~ DONE
- **FR-018**: ~~Clear button MUST trigger list refresh to show unfiltered data~~ DONE

### Key Entities

- **Ingredient**: Core entity being protected/deleted. Has `slug` (unique), `display_name`, `parent_ingredient_id`
- **Product**: Catalog entity referencing Ingredient via `ingredient_id` FK. Blocks ingredient deletion.
- **RecipeIngredient**: Junction table linking Recipe to Ingredient. Blocks ingredient deletion.
- **InventorySnapshotIngredient**: Historical record. Receives denormalized fields (`ingredient_name_snapshot`, `parent_l1_name_snapshot`, `parent_l0_name_snapshot`) before FK nullification.
- **IngredientAlias**: Metadata - alternative names for ingredient. Cascade-deleted with ingredient.
- **IngredientCrosswalk**: Metadata - external ID mappings (FoodOn, etc.). Cascade-deleted with ingredient.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can create ingredients without manually entering slugs (100% auto-generation)
- **SC-002**: Zero data integrity violations from ingredient deletion (Products/Recipes never orphaned)
- **SC-003**: Historical inventory snapshots remain readable after ingredient deletion (ingredient name preserved)
- **SC-004**: ~~Users can clear all hierarchy filters with single click (reduced from 3 clicks to 1)~~ ALREADY COMPLETE (F034)
- **SC-005**: All deletion validation messages clearly indicate required user action

## Assumptions

1. The existing `generate_unique_slug()` service method exists but is not hooked into UI create workflow
2. InventorySnapshotIngredient model may need schema migration to add `ingredient_name_snapshot` field
3. Cascade delete for Alias and Crosswalk can be configured via SQLAlchemy relationship or handled in service layer
4. Existing Phase 1 validation (child count, hierarchy constraints) remains in place and is not modified by this feature
5. Clear filter buttons follow existing UI patterns in the application

## Dependencies

- **F033 (Phase 1)**: Core validation services (`can_change_parent`, `get_product_count`, `get_child_count`) - COMPLETE
- **F034 (Phase 2)**: Cascading filter fixes - COMPLETE
- **Schema**: May require migration to add `ingredient_name_snapshot` to InventorySnapshotIngredient

## Out of Scope

- Auto-updating Product records when ingredient hierarchy changes (not needed - reference by ID)
- Auto-updating Recipe records when ingredient attributes change (not needed - reference by ID)
- Soft-delete mechanism for ingredients (using denormalization approach instead)
- Batch deletion of multiple ingredients
- Undo/restore deleted ingredients
