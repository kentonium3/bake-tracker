# Research: FinishedUnit Model Refactoring

**Feature**: FinishedUnit Model Refactoring
**Branch**: `004-finishedunit-model-refactoring`
**Date**: 2025-11-14
**Phase**: 0 - Research & Architecture Decisions

## Executive Summary

Research findings for transforming the existing single-tier FinishedGood model into a two-tier hierarchical system supporting individual consumable units and assembled packages with polymorphic composition relationships.

## Key Technical Decisions

### Decision 1: Polymorphic Component Reference Strategy

**Chosen**: Separate Foreign Keys Approach
**Rationale**:
- Provides explicit referential integrity with database-level constraints
- Simpler query patterns compared to discriminator or generic FK approaches
- Clear separation of FinishedUnit vs FinishedGood relationships
- Aligns with SQLAlchemy 2.x best practices for association objects

**Evidence Sources**:
- SQLAlchemy 2.x documentation on association object patterns
- Existing codebase analysis showing preference for explicit relationships
- Performance considerations for inventory queries (<500ms requirement)

**Alternatives Considered**:
- Discriminator column approach: Rejected due to weaker constraint enforcement
- Generic foreign key pattern: Rejected due to complexity and constraint management overhead

### Decision 2: Data Migration Strategy

**Chosen**: Backup-and-Restore with Local Database Transformation
**Rationale**:
- Single-user desktop application context eliminates production/downtime concerns
- Full database backup provides maximum safety for zero data loss requirement
- Local SQLite transformation is simpler than complex blue-green deployment
- Clear rollback strategy with complete data restore capability

**Evidence Sources**:
- Desktop application deployment model analysis
- SQLite migration patterns and backup strategies
- Existing database size and complexity assessment

**Alternatives Considered**:
- Blue-green deployment: Overly complex for single-user local application
- Rolling migration: Unnecessary complexity without production environment constraints

### Decision 3: Hierarchy Traversal Implementation

**Chosen**: Iterative Application-Level Traversal with Breadth-First Search
**Rationale**:
- Consistent with existing service layer patterns (event_service.py multi-query aggregation)
- Simpler implementation and debugging compared to recursive SQL solutions
- Appropriate for SQLite and desktop application performance requirements
- Easier testing and maintenance for single-user context

**Evidence Sources**:
- Analysis of existing event_service.py implementation patterns
- SQLite recursive CTE performance characteristics for desktop workloads
- Performance requirement analysis (<500ms for 10k items, 5-level hierarchy depth)

**Alternatives Considered**:
- Recursive CTEs: Overly complex for application domain and data scale
- Materialized path: Path maintenance overhead unnecessary for use case
- Nested set model: Complex insert/update patterns inappropriate for frequent modifications

## Technical Research Findings

### Existing Codebase Analysis

**Service Layer Patterns**:
- Confirmed multi-query aggregation patterns in `event_service.py`
- Established service layer abstraction suitable for polymorphic relationship management
- Existing FIFO calculation patterns adaptable to hierarchical cost aggregation

**Database Schema Patterns**:
- SQLAlchemy 2.x relationship patterns already established
- Foreign key constraint usage consistent throughout codebase
- Migration utilities framework exists for safe schema transformations

**Performance Characteristics**:
- Current database operations meet <2s requirement for CRUD operations
- Multi-query patterns support <500ms inventory query target
- SQLite query optimizer handles moderate relationship complexity effectively

### Architecture Alignment

**Constitution Compliance**:
- ✅ Layered architecture maintained (UI → Services → Models → Database)
- ✅ Service layer remains UI-independent for web migration compatibility
- ✅ SQLAlchemy ORM enables future PostgreSQL migration for web deployment
- ✅ Migration strategy ensures data integrity per constitution requirements

**Technology Stack Integration**:
- SQLAlchemy 2.x association object patterns support polymorphic relationships
- pytest testing framework accommodates complex migration and hierarchy test scenarios
- CustomTkinter UI layer isolation enables backend refactoring without UI changes

## Implementation Recommendations

### Migration Sequencing
1. **Backup Phase**: Full database backup with integrity validation
2. **Schema Transformation**: Rename existing tables, create new model structure
3. **Data Migration**: Transform FinishedGood records to FinishedUnit with validation
4. **Relationship Creation**: Initialize composition relationships for existing data
5. **Service Layer Updates**: Update existing services to use new models
6. **UI Integration**: Modify UI components to use updated service interfaces

### Testing Strategy
- Unit tests for polymorphic relationship handling
- Integration tests for complete migration workflow
- Performance benchmarks for hierarchy traversal algorithms
- Migration dry-run validation with production data copies

### Risk Mitigation
- Pre-migration database backup with validated restore procedures
- Incremental service layer updates to maintain API compatibility during transition
- Rollback procedures documented and tested before production migration
- Performance monitoring for hierarchy query operations

## Outstanding Questions

### Implementation Details
1. **Index Strategy**: Optimal database indexing for composition relationship queries
2. **Service API Compatibility**: Transition strategy for existing UI components during migration
3. **Cost Calculation**: Hierarchical cost aggregation algorithm for assembly pricing
4. **Circular Reference Detection**: Efficient algorithm for preventing composition cycles

### Future Considerations
1. **Web Migration Impact**: Multi-tenant schema modifications required for web deployment
2. **Performance Scaling**: Hierarchy traversal optimization for larger datasets
3. **UI Enhancement**: Interface patterns for managing complex assembly hierarchies
4. **Data Export**: Enhanced export formats supporting hierarchical relationships

## Evidence Trail

**Planning Session References**:
- User confirmation of separate foreign keys approach (2025-11-14)
- Migration strategy simplification for desktop context (2025-11-14)
- Hierarchy traversal pattern selection based on existing codebase (2025-11-14)

**Codebase Analysis**:
- `src/services/event_service.py`: Multi-query aggregation patterns
- `src/models/`: Existing SQLAlchemy relationship patterns
- `src/migrations/`: Database migration utility framework

**External Documentation**:
- SQLAlchemy 2.x Association Object documentation
- SQLite migration and backup best practices
- Desktop application deployment patterns