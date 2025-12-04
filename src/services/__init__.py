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
    package_service,  # Re-enabled Feature 006: Uses FinishedGood not Bundle
    recipient_service,
    # event_service,  # DISABLED: Will be re-enabled in WP04
)

# Migration services
from .migration_service import MigrationService

# FinishedUnit services
from .finished_unit_service import (
    FinishedUnitService,
    get_finished_unit_count,
    get_finished_unit_by_id,
    get_finished_unit_by_slug,
    get_all_finished_units,
    create_finished_unit,
    update_finished_unit,
    delete_finished_unit,
    update_inventory,
    check_availability,
    calculate_unit_cost,
    search_finished_units,
    get_units_by_recipe,
    # Exceptions
    FinishedUnitNotFoundError,
    InvalidInventoryError,
    DuplicateSlugError,
    ReferencedUnitError,
)

# FinishedGood services
from .finished_good_service import (
    FinishedGoodService,
    get_finished_good_by_id,
    get_finished_good_by_slug,
    get_all_finished_goods,
    create_finished_good,
    add_component,
    search_finished_goods,
    get_assemblies_by_type,
    # Exceptions
    FinishedGoodNotFoundError,
    CircularReferenceError,
    InsufficientInventoryError,
    InvalidComponentError,
    AssemblyIntegrityError,
)

# Package services (Feature 006)
from .package_service import (
    create_package,
    get_package_by_id,
    get_package_by_name,
    get_all_packages,
    update_package,
    delete_package,
    add_finished_good_to_package,
    remove_finished_good_from_package,
    update_finished_good_quantity,
    get_package_contents,
    calculate_package_cost,
    get_package_cost_breakdown,
    search_packages,
    get_template_packages,
    get_packages_containing_finished_good,
    check_package_has_event_assignments,
    get_package_event_assignment_count,
    duplicate_package,
    # Exceptions
    PackageNotFoundError,
    PackageInUseError,
    InvalidFinishedGoodError,
    DuplicatePackageNameError,
    PackageFinishedGoodNotFoundError,
)

# Composition services
from .composition_service import (
    CompositionService,
    create_composition,
    get_composition_by_id,
    get_assembly_components,
    get_component_usages,
    validate_no_circular_reference,
    flatten_assembly_components,
    # Exceptions
    CompositionNotFoundError,
    InvalidComponentTypeError,
    DuplicateCompositionError,
    IntegrityViolationError,
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
    "package_service",  # Re-enabled Feature 006
    "recipient_service",
    # "event_service",  # Will be re-enabled in WP04
    # Migration services
    "MigrationService",
    # FinishedUnit services
    "FinishedUnitService",
    "get_finished_unit_count",
    "get_finished_unit_by_id",
    "get_finished_unit_by_slug",
    "get_all_finished_units",
    "create_finished_unit",
    "update_finished_unit",
    "delete_finished_unit",
    "update_inventory",
    "check_availability",
    "calculate_unit_cost",
    "search_finished_units",
    "get_units_by_recipe",
    "FinishedUnitNotFoundError",
    "InvalidInventoryError",
    "DuplicateSlugError",
    "ReferencedUnitError",
    # FinishedGood services
    "FinishedGoodService",
    "get_finished_good_by_id",
    "get_finished_good_by_slug",
    "get_all_finished_goods",
    "create_finished_good",
    "add_component",
    "search_finished_goods",
    "get_assemblies_by_type",
    "FinishedGoodNotFoundError",
    "CircularReferenceError",
    "InsufficientInventoryError",
    "InvalidComponentError",
    "AssemblyIntegrityError",
    # Composition services
    "CompositionService",
    "create_composition",
    "get_composition_by_id",
    "get_assembly_components",
    "get_component_usages",
    "validate_no_circular_reference",
    "flatten_assembly_components",
    "CompositionNotFoundError",
    "InvalidComponentTypeError",
    "DuplicateCompositionError",
    "IntegrityViolationError",
    # Package services (Feature 006)
    "create_package",
    "get_package_by_id",
    "get_package_by_name",
    "get_all_packages",
    "update_package",
    "delete_package",
    "add_finished_good_to_package",
    "remove_finished_good_from_package",
    "update_finished_good_quantity",
    "get_package_contents",
    "calculate_package_cost",
    "get_package_cost_breakdown",
    "search_packages",
    "get_template_packages",
    "get_packages_containing_finished_good",
    "check_package_has_event_assignments",
    "get_package_event_assignment_count",
    "duplicate_package",
    "PackageNotFoundError",
    "PackageInUseError",
    "InvalidFinishedGoodError",
    "DuplicatePackageNameError",
    "PackageFinishedGoodNotFoundError",
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
