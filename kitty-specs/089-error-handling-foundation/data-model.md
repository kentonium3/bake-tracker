# Data Model: Error Handling Foundation

**Feature**: 089-error-handling-foundation
**Date**: 2026-02-02
**Status**: Design Complete

## Exception Hierarchy Design

### Base Class Enhancement

```python
class ServiceError(Exception):
    """Base exception for all service layer errors.

    All service-specific exceptions should inherit from this class.

    Attributes:
        message: Human-readable error message
        correlation_id: Optional correlation ID for tracing (future use)
        http_status_code: HTTP status code for web migration (default 500)

    Example:
        >>> raise ServiceError("Operation failed", correlation_id="abc-123")
    """

    http_status_code: int = 500  # Default for generic service errors

    def __init__(
        self,
        message: str,
        correlation_id: Optional[str] = None,
        **context
    ):
        self.message = message
        self.correlation_id = correlation_id
        self.context = context  # Additional structured context
        super().__init__(message)

    def to_dict(self) -> dict:
        """Return exception as dictionary for logging/serialization."""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "correlation_id": self.correlation_id,
            "http_status_code": self.http_status_code,
            "context": self.context,
        }
```

### Consolidated Hierarchy

```
ServiceError (base)
├── NotFoundError (category base, 404)
│   ├── IngredientNotFoundBySlug(slug)
│   ├── ProductNotFound(product_id)
│   ├── InventoryItemNotFound(inventory_item_id)
│   ├── PurchaseNotFound(purchase_id)
│   ├── RecipeNotFound(recipe_id)
│   ├── EventNotFound(event_id)
│   ├── SupplierNotFoundError(supplier_id)
│   └── [service-local NotFound exceptions]
│
├── ValidationError (category base, 400)
│   ├── HierarchyValidationError
│   │   ├── CircularReferenceError(entity_id, new_parent_id)
│   │   ├── MaxDepthExceededError(entity_id, would_be_level, max_level)
│   │   └── NonLeafIngredientError(ingredient_id, ingredient_name, context, suggestions)
│   └── [field-level validation errors]
│
├── ConflictError (category base, 409)
│   ├── SlugAlreadyExists(slug)
│   ├── DuplicateError (various)
│   ├── EntityInUseError
│   │   ├── IngredientInUse(identifier, deps)
│   │   └── ProductInUse(product_id, dependencies)
│   └── StateConflictError
│       ├── PlanStateError(event_id, current_state, attempted_action)
│       └── InvalidStatusTransitionError
│
├── BusinessRuleError (category base, 422)
│   ├── InsufficientResourceError
│   │   ├── InsufficientStock(ingredient_name, required, available)
│   │   ├── InsufficientInventoryError(ingredient_slug, needed, available, unit)
│   │   ├── InsufficientFinishedUnitError(finished_unit_id, needed, available)
│   │   └── InsufficientPackagingError(product_id, needed, available)
│   └── [other business rule violations]
│
└── DatabaseError(message, original_error) (500)
```

### HTTP Status Code Mapping

| Category | HTTP Status | Description |
|----------|-------------|-------------|
| `NotFoundError` | 404 | Resource not found |
| `ValidationError` | 400 | Input validation failed |
| `ConflictError` | 409 | Resource conflict (in use, duplicate, state) |
| `BusinessRuleError` | 422 | Business rule violation (insufficient resources) |
| `DatabaseError` | 500 | Database/infrastructure error |
| `ServiceError` (generic) | 500 | Unspecified service error |

### Category Base Classes (Optional - for cleaner mapping)

```python
class NotFoundError(ServiceError):
    """Base for all not-found exceptions. Maps to HTTP 404."""
    http_status_code = 404

class ValidationError(ServiceError):
    """Base for all validation exceptions. Maps to HTTP 400."""
    http_status_code = 400

class ConflictError(ServiceError):
    """Base for all conflict exceptions. Maps to HTTP 409."""
    http_status_code = 409

class BusinessRuleError(ServiceError):
    """Base for business rule violations. Maps to HTTP 422."""
    http_status_code = 422
```

## Centralized Error Handler Design

### Location

`src/ui/utils/error_handler.py`

### Interface

```python
from typing import Optional, Tuple
from tkinter import messagebox
import logging

logger = logging.getLogger(__name__)

def handle_error(
    exception: Exception,
    parent: Optional[Any] = None,
    operation: str = "Operation",
    show_dialog: bool = True,
) -> Tuple[str, str]:
    """
    Handle an exception and optionally display user-friendly error dialog.

    Args:
        exception: The caught exception
        parent: Parent widget for dialog (optional)
        operation: Description of what was being attempted
        show_dialog: Whether to show error dialog (default True)

    Returns:
        Tuple of (title, user_message) for further handling

    Example:
        try:
            create_ingredient(data)
        except ServiceError as e:
            handle_error(e, parent=self, operation="Create ingredient")
        except Exception as e:
            handle_error(e, parent=self, operation="Create ingredient")
    """

    # Get user-friendly message
    title, message = _get_user_message(exception, operation)

    # Log technical details
    _log_error(exception, operation)

    # Show dialog if requested
    if show_dialog:
        messagebox.showerror(title, message, parent=parent)

    return title, message


def _get_user_message(exception: Exception, operation: str) -> Tuple[str, str]:
    """Map exception to user-friendly title and message."""

    # Specific exception types
    if isinstance(exception, IngredientNotFoundBySlug):
        return "Not Found", f"Ingredient '{exception.slug}' not found"

    if isinstance(exception, ValidationError):
        errors = "; ".join(exception.errors) if hasattr(exception, 'errors') else str(exception)
        return "Validation Error", f"Validation failed: {errors}"

    if isinstance(exception, InsufficientStock):
        return "Insufficient Inventory", (
            f"Not enough {exception.ingredient_name} in inventory. "
            f"Need {exception.required}, have {exception.available}."
        )

    # ... more specific mappings ...

    # Category-based fallbacks
    if isinstance(exception, ServiceError):
        if exception.http_status_code == 404:
            return "Not Found", f"{operation} failed: resource not found"
        if exception.http_status_code == 400:
            return "Validation Error", f"{operation} failed: {exception.message}"
        if exception.http_status_code == 409:
            return "Conflict", f"{operation} failed: {exception.message}"
        if exception.http_status_code == 422:
            return "Cannot Complete", f"{operation} failed: {exception.message}"
        return "Error", f"{operation} failed: {exception.message}"

    # Unexpected exception
    return "Unexpected Error", "An unexpected error occurred. Please contact support."


def _log_error(exception: Exception, operation: str) -> None:
    """Log technical error details."""

    if isinstance(exception, ServiceError):
        logger.error(
            f"[{exception.correlation_id or 'no-correlation'}] "
            f"{operation} failed: {exception.__class__.__name__}: {exception.message}",
            extra={"context": getattr(exception, 'context', {})}
        )
    else:
        logger.exception(f"{operation} failed with unexpected error")
```

### Three-Tier Pattern Template

```python
# In UI code:
from src.services.exceptions import (
    ServiceError,
    IngredientNotFoundBySlug,
    ValidationError,
    InsufficientStock,
)
from src.ui.utils.error_handler import handle_error

def save_recipe(self):
    """Example of three-tier exception handling."""
    try:
        # Tier 1: Normal operation
        recipe = recipe_service.create_recipe(data)
        self.show_success("Recipe created successfully")

    except IngredientNotFoundBySlug as e:
        # Tier 1: Specific exception with tailored handling
        handle_error(e, parent=self, operation="Create recipe")
        self.highlight_missing_ingredient(e.slug)

    except ValidationError as e:
        # Tier 1: Another specific exception
        handle_error(e, parent=self, operation="Create recipe")
        self.highlight_validation_errors(e.errors)

    except ServiceError as e:
        # Tier 2: Generic service error via centralized handler
        handle_error(e, parent=self, operation="Create recipe")

    except Exception as e:
        # Tier 3: Unexpected error - always log, generic message
        handle_error(e, parent=self, operation="Create recipe")
```

## Migration Patterns

### Before (Current Pattern)

```python
try:
    ingredient = create_ingredient(data)
except Exception as e:
    messagebox.showerror("Error", f"Failed to create ingredient: {str(e)}")
```

### After (Three-Tier Pattern)

```python
try:
    ingredient = create_ingredient(data)
except ValidationError as e:
    handle_error(e, parent=self, operation="Create ingredient")
except ServiceError as e:
    handle_error(e, parent=self, operation="Create ingredient")
except Exception as e:
    handle_error(e, parent=self, operation="Create ingredient")
```

### Simplified (When No Tailored Handling Needed)

```python
try:
    ingredient = create_ingredient(data)
except Exception as e:
    handle_error(e, parent=self, operation="Create ingredient")
```

Note: The centralized handler correctly identifies exception types and provides appropriate messages. The three-tier pattern is required when you need *different behavior* for different exception types (e.g., highlighting specific fields for validation errors).

## Testing Requirements

### Exception Hierarchy Tests

```python
def test_service_error_has_correlation_id():
    error = ServiceError("test", correlation_id="abc-123")
    assert error.correlation_id == "abc-123"

def test_all_exceptions_inherit_from_service_error():
    from src.services.exceptions import (
        IngredientNotFoundBySlug,
        ValidationError,
        # ... all exception classes
    )
    for exc_class in [IngredientNotFoundBySlug, ValidationError, ...]:
        assert issubclass(exc_class, ServiceError)

def test_http_status_codes_assigned():
    assert IngredientNotFoundBySlug.http_status_code == 404
    assert ValidationError.http_status_code == 400
```

### Error Handler Tests

```python
def test_handle_error_maps_not_found():
    exc = IngredientNotFoundBySlug("flour")
    title, msg = handle_error(exc, show_dialog=False, operation="Get ingredient")
    assert title == "Not Found"
    assert "flour" in msg

def test_handle_error_logs_technical_details(caplog):
    exc = ServiceError("test error", correlation_id="test-123")
    handle_error(exc, show_dialog=False, operation="Test")
    assert "test-123" in caplog.text
    assert "ServiceError" in caplog.text
```
