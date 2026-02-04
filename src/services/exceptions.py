"""Service layer exception classes for Bake Tracker.

This module defines all custom exceptions used by the service layer to provide
consistent error handling across the application.

Exception Hierarchy:
    ServiceError (base - all service exceptions)
    ├── NotFoundError (404)
    │   ├── IngredientNotFoundBySlug
    │   ├── IngredientNotFound
    │   ├── ProductNotFound
    │   ├── InventoryItemNotFound
    │   ├── PurchaseNotFound
    │   ├── RecipeNotFound
    │   ├── RecipeNotFoundBySlug
    │   ├── RecipeNotFoundByName
    │   ├── EventNotFoundById
    │   ├── EventNotFoundByName
    │   ├── FinishedGoodNotFoundById
    │   ├── FinishedGoodNotFoundBySlug
    │   ├── FinishedUnitNotFoundById
    │   ├── FinishedUnitNotFoundBySlug
    │   ├── PackageNotFoundById
    │   ├── PackageNotFoundByName
    │   ├── CompositionNotFoundById
    │   ├── UnitNotFoundByCode
    │   ├── MaterialCategoryNotFound
    │   ├── MaterialSubcategoryNotFound
    │   ├── MaterialNotFound
    │   ├── MaterialProductNotFound
    │   ├── RecipientNotFoundByName
    │   └── SupplierNotFoundError
    ├── ValidationError (400)
    │   └── HierarchyValidationError
    │       ├── CircularReferenceError
    │       ├── MaxDepthExceededError
    │       └── NonLeafIngredientError
    ├── ConflictError (409)
    │   ├── SlugAlreadyExists
    │   ├── IngredientInUse
    │   └── ProductInUse
    ├── BusinessRuleError (422)
    │   └── InsufficientStock
    ├── ConversionError (400)
    ├── PlanStateError (409)
    └── DatabaseError (500)

HTTP Status Code Mapping:
    404 - Not Found (entity lookup failures)
    400 - Validation Error (input validation failures)
    409 - Conflict (duplicate, in-use, state conflicts)
    422 - Business Rule Violation (insufficient resources, business logic)
    500 - Server Error (database, unexpected errors)
"""

from typing import Any, Dict, List, Optional


class ServiceError(Exception):
    """Base exception for all service layer errors.

    All service-specific exceptions should inherit from this class.
    Provides correlation_id for tracing and http_status_code for web migration.

    Attributes:
        message: Human-readable error message
        correlation_id: Optional correlation ID for tracing (future use)
        http_status_code: HTTP status code for web migration (default 500)
        context: Additional structured context data

    Example:
        >>> raise ServiceError("Operation failed", correlation_id="abc-123")
        >>> raise ServiceError("Entity error", entity_id=123, slug="test")
    """

    http_status_code: int = 500  # Default for generic service errors

    def __init__(
        self,
        message: str = "",
        correlation_id: Optional[str] = None,
        **context: Any
    ):
        self.message = message
        self.correlation_id = correlation_id
        self.context: Dict[str, Any] = context
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Return exception as dictionary for logging/serialization."""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "correlation_id": self.correlation_id,
            "http_status_code": self.http_status_code,
            "context": self.context,
        }


class IngredientNotFound(ServiceError):
    """Raised when an ingredient cannot be found by ID.

    Args:
        ingredient_id: The ingredient ID that was not found
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise IngredientNotFound(123)
        IngredientNotFound: Ingredient with ID 123 not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, ingredient_id: int, correlation_id: Optional[str] = None):
        self.ingredient_id = ingredient_id
        super().__init__(
            f"Ingredient with ID {ingredient_id} not found",
            correlation_id=correlation_id,
            ingredient_id=ingredient_id
        )


class RecipeNotFound(ServiceError):
    """Raised when a recipe cannot be found by ID.

    Args:
        recipe_id: The recipe ID that was not found
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise RecipeNotFound(123)
        RecipeNotFound: Recipe with ID 123 not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, recipe_id: int, correlation_id: Optional[str] = None):
        self.recipe_id = recipe_id
        super().__init__(
            f"Recipe with ID {recipe_id} not found",
            correlation_id=correlation_id,
            recipe_id=recipe_id
        )


class IngredientInUse(ServiceError):
    """Raised when attempting to delete an ingredient that has dependencies.

    Args:
        identifier: Ingredient identifier (slug string or id int)
        deps: Either an int (recipe count for legacy) or dict with dependency counts
              e.g., {'recipes': 5, 'products': 3, 'inventory_items': 12, 'children': 2}
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> deps = {'recipes': 5, 'products': 3}
        >>> raise IngredientInUse("flour", deps)
        IngredientInUse: Cannot delete ingredient 'flour': used in 5 recipe(s), 3 product(s)

    HTTP Status: 409 Conflict
    """

    http_status_code = 409

    def __init__(self, identifier, deps, correlation_id: Optional[str] = None):
        self.identifier = identifier

        # Support both old (int) and new (dict) signatures
        if isinstance(deps, dict):
            self.deps = deps
            self.details = deps  # F035: Alias for UI access
            # Build descriptive message from all dependencies
            parts = []
            if deps.get("recipes", 0) > 0:
                parts.append(f"{deps['recipes']} recipe(s)")
            if deps.get("products", 0) > 0:
                parts.append(f"{deps['products']} product(s)")
            if deps.get("inventory_items", 0) > 0:
                parts.append(f"{deps['inventory_items']} inventory item(s)")
            if deps.get("children", 0) > 0:
                parts.append(f"{deps['children']} child ingredient(s)")
            deps_msg = ", ".join(parts) if parts else "related records"
        else:
            # Legacy: deps is just recipe_count (int)
            self.deps = {"recipes": deps}
            self.details = self.deps  # F035: Alias for UI access
            deps_msg = f"{deps} recipe(s)"

        super().__init__(
            f"Cannot delete ingredient '{identifier}': used in {deps_msg}",
            correlation_id=correlation_id,
            identifier=identifier,
            deps=self.deps
        )


class ValidationError(ServiceError):
    """Raised when data validation fails.

    Args:
        errors: List of validation error messages
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise ValidationError(["Name is required", "Slug is invalid"])
        ValidationError: Validation failed: Name is required; Slug is invalid

    HTTP Status: 400 Bad Request
    """

    http_status_code = 400

    def __init__(self, errors: list, correlation_id: Optional[str] = None):
        self.errors = errors
        error_msg = "; ".join(str(e) for e in errors)
        super().__init__(
            f"Validation failed: {error_msg}",
            correlation_id=correlation_id,
            errors=errors
        )


class InsufficientStock(ServiceError):
    """Raised when there is not enough ingredient stock for an operation.

    Args:
        ingredient_name: Name of the ingredient with insufficient stock
        required: Amount required for the operation
        available: Amount currently available
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise InsufficientStock("flour", required=100, available=50)
        InsufficientStock: Insufficient stock for flour: required 100, available 50

    HTTP Status: 422 Unprocessable Entity
    """

    http_status_code = 422

    def __init__(
        self,
        ingredient_name: str,
        required: float,
        available: float,
        correlation_id: Optional[str] = None
    ):
        self.ingredient_name = ingredient_name
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient stock for {ingredient_name}: required {required}, available {available}",
            correlation_id=correlation_id,
            ingredient_name=ingredient_name,
            required=required,
            available=available
        )


class DatabaseError(ServiceError):
    """Raised when a database operation fails.

    Args:
        message: Description of the database error
        original_error: The underlying exception that caused this error
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise DatabaseError("Connection failed", original_error=e)
        DatabaseError: Database error: Connection failed

    HTTP Status: 500 Internal Server Error
    """

    http_status_code = 500

    def __init__(
        self,
        message: str,
        original_error: Exception = None,
        correlation_id: Optional[str] = None
    ):
        self.original_error = original_error
        super().__init__(
            f"Database error: {message}",
            correlation_id=correlation_id,
            original_error=str(original_error) if original_error else None
        )


# New Service Layer Exceptions (Ingredient/Product/InventoryItem/Purchase Services)


class IngredientNotFoundBySlug(ServiceError):
    """Raised when ingredient cannot be found by slug.

    Args:
        slug: The ingredient slug that was not found
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise IngredientNotFoundBySlug("all_purpose_flour")
        IngredientNotFoundBySlug: Ingredient 'all_purpose_flour' not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, slug: str, correlation_id: Optional[str] = None):
        self.slug = slug
        super().__init__(
            f"Ingredient '{slug}' not found",
            correlation_id=correlation_id,
            slug=slug
        )


class ProductNotFound(ServiceError):
    """Raised when product cannot be found by ID.

    Args:
        product_id: The product ID that was not found
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise ProductNotFound(123)
        ProductNotFound: Product with ID 123 not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, product_id: int, correlation_id: Optional[str] = None):
        self.product_id = product_id
        super().__init__(
            f"Product with ID {product_id} not found",
            correlation_id=correlation_id,
            product_id=product_id
        )


class InventoryItemNotFound(ServiceError):
    """Raised when inventory item cannot be found by ID.

    Args:
        inventory_item_id: The inventory item ID that was not found
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise InventoryItemNotFound(456)
        InventoryItemNotFound: Inventory item with ID 456 not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, inventory_item_id: int, correlation_id: Optional[str] = None):
        self.inventory_item_id = inventory_item_id
        super().__init__(
            f"Inventory item with ID {inventory_item_id} not found",
            correlation_id=correlation_id,
            inventory_item_id=inventory_item_id
        )


class MaterialInventoryItemNotFoundError(ServiceError):
    """Raised when material inventory item cannot be found by ID.

    Args:
        inventory_item_id: The material inventory item ID that was not found
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise MaterialInventoryItemNotFoundError(123)
        MaterialInventoryItemNotFoundError: Material inventory item with ID 123 not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, inventory_item_id: int, correlation_id: Optional[str] = None):
        self.inventory_item_id = inventory_item_id
        super().__init__(
            f"Material inventory item with ID {inventory_item_id} not found",
            correlation_id=correlation_id,
            inventory_item_id=inventory_item_id
        )


class PurchaseNotFound(ServiceError):
    """Raised when purchase record cannot be found by ID.

    Args:
        purchase_id: The purchase ID that was not found
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise PurchaseNotFound(789)
        PurchaseNotFound: Purchase with ID 789 not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, purchase_id: int, correlation_id: Optional[str] = None):
        self.purchase_id = purchase_id
        super().__init__(
            f"Purchase with ID {purchase_id} not found",
            correlation_id=correlation_id,
            purchase_id=purchase_id
        )


class SlugAlreadyExists(ServiceError):
    """Raised when attempting to create ingredient with duplicate slug.

    Args:
        slug: The slug that already exists
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise SlugAlreadyExists("all_purpose_flour")
        SlugAlreadyExists: Ingredient with slug 'all_purpose_flour' already exists

    HTTP Status: 409 Conflict
    """

    http_status_code = 409

    def __init__(self, slug: str, correlation_id: Optional[str] = None):
        self.slug = slug
        super().__init__(
            f"Ingredient with slug '{slug}' already exists",
            correlation_id=correlation_id,
            slug=slug
        )


class ProductInUse(ServiceError):
    """Raised when attempting to delete product that has dependencies.

    Args:
        product_id: The product ID being deleted
        dependencies: Dictionary of dependency counts {entity_type: count}
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> deps = {"inventory_items": 12, "purchases": 25}
        >>> raise ProductInUse(123, deps)
        ProductInUse: Cannot delete product 123: used in 12 inventory_items, 25 purchases

    HTTP Status: 409 Conflict
    """

    http_status_code = 409

    def __init__(
        self,
        product_id: int,
        dependencies: dict,
        correlation_id: Optional[str] = None
    ):
        self.product_id = product_id
        self.dependencies = dependencies

        # Format dependency details
        details = ", ".join(
            f"{count} {entity_type}" for entity_type, count in dependencies.items() if count > 0
        )

        super().__init__(
            f"Cannot delete product {product_id}: used in {details}",
            correlation_id=correlation_id,
            product_id=product_id,
            dependencies=dependencies
        )


class SupplierNotFoundError(ServiceError):
    """Raised when a supplier cannot be found by ID.

    Args:
        supplier_id: The supplier ID that was not found
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise SupplierNotFoundError(123)
        SupplierNotFoundError: Supplier with ID 123 not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, supplier_id: int, correlation_id: Optional[str] = None):
        self.supplier_id = supplier_id
        super().__init__(
            f"Supplier with ID {supplier_id} not found",
            correlation_id=correlation_id,
            supplier_id=supplier_id
        )


# F094 Core API Standardization - Additional NotFound Exceptions


class RecipeNotFoundBySlug(ServiceError):
    """Raised when a recipe cannot be found by slug.

    Args:
        slug: The recipe slug that was not found
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise RecipeNotFoundBySlug("chocolate-cake")
        RecipeNotFoundBySlug: Recipe with slug 'chocolate-cake' not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, slug: str, correlation_id: Optional[str] = None):
        self.slug = slug
        super().__init__(
            f"Recipe with slug '{slug}' not found",
            correlation_id=correlation_id,
            slug=slug
        )


class RecipeNotFoundByName(ServiceError):
    """Raised when a recipe cannot be found by name.

    Args:
        name: The recipe name that was not found
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise RecipeNotFoundByName("Chocolate Cake")
        RecipeNotFoundByName: Recipe with name 'Chocolate Cake' not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, name: str, correlation_id: Optional[str] = None):
        self.name = name
        super().__init__(
            f"Recipe with name '{name}' not found",
            correlation_id=correlation_id,
            name=name
        )


class EventNotFoundById(ServiceError):
    """Raised when an event cannot be found by ID.

    Args:
        event_id: The event ID that was not found
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise EventNotFoundById(123)
        EventNotFoundById: Event with ID 123 not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, event_id: int, correlation_id: Optional[str] = None):
        self.event_id = event_id
        super().__init__(
            f"Event with ID {event_id} not found",
            correlation_id=correlation_id,
            event_id=event_id
        )


class EventNotFoundByName(ServiceError):
    """Raised when an event cannot be found by name.

    Args:
        name: The event name that was not found
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise EventNotFoundByName("Christmas 2024")
        EventNotFoundByName: Event with name 'Christmas 2024' not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, name: str, correlation_id: Optional[str] = None):
        self.name = name
        super().__init__(
            f"Event with name '{name}' not found",
            correlation_id=correlation_id,
            name=name
        )


class FinishedGoodNotFoundById(ServiceError):
    """Raised when a finished good cannot be found by ID.

    Args:
        finished_good_id: The finished good ID that was not found
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise FinishedGoodNotFoundById(123)
        FinishedGoodNotFoundById: Finished good with ID 123 not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, finished_good_id: int, correlation_id: Optional[str] = None):
        self.finished_good_id = finished_good_id
        super().__init__(
            f"Finished good with ID {finished_good_id} not found",
            correlation_id=correlation_id,
            finished_good_id=finished_good_id
        )


class FinishedGoodNotFoundBySlug(ServiceError):
    """Raised when a finished good cannot be found by slug.

    Args:
        slug: The finished good slug that was not found
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise FinishedGoodNotFoundBySlug("chocolate-truffles")
        FinishedGoodNotFoundBySlug: Finished good with slug 'chocolate-truffles' not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, slug: str, correlation_id: Optional[str] = None):
        self.slug = slug
        super().__init__(
            f"Finished good with slug '{slug}' not found",
            correlation_id=correlation_id,
            slug=slug
        )


class FinishedUnitNotFoundById(ServiceError):
    """Raised when a finished unit cannot be found by ID.

    Args:
        finished_unit_id: The finished unit ID that was not found
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise FinishedUnitNotFoundById(123)
        FinishedUnitNotFoundById: Finished unit with ID 123 not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, finished_unit_id: int, correlation_id: Optional[str] = None):
        self.finished_unit_id = finished_unit_id
        super().__init__(
            f"Finished unit with ID {finished_unit_id} not found",
            correlation_id=correlation_id,
            finished_unit_id=finished_unit_id
        )


class FinishedUnitNotFoundBySlug(ServiceError):
    """Raised when a finished unit cannot be found by slug.

    Args:
        slug: The finished unit slug that was not found
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise FinishedUnitNotFoundBySlug("cookie-dozen")
        FinishedUnitNotFoundBySlug: Finished unit with slug 'cookie-dozen' not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, slug: str, correlation_id: Optional[str] = None):
        self.slug = slug
        super().__init__(
            f"Finished unit with slug '{slug}' not found",
            correlation_id=correlation_id,
            slug=slug
        )


class PackageNotFoundById(ServiceError):
    """Raised when a package cannot be found by ID.

    Args:
        package_id: The package ID that was not found
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise PackageNotFoundById(123)
        PackageNotFoundById: Package with ID 123 not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, package_id: int, correlation_id: Optional[str] = None):
        self.package_id = package_id
        super().__init__(
            f"Package with ID {package_id} not found",
            correlation_id=correlation_id,
            package_id=package_id
        )


class PackageNotFoundByName(ServiceError):
    """Raised when a package cannot be found by name.

    Args:
        name: The package name that was not found
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise PackageNotFoundByName("Holiday Gift Box")
        PackageNotFoundByName: Package with name 'Holiday Gift Box' not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, name: str, correlation_id: Optional[str] = None):
        self.name = name
        super().__init__(
            f"Package with name '{name}' not found",
            correlation_id=correlation_id,
            name=name
        )


class CompositionNotFoundById(ServiceError):
    """Raised when a composition cannot be found by ID.

    Args:
        composition_id: The composition ID that was not found
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise CompositionNotFoundById(123)
        CompositionNotFoundById: Composition with ID 123 not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, composition_id: int, correlation_id: Optional[str] = None):
        self.composition_id = composition_id
        super().__init__(
            f"Composition with ID {composition_id} not found",
            correlation_id=correlation_id,
            composition_id=composition_id
        )


class UnitNotFoundByCode(ServiceError):
    """Raised when a unit cannot be found by code.

    Args:
        code: The unit code that was not found
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise UnitNotFoundByCode("kg")
        UnitNotFoundByCode: Unit with code 'kg' not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, code: str, correlation_id: Optional[str] = None):
        self.code = code
        super().__init__(
            f"Unit with code '{code}' not found",
            correlation_id=correlation_id,
            code=code
        )


class MaterialCategoryNotFound(ServiceError):
    """Raised when a material category cannot be found.

    Args:
        identifier: The category identifier (ID or name)
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise MaterialCategoryNotFound(123)
        MaterialCategoryNotFound: Material category 123 not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, identifier, correlation_id: Optional[str] = None):
        self.identifier = identifier
        super().__init__(
            f"Material category {identifier} not found",
            correlation_id=correlation_id,
            identifier=identifier
        )


class MaterialSubcategoryNotFound(ServiceError):
    """Raised when a material subcategory cannot be found.

    Args:
        identifier: The subcategory identifier (ID or name)
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise MaterialSubcategoryNotFound(123)
        MaterialSubcategoryNotFound: Material subcategory 123 not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, identifier, correlation_id: Optional[str] = None):
        self.identifier = identifier
        super().__init__(
            f"Material subcategory {identifier} not found",
            correlation_id=correlation_id,
            identifier=identifier
        )


class MaterialNotFound(ServiceError):
    """Raised when a material cannot be found.

    Args:
        identifier: The material identifier (ID or slug)
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise MaterialNotFound(123)
        MaterialNotFound: Material 123 not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, identifier, correlation_id: Optional[str] = None):
        self.identifier = identifier
        super().__init__(
            f"Material {identifier} not found",
            correlation_id=correlation_id,
            identifier=identifier
        )


class MaterialProductNotFound(ServiceError):
    """Raised when a material product cannot be found.

    Args:
        identifier: The material product identifier (ID or slug)
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise MaterialProductNotFound(123)
        MaterialProductNotFound: Material product 123 not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, identifier, correlation_id: Optional[str] = None):
        self.identifier = identifier
        super().__init__(
            f"Material product {identifier} not found",
            correlation_id=correlation_id,
            identifier=identifier
        )


class RecipientNotFoundByName(ServiceError):
    """Raised when a recipient cannot be found by name.

    Args:
        name: The recipient name that was not found
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise RecipientNotFoundByName("John Smith")
        RecipientNotFoundByName: Recipient with name 'John Smith' not found

    HTTP Status: 404 Not Found
    """

    http_status_code = 404

    def __init__(self, name: str, correlation_id: Optional[str] = None):
        self.name = name
        super().__init__(
            f"Recipient with name '{name}' not found",
            correlation_id=correlation_id,
            name=name
        )


class ConversionError(ServiceError):
    """Raised when a unit conversion fails.

    Args:
        message: Description of the conversion error
        from_unit: The source unit (optional)
        to_unit: The target unit (optional)
        value: The value being converted (optional)
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise ConversionError("Cannot convert weight to volume", from_unit="kg", to_unit="ml")
        ConversionError: Cannot convert weight to volume

    HTTP Status: 400 Bad Request
    """

    http_status_code = 400

    def __init__(
        self,
        message: str,
        from_unit: Optional[str] = None,
        to_unit: Optional[str] = None,
        value: Optional[float] = None,
        correlation_id: Optional[str] = None
    ):
        self.from_unit = from_unit
        self.to_unit = to_unit
        self.value = value
        super().__init__(
            message,
            correlation_id=correlation_id,
            from_unit=from_unit,
            to_unit=to_unit,
            value=value
        )


# Hierarchy Service Exceptions (Feature 031)


class HierarchyValidationError(ValidationError):
    """Raised for hierarchy-specific validation failures.

    Base class for all hierarchy validation errors.

    Args:
        message: Description of the hierarchy validation error
        correlation_id: Optional correlation ID for tracing

    HTTP Status: 400 Bad Request (inherited from ValidationError)
    """

    http_status_code = 400

    def __init__(self, message: str, correlation_id: Optional[str] = None):
        self.message = message
        # Call ServiceError.__init__ directly to avoid ValidationError's list handling
        ServiceError.__init__(
            self,
            f"Validation failed: {message}",
            correlation_id=correlation_id,
            validation_message=message
        )
        self.errors = [message]  # Maintain compatibility with ValidationError


class CircularReferenceError(HierarchyValidationError):
    """Raised when operation would create circular reference.

    Args:
        ingredient_id: The ingredient being moved
        new_parent_id: The proposed new parent that would create a cycle
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise CircularReferenceError(123, 456)
        CircularReferenceError: Moving ingredient 123 under 456 would create a circular reference

    HTTP Status: 422 Unprocessable Entity
    """

    http_status_code = 422

    def __init__(
        self,
        ingredient_id: int,
        new_parent_id: int,
        correlation_id: Optional[str] = None
    ):
        self.ingredient_id = ingredient_id
        self.new_parent_id = new_parent_id
        msg = f"Moving ingredient {ingredient_id} under {new_parent_id} would create a circular reference"
        ServiceError.__init__(
            self,
            msg,
            correlation_id=correlation_id,
            ingredient_id=ingredient_id,
            new_parent_id=new_parent_id
        )
        self.errors = [msg]
        self.message = msg


class MaxDepthExceededError(HierarchyValidationError):
    """Raised when operation would exceed maximum hierarchy depth.

    Args:
        ingredient_id: The ingredient being moved or created
        would_be_level: The level the ingredient would be at
        max_level: The maximum allowed level (default 2)
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise MaxDepthExceededError(123, 3, 2)
        MaxDepthExceededError: Ingredient 123 would be at level 3, but maximum is 2

    HTTP Status: 422 Unprocessable Entity
    """

    http_status_code = 422

    def __init__(
        self,
        ingredient_id: int,
        would_be_level: int,
        max_level: int = 2,
        correlation_id: Optional[str] = None
    ):
        self.ingredient_id = ingredient_id
        self.would_be_level = would_be_level
        self.max_level = max_level
        msg = f"Ingredient {ingredient_id} would be at level {would_be_level}, but maximum is {max_level}"
        ServiceError.__init__(
            self,
            msg,
            correlation_id=correlation_id,
            ingredient_id=ingredient_id,
            would_be_level=would_be_level,
            max_level=max_level
        )
        self.errors = [msg]
        self.message = msg


class NonLeafIngredientError(HierarchyValidationError):
    """Raised when non-leaf ingredient is used where only leaf is allowed.

    Args:
        ingredient_id: The non-leaf ingredient ID
        ingredient_name: Display name of the ingredient
        context: Where the error occurred (e.g., "recipe", "product")
        suggestions: Optional list of leaf ingredient names to suggest
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise NonLeafIngredientError(123, "Dark Chocolate", "recipe", ["Semi-Sweet Chips"])
        NonLeafIngredientError: Cannot add 'Dark Chocolate' to recipe: only leaf ingredients allowed. Try: Semi-Sweet Chips

    HTTP Status: 400 Bad Request
    """

    http_status_code = 400

    def __init__(
        self,
        ingredient_id: int,
        ingredient_name: str,
        context: str = "recipe",
        suggestions: List[str] = None,
        correlation_id: Optional[str] = None,
    ):
        self.ingredient_id = ingredient_id
        self.ingredient_name = ingredient_name
        self.context = context
        self.suggestions = suggestions or []

        msg = f"Cannot add '{ingredient_name}' to {context}: only leaf ingredients allowed"
        if self.suggestions:
            msg += f". Try: {', '.join(self.suggestions[:3])}"

        ServiceError.__init__(
            self,
            msg,
            correlation_id=correlation_id,
            ingredient_id=ingredient_id,
            ingredient_name=ingredient_name,
            context=context,
            suggestions=self.suggestions
        )
        self.errors = [msg]
        self.message = msg


# Plan State Exceptions (Feature 077)


class PlanStateError(ServiceError):
    """Raised when an invalid plan state transition or modification is attempted.

    Args:
        event_id: The event ID involved in the failed operation
        current_state: The current PlanState value
        attempted_action: Description of what was attempted
        correlation_id: Optional correlation ID for tracing

    Example:
        >>> raise PlanStateError(123, PlanState.LOCKED, "modify recipes")
        PlanStateError: Cannot modify recipes: event 123 plan is locked

    HTTP Status: 409 Conflict
    """

    http_status_code = 409

    def __init__(
        self,
        event_id: int,
        current_state,
        attempted_action: str,
        correlation_id: Optional[str] = None
    ):
        self.event_id = event_id
        self.current_state = current_state
        self.attempted_action = attempted_action
        state_name = current_state.value if hasattr(current_state, "value") else str(current_state)
        super().__init__(
            f"Cannot {attempted_action}: event {event_id} plan is {state_name}",
            correlation_id=correlation_id,
            event_id=event_id,
            current_state=state_name,
            attempted_action=attempted_action
        )
