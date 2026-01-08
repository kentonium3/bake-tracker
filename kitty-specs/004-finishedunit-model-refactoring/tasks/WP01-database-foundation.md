---
work_package_id: WP01
title: Database Foundation & Migration Infrastructure
lane: done
history:
- timestamp: '2025-11-14T17:30:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
- timestamp: '2025-11-14T17:45:00Z'
  lane: doing
  agent: claude
  shell_pid: '19144'
  action: Started implementation
agent: claude
assignee: Claude
phase: Phase 1 - Foundation
reviewer: claude
reviewer_shell_pid: '36008'
shell_pid: '36008'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
---

# Work Package Prompt: WP01 – Database Foundation & Migration Infrastructure

## Objectives & Success Criteria

- Create two-tier hierarchical database model with FinishedUnit (individual items) and FinishedGood (assemblies)
- Implement safe data migration infrastructure with backup/restore capabilities
- Establish Composition junction model supporting polymorphic relationships
- Validate zero data loss migration from existing FinishedGood to new FinishedUnit structure
- All database models ready for service layer implementation

## Context & Constraints

- **Prerequisites**: Planning documents completed (spec.md, plan.md, data-model.md)
- **Architecture**: Layered architecture (UI → Services → Models → Database) per constitution
- **Technology**: SQLAlchemy 2.x with SQLite for desktop application
- **Migration Strategy**: Backup-and-restore approach for single-user desktop context
- **Performance**: Support up to 10k items with <500ms query targets
- **References**:
  - `data-model.md`: Complete entity specifications
  - `contracts/`: Service interface requirements
  - `research.md`: Technical decisions and evidence

## Subtasks & Detailed Guidance

### Subtask T001 – Create Database Backup and Validation Utilities

- **Purpose**: Establish safe migration infrastructure with data protection
- **Steps**:
  1. Create `src/utils/backup_validator.py` with backup creation and validation functions
  2. Implement `create_database_backup(backup_path: str) -> bool` with timestamp naming
  3. Implement `validate_backup_integrity(backup_path: str) -> dict` with checksum validation
  4. Implement `restore_database_from_backup(backup_path: str) -> bool` with safety checks
  5. Add logging for all backup operations with detailed status reporting
- **Files**: `src/utils/backup_validator.py`, update `src/utils/__init__.py`
- **Parallel?**: No - foundational for all migration work
- **Notes**: Must handle SQLite WAL mode properly, validate file integrity before operations

### Subtask T002 – Create FinishedUnit Model (Renamed from FinishedGood)

- **Purpose**: Transform existing FinishedGood model to represent individual consumable items
- **Steps**:
  1. Create `src/models/finished_unit.py` based on existing FinishedGood structure
  2. Preserve all existing fields with compatible types: id, slug, display_name, recipe_id, cost_per_unit → unit_cost
  3. Add new fields: production_notes (Text), enhanced created_at/updated_at timestamps
  4. Implement SQLAlchemy 2.x relationship patterns for Recipe, PantryConsumption, ProductionRun
  5. Add unique constraints on slug, non-negative constraints on costs and inventory
  6. Update `src/models/__init__.py` to export FinishedUnit
- **Files**: `src/models/finished_unit.py`, `src/models/__init__.py`
- **Parallel?**: Yes - can proceed alongside T003, T004
- **Notes**: Field mapping critical for migration - document all changes in model docstring

### Subtask T003 – Create New FinishedGood Model for Assemblies

- **Purpose**: Create fresh model for assembled packages containing multiple components
- **Steps**:
  1. Create `src/models/finished_good.py` with assembly-specific structure
  2. Add core fields: id, slug, display_name, description, assembly_type, packaging_instructions
  3. Add calculated fields: total_cost (derived from components), inventory_count
  4. Implement assembly_type enumeration (gift_box, variety_pack, holiday_set, bulk_pack, custom_order)
  5. Add timestamps: created_at, updated_at
  6. Establish relationship with Composition for component management
  7. Update `src/models/__init__.py` to export FinishedGood and AssemblyType
- **Files**: `src/models/finished_good.py`, `src/models/__init__.py`
- **Parallel?**: Yes - can proceed alongside T002, T004
- **Notes**: AssemblyType enum can be created as separate file if complex

### Subtask T004 – Create Composition Junction Model with Polymorphic References

- **Purpose**: Enable FinishedGoods to contain both FinishedUnits and other FinishedGoods
- **Steps**:
  1. Create `src/models/composition.py` with association object pattern
  2. Implement separate foreign keys: assembly_id (to FinishedGood), finished_unit_id, finished_good_id
  3. Add constraint ensuring exactly one of finished_unit_id or finished_good_id is non-null
  4. Add component fields: component_quantity (positive integer), component_notes, sort_order
  5. Add timestamp: created_at
  6. Establish relationships: assembly (Many-to-One FinishedGood), finished_unit_component, finished_good_component
  7. Update `src/models/__init__.py` to export Composition
- **Files**: `src/models/composition.py`, `src/models/__init__.py`
- **Parallel?**: Yes - can proceed alongside T002, T003
- **Notes**: Constraint implementation critical for data integrity - use SQLAlchemy CheckConstraint

### Subtask T005 – Create Migration Service with Backup/Restore Functions

- **Purpose**: Coordinate safe data migration from old to new schema
- **Steps**:
  1. Create `src/services/migration_service.py` with comprehensive migration orchestration
  2. Implement `validate_pre_migration() -> dict` to check existing data integrity
  3. Implement `execute_schema_migration() -> bool` for table transformations
  4. Implement `migrate_finished_good_to_unit() -> dict` with field mapping and validation
  5. Implement `validate_post_migration() -> dict` to verify migration success
  6. Implement `rollback_migration(backup_path: str) -> bool` for failure recovery
  7. Add detailed logging and progress reporting for each migration step
- **Files**: `src/services/migration_service.py`, `src/services/__init__.py`
- **Parallel?**: No - depends on T001-T004 completion
- **Notes**: Must preserve all existing foreign key relationships during migration

### Subtask T006 – Create Migration Orchestrator for Coordinated Schema Updates

- **Purpose**: Coordinate multi-step migration process with proper sequencing
- **Steps**:
  1. Create `src/migrations/migration_orchestrator.py` for workflow management
  2. Implement `get_migration_status() -> dict` to track migration state
  3. Implement `execute_full_migration() -> dict` with complete workflow orchestration
  4. Add migration phases: backup → schema → data → indexes → validation
  5. Implement rollback capability at each phase with detailed error reporting
  6. Add migration logging with timestamps and detailed status tracking
  7. Create `src/migrations/__init__.py` and update imports
- **Files**: `src/migrations/migration_orchestrator.py`, `src/migrations/__init__.py`
- **Parallel?**: No - depends on T005 completion
- **Notes**: Must handle partial migration failures gracefully with clear recovery instructions

## Test Strategy

- **Unit Tests**: Create `tests/unit/test_migration_service.py` and `tests/unit/models/` for all models
- **Integration Tests**: Create `tests/integration/test_migration_workflow.py` with realistic data scenarios
- **Test Commands**: Use pytest with coverage: `pytest tests/unit/test_migration_service.py -v --cov=src`
- **Test Data**: Create fixtures in `tests/fixtures/migration_test_data.py` with sample FinishedGood records

## Risks & Mitigations

- **Data Loss Risk**: Comprehensive backup strategy with validation before/after all operations
- **Migration Complexity**: Staged approach with rollback at each phase, extensive logging
- **Performance Impact**: Index optimization after migration, query performance validation
- **Referential Integrity**: Careful foreign key preservation, constraint validation in tests

## Definition of Done Checklist

- [ ] All six subtasks (T001-T006) completed and validated
- [ ] Database models created with proper relationships and constraints
- [ ] Migration infrastructure tested with sample data
- [ ] Backup/restore functionality validated with realistic datasets
- [ ] All models properly exported in `__init__.py` files
- [ ] Migration orchestrator handles all phases with rollback capability
- [ ] Unit tests created for all models and migration functions
- [ ] Integration test validates complete migration workflow
- [ ] Documentation updated in model docstrings with field mappings

## Activity Log

- 2025-11-15T14:31:18Z – claude – shell_pid=23431 – lane=for_review – Infrastructure complete - ready for review
- 2025-11-15T18:45:00Z – claude – shell_pid=36008 – lane=done – **APPROVED**: All 6 subtasks completed successfully. Database models, migration infrastructure, and backup systems validated. Ready for service layer implementation.
