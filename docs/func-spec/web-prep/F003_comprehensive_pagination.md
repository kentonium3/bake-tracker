# F003: Comprehensive Service Layer Pagination

**Version**: 1.0
**Priority**: PARKED (implement when web migration starts)
**Type**: Service Layer Refactoring
**Status**: Ready for implementation when needed
**Location**: web-prep/ (parked until web migration)
**Estimated Effort**: 2-3 days

---

## Executive Summary

**Status: This feature is PARKED until web migration begins.**

Pagination DTOs already exist (F093). This spec covers comprehensive service layer refactoring to adopt pagination across all list operations, supporting both desktop (all items) and web (paginated) usage patterns.

Current status:
- ✅ `PaginationParams` and `PaginatedResult[T]` DTOs exist (F093)
- ✅ Desktop works fine without pagination (100-500 items per list)
- ✅ Service functions can adopt pagination incrementally
- ⏸️ No need to refactor all services until web migration

**Estimated implementation time when needed:** 2-3 days

---

## Why This is Parked (Not Implemented Now)

**No current desktop need:**
1. ✅ Desktop loads 100-500 items instantly
2. ✅ No performance complaints
3. ✅ No memory issues
4. ✅ TreeView handles current scale fine

**Better desktop patterns exist:**
- **Virtual scrolling** (UI-layer only) for large lists
- **Client-side filtering** (data already loaded) is instant
- **Lazy loading** (on-demand) simpler than pagination

**Web migration doesn't exist yet:**
- No FastAPI application
- No concrete web requirements
- Can implement pagination in 2-3 days when building web API

**YAGNI principle:**
- Don't refactor 22 service functions for hypothetical needs
- Service refactoring is high-effort (2-3 weeks total)
- Can adopt incrementally when actually needed
- DTOs provide clear pattern when time comes

---

## When to Implement This Feature

**Implement when ANY of these conditions are true:**

✅ **Starting web migration**
- Building FastAPI application
- Need paginated API endpoints
- Web scalability becomes requirement

✅ **Desktop performance issues emerge**
- Lists exceed 1000+ items
- UI lag noticeable
- Memory issues reported

✅ **Specific feature needs pagination**
- Batch processing requires chunking
- Export needs memory-efficient iteration
- Search results need to be paginated

**Current status:** Desktop-only, web timeline TBD, no performance issues → REMAINS PARKED

---

## Problem Statement (Future Web Migration)

**Current State (Desktop Pattern):**
```
List Operations
├─ ✅ get_all_ingredients() returns List[Ingredient]
├─ ✅ get_all_recipes() returns List[Recipe]
├─ ✅ get_all_materials() returns List[Material]
├─ ✅ Works fine for desktop (100-500 items)
└─ ⏸️ Not web-scalable (loads all items)

Web API Requirements (Future)
└─ ⚠️ Need paginated endpoints (1000s of items)
```

**Target State (Web-Ready Pattern):**
```
List Operations
├─ ✅ list_ingredients() accepts optional PaginationParams
├─ ✅ Returns PaginatedResult[Ingredient]
├─ ✅ Desktop: pagination=None → all items (backward compatible)
├─ ✅ Web: pagination=PaginationParams(page=X) → one page
└─ ✅ Same function serves both desktop and web

Web API Readiness
└─ ✅ READY: Services support paginated endpoints
```

---

## Functional Requirements (When Implementing)

### FR-1: Refactor List Operations to Support Pagination

**Scope:** ~22 service functions across 16 service files

**Pattern to apply:**

```python
# Before: Desktop-only pattern
def get_all_ingredients() -> List[Ingredient]:
    """Get all ingredients."""
    with session_scope() as session:
        return session.query(Ingredient).all()

# After: Desktop + Web pattern
def list_ingredients(
    filter: Optional[IngredientFilter] = None,
    pagination: Optional[PaginationParams] = None,
    session: Optional[Session] = None
) -> PaginatedResult[Ingredient]:
    """
    List ingredients with optional filtering and pagination.

    Transaction boundary: Read-only, no transaction needed.

    Args:
        filter: Optional filter parameters
        pagination: Optional pagination (None = all items for desktop)
        session: Optional session

    Returns:
        Paginated result with ingredients

    Examples:
        # Desktop usage (all items)
        result = list_ingredients()  # pagination=None
        all_ingredients = result.items

        # Web usage (paginated)
        result = list_ingredients(pagination=PaginationParams(page=2, per_page=50))
        page_items = result.items
        print(f"Page {result.page} of {result.pages}")
    """
    def _impl(sess: Session) -> PaginatedResult[Ingredient]:
        query = sess.query(Ingredient)

        # Apply filters (if provided)
        if filter:
            if filter.category:
                query = query.filter(Ingredient.category == filter.category)
            if filter.search_query:
                query = query.filter(
                    Ingredient.display_name.ilike(f"%{filter.search_query}%")
                )

        # Count total before pagination
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
            per_page = total if total > 0 else 1

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
```

**Functions to refactor (~22):**
- `ingredient_service.get_all_ingredients()` → `list_ingredients()`
- `recipe_service.get_all_recipes()` → `list_recipes()`
- `material_catalog_service.get_all_materials()` → `list_materials()`
- `event_service.get_all_events()` → `list_events()`
- `finished_good_service.get_all_finished_goods()` → `list_finished_goods()`
- `finished_unit_service.get_all_finished_units()` → `list_finished_units()`
- (Plus ~16 more across service files)

**Success criteria:**
- [ ] All list operations support optional pagination parameter
- [ ] All return `PaginatedResult[T]`
- [ ] Desktop behavior preserved (pagination=None returns all)
- [ ] Web behavior supported (pagination returns one page)
- [ ] Consistent signature pattern across services

---

### FR-2: Create Filter Objects

**What it must do:**
- Create filter dataclasses for complex queries
- Replace scattered keyword arguments
- Standardize filtering interface

**Example:**

```python
# src/services/dto.py
@dataclass
class IngredientFilter:
    """Filter parameters for ingredient queries."""
    category: Optional[str] = None
    search_query: Optional[str] = None
    has_density: Optional[bool] = None
    parent_id: Optional[int] = None

@dataclass
class RecipeFilter:
    """Filter parameters for recipe queries."""
    category: Optional[str] = None
    search_query: Optional[str] = None
    ingredient_id: Optional[int] = None
    include_archived: bool = False

@dataclass
class MaterialFilter:
    """Filter parameters for material queries."""
    category_id: Optional[int] = None
    subcategory_id: Optional[int] = None
    search_query: Optional[str] = None
```

**Success criteria:**
- [ ] Filter dataclasses created for major entities (~15 filters)
- [ ] Services use filter objects instead of kwargs
- [ ] Consistent filtering pattern across services

---

### FR-3: Add Backward-Compatible Wrappers

**What it must do:**
- Keep `get_all_*()` functions for backward compatibility
- Internally call `list_*()` with pagination=None
- Mark as deprecated in docstrings
- Provide migration timeline

**Example:**

```python
def get_all_ingredients() -> List[Ingredient]:
    """
    Get all ingredients.

    DEPRECATED: Use list_ingredients() for better flexibility.
    This function will be removed in v2.0.

    Desktop migration:
        # Old
        ingredients = get_all_ingredients()

        # New
        result = list_ingredients()
        ingredients = result.items

    Returns:
        List of all ingredients
    """
    result = list_ingredients(pagination=None)
    return result.items
```

**Success criteria:**
- [ ] Backward-compatible wrappers for all refactored functions
- [ ] Marked deprecated with migration examples
- [ ] Desktop UI works without changes initially
- [ ] Deprecation timeline documented

---

### FR-4: Update UI Components (Phased)

**Phase 1: Desktop continues unchanged**
- Use deprecated `get_all_*()` wrappers
- No UI changes required
- Verify functionality unchanged

**Phase 2: Migrate to `list_*()` (optional)**
- Update UI to use `list_*()` with pagination=None
- Extract items from PaginatedResult
- Same UX, updated API calls

**Phase 3: Add pagination controls (optional for desktop)**
- Add pagination controls to large lists (>500 items)
- Implement page navigation
- Show "Page X of Y" status

**Example UI migration:**

```python
# Phase 1: No changes (deprecated wrapper)
def load_data(self):
    self.ingredients = ingredient_service.get_all_ingredients()
    self._update_display()

# Phase 2: Use new API (no pagination)
def load_data(self):
    result = ingredient_service.list_ingredients()
    self.ingredients = result.items
    self._update_display()

# Phase 3: Add pagination (optional for desktop)
def load_data(self, page=1):
    result = ingredient_service.list_ingredients(
        pagination=PaginationParams(page=page, per_page=100)
    )
    self.ingredients = result.items
    self.update_status(f"Page {result.page} of {result.pages} ({result.total} total)")
    self._update_display()
```

**Success criteria:**
- [ ] Phase 1: Desktop works with wrappers (no UI changes)
- [ ] Phase 2: UI migrated to `list_*()` (optional)
- [ ] Phase 3: Pagination controls added (optional)
- [ ] No UX regression at any phase

---

## Implementation Plan (When Needed)

### Phase 1: Service Layer Refactoring (2 days)

**Day 1: Core services**
- Refactor ingredient_service (~4 functions, 2 hours)
- Refactor recipe_service (~4 functions, 2 hours)
- Refactor material_catalog_service (~4 functions, 2 hours)
- Create filter objects for above (~1 hour)
- Test desktop behavior unchanged (~1 hour)

**Day 2: Remaining services**
- Refactor event_service, finished_good_service, etc. (~10 functions, 4 hours)
- Create remaining filter objects (~2 hours)
- Add backward-compatible wrappers (~1 hour)
- Update tests (~1 hour)

### Phase 2: Documentation & Testing (0.5 day)
- Update CLAUDE.md with new patterns
- Document migration path for UI
- Comprehensive testing (desktop + web)
- Performance verification

### Phase 3: UI Migration (Optional, 1-2 days)
- Phase 1: Verify wrappers work (0 hours - automatic)
- Phase 2: Migrate UI to `list_*()` (1 day if desired)
- Phase 3: Add pagination controls (1 day if desired)

**Total: 2-3 days (service layer) + optional 1-2 days (UI)**

---

## Usage Patterns (When Implemented)

### Desktop Usage (Backward Compatible)

**Option A: Continue using deprecated wrappers**
```python
# UI code unchanged
ingredients = get_all_ingredients()  # Uses wrapper internally
for ingredient in ingredients:
    print(ingredient.display_name)
```

**Option B: Use new API (recommended)**
```python
# Updated UI code
result = list_ingredients()  # pagination=None (all items)
ingredients = result.items
print(f"Loaded {result.total} ingredients")
```

### Web API Usage (FastAPI)

```python
# web/routes/ingredients.py
from fastapi import APIRouter, Query
from src.services import ingredient_service
from src.services.dto import PaginationParams, IngredientFilter

router = APIRouter()

@router.get("/api/ingredients")
async def get_ingredients(
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    List ingredients with pagination.

    Query parameters:
        category: Filter by category
        search: Search by name
        page: Page number (default 1)
        per_page: Items per page (default 50, max 1000)
    """
    filter_params = IngredientFilter(category=category, search_query=search)
    pagination = PaginationParams(page=page, per_page=per_page)

    result = ingredient_service.list_ingredients(
        filter=filter_params,
        pagination=pagination,
        session=db
    )

    return {
        "items": [IngredientResponse.from_orm(i) for i in result.items],
        "total": result.total,
        "page": result.page,
        "per_page": result.per_page,
        "pages": result.pages,
        "has_next": result.has_next,
        "has_prev": result.has_prev
    }
```

---

## Out of Scope (NOT Implemented)

**This spec does NOT include:**

- ❌ **Cursor-based pagination** — Offset/limit sufficient for 99% of cases
- ❌ **Advanced sorting** — Simple ORDER BY sufficient initially
- ❌ **Full-text search** — LIKE queries sufficient for desktop scale
- ❌ **Result caching** — Premature optimization
- ❌ **Infinite scroll** — Pagination sufficient
- ❌ **Virtual scrolling** — UI-layer concern, not service layer

---

## Success Criteria (When Implementing)

**Complete when:**

### Service Layer
- [ ] All 22 list operations support optional pagination
- [ ] All return `PaginatedResult[T]`
- [ ] Filter objects created for complex queries (~15 filters)
- [ ] Backward-compatible wrappers exist
- [ ] Desktop behavior unchanged (pagination=None)

### Documentation
- [ ] CLAUDE.md updated with pagination patterns
- [ ] Migration examples provided
- [ ] Deprecation timeline documented
- [ ] Web usage examples added

### Testing
- [ ] Desktop tests pass (using pagination=None)
- [ ] Web tests pass (using pagination params)
- [ ] Performance verified (no regression)
- [ ] Backward-compatible wrappers tested

### UI (Optional)
- [ ] Phase 1: Wrappers work (automatic)
- [ ] Phase 2: UI migrated to `list_*()` (if desired)
- [ ] Phase 3: Pagination controls added (if desired)

---

## Constitutional Compliance

✅ **Principle VI.D: API Consistency & Contracts**
- Consistent pagination pattern across all services
- Standardized filter objects
- Predictable return types

✅ **Principle VI.G: Resource Management**
- Memory-efficient pagination for large datasets
- Optional chunking for export operations

✅ **Principle VI.F: Migration Readiness**
- Service layer ready for web APIs
- Desktop and web use same functions
- Incremental adoption path

---

## Risk Mitigation

### Risk: Desktop Performance Regression

**Problem:** Pagination adds overhead for small datasets

**Mitigation:**
- Optional pagination (pagination=None returns all)
- Desktop continues using "return all" pattern
- Pagination only used when beneficial (web, large datasets)

### Risk: UI Breaking Changes

**Problem:** Changing return types breaks UI

**Mitigation:**
- Backward-compatible wrappers maintain old interface
- Phased UI migration (can stay on wrappers indefinitely)
- Desktop works without changes

### Risk: Inconsistent Adoption

**Problem:** Some services paginated, others not

**Mitigation:**
- Clear documentation of pattern
- Code review checklist enforces consistency
- Implement all services in single feature (2-3 days)

---

## Decision: Why Park This Feature

**Reasons to defer until web migration:**

1. **No Current Desktop Need**
   - 100-500 items load instantly
   - No performance complaints
   - UI handles current scale fine

2. **Better Desktop Patterns Exist**
   - Virtual scrolling (UI-only) for perceived performance
   - Client-side filtering (data already loaded)
   - Lazy loading (simpler than pagination)

3. **Quick Implementation When Needed**
   - 2-3 days to implement all services
   - DTOs already exist (F093)
   - Clear pattern documented

4. **Web Migration Doesn't Exist**
   - No FastAPI application
   - No concrete requirements
   - Can implement when actually building web

**Implementing now would be premature optimization for hypothetical web needs.**

---

## When to Un-Park This Feature

**Un-park and implement when:**

✅ **Building FastAPI application** (primary trigger)
- Creating web API endpoints
- Need paginated responses
- Web scalability required

✅ **Desktop performance issues emerge**
- Lists exceed 1000+ items
- UI becomes noticeably slow
- Memory usage concerning

✅ **Specific feature needs pagination**
- Batch export of large datasets
- Search results pagination required
- Admin tools for large data management

**Don't un-park for:**
❌ "Might be useful someday"
❌ "Best practice says we should"
❌ "Let's prepare for future"

**Current status:** Desktop-only, no performance issues, web TBD → REMAINS PARKED

---

## Reference Documentation

**Study these when implementing:**

1. **F093: Pagination DTOs Foundation**
   - `PaginationParams` and `PaginatedResult[T]` implementations
   - Usage patterns and examples

2. **Architecture Best Practices Gap Analysis**
   - Section 6: API/Interface Design
   - Pagination patterns and recommendations

3. **Current Service Patterns**
   - Session parameter pattern (CLAUDE.md)
   - Filter implementation examples
   - Transaction boundary documentation (F091)

4. **FastAPI Dependency Injection (when building web)**
   - https://fastapi.tiangolo.com/tutorial/dependencies/
   - https://fastapi.tiangolo.com/tutorial/sql-databases/

---

**END OF PARKED SPECIFICATION**
