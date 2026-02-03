"""Centralized error handler for UI layer.

Provides consistent error display and logging across all UI components.
Maps service exceptions to user-friendly messages while preserving
technical details in logs for debugging.
"""

import logging
from tkinter import messagebox
from typing import Any, Optional, Tuple

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
        return "Not Found", "Ingredient not found."

    if isinstance(exception, ProductNotFound):
        return "Not Found", "Product not found."

    if isinstance(exception, RecipeNotFound):
        return "Not Found", "Recipe not found."

    if isinstance(exception, PurchaseNotFound):
        return "Not Found", "Purchase record not found."

    if isinstance(exception, InventoryItemNotFound):
        return "Not Found", "Inventory item not found."

    # Hierarchy exceptions (422) - check BEFORE generic ValidationError
    # These inherit from HierarchyValidationError -> ValidationError
    if isinstance(exception, CircularReferenceError):
        return "Invalid Operation", "This operation would create a circular reference."

    if isinstance(exception, MaxDepthExceededError):
        return "Invalid Operation", f"Maximum hierarchy depth ({exception.max_level}) would be exceeded."

    if isinstance(exception, NonLeafIngredientError):
        msg = f"Cannot use '{exception.ingredient_name}': only leaf ingredients allowed."
        if exception.suggestions:
            msg += f" Try: {', '.join(exception.suggestions[:3])}"
        return "Invalid Selection", msg

    # Generic validation exceptions (400) - check AFTER more specific subtypes
    if isinstance(exception, ValidationError):
        if hasattr(exception, "errors") and exception.errors:
            errors_str = "; ".join(str(e) for e in exception.errors)
            return "Validation Error", f"Validation failed: {errors_str}"
        return "Validation Error", str(exception)

    # Conflict exceptions (409)
    if isinstance(exception, IngredientInUse):
        deps = getattr(exception, "details", getattr(exception, "deps", {}))
        if isinstance(deps, dict):
            parts = []
            if deps.get("recipes", 0) > 0:
                parts.append(f"{deps['recipes']} recipe(s)")
            if deps.get("products", 0) > 0:
                parts.append(f"{deps['products']} product(s)")
            if deps.get("inventory_items", 0) > 0:
                parts.append(f"{deps['inventory_items']} inventory item(s)")
            if deps.get("children", 0) > 0:
                parts.append(f"{deps['children']} child ingredient(s)")
            deps_msg = ", ".join(parts) if parts else "other items"
        else:
            deps_msg = "other items"
        return "Cannot Delete", f"This ingredient is used in {deps_msg}."

    if isinstance(exception, ProductInUse):
        deps = getattr(exception, "dependencies", {})
        if deps:
            parts = [f"{count} {name}" for name, count in deps.items() if count > 0]
            deps_msg = ", ".join(parts)
        else:
            deps_msg = "other items"
        return "Cannot Delete", f"This product is used in {deps_msg}."

    if isinstance(exception, SlugAlreadyExists):
        return "Duplicate", f"An item with identifier '{exception.slug}' already exists."

    if isinstance(exception, PlanStateError):
        state = getattr(exception, "current_state", "unknown")
        state_name = state.value if hasattr(state, "value") else str(state)
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
        status = getattr(exception, "http_status_code", 500)

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
        correlation_id = getattr(exception, "correlation_id", None) or "no-correlation"
        context = getattr(exception, "context", {})

        # Build log message with structured data
        log_data = {
            "operation": operation,
            "exception_type": exception.__class__.__name__,
            "message": str(exception),
            "correlation_id": correlation_id,
            "http_status_code": getattr(exception, "http_status_code", 500),
        }

        # Add context attributes
        if context:
            log_data["context"] = context

        logger.error(
            f"[{correlation_id}] {operation} failed: "
            f"{exception.__class__.__name__}: {exception}",
            extra={"error_data": log_data}
        )
    else:
        # Unexpected exception - log full stack trace
        logger.exception(
            f"{operation} failed with unexpected error: {exception.__class__.__name__}"
        )
