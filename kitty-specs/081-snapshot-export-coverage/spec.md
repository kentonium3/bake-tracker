# Feature Specification: Snapshot Export Coverage

**Feature Branch**: `081-snapshot-export-coverage`
**Created**: 2026-01-28
**Status**: Draft
**Priority**: CRITICAL
**Input**: User description: "F081 Snapshot Export Coverage - Add export/import support for RecipeSnapshot, FinishedGoodSnapshot, MaterialUnitSnapshot, and FinishedUnitSnapshot entities. Critical for preserving cost history audit trail during data migrations."

## Problem Statement

Cost snapshot entities are not currently exported, causing loss of cost history audit trail during data migrations. This violates Constitution Principle II (Data Integrity).

**Current State:**
- RecipeSnapshot not exported (production cost history lost)
- FinishedGoodSnapshot not exported (assembly cost history lost)
- MaterialUnitSnapshot not exported (material pricing history lost)
- FinishedUnitSnapshot not exported (unit cost history lost)

**Impact:** Export-Reset-Import cycle loses all cost history, making it impossible to recreate historical cost calculations.

## User Scenarios & Testing

### User Story 1 - Export Snapshots for Data Migration (Priority: P1)

As a system administrator performing a data migration, I need all cost snapshots exported so that historical cost calculations are preserved when data is imported into a new database.

**Why this priority**: Without snapshot export, all cost history is lost during migration, violating data integrity requirements.

**Independent Test**: Export data, verify snapshot JSON files are created with correct content.

**Acceptance Scenarios**:

1. **Given** a database with RecipeSnapshot records, **When** export_all() is executed, **Then** recipe_snapshots.json is created containing all snapshots with UUID, recipe_slug, timestamp, and cost_data preserved.

2. **Given** a database with FinishedGoodSnapshot records, **When** export_all() is executed, **Then** finished_good_snapshots.json is created with all snapshot data.

3. **Given** a database with MaterialUnitSnapshot records, **When** export_all() is executed, **Then** material_unit_snapshots.json is created with all snapshot data.

4. **Given** a database with FinishedUnitSnapshot records, **When** export_all() is executed, **Then** finished_unit_snapshots.json is created with all snapshot data.

---

### User Story 2 - Import Snapshots to Restore Cost History (Priority: P1)

As a system administrator, I need to import previously exported snapshots so that cost history is fully restored after a database reset.

**Why this priority**: Import is the complement to export; both are required for complete data portability.

**Independent Test**: Import snapshot JSON files, verify records created with correct FK relationships.

**Acceptance Scenarios**:

1. **Given** recipe_snapshots.json file and recipes already imported, **When** import_all() is executed, **Then** RecipeSnapshot records are created with correct recipe_id FK resolved from recipe_slug.

2. **Given** finished_good_snapshots.json file and finished_goods already imported, **When** import_all() is executed, **Then** FinishedGoodSnapshot records are created with correct FK.

3. **Given** material_unit_snapshots.json and material_units already imported, **When** import_all() is executed, **Then** MaterialUnitSnapshot records are created with correct FK.

4. **Given** finished_unit_snapshots.json and finished_units already imported, **When** import_all() is executed, **Then** FinishedUnitSnapshot records are created with correct FK.

---

### User Story 3 - Round-Trip Data Integrity (Priority: P1)

As a data steward, I need export-import cycles to preserve snapshot data exactly so I can trust the system for audit purposes.

**Why this priority**: Data integrity is non-negotiable for financial/cost tracking systems.

**Independent Test**: Export, clear database, import, export again, compare exports.

**Acceptance Scenarios**:

1. **Given** snapshots exported to JSON, **When** imported to fresh database and re-exported, **Then** the snapshot UUIDs, timestamps, and cost_data match exactly.

2. **Given** a snapshot with a parent entity that no longer exists, **When** import is attempted, **Then** the snapshot is skipped with a warning log (not a failure).

---

### User Story 4 - Graceful Handling of Missing Parents (Priority: P2)

As a system administrator, I need snapshot imports to handle missing parent entities gracefully so that partial imports don't fail entirely.

**Why this priority**: Real-world migrations may have data inconsistencies; system should be resilient.

**Independent Test**: Import snapshots without their parent entities, verify warnings logged but import continues.

**Acceptance Scenarios**:

1. **Given** recipe_snapshots.json referencing a non-existent recipe_slug, **When** import runs, **Then** the snapshot is skipped and a warning is logged.

---

### Edge Cases

- What happens when snapshot cost_data JSON is malformed? (Preserve as-is, no validation)
- How does system handle snapshots with NULL timestamps? (Preserve NULL)
- What happens when export is run with zero snapshots? (Create empty JSON array)
- How does system handle duplicate snapshot UUIDs on import? (Skip duplicates, log warning)

## Requirements

### Functional Requirements

- **FR-001**: System MUST export RecipeSnapshot entities to recipe_snapshots.json with UUID, recipe_slug, snapshot_at, and cost_data fields
- **FR-002**: System MUST export FinishedGoodSnapshot entities to finished_good_snapshots.json with UUID, finished_good_slug, snapshot_at, and cost_data fields
- **FR-003**: System MUST export MaterialUnitSnapshot entities to material_unit_snapshots.json with UUID, material_unit_slug, snapshot_at, and pricing_data fields
- **FR-004**: System MUST export FinishedUnitSnapshot entities to finished_unit_snapshots.json with UUID, finished_unit_slug, snapshot_at, and cost_data fields
- **FR-005**: System MUST import RecipeSnapshot entities, resolving recipe_slug to recipe_id
- **FR-006**: System MUST import FinishedGoodSnapshot entities, resolving finished_good_slug to finished_good_id
- **FR-007**: System MUST import MaterialUnitSnapshot entities, resolving material_unit_slug to material_unit_id
- **FR-008**: System MUST import FinishedUnitSnapshot entities, resolving finished_unit_slug to finished_unit_id
- **FR-009**: System MUST import snapshots AFTER their parent entities are imported (dependency ordering)
- **FR-010**: System MUST preserve original snapshot UUIDs during import (no regeneration)
- **FR-011**: System MUST preserve original snapshot timestamps during import (no modification)
- **FR-012**: System MUST preserve cost_data/pricing_data JSON exactly as exported (no transformation)
- **FR-013**: System MUST skip snapshots with unresolvable parent slugs and log a warning
- **FR-014**: System MUST include snapshot file counts in export manifest
- **FR-015**: System MUST export snapshots in chronological order (oldest first)

### Key Entities

- **RecipeSnapshot**: Point-in-time capture of recipe cost calculations; links to Recipe via recipe_id
- **FinishedGoodSnapshot**: Point-in-time capture of assembly costs; links to FinishedGood via finished_good_id
- **MaterialUnitSnapshot**: Point-in-time capture of material unit pricing; links to MaterialUnit via material_unit_id
- **FinishedUnitSnapshot**: Point-in-time capture of finished unit costs; links to FinishedUnit via finished_unit_id

## Success Criteria

### Measurable Outcomes

- **SC-001**: All 4 snapshot types export to separate JSON files with 100% of records captured
- **SC-002**: All 4 snapshot types import successfully with parent FK relationships resolved correctly
- **SC-003**: Round-trip export-import-export produces identical snapshot data (UUIDs, timestamps, cost_data match)
- **SC-004**: Export of 1000 snapshots completes in under 5 seconds
- **SC-005**: Import of 1000 snapshots completes in under 10 seconds
- **SC-006**: Missing parent entities result in warnings, not failures (import continues)
- **SC-007**: Zero failing tests after implementation
- **SC-008**: Export manifest includes accurate counts for all 4 snapshot files

## Out of Scope

- PlanSnapshot export/import (separate feature, lower priority)
- ProductionPlanSnapshot export/import (separate feature)
- PlanAmendment export/import (separate feature)
- PlanningSnapshot export/import (separate feature)
- Snapshot data transformation or migration
- Snapshot cleanup or archival
- Snapshot compression

## Assumptions

- Snapshot models already exist with UUID, timestamp, parent FK, and data JSON blob fields
- Parent entity export/import already works correctly with slug-based FK resolution
- The coordinated_export_service.py and enhanced_import_service.py files exist and follow established patterns
- All snapshot parent entities (Recipe, FinishedGood, MaterialUnit, FinishedUnit) already have slug fields

## Dependencies

- F064: FinishedGoodSnapshot, MaterialUnitSnapshot, FinishedUnitSnapshot models
- F065: RecipeSnapshot model
- F080: Recipe slug support (for recipe_slug FK resolution)
- Existing export/import infrastructure in coordinated_export_service.py and enhanced_import_service.py
