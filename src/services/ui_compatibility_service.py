"""
UI Compatibility Service for smooth FinishedGood → FinishedUnit migration.

This service provides a compatibility layer during the transition period,
ensuring that UI operations continue to work even if there are issues
with the new service implementations.

Features:
- API compatibility wrappers for UI integrations
- Fallback mechanisms for failed operations
- Transition monitoring and logging
- Gradual feature rollout capabilities
- Rollback mechanisms for UI issues
"""

import logging
import time
import random
import copy
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Callable, Protocol
from enum import Enum
import functools

# Conditional imports for forward compatibility (using module-level function pattern)
try:
    from . import finished_unit_service

    HAS_FINISHED_UNIT_SERVICE = True
except ImportError:
    # Create placeholder service module until FinishedUnit service is implemented
    class finished_unit_service:
        """Placeholder service module until FinishedUnit implementation is complete."""

        @staticmethod
        def get_all_finished_units():
            raise NotImplementedError("FinishedUnit service not yet implemented")

        @staticmethod
        def create_finished_unit(**kwargs):
            raise NotImplementedError("FinishedUnit service not yet implemented")

        @staticmethod
        def update_finished_unit(unit_id, **kwargs):
            raise NotImplementedError("FinishedUnit service not yet implemented")

        @staticmethod
        def delete_finished_unit(unit_id):
            raise NotImplementedError("FinishedUnit service not yet implemented")

        @staticmethod
        def update_inventory(unit_id, quantity_change):
            raise NotImplementedError("FinishedUnit service not yet implemented")

    HAS_FINISHED_UNIT_SERVICE = False

try:
    from . import finished_good_service

    HAS_FINISHED_GOOD_SERVICE = True
except ImportError:
    # Create placeholder service module until FinishedGood service is updated
    class finished_good_service:
        """Placeholder service module until FinishedGood service is updated."""

        @staticmethod
        def get_all_finished_goods():
            raise NotImplementedError("Enhanced FinishedGood service not yet implemented")

        @staticmethod
        def create_finished_good(**kwargs):
            raise NotImplementedError("Enhanced FinishedGood service not yet implemented")

    HAS_FINISHED_GOOD_SERVICE = False

from .exceptions import ServiceError, DatabaseError, ValidationError

# Conditional model imports
try:
    from ..models import FinishedUnit

    HAS_FINISHED_UNIT_MODEL = True
except ImportError:
    # Create placeholder model until FinishedUnit model is implemented
    class FinishedUnit:
        """Placeholder model until FinishedUnit implementation is complete."""

        pass

    HAS_FINISHED_UNIT_MODEL = False

try:
    from ..models import FinishedGood

    HAS_FINISHED_GOOD_MODEL = True
except ImportError:
    # Create placeholder model
    class FinishedGood:
        """Placeholder model."""

        pass

    HAS_FINISHED_GOOD_MODEL = False

try:
    from .deprecation_warnings import warn_deprecated_service_method

    HAS_DEPRECATION_WARNINGS = True
except ImportError:
    # Create placeholder warning function
    def warn_deprecated_service_method(*args, **kwargs):
        """Placeholder warning function until deprecation_warnings module is created."""
        pass

    HAS_DEPRECATION_WARNINGS = False

logger = logging.getLogger(__name__)


# Constants for compatibility thresholds
class CompatibilityThresholds:
    """Threshold constants for compatibility service monitoring and rollback decisions."""

    UNHEALTHY_FAILURE_RATE = 10.0  # percent - failure rate indicating unhealthy state
    DEGRADED_FALLBACK_RATE = 20.0  # percent - fallback usage indicating degraded performance
    ROLLBACK_FAILURE_RATE = 15.0  # percent - failure rate triggering automatic rollback
    MIN_OPERATIONS_FOR_ROLLBACK = 10  # minimum operations before rollback consideration


# Protocol definitions for type safety
class IndividualItemLike(Protocol):
    """Protocol for individual item objects (FinishedUnit or dict)."""

    id: int
    display_name: str
    slug: str
    inventory_count: int


class AssemblyItemLike(Protocol):
    """Protocol for assembly item objects (FinishedGood or dict)."""

    id: int
    display_name: str
    slug: str
    total_cost: float
    assembly_type: str


# Exception classes for better error handling
class CompatibilityOperationFailed(Exception):
    """Raised when a compatibility operation fails completely."""

    def __init__(self, operation_name: str, original_error: Optional[Exception] = None):
        self.operation_name = operation_name
        self.original_error = original_error
        message = f"Compatibility operation '{operation_name}' failed"
        if original_error:
            message += f": {original_error}"
        super().__init__(message)


class CompatibilityMode(Enum):
    """Compatibility operation modes."""

    NEW_ONLY = "new_only"  # Use only new services
    OLD_ONLY = "old_only"  # Use only legacy services (fallback)
    NEW_WITH_FALLBACK = "new_with_fallback"  # Try new, fallback to old
    GRADUAL_ROLLOUT = "gradual_rollout"  # Gradual migration


class TransitionStatus(Enum):
    """Status of transition operations."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FALLBACK_USED = "fallback_used"
    FAILED = "failed"


class UICompatibilityService:
    """
    Compatibility service for smooth UI migration.

    Provides safe wrappers around new service implementations with
    fallback capabilities and monitoring.
    """

    def __init__(self):
        """Initialize the compatibility service."""
        self.mode = CompatibilityMode.NEW_WITH_FALLBACK
        self.rollout_percentage = 100  # Percentage of operations to use new service
        self.operation_stats = {
            "new_success": 0,
            "new_failure": 0,
            "fallback_used": 0,
            "total_operations": 0,
        }

    def set_compatibility_mode(self, mode: CompatibilityMode) -> None:
        """Set the compatibility mode for operations."""
        self.mode = mode
        logger.info(f"UI Compatibility mode set to: {mode.value}")

    def set_rollout_percentage(self, percentage: int) -> None:
        """Set the percentage of operations that should use new services."""
        if not isinstance(percentage, int):
            raise TypeError(
                f"Rollout percentage must be an integer, got {type(percentage).__name__}"
            )
        if not 0 <= percentage <= 100:
            raise ValueError(f"Rollout percentage must be between 0 and 100, got {percentage}")
        self.rollout_percentage = percentage
        logger.info(f"UI Compatibility rollout percentage set to: {percentage}%")

    def should_use_new_service(self) -> bool:
        """Determine if we should use the new service based on rollout percentage."""
        if self.mode == CompatibilityMode.OLD_ONLY:
            return False
        if self.mode == CompatibilityMode.NEW_ONLY:
            return True
        if self.mode == CompatibilityMode.GRADUAL_ROLLOUT:
            return random.randint(1, 100) <= self.rollout_percentage
        return True  # NEW_WITH_FALLBACK uses new by default

    def record_operation_result(
        self,
        operation: str,
        status: TransitionStatus,
        execution_time: float,
        error: Optional[Exception] = None,
    ) -> None:
        """Record the result of a compatibility operation for monitoring."""
        self.operation_stats["total_operations"] += 1

        if status == TransitionStatus.SUCCESS:
            self.operation_stats["new_success"] += 1
        elif status == TransitionStatus.FALLBACK_USED:
            self.operation_stats["fallback_used"] += 1
        elif status == TransitionStatus.FAILED:
            self.operation_stats["new_failure"] += 1

        logger.info(
            f"UI Compatibility Operation: {operation} - {status.value} " f"({execution_time:.3f}s)"
        )

        if error:
            logger.warning(f"UI Compatibility Error in {operation}: {error}")

    def safe_operation(
        self,
        operation_name: str,
        new_operation: Callable,
        fallback_operation: Optional[Callable] = None,
        default_return: Any = None,
        raise_on_failure: bool = False,
    ) -> Any:
        """
        Execute an operation safely with fallback capabilities.

        Args:
            operation_name: Name of the operation for logging
            new_operation: New service operation to try
            fallback_operation: Legacy operation to fall back to
            default_return: Default value if all operations fail (ignored if raise_on_failure=True)
            raise_on_failure: If True, raise CompatibilityOperationFailed instead of returning default

        Returns:
            Result of the operation or default value

        Raises:
            CompatibilityOperationFailed: If raise_on_failure=True and all operations fail
        """
        start_time = time.time()

        if not self.should_use_new_service():
            if fallback_operation:
                try:
                    result = fallback_operation()
                    execution_time = time.time() - start_time
                    self.record_operation_result(
                        operation_name, TransitionStatus.FALLBACK_USED, execution_time
                    )
                    return result
                except Exception as e:
                    execution_time = time.time() - start_time
                    self.record_operation_result(
                        operation_name, TransitionStatus.FAILED, execution_time, e
                    )
                    logger.error(f"Fallback operation failed for {operation_name}: {e}")
                    if raise_on_failure:
                        raise CompatibilityOperationFailed(operation_name, e)
                    return default_return

        # Try new operation first
        try:
            result = new_operation()
            execution_time = time.time() - start_time
            self.record_operation_result(operation_name, TransitionStatus.SUCCESS, execution_time)
            return result

        except Exception as e:
            logger.warning(f"New operation failed for {operation_name}: {e}")

            # Try fallback if available and not in NEW_ONLY mode
            if fallback_operation and self.mode != CompatibilityMode.NEW_ONLY:
                try:
                    result = fallback_operation()
                    execution_time = time.time() - start_time
                    self.record_operation_result(
                        operation_name, TransitionStatus.FALLBACK_USED, execution_time
                    )
                    logger.info(f"Successfully used fallback for {operation_name}")
                    return result

                except Exception as fallback_error:
                    execution_time = time.time() - start_time
                    self.record_operation_result(
                        operation_name, TransitionStatus.FAILED, execution_time, fallback_error
                    )
                    logger.error(f"Both new and fallback operations failed for {operation_name}")
                    # Use the fallback error as the final error
                    e = fallback_error
            else:
                execution_time = time.time() - start_time
                self.record_operation_result(
                    operation_name, TransitionStatus.FAILED, execution_time, e
                )

        # Final failure handling
        if raise_on_failure:
            raise CompatibilityOperationFailed(operation_name, e)
        return default_return

    # Individual Item Operations (FinishedUnit compatibility)

    def get_all_individual_items(self) -> List[IndividualItemLike]:
        """Get all individual items with compatibility fallback."""
        return self.safe_operation(
            operation_name="get_all_individual_items",
            new_operation=lambda: finished_unit_service.get_all_finished_units(),
            default_return=[],
        )

    def create_individual_item(self, item_data: Dict[str, Any]) -> Optional[IndividualItemLike]:
        """Create an individual item with compatibility fallback."""
        return self.safe_operation(
            operation_name="create_individual_item",
            new_operation=lambda: finished_unit_service.create_finished_unit(**item_data),
            default_return=None,
        )

    def update_individual_item(
        self, item_id: int, updates: Dict[str, Any]
    ) -> Optional[IndividualItemLike]:
        """Update an individual item with compatibility fallback."""
        return self.safe_operation(
            operation_name="update_individual_item",
            new_operation=lambda: finished_unit_service.update_finished_unit(item_id, **updates),
            default_return=None,
        )

    def delete_individual_item(self, item_id: int) -> bool:
        """Delete an individual item with compatibility fallback."""
        return self.safe_operation(
            operation_name="delete_individual_item",
            new_operation=lambda: finished_unit_service.delete_finished_unit(item_id),
            default_return=False,
        )

    def update_item_inventory(
        self, item_id: int, quantity_change: int
    ) -> Optional[IndividualItemLike]:
        """Update item inventory with compatibility fallback."""
        return self.safe_operation(
            operation_name="update_item_inventory",
            new_operation=lambda: finished_unit_service.update_inventory(item_id, quantity_change),
            default_return=None,
        )

    # Assembly Operations (FinishedGood compatibility)

    def get_all_assemblies(self) -> List[AssemblyItemLike]:
        """Get all assemblies with compatibility fallback."""
        return self.safe_operation(
            operation_name="get_all_assemblies",
            new_operation=lambda: finished_good_service.get_all_finished_goods(),
            default_return=[],
        )

    def create_assembly(self, assembly_data: Dict[str, Any]) -> Optional[AssemblyItemLike]:
        """Create an assembly with compatibility fallback."""
        return self.safe_operation(
            operation_name="create_assembly",
            new_operation=lambda: finished_good_service.create_finished_good(**assembly_data),
            default_return=None,
        )

    # Monitoring and Health Check Operations

    def get_migration_health_status(self) -> Dict[str, Any]:
        """Get current migration health status."""
        total_ops = self.operation_stats["total_operations"]
        success_rate = (
            (self.operation_stats["new_success"] / total_ops * 100) if total_ops > 0 else 0
        )
        fallback_rate = (
            (self.operation_stats["fallback_used"] / total_ops * 100) if total_ops > 0 else 0
        )
        failure_rate = (
            (self.operation_stats["new_failure"] / total_ops * 100) if total_ops > 0 else 0
        )

        health_status = "healthy"
        if failure_rate > CompatibilityThresholds.UNHEALTHY_FAILURE_RATE:
            health_status = "unhealthy"
        elif fallback_rate > CompatibilityThresholds.DEGRADED_FALLBACK_RATE:
            health_status = "degraded"

        return {
            "status": health_status,
            "mode": self.mode.value,
            "rollout_percentage": self.rollout_percentage,
            "statistics": {
                "total_operations": total_ops,
                "success_rate": round(success_rate, 2),
                "fallback_rate": round(fallback_rate, 2),
                "failure_rate": round(failure_rate, 2),
            },
            "raw_stats": copy.deepcopy(self.operation_stats),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def should_rollback(self) -> bool:
        """Determine if we should recommend a rollback based on health metrics."""
        total_ops = self.operation_stats["total_operations"]
        if total_ops < CompatibilityThresholds.MIN_OPERATIONS_FOR_ROLLBACK:  # Not enough data
            return False

        failure_rate = self.operation_stats["new_failure"] / total_ops
        return failure_rate > (
            CompatibilityThresholds.ROLLBACK_FAILURE_RATE / 100
        )  # Convert percentage to decimal

    def emergency_rollback_to_legacy(self) -> None:
        """Emergency rollback to legacy services only."""
        self.mode = CompatibilityMode.OLD_ONLY
        self.rollout_percentage = 0
        logger.error("EMERGENCY ROLLBACK: Switched to legacy-only mode due to high failure rate")

    def reset_statistics(self) -> None:
        """Reset operation statistics."""
        self.operation_stats = {
            "new_success": 0,
            "new_failure": 0,
            "fallback_used": 0,
            "total_operations": 0,
        }
        logger.info("UI Compatibility statistics reset")


# Global compatibility service instance
_compatibility_service = UICompatibilityService()


def get_ui_compatibility_service() -> UICompatibilityService:
    """Get the global UI compatibility service instance."""
    return _compatibility_service


def ui_safe_operation(
    operation_name: str, fallback_return: Any = None, fallback_operation: Optional[Callable] = None
):
    """
    Decorator to make UI operations safe with automatic compatibility handling.

    Args:
        operation_name: Name of the operation for monitoring
        fallback_return: Value to return if operation fails
        fallback_operation: Optional fallback operation to try if main operation fails

    Returns:
        Decorated function with compatibility layer
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            compatibility_service = get_ui_compatibility_service()

            return compatibility_service.safe_operation(
                operation_name=operation_name,
                new_operation=lambda: func(*args, **kwargs),
                fallback_operation=fallback_operation,
                default_return=fallback_return,
            )

        return wrapper

    return decorator


def configure_ui_compatibility(
    mode: CompatibilityMode = CompatibilityMode.NEW_WITH_FALLBACK, rollout_percentage: int = 100
) -> None:
    """
    Configure the UI compatibility layer.

    Args:
        mode: Compatibility mode to use
        rollout_percentage: Percentage of operations to use new services
    """
    compatibility_service = get_ui_compatibility_service()
    compatibility_service.set_compatibility_mode(mode)
    compatibility_service.set_rollout_percentage(rollout_percentage)


def check_migration_health() -> Dict[str, Any]:
    """Check the health of the UI migration."""
    compatibility_service = get_ui_compatibility_service()
    health_status = compatibility_service.get_migration_health_status()

    # Auto-rollback if health is critical
    if compatibility_service.should_rollback():
        compatibility_service.emergency_rollback_to_legacy()
        health_status["auto_rollback_triggered"] = True

    return health_status


def reset_migration_stats() -> None:
    """Reset migration statistics for fresh monitoring."""
    compatibility_service = get_ui_compatibility_service()
    compatibility_service.reset_statistics()
