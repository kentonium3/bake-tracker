# Feature Specification: Cost Architecture Refactor

**Feature Branch**: `045-cost-architecture-refactor`
**Created**: 2026-01-09
**Status**: Draft
**Priority**: P0 - FOUNDATIONAL ARCHITECTURE (blocks F046-F048)
**Input**: Design document `docs/design/F045_cost_architecture_refactor.md`

## Overview

**Problem**: Current architecture stores costs as fields in definition models (FinishedUnit.unit_cost, FinishedGood.total_cost), creating cascading staleness when ingredient prices change. Stored costs become outdated but remain in the database, causing data integrity issues and user confusion.

**Solution**: Remove stored costs from definition models. This is a "removal only" refactor - costs will be calculated dynamically in future features (F046+), but this feature strictly removes the stored cost fields and updates all dependent code.

**Philosophy**: "Costs on Instances, Not Definitions" - definitions (recipes, finished units, finished goods) have no inherent stored cost. Costs only exist when instantiated for actual production/assembly (future features).

**Breaking Change**: Import/export format version bumps to 4.1. Old v4.0 exports are rejected with clear error messages guiding users to update their files.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Database Integrity After Migration (Priority: P1)

As a system administrator, I need the database migration to remove cost columns without data loss so that the application runs correctly after the upgrade.

**Why this priority**: This is the foundation - if the migration fails, nothing else works. The migration must drop `unit_cost` and `total_cost` columns cleanly.

**Independent Test**: Run migration on test database, verify columns are dropped, verify all other data intact.

**Acceptance Scenarios**:

1. **Given** a database with FinishedUnit.unit_cost and FinishedGood.total_cost columns, **When** migration runs, **Then** those columns are dropped and no other data is affected
2. **Given** a migrated database, **When** the application starts, **Then** no errors occur related to missing cost columns
3. **Given** existing FinishedUnit and FinishedGood records, **When** migration runs, **Then** all records remain with their non-cost fields intact

---

### User Story 2 - Export Produces Clean Format (Priority: P2)

As a user exporting my data, I need the export to produce version 4.1 format without cost fields so that I can back up my data in the current format.

**Why this priority**: Export functionality must work correctly after model changes. Users depend on exports for backup.

**Independent Test**: Export data, verify JSON contains no unit_cost or total_cost fields, verify version is 4.1.

**Acceptance Scenarios**:

1. **Given** FinishedUnit records exist, **When** I export data, **Then** the exported JSON does not contain `unit_cost` in any finished_units entry
2. **Given** FinishedGood records exist, **When** I export data, **Then** the exported JSON does not contain `total_cost` in any finished_goods entry
3. **Given** any export, **When** I check the version field, **Then** it shows "4.1"

---

### User Story 3 - Import Rejects Old Format (Priority: P3)

As a user importing data, I need clear error messages when my import file contains deprecated cost fields so that I know exactly how to fix my file.

**Why this priority**: Users with old exports need guidance, but this is less common than normal operations.

**Independent Test**: Attempt import with v4.0 file containing cost fields, verify rejection with helpful error message.

**Acceptance Scenarios**:

1. **Given** an import file with `unit_cost` in a finished_units entry, **When** I attempt import, **Then** import fails with error message mentioning "unit_cost", "4.1", and "remove"
2. **Given** an import file with `total_cost` in a finished_goods entry, **When** I attempt import, **Then** import fails with error message mentioning "total_cost", "4.1", and "remove"
3. **Given** an import file with version "4.0", **When** I attempt import, **Then** import fails with error explaining version incompatibility and how to update
4. **Given** a clean v4.1 import file without cost fields, **When** I import, **Then** import succeeds

---

### User Story 4 - UI Shows No Cost Columns (Priority: P4)

As a user browsing Finished Units or recipes, I should not see cost columns in catalog views since stored costs no longer exist.

**Why this priority**: UI cleanup is necessary but cosmetic - core functionality works regardless.

**Independent Test**: Open Finished Units tab, verify no cost column visible in the list.

**Acceptance Scenarios**:

1. **Given** I am viewing the Finished Units catalog, **When** I look at the column headers, **Then** there is no "Cost" or "Unit Cost" column
2. **Given** I am viewing the Recipes catalog, **When** I look at the column headers, **Then** there is no "Cost" or "Total Cost" column

---

### Edge Cases

- What happens when importing a file with mixed valid/invalid entries? The import fails on first deprecated field encountered with clear error.
- What happens when the migration runs on an already-migrated database? The migration should be idempotent (no error if columns don't exist).
- How does system handle NULL values in cost fields during migration? They are simply dropped with the column - no special handling needed.

## Requirements *(mandatory)*

### Functional Requirements

**Model Changes:**
- **FR-001**: System MUST remove the `unit_cost` column from the FinishedUnit database table
- **FR-002**: System MUST remove the `total_cost` column from the FinishedGood database table
- **FR-003**: System MUST provide a database migration script that drops these columns safely

**Export Service:**
- **FR-004**: Export service MUST NOT include `unit_cost` field in finished_units JSON output
- **FR-005**: Export service MUST NOT include `total_cost` field in finished_goods JSON output
- **FR-006**: Export service MUST set version field to "4.1" in export output

**Import Service:**
- **FR-007**: Import service MUST reject files containing `unit_cost` in any finished_units entry
- **FR-008**: Import service MUST reject files containing `total_cost` in any finished_goods entry
- **FR-009**: Import service MUST reject files with version "4.0" or lower
- **FR-010**: Import service MUST provide clear, actionable error messages explaining what field to remove and referencing version 4.1

**Sample Data:**
- **FR-011**: Sample data file `test_data/sample_data_min.json` MUST be updated to version 4.1 format with no cost fields
- **FR-012**: Sample data file `test_data/sample_data_all.json` MUST be updated to version 4.1 format with no cost fields

**UI Changes:**
- **FR-013**: Finished Units catalog view MUST NOT display a cost column
- **FR-014**: Recipes catalog view MUST NOT display a cost column

**Testing:**
- **FR-015**: System MUST include tests verifying exports exclude cost fields
- **FR-016**: System MUST include tests verifying imports reject deprecated cost fields
- **FR-017**: System MUST include tests verifying sample data files are version 4.1 compliant

### Key Entities

- **FinishedUnit**: Represents a production output (e.g., "Large Cookie"). Previously had `unit_cost` field - now removed. Cost will be calculated dynamically in future features.
- **FinishedGood**: Represents an assembled gift package. Previously had `total_cost` field - now removed. Cost will be calculated from components in future features.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Database migration completes without errors on existing databases with FinishedUnit and FinishedGood records
- **SC-002**: All existing tests pass after model changes (with necessary test updates)
- **SC-003**: 100% of exported finished_units entries contain no `unit_cost` field
- **SC-004**: 100% of exported finished_goods entries contain no `total_cost` field
- **SC-005**: Import attempts with deprecated fields fail with error messages containing the field name, version number, and remediation guidance
- **SC-006**: Sample data files load successfully after updates
- **SC-007**: UI catalog views display without cost columns

## Assumptions

- The FinishedUnit and FinishedGood models currently have `unit_cost` and `total_cost` fields respectively (to be verified during planning)
- Export and import services already exist and handle these models (to be verified during planning)
- Sample data files exist at the specified paths (to be verified during planning)
- UI tabs for Finished Units and Recipes exist with cost columns (to be verified during planning)

## Out of Scope

- Dynamic cost calculation methods (deferred to F046+)
- Cost display in detail/edit views (explicitly excluded per user confirmation)
- Backward compatibility with v4.0 imports (clean break approach)
- Automated migration tool for old exports (users manually update)
- Instance-side cost capture on production/assembly runs (F046-F048)

## Dependencies

- **F044** (Finished Units Functionality & UI): Must be complete (confirmed complete)

## Blocks

- **F046** (Finished Goods)
- **F047** (Shopping Lists)
- **F048** (Assembly)
- Event Planning features
