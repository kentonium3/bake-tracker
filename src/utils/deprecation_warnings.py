"""
Deprecation warning utilities for tracking legacy API usage during migration.

This module provides utilities for warning users about deprecated functionality
during the FinishedGood → FinishedUnit migration process.
"""

import warnings
import logging
from datetime import datetime
from src.utils.datetime_utils import utc_now
from typing import Optional, Dict, Any
import functools

logger = logging.getLogger(__name__)

# Migration timeline constants
MIGRATION_START_DATE = "2025-11-15"
PLANNED_REMOVAL_DATE = "2025-12-15"  # 30 days from start


class DeprecationCategory:
    """Categories for different types of deprecation warnings."""

    UI_COMPONENT = "ui_component"
    SERVICE_METHOD = "service_method"
    MODEL_USAGE = "model_usage"
    DATA_FORMAT = "data_format"


class LegacyAPIWarning(UserWarning):
    """Custom warning class for legacy API usage."""

    pass


def warn_deprecated_ui_component(
    component_name: str, replacement: str, removal_version: str = "v0.5.0"
) -> None:
    """
    Warn about deprecated UI component usage.

    Args:
        component_name: Name of the deprecated component
        replacement: Name of the replacement component
        removal_version: Version when the component will be removed
    """
    message = (
        f"UI component '{component_name}' is deprecated and will be removed in {removal_version}. "
        f"Please migrate to '{replacement}'. "
        f"This change supports the new two-tier FinishedUnit/FinishedGood system. "
        f"See migration guide for details."
    )

    warnings.warn(message, LegacyAPIWarning, stacklevel=3)
    logger.warning(f"DEPRECATED UI: {component_name} -> {replacement}")


def warn_deprecated_service_method(
    method_name: str, replacement: str, removal_version: str = "v0.5.0"
) -> None:
    """
    Warn about deprecated service method usage.

    Args:
        method_name: Name of the deprecated method
        replacement: Name of the replacement method
        removal_version: Version when the method will be removed
    """
    message = (
        f"Service method '{method_name}' is deprecated and will be removed in {removal_version}. "
        f"Please use '{replacement}' instead. "
        f"This method does not support the new FinishedUnit model. "
        f"Migration timeline: removal planned for {PLANNED_REMOVAL_DATE}."
    )

    warnings.warn(message, LegacyAPIWarning, stacklevel=3)
    logger.warning(f"DEPRECATED SERVICE: {method_name} -> {replacement}")


def warn_deprecated_model_usage(
    model_name: str, context: str, replacement: str = "FinishedUnit"
) -> None:
    """
    Warn about deprecated model usage patterns.

    Args:
        model_name: Name of the deprecated model usage
        context: Context where the deprecation occurs
        replacement: Recommended replacement model
    """
    message = (
        f"Model usage '{model_name}' in '{context}' is deprecated. "
        f"Individual items should use '{replacement}' model instead. "
        f"FinishedGood is now reserved for assemblies/packages only. "
        f"Please update your code to use the correct model."
    )

    warnings.warn(message, LegacyAPIWarning, stacklevel=3)
    logger.warning(f"DEPRECATED MODEL: {model_name} in {context} -> {replacement}")


def deprecated_api(
    replacement: str,
    removal_version: str = "v0.5.0",
    category: str = DeprecationCategory.SERVICE_METHOD,
):
    """
    Decorator to mark API methods as deprecated.

    Args:
        replacement: Name of the replacement API
        removal_version: Version when the API will be removed
        category: Category of deprecation

    Returns:
        Decorated function with deprecation warning
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            message = (
                f"Function '{func.__name__}' is deprecated and will be removed in {removal_version}. "
                f"Use '{replacement}' instead. "
                f"Category: {category}"
            )
            warnings.warn(message, LegacyAPIWarning, stacklevel=2)
            logger.warning(f"DEPRECATED API CALL: {func.__name__} -> {replacement}")

            return func(*args, **kwargs)

        return wrapper

    return decorator


def log_legacy_usage_stats() -> Dict[str, Any]:
    """
    Get statistics about legacy API usage for migration tracking.

    Returns:
        Dictionary with usage statistics
    """
    # In a real implementation, this would query logging data
    # For now, return a placeholder structure
    return {
        "timestamp": utc_now().isoformat(),
        "deprecated_ui_components": {
            "FinishedGoodsTab": {"usage_count": 0, "last_used": None},
            "FinishedGoodFormDialog": {"usage_count": 0, "last_used": None},
        },
        "deprecated_service_methods": {
            "legacy_finished_good_operations": {"usage_count": 0, "last_used": None}
        },
        "migration_progress": {
            "start_date": MIGRATION_START_DATE,
            "planned_completion": PLANNED_REMOVAL_DATE,
            "components_migrated": 2,
            "components_remaining": 0,
        },
    }


def show_migration_status_message() -> str:
    """
    Generate a user-friendly migration status message.

    Returns:
        Status message for users
    """
    return (
        f"🔄 Migration in Progress: FinishedGood → FinishedUnit\n\n"
        f"The application is transitioning to a new two-tier system:\n"
        f"• FinishedUnit: Individual consumable items (cookies, brownies, etc.)\n"
        f"• FinishedGood: Package assemblies (gift boxes, variety packs, etc.)\n\n"
        f"Migration started: {MIGRATION_START_DATE}\n"
        f"Planned completion: {PLANNED_REMOVAL_DATE}\n\n"
        f"What's changing:\n"
        f"• 'Finished Goods' tab → 'Finished Units' tab (for individual items)\n"
        f"• 'Bundles' tab → enhanced for assembly management\n"
        f"• Improved inventory tracking and packaging capabilities\n\n"
        f"Your data is preserved during this transition."
    )


def configure_deprecation_warnings():
    """Configure deprecation warnings to be visible by default."""
    warnings.filterwarnings("always", category=LegacyAPIWarning)

    # Set up logger for deprecation tracking
    deprecation_logger = logging.getLogger(__name__)
    if not deprecation_logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - DEPRECATION - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        deprecation_logger.addHandler(handler)
        deprecation_logger.setLevel(logging.WARNING)


# Initialize deprecation warnings when module is imported
configure_deprecation_warnings()
