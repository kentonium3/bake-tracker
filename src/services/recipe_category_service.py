"""
Recipe Category Service - CRUD operations for recipe categories.

This service provides CRUD operations for the flat recipe category system.
Part of Feature 096: Recipe Category Management.

Session Management Pattern:
- All functions accept optional `session` parameter
- If session is provided, use it directly (allows callers to manage transactions)
- If session is None, create a new session_scope for the operation
"""

import re
from typing import List, Optional

from sqlalchemy.orm import Session

from src.models.recipe_category import RecipeCategory
from src.services.database import session_scope
from src.services.exceptions import (
    RecipeCategoryNotFoundById,
    RecipeCategoryNotFoundByName,
    ValidationError,
)


# ============================================================================
# Utility Functions
# ============================================================================


def _slugify(name: str) -> str:
    """
    Convert a name to a URL-friendly slug.

    Args:
        name: Display name to convert

    Returns:
        Lowercase slug with hyphens (e.g., "Layer Cakes" -> "layer-cakes")
    """
    slug = name.lower()
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug


def _generate_unique_slug(
    base_slug: str,
    session: Session,
    exclude_id: Optional[int] = None,
) -> str:
    """
    Generate a unique slug by appending a number suffix if needed.

    Args:
        base_slug: The base slug to make unique
        session: Database session
        exclude_id: ID to exclude from uniqueness check (for updates)

    Returns:
        Unique slug (e.g., "cakes" or "cakes-2")
    """
    slug = base_slug
    counter = 1

    while True:
        query = session.query(RecipeCategory).filter(RecipeCategory.slug == slug)
        if exclude_id is not None:
            query = query.filter(RecipeCategory.id != exclude_id)

        if query.first() is None:
            return slug

        counter += 1
        slug = f"{base_slug}-{counter}"


# ============================================================================
# CRUD Operations
# ============================================================================


def list_categories(session: Optional[Session] = None) -> List[RecipeCategory]:
    """
    List all recipe categories ordered by sort_order, then name.

    Args:
        session: Optional database session

    Returns:
        List of RecipeCategory objects
    """

    def _impl(sess: Session) -> List[RecipeCategory]:
        return (
            sess.query(RecipeCategory)
            .order_by(RecipeCategory.sort_order, RecipeCategory.name)
            .all()
        )

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


def create_category(
    name: str,
    slug: Optional[str] = None,
    sort_order: int = 0,
    description: Optional[str] = None,
    session: Optional[Session] = None,
) -> RecipeCategory:
    """
    Create a new recipe category.

    Args:
        name: Category display name (e.g., "Cakes")
        slug: URL-friendly identifier (auto-generated if not provided)
        sort_order: Display ordering (default 0)
        description: Optional description
        session: Optional database session

    Returns:
        Created RecipeCategory instance

    Raises:
        ValidationError: If name is empty or duplicate
    """
    if not name or not name.strip():
        raise ValidationError(["Category name cannot be empty"])

    def _impl(sess: Session) -> RecipeCategory:
        # Check for duplicate name
        existing = (
            sess.query(RecipeCategory)
            .filter(RecipeCategory.name == name.strip())
            .first()
        )
        if existing:
            raise ValidationError(
                [f"Category with name '{name.strip()}' already exists"]
            )

        base_slug = slug or _slugify(name)
        unique_slug = _generate_unique_slug(base_slug, sess)

        category = RecipeCategory(
            name=name.strip(),
            slug=unique_slug,
            sort_order=sort_order,
            description=description,
        )
        sess.add(category)
        sess.flush()
        sess.refresh(category)
        return category

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


def get_category_by_id(
    category_id: int,
    session: Optional[Session] = None,
) -> RecipeCategory:
    """
    Get a recipe category by ID.

    Args:
        category_id: Category ID
        session: Optional database session

    Returns:
        RecipeCategory instance

    Raises:
        RecipeCategoryNotFoundById: If category doesn't exist
    """

    def _impl(sess: Session) -> RecipeCategory:
        category = (
            sess.query(RecipeCategory)
            .filter(RecipeCategory.id == category_id)
            .first()
        )
        if category is None:
            raise RecipeCategoryNotFoundById(category_id)
        return category

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


def get_category_by_name(
    name: str,
    session: Optional[Session] = None,
) -> RecipeCategory:
    """
    Get a recipe category by name.

    Args:
        name: Category name
        session: Optional database session

    Returns:
        RecipeCategory instance

    Raises:
        RecipeCategoryNotFoundByName: If category doesn't exist
    """

    def _impl(sess: Session) -> RecipeCategory:
        category = (
            sess.query(RecipeCategory)
            .filter(RecipeCategory.name == name)
            .first()
        )
        if category is None:
            raise RecipeCategoryNotFoundByName(name)
        return category

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


def update_category(
    category_id: int,
    name: Optional[str] = None,
    sort_order: Optional[int] = None,
    description: Optional[str] = None,
    session: Optional[Session] = None,
) -> RecipeCategory:
    """
    Update a recipe category's fields.

    Args:
        category_id: Category ID to update
        name: New name (optional)
        sort_order: New sort order (optional)
        description: New description (optional)
        session: Optional database session

    Returns:
        Updated RecipeCategory instance

    Raises:
        RecipeCategoryNotFoundById: If category doesn't exist
        ValidationError: If name is empty or duplicate
    """

    def _impl(sess: Session) -> RecipeCategory:
        category = (
            sess.query(RecipeCategory)
            .filter(RecipeCategory.id == category_id)
            .first()
        )
        if category is None:
            raise RecipeCategoryNotFoundById(category_id)

        if name is not None:
            if not name.strip():
                raise ValidationError(["Category name cannot be empty"])
            # Check for duplicate name (excluding current category)
            existing = (
                sess.query(RecipeCategory)
                .filter(
                    RecipeCategory.name == name.strip(),
                    RecipeCategory.id != category_id,
                )
                .first()
            )
            if existing:
                raise ValidationError(
                    [f"Category with name '{name.strip()}' already exists"]
                )
            category.name = name.strip()

        if description is not None:
            category.description = description

        if sort_order is not None:
            category.sort_order = sort_order

        sess.flush()
        sess.refresh(category)
        return category

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


def is_category_in_use(
    category_id: int,
    session: Optional[Session] = None,
) -> bool:
    """
    Check if a recipe category is in use by any recipes.

    Args:
        category_id: Category ID to check
        session: Optional database session

    Returns:
        True if any recipes use this category name

    Raises:
        RecipeCategoryNotFoundById: If category doesn't exist
    """

    def _impl(sess: Session) -> bool:
        category = (
            sess.query(RecipeCategory)
            .filter(RecipeCategory.id == category_id)
            .first()
        )
        if category is None:
            raise RecipeCategoryNotFoundById(category_id)

        # Lazy import to avoid circular dependency
        from src.models.recipe import Recipe

        count = (
            sess.query(Recipe)
            .filter(Recipe.category == category.name)
            .count()
        )
        return count > 0

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)


def delete_category(
    category_id: int,
    session: Optional[Session] = None,
) -> None:
    """
    Delete a recipe category.

    Args:
        category_id: Category ID to delete
        session: Optional database session

    Raises:
        RecipeCategoryNotFoundById: If category doesn't exist
        ValidationError: If category is in use by recipes
    """

    def _impl(sess: Session) -> None:
        category = (
            sess.query(RecipeCategory)
            .filter(RecipeCategory.id == category_id)
            .first()
        )
        if category is None:
            raise RecipeCategoryNotFoundById(category_id)

        # Lazy import to avoid circular dependency
        from src.models.recipe import Recipe

        recipe_count = (
            sess.query(Recipe)
            .filter(Recipe.category == category.name)
            .count()
        )
        if recipe_count > 0:
            raise ValidationError(
                [
                    f"Cannot delete category '{category.name}': "
                    f"used by {recipe_count} recipe(s)"
                ]
            )

        sess.delete(category)

    if session is not None:
        return _impl(session)

    with session_scope() as sess:
        return _impl(sess)
