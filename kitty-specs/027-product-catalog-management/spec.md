# Feature Specification: Product Catalog Management

**Feature Branch**: `027-product-catalog-management`
**Created**: 2025-12-22
**Status**: Draft
**Input**: User description: "See docs/design/F027_product_catalog_management.md"

## Problem Statement

Product and inventory management workflows have critical gaps blocking effective user testing:

1. **No standalone product management**: Cannot add products to catalog independently
2. **Forced ingredient-first entry**: Adding inventory blocked if ingredient has no products
3. **No price history**: Cannot track price changes over time (critical for FIFO costing)
4. **No product catalog maintenance**: Cannot hide obsolete products, filter by category/supplier

**User Impact**:
- "I just shopped at Costco with 20 items" results in 40+ minutes of data entry
- Cannot answer "What did I pay for chocolate chips last time?"
- Price volatility (tariffs, inflation) makes cost tracking critical
- Testing blocked: cannot populate inventory without product catalog management

## User Scenarios & Testing

### User Story 1 - View and Search Products (Priority: P1)

As a baker, I want to view all products in a searchable, filterable grid so I can quickly find specific products and see their details.

**Why this priority**: Core foundation - users must be able to see what products exist before any other operations are useful.

**Independent Test**: Can be fully tested by loading the Products tab and verifying products display with correct data; delivers immediate visibility into the product catalog.

**Acceptance Scenarios**:

1. **Given** the Products tab is selected, **When** the tab loads, **Then** all non-hidden products display in a grid showing name, ingredient, category, preferred supplier, last purchase date, and last price.

2. **Given** products exist in the catalog, **When** user types "chocolate" in the search box, **Then** only products with "chocolate" in the name display.

3. **Given** products exist across multiple categories, **When** user selects "Dairy" from the Category filter, **Then** only products linked to dairy ingredients display.

4. **Given** hidden products exist, **When** user checks "Show Hidden", **Then** hidden products appear with visual distinction (grayed out).

---

### User Story 2 - Add New Products (Priority: P1)

As a baker, I want to add new products to the catalog so I can track items I purchase from stores.

**Why this priority**: Without adding products, the catalog cannot grow and inventory tracking remains blocked.

**Independent Test**: Can be tested by clicking "Add Product", filling the form, and verifying the product appears in the grid.

**Acceptance Scenarios**:

1. **Given** the Products tab is displayed, **When** user clicks "Add Product", **Then** a dialog opens with fields for brand/name, ingredient selection, package unit, package quantity, and optional preferred supplier.

2. **Given** the Add Product dialog is open, **When** user fills all required fields and clicks Save, **Then** the product is created and appears in the grid.

3. **Given** the Add Product dialog is open, **When** user selects an ingredient, **Then** the ingredient category is automatically determined from the selection.

4. **Given** the Add Product dialog is open, **When** user leaves required fields empty and clicks Save, **Then** validation errors display and the product is not created.

---

### User Story 3 - Manage Suppliers (Priority: P1)

As a baker, I want to track which stores I purchase from so I can see price history by supplier and set preferred suppliers for products.

**Why this priority**: Suppliers are required for purchase tracking; without them, price history cannot be recorded.

**Independent Test**: Can be tested by adding a supplier and verifying it appears in supplier dropdowns throughout the app.

**Acceptance Scenarios**:

1. **Given** the user needs to add a new supplier, **When** they access supplier management, **Then** they can enter name, city, state, and zip code (street address optional).

2. **Given** suppliers exist, **When** viewing the supplier list, **Then** suppliers display with name and location (e.g., "Costco (Waltham, MA)").

3. **Given** a supplier has purchase history, **When** user attempts to delete the supplier, **Then** deletion is blocked and user is offered to deactivate instead.

4. **Given** a supplier is deactivated, **When** viewing product dropdowns, **Then** the deactivated supplier does not appear as an option.

---

### User Story 4 - View Product Details and Purchase History (Priority: P2)

As a baker, I want to see a product's purchase history so I can understand price trends and where I typically buy items.

**Why this priority**: Builds on P1 foundation; provides value once products and suppliers exist.

**Independent Test**: Can be tested by double-clicking a product with purchase history and verifying the detail view shows historical purchases.

**Acceptance Scenarios**:

1. **Given** a product exists with purchase history, **When** user double-clicks the product row, **Then** a detail view opens showing all purchases sorted by date (newest first).

2. **Given** the product detail view is open, **When** viewing purchase history, **Then** each entry shows date, supplier, unit price, and quantity purchased.

3. **Given** a product exists without purchase history, **When** viewing the detail view, **Then** an appropriate message indicates no purchase history exists.

---

### User Story 5 - Edit Products (Priority: P2)

As a baker, I want to edit product details so I can correct mistakes or update information as products change.

**Why this priority**: Enables maintenance of product data after initial entry.

**Independent Test**: Can be tested by editing a product's name and verifying the change persists.

**Acceptance Scenarios**:

1. **Given** the product detail view is open, **When** user clicks "Edit", **Then** product fields become editable.

2. **Given** product fields are being edited, **When** user changes the preferred supplier and saves, **Then** the change persists and displays on the grid.

3. **Given** product fields are being edited, **When** user clears a required field and saves, **Then** validation prevents the save.

---

### User Story 6 - Hide and Unhide Products (Priority: P2)

As a baker, I want to hide products I no longer use so they don't clutter my catalog, while preserving their history.

**Why this priority**: Catalog maintenance for long-term usability; lower priority than core CRUD.

**Independent Test**: Can be tested by hiding a product and verifying it disappears from the default view but remains accessible via "Show Hidden".

**Acceptance Scenarios**:

1. **Given** a product with purchase history exists, **When** user clicks "Hide", **Then** the product is marked hidden and disappears from the default grid view.

2. **Given** a hidden product is visible (via Show Hidden checkbox), **When** user clicks "Unhide", **Then** the product returns to normal visibility.

3. **Given** a product exists with no purchase history or inventory, **When** user clicks "Delete", **Then** the product is permanently removed.

4. **Given** a product exists with purchase history, **When** user attempts to delete, **Then** deletion is blocked and user is prompted to hide instead.

---

### User Story 7 - Track Purchases When Adding Inventory (Priority: P3)

As a baker, when I add items to inventory, I want the purchase details (supplier, price, date) recorded so I can track costs accurately.

**Why this priority**: Connects to existing inventory workflow; requires all P1/P2 foundations in place.

**Independent Test**: Can be tested by adding an inventory item and verifying a corresponding purchase record is created.

**Acceptance Scenarios**:

1. **Given** user is adding an inventory item, **When** they complete the form with supplier and price, **Then** a Purchase record is created linking product, supplier, date, and price.

2. **Given** a purchase record exists, **When** viewing the product's purchase history, **Then** the purchase appears in the list.

3. **Given** multiple inventory items are added from the same shopping trip, **When** viewing purchase records, **Then** each addition has its own purchase record with the appropriate details.

---

### Edge Cases

- What happens when a product's ingredient is the only reference and user tries to delete the ingredient? (Block deletion)
- How does the system handle duplicate product names for the same ingredient? (Allow - differentiated by brand/package)
- What happens when filtering by supplier and that supplier is later deactivated? (Filter resets to "All")
- How does search handle special characters? (Escape and match literally)
- What happens when the last active supplier is deactivated? (Allow - products can exist without preferred supplier)

## Requirements

### Functional Requirements

**Product Management:**
- **FR-001**: System MUST allow creation of products with brand/name, ingredient reference, package unit, and package quantity
- **FR-002**: System MUST allow optional preferred supplier assignment to products
- **FR-003**: System MUST support hiding products (soft delete) to preserve purchase history
- **FR-004**: System MUST prevent deletion of products that have purchase history
- **FR-005**: System MUST allow permanent deletion of products without dependencies
- **FR-006**: System MUST display products in a filterable, searchable grid view

**Supplier Management:**
- **FR-007**: System MUST allow creation of suppliers with name, city, state, and zip code
- **FR-008**: System MUST support deactivating suppliers (soft delete) to preserve purchase history
- **FR-009**: System MUST clear preferred_supplier_id on products when their supplier is deactivated
- **FR-010**: System MUST prevent display of inactive suppliers in selection dropdowns

**Purchase Tracking:**
- **FR-011**: System MUST create a Purchase record when inventory is added, capturing product, supplier, date, unit price, and quantity
- **FR-012**: System MUST display purchase history for each product sorted by date (newest first)
- **FR-013**: System MUST calculate and display the most recent purchase price for each product

**Filtering and Search:**
- **FR-014**: System MUST allow filtering products by ingredient
- **FR-015**: System MUST allow filtering products by ingredient category
- **FR-016**: System MUST allow filtering products by preferred supplier
- **FR-017**: System MUST allow searching products by name (case-insensitive partial match)
- **FR-018**: System MUST allow toggling visibility of hidden products

**Data Integrity:**
- **FR-019**: System MUST enforce referential integrity between purchases, products, and suppliers
- **FR-020**: System MUST use ON DELETE RESTRICT for purchases referencing products and suppliers
- **FR-021**: System MUST use ON DELETE SET NULL for product preferred_supplier_id

### Key Entities

- **Product**: Represents a specific purchasable item (brand + package size) linked to an Ingredient. Has optional preferred supplier and hidden status.

- **Supplier**: Represents a store or vendor location where products are purchased. Identified by name + city + state. Has active/inactive status.

- **Purchase**: Represents a shopping transaction recording when a product was bought from a supplier at a specific price. Immutable after creation. Links to inventory additions for FIFO costing.

- **InventoryAddition** (modified): Now references a Purchase record instead of storing price directly. This centralizes price data and enables purchase history queries.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can add a new product to the catalog in under 30 seconds
- **SC-002**: Users can find a specific product using search in under 5 seconds
- **SC-003**: Users can view a product's complete purchase history in 2 clicks from the main grid
- **SC-004**: 100% of inventory additions create corresponding purchase records
- **SC-005**: Hidden products do not appear in default product views or selection dropdowns
- **SC-006**: Service layer test coverage for new product and supplier services exceeds 70%
- **SC-007**: All existing tests pass after migration with zero data loss
- **SC-008**: Data migration successfully transforms existing inventory additions to purchase records

## Assumptions

1. **Single-user desktop context**: No concurrent access concerns; SQLite locking sufficient
2. **US-based suppliers**: State field uses 2-letter codes; ZIP code format is US standard
3. **Unknown supplier for migration**: Historical inventory additions will be assigned to a placeholder "Unknown" supplier during migration
4. **One purchase per inventory addition**: Each inventory addition creates exactly one purchase record (no bulk purchase splitting)
5. **Preferred supplier auto-set deferred**: Auto-setting preferred supplier from first purchase is out of scope (Feature 029)

## Dependencies

- **Existing Models**: Product, Ingredient, InventoryAddition (will be modified)
- **Existing Services**: inventory_service (will be updated to create Purchase records)
- **Schema Migration**: Requires export/reset/import cycle per Constitution VI
- **Features 028-029**: This feature is foundation; subsequent features will build on these entities

## Out of Scope

- Inventory addition workflow changes (Feature 029)
- Price suggestion UI (Feature 029)
- Inline product creation during inventory addition (Feature 029)
- Supplier-based shopping list grouping (future)
- Receipt scanning/OCR integration (future)
- Multi-supplier price comparison views (future)
