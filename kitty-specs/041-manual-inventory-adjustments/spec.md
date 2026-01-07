# Feature Specification: Manual Inventory Adjustments

**Feature Branch**: `041-manual-inventory-adjustments`
**Created**: 2026-01-07
**Status**: Draft
**Input**: User description: "Manual adjustment interface for inventory items supporting both additions and depletions. Depletions handle spoilage, gifts, corrections, ad hoc usage. Additions handle found inventory with smart defaults. Low friction UX with live preview."
**Reference**: `docs/design/_F041_manual_inventory_adjust.md`

## Clarifications

### Session 2026-01-07

- Q: When adding found inventory, should the product selection include only products already in inventory, any product from catalog, or allow inline product creation? → A: Any product from the product catalog (including those with no current inventory). Inventory adjustment workflow remains distinct from purchasing workflow where new products are added to catalog.

## Problem Statement

Inventory records drift from physical reality over time because the system only tracks automatic depletions (production/assembly). Real-world changes occur outside the application:

- **Spoilage**: Ingredients go bad and must be discarded
- **Gifts**: Ingredients given to friends/family
- **Corrections**: Physical count doesn't match system records
- **Ad hoc usage**: Testing recipes, personal consumption outside app
- **Found inventory**: Discovering inventory not previously recorded

Without manual adjustments, users discover shortfalls during production ("System says I have 10 cups flour, but I only have 5") or miss inventory they actually have.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record Spoilage (Priority: P1)

User discovers ingredients have spoiled (mold, weevils, expiration) and must discard them. They need to reduce inventory to match reality.

**Why this priority**: Spoilage is the most common reason for inventory adjustments. Without this, planning becomes unreliable and production fails unexpectedly.

**Independent Test**: Can be fully tested by selecting an inventory item, entering a depletion amount with "Spoilage" reason, and verifying quantity updates correctly.

**Acceptance Scenarios**:

1. **Given** user has 10 cups of flour in inventory, **When** user opens adjustment dialog, enters 5 cups reduction with "Spoilage" reason and note "Weevils discovered", **Then** inventory shows 5 cups remaining and depletion history shows the adjustment with reason and notes.

2. **Given** user has 3 cups of an ingredient, **When** user attempts to deplete 5 cups, **Then** system shows validation error "Cannot reduce by more than available quantity" and prevents the adjustment.

---

### User Story 2 - Physical Count Correction (Priority: P2)

User performs physical inventory count and finds discrepancy between system and reality. They need to correct inventory up or down to match the physical count.

**Why this priority**: Physical count corrections maintain long-term inventory accuracy. Supports both increases (system too low) and decreases (system too high).

**Independent Test**: Can test by adjusting inventory in either direction and verifying the correction is recorded with appropriate audit trail.

**Acceptance Scenarios**:

1. **Given** system shows 10 cups sugar but physical count is 7, **When** user reduces by 3 cups with "Physical Count Correction" reason, **Then** inventory shows 7 cups and history shows correction.

2. **Given** system shows 5 cups butter but physical count is 8, **When** user adds 3 cups with "Physical Count Correction" reason, **Then** inventory shows 8 cups with new inventory record using default values (today's date, last purchase price).

---

### User Story 3 - Record Gift or Donation (Priority: P3)

User gave ingredients to friend or family member. They need to record this depletion to keep inventory accurate.

**Why this priority**: Gifts are occasional but important for accuracy. Also useful for potential tax tracking of charitable donations.

**Independent Test**: Can test by depleting inventory with "Gift" reason and verifying depletion record captures the context.

**Acceptance Scenarios**:

1. **Given** user has 6 cups chocolate chips, **When** user depletes 2 cups with "Gift" reason and note "Gave to neighbor for cookies", **Then** inventory shows 4 cups and history shows gift with notes.

---

### User Story 4 - Add Found Inventory (Priority: P4)

User discovers inventory that wasn't in the system (found in back of pantry, received as gift, etc.). They need to add it with minimal data entry.

**Why this priority**: Less common than depletions but necessary for complete inventory accuracy. Must be low friction.

**Independent Test**: Can test by adding inventory with defaults and verifying sensible values are applied automatically.

**Acceptance Scenarios**:

1. **Given** user finds 2 cups of cocoa powder not currently in inventory, **When** user adds inventory by selecting cocoa powder from the product catalog, **Then** system creates inventory record with today's date, last purchase price (or $0 if none), and optional supplier.

2. **Given** user adds found inventory, **When** user wants to specify a different date or price, **Then** user can override defaults before saving.

---

### User Story 5 - Ad Hoc Usage Tracking (Priority: P5)

User consumed ingredients outside the app (testing recipes, personal use) and needs to record the depletion.

**Why this priority**: Enables complete tracking but is less critical than spoilage/corrections.

**Independent Test**: Can test by depleting with "Ad Hoc Usage" reason.

**Acceptance Scenarios**:

1. **Given** user used 2 eggs testing a recipe outside the app, **When** user depletes with "Ad Hoc Usage" reason, **Then** inventory reflects the usage.

---

### Edge Cases

- **Zero quantity**: What happens when adjustment would result in exactly zero? (Allowed - inventory item remains with 0 quantity)
- **No previous purchase price**: When adding inventory for a product with no purchase history, default unit cost to $0.00 with option to enter actual cost
- **Notes requirement**: Notes are required when reason is "Other" to ensure audit trail has context
- **Decimal quantities**: System handles fractional quantities (e.g., 2.5 cups)
- **Live preview accuracy**: Preview must update immediately as user types, showing new quantity and cost impact

## Requirements *(mandatory)*

### Functional Requirements

**Adjustment Interface:**
- **FR-001**: System MUST provide an [Adjust] action on each inventory item in the Inventory tab
- **FR-002**: Adjustment dialog MUST display current inventory details (product, purchase date, current quantity, unit cost)
- **FR-003**: User MUST be able to choose adjustment direction (reduce or add)
- **FR-004**: System MUST show live preview of new quantity and cost impact as user enters values (no additional click required)

**Depletion (Reduce Inventory):**
- **FR-005**: User MUST enter a positive number representing the amount to reduce
- **FR-006**: User MUST select a depletion reason from: Spoilage, Gift, Physical Count Correction, Ad Hoc Usage, Other
- **FR-007**: User MAY enter optional notes (notes MUST be required when reason is "Other")
- **FR-008**: System MUST validate that reduction does not exceed available quantity
- **FR-009**: System MUST create a depletion record with quantity, reason, notes, timestamp, and user identifier

**Addition (Add Inventory):**
- **FR-010**: User MUST select a product from the full product catalog when adding inventory (not limited to products currently in inventory)
- **FR-011**: System MUST pre-populate defaults: date=today, price=last purchase price (or $0), supplier=optional
- **FR-012**: User MAY override any default value before saving
- **FR-013**: System MUST create an inventory record linked to the selected product
- **FR-014**: Addition reason MUST be recorded (e.g., "Physical Count Correction", "Found", "Received Gift", "Other")

**Data Integrity:**
- **FR-015**: System MUST NOT allow inventory quantity to go negative
- **FR-016**: All adjustments MUST create immutable audit records (who, when, why, how much)
- **FR-017**: Cost impact MUST be calculated accurately (quantity x unit cost)
- **FR-018**: Adjustments MUST integrate with existing FIFO tracking

**Depletion History:**
- **FR-019**: Depletion history view MUST show all depletions (automatic and manual)
- **FR-020**: History MUST display: date, reason, quantity, cost, and notes (truncated with hover for full text)
- **FR-021**: History MUST be sorted by date (newest first)

### Key Entities

- **InventoryDepletion**: Records each inventory reduction with quantity, reason (extended enum), notes, cost, timestamp, and user. Immutable audit trail.
- **InventoryItem**: Existing entity tracking current quantity per purchase. Updated by adjustments.
- **AdjustmentReason**: Extended enumeration including manual reasons (Spoilage, Gift, Correction, Ad Hoc Usage, Found, Received Gift, Other) alongside automatic reasons (Production, Assembly).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can complete a simple inventory adjustment (single item, standard reason) in under 30 seconds
- **SC-002**: 100% of manual adjustments are recorded with complete audit trail (who, when, why, how much)
- **SC-003**: Live preview updates within 100ms of user input (perceived as instant)
- **SC-004**: Zero data entry required beyond amount for standard depletions (reason dropdown, optional notes)
- **SC-005**: Addition workflow requires only product selection and amount; all other fields have sensible defaults
- **SC-006**: Inventory accuracy improves such that physical counts match system records within 5% tolerance after regular use

## Assumptions

- Existing `InventoryDepletion` model can be extended with new reason values without schema migration
- The `notes` field already exists on the depletion model
- User identifier will use a simple string (e.g., "desktop-user") until multi-user authentication is implemented
- Last purchase price lookup is already available through existing services
