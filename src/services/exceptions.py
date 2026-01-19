"""Service layer exception classes for Bake Tracker.

This module defines all custom exceptions used by the service layer to provide
consistent error handling across the application.

Exception Hierarchy:
    ServiceException (base - legacy)
    ServiceError (base - new service layer)
    ├── IngredientNotFoundBySlug
    ├── ProductNotFound
    ├── InventoryItemNotFound
    ├── PurchaseNotFound
    ├── SlugAlreadyExists
    ├── IngredientInUse
    ├── ProductInUse
    ├── ValidationError
    └── DatabaseError
"""

from typing import List


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
    """Raised when attempting to delete an ingredient that has dependencies."""

    def __init__(self, identifier, deps):
        """
        Initialize IngredientInUse exception.

        Args:
            identifier: Ingredient identifier (slug string or id int)
            deps: Either an int (recipe count for legacy) or dict with dependency counts
                  e.g., {'recipes': 5, 'products': 3, 'inventory_items': 12, 'children': 2}
        """
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
            f"Cannot delete ingredient '{identifier}': used in {deps_msg}"
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


# New Service Layer Exceptions (Ingredient/Product/InventoryItem/Purchase Services)


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




class InventoryItemNotFound(ServiceError):
    """Raised when inventory item cannot be found by ID.

    Args:
        inventory_item_id: The inventory item ID that was not found

    Example:
        >>> raise InventoryItemNotFound(456)
        InventoryItemNotFound: Inventory item with ID 456 not found
    """

    def __init__(self, inventory_item_id: int):
        self.inventory_item_id = inventory_item_id
        super().__init__(f"Inventory item with ID {inventory_item_id} not found")


class MaterialInventoryItemNotFoundError(ServiceError):
    """Raised when material inventory item cannot be found by ID.

    Args:
        inventory_item_id: The material inventory item ID that was not found
    """

    def __init__(self, inventory_item_id: int):
        self.inventory_item_id = inventory_item_id
        super().__init__(f"Material inventory item with ID {inventory_item_id} not found")



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
        >>> deps = {"inventory_items": 12, "purchases": 25}
        >>> raise ProductInUse(123, deps)
        ProductInUse: Cannot delete product 123: used in 12 inventory_items, 25 purchases
    """

    def __init__(self, product_id: int, dependencies: dict):
        self.product_id = product_id
        self.dependencies = dependencies

        # Format dependency details
        details = ", ".join(
            f"{count} {entity_type}" for entity_type, count in dependencies.items() if count > 0
        )

        super().__init__(f"Cannot delete product {product_id}: used in {details}")


class SupplierNotFoundError(ServiceError):
    """Raised when a supplier cannot be found by ID.

    Args:
        supplier_id: The supplier ID that was not found

    Example:
        >>> raise SupplierNotFoundError(123)
        SupplierNotFoundError: Supplier with ID 123 not found
    """

    def __init__(self, supplier_id: int):
        self.supplier_id = supplier_id
        super().__init__(f"Supplier with ID {supplier_id} not found")


class MaterialInventoryItemNotFoundError(ServiceError):
    """Raised when a material inventory item cannot be found by ID.

    Args:
        inventory_item_id: The inventory item ID that was not found

    Example:
        >>> raise MaterialInventoryItemNotFoundError(123)
        MaterialInventoryItemNotFoundError: Material inventory item with ID 123 not found
    """

    def __init__(self, inventory_item_id: int):
        self.inventory_item_id = inventory_item_id
        super().__init__(f"Material inventory item with ID {inventory_item_id} not found")


# Hierarchy Service Exceptions (Feature 031)


class HierarchyValidationError(ValidationError):
    """Raised for hierarchy-specific validation failures.

    Base class for all hierarchy validation errors.
    """

    def __init__(self, message: str):
        super().__init__([message])
        self.message = message


class CircularReferenceError(HierarchyValidationError):
    """Raised when operation would create circular reference.

    Args:
        ingredient_id: The ingredient being moved
        new_parent_id: The proposed new parent that would create a cycle

    Example:
        >>> raise CircularReferenceError(123, 456)
        CircularReferenceError: Moving ingredient 123 under 456 would create a circular reference
    """

    def __init__(self, ingredient_id: int, new_parent_id: int):
        self.ingredient_id = ingredient_id
        self.new_parent_id = new_parent_id
        super().__init__(
            f"Moving ingredient {ingredient_id} under {new_parent_id} would create a circular reference"
        )


class MaxDepthExceededError(HierarchyValidationError):
    """Raised when operation would exceed maximum hierarchy depth.

    Args:
        ingredient_id: The ingredient being moved or created
        current_level: The current hierarchy level
        max_level: The maximum allowed level (2)

    Example:
        >>> raise MaxDepthExceededError(123, 3, 2)
        MaxDepthExceededError: Ingredient 123 would be at level 3, but maximum is 2
    """

    def __init__(self, ingredient_id: int, would_be_level: int, max_level: int = 2):
        self.ingredient_id = ingredient_id
        self.would_be_level = would_be_level
        self.max_level = max_level
        super().__init__(
            f"Ingredient {ingredient_id} would be at level {would_be_level}, but maximum is {max_level}"
        )


class NonLeafIngredientError(HierarchyValidationError):
    """Raised when non-leaf ingredient is used where only leaf is allowed.

    Args:
        ingredient_id: The non-leaf ingredient ID
        ingredient_name: Display name of the ingredient
        context: Where the error occurred (e.g., "recipe", "product")
        suggestions: Optional list of leaf ingredient names to suggest

    Example:
        >>> raise NonLeafIngredientError(123, "Dark Chocolate", "recipe", ["Semi-Sweet Chips"])
    """

    def __init__(
        self,
        ingredient_id: int,
        ingredient_name: str,
        context: str = "recipe",
        suggestions: List[str] = None,
    ):
        self.ingredient_id = ingredient_id
        self.ingredient_name = ingredient_name
        self.context = context
        self.suggestions = suggestions or []

        msg = f"Cannot add '{ingredient_name}' to {context}: only leaf ingredients allowed"
        if self.suggestions:
            msg += f". Try: {', '.join(self.suggestions[:3])}"
        super().__init__(msg)
