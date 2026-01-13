# Feature Specification: Import/Export UI Rationalization

**Feature Branch**: `051-import-export-ui-rationalization`
**Created**: 2026-01-13
**Status**: Draft
**Input**: Design document F051_import_export_ui_rationalization.md

## Clarifications

### Session 2026-01-13

- Q: In the unified Import Data dialog, what is the sequencing for file selection vs purpose selection? → A: File-first: User selects file, then system auto-detects and suggests purpose, user can override
- Q: Does Context-Rich import support multi-entity files or only single-entity aug_*.json files? → A: Single-entity only; files include read-only context for AI augmentation (e.g., related supplier/ingredient info) but only primary entity's editable fields are consumed during import
- Q: What format should import log files use? → A: Plain text with headers (human-readable sections separated by headers)
- Q: For Context-Rich imports, when does schema validation occur relative to preprocessing? → A: After preprocessing; preprocessing converts aug_*.json to normalized format and validates FK references, then schema validation runs on normalized output using the same schemas as Catalog imports (avoids separate aug format schemas)
- Q: What feedback does the user see after an import completes successfully? → A: Modal dialog with summary showing counts (imported/skipped/failed) per entity, user dismisses

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Unified Import Workflow (Priority: P1)

A user wants to import data into the application. Currently there are three different menu options (Import Data, Import Catalog, Import Context-Rich), causing confusion about which to use. After this feature, users access a single Import Data dialog that handles all import types. The dialog follows a file-first flow: user selects a file, system auto-detects and suggests the appropriate purpose, user can override if needed.

**Why this priority**: This is the core consolidation that eliminates user confusion. Every import workflow depends on this unified entry point.

**Independent Test**: Can be fully tested by importing files through the unified dialog for each purpose type (Backup, Catalog, Purchases, Adjustments, Context-Rich).

**Acceptance Scenarios**:

1. **Given** a user wants to import any type of data, **When** they open File menu, **Then** they see only "Import Data" (no separate Import Catalog or Import Context-Rich options)
2. **Given** the Import Data dialog is open, **When** a user selects a file, **Then** the system auto-detects the file type and suggests the appropriate purpose
3. **Given** a user selects a purpose type, **When** they click Import, **Then** the import completes successfully using the appropriate workflow

---

### User Story 2 - Supplier Import/Export (Priority: P1)

A user wants to export their supplier list and later import it (or share with another instance). Currently suppliers cannot be exported from or imported through the UI despite backend support existing. After this feature, suppliers appear in the Export Catalog tab and are auto-detected during import.

**Why this priority**: Supplier data portability was promised in F050 but the UI was never connected. This blocks real-world backup/restore workflows.

**Independent Test**: Can be fully tested by exporting suppliers via Catalog tab checkbox, then importing the exported file and verifying supplier data appears correctly.

**Acceptance Scenarios**:

1. **Given** a user opens Export Data dialog Catalog tab, **When** viewing entity checkboxes, **Then** a "Suppliers" checkbox appears in alphabetical order with other entities
2. **Given** a user selects Suppliers checkbox and exports, **When** export completes, **Then** suppliers.json is included with slug field per F050 format
3. **Given** a user imports a file containing suppliers, **When** auto-detection runs, **Then** suppliers are detected and displayed with record count
4. **Given** a user imports suppliers via Catalog purpose, **When** import completes, **Then** all supplier records are created with correct slug values

---

### User Story 3 - Context-Rich Import Purpose (Priority: P2)

A user receives AI-augmented data files (with hierarchy paths and computed values) that need preprocessing before import. Previously this required a separate menu option. After this feature, Context-Rich is the 5th purpose type in Import Data with seamless preprocessing. Each aug_*.json file targets a single entity type but includes read-only context from related entities (e.g., supplier info embedded in products file) for AI augmentation purposes. During import, only the primary entity's editable fields are consumed; context fields are ignored.

**Why this priority**: Enables AI-assisted workflows which are foundational to the product's future direction. Depends on unified import (P1).

**Independent Test**: Can be fully tested by importing an aug_*.json file and verifying it's auto-detected as Context-Rich, preprocessed, and imported correctly.

**Acceptance Scenarios**:

1. **Given** the Import Data dialog is open, **When** viewing purpose options, **Then** "Context-Rich" appears as the 5th purpose with appropriate description
2. **Given** a user selects an aug_ingredients.json file, **When** auto-detection runs, **Then** "Context-Rich" purpose is auto-selected
3. **Given** a context-rich file has valid FK references, **When** imported, **Then** preprocessing runs invisibly and import succeeds
4. **Given** a context-rich file references missing entities (e.g., unknown supplier slug), **When** imported, **Then** a blocking error dialog appears with actionable information about missing references

---

### User Story 4 - Pre-Import Schema Validation (Priority: P2)

A user attempts to import a malformed file (often AI-generated with structural errors). Previously this would cause cryptic database errors. After this feature, schema validation catches problems before import and provides clear error messages.

**Why this priority**: Critical for AI-assisted workflows where generated files may have structural issues. Prevents confusing failures.

**Independent Test**: Can be fully tested by importing a deliberately malformed JSON file and verifying clear validation errors appear.

**Acceptance Scenarios**:

1. **Given** a user selects a file missing required fields, **When** validation runs, **Then** an error dialog shows which fields are missing and in which records
2. **Given** a user selects a file with wrong field types, **When** validation runs, **Then** an error dialog shows expected vs actual types
3. **Given** a user selects a file with unexpected extra fields, **When** validation runs, **Then** a warning is shown but import proceeds
4. **Given** a user selects a structurally valid file, **When** validation runs, **Then** validation passes silently and import proceeds

---

### User Story 5 - Comprehensive Import Logging (Priority: P2)

A user encounters import errors and needs to troubleshoot. Previously logs were minimal and hardcoded to a repo directory. After this feature, detailed structured logs are written to a configurable directory with full error context and resolution suggestions.

**Why this priority**: Essential for debugging AI-generated files and providing user support. Enables external analysis of import issues.

**Independent Test**: Can be fully tested by performing an import (success or failure) and verifying log file contains all required sections with appropriate detail.

**Acceptance Scenarios**:

1. **Given** any import operation completes, **When** checking the logs directory, **Then** a timestamped log file exists
2. **Given** an import encounters errors, **When** reviewing the log, **Then** errors include entity name, record snippet, expected vs actual, and resolution suggestion
3. **Given** an import has warnings (unexpected fields, optional FK not found), **When** reviewing the log, **Then** warnings include context and action taken
4. **Given** an import succeeds, **When** reviewing the log, **Then** summary shows total/successful/skipped/failed counts per entity

---

### User Story 6 - Configurable Directories (Priority: P3)

A user repeatedly navigates to the same directories for import/export and wants logs outside the repo. Previously directories were hardcoded or defaulted. After this feature, users can configure default directories via Preferences.

**Why this priority**: Quality-of-life improvement that reduces friction. Not required for core functionality.

**Independent Test**: Can be fully tested by setting directory preferences, restarting the app, and verifying dialogs open in configured locations.

**Acceptance Scenarios**:

1. **Given** a user opens File > Preferences, **When** viewing the dialog, **Then** they can configure Import, Export, and Logs directories
2. **Given** a user sets import directory to ~/Documents/imports, **When** they open Import Data dialog, **Then** file browser starts in that directory
3. **Given** a user sets logs directory, **When** an import runs, **Then** logs are written to the configured location
4. **Given** a user clicks "Restore Defaults", **When** preferences save, **Then** all directories revert to system defaults
5. **Given** preferences are set, **When** the database is reset, **Then** directory preferences survive (stored in app_config table)

---

### User Story 7 - Multi-Entity Catalog Import (Priority: P2)

A user imports a file containing multiple entity types (e.g., suppliers, ingredients, and products together). Previously entity selection was manual. After this feature, all entities are auto-detected and imported in dependency order.

**Why this priority**: Simplifies bulk data operations. Common use case for restoring complete datasets.

**Independent Test**: Can be fully tested by importing a multi-entity JSON file and verifying all entities are detected, listed, and imported correctly.

**Acceptance Scenarios**:

1. **Given** a user selects a file with multiple entity arrays, **When** auto-detection runs, **Then** all entities are listed with counts (e.g., "Multiple entities: Suppliers (6), Ingredients (45), Products (12)")
2. **Given** Catalog purpose is selected, **When** viewing options, **Then** only mode selection appears (no entity checkboxes)
3. **Given** a multi-entity import runs, **When** processing, **Then** entities are imported in dependency order (suppliers before products that reference them)

---

### Edge Cases

- What happens when a file has valid structure but empty data arrays? Import succeeds with 0 records message.
- What happens when a multi-entity file has some valid and some invalid entities? Valid entities import, invalid ones logged with errors.
- What happens when configured directory no longer exists? Fall back to system default with warning.
- What happens when log directory is not writable? Show error, suggest alternative.
- What happens when context-rich file has circular FK references? Detect and block with clear message.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide Import Data dialog as the single entry point for all import operations with 5 purpose types: Backup, Catalog, Purchases, Adjustments, Context-Rich
- **FR-001a**: System MUST use file-first dialog flow: user selects file first, system auto-detects and suggests purpose, user can override selection
- **FR-002**: System MUST remove "Import Catalog" and "Import Context-Rich" menu items from File menu (clean removal)
- **FR-003**: System MUST display "Suppliers" checkbox in Export Data Catalog tab, positioned alphabetically with other entities
- **FR-004**: System MUST include suppliers with slug field in export when Suppliers checkbox is selected
- **FR-005**: System MUST auto-detect supplier files during import (suppliers.json or multi-entity files with suppliers array)
- **FR-006**: System MUST auto-detect context-rich files (aug_*.json pattern or context_rich metadata)
- **FR-007**: System MUST display detected entities with record counts during import (e.g., "Suppliers (6 records)")
- **FR-008**: System MUST provide mode selection for Catalog and Context-Rich purposes: "Update Existing" and "Add New Only"
- **FR-009**: System MUST NOT display entity checkboxes for Catalog purpose (rely on auto-detection)
- **FR-010**: System MUST preprocess context-rich files (aug_*.json) before import: convert to normalized format and validate FK references
- **FR-010a**: System MUST ignore read-only context fields in aug_*.json files during preprocessing (only primary entity's editable fields are extracted)
- **FR-010b**: System MUST run schema validation on preprocessed Context-Rich output using the same schemas as Catalog imports (no separate aug format schemas)
- **FR-011**: System MUST block context-rich import with actionable error dialog when FK references are missing (detected during preprocessing)
- **FR-012**: System MUST validate JSON structure before import (required fields, field types, array structure); for Context-Rich this occurs after preprocessing
- **FR-013**: System MUST display clear validation errors with record numbers and expected vs actual values
- **FR-014**: System MUST treat unexpected fields as warnings, not errors (import proceeds with warning)
- **FR-014a**: System MUST display modal summary dialog after import completion showing counts (imported/skipped/failed) per entity
- **FR-015**: System MUST provide Preferences dialog (File > Preferences) for configuring Import, Export, and Logs directories
- **FR-016**: System MUST persist directory preferences in app_config table (survives database reset)
- **FR-017**: System MUST write timestamped import logs to configured logs directory
- **FR-018**: System MUST include structured log sections: SOURCE, OPERATION, PREPROCESSING, SCHEMA VALIDATION, IMPORT RESULTS, ERRORS, WARNINGS, SUMMARY, METADATA
- **FR-019**: System MUST include resolution suggestions in error log entries
- **FR-020**: System MUST import multi-entity files in dependency order (e.g., suppliers before products)
- **FR-021**: System MUST preserve all existing import/export workflows without regression (backup, purchases, adjustments)
- **FR-022**: System MUST support all existing file format versions

### Key Entities *(include if feature involves data)*

- **app_config**: Stores user preferences as key-value pairs. Keys include import_directory, export_directory, logs_directory. Values are file paths. Survives database reset.
- **Import Log**: Timestamped plain text file (.txt) with human-readable header-separated sections (SOURCE, OPERATION, PREPROCESSING, SCHEMA VALIDATION, IMPORT RESULTS, ERRORS, WARNINGS, SUMMARY, METADATA) documenting import operation details.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can complete any import operation through a single unified dialog (no need for multiple entry points)
- **SC-002**: Supplier round-trip test passes: export suppliers, import to fresh database, verify all records match
- **SC-003**: Schema validation catches 100% of structural errors (missing required fields, wrong types) before database operations begin
- **SC-004**: Import logs contain sufficient detail for external troubleshooting (entity name, record context, resolution suggestion for every error)
- **SC-005**: Directory preferences persist across application restarts and database resets
- **SC-006**: All 5 import purpose types complete successfully for valid files
- **SC-007**: Context-rich import blocks with clear error when FK references are missing, proceeds seamlessly when valid
- **SC-008**: Multi-entity files import all detected entities in correct dependency order
- **SC-009**: Zero regressions in existing backup, purchase, and adjustment import workflows
- **SC-010**: Malformed AI-generated files produce actionable error messages (not cryptic database errors)
