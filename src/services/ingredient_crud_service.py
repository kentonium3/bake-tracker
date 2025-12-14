"""
Ingredient CRUD Service - Business logic for ingredient management.

This service provides CRUD operations for ingredients with:
- Input validation
- Search and filtering
- Dependency checking before deletion

Note: Renamed from inventory_service.py for clarity. The name "inventory_service"
was confusing since InventoryItem tracks actual stock.
"""

from typing import List, Optional, Dict
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from src.models import Ingredient, RecipeIngredient
from src.services.database import session_scope
from src.services.exceptions import (
    IngredientNotFound,
    IngredientInUse,
    ValidationError,
    DatabaseError,
)
from src.utils.validators import validate_ingredient_data


# ============================================================================
# CRUD Operations
# ============================================================================


def create_ingredient(data: Dict) -> Ingredient:
    """
    Create a new ingredient.

    Args:
        data: Dictionary with ingredient fields

    Returns:
        Created Ingredient instance

    Raises:
        ValidationError: If data validation fails
        DatabaseError: If database operation fails
    """
    # Validate data
    is_valid, errors = validate_ingredient_data(data)
    if not is_valid:
        raise ValidationError(errors)

    try:
        with session_scope() as session:
            # Create ingredient (NEW SCHEMA: generic ingredient definition)
            # Support both 'name' and 'display_name' for backward compatibility
            display_name = data.get("display_name") or data.get("name")
            ingredient = Ingredient(
                display_name=display_name,
                slug=data.get("slug", display_name.lower().replace(" ", "_")),
                category=data["category"],
                description=data.get("description"),
                notes=data.get("notes"),
                # 4-field density model (Feature 010)
                density_volume_value=data.get("density_volume_value"),
                density_volume_unit=data.get("density_volume_unit"),
                density_weight_value=data.get("density_weight_value"),
                density_weight_unit=data.get("density_weight_unit"),
                moisture_pct=data.get("moisture_pct"),
                allergens=data.get("allergens"),
                foodon_id=data.get("foodon_id"),
                foodex2_code=data.get("foodex2_code"),
                langual_terms=data.get("langual_terms"),
                fdc_ids=data.get("fdc_ids"),
            )

            session.add(ingredient)
            session.flush()
            session.refresh(ingredient)

            return ingredient

    except SQLAlchemyError as e:
        raise DatabaseError("Failed to create ingredient", e)


def get_ingredient(ingredient_id: int) -> Ingredient:
    """
    Retrieve an ingredient by ID.

    Args:
        ingredient_id: Ingredient ID

    Returns:
        Ingredient instance

    Raises:
        IngredientNotFound: If ingredient doesn't exist
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            ingredient = session.query(Ingredient).filter_by(id=ingredient_id).first()

            if not ingredient:
                raise IngredientNotFound(ingredient_id)

            return ingredient

    except IngredientNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to retrieve ingredient {ingredient_id}", e)


def get_all_ingredients(
    category: Optional[str] = None,
    name_search: Optional[str] = None,
    low_stock_threshold: Optional[float] = None,
) -> List[Ingredient]:
    """
    Retrieve all ingredients with optional filtering.

    Args:
        category: Filter by category (exact match)
        name_search: Filter by name (case-insensitive partial match)
        low_stock_threshold: Filter by quantity <= threshold

    Returns:
        List of Ingredient instances

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            query = session.query(Ingredient)

            # Apply filters
            if category:
                query = query.filter(Ingredient.category == category)

            if name_search:
                query = query.filter(
                    or_(
                        Ingredient.display_name.ilike(f"%{name_search}%"),
                        Ingredient.slug.ilike(f"%{name_search}%"),
                    )
                )

            # Note: low_stock_threshold filtering removed - quantity is now on InventoryItem, not Ingredient
            # if low_stock_threshold is not None:
            #     query = query.filter(Ingredient.quantity <= low_stock_threshold)

            # Order by display_name
            query = query.order_by(Ingredient.display_name)

            ingredients = query.all()

            return ingredients

    except SQLAlchemyError as e:
        raise DatabaseError("Failed to retrieve ingredients", e)


def update_ingredient(ingredient_id: int, data: Dict) -> Ingredient:
    """
    Update an ingredient.

    Args:
        ingredient_id: Ingredient ID
        data: Dictionary with fields to update

    Returns:
        Updated Ingredient instance

    Raises:
        IngredientNotFound: If ingredient doesn't exist
        ValidationError: If data validation fails
        DatabaseError: If database operation fails
    """
    # Validate data
    is_valid, errors = validate_ingredient_data(data)
    if not is_valid:
        raise ValidationError(errors)

    try:
        with session_scope() as session:
            ingredient = session.query(Ingredient).filter_by(id=ingredient_id).first()

            if not ingredient:
                raise IngredientNotFound(ingredient_id)

            # Update fields
            for field, value in data.items():
                if hasattr(ingredient, field):
                    setattr(ingredient, field, value)

            # Update timestamp
            ingredient.last_updated = datetime.utcnow()

            session.flush()
            session.refresh(ingredient)

            return ingredient

    except (IngredientNotFound, ValidationError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to update ingredient {ingredient_id}", e)


def delete_ingredient(ingredient_id: int, force: bool = False) -> bool:
    """
    Delete an ingredient.

    Args:
        ingredient_id: Ingredient ID
        force: If True, delete even if used in recipes (NOT RECOMMENDED)

    Returns:
        True if deleted successfully

    Raises:
        IngredientNotFound: If ingredient doesn't exist
        IngredientInUse: If ingredient is used in recipes and force=False
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            ingredient = session.query(Ingredient).filter_by(id=ingredient_id).first()

            if not ingredient:
                raise IngredientNotFound(ingredient_id)

            # Check if ingredient is used in recipes
            recipe_count = (
                session.query(RecipeIngredient).filter_by(ingredient_id=ingredient_id).count()
            )

            if recipe_count > 0:
                if not force:
                    raise IngredientInUse(ingredient_id, recipe_count)
                else:
                    # Force delete: remove all recipe_ingredients first
                    session.query(RecipeIngredient).filter_by(ingredient_id=ingredient_id).delete()

            # Delete ingredient
            session.delete(ingredient)

            return True

    except (IngredientNotFound, IngredientInUse):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to delete ingredient {ingredient_id}", e)


# ============================================================================
# Stock Management
# ============================================================================


def update_quantity(ingredient_id: int, new_quantity: float) -> Ingredient:
    """
    Update ingredient quantity.

    Args:
        ingredient_id: Ingredient ID
        new_quantity: New quantity value

    Returns:
        Updated Ingredient instance

    Raises:
        IngredientNotFound: If ingredient doesn't exist
        ValidationError: If quantity is invalid
        DatabaseError: If database operation fails
    """
    if new_quantity < 0:
        raise ValidationError(["Quantity cannot be negative"])

    try:
        with session_scope() as session:
            ingredient = session.query(Ingredient).filter_by(id=ingredient_id).first()

            if not ingredient:
                raise IngredientNotFound(ingredient_id)

            ingredient.update_quantity(new_quantity)

            session.flush()
            session.refresh(ingredient)

            return ingredient

    except (IngredientNotFound, ValidationError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to update quantity for ingredient {ingredient_id}", e)


def adjust_quantity(ingredient_id: int, adjustment: float) -> Ingredient:
    """
    Adjust ingredient quantity by a delta amount.

    Args:
        ingredient_id: Ingredient ID
        adjustment: Amount to add (positive) or subtract (negative)

    Returns:
        Updated Ingredient instance

    Raises:
        IngredientNotFound: If ingredient doesn't exist
        ValidationError: If resulting quantity would be negative
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            ingredient = session.query(Ingredient).filter_by(id=ingredient_id).first()

            if not ingredient:
                raise IngredientNotFound(ingredient_id)

            new_quantity = ingredient.quantity + adjustment

            if new_quantity < 0:
                raise ValidationError(
                    [
                        f"Adjustment would result in negative quantity: "
                        f"{ingredient.quantity} + {adjustment} = {new_quantity}"
                    ]
                )

            ingredient.adjust_quantity(adjustment)

            session.flush()
            session.refresh(ingredient)

            return ingredient

    except (IngredientNotFound, ValidationError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to adjust quantity for ingredient {ingredient_id}", e)


# ============================================================================
# Search and Filter Functions
# ============================================================================


def search_ingredients_by_name(search_term: str) -> List[Ingredient]:
    """
    Search ingredients by name or brand (case-insensitive partial match).

    Args:
        search_term: Search string

    Returns:
        List of matching Ingredient instances

    Raises:
        DatabaseError: If database operation fails
    """
    return get_all_ingredients(name_search=search_term)


def get_ingredients_by_category(category: str) -> List[Ingredient]:
    """
    Get all ingredients in a specific category.

    Args:
        category: Category name

    Returns:
        List of Ingredient instances

    Raises:
        DatabaseError: If database operation fails
    """
    return get_all_ingredients(category=category)


def get_low_stock_ingredients(threshold: float = 0.0) -> List[Ingredient]:
    """
    Get ingredients with quantity at or below threshold.

    Args:
        threshold: Stock threshold (default: 0.0)

    Returns:
        List of Ingredient instances with low stock

    Raises:
        DatabaseError: If database operation fails
    """
    return get_all_ingredients(low_stock_threshold=threshold)


# ============================================================================
# Utility Functions
# ============================================================================


def get_ingredient_count() -> int:
    """
    Get total count of ingredients.

    Returns:
        Number of ingredients in database

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            return session.query(Ingredient).count()

    except SQLAlchemyError as e:
        raise DatabaseError("Failed to count ingredients", e)


def get_category_list() -> List[str]:
    """
    Get list of all ingredient categories in use.

    Returns:
        Sorted list of unique category names

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            categories = (
                session.query(Ingredient.category).distinct().order_by(Ingredient.category).all()
            )

            return [cat[0] for cat in categories]

    except SQLAlchemyError as e:
        raise DatabaseError("Failed to retrieve category list", e)


def get_total_inventory_value() -> float:
    """
    Calculate total value of all inventory.

    Returns:
        Sum of (quantity × unit_cost) for all ingredients

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            ingredients = session.query(Ingredient).all()
            total_value = sum(ing.total_value for ing in ingredients)

            return total_value

    except SQLAlchemyError as e:
        raise DatabaseError("Failed to calculate inventory value", e)
