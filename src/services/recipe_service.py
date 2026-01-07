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

from src.models import Recipe, RecipeIngredient, RecipeComponent, Ingredient, ProductionRun, FinishedUnit
from src.services.database import session_scope
from src.services.exceptions import (
    RecipeNotFound,
    IngredientNotFound,
    ValidationError,
    DatabaseError,
    NonLeafIngredientError,
)
from src.services import inventory_item_service, product_service, purchase_service

from src.services.unit_converter import convert_any_units
from src.utils.validators import validate_recipe_data


# ============================================================================
# Feature 031: Hierarchy Validation Helpers
# ============================================================================


def _validate_leaf_ingredient(ingredient: Ingredient, context: str, session) -> None:
    """
    Validate that an ingredient is a leaf (level 2) before adding to recipe/product.

    Args:
        ingredient: Ingredient object to validate
        context: Context string for error message (e.g., "recipe", "product")
        session: Database session

    Raises:
        NonLeafIngredientError: If ingredient is not a leaf (hierarchy_level != 2)
    """
    if ingredient.hierarchy_level != 2:
        # Get leaf suggestions from descendants
        from src.services import ingredient_hierarchy_service

        suggestions = []
        try:
            descendants = ingredient_hierarchy_service.get_leaf_ingredients(
                parent_id=ingredient.id, session=session
            )
            suggestions = [d["display_name"] for d in descendants[:3]]
        except Exception:
            # If we can't get suggestions, continue without them
            pass

        raise NonLeafIngredientError(
            ingredient_id=ingredient.id,
            ingredient_name=ingredient.display_name,
            context=context,
            suggestions=suggestions,
        )


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
            # T032 - Feature 037: is_production_ready defaults to False if not provided
            recipe = Recipe(
                name=recipe_data["name"],
                category=recipe_data["category"],
                yield_quantity=recipe_data["yield_quantity"],
                yield_unit=recipe_data["yield_unit"],
                yield_description=recipe_data.get("yield_description"),
                estimated_time_minutes=recipe_data.get("estimated_time_minutes"),
                source=recipe_data.get("source"),
                notes=recipe_data.get("notes"),
                is_production_ready=recipe_data.get("is_production_ready", False),
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

                    # Feature 031: Validate leaf-only constraint
                    _validate_leaf_ingredient(ingredient, "recipe", session)

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
                # Load products for cost calculation (get_preferred_product())
                if ri.ingredient:
                    _ = ri.ingredient.products
                    # Also load purchases for cost calculation (get_current_cost_per_unit())
                    for product in ri.ingredient.products:
                        _ = product.purchases

            return recipe

    except (ValidationError, IngredientNotFound, NonLeafIngredientError):
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
                # Load products for cost calculation (get_preferred_product())
                if ri.ingredient:
                    _ = ri.ingredient.products
                    # Also load purchases for cost calculation (get_current_cost_per_unit())
                    for product in ri.ingredient.products:
                        _ = product.purchases

            return recipe

    except RecipeNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to retrieve recipe {recipe_id}", e)


def get_all_recipes(
    category: Optional[str] = None,
    name_search: Optional[str] = None,
    ingredient_id: Optional[int] = None,
    include_archived: bool = False,
) -> List[Recipe]:
    """
    Retrieve all recipes with optional filtering.

    Args:
        category: Filter by category (exact match)
        name_search: Filter by name (case-insensitive partial match)
        ingredient_id: Filter by recipes using specific ingredient
        include_archived: If True, include archived recipes in the results.

    Returns:
        List of Recipe instances

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            query = session.query(Recipe)

            # Filter out archived recipes by default
            if not include_archived:
                query = query.filter(Recipe.is_archived == False)

            # Apply other filters
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
                    # Load products for cost calculation (get_preferred_product())
                    if ri.ingredient:
                        _ = ri.ingredient.products
                        # Also load purchases for cost calculation (get_current_cost_per_unit())
                        for product in ri.ingredient.products:
                            _ = product.purchases

                # Also load recipe_components and their component_recipe
                _ = recipe.recipe_components
                for comp in recipe.recipe_components:
                    _ = comp.component_recipe

                # Feature 040: Load variant relationships for export
                # Load base_recipe for variant recipes
                if recipe.base_recipe_id:
                    _ = recipe.base_recipe

                # Load finished_units for recipe export
                _ = recipe.finished_units

            return recipes

    except SQLAlchemyError as e:
        raise DatabaseError("Failed to retrieve recipes", e)


def get_recipe_by_name(name: str) -> Optional[Recipe]:
    """
    Retrieve a recipe by its exact name.

    Args:
        name: Exact recipe name

    Returns:
        Recipe instance if found, None otherwise

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            recipe = session.query(Recipe).filter_by(name=name).first()

            if recipe:
                # Eagerly load relationships
                _ = recipe.recipe_ingredients
                for ri in recipe.recipe_ingredients:
                    _ = ri.ingredient
                    # Load products for cost calculation (get_preferred_product())
                    if ri.ingredient:
                        _ = ri.ingredient.products
                        # Also load purchases for cost calculation (get_current_cost_per_unit())
                        for product in ri.ingredient.products:
                            _ = product.purchases

                _ = recipe.recipe_components
                for comp in recipe.recipe_components:
                    _ = comp.component_recipe

            return recipe

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to retrieve recipe by name: {name}", e)


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

                    # Feature 031: Validate leaf-only constraint
                    _validate_leaf_ingredient(ingredient, "recipe", session)

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
                # Load products for cost calculation (get_preferred_product())
                if ri.ingredient:
                    _ = ri.ingredient.products
                    # Also load purchases for cost calculation (get_current_cost_per_unit())
                    for product in ri.ingredient.products:
                        _ = product.purchases

            return recipe

    except (RecipeNotFound, ValidationError, IngredientNotFound, NonLeafIngredientError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to update recipe {recipe_id}", e)


def delete_recipe(recipe_id: int) -> bool:
    """
    Deletes or archives a recipe.

    - If the recipe is used as a component in other recipes, deletion is blocked.
    - If the recipe has historical usage (production runs, finished units), it is archived (soft-deleted).
    - If there are no dependencies, it is hard-deleted.

    Args:
        recipe_id: The ID of the recipe to delete or archive.

    Returns:
        True if the operation was successful.

    Raises:
        RecipeNotFound: If the recipe does not exist.
        ValidationError: If the recipe cannot be deleted or archived due to being a component.
        DatabaseError: For any other database-related errors.
    """
    try:
        with session_scope() as session:
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()

            if not recipe:
                raise RecipeNotFound(recipe_id)

            # 1. Check if recipe is used as a component in other recipes (blocking condition)
            parent_components = (
                session.query(RecipeComponent)
                .filter_by(component_recipe_id=recipe_id)
                .all()
            )

            if parent_components:
                parent_names = [comp.recipe.name for comp in parent_components if comp.recipe]
                raise ValidationError(
                    [f"Cannot delete '{recipe.name}': it is used as a component in: {', '.join(parent_names)}"]
                )

            # 2. Check for historical dependencies
            dependencies = check_recipe_dependencies(recipe_id, session)
            has_history = any(dependencies.values())

            if has_history:
                # Soft delete by archiving
                recipe.is_archived = True
                return True
            else:
                # Hard delete if no history
                session.delete(recipe)
                return True

    except (RecipeNotFound, ValidationError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to delete or archive recipe {recipe_id}", e)


def check_recipe_dependencies(recipe_id: int, session) -> Dict[str, int]:
    """
    Check for recipe dependencies in other parts of the system.

    Args:
        recipe_id: The ID of the recipe to check.
        session: The SQLAlchemy session to use for querying.

    Returns:
        A dictionary with dependency counts.
    """
    from src.models import ProductionRun, FinishedUnit

    dependencies = {
        "production_runs": session.query(ProductionRun).filter_by(recipe_id=recipe_id).count(),
        "finished_units": session.query(FinishedUnit).filter_by(recipe_id=recipe_id).count(),
    }
    return dependencies

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

            # Feature 031: Validate leaf-only constraint
            _validate_leaf_ingredient(ingredient, "recipe", session)

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

    except (RecipeNotFound, IngredientNotFound, ValidationError, NonLeafIngredientError):
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

            # Calculate direct ingredient cost
            direct_ingredient_cost = recipe.calculate_cost()

            # Build component cost breakdown
            component_costs = []
            total_component_cost = 0.0

            for comp in recipe.recipe_components:
                # Get component recipe cost recursively
                comp_total_cost = _calculate_recipe_cost_recursive(
                    comp.component_recipe_id, session
                )["total_cost"]

                comp_cost = comp.quantity * comp_total_cost

                component_costs.append({
                    "component_recipe": comp.component_recipe,
                    "quantity": comp.quantity,
                    "notes": comp.notes,
                    "unit_cost": comp_total_cost,
                    "total_cost": comp_cost,
                })

                total_component_cost += comp_cost

            # Calculate totals including components
            total_cost = direct_ingredient_cost + total_component_cost
            cost_per_unit = total_cost / recipe.yield_quantity if recipe.yield_quantity > 0 else 0.0

            return {
                "recipe": recipe,
                "total_cost": total_cost,
                "cost_per_unit": cost_per_unit,
                "ingredients": ingredient_costs,
                "components": component_costs,
                "direct_ingredient_cost": direct_ingredient_cost,
                "total_component_cost": total_component_cost,
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

                # Call consume_fifo with dry_run=True to get FIFO cost without modifying inventory
                # consume_fifo handles unit conversion from package_unit to recipe_unit
                fifo_result = inventory_item_service.consume_fifo(
                    ingredient.slug, recipe_qty, recipe_unit, dry_run=True
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

                    # Convert shortfall to package units if needed
                    package_unit = preferred_product.package_unit
                    if recipe_unit != package_unit:
                        success, shortfall_float, error = convert_any_units(
                            float(shortfall),
                            recipe_unit,
                            package_unit,
                            ingredient=ingredient,
                        )
                        if not success:
                            raise ValidationError(
                                [f"Cannot convert shortfall units for '{ingredient.display_name}': {error}"]
                            )
                        shortfall_in_package_unit = Decimal(str(shortfall_float))
                    else:
                        shortfall_in_package_unit = shortfall

                    # Calculate fallback cost
                    unit_cost = Decimal(str(latest_purchase.unit_cost))
                    fallback_cost = shortfall_in_package_unit * unit_cost

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

                # Convert recipe quantity to package units
                package_unit = preferred_product.package_unit
                if recipe_unit != package_unit:
                    success, converted_float, error = convert_any_units(
                        float(recipe_qty),
                        recipe_unit,
                        package_unit,
                        ingredient=ingredient,
                    )
                    if not success:
                        raise ValidationError(
                            [f"Cannot convert units for '{ingredient.display_name}': {error}. "
                             f"Density data may be required for {recipe_unit} to {package_unit} conversion."]
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


# Maximum allowed nesting depth for sub-recipes
MAX_RECIPE_NESTING_DEPTH = 3


def _would_create_cycle(parent_id: int, component_id: int, session) -> bool:
    """
    Check if adding component_id as child of parent_id would create a cycle.

    Traverses the component tree starting from component_id to see if
    parent_id is reachable (which would mean adding this edge creates a cycle).

    Args:
        parent_id: The recipe that would become the parent
        component_id: The recipe to add as a component
        session: Database session

    Returns:
        True if adding this component would create a circular reference
    """
    # Self-reference check
    if parent_id == component_id:
        return True

    # BFS to find if parent_id is reachable from component_id
    visited = set()
    to_visit = [component_id]

    while to_visit:
        current = to_visit.pop(0)

        if current == parent_id:
            return True  # Found a path back to parent = cycle

        if current in visited:
            continue

        visited.add(current)

        # Get all components of current recipe
        components = (
            session.query(RecipeComponent.component_recipe_id)
            .filter_by(recipe_id=current)
            .all()
        )

        for (comp_id,) in components:
            if comp_id not in visited:
                to_visit.append(comp_id)

    return False


def _get_recipe_depth(recipe_id: int, session, _visited: set = None) -> int:
    """
    Get the maximum depth of a recipe's component hierarchy.

    Args:
        recipe_id: Recipe to check
        session: Database session
        _visited: Set of already visited recipe IDs (for cycle protection)

    Returns:
        Depth: 1 = no components, 2 = has components, 3 = has nested components
    """
    if _visited is None:
        _visited = set()

    # Cycle protection (shouldn't happen with valid data, but be safe)
    if recipe_id in _visited:
        return 0

    _visited.add(recipe_id)

    # Get components
    components = (
        session.query(RecipeComponent.component_recipe_id)
        .filter_by(recipe_id=recipe_id)
        .all()
    )

    if not components:
        return 1  # Leaf recipe

    max_child_depth = 0
    for (comp_id,) in components:
        child_depth = _get_recipe_depth(comp_id, session, _visited.copy())
        max_child_depth = max(max_child_depth, child_depth)

    return 1 + max_child_depth


def _would_exceed_depth(parent_id: int, component_id: int, session, max_depth: int = MAX_RECIPE_NESTING_DEPTH) -> bool:
    """
    Check if adding component would exceed maximum nesting depth.

    The depth calculation considers:
    - Where the parent recipe sits in its own hierarchy (could already be nested)
    - The depth of the component's subtree

    Args:
        parent_id: The recipe that would become the parent
        component_id: The recipe to add as a component
        session: Database session
        max_depth: Maximum allowed depth (default: 3)

    Returns:
        True if adding this component would exceed the depth limit
    """
    # Get depth of component's subtree
    component_depth = _get_recipe_depth(component_id, session)

    # Check all paths where parent appears and calculate resulting depth
    # We need to find the deepest position of parent_id in any hierarchy
    def get_max_ancestor_depth(recipe_id: int, visited: set = None) -> int:
        """Find how deep this recipe is as a component in other recipes."""
        if visited is None:
            visited = set()

        if recipe_id in visited:
            return 0

        visited.add(recipe_id)

        # Find recipes that use this as a component
        parents = (
            session.query(RecipeComponent.recipe_id)
            .filter_by(component_recipe_id=recipe_id)
            .all()
        )

        if not parents:
            return 1  # Top-level recipe

        max_depth_above = 0
        for (pid,) in parents:
            depth_above = get_max_ancestor_depth(pid, visited.copy())
            max_depth_above = max(max_depth_above, depth_above)

        return 1 + max_depth_above

    # Parent's position in hierarchy + component's subtree depth
    parent_position = get_max_ancestor_depth(parent_id)
    total_depth = parent_position + component_depth

    return total_depth > max_depth


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

            # Check for circular reference
            if _would_create_cycle(recipe_id, component_recipe_id, session):
                raise ValidationError(
                    [f"Cannot add '{component.name}' as component: would create circular reference"]
                )

            # Check depth limit
            if _would_exceed_depth(recipe_id, component_recipe_id, session):
                raise ValidationError(
                    [f"Cannot add '{component.name}': would exceed maximum nesting depth of {MAX_RECIPE_NESTING_DEPTH} levels"]
                )

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


# ============================================================================
# Recipe Component Cost & Aggregation (Nested Recipes)
# ============================================================================


def get_aggregated_ingredients(
    recipe_id: int,
    multiplier: float = 1.0,
    session=None,
) -> List[Dict]:
    """
    Get all ingredients from a recipe and all sub-recipes with aggregated quantities.

    Args:
        recipe_id: Recipe ID
        multiplier: Scale factor for all quantities (default: 1.0)
        session: Optional database session. If provided, uses this session instead
                 of creating a new one. This is important for maintaining transactional
                 atomicity when called from within another session_scope block.

    Returns:
        List of aggregated ingredients with structure:
        [
            {
                "ingredient": Ingredient instance,
                "ingredient_id": int,
                "ingredient_name": str,
                "total_quantity": float,
                "unit": str,
                "sources": [{"recipe_name": str, "quantity": float}, ...]
            },
            ...
        ]

    Raises:
        RecipeNotFound: If recipe doesn't exist
    """
    # If session is provided, use it directly; otherwise use session_scope
    if session is not None:
        return _get_aggregated_ingredients_impl(recipe_id, multiplier, session)

    try:
        with session_scope() as session:
            return _get_aggregated_ingredients_impl(recipe_id, multiplier, session)
    except RecipeNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to aggregate ingredients for recipe {recipe_id}", e)


def _get_aggregated_ingredients_impl(
    recipe_id: int,
    multiplier: float,
    session,
) -> List[Dict]:
    """
    Internal implementation of get_aggregated_ingredients.

    Args:
        recipe_id: Recipe ID
        multiplier: Scale factor for all quantities
        session: Database session (required)

    Returns:
        List of aggregated ingredients
    """
    recipe = session.query(Recipe).filter_by(id=recipe_id).first()
    if not recipe:
        raise RecipeNotFound(recipe_id)

    # Dictionary to aggregate: key = (ingredient_id, unit)
    aggregated = {}

    def collect_ingredients(r_id: int, mult: float, visited: set = None):
        """Recursively collect ingredients from recipe and components."""
        if visited is None:
            visited = set()

        if r_id in visited:
            return  # Prevent infinite loop (shouldn't happen with validation)

        visited.add(r_id)

        # Get recipe
        r = session.query(Recipe).filter_by(id=r_id).first()
        if not r:
            return

        # Collect direct ingredients
        for ri in r.recipe_ingredients:
            key = (ri.ingredient_id, ri.unit)
            qty = ri.quantity * mult

            if key not in aggregated:
                aggregated[key] = {
                    "ingredient": ri.ingredient,
                    "ingredient_id": ri.ingredient_id,
                    "ingredient_name": ri.ingredient.display_name if ri.ingredient else "Unknown",
                    "total_quantity": 0.0,
                    "unit": ri.unit,
                    "sources": [],
                }

            aggregated[key]["total_quantity"] += qty
            aggregated[key]["sources"].append({
                "recipe_name": r.name,
                "quantity": qty,
            })

        # Collect from components
        components = (
            session.query(RecipeComponent)
            .filter_by(recipe_id=r_id)
            .all()
        )

        for comp in components:
            component_mult = mult * comp.quantity
            collect_ingredients(comp.component_recipe_id, component_mult, visited.copy())

    # Start collection
    collect_ingredients(recipe_id, multiplier)

    # Convert to list and sort by ingredient name
    result = sorted(aggregated.values(), key=lambda x: x["ingredient_name"])

    return result


def _calculate_recipe_cost_recursive(recipe_id: int, session, visited: set = None) -> Dict:
    """
    Internal helper for recursive cost calculation.

    Args:
        recipe_id: Recipe ID
        session: Database session
        visited: Set of visited recipe IDs (cycle protection)

    Returns:
        {"total_cost": float}
    """
    if visited is None:
        visited = set()

    if recipe_id in visited:
        return {"total_cost": 0.0}  # Prevent infinite loop

    visited.add(recipe_id)

    recipe = session.query(Recipe).filter_by(id=recipe_id).first()
    if not recipe:
        return {"total_cost": 0.0}

    # Direct ingredient cost
    direct_cost = 0.0
    for ri in recipe.recipe_ingredients:
        direct_cost += ri.calculate_cost()

    # Component costs
    component_cost = 0.0
    components = session.query(RecipeComponent).filter_by(recipe_id=recipe_id).all()

    for comp in components:
        comp_result = _calculate_recipe_cost_recursive(comp.component_recipe_id, session, visited.copy())
        component_cost += comp.quantity * comp_result["total_cost"]

    return {"total_cost": direct_cost + component_cost}


def calculate_total_cost_with_components(recipe_id: int) -> Dict:
    """
    Calculate total recipe cost including all sub-recipe costs.

    Args:
        recipe_id: Recipe ID

    Returns:
        Cost breakdown:
        {
            "recipe_id": int,
            "recipe_name": str,
            "direct_ingredient_cost": float,
            "component_costs": [
                {
                    "component_recipe_id": int,
                    "component_recipe_name": str,
                    "quantity": float,
                    "unit_cost": float,
                    "total_cost": float
                },
                ...
            ],
            "total_component_cost": float,
            "total_cost": float,
            "cost_per_unit": float,
        }

    Raises:
        RecipeNotFound: If recipe doesn't exist
    """
    try:
        with session_scope() as session:
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if not recipe:
                raise RecipeNotFound(recipe_id)

            # Calculate direct ingredient cost
            direct_cost = 0.0
            for ri in recipe.recipe_ingredients:
                direct_cost += ri.calculate_cost()

            # Calculate component costs
            component_costs = []
            total_component_cost = 0.0

            components = (
                session.query(RecipeComponent)
                .filter_by(recipe_id=recipe_id)
                .order_by(RecipeComponent.sort_order)
                .all()
            )

            for comp in components:
                # Recursive call to get component's total cost
                comp_result = _calculate_recipe_cost_recursive(comp.component_recipe_id, session)
                unit_cost = comp_result["total_cost"]
                comp_total = unit_cost * comp.quantity

                component_costs.append({
                    "component_recipe_id": comp.component_recipe_id,
                    "component_recipe_name": comp.component_recipe.name if comp.component_recipe else "Unknown",
                    "quantity": comp.quantity,
                    "unit_cost": unit_cost,
                    "total_cost": comp_total,
                })

                total_component_cost += comp_total

            total_cost = direct_cost + total_component_cost
            cost_per_unit = total_cost / recipe.yield_quantity if recipe.yield_quantity > 0 else 0.0

            return {
                "recipe_id": recipe_id,
                "recipe_name": recipe.name,
                "direct_ingredient_cost": direct_cost,
                "component_costs": component_costs,
                "total_component_cost": total_component_cost,
                "total_cost": total_cost,
                "cost_per_unit": cost_per_unit,
            }

    except RecipeNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to calculate cost for recipe {recipe_id}", e)


# ============================================================================
# Recipe Variant Management (Feature 037)
# ============================================================================


def get_recipe_variants(base_recipe_id: int, session=None) -> list:
    """
    Get all variants of a base recipe.

    Args:
        base_recipe_id: The base recipe ID
        session: Optional session for transaction sharing

    Returns:
        List of variant recipe dicts with keys:
        - id, name, variant_name, category, is_production_ready
    """
    if session is not None:
        return _get_recipe_variants_impl(base_recipe_id, session)

    try:
        with session_scope() as session:
            return _get_recipe_variants_impl(base_recipe_id, session)
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get variants for recipe {base_recipe_id}", e)


def _get_recipe_variants_impl(base_recipe_id: int, session) -> list:
    """Internal implementation for get_recipe_variants."""
    variants = (
        session.query(Recipe)
        .filter_by(base_recipe_id=base_recipe_id, is_archived=False)
        .order_by(Recipe.variant_name, Recipe.name)
        .all()
    )

    return [
        {
            "id": v.id,
            "name": v.name,
            "variant_name": v.variant_name,
            "category": v.category,
            "is_production_ready": v.is_production_ready,
        }
        for v in variants
    ]


def create_recipe_variant(
    base_recipe_id: int,
    variant_name: str,
    name: str = None,
    copy_ingredients: bool = True,
    session=None
) -> dict:
    """
    Create a variant of an existing recipe.

    Args:
        base_recipe_id: The recipe to create a variant of
        variant_name: Name distinguishing this variant (e.g., "Raspberry")
        name: Full recipe name (defaults to "Base Name - Variant Name")
        copy_ingredients: If True, copy ingredients from base recipe
        session: Optional session for transaction sharing

    Returns:
        Created variant recipe dict with keys:
        - id, name, variant_name, base_recipe_id

    Raises:
        RecipeNotFound: If base recipe does not exist
        DatabaseError: If database operation fails
    """
    if session is not None:
        return _create_recipe_variant_impl(
            base_recipe_id, variant_name, name, copy_ingredients, session
        )

    try:
        with session_scope() as session:
            return _create_recipe_variant_impl(
                base_recipe_id, variant_name, name, copy_ingredients, session
            )
    except RecipeNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to create variant of recipe {base_recipe_id}", e)


def _create_recipe_variant_impl(
    base_recipe_id: int,
    variant_name: str,
    name: str,
    copy_ingredients: bool,
    session
) -> dict:
    """Internal implementation for create_recipe_variant."""
    # Get base recipe
    base = session.query(Recipe).filter_by(id=base_recipe_id).first()
    if not base:
        raise RecipeNotFound(base_recipe_id)

    # Generate name if not provided
    if not name:
        name = f"{base.name} - {variant_name}"

    # Create variant
    variant = Recipe(
        name=name,
        category=base.category,
        source=base.source,
        yield_quantity=base.yield_quantity,
        yield_unit=base.yield_unit,
        yield_description=base.yield_description,
        estimated_time_minutes=base.estimated_time_minutes,
        notes=f"Variant of {base.name}",
        base_recipe_id=base_recipe_id,
        variant_name=variant_name,
        is_production_ready=False,  # Variants start experimental
    )

    session.add(variant)
    session.flush()

    # Copy ingredients if requested
    if copy_ingredients:
        for ri in base.recipe_ingredients:
            new_ri = RecipeIngredient(
                recipe_id=variant.id,
                ingredient_id=ri.ingredient_id,
                quantity=ri.quantity,
                unit=ri.unit,
                notes=ri.notes,
            )
            session.add(new_ri)

    session.flush()  # Flush to get IDs; caller controls commit

    return {
        "id": variant.id,
        "name": variant.name,
        "variant_name": variant.variant_name,
        "base_recipe_id": variant.base_recipe_id,
    }


def get_all_recipes_grouped(
    category: Optional[str] = None,
    name_search: Optional[str] = None,
    ingredient_id: Optional[int] = None,
    include_archived: bool = False,
    group_variants: bool = True,
) -> List[Dict]:
    """
    Retrieve all recipes as dictionaries with optional variant grouping.

    This function returns recipes as dictionaries (not ORM objects) and
    supports grouping variants under their base recipes.

    Args:
        category: Filter by category (exact match)
        name_search: Filter by name (case-insensitive partial match)
        ingredient_id: Filter by recipes using specific ingredient
        include_archived: If True, include archived recipes
        group_variants: If True, sort variants under their base recipe

    Returns:
        List of recipe dictionaries with additional fields:
        - _is_base: True if recipe has variants
        - _variant_count: Number of variants (for base recipes)
        - _is_variant: True if recipe is a variant
        - _indent_level: 1 for variants (for display indentation)
        - _is_orphaned_variant: True if base was deleted

    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with session_scope() as session:
            query = session.query(Recipe)

            # Filter out archived recipes by default
            if not include_archived:
                query = query.filter(Recipe.is_archived == False)

            # Apply other filters
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

            # Convert to dicts
            recipe_dicts = []
            for r in recipes:
                recipe_dicts.append({
                    "id": r.id,
                    "name": r.name,
                    "category": r.category,
                    "source": r.source,
                    "yield_quantity": r.yield_quantity,
                    "yield_unit": r.yield_unit,
                    "yield_description": r.yield_description,
                    "estimated_time_minutes": r.estimated_time_minutes,
                    "notes": r.notes,
                    "is_archived": r.is_archived,
                    "base_recipe_id": r.base_recipe_id,
                    "variant_name": r.variant_name,
                    "is_production_ready": r.is_production_ready,
                })

            if group_variants:
                return _group_recipes_with_variants(recipe_dicts)

            return recipe_dicts

    except SQLAlchemyError as e:
        raise DatabaseError("Failed to retrieve recipes", e)


def _group_recipes_with_variants(recipes: list) -> list:
    """
    Sort recipes so variants appear indented under their base.

    Order:
    1. Base recipes (base_recipe_id is None) sorted by name
    2. Variants immediately after their base, sorted by variant_name

    Args:
        recipes: List of recipe dicts

    Returns:
        Sorted list with metadata fields:
        - _is_base: True for base recipes with variants
        - _variant_count: Number of variants
        - _is_variant: True for variants
        - _indent_level: 1 for variants
        - _is_orphaned_variant: True if base not in list
    """
    # Separate base recipes and variants
    base_recipes = [r for r in recipes if r.get("base_recipe_id") is None]
    variants = [r for r in recipes if r.get("base_recipe_id") is not None]

    # Build variant lookup by base_recipe_id
    variant_map = {}
    for v in variants:
        base_id = v["base_recipe_id"]
        if base_id not in variant_map:
            variant_map[base_id] = []
        variant_map[base_id].append(v)

    # Sort variants within each group
    for base_id in variant_map:
        variant_map[base_id].sort(key=lambda x: x.get("variant_name") or x.get("name") or "")

    # Build set of base recipe IDs for orphan detection
    base_ids = {b["id"] for b in base_recipes}

    # Build result with variants under base
    result = []
    for base in sorted(base_recipes, key=lambda x: x.get("name") or ""):
        base["_is_base"] = True
        base["_variant_count"] = len(variant_map.get(base["id"], []))
        result.append(base)

        # Add variants indented
        for variant in variant_map.get(base["id"], []):
            variant["_is_variant"] = True
            variant["_indent_level"] = 1
            result.append(variant)

    # Add orphaned variants (base was deleted or not in filtered results)
    orphaned = [v for v in variants if v["base_recipe_id"] not in base_ids]
    for v in orphaned:
        v["_is_orphaned_variant"] = True
        result.append(v)

    return result
