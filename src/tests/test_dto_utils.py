"""Tests for DTO utility functions."""

import pytest
from decimal import Decimal

from src.services.dto_utils import cost_to_string


class TestCostToString:
    """Tests for cost_to_string function."""

    def test_none_returns_zero(self):
        """None value returns '0.00'."""
        assert cost_to_string(None) == "0.00"

    def test_decimal_value(self):
        """Decimal values are formatted correctly."""
        assert cost_to_string(Decimal("12.34")) == "12.34"
        assert cost_to_string(Decimal("0")) == "0.00"
        assert cost_to_string(Decimal("100")) == "100.00"

    def test_decimal_rounding(self):
        """Decimal values are rounded to 2 places using ROUND_HALF_UP."""
        assert cost_to_string(Decimal("12.345")) == "12.35"  # Round up
        assert cost_to_string(Decimal("12.344")) == "12.34"  # Round down
        assert cost_to_string(Decimal("12.3449")) == "12.34"  # Round down
        assert cost_to_string(Decimal("12.3450")) == "12.35"  # Round up at .5

    def test_float_value(self):
        """Float values are formatted correctly."""
        assert cost_to_string(12.34) == "12.34"
        assert cost_to_string(12.3) == "12.30"
        assert cost_to_string(12.0) == "12.00"

    def test_int_value(self):
        """Integer values are formatted with decimals."""
        assert cost_to_string(12) == "12.00"
        assert cost_to_string(0) == "0.00"
        assert cost_to_string(100) == "100.00"

    def test_string_value(self):
        """String numeric values are parsed and formatted."""
        assert cost_to_string("12.34") == "12.34"
        assert cost_to_string("15.999") == "16.00"
        assert cost_to_string("0") == "0.00"

    def test_negative_values(self):
        """Negative values are handled correctly."""
        assert cost_to_string(Decimal("-12.34")) == "-12.34"
        assert cost_to_string(-12.345) == "-12.35"

    def test_large_values(self):
        """Large values are formatted correctly."""
        assert cost_to_string(Decimal("999999.99")) == "999999.99"
        assert cost_to_string(1234567.89) == "1234567.89"

    def test_return_type_is_string(self):
        """Return value is always a string."""
        result = cost_to_string(Decimal("12.34"))
        assert isinstance(result, str)

        result = cost_to_string(12.34)
        assert isinstance(result, str)

        result = cost_to_string(None)
        assert isinstance(result, str)

    def test_json_serializable(self):
        """Result can be JSON serialized."""
        import json

        result = cost_to_string(Decimal("12.34"))
        # Should not raise
        json.dumps({"cost": result})
