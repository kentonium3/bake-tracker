<!--
Sync Impact Report:
- Version change: 1.6.0 → 1.6.1
- Modified principles: VI (Code Quality & Consistency Disciplines - checklist clarification)
- Changes:
  - Added "Transaction boundary matches implementation (verify Pattern A, B, or C)" to Code Review Checklist
  - Added "Transaction boundary section in docstring" with reference to transaction_patterns_guide.md in New Service Function Checklist
- Based on: F091 Transaction Boundary Documentation (2026-02-03)
- Templates requiring updates:
  ✅ spec-template.md - No changes needed (references constitution dynamically)
  ✅ plan-template.md - No changes needed (Constitution Check gates are generic)
- Follow-up TODOs: None
-->

# Bake Tracker Constitution

## Core Principles

### I. User-Centric Design & Workflow Validation

**The application serves dual purposes: a practical tool for a real user AND a workflow validator for future AI-assisted SaaS evolution.**

#### Immediate User Value
- Features MUST solve actual user problems, not theoretical ones
- UI MUST be intuitive for non-technical users
- Workflows MUST match natural baking planning processes
- User testing with the primary user (wife) MUST validate major features before completion
- Complexity that doesn't serve the user MUST be rejected
- Mobile companion workflows MUST reduce friction for common tasks (shopping, inventory checks)

#### Prototype & Workflow Validation
- Data structures MUST support complete, real-world workflows that can be exercised manually
- Business logic MUST be explicit, testable, and separable from UI for future API/voice/chat wrapping
- Catalog creation workflows (Products, Bundles/Finished Goods, Recipe variations) MUST be fully functional before AI assistance layers are added
- Planning and purchasing workflows MUST be validated with real use before conversational interfaces wrap them

#### AI-Forward Foundation
- Application logic and data models will form RAG/RAGraph foundations for AI-assisted user interactions
- Voice and chat AI interactions for planning, purchasing, and catalog creation depend on proven manual workflows
- The principle "solve it manually first, then add AI" ensures AI assistance enhances rather than obscures validated processes

**Rationale:** This application is both a personal holiday baking tool AND a functional prototype for a multi-user, AI-forward SaaS platform. Features must work flawlessly for the current user while simultaneously validating the workflows, data structures, and business logic that will underpin future voice/chat AI interactions. If a workflow doesn't work well manually, wrapping AI around it will only amplify the friction. Proven manual workflows become the foundation for frictionless conversational experiences.

### II. Data Integrity & FIFO Accuracy (NON-NEGOTIABLE)

**Cost calculations and inventory tracking must be accurate and trustworthy.**

- FIFO (First In, First Out) consumption MUST be enforced for pantry items
- Unit conversions MUST be ingredient-specific where density/volume matters
- Cost calculations MUST reflect actual pantry consumption or preferred variant pricing
- Database migrations MUST preserve all existing data with validation
- Data import/export MUST be lossless and version-controlled

**Rationale:** The user relies on this application for expense tracking and shopping planning. Incorrect costs or lost data breaks trust and renders the application useless. FIFO matches physical reality (using oldest ingredients first) and provides accurate historical costing.

### III. Future-Proof Schema, Present-Simple Implementation

**Database schema supports future enhancements, but only required fields are populated initially.**

- Schema MUST include industry standard fields (FoodOn, GTIN, etc.) as nullable
- Implementation MUST populate only essential fields initially
- Features MUST be added incrementally without schema breaking changes
- User MUST NOT be burdened with unnecessary data entry upfront
- Optional enhancements MUST be clearly documented for future phases

**Rationale:** The schema is designed to support potential commercial product evolution, but the immediate need is a working personal tool. This principle allows the application to grow without disruptive migrations while keeping the MVP simple and usable.

### IV. Test-Driven Development

**Service layer logic must be tested before implementation is considered complete.**

- Unit tests MUST be written for all service layer methods
- Tests MUST cover happy path, edge cases, and error conditions
- Integration tests MUST validate database operations
- Test coverage MUST exceed 70% for services layer
- Failing tests MUST block feature completion

**Rationale:** The application involves complex calculations (FIFO costing, unit conversions, event planning aggregations). Manual testing cannot reliably catch regressions. Automated tests provide confidence during refactoring and feature additions.

### V. Layered Architecture Discipline

**Clear separation between UI, business logic, and data access layers.**

- UI layer (`src/ui/`) MUST NOT contain business logic
- Services layer (`src/services/`) MUST NOT import UI components
- Models layer (`src/models/`) MUST define schema and relationships only
- Cross-layer dependencies MUST flow downward only (UI → Services → Models → Database)
- Each layer MUST have a single, well-defined responsibility

**Rationale:** Layered architecture enables independent testing, easier refactoring, and potential future UI alternatives (web, mobile). Violations create tight coupling and make the codebase unmaintainable.

### VI. Code Quality & Consistency Disciplines

**Consistent code quality disciplines reduce cognitive load, prevent entire categories of bugs, and make the codebase approachable for future contributors (human or AI).**

These standards are particularly important given the dual-purpose nature of this application—code that will evolve into a multi-user SaaS must be robust from the start.

#### A. Error Handling Standards
**Principle**: Errors should be predictable, debuggable, and user-friendly.

1. **Exception Hierarchy** ✨ ENHANCED
   - All domain exceptions MUST inherit from `ServiceError` base class
   - Use domain-specific exceptions: `IngredientNotFoundBySlug`, `InsufficientInventoryError`, `ValidationError`
   - **NEVER catch bare `Exception` in UI layer** — catch `ServiceError` specifically, then generic `Exception` only for logging unexpected errors
   - **Web migration consideration**: Exception hierarchy must map cleanly to HTTP status codes (404, 400, 500)

2. **Error Propagation** ✨ ENHANCED
   - **Three-tier strategy**:
     - Services raise domain exceptions with technical details
     - UI layer uses centralized error handler to convert to user-friendly messages
     - Unexpected exceptions logged with full stack trace
   - Include operation context: entity IDs, slugs, attempted operation, current state
   - **Required in exceptions**: correlation ID (for tracing), entity identifiers, actionable error messages

3. **Validation Strategy** ✨ NEW
   - **Validation location hierarchy**:
     1. Schema validation (type, format) via Pydantic at service boundaries
     2. Business rule validation (FIFO, inventory) in service layer
     3. Database constraints as last resort (integrity only)
   - **NEVER validate in UI layer** beyond basic input sanitization
   - Return validation errors as structured exceptions with field-level details
   - All-or-nothing validation for related fields (e.g., density fields)

**Example patterns:**
```python
# CORRECT: Specific exception handling
try:
    ingredient = create_ingredient(data)
except IngredientNotFoundBySlug as e:
    show_error(f"Ingredient '{e.slug}' not found")
except ValidationError as e:
    show_error(f"Validation failed: {', '.join(e.errors)}")
except ServiceError as e:
    show_error(handle_service_error(e))  # Centralized handler
except Exception as e:
    logger.exception("Unexpected error")
    show_error("An unexpected error occurred. Please contact support.")

# WRONG: Generic exception catch
try:
    ingredient = create_ingredient(data)
except Exception as e:
    print(f"ERROR: {e}")  # ❌ Too generic, hides error types
```

#### B. Configuration & Environment Management
**Principle**: Code should work across environments without modification.

1. **No Hard-Coded Values** ✨ ENHANCED
   - Extend existing `Config` class in `src/utils/config.py` for all settings
   - **Never hard-code**:
     - Database connection params (timeout, pool size)
     - File paths (use Config properties)
     - UI settings (theme, appearance)
     - Feature flags
     - API endpoints (future)
   - Use environment variables with sensible defaults: `os.environ.get("VAR_NAME", "default")`

2. **Settings Pattern** ✨ ENHANCED
   - Centralize in `Config` class with `@property` methods
   - Type-safe configuration values (int, bool, Path, not strings)
   - **Feature flags dictionary** for gradual rollout: `config.feature_flags['enable_audit_trail']`
   - Validate required configuration on startup (fail fast)
   - Support both SQLite and PostgreSQL connection strings

**Example pattern:**
```python
# config.py
class Config:
    @property
    def db_timeout(self) -> int:
        return int(os.environ.get("BAKE_TRACKER_DB_TIMEOUT", "30"))

    @property
    def feature_flags(self) -> Dict[str, bool]:
        return {
            "enable_audit_trail": os.environ.get("ENABLE_AUDIT", "false").lower() == "true",
        }

# Usage
config = get_config()
if config.feature_flags['enable_audit_trail']:
    create_audit_log(...)
```

#### C. Dependency & State Management
**Principle**: Components should be loosely coupled and their lifecycle explicit.

1. **Dependency Injection** ✨ ENHANCED
   - **Session parameter pattern (MANDATORY)**:
     - ALL service functions MUST accept `session: Optional[Session] = None`
     - Enables transactional composition (caller controls transaction boundary)
     - Pattern documented in `CLAUDE.md` — follow it consistently
   - Pass dependencies explicitly; avoid importing services within services
   - Enables testing with mocks; makes dependencies visible

2. **Transaction Boundaries** ✨ ENHANCED
   - **Document transaction scope** in service method docstrings
   - Multi-step operations MUST use single session (pass session parameter)
   - **Savepoint support** for nested transactions with partial rollback capability
   - **Transaction isolation levels** configurable for sensitive operations
   - No silent auto-commits; failures roll back cleanly

3. **Resource Cleanup** ✨ ENHANCED
   - Use context managers (`with` statements) for files, connections, sessions
   - **Chunked generators** for large dataset operations (avoid loading entire tables)
   - Connection pool monitoring via `get_pool_status()` for visibility
   - Explicit graceful shutdown handlers for long-lived resources

**Example patterns:**
```python
# CORRECT: Session parameter pattern
def create_ingredient(
    ingredient_data: IngredientCreate,
    session: Optional[Session] = None
) -> Ingredient:
    """
    Create ingredient.

    Transaction boundary: Single session ensures atomic creation.
    """
    def _impl(sess: Session) -> Ingredient:
        # Implementation
        ingredient = Ingredient(**ingredient_data.dict())
        sess.add(ingredient)
        sess.flush()
        return ingredient

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)

# CORRECT: Multi-step transaction
def record_batch_production(recipe_slug, quantity, session=None):
    """
    Record production and consume inventory atomically.

    Transaction boundary: ALL operations in single session.
    Either production recorded AND inventory consumed, OR entire operation rolled back.
    """
    def _impl(sess):
        production = ProductionRun(...)
        sess.add(production)

        # PASS SESSION - critical for atomicity
        consume_inventory(recipe_slug, quantity, session=sess)
        return production

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)

# WRONG: Multiple session scopes (non-atomic)
def record_batch_production(recipe_slug, quantity):
    with session_scope() as sess:
        production = ProductionRun(...)
        sess.add(production)

    # ❌ New session - if this fails, production still recorded!
    consume_inventory(recipe_slug, quantity)
```

#### D. API Consistency & Contracts
**Principle**: Service interfaces should be predictable and self-documenting.

1. **Method Signatures** ✨ ENHANCED
   - **Consistent return types**:
     - Single object operations: Return ORM object or raise exception
     - List operations: Return `PaginatedResult[T]` (not bare lists)
     - Complex results: Use Pydantic models or dataclasses (not dicts)
     - **NEVER return tuples** for validation results — use exceptions or result objects
   - Type hints REQUIRED for all public methods (parameters and return type)
   - Docstrings REQUIRED documenting: args, returns, raises, transaction boundaries

2. **Null/Optional Handling** ✨ ENHANCED
   - **Standardized pattern**: Raise exception for "not found", NEVER return `None`
     - Use: `raise IngredientNotFoundBySlug(slug)`
     - Don't use: `return None` (caller must check, easy to forget)
   - Use `Optional[T]` only for truly optional results (partial data, nullable fields)
   - **Exception**: Collection filters may return empty list (not None, not exception)

3. **Collection Operations** ✨ ENHANCED
   - **Pagination REQUIRED** for all list operations
     - Use `PaginationParams` dataclass (page, per_page)
     - Return `PaginatedResult[T]` with items, total, page, pages
     - Provide backwards-compatible `get_all_*()` wrappers during migration
   - **Filter objects** for complex queries (not many keyword arguments)
     - Use `IngredientFilter`, `RecipeFilter` dataclasses
     - Compose filters with standard patterns
   - Explicit ordering: `order_by` parameter (don't rely on database defaults)

**Example patterns:**
```python
# CORRECT: Exception for not found
def get_ingredient(slug: str, session: Optional[Session] = None) -> Ingredient:
    """Get ingredient by slug. Raises IngredientNotFoundBySlug if not found."""
    ingredient = sess.query(Ingredient).filter_by(slug=slug).first()
    if not ingredient:
        raise IngredientNotFoundBySlug(slug)  # ✅ Clear error
    return ingredient

# WRONG: Return None
def get_ingredient(slug: str) -> Optional[Ingredient]:
    ingredient = sess.query(Ingredient).filter_by(slug=slug).first()
    return ingredient  # ❌ Caller must remember to check None

# CORRECT: Pagination
def list_ingredients(
    filter: Optional[IngredientFilter] = None,
    pagination: Optional[PaginationParams] = None,
    session: Optional[Session] = None
) -> PaginatedResult[Ingredient]:
    """List ingredients with filtering and pagination."""
    # ... returns PaginatedResult with items, total, page, pages

# WRONG: No pagination
def get_all_ingredients() -> List[Ingredient]:
    return session.query(Ingredient).all()  # ❌ Loads entire table!
```

#### E. Observability & Debugging Support
**Principle**: When things go wrong, diagnosis should be straightforward.

1. **Logging Strategy** ✨ ENHANCED
   - **Structured logging** with severity levels consistently applied:
     - `DEBUG`: Function entry/exit, variable values, SQL queries
     - `INFO`: Successful operations, business events
     - `WARNING`: Slow operations (>threshold), deprecated usage, resource constraints
     - `ERROR`: Validation failures, business rule violations, handled exceptions
     - `CRITICAL`: Database connection failures, config errors, unhandled exceptions
   - **Include operation context**: correlation ID, entity slugs, timing, user intent
   - **Correlation IDs REQUIRED** for all multi-step operations (use context variables)

2. **Audit Trail** ✨ ENHANCED
   - **Required for critical operations**: create, update, delete on core entities
   - Track: correlation ID, entity type/ID/slug, action, changed fields (old/new), timestamp
   - Use `AuditLog` model with `create_audit_log()` service function
   - Immutable audit records (append-only, no updates/deletes)
   - Debug mode: verbose operation logging with full state dumps

3. **Development Tools** ✨ NEW
   - Connection pool status monitoring: `get_pool_status()`
   - Performance tracking: `@track_performance(threshold_ms=500)` decorator
   - Health check endpoints with detailed diagnostics
   - Data export utilities for reproducing issues
   - Clear error messages with actionable remediation (not just "failed")

**Example patterns:**
```python
# Correlation ID usage
from src.services.context import set_correlation_id, get_correlation_id

# At operation start (UI handler, API endpoint)
correlation = set_correlation_id()  # Generates UUID

# In service functions
def update_ingredient(slug, data, session=None):
    correlation = get_correlation_id()
    logger.info(f"[{correlation}] Updating ingredient {slug}")

    # ... operation ...

    # Audit trail
    create_audit_log(
        correlation_id=correlation,
        entity_type='ingredient',
        entity_id=ingredient.id,
        action='update',
        changed_fields={'name': {'old': old_name, 'new': new_name}},
        session=sess
    )

# Performance tracking
@track_performance(threshold_ms=500)
def expensive_operation():
    # Logs warning if exceeds 500ms
    pass
```

#### F. Migration & Evolution Readiness
**Principle**: Today's decisions should ease tomorrow's changes.

1. **Database Abstraction** ✨ ENHANCED
   - **ORM-based queries** over raw SQL (99% of queries)
   - **SQLite-specific features isolated**: Document with `# SQLite-specific` comments
   - **Session factory pattern** for request-scoped sessions (web readiness):
     - Desktop: `session_scope()` context manager (current)
     - Web: `SessionFactory` with request-scoped sessions
   - **Support both SQLite and PostgreSQL** via `Config.database_url` abstraction
   - Connection pooling configuration (size, timeout, recycle) via Config

2. **Authentication/Authorization Hooks** ✨ ENHANCED
   - Service methods SHOULD accept `user_id: Optional[str] = None` parameter (even if unused now)
   - Audit logs include `user_id` field (nullable for desktop, populated for web)
   - Data access patterns consider future row-level security (filter by user)
   - **No global "current user" state** — always passed explicitly

3. **Multi-Tenancy Awareness** ✨ ENHANCED
   - **Future consideration only** (not required now, but be aware):
     - Service methods could be scoped to tenant (via parameter)
     - Schema includes optional `tenant_id` columns (nullable)
     - Avoid global singleton data stores
   - Focus: Design for single-user desktop, but don't block future SaaS

**Example patterns:**
```python
# Database abstraction
class Config:
    @property
    def database_type(self) -> str:
        return os.environ.get("BAKE_TRACKER_DB_TYPE", "sqlite")

    @property
    def database_url(self) -> str:
        if self.database_type == "postgresql":
            return os.environ.get("DATABASE_URL")  # Web
        else:
            return f"sqlite:///{self._database_path}"  # Desktop

# Session factory (web-ready)
class SessionFactory:
    def create_session(self) -> Session:
        """Create request-scoped session (web) or one-off session (desktop)."""
        return self._session_factory()

# User context (future-ready)
def update_ingredient(
    slug: str,
    data: dict,
    user_id: Optional[str] = None,  # ✅ Future-ready
    session: Optional[Session] = None
) -> Ingredient:
    # ... operation ...

    create_audit_log(
        entity_type='ingredient',
        action='update',
        user_id=user_id,  # ✅ Nullable now, populated later
        session=sess
    )
```

#### G. Code Organization Patterns
**Principle**: Related code lives together; boundaries are clear.

1. **Module Size** ✨ ENHANCED
   - **Maximum 500 lines per module** — split into sub-packages if exceeded
   - Large service example: `finished_good_service.py` (1700 lines) → split into:
     - `finished_good/crud.py` (basic CRUD)
     - `finished_good/assembly.py` (assembly logic)
     - `finished_good/search.py` (search/filtering)
     - `finished_good/__init__.py` (public API exports)
   - Flat is better than nested (avoid deep hierarchies)

2. **Import Discipline** ✨ ENHANCED
   - **Enforce with `isort`** (automated import organization)
   - Import order (PEP 8): Standard library → Third-party → Local
   - **No circular imports** (indicates poor separation of concerns)
   - Import from public interfaces: `from src.services.ingredient import create_ingredient`
   - **Never import from internal modules**: `from src.services.ingredient._internal import ...` ❌

3. **Dead Code** ✨ ENHANCED
   - **Zero tolerance**: Remove commented-out code (Git preserves history)
   - Delete unused imports (use `autoflake` or IDE warnings)
   - Delete unused functions/classes (verify with search first)
   - Feature flags over conditional compilation (`#ifdef` style)

**Example pattern:**
```python
# Proper import organization (enforced by isort)

# Standard library
import os
import sys
from datetime import datetime
from typing import Optional, List

# Third-party
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

# Application
from src.models.base import BaseModel
from src.services.database import session_scope
from src.services.exceptions import ValidationError

# Local (relative imports within same package)
from .validation import validate_ingredient_data
from .helpers import slugify
```

#### H. Testing & Validation Support
**Principle**: Code should be written to be testable.

1. **Test Seams** ✨ ENHANCED
   - **Session parameter pattern enables testing**: Mock/in-memory sessions
   - Test public contracts (service functions), not private implementation
   - Services testable without database via mocked sessions
   - **Deterministic behavior**: No `random()`, `time.time()` without injectable clock
   - Fixtures MUST match production scenarios (realistic data)

2. **Sample Data** ✨ ENHANCED
   - **Factory patterns** for test data generation (not manual construction)
   - Realistic test fixtures in `tests/fixtures/` matching production scenarios
   - **Separation**: Test data (tests/) vs seed data (migrations/)
   - Test data includes edge cases: empty lists, boundary values, nullable fields

**Example pattern:**
```python
# Testable service (session parameter)
def create_ingredient(data, session=None):
    def _impl(sess):
        ingredient = Ingredient(**data)
        sess.add(ingredient)
        sess.flush()
        return ingredient

    if session is not None:
        return _impl(session)  # ✅ Test can pass mock session
    with session_scope() as sess:
        return _impl(sess)

# Test with mock session
def test_create_ingredient():
    mock_session = MagicMock()
    result = create_ingredient(data, session=mock_session)
    mock_session.add.assert_called_once()
```

#### I. Data Validation Framework ✨ NEW SECTION
**Principle**: Schema validation should be type-safe, reusable, and automatic.

1. **Pydantic for Schema Validation**
   - Use Pydantic models for service input/output validation
   - Replaces manual dictionary validation in `validators.py`
   - Enables automatic FastAPI schema generation (web migration)
   - Type-safe data transfer objects (DTOs)

2. **Validation Layers**
   - **Schema layer**: Pydantic models validate type, format, required fields
   - **Business layer**: Service functions validate business rules (FIFO, inventory)
   - **Database layer**: Constraints ensure data integrity only

3. **Validation Result Patterns**
   - Pydantic raises `ValidationError` automatically (catch and convert to domain exception)
   - Service functions raise domain exceptions (`InsufficientInventoryError`)
   - **NEVER return `(bool, List[str])` tuples** — use exceptions

**Example pattern:**
```python
# Schema validation
from pydantic import BaseModel, Field, validator

class IngredientCreate(BaseModel):
    display_name: str = Field(..., max_length=200, min_length=1)
    category: str = Field(..., max_length=100)

    @validator('category')
    def validate_category(cls, v):
        allowed = ['baking', 'dairy', 'produce']
        if v not in allowed:
            raise ValueError(f"Category must be one of {allowed}")
        return v

    class Config:
        str_strip_whitespace = True

# Service function
def create_ingredient(
    ingredient_data: IngredientCreate,  # ✅ Pydantic validates automatically
    session: Optional[Session] = None
) -> Ingredient:
    """Create ingredient. Pydantic handles schema validation."""
    ingredient = Ingredient(**ingredient_data.dict())
    # ... business logic validation ...
    return ingredient

# FastAPI usage (future)
@app.post("/ingredients", response_model=IngredientResponse)
def create_ingredient_endpoint(ingredient: IngredientCreate):
    return create_ingredient(ingredient)  # ✅ Schema generated automatically
```

#### Compliance & Refactoring

##### Enforcement Levels

1. **MUST (Required)**
   - New features MUST follow all disciplines marked "REQUIRED"
   - AI agents MUST reject code violating REQUIRED patterns
   - Examples: No bare `Exception` catches, session parameter pattern, pagination

2. **SHOULD (Recommended)**
   - New features SHOULD follow recommended patterns
   - Exceptions allowed with documented rationale
   - Examples: User context parameters, chunked generators

3. **MAY (Optional)**
   - Future-proofing patterns that don't block current work
   - Examples: Multi-tenancy awareness, tenant_id columns

##### Refactoring Strategy

1. **New Code**
   - MUST follow all disciplines (no exceptions)
   - Sets pattern for incremental codebase improvement

2. **Existing Code**
   - SHOULD be refactored opportunistically when touched
   - Boy Scout Rule: Leave code better than you found it
   - Fix discipline violations in modified files

3. **Major Refactoring**
   - Requires specification if >2 days effort
   - Use spec-kitty workflow: specify → plan → tasks → implement
   - Examples: Splitting large service files, adding pagination everywhere

4. **AI Agent Responsibilities**
   - MUST highlight discipline violations in code review
   - MUST suggest refactoring approach
   - MUST document technical debt if not immediately fixable

##### Migration from Current State

**Current gaps identified (2026-02-02):**
- 88 files with generic `Exception` catches → Refactor incrementally
- 0 services with pagination → Add to new services first, retrofit incrementally
- ~50% services missing session parameter → Retrofit as services are modified
- Large service files (3 over 500 lines) → Split opportunistically

**Priority:**
1. High: Error handling, session parameters (blocks web migration)
2. Medium: Pagination, audit trails (improves quality)
3. Low: Code organization, dead code removal (incremental improvement)

#### Appendix: Quick Reference Checklists

##### New Service Function Checklist

- [ ] Docstring with args, returns, raises, transaction boundaries
- [ ] **Transaction boundary section in docstring** (Pattern A, B, or C per `docs/design/transaction_patterns_guide.md`)
- [ ] Type hints for all parameters and return type
- [ ] Pydantic model for input validation (if accepting complex data)
- [ ] `session: Optional[Session] = None` parameter
- [ ] Session parameter pattern: `if session is not None:` / `else: with session_scope():`
- [ ] Raise domain exceptions (not return None or tuples)
- [ ] Include correlation ID in logging: `logger.info(f"[{get_correlation_id()}] ...")`
- [ ] Audit trail for create/update/delete operations
- [ ] No bare `Exception` catches
- [ ] No hard-coded configuration values

##### New List Operation Checklist

- [ ] Accepts `filter: Optional[FilterClass] = None`
- [ ] Accepts `pagination: Optional[PaginationParams] = None`
- [ ] Accepts `session: Optional[Session] = None`
- [ ] Returns `PaginatedResult[Model]` (not bare list)
- [ ] Explicit ordering (not database-dependent)
- [ ] Type hints for all parameters and return type

##### New Model Checklist

- [ ] Inherits from `BaseModel` (provides created_at, updated_at, UUID)
- [ ] Includes optional `tenant_id` if multi-tenancy considered (nullable)
- [ ] Validation logic in Pydantic schema (not model class)
- [ ] Relationships use `back_populates` for bidirectional navigation

##### Code Review Checklist (AI Agents)

- [ ] No generic `Exception` catches (use specific exceptions)
- [ ] No hard-coded values (use Config)
- [ ] No missing session parameters on service functions
- [ ] No multi-step operations without transaction documentation
- [ ] Transaction boundary matches implementation (verify Pattern A, B, or C)
- [ ] No list operations without pagination
- [ ] No functions returning None for "not found" (raise exception)
- [ ] No commented-out code
- [ ] No circular imports
- [ ] No modules >500 lines (recommend split)
- [ ] All public functions have docstrings and type hints

**Rationale:** Consistent code quality disciplines reduce cognitive load, prevent entire categories of bugs, and make the codebase approachable for future contributors (human or AI). These standards are particularly important given the dual-purpose nature of this application—code that will evolve into a multi-user SaaS must be robust from the start.

### VII. Schema Change Strategy (Desktop Phase)

**For single-user desktop apps, database migrations are unnecessary complexity.**

**Desktop Phase (Current):**
- Schema changes handled via export → reset → import cycle
- Export ALL data to JSON before schema change
- Delete database, update models, recreate empty database
- Programmatically transform JSON to match new schema if needed
- Import transformed data to restored database
- No migration scripts required or maintained

**Web Phase (Future):**
- Re-evaluate migration strategy when multi-user is implemented
- Consider Alembic or similar migration tooling
- Document migration requirements in web phase constitution amendment

**Rationale:** For a single-user desktop application with robust import/export capability, the export/reset/import cycle is simpler, more reliable, and eliminates an entire category of migration-related bugs. Migration tooling becomes necessary only when multiple users have independent databases that must be upgraded in place.

### VIII. Pragmatic Aspiration

**Build for today's user while keeping tomorrow's platform in mind.**

#### Current Phase: Event-Centric Generalization (Q1-Q2 2025)
- **Shift from holiday baking to event baking** - Christmas is one of many event types
- **Shift from packaging to flexible output** - Support quantity goals, serving goals, or package goals
- **Single desktop user** validating workflows for family/friends
- **Manual + AI-assisted data entry** proving friction reduction is achievable
- **English-only** interface for non-technical user

#### Near-Term: Web Application (Q3-Q4 2025)
**Hobby-scale web app for 2025 holiday baking season**

Target: 10-15 users (family, friends, neighbors) using the web version for holiday 2025.

**Technical Goals:**
- **Architecture:** Desktop → Web migration (API design, state management, session handling)
- **Data Design:** Single-user → Multi-user schema (tenant isolation, data privacy)
- **UI Design:** Desktop native → Responsive web (browser compatibility, mobile-friendly)
- **Deployment:** Cloud hosting basics (containerization, CI/CD)
- **Security:** Authentication, authorization, HTTPS

**Scope Constraints:**
- Still **hobby tool scale** (10-15 users max)
- Now **event-focused** (not just baking - any food production event)
- Still **English-only**
- **AI-assisted data entry** validated and integrated

#### Full Platform Vision (2026+)
After validating web deployment and multi-user patterns:

**Platform Expansion:**
- **Any food type** (BBQ, catering, meal prep, weekly planning)
- **Any event type** (weddings, festivals, meal prep, restaurant prep)
- **Multi-language** support with full internationalization
- **Output flexibility** (packages, servings, quantities, catering orders)
- **Scalable infrastructure** for broader user base

**Intelligence & Enhancement:**
- AI-powered menu generation and optimization
- Fluid voice and chat interactions for planning and purchasing
- Nutritional analysis and dietary accommodation
- Recipe scaling and cost optimization
- Smart inventory predictions

#### AI-Assisted Data Entry: Proof of Concept

**The Core Insight:** Data entry friction causes most apps and spreadsheets in this space to fail. AI assistance can overcome this friction IF the underlying structure and workflows are sound.

**Proof-of-Concept Goals (Current Phase):**
- Demonstrate mobile AI-assisted user input for purchasing and inventory updates
- Validate with slow, batch, semi-automated JSON file creation and ingestion
- Show that fluid voice/chat interactions are achievable even if current implementation is clunky
- Prove the workflow structure supports AI wrapping before investing in real-time interfaces

**Current Integrations:**
- **BT Mobile Purchase Scanning:**
  - Gemini photo processing of barcodes, package images, and price tags
  - Results in JSON upload files merged via import service into Purchasing tables

- **BT Mobile Inventory Updates:**
  - Gemini image processing of products
  - Voice or text input for percentage remaining
  - Results in JSON upload files merged via import service into Inventory tables

**Success Criteria:** If AI can create valid JSON that imports cleanly, real-time voice/chat is just an interface layer away.

#### Decision Framework

When making architectural choices, ask:

1. **Does this choice block web deployment (Q3 2025)?**
   - If YES → Find alternative that supports web migration
   - If NO → Proceed with simplest desktop implementation

2. **What's the migration cost for desktop → web?**
   - **High cost** (tightly coupled to desktop UI, local file assumptions) → Reconsider
   - **Medium cost** (clean service layer, just needs API wrapper) → Acceptable
   - **Low cost** (already stateless, testable) → Ideal

3. **Does this support AI-assisted data entry?**
   - If YES with minimal added complexity → Implement now
   - If YES but requires major refactoring → Document for near-term

4. **What's the cost of changing this decision later?**
   - **High cost** (database schema, core abstractions) → Invest extra care now
   - **Low cost** (UI layout, file formats) → Optimize for immediate needs

#### Examples of Pragmatic Aspiration in Practice

**Good Opportunistic Choices:**

- **BT Mobile purchase scanning with Gemini image processing**
  - *Desktop: Proves AI-assisted workflow; reduces data entry friction*
  - *Web: Same JSON import; mobile-first validated*
  - *Platform: Foundation for real-time voice/chat purchasing*

- **BT Mobile inventory updates with percentage input**
  - *Desktop: Validates FIFO + percentage calculation logic*
  - *Web: Same service layer; API-ready*
  - *Platform: Voice command "flour is half empty" → automatic adjustment*

- **Slug-based foreign keys instead of display names**
  - *Desktop: Clean references*
  - *Web: Enables future localization without breaking references*
  - *Platform: Multi-language ready*

- **Service layer separated from UI layer**
  - *Desktop: Easier testing*
  - *Web: Services become API endpoints with minimal refactoring*
  - *Platform: Mobile app and voice assistant use same API*

- **Import/Export v4.0 with atomic rollback**
  - *Desktop: Reliable data operations*
  - *Web: Same guarantees for multi-user*
  - *Platform: Foundation for real-time sync*

**Premature Optimization to Avoid:**

- Building real-time voice interface before batch JSON proves workflow
  - *Validate structure first; polish interface later*

- Implementing OAuth/SSO before web deployment
  - *Desktop doesn't need it; web phase determines auth strategy*

- Designing for 1000+ users before 15 users validated
  - *Prove hobby scale works; then scale*

- Building native mobile app before web + PWA validated
  - *BT Mobile JSON export proves the workflow; native can come later*

**Document for Later:**
- Maintain `/docs/web_migration_notes.md` - decisions that impact web transition
- Track "Web Migration Cost" in complexity justifications
- Note where desktop implementation makes web-hostile assumptions

#### Phase-Specific Constitution Checks

**Desktop Phase (Now - Q2 2025):**
- Does this design block web deployment? → Must be NO or have documented path
- Is the service layer UI-independent? → Must be YES
- Does this support AI-assisted JSON import? → Should be YES
- What's the web migration cost? → Must be documented

**Web Phase (Q3-Q4 2025):**
- Does this assume single-tenant database? → Should be NO
- Does this expose user data to other users? → Must be NO
- Can this scale to 15 users? → Must be YES
- What security vulnerabilities exist? → Must be assessed
- Is AI-assisted input working? → Must be validated

**Platform Phase (2026+):**
- Does this assume baking domain? → Should be NO
- Does this assume English? → Should be NO
- Can this scale to 100+ users? → Validate first
- Is real-time voice/chat feasible? → Must have proof-of-concept

**Rationale:** The 2025 holiday baking season is complete. Focus shifts to event-centric generalization and proving AI-assisted data entry reduces friction. The web app must be ready for 10-15 users by holiday 2025. Current development pace may accelerate these timelines. The key insight: if batch JSON import works with AI assistance, real-time voice/chat is achievable.

## Technology Stack Constraints

**Fixed technology choices for consistency and compatibility.**

- **Language:** Python 3.10+ (minimum version for type hints and syntax features)
- **UI Framework:** CustomTkinter (modern appearance, cross-platform, desktop-native)
- **Database:** SQLite with WAL mode (portable, no server, excellent Python integration)
- **ORM:** SQLAlchemy 2.x (type safety, relationship management, migration support)
- **Testing:** pytest (de facto standard for Python, excellent fixtures and plugins)
- **Packaging:** PyInstaller (single executable for Windows distribution)

**Rationale:** These technologies are mature, well-documented, and meet the requirements for a desktop application. Changes require strong justification (e.g., fundamental limitation discovered) and full migration plan.

## Development Workflow

**Spec-Kitty driven development with documentation-first approach.**

- Feature specifications MUST be created in `kitty-specs/` before implementation
- Implementation plans MUST define technical approach and complexity justifications
- Tasks MUST be tracked in `kitty-specs/<feature>/tasks/` directory with lane status in frontmatter
- Documentation MUST be updated before feature is marked complete
- Git commits MUST reference feature numbers and follow conventional commit format

**Workflow Steps:**
1. `/spec-kitty.specify` - Create feature specification with user stories
2. `/spec-kitty.plan` - Research and plan technical implementation
3. `/spec-kitty.tasks` - Generate atomic, testable task prompts
4. `/spec-kitty.implement` - Execute tasks with TDD approach
5. `/spec-kitty.review` - Validate implementation against acceptance criteria
6. `/spec-kitty.accept` - Run full acceptance checks and user testing
7. `/spec-kitty.merge` - Merge feature branch and cleanup

**Rationale:** Spec-Kitty enforces a disciplined approach that prevents scope creep, ensures testability, and maintains comprehensive documentation. The workflow matches software engineering best practices while providing AI-assisted automation.

## Governance

**The constitution guides all development decisions and must be respected.**

### Amendment Process

- Constitution amendments MUST be proposed with clear rationale
- Version MUST be incremented according to semantic versioning:
  - **MAJOR:** Backward incompatible principle removals or redefinitions
  - **MINOR:** New principles added or material guidance expansions
  - **PATCH:** Clarifications, wording improvements, typo fixes
- Sync Impact Report MUST be generated showing affected templates
- All dependent templates and documentation MUST be updated

### Compliance Review

- Feature plans MUST pass Constitution Check gate before implementation
- Principle violations MUST be explicitly justified in Complexity Tracking table
- "Simpler alternative rejected because" MUST be documented for violations
- Unjustified complexity MUST be rejected and simplified

### Living Documentation

- This constitution supersedes ad-hoc decisions and undocumented practices
- Questions about architecture or approach MUST consult constitution first
- Conflicts between constitution and existing code MUST be resolved in favor of constitution
- Runtime guidance for AI agents found in `.kittify/AGENTS.md`

**Version**: 1.6.1 | **Ratified**: 2025-11-08 | **Last Amended**: 2026-02-03
