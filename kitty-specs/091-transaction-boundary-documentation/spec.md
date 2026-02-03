# Feature Specification: Transaction Boundary Documentation

**Feature Branch**: `091-transaction-boundary-documentation`
**Created**: 2026-02-02
**Status**: Draft
**Input**: F091 Transaction Boundary Documentation - Add comprehensive transaction boundary documentation to all service functions, audit multi-step operations for atomicity, and create a transaction patterns guide.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Understands Transaction Scope (Priority: P1)

A developer working on the codebase needs to understand the transaction boundaries of service functions without reading the implementation. They read the docstring and immediately know:
- Whether the operation is read-only, single-step write, or multi-step atomic
- What atomicity guarantees exist
- How to properly compose the function with other operations

**Why this priority**: Core value proposition - developers can understand transaction behavior from documentation alone, reducing bugs and improving code quality.

**Independent Test**: Can be tested by reading any service function docstring and verifying it contains a "Transaction boundary:" section with clear atomicity guarantees.

**Acceptance Scenarios**:

1. **Given** a developer reads a service function docstring, **When** they look for transaction information, **Then** they find a "Transaction boundary:" section documenting the operation type and atomicity guarantees
2. **Given** a multi-step service function, **When** a developer reads its docstring, **Then** the steps executed atomically are explicitly listed
3. **Given** any service function with a session parameter, **When** a developer reads the docstring, **Then** they understand when to pass a session vs let the function create one

---

### User Story 2 - Code Reviewer Verifies Atomicity (Priority: P2)

A code reviewer needs to verify that multi-step operations maintain atomicity. They can check the docstring to see what steps should be atomic, then verify the implementation passes the session parameter correctly.

**Why this priority**: Enables quality assurance without deep code diving - reviewers can catch atomicity bugs by comparing docstring to implementation.

**Independent Test**: Can be tested by reviewing any multi-step function and verifying the documented atomic steps match the session-passing implementation.

**Acceptance Scenarios**:

1. **Given** a multi-step operation docstring lists steps 1, 2, 3 as atomic, **When** reviewer inspects implementation, **Then** all nested service calls receive the session parameter
2. **Given** the transaction patterns guide exists, **When** a reviewer checks for common pitfalls, **Then** they find documented anti-patterns and correct patterns

---

### User Story 3 - New Developer Learns Patterns (Priority: P3)

A new developer joining the project needs to understand how transaction management works. They read the transaction patterns guide and learn the three patterns (read-only, single-step, multi-step) with examples.

**Why this priority**: Onboarding value - reduces time for new developers to understand codebase patterns.

**Independent Test**: Can be tested by a new developer reading the guide and correctly implementing a new service function with proper transaction documentation.

**Acceptance Scenarios**:

1. **Given** a new developer reads the transaction patterns guide, **When** they look for the session parameter pattern, **Then** they find clear explanation with code examples
2. **Given** the guide documents common pitfalls, **When** a developer reviews anti-patterns, **Then** each pitfall has a corresponding correct pattern shown

---

### Edge Cases

- What happens when a function is misclassified (e.g., documented as read-only but actually writes)?
  - Audit process should catch this during implementation
- How does system handle functions that evolved from single-step to multi-step?
  - Documentation must be updated when function scope changes (added to code review checklist)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All service functions (~50-60) MUST have a "Transaction boundary:" section in their docstrings
- **FR-002**: Read-only operations MUST be documented with Pattern A template stating "Read-only, no transaction needed"
- **FR-003**: Single-step write operations MUST be documented with Pattern B template stating transaction behavior when session is/isn't provided
- **FR-004**: Multi-step atomic operations MUST be documented with Pattern C template listing all steps executed atomically
- **FR-005**: All multi-step operations (~20) MUST be audited for correct session passing to nested service calls
- **FR-006**: Any broken atomicity patterns discovered during audit MUST be fixed (session parameter added)
- **FR-007**: A transaction patterns guide MUST be created documenting all three patterns with code examples
- **FR-008**: The guide MUST document common pitfalls (multiple session_scope() calls, not passing session to nested calls)
- **FR-009**: Code review checklist MUST be updated to include "Transaction boundary matches implementation?" check

### Key Entities

- **Service Function**: A function in the services layer that performs database operations. Has transaction boundary characteristics (read-only, single-step write, multi-step atomic).
- **Transaction Boundary**: The scope within which database operations are atomic. Documented in docstrings for developer clarity.
- **Session Parameter**: Optional parameter accepted by service functions enabling transactional composition with other operations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of service functions (~50-60) have "Transaction boundary:" documentation in their docstrings
- **SC-002**: 100% of multi-step operations (~20) pass atomicity audit (correct session passing verified)
- **SC-003**: Transaction patterns guide exists with all three patterns documented (read-only, single-step, multi-step)
- **SC-004**: Common pitfalls section documents at least 3 anti-patterns with fixes
- **SC-005**: Code review checklist updated with transaction boundary verification item
- **SC-006**: Documentation uses consistent phrasing across all services (same templates applied uniformly)

## Assumptions

- Existing session parameter pattern is correct and should be documented, not changed
- Most multi-step operations already pass session correctly (audit will verify, fixes rare)
- Three docstring templates from func-spec (Pattern A, B, C) are sufficient for all cases
- Transaction patterns guide will be added to docs/design/ or CLAUDE.md

## Out of Scope

- Savepoint implementation (moved to web-prep/F002)
- Changing transaction isolation levels
- Distributed transactions
- Transaction retry logic
- Refactoring service function implementations (focus is documentation)

## Dependencies

- Existing service layer with session parameter pattern
- CLAUDE.md for session management guidance reference
- docs/design/code_quality_principles_revised.md for constitutional compliance

## Constitutional Compliance

- **Principle VI.C.2**: Transaction Boundaries - "Service methods define transaction scope" - Now documented explicitly
- **Principle VI.E.1**: Logging Strategy - Transaction boundaries are operation context for debugging
- **Principle VI.D.1**: Method Signatures - "Explicit over implicit" - Transaction boundaries now explicit in docstrings
