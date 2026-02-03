# Feature Specification: Pagination DTOs Foundation

**Feature Branch**: `093-pagination-dtos-foundation`
**Created**: 2026-02-03
**Status**: Draft
**Input**: docs/func-spec/F093_pagination_dtos_foundation.md

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create Pagination Data Structures (Priority: P1)

As a developer preparing for future web API migration, I need type-safe pagination data structures so that when web migration begins, services can return paginated results consistently.

**Why this priority**: The pagination DTOs are the core deliverable. Without these dataclasses, there is nothing to document or test. This must be completed first.

**Independent Test**: Can be fully tested by creating PaginationParams and PaginatedResult instances and verifying offset calculations, page counts, and navigation properties work correctly.

**Acceptance Scenarios**:

1. **Given** I import from dto.py, **When** I create PaginationParams(page=2, per_page=50), **Then** offset() returns 50
2. **Given** a PaginatedResult with 100 items total and per_page=25, **When** I access the pages property, **Then** it returns 4
3. **Given** a PaginatedResult on page 1 of 3, **When** I check navigation, **Then** has_prev=False and has_next=True
4. **Given** invalid params like page=0, **When** I create PaginationParams, **Then** validation raises ValueError

---

### User Story 2 - Document Usage Patterns (Priority: P2)

As a developer working on future services, I need clear documentation of how to use these pagination DTOs so that I can adopt them consistently when creating new services or migrating to web APIs.

**Why this priority**: Documentation ensures the DTOs are discoverable and correctly adopted. Without documentation, the DTOs may be ignored or used inconsistently.

**Independent Test**: Can be verified by reading CLAUDE.md and confirming it contains the pagination section with desktop vs web examples.

**Acceptance Scenarios**:

1. **Given** CLAUDE.md exists, **When** a developer searches for "pagination", **Then** they find the Pagination Pattern section
2. **Given** the documentation, **When** a developer reads the optional pagination pattern, **Then** they understand how to add pagination=None parameter to services
3. **Given** the documentation, **When** a developer needs web pagination, **Then** they find a FastAPI example showing how to use PaginatedResult

---

### Edge Cases

- What happens when page=0 is passed? Validation raises ValueError with clear message
- What happens when per_page=0? Validation raises ValueError
- What happens when per_page > 1000? Validation raises ValueError to prevent abuse
- What happens when total=0? pages property returns 1 (single empty page)
- What happens with empty items list? PaginatedResult works correctly with items=[]

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide PaginationParams dataclass with page and per_page fields
- **FR-002**: System MUST validate page >= 1 on PaginationParams creation
- **FR-003**: System MUST validate per_page >= 1 and per_page <= 1000 on PaginationParams creation
- **FR-004**: PaginationParams MUST provide offset() method that calculates (page - 1) * per_page
- **FR-005**: System MUST provide PaginatedResult[T] generic dataclass with items, total, page, per_page fields
- **FR-006**: PaginatedResult MUST provide pages property calculating total pages
- **FR-007**: PaginatedResult MUST provide has_next and has_prev boolean properties
- **FR-008**: DTOs MUST include comprehensive docstrings documenting desktop vs web usage patterns
- **FR-009**: CLAUDE.md MUST contain a Pagination Pattern section with usage examples
- **FR-010**: Desktop functionality MUST remain unchanged (zero impact on existing code)

### Key Entities

- **PaginationParams**: Input parameters for pagination requests (page number, items per page)
- **PaginatedResult[T]**: Generic container holding paginated items with metadata (items list, total count, current page, navigation helpers)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All pagination DTO unit tests pass (offset calculation, page counts, validation)
- **SC-002**: PaginatedResult[T] correctly handles edge cases (empty results, single page, many pages)
- **SC-003**: CLAUDE.md contains complete pagination documentation section
- **SC-004**: Existing desktop tests continue to pass (zero regression)
- **SC-005**: New services can immediately import and use PaginationParams and PaginatedResult[T]

## Assumptions

- DTOs will be placed in `src/services/dto.py` (create if doesn't exist)
- No existing services will be modified (this is foundation only)
- Documentation will follow existing CLAUDE.md patterns
- Default per_page of 50 is appropriate for most use cases

## Out of Scope

- Refactoring existing service functions (deferred to web-prep/F003)
- Updating UI components (not needed for desktop)
- Backward-compatible wrappers for existing functions
- Query optimization or caching
- Cursor-based pagination (offset/limit sufficient)
