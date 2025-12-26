# Feature Specification: Enhanced Export/Import System

**Feature Branch**: `030-enhanced-export-import`
**Created**: 2025-12-25
**Status**: Draft
**Input**: See docs/design/F030_enhanced_export_import.md for detailed design context

## Problem Statement

The current export/import system has critical gaps that block AI-assisted data augmentation and efficient test data management:

1. **Monolithic exports** - Single `sample_data.json` file with all entities, no FK resolution strategy
2. **No AI-friendly formats** - Cannot export products with ingredient context for UPC enrichment
3. **No partial import** - Cannot import just price updates without full entity records
4. **No FK resolution** - Import fails if IDs don't match (no slug/name-based matching)
5. **Manual entity creation** - Missing suppliers/products force exit, manual creation, re-import cycle
6. **No validation** - Import proceeds blindly, FK errors discovered at database level

**User Impact Example:**
> User shops at Costco, Wegmans, Penzeys, and Wilson's Farm (new supplier). AI tool generates `purchases.json` file. Import fails: "Supplier 'Wilson's Farm' not found". User must exit import, manually create supplier via UI, re-import file. If file also references new products, cycle repeats multiple times.

## User Scenarios & Testing

### User Story 1 - Export Products for AI Augmentation (Priority: P1)

User wants to export their product catalog with ingredient context so an AI tool can research and fill in missing UPC codes, correct brand names, or verify package sizes.

**Why this priority**: This is the primary use case driving the feature - enabling AI-assisted data enrichment. Without denormalized exports, the AI lacks context to make good decisions.

**Independent Test**: Can be fully tested by exporting products, manually editing UPC fields in the file, and verifying the data is in a usable format.

**Acceptance Scenarios**:

1. **Given** a database with products linked to ingredients and suppliers, **When** user exports the products view, **Then** each product record includes ingredient name, ingredient category, supplier name, last purchase price, and current inventory quantity for context
2. **Given** an exported view file, **When** user opens it, **Then** the file clearly documents which fields are editable vs read-only context
3. **Given** products without UPC codes, **When** user exports the products view, **Then** upc_code fields show null and can be filled in by AI or manually

---

### User Story 2 - Import AI-Enriched Data (Priority: P1)

User has an AI-enriched products file with updated UPC codes and wants to import those updates back into the database without overwriting other data.

**Why this priority**: This completes the export-enrich-import cycle. Without import capability, the export is useless.

**Independent Test**: Can be tested by modifying exported view file and importing to verify only editable fields are updated.

**Acceptance Scenarios**:

1. **Given** an exported products view with modified UPC codes, **When** user imports with merge mode, **Then** only the editable fields (brand, product_name, package_size, package_unit, upc_code, notes) are updated
2. **Given** an import file where products are identified by slug, **When** IDs don't match the database, **Then** system resolves FK via slug matching and updates the correct records
3. **Given** an import with skip_existing mode, **When** importing, **Then** only new records are added and existing records are not modified

---

### User Story 3 - Import Data with Missing References (Priority: P1)

User imports a purchases file that references a new supplier not in the database. Instead of failing, the system guides user through creating or mapping the missing entity.

**Why this priority**: This eliminates the painful "fail, exit, create entity, re-import" cycle that makes data import frustrating.

**Independent Test**: Can be tested by importing a file with an unknown supplier name and verifying the resolution wizard appears.

**Acceptance Scenarios**:

1. **Given** a purchases file with unknown supplier "Wilson's Farm", **When** importing via UI, **Then** system shows resolution dialog with options: create new supplier, map to existing, or skip records
2. **Given** user chooses "Create new supplier", **When** user provides required fields (city, state, zip), **Then** supplier is created and import continues
3. **Given** user chooses "Map to existing", **When** user selects from fuzzy-searched list, **Then** records are imported with the mapped supplier_id
4. **Given** CLI import without --interactive flag, **When** FK error encountered, **Then** import fails with clear error report listing all missing references

---

### User Story 4 - Export Complete Database for Backup (Priority: P2)

User wants to export the entire database as a coordinated set of files that can be used to rebuild the database from scratch or transfer to another machine.

**Why this priority**: Supports the Constitution Principle VI (Export/Reset/Import) workflow but is secondary to the AI augmentation workflow.

**Independent Test**: Can be tested by exporting, deleting database, importing, and verifying all data is restored.

**Acceptance Scenarios**:

1. **Given** a populated database, **When** user runs export_complete command, **Then** system creates timestamped directory with individual entity files and manifest
2. **Given** an export set, **When** user examines manifest.json, **Then** it contains checksums, record counts, import order, and dependencies for each file
3. **Given** an export set, **When** user requests ZIP archive, **Then** system creates compressed archive of all export files

---

### User Story 5 - Import with Error Tolerance (Priority: P2)

User has a large import file with some records that have FK errors. User wants to import the valid records and deal with problem records later.

**Why this priority**: Practical workflow enhancement that prevents one bad record from blocking an entire import.

**Independent Test**: Can be tested by importing a file with some valid and some invalid records.

**Acceptance Scenarios**:

1. **Given** an import file with 100 records where 5 have FK errors, **When** importing with --skip-on-error flag, **Then** 95 records are imported successfully
2. **Given** records skipped during import, **When** import completes, **Then** skipped records are logged to `import_skipped_{timestamp}.json` with error details
3. **Given** a skipped records log file, **When** user reviews it, **Then** each entry shows the skip reason, FK error details, and original record data for correction

---

### User Story 6 - Preview Import Changes (Priority: P3)

User wants to see what changes an import would make before actually applying them.

**Why this priority**: Safety feature that builds confidence, but not essential for core functionality.

**Independent Test**: Can be tested by running dry-run and verifying no database changes occur.

**Acceptance Scenarios**:

1. **Given** an import file, **When** user runs import with --dry-run flag, **Then** system reports what would be added/updated without modifying database
2. **Given** dry-run output, **When** user reviews it, **Then** output clearly shows counts: X new, Y updates, Z skipped

---

### Edge Cases

- **Duplicate slugs in entity files**: For entity imports (suppliers, ingredients, products), import first occurrence and skip subsequent duplicates with warning. For transaction records (purchases, inventory), duplicate FK slug references are expected and valid.
- How does system handle circular dependencies (should not occur with current entities, but validate)?
- **User cancellation during FK resolution**: Prompt user to choose between keeping already-imported records or rolling back all changes.
- How does system handle very large files (>10,000 records)?
- **Checksum mismatch**: Warn and prompt user to continue or abort. Log the mismatch and user's decision.
- **Unknown fields (forward compatibility)**: Warn about unknown fields, then import known fields only.

## Requirements

### Functional Requirements

**Export - Coordinated Sets:**
- **FR-001**: System MUST export complete database to individual entity files with manifest
- **FR-002**: System MUST include import order and dependencies in manifest
- **FR-003**: System MUST calculate and store SHA256 checksums for each exported file
- **FR-004**: System MUST include both ID and slug/name for each FK field (for portable resolution)
- **FR-005**: System MUST support ZIP archive creation for exports

**Export - Denormalized Views:**
- **FR-006**: System MUST export denormalized products view with ingredient and supplier context
- **FR-007**: System MUST export denormalized inventory view with product and purchase context
- **FR-008**: System MUST export denormalized purchases view with product and supplier context
- **FR-009**: System MUST document editable vs read-only fields in each view file
- **FR-010**: System MUST use standard persistent filenames for views (view_products.json, etc.)

**Import - Core:**
- **FR-011**: System MUST validate manifest checksums before importing coordinated sets
- **FR-012**: System MUST resolve FK references via slug/name when IDs don't match
- **FR-013**: System MUST support merge mode (update existing, add new)
- **FR-014**: System MUST support skip_existing mode (only add new records)
- **FR-015**: System MUST ignore read-only context fields when importing denormalized views

**Import - Interactive FK Resolution:**
- **FR-016**: System MUST provide interactive FK resolution in UI (default behavior)
- **FR-017**: System MUST provide interactive FK resolution in CLI (via --interactive flag)
- **FR-018**: System MUST support creating new entities during import (Suppliers, Ingredients, Products)
- **FR-019**: System MUST support mapping to existing entities with fuzzy search
- **FR-020**: System MUST support skipping records with unresolved FKs
- **FR-021**: System MUST resolve dependencies in correct order (Ingredient before Product)

**Import - Error Handling:**
- **FR-022**: System MUST support skip-on-error mode via --skip-on-error flag
- **FR-023**: System MUST log skipped records to timestamped JSON file
- **FR-024**: System MUST support dry-run mode for previewing changes (CLI only)
- **FR-025**: CLI default MUST be fail-fast (no silent failures)
- **FR-026**: System MUST log all import errors, warnings, and user resolution decisions for diagnostics and automation replay

**CLI Interface:**
- **FR-027**: System MUST provide `export_complete` command with --output and --zip flags
- **FR-028**: System MUST provide `export_view` command for denormalized views
- **FR-029**: System MUST provide `import_view` command with --mode, --interactive, --skip-on-error, --dry-run flags
- **FR-030**: System MUST provide `validate_export` command for manifest verification

**UI Integration:**
- **FR-031**: System MUST add File > Import > Import View menu item
- **FR-032**: System MUST provide import dialog with file chooser and mode selection
- **FR-033**: System MUST provide interactive FK resolution wizard (dialogs)
- **FR-034**: System MUST show results summary dialog after import

### Key Entities

No new database entities required. Feature operates on existing entities:

- **Supplier**: Vendor/store information (name, city, state, zip)
- **Ingredient**: Generic ingredient definitions (slug, display_name, category)
- **Product**: Brand-specific products linked to Ingredients and Suppliers
- **Purchase**: Purchase transactions linked to Products and Suppliers
- **InventoryItem**: Physical inventory linked to Products

**Export Artifacts** (file formats, not database entities):
- **Manifest**: Metadata file describing coordinated export set
- **Entity File**: Normalized export of single entity type with FK resolution fields
- **Denormalized View**: Context-rich export for AI augmentation workflows

## Clarifications

### Session 2025-12-25

- Q: How to handle duplicate slugs for same entity type in import file? → A: For entity files (suppliers, ingredients, products): import first occurrence, skip duplicates with warning. For transaction records (purchases, inventory): duplicate FK references are expected and valid.
- Q: How to handle checksum mismatch in coordinated export set? → A: Warn and prompt user to continue or abort. All import errors and user responses must be logged for diagnostics and automation purposes.
- Q: What happens when user cancels mid-way through interactive FK resolution? → A: Prompt user to choose: keep already-imported records or rollback all changes.
- Q: How to handle unknown fields in import file (forward compatibility)? → A: Warn about unknown fields, then import known fields only.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can complete export-edit-import cycle for product UPC enrichment in under 5 minutes (excluding AI processing time)
- **SC-002**: Import with missing FK references prompts for resolution within 2 seconds of detection
- **SC-003**: 95% of FK resolution scenarios are handled by the three options (create, map, skip)
- **SC-004**: Export/import round-trip produces identical database state (verified by automated test)
- **SC-005**: Users can import files with up to 1,000 records without noticeable delay (under 10 seconds)
- **SC-006**: Skip-on-error mode successfully imports valid records even when 20% of records have FK errors
- **SC-007**: Skipped records log provides sufficient detail for user to fix and re-import without external reference
