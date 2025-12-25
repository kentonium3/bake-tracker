"""
Category-to-unit default mapping for smart pre-filling.

This module provides default package units based on ingredient categories,
enabling smart pre-fill in inline product creation. Users can always override
these defaults - they are just sensible starting values to reduce data entry.

Usage:
    from src.utils.category_defaults import get_default_unit_for_category

    # Get default for a category:
    unit = get_default_unit_for_category('Baking')  # Returns 'lb'

    # Or for an ingredient:
    unit = get_default_unit_for_ingredient(ingredient)
"""

from typing import Dict


# Category-to-unit mapping based on typical baking supply package sizes
# Key: Category name (must match INGREDIENT_CATEGORIES from constants.py exactly)
# Value: Default package unit string
CATEGORY_DEFAULT_UNITS: Dict[str, str] = {
    # Food ingredient categories
    "Flour": "lb",  # Flour - sold by weight in bulk
    "Sugar": "lb",  # Sugar - sold by weight
    "Dairy": "lb",  # Butter, cheese - by weight
    "Oils/Butters": "fl oz",  # Oils, melted butters by volume
    "Nuts": "lb",  # Sold by weight
    "Spices": "oz",  # Small quantities
    "Chocolate/Candies": "oz",  # Chips, bars - smaller quantities
    "Cocoa Powders": "oz",  # Small quantities by weight
    "Dried Fruits": "lb",  # By weight
    "Extracts": "fl oz",  # By volume
    "Syrups": "fl oz",  # By volume
    "Alcohol": "fl oz",  # By volume
    "Misc": "lb",  # Default for miscellaneous
    # Packaging categories (less common, default to count)
    "Bags": "count",
    "Boxes": "count",
    "Ribbon": "count",
    "Labels": "count",
    "Tissue Paper": "count",
    "Wrapping": "count",
    "Other Packaging": "count",
}


def get_default_unit_for_category(category: str) -> str:
    """
    Get default package unit for an ingredient category.

    Returns a sensible default package unit based on the ingredient category.
    If the category is not recognized, returns 'lb' as a safe fallback
    since most baking ingredients are sold by weight.

    Args:
        category: Ingredient category name (must match database values)

    Returns:
        Default unit string (e.g., 'lb', 'oz', 'fl oz').
        Returns 'lb' as fallback if category not found.
    """
    return CATEGORY_DEFAULT_UNITS.get(category, "lb")


def get_default_unit_for_ingredient(ingredient) -> str:
    """
    Get default package unit for a specific ingredient.

    Convenience wrapper that extracts the category from an ingredient
    model instance and returns the default unit.

    Args:
        ingredient: Ingredient model instance with .category attribute

    Returns:
        Default unit string for the ingredient's category
    """
    return get_default_unit_for_category(ingredient.category)
