"""
Recipe Service - Business logic for recipe management.

This service provides CRUD operations for recipes with:
- Input validation
- Recipe ingredient management
- Cost calculations
- Search and filtering
"""

from typing import List, Optional, Dict

from sqlalchemy.exc import SQLAlchemyError

from src.models import Recipe, RecipeIngredient, Ingredient
from src.services.database import session_scope
from src.services.exceptions import (
    RecipeNotFound,
    IngredientNotFound,
    ValidationError,
    DatabaseError,
)
from src.utils.validators import validate_recipe_data


# ============================================================================
# CRUD Operations
# ============================================================================


def create_recipe(recipe_data: Dict, ingredients_data: List[Dict] = None) -> Recipe:
    """
    Create a new recipe with optional ingredients.

    Args:
        recipe_data: Dictionary with recipe fields
        ingredients_data: List of ingredient dicts with:
            - ingredient_id: int
            - quantity: float
            - unit: str
            - notes: str (optional)

    Returns:
        Created Recipe instance with ingredients

    Raises:
        ValidationError: If data validation fails
        IngredientNotFound: If an ingredient_id doesn't exist
        DatabaseError: If database operation fails
    """
    # Validate recipe data
    is_valid, errors = validate_recipe_data(recipe_data)
    if not is_valid:
        raise ValidationError(errors)

    try:
        with session_scope() as session:
            # Create recipe
            recipe = Recipe(
                name=recipe_data["name"],
                category=recipe_data["category"],
                yield_quantity=recipe_data["yield_quantity"],
                yield_unit=recipe_data["yield_unit"],
                yield_description=recipe_data.get("yield_description"),
                estimated_time_minutes=recipe_data.get("estimated_time_minutes"),
                source=recipe_data.get("source"),
                notes=recipe_data.get("notes"),
            )

            session.add(recipe)
            session.flush()

            # Add ingredients if provided
            if ingredients_data:
                for ing_data in ingredients_data:
                    # Verify ingredient exists
                    ingredient = (
                        session.query(Ingredient).filter_by(id=ing_data["ingredient_id"]).first()
                    )

                    if not ingredient:
                        raise IngredientNotFound(ing_data["ingredient_id"])

                    # Create recipe ingredient
                    recipe_ingredient = RecipeIngredient(
                        recipe_id=recipe.id,
                        ingredient_id=ing_data["ingredient_id"],
                        quantity=ing_data["quantity"],
                        unit=ing_data["unit"],
                        notes=ing_data.get("notes"),
                    )

                    session.add(recipe_ingredient)

            session.flush()
            session.refresh(recipe)

            # Eagerly load relationships to avoid lazy loading issues
            _ = recipe.recipe_ingredients
            for ri in recipe.recipe_ingredients:
                _ = ri.ingredient

            return recipe

    except (ValidationError, IngredientNotFound):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError("Failed to create recipe", e)


def get_recipe(recipe_id: int, include_costs: bool = False) -> Recipe:
    """
    Retrieve a recipe by ID.

    Args:
        recipe_id: Recipe ID
        include_costs: If True, calculate and attach cost information

    Returns:
        Recipe instance with ingredients

    Raises:
        RecipeNotFound: If recipe doesn't exist
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()

            if not recipe:
                raise RecipeNotFound(recipe_id)

            # Eagerly load relationships to avoid lazy loading issues
            _ = recipe.recipe_ingredients
            for ri in recipe.recipe_ingredients:
                _ = ri.ingredient

            return recipe

    except RecipeNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to retrieve recipe {recipe_id}", e)


def get_all_recipes(
    category: Optional[str] = None,
    name_search: Optional[str] = None,
    ingredient_id: Optional[int] = None,
) -> List[Recipe]:
    """
    Retrieve all recipes with optional filtering.

    Args:
        category: Filter by category (exact match)
        name_search: Filter by name (case-insensitive partial match)
        ingredient_id: Filter by recipes using specific ingredient

    Returns:
        List of Recipe instances

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            query = session.query(Recipe)

            # Apply filters
            if category:
                query = query.filter(Recipe.category == category)

            if name_search:
                query = query.filter(Recipe.name.ilike(f"%{name_search}%"))

            if ingredient_id is not None:
                query = query.join(RecipeIngredient).filter(
                    RecipeIngredient.ingredient_id == ingredient_id
                )

            # Order by name
            query = query.order_by(Recipe.name)

            recipes = query.all()

            # Eagerly load relationships to avoid lazy loading issues
            for recipe in recipes:
                _ = recipe.recipe_ingredients
                for ri in recipe.recipe_ingredients:
                    _ = ri.ingredient

            return recipes

    except SQLAlchemyError as e:
        raise DatabaseError("Failed to retrieve recipes", e)


def update_recipe(  # noqa: C901
    recipe_id: int, recipe_data: Dict, ingredients_data: Optional[List[Dict]] = None
) -> Recipe:
    """
    Update a recipe and optionally its ingredients.

    Args:
        recipe_id: Recipe ID
        recipe_data: Dictionary with recipe fields to update
        ingredients_data: If provided, replaces all recipe ingredients
            Format: List of dicts with ingredient_id, quantity, unit, notes

    Returns:
        Updated Recipe instance

    Raises:
        RecipeNotFound: If recipe doesn't exist
        ValidationError: If data validation fails
        IngredientNotFound: If an ingredient_id doesn't exist
        DatabaseError: If database operation fails
    """
    # Validate recipe data
    is_valid, errors = validate_recipe_data(recipe_data)
    if not is_valid:
        raise ValidationError(errors)

    try:
        with session_scope() as session:
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()

            if not recipe:
                raise RecipeNotFound(recipe_id)

            # Update recipe fields
            for field, value in recipe_data.items():
                if hasattr(recipe, field):
                    setattr(recipe, field, value)

            # Update ingredients if provided
            if ingredients_data is not None:
                # Remove existing ingredients
                session.query(RecipeIngredient).filter_by(recipe_id=recipe_id).delete()

                # Add new ingredients
                for ing_data in ingredients_data:
                    # Verify ingredient exists
                    ingredient = (
                        session.query(Ingredient).filter_by(id=ing_data["ingredient_id"]).first()
                    )

                    if not ingredient:
                        raise IngredientNotFound(ing_data["ingredient_id"])

                    recipe_ingredient = RecipeIngredient(
                        recipe_id=recipe.id,
                        ingredient_id=ing_data["ingredient_id"],
                        quantity=ing_data["quantity"],
                        unit=ing_data["unit"],
                        notes=ing_data.get("notes"),
                    )

                    session.add(recipe_ingredient)

            session.flush()
            session.refresh(recipe)

            # Eagerly load relationships to avoid lazy loading issues
            _ = recipe.recipe_ingredients
            for ri in recipe.recipe_ingredients:
                _ = ri.ingredient

            return recipe

    except (RecipeNotFound, ValidationError, IngredientNotFound):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to update recipe {recipe_id}", e)


def delete_recipe(recipe_id: int) -> bool:
    """
    Delete a recipe and its ingredients.

    Args:
        recipe_id: Recipe ID

    Returns:
        True if deleted successfully

    Raises:
        RecipeNotFound: If recipe doesn't exist
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()

            if not recipe:
                raise RecipeNotFound(recipe_id)

            # Delete recipe (cascade will remove recipe_ingredients)
            session.delete(recipe)

            return True

    except RecipeNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to delete recipe {recipe_id}", e)


# ============================================================================
# Recipe Ingredient Management
# ============================================================================


def add_ingredient_to_recipe(
    recipe_id: int, ingredient_id: int, quantity: float, unit: str, notes: str = None
) -> RecipeIngredient:
    """
    Add an ingredient to a recipe.

    Args:
        recipe_id: Recipe ID
        ingredient_id: Ingredient ID
        quantity: Quantity needed
        unit: Unit of measurement
        notes: Optional notes

    Returns:
        Created RecipeIngredient instance

    Raises:
        RecipeNotFound: If recipe doesn't exist
        IngredientNotFound: If ingredient doesn't exist
        ValidationError: If quantity/unit invalid
        DatabaseError: If database operation fails
    """
    if quantity <= 0:
        raise ValidationError(["Quantity must be positive"])

    if not unit or len(unit.strip()) == 0:
        raise ValidationError(["Unit is required"])

    try:
        with session_scope() as session:
            # Verify recipe exists
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if not recipe:
                raise RecipeNotFound(recipe_id)

            # Verify ingredient exists
            ingredient = session.query(Ingredient).filter_by(id=ingredient_id).first()
            if not ingredient:
                raise IngredientNotFound(ingredient_id)

            # Create recipe ingredient
            recipe_ingredient = RecipeIngredient(
                recipe_id=recipe_id,
                ingredient_id=ingredient_id,
                quantity=quantity,
                unit=unit,
                notes=notes,
            )

            session.add(recipe_ingredient)
            session.flush()
            session.refresh(recipe_ingredient)

            return recipe_ingredient

    except (RecipeNotFound, IngredientNotFound, ValidationError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError("Failed to add ingredient to recipe", e)


def remove_ingredient_from_recipe(recipe_id: int, ingredient_id: int) -> bool:
    """
    Remove an ingredient from a recipe.

    Args:
        recipe_id: Recipe ID
        ingredient_id: Ingredient ID

    Returns:
        True if removed successfully

    Raises:
        RecipeNotFound: If recipe doesn't exist
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            # Verify recipe exists
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if not recipe:
                raise RecipeNotFound(recipe_id)

            # Delete recipe ingredient
            deleted = (
                session.query(RecipeIngredient)
                .filter_by(recipe_id=recipe_id, ingredient_id=ingredient_id)
                .delete()
            )

            return deleted > 0

    except RecipeNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError("Failed to remove ingredient from recipe", e)


# ============================================================================
# Cost Calculations
# ============================================================================


def calculate_recipe_cost(recipe_id: int) -> float:
    """
    Calculate total cost of a recipe.

    Args:
        recipe_id: Recipe ID

    Returns:
        Total cost of all ingredients

    Raises:
        RecipeNotFound: If recipe doesn't exist
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()

            if not recipe:
                raise RecipeNotFound(recipe_id)

            return recipe.calculate_cost()

    except RecipeNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to calculate recipe cost for {recipe_id}", e)


def get_recipe_with_costs(recipe_id: int) -> Dict:
    """
    Get recipe with detailed cost breakdown.

    Args:
        recipe_id: Recipe ID

    Returns:
        Dictionary with recipe info and cost breakdown:
        {
            'recipe': Recipe instance,
            'total_cost': float,
            'cost_per_unit': float,
            'ingredients': [
                {
                    'ingredient': Ingredient,
                    'quantity': float,
                    'unit': str,
                    'cost': float,
                    'notes': str
                },
                ...
            ]
        }

    Raises:
        RecipeNotFound: If recipe doesn't exist
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()

            if not recipe:
                raise RecipeNotFound(recipe_id)

            # Build ingredient cost breakdown
            ingredient_costs = []
            for recipe_ingredient in recipe.recipe_ingredients:
                cost = recipe_ingredient.calculate_cost()
                ingredient_costs.append(
                    {
                        "ingredient": recipe_ingredient.ingredient,
                        "quantity": recipe_ingredient.quantity,
                        "unit": recipe_ingredient.unit,
                        "cost": cost,
                        "notes": recipe_ingredient.notes,
                    }
                )

            total_cost = recipe.calculate_cost()
            cost_per_unit = recipe.get_cost_per_unit()

            return {
                "recipe": recipe,
                "total_cost": total_cost,
                "cost_per_unit": cost_per_unit,
                "ingredients": ingredient_costs,
            }

    except RecipeNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get recipe costs for {recipe_id}", e)


# ============================================================================
# Search and Filter Functions
# ============================================================================


def search_recipes_by_name(search_term: str) -> List[Recipe]:
    """
    Search recipes by name (case-insensitive partial match).

    Args:
        search_term: Search string

    Returns:
        List of matching Recipe instances

    Raises:
        DatabaseError: If database operation fails
    """
    return get_all_recipes(name_search=search_term)


def get_recipes_by_category(category: str) -> List[Recipe]:
    """
    Get all recipes in a specific category.

    Args:
        category: Category name

    Returns:
        List of Recipe instances

    Raises:
        DatabaseError: If database operation fails
    """
    return get_all_recipes(category=category)


def get_recipes_using_ingredient(ingredient_id: int) -> List[Recipe]:
    """
    Get all recipes that use a specific ingredient.

    Args:
        ingredient_id: Ingredient ID

    Returns:
        List of Recipe instances

    Raises:
        DatabaseError: If database operation fails
    """
    return get_all_recipes(ingredient_id=ingredient_id)


# ============================================================================
# Utility Functions
# ============================================================================


def get_recipe_count() -> int:
    """
    Get total count of recipes.

    Returns:
        Number of recipes in database

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            return session.query(Recipe).count()

    except SQLAlchemyError as e:
        raise DatabaseError("Failed to count recipes", e)


def get_recipe_category_list() -> List[str]:
    """
    Get list of all recipe categories in use.

    Returns:
        Sorted list of unique category names

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            categories = session.query(Recipe.category).distinct().order_by(Recipe.category).all()

            return [cat[0] for cat in categories]

    except SQLAlchemyError as e:
        raise DatabaseError("Failed to retrieve recipe category list", e)
