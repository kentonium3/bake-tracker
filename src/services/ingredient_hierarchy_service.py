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
from src.services.exceptions import IngredientNotFound


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
