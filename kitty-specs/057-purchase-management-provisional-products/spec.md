# Feature Specification: Purchase Management with Provisional Products

**Feature Branch**: `057-purchase-management-provisional-products`
**Created**: 2026-01-17
**Status**: Draft
**Input**: See docs/design/_F0XX_purchase_management_refactored.md

## Overview

Purchase recording is currently blocked when products don't exist in the catalog. This prevents real-world workflows where new products are discovered during shopping. This feature enables purchase recording regardless of product catalog state by introducing provisional product creation, adds JSON import UI integration, and establishes proper service boundaries.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record Purchase for Unknown Product (Priority: P1)

A user is recording a purchase from a shopping trip and encounters a product that doesn't exist in the catalog. Instead of being blocked, they can create a provisional product on-the-fly and complete the purchase recording immediately.

**Why this priority**: This is the core value proposition - unblocking the purchase workflow. Without this, users cannot record purchases for new products, which breaks the fundamental use case.

**Independent Test**: Can be fully tested by attempting to record a purchase for a non-existent product and verifying that provisional product creation is offered and the purchase completes successfully.

**Acceptance Scenarios**:

1. **Given** a user is recording a purchase and searches for a product that doesn't exist, **When** they receive "product not found", **Then** they are offered the option to create a provisional product.

2. **Given** a user chooses to create a provisional product, **When** they provide ingredient, brand, package unit, and package quantity, **Then** a provisional product is created with `is_provisional=true` and the purchase is recorded against it.

3. **Given** a provisional product is created during purchase entry, **When** the purchase is saved, **Then** inventory is automatically increased for that product.

4. **Given** a provisional product is created, **When** slug generation encounters a collision, **Then** a unique suffix is automatically added to ensure uniqueness.

---

### User Story 2 - Review Provisional Products (Priority: P2)

A user wants to complete the details of provisional products that were created during purchase entry. They can find these products easily via a review queue and complete the missing information.

**Why this priority**: While provisional products are immediately usable, completing their details improves data quality. This is secondary to the core purchase workflow.

**Independent Test**: Can be fully tested by creating provisional products, then using the Products tab filter to find and complete them.

**Acceptance Scenarios**:

1. **Given** provisional products exist in the system, **When** a user views the Products tab, **Then** a visual badge/count indicator shows how many products need review.

2. **Given** a user is in the Products tab, **When** they select the "Needs Review" filter, **Then** only products with `is_provisional=true` are displayed.

3. **Given** a user is viewing a provisional product, **When** they see missing/incomplete fields, **Then** those fields are clearly highlighted.

4. **Given** a user completes the missing fields for a provisional product, **When** they mark it as reviewed, **Then** the `is_provisional` flag is cleared and the product no longer appears in the review queue.

---

### User Story 3 - Import Purchases from JSON File (Priority: P3)

A user has a JSON file containing purchase data (e.g., from a mobile scanning app or external system). They can import this file through the UI, and any unknown products are automatically created as provisional products.

**Why this priority**: Bulk import is valuable but less frequently used than manual entry. The manual workflow (P1) must work first.

**Independent Test**: Can be fully tested by importing a JSON file with both known and unknown products, verifying purchases are created and provisional products are generated for unknowns.

**Acceptance Scenarios**:

1. **Given** a user has a valid JSON purchase file, **When** they select the file through the import UI, **Then** the import service processes the file.

2. **Given** an import completes, **When** results are displayed, **Then** the user sees counts of successful imports, skipped records, and errors.

3. **Given** an import contains purchases for unknown products, **When** processing completes, **Then** provisional products are created automatically and the user is notified.

4. **Given** provisional products were created during import, **When** the results are displayed, **Then** the user is offered an option to navigate to the provisional product review queue.

---

### User Story 4 - Record Purchase for Known Product (Priority: P4)

A user records a purchase for a product that already exists in the catalog. The existing manual entry workflow continues to work with product lookup delegated to the appropriate service.

**Why this priority**: This workflow already exists (F043). Enhancements ensure proper service delegation but the user experience is largely unchanged.

**Independent Test**: Can be fully tested by recording a purchase for an existing product and verifying it completes successfully with inventory updated.

**Acceptance Scenarios**:

1. **Given** a user is recording a purchase, **When** they search for a product that exists, **Then** the product is found and can be selected.

2. **Given** a user has selected an existing product, **When** they complete the purchase form with valid data, **Then** the purchase is saved and inventory is increased.

3. **Given** a user enters a purchase similar to an existing one, **When** duplicate detection triggers, **Then** a warning is shown but the user can proceed if desired.

---

### Edge Cases

- What happens when a user cancels provisional product creation mid-flow?
  - The purchase entry returns to product search; no partial records are created.

- What happens when the ingredient selector has no matching ingredients for a provisional product?
  - User can create a provisional product with a generic/placeholder ingredient, or cancel and add the ingredient first.

- What happens when JSON import contains malformed records?
  - Malformed records are skipped with errors logged; valid records are processed.

- What happens when inventory service is unavailable during purchase recording?
  - The entire transaction rolls back; user is notified to retry.

- How does the system handle provisional products that are never reviewed?
  - Provisional products remain usable indefinitely; they simply stay in the review queue.

## Requirements *(mandatory)*

### Functional Requirements

**Purchase Recording**
- **FR-001**: System MUST allow recording purchases for products that exist in the catalog.
- **FR-002**: System MUST offer provisional product creation when a product is not found during purchase entry.
- **FR-003**: System MUST validate purchase date, unit price (positive), and quantity (positive) before saving.
- **FR-004**: System MUST calculate total cost as unit_price multiplied by quantity_purchased.
- **FR-005**: System MUST detect potential duplicate purchases and warn the user (without blocking).

**Provisional Product Creation**
- **FR-006**: System MUST create provisional products with `is_provisional=true` flag.
- **FR-007**: System MUST delegate slug generation to product_catalog_service with uniqueness validation.
- **FR-008**: System MUST allow user to provide ingredient, brand, package unit, and package quantity for provisional products (product name optional).
- **FR-009**: System MUST allow purchases to reference provisional products immediately after creation.
- **FR-010**: System MUST trigger inventory creation when a purchase references a provisional product.

**Product Review Queue**
- **FR-011**: System MUST display a visual badge/count indicator when provisional products exist.
- **FR-012**: System MUST provide a "Needs Review" filter in the Products tab.
- **FR-013**: System MUST highlight missing/incomplete fields when viewing provisional products.
- **FR-014**: System MUST clear the `is_provisional` flag when a user marks a product as reviewed.

**JSON Import**
- **FR-015**: System MUST provide UI to select a JSON file for purchase import.
- **FR-016**: System MUST call the existing import service infrastructure to process JSON files.
- **FR-017**: System MUST display import results showing success/skip/error counts.
- **FR-018**: System MUST create provisional products for unknown products during import.
- **FR-019**: System MUST offer navigation to the review queue after import completes.

**Service Boundaries**
- **FR-020**: Purchase service MUST delegate product lookup to product_catalog_service.
- **FR-021**: Purchase service MUST delegate provisional product creation to product_catalog_service.
- **FR-022**: Purchase service MUST delegate inventory updates to inventory_service.
- **FR-023**: Purchase service MUST delegate supplier lookup/creation to supplier_service.
- **FR-024**: Purchase service MUST NOT implement UPC matching, slug generation, or inventory calculations.

**Transaction Integrity**
- **FR-025**: System MUST use atomic transactions for purchase recording (purchase + inventory both succeed or both fail).
- **FR-026**: Purchases MUST be immutable after creation (no edit/delete in production use).

### Key Entities

- **Purchase**: A recorded transaction capturing product, supplier, date, unit price, quantity purchased, and total cost. References a Product and Supplier. Immutable after creation.

- **Product**: An item in the product catalog. May have `is_provisional=true` if created provisionally. Has a unique slug generated by product_catalog_service.

- **Provisional Product**: A Product created during purchase workflow with incomplete information. Flagged with `is_provisional=true`. Fully usable for purchases while awaiting review.

- **Supplier**: The vendor/store where a purchase was made. Looked up or created via supplier_service.

- **Inventory Item**: Created automatically when a purchase is recorded. Managed by inventory_service including quantity and weighted average cost calculations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- [x] **SC-001**: Users can record a purchase for an unknown product in under 2 minutes (including provisional product creation).

- [x] **SC-002**: 100% of purchases result in inventory updates (no orphaned purchases without inventory).

- [x] **SC-003**: Users can identify and access provisional products requiring review within 3 clicks from any screen.

- [x] **SC-004**: JSON import of 50+ purchases completes and displays results within 30 seconds.

- [x] **SC-005**: Purchase workflow is never blocked due to missing product catalog entries.

- [x] **SC-006**: All provisional products are visible in the review queue until explicitly marked as reviewed.

- [x] **SC-007**: Service boundaries are enforced - purchase service contains no UPC matching, slug generation, or inventory calculation logic.

## Out of Scope

- CSV import (JSON only per project decision)
- UPC matching algorithm implementation (product_catalog_service responsibility)
- Slug generation algorithm implementation (product_catalog_service responsibility)
- Inventory quantity calculations (inventory_service responsibility)
- Weighted average cost calculations (inventory_service responsibility)
- File transport mechanisms (Dropbox/Drive sync)
- Mobile app implementation
- Purchase editing after creation
- Purchase deletion (archive, don't delete)
- Receipt OCR

## Assumptions

- Product model supports an `is_provisional` boolean field (or can be added).
- Existing import service infrastructure can be extended to handle provisional product creation.
- Product_catalog_service, inventory_service, and supplier_service exist and expose appropriate methods (verify during planning).
- The Products tab currently supports filtering (enhance with "Needs Review" option).

## Dependencies

- Existing purchase UI (F043) - to be enhanced
- Existing import service infrastructure - to be integrated
- Product catalog service - delegation target
- Inventory service - delegation target
- Supplier service - delegation target

## Risks

- **Service interface mismatch**: Actual service interfaces may differ from assumptions.
  - Mitigation: Planning phase discovers actual interfaces; adapt as needed.

- **Product model changes required**: Adding `is_provisional` field may require migration.
  - Mitigation: Use project's reset/re-import strategy for schema changes.

- **Provisional products accumulate**: Users may not review provisional products.
  - Mitigation: Visual badge draws attention; provisional products remain usable.
