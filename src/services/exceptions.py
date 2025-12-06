"""Service layer exception classes for Bake Tracker.

This module defines all custom exceptions used by the service layer to provide
consistent error handling across the application.

Exception Hierarchy:
    ServiceException (base - legacy)
    ServiceError (base - new service layer)
    ├── IngredientNotFoundBySlug
    ├── ProductNotFound
    ├── PantryItemNotFound
    ├── PurchaseNotFound
    ├── SlugAlreadyExists
    ├── IngredientInUse
    ├── ProductInUse
    ├── ValidationError
    └── DatabaseError
"""


class ServiceException(Exception):
    """Base exception for all service layer errors (legacy).

    Note: New code should use ServiceError instead.
    """

    pass


class ServiceError(Exception):
    """Base exception for all service layer errors.

    All service-specific exceptions should inherit from this class.
    """

    pass


class IngredientNotFound(ServiceException):
    """Raised when an ingredient cannot be found by ID."""

    def __init__(self, ingredient_id: int):
        self.ingredient_id = ingredient_id
        super().__init__(f"Ingredient with ID {ingredient_id} not found")


class RecipeNotFound(ServiceException):
    """Raised when a recipe cannot be found by ID."""

    def __init__(self, recipe_id: int):
        self.recipe_id = recipe_id
        super().__init__(f"Recipe with ID {recipe_id} not found")


class IngredientInUse(ServiceException):
    """Raised when attempting to delete an ingredient that is used in recipes."""

    def __init__(self, ingredient_id: int, recipe_count: int):
        self.ingredient_id = ingredient_id
        self.recipe_count = recipe_count
        super().__init__(
            f"Cannot delete ingredient {ingredient_id}: used in {recipe_count} recipe(s)"
        )


class ValidationError(ServiceException):
    """Raised when data validation fails."""

    def __init__(self, errors: list):
        self.errors = errors
        error_msg = "; ".join(errors)
        super().__init__(f"Validation failed: {error_msg}")


class InsufficientStock(ServiceException):
    """Raised when there is not enough ingredient stock for an operation."""

    def __init__(self, ingredient_name: str, required: float, available: float):
        self.ingredient_name = ingredient_name
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient stock for {ingredient_name}: "
            f"required {required}, available {available}"
        )


class DatabaseError(ServiceException):
    """Raised when a database operation fails."""

    def __init__(self, message: str, original_error: Exception = None):
        self.original_error = original_error
        super().__init__(f"Database error: {message}")


# New Service Layer Exceptions (Ingredient/Variant/Pantry/Purchase Services)


class IngredientNotFoundBySlug(ServiceError):
    """Raised when ingredient cannot be found by slug.

    Args:
        slug: The ingredient slug that was not found

    Example:
        >>> raise IngredientNotFoundBySlug("all_purpose_flour")
        IngredientNotFoundBySlug: Ingredient 'all_purpose_flour' not found
    """

    def __init__(self, slug: str):
        self.slug = slug
        super().__init__(f"Ingredient '{slug}' not found")


class ProductNotFound(ServiceError):
    """Raised when product cannot be found by ID.

    Args:
        product_id: The product ID that was not found

    Example:
        >>> raise ProductNotFound(123)
        ProductNotFound: Product with ID 123 not found
    """

    def __init__(self, product_id: int):
        self.product_id = product_id
        super().__init__(f"Product with ID {product_id} not found")


# Alias for backward compatibility
VariantNotFound = ProductNotFound


class PantryItemNotFound(ServiceError):
    """Raised when pantry item cannot be found by ID.

    Args:
        pantry_item_id: The pantry item ID that was not found

    Example:
        >>> raise PantryItemNotFound(456)
        PantryItemNotFound: Pantry item with ID 456 not found
    """

    def __init__(self, pantry_item_id: int):
        self.pantry_item_id = pantry_item_id
        super().__init__(f"Pantry item with ID {pantry_item_id} not found")


class PurchaseNotFound(ServiceError):
    """Raised when purchase record cannot be found by ID.

    Args:
        purchase_id: The purchase ID that was not found

    Example:
        >>> raise PurchaseNotFound(789)
        PurchaseNotFound: Purchase with ID 789 not found
    """

    def __init__(self, purchase_id: int):
        self.purchase_id = purchase_id
        super().__init__(f"Purchase with ID {purchase_id} not found")


class SlugAlreadyExists(ServiceError):
    """Raised when attempting to create ingredient with duplicate slug.

    Args:
        slug: The slug that already exists

    Example:
        >>> raise SlugAlreadyExists("all_purpose_flour")
        SlugAlreadyExists: Ingredient with slug 'all_purpose_flour' already exists
    """

    def __init__(self, slug: str):
        self.slug = slug
        super().__init__(f"Ingredient with slug '{slug}' already exists")


class ProductInUse(ServiceError):
    """Raised when attempting to delete product that has dependencies.

    Args:
        product_id: The product ID being deleted
        dependencies: Dictionary of dependency counts {entity_type: count}

    Example:
        >>> deps = {"pantry_items": 12, "purchases": 25}
        >>> raise ProductInUse(123, deps)
        ProductInUse: Cannot delete product 123: used in 12 pantry_items, 25 purchases
    """

    def __init__(self, product_id: int, dependencies: dict):
        self.product_id = product_id
        self.dependencies = dependencies

        # Format dependency details
        details = ", ".join(
            f"{count} {entity_type}" for entity_type, count in dependencies.items() if count > 0
        )

        super().__init__(f"Cannot delete product {product_id}: used in {details}")


# Alias for backward compatibility
VariantInUse = ProductInUse
