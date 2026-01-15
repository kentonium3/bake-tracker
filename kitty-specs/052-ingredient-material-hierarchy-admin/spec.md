# Feature Specification: Ingredient & Material Hierarchy Admin

**Feature Branch**: `052-ingredient-material-hierarchy-admin`
**Created**: 2026-01-14
**Status**: Draft
**Input**: User description: "L2-only display for Ingredients/Materials tabs with parent context columns, plus Hierarchy Admin UI for add/rename/reparent operations."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Clear Ingredient Listings (Priority: P1)

As a user browsing ingredients, I want to see only usable items (L2 leaf nodes) with their full hierarchy path visible, so I can quickly find and select the right ingredient without confusion from structural categories.

**Why this priority**: This addresses the primary user complaint - mixed L1/L2 listings are confusing. Users don't understand which items are "structural" vs "usable." This is the core pain point driving this feature.

**Independent Test**: Can be fully tested by opening the Ingredients tab and verifying only L2 items appear with L0/L1 context columns. Delivers immediate clarity to the user experience.

**Acceptance Scenarios**:

1. **Given** the Ingredients tab is open, **When** I view the listing, **Then** I see only L2 (leaf) items - no L1 structural items appear
2. **Given** an ingredient "All-Purpose Flour" exists under "Wheat Flours" (L1) under "Flours & Starches" (L0), **When** I view the listing, **Then** I see three columns: L0="Flours & Starches", L1="Wheat Flours", L2="All-Purpose Flour"
3. **Given** a filter is set to L0="Flours & Starches", **When** I view the filtered listing, **Then** I see only L2 items within that L0 category with their L1 context visible

---

### User Story 2 - View Clear Material Listings (Priority: P1)

As a user browsing materials, I want to see only usable items (materials) with their category/subcategory path visible, so I can quickly find packaging and supplies without confusion from structural categories.

**Why this priority**: Materials have the same display problem as ingredients. Both must be fixed together for UI consistency.

**Independent Test**: Can be fully tested by opening the Materials tab and verifying only materials (not categories/subcategories) appear with parent context columns.

**Acceptance Scenarios**:

1. **Given** the Materials tab is open, **When** I view the listing, **Then** I see only materials - no category or subcategory items appear
2. **Given** a material "10x10 Cake Box" exists under subcategory "Window Boxes" under category "Boxes", **When** I view the listing, **Then** I see columns: Category="Boxes", Subcategory="Window Boxes", Material="10x10 Cake Box"

---

### User Story 3 - Add New Ingredient (Priority: P2)

As an admin, I want to add new L2 ingredients under existing L1 parents, so I can expand the ingredient catalog without editing the database directly.

**Why this priority**: Currently requires database manipulation. Adding new items is essential for catalog maintenance but less urgent than fixing the confusing display.

**Independent Test**: Can be tested by accessing Hierarchy Admin, creating a new L2 ingredient, and verifying it appears in the Ingredients tab and is available in Product/Recipe dropdowns.

**Acceptance Scenarios**:

1. **Given** I'm in Hierarchy Admin for Ingredients, **When** I select an L1 parent and enter a new L2 name and confirm, **Then** the new ingredient is created under that parent
2. **Given** I try to add an L2 with a name that already exists under the same L1 parent, **When** I confirm, **Then** I see a validation error and the item is not created
3. **Given** I successfully add a new L2 ingredient, **When** I return to the Ingredients tab, **Then** the new item appears in the listing
4. **Given** I successfully add a new L2 ingredient, **When** I create or edit a Product, **Then** the new ingredient appears in the ingredient dropdown

---

### User Story 4 - Add New Material (Priority: P2)

As an admin, I want to add new materials under existing subcategories, so I can expand the materials catalog without editing the database directly.

**Why this priority**: Same as ingredients - essential for catalog maintenance.

**Independent Test**: Can be tested by accessing Hierarchy Admin for Materials, creating a new material, and verifying it appears in listings and dropdowns.

**Acceptance Scenarios**:

1. **Given** I'm in Hierarchy Admin for Materials, **When** I select a subcategory and enter a new material name and confirm, **Then** the new material is created under that subcategory
2. **Given** I try to add a material with a name that already exists under the same subcategory, **When** I confirm, **Then** I see a validation error and the item is not created

---

### User Story 5 - Rename Ingredient or Material (Priority: P2)

As an admin, I want to rename any item in the hierarchy (L0, L1, L2 for ingredients; category, subcategory, material for materials), so I can fix typos and standardize naming without database edits.

**Why this priority**: Common maintenance need. Must propagate to display without affecting historical data.

**Independent Test**: Can be tested by renaming an item in Hierarchy Admin and verifying the new name appears in all current listings while historical snapshots retain the original name.

**Acceptance Scenarios**:

1. **Given** I'm in Hierarchy Admin and select an item, **When** I change its name and confirm, **Then** the new name is saved
2. **Given** I rename an L2 ingredient, **When** I view Products that use that ingredient, **Then** I see the new name displayed
3. **Given** I rename an L2 ingredient, **When** I view Recipes that use that ingredient, **Then** I see the new name displayed
4. **Given** I rename an ingredient that was used in a historical recipe snapshot (production run), **When** I view that snapshot, **Then** I see the original name (immutable history)
5. **Given** I try to rename an item to a name that already exists among its siblings, **When** I confirm, **Then** I see a validation error

---

### User Story 6 - Reparent Items (Priority: P3)

As an admin, I want to move L2 items to a different L1 parent (or L1 to different L0), so I can reorganize the hierarchy structure as needs evolve.

**Why this priority**: Less common operation than add/rename. Helpful for reorganization but not daily workflow.

**Independent Test**: Can be tested by moving an L2 ingredient to a new L1 parent in Hierarchy Admin and verifying the new hierarchy path displays correctly everywhere.

**Acceptance Scenarios**:

1. **Given** I'm in Hierarchy Admin and select an L2 ingredient, **When** I choose a new L1 parent and confirm, **Then** the ingredient moves to the new parent
2. **Given** I reparent an ingredient, **When** I view it in the Ingredients tab, **Then** the L0/L1 columns reflect the new hierarchy
3. **Given** I reparent an ingredient used by Products, **When** I view those Products, **Then** they still reference the same ingredient (FK unchanged) but display shows new hierarchy path
4. **Given** I try to reparent in a way that would create a cycle (e.g., L1 becoming child of its own L2), **When** I confirm, **Then** I see a validation error preventing the operation

---

### User Story 7 - View Hierarchy Tree with Usage Counts (Priority: P3)

As an admin, I want to see the complete hierarchy as a tree and see how many products/recipes use each item, so I can make informed decisions about changes.

**Why this priority**: Supporting feature for admin operations. Helps prevent accidental disruption to items with many dependencies.

**Independent Test**: Can be tested by opening Hierarchy Admin and verifying the tree view shows all levels expandable/collapsible with usage counts for selected items.

**Acceptance Scenarios**:

1. **Given** I open Hierarchy Admin for Ingredients, **When** I view the interface, **Then** I see a tree showing L0 nodes expandable to L1 nodes expandable to L2 nodes
2. **Given** I select an L2 ingredient in the tree, **When** I view its details, **Then** I see counts of products and recipes that reference it
3. **Given** I select an L1 item in the tree, **When** I view its details, **Then** I see counts reflecting all L2 children under it

---

### Edge Cases

- What happens when reparenting the last L2 under an L1? (L1 becomes empty - display should handle gracefully)
- How does the system handle renaming to an empty string? (Validation must reject)
- What happens when an L1 has no L2 children? (Not displayed in L2-only listings, but visible in Hierarchy Admin tree)
- What if user enters leading/trailing whitespace in names? (Should be trimmed automatically)
- What happens if two users (future multi-user scenario) edit the same item concurrently? (First-write-wins or conflict detection - defer to future implementation)

## Requirements *(mandatory)*

### Functional Requirements

**Display Requirements:**
- **FR-001**: System MUST display only L2 (leaf) items in the Ingredients tab main listing
- **FR-002**: System MUST display only materials (not categories/subcategories) in the Materials tab main listing
- **FR-003**: System MUST show L0 parent in a dedicated column for each ingredient
- **FR-004**: System MUST show L1 parent in a dedicated column for each ingredient
- **FR-005**: System MUST show category in a dedicated column for each material
- **FR-006**: System MUST show subcategory in a dedicated column for each material
- **FR-007**: System MUST maintain existing filter functionality (by L0/category, by L1/subcategory)

**Admin UI Requirements:**
- **FR-008**: System MUST provide a "Hierarchy Admin" menu option in Catalog mode
- **FR-009**: System MUST display ingredient hierarchy as an expandable/collapsible tree in Hierarchy Admin
- **FR-010**: System MUST display material hierarchy as an expandable/collapsible tree in Hierarchy Admin
- **FR-011**: System MUST show usage counts (products, recipes) when an item is selected in Hierarchy Admin

**Add Item Requirements:**
- **FR-012**: Admin MUST be able to create new L2 ingredients by selecting an L1 parent and entering a name
- **FR-013**: Admin MUST be able to create new materials by selecting a subcategory and entering a name
- **FR-014**: System MUST validate that new item names are unique among siblings
- **FR-015**: System MUST automatically set hierarchy_level = 2 for new ingredients

**Rename Requirements:**
- **FR-016**: Admin MUST be able to rename any item (L0, L1, L2 for ingredients; category, subcategory, material for materials)
- **FR-017**: System MUST validate that renamed item names are unique among siblings
- **FR-018**: System MUST propagate name changes to Product displays
- **FR-019**: System MUST propagate name changes to Recipe displays
- **FR-020**: System MUST NOT change historical recipe snapshots (F037 immutability)

**Reparent Requirements:**
- **FR-021**: Admin MUST be able to move L2 ingredients to a different L1 parent
- **FR-022**: Admin MUST be able to move L1 ingredients to a different L0 parent
- **FR-023**: Admin MUST be able to move materials to a different subcategory
- **FR-024**: System MUST validate that reparenting does not create cycles
- **FR-025**: System MUST update hierarchy path display after reparenting
- **FR-026**: System MUST NOT change Product/Recipe FKs when reparenting (only display context changes)

### Key Entities

- **Ingredient**: Hierarchical catalog item (L0, L1, or L2). L2 items are "usable" in products/recipes. Has parent_ingredient_id FK for hierarchy, hierarchy_level (0, 1, or 2), display_name, slug.
- **Material**: Catalog item for packaging/supplies. Has category and subcategory references. Leaf materials are usable in products.
- **Product**: Uses ingredients and materials via FK relationships. Display shows current ingredient/material names.
- **Recipe**: Uses ingredients via FK relationships. Display shows current ingredient names.
- **RecipeSnapshot**: Immutable historical record of a recipe at production time. Must preserve original names.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users see only usable items (L2/materials) in main listings - 100% of L1/category/subcategory structural items filtered out
- **SC-002**: Users can identify the full hierarchy path (L0/L1/L2) at a glance without clicking into item details
- **SC-003**: Admin can add a new L2 ingredient in under 30 seconds (open admin, select parent, enter name, confirm)
- **SC-004**: Admin can rename any item in under 20 seconds (select item, edit name, confirm)
- **SC-005**: Admin can reparent an item in under 30 seconds (select item, choose new parent, confirm)
- **SC-006**: 100% of existing filters (by L0, by L1) continue to work correctly
- **SC-007**: 100% of historical recipe snapshots remain unchanged after any admin operation
- **SC-008**: Materials admin interface matches Ingredients admin interface in structure and behavior (UI consistency)

## Assumptions

- Materials already have a category/subcategory structure similar to ingredient L0/L1 hierarchy
- Existing ingredient hierarchy service provides validation methods that can be extended
- Tree view can be implemented with CustomTkinter's treeview widget or equivalent
- Single-user desktop app means no concurrent edit conflicts to handle in MVP
- Historical immutability is enforced by recipe snapshot architecture (F037 - RecipeSnapshot stores denormalized ingredient names at production time; these records are never modified by admin operations)
