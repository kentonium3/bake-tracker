# F001: Web Migration Session Management Guide

**Version**: 2.0 (Revised)
**Priority**: PARKED (implement when building web version)
**Type**: Migration Guide
**Status**: Ready for implementation when needed
**Location**: web-prep/ (parked until web migration)

---

## Executive Summary

**Status: This feature is PARKED until web migration begins.**

Current desktop session management is **already web-ready** due to the session parameter pattern. When migrating to web (FastAPI), minimal changes are needed:
- ✅ Service layer already accepts `session` parameter — no changes needed
- ✅ FastAPI provides built-in dependency injection for request-scoped sessions
- ✅ SQLAlchemy provides `scoped_session` for thread-local storage if needed
- ⏸️ No changes to desktop codebase required until web migration

**Estimated implementation time when needed:** 2-4 hours

---

## Problem Statement

**Current State (Desktop):**
```
Session Management
├─ ✅ session_scope() context manager works perfectly
├─ ✅ Session parameter pattern enables composition
├─ ✅ Service functions accept optional session parameter
└─ ✅ Transaction boundaries documented

Web Migration Concerns
└─ ⚠️ Need request-scoped sessions for concurrent requests
```

**Target State (Web):**
```
Session Management
├─ ✅ Desktop: session_scope() unchanged (backward compatible)
├─ ✅ Web: FastAPI dependency injection for request-scoped sessions
├─ ✅ Service layer: No changes (already accepts session parameter)
└─ ✅ Thread-safe concurrent request handling

Web Migration Readiness
└─ ✅ READY: Service layer already web-compatible
```

---

## Why This is Parked (Not Implemented Now)

**Current session management is already sufficient:**
1. ✅ Service layer accepts `session` parameter — enables request-scoped composition
2. ✅ `session_scope()` context manager works perfectly for desktop
3. ✅ Transaction boundaries documented in service functions
4. ✅ No concurrent request issues in single-user desktop app

**Why defer to web migration:**
1. 🎯 **YAGNI Principle** — Don't build infrastructure for hypothetical needs
2. 🎯 **Framework Integration** — FastAPI has better patterns built-in
3. 🎯 **Zero Risk** — Current code works, changes add risk without benefit
4. 🎯 **Quick Implementation** — Takes 2-4 hours when actually needed

---

## Web Migration Implementation Guide

**When you actually build the web application, implement this:**

### Approach 1: FastAPI Dependency Injection (RECOMMENDED)

**Idiomatic FastAPI pattern, zero changes to service layer:**

```python
# web/dependencies.py (NEW FILE when building FastAPI app)
from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session
from src.services.database import get_session

async def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    Automatically:
    - Creates session at request start
    - Commits on success
    - Rolls back on error
    - Closes session after response

    Usage:
        @app.get("/ingredients")
        def list_ingredients(db: Session = Depends(get_db)):
            return ingredient_service.list_ingredients(session=db)
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# web/routes/ingredients.py (NEW FILE)
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.services import ingredient_service
from .dependencies import get_db

router = APIRouter()

@app.get("/api/ingredients")
async def list_ingredients(
    category: Optional[str] = None,
    db: Session = Depends(get_db)  # ← Request-scoped session
):
    """
    List ingredients with filtering.

    Session automatically scoped to this HTTP request.
    Service layer unchanged - just pass the session.
    """
    filter_params = IngredientFilter(category=category)
    result = ingredient_service.list_ingredients(
        filter=filter_params,
        session=db  # ← Pass request-scoped session
    )
    return result
```

**Benefits:**
- ✅ Idiomatic FastAPI pattern (what everyone expects)
- ✅ Zero changes to service layer (already accepts session parameter)
- ✅ Framework handles lifecycle automatically
- ✅ Built-in request scoping (no manual context management)
- ✅ Works with FastAPI middleware, background tasks, etc.

**Implementation time:** 1-2 hours

---

### Approach 2: SQLAlchemy Scoped Session (Optional Enhancement)

**If you need thread-local sessions (rare):**

```python
# src/services/database.py (MODIFY when needed)
from sqlalchemy.orm import scoped_session, sessionmaker

_scoped_session: Optional[scoped_session] = None

def get_scoped_session() -> scoped_session:
    """
    Get thread-local scoped session (for web concurrency).

    Desktop usage: Ignore this function, use session_scope() as always.
    Web usage: Use in middleware for automatic thread-local storage.

    Returns:
        Thread-local session that persists across function calls in same request
    """
    global _scoped_session
    if _scoped_session is None:
        factory = get_session_factory()
        _scoped_session = scoped_session(factory)
    return _scoped_session

# web/middleware.py (NEW FILE if using this approach)
from fastapi import Request
from src.services.database import get_scoped_session

@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    """Store request-scoped session in thread-local storage."""
    session_factory = get_scoped_session()
    session = session_factory()

    try:
        response = await call_next(request)
        session.commit()
        return response
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        session_factory.remove()  # Clear thread-local
```

**When to use:**
- Only if Approach 1 (Depends) doesn't work for your use case
- If you need implicit session access across many function calls
- If migrating from Flask/Django patterns

**Implementation time:** 2-3 hours

---

## What Needs to Change (When Migrating)

### Desktop Code: NO CHANGES NEEDED
```python
# src/services/ingredient_service.py
# This code works identically for both desktop and web
def create_ingredient(
    ingredient_data: IngredientCreate,
    session: Optional[Session] = None  # ← Already web-ready
) -> Ingredient:
    def _impl(sess: Session) -> Ingredient:
        ingredient = Ingredient(**ingredient_data.dict())
        sess.add(ingredient)
        sess.flush()
        return ingredient

    if session is not None:
        return _impl(session)  # ← Web passes session here
    with session_scope() as sess:
        return _impl(sess)     # ← Desktop uses this path
```

**No changes to service layer.** The session parameter pattern makes it web-ready.

### Web App: NEW CODE ONLY
```
project/
├── src/                      # UNCHANGED - desktop code
│   ├── models/
│   ├── services/            # ← These work as-is
│   └── ui/                  # ← Desktop UI only
│
└── web/                     # NEW - web application
    ├── main.py              # FastAPI app
    ├── dependencies.py      # get_db() dependency
    ├── routes/
    │   ├── ingredients.py
    │   ├── recipes.py
    │   └── ...
    └── middleware.py        # Optional
```

**Add new web layer, don't modify existing services.**

---

## Implementation Checklist (When Building Web App)

**This checklist is for when you actually implement the web version:**

### Phase 1: Create Web Dependency (30 minutes)
- [ ] Create `web/dependencies.py` file
- [ ] Implement `get_db()` function using FastAPI Depends pattern
- [ ] Test that sessions are properly scoped to requests
- [ ] Verify commit/rollback behavior

### Phase 2: Create Web Routes (1-2 hours)
- [ ] Create `web/routes/` directory structure
- [ ] Implement first endpoint (e.g., list ingredients)
- [ ] Pass `db: Session = Depends(get_db)` to route
- [ ] Pass session to service functions: `service.list_items(session=db)`
- [ ] Verify service layer works without changes

### Phase 3: Test Concurrent Requests (30 minutes)
- [ ] Test multiple simultaneous requests
- [ ] Verify sessions don't cross-contaminate
- [ ] Verify proper session cleanup
- [ ] Load test with realistic traffic

### Phase 4: Update Documentation (30 minutes)
- [ ] Document web dependency pattern in README
- [ ] Add examples to service function docstrings
- [ ] Note desktop vs web usage patterns
- [ ] Document middleware if using Approach 2

**Total estimated time:** 2-4 hours

---

## Key Insights (Why Current Code is Web-Ready)

### Service Layer Already Web-Compatible

**The session parameter pattern makes services web-ready:**

```python
# Every service function follows this pattern
def service_function(
    data: InputModel,
    session: Optional[Session] = None  # ← Web compatibility
) -> OutputModel:
    def _impl(sess: Session):
        # Implementation here
        pass

    # Desktop path (no session passed)
    if session is not None:
        return _impl(session)

    # Web path (session from Depends)
    with session_scope() as sess:
        return _impl(sess)
```

**This pattern enables:**
- ✅ Desktop: Calls without session parameter (uses `session_scope()`)
- ✅ Web: Calls with request-scoped session from FastAPI
- ✅ Testing: Pass mock/in-memory session
- ✅ Composition: Pass session between service functions

### FastAPI Handles Request Scoping

**No need for manual context management:**

```python
# FastAPI automatically:
# 1. Creates session at request start
# 2. Injects into route handler
# 3. Commits on success / rolls back on error
# 4. Closes session after response

@app.get("/items")
def get_items(db: Session = Depends(get_db)):
    # db is request-scoped automatically
    return service.list_items(session=db)
```

**No context variables needed.** Framework does it.

### Desktop Code Unchanged

**Desktop continues using session_scope():**

```python
# Desktop UI (unchanged)
def on_create_button_click():
    data = get_form_data()
    try:
        ingredient = create_ingredient(data)  # No session passed
        show_success("Ingredient created")
    except ServiceError as e:
        show_error(str(e))
```

**Web and desktop coexist peacefully:**
- Desktop calls services without session → uses `session_scope()`
- Web calls services with session → uses FastAPI's `Depends`
- Same service code, different callers

---

## Out of Scope (NOT Implemented)

**This guide explicitly DOES NOT include:**
- ❌ Building the actual FastAPI application (separate feature)
- ❌ Authentication/authorization (separate feature)
- ❌ API schemas and serialization (separate feature)
- ❌ Database migration to PostgreSQL (optional, separate feature)
- ❌ Changes to desktop application (works as-is)
- ❌ Changes to service layer (already web-ready)

---

## Constitutional Compliance

✅ **Principle VI.C: Dependency & State Management**
- Session parameter pattern enables dependency injection
- Explicit session lifecycle in both desktop and web contexts
- Transaction boundaries maintained

✅ **Principle VI.F: Migration & Evolution Readiness**
- Service layer already web-compatible (session parameter)
- FastAPI patterns are industry-standard
- Desktop unchanged, web added alongside

✅ **YAGNI Principle (Do Not Implement Until Needed)**
- No premature abstraction
- Implement when building actual web app
- Use framework patterns over custom infrastructure

---

## Risk Mitigation

**Risk: Desktop breaks when adding web**
- **Mitigation:** Web is separate code path, desktop unchanged
- **Verification:** Run desktop app tests after adding web layer

**Risk: Performance degradation**
- **Mitigation:** FastAPI Depends pattern is lightweight
- **Verification:** Load test web API before production

**Risk: Session lifecycle bugs in web**
- **Mitigation:** FastAPI's Depends handles lifecycle automatically
- **Verification:** Test concurrent requests, verify no cross-contamination

**Risk: Developer confusion (two patterns)**
- **Mitigation:** Clear documentation of when to use each
- **Rule:** Desktop uses session_scope(), web uses Depends(get_db)

---

## Reference Documentation

**Study these when implementing web version:**

1. **FastAPI Dependency Injection:**
   - https://fastapi.tiangolo.com/tutorial/dependencies/
   - https://fastapi.tiangolo.com/tutorial/sql-databases/

2. **SQLAlchemy Session Management:**
   - https://docs.sqlalchemy.org/en/20/orm/session_basics.html
   - https://docs.sqlalchemy.org/en/20/orm/contextual.html (scoped_session)

3. **Current Session Pattern (CLAUDE.md):**
   - Session parameter pattern documented
   - Transaction boundary guidelines
   - Multi-step operation examples

---

## Decision: Why Defer This Feature

**Reasons to park until web migration:**

1. **YAGNI (You Aren't Gonna Need It):**
   - Current code works perfectly for desktop
   - No web app exists to use new patterns
   - Building infrastructure for hypothetical needs

2. **Framework Integration is Better:**
   - FastAPI has session management built-in
   - More idiomatic than custom patterns
   - Better documented, more maintainable

3. **Zero Current Benefit:**
   - Desktop doesn't need concurrent request support
   - Desktop doesn't need request-scoped sessions
   - Adding complexity without solving problems

4. **Quick Implementation Later:**
   - Takes 2-4 hours when actually needed
   - Service layer already compatible
   - No risky refactoring required

**Implementing now would be premature optimization.**

---

## When to Implement This Feature

**Implement when ANY of these conditions are true:**

✅ **You start building the FastAPI web application**
- Need API endpoints that call service layer
- Need request-scoped database sessions
- Ready to test web concurrency

✅ **You're planning web migration in next 1-2 months**
- Want to prepare infrastructure ahead
- Have time to test web patterns
- Can verify both desktop and web work

❌ **Don't implement if:**
- Only building desktop features
- Web migration is >6 months away
- No concrete web requirements yet

**Current status:** Desktop-only, web migration timeline TBD → PARKED

---

**END OF MIGRATION GUIDE**
