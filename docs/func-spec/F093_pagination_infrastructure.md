# F093: Pagination Infrastructure

**Version**: 1.0
**Priority**: HIGH
**Type**: Architecture Enhancement

---

## Executive Summary

Current gaps:
- ❌ No pagination support (all list operations load entire tables)
- ❌ `get_all_*()` functions load thousands of records into memory
- ❌ No scalable pattern for web APIs
- ❌ UI performance degrades with large datasets

This spec implements pagination infrastructure with PaginationParams and PaginatedResult DTOs, updates all list operations to support pagination, and provides backward-compatible wrappers.

---

## Problem Statement

**Current State (NO PAGINATION):**
```
List Operations
├─ ❌ get_all_ingredients() loads entire table
├─ ❌ get_all_materials() loads entire table
├─ ❌ get_all_recipes() loads entire table
├─ ❌ No pagination support (~30 list functions)
└─ ❌ Memory issues with large datasets

Web API Readiness
└─ ❌ BLOCKED: Cannot scale to production data volumes
```

**Target State (PAGINATED):**
```
List Operations
├─ ✅ list_ingredients() with pagination support
├─ ✅ list_materials() with pagination support
├─ ✅ list_recipes() with pagination support
├─ ✅ All list operations paginated (~30 functions)
└─ ✅ Memory efficient for large datasets

Web API Readiness
└─ ✅ READY: Scalable pagination for production
```

---

## CRITICAL: Study These Files FIRST

1. **Current List Operations**
   - Find `get_all_*` functions across service files
   - Study query patterns
   - Note return types

2. **Existing Filter Patterns**
   - Find search/filter implementations
   - Study parameter passing
   - Note result handling

---

## Requirements Reference

This specification implements:
- **Code Quality Principle VI.D**: API Consistency & Contracts - Collection operations
- **Code Quality Principle VI.G**: Resource Management - Memory-intensive operations

From: `docs/design/code_quality_principles_revised.md` (v1.0)

---

## Functional Requirements

### FR-1: Create Pagination DTOs

**What it must do:**
- Create PaginationParams dataclass (page, per_page)
- Create PaginatedResult generic dataclass
- Support offset/limit calculation
- Include pagination metadata

**Pattern reference:** Study dataclass patterns, create generic result container

**Success criteria:**
- [ ] PaginationParams exists with page, per_page fields
- [ ] PaginatedResult[T] generic exists
- [ ] Contains items, total, page, per_page, pages
- [ ] offset() method calculates SQL offset correctly

---

### FR-2: Update List Operations

**What it must do:**
- Convert ~30 `get_all_*()` functions to `list_*()`
- Add pagination and filter parameters
- Return PaginatedResult[Model]
- Maintain consistent signatures

**Pattern reference:** Study query patterns, apply pagination consistently

**Standard signature:**
```python
def list_items(
    filter: Optional[ItemFilter] = None,
    pagination: Optional[PaginationParams] = None,
    session: Optional[Session] = None
) -> PaginatedResult[Item]:
```

**Success criteria:**
- [ ] All list operations support pagination
- [ ] All return PaginatedResult[T]
- [ ] Consistent signatures across services
- [ ] Query performance optimized

---

### FR-3: Create Backward-Compatible Wrappers

**What it must do:**
- Keep `get_all_*()` functions for backward compatibility
- Internally call `list_*()` with large per_page
- Mark as deprecated in docstrings
- Plan removal timeline

**Pattern reference:** Study deprecation patterns, apply to legacy functions

**Success criteria:**
- [ ] get_all_*() wrappers exist
- [ ] Call list_*() internally
- [ ] Marked deprecated
- [ ] Desktop UI works without changes

---

### FR-4: Update UI Components

**What it must do:**
- Update UI to use paginated list operations
- Add pagination controls where needed
- Handle PaginatedResult in UI code
- Maintain UI performance

**Pattern reference:** Study existing UI list components, add pagination

**Success criteria:**
- [ ] UI components use list_*() functions
- [ ] Pagination controls added to large lists
- [ ] PaginatedResult handled correctly
- [ ] UI performance improved

---

## Out of Scope

- ❌ Cursor-based pagination - offset/limit sufficient
- ❌ Advanced sorting - defer
- ❌ Full-text search - defer
- ❌ Caching - defer

---

## Success Criteria

**Complete when:**

### Infrastructure
- [ ] PaginationParams DTO exists
- [ ] PaginatedResult[T] DTO exists
- [ ] Pagination logic reusable
- [ ] Pattern documented

### Service Layer
- [ ] All list operations support pagination
- [ ] Backward-compatible wrappers exist
- [ ] Consistent signatures
- [ ] Query performance optimized

### UI Layer
- [ ] UI uses paginated operations
- [ ] Pagination controls added
- [ ] Large lists performant
- [ ] User experience improved

### Quality
- [ ] Follows Code Quality Principle VI.D
- [ ] Scalable for production
- [ ] Memory efficient
- [ ] Web-ready pattern

---

## Architecture Principles

### Pagination Pattern

**All list operations must:**
- Accept optional PaginationParams
- Return PaginatedResult[T]
- Default to reasonable page size (50)
- Include total count

### Generic Result Container

**PaginatedResult[T] provides:**
- Type-safe items list
- Pagination metadata
- Helper properties (has_next, has_prev)
- Web API ready

---

## Constitutional Compliance

✅ **Principle VI.D: API Consistency & Contracts**
- Implements pagination for collection operations
- Consistent signatures across services

✅ **Principle VI.G: Resource Management**
- Addresses memory-intensive operations
- Chunked data loading

---

## Risk Considerations

**Risk: Breaking UI components**
- Mitigation: Backward-compatible wrappers
- Mitigation: Phased UI migration

**Risk: Performance regression**
- Mitigation: Query optimization
- Mitigation: Measure before/after

---

## Notes for Implementation

**Pattern Discovery:**
- Study all list operations → identify functions to update
- Study query patterns → optimize pagination queries
- Study UI components → identify pagination needs

**Focus Areas:**
- Pagination is critical for web scalability
- Backward compatibility maintains desktop stability
- Consistent pattern simplifies future development

---

**END OF SPECIFICATION**
