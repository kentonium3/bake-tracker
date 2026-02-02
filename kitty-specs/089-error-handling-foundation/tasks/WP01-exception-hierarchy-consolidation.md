---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
title: "Exception Hierarchy Consolidation"
phase: "Phase 1 - Foundation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-02-02T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Exception Hierarchy Consolidation

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP01
```

No dependencies - this is the starting work package.

---

## Objectives & Success Criteria

**Objective**: Consolidate the exception hierarchy under a single `ServiceError` base class with correlation_id support and HTTP status code mapping for web migration readiness.

**Success Criteria**:
- [ ] `ServiceError` base class has `correlation_id` parameter and `http_status_code` class attribute
- [ ] All exceptions in `src/services/exceptions.py` inherit from `ServiceError`
- [ ] `ServiceException` is deprecated with warning
- [ ] Duplicate `MaterialInventoryItemNotFoundError` removed
- [ ] All exceptions have comprehensive docstrings

---

## Context & Constraints

**Reference Documents**:
- Constitution: `.kittify/memory/constitution.md` (Section VI.A - Error Handling Standards)
- Plan: `kitty-specs/089-error-handling-foundation/plan.md`
- Data Model: `kitty-specs/089-error-handling-foundation/data-model.md`
- Research: `kitty-specs/089-error-handling-foundation/research.md`

**Current State** (from research.md):
- Two base classes exist: `ServiceException` (legacy) and `ServiceError` (new)
- Legacy exceptions: `IngredientNotFound`, `RecipeNotFound`, `IngredientInUse`, `ValidationError`, `InsufficientStock`, `DatabaseError`, `HierarchyValidationError`
- `MaterialInventoryItemNotFoundError` is defined twice (lines 176 & 261)

**Constraints**:
- Do NOT change exception import paths (UI files still import from `src.services.exceptions`)
- Maintain backward compatibility - existing code catching these exceptions must still work
- Do NOT relocate service-local exceptions (handled in WP02)

---

## Subtasks & Detailed Guidance

### Subtask T001 – Update ServiceError Base Class

**Purpose**: Add correlation_id support and http_status_code attribute to enable tracing and web migration.

**Steps**:
1. Open `src/services/exceptions.py`
2. Update `ServiceError` class:

```python
from typing import Optional, Any, Dict

class ServiceError(Exception):
    """Base exception for all service layer errors.

    All service-specific exceptions should inherit from this class.
    Provides correlation_id for tracing and http_status_code for web migration.

    Attributes:
        message: Human-readable error message
        correlation_id: Optional correlation ID for tracing (future use)
        http_status_code: HTTP status code for web migration (default 500)
        context: Additional structured context data

    Example:
        >>> raise ServiceError("Operation failed", correlation_id="abc-123")
    """

    http_status_code: int = 500  # Default for generic service errors

    def __init__(
        self,
        message: str = "",
        correlation_id: Optional[str] = None,
        **context: Any
    ):
        self.message = message if message else str(self.args[0]) if self.args else ""
        self.correlation_id = correlation_id
        self.context: Dict[str, Any] = context
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Return exception as dictionary for logging/serialization."""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "correlation_id": self.correlation_id,
            "http_status_code": self.http_status_code,
            "context": self.context,
        }
```

3. Add required imports at top of file: `from typing import Optional, Any, Dict`

**Files**: `src/services/exceptions.py`
**Parallel?**: No - must complete before T002-T006

**Notes**:
- The `message` parameter handling allows both `ServiceError("msg")` and keyword args
- `**context` enables structured data like `ServiceError("fail", entity_id=123)`

---

### Subtask T002 – Create Category Base Classes (Optional)

**Purpose**: Create intermediate base classes for cleaner HTTP status code mapping. These are OPTIONAL but recommended.

**Steps**:
1. Add category base classes after `ServiceError`:

```python
class NotFoundError(ServiceError):
    """Base for all not-found exceptions. Maps to HTTP 404."""
    http_status_code = 404


class ValidationError(ServiceError):
    """Base for all validation exceptions. Maps to HTTP 400.

    Attributes:
        errors: List of validation error messages
    """
    http_status_code = 400

    def __init__(self, errors: list, correlation_id: Optional[str] = None):
        self.errors = errors
        error_msg = "; ".join(errors)
        super().__init__(f"Validation failed: {error_msg}", correlation_id=correlation_id)


class ConflictError(ServiceError):
    """Base for all conflict exceptions (in use, duplicate, state). Maps to HTTP 409."""
    http_status_code = 409


class BusinessRuleError(ServiceError):
    """Base for business rule violations (insufficient resources). Maps to HTTP 422."""
    http_status_code = 422
```

2. Note: The existing `ValidationError` will be updated in T003 to use this pattern

**Files**: `src/services/exceptions.py`
**Parallel?**: Yes - can run after T001

**Notes**:
- Category bases are optional but make HTTP mapping cleaner
- Existing `ValidationError` (line 95) will be modified in T003

---

### Subtask T003 – Migrate Legacy ServiceException Subclasses

**Purpose**: Update all classes inheriting from `ServiceException` to inherit from `ServiceError` or appropriate category base.

**Steps**:
1. Update each legacy exception class:

| Class | Current Base | New Base | HTTP Code |
|-------|--------------|----------|-----------|
| `IngredientNotFound` | ServiceException | ServiceError | 404 |
| `RecipeNotFound` | ServiceException | ServiceError | 404 |
| `IngredientInUse` | ServiceException | ConflictError | 409 |
| `ValidationError` | ServiceException | ServiceError | 400 |
| `InsufficientStock` | ServiceException | BusinessRuleError | 422 |
| `DatabaseError` | ServiceException | ServiceError | 500 |
| `HierarchyValidationError` | ValidationError | ValidationError | 400 |

2. For each class, change inheritance and add `http_status_code`:

```python
# Before
class IngredientNotFound(ServiceException):
    ...

# After
class IngredientNotFound(ServiceError):
    """Raised when an ingredient cannot be found by ID."""
    http_status_code = 404

    def __init__(self, ingredient_id: int, correlation_id: Optional[str] = None):
        self.ingredient_id = ingredient_id
        super().__init__(
            f"Ingredient with ID {ingredient_id} not found",
            correlation_id=correlation_id,
            ingredient_id=ingredient_id
        )
```

3. Update `IngredientInUse` (most complex):

```python
class IngredientInUse(ConflictError):
    """Raised when attempting to delete an ingredient that has dependencies."""
    http_status_code = 409

    def __init__(self, identifier, deps, correlation_id: Optional[str] = None):
        self.identifier = identifier
        # ... existing logic for building deps_msg ...
        super().__init__(
            f"Cannot delete ingredient '{identifier}': used in {deps_msg}",
            correlation_id=correlation_id,
            identifier=identifier,
            deps=self.deps
        )
```

4. Update `InsufficientStock`:

```python
class InsufficientStock(BusinessRuleError):
    """Raised when there is not enough ingredient stock for an operation."""
    http_status_code = 422

    def __init__(
        self,
        ingredient_name: str,
        required: float,
        available: float,
        correlation_id: Optional[str] = None
    ):
        self.ingredient_name = ingredient_name
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient stock for {ingredient_name}: required {required}, available {available}",
            correlation_id=correlation_id,
            ingredient_name=ingredient_name,
            required=required,
            available=available
        )
```

**Files**: `src/services/exceptions.py`
**Parallel?**: Yes - can run after T001

**Notes**:
- Preserve ALL existing attributes (e.g., `self.ingredient_id`, `self.deps`)
- Add `correlation_id` parameter to all `__init__` methods
- Pass context data to super().__init__() via **kwargs

---

### Subtask T004 – Fix Duplicate MaterialInventoryItemNotFoundError

**Purpose**: Remove the duplicate class definition.

**Steps**:
1. Find both definitions in `src/services/exceptions.py`:
   - First at line ~176
   - Second at line ~261
2. Delete the second definition (lines ~261-275)
3. Verify no import issues

**Files**: `src/services/exceptions.py`
**Parallel?**: Yes - can run after T001

**Notes**: The two definitions are identical; keep the first one.

---

### Subtask T005 – Add Docstrings to All Exceptions

**Purpose**: Ensure all exceptions have comprehensive docstrings with usage examples.

**Steps**:
1. Review each exception class
2. Add/update docstring with:
   - One-line description
   - Args section documenting parameters
   - Example section showing usage
   - HTTP status code documentation

**Example format**:
```python
class ProductNotFound(ServiceError):
    """Raised when product cannot be found by ID.

    Args:
        product_id: The product ID that was not found
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise ProductNotFound(123)
        ProductNotFound: Product with ID 123 not found

    HTTP Status: 404 Not Found
    """
    http_status_code = 404
    ...
```

**Files**: `src/services/exceptions.py`
**Parallel?**: Yes - can run after T001

**Notes**: Focus on exceptions that lack docstrings or have minimal ones.

---

### Subtask T006 – Deprecate ServiceException Class

**Purpose**: Mark `ServiceException` as deprecated to guide migration.

**Steps**:
1. Add deprecation warning to `ServiceException`:

```python
import warnings

class ServiceException(Exception):
    """Base exception for all service layer errors (DEPRECATED).

    .. deprecated::
        Use ServiceError instead. ServiceException will be removed in a future version.

    Note: New code should use ServiceError instead.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "ServiceException is deprecated. Use ServiceError instead.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(*args, **kwargs)
```

2. Add `import warnings` at top of file if not present

**Files**: `src/services/exceptions.py`
**Parallel?**: Yes - can run after T003 (after subclasses migrated)

**Notes**:
- Don't remove `ServiceException` yet - external code may still reference it
- The warning will help identify remaining usages

---

## Test Strategy

**Manual Verification**:
```python
# In Python REPL or test file:
from src.services.exceptions import (
    ServiceError, ServiceException,
    IngredientNotFound, ValidationError, InsufficientStock
)

# Test ServiceError base
e = ServiceError("test", correlation_id="abc-123")
assert e.correlation_id == "abc-123"
assert e.http_status_code == 500

# Test inheritance
assert issubclass(IngredientNotFound, ServiceError)
assert IngredientNotFound.http_status_code == 404

# Test deprecation warning
import warnings
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    ServiceException("test")
    assert len(w) == 1
    assert "deprecated" in str(w[0].message).lower()
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing exception catches | Maintain backward compatibility - don't change class names or required args |
| Import errors | Keep all exceptions in same file, same location |
| Missing http_status_code | Default to 500 in ServiceError base |

---

## Definition of Done Checklist

- [ ] `ServiceError` has `correlation_id` and `http_status_code`
- [ ] All legacy `ServiceException` subclasses now inherit from `ServiceError`
- [ ] Duplicate `MaterialInventoryItemNotFoundError` removed
- [ ] All exceptions have comprehensive docstrings
- [ ] `ServiceException` shows deprecation warning
- [ ] Manual verification passes
- [ ] No import errors when running `python -c "from src.services.exceptions import *"`

---

## Review Guidance

**Key Checkpoints**:
1. Verify `http_status_code` values match expected HTTP semantics (404=not found, 400=validation, 409=conflict, 422=business rule, 500=server error)
2. Verify all existing attributes preserved (e.g., `IngredientInUse.deps`, `InsufficientStock.required`)
3. Verify deprecation warning fires for `ServiceException`
4. Verify no duplicate class definitions remain

---

## Activity Log

- 2026-02-02T00:00:00Z – system – lane=planned – Prompt created.
