# Feature Specification: Service Session Consistency Hardening

**Feature Branch**: `062-service-session-consistency-hardening`
**Created**: 2026-01-22
**Status**: Draft
**Input**: See docs/func-spec/F062_service_session_consistency_hardening.md for specs on this feature.

## Overview

Complete session discipline across all service layer functions to prevent silent data loss and enable reliable multi-service transactions. This foundational work ensures all services can participate in caller-controlled transactions with consistent patterns.

**Problem**: Current services have inconsistent session handling - some accept session parameters, some ignore them, and most event service functions (~40+) don't accept sessions at all. This creates atomicity risks where multi-step operations can partially complete, causing data inconsistency.

**Solution**: Establish universal session discipline where ALL service methods require a session parameter, use it exclusively, and never manage their own transaction lifecycle.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Multi-Service Transaction Reliability (Priority: P1)

When performing operations that span multiple services (e.g., production recording that updates events, inventory, and production records), the system must guarantee all-or-nothing behavior. If any step fails, the entire operation must roll back cleanly.

**Why this priority**: Data integrity is non-negotiable. Per CLAUDE.md documentation, session management bugs have caused silent data loss before. This is the core reason for this feature.

**Independent Test**: Can be verified by triggering a failure mid-transaction and confirming no partial state persists.

**Acceptance Scenarios**:

1. **Given** a multi-service operation in progress, **When** an error occurs after some database writes, **Then** all changes from that operation are rolled back completely.
2. **Given** a planning operation reading from multiple services, **When** data is queried, **Then** all reads see a consistent snapshot (no stale reads from separate transactions).
3. **Given** a production recording operation, **When** inventory consumption succeeds but cost calculation fails, **Then** inventory changes are rolled back.

---

### User Story 2 - Event Service Transaction Participation (Priority: P1)

All event-related operations must be able to participate in a caller's transaction, enabling atomic operations that span events, production, and assembly.

**Why this priority**: Event service is the most-used service (~40+ functions) and currently cannot participate in multi-service transactions because functions don't accept session parameters.

**Independent Test**: Can be verified by calling any event service function within a transaction and confirming it uses the provided session.

**Acceptance Scenarios**:

1. **Given** an event query within a multi-service transaction, **When** the event service function is called with a session, **Then** it uses that session for all database operations.
2. **Given** an event update operation, **When** called with a session from a larger transaction, **Then** the update is not committed until the caller commits.
3. **Given** a progress query spanning events and production, **When** both services are called in one transaction, **Then** they see consistent data from the same transaction snapshot.

---

### User Story 3 - History Query Consistency (Priority: P2)

Production and assembly history queries must use provided sessions instead of ignoring them, ensuring history reads are consistent with other operations in the same transaction.

**Why this priority**: These functions currently accept session parameters but silently ignore them - a subtle bug that violates caller expectations.

**Independent Test**: Can be verified by querying history within a transaction that has uncommitted changes and confirming the query sees those changes.

**Acceptance Scenarios**:

1. **Given** a production history query called with a session, **When** there are uncommitted production records in that session, **Then** the history query includes those uncommitted records.
2. **Given** an assembly history query called with a session, **When** there are uncommitted assembly records in that session, **Then** the history query includes those uncommitted records.
3. **Given** a get_production_run query with a session, **When** the production run was just created in that session, **Then** the query returns the uncommitted record.

---

### User Story 4 - Progress Query Atomicity (Priority: P2)

Progress calculations that aggregate data across events, production, and assembly must read atomically to produce accurate percentages and summaries.

**Why this priority**: Progress percentages can be incorrect if reads span multiple transactions with concurrent writes.

**Independent Test**: Can be verified by confirming progress calculations use a single session throughout all sub-queries.

**Acceptance Scenarios**:

1. **Given** a progress query for an event, **When** production is being recorded concurrently, **Then** the progress either includes or excludes the new production atomically (no partial state).
2. **Given** get_events_with_progress called with a session, **When** it queries events and their progress, **Then** all sub-queries use the same session.

---

### User Story 5 - Consistent Data Format for Cost Values (Priority: P3)

All service responses that include cost values must use a consistent format (2-decimal string representation) for reliable downstream processing and future API exposure.

**Why this priority**: Inconsistent types (Decimal objects vs strings) cause serialization errors and type mismatches. Important for API readiness but not blocking core functionality.

**Independent Test**: Can be verified by calling any service that returns costs and confirming the format is a 2-decimal string.

**Acceptance Scenarios**:

1. **Given** a service returning cost data, **When** the response is serialized to JSON, **Then** all cost values serialize successfully as strings with 2 decimal places.
2. **Given** different services returning cost data, **When** their responses are compared, **Then** all use the same string format (e.g., "12.34", not Decimal("12.34") or "12.3400").

---

### User Story 6 - Debuggable Production Operations (Priority: P3)

Production and assembly operations must log sufficient context to debug issues in multi-service transactions.

**Why this priority**: Transaction bugs are notoriously hard to debug. Structured logging enables post-mortem analysis. Lower priority than correctness but important for maintainability.

**Independent Test**: Can be verified by running a production operation and confirming logs contain operation type, entity IDs, and outcome.

**Acceptance Scenarios**:

1. **Given** a production operation, **When** it completes or fails, **Then** a structured log entry includes operation type, production_run_id, and outcome.
2. **Given** an assembly operation, **When** it completes or fails, **Then** a structured log entry includes operation type, assembly_run_id, and outcome.

---

### Edge Cases

- What happens when a caller forgets to pass a session? (Answer: Compilation/runtime error - sessions are required, not optional)
- How does the system handle nested service calls within a transaction? (Answer: Session is threaded through all calls)
- What happens to in-flight transactions during application shutdown? (Answer: Uncommitted changes are rolled back by the database)
- How are Decimal values with more than 2 decimal places handled? (Answer: Rounded to 2 places using standard rounding)

---

## Requirements *(mandatory)*

### Functional Requirements

**Session Discipline (Core)**

- **FR-001**: ALL event_service functions (~40+) MUST require a session parameter
- **FR-002**: ALL event_service functions MUST use the provided session exclusively for database operations
- **FR-003**: ALL event_service functions MUST thread the session to any downstream service calls
- **FR-004**: NO service function MAY open its own session scope when a session is provided
- **FR-005**: NO service function MAY commit or rollback - the caller owns the transaction lifecycle

**Bug Fixes (Ignored Sessions)**

- **FR-006**: batch_production_service.get_production_history MUST use the provided session parameter (currently ignores it)
- **FR-007**: batch_production_service.get_production_run MUST use the provided session parameter (currently ignores it)
- **FR-008**: assembly_service.get_assembly_history MUST use the provided session parameter (currently ignores it)
- **FR-009**: assembly_service.get_assembly_run MUST use the provided session parameter (currently ignores it)

**Production Service Completeness**

- **FR-010**: ALL production_service functions MUST require a session parameter
- **FR-011**: production_service.get_production_progress MUST accept and use a session parameter

**Progress Query Threading**

- **FR-012**: get_events_with_progress MUST require a session parameter
- **FR-013**: get_events_with_progress MUST thread the session to all event, production, and assembly sub-queries

**DTO Consistency**

- **FR-014**: ALL service DTOs returning cost values MUST format them as strings with 2 decimal places
- **FR-015**: Decimal-to-string conversion MUST happen at the DTO boundary (service layer output)

**Observability**

- **FR-016**: Production operations MUST emit structured log entries with operation type, entity IDs, and outcome
- **FR-017**: Assembly operations MUST emit structured log entries with operation type, entity IDs, and outcome

**Caller Updates**

- **FR-018**: ALL existing callers of modified services MUST be updated to pass the required session parameter

### Key Entities

- **Session**: Database transaction context that groups operations for atomic commit/rollback
- **DTO (Data Transfer Object)**: Service response format containing business data in serializable types
- **Production Run**: Record of a batch production with costs and consumption ledger
- **Assembly Run**: Record of an assembly operation with component costs

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of service layer functions require session parameter (no optional sessions)
- **SC-002**: 0 internal session_scope calls in any service method that accepts session
- **SC-003**: 0 internal commit calls in any service method
- **SC-004**: All cost values in service DTOs are strings with exactly 2 decimal places
- **SC-005**: All production/assembly operations produce structured log entries
- **SC-006**: Multi-service transaction rollback succeeds 100% of the time (no partial state persists)
- **SC-007**: All existing tests pass after session parameter changes
- **SC-008**: Test coverage includes transaction rollback scenarios for critical multi-service operations

### Acceptance Checklist

- [ ] Event service: All ~40+ functions require and use session
- [ ] Batch production service: History queries use provided session
- [ ] Assembly service: History queries use provided session
- [ ] Production service: All functions require session
- [ ] Progress queries: Session threaded through all sub-queries
- [ ] DTOs: Costs formatted as 2-decimal strings
- [ ] Logging: Production/assembly operations logged with context
- [ ] Callers: All service callers updated to pass session
- [ ] Tests: Transaction rollback scenarios covered

---

## Assumptions

- This is a desktop single-user application where we control all callers (no external API consumers)
- Breaking changes to function signatures are acceptable (required sessions instead of optional)
- Existing test infrastructure supports transaction rollback testing
- Python's type system will help catch missing session arguments during development

---

## Dependencies

- **F060/F061**: This feature completes architecture hardening work started in those features
- **CLAUDE.md Session Management Documentation**: Establishes the pattern this feature universalizes
- **Cursor Code Review (2026-01-20)**: Identifies specific gaps this feature addresses

---

## Out of Scope

- New planning features (depends on this foundation)
- New production features (depends on this foundation)
- UI changes (service layer only)
- Performance optimization (correctness first)
- Materials service hardening (separate feature)
- Backward compatibility with optional sessions
