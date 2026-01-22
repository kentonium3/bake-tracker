"""Service layer logging utilities.

Provides structured logging functions for service operations, enabling
consistent log format and context across production, assembly, and other
service operations.

Usage:
    from src.services.logging_utils import get_service_logger, log_operation

    logger = get_service_logger(__name__)

    # Log successful operation
    log_operation(
        logger,
        operation="record_production",
        outcome="success",
        production_run_id=123,
        recipe_id=45,
    )

    # Log validation failure
    log_operation(
        logger,
        operation="check_can_produce",
        outcome="insufficient_inventory",
        recipe_id=45,
        missing_ingredients=["flour", "sugar"],
    )
"""

import logging
from typing import Any


def get_service_logger(name: str) -> logging.Logger:
    """
    Get a logger configured for service operations.

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        Configured logger instance with the 'bake_tracker.services' prefix.

    Example:
        >>> logger = get_service_logger(__name__)
        >>> logger.name
        'bake_tracker.services.batch_production_service'
    """
    # Extract just the module name if full path is provided
    if "." in name:
        name = name.split(".")[-1]
    return logging.getLogger(f"bake_tracker.services.{name}")


def log_operation(
    logger: logging.Logger,
    operation: str,
    outcome: str,
    level: int = logging.INFO,
    **context: Any,
) -> None:
    """
    Log a service operation with structured context.

    This function provides a consistent format for logging service operations,
    including the operation name, outcome, and any additional context fields.
    The context is passed via the 'extra' parameter for structured logging.

    Args:
        logger: Logger instance to use
        operation: Operation name (e.g., "record_production", "check_can_assemble")
        outcome: Outcome description (e.g., "success", "validation_failed", "error")
        level: Log level (default: INFO). Use DEBUG for verbose/frequent logs.
        **context: Additional context fields (entity IDs, error details, etc.)
            Common fields:
            - production_run_id: ID of created production run
            - assembly_run_id: ID of created assembly run
            - recipe_id: Recipe being processed
            - finished_good_id: Finished good being assembled
            - error: Error message if outcome is "error"
            - missing_ingredients: List of missing ingredients for check failures

    Example:
        >>> log_operation(
        ...     logger,
        ...     operation="record_batch_production",
        ...     outcome="success",
        ...     production_run_id=123,
        ...     recipe_id=45,
        ...     actual_yield=24,
        ... )
        # Logs: "record_batch_production: success" with extra context

        >>> log_operation(
        ...     logger,
        ...     operation="check_can_produce",
        ...     outcome="insufficient_inventory",
        ...     level=logging.WARNING,
        ...     recipe_id=45,
        ...     missing_ingredients=["flour"],
        ... )
        # Logs at WARNING level with missing ingredient context
    """
    extra = {
        "operation": operation,
        "outcome": outcome,
        **context,
    }
    logger.log(level, f"{operation}: {outcome}", extra=extra)
