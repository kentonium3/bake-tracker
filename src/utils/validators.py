"""
Input validation functions for the Seasonal Baking Tracker application.

This module provides validation functions for all user inputs including:
- Numeric validation (positive, non-negative, ranges)
- String validation (length, format, required fields)
- Unit validation
- Category validation

All validation functions raise ValidationError on failure instead of returning
tuples. This is the standardized API pattern (F094).
"""

from typing import Optional, Set

from src.services.database import session_scope
from src.services.exceptions import ValidationError
from src.models.ingredient import Ingredient
from src.models.recipe import Recipe

from .constants import (
    ALL_UNITS,
    MAX_NAME_LENGTH,
    MAX_BRAND_LENGTH,
    MAX_CATEGORY_LENGTH,
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


def validate_required_string(value: Optional[str], field_name: str = "Field") -> None:
    """
    Validate that a string field is not empty.

    Args:
        value: The string value to validate
        field_name: Name of the field for error messages

    Raises:
        ValidationError: If value is None or empty string
    """
    if value is None or (isinstance(value, str) and value.strip() == ""):
        raise ValidationError([f"{field_name}: {ERROR_REQUIRED_FIELD}"])


def validate_string_length(
    value: str, max_length: int, field_name: str = "Field"
) -> None:
    """
    Validate that a string doesn't exceed maximum length.

    Args:
        value: The string value to validate
        max_length: Maximum allowed length
        field_name: Name of the field for error messages

    Raises:
        ValidationError: If value exceeds max_length
    """
    if value and len(value) > max_length:
        raise ValidationError([f"{field_name}: Must be {max_length} characters or less"])


def validate_positive_number(value: any, field_name: str = "Field") -> None:
    """
    Validate that a value is a positive number (> 0).

    Args:
        value: The value to validate
        field_name: Name of the field for error messages

    Raises:
        ValidationError: If value is not a positive number
    """
    try:
        num_value = float(value)
        if num_value <= 0:
            raise ValidationError([f"{field_name}: {ERROR_INVALID_POSITIVE}"])
    except (ValueError, TypeError):
        raise ValidationError([f"{field_name}: {ERROR_INVALID_NUMBER}"])


def validate_non_negative_number(value: any, field_name: str = "Field") -> None:
    """
    Validate that a value is a non-negative number (>= 0).

    Args:
        value: The value to validate
        field_name: Name of the field for error messages

    Raises:
        ValidationError: If value is not a non-negative number
    """
    try:
        num_value = float(value)
        if num_value < 0:
            raise ValidationError([f"{field_name}: {ERROR_INVALID_NON_NEGATIVE}"])
    except (ValueError, TypeError):
        raise ValidationError([f"{field_name}: {ERROR_INVALID_NUMBER}"])


def validate_number_range(
    value: any, min_value: float, max_value: float, field_name: str = "Field"
) -> None:
    """
    Validate that a number is within a specified range.

    Args:
        value: The value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        field_name: Name of the field for error messages

    Raises:
        ValidationError: If value is not within range
    """
    try:
        num_value = float(value)
        if num_value < min_value or num_value > max_value:
            raise ValidationError([f"{field_name}: Must be between {min_value} and {max_value}"])
    except (ValueError, TypeError):
        raise ValidationError([f"{field_name}: {ERROR_INVALID_NUMBER}"])


def validate_unit(unit: str, field_name: str = "Unit") -> None:
    """
    Validate that a unit is in the list of valid units.

    Args:
        unit: The unit string to validate
        field_name: Name of the field for error messages

    Raises:
        ValidationError: If unit is not valid
    """
    if not unit:
        raise ValidationError([f"{field_name}: {ERROR_REQUIRED_FIELD}"])

    if unit.lower() not in [u.lower() for u in ALL_UNITS]:
        raise ValidationError([f"{field_name}: {ERROR_INVALID_UNIT}"])


def _get_valid_ingredient_categories() -> Set[str]:
    """Get valid ingredient categories from database.

    Returns:
        Set of valid category names.
    """
    try:
        with session_scope() as session:
            categories = session.query(Ingredient.category).distinct().all()
            return {cat[0] for cat in categories if cat[0]}
    except Exception:
        return set()


def _get_valid_recipe_categories() -> Set[str]:
    """Get valid recipe categories from database.

    Returns:
        Set of valid category names.
    """
    try:
        with session_scope() as session:
            categories = session.query(Recipe.category).distinct().all()
            return {cat[0] for cat in categories if cat[0]}
    except Exception:
        return set()


def validate_ingredient_category(category: str, field_name: str = "Category") -> None:
    """
    Validate ingredient category.

    Categories are treated as **free-form** labels (not an enum and not a DB-backed
    allowlist). Validation enforces only:
    - required / non-empty after trimming
    - max length

    Args:
        category: The category string to validate
        field_name: Name of the field for error messages

    Raises:
        ValidationError: If category fails validation
    """
    category = sanitize_string(category)
    validate_required_string(category, field_name)
    validate_string_length(category, MAX_CATEGORY_LENGTH, field_name)


def validate_recipe_category(category: str, field_name: str = "Category") -> None:
    """
    Validate recipe category.

    Categories are treated as **free-form** labels (not an enum and not a DB-backed
    allowlist). Validation enforces only:
    - required / non-empty after trimming
    - max length

    Args:
        category: The category string to validate
        field_name: Name of the field for error messages

    Raises:
        ValidationError: If category fails validation
    """
    category = sanitize_string(category)
    validate_required_string(category, field_name)
    validate_string_length(category, MAX_CATEGORY_LENGTH, field_name)


def validate_ingredient_data(data: dict) -> None:  # noqa: C901
    """
    Validate all fields for an ingredient (NEW SCHEMA: generic ingredient definition).

    Args:
        data: Dictionary containing ingredient fields

    Raises:
        ValidationError: If any validation fails, with all errors collected
    """
    errors = []

    # Required: Display name
    display_name = data.get("display_name")
    try:
        validate_required_string(display_name, "Name")
        validate_string_length(display_name, MAX_NAME_LENGTH, "Name")
    except ValidationError as e:
        errors.extend(e.errors)

    # Required: Category
    try:
        validate_ingredient_category(data.get("category", ""), "Category")
    except ValidationError as e:
        errors.extend(e.errors)

    # Optional: Slug (will be auto-generated if not provided)
    if data.get("slug"):
        try:
            validate_string_length(data.get("slug"), MAX_NAME_LENGTH, "Slug")
        except ValidationError as e:
            errors.extend(e.errors)

    # Optional: Description
    if data.get("description"):
        try:
            validate_string_length(
                data.get("description"), MAX_NOTES_LENGTH * 2, "Description"
            )
        except ValidationError as e:
            errors.extend(e.errors)

    # Optional: 4-field density (all-or-nothing validation)
    # Note: Full density validation is done in ingredient_service.validate_density_fields()
    # Here we just do basic positive number checks if values are provided
    if data.get("density_volume_value") is not None:
        try:
            validate_positive_number(
                data.get("density_volume_value"), "Density volume value"
            )
        except ValidationError as e:
            errors.extend(e.errors)
    if data.get("density_weight_value") is not None:
        try:
            validate_positive_number(
                data.get("density_weight_value"), "Density weight value"
            )
        except ValidationError as e:
            errors.extend(e.errors)

    # Optional: Moisture percentage (must be 0-100 if provided)
    if data.get("moisture_pct") is not None:
        try:
            validate_number_range(data.get("moisture_pct"), 0, 100, "Moisture %")
        except ValidationError as e:
            errors.extend(e.errors)

    # Optional: Notes
    if data.get("notes"):
        try:
            validate_string_length(data.get("notes"), MAX_NOTES_LENGTH, "Notes")
        except ValidationError as e:
            errors.extend(e.errors)

    if errors:
        raise ValidationError(errors)


def validate_recipe_data(data: dict) -> None:  # noqa: C901
    """
    Validate all fields for a recipe.

    Args:
        data: Dictionary containing recipe fields

    Raises:
        ValidationError: If any validation fails, with all errors collected
    """
    errors = []

    # Required string fields
    try:
        validate_required_string(data.get("name"), "Recipe Name")
        validate_string_length(data.get("name"), MAX_NAME_LENGTH, "Recipe Name")
    except ValidationError as e:
        errors.extend(e.errors)

    # Category
    try:
        validate_recipe_category(data.get("category", ""), "Category")
    except ValidationError as e:
        errors.extend(e.errors)

    # F056: yield_quantity, yield_unit, yield_description are DEPRECATED
    # Yield data is now stored in FinishedUnit records (yield_types)
    # Validation of yield_types happens in the UI form before calling service layer

    # Optional fields with length limits
    if data.get("source"):
        try:
            validate_string_length(
                data.get("source"), MAX_DESCRIPTION_LENGTH, "Source"
            )
        except ValidationError as e:
            errors.extend(e.errors)

    if data.get("notes"):
        try:
            validate_string_length(data.get("notes"), MAX_NOTES_LENGTH, "Notes")
        except ValidationError as e:
            errors.extend(e.errors)

    # Estimated time (optional, must be non-negative if provided)
    if data.get("estimated_time_minutes") is not None:
        try:
            validate_non_negative_number(
                data.get("estimated_time_minutes"), "Estimated Time"
            )
        except ValidationError as e:
            errors.extend(e.errors)

    if errors:
        raise ValidationError(errors)


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


def validate_product_data(data: dict, ingredient_slug: str) -> None:
    """
    Validate all fields for a product (brand-specific version of ingredient).

    Args:
        data: Dictionary containing product fields
        ingredient_slug: Slug of parent ingredient (for context)

    Raises:
        ValidationError: If any validation fails, with all errors collected

    Required fields:
        - brand (str): Brand name
        - package_unit (str): Unit the package contains
        - package_unit_quantity (Decimal/float): Quantity in package (must be > 0)

    Optional fields:
        - package_size (str): Human-readable size description
        - upc (str): Universal Product Code (12-14 digits)
        - gtin (str): Global Trade Item Number
        - supplier (str): Where to buy
        - preferred (bool): Mark as preferred product
        - net_content_value (Decimal/float): Industry standard field
        - net_content_uom (str): Industry standard field
    """
    errors = []

    # Required: Brand
    try:
        validate_required_string(data.get("brand"), "Brand")
        validate_string_length(data.get("brand"), MAX_BRAND_LENGTH, "Brand")
    except ValidationError as e:
        errors.extend(e.errors)

    # Required: Package unit
    try:
        validate_unit(data.get("package_unit", ""), "Package Unit")
    except ValidationError as e:
        errors.extend(e.errors)

    # Required: Package quantity (must be positive)
    try:
        validate_positive_number(
            data.get("package_unit_quantity"), "Package Quantity"
        )
    except ValidationError as e:
        errors.extend(e.errors)

    # Optional: Package size
    if data.get("package_size"):
        try:
            validate_string_length(
                data.get("package_size"), MAX_DESCRIPTION_LENGTH, "Package Size"
            )
        except ValidationError as e:
            errors.extend(e.errors)

    # Optional: UPC (12-14 digit string if provided)
    if data.get("upc"):
        upc = str(data.get("upc")).strip()
        if not upc.isdigit():
            errors.append("UPC: Must contain only digits")
        elif len(upc) < 12 or len(upc) > 14:
            errors.append("UPC: Must be 12-14 digits")

    # Optional: Supplier
    if data.get("supplier"):
        try:
            validate_string_length(data.get("supplier"), MAX_NAME_LENGTH, "Supplier")
        except ValidationError as e:
            errors.extend(e.errors)

    # Optional: Net content value (must be positive if provided)
    if data.get("net_content_value") is not None:
        try:
            validate_positive_number(
                data.get("net_content_value"), "Net Content Value"
            )
        except ValidationError as e:
            errors.extend(e.errors)

    # Optional: Net content unit (must be valid unit if provided)
    if data.get("net_content_uom"):
        try:
            validate_unit(data.get("net_content_uom", ""), "Net Content UOM")
        except ValidationError as e:
            errors.extend(e.errors)

    if errors:
        raise ValidationError(errors)
