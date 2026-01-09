# Feature Specification: Purchases Tab with CRUD Operations

**Feature Branch**: `043-purchases-tab-crud-operations`
**Created**: 2026-01-08
**Status**: Draft
**Input**: User description: "See docs/design/F043_purchases_tab_implementation.md"

## Clarifications

### Session 2026-01-08

- Q: Should quantity field accept only whole numbers or decimals? → A: Allow one decimal place for loose/bulk goods
- Q: What should the default date range filter be? → A: Default to "Last 30 days"

## Overview

Implement a Purchases tab in PURCHASE mode as the **primary data entry point** for recording purchases. This establishes the correct architectural flow where Purchases drive Inventory (not vice versa), enables purchase history browsing with FIFO tracking, and provides full CRUD operations for managing purchase records.

**Problem Being Solved**: Users currently add purchases via the Inventory tab's "Add to Pantry" dialog, which obscures the Purchase-to-Inventory relationship. There is no way to view purchase history, track spending, or edit/delete past purchases.

**Value Delivered**:
- Primary workflow for recording purchases
- Purchase history with filtering and search
- Ability to correct errors (edit) and remove duplicates (delete)
- FIFO-aware remaining inventory tracking
- Foundation for AI-assisted purchase entry (BT Mobile, voice)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Purchase History (Priority: P1)

User wants to see all their purchases to track spending and verify what was bought.

**Why this priority**: Without the ability to view purchases, no other functionality matters. This is the foundation that makes the tab useful.

**Independent Test**: Can be fully tested by navigating to Purchases tab and verifying the list displays existing purchases with all columns (date, product, supplier, qty, price, total, remaining).

**Acceptance Scenarios**:

1. **Given** purchases exist in the database, **When** user opens PURCHASE mode and clicks Purchases tab, **Then** purchases display in descending date order with all columns visible
2. **Given** the Purchases tab is open, **When** user scrolls the list, **Then** at least 20 rows are visible without horizontal scrolling
3. **Given** purchases exist, **When** user clicks a column header, **Then** the list sorts by that column

---

### User Story 2 - Filter Purchase History (Priority: P1)

User wants to filter purchases by date range, supplier, or product name to find specific purchases quickly.

**Why this priority**: With potentially hundreds of purchases, filtering is essential for usability. Combined with User Story 1, this forms the minimum viable tab.

**Independent Test**: Can be tested by applying each filter type and verifying the list updates to show only matching purchases.

**Acceptance Scenarios**:

1. **Given** purchases from multiple dates exist, **When** user selects "Last 30 days" from date range dropdown, **Then** only purchases within the last 30 days display
2. **Given** purchases from multiple suppliers exist, **When** user selects a specific supplier, **Then** only purchases from that supplier display
3. **Given** purchases for various products exist, **When** user types a product name in the search box, **Then** only purchases matching that product display (fuzzy match)
4. **Given** filters are applied, **When** user changes a filter, **Then** the list updates immediately (under 200ms perceived)

---

### User Story 3 - Add New Purchase (Priority: P1)

User returns from a shopping trip and needs to record what they bought. The system should create both the purchase record and update inventory automatically.

**Why this priority**: Data entry is the core purpose of the Purchases tab. Without this, the tab is read-only and doesn't establish the Purchase-to-Inventory workflow.

**Independent Test**: Can be tested by adding a purchase and verifying both the purchase appears in the list and the inventory increases accordingly.

**Acceptance Scenarios**:

1. **Given** user is on Purchases tab, **When** user clicks "Add Purchase", **Then** the Add Purchase dialog opens
2. **Given** the Add Purchase dialog is open, **When** user selects a product, **Then** the unit price auto-fills from the most recent purchase of that product
3. **Given** the Add Purchase dialog is open, **When** user selects a product with a preferred supplier, **Then** the supplier dropdown defaults to that preferred supplier
4. **Given** all required fields are filled (product, date, quantity, price, supplier), **When** user clicks "Add Purchase", **Then** a purchase record is created AND an inventory item is created AND the list refreshes to show the new purchase
5. **Given** the Add Purchase dialog is open, **When** user enters a future date, **Then** validation prevents saving with an error message
6. **Given** the Add Purchase dialog is open, **When** user enters quantity of 0 or negative, **Then** validation prevents saving with an error message

---

### User Story 4 - Edit Purchase to Fix Errors (Priority: P2)

User made a typo when entering a purchase (wrong price, date, or quantity) and needs to correct it.

**Why this priority**: Errors happen. Without edit capability, users must delete and re-enter, which is cumbersome and may not be possible if inventory was consumed.

**Independent Test**: Can be tested by editing a purchase's price and verifying the change persists and FIFO costs update if applicable.

**Acceptance Scenarios**:

1. **Given** a purchase exists, **When** user right-clicks and selects "Edit" (or double-clicks), **Then** the Edit Purchase dialog opens with fields pre-filled
2. **Given** the Edit Purchase dialog is open, **When** user views the product field, **Then** it is read-only (cannot change product)
3. **Given** a purchase with no consumption, **When** user changes the quantity, **Then** the change saves successfully and inventory updates
4. **Given** a purchase where 5 units were consumed, **When** user tries to reduce quantity below 5, **Then** validation blocks with message explaining the consumed amount
5. **Given** the Edit Purchase dialog is open, **When** user changes the unit price, **Then** FIFO unit costs are recalculated for remaining inventory

---

### User Story 5 - Delete Duplicate or Erroneous Purchase (Priority: P2)

User accidentally entered the same purchase twice or entered a completely wrong purchase and needs to remove it.

**Why this priority**: Data integrity requires the ability to remove mistakes. Blocking deletion of consumed purchases protects FIFO accuracy.

**Independent Test**: Can be tested by attempting to delete both a consumed and unconsumed purchase, verifying the correct behavior for each.

**Acceptance Scenarios**:

1. **Given** a purchase with no inventory consumption, **When** user clicks "Delete" and confirms, **Then** the purchase is removed AND the linked inventory item is removed AND the list refreshes
2. **Given** a purchase where some inventory was consumed in production, **When** user clicks "Delete", **Then** an error dialog displays explaining why deletion is blocked (shows consumed quantity and which recipes used it)
3. **Given** deletion is allowed, **When** user clicks "Delete", **Then** a confirmation dialog appears showing what will be deleted before proceeding
4. **Given** confirmation dialog is shown, **When** user clicks "Cancel", **Then** no deletion occurs

---

### User Story 6 - View Purchase Details and Usage History (Priority: P3)

User wants to see detailed information about a specific purchase, including how much inventory remains and what recipes consumed it.

**Why this priority**: Useful for understanding FIFO tracking and spending analysis, but not essential for core CRUD operations.

**Independent Test**: Can be tested by opening details for a partially-consumed purchase and verifying usage history displays correctly.

**Acceptance Scenarios**:

1. **Given** a purchase exists, **When** user right-clicks and selects "View Details", **Then** the Purchase Details dialog opens showing purchase information
2. **Given** the Purchase Details dialog is open, **When** viewing inventory tracking section, **Then** it shows original quantity, used quantity, and remaining quantity
3. **Given** inventory from this purchase was consumed in production runs, **When** viewing usage history, **Then** each consumption shows date, recipe name, quantity used, and cost
4. **Given** the Purchase Details dialog is open, **When** user clicks "Edit Purchase", **Then** the Edit Purchase dialog opens

---

### Edge Cases

- What happens when no purchases exist? Display empty state with guidance to add first purchase
- What happens when filters return no results? Display "No purchases match your filters" message
- What happens when product has no previous purchases? Unit price field starts empty, user must enter
- What happens when product has no preferred supplier? Supplier dropdown shows all suppliers, no default
- How does system handle very long product names in the list? Truncate with ellipsis, show full name on hover
- What happens if database error occurs during save? Show error message, do not close dialog, allow retry
- How does delete cascade work? Deleting purchase removes linked inventory items (enforced by foreign key)

## Requirements *(mandatory)*

### Functional Requirements

**Purchase List View**

- **FR-001**: System MUST display purchases in descending date order by default
- **FR-002**: System MUST show columns: Date, Product, Supplier, Quantity, Unit Price, Total Cost, Remaining Inventory
- **FR-003**: System MUST display at least 20 rows visible without scrolling (grid expands to fill 70-80% vertical space)
- **FR-004**: System MUST support column sorting by clicking column headers

**Filters**

- **FR-005**: System MUST provide date range filter with options: Last 30 days (default), Last 90 days, Last year, All time
- **FR-006**: System MUST provide supplier filter dropdown showing all suppliers plus "All" option
- **FR-007**: System MUST provide search box that filters by product name with fuzzy matching
- **FR-008**: System MUST update the list immediately when any filter changes

**Add Purchase**

- **FR-009**: System MUST provide "Add Purchase" button that opens the Add Purchase dialog
- **FR-010**: Add Purchase dialog MUST require: product selection, purchase date, quantity, unit price, supplier
- **FR-011**: System MUST auto-fill unit price from the most recent purchase of the selected product
- **FR-012**: System MUST default supplier to the product's preferred_supplier when available
- **FR-013**: System MUST validate: date is not in the future, quantity is greater than 0 (one decimal place allowed for loose/bulk goods), price is non-negative
- **FR-014**: System MUST create both Purchase and InventoryItem records atomically on save
- **FR-015**: System MUST refresh the purchase list after successful save

**Edit Purchase**

- **FR-016**: Edit Purchase dialog MUST allow editing: date, quantity, price, supplier, notes
- **FR-017**: Edit Purchase dialog MUST display product as read-only (cannot be changed)
- **FR-018**: System MUST validate that new quantity is not less than already-consumed quantity
- **FR-019**: System MUST recalculate FIFO unit costs when price or quantity changes
- **FR-020**: Edit dialog MUST show preview of changes before saving

**Delete Purchase**

- **FR-021**: System MUST block deletion if any inventory from the purchase has been consumed
- **FR-022**: System MUST show confirmation dialog before deleting an allowed purchase
- **FR-023**: System MUST show error dialog with specific usage details when deletion is blocked
- **FR-024**: Delete MUST cascade to remove linked InventoryItem records
- **FR-025**: System MUST refresh the purchase list after successful deletion

**View Details**

- **FR-026**: View Details dialog MUST show purchase information (date, supplier, price, notes)
- **FR-027**: View Details dialog MUST show inventory tracking: original, used, remaining quantities
- **FR-028**: View Details dialog MUST show usage history listing each consumption with date, recipe, quantity, cost
- **FR-029**: View Details dialog MUST provide quick action button to open Edit Purchase

### Key Entities

- **Purchase**: Transaction record capturing when, what, and how much was bought. Links to Product (what was bought) and Supplier (where it was bought). Contains purchase_date, quantity_purchased, unit_price, and optional notes.

- **InventoryItem**: Current state of inventory from a purchase. Links to Purchase (source) and Ingredient (generic item). Tracks current_quantity (remaining after FIFO consumption), unit, and unit_cost.

- **InventoryDepletion**: Record of inventory consumption. Links to InventoryItem and ProductionRun. Tracks quantity_depleted for FIFO accuracy. Used to determine if a purchase can be edited/deleted.

- **Product**: Specific brand/package of an ingredient. Contains display_name, package_unit_quantity, package_unit, and preferred_supplier.

- **Supplier**: Store or vendor where products are purchased. Contains name and optional location.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can view their complete purchase history with all relevant details visible in the list
- **SC-002**: Users can find a specific purchase using filters within 10 seconds (date range, supplier, or product search)
- **SC-003**: Users can add a new purchase and see it appear in the list within 5 seconds of clicking save
- **SC-004**: Users can correct a purchase error (typo in price/quantity) without needing to delete and re-enter
- **SC-005**: System prevents accidental data corruption by blocking deletion of consumed purchases
- **SC-006**: Users receive clear, actionable error messages when operations cannot be completed
- **SC-007**: The Purchases tab becomes the primary entry point for recording purchases (replacing Inventory tab's "Add to Pantry" as the recommended workflow)
- **SC-008**: Purchase list loads and displays within 1 second for databases with up to 500 purchases
- **SC-009**: Filter changes reflect in the list within 500 milliseconds

## Assumptions

- The existing Purchase and InventoryItem models from F028 are complete and sufficient (no schema changes needed)
- The existing PurchaseService has create_purchase, update_purchase, and delete_purchase methods that can be extended
- The UI patterns established in F042 (header + filters + expandable grid) will be followed
- The "Add to Pantry" dialog in Inventory tab will remain as a secondary entry point (not removed)
- TypeAheadComboBox or similar component exists or can be created for product selection

## Out of Scope

- Multi-item purchase entry (adding multiple products in one dialog) - planned for F043.5
- Quick re-order functionality - planned for F044
- Price trend analysis and alerts
- Budget tracking and spending reports
- CSV export functionality
- Receipt photo attachment
