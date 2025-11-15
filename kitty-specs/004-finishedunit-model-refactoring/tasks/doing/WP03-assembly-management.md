---
work_package_id: "WP03"
subtasks:
  - "T011"
  - "T012"
  - "T013"
  - "T014"
title: "Assembly Management Services"
phase: "Phase 3 - User Story 2 Implementation"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "26869"
history:
  - timestamp: "2025-11-14T17:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
  - timestamp: "2025-11-15T00:50:00Z"
    lane: "doing"
    agent: "claude"
    shell_pid: "26869"
    action: "Started implementation"
---

# Work Package Prompt: WP03 – Assembly Management Services

## Objectives & Success Criteria

- Implement complete User Story 2: Create Simple Package Assemblies (Priority P2)
- Create FinishedGood service with assembly creation and component tracking
- Create Composition service for polymorphic relationship management
- Enable gift package creation with multiple FinishedUnit components
- Validate component availability and inventory tracking for assemblies
- Ready for User Story 3 implementation (nested hierarchies)

## Context & Constraints

- **Prerequisites**: WP02 (Core Service Layer) completed with working FinishedUnit service
- **User Story Focus**: P2 - Basic packaging functionality for holiday gift scenarios
- **Architecture**: Separate foreign keys pattern for polymorphic component references
- **Performance**: <30s assembly creation, <500ms component queries
- **Business Logic**: Component availability validation, cost aggregation, inventory management
- **References**:
  - `contracts/finished_good_service.md`: Assembly service interface
  - `contracts/composition_service.md`: Relationship management interface
  - `data-model.md`: Polymorphic relationship specifications

## Subtasks & Detailed Guidance

### Subtask T011 – Implement FinishedGood Service with Assembly Creation and Management

- **Purpose**: Core assembly service implementing User Story 2 with component tracking
- **Steps**:
  1. Create `src/services/finished_good_service.py` following contract specifications
  2. Implement core operations: get_finished_good_by_id(), get_finished_good_by_slug(), get_all_finished_goods()
  3. Implement assembly CRUD: create_finished_good(), update_finished_good(), delete_finished_good()
  4. Implement component management: add_component(), remove_component(), update_component_quantity()
  5. Implement cost calculation: calculate_total_cost() with component aggregation
  6. Implement availability checking: check_assembly_availability() with component validation
  7. Implement assembly production: create_assembly_from_inventory(), disassemble_into_components()
  8. Add comprehensive error handling for assembly integrity violations
- **Files**: `src/services/finished_good_service.py`, `src/services/__init__.py`
- **Parallel?**: No - core assembly functionality
- **Notes**: Must integrate with FinishedUnit service for component validation and inventory management

### Subtask T012 – Implement Composition Service for Relationship Management

- **Purpose**: Manage junction table operations and polymorphic relationships between assemblies and components
- **Steps**:
  1. Create `src/services/composition_service.py` following contract specifications
  2. Implement composition CRUD: create_composition(), get_composition_by_id(), update_composition(), delete_composition()
  3. Implement assembly queries: get_assembly_components(), get_component_usages()
  4. Implement validation: validate_component_exists(), check_composition_integrity()
  5. Implement bulk operations: bulk_create_compositions(), reorder_assembly_components()
  6. Implement cost utilities: calculate_assembly_component_costs(), calculate_required_inventory()
  7. Add comprehensive error handling for referential integrity violations
  8. Integrate with both FinishedUnit and FinishedGood services for component validation
- **Files**: `src/services/composition_service.py`, `src/services/__init__.py`
- **Parallel?**: No - depends on T011 for FinishedGood service integration
- **Notes**: Critical for polymorphic relationship integrity - extensive validation required

### Subtask T013 – Add Assembly Type Enumeration and Metadata Handling

- **Purpose**: Support assembly categorization and business logic for different package types
- **Steps**:
  1. Create `src/models/assembly_type.py` with enum definition (gift_box, variety_pack, holiday_set, bulk_pack, custom_order)
  2. Add assembly type validation in FinishedGood model
  3. Implement assembly type filtering in FinishedGood service: get_assemblies_by_type()
  4. Add assembly type-specific business rules (e.g., component limits, pricing rules)
  5. Update FinishedGood creation to require valid assembly type
  6. Add assembly type metadata support (e.g., display names, descriptions)
- **Files**: `src/models/assembly_type.py`, update `src/models/finished_good.py`, `src/services/finished_good_service.py`
- **Parallel?**: Yes - can proceed alongside T011/T012 development
- **Notes**: Enum values should be extensible for future assembly types

### Subtask T014 – Create Unit Tests for Assembly Services (70%+ Coverage)

- **Purpose**: Comprehensive testing for all assembly management functionality
- **Steps**:
  1. Create `tests/unit/services/test_finished_good_service.py` with complete test coverage
  2. Create `tests/unit/services/test_composition_service.py` with relationship testing
  3. Test assembly CRUD operations with component validation scenarios
  4. Test component management with availability checking and inventory integration
  5. Test cost calculation scenarios with multi-component assemblies
  6. Test assembly production workflows with inventory consumption/creation
  7. Test error handling for component availability failures and integrity violations
  8. Create comprehensive fixtures with realistic assembly and component data
- **Files**: `tests/unit/services/test_finished_good_service.py`, `tests/unit/services/test_composition_service.py`, `tests/fixtures/assembly_fixtures.py`
- **Parallel?**: No - requires T011, T012, T013 completion
- **Notes**: Focus on User Story 2 acceptance scenarios and edge cases

## Test Strategy

- **Unit Test Coverage**: Minimum 70% service layer coverage per constitution
- **Integration Testing**: Cross-service operations between FinishedGood, Composition, and FinishedUnit services
- **Test Commands**:
  - `pytest tests/unit/services/test_finished_good_service.py -v --cov=src.services.finished_good_service`
  - `pytest tests/unit/services/test_composition_service.py -v --cov=src.services.composition_service`
- **Test Scenarios**: Focus on User Story 2 acceptance criteria with realistic gift package examples

## Risks & Mitigations

- **Component Availability Risk**: Comprehensive validation before assembly creation, clear error messages
- **Inventory Consistency**: Transactional operations for assembly production, rollback on failures
- **Performance Risk**: Optimize component queries with proper indexing, batch operations where possible
- **Business Logic Complexity**: Clear separation between FinishedGood and Composition services, well-defined interfaces

## Definition of Done Checklist

- [ ] FinishedGood service implemented with assembly management (T011)
- [ ] Composition service implemented with relationship management (T012)
- [ ] Assembly type enumeration and metadata handling added (T013)
- [ ] Unit tests achieve >70% coverage for both services (T014)
- [ ] All User Story 2 acceptance scenarios pass:
  - [ ] Create gift package FinishedGood with multiple FinishedUnit components
  - [ ] Track individual units and quantities in packages
  - [ ] Show both package availability and component availability
  - [ ] Update both package and component counts when distributed
- [ ] Performance targets met: <30s assembly creation, <500ms component queries
- [ ] Component availability validation prevents invalid assemblies
- [ ] Cost aggregation calculates correct total from component costs
- [ ] Assembly production manages inventory correctly (consumption/creation)
- [ ] Error handling provides clear messages for business rule violations
- [ ] Integration with FinishedUnit service maintains data consistency

## Activity Log

- 2025-11-15T17:15:32Z – system – shell_pid= – lane=doing – Moved to doing
