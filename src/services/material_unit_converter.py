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
from typing import Optional

from src.services.exceptions import ConversionError


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

# Feature 085: Display names for dropdown menus
LINEAR_UNIT_NAMES = {
    "cm": "Centimeters (cm)",
    "mm": "Millimeters (mm)",
    "inches": "Inches (in)",
    "feet": "Feet (ft)",
    "yards": "Yards (yd)",
    "meters": "Meters (m)",
}

AREA_UNIT_NAMES = {
    "square_cm": "Square Centimeters (sq cm)",
    "square_inches": "Square Inches (sq in)",
    "square_feet": "Square Feet (sq ft)",
    "square_meters": "Square Meters (sq m)",
}


# ============================================================================
# Validation Functions
# ============================================================================


def validate_unit_compatibility(
    unit: str,
    base_unit_type: str,
) -> None:
    """
    Validate that a unit is compatible with a base unit type.

    Args:
        unit: Unit to validate (e.g., "feet", "square_inches")
        base_unit_type: Expected base type ("linear_cm", "square_cm", "each")

    Raises:
        ConversionError: If the unit is not compatible with the base type
    """
    if base_unit_type not in UNIT_TYPES:
        raise ConversionError(
            f"Unknown base unit type: {base_unit_type}",
            from_unit=unit,
            to_unit=base_unit_type,
        )

    valid_units = UNIT_TYPES[base_unit_type]
    if unit not in valid_units:
        raise ConversionError(
            f"Unit '{unit}' is not compatible with base type '{base_unit_type}'. "
            f"Valid units: {sorted(valid_units)}",
            from_unit=unit,
            to_unit=base_unit_type,
        )


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
) -> Decimal:
    """
    Convert quantity from source unit to base units.

    Args:
        quantity: Amount to convert
        from_unit: Source unit (e.g., "feet", "square_inches")
        base_unit_type: Target base type ("linear_cm", "square_cm", "each")

    Returns:
        Converted value in base units

    Raises:
        ConversionError: If conversion fails
    """
    # Validate quantity
    if quantity < Decimal("0"):
        raise ConversionError(
            "Quantity cannot be negative",
            from_unit=from_unit,
            to_unit=base_unit_type,
            value=float(quantity),
        )

    # Handle "each" type - no conversion needed
    if base_unit_type == "each":
        if from_unit != "each":
            raise ConversionError(
                f"Unit '{from_unit}' is not compatible with base type 'each'. "
                f"Only 'each' is valid for discrete counts.",
                from_unit=from_unit,
                to_unit=base_unit_type,
                value=float(quantity),
            )
        return quantity

    # Validate unit compatibility (raises ConversionError on failure)
    validate_unit_compatibility(from_unit, base_unit_type)

    # Get conversion factor
    if base_unit_type == "linear_cm":
        factor = LINEAR_TO_CM[from_unit]
    elif base_unit_type == "square_cm":
        factor = AREA_TO_SQUARE_CM[from_unit]
    else:
        raise ConversionError(
            f"Unknown base unit type: {base_unit_type}",
            from_unit=from_unit,
            to_unit=base_unit_type,
            value=float(quantity),
        )

    # Convert to base units
    return quantity * factor


def convert_from_base_units(
    quantity: Decimal,
    to_unit: str,
    base_unit_type: str,
) -> Decimal:
    """
    Convert quantity from base units to target unit.

    Args:
        quantity: Amount in base units
        to_unit: Target unit (e.g., "feet", "square_inches")
        base_unit_type: Source base type ("linear_cm", "square_cm", "each")

    Returns:
        Converted value in target unit

    Raises:
        ConversionError: If conversion fails
    """
    # Validate quantity
    if quantity < Decimal("0"):
        raise ConversionError(
            "Quantity cannot be negative",
            from_unit=base_unit_type,
            to_unit=to_unit,
            value=float(quantity),
        )

    # Handle "each" type - no conversion needed
    if base_unit_type == "each":
        if to_unit != "each":
            raise ConversionError(
                f"Unit '{to_unit}' is not compatible with base type 'each'. "
                f"Only 'each' is valid for discrete counts.",
                from_unit=base_unit_type,
                to_unit=to_unit,
                value=float(quantity),
            )
        return quantity

    # Validate unit compatibility (raises ConversionError on failure)
    validate_unit_compatibility(to_unit, base_unit_type)

    # Get conversion factor
    if base_unit_type == "linear_cm":
        factor = LINEAR_TO_CM[to_unit]
    elif base_unit_type == "square_cm":
        factor = AREA_TO_SQUARE_CM[to_unit]
    else:
        raise ConversionError(
            f"Unknown base unit type: {base_unit_type}",
            from_unit=base_unit_type,
            to_unit=to_unit,
            value=float(quantity),
        )

    # Convert from base units (divide by factor)
    return quantity / factor


def convert_units(
    quantity: Decimal,
    from_unit: str,
    to_unit: str,
) -> Decimal:
    """
    Convert quantity between compatible units.

    Args:
        quantity: Amount to convert
        from_unit: Source unit (e.g., "feet", "meters")
        to_unit: Target unit (e.g., "cm", "inches")

    Returns:
        Converted value in target unit

    Raises:
        ConversionError: If conversion fails
    """
    # Validate quantity
    if quantity < Decimal("0"):
        raise ConversionError(
            "Quantity cannot be negative",
            from_unit=from_unit,
            to_unit=to_unit,
            value=float(quantity),
        )

    # Same unit - no conversion needed
    if from_unit == to_unit:
        return quantity

    # Determine unit types
    from_type = get_unit_type(from_unit)
    to_type = get_unit_type(to_unit)

    if from_type is None:
        raise ConversionError(
            f"Unknown unit: {from_unit}",
            from_unit=from_unit,
            to_unit=to_unit,
            value=float(quantity),
        )

    if to_type is None:
        raise ConversionError(
            f"Unknown unit: {to_unit}",
            from_unit=from_unit,
            to_unit=to_unit,
            value=float(quantity),
        )

    if from_type != to_type:
        raise ConversionError(
            f"Cannot convert between incompatible types: "
            f"'{from_unit}' ({from_type}) and '{to_unit}' ({to_type})",
            from_unit=from_unit,
            to_unit=to_unit,
            value=float(quantity),
        )

    # Convert through base units (both functions now raise on error)
    base_value = convert_to_base_units(quantity, from_unit, from_type)
    return convert_from_base_units(base_value, to_unit, to_type)


# ============================================================================
# Feature 085: Dropdown Helpers
# ============================================================================


def get_linear_unit_options() -> list[tuple[str, str]]:
    """
    Return list of (code, display_name) tuples for linear unit dropdown.

    Feature 085: Provides options for MaterialUnit dialog dropdown.

    Returns:
        List of tuples like [('cm', 'Centimeters (cm)'), ('inches', 'Inches (in)'), ...]
        Ordered by: cm first (default), then alphabetically by code
    """
    options = []
    # cm first as it's the base unit
    options.append(("cm", LINEAR_UNIT_NAMES["cm"]))
    # Add others alphabetically
    for code in sorted(LINEAR_TO_CM.keys()):
        if code != "cm":
            options.append((code, LINEAR_UNIT_NAMES[code]))
    return options


def get_area_unit_options() -> list[tuple[str, str]]:
    """
    Return list of (code, display_name) tuples for area unit dropdown.

    Feature 085: Provides options for MaterialUnit dialog dropdown (area products).

    Returns:
        List of tuples like [('square_cm', 'Square Centimeters (sq cm)'), ...]
        Ordered by: square_cm first (default), then alphabetically by code
    """
    options = []
    # square_cm first as it's the base unit
    options.append(("square_cm", AREA_UNIT_NAMES["square_cm"]))
    # Add others alphabetically
    for code in sorted(AREA_TO_SQUARE_CM.keys()):
        if code != "square_cm":
            options.append((code, AREA_UNIT_NAMES[code]))
    return options


def convert_to_cm(value: float, from_unit: str) -> float:
    """
    Convert a linear measurement to centimeters.

    Feature 085: Simple wrapper for UI usage.

    Args:
        value: The quantity to convert
        from_unit: The source unit code ('cm', 'inches', 'feet', 'yards', 'meters', 'mm')

    Returns:
        The equivalent value in centimeters

    Raises:
        ValueError: If from_unit is not a valid linear unit code
        ValueError: If value is negative

    Examples:
        >>> convert_to_cm(8, 'inches')
        20.32
        >>> convert_to_cm(1, 'yards')
        91.44
    """
    if value < 0:
        raise ValueError(f"Value must be non-negative, got {value}")

    from_unit_lower = from_unit.lower()
    if from_unit_lower not in LINEAR_TO_CM:
        raise ValueError(
            f"Unknown unit '{from_unit}'. Valid units: {list(LINEAR_TO_CM.keys())}"
        )

    return float(Decimal(str(value)) * LINEAR_TO_CM[from_unit_lower])


def convert_from_cm(value: float, to_unit: str) -> float:
    """
    Convert centimeters to another linear unit (for display).

    Feature 085: Simple wrapper for UI usage.

    Args:
        value: The value in centimeters
        to_unit: The target unit code

    Returns:
        The equivalent value in the target unit

    Raises:
        ValueError: If to_unit is not a valid linear unit code
    """
    to_unit_lower = to_unit.lower()
    if to_unit_lower not in LINEAR_TO_CM:
        raise ValueError(
            f"Unknown unit '{to_unit}'. Valid units: {list(LINEAR_TO_CM.keys())}"
        )

    return float(Decimal(str(value)) / LINEAR_TO_CM[to_unit_lower])
