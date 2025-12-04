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
    event_service,  # Re-enabled Feature 006: Uses FinishedGood not Bundle
    production_service,  # Feature 008: Production tracking
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

# Production services (Feature 008)
from .production_service import (
    record_production,
    get_production_records,
    get_production_total,
    can_assemble_package,
    update_package_status,
    get_production_progress,
    get_dashboard_summary,
    get_recipe_cost_breakdown,
    # Exceptions
    InsufficientInventoryError as ProductionInsufficientInventoryError,
    RecipeNotFoundError as ProductionRecipeNotFoundError,
    ProductionExceedsPlannedError,
    InvalidStatusTransitionError,
    IncompleteProductionError,
    AssignmentNotFoundError as ProductionAssignmentNotFoundError,
)

# Event services (Feature 006)
from .event_service import (
    create_event,
    get_event_by_id,
    get_event_by_name,
    get_all_events,
    get_events_by_year,
    get_available_years,
    update_event,
    delete_event,
    assign_package_to_recipient,
    update_assignment,
    remove_assignment,
    get_event_assignments,
    get_event_total_cost,
    get_event_recipient_count,
    get_event_package_count,
    get_event_summary,
    get_recipe_needs,
    get_shopping_list,
    clone_event,
    get_recipient_history,
    get_recipient_assignments_for_event,
    # Exceptions
    EventNotFoundError,
    EventHasAssignmentsError,
    AssignmentNotFoundError,
    RecipientNotFoundError,
    DuplicateAssignmentError,
)

# Recipient services (Feature 006)
from .recipient_service import (
    create_recipient,
    get_recipient,
    get_recipient_by_name,
    get_all_recipients,
    update_recipient,
    delete_recipient,
    check_recipient_has_assignments,
    get_recipient_assignment_count,
    get_recipient_events,
    search_recipients,
    get_recipients_by_household,
    # Exceptions
    RecipientNotFound,
    RecipientInUse,
    RecipientHasAssignmentsError,
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
    "event_service",  # Re-enabled Feature 006
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
    # Event services (Feature 006)
    "create_event",
    "get_event_by_id",
    "get_event_by_name",
    "get_all_events",
    "get_events_by_year",
    "get_available_years",
    "update_event",
    "delete_event",
    "assign_package_to_recipient",
    "update_assignment",
    "remove_assignment",
    "get_event_assignments",
    "get_event_total_cost",
    "get_event_recipient_count",
    "get_event_package_count",
    "get_event_summary",
    "get_recipe_needs",
    "get_shopping_list",
    "clone_event",
    "get_recipient_history",
    "EventNotFoundError",
    "EventHasAssignmentsError",
    "AssignmentNotFoundError",
    "RecipientNotFoundError",
    "DuplicateAssignmentError",
    # Recipient services (Feature 006)
    "create_recipient",
    "get_recipient",
    "get_recipient_by_name",
    "get_all_recipients",
    "update_recipient",
    "delete_recipient",
    "check_recipient_has_assignments",
    "get_recipient_assignment_count",
    "get_recipient_events",
    "search_recipients",
    "get_recipients_by_household",
    "RecipientNotFound",
    "RecipientInUse",
    "RecipientHasAssignmentsError",
    # Production services (Feature 008)
    "production_service",
    "record_production",
    "get_production_records",
    "get_production_total",
    "can_assemble_package",
    "update_package_status",
    "get_production_progress",
    "get_dashboard_summary",
    "get_recipe_cost_breakdown",
    "ProductionInsufficientInventoryError",
    "ProductionRecipeNotFoundError",
    "ProductionExceedsPlannedError",
    "InvalidStatusTransitionError",
    "IncompleteProductionError",
    "ProductionAssignmentNotFoundError",
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
