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
  >>>
  >>> # Create an ingredient with 4-field density (1 cup = 4.25 oz)
  >>> data = {
  ...     "name": "All-Purpose Flour",
  ...     "category": "Flour",
  ...     "density_volume_value": 1.0,
  ...     "density_volume_unit": "cup",
  ...     "density_weight_value": 4.25,
  ...     "density_weight_unit": "oz",
  ... }
  >>> ingredient = create_ingredient(data)
  >>> ingredient.slug
  'all_purpose_flour'
  >>> ingredient.format_density_display()
  '1 cup = 4.25 oz'
  >>>
  >>> # Retrieve it
  >>> flour = get_ingredient("all_purpose_flour")
  >>> flour.display_name
  'All-Purpose Flour'
"""

import logging
from typing import Dict, Any, List, Optional, Tuple

from ..models import Ingredient
from .database import session_scope
from .exceptions import (
    IngredientNotFoundBySlug,
    SlugAlreadyExists,
    IngredientInUse,
    ValidationError as ServiceValidationError,
    DatabaseError,
    IngredientNotFound,
    MaxDepthExceededError,
    CircularReferenceError,
)
from ..utils.slug_utils import create_slug
from ..utils.validators import validate_ingredient_data
from ..utils.constants import VOLUME_UNITS, WEIGHT_UNITS

# Configure logging
logger = logging.getLogger(__name__)


def validate_density_fields(
    volume_value: Optional[float],
    volume_unit: Optional[str],
    weight_value: Optional[float],
    weight_unit: Optional[str],
) -> Tuple[bool, str]:
    """
    Validate density field group (all or nothing).

    Args:
        volume_value: Volume amount (e.g., 1.0)
        volume_unit: Volume unit (e.g., "cup")
        weight_value: Weight amount (e.g., 4.25)
        weight_unit: Weight unit (e.g., "oz")

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Normalize empty strings to None
    fields = [
        volume_value if volume_value not in (None, "", 0) else None,
        volume_unit if volume_unit not in (None, "") else None,
        weight_value if weight_value not in (None, "", 0) else None,
        weight_unit if weight_unit not in (None, "") else None,
    ]

    filled_count = sum(1 for f in fields if f is not None)

    # All empty is valid (no density)
    if filled_count == 0:
        return True, ""

    # Partially filled is invalid
    if filled_count < 4:
        return False, "All density fields must be provided together"

    # Validate positive values
    if volume_value <= 0:
        return False, "Volume value must be greater than zero"

    if weight_value <= 0:
        return False, "Weight value must be greater than zero"

    # Validate unit types
    volume_unit_lower = volume_unit.lower()
    if volume_unit_lower not in [u.lower() for u in VOLUME_UNITS]:
        return False, f"Invalid volume unit: {volume_unit}"

    weight_unit_lower = weight_unit.lower()
    if weight_unit_lower not in [u.lower() for u in WEIGHT_UNITS]:
        return False, f"Invalid weight unit: {weight_unit}"

    return True, ""


def create_ingredient(ingredient_data: Dict[str, Any]) -> Ingredient:
    """Create a new ingredient with auto-generated slug.

    This function validates the ingredient data, generates a unique slug from
    the name, and creates the ingredient record in the database.

    Args:
        ingredient_data: Dictionary containing ingredient fields:
            - display_name or name (str, required): Ingredient display name
              (name is normalized to display_name for backward compatibility)
            - category (str, required): Category classification
            - density_volume_value (float, optional): Volume amount for density
            - density_volume_unit (str, optional): Volume unit for density
            - density_weight_value (float, optional): Weight amount for density
            - density_weight_unit (str, optional): Weight unit for density
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
        ...     "density_volume_value": 1.0,
        ...     "density_volume_unit": "cup",
        ...     "density_weight_value": 4.25,
        ...     "density_weight_unit": "oz"
        ... }
        >>> ingredient = create_ingredient(data)
        >>> ingredient.slug
        'all_purpose_flour'
        >>> ingredient.id is not None
        True
    """
    # Normalize field names for backward compatibility (F035)
    # UI may send "name" but service expects "display_name"
    if "name" in ingredient_data and "display_name" not in ingredient_data:
        ingredient_data["display_name"] = ingredient_data.pop("name")

    # Validate ingredient data
    is_valid, errors = validate_ingredient_data(ingredient_data)
    if not is_valid:
        raise ServiceValidationError(errors)

    # Validate density fields
    density_valid, density_error = validate_density_fields(
        ingredient_data.get("density_volume_value"),
        ingredient_data.get("density_volume_unit"),
        ingredient_data.get("density_weight_value"),
        ingredient_data.get("density_weight_unit"),
    )
    if not density_valid:
        raise ServiceValidationError(density_error)

    try:
        with session_scope() as session:
            # Generate slug from display_name
            slug = create_slug(ingredient_data["display_name"], session)

            # Feature 031: Handle hierarchy fields
            parent_ingredient_id = ingredient_data.get("parent_ingredient_id")
            hierarchy_level = ingredient_data.get("hierarchy_level")

            if parent_ingredient_id is not None:
                # Validate parent exists
                parent = (
                    session.query(Ingredient).filter(Ingredient.id == parent_ingredient_id).first()
                )
                if parent is None:
                    raise IngredientNotFound(parent_ingredient_id)

                # Calculate hierarchy level from parent
                calculated_level = parent.hierarchy_level + 1
                if calculated_level > 2:
                    raise MaxDepthExceededError(0, calculated_level)  # 0 = new ingredient

                # Use calculated level (override any provided value)
                hierarchy_level = calculated_level
            else:
                # No parent - default to level 2 (leaf) for backwards compatibility
                if hierarchy_level is None:
                    hierarchy_level = 2

            # Validate hierarchy level is valid (0, 1, or 2)
            if hierarchy_level not in (0, 1, 2):
                raise ServiceValidationError(
                    [f"Invalid hierarchy level: {hierarchy_level}. Must be 0, 1, or 2."]
                )

            # Create ingredient instance
            fdc_ids = ingredient_data.get("fdc_ids")
            if fdc_ids is None:
                legacy_fdc = ingredient_data.get("fdc_id")
                if legacy_fdc:
                    fdc_ids = [legacy_fdc] if not isinstance(legacy_fdc, list) else legacy_fdc

            foodex2_code = ingredient_data.get("foodex2_code")
            if foodex2_code is None:
                foodex2_code = ingredient_data.get("gtin")

            display_name = ingredient_data["display_name"]
            category = ingredient_data["category"]

            ingredient = Ingredient(
                slug=slug,
                display_name=display_name,
                category=category,
                description=ingredient_data.get("description"),
                # Feature 031: Hierarchy fields
                parent_ingredient_id=parent_ingredient_id,
                hierarchy_level=hierarchy_level,
                density_volume_value=ingredient_data.get("density_volume_value"),
                density_volume_unit=ingredient_data.get("density_volume_unit"),
                density_weight_value=ingredient_data.get("density_weight_value"),
                density_weight_unit=ingredient_data.get("density_weight_unit"),
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
    except (IngredientNotFound, MaxDepthExceededError, ServiceValidationError):
        # Re-raise hierarchy validation errors as-is
        raise
    except Exception as e:
        # Check if it's a duplicate name IntegrityError
        error_str = str(e).lower()
        if "unique constraint" in error_str or "duplicate" in error_str:
            if "name" in error_str or "display_name" in error_str or "ingredients." in error_str:
                display_name = ingredient_data.get("display_name") or ingredient_data.get("name")
                raise ServiceValidationError(
                    [
                        f"An ingredient named '{display_name}' already exists. "
                        f"Please use a different name or edit the existing ingredient."
                    ]
                )
        raise DatabaseError(f"Failed to create ingredient", original_error=e)


def get_ingredient(slug: str, session=None) -> Ingredient:
    """Retrieve ingredient by slug.

    Args:
        slug: Unique ingredient identifier (e.g., "all_purpose_flour")
        session: Optional database session. If provided, uses this session instead
                 of creating a new one. This is important for maintaining transactional
                 atomicity when called from within another session_scope block.

    Returns:
        Ingredient: Ingredient object with relationships eager-loaded

    Raises:
        IngredientNotFoundBySlug: If slug doesn't exist

    Example:
        >>> ingredient = get_ingredient("all_purpose_flour")
        >>> ingredient.display_name
        'All-Purpose Flour'
        >>> ingredient.category
        'Flour'
    """
    if session is not None:
        ingredient = session.query(Ingredient).filter_by(slug=slug).first()
        if not ingredient:
            raise IngredientNotFoundBySlug(slug)
        return ingredient

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
            q = q.filter(Ingredient.display_name.ilike(f"%{query}%"))
        if category:
            q = q.filter(Ingredient.category == category)

        # Sort and limit
        return q.order_by(Ingredient.display_name).limit(limit).all()


def update_ingredient(slug: str, ingredient_data: Dict[str, Any]) -> Ingredient:
    """Update ingredient attributes (slug cannot be changed).

    Args:
        slug: Ingredient identifier
        ingredient_data: Dictionary with fields to update (partial update supported)
            - name (str, optional): New name
            - category (str, optional): New category
            - density_volume_value (float, optional): Volume amount for density
            - density_volume_unit (str, optional): Volume unit for density
            - density_weight_value (float, optional): Weight amount for density
            - density_weight_unit (str, optional): Weight unit for density
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
        ...     "density_volume_value": 1.0,
        ...     "density_volume_unit": "cup",
        ...     "density_weight_value": 4.25,
        ...     "density_weight_unit": "oz"
        ... })
        >>> updated.category
        'Baking Essentials'
        >>> updated.slug  # Unchanged
        'all_purpose_flour'
    """
    # Prevent slug changes
    if "slug" in ingredient_data:
        raise ServiceValidationError("Slug cannot be changed after creation")

    # Validate density fields if any are being updated
    density_valid, density_error = validate_density_fields(
        ingredient_data.get("density_volume_value"),
        ingredient_data.get("density_volume_unit"),
        ingredient_data.get("density_weight_value"),
        ingredient_data.get("density_weight_unit"),
    )
    if not density_valid:
        raise ServiceValidationError(density_error)

    try:
        with session_scope() as session:
            # Get existing ingredient
            ingredient = session.query(Ingredient).filter_by(slug=slug).first()
            if not ingredient:
                raise IngredientNotFoundBySlug(slug)

            # Feature 031: Handle hierarchy field changes
            new_parent_id = ingredient_data.get("parent_ingredient_id")
            if (
                "parent_ingredient_id" in ingredient_data
                and new_parent_id != ingredient.parent_ingredient_id
            ):
                # Parent is changing - use move_ingredient logic
                from . import ingredient_hierarchy_service

                ingredient_hierarchy_service.move_ingredient(
                    ingredient.id, new_parent_id, session=session
                )
                # Remove from ingredient_data so it's not set again below
                ingredient_data = {
                    k: v for k, v in ingredient_data.items() if k != "parent_ingredient_id"
                }
                # Also remove hierarchy_level as move_ingredient handles it
                ingredient_data = {
                    k: v for k, v in ingredient_data.items() if k != "hierarchy_level"
                }

            # Update attributes
            for key, value in ingredient_data.items():
                if hasattr(ingredient, key):
                    setattr(ingredient, key, value)

            return ingredient

    except IngredientNotFoundBySlug:
        raise
    except (
        ServiceValidationError,
        IngredientNotFound,
        MaxDepthExceededError,
        CircularReferenceError,
    ):
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to update ingredient '{slug}'", original_error=e)


def delete_ingredient(slug: str) -> bool:
    """Delete ingredient if not referenced by other entities.

    This function checks for dependencies (recipes, products, inventory items)
    before deletion to prevent orphaned references.

    Args:
        slug: Ingredient identifier

    Returns:
        bool: True if deletion successful

    Raises:
        IngredientNotFoundBySlug: If slug doesn't exist
        IngredientInUse: If ingredient has dependencies (recipes, products)
        DatabaseError: If database operation fails

    Example:
        >>> delete_ingredient("unused_ingredient")
        True

        >>> delete_ingredient("all_purpose_flour")  # Has products
        Traceback (most recent call last):
        ...
        IngredientInUse: Cannot delete ingredient 'all_purpose_flour': used in 5 recipes, 3 products
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


# =============================================================================
# Feature 035: Safe Deletion with Protection (F035)
# =============================================================================


def can_delete_ingredient(ingredient_id: int, session=None) -> Tuple[bool, str, Dict[str, int]]:
    """Check if ingredient can be deleted.

    This function checks all blocking conditions before deletion:
    - Products referencing the ingredient (blocks deletion)
    - RecipeIngredients referencing the ingredient (blocks deletion)
    - Child ingredients (blocks deletion)
    - SnapshotIngredients (does NOT block - will be denormalized)

    Args:
        ingredient_id: ID of ingredient to check
        session: Optional SQLAlchemy session

    Returns:
        Tuple of (can_delete, reason, details)
        - can_delete: True if deletion is allowed
        - reason: Error message if blocked, empty string if allowed
        - details: Dict with counts {products: N, recipes: N, children: N, snapshots: N}

    Example:
        >>> can_delete, reason, details = can_delete_ingredient(123)
        >>> if not can_delete:
        ...     print(f"Blocked: {reason}")
        ...     print(f"Products: {details['products']}, Recipes: {details['recipes']}")
    """
    from ..models import Product, RecipeIngredient
    from ..models.inventory_snapshot import SnapshotIngredient
    from .ingredient_hierarchy_service import get_child_count

    def _check(session):
        details = {
            "products": 0,
            "recipes": 0,
            "children": 0,
            "snapshots": 0,
        }
        reasons = []

        # Check Product references (blocks deletion)
        product_count = (
            session.query(Product).filter(Product.ingredient_id == ingredient_id).count()
        )
        details["products"] = product_count
        if product_count > 0:
            reasons.append(
                f"{product_count} product{'s' if product_count != 1 else ''} reference this ingredient"
            )

        # Check RecipeIngredient references (blocks deletion)
        recipe_count = (
            session.query(RecipeIngredient)
            .filter(RecipeIngredient.ingredient_id == ingredient_id)
            .count()
        )
        details["recipes"] = recipe_count
        if recipe_count > 0:
            reasons.append(
                f"{recipe_count} recipe{'s' if recipe_count != 1 else ''} use this ingredient"
            )

        # Check child ingredients (blocks deletion)
        child_count = get_child_count(ingredient_id, session=session)
        details["children"] = child_count
        if child_count > 0:
            reasons.append(f"{child_count} child ingredient{'s' if child_count != 1 else ''} exist")

        # Check SnapshotIngredient references (does NOT block, just count for info)
        snapshot_count = (
            session.query(SnapshotIngredient)
            .filter(SnapshotIngredient.ingredient_id == ingredient_id)
            .count()
        )
        details["snapshots"] = snapshot_count

        if reasons:
            reason = (
                "Cannot delete: " + "; ".join(reasons) + ". Reassign or remove references first."
            )
            return False, reason, details

        return True, "", details

    if session is not None:
        return _check(session)
    with session_scope() as session:
        return _check(session)


def _denormalize_snapshot_ingredients(ingredient_id: int, session) -> int:
    """Copy ingredient names to snapshot records before deletion.

    This preserves historical data when the ingredient is deleted.
    After denormalization, the ingredient_id FK is set to NULL.

    Args:
        ingredient_id: ID of ingredient being deleted
        session: SQLAlchemy session (required, not optional)

    Returns:
        Count of records denormalized
    """
    from ..models.inventory_snapshot import SnapshotIngredient
    from .ingredient_hierarchy_service import get_ancestors

    # Get the ingredient being deleted
    ingredient = session.query(Ingredient).filter(Ingredient.id == ingredient_id).first()

    if not ingredient:
        return 0

    # Get hierarchy ancestors for parent names
    ancestors = get_ancestors(ingredient_id, session=session)

    # Determine parent names from ancestors
    # ancestors returns [immediate parent, grandparent, ...] (nearest to farthest)
    # Note: get_ancestors() returns list of dicts from .to_dict()
    l1_name = None
    l0_name = None
    if len(ancestors) >= 1:
        l1_name = ancestors[0]["display_name"]  # Immediate parent (L1)
    if len(ancestors) >= 2:
        l0_name = ancestors[1]["display_name"]  # Grandparent (L0/root)

    # Find all snapshot records referencing this ingredient
    snapshots = (
        session.query(SnapshotIngredient)
        .filter(SnapshotIngredient.ingredient_id == ingredient_id)
        .all()
    )

    count = 0
    for snapshot in snapshots:
        # Denormalize names
        snapshot.ingredient_name_snapshot = ingredient.display_name
        snapshot.parent_l1_name_snapshot = l1_name
        snapshot.parent_l0_name_snapshot = l0_name
        # Nullify FK (ingredient will be deleted)
        snapshot.ingredient_id = None
        count += 1

    return count


def delete_ingredient_safe(ingredient_id: int, session=None) -> bool:
    """Safely delete an ingredient with full protection.

    This function:
    1. Checks if deletion is allowed (no Product/Recipe/child references)
    2. Denormalizes snapshot records to preserve historical data
    3. Deletes the ingredient (cascades Alias/Crosswalk via DB)

    Args:
        ingredient_id: ID of ingredient to delete
        session: Optional SQLAlchemy session

    Returns:
        True if deleted successfully

    Raises:
        IngredientNotFound: If ingredient doesn't exist
        IngredientInUse: If ingredient has blocking references
        DatabaseError: If database operation fails

    Example:
        >>> try:
        ...     delete_ingredient_safe(123)
        ...     print("Deleted successfully")
        ... except IngredientInUse as e:
        ...     print(f"Cannot delete: {e.details}")
    """

    def _delete(session):
        # Verify ingredient exists
        ingredient = session.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if not ingredient:
            raise IngredientNotFound(ingredient_id)

        # Check if deletion is allowed
        can_delete, reason, details = can_delete_ingredient(ingredient_id, session=session)
        if not can_delete:
            raise IngredientInUse(ingredient_id, details)

        # Denormalize snapshot records
        denorm_count = _denormalize_snapshot_ingredients(ingredient_id, session)
        if denorm_count > 0:
            logger.info(
                f"Denormalized {denorm_count} snapshot records for ingredient {ingredient_id}"
            )

        # Delete ingredient (Alias/Crosswalk cascade via DB foreign key constraints)
        session.delete(ingredient)

        return True

    try:
        if session is not None:
            return _delete(session)
        with session_scope() as session:
            return _delete(session)
    except (IngredientNotFound, IngredientInUse):
        raise
    except Exception as e:
        raise DatabaseError(f"Failed to delete ingredient {ingredient_id}", original_error=e)


def check_ingredient_dependencies(slug: str) -> Dict[str, int]:
    """Check if ingredient is referenced by other entities.

    Args:
        slug: Ingredient identifier

    Returns:
        Dict[str, int]: Dependency counts
            - "recipes": Number of recipes using this ingredient
            - "products": Number of products for this ingredient
            - "inventory_items": Number of inventory items (via products)

    Raises:
        IngredientNotFoundBySlug: If slug doesn't exist

    Example:
        >>> deps = check_ingredient_dependencies("all_purpose_flour")
        >>> deps
        {'recipes': 5, 'products': 3, 'inventory_items': 12}

        >>> deps = check_ingredient_dependencies("unused_ingredient")
        >>> deps
        {'recipes': 0, 'products': 0, 'inventory_items': 0}
    """
    # Import models here to avoid circular dependencies
    from ..models import Product, InventoryItem, RecipeIngredient

    with session_scope() as session:
        # Verify ingredient exists
        ingredient = session.query(Ingredient).filter_by(slug=slug).first()
        if not ingredient:
            raise IngredientNotFoundBySlug(slug)

        ingredient_id = ingredient.id

        products_count = (
            session.query(Product).filter(Product.ingredient_id == ingredient_id).count()
        )

        recipes_count = (
            session.query(RecipeIngredient)
            .filter(RecipeIngredient.ingredient_id == ingredient_id)
            .count()
        )

        inventory_count = (
            session.query(InventoryItem)
            .join(Product, InventoryItem.product_id == Product.id)
            .filter(Product.ingredient_id == ingredient_id)
            .count()
        )

        return {
            "recipes": recipes_count,
            "products": products_count,
            "inventory_items": inventory_count,
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
            q = q.order_by(Ingredient.display_name)
        elif sort_by == "category":
            q = q.order_by(Ingredient.category, Ingredient.display_name)
        elif sort_by == "created_at":
            # Assuming Ingredient has created_at field (from BaseModel)
            if hasattr(Ingredient, "created_at"):
                q = q.order_by(Ingredient.created_at.desc())
            else:
                q = q.order_by(Ingredient.display_name)  # Fallback
        else:
            q = q.order_by(Ingredient.display_name)  # Default

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
            "name": ing.display_name,
            "display_name": ing.display_name,  # F031: UI expects this key
            "category": ing.category,
            "hierarchy_level": ing.hierarchy_level,  # F031: hierarchy level (0/1/2)
            "parent_ingredient_id": ing.parent_ingredient_id,  # F031: parent reference
            "density_volume_value": ing.density_volume_value,
            "density_volume_unit": ing.density_volume_unit,
            "density_weight_value": ing.density_weight_value,
            "density_weight_unit": ing.density_weight_unit,
            "density_display": ing.format_density_display(),
            "notes": ing.notes,
        }
        for ing in ingredients
    ]


def get_distinct_ingredient_categories() -> List[str]:
    """Get distinct ingredient categories from the database.

    This is the canonical source for ingredient categories. UI components
    should use this instead of hardcoded constants.

    Returns:
        List of distinct category names, sorted alphabetically.
    """
    with session_scope() as session:
        categories = [
            row[0] for row in session.query(Ingredient.category).distinct().all() if row[0]
        ]
        return sorted(categories)


def get_all_distinct_categories() -> List[str]:
    """Get all distinct ingredient categories (food + packaging) from database.

    Returns:
        List of all distinct category names, sorted alphabetically.
    """
    with session_scope() as session:
        categories = [
            row[0] for row in session.query(Ingredient.category).distinct().all() if row[0]
        ]
        return sorted(categories)
