"""
Ingredient hierarchy service for tree traversal and navigation.

This service provides tree traversal and hierarchy management operations
for the ingredient taxonomy. All hierarchy-related business logic is
encapsulated here, keeping the UI layer thin.

Feature 031: Ingredient Hierarchy Taxonomy
"""

from typing import List, Dict, Optional

from src.models.ingredient import Ingredient
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


def get_all_descendants(ancestor_id: int, session=None) -> List[Dict]:
    """
    Get all descendants (recursive) of an ingredient.

    Args:
        ancestor_id: ID of ancestor ingredient
        session: Optional SQLAlchemy session

    Returns:
        List of all descendant ingredients (all levels below ancestor)

    Raises:
        IngredientNotFound: If ancestor_id doesn't exist
    """
    def _impl(session):
        ancestor = session.query(Ingredient).filter(Ingredient.id == ancestor_id).first()
        if ancestor is None:
            raise IngredientNotFound(ancestor_id)

        descendants = []
        _collect_descendants(ancestor, descendants, session)
        return descendants

    if session is not None:
        return _impl(session)
    with session_scope() as session:
        return _impl(session)


def _collect_descendants(ingredient: Ingredient, descendants: List[Dict], session) -> None:
    """
    Recursively collect all descendants of an ingredient.

    Helper function for get_all_descendants.
    """
    # Get direct children
    children = (
        session.query(Ingredient)
        .filter(Ingredient.parent_ingredient_id == ingredient.id)
        .all()
    )
    for child in children:
        descendants.append(child.to_dict())
        _collect_descendants(child, descendants, session)


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
            descendants = get_all_descendants(parent_id, session=session)
            leaves = [d for d in descendants if d.get("hierarchy_level") == 2]
            # Sort by display_name
            return sorted(leaves, key=lambda x: x.get("display_name", ""))

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


def validate_hierarchy_level(
    ingredient_id: int, allowed_levels: List[int], session=None
) -> bool:
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

        allowed_str = ", ".join(str(l) for l in allowed_levels)
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


def move_ingredient(
    ingredient_id: int, new_parent_id: Optional[int], session=None
) -> Dict:
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
            session.query(Ingredient)
            .filter(Ingredient.parent_ingredient_id == ingredient_id)
            .all()
        )
        for child in children:
            child_new_level = new_level + (child.hierarchy_level - ingredient.hierarchy_level)
            if child_new_level > 2:
                raise MaxDepthExceededError(
                    child.id, child_new_level
                )

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
        session.query(Ingredient)
        .filter(Ingredient.parent_ingredient_id == ingredient.id)
        .all()
    )
    for child in children:
        child.hierarchy_level += level_diff
        _update_descendant_levels(child, level_diff, session)


def search_ingredients(query: str, session=None) -> List[Dict]:
    """
    Search ingredients by display_name, returning matches with ancestry info.

    Args:
        query: Search string (case-insensitive partial match)
        session: Optional SQLAlchemy session

    Returns:
        List of matching ingredients with `ancestors` field populated
    """
    def _impl(session):
        results = (
            session.query(Ingredient)
            .filter(Ingredient.display_name.ilike(f"%{query}%"))
            .order_by(Ingredient.display_name)
            .all()
        )

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
