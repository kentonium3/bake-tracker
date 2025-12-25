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
    """Tests for known category defaults.

    Categories match INGREDIENT_CATEGORIES from constants.py.
    """

    def test_flour_defaults_to_lb(self):
        """Flour should default to lb (bulk purchases)."""
        assert get_default_unit_for_category("Flour") == "lb"

    def test_sugar_defaults_to_lb(self):
        """Sugar should default to lb."""
        assert get_default_unit_for_category("Sugar") == "lb"

    def test_dairy_defaults_to_lb(self):
        """Dairy (butter, cheese) should default to lb."""
        assert get_default_unit_for_category("Dairy") == "lb"

    def test_oils_butters_defaults_to_fl_oz(self):
        """Oils/Butters should default to fl oz."""
        assert get_default_unit_for_category("Oils/Butters") == "fl oz"

    def test_nuts_defaults_to_lb(self):
        """Nuts should default to lb."""
        assert get_default_unit_for_category("Nuts") == "lb"

    def test_spices_defaults_to_oz(self):
        """Spices should default to oz (small quantities)."""
        assert get_default_unit_for_category("Spices") == "oz"

    def test_chocolate_candies_defaults_to_oz(self):
        """Chocolate/Candies (chips, bars) should default to oz."""
        assert get_default_unit_for_category("Chocolate/Candies") == "oz"

    def test_cocoa_powders_defaults_to_oz(self):
        """Cocoa Powders should default to oz."""
        assert get_default_unit_for_category("Cocoa Powders") == "oz"

    def test_dried_fruits_defaults_to_lb(self):
        """Dried Fruits should default to lb."""
        assert get_default_unit_for_category("Dried Fruits") == "lb"

    def test_extracts_defaults_to_fl_oz(self):
        """Extracts should default to fl oz."""
        assert get_default_unit_for_category("Extracts") == "fl oz"

    def test_syrups_defaults_to_fl_oz(self):
        """Syrups should default to fl oz."""
        assert get_default_unit_for_category("Syrups") == "fl oz"

    def test_alcohol_defaults_to_fl_oz(self):
        """Alcohol should default to fl oz."""
        assert get_default_unit_for_category("Alcohol") == "fl oz"

    def test_misc_defaults_to_lb(self):
        """Misc should default to lb."""
        assert get_default_unit_for_category("Misc") == "lb"

    def test_bags_defaults_to_count(self):
        """Bags (packaging) should default to count."""
        assert get_default_unit_for_category("Bags") == "count"

    def test_boxes_defaults_to_count(self):
        """Boxes (packaging) should default to count."""
        assert get_default_unit_for_category("Boxes") == "count"


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
        """Mapping should have 20 categories (13 food + 7 packaging)."""
        assert len(CATEGORY_DEFAULT_UNITS) == 20


class MockIngredient:
    """Mock ingredient for testing get_default_unit_for_ingredient."""

    def __init__(self, category: str):
        self.category = category


class TestIngredientWrapper:
    """Tests for the ingredient wrapper function."""

    def test_ingredient_wrapper_flour(self):
        """Wrapper should work with Flour category ingredient."""
        ingredient = MockIngredient("Flour")
        assert get_default_unit_for_ingredient(ingredient) == "lb"

    def test_ingredient_wrapper_chocolate_candies(self):
        """Wrapper should work with Chocolate/Candies category ingredient."""
        ingredient = MockIngredient("Chocolate/Candies")
        assert get_default_unit_for_ingredient(ingredient) == "oz"

    def test_ingredient_wrapper_unknown(self):
        """Wrapper should fall back for unknown category ingredient."""
        ingredient = MockIngredient("Unknown")
        assert get_default_unit_for_ingredient(ingredient) == "lb"

    def test_ingredient_wrapper_extracts(self):
        """Wrapper should work with Extracts category ingredient."""
        ingredient = MockIngredient("Extracts")
        assert get_default_unit_for_ingredient(ingredient) == "fl oz"
