"""
Tests for Ingredient model density methods.

Tests cover:
- get_density_g_per_ml() calculation
- format_density_display() formatting
- Edge cases (missing fields, zero values, invalid units)
"""

import pytest

from src.models.ingredient import Ingredient


class TestIngredientDensity:
    """Tests for Ingredient density calculation methods."""

    def test_get_density_g_per_ml_with_valid_fields(self):
        """Test density calculation with all fields set."""
        ingredient = Ingredient(
            name="Test Flour",
            slug="test-flour",
            category="Flour",
            density_volume_value=1.0,
            density_volume_unit="cup",
            density_weight_value=4.25,
            density_weight_unit="oz",
        )
        density = ingredient.get_density_g_per_ml()
        assert density is not None
        # 1 cup = 236.588 ml, 4.25 oz = 120.49 g
        # Expected: ~0.509 g/ml
        assert abs(density - 0.509) < 0.01

    def test_get_density_g_per_ml_without_fields(self):
        """Test that missing density fields return None."""
        ingredient = Ingredient(
            name="Test",
            slug="test",
            category="Flour",
        )
        assert ingredient.get_density_g_per_ml() is None

    def test_get_density_g_per_ml_partial_fields_volume_only(self):
        """Test that partial density fields (volume only) return None."""
        ingredient = Ingredient(
            name="Test",
            slug="test",
            category="Flour",
            density_volume_value=1.0,
            density_volume_unit="cup",
            # weight fields missing
        )
        assert ingredient.get_density_g_per_ml() is None

    def test_get_density_g_per_ml_partial_fields_weight_only(self):
        """Test that partial density fields (weight only) return None."""
        ingredient = Ingredient(
            name="Test",
            slug="test",
            category="Flour",
            # volume fields missing
            density_weight_value=4.25,
            density_weight_unit="oz",
        )
        assert ingredient.get_density_g_per_ml() is None

    def test_get_density_g_per_ml_partial_fields_missing_units(self):
        """Test that partial density fields (missing units) return None."""
        ingredient = Ingredient(
            name="Test",
            slug="test",
            category="Flour",
            density_volume_value=1.0,
            # density_volume_unit missing
            density_weight_value=4.25,
            density_weight_unit="oz",
        )
        assert ingredient.get_density_g_per_ml() is None

    def test_get_density_g_per_ml_with_grams_and_ml(self):
        """Test density calculation with grams and milliliters."""
        ingredient = Ingredient(
            name="Water",
            slug="water",
            category="Liquid",
            density_volume_value=100.0,
            density_volume_unit="ml",
            density_weight_value=100.0,
            density_weight_unit="g",
        )
        density = ingredient.get_density_g_per_ml()
        assert density is not None
        # 100ml water = 100g -> 1.0 g/ml
        assert abs(density - 1.0) < 0.001

    def test_get_density_g_per_ml_with_tablespoons(self):
        """Test density calculation with tablespoons."""
        ingredient = Ingredient(
            name="Honey",
            slug="honey",
            category="Sweetener",
            density_volume_value=1.0,
            density_volume_unit="tbsp",
            density_weight_value=21.0,
            density_weight_unit="g",
        )
        density = ingredient.get_density_g_per_ml()
        assert density is not None
        # 1 tbsp = 14.787 ml, 21g / 14.787ml = ~1.42 g/ml
        assert abs(density - 1.42) < 0.02

    def test_format_density_display(self):
        """Test user-friendly density formatting."""
        ingredient = Ingredient(
            name="Test",
            slug="test",
            category="Flour",
            density_volume_value=1.0,
            density_volume_unit="cup",
            density_weight_value=4.25,
            density_weight_unit="oz",
        )
        assert ingredient.format_density_display() == "1 cup = 4.25 oz"

    def test_format_density_display_not_set(self):
        """Test format when density not set."""
        ingredient = Ingredient(name="Test", slug="test", category="Flour")
        assert ingredient.format_density_display() == "Not set"

    def test_format_density_display_strips_trailing_zeros(self):
        """Test that format strips trailing zeros."""
        ingredient = Ingredient(
            name="Test",
            slug="test",
            category="Flour",
            density_volume_value=1.0,  # Should display as "1"
            density_volume_unit="cup",
            density_weight_value=120.0,  # Should display as "120"
            density_weight_unit="g",
        )
        assert ingredient.format_density_display() == "1 cup = 120 g"

    def test_format_density_display_partial_fields(self):
        """Test format when only some density fields set."""
        ingredient = Ingredient(
            name="Test",
            slug="test",
            category="Flour",
            density_volume_value=1.0,
            density_volume_unit="cup",
            # weight fields missing - density calculation returns None
        )
        assert ingredient.format_density_display() == "Not set"
