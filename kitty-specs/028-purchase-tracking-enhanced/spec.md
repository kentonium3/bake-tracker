# Feature Specification: Purchase Tracking & Enhanced Costing

**Feature Branch**: `028-purchase-tracking-enhanced`
**Created**: 2025-12-22
**Status**: Draft
**Input**: User description: "Feature 028: Purchase Tracking & Enhanced Costing - Implement Purchase entity as first-class transaction record linking products to suppliers with temporal pricing context."

## Problem Statement

Current inventory management lacks purchase transaction tracking, preventing accurate cost analysis and price history:

1. **No purchase history**: Cannot answer "What did I pay for chocolate chips last time?"
2. **No supplier tracking**: Cannot determine "Do I usually buy this at Costco or Wegmans?"
3. **Static price data**: InventoryAddition.price_paid is a snapshot with no context (when, where, market conditions)
4. **FIFO accuracy limited**: Cost calculations use addition price, not purchase transaction context
5. **Price volatility invisible**: Price changes over time (e.g., $300 to $600 for chocolate) not tracked

**Real-World Example**: Marianne buys chocolate chips at Costco in January ($300), June ($450), December ($600). Current system treats each as an isolated addition. Cannot see: price trend, supplier consistency, or whether December price is a market change vs data entry error.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Add Inventory with Supplier Selection (Priority: P1)

When adding inventory, the user selects which supplier (store) they purchased the item from. The system records this as a purchase transaction linked to the inventory addition.

**Why this priority**: This is the core data capture mechanism. Without supplier selection during inventory addition, no purchase history can be built. All other features depend on this.

**Independent Test**: Can be fully tested by adding inventory through the dialog with supplier selection and verifying the Purchase record is created in the database with correct supplier linkage.

**Acceptance Scenarios**:

1. **Given** the Add Inventory dialog is open and a product is selected, **When** the user selects a supplier from the dropdown, **Then** the supplier dropdown shows all suppliers alphabetically sorted by name.
2. **Given** the user has selected a product and supplier, **When** the user enters price and quantity and clicks Add, **Then** a Purchase record is created linking product, supplier, date, price, and quantity.
3. **Given** the user has not selected a supplier, **When** the user clicks Add, **Then** validation prevents submission with a clear error message.

---

### User Story 2 - Price Suggestion from Purchase History (Priority: P1)

When the user selects a product and supplier, the system suggests the last paid price at that supplier. If no history exists at that supplier, it falls back to showing the last price paid at any supplier.

**Why this priority**: Price suggestion reduces data entry errors and speeds up the workflow. It provides immediate value feedback from purchase history.

**Independent Test**: Can be tested by adding multiple purchases at different prices/suppliers, then verifying price pre-fill behavior when adding new inventory.

**Acceptance Scenarios**:

1. **Given** a product was previously purchased at Costco for $8.99, **When** the user selects that product and Costco as supplier, **Then** the price field pre-fills with $8.99 and shows hint "(last paid: $8.99 on YYYY-MM-DD)".
2. **Given** a product was purchased at Costco but user selects Wegmans (no history), **When** the supplier is selected, **Then** the price field pre-fills with the Costco price and shows hint "(last paid: $8.99 at Costco on YYYY-MM-DD)".
3. **Given** a product has no purchase history at any supplier, **When** the user selects any supplier, **Then** the price field remains blank and shows hint "(no purchase history)".

---

### User Story 3 - Accurate FIFO Cost Calculation (Priority: P1)

When producing recipes that consume inventory, the system calculates ingredient costs using the actual purchase price paid for each unit consumed, following FIFO (First In, First Out) order.

**Why this priority**: FIFO accuracy is a core principle of the application. Linking costs to purchase transactions ensures accurate cost-of-goods calculations.

**Independent Test**: Can be tested by adding inventory at different prices over time, then producing a recipe and verifying the cost calculation uses the correct FIFO prices from Purchase records.

**Acceptance Scenarios**:

1. **Given** inventory was added: 10 units at $5.00 (Jan), then 10 units at $6.00 (Feb), **When** a recipe consumes 15 units, **Then** cost is calculated as (10 x $5.00) + (5 x $6.00) = $80.00.
2. **Given** an inventory addition exists with a linked Purchase record, **When** FIFO consumption occurs, **Then** the cost is retrieved from Purchase.unit_price (not a deprecated price_paid field).

---

### User Story 4 - Purchase History Query (Priority: P2)

Users can query purchase history for a product to see price trends over time and across suppliers.

**Why this priority**: Enables informed purchasing decisions but not required for basic inventory operations.

**Independent Test**: Can be tested by creating multiple purchases for a product and verifying history queries return correct results sorted by date.

**Acceptance Scenarios**:

1. **Given** a product has been purchased 5 times at various prices, **When** purchase history is queried, **Then** results are returned sorted by date (most recent first).
2. **Given** purchases exist at multiple suppliers, **When** history is filtered by supplier, **Then** only purchases from that supplier are returned.

---

### User Story 5 - Data Migration from Existing Inventory (Priority: P1)

Existing inventory additions are migrated to have linked Purchase records, preserving all historical price data.

**Why this priority**: Without migration, existing data would be orphaned. The system must maintain data integrity through the transition.

**Independent Test**: Can be tested by running migration on a database with existing InventoryAdditions and verifying each has a corresponding Purchase record.

**Acceptance Scenarios**:

1. **Given** existing InventoryAddition records with price_paid values, **When** migration runs, **Then** one Purchase record is created per InventoryAddition with matching price, quantity, and date.
2. **Given** no supplier information exists for historical data, **When** migration runs, **Then** all migrated Purchases are assigned to "Unknown Supplier".
3. **Given** migration completes, **When** the system queries inventory costs, **Then** FIFO calculations work correctly using migrated Purchase records.

---

### Edge Cases

- **Zero-price purchases**: User enters $0.00 (donation, free sample). System allows with confirmation warning.
- **Negative price attempted**: User enters negative price. System rejects with validation error.
- **Missing supplier**: User tries to add inventory without selecting supplier. System prevents submission.
- **Product deleted with purchase history**: Purchases reference products with RESTRICT delete - cannot delete product with purchase history.
- **Supplier deleted with purchase history**: Purchases reference suppliers with RESTRICT delete - cannot delete supplier with purchase history.
- **Multiple purchases same day**: System handles multiple purchases of same product at same supplier on same day as separate transactions.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST create a Purchase record for every inventory addition, linking product, supplier, date, price, and quantity.
- **FR-002**: System MUST require supplier selection when adding inventory (no default, no blank allowed).
- **FR-003**: System MUST display suppliers in alphabetical order (by name, then city, then state) in the selection dropdown.
- **FR-004**: System MUST suggest the last paid price when a product/supplier combination is selected.
- **FR-005**: System MUST fall back to showing last price from any supplier when no history exists at the selected supplier.
- **FR-006**: System MUST display price hints showing last paid price, date, and supplier context.
- **FR-007**: System MUST allow $0.00 prices with a confirmation warning dialog.
- **FR-008**: System MUST reject negative prices with a validation error.
- **FR-009**: System MUST calculate FIFO costs using Purchase.unit_price via the InventoryAddition.purchase relationship.
- **FR-010**: System MUST prevent deletion of Products or Suppliers that have associated Purchase records.
- **FR-011**: System MUST migrate existing InventoryAddition records to have linked Purchase records.
- **FR-012**: System MUST assign migrated Purchases to "Unknown Supplier" (created in F027).
- **FR-013**: System MUST default purchase_date to today when not explicitly provided.
- **FR-014**: System MUST store user notes on InventoryAddition (Purchase.notes remains unused in this feature).
- **FR-015**: System MUST maintain 1:1 relationship between Purchase and InventoryAddition (one purchase creates one addition).

### Key Entities

- **Purchase**: A transaction record capturing when a product was bought, from which supplier, at what price, and in what quantity. Immutable after creation (no updated_at). Links to Product and Supplier. Primary source of cost data for FIFO calculations.

- **InventoryAddition** (Modified): Now references a Purchase record via purchase_id FK. The price_paid field is deprecated and removed after migration. Quantity matches the linked Purchase.quantity_purchased.

- **Supplier** (From F027): Store/vendor where purchases are made. Already exists with "Unknown Supplier" as migration fallback.

- **Product** (Existing): Specific branded/packaged item. Now has relationship to Purchase records.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every new inventory addition creates a linked Purchase record (100% linkage rate).
- **SC-002**: Price suggestions appear within 1 second of supplier selection.
- **SC-003**: Users can identify price trends by viewing purchase history sorted by date.
- **SC-004**: FIFO cost calculations produce correct results using purchase prices (validated by test suite achieving >70% coverage on service layer).
- **SC-005**: Migration preserves all existing inventory data with zero data loss (validated by comparing record counts pre/post migration).
- **SC-006**: All existing application tests continue to pass after migration.
- **SC-007**: User can complete inventory addition with supplier selection in under 30 seconds (comparable to current workflow plus one dropdown selection).

---

## Scope Boundaries

### In Scope (F028)

- Purchase table and InventoryAddition.purchase_id FK
- purchase_service.py with CRUD and price queries
- Supplier dropdown in Add Inventory dialog
- Price suggestion with hints
- FIFO cost calculation update
- Data migration for existing records

### Out of Scope (Deferred to F029 - Workflow Intelligence)

- Session-based supplier memory ("last used: Costco")
- Price variance alerts (warning when price differs significantly)
- Purchase.notes field usage
- Bulk purchase entry ("I bought 5 bags at once")
- Smart supplier defaults (preferred supplier auto-selection)
- Purchase date picker (override today default)
- Purchase editing/deletion

---

## Assumptions

1. **F027 Complete**: Supplier table exists with "Unknown Supplier" (id=1) already created.
2. **Single User**: No concurrent editing concerns for purchase records.
3. **Desktop Context**: UI patterns follow CustomTkinter conventions.
4. **Notes Location**: User-entered notes are stored on InventoryAddition, not Purchase (confirmed).
5. **Migration Strategy**: Uses export/reset/import cycle per Constitution VI (no in-place ALTER TABLE).

---

## Dependencies

- **Feature 027**: Product Catalog Management - provides Supplier table and "Unknown Supplier" fallback
- **Existing Infrastructure**: inventory_service.py, batch_production_service.py (FIFO logic), Add Inventory dialog

---

## Risks

1. **Migration Data Integrity**: If price_paid is NULL on existing records, migration fails. Mitigation: Validation script checks before migration.
2. **UI Complexity**: Adding supplier dropdown increases cognitive load. Mitigation: Price suggestions provide immediate value; F029 adds session memory.
3. **Historical Accuracy**: Migrated purchases lose supplier context. Mitigation: Accepted tradeoff; forward-looking data captures full context.
