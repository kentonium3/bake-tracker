# Implementation Plan: FinishedUnit Model Refactoring

**Branch**: `004-finishedunit-model-refactoring` | **Date**: 2025-11-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/004-finishedunit-model-refactoring/spec.md`

**Note**: This template is filled in by the `/spec-kitty.plan` command. See `.kittify/templates/commands/plan.md` for the execution workflow.

The planner will not begin until all planning questions have been answered—capture those answers in this document before progressing to later phases.

## Summary

Transform the existing FinishedGood model into a two-tier hierarchical system with FinishedUnit representing individual consumable units and FinishedGood representing assembled packages. Key technical approach: separate foreign keys for polymorphic references, simple local database migration with backup, iterative application-level hierarchy traversal using breadth-first search patterns consistent with existing service layer architecture.

## Technical Context

**Language/Version**: Python 3.10+ (per constitution technology stack)
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter (desktop UI)
**Storage**: SQLite with WAL mode (per constitution, local desktop application)
**Testing**: pytest (per constitution, minimum 70% service layer coverage)
**Target Platform**: Windows desktop application (single-user, local installation)
**Project Type**: Single desktop application with layered architecture
**Performance Goals**: <500ms inventory queries for 10k items, <2s CRUD operations, <30s assembly creation
**Constraints**: Zero data loss during migration, local SQLite database, maintain existing service layer APIs during transition
**Scale/Scope**: Single-user desktop application, support hierarchies up to 5 levels deep, handle up to 20 components per assembly

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Desktop Phase Constitution Questions:

✅ **Does this design block web deployment?** → NO
- Service layer remains UI-independent with clean business logic separation
- SQLAlchemy ORM supports migration to PostgreSQL for web deployment
- Polymorphic relationships work across database backends
- Migration to web would require multi-tenant schema updates but core design is compatible

✅ **Is the service layer UI-independent?** → YES
- All business logic contained in services layer (`src/services/`)
- Models define schema and relationships only (`src/models/`)
- UI layer will consume services without direct database access

✅ **Are business rules in services, not UI?** → YES
- Hierarchy validation, circular reference prevention in services
- FIFO compliance and cost calculations remain in services layer
- Assembly composition logic encapsulated in services

✅ **What's the web migration cost?** → MEDIUM (acceptable per constitution)
- **Low cost**: Service layer already abstracted, testable business logic
- **Medium cost**: Multi-user schema modifications needed (tenant isolation)
- **Migration path**: Add user_id columns, implement tenant filtering, wrap services with API layer

**Web Migration Documentation**: Service layer design enables API wrapper with minimal refactoring. Polymorphic relationships support multi-tenant scenarios. Primary cost is schema updates for user isolation.

## Project Structure

### Documentation (this feature)

```
kitty-specs/004-finishedunit-model-refactoring/
├── plan.md              # This file (/spec-kitty.plan command output)
├── research.md          # Phase 0 output (/spec-kitty.plan command)
├── data-model.md        # Phase 1 output (/spec-kitty.plan command)
├── quickstart.md        # Phase 1 output (/spec-kitty.plan command)
├── contracts/           # Phase 1 output (/spec-kitty.plan command)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks command - NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── finished_unit.py        # Individual consumable items (renamed from finished_good.py)
│   ├── finished_good.py        # Assembly packages (new model)
│   └── composition.py          # Junction table for hierarchical relationships
├── services/
│   ├── finished_unit_service.py    # CRUD operations for individual units
│   ├── finished_good_service.py    # Assembly management with hierarchy traversal
│   ├── composition_service.py      # Component relationship management
│   └── migration_service.py        # Data migration and validation utilities
├── migrations/
│   ├── migration_orchestrator.py   # Coordinate multi-step migration process
│   └── backup_validator.py         # Pre/post migration validation
└── ui/
    └── [existing UI files updated to use new services]

tests/
├── unit/
│   ├── test_finished_unit_service.py
│   ├── test_finished_good_service.py
│   └── test_migration_service.py
├── integration/
│   ├── test_hierarchy_traversal.py
│   └── test_migration_workflow.py
└── fixtures/
    └── migration_test_data.py
```

**Structure Decision**: Single desktop project structure with enhanced models and services layers. Maintains existing layered architecture (UI → Services → Models → Database) per constitution. Migration services added for safe schema transformation.

## Complexity Tracking

*No constitution violations - all design decisions align with established principles.*

## Implementation Strategy

### Migration Approach
1. **Backup Phase**: Create full database backup with validation
2. **Schema Phase**: Rename existing tables, create new schema
3. **Data Phase**: Transform existing FinishedGood records to FinishedUnit
4. **Validation Phase**: Verify data integrity and referential consistency
5. **Rollback Plan**: Restore from backup if validation fails

### Hierarchy Traversal Pattern
- Breadth-first search using iterative application logic
- Consistent with existing service layer multi-query patterns
- Leverage SQLAlchemy relationship loading for efficiency
- Circular reference prevention with visited node tracking

### Testing Strategy
- Unit tests for all new service methods
- Integration tests for migration workflow
- Performance benchmarks for hierarchy queries
- Migration dry-run validation with test datasets