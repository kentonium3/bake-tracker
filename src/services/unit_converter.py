"""
Unit conversion system for the Seasonal Baking Tracker.

This module provides:
- Standard unit conversions (weight, volume, count)
- Density-based cross-type conversions (volume↔weight)
- Cost calculation utilities
- Conversion display helpers

Conversion Strategy:
- Weight units convert through grams (base unit)
- Volume units convert through milliliters (base unit)
- Volume↔weight conversions use ingredient density (4-field model)
"""

from typing import Optional, TYPE_CHECKING

from .exceptions import ConversionError, ValidationError

if TYPE_CHECKING:
    from src.models.ingredient import Ingredient


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


def convert_standard_units(value: float, from_unit: str, to_unit: str) -> float:
    """
    Convert between standard units of the same type.

    Args:
        value: Quantity to convert
        from_unit: Source unit (e.g., "lb")
        to_unit: Target unit (e.g., "oz")

    Returns:
        Converted value

    Raises:
        ConversionError: If conversion is not possible
    """
    # Validate inputs
    if value < 0:
        raise ConversionError(
            "Value cannot be negative", from_unit=from_unit, to_unit=to_unit, value=value
        )

    from_unit_lower = from_unit.lower()
    to_unit_lower = to_unit.lower()

    # Check if units are the same
    if from_unit_lower == to_unit_lower:
        return value

    # Get conversion table
    conversion_table = get_conversion_table(from_unit_lower)
    if not conversion_table:
        raise ConversionError(
            f"Unknown unit: {from_unit}", from_unit=from_unit, to_unit=to_unit, value=value
        )

    # Check if target unit is in same table
    if to_unit_lower not in conversion_table:
        raise ConversionError(
            f"Cannot convert {from_unit} to {to_unit}: incompatible unit types",
            from_unit=from_unit,
            to_unit=to_unit,
            value=value,
        )

    # Convert: value -> base unit -> target unit
    base_value = value * conversion_table[from_unit_lower]
    converted_value = base_value / conversion_table[to_unit_lower]

    return converted_value


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
    try:
        converted = convert_standard_units(value, from_unit, to_unit)
        return f"{value:g} {from_unit} = {converted:.{precision}f} {to_unit}"
    except ConversionError as e:
        return f"Error: {e}"


# ============================================================================
# Volume-to-Weight Conversions
# ============================================================================


def convert_volume_to_weight(
    volume_value: float,
    volume_unit: str,
    weight_unit: str,
    ingredient: "Ingredient" = None,
    density_g_per_ml: float = None,
) -> float:
    """
    Convert a volume measurement to weight using ingredient density.

    Args:
        volume_value: Quantity in volume units
        volume_unit: Volume unit (e.g., "cup", "tbsp", "ml")
        weight_unit: Target weight unit (e.g., "g", "oz", "lb")
        ingredient: Ingredient object (for density lookup from 4-field model)
        density_g_per_ml: Direct density value (g/ml) to use instead of lookup

    Returns:
        Weight value in the target unit

    Raises:
        ConversionError: If conversion fails (missing density, invalid units)
    """
    # Get density from ingredient or override
    density = density_g_per_ml
    if density is None and ingredient is not None:
        density = ingredient.get_density_g_per_ml()

    if density is None or density <= 0:
        ingredient_name = ingredient.display_name if ingredient else "unknown"
        raise ConversionError(
            f"Density required for conversion. Edit ingredient '{ingredient_name}' to set density.",
            from_unit=volume_unit,
            to_unit=weight_unit,
            value=volume_value,
        )

    # Convert volume to ml (raises ConversionError on failure)
    ml = convert_standard_units(volume_value, volume_unit, "ml")

    # Calculate weight in grams using density (g/ml)
    grams = ml * density

    # Convert to target weight unit (raises ConversionError on failure)
    weight = convert_standard_units(grams, "g", weight_unit)

    return weight


def convert_weight_to_volume(
    weight_value: float,
    weight_unit: str,
    volume_unit: str,
    ingredient: "Ingredient" = None,
    density_g_per_ml: float = None,
) -> float:
    """
    Convert a weight measurement to volume using ingredient density.

    Args:
        weight_value: Quantity in weight units
        weight_unit: Weight unit (e.g., "g", "oz", "lb")
        volume_unit: Target volume unit (e.g., "cup", "tbsp", "ml")
        ingredient: Ingredient object (for density lookup from 4-field model)
        density_g_per_ml: Direct density value (g/ml) to use instead of lookup

    Returns:
        Volume value in the target unit

    Raises:
        ConversionError: If conversion fails (missing density, invalid units)
    """
    # Get density from ingredient or override
    density = density_g_per_ml
    if density is None and ingredient is not None:
        density = ingredient.get_density_g_per_ml()

    if density is None or density <= 0:
        ingredient_name = ingredient.display_name if ingredient else "unknown"
        raise ConversionError(
            f"Density required for conversion. Edit ingredient '{ingredient_name}' to set density.",
            from_unit=weight_unit,
            to_unit=volume_unit,
            value=weight_value,
        )

    # Convert weight to grams (raises ConversionError on failure)
    grams = convert_standard_units(weight_value, weight_unit, "g")

    # Calculate volume in ml using density (g/ml)
    ml = grams / density

    # Convert to target volume unit (raises ConversionError on failure)
    volume = convert_standard_units(ml, "ml", volume_unit)

    return volume


def convert_any_units(
    value: float,
    from_unit: str,
    to_unit: str,
    ingredient: "Ingredient" = None,
    density_g_per_ml: Optional[float] = None,
) -> float:
    """
    Convert between any units, including cross-type conversions (volume↔weight).

    This function intelligently handles:
    - Same-type conversions (weight→weight, volume→volume)
    - Cross-type conversions (volume→weight, weight→volume) using ingredient density

    Args:
        value: Quantity to convert
        from_unit: Source unit
        to_unit: Target unit
        ingredient: Ingredient object (for density lookup from 4-field model)
        density_g_per_ml: Direct density value (g/ml) to use instead of lookup

    Returns:
        Converted value

    Raises:
        ConversionError: If conversion fails
    """
    from_type = get_unit_type(from_unit)
    to_type = get_unit_type(to_unit)

    # Same type conversion - use standard conversion
    if from_type == to_type:
        return convert_standard_units(value, from_unit, to_unit)

    # Volume to weight conversion
    if from_type == "volume" and to_type == "weight":
        if ingredient is None and density_g_per_ml is None:
            raise ConversionError(
                "Ingredient or density required for volume-to-weight conversion",
                from_unit=from_unit,
                to_unit=to_unit,
                value=value,
            )
        return convert_volume_to_weight(value, from_unit, to_unit, ingredient, density_g_per_ml)

    # Weight to volume conversion
    if from_type == "weight" and to_type == "volume":
        if ingredient is None and density_g_per_ml is None:
            raise ConversionError(
                "Ingredient or density required for weight-to-volume conversion",
                from_unit=from_unit,
                to_unit=to_unit,
                value=value,
            )
        return convert_weight_to_volume(value, from_unit, to_unit, ingredient, density_g_per_ml)

    # Incompatible conversion
    raise ConversionError(
        f"Cannot convert between {from_type} and {to_type} (incompatible unit types)",
        from_unit=from_unit,
        to_unit=to_unit,
        value=value,
    )


# ============================================================================
# Cost Calculation Utilities
# ============================================================================


def calculate_cost_per_yield_unit(
    total_recipe_cost: float, yield_quantity: float
) -> float:
    """
    Calculate the cost per yield unit for a recipe.

    Args:
        total_recipe_cost: Total cost of all ingredients
        yield_quantity: Number of yield units produced
                       (F056: Get from FinishedUnit.items_per_batch, not Recipe)

    Returns:
        Cost per yield unit

    Raises:
        ValidationError: If inputs are invalid
    """
    if total_recipe_cost < 0:
        raise ValidationError(["Total cost cannot be negative"])

    if yield_quantity <= 0:
        raise ValidationError(["Yield quantity must be positive"])

    cost_per_unit = total_recipe_cost / yield_quantity

    return cost_per_unit


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


def validate_quantity(quantity: float, allow_zero: bool = True) -> None:
    """
    Validate a quantity value.

    Args:
        quantity: Value to validate
        allow_zero: Whether to allow zero values

    Raises:
        ValidationError: If quantity is invalid
    """
    if quantity < 0:
        raise ValidationError(["Quantity cannot be negative"])

    if not allow_zero and quantity == 0:
        raise ValidationError(["Quantity cannot be zero"])

    if quantity > 1e9:
        raise ValidationError(["Quantity is unreasonably large"])
