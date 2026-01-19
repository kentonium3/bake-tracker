"""
Tests for input validation functions.

Tests cover all validation functions in the validators module including:
- String validation (required, length)
- Numeric validation (positive, non-negative, ranges)
- Unit validation
- Category validation
- Complete data validation (ingredient, recipe)
"""

import pytest

from src.utils import validators
from src.utils.constants import (
    MAX_NAME_LENGTH,
    MAX_NOTES_LENGTH,
    MIN_QUANTITY,
    MAX_QUANTITY,
)


class TestStringValidation:
    """Test string validation functions."""

    def test_validate_required_string_valid(self):
        """Test required string with valid input."""
        is_valid, error = validators.validate_required_string("Test Value", "Test Field")
        assert is_valid is True
        assert error == ""

    def test_validate_required_string_none(self):
        """Test required string with None."""
        is_valid, error = validators.validate_required_string(None, "Test Field")
        assert is_valid is False
        assert "required" in error.lower()

    def test_validate_required_string_empty(self):
        """Test required string with empty string."""
        is_valid, error = validators.validate_required_string("", "Test Field")
        assert is_valid is False
        assert "required" in error.lower()

    def test_validate_required_string_whitespace(self):
        """Test required string with only whitespace."""
        is_valid, error = validators.validate_required_string("   ", "Test Field")
        assert is_valid is False
        assert "required" in error.lower()

    def test_validate_string_length_valid(self):
        """Test string length validation with valid string."""
        is_valid, error = validators.validate_string_length("Test", 100, "Test Field")
        assert is_valid is True
        assert error == ""

    def test_validate_string_length_exact_max(self):
        """Test string length at exact maximum."""
        is_valid, error = validators.validate_string_length("A" * 100, 100, "Test Field")
        assert is_valid is True

    def test_validate_string_length_too_long(self):
        """Test string length exceeding maximum."""
        is_valid, error = validators.validate_string_length("A" * 101, 100, "Test Field")
        assert is_valid is False
        assert "100" in error


class TestNumericValidation:
    """Test numeric validation functions."""

    def test_validate_positive_number_valid_int(self):
        """Test positive number with valid integer."""
        is_valid, error = validators.validate_positive_number(5, "Test Field")
        assert is_valid is True
        assert error == ""

    def test_validate_positive_number_valid_float(self):
        """Test positive number with valid float."""
        is_valid, error = validators.validate_positive_number(5.5, "Test Field")
        assert is_valid is True

    def test_validate_positive_number_zero(self):
        """Test positive number with zero (should fail)."""
        is_valid, error = validators.validate_positive_number(0, "Test Field")
        assert is_valid is False
        assert "greater than zero" in error.lower()

    def test_validate_positive_number_negative(self):
        """Test positive number with negative value."""
        is_valid, error = validators.validate_positive_number(-5, "Test Field")
        assert is_valid is False

    def test_validate_positive_number_invalid_string(self):
        """Test positive number with non-numeric string."""
        is_valid, error = validators.validate_positive_number("abc", "Test Field")
        assert is_valid is False
        assert "valid number" in error.lower()

    def test_validate_non_negative_number_valid(self):
        """Test non-negative number with valid value."""
        is_valid, error = validators.validate_non_negative_number(0, "Test Field")
        assert is_valid is True

    def test_validate_non_negative_number_positive(self):
        """Test non-negative number with positive value."""
        is_valid, error = validators.validate_non_negative_number(5.5, "Test Field")
        assert is_valid is True

    def test_validate_non_negative_number_negative(self):
        """Test non-negative number with negative value."""
        is_valid, error = validators.validate_non_negative_number(-1, "Test Field")
        assert is_valid is False

    def test_validate_number_range_valid(self):
        """Test number range with value in range."""
        is_valid, error = validators.validate_number_range(5, 0, 10, "Test Field")
        assert is_valid is True

    def test_validate_number_range_at_min(self):
        """Test number range at minimum boundary."""
        is_valid, error = validators.validate_number_range(0, 0, 10, "Test Field")
        assert is_valid is True

    def test_validate_number_range_at_max(self):
        """Test number range at maximum boundary."""
        is_valid, error = validators.validate_number_range(10, 0, 10, "Test Field")
        assert is_valid is True

    def test_validate_number_range_below_min(self):
        """Test number range below minimum."""
        is_valid, error = validators.validate_number_range(-1, 0, 10, "Test Field")
        assert is_valid is False
        assert "between" in error.lower()

    def test_validate_number_range_above_max(self):
        """Test number range above maximum."""
        is_valid, error = validators.validate_number_range(11, 0, 10, "Test Field")
        assert is_valid is False


class TestUnitValidation:
    """Test unit validation functions."""

    def test_validate_unit_valid_weight(self):
        """Test unit validation with valid weight unit."""
        is_valid, error = validators.validate_unit("lb", "Test Unit")
        assert is_valid is True

    def test_validate_unit_valid_volume(self):
        """Test unit validation with valid volume unit."""
        is_valid, error = validators.validate_unit("cup", "Test Unit")
        assert is_valid is True

    def test_validate_unit_valid_count(self):
        """Test unit validation with valid count unit."""
        is_valid, error = validators.validate_unit("each", "Test Unit")
        assert is_valid is True

    def test_validate_unit_valid_package(self):
        """Test unit validation with valid package unit."""
        is_valid, error = validators.validate_unit("bag", "Test Unit")
        assert is_valid is True

    def test_validate_unit_case_insensitive(self):
        """Test unit validation is case-insensitive."""
        is_valid, error = validators.validate_unit("CUP", "Test Unit")
        assert is_valid is True

    def test_validate_unit_invalid(self):
        """Test unit validation with invalid unit."""
        is_valid, error = validators.validate_unit("invalid_unit", "Test Unit")
        assert is_valid is False
        assert "invalid unit" in error.lower()

    def test_validate_unit_empty(self):
        """Test unit validation with empty string."""
        is_valid, error = validators.validate_unit("", "Test Unit")
        assert is_valid is False


class TestCategoryValidation:
    """Test category validation functions."""

    def test_validate_ingredient_category_valid(self):
        """Test ingredient category with valid category."""
        is_valid, error = validators.validate_ingredient_category("Flour", "Category")
        assert is_valid is True

    def test_validate_ingredient_category_invalid(self):
        """Test ingredient category with whitespace-only string."""
        is_valid, error = validators.validate_ingredient_category("   ", "Category")
        assert is_valid is False

    def test_validate_ingredient_category_empty(self):
        """Test ingredient category with empty string."""
        is_valid, error = validators.validate_ingredient_category("", "Category")
        assert is_valid is False

    def test_validate_recipe_category_valid(self):
        """Test recipe category with valid category."""
        is_valid, error = validators.validate_recipe_category("Cookies", "Category")
        assert is_valid is True

    def test_validate_recipe_category_invalid(self):
        """Test recipe category with whitespace-only string."""
        is_valid, error = validators.validate_recipe_category("   ", "Category")
        assert is_valid is False


class TestIngredientValidation:
    """Test complete ingredient data validation."""

    def get_valid_ingredient_data(self):
        """Get valid ingredient data for testing."""
        return {
            "display_name": "All-Purpose Flour",
            "brand": "King Arthur",
            "category": "Flour",
            "package_unit": "bag",
            "package_unit_size": "50 lb",
            "conversion_factor": 200.0,
            "quantity": 2.5,
            "unit_cost": 15.99,
            "notes": "Store in cool, dry place",
        }

    def test_validate_ingredient_data_valid(self):
        """Test ingredient validation with all valid data."""
        data = self.get_valid_ingredient_data()
        is_valid, errors = validators.validate_ingredient_data(data)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_ingredient_data_missing_name(self):
        """Test ingredient validation with missing name."""
        data = self.get_valid_ingredient_data()
        del data["display_name"]
        is_valid, errors = validators.validate_ingredient_data(data)
        assert is_valid is False
        assert any("name" in e.lower() for e in errors)

    def test_validate_ingredient_data_invalid_category(self):
        """Test ingredient validation with missing/blank category."""
        data = self.get_valid_ingredient_data()
        data["category"] = "   "
        is_valid, errors = validators.validate_ingredient_data(data)
        assert is_valid is False
        assert any("category" in e.lower() for e in errors)

    @pytest.mark.skip(
        reason="TD-001: quantity moved to InventoryItem (formerly PantryItem), not Ingredient"
    )
    def test_validate_ingredient_data_negative_quantity(self):
        """Test ingredient validation with negative quantity - OBSOLETE."""
        pass

    @pytest.mark.skip(reason="TD-001: conversion_factor replaced by 4-field density model")
    def test_validate_ingredient_data_zero_conversion_factor(self):
        """Test ingredient validation with zero conversion factor - OBSOLETE."""
        pass

    @pytest.mark.skip(
        reason="TD-001: package_unit (formerly purchase_unit) moved to Product, not Ingredient"
    )
    def test_validate_ingredient_data_invalid_unit(self):
        """Test ingredient validation with invalid package_unit - OBSOLETE."""
        pass


class TestRecipeValidation:
    """Test complete recipe data validation."""

    def get_valid_recipe_data(self):
        """Get valid recipe data for testing."""
        return {
            "name": "Chocolate Chip Cookies",
            "category": "Cookies",
            "source": "Grandma's Recipe",
            "yield_quantity": 48,
            "yield_unit": "cookies",
            "yield_description": "2-inch cookies",
            "estimated_time_minutes": 45,
            "notes": "Best when served warm",
        }

    def test_validate_recipe_data_valid(self):
        """Test recipe validation with all valid data."""
        data = self.get_valid_recipe_data()
        is_valid, errors = validators.validate_recipe_data(data)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_recipe_data_missing_name(self):
        """Test recipe validation with missing name."""
        data = self.get_valid_recipe_data()
        del data["name"]
        is_valid, errors = validators.validate_recipe_data(data)
        assert is_valid is False

    def test_validate_recipe_data_invalid_category(self):
        """Test recipe validation with missing/blank category."""
        data = self.get_valid_recipe_data()
        data["category"] = "   "
        is_valid, errors = validators.validate_recipe_data(data)
        assert is_valid is False

    def test_validate_recipe_data_zero_yield(self):
        """Test recipe validation with zero yield.

        Note: yield_quantity is deprecated (F056). FinishedUnits are the
        source of truth for yield data. This field is now ignored by validation.
        """
        data = self.get_valid_recipe_data()
        data["yield_quantity"] = 0
        is_valid, errors = validators.validate_recipe_data(data)
        # yield_quantity is deprecated and ignored - validation should pass
        assert is_valid is True

    def test_validate_recipe_data_negative_time(self):
        """Test recipe validation with negative time."""
        data = self.get_valid_recipe_data()
        data["estimated_time_minutes"] = -10
        is_valid, errors = validators.validate_recipe_data(data)
        assert is_valid is False


class TestUtilityFunctions:
    """Test utility functions."""

    def test_sanitize_string_normal(self):
        """Test sanitize string with normal string."""
        result = validators.sanitize_string("  test  ")
        assert result == "test"

    def test_sanitize_string_none(self):
        """Test sanitize string with None."""
        result = validators.sanitize_string(None)
        assert result is None

    def test_sanitize_string_empty(self):
        """Test sanitize string with empty string."""
        result = validators.sanitize_string("")
        assert result is None

    def test_sanitize_string_whitespace_only(self):
        """Test sanitize string with only whitespace."""
        result = validators.sanitize_string("   ")
        assert result is None

    def test_parse_decimal_valid(self):
        """Test parse decimal with valid number."""
        result = validators.parse_decimal("5.5")
        assert result == 5.5

    def test_parse_decimal_invalid(self):
        """Test parse decimal with invalid input."""
        result = validators.parse_decimal("abc", default=10.0)
        assert result == 10.0

    def test_parse_decimal_none(self):
        """Test parse decimal with None."""
        result = validators.parse_decimal(None, default=10.0)
        assert result == 10.0

    def test_parse_int_valid(self):
        """Test parse int with valid number."""
        result = validators.parse_int("5")
        assert result == 5

    def test_parse_int_invalid(self):
        """Test parse int with invalid input."""
        result = validators.parse_int("abc", default=10)
        assert result == 10

    def test_parse_int_none(self):
        """Test parse int with None."""
        result = validators.parse_int(None, default=10)
        assert result == 10
