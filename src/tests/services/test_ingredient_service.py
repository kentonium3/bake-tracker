"""
Tests for Ingredient Service density validation.

Tests cover:
- validate_density_fields() all-or-nothing validation
- Positive value validation
- Unit validation
"""

import pytest

from src.services.ingredient_service import validate_density_fields


class TestValidateDensityFields:
    """Tests for density field validation."""

    def test_validate_density_fields_all_empty(self):
        """Empty density fields are valid."""
        is_valid, error = validate_density_fields(None, None, None, None)
        assert is_valid
        assert error == ""

    def test_validate_density_fields_all_filled(self):
        """All density fields filled with valid data."""
        is_valid, error = validate_density_fields(1.0, "cup", 4.25, "oz")
        assert is_valid
        assert error == ""

    def test_validate_density_fields_partial_volume_only(self):
        """Partial density fields (volume only) fail validation."""
        is_valid, error = validate_density_fields(1.0, "cup", None, None)
        assert not is_valid
        assert "All density fields must be provided together" in error

    def test_validate_density_fields_partial_weight_only(self):
        """Partial density fields (weight only) fail validation."""
        is_valid, error = validate_density_fields(None, None, 4.25, "oz")
        assert not is_valid
        assert "All density fields must be provided together" in error

    def test_validate_density_fields_partial_missing_unit(self):
        """Partial density fields (missing unit) fail validation."""
        is_valid, error = validate_density_fields(1.0, None, 4.25, "oz")
        assert not is_valid
        assert "All density fields must be provided together" in error

    def test_validate_density_fields_zero_volume(self):
        """Zero volume value fails validation."""
        is_valid, error = validate_density_fields(0, "cup", 4.25, "oz")
        assert not is_valid
        # Zero is treated as "not filled" so it's a partial fill error
        assert "All density fields must be provided together" in error

    def test_validate_density_fields_negative_volume(self):
        """Negative volume value fails validation."""
        is_valid, error = validate_density_fields(-1.0, "cup", 4.25, "oz")
        assert not is_valid
        assert "greater than zero" in error

    def test_validate_density_fields_negative_weight(self):
        """Negative weight value fails validation."""
        is_valid, error = validate_density_fields(1.0, "cup", -1.0, "oz")
        assert not is_valid
        assert "greater than zero" in error

    def test_validate_density_fields_invalid_volume_unit(self):
        """Invalid volume unit fails validation."""
        is_valid, error = validate_density_fields(1.0, "invalid", 4.25, "oz")
        assert not is_valid
        assert "Invalid volume unit" in error

    def test_validate_density_fields_invalid_weight_unit(self):
        """Invalid weight unit fails validation."""
        is_valid, error = validate_density_fields(1.0, "cup", 4.25, "invalid")
        assert not is_valid
        assert "Invalid weight unit" in error

    def test_validate_density_fields_weight_unit_as_volume(self):
        """Using weight unit in volume field fails validation."""
        is_valid, error = validate_density_fields(1.0, "oz", 4.25, "oz")
        assert not is_valid
        assert "Invalid volume unit" in error

    def test_validate_density_fields_volume_unit_as_weight(self):
        """Using volume unit in weight field fails validation."""
        is_valid, error = validate_density_fields(1.0, "cup", 4.25, "cup")
        assert not is_valid
        assert "Invalid weight unit" in error

    def test_validate_density_fields_empty_string_treated_as_none(self):
        """Empty strings are treated as None."""
        is_valid, error = validate_density_fields("", "", "", "")
        assert is_valid  # All empty is valid
        assert error == ""

    def test_validate_density_fields_mixed_empty_string(self):
        """Mixed empty strings are treated as partial."""
        is_valid, error = validate_density_fields(1.0, "", 4.25, "oz")
        assert not is_valid
        assert "All density fields must be provided together" in error

    def test_validate_density_fields_all_valid_units(self):
        """Test various valid unit combinations."""
        valid_combos = [
            (1.0, "cup", 4.25, "oz"),
            (1.0, "tbsp", 14.0, "g"),
            (1.0, "ml", 1.0, "g"),
            (1.0, "tsp", 5.0, "g"),
            (1.0, "l", 1000.0, "kg"),
        ]
        for vol_val, vol_unit, wt_val, wt_unit in valid_combos:
            is_valid, error = validate_density_fields(vol_val, vol_unit, wt_val, wt_unit)
            assert is_valid, f"Expected valid: {vol_val} {vol_unit} = {wt_val} {wt_unit}, got error: {error}"

    def test_validate_density_fields_case_insensitive(self):
        """Unit validation is case insensitive."""
        is_valid, error = validate_density_fields(1.0, "CUP", 4.25, "OZ")
        assert is_valid
        assert error == ""
