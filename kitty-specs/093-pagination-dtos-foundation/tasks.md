# Tasks: Pagination DTOs Foundation

**Feature**: 093-pagination-dtos-foundation
**Created**: 2026-02-03
**Estimated Effort**: 4 hours

## Subtask Index

| ID | Description | WP | Status |
|----|-------------|-----|--------|
| T001 | Create PaginationParams dataclass | WP01 | [ ] |
| T002 | Create PaginatedResult[T] generic dataclass | WP01 | [ ] |
| T003 | Add validation and docstrings | WP01 | [ ] |
| T004 | Create unit tests for PaginationParams | WP01 | [ ] |
| T005 | Create unit tests for PaginatedResult | WP01 | [ ] |
| T006 | Add pagination section to CLAUDE.md | WP02 | [ ] |

---

## Work Packages

### WP01: Create Pagination DTOs and Tests (Phase 1-2)

**Priority**: P1 (Core deliverable)
**Estimated**: 3 hours
**Dependencies**: None
**Files**: `src/services/dto.py` (create), `src/tests/services/test_dto.py` (create)

**Summary**: Implement PaginationParams and PaginatedResult[T] dataclasses with comprehensive unit tests.

**Subtasks**:
- [x] T001: Create PaginationParams dataclass with page/per_page fields and offset() method
- [x] T002: Create PaginatedResult[T] generic dataclass with items/total/page/per_page fields and pages/has_next/has_prev properties
- [x] T003: Add __post_init__ validation and comprehensive docstrings with usage examples
- [x] T004: Create unit tests for PaginationParams (offset calculation, validation errors)
- [ ] T005: Create unit tests for PaginatedResult (pages calculation, navigation properties, edge cases)

**Definition of Done**:
- dto.py exists in src/services/
- All tests pass
- Docstrings include desktop vs web examples

---

### WP02: Documentation (Phase 3)

**Priority**: P2 (Enables adoption)
**Estimated**: 1 hour
**Dependencies**: WP01
**Files**: `CLAUDE.md` (update)

**Summary**: Document pagination pattern in CLAUDE.md for future service adoption.

**Subtasks**:
- [ ] T006: Add "Pagination Pattern (Web Migration Ready)" section to CLAUDE.md with optional pagination pattern, desktop vs web examples, and adoption guidance

**Definition of Done**:
- CLAUDE.md contains Pagination Pattern section
- Examples for desktop (pagination=None) and web (PaginationParams) usage
- References web-prep/F003 for future full adoption
