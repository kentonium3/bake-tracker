# Feature Specification: Materials FIFO Foundation

**Feature Branch**: `058-materials-fifo-foundation`
**Created**: 2026-01-18
**Status**: Draft
**Input**: Design document `docs/design/F058_materials_fifo_foundation.md`

## Overview

Bring the materials domain into constitutional compliance by implementing FIFO (First In, First Out) inventory tracking that parallels the food/ingredients system. This establishes strict definition/instantiation separation where MaterialProduct holds only catalog definitions while MaterialInventoryItem tracks actual inventory with FIFO costing.

**Breaking Change**: Existing material purchase history will not migrate. Users start fresh with material inventory after this feature.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Material Purchase Creates Inventory (Priority: P1)

When a user records a material purchase, the system automatically creates an inventory item that tracks the purchased quantity and cost for FIFO consumption.

**Why this priority**: Core foundation - without inventory items, FIFO tracking cannot function. All other stories depend on this.

**Independent Test**: Record a material purchase and verify an inventory item is created with correct quantity and cost snapshot.

**Acceptance Scenarios**:

1. **Given** a material product exists in the catalog, **When** user records a purchase of 100 feet of ribbon at $15.00, **Then** a MaterialInventoryItem is created with quantity_purchased=3048cm (converted to base units), cost_per_unit calculated, and quantity_remaining=3048cm.

2. **Given** a material purchase is recorded, **When** viewing the inventory item later, **Then** the cost_per_unit and quantity_purchased values have not changed (immutable snapshots).

3. **Given** a material purchase uses imperial units (feet), **When** the inventory item is created, **Then** quantities are stored in metric base units (cm) with correct conversion (1 foot = 30.48 cm).

---

### User Story 2 - FIFO Consumption of Materials (Priority: P1)

When materials are consumed (e.g., during assembly), the system consumes from the oldest inventory first (FIFO) and tracks the actual cost based on which lots were consumed.

**Why this priority**: Core FIFO algorithm - the primary purpose of this feature. Equal priority with P1 as both are foundational.

**Independent Test**: Create multiple purchases at different prices, consume materials, verify oldest lots consumed first and cost calculated correctly.

**Acceptance Scenarios**:

1. **Given** two inventory lots exist (Lot A: 100cm at $0.10/cm, Lot B: 100cm at $0.15/cm) where Lot A was purchased first, **When** 50cm is consumed, **Then** consumption comes from Lot A only and total cost is $5.00.

2. **Given** Lot A has 30cm remaining and Lot B has 100cm, **When** 50cm is consumed, **Then** all 30cm from Lot A is consumed first, then 20cm from Lot B, with total cost calculated as (30 * $0.10) + (20 * $0.15) = $6.00.

3. **Given** materials are consumed, **When** viewing consumption records, **Then** each record links to the specific inventory item it consumed from (traceability).

---

### User Story 3 - Inventory Availability Check (Priority: P2)

Before starting an assembly or planning an event, users can verify if sufficient material inventory exists.

**Why this priority**: Enables planning workflows. Depends on P1 inventory tracking being in place.

**Independent Test**: Query available inventory for a material product and verify correct totals.

**Acceptance Scenarios**:

1. **Given** three inventory lots with quantities 50cm, 30cm, and 20cm remaining, **When** checking available inventory, **Then** system returns 100cm total.

2. **Given** a requirement for 150cm but only 100cm available, **When** validating availability, **Then** system indicates insufficient inventory with shortfall of 50cm.

---

### User Story 4 - Catalog Shows Definitions Only (Priority: P2)

The Materials Catalog view displays only product definitions (name, brand, package info) without cost or inventory data, maintaining clear separation between catalog and inventory.

**Why this priority**: Constitutional compliance - UI must reflect the definition/instantiation separation. Can be verified independently.

**Independent Test**: View Materials Catalog and verify no cost or inventory columns appear.

**Acceptance Scenarios**:

1. **Given** the user navigates to Catalog > Materials > Material Products, **When** viewing the product list, **Then** columns show only: Name, Brand, SKU, Package (qty + unit), Supplier - NO cost or inventory columns.

2. **Given** a material product in the catalog, **When** user wants to see inventory, **Then** a "View Inventory" link navigates to the inventory view (handled by F059).

---

### User Story 5 - Import/Export Handles Schema Changes (Priority: P3)

Users can export and import material catalogs with the new schema, and old export files (with deprecated fields) import gracefully.

**Why this priority**: Data portability - important but not blocking core functionality.

**Independent Test**: Export materials, modify, re-import and verify data integrity.

**Acceptance Scenarios**:

1. **Given** the new schema is in place, **When** exporting material products, **Then** the export does NOT include current_inventory or weighted_avg_cost fields.

2. **Given** an old export file with current_inventory and weighted_avg_cost fields, **When** importing, **Then** those fields are ignored and import succeeds with definition fields only.

---

### Edge Cases

- What happens when consuming more than available inventory? System reports shortfall; partial consumption not performed without explicit confirmation.
- What happens when a material product has no inventory items? Available inventory returns 0; consumption fails with clear error.
- What happens with unit conversion edge cases (e.g., square feet to linear cm)? Validation rejects incompatible unit type conversions.
- What happens if purchase has $0 cost? cost_per_unit is $0; valid scenario (donated materials).

## Requirements *(mandatory)*

### Functional Requirements

#### Schema Changes

- **FR-001**: System MUST remove `current_inventory` field from MaterialProduct model
- **FR-002**: System MUST remove `weighted_avg_cost` field from MaterialProduct model
- **FR-003**: System MUST create MaterialInventoryItem table with fields: material_product_id, material_purchase_id, quantity_purchased, quantity_remaining, cost_per_unit, purchase_date, location, notes, timestamps
- **FR-004**: System MUST add `inventory_item_id` FK to MaterialConsumption model for FIFO traceability
- **FR-005**: System MUST change Material.base_unit_type to use metric values: "linear_cm", "square_cm", "each"

#### Service Layer

- **FR-006**: System MUST provide `get_fifo_inventory(material_product_id)` returning inventory items ordered by purchase date ascending (oldest first)
- **FR-007**: System MUST provide `consume_material_fifo(material_product_id, quantity_needed, target_unit, context_id)` that consumes from oldest lots first
- **FR-008**: System MUST provide `validate_inventory_availability(requirements)` to check if sufficient inventory exists
- **FR-009**: System MUST provide `calculate_available_inventory(material_product_id)` summing quantity_remaining across all lots
- **FR-010**: System MUST automatically create MaterialInventoryItem when MaterialPurchase is created

#### Unit Conversion

- **FR-011**: System MUST convert imperial linear units to cm: feet (x30.48), inches (x2.54), yards (x91.44)
- **FR-012**: System MUST convert imperial area units to square cm: square_feet (x929.03), square_inches (x6.4516)
- **FR-013**: System MUST convert metric units to base: meters (x100), mm (/10), square_meters (x10000)
- **FR-014**: System MUST validate that package_unit is convertible to Material.base_unit_type before storing

#### Data Integrity

- **FR-015**: System MUST enforce quantity_purchased as immutable after creation
- **FR-016**: System MUST enforce cost_per_unit as immutable after creation
- **FR-017**: System MUST prevent quantity_remaining from going negative
- **FR-018**: System MUST store all inventory quantities in base units (cm for linear/area)

#### Import/Export

- **FR-019**: System MUST exclude current_inventory and weighted_avg_cost from MaterialProduct exports
- **FR-020**: System MUST gracefully ignore current_inventory and weighted_avg_cost in MaterialProduct imports

### Key Entities

- **MaterialInventoryItem**: Represents a specific lot of material inventory from a purchase. Tracks quantity_purchased (immutable), quantity_remaining (mutable, decremented on consumption), and cost_per_unit (immutable snapshot). Links to MaterialProduct (what) and MaterialPurchase (when/where).

- **MaterialConsumption**: Records when materials are consumed. Now includes inventory_item_id to trace exactly which lot was consumed for FIFO accuracy.

- **MaterialProduct** (modified): Catalog definition only - name, brand, SKU, package info, supplier. NO longer contains cost or inventory data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: FIFO consumption correctly consumes oldest inventory first, verified with multi-lot test scenarios
- **SC-002**: All inventory quantities stored in metric base units (cm) with correct conversion from imperial inputs
- **SC-003**: MaterialProduct catalog queries return no cost or inventory data
- **SC-004**: Import/export roundtrip succeeds with new schema (export → import → verify data integrity)
- **SC-005**: Cost snapshots remain immutable - verified by attempting modification and confirming rejection
- **SC-006**: Material inventory service primitives can be called by other services (integration test with mock consumer)
- **SC-007**: Pattern consistency with ingredient system - MaterialInventoryItem structure matches InventoryItem structure

## Assumptions

- Users accept fresh start for material inventory (no migration of existing purchases)
- The ingredient FIFO pattern is the authoritative reference for implementation
- F059 (Materials Purchase Mode UI) will be implemented separately to provide the UI for these services
- Assembly integration will be a separate future feature

## Out of Scope

- Purchase mode UI (F059)
- Manual inventory adjustment UI (F059)
- Assembly integration with materials
- Event planning cost calculations with materials
- FinishedGood composition with materials
