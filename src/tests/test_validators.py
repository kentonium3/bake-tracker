"""
Tests for input validation functions.

Tests cover all validation functions in the validators module including:
- String validation (required, length)
- Numeric validation (positive, non-negative, ranges)
- Unit validation
- Category validation
- Complete data validation (ingredient, recipe)

All validation functions raise ValidationError on failure (F094).
"""

import pytest

from src.utils import validators
from src.services.exceptions import ValidationError
from src.utils.constants import (
    MAX_NAME_LENGTH,
    MAX_NOTES_LENGTH,
    MIN_QUANTITY,
    MAX_QUANTITY,
)


class TestStringValidation:
    """Test string validation functions."""

    def test_validate_required_string_valid(self):
        """Test required string with valid input - no exception raised."""
        validators.validate_required_string("Test Value", "Test Field")
        # No exception means success

    def test_validate_required_string_none(self):
        """Test required string with None raises ValidationError."""
        with pytest.raises(ValidationError) as exc:
            validators.validate_required_string(None, "Test Field")
        assert "required" in str(exc.value).lower()

    def test_validate_required_string_empty(self):
        """Test required string with empty string raises ValidationError."""
        with pytest.raises(ValidationError) as exc:
            validators.validate_required_string("", "Test Field")
        assert "required" in str(exc.value).lower()

    def test_validate_required_string_whitespace(self):
        """Test required string with only whitespace raises ValidationError."""
        with pytest.raises(ValidationError) as exc:
            validators.validate_required_string("   ", "Test Field")
        assert "required" in str(exc.value).lower()

    def test_validate_string_length_valid(self):
        """Test string length validation with valid string - no exception."""
        validators.validate_string_length("Test", 100, "Test Field")

    def test_validate_string_length_exact_max(self):
        """Test string length at exact maximum - no exception."""
        validators.validate_string_length("A" * 100, 100, "Test Field")

    def test_validate_string_length_too_long(self):
        """Test string length exceeding maximum raises ValidationError."""
        with pytest.raises(ValidationError) as exc:
            validators.validate_string_length("A" * 101, 100, "Test Field")
        assert "100" in str(exc.value)


class TestNumericValidation:
    """Test numeric validation functions."""

    def test_validate_positive_number_valid_int(self):
        """Test positive number with valid integer - no exception."""
        validators.validate_positive_number(5, "Test Field")

    def test_validate_positive_number_valid_float(self):
        """Test positive number with valid float - no exception."""
        validators.validate_positive_number(5.5, "Test Field")

    def test_validate_positive_number_zero(self):
        """Test positive number with zero raises ValidationError."""
        with pytest.raises(ValidationError) as exc:
            validators.validate_positive_number(0, "Test Field")
        assert "greater than zero" in str(exc.value).lower()

    def test_validate_positive_number_negative(self):
        """Test positive number with negative value raises ValidationError."""
        with pytest.raises(ValidationError):
            validators.validate_positive_number(-5, "Test Field")

    def test_validate_positive_number_invalid_string(self):
        """Test positive number with non-numeric string raises ValidationError."""
        with pytest.raises(ValidationError) as exc:
            validators.validate_positive_number("abc", "Test Field")
        assert "valid number" in str(exc.value).lower()

    def test_validate_non_negative_number_valid(self):
        """Test non-negative number with valid value - no exception."""
        validators.validate_non_negative_number(0, "Test Field")

    def test_validate_non_negative_number_positive(self):
        """Test non-negative number with positive value - no exception."""
        validators.validate_non_negative_number(5.5, "Test Field")

    def test_validate_non_negative_number_negative(self):
        """Test non-negative number with negative value raises ValidationError."""
        with pytest.raises(ValidationError):
            validators.validate_non_negative_number(-1, "Test Field")

    def test_validate_number_range_valid(self):
        """Test number range with value in range - no exception."""
        validators.validate_number_range(5, 0, 10, "Test Field")

    def test_validate_number_range_at_min(self):
        """Test number range at minimum boundary - no exception."""
        validators.validate_number_range(0, 0, 10, "Test Field")

    def test_validate_number_range_at_max(self):
        """Test number range at maximum boundary - no exception."""
        validators.validate_number_range(10, 0, 10, "Test Field")

    def test_validate_number_range_below_min(self):
        """Test number range below minimum raises ValidationError."""
        with pytest.raises(ValidationError) as exc:
            validators.validate_number_range(-1, 0, 10, "Test Field")
        assert "between" in str(exc.value).lower()

    def test_validate_number_range_above_max(self):
        """Test number range above maximum raises ValidationError."""
        with pytest.raises(ValidationError):
            validators.validate_number_range(11, 0, 10, "Test Field")


class TestUnitValidation:
    """Test unit validation functions."""

    def test_validate_unit_valid_weight(self):
        """Test unit validation with valid weight unit - no exception."""
        validators.validate_unit("lb", "Test Unit")

    def test_validate_unit_valid_volume(self):
        """Test unit validation with valid volume unit - no exception."""
        validators.validate_unit("cup", "Test Unit")

    def test_validate_unit_valid_count(self):
        """Test unit validation with valid count unit - no exception."""
        validators.validate_unit("each", "Test Unit")

    def test_validate_unit_valid_package(self):
        """Test unit validation with valid package unit - no exception."""
        validators.validate_unit("bag", "Test Unit")

    def test_validate_unit_case_insensitive(self):
        """Test unit validation is case-insensitive - no exception."""
        validators.validate_unit("CUP", "Test Unit")

    def test_validate_unit_invalid(self):
        """Test unit validation with invalid unit raises ValidationError."""
        with pytest.raises(ValidationError) as exc:
            validators.validate_unit("invalid_unit", "Test Unit")
        assert "invalid unit" in str(exc.value).lower()

    def test_validate_unit_empty(self):
        """Test unit validation with empty string raises ValidationError."""
        with pytest.raises(ValidationError):
            validators.validate_unit("", "Test Unit")


class TestCategoryValidation:
    """Test category validation functions."""

    def test_validate_ingredient_category_valid(self):
        """Test ingredient category with valid category - no exception."""
        validators.validate_ingredient_category("Flour", "Category")

    def test_validate_ingredient_category_invalid(self):
        """Test ingredient category with whitespace-only raises ValidationError."""
        with pytest.raises(ValidationError):
            validators.validate_ingredient_category("   ", "Category")

    def test_validate_ingredient_category_empty(self):
        """Test ingredient category with empty string raises ValidationError."""
        with pytest.raises(ValidationError):
            validators.validate_ingredient_category("", "Category")

    def test_validate_recipe_category_valid(self):
        """Test recipe category with valid category - no exception."""
        validators.validate_recipe_category("Cookies", "Category")

    def test_validate_recipe_category_invalid(self):
        """Test recipe category with whitespace-only raises ValidationError."""
        with pytest.raises(ValidationError):
            validators.validate_recipe_category("   ", "Category")


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
        """Test ingredient validation with all valid data - no exception."""
        data = self.get_valid_ingredient_data()
        validators.validate_ingredient_data(data)

    def test_validate_ingredient_data_missing_name(self):
        """Test ingredient validation with missing name raises ValidationError."""
        data = self.get_valid_ingredient_data()
        del data["display_name"]
        with pytest.raises(ValidationError) as exc:
            validators.validate_ingredient_data(data)
        assert any("name" in e.lower() for e in exc.value.errors)

    def test_validate_ingredient_data_invalid_category(self):
        """Test ingredient validation with missing/blank category raises ValidationError."""
        data = self.get_valid_ingredient_data()
        data["category"] = "   "
        with pytest.raises(ValidationError) as exc:
            validators.validate_ingredient_data(data)
        assert any("category" in e.lower() for e in exc.value.errors)


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
        """Test recipe validation with all valid data - no exception."""
        data = self.get_valid_recipe_data()
        validators.validate_recipe_data(data)

    def test_validate_recipe_data_missing_name(self):
        """Test recipe validation with missing name raises ValidationError."""
        data = self.get_valid_recipe_data()
        del data["name"]
        with pytest.raises(ValidationError):
            validators.validate_recipe_data(data)

    def test_validate_recipe_data_invalid_category(self):
        """Test recipe validation with missing/blank category raises ValidationError."""
        data = self.get_valid_recipe_data()
        data["category"] = "   "
        with pytest.raises(ValidationError):
            validators.validate_recipe_data(data)

    def test_validate_recipe_data_zero_yield(self):
        """Test recipe validation with zero yield.

        Note: yield_quantity is deprecated (F056). FinishedUnits are the
        source of truth for yield data. This field is now ignored by validation.
        """
        data = self.get_valid_recipe_data()
        data["yield_quantity"] = 0
        # yield_quantity is deprecated and ignored - validation should pass
        validators.validate_recipe_data(data)

    def test_validate_recipe_data_negative_time(self):
        """Test recipe validation with negative time raises ValidationError."""
        data = self.get_valid_recipe_data()
        data["estimated_time_minutes"] = -10
        with pytest.raises(ValidationError):
            validators.validate_recipe_data(data)


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
