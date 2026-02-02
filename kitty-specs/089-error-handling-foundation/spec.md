# Feature Specification: Error Handling Foundation

**Feature Branch**: `089-error-handling-foundation`
**Created**: 2026-02-02
**Status**: Draft
**Input**: F089 Error Handling Foundation - Establish three-tier exception strategy with consolidated ServiceError hierarchy, centralized UI error handler, update 88 files catching generic Exception to catch specific exceptions, add exception context requirements, and create developer documentation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - User-Friendly Error Messages (Priority: P1)

When an error occurs during any operation (creating recipes, recording production, managing inventory), the user sees a clear, friendly message explaining what went wrong - not a technical stack trace or cryptic error code.

**Why this priority**: The primary user is non-technical. Showing raw Python exceptions causes confusion and frustration. This is the core user-facing improvement.

**Independent Test**: Can be tested by triggering any known error condition (e.g., insufficient inventory for production) and verifying the displayed message is user-friendly.

**Acceptance Scenarios**:

1. **Given** a user attempts to record production with insufficient inventory, **When** the operation fails, **Then** the user sees "Not enough [ingredient] in inventory" (not a Python exception)
2. **Given** a user searches for a non-existent ingredient, **When** the lookup fails, **Then** the user sees "Ingredient '[name]' not found" (not IngredientNotFoundBySlug traceback)
3. **Given** an unexpected system error occurs, **When** the error is caught, **Then** the user sees "An unexpected error occurred. Please contact support." and technical details are logged

---

### User Story 2 - Consistent Error Presentation (Priority: P1)

Error dialogs and messages appear consistently across all application screens - same styling, same tone, same level of detail - regardless of which feature triggered the error.

**Why this priority**: Inconsistent error handling confuses users and creates a perception of an unpolished application. Tied with P1 above as both address the same core user experience.

**Independent Test**: Can be tested by triggering errors in multiple different screens (Recipes, Inventory, Production) and verifying identical presentation style.

**Acceptance Scenarios**:

1. **Given** errors can occur in any UI screen, **When** an error occurs in the Recipe screen, **Then** it uses the same error presentation as errors in the Inventory screen
2. **Given** multiple error types exist, **When** any ServiceError occurs in any screen, **Then** the centralized error handler processes it identically

---

### User Story 3 - Improved Debugging for Developers (Priority: P2)

When errors occur, developers can quickly identify the root cause through specific exception types, structured context data, and consistent logging - without needing to reproduce the exact user scenario.

**Why this priority**: Enables faster bug resolution and reduces time-to-fix, but is developer-facing rather than user-facing.

**Independent Test**: Can be tested by examining log output when errors occur - verify specific exception types and context (entity IDs, operation attempted, current state) are logged.

**Acceptance Scenarios**:

1. **Given** an InsufficientInventoryError occurs, **When** a developer examines the logs, **Then** they see the ingredient slug, quantity needed, quantity available, and unit
2. **Given** any ServiceError occurs, **When** it is logged, **Then** the log includes exception type, message, and all context attributes
3. **Given** code catches a specific exception, **When** debugging, **Then** the exception type immediately indicates the category of problem (not generic Exception)

---

### User Story 4 - Web Migration Readiness (Priority: P3)

The exception hierarchy maps cleanly to HTTP status codes, enabling future web/API migration without restructuring error handling.

**Why this priority**: Future-proofing for web migration. Not needed for current desktop app but establishes foundation.

**Independent Test**: Can be verified by reviewing exception documentation and confirming each exception type has a documented HTTP status code mapping.

**Acceptance Scenarios**:

1. **Given** the exception hierarchy is documented, **When** a developer reviews the mapping, **Then** each ServiceError subclass has a corresponding HTTP status code (404, 400, 500, etc.)
2. **Given** NotFound-style exceptions exist, **When** mapped to HTTP, **Then** they correspond to 404 status
3. **Given** validation exceptions exist, **When** mapped to HTTP, **Then** they correspond to 400 status

---

### Edge Cases

- What happens when multiple errors occur in sequence (e.g., batch operation fails partway)?
- How does the system handle errors during startup/initialization?
- What happens when logging itself fails?
- How are errors handled in background operations (if any exist)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST consolidate all domain exceptions under a single `ServiceError` base class
- **FR-002**: System MUST deprecate/remove the legacy `ServiceException` base class
- **FR-003**: System MUST provide a centralized UI error handler function that converts service exceptions to user-friendly messages
- **FR-004**: System MUST map each domain exception type (IngredientNotFoundBySlug, ValidationError, InsufficientInventoryError, etc.) to an appropriate user-friendly message
- **FR-005**: System MUST log technical error details (exception type, message, context, stack trace) separately from user display
- **FR-006**: System MUST update all files catching generic `Exception` to use the three-tier catch strategy
- **FR-007**: All domain exceptions MUST include operation context (entity identifiers, attempted operation, current state)
- **FR-008**: All domain exceptions MUST support an optional `correlation_id` parameter for future tracing
- **FR-009**: System MUST provide developer documentation covering exception usage, three-tier pattern, and HTTP status code mapping
- **FR-010**: System MUST never display raw Python exception messages to users

### Three-Tier Exception Strategy

The three-tier catch pattern for UI layer code:

1. **Tier 1**: Catch specific domain exceptions (ServiceError subclasses) with tailored handling
2. **Tier 2**: Catch `ServiceError` base class with centralized error handler
3. **Tier 3**: Catch generic `Exception` as last resort - always log full stack trace, show generic user message

### Key Entities

- **ServiceError**: Base exception class for all domain/service exceptions. Includes context attributes and correlation_id support.
- **Domain Exceptions**: Specific exception types (IngredientNotFoundBySlug, ValidationError, InsufficientInventoryError, etc.) that inherit from ServiceError
- **ErrorHandler**: Centralized utility that maps exceptions to user-friendly messages and handles logging

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of domain exceptions inherit from the single `ServiceError` base class
- **SC-002**: 0 files contain generic `Exception` catches without proper logging (all 88 files updated)
- **SC-003**: All user-facing error messages are non-technical (no Python exception names, no stack traces)
- **SC-004**: All service exceptions include structured context (entity identifiers accessible as attributes, not just in string message)
- **SC-005**: Developer documentation exists covering all exception types with usage examples
- **SC-006**: HTTP status code mapping documented for all exception types
- **SC-007**: Centralized error handler used consistently across all UI files

### Out of Scope

- Correlation ID implementation (just prepare exception constructors)
- Audit trail integration (separate observability feature)
- FastAPI error handlers (separate web migration feature)
- Advanced error recovery/retry logic
- User-configurable error verbosity
