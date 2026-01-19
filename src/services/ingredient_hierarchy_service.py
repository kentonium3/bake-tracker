"""
Ingredient hierarchy service for tree traversal and navigation.

This service provides tree traversal and hierarchy management operations
for the ingredient taxonomy. All hierarchy-related business logic is
encapsulated here, keeping the UI layer thin.

Feature 031: Ingredient Hierarchy Taxonomy
Feature 033: Added validation convenience functions (get_child_count,
             get_product_count, can_change_parent)
"""

from typing import List, Dict, Optional, Any

from src.models.ingredient import Ingredient
from src.models.product import Product
from src.services.database import session_scope
from src.services.exceptions import (
    IngredientNotFound,
    CircularReferenceError,
    MaxDepthExceededError,
    HierarchyValidationError,
)


def get_root_ingredients(session=None) -> List[Dict]:
    """
    Get all root-level (hierarchy_level=0) ingredients.

    Args:
        session: Optional SQLAlchemy session

    Returns:
        List of ingredient dictionaries, sorted by display_name
    """

    def _impl(session):
        results = (
            session.query(Ingredient)
            .filter(Ingredient.hierarchy_level == 0)
            .order_by(Ingredient.display_name)
            .all()
        )
        return [i.to_dict() for i in results]

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def get_children(parent_id: int, session=None) -> List[Dict]:
    """
    Get direct children of an ingredient.

    Args:
        parent_id: ID of parent ingredient
        session: Optional SQLAlchemy session

    Returns:
        List of child ingredient dictionaries, sorted by display_name

    Raises:
        IngredientNotFound: If parent_id doesn't exist
    """

    def _impl(session):
        # Verify parent exists
        parent = session.query(Ingredient).filter(Ingredient.id == parent_id).first()
        if parent is None:
            raise IngredientNotFound(parent_id)

        results = (
            session.query(Ingredient)
            .filter(Ingredient.parent_ingredient_id == parent_id)
            .order_by(Ingredient.display_name)
            .all()
        )
        return [i.to_dict() for i in results]

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def get_ancestors(ingredient_id: int, session=None) -> List[Dict]:
    """
    Get path from ingredient to root (for breadcrumb display).

    Args:
        ingredient_id: ID of ingredient
        session: Optional SQLAlchemy session

    Returns:
        List of ancestors ordered from immediate parent to root

    Raises:
        IngredientNotFound: If ingredient_id doesn't exist
    """

    def _impl(session):
        ingredient = session.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if ingredient is None:
            raise IngredientNotFound(ingredient_id)

        ancestors = []
        current = ingredient.parent
        while current is not None:
            ancestors.append(current.to_dict())
            current = current.parent

        return ancestors

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def get_descendants(ingredient_id: int, session=None) -> List[Dict]:
    """
    Get all descendants (recursive) of an ingredient.

    Args:
        ingredient_id: ID of ingredient to get descendants for
        session: Optional SQLAlchemy session

    Returns:
        List of all descendant ingredients (all levels below this ingredient)

    Raises:
        IngredientNotFound: If ingredient_id doesn't exist
    """

    def _impl(session):
        ingredient = session.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if ingredient is None:
            raise IngredientNotFound(ingredient_id)

        descendants = []
        _collect_descendants(ingredient, descendants, session)
        return descendants

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def _collect_descendants(ingredient: Ingredient, descendants: List[Dict], session) -> None:
    """
    Recursively collect all descendants of an ingredient.

    Helper function for get_descendants.
    """
    # Get direct children
    children = (
        session.query(Ingredient).filter(Ingredient.parent_ingredient_id == ingredient.id).all()
    )
    for child in children:
        descendants.append(child.to_dict())
        _collect_descendants(child, descendants, session)


def get_ingredients_by_level(level: int, session=None) -> List[Dict]:
    """
    Get all ingredients at a specific hierarchy level.

    Args:
        level: Hierarchy level (0=root, 1=mid-tier, 2=leaf)
        session: Optional SQLAlchemy session

    Returns:
        List of ingredient dictionaries at the specified level, sorted by display_name
    """

    def _impl(session):
        results = (
            session.query(Ingredient)
            .filter(Ingredient.hierarchy_level == level)
            .order_by(Ingredient.display_name)
            .all()
        )
        return [i.to_dict() for i in results]

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def get_ingredient_by_id(ingredient_id: int, session=None) -> Optional[Dict]:
    """
    Get a single ingredient by ID.

    Args:
        ingredient_id: ID of ingredient to retrieve
        session: Optional SQLAlchemy session

    Returns:
        Ingredient dictionary, or None if not found
    """

    def _impl(session):
        ingredient = session.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if ingredient is None:
            return None
        return ingredient.to_dict()

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def get_leaf_ingredients(parent_id: Optional[int] = None, session=None) -> List[Dict]:
    """
    Get all leaf-level (hierarchy_level=2) ingredients.

    Args:
        parent_id: Optional - filter to descendants of this parent
        session: Optional SQLAlchemy session

    Returns:
        List of leaf ingredients, sorted by display_name
    """

    def _impl(session):
        if parent_id is None:
            # Return all leaves
            results = (
                session.query(Ingredient)
                .filter(Ingredient.hierarchy_level == 2)
                .order_by(Ingredient.display_name)
                .all()
            )
            return [i.to_dict() for i in results]
        else:
            # Return leaves that are descendants of the specified parent
            # First get all descendants, then filter to leaves
            descendants = get_descendants(parent_id, session=session)
            leaves = [d for d in descendants if d.get("hierarchy_level") == 2]
            # Sort by display_name
            return sorted(leaves, key=lambda x: x.get("display_name", ""))

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def get_all_leaf_ingredients_with_ancestors(
    l0_filter_id: Optional[int] = None, session=None
) -> List[Dict]:
    """
    Get all L2 (leaf) ingredients with pre-resolved L0 and L1 ancestor names.

    Feature 052: Optimized method for Ingredients tab display that returns
    leaf ingredients with their hierarchy context pre-computed to avoid
    N+1 queries in the UI.

    Args:
        l0_filter_id: Optional - filter to descendants of this L0 root category
        session: Optional SQLAlchemy session

    Returns:
        List of dicts with keys:
        - l0_name: str - Root category (L0) display name
        - l1_name: str - Subcategory (L1) display name
        - l2_name: str - Ingredient (L2) display name
        - ingredient: dict - Full ingredient dict from to_dict()
    """

    def _impl(session):
        # Get all L2 ingredients
        query = (
            session.query(Ingredient)
            .filter(Ingredient.hierarchy_level == 2)
            .order_by(Ingredient.display_name)
        )
        ingredients = query.all()

        result = []
        for ing in ingredients:
            # Walk up the parent chain to get L1 and L0 names
            l1 = ing.parent
            l0 = l1.parent if l1 else None

            l0_name = l0.display_name if l0 else ""
            l1_name = l1.display_name if l1 else ""

            # Apply L0 filter if specified
            if l0_filter_id is not None:
                if l0 is None or l0.id != l0_filter_id:
                    continue

            result.append(
                {
                    "l0_name": l0_name,
                    "l1_name": l1_name,
                    "l2_name": ing.display_name,
                    "ingredient": ing.to_dict(),
                }
            )

        return result

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def get_ingredient_with_ancestors(ingredient_id: int, session=None) -> Optional[Dict]:
    """
    Get a single ingredient with its L0 and L1 ancestor names resolved.

    Feature 052: Helper for detailed ingredient display.

    Args:
        ingredient_id: ID of ingredient to retrieve
        session: Optional SQLAlchemy session

    Returns:
        Dict with keys: l0_name, l1_name, l2_name, ingredient
        Or None if ingredient not found
    """

    def _impl(session):
        ingredient = session.query(Ingredient).filter(Ingredient.id == ingredient_id).first()

        if not ingredient:
            return None

        l1 = ingredient.parent
        l0 = l1.parent if l1 else None

        return {
            "l0_name": l0.display_name if l0 else "",
            "l1_name": l1.display_name if l1 else "",
            "l2_name": ingredient.display_name,
            "ingredient": ingredient.to_dict(),
        }

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def get_ingredient_tree(session=None) -> List[Dict]:
    """
    Build a nested tree structure of all ingredients.

    Returns a list of root ingredients, each with a 'children' field
    containing their nested descendants recursively.

    Args:
        session: Optional SQLAlchemy session

    Returns:
        List of root ingredient dicts, each with nested 'children' lists
    """

    def _impl(session):
        # Get all ingredients in one query
        all_ingredients = (
            session.query(Ingredient)
            .order_by(Ingredient.hierarchy_level, Ingredient.display_name)
            .all()
        )

        # Build lookup by ID
        by_id = {}
        for ing in all_ingredients:
            ing_dict = ing.to_dict()
            ing_dict["children"] = []
            by_id[ing.id] = ing_dict

        # Build tree structure
        roots = []
        for ing in all_ingredients:
            ing_dict = by_id[ing.id]
            if ing.parent_ingredient_id is None:
                roots.append(ing_dict)
            else:
                parent_dict = by_id.get(ing.parent_ingredient_id)
                if parent_dict:
                    parent_dict["children"].append(ing_dict)

        return roots

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def is_leaf(ingredient_id: int, session=None) -> bool:
    """
    Check if ingredient is a leaf (hierarchy_level=2).

    Args:
        ingredient_id: ID of ingredient
        session: Optional SQLAlchemy session

    Returns:
        True if leaf, False otherwise

    Raises:
        IngredientNotFound: If ingredient_id doesn't exist
    """

    def _impl(session):
        ingredient = session.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if ingredient is None:
            raise IngredientNotFound(ingredient_id)
        return ingredient.hierarchy_level == 2

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


# =============================================================================
# Validation Functions (WP03)
# =============================================================================


def validate_hierarchy_level(ingredient_id: int, allowed_levels: List[int], session=None) -> bool:
    """
    Check if ingredient is at an allowed hierarchy level.

    Args:
        ingredient_id: ID of ingredient to check
        allowed_levels: List of allowed levels (e.g., [2] for recipes)
        session: Optional SQLAlchemy session

    Returns:
        True if valid

    Raises:
        HierarchyValidationError: With helpful message if invalid
        IngredientNotFound: If ingredient doesn't exist
    """

    def _impl(session):
        ingredient = session.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if ingredient is None:
            raise IngredientNotFound(ingredient_id)

        if ingredient.hierarchy_level in allowed_levels:
            return True

        allowed_str = ", ".join(str(lvl) for lvl in allowed_levels)
        raise HierarchyValidationError(
            f"Ingredient '{ingredient.display_name}' is at level {ingredient.hierarchy_level}, "
            f"but only levels [{allowed_str}] are allowed"
        )

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def would_create_cycle(ingredient_id: int, new_parent_id: int, session=None) -> bool:
    """
    Check if setting new_parent_id would create a circular reference.

    Args:
        ingredient_id: ID of ingredient being moved
        new_parent_id: Proposed new parent ID
        session: Optional SQLAlchemy session

    Returns:
        True if cycle would be created, False if safe
    """

    def _impl(session):
        # Self-reference is a cycle
        if ingredient_id == new_parent_id:
            return True

        # Walk from new_parent up to root
        current = session.query(Ingredient).filter(Ingredient.id == new_parent_id).first()
        while current is not None:
            if current.id == ingredient_id:
                return True  # Found ingredient in ancestor chain - cycle!
            current = current.parent

        return False  # Safe - no cycle

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def validate_hierarchy(ingredient_id: int, proposed_parent_id: Optional[int], session=None) -> bool:
    """
    Validate that a proposed parent assignment is safe.

    Performs all hierarchy validation checks:
    - Both ingredient and proposed parent exist
    - No circular reference would be created
    - Max depth (3 levels: 0, 1, 2) would not be exceeded

    Args:
        ingredient_id: ID of ingredient to validate
        proposed_parent_id: Proposed new parent ID (None = make root)
        session: Optional SQLAlchemy session

    Returns:
        True if the proposed parent assignment is valid

    Raises:
        IngredientNotFound: If ingredient or parent doesn't exist
        CircularReferenceError: If assignment would create cycle
        MaxDepthExceededError: If assignment would exceed max depth
    """

    def _impl(session):
        # Verify ingredient exists
        ingredient = session.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if ingredient is None:
            raise IngredientNotFound(ingredient_id)

        # If becoming root, only need to check depth of descendants
        if proposed_parent_id is None:
            new_level = 0
        else:
            # Verify proposed parent exists
            parent = session.query(Ingredient).filter(Ingredient.id == proposed_parent_id).first()
            if parent is None:
                raise IngredientNotFound(proposed_parent_id)

            # Check for cycle
            if would_create_cycle(ingredient_id, proposed_parent_id, session=session):
                raise CircularReferenceError(ingredient_id, proposed_parent_id)

            # Calculate new level
            new_level = parent.hierarchy_level + 1

        # Check max depth for ingredient
        if new_level > 2:
            raise MaxDepthExceededError(ingredient_id, new_level)

        # Check max depth for descendants
        level_diff = new_level - ingredient.hierarchy_level
        descendants = get_descendants(ingredient_id, session=session)
        for desc in descendants:
            desc_new_level = desc.get("hierarchy_level", 0) + level_diff
            if desc_new_level > 2:
                raise MaxDepthExceededError(desc.get("id"), desc_new_level)

        return True

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def move_ingredient(ingredient_id: int, new_parent_id: Optional[int], session=None) -> Dict:
    """
    Move ingredient to a new parent with full validation.

    Args:
        ingredient_id: ID of ingredient to move
        new_parent_id: ID of new parent (None = make root)
        session: Optional SQLAlchemy session

    Returns:
        Updated ingredient dictionary

    Raises:
        IngredientNotFound: If ingredient or parent not found
        CircularReferenceError: If move would create cycle
        MaxDepthExceededError: If move would exceed max depth (3 levels)
    """

    def _impl(session):
        # Get ingredient
        ingredient = session.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if ingredient is None:
            raise IngredientNotFound(ingredient_id)

        # If moving to no parent, becomes root (level 0)
        if new_parent_id is None:
            new_level = 0
        else:
            # Verify new parent exists
            new_parent = session.query(Ingredient).filter(Ingredient.id == new_parent_id).first()
            if new_parent is None:
                raise IngredientNotFound(new_parent_id)

            # Check for cycle
            if would_create_cycle(ingredient_id, new_parent_id, session=session):
                raise CircularReferenceError(ingredient_id, new_parent_id)

            # Calculate new level
            new_level = new_parent.hierarchy_level + 1

        # Check max depth (max level is 2)
        if new_level > 2:
            raise MaxDepthExceededError(ingredient_id, new_level)

        # Check if ingredient has children - they would also move deeper
        children = (
            session.query(Ingredient).filter(Ingredient.parent_ingredient_id == ingredient_id).all()
        )
        for child in children:
            child_new_level = new_level + (child.hierarchy_level - ingredient.hierarchy_level)
            if child_new_level > 2:
                raise MaxDepthExceededError(child.id, child_new_level)

        # Calculate level difference for updating children
        level_diff = new_level - ingredient.hierarchy_level

        # Update ingredient
        ingredient.parent_ingredient_id = new_parent_id
        ingredient.hierarchy_level = new_level

        # Update children's levels recursively
        _update_descendant_levels(ingredient, level_diff, session)

        session.commit()
        return ingredient.to_dict()

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def _update_descendant_levels(ingredient: Ingredient, level_diff: int, session) -> None:
    """
    Recursively update hierarchy levels of all descendants.

    Helper function for move_ingredient.
    """
    children = (
        session.query(Ingredient).filter(Ingredient.parent_ingredient_id == ingredient.id).all()
    )
    for child in children:
        child.hierarchy_level += level_diff
        _update_descendant_levels(child, level_diff, session)


def search_ingredients(query: str, limit: Optional[int] = None, session=None) -> List[Dict]:
    """
    Search ingredients by display_name, returning matches with ancestry info.

    Args:
        query: Search string (case-insensitive partial match)
        limit: Optional maximum number of results to return
        session: Optional SQLAlchemy session

    Returns:
        List of matching ingredients with `ancestors` field populated
    """

    def _impl(session):
        db_query = (
            session.query(Ingredient)
            .filter(Ingredient.display_name.ilike(f"%{query}%"))
            .order_by(Ingredient.display_name)
        )
        if limit is not None:
            db_query = db_query.limit(limit)
        results = db_query.all()

        matches = []
        for ingredient in results:
            ingredient_dict = ingredient.to_dict()
            # Add ancestors for breadcrumb display
            ingredient_dict["ancestors"] = get_ancestors(ingredient.id, session=session)
            matches.append(ingredient_dict)

        return matches

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


# =============================================================================
# Feature 033: Convenience Functions for UI Validation
# =============================================================================


def get_child_count(ingredient_id: int, session=None) -> int:
    """
    Count direct child ingredients.

    Args:
        ingredient_id: ID of ingredient to count children for
        session: Optional SQLAlchemy session

    Returns:
        Number of direct child ingredients
    """

    def _impl(session):
        return (
            session.query(Ingredient)
            .filter(Ingredient.parent_ingredient_id == ingredient_id)
            .count()
        )

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def get_product_count(ingredient_id: int, session=None) -> int:
    """
    Count products linked to this ingredient.

    Args:
        ingredient_id: ID of ingredient to count products for
        session: Optional SQLAlchemy session

    Returns:
        Number of products linked to this ingredient
    """

    def _impl(session):
        return session.query(Product).filter(Product.ingredient_id == ingredient_id).count()

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def get_usage_counts(ingredient_id: int, session=None) -> Dict[str, int]:
    """
    Get product and recipe counts for an ingredient.

    Feature 052: Used in Hierarchy Admin UI to show usage information
    before performing rename/reparent/delete operations.

    Args:
        ingredient_id: ID of ingredient to check
        session: Optional SQLAlchemy session

    Returns:
        {"product_count": int, "recipe_count": int}
    """
    # RecipeIngredient lives in recipe.py (no separate recipe_ingredient module)
    from src.models.recipe import RecipeIngredient

    def _impl(session):
        product_count = (
            session.query(Product).filter(Product.ingredient_id == ingredient_id).count()
        )

        recipe_count = (
            session.query(RecipeIngredient)
            .filter(RecipeIngredient.ingredient_id == ingredient_id)
            .count()
        )

        return {
            "product_count": product_count,
            "recipe_count": recipe_count,
        }

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def get_aggregated_usage_counts(ingredient_id: int, session=None) -> Dict[str, int]:
    """
    Get aggregated product and recipe counts for an ingredient and all descendants.

    Feature 052: Used in Hierarchy Admin UI to show total usage for L0/L1 nodes.
    For L2 (leaf) ingredients, returns direct usage only.
    For L1 ingredients, sums usage of all L2 children.
    For L0 ingredients, sums usage of all L1 and L2 descendants.

    Args:
        ingredient_id: ID of ingredient to check
        session: Optional SQLAlchemy session

    Returns:
        {"product_count": int, "recipe_count": int, "descendant_count": int}
    """
    from src.models.recipe import RecipeIngredient

    def _impl(session):
        ingredient = session.query(Ingredient).filter(Ingredient.id == ingredient_id).first()

        if not ingredient:
            return {"product_count": 0, "recipe_count": 0, "descendant_count": 0}

        # Collect all ingredient IDs to count (self + descendants)
        ingredient_ids = [ingredient_id]

        if ingredient.hierarchy_level == 0:
            # L0: Get all L1 children and their L2 children
            l1_children = (
                session.query(Ingredient)
                .filter(Ingredient.parent_ingredient_id == ingredient_id)
                .all()
            )
            for l1 in l1_children:
                ingredient_ids.append(l1.id)
                l2_children = (
                    session.query(Ingredient).filter(Ingredient.parent_ingredient_id == l1.id).all()
                )
                ingredient_ids.extend([l2.id for l2 in l2_children])

        elif ingredient.hierarchy_level == 1:
            # L1: Get all L2 children
            l2_children = (
                session.query(Ingredient)
                .filter(Ingredient.parent_ingredient_id == ingredient_id)
                .all()
            )
            ingredient_ids.extend([l2.id for l2 in l2_children])

        # L2: Just count self (already in list)

        # Count products and recipes for all collected IDs
        product_count = (
            session.query(Product).filter(Product.ingredient_id.in_(ingredient_ids)).count()
        )

        from sqlalchemy import func

        recipe_count = (
            session.query(func.count(func.distinct(RecipeIngredient.recipe_id)))
            .filter(RecipeIngredient.ingredient_id.in_(ingredient_ids))
            .scalar()
        ) or 0

        return {
            "product_count": product_count,
            "recipe_count": recipe_count,
            "descendant_count": len(ingredient_ids) - 1,  # Exclude self
        }

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def can_change_parent(
    ingredient_id: int, new_parent_id: Optional[int], session=None
) -> Dict[str, Any]:
    """
    Check if parent change is allowed and gather impact information.

    This is a convenience wrapper around validate_hierarchy() that
    catches exceptions and returns a structured dict for UI display.
    Warnings are informational only (non-blocking per F033 design).

    Args:
        ingredient_id: ID of ingredient to change
        new_parent_id: Proposed new parent ID (None = make root)
        session: Optional SQLAlchemy session

    Returns:
        {
            "allowed": bool,
            "reason": str,  # Empty if allowed, error message if not
            "warnings": List[str],  # Informational warnings
            "child_count": int,
            "product_count": int,
            "new_level": int  # 0, 1, or 2
        }
    """

    def _impl(session):
        result: Dict[str, Any] = {
            "allowed": True,
            "reason": "",
            "warnings": [],
            "child_count": 0,
            "product_count": 0,
            "new_level": 0,
        }

        # Get counts
        result["child_count"] = get_child_count(ingredient_id, session=session)
        result["product_count"] = get_product_count(ingredient_id, session=session)

        # Compute new level
        if new_parent_id is None:
            result["new_level"] = 0
        else:
            parent = session.query(Ingredient).filter(Ingredient.id == new_parent_id).first()
            if parent:
                result["new_level"] = parent.hierarchy_level + 1

        # Try validation
        try:
            validate_hierarchy(ingredient_id, new_parent_id, session=session)
        except IngredientNotFound as e:
            result["allowed"] = False
            result["reason"] = str(e)
            return result
        except CircularReferenceError:
            result["allowed"] = False
            result["reason"] = "Cannot change: would create circular reference"
            return result
        except MaxDepthExceededError:
            result["allowed"] = False
            result["reason"] = "Cannot change: would exceed maximum hierarchy depth (3 levels)"
            return result

        # Add informational warnings (non-blocking)
        if result["product_count"] > 0:
            result["warnings"].append(
                f"This ingredient has {result['product_count']} linked product(s)"
            )
        if result["child_count"] > 0:
            result["warnings"].append(
                f"This ingredient has {result['child_count']} child ingredient(s)"
            )

        return result

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def add_leaf_ingredient(parent_id: int, name: str, session=None) -> Dict:
    """
    Create new L2 (leaf) ingredient under L1 parent.

    Feature 052: Admin operation to add new ingredient.

    Args:
        parent_id: ID of L1 parent ingredient
        name: Display name for new ingredient
        session: Optional SQLAlchemy session

    Returns:
        Dictionary representation of created Ingredient

    Raises:
        ValueError: If parent not found, parent not L1, name empty, or name not unique
    """
    from src.services import hierarchy_admin_service

    def _impl(session):
        # Validate name not empty
        if not hierarchy_admin_service.validate_name_not_empty(name):
            raise ValueError("Ingredient name cannot be empty")

        # Trim name
        trimmed_name = hierarchy_admin_service.trim_name(name)

        # Validate parent exists and is L1
        parent = session.query(Ingredient).filter(Ingredient.id == parent_id).first()

        if not parent:
            raise ValueError(f"Parent ingredient {parent_id} not found")

        if parent.hierarchy_level != 1:
            raise ValueError(f"Parent must be L1 (level 1), got level {parent.hierarchy_level}")

        # Get siblings for uniqueness check
        siblings = (
            session.query(Ingredient).filter(Ingredient.parent_ingredient_id == parent_id).all()
        )

        # Validate unique name
        if not hierarchy_admin_service.validate_unique_sibling_name(siblings, trimmed_name):
            raise ValueError(
                f"An ingredient named '{trimmed_name}' already exists under this parent"
            )

        # Generate slug
        slug = hierarchy_admin_service.generate_slug(trimmed_name)

        # Check slug uniqueness globally
        existing_slug = session.query(Ingredient).filter(Ingredient.slug == slug).first()
        if existing_slug:
            # Append parent slug for uniqueness
            slug = f"{parent.slug}-{slug}"

        # Create ingredient (inherit category from parent)
        ingredient = Ingredient(
            display_name=trimmed_name,
            slug=slug,
            parent_ingredient_id=parent_id,
            hierarchy_level=2,
            category=parent.category,
        )

        session.add(ingredient)
        session.flush()  # Get ID

        return ingredient.to_dict()

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        result = _impl(session)
        session.commit()
        return result


def rename_ingredient(ingredient_id: int, new_name: str, session=None) -> Dict:
    """
    Rename an ingredient (any level).

    Feature 052: Admin operation to rename ingredient.

    Args:
        ingredient_id: ID of ingredient to rename
        new_name: New display name
        session: Optional SQLAlchemy session

    Returns:
        Dictionary representation of updated Ingredient

    Raises:
        ValueError: If ingredient not found, name empty, or name not unique among siblings
    """
    from src.services import hierarchy_admin_service

    def _impl(session):
        # Find ingredient
        ingredient = session.query(Ingredient).filter(Ingredient.id == ingredient_id).first()

        if not ingredient:
            raise ValueError(f"Ingredient {ingredient_id} not found")

        # Validate name not empty
        if not hierarchy_admin_service.validate_name_not_empty(new_name):
            raise ValueError("Name cannot be empty")

        # Trim name
        new_name_stripped = hierarchy_admin_service.trim_name(new_name)

        # Get siblings for uniqueness check
        if ingredient.parent_ingredient_id:
            siblings = (
                session.query(Ingredient)
                .filter(Ingredient.parent_ingredient_id == ingredient.parent_ingredient_id)
                .all()
            )
        else:
            # Root level - siblings are other roots at same level
            siblings = (
                session.query(Ingredient)
                .filter(
                    Ingredient.parent_ingredient_id.is_(None),
                    Ingredient.hierarchy_level == ingredient.hierarchy_level,
                )
                .all()
            )

        # Validate unique name (excluding self)
        if not hierarchy_admin_service.validate_unique_sibling_name(
            siblings, new_name_stripped, exclude_id=ingredient_id
        ):
            raise ValueError(
                f"An ingredient named '{new_name_stripped}' already exists at this level"
            )

        # Update name
        ingredient.display_name = new_name_stripped

        # Regenerate slug
        new_slug = hierarchy_admin_service.generate_slug(new_name_stripped)

        # Check slug uniqueness globally (excluding self)
        existing_slug = (
            session.query(Ingredient)
            .filter(Ingredient.slug == new_slug, Ingredient.id != ingredient_id)
            .first()
        )

        if existing_slug:
            # Append parent or level info for uniqueness
            if ingredient.parent:
                new_slug = f"{ingredient.parent.slug}-{new_slug}"
            else:
                new_slug = f"l{ingredient.hierarchy_level}-{new_slug}"

        ingredient.slug = new_slug

        session.flush()
        return ingredient.to_dict()

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        result = _impl(session)
        session.commit()
        return result


def reparent_ingredient(ingredient_id: int, new_parent_id: int, session=None) -> Dict:
    """
    Move ingredient to new parent.

    Feature 052: Admin operation to move ingredient.

    Valid moves:
    - L2 can move to any L1
    - L1 can move to any L0

    Args:
        ingredient_id: ID of ingredient to move
        new_parent_id: ID of new parent ingredient
        session: Optional SQLAlchemy session

    Returns:
        Dictionary representation of updated Ingredient

    Raises:
        ValueError: If invalid move (wrong levels, cycle, duplicate name)
    """
    from src.services import hierarchy_admin_service

    def _impl(session):
        # Find ingredient
        ingredient = session.query(Ingredient).filter(Ingredient.id == ingredient_id).first()

        if not ingredient:
            raise ValueError(f"Ingredient {ingredient_id} not found")

        # Find new parent
        new_parent = session.query(Ingredient).filter(Ingredient.id == new_parent_id).first()

        if not new_parent:
            raise ValueError(f"New parent ingredient {new_parent_id} not found")

        # Validate level compatibility
        if ingredient.hierarchy_level == 2:
            # L2 must move to L1
            if new_parent.hierarchy_level != 1:
                raise ValueError("L2 ingredients can only move to L1 parents")
        elif ingredient.hierarchy_level == 1:
            # L1 must move to L0
            if new_parent.hierarchy_level != 0:
                raise ValueError("L1 ingredients can only move to L0 parents")
        else:
            # L0 cannot be moved
            raise ValueError("L0 (root) ingredients cannot be reparented")

        # Check if already under this parent
        if ingredient.parent_ingredient_id == new_parent_id:
            raise ValueError("Item is already under this parent")

        # Validate no cycle (for L1 moving to L0, check descendants)
        if ingredient.hierarchy_level == 1:
            descendants = ingredient.get_descendants()
            if not hierarchy_admin_service.validate_no_cycle(descendants, new_parent):
                raise ValueError("Cannot move: would create circular reference")

        # Validate unique name in new location
        siblings = (
            session.query(Ingredient).filter(Ingredient.parent_ingredient_id == new_parent_id).all()
        )

        if not hierarchy_admin_service.validate_unique_sibling_name(
            siblings, ingredient.display_name, exclude_id=ingredient_id
        ):
            raise ValueError(
                f"An ingredient named '{ingredient.display_name}' already exists under the new parent"
            )

        # Perform move
        ingredient.parent_ingredient_id = new_parent_id

        session.flush()
        return ingredient.to_dict()

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        result = _impl(session)
        session.commit()
        return result
