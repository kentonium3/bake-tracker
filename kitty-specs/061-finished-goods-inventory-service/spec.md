# Feature Specification: Finished Goods Inventory Service

**Feature Branch**: `061-finished-goods-inventory-service`
**Created**: 2026-01-21
**Status**: Draft
**Input**: See `docs/func-spec/F061_finished_goods_inventory.md`

## Overview

Finished goods inventory tracking exists in the data model (`inventory_count` fields on FinishedUnit and FinishedGood), but lacks service layer support. Production runs add inventory without service coordination, assembly runs may fail due to insufficient components, and there is no way to query current stock levels programmatically.

This feature adds a finished goods inventory service with session-aware primitives, enabling validated inventory operations and preparing for future UI implementation.

**Phase**: Service Layer Only (Phase 2) - UI deferred to Phase 3

## User Scenarios & Testing

### User Story 1 - Query Inventory Status (Priority: P1)

As a system component (production service, assembly service, or future UI), I need to query current inventory levels for finished units and finished goods so I can make informed decisions about production planning and assembly feasibility.

**Why this priority**: All other inventory operations depend on accurate status queries. Without knowing current stock, validation and adjustments cannot function correctly.

**Independent Test**: Can be fully tested by querying inventory for sample finished units/goods and verifying counts match database state.

**Acceptance Scenarios**:

1. **Given** finished units exist with varying inventory counts, **When** querying all finished unit inventory, **Then** returns list with item identifiers and current counts
2. **Given** a specific finished unit ID, **When** querying that item's inventory, **Then** returns that item's current count and value
3. **Given** items with zero inventory exist, **When** querying with exclude-zero option, **Then** zero-stock items are omitted from results
4. **Given** an optional session parameter is provided, **When** querying inventory, **Then** query executes within the provided session context

---

### User Story 2 - Validate Consumption Before Assembly (Priority: P1)

As the assembly service, I need to validate that sufficient component inventory exists before attempting assembly so that assembly operations fail fast with clear error messages rather than mid-operation.

**Why this priority**: Prevents partial operations and data inconsistency. Assembly cannot proceed safely without pre-validation.

**Independent Test**: Can be tested by checking availability for various quantities against known inventory levels.

**Acceptance Scenarios**:

1. **Given** a finished unit with inventory_count of 10, **When** checking availability for quantity 5, **Then** returns available=true with current count
2. **Given** a finished unit with inventory_count of 3, **When** checking availability for quantity 5, **Then** returns available=false with shortage amount of 2
3. **Given** assembly service provides a session, **When** validating within that session, **Then** validation sees uncommitted changes from the same transaction
4. **Given** a finished good with inventory_count of 0, **When** checking availability for any positive quantity, **Then** returns available=false with full shortage amount

---

### User Story 3 - Adjust Inventory with Tracking (Priority: P1)

As the production or assembly service, I need to adjust inventory counts with reason tracking so that inventory changes are validated, atomic, and traceable.

**Why this priority**: Core mutation operation that all inventory changes depend on. Production completion and assembly consumption both require this.

**Independent Test**: Can be tested by adjusting inventory and verifying count changes and reason recording.

**Acceptance Scenarios**:

1. **Given** a finished unit with inventory_count of 5, **When** adjusting by +3 with reason="production", **Then** inventory becomes 8 and adjustment is tracked
2. **Given** a finished unit with inventory_count of 5, **When** adjusting by -2 with reason="assembly", **Then** inventory becomes 3 and adjustment is tracked
3. **Given** a finished unit with inventory_count of 2, **When** attempting to adjust by -5, **Then** operation fails with clear error message about insufficient inventory
4. **Given** production service provides a session, **When** adjusting inventory within that session, **Then** change is not committed until caller commits
5. **Given** a negative adjustment request, **When** validation fails, **Then** no partial changes occur and session state is unchanged

---

### User Story 4 - Atomic Multi-Item Assembly Operations (Priority: P2)

As the assembly service, I need to consume multiple component items and create a finished good atomically so that partial assemblies cannot occur.

**Why this priority**: Depends on individual adjustment and validation operations from P1 stories. Ensures data consistency for complex operations.

**Independent Test**: Can be tested by performing assembly with multiple components and verifying all-or-nothing behavior on failure.

**Acceptance Scenarios**:

1. **Given** assembly requires 3 different component items, **When** all components have sufficient inventory, **Then** all consumptions and creation succeed together
2. **Given** assembly requires 3 components but one is insufficient, **When** assembly is attempted, **Then** no inventory changes occur for any item
3. **Given** assembly service passes session to all inventory calls, **When** an error occurs mid-operation, **Then** rollback restores all inventory to original state

---

### User Story 5 - Identify Low Stock Items (Priority: P2)

As a production planner (or future UI), I need to identify finished goods with inventory below a threshold so I can prioritize production.

**Why this priority**: Supports planning but not required for core operations. Enhances visibility once basic operations work.

**Independent Test**: Can be tested by setting threshold and verifying correct items returned.

**Acceptance Scenarios**:

1. **Given** items with counts [2, 5, 10, 15] and threshold of 6, **When** querying low stock, **Then** returns items with counts 2 and 5
2. **Given** default threshold (configurable), **When** querying without explicit threshold, **Then** uses default value
3. **Given** option to filter by item type, **When** requesting only finished units, **Then** finished goods are excluded

---

### User Story 6 - Calculate Total Inventory Value (Priority: P3)

As a business owner (or future reporting UI), I need to calculate the total value of finished goods inventory so I can understand asset value.

**Why this priority**: Reporting/analytics feature that doesn't affect core operations. Useful but not essential for MVP.

**Independent Test**: Can be tested by calculating value for known inventory and costs.

**Acceptance Scenarios**:

1. **Given** finished units with known costs and counts, **When** calculating total value, **Then** returns sum of (count x cost) for all items
2. **Given** items with zero inventory, **When** calculating total, **Then** zero-inventory items contribute zero to total
3. **Given** both finished units and finished goods exist, **When** calculating grand total, **Then** includes both categories

---

### User Story 7 - Export/Import Inventory State (Priority: P3)

As a user performing backup/restore operations, I need finished goods inventory state to be preserved through export/import cycles.

**Why this priority**: Data preservation feature. Important for system reliability but not for daily operations.

**Independent Test**: Can be tested by exporting, clearing, importing, and verifying inventory counts match.

**Acceptance Scenarios**:

1. **Given** finished units with inventory counts, **When** performing full backup export, **Then** inventory counts are included in export data
2. **Given** export file with inventory state, **When** importing into fresh database, **Then** inventory counts are restored correctly
3. **Given** export/import round-trip, **When** comparing before and after, **Then** all inventory counts match

---

### Edge Cases

- What happens when adjusting inventory for an item that doesn't exist? (Return clear error)
- How does system handle concurrent adjustments to same item? (Session isolation prevents conflicts within transaction; cross-transaction handled by database constraints)
- What happens when cost fields are null during value calculation? (Treat as zero or skip with warning)
- How does system handle negative inventory_count in database? (Database constraint prevents this; service validates before attempting)

## Requirements

### Functional Requirements

- **FR-001**: Service MUST accept optional `session` parameter on all methods (F060 compliance)
- **FR-002**: When session is provided, service MUST use it exclusively without creating internal sessions
- **FR-003**: When session is provided, service MUST NOT commit internally (caller owns transaction)
- **FR-004**: Service MUST provide inventory status queries for finished units and finished goods
- **FR-005**: Service MUST validate availability before consumption operations
- **FR-006**: Service MUST prevent inventory adjustments that would result in negative counts
- **FR-007**: Service MUST track reason for all inventory adjustments (production, assembly, consumption, spoilage, gift, adjustment)
- **FR-008**: Service MUST return previous count, new count, and change amount for adjustments
- **FR-009**: Service MUST support filtering low-stock items by configurable threshold
- **FR-010**: Service MUST calculate inventory value using item costs
- **FR-011**: Business logic in model methods (`is_available`, `update_inventory`, `can_assemble`) MUST be moved to service layer
- **FR-012**: Export service MUST include finished goods inventory counts
- **FR-013**: Import service MUST restore finished goods inventory counts

### Key Entities

- **FinishedUnit**: A produced item (e.g., batch of cookies) with inventory_count field. Cost determined at production time.
- **FinishedGood**: An assembled package (e.g., gift box) containing finished units, with inventory_count field. Cost is sum of component costs.
- **Inventory Adjustment**: A tracked change to inventory with reason, quantity, and optional notes. (Minimal tracking in Phase 2; full audit trail deferred)

## Success Criteria

### Measurable Outcomes

- **SC-001**: All service methods accept optional session parameter and function correctly with or without it
- **SC-002**: Overconsumption attempts are blocked 100% of the time with clear error messages
- **SC-003**: Multi-item assembly operations are fully atomic (all succeed or all fail)
- **SC-004**: Export/import round-trip preserves all inventory counts exactly
- **SC-005**: Service layer tests achieve >70% coverage
- **SC-006**: No direct inventory_count field modifications bypass the service layer after implementation

## Out of Scope

- UI implementation (deferred to Phase 3)
- Historical inventory tracking / full audit trail
- FIFO inventory management (not needed for finished goods - cost determined at production time)
- Consumption ledger records (simple counting sufficient)
- Manual inventory adjustment UI
- Low stock alerts/notifications (query only)
- Event fulfillment allocation
- Inventory forecasting/planning

## Assumptions

- Cost fields exist on FinishedUnit and FinishedGood models (planning phase will verify)
- Database CHECK constraint (inventory_count >= 0) is already in place
- F060 session ownership pattern is established and understood
- Existing production and assembly services can be updated to use new inventory primitives

## Dependencies

- **F060**: Architecture Hardening - Session ownership pattern (must be followed)
- **F049**: Import/Export System - Export/import coordination patterns
