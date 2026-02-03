# F093: Pagination DTOs Foundation

**Version**: 2.0 (Revised - Minimal Foundation)
**Priority**: MEDIUM
**Type**: Infrastructure Foundation
**Estimated Effort**: 4 hours

---

## Executive Summary

**Status: Minimal foundation only - create DTOs, defer service refactoring.**

Current state:
- ✅ Desktop app loads 100-500 items per list (works fine)
- ✅ No performance issues with current scale
- ❌ No pagination DTOs exist (needed for future web API)
- ⏸️ Service layer refactoring not needed yet

This spec creates pagination data structures (DTOs) as foundation for future web migration, WITHOUT refactoring existing service functions or UI components.

**What this includes:**
- ✅ Create `PaginationParams` and `PaginatedResult[T]` dataclasses
- ✅ Document usage patterns for future adoption
- ✅ Zero impact on current desktop functionality

**What this does NOT include:**
- ❌ Refactoring service functions (deferred to web-prep/F003)
- ❌ Updating UI components (not needed for desktop)
- ❌ Backward-compatible wrappers (nothing to wrap)

**Note:** Comprehensive service layer pagination moved to web-prep/F003 (parked until web migration).

---

## Problem Statement

**Current State (No DTOs):**
```
List Operations
├─ ✅ get_all_ingredients() works fine for desktop (100-500 items)
├─ ✅ get_all_materials() works fine for desktop
├─ ✅ get_all_recipes() works fine for desktop
├─ ✅ No performance issues at current scale
└─ ❌ No pagination DTOs for future web API

Web API Readiness
└─ ⚠️ Need pagination data structures (but not full refactor yet)
```

**Target State (DTOs Ready):**
```
Infrastructure
├─ ✅ PaginationParams dataclass exists
├─ ✅ PaginatedResult[T] generic dataclass exists
├─ ✅ Usage patterns documented
└─ ✅ Ready for future web migration

List Operations
├─ ✅ Current functions unchanged (work as-is)
├─ ✅ Desktop UI unchanged (no impact)
└─ ⏸️ Service layer refactoring deferred (web-prep/F003 when needed)

Web API Readiness
└─ ✅ DTOs ready when web migration starts
```

---

## Why Minimal Foundation (Not Full Refactoring)

**Current desktop scale is appropriate:**
- 100-500 ingredients → loads instantly
- 50-200 recipes → no performance issues
- TreeView handles current volumes fine
- No user complaints about performance

**Desktop doesn't need server-side pagination:**
- Virtual scrolling (UI-only) sufficient for better UX
- Client-side filtering already fast enough
- Lazy loading pattern available if needed

**Web migration doesn't exist yet:**
- No FastAPI application
- No concrete web requirements
- Can add full pagination in 2-3 days when needed

**YAGNI principle:**
- Don't refactor 22 service functions for hypothetical needs
- Create DTOs (4 hours) vs full refactor (2-3 weeks)
- DTOs enable future adoption without blocking current work

---

## Requirements Reference

This specification implements:
- **Code Quality Principle VI.F**: Migration & Evolution Readiness
  - "Today's decisions should ease tomorrow's changes"
  - Create DTOs now, refactor when needed
- **YAGNI Principle**: Don't build infrastructure for hypothetical scenarios
  - Minimal foundation enables future without premature optimization

From: `docs/design/code_quality_principles_revised.md` (v1.0) and architecture gap analysis

---

## Functional Requirements

### FR-1: Create Pagination DTOs

**What it must do:**
- Create `PaginationParams` dataclass in `src/services/dto.py` (or new file)
- Create `PaginatedResult[T]` generic dataclass
- Support offset/limit calculation for SQL queries
- Include pagination metadata (total, page, pages)
- Add helper properties (has_next, has_prev)

**File location:** `src/services/dto.py` (create if doesn't exist)

**Implementation:**

```python
# src/services/dto.py
from dataclasses import dataclass
from typing import Generic, TypeVar, List

T = TypeVar('T')

@dataclass
class PaginationParams:
    """
    Pagination parameters for list operations.

    Desktop usage: Optional - pass None to get all items (current behavior)
    Web usage: Required - pass page/per_page for paginated results

    Examples:
        # Desktop (get all items)
        result = list_items(pagination=None)  # Returns all

        # Web (paginated)
        result = list_items(pagination=PaginationParams(page=2, per_page=25))
    """
    page: int = 1
    per_page: int = 50

    def offset(self) -> int:
        """Calculate SQL OFFSET value."""
        return (self.page - 1) * self.per_page

    def __post_init__(self):
        """Validate pagination parameters."""
        if self.page < 1:
            raise ValueError("page must be >= 1")
        if self.per_page < 1:
            raise ValueError("per_page must be >= 1")
        if self.per_page > 1000:
            raise ValueError("per_page must be <= 1000")

@dataclass
class PaginatedResult(Generic[T]):
    """
    Generic paginated result container.

    Desktop usage: All items in single page (pagination=None in service)
    Web usage: One page of items (pagination=PaginationParams in service)

    Attributes:
        items: List of items for this page
        total: Total number of items across all pages
        page: Current page number
        per_page: Items per page

    Properties:
        pages: Total number of pages
        has_next: Whether there's a next page
        has_prev: Whether there's a previous page

    Examples:
        # Desktop (all items)
        result = PaginatedResult(
            items=all_items,
            total=len(all_items),
            page=1,
            per_page=len(all_items)
        )

        # Web (paginated)
        result = PaginatedResult(
            items=page_items,
            total=1000,
            page=2,
            per_page=50
        )
        print(f"Page {result.page} of {result.pages}")
        if result.has_next:
            print("More results available")
    """
    items: List[T]
    total: int
    page: int
    per_page: int

    @property
    def pages(self) -> int:
        """Calculate total number of pages."""
        if self.total == 0:
            return 1
        return (self.total + self.per_page - 1) // self.per_page

    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        """Check if there's a previous page."""
        return self.page > 1
```

**Success criteria:**
- [ ] `PaginationParams` dataclass exists with page, per_page fields
- [ ] `PaginatedResult[T]` generic dataclass exists
- [ ] offset() method calculates SQL offset correctly
- [ ] Helper properties (pages, has_next, has_prev) work correctly
- [ ] Validation prevents invalid pagination parameters
- [ ] Docstrings document desktop vs web usage patterns

---

### FR-2: Document Usage Patterns

**What it must do:**
- Document how to use pagination DTOs in service functions (future)
- Provide examples for desktop (optional pagination) and web (required pagination)
- Document in CLAUDE.md or architecture guide
- Show optional pagination pattern (backward-compatible)

**Documentation content:**

Create section in CLAUDE.md:

```markdown
## Pagination Pattern (Web Migration Ready)

### DTOs Available

- `PaginationParams`: Page number and items per page
- `PaginatedResult[T]`: Generic result container with metadata

### Usage Pattern (Future Service Adoption)

When adding pagination to a service function:

**Pattern: Optional Pagination (Backward-Compatible)**

\```python
def list_items(
    filter: Optional[ItemFilter] = None,
    pagination: Optional[PaginationParams] = None,  # ← Optional!
    session: Optional[Session] = None
) -> PaginatedResult[Item]:
    """
    List items with optional pagination.

    Desktop usage: pagination=None returns all items (current behavior)
    Web usage: pagination=PaginationParams(...) returns one page
    """
    def _impl(sess: Session) -> PaginatedResult[Item]:
        query = sess.query(Item)

        # Apply filters...
        if filter:
            # ... filtering logic

        # Count total
        total = query.count()

        # Apply pagination (if provided)
        if pagination:
            # Web: return one page
            items = query.offset(pagination.offset()).limit(pagination.per_page).all()
            page = pagination.page
            per_page = pagination.per_page
        else:
            # Desktop: return all items (current behavior)
            items = query.all()
            page = 1
            per_page = total or 1

        return PaginatedResult(
            items=items,
            total=total,
            page=page,
            per_page=per_page
        )

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
\```

### Desktop vs Web Usage

**Desktop (current pattern unchanged):**
\```python
# No pagination parameter - get all items
result = list_ingredients(filter=IngredientFilter(category="baking"))
all_items = result.items  # All ingredients
\```

**Web (future FastAPI):**
\```python
@app.get("/api/ingredients")
def get_ingredients(page: int = 1, per_page: int = 50):
    result = list_ingredients(
        pagination=PaginationParams(page=page, per_page=per_page)
    )
    return {
        "items": [serialize(i) for i in result.items],
        "total": result.total,
        "page": result.page,
        "pages": result.pages,
        "has_next": result.has_next
    }
\```

### When to Adopt

- **New services**: Use pagination from the start
- **Existing services**: Adopt incrementally during refactoring
- **Desktop UI**: No changes needed (pagination=None)
- **Web migration**: See web-prep/F003 for comprehensive adoption plan
```

**Success criteria:**
- [ ] Usage patterns documented in CLAUDE.md
- [ ] Desktop vs web examples provided
- [ ] Optional pagination pattern explained
- [ ] Future adoption strategy clear

---

## Out of Scope

**Explicitly NOT included in this minimal foundation:**

- ❌ **Refactoring service functions** — Deferred to web-prep/F003 (parked)
  - No changes to existing `get_all_*()` functions
  - No creation of new `list_*()` functions
  - Current service layer unchanged

- ❌ **Updating UI components** — Not needed for desktop
  - Desktop UI continues using `get_all_*()` functions
  - No pagination controls in UI
  - No TreeView changes

- ❌ **Backward-compatible wrappers** — Nothing to wrap
  - No deprecated functions
  - No migration path needed yet

- ❌ **Query optimization** — Current queries work fine
  - Desktop scale appropriate (100-500 items)
  - No performance issues

- ❌ **Advanced features** — Defer to web migration
  - Cursor-based pagination (offset/limit sufficient)
  - Advanced sorting (simple ORDER BY sufficient)
  - Full-text search (LIKE queries sufficient)
  - Result caching (premature optimization)

---

## Success Criteria

**Complete when:**

### DTOs Created
- [ ] `PaginationParams` dataclass exists in `src/services/dto.py`
- [ ] `PaginatedResult[T]` generic dataclass exists
- [ ] offset() method calculates correctly
- [ ] Helper properties (pages, has_next, has_prev) implemented
- [ ] Validation prevents invalid parameters (page < 1, per_page > 1000)

### Documentation
- [ ] Usage patterns documented in CLAUDE.md
- [ ] Desktop vs web examples provided
- [ ] Optional pagination pattern explained
- [ ] Docstrings in DTOs are comprehensive

### Quality Checks
- [ ] DTOs are type-safe (Generic[T] works correctly)
- [ ] Validation raises appropriate errors
- [ ] Examples in docstrings are accurate
- [ ] No impact on current desktop functionality

### Non-Goals (Verified NOT Done)
- [ ] No service functions refactored (intentionally skipped)
- [ ] No UI components updated (intentionally skipped)
- [ ] No `get_all_*()` functions changed (intentionally skipped)
- [ ] Desktop app behavior unchanged (verified)

---

## Architecture Principles

### Minimal Infrastructure, Maximum Flexibility

**Why DTOs only:**
- Provides type-safe data structures for future adoption
- Zero impact on current desktop functionality
- Enables incremental adoption (service by service)
- Web-ready without premature refactoring

### Optional Pagination Pattern (Future)

**When services adopt pagination:**
- Accept `pagination: Optional[PaginationParams] = None`
- Return `PaginatedResult[T]`
- If pagination=None → return all items (desktop behavior)
- If pagination provided → return one page (web behavior)

**This maintains backward compatibility:**
- Desktop continues passing `pagination=None`
- Web passes `PaginationParams(page=X, per_page=Y)`
- Same service function, different callers

### Type-Safe Generic Container

**PaginatedResult[T] provides:**
- Type-safe items list (Generic[T])
- Pagination metadata (total, page, per_page)
- Helper properties (pages, has_next, has_prev)
- Works for any model type (Ingredient, Recipe, etc.)

---

## Constitutional Compliance

✅ **Principle VI.F: Migration & Evolution Readiness**
- "Today's decisions should ease tomorrow's changes"
- DTOs enable web migration without blocking current work
- Incremental adoption path (no big-bang refactor)

✅ **YAGNI Principle (Code Quality)**
- "Don't build infrastructure for hypothetical needs"
- Create minimal foundation (4 hours) vs full refactor (2-3 weeks)
- Defer service/UI changes until actually needed

✅ **Principle VI.D: API Consistency (Future)**
- Standardized pagination pattern for future adoption
- Consistent signatures when services eventually adopt
- Clear examples for future implementation

---

## Risk Considerations

### Risk: DTOs Not Adopted

**Problem:** DTOs exist but never used

**Mitigation:**
- Document in CLAUDE.md (discoverable)
- Include examples in docstrings
- Reference from architecture gap analysis
- web-prep/F003 provides adoption plan when needed

### Risk: Pattern Inconsistency

**Problem:** Future services adopt differently

**Mitigation:**
- Clear documentation of optional pagination pattern
- Examples show desktop and web usage
- Code review checklist can enforce pattern

### Risk: Premature Optimization

**Problem:** Creating infrastructure we don't need

**Mitigation:**
- MINIMAL infrastructure only (40 lines of code)
- 4 hours effort (not weeks)
- Zero impact on current functionality
- Easy to remove if never adopted

---

## Implementation Plan

### Phase 1: Create DTOs (2 hours)
1. Create `src/services/dto.py` if doesn't exist
2. Add `PaginationParams` dataclass with validation
3. Add `PaginatedResult[T]` generic dataclass
4. Add comprehensive docstrings with examples

### Phase 2: Documentation (2 hours)
1. Add pagination pattern section to CLAUDE.md
2. Document optional pagination pattern
3. Provide desktop vs web examples
4. Document future adoption strategy

### Total: 4 hours

---

## Notes for Implementation

### Key Points

1. **This is foundation only** — No service/UI changes
2. **Zero desktop impact** — Current code unchanged
3. **Web-ready** — DTOs available when migration starts
4. **Incremental adoption** — Services can adopt individually
5. **Low risk** — Just data structures, no refactoring

### When to Use These DTOs

**Immediately:**
- When creating NEW services (use from the start)

**Eventually:**
- When web migration starts (see web-prep/F003)
- When refactoring existing services (opportunistic)

**Never required for:**
- Desktop-only features
- Small lists (<100 items)
- Internal utility functions

### Testing

**Unit tests for DTOs:**
- Test offset() calculation (page 1 → offset 0, page 2 → offset 50)
- Test pages property (100 items, 50 per page → 2 pages)
- Test has_next/has_prev (first page, last page, middle page)
- Test validation (page < 1, per_page > 1000)

---

**END OF SPECIFICATION**
