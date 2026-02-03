# F004: Advanced API Interface Patterns

**Version**: 1.0
**Priority**: PARKED (implement when web migration starts)
**Type**: Service Layer Enhancement
**Status**: Ready for implementation when needed
**Location**: web-prep/ (parked until web migration)
**Estimated Effort**: 2-3 days

---

## Executive Summary

**Status: This feature is PARKED until web migration begins.**

Core API standardization already completed (F094: exceptions, type hints). This spec covers advanced interface patterns - filter objects and method signature standardization - which are most useful with pagination (web-prep/F003, also parked).

Current status:
- ✅ Exception vs None pattern standardized (F094)
- ✅ Tuple returns eliminated (F094)
- ✅ Type hints complete (F094)
- ⏸️ No filter objects (not urgent for desktop)
- ⏸️ Method signatures inconsistent (acceptable for now)

**Estimated implementation time when needed:** 2-3 days

---

## Why This is Parked (Not Implemented Now)

**Filter objects work best with pagination:**
- Filter objects are most useful for paginated list operations
- Pagination is parked (web-prep/F003) until web migration
- Desktop works fine with keyword arguments (small datasets)

**Method signatures depend on filters + pagination:**
```python
# Standard signature (future)
def list_items(
    filter: Optional[ItemFilter] = None,  # ← FR-1: Needs filter objects
    pagination: Optional[PaginationParams] = None,  # ← web-prep/F003: Parked
    session: Optional[Session] = None
) -> PaginatedResult[Item]:  # ← web-prep/F003: Parked
```

**YAGNI principle:**
- Desktop doesn't benefit from filter objects (few parameters, small datasets)
- Large refactoring effort (40+ function signatures)
- Can document pattern and adopt incrementally when web migration starts

**Current state is acceptable:**
- Keyword arguments work fine for desktop
- Can add filters incrementally as needed
- No performance issues with current approach

---

## When to Implement This Feature

**Implement when ANY of these conditions are true:**

✅ **Starting web migration**
- Building FastAPI application
- Implementing web-prep/F003 (pagination)
- Need consistent API patterns

✅ **Query complexity increasing**
- Functions have 5+ filter parameters
- Complex filter composition needed
- Readability suffering from many kwargs

✅ **Team requests standardization**
- Developers ask for consistent patterns
- Code review reveals inconsistency
- Onboarding is harder due to varied signatures

**Current status:** Desktop-only, simple queries, web timeline TBD → REMAINS PARKED

---

## Problem Statement (Future Web Migration)

**Current State (Acceptable for Desktop):**
```
Query Interfaces
├─ ✅ Keyword arguments work fine (2-4 params typical)
├─ ✅ Desktop queries are simple
├─ ❌ No filter objects (not needed yet)
├─ ❌ Method signatures inconsistent
└─ ⏸️ Would benefit from standardization (web)

Method Signatures
├─ ✅ Core patterns consistent (session parameter, etc.)
├─ ❌ Parameter order varies
├─ ❌ Naming inconsistent (search_query vs name_search)
└─ ⏸️ Acceptable for desktop, should improve for web
```

**Target State (Web-Ready Patterns):**
```
Query Interfaces
├─ ✅ Filter objects for complex queries
├─ ✅ Type-safe filter fields
├─ ✅ Composable filter patterns
└─ ✅ Consistent across all services

Method Signatures
├─ ✅ Standard parameter order (primary, filter, pagination, session)
├─ ✅ Consistent naming (filter, pagination, session)
├─ ✅ Predictable patterns across services
└─ ✅ Web-ready interfaces
```

---

## Functional Requirements (When Implementing)

### FR-1: Create Filter Objects

**What it must do:**
- Create filter dataclasses for complex queries (~15 filters)
- Replace multiple keyword arguments with single filter object
- Support optional filter fields (all fields Optional)
- Enable filter composition

**Scope:** Functions with 3+ filter parameters (~30 functions)

**Pattern to apply:**

```python
# Before: Many keyword arguments (desktop pattern)
def get_all_recipes(
    category: Optional[str] = None,
    name_search: Optional[str] = None,
    ingredient_id: Optional[int] = None,
    include_archived: bool = False,
    session: Optional[Session] = None
) -> List[Recipe]:
    """Get all recipes with optional filters."""
    with session_scope() as session:
        query = session.query(Recipe)
        if category:
            query = query.filter(Recipe.category == category)
        if name_search:
            query = query.filter(Recipe.display_name.ilike(f"%{name_search}%"))
        if ingredient_id:
            query = query.join(...)  # Complex join
        if not include_archived:
            query = query.filter(Recipe.archived == False)
        return query.all()

# After: Filter object (web-ready pattern)
@dataclass
class RecipeFilter:
    """Filter parameters for recipe queries."""
    category: Optional[str] = None
    name_search: Optional[str] = None
    ingredient_id: Optional[int] = None
    include_archived: bool = False

def list_recipes(
    filter: Optional[RecipeFilter] = None,
    pagination: Optional[PaginationParams] = None,  # From web-prep/F003
    session: Optional[Session] = None
) -> PaginatedResult[Recipe]:  # From web-prep/F003
    """
    List recipes with optional filtering and pagination.

    Args:
        filter: Optional filter parameters
        pagination: Optional pagination (None = all items)
        session: Optional session

    Returns:
        Paginated result with recipes
    """
    def _impl(sess: Session) -> PaginatedResult[Recipe]:
        query = sess.query(Recipe)

        # Apply filters (if provided)
        if filter:
            if filter.category:
                query = query.filter(Recipe.category == filter.category)
            if filter.name_search:
                query = query.filter(Recipe.display_name.ilike(f"%{filter.name_search}%"))
            if filter.ingredient_id:
                query = query.join(...)
            if not filter.include_archived:
                query = query.filter(Recipe.archived == False)

        # Count total
        total = query.count()

        # Apply pagination (if provided)
        if pagination:
            items = query.offset(pagination.offset()).limit(pagination.per_page).all()
            page, per_page = pagination.page, pagination.per_page
        else:
            items = query.all()
            page, per_page = 1, total if total > 0 else 1

        return PaginatedResult(items=items, total=total, page=page, per_page=per_page)

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

**Filter objects to create (~15):**
- `IngredientFilter` (category, search_query, has_density, parent_id)
- `RecipeFilter` (category, search_query, ingredient_id, include_archived)
- `MaterialFilter` (category_id, subcategory_id, search_query)
- `ProductFilter` (material_id, supplier_id, search_query)
- `EventFilter` (start_date, end_date, status)
- `FinishedGoodFilter` (category, search_query, has_inventory)
- `FinishedUnitFilter` (recipe_id, search_query, has_inventory)
- (Plus ~8 more for other entities)

**Success criteria:**
- [ ] Filter dataclasses created for major entities (~15 filters)
- [ ] All filter fields are Optional (none required)
- [ ] Services accept filter parameter instead of many kwargs
- [ ] Type-safe filter fields
- [ ] Pattern documented with examples

---

### FR-2: Standardize Method Signatures

**What it must do:**
- Establish standard parameter order across all service functions
- Consistent parameter naming (filter, pagination, session)
- Update ~40 function signatures to follow pattern
- Document standard in CLAUDE.md

**Standard signature pattern:**

```python
def operation_name(
    primary_param: PrimaryType,  # Required entity ID, slug, or data
    filter: Optional[FilterClass] = None,  # Optional filtering
    pagination: Optional[PaginationParams] = None,  # Optional pagination
    session: Optional[Session] = None  # Optional session for composition
) -> ReturnType:
    """
    [Operation description]

    Transaction boundary: [Description]

    Args:
        primary_param: [Description]
        filter: Optional filter parameters
        pagination: Optional pagination (None = all items for desktop)
        session: Optional session for transactional composition

    Returns:
        [Return type description]

    Raises:
        [Exceptions that may be raised]
    """
```

**Parameter order rules:**
1. **Primary parameters first** — Required entity identifiers or data
2. **filter second** — Optional filtering
3. **pagination third** — Optional pagination
4. **session last** — Always last (consistency with existing pattern)

**Naming standards:**
- `filter: Optional[EntityFilter]` — NOT search_params, query_params, filters (plural)
- `pagination: Optional[PaginationParams]` — NOT page_params, paging
- `session: Optional[Session]` — Already standardized

**Functions to update (~40):**
- All `list_*()` functions (~20) — Add filter, pagination, session
- All `search_*()` functions (~10) — Convert to list_*() with filter
- Other query functions (~10) — Standardize parameter order

**Success criteria:**
- [ ] Standard signature documented in CLAUDE.md
- [ ] ~40 functions updated to standard order
- [ ] Parameter naming consistent (filter, pagination, session)
- [ ] Docstrings follow standard format
- [ ] Pattern enforced in code review checklist

---

## Implementation Plan (When Needed)

### Phase 1: Create Filter Objects (Day 1)
1. Create `src/services/dto.py` if doesn't exist (or extend)
2. Create ~15 filter dataclasses
3. Document filter pattern in CLAUDE.md
4. Examples for common filter patterns

### Phase 2: Update Service Functions (Day 2)
1. Update ~40 functions to accept filter parameter
2. Update ~40 functions to follow standard signature order
3. Replace keyword arguments with filter field access
4. Update calling code (UI + tests)

### Phase 3: Testing & Documentation (Day 3)
1. Update tests to use filter objects
2. Test desktop behavior unchanged
3. Test web pagination + filtering (if web exists)
4. Comprehensive documentation

**Total: 2-3 days**

---

## Usage Patterns (When Implemented)

### Desktop Usage (Backward Compatible)

**Option A: Use filter objects**
```python
# Desktop UI code
filter_params = RecipeFilter(
    category="cookies",
    name_search="chocolate"
)
result = list_recipes(filter=filter_params)
recipes = result.items  # All matching recipes (pagination=None)
```

**Option B: Don't use filters (if simple)**
```python
# Simple queries can still use get_all_* wrappers (if maintained)
recipes = get_all_recipes()  # All recipes, no filtering
```

### Web API Usage (FastAPI)

```python
# web/routes/recipes.py
from fastapi import APIRouter, Query
from src.services import recipe_service
from src.services.dto import RecipeFilter, PaginationParams

router = APIRouter()

@router.get("/api/recipes")
async def get_recipes(
    category: Optional[str] = None,
    search: Optional[str] = None,
    ingredient_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    List recipes with filtering and pagination.

    Query parameters:
        category: Filter by category
        search: Search recipe names
        ingredient_id: Filter by ingredient
        page: Page number
        per_page: Items per page
    """
    # Build filter from query params
    filter_params = RecipeFilter(
        category=category,
        name_search=search,
        ingredient_id=ingredient_id
    )

    pagination = PaginationParams(page=page, per_page=per_page)

    result = recipe_service.list_recipes(
        filter=filter_params,
        pagination=pagination,
        session=db
    )

    return {
        "items": [RecipeResponse.from_orm(r) for r in result.items],
        "total": result.total,
        "page": result.page,
        "pages": result.pages
    }
```

---

## Out of Scope (NOT Implemented)

**This spec does NOT include:**

- ❌ **Pydantic schemas** — Separate feature (F107 or similar)
- ❌ **DTO layer** — May not be needed (ORM objects work)
- ❌ **Query builders** — SQLAlchemy queries sufficient
- ❌ **Advanced filter composition** — Simple filters sufficient
- ❌ **Filter validation** — Pydantic would handle (future)
- ❌ **Search scoring** — Not needed
- ❌ **Faceted search** — YAGNI

---

## Success Criteria (When Implementing)

**Complete when:**

### Filter Objects
- [ ] ~15 filter dataclasses created
- [ ] All fields Optional (none required)
- [ ] Services accept filter parameter
- [ ] Keyword arguments replaced with filter access
- [ ] Type-safe filter fields
- [ ] Pattern documented

### Method Signatures
- [ ] Standard signature pattern documented
- [ ] ~40 functions updated to standard order
- [ ] Parameter naming consistent (filter, pagination, session)
- [ ] Docstrings follow standard format
- [ ] Code review checklist enforced

### Testing
- [ ] Desktop tests pass (using filter objects)
- [ ] Web tests pass (if web exists)
- [ ] Performance verified (no regression)
- [ ] UI works correctly

### Documentation
- [ ] CLAUDE.md updated with patterns
- [ ] Filter object examples provided
- [ ] Standard signature documented
- [ ] Migration guide for services

---

## Constitutional Compliance

✅ **Principle VI.D.3: Collection Operations**
- "Consistent filtering/search patterns across services"
- Filter objects implement this requirement

✅ **Principle VI.D.1: Method Signatures**
- "Consistent return types across similar operations"
- Standard signatures implement this requirement

✅ **Principle VI.F: Migration & Evolution Readiness**
- Web-ready filter and pagination patterns
- Incremental adoption path

---

## Risk Mitigation

### Risk: Filter Objects Not Adopted

**Problem:** Developers continue using keyword arguments

**Mitigation:**
- Document pattern clearly in CLAUDE.md
- Show examples in common service functions
- Code review enforces pattern
- Pydantic integration (future) makes filters more valuable

### Risk: Signature Standardization Breaking Changes

**Problem:** 40+ functions changing, could break calling code

**Mitigation:**
- Implement with web-prep/F003 (pagination) for consistency
- Update all calling code in same commit
- Comprehensive testing before merge
- Desktop UI should be minimally affected (uses simple patterns)

### Risk: Performance Regression

**Problem:** Filter objects add object creation overhead

**Mitigation:**
- Dataclasses are lightweight (minimal overhead)
- Desktop already fast (no performance issues)
- Web benefits from clearer API patterns

---

## Decision: Why Park This Feature

**Reasons to defer until web migration:**

1. **Dependencies on Parked Features**
   - Works best with pagination (web-prep/F003 - parked)
   - Standard signatures include pagination parameter
   - Natural to implement together

2. **No Current Desktop Need**
   - Keyword arguments work fine (2-4 params typical)
   - Small datasets don't need complex filtering
   - Current patterns are acceptable

3. **Large Refactoring Effort**
   - 40+ function signatures to update
   - All calling code must be updated
   - Significant testing required

4. **Can Adopt Incrementally**
   - Create filter objects as needed (per-service)
   - Document pattern without full rollout
   - Implement when building web API

**Implementing now would be premature for desktop-only needs.**

---

## When to Un-Park This Feature

**Un-park and implement when:**

✅ **Implementing web-prep/F003 (pagination)** (primary trigger)
- Natural to add filter objects at same time
- Standard signature includes pagination
- Consistent rollout

✅ **Building FastAPI application**
- Web APIs benefit most from filter objects
- Consistent patterns important for OpenAPI
- Filter objects → Pydantic schemas (natural progression)

✅ **Query complexity increases**
- Functions have 5+ parameters
- Complex filter composition needed
- Keyword arguments becoming unwieldy

**Don't un-park for:**
❌ "Best practice says we should"
❌ "Might be useful someday"
❌ "Let's standardize everything"

**Current status:** Desktop-only, simple queries, web TBD → REMAINS PARKED

---

## Reference Documentation

**Study these when implementing:**

1. **F094: Core API Standardization**
   - Exception vs None pattern (already implemented)
   - Type hints pattern (already implemented)

2. **F093: Pagination DTOs**
   - `PaginationParams` and `PaginatedResult[T]`
   - Usage patterns for optional pagination

3. **web-prep/F003: Comprehensive Pagination**
   - Service layer pagination patterns
   - Works with filter objects

4. **Architecture Best Practices Gap Analysis**
   - Section 6: API/Interface Design
   - Filter object recommendations

---

**END OF PARKED SPECIFICATION**
