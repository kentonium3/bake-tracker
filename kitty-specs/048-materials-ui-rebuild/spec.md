# Feature Specification: Materials UI Rebuild - Match Ingredients Pattern

**Feature Branch**: `048-materials-ui-rebuild`
**Created**: 2026-01-11
**Status**: Draft
**Input**: Design document `docs/design/F048_materials_ui_rebuild.md`

## Overview

The current Materials UI violates the "parallel ingredients exactly" principle established in F047. The Materials tab uses a single collapsible tree view with mixed listings instead of the standardized 3-tab grid pattern used by Ingredients. This feature rebuilds the Materials UI to exactly match the Ingredients UI structure, ensuring consistent user experience across the application.

**Problem Statement**:
- Current: Single Materials tab with collapsible hierarchy tree and mixed listings
- Target: Separate Materials Catalog, Material Products, and Material Units tabs (3 tabs) with grid views and filters

**Planning Decision**: Per user confirmation during `/spec-kitty.plan`, flat grid views only - no tree/flat toggle required. Hierarchy is displayed via L0/L1 columns in the grid.

**Constraint**: Implementation must copy patterns from `src/ui/ingredients_tab.py` exactly, not invent new approaches.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse and Manage Materials Catalog (Priority: P1)

As a user managing packaging supplies, I want to browse, search, and filter materials in a familiar grid interface so I can quickly find and manage material definitions.

**Why this priority**: Core functionality - users cannot work with materials without a functional catalog view. This matches the primary interaction pattern already learned from Ingredients.

**Independent Test**: Can be fully tested by opening Materials tab, searching/filtering materials, and performing CRUD operations on materials.

**Acceptance Scenarios**:

1. **Given** the Materials tab is open, **When** I view the materials list, **Then** I see a grid with columns for Category (L0), Subcategory (L1), Material Name, and Default Unit
2. **Given** materials exist in the database, **When** I type in the search box, **Then** the grid filters to show only materials matching my search text
3. **Given** materials exist across categories, **When** I select a Category from the L0 dropdown, **Then** the grid shows only materials in that category AND the L1 dropdown populates with subcategories
4. **Given** I have selected an L0 category, **When** I select a Subcategory from the L1 dropdown, **Then** the grid shows only materials in that subcategory
5. **Given** I am viewing filtered results, **When** I click Clear, **Then** all filters reset and I see all materials

---

### User Story 2 - Add and Edit Materials (Priority: P1)

As a user, I want to add new materials and edit existing ones through a form dialog that follows the same pattern as ingredient forms.

**Why this priority**: Essential CRUD operations - users must be able to define their material catalog.

**Independent Test**: Can be tested by clicking Add Material, filling out the form with cascading L0/L1 dropdowns, saving, then editing the created material.

**Acceptance Scenarios**:

1. **Given** I am on the Materials tab, **When** I click "+ Add Material", **Then** a form dialog opens with fields for Name, L0 Category, L1 Subcategory, Default Unit, and Notes
2. **Given** the Add Material dialog is open, **When** I select an L0 category, **Then** the L1 dropdown populates with subcategories for that category
3. **Given** I have filled required fields (Name, Default Unit), **When** I click Save, **Then** the material is created and appears in the grid
4. **Given** a material is selected in the grid, **When** I click Edit (or double-click the row), **Then** the edit dialog opens pre-populated with the material's data
5. **Given** I am editing a material, **When** I click Delete, **Then** I am prompted for confirmation and the material is removed upon confirmation

---

### User Story 3 - Browse and Manage Material Products (Priority: P1)

As a user tracking specific purchased packaging products, I want to view and manage material products (specific brands/SKUs) linked to materials.

**Why this priority**: Users need to track actual purchasable items, not just abstract material definitions. This parallels Products tab for ingredients.

**Independent Test**: Can be tested by opening Material Products tab, filtering by material, viewing inventory levels, and performing CRUD operations.

**Acceptance Scenarios**:

1. **Given** the Material Products tab is open, **When** I view the products list, **Then** I see a grid with columns for Material, Product Name, Inventory, Unit Cost, and Supplier
2. **Given** material products exist, **When** I select a material from the filter dropdown, **Then** the grid shows only products for that material
3. **Given** a product has inventory, **When** I view its row, **Then** the inventory displays with proper formatting (quantity + unit, e.g., "4,724 inches")
4. **Given** a product has cost data, **When** I view its row, **Then** the unit cost displays as currency (e.g., "$0.0016")

---

### User Story 4 - Add and Edit Material Products (Priority: P2)

As a user, I want to add new material products and edit existing ones to track specific brands and packages I purchase.

**Why this priority**: Supports inventory management but depends on materials catalog existing first.

**Independent Test**: Can be tested by clicking Add Product, selecting a material, filling product details, and saving.

**Acceptance Scenarios**:

1. **Given** I am on Material Products tab, **When** I click "+ Add Product", **Then** a form dialog opens with fields for Material, Product Name, Package Quantity, Package Unit, Supplier, SKU, and Notes
2. **Given** the Add Product dialog is open, **When** I select a Material, **Then** the package unit defaults to that material's default unit
3. **Given** I have filled required fields, **When** I click Save, **Then** the product is created and appears in the grid
4. **Given** a product is selected, **When** I click Edit, **Then** the edit dialog opens pre-populated with the product's data

---

### User Story 5 - Record Material Purchases (Priority: P2)

As a user, I want to record purchases of material products to track inventory and costs.

**Why this priority**: Enables inventory tracking but depends on products existing first.

**Independent Test**: Can be tested by selecting a product, clicking Record Purchase, entering purchase details, and verifying inventory updates.

**Acceptance Scenarios**:

1. **Given** a material product is selected, **When** I click "Record Purchase", **Then** a purchase dialog opens with the product pre-selected
2. **Given** the purchase dialog is open, **When** I enter packages purchased and total cost, **Then** the dialog calculates and displays total units and unit cost automatically
3. **Given** I have entered valid purchase details, **When** I click "Record Purchase", **Then** the purchase is recorded and inventory updates
4. **Given** invalid data is entered, **When** I attempt to submit, **Then** validation errors display below the relevant fields

---

### User Story 6 - Adjust Material Inventory (Priority: P3)

As a user, I want to adjust inventory levels directly for corrections, waste, or transfers.

**Why this priority**: Secondary workflow for edge cases; most inventory changes happen via purchases.

**Independent Test**: Can be tested by selecting a product, clicking Adjust Inventory, entering adjustment, and verifying the change.

**Acceptance Scenarios**:

1. **Given** a material product is selected, **When** I click "Adjust Inventory", **Then** an adjustment dialog opens showing current inventory
2. **Given** the adjustment dialog is open, **When** I enter an adjustment amount and reason, **Then** I can submit the adjustment
3. **Given** I submit a valid adjustment, **When** processing completes, **Then** the product's inventory reflects the adjustment

---

### Edge Cases

- What happens when deleting a material that has associated products? System displays error: "Cannot delete [material name]. It has N associated products. Remove products first to delete this material."
- What happens when filtering by a category that has no materials? Grid shows empty state with message "No materials match the current filters."
- How does inventory display when a product has zero inventory? Shows "0" with unit (e.g., "0 inches").
- What happens when recording a purchase with zero packages? Validation prevents submission with field-level error.

## Requirements *(mandatory)*

### Functional Requirements

**Materials Tab Structure**:
- **FR-001**: System MUST display Materials in a grid view with columns: Category (L0), Subcategory (L1), Material Name, Default Unit
- **FR-002**: System MUST provide a search box that filters materials by name in real-time
- **FR-003**: System MUST provide cascading L0/L1 category dropdowns where L1 options depend on selected L0
- **FR-004**: System MUST provide a Level filter dropdown with options: All Levels, Root Categories (L0), Subcategories (L1), Leaf Materials (L2)
- ~~**FR-005**: System MUST provide a Flat/Tree view toggle~~ *[REMOVED: Per planning decision, flat grid views only]*
- **FR-006**: System MUST provide a Clear button that resets all filters to defaults
- **FR-007**: System MUST display a status bar showing count of materials and active filter status
- **FR-008**: System MUST enable Edit button only when a material is selected
- **FR-009**: System MUST open edit dialog on double-click of a grid row

**Material Products Tab Structure**:
- **FR-010**: System MUST display Material Products in a grid with columns: Material, Product Name, Inventory, Unit Cost, Supplier
- **FR-011**: System MUST provide a material filter dropdown to filter products by their linked material
- **FR-012**: System MUST format inventory values with quantity and unit (e.g., "100 each", "4,724 inches")
- **FR-013**: System MUST format unit cost as currency
- **FR-014**: System MUST enable Edit, Record Purchase, and Adjust Inventory buttons only when a product is selected

**Material Form Dialog**:
- **FR-015**: System MUST provide form fields: Name (required), L0 Category, L1 Subcategory (cascading), Default Unit (required), Notes
- **FR-016**: System MUST compute and display the material's level based on parent selection
- **FR-017**: System MUST provide Delete button when editing (not when adding)

**Material Product Form Dialog**:
- **FR-018**: System MUST provide form fields: Material (required), Product Name (required), Package Quantity, Package Unit, Supplier, SKU, Notes

**Record Purchase Dialog**:
- **FR-019**: System MUST auto-calculate total units from (units per package * packages purchased)
- **FR-020**: System MUST auto-calculate unit cost from (total cost / total units)
- **FR-021**: System MUST provide date picker for purchase date defaulting to today
- **FR-022**: System MUST validate all required fields before enabling submit

**Adjust Inventory Dialog**:
- **FR-023**: System MUST display current inventory level
- **FR-024**: System MUST require adjustment amount and reason

**UI Pattern Compliance**:
- **FR-025**: Materials tab MUST use identical widget types as Ingredients tab
- **FR-026**: Materials tab MUST use identical grid configuration as Ingredients tab
- **FR-027**: All dialogs MUST follow the same layout pattern as Ingredient dialogs (label column 120px, input flexible)

### Key Entities

- **Material**: Abstract definition of a packaging material (e.g., "10x10 Window Box"). Has L0/L1/L2 hierarchy, default unit, and notes. Parallel to Ingredient.
- **MaterialProduct**: Specific purchasable product linked to a Material (e.g., "Amazon 10x10 Box 25pk"). Has supplier, SKU, package details, inventory. Parallel to Product.
- **MaterialInventoryLot**: Tracks inventory quantities and costs for material products (existing from F047).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can locate any material within 3 interactions (search, filter, or scroll)
- **SC-002**: Materials tab layout is visually indistinguishable from Ingredients tab layout (same grid config, spacing, widget types)
- **SC-003**: All CRUD operations complete without errors on valid input
- **SC-004**: Users can complete a material purchase recording in under 30 seconds
- **SC-005**: Filter state persists correctly when switching between tabs
- **SC-006**: 100% of acceptance scenarios pass manual testing
- **SC-007**: No regression in existing materials functionality (data remains intact, services work correctly)

## Assumptions

- The existing `material_catalog_service`, `material_product_service`, and `material_unit_service` provide all necessary backend functionality
- `src/ui/ingredients_tab.py` serves as the authoritative reference for UI patterns
- No changes to data models are required - this is UI-only

## Out of Scope

- Import dialog Materials checkbox (already fixed separately)
- Data model changes
- Service layer modifications
- Unit conversion logic changes
