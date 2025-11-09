"""
Input validation functions for the Seasonal Baking Tracker application.

This module provides validation functions for all user inputs including:
- Numeric validation (positive, non-negative, ranges)
- String validation (length, format, required fields)
- Unit validation
- Category validation
"""

from typing import Optional, Tuple

from .constants import (
    ALL_UNITS,
    INGREDIENT_CATEGORIES,
    RECIPE_CATEGORIES,
    MAX_NAME_LENGTH,
    MAX_BRAND_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    MAX_NOTES_LENGTH,
    MIN_QUANTITY,
    MAX_QUANTITY,
    MIN_COST,
    MAX_COST,
    MIN_CONVERSION_FACTOR,
    MAX_CONVERSION_FACTOR,
    ERROR_REQUIRED_FIELD,
    ERROR_INVALID_NUMBER,
    ERROR_INVALID_POSITIVE,
    ERROR_INVALID_NON_NEGATIVE,
    ERROR_INVALID_UNIT,
    ERROR_INVALID_CATEGORY,
)


class ValidationError(Exception):
    """Exception raised for validation errors."""

    pass


def validate_required_string(value: Optional[str], field_name: str = "Field") -> Tuple[bool, str]:
    """
    Validate that a string field is not empty.

    Args:
        value: The string value to validate
        field_name: Name of the field for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return False, f"{field_name}: {ERROR_REQUIRED_FIELD}"
    return True, ""


def validate_string_length(
    value: str, max_length: int, field_name: str = "Field"
) -> Tuple[bool, str]:
    """
    Validate that a string doesn't exceed maximum length.

    Args:
        value: The string value to validate
        max_length: Maximum allowed length
        field_name: Name of the field for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    if value and len(value) > max_length:
        return False, f"{field_name}: Must be {max_length} characters or less"
    return True, ""


def validate_positive_number(value: any, field_name: str = "Field") -> Tuple[bool, str]:
    """
    Validate that a value is a positive number (> 0).

    Args:
        value: The value to validate
        field_name: Name of the field for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        num_value = float(value)
        if num_value <= 0:
            return False, f"{field_name}: {ERROR_INVALID_POSITIVE}"
        return True, ""
    except (ValueError, TypeError):
        return False, f"{field_name}: {ERROR_INVALID_NUMBER}"


def validate_non_negative_number(value: any, field_name: str = "Field") -> Tuple[bool, str]:
    """
    Validate that a value is a non-negative number (>= 0).

    Args:
        value: The value to validate
        field_name: Name of the field for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        num_value = float(value)
        if num_value < 0:
            return False, f"{field_name}: {ERROR_INVALID_NON_NEGATIVE}"
        return True, ""
    except (ValueError, TypeError):
        return False, f"{field_name}: {ERROR_INVALID_NUMBER}"


def validate_number_range(
    value: any, min_value: float, max_value: float, field_name: str = "Field"
) -> Tuple[bool, str]:
    """
    Validate that a number is within a specified range.

    Args:
        value: The value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        field_name: Name of the field for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        num_value = float(value)
        if num_value < min_value or num_value > max_value:
            return False, f"{field_name}: Must be between {min_value} and {max_value}"
        return True, ""
    except (ValueError, TypeError):
        return False, f"{field_name}: {ERROR_INVALID_NUMBER}"


def validate_unit(unit: str, field_name: str = "Unit") -> Tuple[bool, str]:
    """
    Validate that a unit is in the list of valid units.

    Args:
        unit: The unit string to validate
        field_name: Name of the field for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not unit:
        return False, f"{field_name}: {ERROR_REQUIRED_FIELD}"

    if unit.lower() not in [u.lower() for u in ALL_UNITS]:
        return False, f"{field_name}: {ERROR_INVALID_UNIT}"

    return True, ""


def validate_ingredient_category(category: str, field_name: str = "Category") -> Tuple[bool, str]:
    """
    Validate that a category is in the list of valid ingredient categories.

    Args:
        category: The category string to validate
        field_name: Name of the field for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not category:
        return False, f"{field_name}: {ERROR_REQUIRED_FIELD}"

    if category not in INGREDIENT_CATEGORIES:
        return False, f"{field_name}: {ERROR_INVALID_CATEGORY}"

    return True, ""


def validate_recipe_category(category: str, field_name: str = "Category") -> Tuple[bool, str]:
    """
    Validate that a category is in the list of valid recipe categories.

    Args:
        category: The category string to validate
        field_name: Name of the field for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not category:
        return False, f"{field_name}: {ERROR_REQUIRED_FIELD}"

    if category not in RECIPE_CATEGORIES:
        return False, f"{field_name}: {ERROR_INVALID_CATEGORY}"

    return True, ""


def validate_ingredient_data(data: dict) -> Tuple[bool, list]:  # noqa: C901
    """
    Validate all fields for an ingredient (NEW SCHEMA: generic ingredient definition).

    Args:
        data: Dictionary containing ingredient fields

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Required: Name
    is_valid, error = validate_required_string(data.get("name"), "Name")
    if not is_valid:
        errors.append(error)
    else:
        is_valid, error = validate_string_length(data.get("name"), MAX_NAME_LENGTH, "Name")
        if not is_valid:
            errors.append(error)

    # Required: Category
    is_valid, error = validate_ingredient_category(data.get("category", ""), "Category")
    if not is_valid:
        errors.append(error)

    # Required: Recipe unit
    is_valid, error = validate_unit(data.get("recipe_unit", ""), "Recipe Unit")
    if not is_valid:
        errors.append(error)

    # Optional: Slug (will be auto-generated if not provided)
    if data.get("slug"):
        is_valid, error = validate_string_length(data.get("slug"), MAX_NAME_LENGTH, "Slug")
        if not is_valid:
            errors.append(error)

    # Optional: Description
    if data.get("description"):
        is_valid, error = validate_string_length(data.get("description"), MAX_NOTES_LENGTH * 2, "Description")
        if not is_valid:
            errors.append(error)

    # Optional: Density (must be positive if provided)
    if data.get("density_g_per_ml") is not None:
        is_valid, error = validate_positive_number(data.get("density_g_per_ml"), "Density (g/mL)")
        if not is_valid:
            errors.append(error)

    # Optional: Moisture percentage (must be 0-100 if provided)
    if data.get("moisture_pct") is not None:
        is_valid, error = validate_number_range(data.get("moisture_pct"), 0, 100, "Moisture %")
        if not is_valid:
            errors.append(error)

    # Optional: Notes
    if data.get("notes"):
        is_valid, error = validate_string_length(data.get("notes"), MAX_NOTES_LENGTH, "Notes")
        if not is_valid:
            errors.append(error)

    return len(errors) == 0, errors


def validate_recipe_data(data: dict) -> Tuple[bool, list]:  # noqa: C901
    """
    Validate all fields for a recipe.

    Args:
        data: Dictionary containing recipe fields

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Required string fields
    is_valid, error = validate_required_string(data.get("name"), "Recipe Name")
    if not is_valid:
        errors.append(error)
    else:
        is_valid, error = validate_string_length(data.get("name"), MAX_NAME_LENGTH, "Recipe Name")
        if not is_valid:
            errors.append(error)

    # Category
    is_valid, error = validate_recipe_category(data.get("category", ""), "Category")
    if not is_valid:
        errors.append(error)

    # Yield quantity (must be positive)
    is_valid, error = validate_positive_number(data.get("yield_quantity"), "Yield Quantity")
    if not is_valid:
        errors.append(error)

    # Yield unit
    is_valid, error = validate_required_string(data.get("yield_unit"), "Yield Unit")
    if not is_valid:
        errors.append(error)

    # Optional fields with length limits
    if data.get("source"):
        is_valid, error = validate_string_length(
            data.get("source"), MAX_DESCRIPTION_LENGTH, "Source"
        )
        if not is_valid:
            errors.append(error)

    if data.get("yield_description"):
        is_valid, error = validate_string_length(
            data.get("yield_description"), MAX_DESCRIPTION_LENGTH, "Yield Description"
        )
        if not is_valid:
            errors.append(error)

    if data.get("notes"):
        is_valid, error = validate_string_length(data.get("notes"), MAX_NOTES_LENGTH, "Notes")
        if not is_valid:
            errors.append(error)

    # Estimated time (optional, must be non-negative if provided)
    if data.get("estimated_time_minutes") is not None:
        is_valid, error = validate_non_negative_number(
            data.get("estimated_time_minutes"), "Estimated Time"
        )
        if not is_valid:
            errors.append(error)

    return len(errors) == 0, errors


def sanitize_string(value: Optional[str]) -> Optional[str]:
    """
    Sanitize a string value by stripping whitespace and converting empty strings to None.

    Args:
        value: The string value to sanitize

    Returns:
        Sanitized string or None
    """
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def parse_decimal(value: any, default: float = 0.0) -> float:
    """
    Safely parse a value to a float.

    Args:
        value: The value to parse
        default: Default value if parsing fails

    Returns:
        Parsed float value or default
    """
    if value is None:
        return default

    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def parse_int(value: any, default: int = 0) -> int:
    """
    Safely parse a value to an integer.

    Args:
        value: The value to parse
        default: Default value if parsing fails

    Returns:
        Parsed integer value or default
    """
    if value is None:
        return default

    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def validate_variant_data(data: dict, ingredient_slug: str) -> Tuple[bool, list]:
    """
    Validate all fields for a variant (brand-specific product).

    Args:
        data: Dictionary containing variant fields
        ingredient_slug: Slug of parent ingredient (for context)

    Returns:
        Tuple of (is_valid, list_of_errors)

    Required fields:
        - brand (str): Brand name
        - purchase_unit (str): Unit purchased in
        - purchase_quantity (Decimal/float): Quantity in package (must be > 0)

    Optional fields:
        - package_size (str): Human-readable size description
        - upc (str): Universal Product Code (12-14 digits)
        - gtin (str): Global Trade Item Number
        - supplier (str): Where to buy
        - preferred (bool): Mark as preferred variant
        - net_content_value (Decimal/float): Industry standard field
        - net_content_uom (str): Industry standard field
    """
    errors = []

    # Required: Brand
    is_valid, error = validate_required_string(data.get("brand"), "Brand")
    if not is_valid:
        errors.append(error)
    else:
        is_valid, error = validate_string_length(data.get("brand"), MAX_BRAND_LENGTH, "Brand")
        if not is_valid:
            errors.append(error)

    # Required: Purchase unit
    is_valid, error = validate_unit(data.get("purchase_unit", ""), "Purchase Unit")
    if not is_valid:
        errors.append(error)

    # Required: Purchase quantity (must be positive)
    is_valid, error = validate_positive_number(data.get("purchase_quantity"), "Purchase Quantity")
    if not is_valid:
        errors.append(error)

    # Optional: Package size
    if data.get("package_size"):
        is_valid, error = validate_string_length(
            data.get("package_size"), MAX_DESCRIPTION_LENGTH, "Package Size"
        )
        if not is_valid:
            errors.append(error)

    # Optional: UPC (12-14 digit string if provided)
    if data.get("upc"):
        upc = str(data.get("upc")).strip()
        if not upc.isdigit():
            errors.append("UPC: Must contain only digits")
        elif len(upc) < 12 or len(upc) > 14:
            errors.append("UPC: Must be 12-14 digits")

    # Optional: Supplier
    if data.get("supplier"):
        is_valid, error = validate_string_length(
            data.get("supplier"), MAX_NAME_LENGTH, "Supplier"
        )
        if not is_valid:
            errors.append(error)

    # Optional: Net content value (must be positive if provided)
    if data.get("net_content_value") is not None:
        is_valid, error = validate_positive_number(
            data.get("net_content_value"), "Net Content Value"
        )
        if not is_valid:
            errors.append(error)

    # Optional: Net content unit (must be valid unit if provided)
    if data.get("net_content_uom"):
        is_valid, error = validate_unit(data.get("net_content_uom", ""), "Net Content UOM")
        if not is_valid:
            errors.append(error)

    return len(errors) == 0, errors
