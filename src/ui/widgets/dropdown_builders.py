"""
Dropdown builder functions with recency intelligence.

This module provides functions to build dropdown values for
Category/Ingredient/Product selections with:
- Recent items starred and shown first
- Separator lines between sections
- Create-new option for products

Usage:
    from src.ui.widgets.dropdown_builders import (
        build_product_dropdown_values,
        build_ingredient_dropdown_values,
        SEPARATOR,
        CREATE_NEW_OPTION,
    )

    # Build product dropdown for an ingredient
    values = build_product_dropdown_values(ingredient_id, session)

    # Build ingredient dropdown for a category
    values = build_ingredient_dropdown_values(category, session)
"""

from typing import List

from sqlalchemy.orm import Session

from src.models import Ingredient, Product
from src.services.inventory_item_service import (
    get_recent_ingredients,
    get_recent_products,
)


# Unicode separator line for visual grouping
SEPARATOR = "─────────────────────────────"

# Option to create new product inline
CREATE_NEW_OPTION = "[+ Create New Product]"

# Star prefix for recent items
STAR_PREFIX = "⭐ "


def build_product_dropdown_values(
    ingredient_id: int,
    session: Session,
) -> List[str]:
    """
    Build product dropdown values with recency markers and sorting.

    Args:
        ingredient_id: Ingredient to filter products for
        session: Database session

    Returns:
        List of dropdown values in display order:
        1. Recent products (starred)
        2. Separator (if both recent and non-recent exist)
        3. Non-recent products (alphabetical)
        4. Separator
        5. Create new option
    """
    # Get all products for ingredient (non-hidden)
    products = (
        session.query(Product)
        .filter_by(ingredient_id=ingredient_id, is_hidden=False)
        .order_by(Product.brand)
        .all()
    )

    if not products:
        return [CREATE_NEW_OPTION]

    # Get recent product IDs
    recent_ids = set(get_recent_products(ingredient_id, session=session))

    # Separate recent vs non-recent
    recent_products = []
    other_products = []

    for product in products:
        if product.id in recent_ids:
            recent_products.append(f"{STAR_PREFIX}{product.display_name}")
        else:
            other_products.append(product.display_name)

    # Build final list
    values = []

    if recent_products:
        values.extend(recent_products)
        if other_products:
            values.append(SEPARATOR)

    values.extend(other_products)

    if values:
        values.append(SEPARATOR)

    values.append(CREATE_NEW_OPTION)

    return values


def build_ingredient_dropdown_values(
    category: str,
    session: Session,
) -> List[str]:
    """
    Build ingredient dropdown values with recency sorting.

    Args:
        category: Category to filter ingredients for
        session: Database session

    Returns:
        List of dropdown values in display order:
        1. Recent ingredients (starred)
        2. Separator (if both recent and non-recent exist)
        3. Non-recent ingredients (alphabetical)
    """
    # Get all ingredients in category
    ingredients = (
        session.query(Ingredient)
        .filter_by(category=category)
        .order_by(Ingredient.display_name)
        .all()
    )

    if not ingredients:
        return []

    # Get recent ingredient IDs
    recent_ids = set(get_recent_ingredients(category, session=session))

    # Separate recent vs non-recent
    recent_ingredients = []
    other_ingredients = []

    for ingredient in ingredients:
        if ingredient.id in recent_ids:
            recent_ingredients.append(f"{STAR_PREFIX}{ingredient.display_name}")
        else:
            other_ingredients.append(ingredient.display_name)

    # Build final list
    values = []

    if recent_ingredients:
        values.extend(recent_ingredients)
        if other_ingredients:
            values.append(SEPARATOR)

    values.extend(other_ingredients)

    return values


def strip_star_prefix(value: str) -> str:
    """
    Remove star prefix from a dropdown value.

    Used by dialogs to get the actual product/ingredient name.

    Args:
        value: Dropdown value that may have star prefix

    Returns:
        Value with star prefix removed
    """
    if value.startswith(STAR_PREFIX):
        return value[len(STAR_PREFIX) :]
    return value


def is_separator(value: str) -> bool:
    """
    Check if a dropdown value is a separator.

    Used by dialogs to ignore separator selections.

    Args:
        value: Dropdown value to check

    Returns:
        True if value is the separator line
    """
    return value == SEPARATOR


def is_create_new_option(value: str) -> bool:
    """
    Check if a dropdown value is the create-new option.

    Used by dialogs to trigger inline creation flow.

    Args:
        value: Dropdown value to check

    Returns:
        True if value is the create-new option
    """
    return value == CREATE_NEW_OPTION
