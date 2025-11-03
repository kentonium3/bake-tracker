"""
Unit conversion system for the Seasonal Baking Tracker.

This module provides:
- Standard unit conversions (weight, volume)
- Ingredient-specific unit conversions using conversion factors
- Cost calculation utilities
- Conversion display helpers

Conversion Strategy:
- Weight units convert through grams (base unit)
- Volume units convert through milliliters (base unit)
- Ingredient custom units use stored conversion_factor
"""

from typing import Optional, Tuple


# ============================================================================
# Standard Conversion Tables
# ============================================================================

# Weight conversions to grams (base unit)
WEIGHT_TO_GRAMS = {
    "g": 1.0,
    "kg": 1000.0,
    "oz": 28.3495,
    "lb": 453.592,
}

# Volume conversions to milliliters (base unit)
VOLUME_TO_ML = {
    "ml": 1.0,
    "l": 1000.0,
    "tsp": 4.92892,
    "tbsp": 14.7868,
    "fl oz": 29.5735,
    "cup": 236.588,
    "pt": 473.176,
    "qt": 946.353,
    "gal": 3785.41,
}

# Count conversions to individual items (base unit)
COUNT_TO_ITEMS = {
    "each": 1.0,
    "count": 1.0,
    "piece": 1.0,
    "dozen": 12.0,
}


# ============================================================================
# Unit Type Detection
# ============================================================================


def get_conversion_table(unit: str) -> Optional[dict]:
    """
    Get the appropriate conversion table for a unit.

    Args:
        unit: Unit string (e.g., "oz", "cup", "dozen")

    Returns:
        Conversion table dict, or None if unit not found
    """
    unit_lower = unit.lower()

    if unit_lower in WEIGHT_TO_GRAMS:
        return WEIGHT_TO_GRAMS
    elif unit_lower in VOLUME_TO_ML:
        return VOLUME_TO_ML
    elif unit_lower in COUNT_TO_ITEMS:
        return COUNT_TO_ITEMS

    return None


def get_unit_type(unit: str) -> str:
    """
    Determine the type of a unit.

    Args:
        unit: Unit string

    Returns:
        Unit type: "weight", "volume", "count", or "unknown"
    """
    unit_lower = unit.lower()

    if unit_lower in WEIGHT_TO_GRAMS:
        return "weight"
    elif unit_lower in VOLUME_TO_ML:
        return "volume"
    elif unit_lower in COUNT_TO_ITEMS:
        return "count"

    return "unknown"


def units_compatible(unit1: str, unit2: str) -> bool:
    """
    Check if two units are of the same type and can be converted.

    Args:
        unit1: First unit
        unit2: Second unit

    Returns:
        True if units are compatible for conversion
    """
    type1 = get_unit_type(unit1)
    type2 = get_unit_type(unit2)

    if type1 == "unknown" or type2 == "unknown":
        return False

    return type1 == type2


# ============================================================================
# Standard Unit Conversions
# ============================================================================


def convert_standard_units(value: float, from_unit: str, to_unit: str) -> Tuple[bool, float, str]:
    """
    Convert between standard units of the same type.

    Args:
        value: Quantity to convert
        from_unit: Source unit (e.g., "lb")
        to_unit: Target unit (e.g., "oz")

    Returns:
        Tuple of (success, converted_value, error_message)
        - success: True if conversion successful
        - converted_value: Result (0.0 if failed)
        - error_message: Error description (empty string if successful)
    """
    # Validate inputs
    if value < 0:
        return False, 0.0, "Value cannot be negative"

    from_unit_lower = from_unit.lower()
    to_unit_lower = to_unit.lower()

    # Check if units are the same
    if from_unit_lower == to_unit_lower:
        return True, value, ""

    # Get conversion table
    conversion_table = get_conversion_table(from_unit_lower)
    if not conversion_table:
        return False, 0.0, f"Unknown unit: {from_unit}"

    # Check if target unit is in same table
    if to_unit_lower not in conversion_table:
        return (
            False,
            0.0,
            f"Cannot convert {from_unit} to {to_unit}: incompatible unit types",
        )

    # Convert: value -> base unit -> target unit
    base_value = value * conversion_table[from_unit_lower]
    converted_value = base_value / conversion_table[to_unit_lower]

    return True, converted_value, ""


def format_conversion(value: float, from_unit: str, to_unit: str, precision: int = 2) -> str:
    """
    Format a unit conversion for display.

    Args:
        value: Source quantity
        from_unit: Source unit
        to_unit: Target unit
        precision: Decimal places for result

    Returns:
        Formatted string (e.g., "1 lb = 16.00 oz")
        Returns error message if conversion fails
    """
    success, converted, error = convert_standard_units(value, from_unit, to_unit)

    if not success:
        return f"Error: {error}"

    return f"{value:g} {from_unit} = {converted:.{precision}f} {to_unit}"


# ============================================================================
# Ingredient Unit Conversions
# ============================================================================


def convert_to_purchase_units(recipe_quantity: float, conversion_factor: float) -> float:
    """
    Convert from recipe units to purchase units.

    Args:
        recipe_quantity: Quantity in recipe units
        conversion_factor: Ingredient's conversion factor (purchase to recipe)

    Returns:
        Quantity in purchase units
    """
    if conversion_factor == 0:
        return 0.0

    return recipe_quantity / conversion_factor


def convert_to_recipe_units(purchase_quantity: float, conversion_factor: float) -> float:
    """
    Convert from purchase units to recipe units.

    Args:
        purchase_quantity: Quantity in purchase units
        conversion_factor: Ingredient's conversion factor (purchase to recipe)

    Returns:
        Quantity in recipe units
    """
    return purchase_quantity * conversion_factor


def format_ingredient_conversion(
    conversion_factor: float,
    purchase_unit: str,
    recipe_unit: str,
    precision: int = 2,
) -> str:
    """
    Format an ingredient's conversion factor for display.

    Args:
        conversion_factor: Conversion factor value
        purchase_unit: Purchase unit name
        recipe_unit: Recipe unit name
        precision: Decimal places

    Returns:
        Formatted string (e.g., "1 bag = 200.00 cups")
    """
    return f"1 {purchase_unit} = {conversion_factor:.{precision}f} {recipe_unit}"


# ============================================================================
# Cost Calculation Utilities
# ============================================================================


def calculate_ingredient_cost(
    unit_cost: float, conversion_factor: float, recipe_quantity: float
) -> Tuple[bool, float, str]:
    """
    Calculate the cost of an ingredient used in a recipe.

    Formula: cost = (unit_cost / conversion_factor) × recipe_quantity

    Args:
        unit_cost: Cost per purchase unit
        conversion_factor: Purchase to recipe conversion factor
        recipe_quantity: Quantity needed in recipe units

    Returns:
        Tuple of (success, cost, error_message)
    """
    # Validate inputs
    if unit_cost < 0:
        return False, 0.0, "Unit cost cannot be negative"

    if conversion_factor <= 0:
        return False, 0.0, "Conversion factor must be positive"

    if recipe_quantity < 0:
        return False, 0.0, "Recipe quantity cannot be negative"

    # Calculate cost per recipe unit
    cost_per_recipe_unit = unit_cost / conversion_factor

    # Calculate total cost
    total_cost = cost_per_recipe_unit * recipe_quantity

    return True, total_cost, ""


def calculate_cost_per_recipe_unit(
    unit_cost: float, conversion_factor: float
) -> Tuple[bool, float, str]:
    """
    Calculate the cost per recipe unit for an ingredient.

    Args:
        unit_cost: Cost per purchase unit
        conversion_factor: Purchase to recipe conversion factor

    Returns:
        Tuple of (success, cost_per_recipe_unit, error_message)
    """
    if unit_cost < 0:
        return False, 0.0, "Unit cost cannot be negative"

    if conversion_factor <= 0:
        return False, 0.0, "Conversion factor must be positive"

    cost_per_recipe_unit = unit_cost / conversion_factor

    return True, cost_per_recipe_unit, ""


def calculate_cost_per_yield_unit(
    total_recipe_cost: float, yield_quantity: float
) -> Tuple[bool, float, str]:
    """
    Calculate the cost per yield unit for a recipe.

    Args:
        total_recipe_cost: Total cost of all ingredients
        yield_quantity: Number of yield units produced

    Returns:
        Tuple of (success, cost_per_unit, error_message)
    """
    if total_recipe_cost < 0:
        return False, 0.0, "Total cost cannot be negative"

    if yield_quantity <= 0:
        return False, 0.0, "Yield quantity must be positive"

    cost_per_unit = total_recipe_cost / yield_quantity

    return True, cost_per_unit, ""


def format_cost(amount: float, currency_symbol: str = "$", precision: int = 2) -> str:
    """
    Format a cost value for display.

    Args:
        amount: Cost amount
        currency_symbol: Currency symbol to use
        precision: Decimal places

    Returns:
        Formatted currency string (e.g., "$12.50")
    """
    return f"{currency_symbol}{amount:.{precision}f}"


# ============================================================================
# Validation Helpers
# ============================================================================


def validate_conversion_factor(conversion_factor: float) -> Tuple[bool, str]:
    """
    Validate a conversion factor value.

    Args:
        conversion_factor: Value to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if conversion_factor <= 0:
        return False, "Conversion factor must be positive"

    if conversion_factor > 1e6:
        return False, "Conversion factor is unreasonably large"

    return True, ""


def validate_quantity(quantity: float, allow_zero: bool = True) -> Tuple[bool, str]:
    """
    Validate a quantity value.

    Args:
        quantity: Value to validate
        allow_zero: Whether to allow zero values

    Returns:
        Tuple of (is_valid, error_message)
    """
    if quantity < 0:
        return False, "Quantity cannot be negative"

    if not allow_zero and quantity == 0:
        return False, "Quantity cannot be zero"

    if quantity > 1e9:
        return False, "Quantity is unreasonably large"

    return True, ""
