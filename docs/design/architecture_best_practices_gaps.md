# Architecture Best Practices Gap Analysis

**Document Type:** Design Recommendation
**Created:** 2026-02-02
**Status:** Active
**Purpose:** Identify architectural gaps and inconsistencies to improve development velocity, ease web migration, and support multi-agent AI workflows

---

## Executive Summary

This document provides a comprehensive analysis of architectural best practices gaps in the Bake Tracker desktop application. The codebase has **solid foundations** with clear layered architecture and separation of concerns, but exhibits inconsistencies that will impact web migration and maintenance.

### Key Findings

**Strengths:**
- ✅ Clear layered architecture (UI → Services → Models → Database)
- ✅ Good separation of concerns
- ✅ Centralized configuration system (`Config` class)
- ✅ Custom exception hierarchy exists
- ✅ Session management patterns documented

**Critical Gaps (Web Migration Blockers):**
1. **Error handling inconsistency** - 88 files catch generic `Exception`
2. **Session management** - Desktop-focused, needs request-scoped pattern
3. **API design** - Mixed return types, no pagination, inconsistent None handling

**Priority Matrix:**

| Area | Current Impact | Migration Impact | Refactor Effort |
|------|---------------|------------------|-----------------|
| Error Handling | Medium | High | Medium |
| Migration Readiness | Low | High | Large |
| API/Interface Design | Low | High | Large |
| Transaction Management | Low | Medium | Medium |
| Observability | Low | Medium | Medium |
| Data Validation | Low | Medium | Large |
| Configuration | Low | Medium | Small |
| Dependency Injection | Low | Low | Medium |
| Resource Management | Low | Low | Small |
| Code Organization | Low | Low | Medium |

---

## 1. Error Handling & Resilience

### Current State

**Good foundations:**
- Custom exception hierarchy exists (`ServiceException`, `ServiceError` base classes)
- Domain-specific exceptions (`IngredientNotFoundBySlug`, `ProductNotFound`, `ValidationError`)
- Structured logging utilities (`logging_utils.py`)

**Key files:**
- `src/services/exceptions.py` - Exception hierarchy
- `src/services/logging_utils.py` - Structured logging
- `src/services/batch_production_service.py` - Domain exceptions

### Gaps Identified

1. **Generic exception catching (88 files):**
   ```python
   # Current pattern in UI files
   try:
       ingredient = create_ingredient(data)
   except Exception as e:
       print(f"ERROR: {e}")  # Generic catch-all
   ```

2. **Mixed exception bases:**
   ```python
   # exceptions.py shows both:
   class ServiceException(Exception):  # Legacy
   class ServiceError(Exception):      # New
   ```

3. **Mixed user/developer error messages:**
   ```python
   # batch_production_service.py:89
   super().__init__(f"Insufficient {ingredient_slug}: need {needed} {unit}, have {available} {unit}")
   # Good for developers, needs user-friendly wrapper
   ```

4. **No centralized error recovery/retry patterns**
5. **Inconsistent logging levels** - some use `logger.info()` for errors

### Impact Assessment

- **Current desktop development:** Medium — works but harder to debug
- **Web migration difficulty:** High — generic exceptions won't map to HTTP status codes
- **Maintenance burden:** Medium — inconsistent patterns slow debugging

### Recommendation

**Adopt three-tier exception strategy:**

1. **Domain exceptions** (inherit from `ServiceError`)
2. **Error context wrapper** for user-facing messages
3. **Centralized error handler** for UI layer

### Proposed Pattern

```python
# src/services/exceptions.py
class UserFriendlyError(ServiceError):
    """Exception with user-facing message."""
    def __init__(self, user_message: str, technical_details: str = None):
        self.user_message = user_message
        self.technical_details = technical_details
        super().__init__(user_message)

# src/ui/error_handler.py
def handle_service_error(error: Exception) -> str:
    """Convert service exceptions to user-friendly messages."""
    if isinstance(error, IngredientNotFoundBySlug):
        return f"Ingredient '{error.slug}' not found"
    elif isinstance(error, ValidationError):
        return f"Validation failed: {', '.join(error.errors)}"
    elif isinstance(error, InsufficientInventoryError):
        return f"Not enough {error.ingredient_slug} in inventory"
    else:
        logger.exception("Unexpected error")
        return "An unexpected error occurred"

# Usage in UI
try:
    ingredient = create_ingredient(data)
except ServiceError as e:
    user_msg = handle_service_error(e)
    messagebox.showerror("Error", user_msg)
except Exception as e:
    logger.exception("Unexpected error")
    messagebox.showerror("Error", "An unexpected error occurred")
```

### Refactoring Scope

**Medium effort** — requires updating 88 files but can be done incrementally:
1. Create centralized error handler (1 file)
2. Update UI files batch by batch (88 files, ~5 min each)
3. Standardize exception hierarchy (consolidate legacy classes)

---

## 2. Configuration Management

### Current State

**Good foundations:**
- Centralized `Config` class in `src/utils/config.py`
- Environment-based paths (development vs production)
- Environment variable support (`BAKING_TRACKER_ENV`)

**Key files:**
- `src/utils/config.py` - Config class
- `src/utils/constants.py` - Application constants

### Gaps Identified

1. **Hard-coded values scattered throughout:**
   ```python
   # database.py:130
   connect_args={"check_same_thread": False, "timeout": 30}  # Hard-coded timeout

   # health_service.py:51
   check_interval: int = 30  # Hard-coded default

   # main.py:139-140
   ctk.set_appearance_mode("system")
   ctk.set_default_color_theme("blue")  # Hard-coded theme
   ```

2. **No feature flags system**
3. **Database connection settings not configurable** (timeout, pool size)
4. **UI constants in code** rather than configurable

### Impact Assessment

- **Current desktop development:** Low — works but inflexible
- **Web migration difficulty:** Medium — need environment-specific configs
- **Maintenance burden:** Low — manageable but could be better

### Recommendation

**Extend `Config` class with:**
- Database connection settings (timeout, pool size)
- Feature flags dictionary
- UI theme/appearance settings
- Optional config file (YAML/JSON) for overrides

### Proposed Pattern

```python
# config.py
class Config:
    # Existing properties...

    @property
    def db_timeout(self) -> int:
        """Database connection timeout in seconds."""
        return int(os.environ.get("BAKE_TRACKER_DB_TIMEOUT", "30"))

    @property
    def db_pool_size(self) -> int:
        """Database connection pool size."""
        return int(os.environ.get("BAKE_TRACKER_DB_POOL_SIZE", "5"))

    @property
    def db_pool_recycle(self) -> int:
        """Connection recycle time in seconds."""
        return int(os.environ.get("BAKE_TRACKER_DB_POOL_RECYCLE", "3600"))

    @property
    def feature_flags(self) -> Dict[str, bool]:
        """Feature flags for gradual rollout."""
        return {
            "enable_audit_trail": os.environ.get("ENABLE_AUDIT", "false").lower() == "true",
            "enable_health_checks": os.environ.get("ENABLE_HEALTH", "true").lower() == "true",
            "enable_performance_monitoring": os.environ.get("ENABLE_PERF_MON", "false").lower() == "true",
        }

    @property
    def ui_theme(self) -> str:
        """UI color theme."""
        return os.environ.get("BAKE_TRACKER_THEME", "blue")

    @property
    def ui_appearance(self) -> str:
        """UI appearance mode (system/dark/light)."""
        return os.environ.get("BAKE_TRACKER_APPEARANCE", "system")

# database.py
config = get_config()
engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False, "timeout": config.db_timeout},
    pool_size=config.db_pool_size,
    pool_recycle=config.db_pool_recycle,
)

# main.py
config = get_config()
ctk.set_appearance_mode(config.ui_appearance)
ctk.set_default_color_theme(config.ui_theme)
```

### Refactoring Scope

**Small effort** — extend existing `Config` class, migrate hard-coded values incrementally:
1. Add new properties to `Config` class (1 hour)
2. Update database initialization (30 min)
3. Update UI initialization (30 min)
4. Find and migrate other hard-coded values as discovered

---

## 3. Dependency Injection & Testability

### Current State

**Good foundations:**
- Services are stateless functions (good for testability)
- `session_scope()` context manager for database access
- Some services accept optional `session` parameter

**Key files:**
- `src/services/database.py` - `session_scope()` context manager
- `src/services/inventory_item_service.py:65` - `session: Optional[Session] = None` pattern
- `src/services/batch_production_service.py:126` - Session parameter support

### Gaps Identified

1. **Inconsistent session parameter usage:**
   - Some services accept `session=None` (good)
   - Others always create new sessions (less composable)
   - Pattern documented in `CLAUDE.md` but not universally applied

2. **No dependency injection container:**
   - Services import each other directly
   - Hard to mock dependencies in tests
   - Circular dependency risks

3. **Mixed service instantiation patterns:**
   - Some modules use classes (`FinishedUnitService`)
   - Others use module-level functions (`ingredient_service.create_ingredient()`)

### Impact Assessment

- **Current desktop development:** Low — works but testing harder
- **Web migration difficulty:** Medium — need request-scoped sessions
- **Maintenance burden:** Medium — inconsistent patterns

### Recommendation

**Standardize on:**
1. Session parameter pattern for all services (already documented)
2. Service registry pattern for dependency lookup (future)
3. Consistent function-based services (avoid mixing classes/functions)

### Proposed Pattern

```python
# Standard pattern for ALL services
def create_ingredient(
    ingredient_data: Dict[str, Any],
    session: Optional[Session] = None
) -> Ingredient:
    """
    Create ingredient with optional session for composability.

    Args:
        ingredient_data: Ingredient data dictionary
        session: Optional SQLAlchemy session (for transactional composition)

    Returns:
        Created Ingredient object

    Raises:
        ValidationError: If ingredient data is invalid
    """
    def _impl(sess: Session) -> Ingredient:
        # Actual implementation here
        validate_ingredient_data(ingredient_data)
        ingredient = Ingredient(**ingredient_data)
        sess.add(ingredient)
        sess.flush()  # Get ID without committing
        return ingredient

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)
```

**Current inconsistent patterns:**

```python
# ingredient_service.py - creates own session (INCONSISTENT)
def create_ingredient(data):
    with session_scope() as session:
        # ...

# inventory_item_service.py - accepts session (GOOD)
def add_to_inventory(..., session: Optional[Session] = None):
    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)
```

### Refactoring Scope

**Medium effort** — update service signatures and calling code:
1. Audit all service functions (~50 functions)
2. Add `session` parameter to functions that lack it (~25 functions)
3. Update calling code to pass session in transactional contexts (~30 call sites)
4. Update tests to use session parameter for better isolation

---

## 4. Data Validation & Constraints

### Current State

**Good foundations:**
- Validation utilities in `src/utils/validators.py`
- Model-level validation via SQLAlchemy `@validates` decorator
- Business rule validation in services

**Key files:**
- `src/utils/validators.py` - Validation functions
- `src/models/base.py` - Base model with validation support
- `src/services/ingredient_service.py:62` - `validate_density_fields()` example

### Gaps Identified

1. **No Pydantic or schema validation framework:**
   - Validation logic scattered (validators.py, services, models)
   - No automatic API schema generation for web migration
   - Manual dictionary validation is error-prone

2. **Type hints incomplete:**
   - Some functions lack return type hints
   - `Any` used frequently instead of specific types
   - Runtime type validation missing

3. **Validation error messages inconsistent:**
   - Some return tuples `(bool, str)`
   - Others raise exceptions
   - No standardized error format

4. **Business rules validation location unclear:**
   - Some in services (good)
   - Some in models (acceptable)
   - Some in UI (bad)

### Impact Assessment

- **Current desktop development:** Low — works but inconsistent
- **Web migration difficulty:** High — need API request/response validation
- **Maintenance burden:** Medium — scattered validation logic

### Recommendation

**Introduce Pydantic models for:**
- Service input/output validation
- API request/response schemas (web migration ready)
- Type-safe data transfer objects
- Automatic FastAPI schema generation

### Proposed Pattern

```python
# schemas.py
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class IngredientCreate(BaseModel):
    """Schema for creating an ingredient."""
    display_name: str = Field(..., max_length=200, min_length=1)
    category: str = Field(..., max_length=100)
    density_volume_value: Optional[float] = Field(None, gt=0)
    density_volume_unit: Optional[str] = Field(None, max_length=20)
    density_weight_value: Optional[float] = Field(None, gt=0)
    density_weight_unit: Optional[str] = Field(None, max_length=20)

    @validator('density_volume_unit', 'density_weight_unit')
    def validate_density_fields(cls, v, values):
        """All-or-nothing validation for density fields."""
        has_any = any([
            values.get('density_volume_value'),
            v,
            values.get('density_weight_value')
        ])
        if has_any:
            has_all = all([
                values.get('density_volume_value'),
                values.get('density_volume_unit'),
                values.get('density_weight_value'),
                values.get('density_weight_unit')
            ])
            if not has_all:
                raise ValueError("All density fields required together or none")
        return v

    class Config:
        """Pydantic config."""
        str_strip_whitespace = True

class IngredientResponse(BaseModel):
    """Schema for ingredient response."""
    id: int
    slug: str
    display_name: str
    category: str
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""
        orm_mode = True  # Allows creation from ORM objects

# ingredient_service.py
def create_ingredient(
    ingredient_data: IngredientCreate,  # Pydantic validation automatic
    session: Optional[Session] = None
) -> Ingredient:
    """
    Create ingredient.

    Args:
        ingredient_data: Validated ingredient data (Pydantic handles validation)
        session: Optional session

    Returns:
        Created Ingredient object
    """
    def _impl(sess: Session) -> Ingredient:
        ingredient = Ingredient(**ingredient_data.dict())
        sess.add(ingredient)
        sess.flush()
        return ingredient

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)

# FastAPI usage (future)
from fastapi import APIRouter
router = APIRouter()

@router.post("/ingredients", response_model=IngredientResponse)
def create_ingredient_endpoint(ingredient: IngredientCreate):
    """Create ingredient via API."""
    result = create_ingredient(ingredient)  # Validation automatic
    return IngredientResponse.from_orm(result)
```

**Current pattern (manual validation):**

```python
# validators.py
def validate_ingredient_data(data: dict) -> Tuple[bool, list]:
    errors = []
    if not data.get('display_name'):
        errors.append("Display name required")
    # ... many more manual checks
    return len(errors) == 0, errors

# ingredient_service.py
def create_ingredient(ingredient_data: Dict[str, Any]) -> Ingredient:
    is_valid, errors = validate_ingredient_data(ingredient_data)
    if not is_valid:
        raise ValidationError(errors)
    # ...
```

### Refactoring Scope

**Large effort** — requires adding Pydantic and migrating validation:
1. Add `pydantic` to requirements.txt
2. Create schema definitions for all domain models (~20 schemas)
3. Migrate validation logic from validators.py to Pydantic validators
4. Update all service signatures to use Pydantic models
5. Update UI layer to convert to Pydantic models before service calls
6. Update tests to use Pydantic models

**Benefit:** Web migration gets automatic OpenAPI schema generation for free.

---

## 5. Transaction & State Management

### Current State

**Good foundations:**
- `session_scope()` context manager handles transactions
- Automatic rollback on exception
- Some services support session parameter for composability

**Key files:**
- `src/services/database.py:316` - `session_scope()` implementation
- `src/services/inventory_item_service.py:126` - Session composability pattern
- `CLAUDE.md` documents session management anti-patterns

### Gaps Identified

1. **Nested transaction handling unclear:**
   - `session_scope()` doesn't support nested transactions
   - No savepoint support for partial rollbacks
   - Complex operations can't be composed with fine-grained rollback

2. **Transaction boundaries inconsistent:**
   - Some operations span multiple `session_scope()` calls
   - Risk of partial commits (some succeed, others fail)
   - Multi-step operations lack atomic guarantees

3. **No explicit transaction isolation levels:**
   - SQLite defaults used (may not be sufficient for web)
   - No control over isolation for sensitive operations

4. **State mutation tracking limited:**
   - `updated_at` timestamps exist
   - No change history/audit trail
   - Can't see "what changed" or rollback to previous state

### Impact Assessment

- **Current desktop development:** Low — single-user, works fine
- **Web migration difficulty:** High — need proper transaction isolation
- **Maintenance burden:** Medium — current pattern works but needs enhancement

### Recommendation

1. **Add savepoint support** for nested transactions
2. **Document transaction boundaries** explicitly in service docstrings
3. **Consider audit trail** for critical operations (see Observability section)

### Proposed Pattern

```python
# database.py
from sqlalchemy import text

@contextmanager
def session_scope(isolation_level: str = None):
    """
    Enhanced session scope with optional isolation level.

    Args:
        isolation_level: Optional isolation level (READ COMMITTED, SERIALIZABLE, etc.)

    Yields:
        SQLAlchemy Session

    Example:
        with session_scope(isolation_level="SERIALIZABLE") as session:
            # Sensitive financial operation
            process_payment(session)
    """
    session = get_session()

    if isolation_level:
        # PostgreSQL: SET TRANSACTION ISOLATION LEVEL
        session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"))

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

@contextmanager
def savepoint(session: Session, name: str = "sp"):
    """
    Create a savepoint for nested transaction support.

    Args:
        session: Active SQLAlchemy session
        name: Savepoint name (optional)

    Yields:
        Savepoint object

    Example:
        with session_scope() as session:
            create_recipe(data, session=session)
            try:
                with savepoint(session):
                    # This can rollback independently
                    add_optional_components(recipe_id, session=session)
            except ValidationError:
                # Recipe created, but components skipped
                logger.warning("Components validation failed, continuing without them")
    """
    savepoint_obj = session.begin_nested()
    try:
        yield savepoint_obj
    except Exception:
        savepoint_obj.rollback()
        raise
    else:
        # Commit savepoint (not the outer transaction)
        pass  # Nested transaction commits on context exit

# Usage in service
def record_batch_production(
    recipe_slug: str,
    quantity: float,
    consume_inventory: bool = True,
    session: Optional[Session] = None
) -> ProductionRun:
    """
    Record batch production with atomic inventory consumption.

    Transaction boundary: Single session ensures either:
    - Production recorded AND inventory consumed
    - OR entire operation rolled back

    Args:
        recipe_slug: Recipe to produce
        quantity: Quantity produced
        consume_inventory: Whether to consume inventory (default True)
        session: Optional session for composability

    Returns:
        Created ProductionRun

    Raises:
        InsufficientInventoryError: If inventory insufficient
    """
    def _impl(sess: Session) -> ProductionRun:
        # Create production run
        production = ProductionRun(recipe_slug=recipe_slug, quantity=quantity)
        sess.add(production)
        sess.flush()

        if consume_inventory:
            # This happens in same transaction - atomic
            ingredients = get_aggregated_ingredients(recipe_slug, session=sess)
            for ingredient in ingredients:
                consume_fifo(
                    ingredient_slug=ingredient['slug'],
                    quantity=ingredient['quantity'] * quantity,
                    unit=ingredient['unit'],
                    session=sess  # PASS SESSION - critical for atomicity
                )

        return production

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

### Refactoring Scope

**Medium effort** — enhance `session_scope()` and update documentation:
1. Add `savepoint()` context manager (1 hour)
2. Add isolation level support to `session_scope()` (1 hour)
3. Audit multi-step operations for transaction boundaries (~20 functions)
4. Update service docstrings to document transaction guarantees (~50 functions)
5. Add transaction tests for critical operations (~10 tests)

---

## 6. API/Interface Design

### Current State

**Good foundations:**
- Service functions follow consistent naming (`create_*`, `get_*`, `update_*`, `delete_*`)
- Return types mostly consistent (ORM objects or lists)
- Some functions return dictionaries for complex data

**Key files:**
- `src/services/ingredient_service.py` - Consistent function signatures
- `src/services/batch_production_service.py:121` - Returns Dict for complex results
- `src/services/finished_good_service.py` - Mix of objects and dicts

### Gaps Identified

1. **Return type inconsistency:**
   ```python
   # Some return ORM objects
   def get_ingredient(slug: str) -> Optional[Ingredient]: ...

   # Some return dictionaries
   def check_can_produce(...) -> Dict[str, Any]:
       return {"can_produce": True, "missing": [...]}

   # Some return tuples (legacy)
   def validate_data(data: dict) -> Tuple[bool, list]: ...
   ```

2. **None/null handling unclear:**
   - Some functions return `None` for not found
   - Others raise exceptions
   - No consistent pattern documented

3. **No pagination support:**
   ```python
   def get_all_ingredients() -> List[Ingredient]:
       return session.query(Ingredient).all()  # Loads everything!
   ```

4. **Filtering interface inconsistent:**
   - Some use keyword arguments (`get_inventory_items(ingredient_slug=...)`)
   - Others use separate functions (`search_ingredients()`)
   - No standardized filter object

### Impact Assessment

- **Current desktop development:** Low — works for current scale
- **Web migration difficulty:** High — need consistent API patterns
- **Maintenance burden:** Medium — inconsistent patterns slow development

### Recommendation

**Standardize on:**
1. **Consistent return types** (Pydantic DTOs or ORM objects, not mixed)
2. **Pagination support** for all list operations
3. **Filter objects** instead of many keyword arguments
4. **Consistent None vs exception pattern**: Raise exception for not found

### Proposed Pattern

```python
# dto.py
from dataclasses import dataclass
from typing import Optional, List, Generic, TypeVar

T = TypeVar('T')

@dataclass
class PaginationParams:
    """Pagination parameters for list operations."""
    page: int = 1
    per_page: int = 50

    def offset(self) -> int:
        """Calculate SQL offset."""
        return (self.page - 1) * self.per_page

@dataclass
class PaginatedResult(Generic[T]):
    """Generic paginated result."""
    items: List[T]
    total: int
    page: int
    per_page: int

    @property
    def pages(self) -> int:
        """Total number of pages."""
        return (self.total + self.per_page - 1) // self.per_page

    @property
    def has_next(self) -> bool:
        """Whether there's a next page."""
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        """Whether there's a previous page."""
        return self.page > 1

@dataclass
class IngredientFilter:
    """Filter parameters for ingredient queries."""
    category: Optional[str] = None
    search_query: Optional[str] = None
    has_density: Optional[bool] = None

# ingredient_service.py
def get_ingredient(slug: str, session: Optional[Session] = None) -> Ingredient:
    """
    Get ingredient by slug.

    Args:
        slug: Ingredient slug
        session: Optional session

    Returns:
        Ingredient object

    Raises:
        IngredientNotFoundBySlug: If ingredient not found
    """
    def _impl(sess: Session) -> Ingredient:
        ingredient = sess.query(Ingredient).filter_by(slug=slug).first()
        if not ingredient:
            raise IngredientNotFoundBySlug(slug)
        return ingredient

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)

def list_ingredients(
    filter: Optional[IngredientFilter] = None,
    pagination: Optional[PaginationParams] = None,
    session: Optional[Session] = None
) -> PaginatedResult[Ingredient]:
    """
    List ingredients with filtering and pagination.

    Args:
        filter: Optional filter parameters
        pagination: Optional pagination parameters
        session: Optional session

    Returns:
        Paginated result with ingredients

    Example:
        # Get second page of baking ingredients
        result = list_ingredients(
            filter=IngredientFilter(category="baking"),
            pagination=PaginationParams(page=2, per_page=25)
        )
        for ingredient in result.items:
            print(ingredient.display_name)
        print(f"Page {result.page} of {result.pages}")
    """
    def _impl(sess: Session) -> PaginatedResult[Ingredient]:
        query = sess.query(Ingredient)

        # Apply filters
        if filter:
            if filter.category:
                query = query.filter_by(category=filter.category)
            if filter.search_query:
                query = query.filter(
                    Ingredient.display_name.ilike(f"%{filter.search_query}%")
                )
            if filter.has_density is not None:
                if filter.has_density:
                    query = query.filter(Ingredient.density_volume_value.isnot(None))
                else:
                    query = query.filter(Ingredient.density_volume_value.is_(None))

        # Count total before pagination
        total = query.count()

        # Apply pagination
        pagination_params = pagination or PaginationParams()
        items = query.offset(pagination_params.offset()).limit(pagination_params.per_page).all()

        return PaginatedResult(
            items=items,
            total=total,
            page=pagination_params.page,
            per_page=pagination_params.per_page
        )

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

**Backwards compatibility wrapper:**

```python
def get_all_ingredients(session: Optional[Session] = None) -> List[Ingredient]:
    """
    Get all ingredients (legacy method).

    DEPRECATED: Use list_ingredients() with pagination for better performance.
    """
    result = list_ingredients(
        pagination=PaginationParams(page=1, per_page=10000),
        session=session
    )
    return result.items
```

### Refactoring Scope

**Large effort** — requires updating all service interfaces:
1. Create DTOs for pagination and filters (1-2 days)
2. Update all `list_*` / `get_all_*` functions to support pagination (~30 functions)
3. Standardize exception vs None pattern (~40 functions)
4. Create filter objects for complex queries (~15 filters)
5. Update UI layer to handle pagination (~20 UI components)
6. Update tests to use new patterns (~100 test updates)

**Phased approach:**
- Phase 1: Add pagination support to new services
- Phase 2: Add backwards-compatible pagination to existing services
- Phase 3: Migrate UI to use pagination
- Phase 4: Remove deprecated methods

---

## 7. Resource Management

### Current State

**Good foundations:**
- Database connections managed via SQLAlchemy session lifecycle
- `session_scope()` ensures proper cleanup
- File operations generally use context managers

**Key files:**
- `src/services/database.py:316` - Proper session cleanup
- `src/services/health_service.py:61` - File path management

### Gaps Identified

1. **File handle management:**
   - Import/export operations may not always use context managers
   - Backup operations need verification
   - Large file imports might hold handles too long

2. **Database connection pooling:**
   - SQLite uses default pooling (may need tuning for web)
   - No connection pool monitoring or metrics
   - No visibility into pool exhaustion

3. **Memory-intensive operations:**
   - `get_all_*` functions load entire tables into memory
   - No streaming/chunking for large datasets
   - Risk of OOM with large production databases

4. **Background thread cleanup:**
   - `HealthCheckService` uses daemon threads (good)
   - But no explicit cleanup verification on shutdown
   - No graceful shutdown hooks

### Impact Assessment

- **Current desktop development:** Low — single-user, works fine
- **Web migration difficulty:** Medium — need connection pooling
- **Maintenance burden:** Low — current patterns adequate

### Recommendation

1. **Add connection pool monitoring** for visibility
2. **Implement chunking/streaming** for large queries
3. **Verify all file operations** use context managers
4. **Add graceful shutdown** handlers

### Proposed Pattern

```python
# database.py
def get_pool_status() -> Dict[str, Any]:
    """
    Get connection pool status for monitoring.

    Returns:
        Dictionary with pool metrics

    Example:
        status = get_pool_status()
        print(f"Active connections: {status['checked_out']}/{status['size']}")
    """
    pool = get_engine().pool
    return {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "overflow_current": getattr(pool, '_overflow', 0),
    }

# ingredient_service.py
from typing import Generator

def get_all_ingredients_chunked(
    chunk_size: int = 1000,
    session: Optional[Session] = None
) -> Generator[List[Ingredient], None, None]:
    """
    Generator for large datasets to avoid memory issues.

    Args:
        chunk_size: Number of records per chunk
        session: Optional session

    Yields:
        Lists of Ingredient objects

    Example:
        for chunk in get_all_ingredients_chunked(chunk_size=100):
            for ingredient in chunk:
                process(ingredient)
    """
    def _impl(sess: Session):
        offset = 0
        while True:
            chunk = sess.query(Ingredient).offset(offset).limit(chunk_size).all()
            if not chunk:
                break
            yield chunk
            offset += chunk_size

    if session is not None:
        yield from _impl(session)
    else:
        with session_scope() as sess:
            yield from _impl(sess)

# import_export_service.py
def export_ingredients_to_csv(file_path: Path) -> None:
    """
    Export ingredients to CSV with proper resource management.

    Args:
        file_path: Output CSV file path

    Example:
        export_ingredients_to_csv(Path("ingredients.csv"))
    """
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['slug', 'display_name', 'category'])
        writer.writeheader()

        # Process in chunks to avoid memory issues
        for chunk in get_all_ingredients_chunked(chunk_size=1000):
            for ingredient in chunk:
                writer.writerow({
                    'slug': ingredient.slug,
                    'display_name': ingredient.display_name,
                    'category': ingredient.category
                })

    logger.info(f"Exported ingredients to {file_path}")

# main.py
import signal
import sys

def shutdown_handler(signum, frame):
    """Graceful shutdown handler."""
    logger.info("Shutdown signal received, cleaning up...")

    # Stop health check service
    if health_service_instance:
        health_service_instance.stop()

    # Close database connections
    from src.services.database import close_all_connections
    close_all_connections()

    logger.info("Cleanup complete, exiting")
    sys.exit(0)

# Register shutdown handlers
signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)
```

### Refactoring Scope

**Small effort** — mostly verification and monitoring additions:
1. Add pool monitoring utilities (2 hours)
2. Implement chunked generators for large queries (~10 functions, 1 day)
3. Audit file operations for context manager usage (4 hours)
4. Add graceful shutdown handlers (2 hours)

---

## 8. Observability & Debugging

### Current State

**Good foundations:**
- Basic logging via Python `logging` module
- Structured logging utilities in `logging_utils.py`
- Health check service writes status to JSON file
- `created_at`/`updated_at` timestamps on all models

**Key files:**
- `src/services/logging_utils.py` - Structured logging helpers
- `src/services/health_service.py` - Health monitoring
- `src/models/base.py:49` - Timestamp fields

### Gaps Identified

1. **No audit trail for data changes:**
   - Timestamps exist but no change history
   - Can't see who changed what or when
   - No rollback capability from audit log
   - Critical for compliance and debugging

2. **No correlation IDs:**
   - Can't trace requests across service calls
   - Multi-step operations difficult to debug
   - Log entries not linked across function boundaries

3. **Logging levels inconsistent:**
   - Some use `logger.info()` for errors
   - No standard for when to use each level
   - Makes filtering logs difficult

4. **No performance monitoring:**
   - No query timing
   - No slow query detection
   - No operation duration tracking
   - Can't identify performance bottlenecks

5. **Limited debug mode support:**
   - No debug flag in config
   - SQL echo controlled per-engine, not globally
   - Hard to enable verbose logging for troubleshooting

### Impact Assessment

- **Current desktop development:** Low — single-user, easier to debug
- **Web migration difficulty:** High — need request tracing and audit trails
- **Maintenance burden:** Medium — harder to debug production issues

### Recommendation

1. **Add correlation ID support** (thread-local or context variable)
2. **Implement audit trail** for critical operations (creates, updates, deletes)
3. **Add performance monitoring** middleware/decorators
4. **Standardize logging levels** across codebase

### Proposed Pattern

```python
# context.py
from contextvars import ContextVar
from uuid import uuid4
from typing import Optional

# Context variable for correlation ID (thread-safe)
correlation_id: ContextVar[str] = ContextVar('correlation_id', default=None)

def get_correlation_id() -> Optional[str]:
    """Get current correlation ID."""
    return correlation_id.get()

def set_correlation_id(corr_id: str = None) -> str:
    """
    Set correlation ID for current context.

    Args:
        corr_id: Optional correlation ID (generates UUID if not provided)

    Returns:
        The correlation ID set
    """
    corr_id = corr_id or str(uuid4())
    correlation_id.set(corr_id)
    return corr_id

# audit.py
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text
from src.models.base import BaseModel
from src.utils.datetime_utils import utc_now

class AuditLog(BaseModel):
    """Audit trail for data changes."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    correlation_id = Column(String(36), index=True, nullable=True)
    entity_type = Column(String(50), nullable=False, index=True)  # 'ingredient', 'recipe', etc.
    entity_id = Column(Integer, nullable=False, index=True)
    entity_slug = Column(String(200), nullable=True)  # For easier debugging
    action = Column(String(20), nullable=False)  # 'create', 'update', 'delete'
    changed_fields = Column(JSON, nullable=True)  # {'field': {'old': x, 'new': y}}
    user_id = Column(String(100), nullable=True)  # For future multi-user
    timestamp = Column(DateTime, default=utc_now, nullable=False)
    notes = Column(Text, nullable=True)  # Optional context

    def __repr__(self):
        return f"<AuditLog {self.action} {self.entity_type}:{self.entity_id} at {self.timestamp}>"

def create_audit_log(
    entity_type: str,
    entity_id: int,
    action: str,
    changed_fields: dict = None,
    entity_slug: str = None,
    notes: str = None,
    session: Session = None
) -> AuditLog:
    """
    Create audit log entry.

    Args:
        entity_type: Type of entity ('ingredient', 'recipe', etc.)
        entity_id: ID of entity
        action: Action performed ('create', 'update', 'delete')
        changed_fields: Dictionary of changed fields with old/new values
        entity_slug: Optional slug for easier debugging
        notes: Optional notes
        session: SQLAlchemy session

    Returns:
        Created AuditLog
    """
    audit = AuditLog(
        correlation_id=get_correlation_id(),
        entity_type=entity_type,
        entity_id=entity_id,
        entity_slug=entity_slug,
        action=action,
        changed_fields=changed_fields,
        notes=notes
    )

    if session:
        session.add(audit)
        session.flush()

    return audit

# ingredient_service.py
def update_ingredient(
    slug: str,
    ingredient_data: dict,
    session: Optional[Session] = None
) -> Ingredient:
    """
    Update ingredient with audit trail.

    Args:
        slug: Ingredient slug
        ingredient_data: Fields to update
        session: Optional session

    Returns:
        Updated Ingredient
    """
    def _impl(sess: Session) -> Ingredient:
        correlation = get_correlation_id()
        logger.info(f"[{correlation}] Updating ingredient {slug}")

        ingredient = get_ingredient(slug, session=sess)

        # Capture old values for audit
        old_values = {
            'display_name': ingredient.display_name,
            'category': ingredient.category,
            # ... other fields
        }

        # Apply updates
        for key, value in ingredient_data.items():
            setattr(ingredient, key, value)

        # Create audit trail
        changes = {
            k: {'old': old_values.get(k), 'new': ingredient_data.get(k)}
            for k in ingredient_data.keys()
            if old_values.get(k) != ingredient_data.get(k)
        }

        if changes:
            create_audit_log(
                entity_type='ingredient',
                entity_id=ingredient.id,
                entity_slug=ingredient.slug,
                action='update',
                changed_fields=changes,
                session=sess
            )

        logger.info(f"[{correlation}] Updated ingredient {slug}: {list(changes.keys())}")
        return ingredient

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)

# performance.py
import time
import functools
from typing import Callable

def track_performance(threshold_ms: float = 1000):
    """
    Decorator to track function performance.

    Args:
        threshold_ms: Log warning if execution exceeds this threshold (milliseconds)

    Example:
        @track_performance(threshold_ms=500)
        def expensive_operation():
            # ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            correlation = get_correlation_id()

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.perf_counter() - start) * 1000

                if duration_ms > threshold_ms:
                    logger.warning(
                        f"[{correlation}] Slow operation: {func.__name__} "
                        f"took {duration_ms:.2f}ms (threshold: {threshold_ms}ms)"
                    )
                else:
                    logger.debug(
                        f"[{correlation}] {func.__name__} took {duration_ms:.2f}ms"
                    )

        return wrapper
    return decorator

# Usage
@track_performance(threshold_ms=500)
def aggregate_ingredients_for_recipe(recipe_slug: str) -> List[dict]:
    # Will log warning if takes > 500ms
    # ...
```

**Logging level standards:**

```python
# logging_standards.py
"""
Logging Level Standards
=======================

DEBUG: Detailed diagnostic information
- Function entry/exit
- Variable values during execution
- SQL queries (when SQL echo enabled)

INFO: Normal operation events
- Successful operations (created, updated, deleted)
- Operation parameters
- Business events (production recorded, inventory consumed)

WARNING: Unexpected but recoverable events
- Slow operations (exceeding threshold)
- Deprecated function usage
- Resource constraints (low inventory, nearing limits)

ERROR: Error events that don't stop execution
- Validation failures
- Business rule violations (insufficient inventory)
- Handled exceptions

CRITICAL: Severe errors that might cause shutdown
- Database connection failures
- Configuration errors
- Unhandled exceptions at top level
"""
```

### Refactoring Scope

**Medium effort** — requires adding audit models and correlation ID infrastructure:
1. Create `AuditLog` model and migration (4 hours)
2. Add correlation ID context variable (2 hours)
3. Add audit logging to critical operations (~30 functions, 2 days)
4. Add performance tracking decorator (2 hours)
5. Standardize logging levels across codebase (~100 files, 2 days)
6. Add UI for viewing audit logs (1 day)

---

## 9. Code Organization

### Current State

**Good foundations:**
- Clear layered architecture (models/, services/, ui/, utils/)
- Services organized by domain (ingredient_service, recipe_service, etc.)
- Good separation of concerns

**Key files:**
- `src/services/` - Well-organized service modules
- `src/models/` - Clear model definitions
- `src/ui/` - UI components separated

### Gaps Identified

1. **Some large service files:**
   - `finished_good_service.py` - 1700+ lines
   - `ingredient_service.py` - 800+ lines
   - Could benefit from splitting into focused modules

2. **Import patterns:**
   - Some circular import risks (models importing services)
   - No explicit import organization (isort not enforced)
   - Relative vs absolute imports mixed

3. **Dead code:**
   - Some commented-out code
   - Legacy functions may not be used
   - No automated dead code detection

4. **Module complexity:**
   - Some services mix multiple responsibilities
   - Could benefit from further decomposition
   - Single Responsibility Principle violations

### Impact Assessment

- **Current desktop development:** Low — works but harder to navigate
- **Web migration difficulty:** Low — structure is fine
- **Maintenance burden:** Medium — large files harder to maintain

### Recommendation

1. **Split large service files** into focused modules
2. **Add import organization** (isort)
3. **Remove dead code** systematically
4. **Consider feature-based organization** for very large domains

### Proposed Pattern

```python
# Current: finished_good_service.py - 1700+ lines
# Contains: CRUD, search, assembly logic, component management, hierarchy, etc.

# Proposed: Split into focused modules
# finished_good/
#   __init__.py          # Public API exports
#   crud.py              # Basic CRUD operations
#   assembly.py          # Assembly-specific logic
#   search.py            # Search and filtering
#   hierarchy.py         # Hierarchy operations
#   validation.py        # Business rule validation

# finished_good/__init__.py
"""
Finished Good service module.

Public API for finished good operations. Import from this module
to access all finished good functionality.
"""

from .crud import (
    create_finished_good,
    get_finished_good_by_id,
    update_finished_good,
    delete_finished_good,
)

from .assembly import (
    add_component,
    remove_component,
    get_components,
    calculate_total_cost,
)

from .search import (
    search_finished_goods,
    list_finished_goods,
    get_by_category,
)

from .hierarchy import (
    get_hierarchy,
    get_parent_assemblies,
    validate_hierarchy,
)

__all__ = [
    # CRUD
    'create_finished_good',
    'get_finished_good_by_id',
    'update_finished_good',
    'delete_finished_good',
    # Assembly
    'add_component',
    'remove_component',
    'get_components',
    'calculate_total_cost',
    # Search
    'search_finished_goods',
    'list_finished_goods',
    'get_by_category',
    # Hierarchy
    'get_hierarchy',
    'get_parent_assemblies',
    'validate_hierarchy',
]

# finished_good/crud.py
"""CRUD operations for finished goods."""

from typing import Optional
from sqlalchemy.orm import Session

from src.models.finished_good import FinishedGood
from src.services.database import session_scope
from src.services.exceptions import FinishedGoodNotFound

def create_finished_good(
    data: dict,
    session: Optional[Session] = None
) -> FinishedGood:
    """Create finished good."""
    # Implementation...

def get_finished_good_by_id(
    finished_good_id: int,
    session: Optional[Session] = None
) -> FinishedGood:
    """Get finished good by ID."""
    # Implementation...

# ... etc

# finished_good/assembly.py
"""Assembly operations for finished goods."""

def add_component(
    finished_good_id: int,
    component_id: int,
    quantity: float,
    session: Optional[Session] = None
) -> None:
    """Add component to finished good."""
    # Implementation...

# Usage (external code imports from package)
from src.services.finished_good import create_finished_good, add_component

finished_good = create_finished_good(data)
add_component(finished_good.id, component_id=42, quantity=2.0)
```

**Import organization with isort:**

```python
# pyproject.toml or setup.cfg
[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
skip_gitignore = true

# Enforced import order
import_heading_stdlib = "Standard library"
import_heading_thirdparty = "Third-party"
import_heading_firstparty = "Application"
import_heading_localfolder = "Local"

# Example properly organized imports
# Standard library
import os
import sys
from datetime import datetime
from typing import Optional, List

# Third-party
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Session

# Application
from src.models.base import BaseModel
from src.services.database import session_scope
from src.services.exceptions import ValidationError

# Local (relative imports within same package)
from .validation import validate_ingredient_data
from .helpers import slugify
```

### Refactoring Scope

**Medium effort** — requires refactoring large files but can be incremental:
1. Add isort to pre-commit hooks (1 hour)
2. Run isort on entire codebase (1 hour)
3. Split `finished_good_service.py` into package (~1 week)
4. Split `ingredient_service.py` if needed (~2 days)
5. Remove commented-out code (~4 hours)
6. Identify and remove unused functions (requires analysis, ~1 week)

**Phased approach:**
- Phase 1: Add isort and organize imports
- Phase 2: Split largest service file (finished_good)
- Phase 3: Remove dead code
- Phase 4: Split additional large files as needed

---

## 10. Migration Readiness

### Current State

**Good foundations:**
- SQLAlchemy ORM used throughout (database abstraction)
- Some raw SQL in migration scripts (acceptable)
- Session management via context manager

**Key files:**
- `src/services/database.py` - SQLAlchemy-based
- `src/services/migration_service.py` - Some raw SQL for migrations
- `src/models/base.py` - Database-agnostic model base

### Gaps Identified

1. **SQLite-specific code:**
   ```python
   # database.py:121
   db_path_str = str(self._database_path).replace("\\", "/")
   return f"sqlite:///{db_path_str}"  # SQLite-specific URL format

   # database.py:130
   connect_args={"check_same_thread": False, "timeout": 30}  # SQLite-specific
   ```

2. **Session management desktop-focused:**
   - `session_scope()` assumes single-threaded desktop app
   - Web needs request-scoped sessions
   - No session factory pattern for dependency injection
   - Global session state won't work for concurrent requests

3. **No authentication/authorization preparation:**
   - No user model
   - No permission system
   - All operations assume single user
   - No concept of ownership or access control

4. **Multi-tenancy not considered:**
   - No tenant isolation
   - All data in single database
   - Would need significant refactoring for SaaS

5. **Connection string handling:**
   - Hard-coded SQLite URL format
   - No support for PostgreSQL connection strings
   - No connection pooling configuration

### Impact Assessment

- **Current desktop development:** Low — works fine
- **Web migration difficulty:** High — significant refactoring needed
- **Maintenance burden:** Medium — database-agnostic patterns help

### Recommendation

1. **Abstract database URL creation** (support PostgreSQL)
2. **Add session factory pattern** for request-scoped sessions
3. **Plan user/auth model** (even if single-user initially)
4. **Consider tenant_id columns** for future multi-tenancy (optional)

### Proposed Pattern

```python
# config.py - Database-agnostic configuration
class Config:
    @property
    def database_type(self) -> str:
        """Database type: 'sqlite' or 'postgresql'."""
        return os.environ.get("BAKE_TRACKER_DB_TYPE", "sqlite")

    @property
    def database_url(self) -> str:
        """
        Get database URL based on environment.

        SQLite (desktop): sqlite:///path/to/database.db
        PostgreSQL (web): postgresql://user:pass@host:port/dbname
        """
        if self.database_type == "postgresql":
            # Use standard DATABASE_URL from environment
            url = os.environ.get("DATABASE_URL")
            if not url:
                raise ValueError("DATABASE_URL required for PostgreSQL")
            return url
        else:
            # SQLite for desktop
            db_path_str = str(self._database_path).replace("\\", "/")
            return f"sqlite:///{db_path_str}"

    @property
    def db_connect_args(self) -> dict:
        """Database-specific connection arguments."""
        if self.database_type == "postgresql":
            return {}  # PostgreSQL doesn't need special args
        else:
            # SQLite-specific
            return {
                "check_same_thread": False,
                "timeout": self.db_timeout
            }

# database.py - Web-ready session management
from contextvars import ContextVar
from sqlalchemy.orm import sessionmaker

# Request-scoped session for web (context variable is thread-safe)
request_session: ContextVar[Session] = ContextVar('request_session', default=None)

class SessionFactory:
    """Factory for creating sessions (request-scoped for web)."""

    def __init__(self, engine: Engine):
        self.engine = engine
        self._session_factory = sessionmaker(bind=engine)

    def create_session(self) -> Session:
        """
        Create a new session.

        In web context, this creates a request-scoped session.
        In desktop context, creates a one-off session.
        """
        return self._session_factory()

    def get_current_session(self) -> Optional[Session]:
        """Get current request-scoped session (web only)."""
        return request_session.get()

    def set_current_session(self, session: Session) -> None:
        """Set current request-scoped session (web only)."""
        request_session.set(session)

# Global session factory (initialized at startup)
_session_factory: Optional[SessionFactory] = None

def init_database(config: Config) -> SessionFactory:
    """
    Initialize database and return session factory.

    Args:
        config: Configuration object

    Returns:
        SessionFactory for creating sessions
    """
    global _session_factory

    engine = create_engine(
        config.database_url,
        connect_args=config.db_connect_args,
        pool_size=config.db_pool_size,
        pool_recycle=config.db_pool_recycle,
        echo=config.sql_echo,
    )

    _session_factory = SessionFactory(engine)
    return _session_factory

def get_session_factory() -> SessionFactory:
    """Get global session factory."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _session_factory

# Desktop usage (unchanged)
@contextmanager
def session_scope():
    """
    Desktop session context manager.

    Creates a one-off session, commits on success, rolls back on error.
    """
    factory = get_session_factory()
    session = factory.create_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# Web usage (FastAPI example)
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse

app = FastAPI()

@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    """
    Middleware to create request-scoped database session.

    Creates session at start of request, commits on success,
    rolls back on error, and always closes.
    """
    factory = get_session_factory()
    session = factory.create_session()
    factory.set_current_session(session)

    try:
        response = await call_next(request)
        session.commit()
        return response
    except Exception as e:
        session.rollback()
        logger.exception("Request failed")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )
    finally:
        session.close()
        factory.set_current_session(None)

# Dependency for route handlers
def get_db() -> Session:
    """
    FastAPI dependency to get current request session.

    Usage:
        @app.get("/ingredients")
        def list_ingredients(db: Session = Depends(get_db)):
            return ingredient_service.list_ingredients(session=db)
    """
    factory = get_session_factory()
    session = factory.get_current_session()
    if session is None:
        raise RuntimeError("No active database session")
    return session

# Example FastAPI route
from src.services.ingredient import list_ingredients, IngredientFilter
from src.dto import PaginationParams

@app.get("/api/ingredients")
def get_ingredients_endpoint(
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db)
):
    """List ingredients with filtering and pagination."""
    filter_params = IngredientFilter(category=category, search_query=search)
    pagination = PaginationParams(page=page, per_page=per_page)

    result = list_ingredients(
        filter=filter_params,
        pagination=pagination,
        session=db  # Request-scoped session from middleware
    )

    return {
        "items": [IngredientResponse.from_orm(i) for i in result.items],
        "total": result.total,
        "page": result.page,
        "pages": result.pages,
    }
```

**User model for authentication (future):**

```python
# models/user.py
from sqlalchemy import Column, String, Boolean, DateTime
from src.models.base import BaseModel
from src.utils.datetime_utils import utc_now

class User(BaseModel):
    """User model for authentication."""
    __tablename__ = "users"

    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(200), unique=True, nullable=False, index=True)
    hashed_password = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # For multi-tenancy (optional)
    tenant_id = Column(String(36), nullable=True, index=True)

    def __repr__(self):
        return f"<User {self.username}>"

# For single-user desktop app, can have a default user
# For web, integrate with FastAPI Users or similar
```

**Migration path:**

1. **Phase 1: Abstract database layer**
   - Add database type configuration
   - Support PostgreSQL URLs
   - Test with both SQLite and PostgreSQL

2. **Phase 2: Session factory pattern**
   - Implement `SessionFactory`
   - Add request-scoped session support
   - Keep `session_scope()` for backwards compatibility

3. **Phase 3: Authentication preparation**
   - Add `User` model (single default user for desktop)
   - Add authentication middleware (no-op for desktop)
   - Add `user_id` to audit logs

4. **Phase 4: Web API development**
   - FastAPI routes using session factory
   - Request-scoped sessions via middleware
   - Authentication via FastAPI Users

### Refactoring Scope

**Large effort** — requires significant architectural changes:
1. Abstract database URL creation (4 hours)
2. Implement session factory pattern (1-2 days)
3. Test with PostgreSQL (1-2 days)
4. Add User model and authentication prep (2-3 days)
5. Create FastAPI skeleton with middleware (1 week)
6. Migrate services to work with both desktop and web (ongoing)

---

## Implementation Roadmap

### Phase 1: Pre-Migration Foundation (High Priority)

**Goal:** Establish patterns that enable smooth web migration

**Tasks:**
1. **Error Handling Consolidation** (1 week)
   - Create centralized UI error handler
   - Update 88 files to use specific exceptions
   - Standardize user-facing error messages

2. **Configuration Enhancement** (2 days)
   - Add database connection settings to Config
   - Support PostgreSQL connection strings
   - Add feature flags support

3. **API Standardization** (2-3 weeks)
   - Define pagination DTOs
   - Add pagination to all `list_*` functions
   - Standardize exception vs None pattern
   - Create filter objects for complex queries

### Phase 2: Migration Enablers (Medium Priority)

**Goal:** Adapt architecture for web deployment

**Tasks:**
4. **Database Abstraction** (1 week)
   - Implement session factory pattern
   - Test with PostgreSQL
   - Add connection pool monitoring

5. **Transaction Patterns** (1 week)
   - Add savepoint support
   - Document transaction boundaries
   - Audit multi-step operations

6. **Session Management Refactor** (1-2 weeks)
   - Implement request-scoped session support
   - Add middleware pattern
   - Keep backwards compatibility

### Phase 3: Quality & Observability (Lower Priority)

**Goal:** Enhance debugging and maintenance

**Tasks:**
7. **Observability** (2 weeks)
   - Add correlation ID infrastructure
   - Implement audit trail for critical operations
   - Add performance monitoring decorators
   - Standardize logging levels

8. **Validation Framework** (3-4 weeks)
   - Add Pydantic to requirements
   - Create schema definitions
   - Migrate validation logic
   - Update service signatures

### Phase 4: Code Quality (Ongoing)

**Goal:** Incremental improvements

**Tasks:**
9. **Resource Management** (1 week)
   - Add chunked generators for large queries
   - Verify file operation patterns
   - Add graceful shutdown handlers

10. **Code Organization** (2-3 weeks)
    - Add isort and organize imports
    - Split `finished_good_service.py`
    - Remove dead code

---

## Decision Matrix: What to Do First

### Immediate Action Items (Do Now)

1. **Create centralized error handler** (1 day, high impact)
   - Prevents accumulation of more generic exception catches
   - Makes debugging easier immediately

2. **Add database settings to Config** (2 hours, enables future work)
   - Unblocks PostgreSQL testing
   - Low effort, high value

3. **Document transaction boundaries** (1 week, prevents bugs)
   - Add docstrings to multi-step service functions
   - Clarifies expected usage

### Before Web Migration (Must Do)

1. **API standardization** - Required for consistent REST endpoints
2. **Session factory pattern** - Required for request-scoped sessions
3. **Database abstraction** - Required for PostgreSQL support

### After Web Migration (Nice to Have)

1. **Pydantic validation** - Enhances but not required
2. **Audit trail** - Useful for production but can add later
3. **Code organization** - Improves maintainability but not urgent

### Optional Enhancements (Consider Later)

1. **Multi-tenancy support** - Only if building SaaS
2. **Advanced transaction patterns** - Only if needed
3. **Performance monitoring** - Only if performance issues arise

---

## Metrics for Success

### Current State Metrics (Baseline)

- 88 files with generic exception catches
- 0 services with pagination support
- 0 services with audit logging
- ~50% services with session parameter
- 0 automated import organization
- Large service files: 3 over 500 lines

### Target State Metrics (6 Months)

- 0 files with generic exception catches
- 100% of list operations support pagination
- 100% of critical operations have audit logging
- 100% of services accept session parameter
- 100% automated import organization via isort
- No service files over 500 lines (split into packages)

### Migration Readiness Checklist

- [ ] Database abstraction supports PostgreSQL
- [ ] Session factory pattern implemented
- [ ] Request-scoped session middleware working
- [ ] Pagination available for all list endpoints
- [ ] Error handling maps to HTTP status codes
- [ ] Configuration supports environment variables
- [ ] Transaction boundaries documented
- [ ] User model exists (even if single user)

---

## References

### Related Documentation

- `CLAUDE.md` - Session management anti-patterns
- `AGENTS.md` - Project structure and conventions
- `docs/design/schema_v0.6_design.md` - Current schema design
- `src/services/exceptions.py` - Exception hierarchy
- `src/utils/config.py` - Configuration system

### External Resources

- [SQLAlchemy: Session Basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)
- [Pydantic: Data Validation](https://docs.pydantic.dev/)
- [FastAPI: Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [Python Logging: Best Practices](https://docs.python.org/3/howto/logging.html)

---

## Appendix: Quick Reference

### Exception Handling Pattern

```python
# UI Layer
try:
    result = service_function(data)
except ServiceError as e:
    user_msg = handle_service_error(e)
    show_error(user_msg)
except Exception as e:
    logger.exception("Unexpected error")
    show_error("An unexpected error occurred")
```

### Service Function Signature

```python
def service_function(
    data: PydanticModel,
    session: Optional[Session] = None
) -> ReturnType:
    """Docstring with transaction boundary info."""
    def _impl(sess: Session) -> ReturnType:
        # Implementation
        pass

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

### Pagination Pattern

```python
def list_items(
    filter: Optional[FilterModel] = None,
    pagination: Optional[PaginationParams] = None,
    session: Optional[Session] = None
) -> PaginatedResult[Model]:
    """List with filtering and pagination."""
    # ... implementation
```

### Audit Log Pattern

```python
create_audit_log(
    entity_type='model_name',
    entity_id=obj.id,
    entity_slug=obj.slug,
    action='create'|'update'|'delete',
    changed_fields={'field': {'old': x, 'new': y}},
    session=session
)
```

---

**Document Version:** 1.0
**Last Updated:** 2026-02-02
**Next Review:** After Phase 1 completion
