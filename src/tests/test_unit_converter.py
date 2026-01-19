"""
Unit tests for the unit conversion system.

Tests cover:
- Standard unit conversions (weight, volume, count)
- Density-based cross-type conversions (volume↔weight)
- Cost calculations
- Edge cases and error handling
"""

import pytest
from src.services.unit_converter import (
    # Unit type detection
    get_conversion_table,
    get_unit_type,
    units_compatible,
    # Standard conversions
    convert_standard_units,
    format_conversion,
    # Cost calculations
    calculate_cost_per_yield_unit,
    format_cost,
    # Validation
    validate_quantity,
)

# ============================================================================
# Unit Type Detection Tests
# ============================================================================


class TestUnitTypeDetection:
    """Test unit type detection and compatibility checking."""

    def test_get_unit_type_weight(self):
        """Test weight unit type detection."""
        assert get_unit_type("oz") == "weight"
        assert get_unit_type("lb") == "weight"
        assert get_unit_type("g") == "weight"
        assert get_unit_type("kg") == "weight"

    def test_get_unit_type_volume(self):
        """Test volume unit type detection."""
        assert get_unit_type("tsp") == "volume"
        assert get_unit_type("tbsp") == "volume"
        assert get_unit_type("cup") == "volume"
        assert get_unit_type("ml") == "volume"
        assert get_unit_type("l") == "volume"
        assert get_unit_type("fl oz") == "volume"
        assert get_unit_type("pt") == "volume"
        assert get_unit_type("qt") == "volume"
        assert get_unit_type("gal") == "volume"

    def test_get_unit_type_count(self):
        """Test count unit type detection."""
        assert get_unit_type("each") == "count"
        assert get_unit_type("count") == "count"
        assert get_unit_type("piece") == "count"
        assert get_unit_type("dozen") == "count"

    def test_get_unit_type_unknown(self):
        """Test unknown unit type detection."""
        assert get_unit_type("bag") == "unknown"
        assert get_unit_type("box") == "unknown"
        assert get_unit_type("invalid") == "unknown"

    def test_get_unit_type_case_insensitive(self):
        """Test case-insensitive unit type detection."""
        assert get_unit_type("OZ") == "weight"
        assert get_unit_type("Cup") == "volume"
        assert get_unit_type("DOZEN") == "count"

    def test_get_conversion_table_weight(self):
        """Test getting weight conversion table."""
        table = get_conversion_table("oz")
        assert table is not None
        assert "oz" in table
        assert "lb" in table
        assert "g" in table
        assert "kg" in table

    def test_get_conversion_table_volume(self):
        """Test getting volume conversion table."""
        table = get_conversion_table("cup")
        assert table is not None
        assert "cup" in table
        assert "ml" in table
        assert "l" in table
        assert "tsp" in table

    def test_get_conversion_table_unknown(self):
        """Test unknown unit returns None."""
        assert get_conversion_table("bag") is None
        assert get_conversion_table("invalid") is None

    def test_units_compatible_same_type(self):
        """Test compatible units of same type."""
        assert units_compatible("oz", "lb") is True
        assert units_compatible("cup", "ml") is True
        assert units_compatible("each", "dozen") is True

    def test_units_compatible_different_types(self):
        """Test incompatible units of different types."""
        assert units_compatible("oz", "cup") is False
        assert units_compatible("lb", "tsp") is False
        assert units_compatible("dozen", "g") is False

    def test_units_compatible_unknown(self):
        """Test compatibility with unknown units."""
        assert units_compatible("oz", "bag") is False
        assert units_compatible("invalid", "cup") is False
        assert units_compatible("bag", "box") is False


# ============================================================================
# Standard Weight Conversion Tests
# ============================================================================


class TestWeightConversions:
    """Test standard weight unit conversions."""

    def test_convert_oz_to_lb(self):
        """Test ounces to pounds conversion."""
        success, result, error = convert_standard_units(16, "oz", "lb")
        assert success is True
        assert error == ""
        assert result == pytest.approx(1.0, rel=1e-6)

    def test_convert_lb_to_oz(self):
        """Test pounds to ounces conversion."""
        success, result, error = convert_standard_units(1, "lb", "oz")
        assert success is True
        assert result == pytest.approx(16.0, rel=1e-6)

    def test_convert_lb_to_kg(self):
        """Test pounds to kilograms conversion."""
        success, result, error = convert_standard_units(1, "lb", "kg")
        assert success is True
        assert result == pytest.approx(0.453592, rel=1e-4)

    def test_convert_kg_to_lb(self):
        """Test kilograms to pounds conversion."""
        success, result, error = convert_standard_units(1, "kg", "lb")
        assert success is True
        assert result == pytest.approx(2.20462, rel=1e-4)

    def test_convert_oz_to_g(self):
        """Test ounces to grams conversion."""
        success, result, error = convert_standard_units(1, "oz", "g")
        assert success is True
        assert result == pytest.approx(28.3495, rel=1e-4)

    def test_convert_g_to_oz(self):
        """Test grams to ounces conversion."""
        success, result, error = convert_standard_units(100, "g", "oz")
        assert success is True
        assert result == pytest.approx(3.5274, rel=1e-4)

    def test_convert_case_insensitive(self):
        """Test case-insensitive weight conversions."""
        success1, result1, _ = convert_standard_units(1, "LB", "oz")
        success2, result2, _ = convert_standard_units(1, "lb", "OZ")
        assert success1 is True
        assert success2 is True
        assert result1 == pytest.approx(result2, rel=1e-6)


# ============================================================================
# Standard Volume Conversion Tests
# ============================================================================


class TestVolumeConversions:
    """Test standard volume unit conversions."""

    def test_convert_tsp_to_tbsp(self):
        """Test teaspoons to tablespoons conversion."""
        success, result, error = convert_standard_units(3, "tsp", "tbsp")
        assert success is True
        assert error == ""
        assert result == pytest.approx(1.0, rel=1e-4)

    def test_convert_tbsp_to_cup(self):
        """Test tablespoons to cups conversion."""
        success, result, error = convert_standard_units(16, "tbsp", "cup")
        assert success is True
        assert result == pytest.approx(1.0, rel=1e-4)

    def test_convert_cup_to_ml(self):
        """Test cups to milliliters conversion."""
        success, result, error = convert_standard_units(1, "cup", "ml")
        assert success is True
        assert result == pytest.approx(236.588, rel=1e-4)

    def test_convert_ml_to_cup(self):
        """Test milliliters to cups conversion."""
        success, result, error = convert_standard_units(250, "ml", "cup")
        assert success is True
        assert result == pytest.approx(1.0567, rel=1e-4)

    def test_convert_cup_to_fl_oz(self):
        """Test cups to fluid ounces conversion."""
        success, result, error = convert_standard_units(1, "cup", "fl oz")
        assert success is True
        assert result == pytest.approx(8.0, rel=1e-4)

    def test_convert_qt_to_gal(self):
        """Test quarts to gallons conversion."""
        success, result, error = convert_standard_units(4, "qt", "gal")
        assert success is True
        assert result == pytest.approx(1.0, rel=1e-4)

    def test_convert_l_to_ml(self):
        """Test liters to milliliters conversion."""
        success, result, error = convert_standard_units(1, "l", "ml")
        assert success is True
        assert result == pytest.approx(1000.0, rel=1e-6)


# ============================================================================
# Count Conversion Tests
# ============================================================================


class TestCountConversions:
    """Test count unit conversions."""

    def test_convert_each_to_dozen(self):
        """Test each to dozen conversion."""
        success, result, error = convert_standard_units(12, "each", "dozen")
        assert success is True
        assert error == ""
        assert result == pytest.approx(1.0, rel=1e-6)

    def test_convert_dozen_to_each(self):
        """Test dozen to each conversion."""
        success, result, error = convert_standard_units(2, "dozen", "each")
        assert success is True
        assert result == pytest.approx(24.0, rel=1e-6)

    def test_convert_piece_to_count(self):
        """Test piece to count conversion (both = 1)."""
        success, result, error = convert_standard_units(10, "piece", "count")
        assert success is True
        assert result == pytest.approx(10.0, rel=1e-6)


# ============================================================================
# Conversion Error Handling Tests
# ============================================================================


class TestConversionErrors:
    """Test error handling in standard conversions."""

    def test_negative_value(self):
        """Test negative value error."""
        success, result, error = convert_standard_units(-5, "oz", "lb")
        assert success is False
        assert result == 0.0
        assert "negative" in error.lower()

    def test_unknown_from_unit(self):
        """Test unknown source unit error."""
        success, result, error = convert_standard_units(10, "invalid", "oz")
        assert success is False
        assert result == 0.0
        assert "unknown" in error.lower()

    def test_incompatible_units(self):
        """Test incompatible unit types error."""
        success, result, error = convert_standard_units(10, "oz", "cup")
        assert success is False
        assert result == 0.0
        assert "incompatible" in error.lower()

    def test_same_unit_conversion(self):
        """Test converting to same unit returns original value."""
        success, result, error = convert_standard_units(5, "oz", "oz")
        assert success is True
        assert result == 5.0
        assert error == ""


# ============================================================================
# Format Conversion Tests
# ============================================================================


class TestFormatConversion:
    """Test conversion formatting for display."""

    def test_format_conversion_basic(self):
        """Test basic conversion formatting."""
        result = format_conversion(1, "lb", "oz")
        assert "1 lb" in result
        assert "16.00 oz" in result

    def test_format_conversion_precision(self):
        """Test conversion formatting with custom precision."""
        result = format_conversion(1, "cup", "ml", precision=1)
        assert "1 cup" in result
        assert "236.6 ml" in result

    def test_format_conversion_error(self):
        """Test error message formatting."""
        result = format_conversion(10, "oz", "cup")
        assert "Error" in result


# ============================================================================
# Cost Calculation Tests
# ============================================================================


class TestCostCalculations:
    """Test cost calculation utilities."""

    def test_calculate_cost_per_yield_unit(self):
        """Test cost per yield unit calculation."""
        # Total recipe cost $5.00, yields 24 cookies
        # Cost per cookie = $5.00 / 24 = $0.2083...
        success, cost, error = calculate_cost_per_yield_unit(5.0, 24.0)
        assert success is True
        assert error == ""
        assert cost == pytest.approx(0.2083333, rel=1e-6)

    def test_calculate_cost_per_yield_unit_errors(self):
        """Test cost per yield unit error handling."""
        # Negative total cost
        success, _, error = calculate_cost_per_yield_unit(-5.0, 24.0)
        assert success is False
        assert "negative" in error.lower()

        # Zero yield quantity
        success, _, error = calculate_cost_per_yield_unit(5.0, 0.0)
        assert success is False
        assert "positive" in error.lower()


# ============================================================================
# Format Cost Tests
# ============================================================================


class TestFormatCost:
    """Test cost formatting utilities."""

    def test_format_cost_default(self):
        """Test default cost formatting."""
        result = format_cost(12.50)
        assert result == "$12.50"

    def test_format_cost_custom_symbol(self):
        """Test cost formatting with custom currency symbol."""
        result = format_cost(15.00, currency_symbol="€")
        assert result == "€15.00"

    def test_format_cost_custom_precision(self):
        """Test cost formatting with custom precision."""
        result = format_cost(10.123, precision=3)
        assert result == "$10.123"

    def test_format_cost_zero(self):
        """Test formatting zero cost."""
        result = format_cost(0.0)
        assert result == "$0.00"

    def test_format_cost_large_amount(self):
        """Test formatting large cost."""
        result = format_cost(1234.56)
        assert result == "$1234.56"


# ============================================================================
# Validation Tests
# ============================================================================


class TestValidation:
    """Test validation helper functions."""

    def test_validate_quantity_valid(self):
        """Test valid quantity."""
        is_valid, error = validate_quantity(10.5)
        assert is_valid is True
        assert error == ""

    def test_validate_quantity_zero_allowed(self):
        """Test zero quantity when allowed."""
        is_valid, error = validate_quantity(0.0, allow_zero=True)
        assert is_valid is True
        assert error == ""

    def test_validate_quantity_zero_not_allowed(self):
        """Test zero quantity when not allowed."""
        is_valid, error = validate_quantity(0.0, allow_zero=False)
        assert is_valid is False
        assert "zero" in error.lower()

    def test_validate_quantity_negative(self):
        """Test negative quantity."""
        is_valid, error = validate_quantity(-5.0)
        assert is_valid is False
        assert "negative" in error.lower()

    def test_validate_quantity_too_large(self):
        """Test unreasonably large quantity."""
        is_valid, error = validate_quantity(1e10)
        assert is_valid is False
        assert "large" in error.lower()


# ============================================================================
# Volume-Weight Conversion Tests (Feature 010 - Ingredient density)
# ============================================================================

from src.services.unit_converter import (
    convert_volume_to_weight,
    convert_weight_to_volume,
    convert_any_units,
)
from src.models.ingredient import Ingredient


class TestVolumeWeightConversions:
    """Test volume-to-weight and weight-to-volume conversions using Ingredient density."""

    def test_convert_volume_to_weight_with_ingredient(self):
        """Test volume to weight conversion using ingredient density."""
        ingredient = Ingredient(
            display_name="All-Purpose Flour",
            slug="all-purpose-flour",
            category="Flour",
            density_volume_value=1.0,
            density_volume_unit="cup",
            density_weight_value=120.0,
            density_weight_unit="g",
        )
        success, weight, error = convert_volume_to_weight(1.0, "cup", "g", ingredient=ingredient)
        assert success
        assert abs(weight - 120.0) < 0.5  # Allow small rounding difference
        assert error == ""

    def test_convert_volume_to_weight_no_density(self):
        """Test conversion fails gracefully when no density."""
        ingredient = Ingredient(display_name="Mystery Ingredient", slug="mystery", category="Other")
        success, weight, error = convert_volume_to_weight(1.0, "cup", "g", ingredient=ingredient)
        assert not success
        assert "Density required" in error

    def test_convert_volume_to_weight_with_override(self):
        """Test density override still works."""
        # 1 cup water = 236.588 ml, 1.0 g/ml -> 236.588 g
        success, weight, error = convert_volume_to_weight(1.0, "cup", "g", density_g_per_ml=1.0)
        assert success
        assert abs(weight - 236.588) < 0.1

    def test_convert_weight_to_volume_with_ingredient(self):
        """Test weight to volume conversion using ingredient density."""
        ingredient = Ingredient(
            display_name="All-Purpose Flour",
            slug="all-purpose-flour",
            category="Flour",
            density_volume_value=1.0,
            density_volume_unit="cup",
            density_weight_value=120.0,
            density_weight_unit="g",
        )
        success, volume, error = convert_weight_to_volume(120.0, "g", "cup", ingredient=ingredient)
        assert success
        assert abs(volume - 1.0) < 0.05  # Allow small rounding difference
        assert error == ""

    def test_convert_weight_to_volume_no_density(self):
        """Test conversion fails gracefully when no density."""
        ingredient = Ingredient(display_name="Mystery Ingredient", slug="mystery", category="Other")
        success, volume, error = convert_weight_to_volume(100.0, "g", "cup", ingredient=ingredient)
        assert not success
        assert "Density required" in error

    def test_convert_weight_to_volume_with_override(self):
        """Test density override still works for weight to volume."""
        # 100g at 1.0 g/ml = 100 ml
        success, volume, error = convert_weight_to_volume(100.0, "g", "ml", density_g_per_ml=1.0)
        assert success
        assert abs(volume - 100.0) < 0.1

    def test_convert_any_units_same_type(self):
        """Test convert_any_units for same-type conversion."""
        success, result, error = convert_any_units(1.0, "lb", "oz")
        assert success
        assert abs(result - 16.0) < 0.01
        assert error == ""

    def test_convert_any_units_volume_to_weight(self):
        """Test convert_any_units for volume to weight with ingredient."""
        ingredient = Ingredient(
            display_name="Sugar",
            slug="sugar",
            category="Sugar",
            density_volume_value=1.0,
            density_volume_unit="cup",
            density_weight_value=200.0,
            density_weight_unit="g",
        )
        success, result, error = convert_any_units(1.0, "cup", "g", ingredient=ingredient)
        assert success
        assert abs(result - 200.0) < 1.0

    def test_convert_any_units_weight_to_volume(self):
        """Test convert_any_units for weight to volume with ingredient."""
        ingredient = Ingredient(
            display_name="Sugar",
            slug="sugar",
            category="Sugar",
            density_volume_value=1.0,
            density_volume_unit="cup",
            density_weight_value=200.0,
            density_weight_unit="g",
        )
        success, result, error = convert_any_units(200.0, "g", "cup", ingredient=ingredient)
        assert success
        assert abs(result - 1.0) < 0.05

    def test_convert_any_units_no_ingredient_or_density(self):
        """Test convert_any_units fails for cross-type without density."""
        success, result, error = convert_any_units(1.0, "cup", "g")
        assert not success
        assert "required" in error.lower()

    def test_error_message_includes_ingredient_name(self):
        """Test that error message includes ingredient name for user guidance."""
        ingredient = Ingredient(
            display_name="Special Flour", slug="special-flour", category="Flour"
        )
        success, weight, error = convert_volume_to_weight(1.0, "cup", "g", ingredient=ingredient)
        assert not success
        assert "Special Flour" in error
