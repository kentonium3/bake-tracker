# Feature Specification: Import/Export v4.0 Upgrade

**Feature Branch**: `040-import-export-v4`
**Created**: 2026-01-06
**Status**: Draft
**Input**: Upgrade import/export to v4.0 schema supporting F037 recipe structure, F039 event output_mode, BT Mobile purchase imports, and percentage-based inventory updates

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Export and Import Recipes with New Structure (Priority: P1)

The baker needs to export her recipe catalog (including new yield modes, scaling factors, and recipe variants) and later import it into a fresh database or share with future users.

**Why this priority**: This is the primary blocker. Without recipe import/export, the user cannot restore from backup, load sample data, or test the F037 recipe redesign features. All other testing is blocked.

**Independent Test**: Can be fully tested by exporting a database with scaled recipes and variants, resetting the database, and importing - verifying all recipes, yield modes, and variants are preserved.

**Acceptance Scenarios**:

1. **Given** a recipe with yield_mode="scaled", base_yield=48, and variants (Chocolate Chip, Plain), **When** exported and re-imported, **Then** the recipe retains yield_mode, base_yield, scaling_factor, and all variant definitions with their finished unit linkages.

2. **Given** a recipe with yield_mode="fixed" and no variants, **When** exported, **Then** the export file contains the correct yield_mode and empty variants array.

3. **Given** an import file with a recipe referencing a non-existent ingredient slug, **When** imported, **Then** the system rejects the recipe with a clear error message identifying the missing ingredient.

4. **Given** an import file with a recipe variant referencing a non-existent finished unit, **When** imported, **Then** the system rejects the variant with a clear error identifying the missing finished unit.

---

### User Story 2 - Export and Import Events with Output Mode (Priority: P1)

The baker needs to export her event configurations (including the new output_mode field and assembly/production targets) and import them to test the Planning Workspace features.

**Why this priority**: Tied with P1 - without event import/export with output_mode, the F039 Planning Workspace cannot be tested. Events drive the entire planning workflow.

**Independent Test**: Can be fully tested by creating events with different output_modes (bundled, bulk_count), exporting, resetting database, and importing - verifying output_mode and targets are preserved.

**Acceptance Scenarios**:

1. **Given** an event with output_mode="bundled" and event_assembly_targets, **When** exported and re-imported, **Then** the event retains output_mode and all assembly targets with quantities.

2. **Given** an event with output_mode="bulk_count" and event_production_targets, **When** exported and re-imported, **Then** the event retains output_mode and all production targets.

3. **Given** an import file with output_mode="bundled" but no event_assembly_targets, **When** imported, **Then** the system warns about the mismatch but imports the event.

---

### User Story 3 - Import Purchases from Mobile App via UPC (Priority: P2)

The baker scans product barcodes while shopping using a mobile app. The scanned purchases (with UPC, price, quantity) are exported to a JSON file. She imports this file into Bake Tracker to record purchases and add inventory without manual data entry.

**Why this priority**: Reduces manual data entry significantly for the most frequent user activity (shopping). Depends on core schema upgrade being complete.

**Independent Test**: Can be fully tested by creating a purchase JSON file with known UPCs, importing it, and verifying Purchase and InventoryItem records are created correctly.

**Acceptance Scenarios**:

1. **Given** a purchase file with a UPC that matches an existing product, **When** imported, **Then** a Purchase record and corresponding InventoryItem are created with correct price, quantity, and date.

2. **Given** a purchase file with a UPC that does NOT match any product, **When** imported, **Then** the system presents a resolution dialog allowing the user to: (a) map to existing product, (b) create new product with the UPC, or (c) skip.

3. **Given** the user chooses to map an unknown UPC to an existing product, **When** confirmed, **Then** the product is updated with the new UPC for future matching, and the purchase is recorded.

4. **Given** the user chooses to create a new product for an unknown UPC, **When** they fill in ingredient, brand, and package details, **Then** a new product is created with the UPC and the purchase is recorded.

5. **Given** multiple purchases in a single import file, **When** some match and some don't, **Then** matched purchases are imported immediately and unmatched ones are queued for resolution.

---

### User Story 4 - Import Inventory Updates via Percentage (Priority: P2)

The baker physically checks her pantry and estimates remaining quantities as percentages (e.g., "flour bag is about 30% full"). She records these via the mobile app and imports the updates to correct inventory levels without calculating exact weights.

**Why this priority**: Simplifies inventory correction - the most error-prone manual task. Enables quick physical inventory audits.

**Independent Test**: Can be fully tested by creating an inventory update JSON file with UPC and percentage values, importing it, and verifying inventory quantities are adjusted correctly.

**Acceptance Scenarios**:

1. **Given** an inventory item purchased as 25 lbs with current_quantity=18 lbs, **When** an update specifies remaining_percentage=30, **Then** the system calculates target=7.5 lbs, creates a depletion of 10.5 lbs, and updates current_quantity to 7.5 lbs.

2. **Given** an inventory update for a UPC with no active inventory (all consumed), **When** imported, **Then** the system logs a warning and skips the update.

3. **Given** an inventory update for a UPC with multiple active inventory items, **When** imported, **Then** the adjustment applies to the oldest item (FIFO).

4. **Given** a percentage that would result in an increase (e.g., current=5 lbs, percentage=50% of original 25 lbs = 12.5 lbs), **When** imported, **Then** the system creates an addition adjustment of +7.5 lbs.

5. **Given** an inventory item with no linked purchase, **When** a percentage update is attempted, **Then** the system reports an error (cannot calculate without original quantity).

---

### User Story 5 - Round-Trip Data Integrity (Priority: P1)

The baker needs confidence that exporting her entire database and importing it back results in identical data - no loss, no corruption, no orphaned records.

**Why this priority**: Data integrity is foundational. Users must trust backup/restore.

**Independent Test**: Can be fully tested by populating a database with all entity types, exporting, resetting, importing, and comparing record counts and key field values.

**Acceptance Scenarios**:

1. **Given** a database with recipes, events, inventory, purchases, and production records, **When** exported then imported in "replace" mode, **Then** all record counts match and key fields are identical.

2. **Given** an existing database with some records, **When** importing in "merge" mode, **Then** new records are added and existing records (matched by slug) are skipped without error.

---

### Edge Cases

- What happens when importing a v3.x format file? System rejects with clear message about version requirement.
- What happens when a recipe component references itself (circular)? Validation prevents import.
- What happens when import file has invalid JSON syntax? Clear error message before any data changes.
- What happens when percentage update would result in negative inventory? Error, no change made.
- What happens when UPC matches multiple products? First match used (shouldn't occur with unique constraint).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST export recipes with yield_mode, base_yield, scaling_factor, and variants array
- **FR-002**: System MUST import recipes and create RecipeIngredient records with is_base flag and variant ingredient changes
- **FR-003**: System MUST export events with output_mode field and associated targets (assembly or production)
- **FR-004**: System MUST import events and create EventAssemblyTarget or EventProductionTarget records based on output_mode
- **FR-005**: System MUST validate yield_mode is "fixed" or "scaled" on import
- **FR-006**: System MUST validate output_mode is "bulk_count", "bundled", or "packaged" on import
- **FR-007**: System MUST validate all ingredient_slug references exist before creating recipe
- **FR-008**: System MUST validate all finished_unit_slug references exist before creating variant
- **FR-009**: System MUST reject v3.x format files with clear version error message
- **FR-010**: System MUST support import modes: "merge" (add new, skip existing) and "replace" (clear all, import fresh)
- **FR-011**: System MUST import purchases from JSON files containing UPC, price, quantity, supplier, and timestamp
- **FR-012**: System MUST match purchase UPCs against existing product.upc_code field
- **FR-013**: System MUST provide resolution workflow for unknown UPCs: map to existing, create new, or skip
- **FR-014**: System MUST create both Purchase and InventoryItem records for each imported purchase
- **FR-015**: System MUST import inventory updates specifying remaining_percentage (0-100)
- **FR-016**: System MUST calculate quantity adjustments from percentage using linked purchase's original quantity
- **FR-017**: System MUST apply percentage adjustments to oldest active inventory item (FIFO)
- **FR-018**: System MUST create InventoryDepletion records for all adjustments (audit trail)
- **FR-019**: System MUST prevent adjustments that would result in negative inventory
- **FR-020**: System MUST provide both programmatic and command-line interfaces for all import/export functions
- **FR-021**: System MUST report import results: success count, skip count, error count with details

### Key Entities

- **Recipe**: Extended with yield_mode (fixed/scaled), base_yield, scaling_factor; variants array linking to FinishedUnits
- **RecipeIngredient**: Extended with is_base flag to distinguish base vs variant ingredients
- **Event**: Extended with output_mode (bulk_count/bundled/packaged) determining which targets apply
- **Purchase Import Record**: UPC, price, quantity, supplier, timestamp - maps to Product via UPC matching
- **Inventory Update Record**: UPC, remaining_percentage - calculates adjustment from original purchase quantity

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can export and import a complete database (all entity types) with 100% data fidelity in under 30 seconds for typical dataset sizes (500 records)
- **SC-002**: Recipe round-trip preserves yield_mode, base_yield, variants, and all ingredient relationships with zero data loss
- **SC-003**: Event round-trip preserves output_mode and all assembly/production targets with zero data loss
- **SC-004**: Purchase imports via UPC achieve 90%+ automatic matching rate for products with UPC codes assigned
- **SC-005**: Unknown UPC resolution allows users to resolve each item in under 30 seconds (map, create, or skip)
- **SC-006**: Percentage-based inventory updates calculate correct quantities matching manual calculations within rounding tolerance
- **SC-007**: All import errors produce actionable messages identifying the specific record and field causing the issue
- **SC-008**: Import operations are atomic - failures roll back completely with no partial data changes

## Assumptions

- F037 Recipe Redesign models (yield_mode, variants) are already in the database schema
- F039 Event output_mode field is already in the Event model
- Products have optional upc_code field for UPC matching
- InventoryItem records are linked to Purchase records for percentage calculation
- User is comfortable with JSON file format for import/export operations
