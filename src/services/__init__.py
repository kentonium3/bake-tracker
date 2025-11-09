"""Services package - Business logic layer for Bake Tracker.

This package contains all service modules that provide business logic
and database operations for the application.

Architecture:
- Services: Stateless functions organized by domain (ingredient, variant, pantry, purchase)
- Transactions: Managed via session_scope() context manager
- Exceptions: Consistent error handling via ServiceError hierarchy
- Validation: Input validation before database operations

Service Modules:
- ingredient_service: Ingredient catalog CRUD operations
- variant_service: Brand/package variant management
- pantry_service: Inventory tracking with FIFO consumption
- purchase_service: Price history tracking and trend analysis
- recipe_service: Recipe management
- event_service: Event planning
- finished_good_service: Finished good tracking
- package_service: Package management
- recipient_service: Recipient management
- inventory_service: Inventory operations

Infrastructure:
- exceptions: Custom exception classes for service layer errors
- database: Session management and database utilities
- unit_converter: Unit conversion utilities
"""

# Service modules
from . import (
    database,
    inventory_service,
    recipe_service,
    unit_converter,
    finished_good_service,
    package_service,
    recipient_service,
    event_service,
)

# Infrastructure exports for new service layer
from .exceptions import (
    ServiceError,
    ServiceException,  # Legacy
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

from .database import session_scope

__all__ = [
    # Service modules
    "database",
    "inventory_service",
    "recipe_service",
    "unit_converter",
    "finished_good_service",
    "package_service",
    "recipient_service",
    "event_service",
    # Infrastructure - Exception hierarchy
    "ServiceError",
    "ServiceException",
    "IngredientNotFoundBySlug",
    "VariantNotFound",
    "PantryItemNotFound",
    "PurchaseNotFound",
    "SlugAlreadyExists",
    "IngredientInUse",
    "VariantInUse",
    "ValidationError",
    "DatabaseError",
    # Infrastructure - Session management
    "session_scope",
]
