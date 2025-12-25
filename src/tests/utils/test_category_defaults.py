"""
Unit tests for category defaults utility.

Tests verify:
- Known categories return expected default units
- Unknown categories fall back to 'lb'
- Ingredient wrapper function works correctly
- All mapped categories have valid values
"""

import pytest

from src.utils.category_defaults import (
    CATEGORY_DEFAULT_UNITS,
    get_default_unit_for_category,
    get_default_unit_for_ingredient,
)


class TestKnownCategories:
    """Tests for known category defaults."""

    def test_baking_defaults_to_lb(self):
        """Baking ingredients (flour, sugar) should default to lb."""
        assert get_default_unit_for_category("Baking") == "lb"

    def test_chocolate_defaults_to_oz(self):
        """Chocolate (chips, bars) should default to oz."""
        assert get_default_unit_for_category("Chocolate") == "oz"

    def test_dairy_defaults_to_lb(self):
        """Dairy (butter) should default to lb."""
        assert get_default_unit_for_category("Dairy") == "lb"

    def test_spices_defaults_to_oz(self):
        """Spices should default to oz (small quantities)."""
        assert get_default_unit_for_category("Spices") == "oz"

    def test_liquids_defaults_to_fl_oz(self):
        """Liquids (extracts) should default to fl oz."""
        assert get_default_unit_for_category("Liquids") == "fl oz"

    def test_nuts_defaults_to_lb(self):
        """Nuts should default to lb."""
        assert get_default_unit_for_category("Nuts") == "lb"

    def test_fruits_defaults_to_lb(self):
        """Fruits (dried) should default to lb."""
        assert get_default_unit_for_category("Fruits") == "lb"

    def test_sweeteners_defaults_to_lb(self):
        """Sweeteners (honey, syrups) should default to lb."""
        assert get_default_unit_for_category("Sweeteners") == "lb"

    def test_leavening_defaults_to_oz(self):
        """Leavening (baking powder) should default to oz."""
        assert get_default_unit_for_category("Leavening") == "oz"

    def test_oils_defaults_to_fl_oz(self):
        """Oils should default to fl oz."""
        assert get_default_unit_for_category("Oils") == "fl oz"

    def test_grains_defaults_to_lb(self):
        """Grains (oats) should default to lb."""
        assert get_default_unit_for_category("Grains") == "lb"


class TestUnknownCategories:
    """Tests for fallback behavior with unknown categories."""

    def test_unknown_category_falls_back_to_lb(self):
        """Unknown category should return 'lb' as fallback."""
        assert get_default_unit_for_category("UnknownCategory") == "lb"

    def test_empty_category_falls_back_to_lb(self):
        """Empty string category should return 'lb' as fallback."""
        assert get_default_unit_for_category("") == "lb"

    def test_none_like_category_falls_back_to_lb(self):
        """Category that looks like None string should return 'lb'."""
        assert get_default_unit_for_category("None") == "lb"

    def test_case_sensitivity(self):
        """Category matching should be case-sensitive (lowercase fails)."""
        assert get_default_unit_for_category("baking") == "lb"  # Falls back
        assert get_default_unit_for_category("BAKING") == "lb"  # Falls back


class TestMappingIntegrity:
    """Tests for the mapping dictionary itself."""

    def test_all_mapped_categories_have_values(self):
        """All mapped categories should have non-empty unit strings."""
        for category, unit in CATEGORY_DEFAULT_UNITS.items():
            assert unit, f"Category {category} has empty unit"
            assert isinstance(unit, str), f"Category {category} unit is not string"

    def test_mapping_has_expected_count(self):
        """Mapping should have 11 categories."""
        assert len(CATEGORY_DEFAULT_UNITS) == 11


class MockIngredient:
    """Mock ingredient for testing get_default_unit_for_ingredient."""

    def __init__(self, category: str):
        self.category = category


class TestIngredientWrapper:
    """Tests for the ingredient wrapper function."""

    def test_ingredient_wrapper_baking(self):
        """Wrapper should work with Baking category ingredient."""
        ingredient = MockIngredient("Baking")
        assert get_default_unit_for_ingredient(ingredient) == "lb"

    def test_ingredient_wrapper_chocolate(self):
        """Wrapper should work with Chocolate category ingredient."""
        ingredient = MockIngredient("Chocolate")
        assert get_default_unit_for_ingredient(ingredient) == "oz"

    def test_ingredient_wrapper_unknown(self):
        """Wrapper should fall back for unknown category ingredient."""
        ingredient = MockIngredient("Unknown")
        assert get_default_unit_for_ingredient(ingredient) == "lb"

    def test_ingredient_wrapper_liquids(self):
        """Wrapper should work with Liquids category ingredient."""
        ingredient = MockIngredient("Liquids")
        assert get_default_unit_for_ingredient(ingredient) == "fl oz"
