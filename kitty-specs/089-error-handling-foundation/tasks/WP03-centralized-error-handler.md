---
work_package_id: WP03
title: Centralized Error Handler
lane: "done"
dependencies: [WP01, WP02]
base_branch: 089-error-handling-foundation-WP02
base_commit: 482779c0655df9df1b3be0466d69bb983d32d5ee
created_at: '2026-02-02T23:58:43.238523+00:00'
subtasks:
- T014
- T015
- T016
- T017
- T018
phase: Phase 1 - Foundation
assignee: ''
agent: ''
shell_pid: "59805"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-02-02T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Centralized Error Handler

## ⚠️ IMPORTANT: Review Feedback Status

Check `review_status` field above. If `has_feedback`, address feedback items first.

---

## Review Feedback

*[Empty initially. Reviewers populate if work needs changes.]*

---

## Implementation Command

```bash
spec-kitty implement WP03 --base WP02
```

**Depends on**: WP01, WP02 (needs complete exception hierarchy)

---

## Objectives & Success Criteria

**Objective**: Create a centralized UI error handler that converts service exceptions to user-friendly messages while logging technical details.

**Success Criteria**:
- [ ] `src/ui/utils/error_handler.py` exists with `handle_error()` function
- [ ] All `ServiceError` subclasses mapped to user-friendly messages
- [ ] Technical details logged (exception type, message, correlation_id, stack trace)
- [ ] Generic `Exception` handled with safe fallback message
- [ ] Unit tests pass for all exception type mappings

---

## Context & Constraints

**Reference Documents**:
- Data Model: `kitty-specs/089-error-handling-foundation/data-model.md` (Centralized Error Handler Design)
- Constitution: Section VI.A.2 - Error Propagation

**User-Friendly Message Requirements** (from spec):
- `IngredientNotFoundBySlug` → "Ingredient '[slug]' not found"
- `ValidationError` → "Validation failed: [field-level errors]"
- `InsufficientInventoryError` → "Not enough [ingredient] in inventory"
- Generic `ServiceError` → "Operation failed: [safe message]"
- Unexpected `Exception` → "An unexpected error occurred. Please contact support."

**Constraints**:
- User messages must NEVER expose Python exception names or stack traces
- Technical details logged at ERROR level for debugging
- Must work with existing `messagebox.showerror()` pattern

---

## Subtasks & Detailed Guidance

### Subtask T014 – Create Module Structure

**Purpose**: Set up the `src/ui/utils/` package structure.

**Steps**:
1. Create directory if not exists: `src/ui/utils/`
2. Create `src/ui/utils/__init__.py`:

```python
"""UI utility modules for Bake Tracker."""

from .error_handler import handle_error, get_user_message

__all__ = ["handle_error", "get_user_message"]
```

3. Create empty `src/ui/utils/error_handler.py` for next subtask

**Files**:
- `src/ui/utils/__init__.py` (create)
- `src/ui/utils/error_handler.py` (create empty)

**Parallel?**: No - must complete before T015-T017

---

### Subtask T015 – Implement handle_error() Main Function

**Purpose**: Create the main error handling function with exception dispatch and dialog display.

**Steps**:
1. Implement in `src/ui/utils/error_handler.py`:

```python
"""Centralized error handler for UI layer.

Provides consistent error display and logging across all UI components.
Maps service exceptions to user-friendly messages while preserving
technical details in logs for debugging.
"""

import logging
from tkinter import messagebox
from typing import Any, Optional, Tuple

from src.services.exceptions import ServiceError

logger = logging.getLogger(__name__)


def handle_error(
    exception: Exception,
    parent: Optional[Any] = None,
    operation: str = "Operation",
    show_dialog: bool = True,
) -> Tuple[str, str]:
    """Handle an exception and optionally display user-friendly error dialog.

    This is the primary entry point for error handling in the UI layer.
    It converts exceptions to user-friendly messages, logs technical
    details, and optionally shows an error dialog.

    Args:
        exception: The caught exception to handle
        parent: Parent widget for dialog positioning (optional)
        operation: Description of what was being attempted (e.g., "Create recipe")
        show_dialog: Whether to show error dialog (default True)

    Returns:
        Tuple of (title, user_message) for further handling if needed

    Example:
        try:
            create_ingredient(data)
        except ServiceError as e:
            handle_error(e, parent=self, operation="Create ingredient")
        except Exception as e:
            handle_error(e, parent=self, operation="Create ingredient")
    """
    # Get user-friendly message
    title, message = get_user_message(exception, operation)

    # Log technical details
    _log_error(exception, operation)

    # Show dialog if requested
    if show_dialog:
        if parent is not None:
            messagebox.showerror(title, message, parent=parent)
        else:
            messagebox.showerror(title, message)

    return title, message


def get_user_message(exception: Exception, operation: str = "Operation") -> Tuple[str, str]:
    """Convert exception to user-friendly title and message.

    This function maps exception types to appropriate user messages.
    Can be used without showing a dialog when custom handling is needed.

    Args:
        exception: The exception to convert
        operation: Description of what was being attempted

    Returns:
        Tuple of (title, message) suitable for user display
    """
    return _get_user_message(exception, operation)
```

**Files**: `src/ui/utils/error_handler.py`
**Parallel?**: No - establishes interface for T016-T017

---

### Subtask T016 – Implement _get_user_message() with Exception Mapping

**Purpose**: Create comprehensive mapping from exception types to user-friendly messages.

**Steps**:
1. Add imports for all exception types at top of file:

```python
from src.services.exceptions import (
    ServiceError,
    IngredientNotFoundBySlug,
    IngredientNotFound,
    ProductNotFound,
    InventoryItemNotFound,
    PurchaseNotFound,
    RecipeNotFound,
    ValidationError,
    InsufficientStock,
    IngredientInUse,
    ProductInUse,
    SlugAlreadyExists,
    DatabaseError,
    HierarchyValidationError,
    CircularReferenceError,
    MaxDepthExceededError,
    NonLeafIngredientError,
    PlanStateError,
)
```

2. Implement `_get_user_message()`:

```python
def _get_user_message(exception: Exception, operation: str) -> Tuple[str, str]:
    """Map exception to user-friendly title and message.

    Handles specific exception types first, then falls back to
    category-based handling using http_status_code, and finally
    provides a generic message for unexpected exceptions.
    """
    # === Specific Exception Handlers ===

    # Not Found exceptions (404)
    if isinstance(exception, IngredientNotFoundBySlug):
        return "Not Found", f"Ingredient '{exception.slug}' not found."

    if isinstance(exception, IngredientNotFound):
        return "Not Found", f"Ingredient not found."

    if isinstance(exception, ProductNotFound):
        return "Not Found", f"Product not found."

    if isinstance(exception, RecipeNotFound):
        return "Not Found", f"Recipe not found."

    if isinstance(exception, PurchaseNotFound):
        return "Not Found", f"Purchase record not found."

    if isinstance(exception, InventoryItemNotFound):
        return "Not Found", f"Inventory item not found."

    # Validation exceptions (400)
    if isinstance(exception, NonLeafIngredientError):
        msg = f"Cannot use '{exception.ingredient_name}': only leaf ingredients allowed."
        if exception.suggestions:
            msg += f" Try: {', '.join(exception.suggestions[:3])}"
        return "Invalid Selection", msg

    if isinstance(exception, ValidationError):
        if hasattr(exception, 'errors') and exception.errors:
            errors_str = "; ".join(str(e) for e in exception.errors)
            return "Validation Error", f"Validation failed: {errors_str}"
        return "Validation Error", str(exception)

    # Hierarchy exceptions (422)
    if isinstance(exception, CircularReferenceError):
        return "Invalid Operation", "This operation would create a circular reference."

    if isinstance(exception, MaxDepthExceededError):
        return "Invalid Operation", f"Maximum hierarchy depth ({exception.max_level}) would be exceeded."

    # Conflict exceptions (409)
    if isinstance(exception, IngredientInUse):
        deps = getattr(exception, 'details', getattr(exception, 'deps', {}))
        if isinstance(deps, dict):
            parts = []
            if deps.get('recipes', 0) > 0:
                parts.append(f"{deps['recipes']} recipe(s)")
            if deps.get('products', 0) > 0:
                parts.append(f"{deps['products']} product(s)")
            if deps.get('inventory_items', 0) > 0:
                parts.append(f"{deps['inventory_items']} inventory item(s)")
            if deps.get('children', 0) > 0:
                parts.append(f"{deps['children']} child ingredient(s)")
            deps_msg = ", ".join(parts) if parts else "other items"
        else:
            deps_msg = "other items"
        return "Cannot Delete", f"This ingredient is used in {deps_msg}."

    if isinstance(exception, ProductInUse):
        deps = getattr(exception, 'dependencies', {})
        if deps:
            parts = [f"{count} {name}" for name, count in deps.items() if count > 0]
            deps_msg = ", ".join(parts)
        else:
            deps_msg = "other items"
        return "Cannot Delete", f"This product is used in {deps_msg}."

    if isinstance(exception, SlugAlreadyExists):
        return "Duplicate", f"An item with identifier '{exception.slug}' already exists."

    if isinstance(exception, PlanStateError):
        state = getattr(exception, 'current_state', 'unknown')
        state_name = state.value if hasattr(state, 'value') else str(state)
        return "Invalid Operation", f"Cannot {exception.attempted_action}: plan is {state_name}."

    # Business rule exceptions (422)
    if isinstance(exception, InsufficientStock):
        return (
            "Insufficient Inventory",
            f"Not enough {exception.ingredient_name} in inventory. "
            f"Need {exception.required}, have {exception.available}."
        )

    # Database errors (500)
    if isinstance(exception, DatabaseError):
        return "Database Error", "A database error occurred. Please try again."

    # === Category-Based Fallbacks ===

    if isinstance(exception, ServiceError):
        status = getattr(exception, 'http_status_code', 500)

        if status == 404:
            return "Not Found", f"{operation} failed: the requested item was not found."

        if status == 400:
            return "Validation Error", f"{operation} failed: {exception.message or 'invalid input'}"

        if status == 409:
            return "Conflict", f"{operation} failed: {exception.message or 'resource conflict'}"

        if status == 422:
            return "Cannot Complete", f"{operation} failed: {exception.message or 'business rule violation'}"

        # Default ServiceError (500)
        return "Error", f"{operation} failed: {exception.message or 'an error occurred'}"

    # === Unexpected Exception (last resort) ===
    return "Unexpected Error", "An unexpected error occurred. Please contact support."
```

**Files**: `src/ui/utils/error_handler.py`
**Parallel?**: Yes - can run after T015

**Notes**:
- Order matters: specific types checked before generic ServiceError
- Use `getattr()` for safe attribute access
- Never expose exception class names to user

---

### Subtask T017 – Implement _log_error() with Structured Logging

**Purpose**: Log technical error details for debugging while keeping them hidden from users.

**Steps**:
1. Add the logging function:

```python
def _log_error(exception: Exception, operation: str) -> None:
    """Log technical error details for debugging.

    Logs structured information including exception type, message,
    correlation_id (if available), and context data. Uses ERROR level
    for ServiceError subclasses and logs full stack trace for
    unexpected exceptions.

    Args:
        exception: The exception to log
        operation: Description of what was being attempted
    """
    if isinstance(exception, ServiceError):
        correlation_id = getattr(exception, 'correlation_id', None) or 'no-correlation'
        context = getattr(exception, 'context', {})

        # Build log message with structured data
        log_data = {
            'operation': operation,
            'exception_type': exception.__class__.__name__,
            'message': str(exception),
            'correlation_id': correlation_id,
            'http_status_code': getattr(exception, 'http_status_code', 500),
        }

        # Add context attributes
        if context:
            log_data['context'] = context

        logger.error(
            f"[{correlation_id}] {operation} failed: "
            f"{exception.__class__.__name__}: {exception}",
            extra={'error_data': log_data}
        )
    else:
        # Unexpected exception - log full stack trace
        logger.exception(
            f"{operation} failed with unexpected error: {exception.__class__.__name__}"
        )
```

**Files**: `src/ui/utils/error_handler.py`
**Parallel?**: Yes - can run after T015

---

### Subtask T018 – Create Error Handler Unit Tests

**Purpose**: Ensure error handler correctly maps all exception types and logs appropriately.

**Steps**:
1. Create `src/tests/unit/test_error_handler.py`:

```python
"""Unit tests for centralized error handler."""

import logging
import pytest
from unittest.mock import patch, MagicMock

from src.ui.utils.error_handler import handle_error, get_user_message
from src.services.exceptions import (
    ServiceError,
    IngredientNotFoundBySlug,
    ValidationError,
    InsufficientStock,
    IngredientInUse,
    SlugAlreadyExists,
    DatabaseError,
)


class TestGetUserMessage:
    """Tests for exception to user message mapping."""

    def test_ingredient_not_found_by_slug(self):
        exc = IngredientNotFoundBySlug("flour")
        title, msg = get_user_message(exc, "Get ingredient")
        assert title == "Not Found"
        assert "flour" in msg
        assert "IngredientNotFoundBySlug" not in msg  # No class names

    def test_validation_error_with_errors_list(self):
        exc = ValidationError(["Name is required", "Slug is invalid"])
        title, msg = get_user_message(exc, "Create ingredient")
        assert title == "Validation Error"
        assert "Name is required" in msg
        assert "Slug is invalid" in msg

    def test_insufficient_stock(self):
        exc = InsufficientStock("flour", required=100, available=50)
        title, msg = get_user_message(exc, "Record production")
        assert title == "Insufficient Inventory"
        assert "flour" in msg
        assert "100" in msg
        assert "50" in msg

    def test_ingredient_in_use(self):
        deps = {'recipes': 3, 'products': 2}
        exc = IngredientInUse("flour", deps)
        title, msg = get_user_message(exc, "Delete ingredient")
        assert title == "Cannot Delete"
        assert "3 recipe(s)" in msg
        assert "2 product(s)" in msg

    def test_slug_already_exists(self):
        exc = SlugAlreadyExists("flour")
        title, msg = get_user_message(exc, "Create ingredient")
        assert title == "Duplicate"
        assert "flour" in msg

    def test_generic_service_error_fallback(self):
        exc = ServiceError("Something failed")
        title, msg = get_user_message(exc, "Do something")
        assert title == "Error"
        assert "failed" in msg.lower()

    def test_unexpected_exception(self):
        exc = RuntimeError("Unexpected!")
        title, msg = get_user_message(exc, "Do something")
        assert title == "Unexpected Error"
        assert "contact support" in msg.lower()
        assert "RuntimeError" not in msg  # No class names

    def test_no_python_exception_names_exposed(self):
        """Verify no exception class names leak to user messages."""
        exceptions = [
            IngredientNotFoundBySlug("test"),
            ValidationError(["error"]),
            ServiceError("error"),
            RuntimeError("error"),
        ]
        for exc in exceptions:
            _, msg = get_user_message(exc, "Test")
            assert exc.__class__.__name__ not in msg


class TestHandleError:
    """Tests for handle_error function."""

    @patch('src.ui.utils.error_handler.messagebox')
    def test_shows_dialog_by_default(self, mock_msgbox):
        exc = IngredientNotFoundBySlug("flour")
        handle_error(exc, operation="Get ingredient")
        mock_msgbox.showerror.assert_called_once()

    @patch('src.ui.utils.error_handler.messagebox')
    def test_no_dialog_when_disabled(self, mock_msgbox):
        exc = IngredientNotFoundBySlug("flour")
        handle_error(exc, operation="Get ingredient", show_dialog=False)
        mock_msgbox.showerror.assert_not_called()

    @patch('src.ui.utils.error_handler.messagebox')
    def test_returns_title_and_message(self, mock_msgbox):
        exc = IngredientNotFoundBySlug("flour")
        title, msg = handle_error(exc, operation="Get", show_dialog=False)
        assert title == "Not Found"
        assert "flour" in msg

    def test_logs_service_error(self, caplog):
        exc = ServiceError("test error", correlation_id="test-123")
        with caplog.at_level(logging.ERROR):
            handle_error(exc, operation="Test op", show_dialog=False)
        assert "test-123" in caplog.text
        assert "ServiceError" in caplog.text

    def test_logs_unexpected_error_with_traceback(self, caplog):
        exc = RuntimeError("Boom!")
        with caplog.at_level(logging.ERROR):
            handle_error(exc, operation="Test op", show_dialog=False)
        assert "unexpected error" in caplog.text.lower()


class TestCorrelationIdLogging:
    """Tests for correlation ID in error logging."""

    def test_correlation_id_logged(self, caplog):
        exc = IngredientNotFoundBySlug("flour")
        exc.correlation_id = "corr-abc-123"
        with caplog.at_level(logging.ERROR):
            handle_error(exc, operation="Test", show_dialog=False)
        assert "corr-abc-123" in caplog.text

    def test_no_correlation_id_handled(self, caplog):
        exc = IngredientNotFoundBySlug("flour")
        # No correlation_id set
        with caplog.at_level(logging.ERROR):
            handle_error(exc, operation="Test", show_dialog=False)
        assert "no-correlation" in caplog.text
```

2. Run tests: `./run-tests.sh src/tests/unit/test_error_handler.py -v`

**Files**: `src/tests/unit/test_error_handler.py`
**Parallel?**: Yes - can run after T016-T017

---

## Test Strategy

**Run all tests**:
```bash
./run-tests.sh src/tests/unit/test_error_handler.py -v
```

**Manual verification**:
```python
from src.ui.utils.error_handler import handle_error, get_user_message
from src.services.exceptions import IngredientNotFoundBySlug

# Test without dialog
title, msg = handle_error(
    IngredientNotFoundBySlug("flour"),
    operation="Test",
    show_dialog=False
)
print(f"Title: {title}")
print(f"Message: {msg}")
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Missing exception type mapping | Fallback to category-based handling via http_status_code |
| Import errors for exception types | Import at module level, use try/except if needed |
| Logging failures | Wrap logging in try/except, don't fail on log errors |

---

## Definition of Done Checklist

- [ ] `src/ui/utils/__init__.py` exists and exports `handle_error`
- [ ] `src/ui/utils/error_handler.py` implements complete handler
- [ ] All known exception types have specific mappings
- [ ] Generic fallback works for unknown ServiceError subclasses
- [ ] Unexpected Exception handled safely
- [ ] Unit tests pass
- [ ] No Python exception names exposed in user messages

---

## Review Guidance

**Key Checkpoints**:
1. Verify no exception class names appear in user messages
2. Verify correlation_id logged when present
3. Verify stack trace logged for unexpected exceptions
4. Verify all tests pass
5. Test with a few real exceptions from the app

---

## Activity Log

- 2026-02-02T00:00:00Z – system – lane=planned – Prompt created.
- 2026-02-03T00:11:13Z – unknown – shell_pid=59805 – lane=for_review – Ready for review: Centralized error handler with 39 passing tests
- 2026-02-03T00:34:08Z – unknown – shell_pid=59805 – lane=done – Approved: Centralized error handler with handle_error() function, exception-to-message mapping, structured logging, 39 passing tests
