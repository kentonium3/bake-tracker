"""
Unit tests for dropdown builder functions.

Tests cover:
- Product dropdown building with recency
- Ingredient dropdown building with recency
- Star prefix handling
- Separator handling
- Create-new option handling
"""

import pytest
from unittest.mock import patch, MagicMock

from src.ui.widgets.dropdown_builders import (
    build_product_dropdown_values,
    build_ingredient_dropdown_values,
    strip_star_prefix,
    is_separator,
    is_create_new_option,
    SEPARATOR,
    CREATE_NEW_OPTION,
    STAR_PREFIX,
)


# Mock Product and Ingredient classes for testing
class MockProduct:
    """Mock Product model."""

    # Class-level attribute to allow order_by(Product.brand)
    brand = "brand"

    def __init__(self, id: int, name: str, ingredient_id: int, is_hidden: bool = False):
        self.id = id
        self._name = name
        self.ingredient_id = ingredient_id
        self.is_hidden = is_hidden

    @property
    def display_name(self) -> str:
        """Return display name for the product."""
        return self._name


class MockIngredient:
    """Mock Ingredient model."""

    # Class-level attribute to allow order_by(Ingredient.display_name)
    display_name = "display_name"

    def __init__(self, id: int, display_name: str, category: str):
        self.id = id
        self.display_name = display_name
        self.category = category


class MockQuery:
    """Mock SQLAlchemy query."""

    def __init__(self, items, model_class=None):
        self._items = items
        self._model_class = model_class

    def filter_by(self, **kwargs):
        filtered = [
            item
            for item in self._items
            if all(getattr(item, k, None) == v for k, v in kwargs.items())
        ]
        return MockQuery(filtered, self._model_class)

    def order_by(self, *args):
        return MockQuery(self._items, self._model_class)

    def all(self):
        return self._items


class MockSession:
    """Mock database session."""

    def __init__(self, products=None, ingredients=None):
        self._products = products or []
        self._ingredients = ingredients or []

    def query(self, model):
        # Handle both real and mock model classes
        model_name = getattr(model, "__name__", str(model))
        if "Product" in model_name:
            return MockQuery(self._products, model)
        elif "Ingredient" in model_name:
            return MockQuery(self._ingredients, model)
        return MockQuery([], model)


class TestBuildProductDropdownValues:
    """Tests for build_product_dropdown_values function."""

    @patch("src.ui.widgets.dropdown_builders.get_recent_products")
    @patch("src.ui.widgets.dropdown_builders.Product", MockProduct)
    def test_empty_products_returns_create_option(self, mock_recency):
        """Empty product list should return only create option."""
        mock_recency.return_value = []
        session = MockSession(products=[])

        values = build_product_dropdown_values(999, session)

        assert values == [CREATE_NEW_OPTION]

    @patch("src.ui.widgets.dropdown_builders.get_recent_products")
    @patch("src.ui.widgets.dropdown_builders.Product", MockProduct)
    def test_recent_products_starred(self, mock_recency):
        """Recent products should have star prefix."""
        products = [
            MockProduct(1, "Product A", ingredient_id=10),
            MockProduct(2, "Product B", ingredient_id=10),
        ]
        mock_recency.return_value = [1]  # Product A is recent
        session = MockSession(products=products)

        values = build_product_dropdown_values(10, session)

        # First should be starred recent product
        assert values[0] == f"{STAR_PREFIX}Product A"
        # Non-recent should not have star
        assert "Product B" in values
        assert f"{STAR_PREFIX}Product B" not in values

    @patch("src.ui.widgets.dropdown_builders.get_recent_products")
    @patch("src.ui.widgets.dropdown_builders.Product", MockProduct)
    def test_separator_between_recent_and_other(self, mock_recency):
        """Separator should appear between recent and non-recent."""
        products = [
            MockProduct(1, "Recent Product", ingredient_id=10),
            MockProduct(2, "Other Product", ingredient_id=10),
        ]
        mock_recency.return_value = [1]
        session = MockSession(products=products)

        values = build_product_dropdown_values(10, session)

        # Should have separator between recent and other
        assert SEPARATOR in values
        star_idx = values.index(f"{STAR_PREFIX}Recent Product")
        sep_idx = values.index(SEPARATOR)
        other_idx = values.index("Other Product")

        assert star_idx < sep_idx < other_idx

    @patch("src.ui.widgets.dropdown_builders.get_recent_products")
    @patch("src.ui.widgets.dropdown_builders.Product", MockProduct)
    def test_create_option_always_last(self, mock_recency):
        """Create option should always be last."""
        products = [
            MockProduct(1, "Product A", ingredient_id=10),
            MockProduct(2, "Product B", ingredient_id=10),
        ]
        mock_recency.return_value = [1]
        session = MockSession(products=products)

        values = build_product_dropdown_values(10, session)

        assert values[-1] == CREATE_NEW_OPTION

    @patch("src.ui.widgets.dropdown_builders.get_recent_products")
    @patch("src.ui.widgets.dropdown_builders.Product", MockProduct)
    def test_no_recent_all_alphabetical(self, mock_recency):
        """With no recent, products should be alphabetical."""
        products = [
            MockProduct(1, "Zebra Brand", ingredient_id=10),
            MockProduct(2, "Alpha Brand", ingredient_id=10),
        ]
        mock_recency.return_value = []
        session = MockSession(products=products)

        values = build_product_dropdown_values(10, session)

        # No starred items
        assert not any(v.startswith(STAR_PREFIX) for v in values if v != CREATE_NEW_OPTION)
        # Create option at end
        assert values[-1] == CREATE_NEW_OPTION

    @patch("src.ui.widgets.dropdown_builders.get_recent_products")
    @patch("src.ui.widgets.dropdown_builders.Product", MockProduct)
    def test_all_recent_no_separator_before_others(self, mock_recency):
        """If all products recent, no separator between them."""
        products = [
            MockProduct(1, "Product A", ingredient_id=10),
            MockProduct(2, "Product B", ingredient_id=10),
        ]
        mock_recency.return_value = [1, 2]  # Both recent
        session = MockSession(products=products)

        values = build_product_dropdown_values(10, session)

        # Should have one separator (before create option)
        separator_count = values.count(SEPARATOR)
        assert separator_count == 1


class TestBuildIngredientDropdownValues:
    """Tests for build_ingredient_dropdown_values function."""

    @patch("src.ui.widgets.dropdown_builders.get_recent_ingredients")
    @patch("src.ui.widgets.dropdown_builders.Ingredient", MockIngredient)
    def test_empty_ingredients_returns_empty(self, mock_recency):
        """Empty ingredient list should return empty list."""
        mock_recency.return_value = []
        session = MockSession(ingredients=[])

        values = build_ingredient_dropdown_values("Flour", session)

        assert values == []

    @patch("src.ui.widgets.dropdown_builders.get_recent_ingredients")
    @patch("src.ui.widgets.dropdown_builders.Ingredient", MockIngredient)
    def test_recent_ingredients_starred(self, mock_recency):
        """Recent ingredients should have star prefix."""
        ingredients = [
            MockIngredient(1, "All-Purpose Flour", "Flour"),
            MockIngredient(2, "Bread Flour", "Flour"),
        ]
        mock_recency.return_value = [1]  # All-Purpose is recent
        session = MockSession(ingredients=ingredients)

        values = build_ingredient_dropdown_values("Flour", session)

        assert f"{STAR_PREFIX}All-Purpose Flour" in values
        assert "Bread Flour" in values
        assert f"{STAR_PREFIX}Bread Flour" not in values

    @patch("src.ui.widgets.dropdown_builders.get_recent_ingredients")
    @patch("src.ui.widgets.dropdown_builders.Ingredient", MockIngredient)
    def test_no_create_option_for_ingredients(self, mock_recency):
        """Ingredients should NOT have create option."""
        ingredients = [
            MockIngredient(1, "All-Purpose Flour", "Flour"),
        ]
        mock_recency.return_value = []
        session = MockSession(ingredients=ingredients)

        values = build_ingredient_dropdown_values("Flour", session)

        assert CREATE_NEW_OPTION not in values


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_strip_star_prefix_with_star(self):
        """strip_star_prefix removes star from starred value."""
        assert strip_star_prefix(f"{STAR_PREFIX}Product Name") == "Product Name"

    def test_strip_star_prefix_without_star(self):
        """strip_star_prefix returns value unchanged if no star."""
        assert strip_star_prefix("Product Name") == "Product Name"

    def test_is_separator_true(self):
        """is_separator returns True for separator."""
        assert is_separator(SEPARATOR) is True

    def test_is_separator_false(self):
        """is_separator returns False for non-separator."""
        assert is_separator("Product Name") is False
        assert is_separator("") is False

    def test_is_create_new_option_true(self):
        """is_create_new_option returns True for create option."""
        assert is_create_new_option(CREATE_NEW_OPTION) is True

    def test_is_create_new_option_false(self):
        """is_create_new_option returns False for non-create option."""
        assert is_create_new_option("Product Name") is False
        assert is_create_new_option("") is False


class TestConstants:
    """Tests for module constants."""

    def test_separator_is_visible_line(self):
        """Separator should be a visible line character."""
        assert len(SEPARATOR) > 10
        assert "─" in SEPARATOR

    def test_create_option_format(self):
        """Create option should have expected format."""
        assert CREATE_NEW_OPTION.startswith("[+")
        assert "Create New" in CREATE_NEW_OPTION
        assert CREATE_NEW_OPTION.endswith("]")

    def test_star_prefix_has_star(self):
        """Star prefix should contain star emoji."""
        assert "⭐" in STAR_PREFIX
