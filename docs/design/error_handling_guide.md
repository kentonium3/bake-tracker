# Error Handling Guide

**Version**: 1.0
**Last Updated**: 2026-02-02
**Implements**: Constitution Principle VI.A (Error Handling Standards)

## Overview

This guide documents the error handling patterns for Bake Tracker. The goal is to provide
user-friendly error messages while maintaining structured logging for debugging.

### Core Principles

1. **User-Friendly Messages**: Users never see raw Python exceptions or stack traces
2. **Structured Logging**: Technical details are logged for debugging
3. **Three-Tier Strategy**: Specific exception → ServiceError → generic Exception
4. **Web Migration Ready**: HTTP status codes mapped for future API development

## Exception Hierarchy

All service exceptions inherit from `ServiceError` and include HTTP status code mapping:

```
ServiceError (base - all service exceptions, HTTP 500)
├── NotFoundError (404)
│   ├── IngredientNotFoundBySlug
│   ├── IngredientNotFound
│   ├── ProductNotFound
│   ├── InventoryItemNotFound
│   ├── MaterialInventoryItemNotFoundError
│   ├── PurchaseNotFound
│   ├── RecipeNotFound
│   └── SupplierNotFoundError
├── ValidationError (400)
│   └── HierarchyValidationError
│       ├── CircularReferenceError (422)
│       ├── MaxDepthExceededError (422)
│       └── NonLeafIngredientError (400)
├── ConflictError (409)
│   ├── SlugAlreadyExists
│   ├── IngredientInUse
│   └── ProductInUse
├── BusinessRuleError (422)
│   └── InsufficientStock
├── PlanStateError (409)
└── DatabaseError (500)
```

## Exception Types Reference

### Not Found Exceptions (HTTP 404)

| Exception | When to Raise | Example |
|-----------|---------------|---------|
| `IngredientNotFoundBySlug` | Ingredient lookup by slug fails | `raise IngredientNotFoundBySlug("all_purpose_flour")` |
| `IngredientNotFound` | Ingredient lookup by ID fails | `raise IngredientNotFound(123)` |
| `ProductNotFound` | Product lookup by ID fails | `raise ProductNotFound(456)` |
| `InventoryItemNotFound` | Inventory item lookup fails | `raise InventoryItemNotFound(789)` |
| `PurchaseNotFound` | Purchase record lookup fails | `raise PurchaseNotFound(101)` |
| `RecipeNotFound` | Recipe lookup by ID fails | `raise RecipeNotFound(202)` |
| `SupplierNotFoundError` | Supplier lookup by ID fails | `raise SupplierNotFoundError(303)` |

### Validation Exceptions (HTTP 400)

| Exception | When to Raise | Example |
|-----------|---------------|---------|
| `ValidationError` | Input validation fails | `raise ValidationError(["Name required", "Slug invalid"])` |
| `NonLeafIngredientError` | Non-leaf ingredient used in recipe | `raise NonLeafIngredientError(id, "Chocolate", "recipe")` |

### Conflict Exceptions (HTTP 409)

| Exception | When to Raise | Example |
|-----------|---------------|---------|
| `SlugAlreadyExists` | Duplicate slug creation attempted | `raise SlugAlreadyExists("all_purpose_flour")` |
| `IngredientInUse` | Deleting ingredient with dependencies | `raise IngredientInUse("flour", {"recipes": 5})` |
| `ProductInUse` | Deleting product with dependencies | `raise ProductInUse(123, {"inventory_items": 12})` |
| `PlanStateError` | Invalid plan state modification | `raise PlanStateError(event_id, state, "modify recipes")` |

### Business Rule Exceptions (HTTP 422)

| Exception | When to Raise | Example |
|-----------|---------------|---------|
| `InsufficientStock` | Not enough inventory for operation | `raise InsufficientStock("flour", 100, 50)` |
| `CircularReferenceError` | Operation would create circular hierarchy | `raise CircularReferenceError(123, 456)` |
| `MaxDepthExceededError` | Hierarchy depth would exceed limit | `raise MaxDepthExceededError(123, 4, 2)` |

### Server Exceptions (HTTP 500)

| Exception | When to Raise | Example |
|-----------|---------------|---------|
| `ServiceError` | Generic service failures | `raise ServiceError("Operation failed")` |
| `DatabaseError` | Database operations fail | `raise DatabaseError("Connection lost", e)` |

## Three-Tier Pattern

### The Anti-Pattern (DO NOT USE)

```python
try:
    ingredient = create_ingredient(data)
except Exception as e:
    messagebox.showerror("Error", str(e))  # Exposes Python errors to user
```

**Problems:**
- Exposes technical Python exceptions to users
- No differentiation between recoverable and fatal errors
- No structured logging
- Inconsistent error messages

### The Correct Pattern

```python
from src.services.exceptions import ServiceError, ValidationError
from src.ui.utils.error_handler import handle_error

try:
    ingredient = create_ingredient(data)

except ValidationError as e:
    # Tier 1: Specific exception - can do custom handling
    handle_error(e, parent=self, operation="Create ingredient")
    self.highlight_invalid_fields(e.errors)  # Optional: custom handling

except ServiceError as e:
    # Tier 2: Known service error - consistent handling
    handle_error(e, parent=self, operation="Create ingredient")

except Exception as e:
    # Tier 3: Unexpected error - log and show generic message
    handle_error(e, parent=self, operation="Create ingredient")
```

**Benefits:**
- User sees friendly error messages
- Technical details logged for debugging
- Specific exceptions allow custom UI handling
- Consistent error presentation

### Before/After Examples

**Before (ingredients_tab.py):**
```python
try:
    ingredient_crud_service.delete_ingredient(ingredient.id)
except IngredientInUse as e:
    messagebox.showerror("Cannot Delete", str(e), parent=self)
except Exception as e:
    messagebox.showerror("Error", f"Delete failed: {e}", parent=self)
```

**After (ingredients_tab.py):**
```python
try:
    ingredient_crud_service.delete_ingredient(ingredient.id)
except IngredientInUse as e:
    handle_error(e, parent=self, operation="Delete ingredient")
except ServiceError as e:
    handle_error(e, parent=self, operation="Delete ingredient")
except Exception as e:
    handle_error(e, parent=self, operation="Delete ingredient")
```

### Silent Handlers (Graceful Degradation)

For non-critical operations where the UI should continue despite errors:

```python
# Silent handler - catches both ServiceError and generic Exception
try:
    categories = get_categories()
except (ServiceError, Exception):
    categories = []  # Graceful degradation: empty list
```

**Use cases:**
- Dashboard components that can show partial data
- Optional data loading (recent items, statistics)
- Prefetch operations that can fail silently

## HTTP Status Code Mapping

For future web/API migration, exceptions map to HTTP status codes:

| Category | HTTP Status | Example Exceptions |
|----------|-------------|-------------------|
| Not Found | 404 | `IngredientNotFoundBySlug`, `ProductNotFound`, `RecipeNotFound` |
| Validation | 400 | `ValidationError`, `NonLeafIngredientError` |
| Conflict | 409 | `SlugAlreadyExists`, `IngredientInUse`, `PlanStateError` |
| Business Rule | 422 | `InsufficientStock`, `CircularReferenceError`, `MaxDepthExceededError` |
| Server Error | 500 | `DatabaseError`, generic `ServiceError` |

## The `handle_error()` Function

Located in `src/ui/utils/error_handler.py`, this centralizes error display:

```python
def handle_error(
    error: Exception,
    parent=None,
    operation: str = "",
    log_level: int = logging.ERROR
) -> None:
    """
    Handle an exception with user-friendly display and logging.

    Args:
        error: The exception to handle
        parent: Parent widget for dialog (centers dialog on parent)
        operation: What operation was being performed (for context)
        log_level: Logging level (default ERROR)
    """
```

### Features

- **User-friendly messages**: Converts technical exceptions to readable messages
- **Structured logging**: Logs full exception details for debugging
- **Parent-centered dialogs**: Error dialogs appear centered on parent widget
- **Operation context**: Includes what was being done when error occurred

### Example Output

**For ValidationError:**
```
Dialog Title: "Create ingredient failed"
Message: "Name is required; Slug is invalid"
```

**For generic Exception:**
```
Dialog Title: "Create ingredient failed"
Message: "An unexpected error occurred. Please try again."
Log: Full stack trace with exception details
```

## Quick Reference: New Service Function Checklist

When creating a new service function:

- [ ] Function raises domain exception on failure (not `return None`)
- [ ] Exception includes relevant context (entity IDs, slugs)
- [ ] Exception inherits from `ServiceError`
- [ ] Exception has `http_status_code` class attribute
- [ ] Calling UI code uses `handle_error()`
- [ ] Calling UI code uses three-tier pattern

## Quick Reference: Exception Catch Pattern

```python
# Standard imports
from src.services.exceptions import ServiceError, ValidationError
from src.ui.utils.error_handler import handle_error

# Standard three-tier pattern
try:
    result = service_function(data)
except ValidationError as e:
    handle_error(e, parent=self, operation="Operation name")
    # Optional: custom ValidationError handling
except ServiceError as e:
    handle_error(e, parent=self, operation="Operation name")
except Exception as e:
    handle_error(e, parent=self, operation="Operation name")
```

## CLI Exception Handling

For CLI tools (no GUI), use text output instead of dialogs:

```python
from src.services.exceptions import ServiceError

try:
    result = operation()
except ServiceError as e:
    print(f"ERROR: {e}")
    return 1
except Exception as e:
    print(f"ERROR: {e}")
    return 1
```

**Key differences from GUI:**
- No dialog boxes
- Print error to stdout/stderr
- Return exit code 1 on failure
- Exit code 0 on success

## Adding New Exception Types

1. **Create the exception class** in `src/services/exceptions.py`:

```python
class NewEntityNotFound(ServiceError):
    """Raised when entity cannot be found."""

    http_status_code = 404

    def __init__(self, entity_id: int, correlation_id: Optional[str] = None):
        self.entity_id = entity_id
        super().__init__(
            f"Entity with ID {entity_id} not found",
            correlation_id=correlation_id,
            entity_id=entity_id
        )
```

2. **Include in exception hierarchy** comment at top of file

3. **Export from `__init__.py`** if needed

4. **Document** in this guide

## See Also

- `src/services/exceptions.py` - Exception class definitions
- `src/ui/utils/error_handler.py` - Centralized error handler
- `.kittify/memory/constitution.md` - Section VI.A (Error Handling Standards)
- `docs/design/session_management_remediation_spec.md` - Session management patterns
