"""
Custom exceptions for service layer operations.

These exceptions provide meaningful error messages for common
failure scenarios in the business logic layer.
"""


class ServiceException(Exception):
    """Base exception for all service layer errors."""

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
