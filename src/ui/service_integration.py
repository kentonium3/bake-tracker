"""
UI Service Integration Layer for Bake Tracker.

This module provides centralized service integration utilities for UI components,
including consistent error handling, logging, and operation monitoring.

Features:
- Centralized exception handling with user-friendly messages
- Service operation logging and monitoring
- UI feedback integration (status bars, dialogs)
- Architecture support for assembly management features
"""

import logging
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Union, TypeVar, Protocol, ParamSpec
from enum import Enum
import functools
from collections import deque

# Type variables for the decorator
P = ParamSpec('P')
R = TypeVar('R')

# Service layer exceptions
from src.services.exceptions import (
    ServiceError, ServiceException, ValidationError, DatabaseError,
    IngredientNotFoundBySlug, VariantNotFound, SlugAlreadyExists, VariantInUse
)

# Service layer exceptions - use conditional imports for forward compatibility
try:
    # FinishedUnit service exceptions (may not exist yet)
    from src.services.finished_unit_service import (
        FinishedUnitNotFoundError, InvalidInventoryError,
        DuplicateSlugError, ReferencedUnitError
    )
except ImportError:
    # Create placeholder exceptions until FinishedUnit service is implemented
    class FinishedUnitNotFoundError(ServiceError):
        """Placeholder for FinishedUnit service exception."""
        pass

    class InvalidInventoryError(ServiceError):
        """Placeholder for FinishedUnit service exception."""
        pass

    class DuplicateSlugError(ServiceError):
        """Placeholder for FinishedUnit service exception."""
        pass

    class ReferencedUnitError(ServiceError):
        """Placeholder for FinishedUnit service exception."""
        pass

try:
    # FinishedGood service exceptions
    from src.services.finished_good_service import (
        FinishedGoodNotFoundError, CircularReferenceError,
        InsufficientInventoryError, InvalidComponentError, AssemblyIntegrityError
    )
except ImportError:
    # Create placeholder exceptions until FinishedGood service is updated
    class FinishedGoodNotFoundError(ServiceError):
        """Placeholder for FinishedGood service exception."""
        pass

    class CircularReferenceError(ServiceError):
        """Placeholder for FinishedGood service exception."""
        pass

    class InsufficientInventoryError(ServiceError):
        """Placeholder for FinishedGood service exception."""
        pass

    class InvalidComponentError(ServiceError):
        """Placeholder for FinishedGood service exception."""
        pass

    class AssemblyIntegrityError(ServiceError):
        """Placeholder for FinishedGood service exception."""
        pass

# UI components
from src.ui.widgets.dialogs import show_error, show_success, show_warning, show_info

logger = logging.getLogger(__name__)


# Constants for health monitoring thresholds
class HealthThresholds:
    """Health monitoring thresholds for service operations."""
    UNHEALTHY_FAILURE_RATE = 10.0  # percent
    DEGRADED_FAILURE_RATE = 5.0    # percent
    SLOW_OPERATION_TIME = 1.0      # seconds

# Type variables for better generic typing
T = TypeVar('T')


class OperationType(Enum):
    """Types of service operations for logging and monitoring."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    SEARCH = "search"


class ComponentType(Enum):
    """Types of components for composition relationships."""
    FINISHED_UNIT = "finished_unit"
    FINISHED_GOOD = "finished_good"


class UIServiceIntegrator:
    """
    Centralized service integration layer for UI components.

    Provides consistent error handling, logging, and operation monitoring
    for all UI → Service interactions.
    """

    def __init__(self):
        """Initialize the service integrator."""
        self._lock = threading.Lock()  # Thread synchronization for statistics
        self.operation_stats = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "last_operation_time": None,
            "operation_times": deque(maxlen=100)  # Automatic trimming with deque
        }

    def execute_service_operation(
        self,
        operation_name: str,
        operation_type: OperationType,
        service_function: Callable[[], T],
        parent_widget=None,
        success_message: Optional[str] = None,
        error_context: Optional[str] = None,
        show_success_dialog: bool = False,
        log_level: int = logging.INFO,
        suppress_exception: bool = False
    ) -> Optional[T]:
        """
        Execute a service operation with comprehensive error handling and logging.

        Args:
            operation_name: Human-readable name of the operation
            operation_type: Type of operation for logging
            service_function: Function to execute (should be a lambda or partial)
            parent_widget: Parent widget for error dialogs
            success_message: Optional success message to display
            error_context: Additional context for error messages
            show_success_dialog: Whether to show success dialog
            log_level: Logging level for the operation
            suppress_exception: If True, don't re-raise exceptions after handling

        Returns:
            Result of the service operation or None if failed

        Raises:
            Re-raises exceptions unless suppress_exception=True

        Examples:
            Basic CRUD operation:
            >>> integrator = UIServiceIntegrator()
            >>> result = integrator.execute_service_operation(
            ...     operation_name="Load All Items",
            ...     operation_type=OperationType.READ,
            ...     service_function=lambda: item_service.get_all(),
            ...     parent_widget=self
            ... )

            Create operation with success feedback:
            >>> new_item = integrator.execute_service_operation(
            ...     operation_name="Create New Item",
            ...     operation_type=OperationType.CREATE,
            ...     service_function=lambda: item_service.create(item_data),
            ...     parent_widget=self,
            ...     success_message="Item created successfully!",
            ...     show_success_dialog=True
            ... )

            Operation with custom error context:
            >>> result = integrator.execute_service_operation(
            ...     operation_name="Delete Item",
            ...     operation_type=OperationType.DELETE,
            ...     service_function=lambda: item_service.delete(item_id),
            ...     parent_widget=self,
            ...     error_context="Deleting selected item",
            ...     suppress_exception=True  # Don't re-raise, just handle
            ... )
        """
        start_time = time.time()

        try:
            # Log operation start
            self._log_with_level(log_level, f"Starting {operation_type.value} operation: {operation_name}")

            # Execute the service function
            result = service_function()

            # Calculate execution time
            execution_time = time.time() - start_time
            self._record_success(operation_name, execution_time)

            # Log success
            self._log_with_level(log_level, f"Completed {operation_type.value} operation: {operation_name} "
                                              f"({execution_time:.3f}s)")

            # Show success feedback if requested
            if success_message and show_success_dialog:
                show_success("Success", success_message, parent=parent_widget)

            return result

        except Exception as e:
            # Calculate execution time for failed operation
            execution_time = time.time() - start_time
            self._record_failure(operation_name, execution_time, e)

            # Handle and display user-friendly error message
            user_message = self._get_user_friendly_error_message(e, error_context)

            # Log the error
            logger.error(f"Failed {operation_type.value} operation: {operation_name} "
                        f"({execution_time:.3f}s) - {str(e)}")

            # Show error dialog if parent widget provided
            if parent_widget:
                show_error("Operation Failed", user_message, parent=parent_widget)

            # Re-raise exception unless suppressed
            if not suppress_exception:
                raise

            return None  # Return None when suppressing exceptions

    def _get_user_friendly_error_message(self, exception: Exception, context: Optional[str] = None) -> str:
        """
        Convert service exceptions to user-friendly error messages.

        Args:
            exception: The exception that occurred
            context: Additional context for the error

        Returns:
            User-friendly error message
        """
        # Context prefix if provided
        ctx_prefix = f"{context}: " if context else ""

        # Handle specific FinishedUnit service exceptions
        if isinstance(exception, FinishedUnitNotFoundError):
            return f"{ctx_prefix}The requested finished unit could not be found. It may have been deleted."

        if isinstance(exception, InvalidInventoryError):
            return f"{ctx_prefix}Invalid inventory operation. Please check the quantity and try again."

        if isinstance(exception, DuplicateSlugError):
            return f"{ctx_prefix}An item with this name already exists. Please choose a different name."

        if isinstance(exception, ReferencedUnitError):
            return f"{ctx_prefix}Cannot delete this item because it's being used in assemblies or packages."

        # Handle FinishedGood service exceptions
        if isinstance(exception, FinishedGoodNotFoundError):
            return f"{ctx_prefix}The requested assembly could not be found. It may have been deleted."

        if isinstance(exception, CircularReferenceError):
            return f"{ctx_prefix}Cannot create assembly: this would create a circular reference (assembly containing itself)."

        if isinstance(exception, InsufficientInventoryError):
            return f"{ctx_prefix}Insufficient inventory to complete this operation. Please check stock levels."

        if isinstance(exception, InvalidComponentError):
            return f"{ctx_prefix}Invalid component configuration. Please check the assembly components."

        if isinstance(exception, AssemblyIntegrityError):
            return f"{ctx_prefix}Assembly integrity check failed. Please verify the component relationships."

        # Handle general service exceptions
        if isinstance(exception, ValidationError):
            errors = getattr(exception, 'errors', [str(exception)])
            error_list = '\n• '.join(errors)
            return f"{ctx_prefix}Please correct the following issues:\n• {error_list}"

        if isinstance(exception, DatabaseError):
            return f"{ctx_prefix}A database error occurred. Please try again or contact support if the problem persists."

        if isinstance(exception, IngredientNotFoundBySlug):
            return f"{ctx_prefix}The specified ingredient could not be found."

        if isinstance(exception, VariantNotFound):
            return f"{ctx_prefix}The ingredient variant could not be found. It may have been deleted."

        if isinstance(exception, SlugAlreadyExists):
            return f"{ctx_prefix}An ingredient with this name already exists. Please choose a different name."

        if isinstance(exception, VariantInUse):
            deps = getattr(exception, 'dependencies', {})
            dep_list = ', '.join(f"{count} {entity}" for entity, count in deps.items() if count > 0)
            return f"{ctx_prefix}Cannot delete this variant: it's being used in {dep_list}."

        # Handle legacy service exceptions
        if isinstance(exception, ServiceException) or isinstance(exception, ServiceError):
            return f"{ctx_prefix}{str(exception)}"

        # Generic error fallback
        return f"{ctx_prefix}An unexpected error occurred: {str(exception)}"

    def _record_success(self, operation_name: str, execution_time: float) -> None:
        """Record a successful operation for monitoring."""
        with self._lock:
            self.operation_stats["total_operations"] += 1
            self.operation_stats["successful_operations"] += 1
            self.operation_stats["last_operation_time"] = datetime.utcnow().isoformat()
            self.operation_stats["operation_times"].append(execution_time)
            # Automatic trimming handled by deque maxlen

    def _record_failure(self, operation_name: str, execution_time: float, exception: Exception) -> None:
        """Record a failed operation for monitoring."""
        with self._lock:
            self.operation_stats["total_operations"] += 1
            self.operation_stats["failed_operations"] += 1
            self.operation_stats["last_operation_time"] = datetime.utcnow().isoformat()
            self.operation_stats["operation_times"].append(execution_time)
            # Automatic trimming handled by deque maxlen

    def _log_with_level(self, log_level: int, message: str) -> None:
        """Log a message using the appropriate logging method based on level."""
        if log_level == logging.DEBUG:
            logger.debug(message)
        elif log_level == logging.INFO:
            logger.info(message)
        elif log_level == logging.WARNING:
            logger.warning(message)
        elif log_level == logging.ERROR:
            logger.error(message)
        elif log_level == logging.CRITICAL:
            logger.critical(message)
        else:
            # Fallback for custom log levels
            logger.log(log_level, message)

    def get_operation_statistics(self) -> Dict[str, Any]:
        """
        Get operation statistics for monitoring and debugging.

        Returns:
            Dictionary with operation statistics
        """
        with self._lock:
            total_ops = self.operation_stats["total_operations"]
            success_rate = (self.operation_stats["successful_operations"] / total_ops * 100) if total_ops > 0 else 0
            failure_rate = (self.operation_stats["failed_operations"] / total_ops * 100) if total_ops > 0 else 0

            avg_time = 0
            if self.operation_stats["operation_times"]:
                avg_time = sum(self.operation_stats["operation_times"]) / len(self.operation_stats["operation_times"])

            return {
                "total_operations": total_ops,
                "successful_operations": self.operation_stats["successful_operations"],
                "failed_operations": self.operation_stats["failed_operations"],
                "success_rate": round(success_rate, 2),
                "failure_rate": round(failure_rate, 2),
                "average_operation_time": round(avg_time, 3),
                "last_operation_time": self.operation_stats["last_operation_time"]
            }

    def reset_statistics(self) -> None:
        """Reset operation statistics."""
        with self._lock:
            self.operation_stats = {
                "total_operations": 0,
                "successful_operations": 0,
                "failed_operations": 0,
                "last_operation_time": None,
                "operation_times": deque(maxlen=100)  # Use deque for consistency
            }


# Global service integrator instance
_service_integrator = UIServiceIntegrator()


def get_ui_service_integrator() -> UIServiceIntegrator:
    """Get the global UI service integrator instance."""
    return _service_integrator


def ui_service_operation(operation_name: str, operation_type: OperationType,
                        success_message: Optional[str] = None,
                        error_context: Optional[str] = None,
                        show_success_dialog: bool = False,
                        log_level: int = logging.INFO) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator for UI service operations with automatic error handling.

    Args:
        operation_name: Human-readable name of the operation
        operation_type: Type of operation for logging
        success_message: Optional success message to display
        error_context: Additional context for error messages
        show_success_dialog: Whether to show success dialog
        log_level: Logging level for the operation

    Returns:
        Decorated function with service integration
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Extract parent widget from common UI patterns
            parent_widget = None
            if args and hasattr(args[0], 'winfo_class'):  # First arg is likely a widget
                parent_widget = args[0]
            elif 'parent' in kwargs:
                parent_widget = kwargs['parent']

            integrator = get_ui_service_integrator()

            return integrator.execute_service_operation(
                operation_name=operation_name,
                operation_type=operation_type,
                service_function=lambda: func(*args, **kwargs),
                parent_widget=parent_widget,
                success_message=success_message,
                error_context=error_context,
                show_success_dialog=show_success_dialog,
                log_level=log_level
            )
        return wrapper
    return decorator


# Assembly Management Architecture Support

class AssemblyUIHelper:
    """
    Helper class for assembly management UI features.

    Provides utilities to support future assembly management capabilities
    in the FinishedGood service layer.
    """

    @staticmethod
    def validate_assembly_components(components: list) -> bool:
        """
        Validate assembly component configuration.

        Args:
            components: List of component dictionaries

        Returns:
            True if valid, False otherwise
        """
        if not components:
            return False

        for component in components:
            if not all(key in component for key in ['component_type', 'component_id', 'quantity']):
                return False

            if component['component_type'] not in [ComponentType.FINISHED_UNIT.value, ComponentType.FINISHED_GOOD.value]:
                return False

            if not isinstance(component['quantity'], (int, float)) or component['quantity'] <= 0:
                return False

        return True

    @staticmethod
    def format_component_display(component: dict) -> str:
        """
        Format component for display in UI.

        Args:
            component: Component dictionary

        Returns:
            Formatted display string
        """
        component_type = component.get('component_type', 'unknown')
        quantity = component.get('quantity', 0)
        name = component.get('name', f"ID: {component.get('component_id', 'unknown')}")

        return f"{quantity}x {name} ({component_type.replace('_', ' ').title()})"

    @staticmethod
    def calculate_assembly_cost(components: list, component_costs: dict) -> float:
        """
        Calculate total assembly cost from components.

        Args:
            components: List of component dictionaries
            component_costs: Dict mapping component_id to cost per unit

        Returns:
            Total assembly cost
        """
        total_cost = 0.0

        for component in components:
            component_id = component.get('component_id')
            quantity = component.get('quantity', 0)

            if component_id in component_costs:
                total_cost += component_costs[component_id] * quantity

        return total_cost


def get_assembly_ui_helper() -> AssemblyUIHelper:
    """Get the assembly UI helper instance."""
    return AssemblyUIHelper()


# Service Integration Status Monitoring

def check_service_integration_health() -> Dict[str, Any]:
    """
    Check the health of UI service integrations.

    Returns:
        Dictionary with integration health status
    """
    integrator = get_ui_service_integrator()
    stats = integrator.get_operation_statistics()

    # Determine health status
    health_status = "healthy"
    if stats["total_operations"] > 0:
        if stats["failure_rate"] > 10:
            health_status = "unhealthy"
        elif stats["failure_rate"] > 5:
            health_status = "degraded"

    return {
        "status": health_status,
        "timestamp": datetime.utcnow().isoformat(),
        "statistics": stats,
        "recommendations": _get_health_recommendations(stats)
    }


def _get_health_recommendations(stats: Dict[str, Any]) -> list:
    """
    Get recommendations based on service integration health.

    Args:
        stats: Operation statistics

    Returns:
        List of recommendation strings
    """
    recommendations = []

    if stats["failure_rate"] > HealthThresholds.UNHEALTHY_FAILURE_RATE:
        recommendations.append("High failure rate detected. Check error logs for recurring issues.")

    if stats["average_operation_time"] > HealthThresholds.SLOW_OPERATION_TIME:
        recommendations.append("Slow operations detected. Consider optimizing service calls.")

    if stats["total_operations"] == 0:
        recommendations.append("No operations recorded. Ensure service integration is working.")

    return recommendations