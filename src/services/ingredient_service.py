"""Ingredient Service - Catalog management for generic ingredient definitions.

This module provides business logic for managing the ingredient catalog including
CRUD operations, search, dependency checking, and validation.

All functions are stateless and use session_scope() for transaction management.

Key Features:
- Auto-generated slugs from ingredient names
- Uniqueness enforcement (slug-based)
- Dependency checking before deletion
- Search by name (partial match) and category filtering
- Pagination and sorting support

Example Usage:
  >>> from src.services.ingredient_service import create_ingredient, get_ingredient
  >>> from decimal import Decimal
  >>>
  >>> # Create an ingredient
  >>> data = {
  ...     "name": "All-Purpose Flour",
  ...     "category": "Flour",
  ...     "density_g_per_ml": 0.507
  ... }
  >>> ingredient = create_ingredient(data)
  >>> ingredient.slug
  'all_purpose_flour'
  >>>
  >>> # Retrieve it
  >>> flour = get_ingredient("all_purpose_flour")
  >>> flour.name
  'All-Purpose Flour'
"""

from typing import Dict, Any, List, Optional

from ..models import Ingredient
from .database import session_scope
from .exceptions import (
    IngredientNotFoundBySlug,
    SlugAlreadyExists,
    IngredientInUse,
    ValidationError as ServiceValidationError,
    DatabaseError,
)
from ..utils.slug_utils import create_slug
from ..utils.validators import validate_ingredient_data


def create_ingredient(ingredient_data: Dict[str, Any]) -> Ingredient:
    """Create a new ingredient with auto-generated slug.

    This function validates the ingredient data, generates a unique slug from
    the name, and creates the ingredient record in the database.

    Args:
        ingredient_data: Dictionary containing ingredient fields:
            - name (str, required): Ingredient name
            - category (str, required): Category classification
            - density_g_per_ml (float, optional): For volume-weight conversions
            - foodon_id (str, optional): FoodOn taxonomy ID
            - fdc_id (str, optional): USDA FoodData Central ID
            - gtin (str, optional): Global Trade Item Number
            - allergens (List[str], optional): Allergen codes

    Returns:
        Ingredient: Created ingredient object with generated slug and ID

    Raises:
        ValidationError: If required fields missing or invalid
        SlugAlreadyExists: If generated slug conflicts (rare with auto-increment)
        DatabaseError: If database operation fails

    Example:
        >>> data = {
        ...     "name": "All-Purpose Flour",
        ...     "category": "Flour",
        ...     "density_g_per_ml": 0.507
        ... }
        >>> ingredient = create_ingredient(data)
        >>> ingredient.slug
        'all_purpose_flour'
        >>> ingredient.id is not None
        True
    """
    # Validate ingredient data
    is_valid, errors = validate_ingredient_data(ingredient_data)
    if not is_valid:
        raise ServiceValidationError(errors)

    try:
        with session_scope() as session:
            # Generate slug from name
            slug = create_slug(ingredient_data["name"], session)

            # Create ingredient instance
            fdc_ids = ingredient_data.get("fdc_ids")
            if fdc_ids is None:
                legacy_fdc = ingredient_data.get("fdc_id")
                if legacy_fdc:
                    fdc_ids = [legacy_fdc] if not isinstance(legacy_fdc, list) else legacy_fdc

            foodex2_code = ingredient_data.get("foodex2_code")
            if foodex2_code is None:
                foodex2_code = ingredient_data.get("gtin")

            ingredient = Ingredient(
                slug=slug,
                name=ingredient_data["name"],
                category=ingredient_data["category"],
                description=ingredient_data.get("description"),
                density_g_per_ml=ingredient_data.get("density_g_per_ml"),
                moisture_pct=ingredient_data.get("moisture_pct"),
                foodon_id=ingredient_data.get("foodon_id"),
                foodex2_code=foodex2_code,
                langual_terms=ingredient_data.get("langual_terms"),
                fdc_ids=fdc_ids,
                allergens=ingredient_data.get("allergens"),
                notes=ingredient_data.get("notes"),
            )

            session.add(ingredient)
            session.flush()  # Get ID before commit

            return ingredient

    except SlugAlreadyExists:
        # Re-raise slug conflicts as-is
        raise
    except Exception as e:
        # Check if it's a duplicate name IntegrityError
        error_str = str(e).lower()
        if "unique constraint" in error_str or "duplicate" in error_str:
            if "name" in error_str or "products.name" in error_str:
                raise ServiceValidationError([
                    f"An ingredient named '{ingredient_data['name']}' already exists. "
                    f"Please use a different name or edit the existing ingredient."
                ])
        raise DatabaseError(f"Failed to create ingredient", original_error=e)


def get_ingredient(slug: str) -> Ingredient:
    """Retrieve ingredient by slug.

    Args:
        slug: Unique ingredient identifier (e.g., "all_purpose_flour")

    Returns:
        Ingredient: Ingredient object with relationships eager-loaded

    Raises:
        IngredientNotFoundBySlug: If slug doesn't exist

    Example:
        >>> ingredient = get_ingredient("all_purpose_flour")
        >>> ingredient.name
        'All-Purpose Flour'
        >>> ingredient.category
        'Flour'
    """
    with session_scope() as session:
        ingredient = session.query(Ingredient).filter_by(slug=slug).first()

        if not ingredient:
            raise IngredientNotFoundBySlug(slug)

        return ingredient


def search_ingredients(
    query: Optional[str] = None, category: Optional[str] = None, limit: int = 100
) -> List[Ingredient]:
    """Search ingredients by partial name match and/or category filter.

    Args:
        query: Optional partial name to search (case-insensitive)
        category: Optional category to filter by (exact match)
        limit: Maximum number of results (default 100)

    Returns:
        List[Ingredient]: Matching ingredients, sorted by name

    Example:
        >>> results = search_ingredients(query="flour", category="Flour")
        >>> [i.name for i in results]
        ['All-Purpose Flour', 'Bread Flour', 'Cake Flour']

        >>> results = search_ingredients(category="Flour", limit=10)
        >>> len(results) <= 10
        True
    """
    with session_scope() as session:
        q = session.query(Ingredient)

        # Apply filters
        if query:
            q = q.filter(Ingredient.name.ilike(f"%{query}%"))
        if category:
            q = q.filter(Ingredient.category == category)

        # Sort and limit
        return q.order_by(Ingredient.name).limit(limit).all()


def update_ingredient(slug: str, ingredient_data: Dict[str, Any]) -> Ingredient:
    """Update ingredient attributes (slug cannot be changed).

    Args:
        slug: Ingredient identifier
        ingredient_data: Dictionary with fields to update (partial update supported)
            - name (str, optional): New name
            - category (str, optional): New category
            - density_g_per_ml (float, optional): New density
            - foodon_id, fdc_id, gtin, allergens, notes (optional): Industry standard fields

    Returns:
        Ingredient: Updated ingredient object

    Raises:
        IngredientNotFoundBySlug: If slug doesn't exist
        ValidationError: If update data invalid or attempting to change slug
        DatabaseError: If database operation fails

    Note:
        Slug cannot be changed to maintain foreign key integrity.
        Attempting to change slug will raise ValidationError.

    Example:
        >>> updated = update_ingredient("all_purpose_flour", {
        ...     "category": "Baking Essentials",
        ...     "density_g_per_ml": 0.510
        ... })
        >>> updated.category
        'Baking Essentials'
        >>> updated.slug  # Unchanged
        'all_purpose_flour'
    """
    # Prevent slug changes
    if "slug" in ingredient_data:
        raise ServiceValidationError("Slug cannot be changed after creation")

    try:
        with session_scope() as session:
            # Get existing ingredient
            ingredient = session.query(Ingredient).filter_by(slug=slug).first()
            if not ingredient:
                raise IngredientNotFoundBySlug(slug)

            # Update attributes
            for key, value in ingredient_data.items():
                if hasattr(ingredient, key):
                    setattr(ingredient, key, value)

            return ingredient

    except IngredientNotFoundBySlug:
        raise
    except ServiceValidationError:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to update ingredient '{slug}'", original_error=e)


def delete_ingredient(slug: str) -> bool:
    """Delete ingredient if not referenced by other entities.

    This function checks for dependencies (recipes, variants, pantry items)
    before deletion to prevent orphaned references.

    Args:
        slug: Ingredient identifier

    Returns:
        bool: True if deletion successful

    Raises:
        IngredientNotFoundBySlug: If slug doesn't exist
        IngredientInUse: If ingredient has dependencies (recipes, variants)
        DatabaseError: If database operation fails

    Example:
        >>> delete_ingredient("unused_ingredient")
        True

        >>> delete_ingredient("all_purpose_flour")  # Has variants
        Traceback (most recent call last):
        ...
        IngredientInUse: Cannot delete ingredient 'all_purpose_flour': used in 5 recipes, 3 variants
    """
    # Check dependencies first
    deps = check_ingredient_dependencies(slug)

    if any(deps.values()):
        raise IngredientInUse(slug, deps)

    try:
        with session_scope() as session:
            ingredient = session.query(Ingredient).filter_by(slug=slug).first()
            if not ingredient:
                raise IngredientNotFoundBySlug(slug)

            session.delete(ingredient)
            return True

    except IngredientNotFoundBySlug:
        raise
    except IngredientInUse:
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to delete ingredient '{slug}'", original_error=e)


def check_ingredient_dependencies(slug: str) -> Dict[str, int]:
    """Check if ingredient is referenced by other entities.

    Args:
        slug: Ingredient identifier

    Returns:
        Dict[str, int]: Dependency counts
            - "recipes": Number of recipes using this ingredient
            - "variants": Number of variants for this ingredient
            - "pantry_items": Number of pantry items (via variants)
            - "unit_conversions": Number of custom unit conversions

    Raises:
        IngredientNotFoundBySlug: If slug doesn't exist

    Example:
        >>> deps = check_ingredient_dependencies("all_purpose_flour")
        >>> deps
        {'recipes': 5, 'variants': 3, 'pantry_items': 12, 'unit_conversions': 2}

        >>> deps = check_ingredient_dependencies("unused_ingredient")
        >>> deps
        {'recipes': 0, 'variants': 0, 'pantry_items': 0, 'unit_conversions': 0}
    """
    # Import models here to avoid circular dependencies
    from ..models import Variant, PantryItem, UnitConversion, RecipeIngredient

    with session_scope() as session:
        # Verify ingredient exists
        ingredient = session.query(Ingredient).filter_by(slug=slug).first()
        if not ingredient:
            raise IngredientNotFoundBySlug(slug)

        ingredient_id = ingredient.id

        variants_count = (
            session.query(Variant).filter(Variant.ingredient_id == ingredient_id).count()
        )

        recipes_count = (
            session.query(RecipeIngredient)
            .filter(RecipeIngredient.ingredient_new_id == ingredient_id)
            .count()
        )

        pantry_count = (
            session.query(PantryItem)
            .join(Variant, PantryItem.variant_id == Variant.id)
            .filter(Variant.ingredient_id == ingredient_id)
            .count()
        )

        conversions_count = (
            session.query(UnitConversion)
            .filter(UnitConversion.ingredient_id == ingredient_id)
            .count()
        )

        return {
            "recipes": recipes_count,
            "variants": variants_count,
            "pantry_items": pantry_count,
            "unit_conversions": conversions_count,
        }


def list_ingredients(
    category: Optional[str] = None,
    sort_by: str = "name",
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[Ingredient]:
    """List all ingredients with optional filtering and pagination.

    Args:
        category: Optional category filter (exact match)
        sort_by: Field to sort by ("name", "category", "created_at")
        limit: Maximum number of results (None = all)
        offset: Number of results to skip (for pagination)

    Returns:
        List[Ingredient]: Ingredients matching criteria

    Example:
        >>> ingredients = list_ingredients(category="Flour", sort_by="name", limit=10)
        >>> len(ingredients) <= 10
        True

        >>> # Pagination
        >>> page_1 = list_ingredients(limit=20, offset=0)
        >>> page_2 = list_ingredients(limit=20, offset=20)
    """
    with session_scope() as session:
        q = session.query(Ingredient)

        # Apply category filter
        if category:
            q = q.filter(Ingredient.category == category)

        # Apply sorting
        if sort_by == "name":
            q = q.order_by(Ingredient.name)
        elif sort_by == "category":
            q = q.order_by(Ingredient.category, Ingredient.name)
        elif sort_by == "created_at":
            # Assuming Ingredient has created_at field (from BaseModel)
            if hasattr(Ingredient, "created_at"):
                q = q.order_by(Ingredient.created_at.desc())
            else:
                q = q.order_by(Ingredient.name)  # Fallback
        else:
            q = q.order_by(Ingredient.name)  # Default

        # Apply pagination
        q = q.offset(offset)
        if limit:
            q = q.limit(limit)

        return q.all()


def get_all_ingredients(
    category: Optional[str] = None,
    sort_by: str = "name",
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Alias for list_ingredients() returning dictionaries for backward compatibility.

    This function exists to maintain compatibility with UI code that calls
    get_all_ingredients() and expects dictionary results. New code should use
    list_ingredients() directly which returns Ingredient model objects.

    Args:
        category: Optional category filter (exact match)
        sort_by: Field to sort by ("name", "category", "created_at")
        limit: Maximum number of results (None = all)
        offset: Number of results to skip (for pagination)

    Returns:
        List[Dict[str, Any]]: Ingredient data as dictionaries
    """
    ingredients = list_ingredients(category=category, sort_by=sort_by, limit=limit, offset=offset)

    # Convert Ingredient objects to dictionaries for UI compatibility
    return [
        {
            "id": ing.id,
            "slug": ing.slug,
            "name": ing.name,
            "category": ing.category,
            "density_g_per_ml": ing.density_g_per_ml,
            "notes": ing.notes,
        }
        for ing in ingredients
    ]
