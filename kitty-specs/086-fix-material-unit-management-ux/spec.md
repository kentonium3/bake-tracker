# Feature Specification: Fix MaterialUnit Management and Entry UX

**Feature Branch**: `086-fix-material-unit-management-ux`
**Created**: 2026-01-30
**Status**: Draft
**Input**: User description: "Fix MaterialUnit management for linear products - Edit/Delete buttons disabled, Material Units tab shows no units, Add Unit dialog requires manual cm conversion"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View All Material Units (Priority: P1)

As a user, I want to see all MaterialUnits listed in the Material Units tab so I can browse and manage consumption units across all products.

**Why this priority**: Without visibility into existing units, users cannot verify what units exist or identify what needs to be added. This is foundational for all other management tasks.

**Independent Test**: Navigate to Material Units tab and verify units appear in the listing for both "each" type and linear type products.

**Acceptance Scenarios**:

1. **Given** the database contains MaterialUnits for various products, **When** the user opens the Material Units tab, **Then** all MaterialUnits are listed with their associated product information
2. **Given** the user is viewing the Material Units tab, **When** new units are created via the Edit Product dialog, **Then** the listing refreshes to include the new units

---

### User Story 2 - Edit Existing Material Units (Priority: P1)

As a user, I want to edit MaterialUnits for linear products so I can update names and descriptions of existing consumption units.

**Why this priority**: Users need to correct or clarify unit definitions after creation. The Edit button being disabled prevents basic maintenance tasks.

**Independent Test**: Select a linear product unit in the Edit Product dialog's Material Units section and verify the Edit button enables and opens the edit dialog.

**Acceptance Scenarios**:

1. **Given** a linear product with at least one MaterialUnit, **When** the user selects a unit in the Material Units tree, **Then** the Edit and Delete buttons become enabled
2. **Given** the user clicks Edit on a selected unit, **When** the edit dialog opens, **Then** the user can modify the name and description and save changes

---

### User Story 3 - Add Units with User-Friendly Measurements (Priority: P2)

As a user, I want to create MaterialUnits by entering measurements in familiar units (inches, feet, yards, meters) so I don't have to manually calculate centimeter conversions.

**Why this priority**: Creating ribbon cuts like "8-inch ribbon" or "14-inch ribbon" currently requires converting 8 inches to 20.32 cm manually, which is error-prone and frustrating.

**Independent Test**: Open Add Unit dialog for a linear product and enter "8" with "inches" selected, verify it saves correctly with the proper cm conversion.

**Acceptance Scenarios**:

1. **Given** a linear product (base_unit_type = linear_cm), **When** the user opens the Add Unit dialog, **Then** a unit selector dropdown appears with options: centimeters, inches, feet, yards, meters
2. **Given** the user enters quantity "8" and selects "inches", **When** the user saves, **Then** the system stores quantity_per_unit as 20.32 (8 * 2.54 cm)
3. **Given** the user enters quantity "1" and selects "yards", **When** the user saves, **Then** the system stores quantity_per_unit as 91.44 (1 * 91.44 cm)

---

### User Story 4 - Delete Material Units (Priority: P3)

As a user, I want to delete MaterialUnits that are no longer needed so I can keep my unit list clean.

**Why this priority**: Lower priority than viewing and editing, but necessary for complete CRUD functionality.

**Independent Test**: Select a unit and click Delete, verify confirmation dialog appears and unit is removed upon confirmation.

**Acceptance Scenarios**:

1. **Given** a selected MaterialUnit in the tree, **When** the user clicks Delete, **Then** a confirmation dialog appears
2. **Given** the user confirms deletion, **When** the deletion completes, **Then** the unit is removed from the list and database

---

### Edge Cases

- What happens when a user tries to delete a MaterialUnit that is referenced in existing RecipeMaterialUsage records? System should warn or prevent deletion.
- What happens when the user enters zero or negative quantity in the Add Unit dialog? System should validate and reject with error message.
- What happens when the user enters a duplicate unit name for the same product? System should validate uniqueness and reject with error message.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Material Units tab MUST display all MaterialUnits from the database with their associated product name
- **FR-002**: System MUST enable Edit and Delete buttons when a MaterialUnit is selected in the Edit Product dialog's Material Units section, regardless of material type (each or linear)
- **FR-003**: Add Unit dialog MUST display a unit selector dropdown for linear products with options: centimeters (cm), inches (in), feet (ft), yards (yd), meters (m)
- **FR-004**: System MUST automatically convert user-entered quantities to centimeters before storing in quantity_per_unit field
- **FR-005**: System MUST validate that quantity_per_unit is greater than zero before saving
- **FR-006**: System MUST validate MaterialUnit name uniqueness within a product
- **FR-007**: Delete operation MUST show confirmation dialog before removing a MaterialUnit

### Conversion Factors (for FR-004)

- 1 inch = 2.54 cm
- 1 foot = 30.48 cm
- 1 yard = 91.44 cm
- 1 meter = 100 cm

### Key Entities

- **MaterialUnit**: Consumption unit definition belonging to a MaterialProduct. Key attributes: name, quantity_per_unit (stored in cm for linear), description, material_product_id
- **MaterialProduct**: Product that contains MaterialUnits. Relevant attributes: material_id (links to Material with base_unit_type)
- **Material**: Abstract material definition. Relevant attribute: base_unit_type ('each', 'linear_cm', 'square_cm')

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All MaterialUnits appear in the Material Units tab listing (100% visibility)
- **SC-002**: Users can edit any MaterialUnit within 3 clicks from the Edit Product dialog
- **SC-003**: Users can create a new linear unit (e.g., "8-inch ribbon") in under 30 seconds without needing a calculator
- **SC-004**: Zero conversion errors occur when creating units in non-cm measurements (system handles all conversions)
