# Feature Specification: FinishedUnit Model Refactoring

**Feature Branch**: `004-finishedunit-model-refactoring`
**Created**: 2025-11-14
**Status**: Draft
**Input**: User description: "Transform the existing FinishedGood model into a two-tier hierarchical system where FinishedUnit represents individual consumable units renamed from FinishedGood and a new FinishedGood model represents assembled items that can contain both FinishedUnits and other FinishedGoods in hierarchical compositions for complex packaging scenarios"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Track Individual Consumable Items (Priority: P1)

Users need to track individual baked goods (cookies, brownies, etc.) as discrete consumable units with their own inventory, recipes, and properties.

**Why this priority**: Forms the foundation for all inventory tracking - without individual units, no other packaging scenarios are possible.

**Independent Test**: Can be fully tested by creating, updating, and deleting individual FinishedUnit items and delivers basic inventory management capability.

**Acceptance Scenarios**:

1. **Given** the system has baking inventory, **When** a user creates a new FinishedUnit (e.g., "Chocolate Chip Cookie"), **Then** the system stores it with recipe, inventory count, and unit properties
2. **Given** existing FinishedUnits, **When** a user views the inventory, **Then** they see individual consumable items with current quantities
3. **Given** a FinishedUnit exists, **When** production is completed, **Then** inventory counts are updated for the individual unit

---

### User Story 2 - Create Simple Package Assemblies (Priority: P2)

Users need to bundle multiple individual FinishedUnits into gift packages, variety boxes, or multi-item sets for holiday gift giving.

**Why this priority**: Essential for holiday baking gift scenarios - enables basic packaging functionality that delivers immediate business value.

**Independent Test**: Can be fully tested by creating a FinishedGood assembly containing multiple FinishedUnits and verifying component tracking.

**Acceptance Scenarios**:

1. **Given** multiple FinishedUnits exist, **When** a user creates a gift package FinishedGood, **Then** the system tracks which individual units are included and their quantities
2. **Given** a gift package assembly, **When** inventory is checked, **Then** the system shows both the package availability and component availability
3. **Given** a package is distributed, **When** inventory is updated, **Then** both package and component unit counts are decremented

---

### User Story 3 - Create Nested Package Hierarchies (Priority: P3)

Users need to create complex nested assemblies where packages can contain both individual units and other packages, enabling sophisticated gift set combinations.

**Why this priority**: Supports advanced packaging scenarios for complex gift offerings - valuable but not essential for basic operations.

**Independent Test**: Can be fully tested by creating a FinishedGood that contains both FinishedUnits and other FinishedGoods, verifying nested hierarchy tracking.

**Acceptance Scenarios**:

1. **Given** existing FinishedUnits and simple packages, **When** a user creates a deluxe gift set, **Then** the system tracks multi-level composition including packages within packages
2. **Given** a nested assembly, **When** inventory changes occur, **Then** the system correctly propagates changes through all hierarchy levels

---

### Edge Cases

- What happens when a component of an assembly becomes unavailable or goes out of stock?
- How does the system handle circular references where Package A contains Package B which contains Package A?
- What occurs when trying to delete a FinishedUnit that is used as a component in active assemblies?
- How does the system handle partial assembly scenarios where only some components are available?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support two distinct entity types: FinishedUnit (individual consumable items) and FinishedGood (assembled packages)
- **FR-002**: FinishedUnit MUST represent individual baked goods with recipe associations, inventory counts, and unit-specific properties
- **FR-003**: FinishedGood MUST represent assembled packages that can contain both FinishedUnits and other FinishedGoods in hierarchical compositions
- **FR-004**: System MUST support polymorphic component references allowing FinishedGoods to contain any combination of FinishedUnits and other FinishedGoods
- **FR-005**: System MUST track quantities for each component within assemblies (e.g., "3 chocolate cookies + 2 brownie bites")
- **FR-006**: System MUST prevent circular references in assembly hierarchies
- **FR-007**: System MUST maintain referential integrity when components are modified or deleted
- **FR-008**: System MUST support querying available inventory considering both standalone items and assembly components
- **FR-009**: System MUST provide assembly type categorization (gift box, variety pack, holiday set, etc.)
- **FR-010**: Existing FinishedGood data MUST be migrated to the new FinishedUnit model without data loss

### Key Entities *(include if feature involves data)*

- **FinishedUnit**: Represents individual consumable baked goods (renamed from current FinishedGood), includes recipe association, inventory count, unit cost, and production notes
- **FinishedGood**: Represents assembled packages containing multiple components, includes assembly metadata, total cost calculation, and packaging instructions
- **Composition**: Junction entity linking FinishedGoods to their component items (both FinishedUnits and other FinishedGoods), tracks component quantities and assembly relationships

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can create and manage individual FinishedUnits with full CRUD operations completing in under 2 seconds per operation
- **SC-002**: Users can create package assemblies with up to 20 components completing assembly definition in under 30 seconds
- **SC-003**: System supports hierarchical assemblies up to 5 levels deep without performance degradation
- **SC-004**: Inventory queries return results for both individual units and complex assemblies in under 500ms for datasets up to 10,000 items
- **SC-005**: Data migration from existing FinishedGood model completes successfully with 100% data preservation and zero downtime
- **SC-006**: Assembly integrity constraints prevent all circular reference attempts with clear error messaging
- **SC-007**: Complex gift package creation reduces setup time by 60% compared to manual component tracking

## Assumptions

- Existing FinishedGood records represent individual consumable units and should be migrated to FinishedUnit model
- Assembly hierarchies will typically be 2-3 levels deep in real-world usage
- Component quantities within assemblies will be whole numbers (no fractional units)
- Performance requirements are based on typical small-to-medium bakery inventory volumes
- Database supports modern foreign key constraints and polymorphic associations
- SQLAlchemy 2.x association object patterns will be used for composition relationships

## Dependencies and Constraints

- Migration must occur during a maintenance window to ensure data consistency
- New model structure must be backward compatible with existing service layer APIs during transition period
- Database schema changes must be reversible through migration rollback capabilities
- Performance optimization will require appropriate database indexing on composition relationships