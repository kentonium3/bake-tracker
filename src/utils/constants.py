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
    "bar",
    "bottle",
    "can",
    "jar",
    "packet",
    "container",
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
    "bar": "package",
    "bottle": "package",
    "can": "package",
    "jar": "package",
    "packet": "package",
    "container": "package",
    "package": "package",
    "case": "package",
}

# ============================================================================
# Ingredient Categories
# ============================================================================

INGREDIENT_CATEGORIES: List[str] = [
    "Flour",
    "Sugar",
    "Dairy",
    "Oils/Butters",
    "Nuts",
    "Spices",
    "Chocolate/Candies",
    "Cocoa Powders",
    "Dried Fruits",
    "Extracts",
    "Syrups",
    "Alcohol",
    "Misc",
]

# ============================================================================
# Recipe Categories
# ============================================================================

RECIPE_CATEGORIES: List[str] = [
    "Cookies",
    "Cakes",
    "Candies",
    "Bars",
    "Brownies",
    "Breads",
    "Pastries",
    "Pies",
    "Tarts",
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
DATABASE_FILENAME = "bake_tracker.db"

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


# ============================================================================
# Ingredient Density Data (for volume-to-weight conversions)
# ============================================================================

# Standard densities in grams per cup
# These values are used to convert between volume and weight for common ingredients
INGREDIENT_DENSITIES: Dict[str, float] = {
    # Flours
    "all-purpose flour": 120.0,
    "bread flour": 127.0,
    "cake flour": 114.0,
    "whole wheat flour": 120.0,
    "pastry flour": 106.0,
    "self-rising flour": 120.0,
    "almond flour": 96.0,
    "coconut flour": 112.0,

    # Sugars
    "white granulated sugar": 200.0,
    "granulated sugar": 200.0,
    "cane sugar": 200.0,
    "brown sugar": 220.0,  # packed
    "light brown sugar": 220.0,
    "dark brown sugar": 220.0,
    "powdered sugar": 120.0,
    "confectioners sugar": 120.0,
    "icing sugar": 120.0,
    "turbinado sugar": 180.0,
    "demerara sugar": 180.0,

    # Fats
    "butter": 227.0,
    "margarine": 227.0,
    "shortening": 191.0,
    "lard": 205.0,
    "vegetable oil": 224.0,
    "olive oil": 216.0,
    "coconut oil": 218.0,

    # Liquids
    "water": 237.0,
    "milk": 244.0,
    "heavy cream": 238.0,
    "sour cream": 242.0,
    "yogurt": 245.0,
    "honey": 340.0,
    "maple syrup": 312.0,
    "corn syrup": 312.0,
    "molasses": 322.0,

    # Chocolate & Cocoa
    "cocoa powder": 85.0,
    "dutch cocoa": 85.0,
    "chocolate chips": 170.0,
    "semi-sweet chocolate chips": 170.0,
    "dark chocolate chips": 170.0,
    "milk chocolate chips": 170.0,
    "white chocolate chips": 170.0,

    # Nuts (whole/chopped)
    "almonds": 143.0,
    "walnuts": 120.0,
    "pecans": 109.0,
    "peanuts": 146.0,
    "cashews": 137.0,
    "hazelnuts": 135.0,
    "pistachios": 123.0,
    "macadamia nuts": 134.0,

    # Dried Fruits
    "raisins": 165.0,
    "cranberries": 120.0,
    "dates": 178.0,
    "apricots": 130.0,
    "figs": 149.0,

    # Spices & Leavening
    "baking powder": 192.0,
    "baking soda": 220.0,
    "salt": 292.0,
    "table salt": 292.0,
    "kosher salt": 218.0,
    "sea salt": 273.0,
    "cinnamon": 124.0,
    "vanilla extract": 208.0,

    # Other Common
    "oats": 81.0,  # old-fashioned
    "rolled oats": 81.0,
    "quick oats": 85.0,
    "cornmeal": 138.0,
    "cornstarch": 128.0,
    "bread crumbs": 108.0,
    "graham cracker crumbs": 100.0,
}


def get_ingredient_density(ingredient_name: str) -> float:
    """
    Get the density (g/cup) for an ingredient by name.

    Args:
        ingredient_name: Name of the ingredient

    Returns:
        Density in grams per cup, or 0.0 if not found
    """
    # Normalize the name (lowercase, strip)
    normalized_name = ingredient_name.lower().strip()

    # Try exact match first
    if normalized_name in INGREDIENT_DENSITIES:
        return INGREDIENT_DENSITIES[normalized_name]

    # Try partial matches (e.g., "King Arthur All-Purpose Flour" -> "all-purpose flour")
    for key, density in INGREDIENT_DENSITIES.items():
        if key in normalized_name or normalized_name in key:
            return density

    # No match found
    return 0.0


# ============================================================================
# Sample/Demo Data
# ============================================================================

SAMPLE_INGREDIENTS: List[Dict] = [
    # Flour category
    {
        "name": "All-Purpose Flour",
        "brand": "King Arthur",
        "category": "Flour",
        "purchase_unit": "bag",
        "purchase_unit_size": "25 lb",
        "recipe_unit": "cup",
        "conversion_factor": 100.0,
        "quantity": 2.0,
        "unit_cost": 18.99,
        "notes": "Store in cool, dry place",
    },
    # Sugar category
    {
        "name": "White Granulated Sugar",
        "brand": "Costco",
        "category": "Sugar",
        "purchase_unit": "bag",
        "purchase_unit_size": "25 lb",
        "recipe_unit": "cup",
        "conversion_factor": 56.25,
        "quantity": 1.5,
        "unit_cost": 16.99,
    },
    # Chocolate/Candies category
    {
        "name": "Semi-Sweet Chocolate Chips",
        "brand": "Nestle",
        "category": "Chocolate/Candies",
        "purchase_unit": "bag",
        "purchase_unit_size": "72 oz",
        "recipe_unit": "cup",
        "conversion_factor": 9.0,
        "quantity": 0.5,
        "unit_cost": 12.99,
    },
    # Nuts category
    {
        "name": "Almonds",
        "brand": "Costco",
        "category": "Nuts",
        "purchase_unit": "bag",
        "purchase_unit_size": "3 lb",
        "recipe_unit": "cup",
        "conversion_factor": 12.0,
        "quantity": 1.0,
        "unit_cost": 15.99,
    },
]
