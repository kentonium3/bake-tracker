# Feature Specification: Import/Export System Phase 1

**Feature Branch**: `049-import-export-phase1`
**Created**: 2026-01-12
**Status**: Draft
**Input**: Design document `docs/design/F049_import_export.md` (v4.0)

## Overview

Complete the backup/restore capability and enable AI-augmented data workflows by:
- Adding 8 missing entities to full backup (achieving complete 14-entity backup)
- Expanding context-rich exports to all catalog entities
- Adding materials catalog import support
- Enabling transaction imports (purchases and inventory adjustments)
- Redesigning UI to clearly distinguish export types and import purposes

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Complete System Backup (Priority: P1)

As a user, I want to create a full backup of my entire system so that I can restore my complete data state after a database reset or migration.

**Why this priority**: Without complete backup, users risk data loss. Current backup is missing 8 entities, making restore incomplete. This is foundational for the migration strategy (reset/re-import).

**Independent Test**: Export full backup, reset database, import backup, verify all 14 entity types restored with correct counts.

**Acceptance Scenarios**:

1. **Given** a database with data in all entity types, **When** user exports full backup, **Then** backup folder contains 14 entity files plus manifest.json with accurate counts
2. **Given** a full backup export, **When** user restores to empty database, **Then** all entities restored with matching counts from manifest
3. **Given** some entity types have zero records, **When** user exports full backup, **Then** those entities export as empty arrays (not omitted)

---

### User Story 2 - Import Materials Catalog (Priority: P2)

As a user, I want to import materials and material products from a JSON file so that I can bulk-add my non-food supplies without manual data entry.

**Why this priority**: Materials catalog import is broken (fails silently). This blocks the mobile AI-assisted workflow for adding materials purchased at stores.

**Independent Test**: Create materials JSON file, import via UI, verify materials appear in Materials tab with correct hierarchy and relationships.

**Acceptance Scenarios**:

1. **Given** a JSON file with materials data, **When** user imports as catalog, **Then** materials created in database and visible in Materials tab
2. **Given** a JSON file with material_products referencing materials by slug, **When** user imports, **Then** material_products linked correctly to parent materials
3. **Given** ADD_ONLY mode selected, **When** importing materials that already exist, **Then** existing materials skipped (not duplicated or updated)
4. **Given** AUGMENT mode selected, **When** importing materials that already exist, **Then** existing materials updated with new field values

---

### User Story 3 - Context-Rich Catalog Export (Priority: P3)

As a user, I want to export my catalog data with full context (hierarchy paths, relationships, computed values) so that AI tools can understand and augment my data.

**Why this priority**: Enables AI-augmented workflows. Current context-rich export only supports 3 entities; needs ingredients, materials, and recipes.

**Independent Test**: Export ingredients context-rich, verify output includes hierarchy paths, related products, and computed inventory values.

**Acceptance Scenarios**:

1. **Given** ingredients with category hierarchy, **When** user exports context-rich, **Then** export includes full hierarchy paths (e.g., "Flours & Starches > Wheat Flours > All-Purpose")
2. **Given** ingredients with associated products, **When** user exports context-rich, **Then** export includes nested product data
3. **Given** ingredients with inventory, **When** user exports context-rich, **Then** export includes computed inventory totals and average costs
4. **Given** recipes with nested ingredients, **When** user exports context-rich, **Then** export includes embedded ingredient details and computed costs

---

### User Story 4 - Import Purchase Transactions (Priority: P4)

As a user, I want to import purchase transactions from a JSON file so that I can record purchases made via mobile scanning without manual entry.

**Why this priority**: Enables the BT Mobile purchase scanning workflow. Users scan items at store, AI creates JSON, import adds to inventory.

**Independent Test**: Create purchases JSON file, import via UI, verify purchase records created and inventory quantities increased.

**Acceptance Scenarios**:

1. **Given** a JSON file with purchase transactions, **When** user imports as purchases, **Then** purchase records created in database
2. **Given** valid purchases imported, **When** checking inventory, **Then** inventory quantities increased by purchase amounts
3. **Given** purchases for products with existing inventory, **When** imported, **Then** weighted average costs recalculated correctly
4. **Given** a purchase with negative quantity, **When** user attempts import, **Then** import rejected with clear error message
5. **Given** a purchase referencing non-existent product slug, **When** user attempts import, **Then** import rejected with clear error identifying the invalid slug

---

### User Story 5 - Import Inventory Adjustments (Priority: P5)

As a user, I want to import inventory adjustment transactions so that I can record spoilage, waste, and corrections from mobile inventory checks.

**Why this priority**: Enables the BT Mobile inventory adjustment workflow. Users check inventory, AI creates adjustment JSON, import updates quantities.

**Independent Test**: Create adjustments JSON file with negative quantities, import via UI, verify adjustment records created and inventory decreased.

**Acceptance Scenarios**:

1. **Given** a JSON file with negative-quantity adjustments, **When** user imports as adjustments, **Then** adjustment records created in database
2. **Given** valid adjustments imported, **When** checking inventory, **Then** inventory quantities decreased by adjustment amounts
3. **Given** an adjustment with positive quantity, **When** user attempts import, **Then** import rejected with clear error (increases only via purchases)
4. **Given** an adjustment without reason code, **When** user attempts import, **Then** import rejected with error requiring reason code
5. **Given** an adjustment exceeding available inventory, **When** user attempts import, **Then** import rejected (cannot create negative inventory)

---

### User Story 6 - Context-Rich Import with Auto-Detection (Priority: P6)

As a user, I want to import AI-augmented context-rich files and have the system automatically detect the format so that augmented data merges correctly without manual format selection.

**Why this priority**: Completes the AI augmentation loop. User exports context-rich, AI augments, user imports augmented data.

**Independent Test**: Export context-rich, modify editable fields, import, verify editable fields updated and computed fields ignored.

**Acceptance Scenarios**:

1. **Given** a context-rich format file, **When** user imports, **Then** system auto-detects format and displays to user for confirmation
2. **Given** context-rich import with augmented editable fields, **When** imported, **Then** editable fields merged with existing records
3. **Given** context-rich import with modified computed fields (inventory, hierarchy), **When** imported, **Then** computed fields ignored (not imported)
4. **Given** a normalized format file, **When** user imports, **Then** system auto-detects as normalized (not context-rich)

---

### User Story 7 - Redesigned Import/Export UI (Priority: P7)

As a user, I want clear UI that distinguishes between export types and import purposes so that I choose the right option for my task.

**Why this priority**: Current UI is confusing - doesn't distinguish export types or support transaction imports. This makes all capabilities accessible.

**Independent Test**: Navigate export/import dialogs, verify clear labels, purpose explanations, and appropriate options for each type.

**Acceptance Scenarios**:

1. **Given** user opens export dialog, **When** viewing options, **Then** sees 3 clearly labeled export types with purpose explanations
2. **Given** user selects Full Backup export, **When** proceeding, **Then** no entity selection shown (always exports all)
3. **Given** user selects Catalog export, **When** proceeding, **Then** entity selection and format selection available
4. **Given** user opens import dialog, **When** viewing options, **Then** sees 4 clearly labeled import purposes (Backup Restore, Catalog, Purchases, Adjustments)
5. **Given** user selects file for import, **When** file loaded, **Then** format auto-detected and displayed for confirmation

---

### Edge Cases

- What happens when importing a backup from a different schema version? (Answer: External transformation required before import - per migration strategy)
- What happens when context-rich export references deleted entities? (Answer: Export current state only, deleted entities not included)
- What happens when purchase import has duplicate transaction? (Answer: Duplicate detection based on product/date/cost combination, duplicates skipped)
- What happens when materials import has circular category references? (Answer: Validation rejects circular references)
- What happens when adjustment import reason code is not in allowed list? (Answer: Validation rejects with list of valid reason codes)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST export all 14 entity types in full backup (ingredients, products, recipes, suppliers, purchases, inventory_items, materials, material_products, material_units, material_purchases, finished_goods, events, production_runs, consumption_records)
- **FR-002**: System MUST include manifest.json with entity counts in full backup export
- **FR-003**: System MUST export empty entities as empty arrays (not omit them)
- **FR-004**: System MUST use slug-based references in all exports (not database IDs)
- **FR-005**: System MUST support context-rich export for ingredients, materials, and recipes
- **FR-006**: System MUST include hierarchy paths in context-rich exports (not just parent_id)
- **FR-007**: System MUST include nested relationships in context-rich exports
- **FR-008**: System MUST include computed values (inventory, costs) in context-rich exports
- **FR-009**: System MUST support materials and material_products in catalog import
- **FR-010**: System MUST resolve material_slug references during import (matching ingredient pattern)
- **FR-011**: System MUST support ADD_ONLY and AUGMENT modes for catalog import
- **FR-012**: System MUST report created/updated/skipped/error counts after import
- **FR-013**: System MUST auto-detect import format (normalized vs context-rich)
- **FR-014**: System MUST extract only editable fields from context-rich imports (ignore computed fields)
- **FR-015**: System MUST support purchase transaction imports
- **FR-016**: System MUST validate purchases have positive quantities
- **FR-017**: System MUST update inventory and recalculate costs after purchase import
- **FR-018**: System MUST detect and skip duplicate purchases
- **FR-019**: System MUST support inventory adjustment imports
- **FR-020**: System MUST validate adjustments have negative quantities only
- **FR-021**: System MUST require reason code for adjustments (spoilage, waste, correction, other)
- **FR-022**: System MUST prevent adjustments that would create negative inventory
- **FR-023**: System MUST provide clear UI distinguishing 3 export types with purpose explanations
- **FR-024**: System MUST provide clear UI distinguishing 4 import purposes
- **FR-025**: System MUST display auto-detected format to user for confirmation

### Key Entities

- **Ingredients**: Food items used in recipes, with category hierarchy and associated products
- **Products**: Specific purchasable items (brands/packages) linked to ingredients
- **Materials**: Non-food supplies (packaging, decorations) with category hierarchy
- **Material Products**: Specific purchasable material items linked to materials
- **Material Units**: Unit definitions for materials
- **Recipes**: Production instructions referencing ingredients
- **Suppliers**: Vendors for products and materials
- **Purchases**: Transaction records for product/material acquisitions
- **Material Purchases**: Transaction records for material acquisitions
- **Inventory Items**: Current stock levels and costs
- **Finished Goods**: Completed recipe outputs
- **Events**: Production events (holidays, occasions)
- **Production Runs**: Batch production records
- **Consumption Records**: Inventory consumption tracking

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Full backup export includes all 14 entity types with accurate manifest counts
- **SC-002**: Complete system state can be restored from backup (round-trip test passes)
- **SC-003**: Context-rich export available for ingredients, materials, and recipes with hierarchy paths
- **SC-004**: Materials import creates records visible in Materials tab within 5 seconds of import completion
- **SC-005**: Material products slug resolution achieves 100% accuracy (no orphaned references)
- **SC-006**: Purchase import increases inventory quantities correctly (verified by inventory query)
- **SC-007**: Inventory adjustment import decreases quantities correctly (verified by inventory query)
- **SC-008**: Positive adjustment attempts rejected 100% of the time with clear error
- **SC-009**: Format auto-detection correctly identifies normalized vs context-rich in 100% of test cases
- **SC-010**: User can complete export workflow (select type, export file) in under 30 seconds
- **SC-011**: User can complete import workflow (select file, confirm format, import) in under 60 seconds
- **SC-012**: All exports use slug references (zero database IDs in export files)
- **SC-013**: Materials import pattern matches ingredients import exactly (same service structure, error handling)

## Out of Scope

- Finished goods import (deferred - not needed yet)
- Recipe import (deferred - catalog import sufficient for now)
- Production runs export (deferred - full backup includes if needed)
- Schema version validation (removed - external transformation approach preferred)
- Initial inventory import (separate feature, not part of Phase 1)

## Assumptions

- Existing ingredient import pattern is correct and should be replicated for materials
- Existing view_products.json structure is correct and should be replicated for other context-rich exports
- Reason codes for adjustments are: spoilage, waste, correction, other
- Duplicate purchase detection uses combination of product slug, date, and cost
- Users understand the difference between catalog data and transaction data

## Dependencies

- Existing export service infrastructure
- Existing import service infrastructure
- Existing material catalog services
- Existing purchase and inventory services
- Current import/export UI dialogs (to be enhanced)

## References

- Design document: `docs/design/F049_import_export.md` (v4.0)
- Requirements document: `docs/requirements/req_import_export.md` (v2.0)
- Constitution: `.kittify/memory/constitution.md` (Principles I, II, III, IV, V, VI)
