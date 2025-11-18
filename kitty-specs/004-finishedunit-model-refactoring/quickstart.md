# FinishedUnit Model Refactoring - Implementation Quickstart

**Feature**: FinishedUnit Model Refactoring
**Branch**: `004-finishedunit-model-refactoring`
**Date**: 2025-11-14

## Overview

This quickstart guide provides step-by-step implementation instructions for transforming the existing single-tier FinishedGood model into a two-tier hierarchical system.

## Prerequisites

### Environment Setup
- Python 3.10+ virtual environment activated
- SQLAlchemy 2.x available
- pytest installed for testing
- Access to existing database with FinishedGood data

### Current State Analysis
Before beginning implementation:
1. Run database backup: `python -m src.utils.backup_database`
2. Document current FinishedGood count and structure
3. Identify any existing relationships that will be affected

## Implementation Phases

### Phase 1: Database Models

**Estimated Time**: 2-3 hours

#### Step 1.1: Create FinishedUnit Model
```bash
# Create new model file
touch src/models/finished_unit.py
```

**Key Implementation Points**:
- Rename existing FinishedGood model to FinishedUnit
- Maintain all existing fields with type compatibility
- Add new fields: `production_notes`, enhanced timestamps
- Ensure slug uniqueness constraint
- Preserve relationships to Recipe, PantryConsumption, ProductionRun

**Reference**: `contracts/finished_unit_service.md` for complete field specifications

#### Step 1.2: Create New FinishedGood Model
```bash
# Create assembly model file
touch src/models/finished_good.py
```

**Key Implementation Points**:
- Create fresh model for assembled packages
- Include assembly_type enumeration
- Add packaging_instructions and total_cost fields
- Implement calculated fields for cost aggregation
- Establish relationships with Composition

#### Step 1.3: Create Composition Junction Model
```bash
# Create composition model file
touch src/models/composition.py
```

**Key Implementation Points**:
- Implement separate foreign keys pattern (finished_unit_id, finished_good_id)
- Add constraint ensuring exactly one component reference is non-null
- Include quantity, sort_order, and notes fields
- Establish polymorphic relationships

### Phase 2: Migration Infrastructure

**Estimated Time**: 3-4 hours

#### Step 2.1: Create Migration Service
```bash
touch src/services/migration_service.py
```

**Core Functions**:
- `validate_pre_migration()`: Check existing data integrity
- `create_database_backup()`: Full SQLite backup with validation
- `execute_schema_migration()`: Transform table structure
- `migrate_data()`: Convert FinishedGood records to FinishedUnit
- `validate_post_migration()`: Verify migration success
- `rollback_migration()`: Restore from backup if needed

#### Step 2.2: Create Migration Orchestrator
```bash
touch src/migrations/migration_orchestrator.py
```

**Orchestration Flow**:
1. Pre-migration validation and backup
2. Schema transformation (table renames, new table creation)
3. Data migration with integrity checks
4. Index creation for performance
5. Post-migration validation
6. Service layer compatibility updates

### Phase 3: Service Layer Implementation

**Estimated Time**: 4-5 hours

#### Step 3.1: FinishedUnit Service
```bash
touch src/services/finished_unit_service.py
```

**Core Operations**:
- CRUD operations maintaining existing API compatibility
- Inventory management with non-negative constraints
- Cost calculation integration with existing FIFO patterns
- Search and query functionality

**Migration Compatibility**: Support legacy FinishedGood API calls during transition

#### Step 3.2: FinishedGood Service
```bash
touch src/services/finished_good_service.py
```

**Core Operations**:
- Assembly creation with component validation
- Hierarchy traversal using breadth-first search
- Cost calculation across composition levels
- Circular reference prevention
- Assembly production (inventory consumption/creation)

#### Step 3.3: Composition Service
```bash
touch src/services/composition_service.py
```

**Core Operations**:
- Composition CRUD with referential integrity
- Hierarchy queries and flattening
- Bulk operations for assembly modification
- Validation utilities for components and structure

### Phase 4: Testing Suite

**Estimated Time**: 3-4 hours

#### Step 4.1: Unit Tests
```bash
mkdir -p tests/unit/services tests/unit/models
touch tests/unit/test_finished_unit_service.py
touch tests/unit/test_finished_good_service.py
touch tests/unit/test_composition_service.py
touch tests/unit/test_migration_service.py
```

**Test Coverage Requirements**:
- All service methods with valid/invalid inputs
- Edge cases for inventory management
- Hierarchy traversal algorithms
- Circular reference prevention
- Migration workflow scenarios

#### Step 4.2: Integration Tests
```bash
mkdir -p tests/integration
touch tests/integration/test_hierarchy_operations.py
touch tests/integration/test_migration_workflow.py
touch tests/integration/test_service_interactions.py
```

**Integration Scenarios**:
- Complex assembly creation and modification
- Migration with real data patterns
- Cross-service inventory management
- Performance benchmarks

### Phase 5: UI Integration

**Estimated Time**: 2-3 hours

#### Step 5.1: Service Layer Updates
- Update existing UI components to use new FinishedUnit service
- Add deprecation warnings for legacy API usage
- Ensure backward compatibility during transition

#### Step 5.2: UI Enhancement Planning
- Document new UI requirements for assembly management
- Plan hierarchy visualization components
- Design assembly creation workflows

## Testing Strategy

### Pre-Implementation Tests
1. **Backup Validation**: Ensure backup/restore procedures work
2. **Performance Baseline**: Measure current operation speeds
3. **Data Integrity**: Validate existing database consistency

### Development Testing
1. **Unit Tests**: Test each service method independently
2. **Integration Tests**: Test cross-service operations
3. **Migration Tests**: Test with production data copies
4. **Performance Tests**: Validate speed requirements

### Acceptance Testing
1. **Migration Validation**: Verify zero data loss
2. **Functionality Tests**: Confirm all existing features work
3. **Performance Verification**: Meet <500ms query targets
4. **User Acceptance**: Test with real workflow scenarios

## Risk Mitigation

### Data Safety
- **Multiple Backups**: Create timestamped backups before each phase
- **Dry-Run Mode**: Test all migrations with copies before live execution
- **Rollback Procedures**: Document and test rollback at each phase
- **Validation Checkpoints**: Verify data integrity at each step

### Performance Safety
- **Incremental Implementation**: Implement one service at a time
- **Performance Monitoring**: Benchmark each operation against targets
- **Index Optimization**: Create appropriate indexes before going live
- **Memory Profiling**: Monitor memory usage during hierarchy operations

### Compatibility Safety
- **API Compatibility**: Maintain existing service interfaces during transition
- **Deprecation Warnings**: Clearly mark legacy usage patterns
- **Gradual Migration**: Update UI components incrementally
- **Feature Flags**: Enable/disable new features for testing

## Deployment Checklist

### Pre-Deployment
- [ ] All unit tests pass with >70% service layer coverage
- [ ] Integration tests pass for all cross-service operations
- [ ] Migration dry-run completed successfully with production data copy
- [ ] Performance benchmarks meet all targets (<500ms queries, <2s operations)
- [ ] Database backup procedure validated and tested
- [ ] Rollback procedure documented and tested

### Deployment
- [ ] Application backup created
- [ ] Database backup created with validation
- [ ] Migration executed with monitoring
- [ ] Post-migration validation completed
- [ ] Service layer updated with new APIs
- [ ] UI components updated to use new services
- [ ] Performance monitoring enabled

### Post-Deployment
- [ ] User acceptance testing completed
- [ ] Performance monitoring shows targets met
- [ ] No data integrity issues detected
- [ ] Legacy API deprecation warnings reviewed
- [ ] Documentation updated for new model structure

## Troubleshooting

### Common Issues
1. **Migration Failures**: Check foreign key constraints, run validation queries
2. **Performance Issues**: Verify indexes created, check query execution plans
3. **Circular References**: Review hierarchy validation logic, test edge cases
4. **Inventory Inconsistencies**: Validate quantity calculations, check aggregation logic

### Support Resources
- **Constitution Guidelines**: Review layered architecture requirements
- **Existing Patterns**: Reference event_service.py for multi-query patterns
- **SQLAlchemy Documentation**: Association object patterns and relationship loading
- **Performance Profiling**: Use built-in SQLAlchemy query logging

## Success Metrics

### Technical Metrics
- **Migration Success**: 100% data preservation with integrity validation
- **Performance Targets**: <500ms hierarchy queries, <2s CRUD operations
- **Test Coverage**: >70% service layer coverage with integration tests
- **API Compatibility**: All existing UI functionality preserved

### Business Metrics
- **Feature Completeness**: All specification requirements implemented
- **User Impact**: No workflow disruption during migration
- **System Reliability**: Zero data loss, consistent backup/restore capability
- **Future Readiness**: Architecture supports web migration path