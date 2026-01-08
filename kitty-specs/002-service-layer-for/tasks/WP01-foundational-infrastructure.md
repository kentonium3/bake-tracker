---
work_package_id: WP01
title: Foundational Infrastructure
lane: done
history:
- timestamp: '2025-11-09T03:08:51Z'
  lane: planned
  agent: system
  shell_pid: '4504'
  action: Prompt generated via /spec-kitty.tasks
- timestamp: '2025-11-09T07:58:47Z'
  lane: done
  agent: Claude Code
  shell_pid: '4504'
  action: Work package completed - all tasks implemented and integration tests passing
agent: Claude Code
assignee: Claude Code
phase: Phase 1 - Infrastructure Setup
shell_pid: '4504'
subtasks:
- T001
- T002
- T003
- T004
- T005
---

# Work Package Prompt: WP01 – Foundational Infrastructure

## Objectives & Success Criteria

Establish shared utilities, exceptions, and database infrastructure required by all service layer functions. This work package must complete before any service implementation can begin.

**Success Criteria**:
- All infrastructure modules importable without errors
- `session_scope()` can execute basic database queries with automatic commit/rollback
- Slug generation produces correct, URL-safe identifiers with uniqueness guarantees
- Validation utilities can check ingredient and variant data structures
- Service package structure established with proper `__init__.py` exports

## Context & Constraints

**Supporting Specs**:
- `.kittify/memory/constitution.md` - Principle III (Separation of Concerns), VII (Pragmatic Aspiration)
- `kitty-specs/002-service-layer-for/plan.md` - Technical stack, database strategy
- `kitty-specs/002-service-layer-for/research.md` - Decisions on slug generation, Decimal precision
- `kitty-specs/002-service-layer-for/data-model.md` - Entity definitions, validation rules

**Key Constraints**:
- Services MUST NOT import from `src/ui/` (enforce separation)
- All monetary values use Python Decimal (no floats)
- Slug generation MUST be deterministic and reversible
- Transaction management MUST be handled via context manager (no manual commit/rollback)

**Existing Code**:
- `src/models.py` - Existing ORM models (Ingredient, Variant, PantryItem, Purchase)
- `src/database.py` - Database initialization (may need session factory extraction)
- `src/utils/unit_converter.py` - Unit conversion logic (reference for validation)

## Subtasks & Detailed Guidance

### Subtask T001 – Create service exceptions module

**Purpose**: Centralize all service layer exception classes for consistent error handling across services.

**Steps**:
1. Create `src/services/exceptions.py`
2. Define base exception: `ServiceError(Exception)`
3. Define entity-not-found exceptions (all inherit from `ServiceError`):
   - `IngredientNotFoundBySlug(ServiceError)` - includes slug in message
   - `VariantNotFound(ServiceError)` - includes variant_id in message
   - `PantryItemNotFound(ServiceError)` - includes pantry_item_id in message
   - `PurchaseNotFound(ServiceError)` - includes purchase_id in message
4. Define constraint violation exceptions:
   - `SlugAlreadyExists(ServiceError)` - includes slug in message
   - `IngredientInUse(ServiceError)` - includes dependency details
   - `VariantInUse(ServiceError)` - includes dependency details
5. Define validation exception:
   - `ValidationError(ServiceError)` - includes error_details in message
6. Define database exception:
   - `DatabaseError(ServiceError)` - wraps SQLAlchemy exceptions

**Files**:
- Create: `src/services/exceptions.py`

**Implementation Notes**:
```python
class ServiceError(Exception):
    """Base exception for all service layer errors."""
    pass

class IngredientNotFoundBySlug(ServiceError):
    """Raised when ingredient slug doesn't exist."""
    def __init__(self, slug: str):
        super().__init__(f"Ingredient '{slug}' not found")
        self.slug = slug

# ... similar pattern for other exceptions
```

**Parallel?**: No - other infrastructure tasks depend on these exceptions being defined.

---

### Subtask T002 – Create database session_scope() context manager

**Purpose**: Provide automatic transaction management for all service functions (commit on success, rollback on error).

**Steps**:
1. Create `src/services/database.py`
2. Import `sessionmaker` and `Session` from SQLAlchemy
3. Import or create database engine (may need to extract from existing `src/database.py`)
4. Create `SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)`
5. Implement `session_scope()` context manager:
   - Yields a session
   - Commits on successful exit
   - Rolls back on exception
   - Always closes the session
6. Add docstring with usage example

**Files**:
- Create: `src/services/database.py`
- May read: `src/database.py` (to extract engine)

**Implementation Notes**:
```python
from contextlib import contextmanager
from sqlalchemy.orm import Session, sessionmaker
from src.database import engine  # Or create here

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def session_scope():
    """Provide a transactional scope around database operations.

    Usage:
        with session_scope() as session:
            ingredient = session.query(Ingredient).filter_by(slug="flour").first()
            session.add(new_variant)
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

**Parallel?**: Yes - can proceed in parallel with T003, T004 after T001 completes.

---

### Subtask T003 – Create slug generation utility

**Purpose**: Generate deterministic, URL-safe slugs from ingredient names with uniqueness guarantees.

**Steps**:
1. Create `src/utils/slug_utils.py`
2. Import `unicodedata`, `re`, `Optional`, `Session`
3. Implement `create_slug(name: str, session: Optional[Session] = None) -> str`:
   - Normalize Unicode to NFD (decompose accents)
   - Encode to ASCII, ignoring non-ASCII characters
   - Convert to lowercase
   - Replace whitespace and hyphens with underscores
   - Remove all non-alphanumeric characters except underscores
   - Collapse multiple underscores to single
   - Strip leading/trailing underscores
   - If `session` provided, check uniqueness against `Ingredient` table
   - If slug exists, append `_1`, `_2`, etc. until unique
4. Add comprehensive docstring with examples
5. Import `Ingredient` model for uniqueness check

**Files**:
- Create: `src/utils/slug_utils.py`

**Implementation Notes**:
```python
import unicodedata
import re
from typing import Optional
from sqlalchemy.orm import Session
from src.models import Ingredient

def create_slug(name: str, session: Optional[Session] = None) -> str:
    """Generate URL-safe slug from ingredient name.

    Examples:
        >>> create_slug("All-Purpose Flour")
        'all_purpose_flour'
        >>> create_slug("Confectioner's Sugar")
        'confectioners_sugar'
    """
    # Unicode normalization
    normalized = unicodedata.normalize('NFD', name)
    slug = normalized.encode('ascii', 'ignore').decode('ascii')

    # Cleaning
    slug = slug.lower()
    slug = re.sub(r'[\s\-]+', '_', slug)  # Spaces/hyphens → underscores
    slug = re.sub(r'[^a-z0-9_]', '', slug)  # Remove non-alphanumeric
    slug = re.sub(r'_+', '_', slug)  # Collapse underscores
    slug = slug.strip('_')

    # Uniqueness check
    if session:
        original_slug = slug
        counter = 1
        while session.query(Ingredient).filter_by(slug=slug).first():
            slug = f"{original_slug}_{counter}"
            counter += 1

    return slug
```

**Parallel?**: Yes - can proceed in parallel with T002, T004 after T001 completes.

**Notes**: Research decision documented in `research.md` - custom implementation preferred over library dependency.

---

### Subtask T004 – Create validation utilities

**Purpose**: Centralize validation logic for ingredient and variant data structures.

**Steps**:
1. Create `src/utils/validators.py`
2. Import `Dict`, `Any`, `Decimal` from typing/decimal
3. Import service exceptions from `src/services/exceptions`
4. Implement `validate_ingredient_data(data: Dict[str, Any]) -> None`:
   - Check required fields: name, category, recipe_unit
   - Validate recipe_unit is in valid units (reference `unit_converter.py`)
   - If density_g_per_ml provided, check > 0
   - Raise `ValidationError` with specific message if invalid
5. Implement `validate_variant_data(data: Dict[str, Any], ingredient_slug: str) -> None`:
   - Check required fields: brand, purchase_unit, purchase_quantity
   - Validate purchase_quantity > 0
   - Validate purchase_unit is in valid units
   - If UPC provided, validate format (12-14 digit string)
   - Raise `ValidationError` with specific message if invalid
6. Add docstrings with examples

**Files**:
- Create: `src/utils/validators.py`
- Read: `src/utils/unit_converter.py` (to get valid units)

**Implementation Notes**:
```python
from typing import Dict, Any
from decimal import Decimal
from src.services.exceptions import ValidationError
# from src.utils.unit_converter import VALID_UNITS  # Depends on unit_converter structure

def validate_ingredient_data(data: Dict[str, Any]) -> None:
    """Validate ingredient data before database operations.

    Raises:
        ValidationError: If required fields missing or invalid
    """
    required = ['name', 'category', 'recipe_unit']
    missing = [f for f in required if f not in data or not data[f]]
    if missing:
        raise ValidationError(f"Missing required fields: {', '.join(missing)}")

    # Validate recipe_unit (check against unit_converter.py)
    # Validate density_g_per_ml > 0 if provided
    # etc.

def validate_variant_data(data: Dict[str, Any], ingredient_slug: str) -> None:
    """Validate variant data before database operations."""
    # Similar pattern
```

**Parallel?**: Yes - can proceed in parallel with T002, T003 after T001 completes.

---

### Subtask T005 – Setup service layer package structure

**Purpose**: Create the `src/services/` package with proper exports for clean imports.

**Steps**:
1. Create `src/services/__init__.py`
2. Import and re-export all exception classes from `exceptions.py`
3. Import and re-export `session_scope` from `database.py`
4. Add module docstring explaining service layer architecture
5. Optionally add `__all__` list for explicit exports

**Files**:
- Create: `src/services/__init__.py`

**Implementation Notes**:
```python
"""Service layer for Bake Tracker application.

This package contains business logic separated from UI and database concerns.
All services use functional patterns with explicit session management.

Architecture:
- Services: Stateless functions organized by domain (ingredient, variant, pantry, purchase)
- Transactions: Managed via session_scope() context manager
- Exceptions: Consistent error handling via ServiceError hierarchy
- Validation: Input validation before database operations
"""

from src.services.exceptions import (
    ServiceError,
    IngredientNotFoundBySlug,
    VariantNotFound,
    PantryItemNotFound,
    PurchaseNotFound,
    SlugAlreadyExists,
    IngredientInUse,
    VariantInUse,
    ValidationError,
    DatabaseError,
)

from src.services.database import session_scope

__all__ = [
    'ServiceError',
    'IngredientNotFoundBySlug',
    # ... all exceptions
    'session_scope',
]
```

**Parallel?**: No - depends on T001, T002 completing.

## Test Strategy

**Infrastructure Testing** (optional for this package, but recommended):
- Create `src/tests/test_session_scope.py`:
  - Test successful commit on normal exit
  - Test rollback on exception
  - Test session closure in all cases
- Create `src/tests/test_slug_utils.py`:
  - Test basic slug generation ("All-Purpose Flour" → "all_purpose_flour")
  - Test Unicode handling ("Jalapeño" → "jalapeno")
  - Test special characters ("Confectioner's Sugar" → "confectioners_sugar")
  - Test uniqueness auto-increment (with mock session)
- Create `src/tests/test_validators.py`:
  - Test validation errors for missing fields
  - Test validation errors for invalid values
  - Test successful validation

**Run tests**: `pytest src/tests/test_session_scope.py src/tests/test_slug_utils.py src/tests/test_validators.py -v`

## Risks & Mitigations

**Risk**: Decimal precision errors in validators
- **Mitigation**: Use `Decimal` type hints, no float conversions

**Risk**: Slug generation collisions under concurrent creation
- **Mitigation**: Database UNIQUE constraint + auto-increment suffix, transaction isolation

**Risk**: session_scope() not closing on exceptions
- **Mitigation**: Use try-finally block, comprehensive exception testing

**Risk**: Import circular dependencies (services → models → services)
- **Mitigation**: Models never import services, services import models freely

## Definition of Done Checklist

- [x] All 5 subtasks completed and code working
- [x] `src/services/exceptions.py` defines all 9 exception classes
- [x] `src/services/database.py` provides session_scope() context manager
- [x] `src/utils/slug_utils.py` generates correct slugs with uniqueness check
- [x] `src/utils/validators.py` validates ingredient and variant data
- [x] `src/services/__init__.py` exports all infrastructure components
- [x] All modules have docstrings and type hints
- [x] Infrastructure tests pass (if written)
- [x] No import errors when importing `src.services`

## Review Guidance

**Acceptance checkpoints**:
1. Import `from src.services import session_scope, ValidationError` succeeds
2. session_scope() can execute a simple query and commit
3. Slug generation handles Unicode and special characters correctly
4. Validators raise appropriate exceptions for invalid data
5. Code follows Python conventions (PEP 8, type hints, docstrings)

**Context for reviewers**:
- This is foundational work - all subsequent services depend on it
- Functional pattern (not classes) chosen for consistency with existing codebase
- No UI dependencies (enforce separation of concerns)

## Activity Log

- 2025-11-09T03:08:51Z – system – lane=planned – Prompt created.
- 2025-11-09T08:02:39Z – Claude Code – lane=done – Work package completed. All tasks implemented and integration tests passing.


---

### Updating Metadata When Changing Lanes

1. Capture your shell PID: `echo $$` (or use helper scripts when available).
2. Update frontmatter (`lane`, `assignee`, `agent`, `shell_pid`).
3. Add an entry to the **Activity Log** describing the transition.
4. Run `.kittify/scripts/powershell/tasks-move-to-lane.ps1 002-service-layer-for WP01 <lane>` to move the prompt, update metadata, and append history in one step.
5. Commit or stage the change, preserving history.
