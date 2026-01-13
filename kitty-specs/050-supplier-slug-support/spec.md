# Feature Specification: Supplier Slug Support

**Feature Branch**: `050-supplier-slug-support`
**Created**: 2026-01-12
**Status**: Draft
**Input**: User description: "See docs/design/F050_supplier_slug_support.md for this feature's inputs."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Export and Import Suppliers Across Environments (Priority: P1)

As a user managing data across development and production databases, I need suppliers to have portable identifiers (slugs) so that when I export my complete data and import it into a fresh database, all supplier references remain intact.

**Why this priority**: This is the core problem being solved. Without portable supplier identification, cross-environment data migration fails. Slugs enable reliable data portability.

**Independent Test**: Can be fully tested by exporting data with suppliers, importing into empty database, and verifying all supplier records are recreated with correct associations.

**Acceptance Scenarios**:

1. **Given** a database with 6 existing suppliers, **When** I export all data, **Then** each supplier in the export includes a unique slug field
2. **Given** an export file with suppliers containing slugs, **When** I import into a fresh database, **Then** all suppliers are created with their original slugs preserved
3. **Given** a supplier named "Wegmans" in Burlington, MA, **When** the system generates its slug, **Then** the slug is "wegmans_burlington_ma" (lowercase, underscores)
4. **Given** an online supplier named "King Arthur Baking", **When** the system generates its slug, **Then** the slug is "king_arthur_baking" (name only, no city/state)

---

### User Story 2 - Product Supplier Associations Preserved on Import (Priority: P1)

As a user importing product catalogs, I need products that reference preferred suppliers to correctly resolve those references by slug, so that my product-supplier associations survive the import process.

**Why this priority**: Products frequently reference suppliers. If these references break on import, the entire data migration is incomplete. This is a critical path.

**Independent Test**: Can be tested by exporting products with supplier associations, importing into fresh database (with suppliers imported first), and verifying products point to correct suppliers.

**Acceptance Scenarios**:

1. **Given** a product with preferred_supplier_slug "wegmans_burlington_ma" in import file, **When** I import the product, **Then** its preferred_supplier_id is set to the matching supplier's ID
2. **Given** a product referencing a supplier slug that doesn't exist in the database, **When** I import the product, **Then** the product imports successfully without a supplier association and a warning is logged
3. **Given** a product without any supplier reference in the import file, **When** I import the product, **Then** the product imports successfully without a supplier association
4. **Given** a legacy export file with preferred_supplier_id but no preferred_supplier_slug, **When** I import the product, **Then** the system falls back to ID-based matching (backward compatibility)

---

### User Story 3 - Migrate Existing Suppliers with Generated Slugs (Priority: P1)

As a system administrator, I need all existing suppliers in my database to receive auto-generated slugs during migration, so that they can participate in slug-based import/export immediately.

**Why this priority**: Existing data must be migrated before any slug-based operations can work. This is a prerequisite for all other functionality.

**Independent Test**: Can be tested by running migration on database with existing suppliers and verifying all have unique, correctly-formatted slugs.

**Acceptance Scenarios**:

1. **Given** a database with 6 existing suppliers without slugs, **When** migration runs, **Then** all 6 suppliers have unique slugs assigned
2. **Given** two physical suppliers with the same name in different cities, **When** migration generates slugs, **Then** each has a unique slug (city/state differentiates them)
3. **Given** a potential slug conflict (e.g., two suppliers would get same slug), **When** migration runs, **Then** the second supplier gets a numeric suffix (e.g., "_2")
4. **Given** the migration has already been run once, **When** migration runs again, **Then** existing slugs are preserved (idempotent operation)
5. **Given** a supplier with a malformed or non-standard slug (e.g., manually set), **When** migration runs, **Then** the slug is regenerated to match the standard pattern

---

### User Story 4 - Slug Immutability Prevents Reference Breakage (Priority: P2)

As a data integrity maintainer, I need supplier slugs to be immutable after creation, so that existing exports referencing those slugs remain valid even if supplier details change.

**Why this priority**: Immutability is critical for long-term data portability but secondary to basic import/export functionality. Systems work without this constraint initially.

**Independent Test**: Can be tested by attempting to modify a supplier's slug through service layer and verifying the operation is rejected.

**Acceptance Scenarios**:

1. **Given** a supplier with slug "wegmans_burlington_ma", **When** the supplier's name is updated to "Wegmans Market", **Then** the slug remains "wegmans_burlington_ma"
2. **Given** an attempt to directly modify a supplier's slug via service layer, **When** the update is processed, **Then** the slug modification is rejected with an appropriate error

---

### User Story 5 - Dry-Run Import Preview (Priority: P3)

As a cautious user, I want to preview supplier import operations before committing them, so that I can review what will be created/updated without affecting my database.

**Why this priority**: Dry-run is a safety feature, valuable but not blocking for core functionality.

**Independent Test**: Can be tested by running import with dry-run flag and verifying no database changes occur while receiving accurate preview.

**Acceptance Scenarios**:

1. **Given** an import file with 3 new suppliers and 2 existing suppliers, **When** I run import in dry-run mode, **Then** the preview shows "3 new, 2 existing, 0 errors" without any database changes
2. **Given** an import file with invalid supplier data, **When** I run import in dry-run mode, **Then** the validation errors are reported without any database changes

---

### Edge Cases

- What happens when a supplier slug is empty or null at creation time? (Validation rejects it)
- What happens when slug contains invalid characters? (Normalization removes them)
- How does system handle identical supplier names in same city/state? (Numeric suffix conflict resolution per FR-004; explicit test in T011)
- What happens when importing a supplier that already exists by slug? (Merge mode: update; Skip mode: skip)
- How does product import handle missing supplier references? (Warning logged, product imports without supplier)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST add a `slug` field to Supplier model (String, max 100 chars, unique, indexed, non-nullable)
- **FR-002**: System MUST auto-generate slug on supplier creation using pattern: physical suppliers = `{name}_{city}_{state}`, online suppliers = `{name}`
- **FR-003**: System MUST normalize slugs to lowercase with spaces converted to underscores and non-alphanumeric characters removed (except underscores)
- **FR-004**: System MUST resolve slug conflicts by appending numeric suffixes (`_1`, `_2`, `_3`, etc.) matching existing Ingredient/Material patterns
- **FR-005**: System MUST prevent slug modification after initial creation (immutability)
- **FR-006**: System MUST validate slug uniqueness before saving
- **FR-007**: System MUST export suppliers in JSON format including slug field
- **FR-008**: System MUST import suppliers matching by slug (not name/city/state tuple)
- **FR-009**: System MUST support merge mode (update only explicitly provided fields for existing suppliers + add new) and skip mode (add new only) for supplier import
- **FR-010**: System MUST add `preferred_supplier_slug` and `preferred_supplier_name` to product export
- **FR-011**: System MUST resolve `preferred_supplier_slug` to `preferred_supplier_id` during product import
- **FR-012**: System MUST fall back to `preferred_supplier_id` for legacy files without slug fields (backward compatibility)
- **FR-013**: System MUST log warnings when supplier slug cannot be resolved during product import
- **FR-014**: System MUST support dry-run mode for supplier import (preview without DB changes)
- **FR-015**: System MUST migrate all existing suppliers with generated slugs
- **FR-016**: System MUST update test_data/suppliers.json with slug field for all suppliers

### Key Entities *(include if feature involves data)*

- **Supplier**: Existing entity enhanced with `slug` field (String, unique, indexed, non-nullable). Represents a vendor/retailer where products can be purchased. Two types: physical (with city/state/zip) and online (with website_url).
- **Product**: Existing entity with `preferred_supplier_id` FK. Export enhanced to include `preferred_supplier_slug` and `preferred_supplier_name`. Import enhanced to resolve supplier references by slug.

## Clarifications

### Session 2026-01-12

- Q: When a supplier already exists (matched by slug), which fields should be updated during merge mode? → A: Update only explicitly provided fields in the import file (sparse update semantics). New suppliers are always added regardless of mode.
- Q: If an existing supplier has a slug that doesn't match the generation pattern, should migration preserve or regenerate it? → A: Regenerate to match the standard pattern (enforce consistency)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All existing suppliers (6 records) have unique slugs after migration with zero null values
- **SC-002**: Supplier export creates complete suppliers.json with all fields including slug
- **SC-003**: Round-trip test succeeds: export all data -> fresh database -> import -> all supplier associations verified intact
- **SC-004**: Legacy import files (without supplier slugs) continue to import successfully with warnings
- **SC-005**: Product-supplier associations are correctly resolved by slug on import with 100% accuracy for valid references
- **SC-006**: Slug generation follows existing ingredient/material patterns exactly (code consistency)
- **SC-007**: Import dry-run mode correctly predicts all changes without modifying database
