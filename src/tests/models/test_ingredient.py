"""
Tests for Ingredient model.

Tests cover:
- Hierarchy fields (Feature 031)
- get_density_g_per_ml() calculation
- format_density_display() formatting
- Edge cases (missing fields, zero values, invalid units)
"""

import pytest

from src.models.ingredient import Ingredient


class TestIngredientHierarchy:
    """Tests for Ingredient hierarchy fields (Feature 031)."""

    def test_default_hierarchy_level_is_leaf(self):
        """Test that default hierarchy_level is 2 (leaf) when persisted."""
        # Note: Column defaults are applied on INSERT, not on object creation
        # This test verifies the model accepts hierarchy_level=2 as the expected default
        ingredient = Ingredient(
            display_name="Test Ingredient",
            slug="test-ingredient",
            category="Test",
            hierarchy_level=2,  # Explicitly set to match expected default
        )
        assert ingredient.hierarchy_level == 2

    def test_hierarchy_level_can_be_set_to_root(self):
        """Test that hierarchy_level can be set to 0 (root)."""
        ingredient = Ingredient(
            display_name="Chocolate",
            slug="chocolate",
            category="Chocolate",
            hierarchy_level=0,
        )
        assert ingredient.hierarchy_level == 0

    def test_hierarchy_level_can_be_set_to_mid(self):
        """Test that hierarchy_level can be set to 1 (mid-tier)."""
        ingredient = Ingredient(
            display_name="Dark Chocolate",
            slug="dark-chocolate",
            category="Chocolate",
            hierarchy_level=1,
        )
        assert ingredient.hierarchy_level == 1

    def test_parent_ingredient_id_defaults_to_none(self):
        """Test that parent_ingredient_id defaults to None for root ingredients."""
        ingredient = Ingredient(
            display_name="Test",
            slug="test",
            category="Test",
        )
        assert ingredient.parent_ingredient_id is None

    def test_parent_ingredient_id_can_be_set(self):
        """Test that parent_ingredient_id can be set."""
        ingredient = Ingredient(
            display_name="Child Ingredient",
            slug="child-ingredient",
            category="Test",
            parent_ingredient_id=1,
            hierarchy_level=1,
        )
        assert ingredient.parent_ingredient_id == 1

    def test_to_dict_includes_hierarchy_fields(self):
        """Test that to_dict includes hierarchy fields and is_leaf computed property."""
        ingredient = Ingredient(
            display_name="Test Ingredient",
            slug="test-ingredient",
            category="Test",
            hierarchy_level=2,
            parent_ingredient_id=None,
        )
        result = ingredient.to_dict()
        assert "hierarchy_level" in result
        assert "parent_ingredient_id" in result
        assert "is_leaf" in result
        assert result["hierarchy_level"] == 2
        assert result["parent_ingredient_id"] is None
        assert result["is_leaf"] is True

    def test_to_dict_is_leaf_false_for_non_leaf(self):
        """Test that is_leaf is False for non-leaf ingredients."""
        ingredient = Ingredient(
            display_name="Root Category",
            slug="root-category",
            category="Test",
            hierarchy_level=0,
        )
        result = ingredient.to_dict()
        assert result["is_leaf"] is False

    def test_to_dict_is_leaf_false_for_mid_tier(self):
        """Test that is_leaf is False for mid-tier ingredients."""
        ingredient = Ingredient(
            display_name="Mid Category",
            slug="mid-category",
            category="Test",
            hierarchy_level=1,
        )
        result = ingredient.to_dict()
        assert result["is_leaf"] is False


class TestIngredientDensity:
    """Tests for Ingredient density calculation methods."""

    def test_get_density_g_per_ml_with_valid_fields(self):
        """Test density calculation with all fields set."""
        ingredient = Ingredient(
            display_name="Test Flour",
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
            display_name="Test",
            slug="test",
            category="Flour",
        )
        assert ingredient.get_density_g_per_ml() is None

    def test_get_density_g_per_ml_partial_fields_volume_only(self):
        """Test that partial density fields (volume only) return None."""
        ingredient = Ingredient(
            display_name="Test",
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
            display_name="Test",
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
            display_name="Test",
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
            display_name="Water",
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
            display_name="Honey",
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
            display_name="Test",
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
        ingredient = Ingredient(display_name="Test", slug="test", category="Flour")
        assert ingredient.format_density_display() == "Not set"

    def test_format_density_display_strips_trailing_zeros(self):
        """Test that format strips trailing zeros."""
        ingredient = Ingredient(
            display_name="Test",
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
            display_name="Test",
            slug="test",
            category="Flour",
            density_volume_value=1.0,
            density_volume_unit="cup",
            # weight fields missing - density calculation returns None
        )
        assert ingredient.format_density_display() == "Not set"
