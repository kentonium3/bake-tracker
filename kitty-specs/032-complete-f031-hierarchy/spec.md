# Feature Specification: Complete F031 Hierarchy UI Implementation

**Feature Branch**: `032-complete-f031-hierarchy`
**Created**: 2025-12-31
**Status**: Draft
**Input**: Bug fix for incomplete F031 Ingredient Hierarchy UI implementation
**Related**: F031 (Ingredient Hierarchy), `docs/bugs/BUG_F031_incomplete_hierarchy_ui.md`

## Background

The F031 Ingredient Hierarchy feature is partially implemented:
- **Backend complete**: Schema (`parent_ingredient_id`, `hierarchy_level`), import/export, and services are working
- **Product edit form complete**: Uses hierarchical ingredient selection (Category → Subcategory → Ingredient)
- **UI incomplete**: Multiple tabs and forms still use the deprecated `category` field instead of the three-tier hierarchy

**Impact**: Users cannot effectively manage or view the ingredient hierarchy, making the feature unusable despite full backend support.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Ingredients by Hierarchy (Priority: P1)

As a user viewing my ingredients, I want to see them organized by their three-tier hierarchy (Root Category → Subcategory → Ingredient) so I can understand the ingredient taxonomy at a glance.

**Why this priority**: This is the core visibility requirement. Without hierarchy columns, users cannot see the taxonomy structure that exists in the database.

**Independent Test**: Can be fully tested by opening the Ingredients tab and verifying all three hierarchy levels display correctly for each ingredient.

**Acceptance Scenarios**:

1. **Given** I have ingredients with hierarchy data, **When** I open the Ingredients tab, **Then** I see columns for Root Category (L0), Subcategory (L1), and Ingredient Name (L2)
2. **Given** I have a leaf ingredient "Semi-Sweet Chips" under "Dark Chocolate" under "Chocolate", **When** I view the ingredients grid, **Then** I see "Chocolate | Dark Chocolate | Semi-Sweet Chips" in the respective columns
3. **Given** I click on a hierarchy column header, **When** sorting is applied, **Then** ingredients sort alphabetically by that hierarchy level

---

### User Story 2 - Filter Ingredients by Hierarchy Level (Priority: P1)

As a user with many ingredients, I want to filter by hierarchy level (All, Root Only, Subcategory Only, Leaf Only) so I can quickly find what I'm looking for.

**Why this priority**: Filtering is essential for usability with large ingredient catalogs. The deprecated category filter must be replaced.

**Independent Test**: Can be tested by selecting each filter option and verifying only ingredients at that level appear.

**Acceptance Scenarios**:

1. **Given** I have ingredients at all three levels, **When** I select "Root Categories Only (L0)", **Then** only L0 ingredients appear
2. **Given** I have the filter set to "Leaf Ingredients Only (L2)", **When** I search for "chocolate", **Then** only L2 ingredients containing "chocolate" appear
3. **Given** I have any filter active, **When** I click "Clear", **Then** all filters reset and all ingredients display

---

### User Story 3 - Create/Edit Ingredients with Hierarchy Position (Priority: P1)

As a user managing ingredients, I want to specify where a new ingredient belongs in the hierarchy using cascading dropdowns so I can properly organize my ingredient catalog.

**Why this priority**: Users must be able to create ingredients at any level and correctly position them in the hierarchy.

**Independent Test**: Can be tested by creating a new L2 ingredient, selecting its L0 parent, then L1 parent, and verifying it saves correctly.

**Acceptance Scenarios**:

1. **Given** I am creating a new leaf ingredient, **When** I select a Root Category (L0), **Then** the Subcategory dropdown populates with children of that category
2. **Given** I am editing an existing L2 ingredient, **When** the form opens, **Then** both L0 and L1 dropdowns are pre-populated with the current hierarchy position
3. **Given** I want to create a new Root Category (L0), **When** I leave both parent dropdowns empty/unselected, **Then** the ingredient saves as a new L0
4. **Given** I want to create a new Subcategory (L1), **When** I select only an L0 parent, **Then** the ingredient saves as a child of that L0

---

### User Story 4 - Filter Products by Ingredient Hierarchy (Priority: P2)

As a user viewing products, I want to filter by ingredient hierarchy so I can find all products that use ingredients from a specific category or subcategory.

**Why this priority**: Products are linked to ingredients; users need hierarchy-aware filtering to find related products.

**Independent Test**: Can be tested by selecting an L0 category and verifying all products using ingredients under that hierarchy appear.

**Acceptance Scenarios**:

1. **Given** I select "Chocolate" in the L0 filter, **When** the filter applies, **Then** I see all products using any ingredient under the Chocolate hierarchy
2. **Given** products are displayed, **When** I view the ingredient column, **Then** I see the full hierarchy path (e.g., "Chocolate → Dark → Semi-Sweet Chips")
3. **Given** I have hierarchy filters set, **When** I further narrow with L1 and L2 filters, **Then** the product list updates to show only matching products

---

### User Story 5 - View Inventory with Hierarchy Information (Priority: P2)

As a user managing inventory, I want to see ingredient hierarchy information in the inventory display so I understand what category of ingredients my inventory items belong to.

**Why this priority**: Inventory visibility should match the ingredient taxonomy for consistency across the application.

**Independent Test**: Can be tested by viewing inventory items and verifying hierarchy columns display correctly.

**Acceptance Scenarios**:

1. **Given** I have inventory items, **When** I view the Inventory tab, **Then** I see hierarchy columns (L0, L1, L2) instead of the deprecated category column
2. **Given** I want to filter inventory, **When** I use hierarchy filters, **Then** only inventory items matching the selected hierarchy appear
3. **Given** I am adding/editing inventory, **When** the form displays, **Then** I see the ingredient's full hierarchy path as read-only information

---

### User Story 6 - Prevent Invalid Hierarchy Assignments (Priority: P2)

As a user, I want the system to prevent assigning products or recipes to non-leaf ingredients so I don't accidentally create invalid data.

**Why this priority**: Data integrity requires that only L2 (leaf) ingredients can have products or be used in recipes.

**Independent Test**: Can be tested by attempting to assign a product to an L0 or L1 ingredient and verifying the operation is blocked.

**Acceptance Scenarios**:

1. **Given** I try to create a product linked to an L0 ingredient, **When** I attempt to save, **Then** the system displays an error and prevents the save
2. **Given** I try to use an L1 ingredient in a recipe, **When** I attempt to save, **Then** the system displays an error indicating only leaf ingredients are allowed
3. **Given** I am selecting an ingredient in any form, **When** I view the ingredient dropdown/selector, **Then** only L2 (leaf) ingredients are selectable for product/recipe assignment

---

### Edge Cases

- What happens when an ingredient has no children (empty subcategory list)?
  - The subcategory dropdown should display "(No subcategories)" and remain disabled
- What happens when viewing a legacy ingredient with only `category` field populated?
  - The UI should use hierarchy fields only; legacy `category` is ignored
- How does the system handle moving an ingredient to a different parent?
  - The edit form allows changing the parent; the save operation updates `parent_ingredient_id`
- What happens when a user tries to delete an L1 that has L2 children?
  - Existing deletion validation should prevent this (handled by existing service layer)

---

## Requirements *(mandatory)*

### Functional Requirements

**Ingredients Tab - Display:**
- **FR-001**: Ingredients grid MUST display three hierarchy columns: Root Category (L0), Subcategory (L1), Ingredient Name (L2)
- **FR-002**: System MUST remove the deprecated "Category" column from the Ingredients grid
- **FR-003**: Each hierarchy column MUST be sortable by clicking the column header
- **FR-004**: For ingredients that are L0 or L1, child-level columns MUST display as empty/dash

**Ingredients Tab - Filtering:**
- **FR-005**: System MUST replace the category dropdown with a hierarchy level filter
- **FR-006**: Hierarchy level filter MUST include options: All Levels, Root Categories (L0), Subcategories (L1), Leaf Ingredients (L2)
- **FR-007**: Search MUST work across all hierarchy levels regardless of filter selection

**Ingredient Edit Form:**
- **FR-008**: Form MUST display cascading dropdowns for Root Category (L0) and Subcategory (L1)
- **FR-009**: L1 dropdown MUST populate dynamically based on selected L0
- **FR-010**: When editing existing ingredients, dropdowns MUST pre-populate with current hierarchy position
- **FR-011**: Form MUST allow creating ingredients at any level (L0, L1, or L2)
- **FR-012**: System MUST remove the deprecated "Category" dropdown from the form

**Products Tab:**
- **FR-013**: Products tab MUST display ingredient hierarchy path (e.g., "Chocolate → Dark → Chips")
- **FR-014**: Products tab MUST provide hierarchy-based filtering (L0 → L1 → L2 cascading filters)
- **FR-015**: System MUST remove the deprecated category filter from Products tab

**Inventory Tab:**
- **FR-016**: Inventory grid MUST display hierarchy columns instead of deprecated category column
- **FR-017**: Inventory tab MUST provide hierarchy-based filtering
- **FR-018**: System MUST remove the deprecated category filter and column

**Inventory Edit Form:**
- **FR-019**: Add/Edit Inventory dialogs MUST display ingredient hierarchy as read-only labels
- **FR-020**: All three hierarchy levels (L0, L1, L2) MUST be visible in the form

**Validation:**
- **FR-021**: System MUST prevent assigning products to non-leaf (L0/L1) ingredients
- **FR-022**: System MUST prevent using non-leaf ingredients in recipes

### Key Entities

- **Ingredient**: Has `hierarchy_level` (0, 1, or 2), `parent_ingredient_id` (FK to parent), and deprecated `category` field
- **Product**: Links to Ingredient via `ingredient_id`; can only link to L2 ingredients
- **InventoryItem**: Links to Product, inherits ingredient hierarchy through the relationship

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All tabs (Ingredients, Products, Inventory) display hierarchy information instead of deprecated category field
- **SC-002**: Users can filter ingredients by hierarchy level with 100% accuracy (no misclassified results)
- **SC-003**: Users can create ingredients at any hierarchy level (L0, L1, L2) through the edit form
- **SC-004**: Users can navigate the full ingredient hierarchy within 3 clicks from any tab
- **SC-005**: Zero references to deprecated "category" UI elements remain in affected components
- **SC-006**: 100% of manual test cases from the bug specification pass

### Definition of Done

- Ingredients tab shows L0/L1/L2 columns, not category
- Ingredient edit form uses hierarchy selection, not category dropdown
- Can create L0, L1, and L2 ingredients via edit form
- Products tab filters by hierarchy, shows ingredient paths
- Inventory tab displays and filters by hierarchy
- No UI references to deprecated "category" field in affected components
- All acceptance scenarios pass manual testing

---

## Assumptions

1. The `ingredient_hierarchy_service.py` functions (`get_ancestors()`, `get_children()`, `get_root_ingredients()`, `get_hierarchy_path()`) work correctly as specified in F031
2. The Product edit form's existing hierarchy implementation can serve as a reference pattern
3. Legacy `category` field data can be safely ignored by UI (field remains in schema but unused)
4. Existing deletion validation in service layer prevents orphaning children when deleting parent ingredients

---

## Out of Scope

- Database schema changes (schema is complete)
- Import/export modifications (already handles hierarchy)
- Service layer changes (services are complete)
- Recipe ingredient selection (separate enhancement)
- Bulk ingredient hierarchy reassignment tools
