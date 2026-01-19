"""
Unit tests for the material unit conversion system.

Tests cover:
- Linear unit conversions (feet, inches, yards, meters, mm to cm)
- Area unit conversions (square_feet, square_inches, square_meters to square_cm)
- Reverse conversions (from base to target units)
- Unit compatibility validation
- Edge cases and error handling
"""

import pytest
from decimal import Decimal
from src.services.material_unit_converter import (
    # Conversion factor dictionaries
    LINEAR_TO_CM,
    AREA_TO_SQUARE_CM,
    UNIT_TYPES,
    # Validation
    validate_unit_compatibility,
    get_unit_type,
    # Conversion functions
    convert_to_base_units,
    convert_from_base_units,
    convert_units,
)


# ============================================================================
# Unit Type Detection Tests
# ============================================================================


class TestUnitTypeDetection:
    """Test unit type detection and validation."""

    def test_get_unit_type_linear(self):
        """Test linear unit type detection."""
        assert get_unit_type("feet") == "linear_cm"
        assert get_unit_type("inches") == "linear_cm"
        assert get_unit_type("yards") == "linear_cm"
        assert get_unit_type("meters") == "linear_cm"
        assert get_unit_type("mm") == "linear_cm"
        assert get_unit_type("cm") == "linear_cm"

    def test_get_unit_type_area(self):
        """Test area unit type detection."""
        assert get_unit_type("square_feet") == "square_cm"
        assert get_unit_type("square_inches") == "square_cm"
        assert get_unit_type("square_meters") == "square_cm"
        assert get_unit_type("square_cm") == "square_cm"

    def test_get_unit_type_each(self):
        """Test each unit type detection."""
        assert get_unit_type("each") == "each"

    def test_get_unit_type_unknown(self):
        """Test unknown unit returns None."""
        assert get_unit_type("unknown") is None
        assert get_unit_type("liters") is None
        assert get_unit_type("grams") is None
        assert get_unit_type("") is None


class TestUnitCompatibilityValidation:
    """Test unit compatibility validation."""

    def test_validate_linear_units(self):
        """Test linear unit validation."""
        is_valid, error = validate_unit_compatibility("feet", "linear_cm")
        assert is_valid is True
        assert error is None

        is_valid, error = validate_unit_compatibility("inches", "linear_cm")
        assert is_valid is True
        assert error is None

        is_valid, error = validate_unit_compatibility("cm", "linear_cm")
        assert is_valid is True
        assert error is None

    def test_validate_area_units(self):
        """Test area unit validation."""
        is_valid, error = validate_unit_compatibility("square_feet", "square_cm")
        assert is_valid is True
        assert error is None

        is_valid, error = validate_unit_compatibility("square_inches", "square_cm")
        assert is_valid is True
        assert error is None

    def test_validate_each_unit(self):
        """Test each unit validation."""
        is_valid, error = validate_unit_compatibility("each", "each")
        assert is_valid is True
        assert error is None

    def test_validate_incompatible_linear_to_area(self):
        """Test linear unit rejected for area base type."""
        is_valid, error = validate_unit_compatibility("feet", "square_cm")
        assert is_valid is False
        assert "not compatible" in error
        assert "square_cm" in error

    def test_validate_incompatible_area_to_linear(self):
        """Test area unit rejected for linear base type."""
        is_valid, error = validate_unit_compatibility("square_feet", "linear_cm")
        assert is_valid is False
        assert "not compatible" in error

    def test_validate_unknown_base_type(self):
        """Test unknown base type error."""
        is_valid, error = validate_unit_compatibility("feet", "unknown_type")
        assert is_valid is False
        assert "Unknown base unit type" in error


# ============================================================================
# Linear Conversion Tests (to base)
# ============================================================================


class TestLinearToBaseConversions:
    """Test linear unit conversions to centimeters."""

    def test_feet_to_cm(self):
        """Test feet to cm conversion: 1 foot = 30.48 cm."""
        success, result, error = convert_to_base_units(Decimal("1"), "feet", "linear_cm")
        assert success is True
        assert error is None
        assert result == Decimal("30.48")

    def test_inches_to_cm(self):
        """Test inches to cm conversion: 1 inch = 2.54 cm."""
        success, result, error = convert_to_base_units(Decimal("1"), "inches", "linear_cm")
        assert success is True
        assert error is None
        assert result == Decimal("2.54")

    def test_yards_to_cm(self):
        """Test yards to cm conversion: 1 yard = 91.44 cm."""
        success, result, error = convert_to_base_units(Decimal("1"), "yards", "linear_cm")
        assert success is True
        assert error is None
        assert result == Decimal("91.44")

    def test_meters_to_cm(self):
        """Test meters to cm conversion: 1 meter = 100 cm."""
        success, result, error = convert_to_base_units(Decimal("1"), "meters", "linear_cm")
        assert success is True
        assert error is None
        assert result == Decimal("100")

    def test_mm_to_cm(self):
        """Test mm to cm conversion: 10 mm = 1 cm."""
        success, result, error = convert_to_base_units(Decimal("10"), "mm", "linear_cm")
        assert success is True
        assert error is None
        assert result == Decimal("1.0")

    def test_cm_to_cm(self):
        """Test cm to cm conversion (base unit identity)."""
        success, result, error = convert_to_base_units(Decimal("50"), "cm", "linear_cm")
        assert success is True
        assert error is None
        assert result == Decimal("50")

    def test_multiple_feet_to_cm(self):
        """Test multiple feet to cm: 3 feet = 91.44 cm."""
        success, result, error = convert_to_base_units(Decimal("3"), "feet", "linear_cm")
        assert success is True
        assert result == Decimal("91.44")

    def test_fractional_inches(self):
        """Test fractional inches: 0.5 inch = 1.27 cm."""
        success, result, error = convert_to_base_units(Decimal("0.5"), "inches", "linear_cm")
        assert success is True
        assert result == Decimal("1.27")


# ============================================================================
# Area Conversion Tests (to base)
# ============================================================================


class TestAreaToBaseConversions:
    """Test area unit conversions to square centimeters."""

    def test_square_feet_to_square_cm(self):
        """Test square feet to square cm: 1 sq ft = 929.0304 sq cm."""
        success, result, error = convert_to_base_units(Decimal("1"), "square_feet", "square_cm")
        assert success is True
        assert error is None
        assert result == Decimal("929.0304")

    def test_square_inches_to_square_cm(self):
        """Test square inches to square cm: 1 sq in = 6.4516 sq cm."""
        success, result, error = convert_to_base_units(Decimal("1"), "square_inches", "square_cm")
        assert success is True
        assert error is None
        assert result == Decimal("6.4516")

    def test_square_meters_to_square_cm(self):
        """Test square meters to square cm: 1 sq m = 10000 sq cm."""
        success, result, error = convert_to_base_units(Decimal("1"), "square_meters", "square_cm")
        assert success is True
        assert error is None
        assert result == Decimal("10000")

    def test_square_cm_to_square_cm(self):
        """Test square cm to square cm (base unit identity)."""
        success, result, error = convert_to_base_units(Decimal("100"), "square_cm", "square_cm")
        assert success is True
        assert error is None
        assert result == Decimal("100")

    def test_multiple_square_feet(self):
        """Test multiple square feet: 2 sq ft = 1858.0608 sq cm."""
        success, result, error = convert_to_base_units(Decimal("2"), "square_feet", "square_cm")
        assert success is True
        assert result == Decimal("1858.0608")


# ============================================================================
# Each Type Tests
# ============================================================================


class TestEachTypeConversions:
    """Test each (discrete count) type handling."""

    def test_each_to_base(self):
        """Test each to base conversion (identity)."""
        success, result, error = convert_to_base_units(Decimal("5"), "each", "each")
        assert success is True
        assert error is None
        assert result == Decimal("5")

    def test_each_from_base(self):
        """Test each from base conversion (identity)."""
        success, result, error = convert_from_base_units(Decimal("10"), "each", "each")
        assert success is True
        assert error is None
        assert result == Decimal("10")

    def test_each_incompatible_with_linear(self):
        """Test that each is rejected for linear base type."""
        success, result, error = convert_to_base_units(Decimal("5"), "each", "linear_cm")
        assert success is False
        assert result is None
        assert "not compatible" in error

    def test_linear_incompatible_with_each(self):
        """Test that linear units are rejected for each base type."""
        success, result, error = convert_to_base_units(Decimal("5"), "feet", "each")
        assert success is False
        assert result is None
        assert "not compatible" in error


# ============================================================================
# Reverse Conversion Tests (from base)
# ============================================================================


class TestLinearFromBaseConversions:
    """Test linear unit conversions from centimeters."""

    def test_cm_to_feet(self):
        """Test cm to feet conversion: 30.48 cm = 1 foot."""
        success, result, error = convert_from_base_units(Decimal("30.48"), "feet", "linear_cm")
        assert success is True
        assert error is None
        assert result == Decimal("1")

    def test_cm_to_inches(self):
        """Test cm to inches conversion: 2.54 cm = 1 inch."""
        success, result, error = convert_from_base_units(Decimal("2.54"), "inches", "linear_cm")
        assert success is True
        assert error is None
        assert result == Decimal("1")

    def test_cm_to_yards(self):
        """Test cm to yards conversion: 91.44 cm = 1 yard."""
        success, result, error = convert_from_base_units(Decimal("91.44"), "yards", "linear_cm")
        assert success is True
        assert error is None
        assert result == Decimal("1")

    def test_cm_to_meters(self):
        """Test cm to meters conversion: 100 cm = 1 meter."""
        success, result, error = convert_from_base_units(Decimal("100"), "meters", "linear_cm")
        assert success is True
        assert error is None
        assert result == Decimal("1")

    def test_cm_to_mm(self):
        """Test cm to mm conversion: 1 cm = 10 mm."""
        success, result, error = convert_from_base_units(Decimal("1"), "mm", "linear_cm")
        assert success is True
        assert error is None
        assert result == Decimal("10")


class TestAreaFromBaseConversions:
    """Test area unit conversions from square centimeters."""

    def test_square_cm_to_square_feet(self):
        """Test square cm to square feet: 929.0304 sq cm = 1 sq ft."""
        success, result, error = convert_from_base_units(
            Decimal("929.0304"), "square_feet", "square_cm"
        )
        assert success is True
        assert error is None
        assert result == Decimal("1")

    def test_square_cm_to_square_inches(self):
        """Test square cm to square inches: 6.4516 sq cm = 1 sq in."""
        success, result, error = convert_from_base_units(
            Decimal("6.4516"), "square_inches", "square_cm"
        )
        assert success is True
        assert error is None
        assert result == Decimal("1")

    def test_square_cm_to_square_meters(self):
        """Test square cm to square meters: 10000 sq cm = 1 sq m."""
        success, result, error = convert_from_base_units(
            Decimal("10000"), "square_meters", "square_cm"
        )
        assert success is True
        assert error is None
        assert result == Decimal("1")


# ============================================================================
# Direct Unit-to-Unit Conversion Tests
# ============================================================================


class TestDirectUnitConversions:
    """Test direct conversions between compatible units."""

    def test_feet_to_inches(self):
        """Test feet to inches: 1 foot = 12 inches."""
        success, result, error = convert_units(Decimal("1"), "feet", "inches")
        assert success is True
        assert error is None
        assert result == Decimal("12")

    def test_inches_to_feet(self):
        """Test inches to feet: 12 inches = 1 foot."""
        success, result, error = convert_units(Decimal("12"), "inches", "feet")
        assert success is True
        assert error is None
        assert result == Decimal("1")

    def test_yards_to_feet(self):
        """Test yards to feet: 1 yard = 3 feet."""
        success, result, error = convert_units(Decimal("1"), "yards", "feet")
        assert success is True
        assert error is None
        assert result == Decimal("3")

    def test_meters_to_mm(self):
        """Test meters to mm: 1 meter = 1000 mm."""
        success, result, error = convert_units(Decimal("1"), "meters", "mm")
        assert success is True
        assert error is None
        assert result == Decimal("1000")

    def test_square_feet_to_square_inches(self):
        """Test square feet to square inches: 1 sq ft = 144 sq in."""
        success, result, error = convert_units(Decimal("1"), "square_feet", "square_inches")
        assert success is True
        assert error is None
        assert result == Decimal("144")

    def test_same_unit_conversion(self):
        """Test converting to same unit returns original value."""
        success, result, error = convert_units(Decimal("5.5"), "feet", "feet")
        assert success is True
        assert error is None
        assert result == Decimal("5.5")


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestConversionErrors:
    """Test error handling in conversions."""

    def test_negative_quantity_to_base(self):
        """Test negative quantity error for to_base conversion."""
        success, result, error = convert_to_base_units(Decimal("-5"), "feet", "linear_cm")
        assert success is False
        assert result is None
        assert "negative" in error.lower()

    def test_negative_quantity_from_base(self):
        """Test negative quantity error for from_base conversion."""
        success, result, error = convert_from_base_units(Decimal("-5"), "feet", "linear_cm")
        assert success is False
        assert result is None
        assert "negative" in error.lower()

    def test_negative_quantity_direct(self):
        """Test negative quantity error for direct conversion."""
        success, result, error = convert_units(Decimal("-5"), "feet", "inches")
        assert success is False
        assert result is None
        assert "negative" in error.lower()

    def test_incompatible_linear_to_area(self):
        """Test linear to area conversion is rejected."""
        success, result, error = convert_units(Decimal("5"), "feet", "square_feet")
        assert success is False
        assert result is None
        assert "incompatible" in error.lower()

    def test_incompatible_area_to_linear(self):
        """Test area to linear conversion is rejected."""
        success, result, error = convert_units(Decimal("5"), "square_feet", "feet")
        assert success is False
        assert result is None
        assert "incompatible" in error.lower()

    def test_unknown_from_unit(self):
        """Test unknown source unit error."""
        success, result, error = convert_units(Decimal("5"), "unknown", "feet")
        assert success is False
        assert result is None
        assert "unknown unit" in error.lower()

    def test_unknown_to_unit(self):
        """Test unknown target unit error."""
        success, result, error = convert_units(Decimal("5"), "feet", "unknown")
        assert success is False
        assert result is None
        assert "unknown unit" in error.lower()


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_quantity(self):
        """Test zero quantity conversion."""
        success, result, error = convert_to_base_units(Decimal("0"), "feet", "linear_cm")
        assert success is True
        assert error is None
        assert result == Decimal("0")

    def test_very_large_quantity(self):
        """Test very large quantity conversion."""
        success, result, error = convert_to_base_units(Decimal("1000000"), "meters", "linear_cm")
        assert success is True
        assert error is None
        assert result == Decimal("100000000")  # 100 million cm

    def test_very_small_quantity(self):
        """Test very small quantity conversion."""
        success, result, error = convert_to_base_units(Decimal("0.001"), "inches", "linear_cm")
        assert success is True
        assert error is None
        assert result == Decimal("0.00254")

    def test_high_precision_decimal(self):
        """Test high precision decimal handling."""
        success, result, error = convert_to_base_units(Decimal("1.123456789"), "feet", "linear_cm")
        assert success is True
        assert error is None
        # 1.123456789 * 30.48 = 34.24279876472
        expected = Decimal("1.123456789") * Decimal("30.48")
        assert result == expected

    def test_round_trip_conversion(self):
        """Test round-trip conversion maintains precision."""
        original = Decimal("5.5")

        # Convert to base
        success, base, error = convert_to_base_units(original, "feet", "linear_cm")
        assert success is True

        # Convert back
        success, result, error = convert_from_base_units(base, "feet", "linear_cm")
        assert success is True
        assert result == original


# ============================================================================
# Conversion Factor Verification
# ============================================================================


class TestConversionFactors:
    """Verify conversion factors are correct per FR-011 to FR-014."""

    def test_linear_factors(self):
        """Verify linear conversion factors (FR-011, FR-012)."""
        assert LINEAR_TO_CM["feet"] == Decimal("30.48")
        assert LINEAR_TO_CM["inches"] == Decimal("2.54")
        assert LINEAR_TO_CM["yards"] == Decimal("91.44")
        assert LINEAR_TO_CM["meters"] == Decimal("100")
        assert LINEAR_TO_CM["mm"] == Decimal("0.1")
        assert LINEAR_TO_CM["cm"] == Decimal("1")

    def test_area_factors(self):
        """Verify area conversion factors (FR-013, FR-014)."""
        assert AREA_TO_SQUARE_CM["square_feet"] == Decimal("929.0304")
        assert AREA_TO_SQUARE_CM["square_inches"] == Decimal("6.4516")
        assert AREA_TO_SQUARE_CM["square_meters"] == Decimal("10000")
        assert AREA_TO_SQUARE_CM["square_cm"] == Decimal("1")

    def test_unit_types_complete(self):
        """Verify all expected units are in UNIT_TYPES."""
        # Linear units
        assert "feet" in UNIT_TYPES["linear_cm"]
        assert "inches" in UNIT_TYPES["linear_cm"]
        assert "yards" in UNIT_TYPES["linear_cm"]
        assert "meters" in UNIT_TYPES["linear_cm"]
        assert "mm" in UNIT_TYPES["linear_cm"]
        assert "cm" in UNIT_TYPES["linear_cm"]

        # Area units
        assert "square_feet" in UNIT_TYPES["square_cm"]
        assert "square_inches" in UNIT_TYPES["square_cm"]
        assert "square_meters" in UNIT_TYPES["square_cm"]
        assert "square_cm" in UNIT_TYPES["square_cm"]

        # Each units
        assert "each" in UNIT_TYPES["each"]
