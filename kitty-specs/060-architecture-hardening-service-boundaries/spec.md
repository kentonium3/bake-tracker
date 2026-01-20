# Feature Specification: Architecture Hardening - Service Boundaries & Session Management

**Feature Branch**: `060-architecture-hardening-service-boundaries`
**Created**: 2026-01-20
**Status**: Draft
**Input**: Functional spec `docs/func-spec/F060_architecture_hardening_service_boundaries.md`

---

## Overview

This feature hardens the foundational architecture to address critical gaps in service boundary discipline and session management identified during architecture review. The hardening ensures session ownership discipline, planning snapshot completeness, and assembly/production path consistency before continuing with feature development.

**Problem Statement**: Current architecture has fragile session management patterns that create atomicity risks:
- Services open sessions inside transactions, breaking caller control
- Planning snapshots are incomplete (missing ingredient aggregation, costs)
- Assembly service lacks ledger entries for nested finished goods consumption
- Two competing production service patterns with inconsistent invariants
- Planning orchestration uses detached sessions, causing stale reads
- Staleness detection misses key BOM mutations

---

## User Scenarios & Testing

### User Story 1 - Atomic Multi-Service Operations (Priority: P1)

As a developer working on the bake-tracker codebase, I need all multi-service operations to execute atomically so that partial failures don't leave the database in an inconsistent state.

**Why this priority**: Session atomicity is the foundation that all other requirements depend on. Without proper session ownership, transaction boundaries cannot be controlled, leading to data corruption and audit trail gaps.

**Independent Test**: Can be verified by creating a multi-service operation that fails partway through and confirming no partial writes persist.

**Acceptance Scenarios**:

1. **Given** a caller opens a session and calls multiple services, **When** any downstream service fails, **Then** all changes roll back together with no partial writes persisted.
2. **Given** a service method receives a session parameter, **When** the method executes, **Then** it uses the provided session exclusively (no internal `session_scope`).
3. **Given** a service method receives a session parameter, **When** the method completes, **Then** it does not commit internally (caller controls transaction).
4. **Given** a service method is called without a session parameter, **When** the method executes, **Then** it opens its own session for backward compatibility.

---

### User Story 2 - Complete Planning Snapshots (Priority: P1)

As a user creating production plans, I need planning snapshots to capture aggregated ingredients and cost baselines so that I can audit variances between planned and actual production.

**Why this priority**: Planning snapshots represent the plan contract. Without complete ingredient/cost data, variance analysis and requirement change detection are impossible.

**Independent Test**: Create a production plan and verify the snapshot contains aggregated ingredients with quantities, units, and cost-per-unit at snapshot time.

**Acceptance Scenarios**:

1. **Given** a production plan is calculated, **When** the snapshot is created, **Then** `calculation_results["aggregated_ingredients"]` contains ingredient slug, display name, required quantity, unit, and cost_per_unit.
2. **Given** an ingredient's cost changes after plan creation, **When** viewing the plan, **Then** the original snapshotted cost is preserved for variance analysis.
3. **Given** a recipe composition changes after plan creation, **When** staleness is checked, **Then** the plan is marked stale.

---

### User Story 3 - Assembly Audit Trail for Nested Finished Goods (Priority: P1)

As a user assembling gift packages that contain nested finished goods (e.g., a cookie tin inside a gift basket), I need consumption records created for those nested components so that the audit trail is complete and costs are accurately tracked.

**Why this priority**: Ledger completeness is essential for audit integrity. Currently, nested finished goods are consumed without creating ledger entries, breaking the audit chain.

**Independent Test**: Assemble a package containing a nested finished good and verify a consumption record is created with the cost snapshotted at assembly time.

**Acceptance Scenarios**:

1. **Given** an assembly uses a nested finished good component, **When** the assembly is recorded, **Then** a consumption record is created for the nested finished good.
2. **Given** a nested finished good is consumed in assembly, **When** the consumption record is created, **Then** the cost is snapshotted at consumption time (not calculated later).
3. **Given** an assembly with nested finished goods is exported, **When** the export completes, **Then** the nested consumption records are included in the export.

---

### User Story 4 - Single Production Path (Priority: P2)

As a developer, I need a single consistent production service pattern so that all production operations follow the same invariants for session threading, recipe snapshots, and loss tracking.

**Why this priority**: Two competing production patterns create confusion and inconsistent behavior. Consolidating to the mature batch production pattern ensures consistent guarantees.

**Independent Test**: Search codebase for any calls to the old `production_service.record_production` method - none should remain after migration.

**Acceptance Scenarios**:

1. **Given** the old `production_service.record_production` method exists, **When** migration is complete, **Then** all callers have been updated to use `batch_production_service.record_production`.
2. **Given** migration is complete, **When** reviewing the codebase, **Then** `production_service.record_production` method has been removed.
3. **Given** a user records production via any UI path, **When** the operation completes, **Then** it uses the batch production service with proper session threading.

---

### User Story 5 - Planning Orchestration Session Discipline (Priority: P2)

As a user checking production progress or generating shopping lists, I need these operations to execute within proper session boundaries so that data is consistent within my transaction.

**Why this priority**: Planning orchestration currently uses detached sessions, causing stale reads and breaking caller transaction boundaries.

**Independent Test**: Execute a progress calculation within a transaction and verify it sees uncommitted changes from that transaction.

**Acceptance Scenarios**:

1. **Given** progress calculation receives a session, **When** it queries event data, **Then** it uses the provided session (not detached reads).
2. **Given** shopping list operations receive a session, **When** `mark_shopping_complete` is called, **Then** no internal commit occurs (caller controls transaction).
3. **Given** feasibility is calculated, **When** blockers are identified, **Then** cost and assignment blockers are returned distinctly from inventory blockers.
4. **Given** progress is calculated, **When** `available_to_assemble` is determined, **Then** it is calculated via the feasibility service (not hardcoded).

---

### User Story 6 - Comprehensive Staleness Detection (Priority: P2)

As a user with an existing production plan, I need the system to detect when BOM changes affect my plan so that I know when replanning is needed.

**Why this priority**: Current staleness detection only checks `Composition.created_at`, missing updates, yield changes, and packaging/material changes.

**Independent Test**: Modify a FinishedUnit yield after creating a plan and verify the plan is marked stale.

**Acceptance Scenarios**:

1. **Given** a plan exists and a Composition is updated, **When** staleness is checked, **Then** the plan is marked stale.
2. **Given** a plan exists and a FinishedUnit yield changes, **When** staleness is checked, **Then** the plan is marked stale.
3. **Given** a plan exists and packaging assignments change, **When** staleness is checked, **Then** the plan is marked stale.
4. **Given** a plan exists and a non-schema change occurs (e.g., display name), **When** staleness is checked, **Then** the plan is NOT marked stale.

---

### User Story 7 - Event Service Transactional Support (Priority: P3)

As a developer calling event service methods within a transaction, I need those methods to accept an optional session parameter so that my reads are part of the same transaction.

**Why this priority**: Event service helpers always open their own sessions, preventing planning services from including event reads in their transactions.

**Independent Test**: Call an event service get method with a session parameter and verify it uses that session.

**Acceptance Scenarios**:

1. **Given** an event service helper method is called with a session, **When** the method executes, **Then** it uses the provided session.
2. **Given** an event service helper method is called without a session, **When** the method executes, **Then** it opens its own session (backward compatible).

---

### Edge Cases

- What happens when a session is passed but is already closed/expired? (Should raise clear error)
- How does the system handle nested service calls where both outer and inner could create sessions? (Inner must use outer's session)
- What if a production record references a recipe that was deleted mid-transaction? (Should fail atomically)
- How does staleness handle Composition deletion vs modification? (Both should trigger staleness)
- What if aggregated ingredient calculation encounters circular recipe references? (Should be prevented at recipe creation time per existing validation)

---

## Requirements

### Functional Requirements

- **FR-001**: All service methods MUST accept an optional `session` parameter
- **FR-002**: When a session is provided, services MUST use it exclusively (no internal `session_scope`)
- **FR-003**: When a session is provided, services MUST NOT commit internally (caller controls transaction)
- **FR-004**: When no session is provided, services MUST open their own session (backward compatibility)
- **FR-005**: All downstream service calls MUST receive the session parameter when one is provided
- **FR-006**: Planning snapshots MUST include `aggregated_ingredients` with slug, name, quantity, unit, and cost_per_unit
- **FR-007**: Aggregated ingredients MUST be calculated from recipe composition using correct yield ratios
- **FR-008**: Cost baselines in snapshots MUST be captured at snapshot time (not live lookup)
- **FR-009**: Assembly service MUST create consumption records when nested FinishedGoods are consumed
- **FR-010**: Nested finished good consumption records MUST include cost snapshotted at consumption time
- **FR-011**: Export MUST include nested finished good consumption records
- **FR-012**: The old `production_service.record_production` method MUST be removed after caller migration
- **FR-013**: All production callers MUST be migrated to `batch_production_service.record_production`
- **FR-014**: Planning progress MUST operate within a single session with snapshot data
- **FR-015**: Shopping list operations MUST respect caller transaction (no internal commits)
- **FR-016**: Feasibility service MUST surface cost and assignment blockers distinctly
- **FR-017**: `available_to_assemble` MUST be calculated via feasibility service
- **FR-018**: Staleness detection MUST detect Composition updates (not just created_at)
- **FR-019**: Staleness detection MUST detect FinishedUnit yield changes
- **FR-020**: Staleness detection MUST detect packaging and material assignment changes
- **FR-021**: Composition model MUST have an `updated_at` timestamp (or equivalent hash mechanism)
- **FR-022**: Event service helper methods (get_*, list_*) MUST accept optional session parameter
- **FR-023**: Event service helpers MUST use provided session when available

### Key Entities

- **Session**: Database transaction context that must flow through all service calls in a multi-step operation
- **Planning Snapshot**: Immutable capture of plan state including calculation results, aggregated ingredients, and cost baselines
- **Consumption Record**: Ledger entry tracking what was consumed, when, at what cost, and by which operation
- **Composition**: Recipe component relationship that links recipes to ingredients or nested recipes with quantity and unit

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: All service methods accept optional session parameter (100% coverage across services)
- **SC-002**: No `session_scope` calls exist when a session parameter is provided (verified by code review pattern)
- **SC-003**: Multi-service operations roll back completely on failure (verified by transaction rollback tests)
- **SC-004**: Planning snapshots include complete aggregated ingredient data (verified by snapshot inspection tests)
- **SC-005**: All assembly operations create consumption records for all component types including nested finished goods (verified by ledger completeness tests)
- **SC-006**: Zero calls to deprecated `production_service.record_production` remain in codebase after migration
- **SC-007**: Staleness detection triggers for all BOM mutation types (verified by mutation detection tests)
- **SC-008**: Export/import round-trip preserves complete ledger including nested consumption records
- **SC-009**: Test coverage includes atomicity guarantee verification for multi-service operations

---

## Out of Scope

The following items are explicitly excluded from this feature:

- Materials UI metric base unit updates (separate feature)
- Material FIFO consumption type fixes (linear/square/each) (separate feature)
- New planning features or UI enhancements (this is foundation hardening only)
- Export/import format changes beyond ledger completeness
- Performance optimization (desktop scale makes this premature)
- Database migration scripts (desktop app uses export/reset/import workflow)
- Composition versioning or content hashing (updated_at timestamp is sufficient)
- Unified cost model helpers (some duplication acceptable for now)
- Export/import of planning snapshots (not needed for current workflows)

---

## Assumptions

1. The mature patterns in `batch_production_service` are the correct reference for session threading discipline
2. Desktop single-user context means full deprecation of old production service is safe (no API versioning needed)
3. Export/reset/import workflow is acceptable for any schema changes (no migration scripts required)
4. The existing `session_scope` context manager properly handles rollback on exception
5. Circular recipe references are already prevented by existing validation (no new validation needed)
6. Cost snapshot timing should match the existing packaging/material consumption pattern in assembly service

---

## Dependencies

- Requires understanding of existing mature patterns in `batch_production_service.py`
- Requires understanding of existing assembly ledger patterns in `assembly_service.py`
- Requires review of all services to identify session parameter gaps
- Requires identification of all callers of deprecated production service

---

## References

- Source specification: `docs/func-spec/F060_architecture_hardening_service_boundaries.md`
- Architecture principles: `docs/design/architecture.md`
- Session management remediation: `docs/design/session_management_remediation_spec.md`
- Constitution: `.kittify/memory/constitution.md`
