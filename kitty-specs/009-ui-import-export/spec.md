# Feature Specification: UI Import/Export with v3.0 Schema

**Feature Branch**: `009-ui-import-export`
**Created**: 2025-12-04
**Status**: Draft
**Input**: User description: "Add File menu with Import/Export UI backed by v3.0 specification reflecting current schema"

## Clarifications

### Session 2025-12-04

- Q: Should spec require user choice between Merge and Replace import modes (per planning decision)? → A: Yes, update spec to require mode selection
- Q: How should unknown schema versions be handled? → A: Drop v2.0 compatibility; only v3.0 supported, reject all other versions with clear error

## Problem Statement

The application has CLI-based import/export utilities, but the primary user is non-technical and needs a graphical interface to backup and restore data. Additionally, the import/export specification (v2.0) is stale - it doesn't reflect schema changes from Features 006-008 including deprecated entities (Bundles -> FinishedGoodsPackage) and new production tracking models.

## Background

**Current state**:
- CLI tools exist: `src/utils/import_export_cli.py` with export/import commands
- v2.0 spec exists: `docs/import_export_specification.md` (dated Nov 2024, now outdated)
- Test data exists: `test_data/sample_data.json` (v2.0 format, won't import correctly)
- No File menu: Application has no menu bar; import/export requires command line

**Schema changes since v2.0**:
- Feature 006: Event planning restored with updated relationships
- Feature 007: Shopping list variant integration
- Feature 008: Production tracking - new models (ProductionRecord, package status fields)
- Bundles deprecated -> FinishedGoodsPackage relationship

## User Scenarios & Testing

### User Story 1 - Export Data Backup (Priority: P1)

As a user, I want to back up all my baking data to a file so I can restore it if something goes wrong.

**Why this priority**: Data protection is the primary user need. Without reliable backup, users risk losing valuable recipe and inventory data.

**Independent Test**: Can be fully tested by clicking File -> Export Data, selecting a location, and verifying a valid JSON file is created with all data.

**Acceptance Scenarios**:

1. **Given** the application is running with data in the database, **When** I click File -> Export Data and select a save location, **Then** all data is exported to a JSON file and I see confirmation "Exported N records to [filename]"

2. **Given** the application is running, **When** I click File -> Export Data, **Then** I see a file save dialog that defaults to a sensible filename (e.g., "bake-tracker-backup-2024-12-04.json")

3. **Given** I am exporting data, **When** the export completes successfully, **Then** the exported file contains all entity types in valid JSON format

---

### User Story 2 - Import Data Restore (Priority: P1)

As a user, I want to restore my data from a backup file so I can recover from data loss or set up a new installation.

**Why this priority**: Restore is the complement to backup - both are essential for data protection.

**Independent Test**: Can be fully tested by selecting a valid backup file via File -> Import Data and verifying data appears in the application.

**Acceptance Scenarios**:

1. **Given** the application is running, **When** I click File -> Import Data, **Then** I see a dialog with file selection and mode choice (Merge or Replace)

2. **Given** I select Merge mode and import a valid v3.0 JSON file, **When** import completes, **Then** I see a summary showing "X records imported, Y skipped (duplicates), Z errors"

3. **Given** I select Replace mode, **When** I confirm the warning about clearing existing data, **Then** all existing data is cleared before importing the new data

4. **Given** I am importing a file, **When** an error occurs during import, **Then** the entire import is rolled back and I see a user-friendly error message explaining what went wrong

5. **Given** I have exported data and cleared the database, **When** I import the exported file in Replace mode, **Then** all data is restored with full integrity (round-trip test)

---

### User Story 3 - v3.0 Specification Documentation (Priority: P1)

As a developer or power user, I want a clear specification document for the v3.0 format so I understand the data structure and can create compatible files.

**Why this priority**: Essential foundation - the UI and service layer depend on a well-defined format.

**Independent Test**: Specification document exists at `docs/import_export_specification.md`, covers all entities, includes examples, and documents entity ordering for referential integrity.

**Acceptance Scenarios**:

1. **Given** the v3.0 specification is complete, **When** I read it, **Then** I can understand all exportable entities, their relationships, and validation rules

2. **Given** the old v2.0 spec exists, **When** v3.0 is created, **Then** v2.0 is archived at `docs/archive/import_export_specification_v2.md` for historical reference

---

### User Story 4 - Sample Data Refresh (Priority: P2)

As a developer or tester, I want updated sample data that works with the current schema so I can test the application with realistic data.

**Why this priority**: Enables testing but not user-facing functionality.

**Independent Test**: `test_data/sample_data.json` imports cleanly with zero errors into a fresh database.

**Acceptance Scenarios**:

1. **Given** a fresh database, **When** I import `test_data/sample_data.json`, **Then** import completes with zero errors and all entity types are populated

2. **Given** sample data is imported, **When** I navigate the application, **Then** I see realistic test data for all features (ingredients, recipes, events, packages, production records, etc.)

---

### Edge Cases

- **User cancels file dialog**: Operation is cancelled, no changes made, return to application
- **Corrupted/malformed JSON**: Reject with user-friendly error (FR-009)
- **Export location not writable**: Show error message with path (FR-008)
- **Duplicate records during Merge**: Skip duplicates, include count in summary (FR-013a)
- **Import interrupted**: Transaction rollback ensures no partial data (FR-010)
- **Very large datasets**: Progress indication shown; performance targets apply (<60s for <1000 records)
- **Unsupported schema version**: Reject with clear error indicating v3.0 required (FR-018)

## Requirements

### Functional Requirements

**File Menu**:
- **FR-001**: Application MUST display a menu bar with a "File" menu
- **FR-002**: File menu MUST contain "Import Data..." option that opens a file selection dialog
- **FR-003**: File menu MUST contain "Export Data..." option that opens a file save dialog
- **FR-004**: File dialogs MUST filter for JSON files (*.json)

**Export**:
- **FR-005**: Export MUST include all data from all exportable entity types
- **FR-006**: Export MUST produce valid JSON conforming to v3.0 specification
- **FR-007**: Export MUST show confirmation message with record count on success
- **FR-008**: Export MUST show user-friendly error message on failure

**Import**:
- **FR-009**: Import MUST validate file format before processing
- **FR-010**: Import MUST use database transaction - rollback entirely on any error
- **FR-011**: Import MUST respect entity ordering for referential integrity
- **FR-012**: Import MUST show summary dialog with imported/skipped/error counts
- **FR-013**: Import dialog MUST offer mode selection: Merge (add new, skip duplicates) or Replace (clear all data first)
- **FR-013a**: Merge mode MUST skip duplicate records and include skip count in summary
- **FR-013b**: Replace mode MUST prompt for confirmation before clearing existing data

**v3.0 Specification**:
- **FR-014**: Specification MUST document all current entities from Features 001-008
- **FR-015**: Specification MUST include entity relationship diagram or dependency order
- **FR-016**: Specification MUST provide JSON examples for each entity type
- **FR-017**: Specification MUST document validation rules and constraints

**Version Handling**:
- **FR-018**: Import MUST reject files with unsupported schema versions (non-v3.0) with a clear error message indicating the required version

**Service Layer**:
- **FR-019**: import_export_service.py MUST be refactored to support v3.0 format
- **FR-020**: Service MUST include ProductionRecord and PackageStatus in export/import

### Key Entities

All exportable entities (in dependency order for import):

1. **UnitConversions**: Base unit conversion factors
2. **Ingredients**: Base ingredient definitions (referenced by Variants, RecipeIngredients)
3. **Variants**: Specific brands/sizes of ingredients (referenced by Purchases, PantryItems)
4. **Purchases**: Purchase history for variants
5. **PantryItems**: Current inventory with FIFO lots
6. **Recipes**: Recipe definitions (referenced by RecipeIngredients, FinishedUnits)
7. **RecipeIngredients**: Ingredient usage in recipes
8. **FinishedUnits**: Yield definitions for recipes
9. **FinishedGoods**: Composite finished products
10. **Compositions**: FinishedUnit -> FinishedGood relationships
11. **Packages**: Gift package definitions
12. **PackageFinishedGoods**: FinishedGood -> Package relationships
13. **Recipients**: Gift recipients
14. **Events**: Holiday/occasion events
15. **EventRecipientPackages**: Package assignments (includes status field)
16. **ProductionRecords**: Batch production with FIFO cost capture

## Success Criteria

### Measurable Outcomes

- **SC-001**: User can complete a full export in under 30 seconds for typical dataset (< 1000 records)
- **SC-002**: User can complete a full import in under 60 seconds for typical dataset
- **SC-003**: Round-trip test (export -> clear DB -> import) achieves 100% data integrity
- **SC-004**: Sample data file imports with zero errors on a fresh database
- **SC-005**: Non-technical user can successfully backup and restore data without documentation
- **SC-006**: Import error messages are understandable to non-technical users (no stack traces)
- **SC-007**: v3.0 specification covers 100% of exportable entities with examples

## Scope

### In Scope

1. Schema audit of `src/models/` to document current entity structure
2. v3.0 Import/Export specification document
3. Archive v2.0 specification for historical reference
4. Refactored import_export_service.py for v3.0 format
5. Updated `test_data/sample_data.json` in v3.0 format
6. File menu UI with Import/Export dialogs
7. Progress indication for large datasets
8. Error handling with user-friendly messages

### Out of Scope

- CSV import/export (JSON only for now)
- Selective import (import all or nothing)
- v2.0 or legacy format compatibility (only v3.0 supported)
- Version migration service (v1.0 -> v3.0 automatic upgrade)
- Cloud backup integration
- Database file backup (separate from JSON export)

## Dependencies

- **Requires**: Features 005-008 complete (stable schema)
- **Uses**: Existing `import_export_service.py` as starting point

## Assumptions

1. CustomTkinter supports menu bars via standard tkinter Menu widget
2. Main window (`src/ui/main_window.py`) can accommodate a menu bar addition
3. Existing import_export_service.py provides a solid foundation for refactoring
4. SQLite transactions provide sufficient atomicity for import rollback
5. Typical user datasets are under 1000 records total
6. Users have local file system access for save/open operations

## Technical Notes

- Main window (`main_window.py`) will need menu bar added
- Import should use transaction - rollback on any error
- Consider adding "last export date" to status bar after implementation
- Test data should include all entity types listed in Key Entities section
