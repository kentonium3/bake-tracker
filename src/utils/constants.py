"""
Constants and enumerations for the Seasonal Baking Tracker application.

This module defines all system-wide constants including:
- Unit types (weight, volume, count)
- Ingredient and recipe categories
- UI constants (colors, sizes)
- Application metadata
"""

from typing import List, Dict

# ============================================================================
# Application Metadata
# ============================================================================

APP_NAME = "Seasonal Baking Tracker"
APP_VERSION = "0.1.0"
APP_AUTHOR = "Kent Gale"
DATABASE_VERSION = "1.0"

# ============================================================================
# Unit Types
# ============================================================================

# Weight units
WEIGHT_UNITS: List[str] = [
    "oz",  # Ounce
    "lb",  # Pound
    "g",  # Gram
    "kg",  # Kilogram
]

# Volume units
VOLUME_UNITS: List[str] = [
    "tsp",  # Teaspoon
    "tbsp",  # Tablespoon
    "cup",  # Cup
    "ml",  # Milliliter
    "l",  # Liter
    "fl oz",  # Fluid ounce
    "pt",  # Pint
    "qt",  # Quart
    "gal",  # Gallon
]

# Count/discrete units
COUNT_UNITS: List[str] = [
    "each",  # Individual items
    "count",  # Count
    "piece",  # Piece
    "dozen",  # Dozen
]

# Custom/packaging units (for purchase units)
PACKAGE_UNITS: List[str] = [
    "bag",
    "box",
    "container",
    "jar",
    "bottle",
    "can",
    "package",
    "case",
]

# All valid units combined
ALL_UNITS: List[str] = WEIGHT_UNITS + VOLUME_UNITS + COUNT_UNITS + PACKAGE_UNITS

# Unit type mappings for validation
UNIT_TYPE_MAP: Dict[str, str] = {
    # Weight
    "oz": "weight",
    "lb": "weight",
    "g": "weight",
    "kg": "weight",
    # Volume
    "tsp": "volume",
    "tbsp": "volume",
    "cup": "volume",
    "ml": "volume",
    "l": "volume",
    "fl oz": "volume",
    "pt": "volume",
    "qt": "volume",
    "gal": "volume",
    # Count
    "each": "count",
    "count": "count",
    "piece": "count",
    "dozen": "count",
    # Package (custom units - type determined by ingredient)
    "bag": "package",
    "box": "package",
    "container": "package",
    "jar": "package",
    "bottle": "package",
    "can": "package",
    "package": "package",
    "case": "package",
}

# ============================================================================
# Ingredient Categories
# ============================================================================

INGREDIENT_CATEGORIES: List[str] = [
    "Flour/Grains",
    "Sugar/Sweeteners",
    "Dairy",
    "Eggs",
    "Chocolate/Cocoa",
    "Nuts/Seeds",
    "Spices/Extracts",
    "Fats/Oils",
    "Leavening",
    "Dried Fruit",
    "Fresh Fruit",
    "Decorations",
    "Other",
]

# ============================================================================
# Recipe Categories
# ============================================================================

RECIPE_CATEGORIES: List[str] = [
    "Cookies",
    "Cakes",
    "Bars",
    "Brownies",
    "Candies",
    "Breads",
    "Pastries",
    "Pies",
    "Tarts",
    "Fudge",
    "Other",
]

# ============================================================================
# Event Status
# ============================================================================

EVENT_STATUS_PLANNING = "planning"
EVENT_STATUS_IN_PROGRESS = "in-progress"
EVENT_STATUS_COMPLETED = "completed"

EVENT_STATUSES: List[str] = [
    EVENT_STATUS_PLANNING,
    EVENT_STATUS_IN_PROGRESS,
    EVENT_STATUS_COMPLETED,
]

# ============================================================================
# UI Constants
# ============================================================================

# Window sizing
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 800
MIN_WINDOW_WIDTH = 1000
MIN_WINDOW_HEIGHT = 600

# Colors (CustomTkinter theme compatible)
COLOR_SUCCESS = "#4CAF50"
COLOR_WARNING = "#FF9800"
COLOR_ERROR = "#F44336"
COLOR_INFO = "#2196F3"

# Table column widths (relative)
TABLE_COLUMN_WIDTHS = {
    "ingredient": {
        "name": 200,
        "brand": 150,
        "category": 120,
        "quantity": 100,
        "unit_cost": 100,
        "total_value": 120,
    },
    "recipe": {
        "name": 250,
        "category": 120,
        "yield": 150,
        "cost": 100,
        "time": 100,
    },
}

# Form field widths
FORM_FIELD_WIDTH_SMALL = 100
FORM_FIELD_WIDTH_MEDIUM = 200
FORM_FIELD_WIDTH_LARGE = 400
FORM_FIELD_WIDTH_FULL = 600

# Padding
PADDING_SMALL = 5
PADDING_MEDIUM = 10
PADDING_LARGE = 20

# ============================================================================
# Validation Constants
# ============================================================================

# String length limits
MAX_NAME_LENGTH = 200
MAX_BRAND_LENGTH = 200
MAX_CATEGORY_LENGTH = 100
MAX_UNIT_LENGTH = 50
MAX_DESCRIPTION_LENGTH = 500
MAX_NOTES_LENGTH = 2000

# Numeric limits
MIN_QUANTITY = 0.0
MAX_QUANTITY = 999999.99
MIN_COST = 0.0
MAX_COST = 999999.99
MIN_CONVERSION_FACTOR = 0.0001
MAX_CONVERSION_FACTOR = 999999.99

# Decimal precision
CURRENCY_DECIMAL_PLACES = 2
QUANTITY_DECIMAL_PLACES = 4
CONVERSION_DECIMAL_PLACES = 6

# ============================================================================
# Database Constants
# ============================================================================

# Database file name
DATABASE_FILENAME = "baking_tracker.db"

# Table names (for reference)
TABLE_INGREDIENT = "ingredients"
TABLE_RECIPE = "recipes"
TABLE_RECIPE_INGREDIENT = "recipe_ingredients"
TABLE_FINISHED_GOOD = "finished_goods"
TABLE_BUNDLE = "bundles"
TABLE_PACKAGE = "packages"
TABLE_RECIPIENT = "recipients"
TABLE_EVENT = "events"
TABLE_INVENTORY_SNAPSHOT = "inventory_snapshots"

# ============================================================================
# Date/Time Formats
# ============================================================================

DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DISPLAY_DATE_FORMAT = "%m/%d/%Y"
DISPLAY_DATETIME_FORMAT = "%m/%d/%Y %I:%M %p"

# ============================================================================
# Error Messages
# ============================================================================

ERROR_REQUIRED_FIELD = "This field is required"
ERROR_INVALID_NUMBER = "Please enter a valid number"
ERROR_INVALID_POSITIVE = "Value must be greater than zero"
ERROR_INVALID_NON_NEGATIVE = "Value must be zero or greater"
ERROR_INVALID_UNIT = "Invalid unit type"
ERROR_INVALID_CATEGORY = "Invalid category"
ERROR_NAME_TOO_LONG = f"Name must be {MAX_NAME_LENGTH} characters or less"
ERROR_DUPLICATE_NAME = "An item with this name already exists"
ERROR_DEPENDENCY_EXISTS = "Cannot delete: item is being used"

# ============================================================================
# Success Messages
# ============================================================================

SUCCESS_CREATED = "Successfully created"
SUCCESS_UPDATED = "Successfully updated"
SUCCESS_DELETED = "Successfully deleted"

# ============================================================================
# Helper Functions
# ============================================================================


def get_unit_type(unit: str) -> str:
    """
    Get the type category for a given unit.

    Args:
        unit: The unit string (e.g., "cup", "lb", "bag")

    Returns:
        The unit type: "weight", "volume", "count", "package", or "unknown"
    """
    return UNIT_TYPE_MAP.get(unit.lower(), "unknown")


def is_valid_unit(unit: str) -> bool:
    """
    Check if a unit is valid.

    Args:
        unit: The unit string to validate

    Returns:
        True if the unit is valid, False otherwise
    """
    return unit.lower() in [u.lower() for u in ALL_UNITS]


def is_valid_ingredient_category(category: str) -> bool:
    """
    Check if an ingredient category is valid.

    Args:
        category: The category string to validate

    Returns:
        True if the category is valid, False otherwise
    """
    return category in INGREDIENT_CATEGORIES


def is_valid_recipe_category(category: str) -> bool:
    """
    Check if a recipe category is valid.

    Args:
        category: The category string to validate

    Returns:
        True if the category is valid, False otherwise
    """
    return category in RECIPE_CATEGORIES


def format_currency(amount: float) -> str:
    """
    Format a number as currency.

    Args:
        amount: The amount to format

    Returns:
        Formatted string like "$12.34"
    """
    return f"${amount:,.{CURRENCY_DECIMAL_PLACES}f}"


def format_quantity(quantity: float, precision: int = QUANTITY_DECIMAL_PLACES) -> str:
    """
    Format a quantity with appropriate decimal places.

    Args:
        quantity: The quantity to format
        precision: Number of decimal places

    Returns:
        Formatted string with trailing zeros removed
    """
    formatted = f"{quantity:.{precision}f}"
    # Remove trailing zeros and decimal point if not needed
    return formatted.rstrip("0").rstrip(".")
