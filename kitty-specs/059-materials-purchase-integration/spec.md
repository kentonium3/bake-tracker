# Feature Specification: Materials Purchase Integration & Workflows

**Feature Branch**: `059-materials-purchase-integration`
**Created**: 2026-01-18
**Status**: Draft
**Input**: See docs/design/F059_materials_purchase_integration.md

## Overview

This feature enables complete UI workflows for purchasing and managing materials in Bake Tracker. F058 built the backend FIFO infrastructure for materials, but there is currently no UI to use it. This feature adds:

1. Materials purchasing form in Purchase > Add Purchase
2. MaterialInventoryItem lot display in Purchase > Inventory
3. Manual inventory adjustment dialogs
4. CLI provisional product workflow for mobile purchases
5. Provisional product enrichment in catalog
6. MaterialUnit UI enhancement showing inherited unit type

**Primary User**: Non-technical user managing holiday baking materials

## User Scenarios & Testing

### User Story 1 - Purchase Materials via UI (Priority: P1)

As a user purchasing materials at a store or online, I need to record material purchases through the UI so that my inventory is tracked accurately with FIFO cost accounting.

**Why this priority**: This is the core workflow that enables all other material management. Without purchasing, there is no inventory to display, adjust, or consume.

**Independent Test**: Can be fully tested by adding a material purchase through the UI form and verifying the MaterialInventoryItem lot is created with correct quantities and costs.

**Acceptance Scenarios**:

1. **Given** the Purchase > Add Purchase form is open, **When** I select "Material" as product type, **Then** the form displays MaterialProduct dropdown, package quantity fields, and calculated unit cost fields.

2. **Given** I have selected a MaterialProduct and entered package quantity (e.g., 4 packages of 25 bags each) and total cost ($40), **When** I view the calculated fields, **Then** I see total units (100 bags) and unit cost ($0.40/bag) displayed in read-only fields.

3. **Given** I have filled all required material purchase fields correctly, **When** I click Save, **Then** a MaterialPurchase and MaterialInventoryItem are created, and the form resets for the next entry.

4. **Given** I have left required fields empty, **When** I attempt to save, **Then** the Save button remains disabled or shows validation errors indicating which fields need completion.

---

### User Story 2 - View Material Inventory (Priority: P1)

As a user managing materials, I need to see my current material inventory lots so that I know what I have available and can make purchasing decisions.

**Why this priority**: Visibility into inventory is essential for planning and decision-making. This is tightly coupled with the purchase workflow as it validates that purchases are recorded correctly.

**Independent Test**: Can be fully tested by navigating to Purchase > Inventory > Materials and verifying that MaterialInventoryItem lots display with correct data and formatting.

**Acceptance Scenarios**:

1. **Given** I have material inventory items, **When** I navigate to Purchase > Inventory > Materials, **Then** I see a table showing Product Name, Brand, Purchased Date, Qty Purchased, Qty Remaining, Cost/Unit, Total Value, and an Adjust action.

2. **Given** I have multiple inventory lots for the same product, **When** I view the inventory table, **Then** lots are sorted by purchased date descending (newest first for visibility).

3. **Given** I want to find specific materials, **When** I use the filter controls, **Then** I can filter by MaterialProduct, date range, and whether to show depleted items.

4. **Given** I have no material inventory, **When** I view the Materials inventory section, **Then** I see an empty state message: "No material inventory items. Purchase materials to get started."

---

### User Story 3 - Manually Adjust Inventory (Priority: P2)

As a user who has used materials outside the tracked system or discovered inventory discrepancies, I need to manually adjust inventory quantities so that my records match reality.

**Why this priority**: Manual adjustments are a necessary correction mechanism but secondary to the core purchase and view workflows.

**Independent Test**: Can be fully tested by opening the Manual Adjust dialog on an inventory lot and verifying adjustments update the inventory correctly.

**Acceptance Scenarios**:

1. **Given** I click "Adjust" on an inventory lot for an "each" material (e.g., bags), **When** the dialog opens, **Then** I see the current state (quantity remaining, original quantity, purchase date) and Add/Subtract/Set radio options with an integer quantity input.

2. **Given** I click "Adjust" on an inventory lot for a variable material (e.g., ribbon in cm), **When** the dialog opens, **Then** I see the current state and a percentage slider/input (0-100%) with a preview of the new quantity in cm.

3. **Given** I have entered an adjustment and see the preview calculation, **When** I click Save, **Then** the inventory is updated (new lot for "each" materials, direct update for variable materials) and the inventory table reflects the change.

4. **Given** I am adjusting inventory, **When** I enter a value that would result in negative quantity, **Then** validation prevents saving and displays an error.

5. **Given** I opened the adjustment dialog, **When** I click Cancel, **Then** the dialog closes without making any changes.

---

### User Story 4 - Purchase Materials via CLI with Provisional Product (Priority: P2)

As a user at a store using mobile CLI access, I need to quickly record a material purchase even if the product isn't in my catalog so that my inventory is updated immediately without blocking on catalog setup.

**Why this priority**: Enables mobile workflow which is important for capturing purchases in real-time, but requires CLI infrastructure that may not exist yet.

**Independent Test**: Can be fully tested via CLI by attempting to purchase a material that doesn't exist and verifying a provisional product and inventory lot are created.

**Acceptance Scenarios**:

1. **Given** I am using the CLI to add a material purchase, **When** the MaterialProduct doesn't exist, **Then** I am prompted to create a provisional product with minimal required fields (name, material type, quantity).

2. **Given** I confirm provisional product creation, **When** the product is created, **Then** it has is_provisional=True, and a MaterialPurchase and MaterialInventoryItem are created with inventory immediately available.

3. **Given** a provisional product exists, **When** I view it in Catalog > Materials > Material Products, **Then** it shows a visible indicator (icon/badge) indicating it needs enrichment.

---

### User Story 5 - Enrich Provisional Products (Priority: P3)

As a user who created provisional products via CLI, I need to complete their catalog information later so that my product catalog is accurate and complete.

**Why this priority**: Enrichment is a convenience workflow that can happen asynchronously; the system works without it.

**Independent Test**: Can be fully tested by editing a provisional product in the catalog, adding complete metadata, and verifying the provisional flag is cleared.

**Acceptance Scenarios**:

1. **Given** I have a provisional product showing the "needs enrichment" indicator, **When** I click Edit, **Then** I see the standard product edit form with all fields (brand, SKU, supplier, notes).

2. **Given** I have filled in the complete metadata for a provisional product, **When** I click Save, **Then** is_provisional is set to False and the indicator is removed.

3. **Given** I enrich a provisional product, **When** I check historical purchases and inventory, **Then** they remain linked and unchanged (only the product metadata is updated).

---

### User Story 6 - Understand MaterialUnit Quantity (Priority: P3)

As a user creating or editing MaterialUnits, I need to clearly see the inherited unit type so that I understand what quantity value means for this material.

**Why this priority**: UI clarity enhancement that improves user understanding but doesn't block core functionality.

**Independent Test**: Can be fully tested by opening the MaterialUnit create/edit dialog, selecting a Material, and verifying the inherited unit type and quantity preview display correctly.

**Acceptance Scenarios**:

1. **Given** I am creating a MaterialUnit and select a Material, **When** the Material is selected, **Then** I see "Unit type: [base_unit_type] (inherited from [Material.name])" displayed clearly.

2. **Given** I have selected a variable material (e.g., ribbon with linear_cm), **When** I enter a quantity value, **Then** I see a preview: "This unit will consume [quantity] cm of [Material.name]".

3. **Given** I have selected an "each" material (e.g., bags), **When** I view the quantity field, **Then** it is locked to 1 and shows: "This unit will consume 1 [Material.name]".

---

### Edge Cases

- What happens when a MaterialProduct is deleted that has existing inventory lots? (System should prevent deletion or cascade appropriately)
- How does the system handle unit conversion errors? (Display user-friendly error, don't save invalid data)
- What happens if the user enters extremely large quantities? (Validate reasonable bounds)
- What if the user changes product type (Food/Material) mid-form entry? (Clear the type-specific fields)
- What happens when filtering shows zero results? (Display appropriate "no matching items" message)
- How does manual adjustment handle concurrent edits? (Standard optimistic locking or last-write-wins)

## Requirements

### Functional Requirements

- **FR-001**: Purchase > Add Purchase form MUST include product type selector (Food/Material radio buttons) that controls which fields are displayed.
- **FR-002**: When Material is selected, form MUST display MaterialProduct dropdown, package quantity fields (packages purchased, package unit count, package unit), and total cost input.
- **FR-003**: Form MUST display calculated read-only fields for total units in base units and unit cost that update in real-time as the user types.
- **FR-004**: Form validation MUST prevent submission when required fields are incomplete.
- **FR-005**: Successful submission MUST create MaterialPurchase and MaterialInventoryItem records via F058 services.
- **FR-006**: Purchase > Inventory MUST include a Materials section/tab displaying MaterialInventoryItem lots.
- **FR-007**: Inventory table MUST show columns: Product Name, Brand, Purchased Date, Qty Purchased, Qty Remaining, Cost/Unit, Total Value, and Adjust action.
- **FR-008**: Inventory table MUST sort by purchased_at descending (newest first) by default.
- **FR-009**: Inventory view MUST provide filters for MaterialProduct, date range, and "show depleted" checkbox.
- **FR-010**: Manual Adjust dialog MUST display current inventory state (quantity remaining, original quantity, purchase date).
- **FR-011**: For "each" materials, adjustment dialog MUST offer Add/Subtract/Set options with integer input.
- **FR-012**: For variable materials (linear_cm, square_cm), adjustment dialog MUST offer percentage-based input (0-100%).
- **FR-013**: Adjustment dialog MUST show preview of resulting quantity before save.
- **FR-014**: Adjustment validation MUST prevent negative resulting quantities.
- **FR-015**: CLI purchase workflow MUST support creating provisional MaterialProducts when product not found.
- **FR-016**: Provisional products MUST have is_provisional=True flag and create inventory immediately.
- **FR-017**: Catalog > Materials > Material Products MUST show indicator for provisional products.
- **FR-018**: Edit dialog for provisional products MUST allow enrichment and clear is_provisional flag when complete.
- **FR-019**: MaterialUnit create/edit dialog MUST display inherited unit type when Material is selected.
- **FR-020**: MaterialUnit dialog MUST show dynamic quantity field label indicating the unit type.
- **FR-021**: MaterialUnit dialog MUST display preview text showing consumption in concrete terms.
- **FR-022**: For "each" materials, MaterialUnit quantity MUST be locked to 1.

### Key Entities

- **MaterialPurchase**: Record of a material purchase transaction (date, cost, quantity, supplier)
- **MaterialInventoryItem**: Individual inventory lot with FIFO tracking (quantity_purchased, quantity_remaining, cost_per_unit)
- **MaterialProduct**: Catalog entry for a specific material product (brand, package configuration, provisional flag)
- **Material**: Material definition with base unit type (each, linear_cm, square_cm)
- **MaterialUnit**: Predefined consumption unit linking Material to quantity consumed

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can complete a material purchase through the UI in under 2 minutes.
- **SC-002**: Users can locate specific inventory lots using filters in under 30 seconds.
- **SC-003**: Manual adjustments are completed and reflected in inventory view immediately upon save.
- **SC-004**: CLI provisional workflow allows purchase recording with only 3 required inputs (name, quantity, cost).
- **SC-005**: 100% of provisional products display clear visual indicator distinguishing them from complete products.
- **SC-006**: Users viewing MaterialUnit creation correctly understand quantity meaning on first attempt (unit type and preview visible).
- **SC-007**: All purchase and adjustment operations complete without errors when valid data is provided.
- **SC-008**: Form validation prevents all invalid submissions with clear error messaging.

## Assumptions

- F058 MaterialInventoryService and unit conversion infrastructure is complete and working.
- Existing Purchase form patterns (layout, validation, CTkToplevel dialogs) provide consistent UI foundation.
- CLI infrastructure exists or will be created to support the provisional product workflow (FR-015, FR-016).
- Database schema already includes is_provisional field on MaterialProduct (or can be added via migration).

## Out of Scope

- Assembly integration (separate feature - F060 or later)
- FinishedGood composition with MaterialUnits
- Material assignment interface at assembly time
- Event planning cost calculations
- MaterialInventoryItem lot merging/splitting
- Advanced inventory analytics/reporting
- Low stock alerts
- Barcode scanning for purchases
