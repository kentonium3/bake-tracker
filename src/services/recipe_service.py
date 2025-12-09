"""
Recipe Service - Business logic for recipe management.

This service provides CRUD operations for recipes with:
- Input validation
- Recipe ingredient management
- Cost calculations (including FIFO-based actual cost and estimated cost)
- Search and filtering
"""

from decimal import Decimal
from typing import List, Optional, Dict

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from sqlalchemy import func

from src.models import Recipe, RecipeIngredient, RecipeComponent, Ingredient
from src.services.database import session_scope
from src.services.exceptions import (
    RecipeNotFound,
    IngredientNotFound,
    ValidationError,
    DatabaseError,
)
from src.services import inventory_item_service, product_service, purchase_service

from src.services.unit_converter import convert_any_units
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

            # Eagerly load relationships to avoid lazy loading issues
            _ = recipe.recipe_ingredients
            for ri in recipe.recipe_ingredients:
                _ = ri.ingredient

            # Build ingredient cost breakdown
            ingredient_costs = []
            for recipe_ingredient in recipe.recipe_ingredients:
                cost = recipe_ingredient.calculate_cost()
                packages_needed = recipe_ingredient.get_packages_needed()
                ingredient_costs.append(
                    {
                        "ingredient": recipe_ingredient.ingredient,
                        "quantity": recipe_ingredient.quantity,
                        "unit": recipe_ingredient.unit,
                        "cost": cost,
                        "packages_needed": packages_needed,
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


def calculate_actual_cost(recipe_id: int) -> Decimal:
    """
    Calculate the actual cost of a recipe using FIFO inventory consumption.

    Determines what the recipe would cost to make using ingredients
    currently in inventory, consuming oldest items first (FIFO).
    When inventory is insufficient, falls back to preferred
    product pricing for the shortfall.

    Args:
        recipe_id: The ID of the recipe to cost

    Returns:
        Decimal: Total cost of the recipe

    Raises:
        RecipeNotFound: If recipe_id does not exist
        IngredientNotFound: If a recipe ingredient has no products
        ValidationError: If an ingredient cannot be costed (no pricing data,
                       missing density for unit conversion, etc.)

    Behavior:
        - Uses FIFO ordering (oldest inventory items first)
        - Does NOT modify inventory quantities (read-only via dry_run=True)
        - Converts units using INGREDIENT_DENSITIES constants
        - Fails fast on any uncostable ingredient
        - Returns Decimal for precision in monetary calculations

    Example:
        >>> from src.services.recipe_service import calculate_actual_cost
        >>> cost = calculate_actual_cost(recipe_id=42)
        >>> print(f"Recipe costs ${cost:.2f}")
        Recipe costs $12.50
    """
    try:
        with session_scope() as session:
            # Load recipe with eager-loaded relationships
            recipe = (
                session.query(Recipe)
                .options(
                    joinedload(Recipe.recipe_ingredients).joinedload(
                        RecipeIngredient.ingredient
                    )
                )
                .filter_by(id=recipe_id)
                .first()
            )

            if not recipe:
                raise RecipeNotFound(recipe_id)

            # Handle empty recipe (per FR-008)
            if not recipe.recipe_ingredients:
                return Decimal("0.00")

            total_cost = Decimal("0.00")

            # Iterate through each recipe ingredient
            for recipe_ingredient in recipe.recipe_ingredients:
                ingredient = recipe_ingredient.ingredient
                if not ingredient:
                    raise IngredientNotFound(recipe_ingredient.ingredient_id)

                recipe_qty = Decimal(str(recipe_ingredient.quantity))
                recipe_unit = recipe_ingredient.unit

                # Skip zero quantity ingredients (contribute $0)
                if recipe_qty <= Decimal("0"):
                    continue

                # Determine target unit for FIFO consumption
                # We'll use the ingredient's recipe_unit if set, otherwise fall back to inventory unit
                target_unit = ingredient.recipe_unit or recipe_unit

                # Convert recipe quantity to target unit if needed
                if recipe_unit != target_unit:
                    success, converted_float, error = convert_any_units(
                        float(recipe_qty),
                        recipe_unit,
                        target_unit,
                        ingredient=ingredient,
                    )
                    if not success:
                        raise ValidationError(
                            [f"Cannot convert units for '{ingredient.display_name}': {error}. "
                             f"Density data may be required for {recipe_unit} to {target_unit} conversion."]
                        )
                    converted_qty = Decimal(str(converted_float))
                else:
                    converted_qty = recipe_qty

                # Call consume_fifo with dry_run=True to get FIFO cost without modifying inventory
                fifo_result = inventory_item_service.consume_fifo(
                    ingredient.slug, converted_qty, dry_run=True
                )

                # Get FIFO cost from inventory consumption
                fifo_cost = fifo_result.get("total_cost", Decimal("0.00"))
                shortfall = fifo_result.get("shortfall", Decimal("0.00"))

                # Calculate fallback cost for any shortfall
                fallback_cost = Decimal("0.00")
                if shortfall > Decimal("0.00"):
                    # Get preferred product for fallback pricing
                    preferred_product = product_service.get_preferred_product(ingredient.slug)

                    if not preferred_product:
                        # Fallback to any available product
                        products = product_service.get_products_for_ingredient(ingredient.slug)
                        if not products:
                            raise ValidationError(
                                [f"Cannot cost ingredient '{ingredient.display_name}': no products defined"]
                            )
                        preferred_product = products[0]

                    # Get latest purchase price
                    latest_purchase = purchase_service.get_most_recent_purchase(
                        preferred_product.id
                    )
                    if not latest_purchase:
                        raise ValidationError(
                            [f"Cannot cost product '{preferred_product.brand or ingredient.display_name}': "
                             f"no purchase history available"]
                        )

                    # Convert shortfall to purchase units if needed
                    purchase_unit = preferred_product.purchase_unit
                    if target_unit != purchase_unit:
                        success, shortfall_float, error = convert_any_units(
                            float(shortfall),
                            target_unit,
                            purchase_unit,
                            ingredient=ingredient,
                        )
                        if not success:
                            raise ValidationError(
                                [f"Cannot convert shortfall units for '{ingredient.display_name}': {error}"]
                            )
                        shortfall_in_purchase_unit = Decimal(str(shortfall_float))
                    else:
                        shortfall_in_purchase_unit = shortfall

                    # Calculate fallback cost
                    unit_cost = Decimal(str(latest_purchase.unit_cost))
                    fallback_cost = shortfall_in_purchase_unit * unit_cost

                # Sum ingredient cost
                ingredient_cost = fifo_cost + fallback_cost
                total_cost += ingredient_cost

            return total_cost

    except (RecipeNotFound, IngredientNotFound, ValidationError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to calculate actual cost for recipe {recipe_id}", e)
    except Exception as e:
        raise DatabaseError(f"Failed to calculate actual cost for recipe {recipe_id}", e)


def calculate_estimated_cost(recipe_id: int) -> Decimal:
    """
    Calculate the estimated cost of a recipe using preferred product pricing.

    Determines what the recipe would cost based on current market prices,
    ignoring inventory. Useful for planning and shopping decisions.

    Args:
        recipe_id: The ID of the recipe to cost

    Returns:
        Decimal: Estimated total cost of the recipe

    Raises:
        RecipeNotFound: If recipe_id does not exist
        IngredientNotFound: If a recipe ingredient has no products
        ValidationError: If an ingredient cannot be costed (no purchase
                       history, missing density for unit conversion, etc.)

    Behavior:
        - Uses preferred product for each ingredient
        - Falls back to any available product if no preferred set
        - Uses most recent purchase price for pricing
        - Converts units using INGREDIENT_DENSITIES constants
        - Fails fast on any uncostable ingredient
        - Returns Decimal for precision in monetary calculations

    Example:
        >>> from src.services.recipe_service import calculate_estimated_cost
        >>> cost = calculate_estimated_cost(recipe_id=42)
        >>> print(f"Estimated cost: ${cost:.2f}")
        Estimated cost: $15.00
    """
    try:
        with session_scope() as session:
            # Load recipe with eager-loaded relationships
            recipe = (
                session.query(Recipe)
                .options(
                    joinedload(Recipe.recipe_ingredients).joinedload(
                        RecipeIngredient.ingredient
                    )
                )
                .filter_by(id=recipe_id)
                .first()
            )

            if not recipe:
                raise RecipeNotFound(recipe_id)

            # Handle empty recipe
            if not recipe.recipe_ingredients:
                return Decimal("0.00")

            total_cost = Decimal("0.00")

            # Iterate through each recipe ingredient
            for recipe_ingredient in recipe.recipe_ingredients:
                ingredient = recipe_ingredient.ingredient
                if not ingredient:
                    raise IngredientNotFound(recipe_ingredient.ingredient_id)

                recipe_qty = Decimal(str(recipe_ingredient.quantity))
                recipe_unit = recipe_ingredient.unit

                # Skip zero quantity ingredients (contribute $0)
                if recipe_qty <= Decimal("0"):
                    continue

                # Get preferred product for pricing
                preferred_product = product_service.get_preferred_product(ingredient.slug)

                if not preferred_product:
                    # Fallback to any available product
                    products = product_service.get_products_for_ingredient(ingredient.slug)
                    if not products:
                        raise ValidationError(
                            [f"Cannot cost ingredient '{ingredient.display_name}': no products defined"]
                        )
                    preferred_product = products[0]

                # Get latest purchase price
                latest_purchase = purchase_service.get_most_recent_purchase(preferred_product.id)
                if not latest_purchase:
                    raise ValidationError(
                        [f"Cannot cost product '{preferred_product.brand or ingredient.display_name}': "
                         f"no purchase history available"]
                    )

                # Convert recipe quantity to purchase units
                purchase_unit = preferred_product.purchase_unit
                if recipe_unit != purchase_unit:
                    success, converted_float, error = convert_any_units(
                        float(recipe_qty),
                        recipe_unit,
                        purchase_unit,
                        ingredient=ingredient,
                    )
                    if not success:
                        raise ValidationError(
                            [f"Cannot convert units for '{ingredient.display_name}': {error}. "
                             f"Density data may be required for {recipe_unit} to {purchase_unit} conversion."]
                        )
                    converted_qty = Decimal(str(converted_float))
                else:
                    converted_qty = recipe_qty

                # Calculate ingredient cost using purchase unit cost
                unit_cost = Decimal(str(latest_purchase.unit_cost))
                ingredient_cost = converted_qty * unit_cost
                total_cost += ingredient_cost

            return total_cost

    except (RecipeNotFound, IngredientNotFound, ValidationError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to calculate estimated cost for recipe {recipe_id}", e)
    except Exception as e:
        raise DatabaseError(f"Failed to calculate estimated cost for recipe {recipe_id}", e)


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


# ============================================================================
# Recipe Component Management (Nested Recipes / Sub-Recipes)
# ============================================================================


def add_recipe_component(
    recipe_id: int,
    component_recipe_id: int,
    quantity: float = 1.0,
    notes: str = None,
    sort_order: int = None,
) -> RecipeComponent:
    """
    Add a recipe as a component of another recipe.

    Args:
        recipe_id: Parent recipe ID
        component_recipe_id: Child recipe ID to add as component
        quantity: Batch multiplier (default: 1.0)
        notes: Optional notes for this component
        sort_order: Display order (default: append to end)

    Returns:
        Created RecipeComponent instance

    Raises:
        RecipeNotFound: If parent or component recipe doesn't exist
        ValidationError: If quantity <= 0 or component already exists
    """
    if quantity <= 0:
        raise ValidationError(["Batch quantity must be greater than 0"])

    try:
        with session_scope() as session:
            # Verify parent recipe exists
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if not recipe:
                raise RecipeNotFound(recipe_id)

            # Verify component recipe exists
            component = session.query(Recipe).filter_by(id=component_recipe_id).first()
            if not component:
                raise RecipeNotFound(component_recipe_id)

            # Check if already a component
            existing = (
                session.query(RecipeComponent)
                .filter_by(recipe_id=recipe_id, component_recipe_id=component_recipe_id)
                .first()
            )
            if existing:
                raise ValidationError([f"'{component.name}' is already a component of this recipe"])

            # Determine sort_order if not provided
            if sort_order is None:
                max_order = (
                    session.query(func.max(RecipeComponent.sort_order))
                    .filter_by(recipe_id=recipe_id)
                    .scalar()
                )
                sort_order = (max_order or 0) + 1

            # Create component
            recipe_component = RecipeComponent(
                recipe_id=recipe_id,
                component_recipe_id=component_recipe_id,
                quantity=quantity,
                notes=notes,
                sort_order=sort_order,
            )

            session.add(recipe_component)
            session.flush()
            session.refresh(recipe_component)

            # Eager load relationships
            _ = recipe_component.recipe
            _ = recipe_component.component_recipe

            return recipe_component

    except (RecipeNotFound, ValidationError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError("Failed to add recipe component", e)


def remove_recipe_component(recipe_id: int, component_recipe_id: int) -> bool:
    """
    Remove a component recipe from a parent recipe.

    Args:
        recipe_id: Parent recipe ID
        component_recipe_id: Component recipe ID to remove

    Returns:
        True if removed, False if component not found

    Raises:
        RecipeNotFound: If parent recipe doesn't exist
    """
    try:
        with session_scope() as session:
            # Verify parent recipe exists
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if not recipe:
                raise RecipeNotFound(recipe_id)

            # Delete component
            deleted = (
                session.query(RecipeComponent)
                .filter_by(recipe_id=recipe_id, component_recipe_id=component_recipe_id)
                .delete()
            )

            return deleted > 0

    except RecipeNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError("Failed to remove recipe component", e)


def update_recipe_component(
    recipe_id: int,
    component_recipe_id: int,
    quantity: float = None,
    notes: str = None,
    sort_order: int = None,
) -> RecipeComponent:
    """
    Update quantity or notes for an existing recipe component.

    Args:
        recipe_id: Parent recipe ID
        component_recipe_id: Component recipe ID
        quantity: New batch multiplier (if provided)
        notes: New notes (if provided, use empty string to clear)
        sort_order: New display order (if provided)

    Returns:
        Updated RecipeComponent instance

    Raises:
        RecipeNotFound: If parent recipe doesn't exist
        ValidationError: If component not found or quantity <= 0
    """
    if quantity is not None and quantity <= 0:
        raise ValidationError(["Batch quantity must be greater than 0"])

    try:
        with session_scope() as session:
            # Verify parent recipe exists
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if not recipe:
                raise RecipeNotFound(recipe_id)

            # Find component
            component = (
                session.query(RecipeComponent)
                .filter_by(recipe_id=recipe_id, component_recipe_id=component_recipe_id)
                .first()
            )
            if not component:
                raise ValidationError(["Component recipe not found in this recipe"])

            # Update fields if provided
            if quantity is not None:
                component.quantity = quantity
            if notes is not None:
                component.notes = notes if notes else None
            if sort_order is not None:
                component.sort_order = sort_order

            session.flush()
            session.refresh(component)

            # Eager load relationships
            _ = component.recipe
            _ = component.component_recipe

            return component

    except (RecipeNotFound, ValidationError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError("Failed to update recipe component", e)


def get_recipe_components(recipe_id: int) -> List[RecipeComponent]:
    """
    Get all component recipes for a recipe.

    Args:
        recipe_id: Recipe ID

    Returns:
        List of RecipeComponent instances, ordered by sort_order

    Raises:
        RecipeNotFound: If recipe doesn't exist
    """
    try:
        with session_scope() as session:
            # Verify recipe exists
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if not recipe:
                raise RecipeNotFound(recipe_id)

            # Get components ordered by sort_order
            components = (
                session.query(RecipeComponent)
                .filter_by(recipe_id=recipe_id)
                .order_by(RecipeComponent.sort_order)
                .all()
            )

            # Eager load relationships
            for comp in components:
                _ = comp.recipe
                _ = comp.component_recipe

            return components

    except RecipeNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get recipe components for {recipe_id}", e)


def get_recipes_using_component(component_recipe_id: int) -> List[Recipe]:
    """
    Get all recipes that use a given recipe as a component.

    Args:
        component_recipe_id: Recipe ID to check

    Returns:
        List of Recipe instances that use this as a component

    Raises:
        RecipeNotFound: If recipe doesn't exist
    """
    try:
        with session_scope() as session:
            # Verify recipe exists
            recipe = session.query(Recipe).filter_by(id=component_recipe_id).first()
            if not recipe:
                raise RecipeNotFound(component_recipe_id)

            # Find parent recipes
            parent_recipes = (
                session.query(Recipe)
                .join(RecipeComponent, Recipe.id == RecipeComponent.recipe_id)
                .filter(RecipeComponent.component_recipe_id == component_recipe_id)
                .order_by(Recipe.name)
                .all()
            )

            # Eager load relationships
            for r in parent_recipes:
                _ = r.recipe_ingredients
                for ri in r.recipe_ingredients:
                    _ = ri.ingredient

            return parent_recipes

    except RecipeNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get recipes using component {component_recipe_id}", e)
