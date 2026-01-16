# Feature Specification: CLI Import/Export Parity

**Feature Branch**: `054-cli-import-export-parity`
**Created**: 2026-01-15
**Status**: Draft
**Input**: See docs/design/F054_cli_import_export_parity.md

## Overview

The CLI import/export functionality has fallen behind UI capabilities after F047-F053 refactoring. This feature brings CLI to full parity with UI import/export capabilities, ensuring AI-assisted workflows and mobile JSON ingestion work seamlessly through the command-line interface.

**Key Gaps Being Addressed:**
- Materials entities (Material, MaterialProduct, MaterialCategory, MaterialSubcategory) not exposed in CLI
- Suppliers not accessible despite F050/F051 backend support
- Catalog import functionality incomplete
- Context-rich "aug" exports not exposed (F053)
- No backup/restore commands (16-entity coordinated export from F049)
- Purchase tracking exports missing (F043)

## User Scenarios & Testing

### User Story 1 - Full Database Backup via CLI (Priority: P1)

A developer or automated script needs to create a complete backup of all 16 entity types for disaster recovery, migration, or testing purposes.

**Why this priority**: Data protection is critical. Users need reliable backup/restore before any other CLI operations. This enables safe testing of other features.

**Independent Test**: Can be fully tested by running `backup` command and verifying all 16 entity files are created with valid checksums in manifest.

**Acceptance Scenarios**:

1. **Given** a database with data across multiple entity types, **When** user runs `backup` command, **Then** system creates timestamped directory with 16 JSON files and manifest.json containing checksums
2. **Given** a valid backup directory, **When** user runs `restore` command, **Then** system validates manifest, imports all entities in correct dependency order, and reports success
3. **Given** a corrupted backup (modified file), **When** user runs `backup-validate`, **Then** system reports which files have checksum mismatches
4. **Given** multiple backup directories exist, **When** user runs `backup-list`, **Then** system displays available backups with timestamps and entity counts

---

### User Story 2 - Context-Rich Export for AI Workflows (Priority: P1)

An AI assistant or mobile app needs to export data with human-readable context (resolved foreign keys) for external processing, then re-import modified data with automatic FK resolution.

**Why this priority**: AI-assisted workflows are a core use case. Context-rich "aug" files enable external data generation and modification without requiring knowledge of internal IDs.

**Independent Test**: Can be fully tested by exporting aug file, modifying it externally, and re-importing with FK resolution.

**Acceptance Scenarios**:

1. **Given** products exist with ingredient and supplier references, **When** user runs `aug-export -t products`, **Then** system creates `aug_products.json` with resolved names instead of IDs
2. **Given** an aug file with human-readable references, **When** user runs `aug-import` in interactive mode, **Then** system resolves FKs and prompts for ambiguous matches
3. **Given** user wants all context-rich exports, **When** user runs `aug-export -t all`, **Then** system creates aug files for all 7 supported entity types
4. **Given** an aug file with invalid format, **When** user runs `aug-validate`, **Then** system reports specific schema violations

---

### User Story 3 - Catalog Import/Export (Priority: P2)

A user needs to export catalog data (ingredients, products, recipes, materials) for sharing with another installation or for bulk editing, then import modified catalogs.

**Why this priority**: Catalog operations are common for data migration and bulk updates. Less critical than backup (which includes catalogs) but important for targeted operations.

**Independent Test**: Can be fully tested by exporting specific entity types, modifying JSON, and re-importing with mode selection.

**Acceptance Scenarios**:

1. **Given** catalog data exists, **When** user runs `catalog-export --entities ingredients,products`, **Then** system creates JSON files for only those entity types
2. **Given** a catalog export directory, **When** user runs `catalog-import --mode augment`, **Then** system updates existing records and adds new ones without deleting
3. **Given** a catalog with schema errors, **When** user runs `catalog-validate`, **Then** system reports specific validation failures before import
4. **Given** user wants all catalog entities, **When** user runs `catalog-export` without --entities flag, **Then** system exports all 7 catalog entity types

---

### User Story 4 - Materials Entity Export (Priority: P2)

A user needs to export materials management data (materials, material products, categories, subcategories) for backup or external processing.

**Why this priority**: Materials management (F047) is a major feature but materials are not accessible via CLI. Required for complete backup/catalog operations.

**Independent Test**: Can be fully tested by exporting each materials entity type and verifying JSON structure matches UI export.

**Acceptance Scenarios**:

1. **Given** materials exist in database, **When** user runs `export-materials`, **Then** system creates JSON with all material records including hierarchy
2. **Given** material products with supplier references, **When** user runs `export-material-products`, **Then** system includes supplier slugs in export
3. **Given** materials exist, **When** user runs `catalog-export`, **Then** materials and material-products are included in output
4. **Given** materials exist, **When** user runs `aug-export -t materials`, **Then** system creates context-rich export with resolved category names

---

### User Story 5 - Supplier and Purchase Export (Priority: P3)

A user needs to export supplier information and purchase history for reporting or external analysis.

**Why this priority**: Supplier and purchase data complete the CLI parity. Lower priority because these are less frequently exported independently.

**Independent Test**: Can be fully tested by exporting suppliers/purchases and verifying format matches UI export.

**Acceptance Scenarios**:

1. **Given** suppliers exist, **When** user runs `export-suppliers`, **Then** system creates JSON with supplier records including slugs
2. **Given** purchases exist with supplier references, **When** user runs `export-purchases`, **Then** system includes supplier slugs in export
3. **Given** a backup is created, **When** examining backup contents, **Then** both suppliers and purchases are included

---

### Edge Cases

- What happens when backup directory already exists? (Prompt for overwrite or create timestamped subdirectory)
- How does restore handle missing entities in backup? (Report which entities are missing and continue with available)
- What happens during aug-import when FK cannot be resolved? (Interactive mode prompts user; non-interactive mode skips or fails based on --skip-on-error flag)
- How does catalog-import --mode replace handle foreign key constraints? (Import in dependency order to avoid constraint violations)
- What happens when exporting empty entity types? (Create empty JSON array, not skip file)

## Requirements

### Functional Requirements

**Backup/Restore Commands (FR-1xx)**

- **FR-101**: System MUST provide `backup` command that creates timestamped 16-entity coordinated export with manifest.json
- **FR-102**: System MUST provide `restore` command that validates manifest and imports all entities in dependency order
- **FR-103**: System MUST provide `backup-list` command that displays available backups with metadata
- **FR-104**: System MUST provide `backup-validate` command that verifies all file checksums match manifest
- **FR-105**: Backup command MUST support `--zip` flag to create compressed archive
- **FR-106**: Restore command MUST support `--mode` flag with add/augment/replace options
- **FR-107**: Restore command MUST support `--interactive` flag for FK resolution prompts

**Catalog Commands (FR-2xx)**

- **FR-201**: System MUST provide `catalog-export` command supporting 7 entity types
- **FR-202**: System MUST provide `catalog-import` command with mode selection (add/augment/replace)
- **FR-203**: System MUST provide `catalog-validate` command for pre-import schema validation
- **FR-204**: Catalog commands MUST support `--entities` flag for selective entity operations
- **FR-205**: Default catalog export MUST include all 7 entity types when --entities not specified

**Context-Rich Aug Commands (FR-3xx)**

- **FR-301**: System MUST provide `aug-export` command for context-rich exports with `aug_` prefix
- **FR-302**: System MUST provide `aug-import` command with FK resolution
- **FR-303**: System MUST provide `aug-validate` command for format validation
- **FR-304**: Aug-export MUST support `-t all` to export all 7 entity types
- **FR-305**: Aug-import MUST support `--interactive` flag for manual FK resolution
- **FR-306**: Aug-import MUST support `--skip-on-error` flag for batch processing

**Materials Commands (FR-4xx)**

- **FR-401**: System MUST provide `export-materials` command for material catalog
- **FR-402**: System MUST provide `export-material-products` command
- **FR-403**: System MUST provide `export-material-categories` command
- **FR-404**: System MUST provide `export-material-subcategories` command
- **FR-405**: Materials MUST be included in catalog-export operations
- **FR-406**: Materials MUST be included in backup operations

**Supplier/Purchase Commands (FR-5xx)**

- **FR-501**: System MUST provide `export-suppliers` command with slug field
- **FR-502**: System MUST provide `export-purchases` command with supplier references
- **FR-503**: Suppliers MUST be included in backup operations
- **FR-504**: Purchases MUST be included in backup operations

**Documentation (FR-6xx)**

- **FR-601**: Module docstring MUST document all commands with examples
- **FR-602**: Help text MUST be accurate and actionable for all commands
- **FR-603**: AI workflow patterns MUST be documented (aug export -> modify -> aug import)

**Compatibility (FR-7xx)**

- **FR-701**: Legacy commands (export, import, export-view) MUST remain functional
- **FR-702**: New commands MUST NOT break existing scripts using old commands
- **FR-703**: CLI output formats MUST match corresponding UI export formats exactly

### Key Entities

- **Backup Manifest**: JSON file containing entity list, file checksums, timestamp, and version info
- **Catalog Entity Types**: ingredients, products, recipes, finished-units, finished-goods, materials, material-products (7 types)
- **Aug Entity Types**: Same 7 types as catalog, with resolved FK context fields
- **Import Modes**: ADD_ONLY (skip existing), AUGMENT (update existing + add new), REPLACE (clear + import all)

## Success Criteria

### Measurable Outcomes

- **SC-001**: All 16 backup/restore operations complete successfully when tested against database with 1000+ records per entity type
- **SC-002**: CLI export output is byte-identical to UI export output for the same data
- **SC-003**: Aug-import resolves 95%+ of foreign keys automatically without user intervention in non-interactive mode
- **SC-004**: All new commands have help text accessible via `--help` flag
- **SC-005**: Backup/restore round-trip preserves 100% of data integrity (verified by checksum comparison)
- **SC-006**: CLI documentation covers all 15+ new commands with working examples
- **SC-007**: No existing CLI commands break after adding new commands (backward compatibility)

## Assumptions

- Existing service layer functions (coordinated_export_service, import_service) are stable and well-tested
- F053 context-rich export format uses `aug_` prefix (not legacy `view_` prefix)
- CLIFKResolver pattern from existing import-view command can be reused for new import commands
- 16-entity backup includes materials entities added in F047-F048

## Dependencies

- F047: Materials Management System (materials entities)
- F049: Coordinated Export Service (16-entity backup)
- F050/F051: Supplier Support (supplier slug field)
- F053: Context-Rich Export Fixes (aug_ prefix)
