"""
Material unit conversion system for the Seasonal Baking Tracker.

This module provides:
- Linear unit conversions (feet, inches, yards, meters, mm to cm)
- Area unit conversions (square_feet, square_inches, square_meters to square_cm)
- Unit compatibility validation

Conversion Strategy:
- Linear units convert through centimeters (base unit)
- Area units convert through square centimeters (base unit)
- "each" units are discrete counts (no conversion needed)
"""

from decimal import Decimal
from typing import Tuple, Optional


# ============================================================================
# Conversion Factor Dictionaries
# ============================================================================

# Linear conversions to centimeters (base unit)
LINEAR_TO_CM = {
    "feet": Decimal("30.48"),
    "inches": Decimal("2.54"),
    "yards": Decimal("91.44"),
    "meters": Decimal("100"),
    "mm": Decimal("0.1"),
    "cm": Decimal("1"),  # Base unit
}

# Area conversions to square centimeters (base unit)
AREA_TO_SQUARE_CM = {
    "square_feet": Decimal("929.0304"),
    "square_inches": Decimal("6.4516"),
    "square_meters": Decimal("10000"),
    "square_cm": Decimal("1"),  # Base unit
}

# Unit type mapping
UNIT_TYPES = {
    "linear_cm": set(LINEAR_TO_CM.keys()),
    "square_cm": set(AREA_TO_SQUARE_CM.keys()),
    "each": {"each"},
}


# ============================================================================
# Validation Functions
# ============================================================================


def validate_unit_compatibility(
    unit: str,
    base_unit_type: str,
) -> Tuple[bool, Optional[str]]:
    """
    Validate that a unit is compatible with a base unit type.

    Args:
        unit: Unit to validate (e.g., "feet", "square_inches")
        base_unit_type: Expected base type ("linear_cm", "square_cm", "each")

    Returns:
        Tuple of (is_valid, error_message)
    """
    if base_unit_type not in UNIT_TYPES:
        return False, f"Unknown base unit type: {base_unit_type}"

    valid_units = UNIT_TYPES[base_unit_type]
    if unit not in valid_units:
        return False, (
            f"Unit '{unit}' is not compatible with base type '{base_unit_type}'. "
            f"Valid units: {sorted(valid_units)}"
        )

    return True, None


def get_unit_type(unit: str) -> Optional[str]:
    """
    Determine the base unit type for a given unit.

    Args:
        unit: Unit string (e.g., "feet", "square_inches", "each")

    Returns:
        Base unit type ("linear_cm", "square_cm", "each") or None if unknown
    """
    for base_type, units in UNIT_TYPES.items():
        if unit in units:
            return base_type
    return None


# ============================================================================
# Conversion Functions
# ============================================================================


def convert_to_base_units(
    quantity: Decimal,
    from_unit: str,
    base_unit_type: str,
) -> Tuple[bool, Optional[Decimal], Optional[str]]:
    """
    Convert quantity from source unit to base units.

    Args:
        quantity: Amount to convert
        from_unit: Source unit (e.g., "feet", "square_inches")
        base_unit_type: Target base type ("linear_cm", "square_cm", "each")

    Returns:
        Tuple of (success, converted_value, error_message)
    """
    # Validate quantity
    if quantity < Decimal("0"):
        return False, None, "Quantity cannot be negative"

    # Handle "each" type - no conversion needed
    if base_unit_type == "each":
        if from_unit != "each":
            return False, None, (
                f"Unit '{from_unit}' is not compatible with base type 'each'. "
                f"Only 'each' is valid for discrete counts."
            )
        return True, quantity, None

    # Validate unit compatibility
    is_valid, error = validate_unit_compatibility(from_unit, base_unit_type)
    if not is_valid:
        return False, None, error

    # Get conversion factor
    if base_unit_type == "linear_cm":
        factor = LINEAR_TO_CM[from_unit]
    elif base_unit_type == "square_cm":
        factor = AREA_TO_SQUARE_CM[from_unit]
    else:
        return False, None, f"Unknown base unit type: {base_unit_type}"

    # Convert to base units
    converted = quantity * factor

    return True, converted, None


def convert_from_base_units(
    quantity: Decimal,
    to_unit: str,
    base_unit_type: str,
) -> Tuple[bool, Optional[Decimal], Optional[str]]:
    """
    Convert quantity from base units to target unit.

    Args:
        quantity: Amount in base units
        to_unit: Target unit (e.g., "feet", "square_inches")
        base_unit_type: Source base type ("linear_cm", "square_cm", "each")

    Returns:
        Tuple of (success, converted_value, error_message)
    """
    # Validate quantity
    if quantity < Decimal("0"):
        return False, None, "Quantity cannot be negative"

    # Handle "each" type - no conversion needed
    if base_unit_type == "each":
        if to_unit != "each":
            return False, None, (
                f"Unit '{to_unit}' is not compatible with base type 'each'. "
                f"Only 'each' is valid for discrete counts."
            )
        return True, quantity, None

    # Validate unit compatibility
    is_valid, error = validate_unit_compatibility(to_unit, base_unit_type)
    if not is_valid:
        return False, None, error

    # Get conversion factor
    if base_unit_type == "linear_cm":
        factor = LINEAR_TO_CM[to_unit]
    elif base_unit_type == "square_cm":
        factor = AREA_TO_SQUARE_CM[to_unit]
    else:
        return False, None, f"Unknown base unit type: {base_unit_type}"

    # Convert from base units (divide by factor)
    converted = quantity / factor

    return True, converted, None


def convert_units(
    quantity: Decimal,
    from_unit: str,
    to_unit: str,
) -> Tuple[bool, Optional[Decimal], Optional[str]]:
    """
    Convert quantity between compatible units.

    Args:
        quantity: Amount to convert
        from_unit: Source unit (e.g., "feet", "meters")
        to_unit: Target unit (e.g., "cm", "inches")

    Returns:
        Tuple of (success, converted_value, error_message)
    """
    # Validate quantity
    if quantity < Decimal("0"):
        return False, None, "Quantity cannot be negative"

    # Same unit - no conversion needed
    if from_unit == to_unit:
        return True, quantity, None

    # Determine unit types
    from_type = get_unit_type(from_unit)
    to_type = get_unit_type(to_unit)

    if from_type is None:
        return False, None, f"Unknown unit: {from_unit}"

    if to_type is None:
        return False, None, f"Unknown unit: {to_unit}"

    if from_type != to_type:
        return False, None, (
            f"Cannot convert between incompatible types: "
            f"'{from_unit}' ({from_type}) and '{to_unit}' ({to_type})"
        )

    # Convert through base units
    success, base_value, error = convert_to_base_units(quantity, from_unit, from_type)
    if not success:
        return False, None, error

    success, result, error = convert_from_base_units(base_value, to_unit, to_type)
    if not success:
        return False, None, error

    return True, result, None
