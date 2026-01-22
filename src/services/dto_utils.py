"""DTO utilities for service layer.

Provides standardized formatting functions for data transfer objects,
ensuring consistent JSON serialization and API contracts.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Union


def cost_to_string(value: Union[Decimal, float, int, str, None]) -> str:
    """
    Convert a cost value to a 2-decimal string format.

    This is the standard format for cost values in service DTOs,
    ensuring JSON serialization safety and consistent formatting.

    Args:
        value: Cost value (Decimal, float, int, str, or None)

    Returns:
        String formatted as "12.34" (2 decimal places).
        Returns "0.00" if value is None.

    Examples:
        >>> cost_to_string(Decimal("12.345"))
        '12.35'
        >>> cost_to_string(12.3)
        '12.30'
        >>> cost_to_string(None)
        '0.00'
        >>> cost_to_string("15.999")
        '16.00'
    """
    if value is None:
        return "0.00"

    # Convert to Decimal for precise rounding
    decimal_value = Decimal(str(value))

    # Round to 2 decimal places using standard rounding
    rounded = decimal_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return str(rounded)
