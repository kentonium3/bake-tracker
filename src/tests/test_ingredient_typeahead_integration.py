"""
Tests for ingredient type-ahead integration in the recipe form.

Tests the search callback wrapper and breadcrumb formatting without
requiring a full UI (no tkinter needed for callback-only tests).
"""

from unittest.mock import MagicMock, patch

import pytest


class TestSearchCallbackWrapper:
    """Test the ingredient search callback used by TypeAheadEntry."""

    @patch("src.services.ingredient_hierarchy_service.search_ingredients")
    def test_returns_matching_results(self, mock_search):
        """Callback returns results from search_ingredients service."""
        mock_search.return_value = [
            {
                "id": 1,
                "display_name": "Chocolate Chips",
                "slug": "chocolate-chips",
                "hierarchy_level": 2,
                "ancestors": [
                    {"id": 10, "display_name": "Chocolate"},
                    {"id": 100, "display_name": "Baking"},
                ],
            }
        ]
        from src.ui.forms.recipe_form import IngredientSelectionDialog

        # Call the callback as a standalone function (no UI needed)
        results = IngredientSelectionDialog._search_ingredients_for_typeahead(
            None, "choc"
        )
        assert len(results) == 1
        assert results[0]["display_name"] == "Chocolate Chips"
        mock_search.assert_called_once_with("choc", limit=10)

    @patch("src.services.ingredient_hierarchy_service.search_ingredients")
    def test_filters_to_leaf_only(self, mock_search):
        """Callback filters out non-leaf ingredients."""
        mock_search.return_value = [
            {
                "id": 100,
                "display_name": "Baking",
                "slug": "baking",
                "hierarchy_level": 0,
                "ancestors": [],
            },
            {
                "id": 10,
                "display_name": "Chocolate",
                "slug": "chocolate",
                "hierarchy_level": 1,
                "ancestors": [{"id": 100, "display_name": "Baking"}],
            },
            {
                "id": 1,
                "display_name": "Chocolate Chips",
                "slug": "chocolate-chips",
                "hierarchy_level": 2,
                "ancestors": [
                    {"id": 10, "display_name": "Chocolate"},
                    {"id": 100, "display_name": "Baking"},
                ],
            },
        ]
        from src.ui.forms.recipe_form import IngredientSelectionDialog

        results = IngredientSelectionDialog._search_ingredients_for_typeahead(
            None, "choc"
        )
        # Only leaf (hierarchy_level >= 2) should be returned
        assert len(results) == 1
        assert results[0]["display_name"] == "Chocolate Chips"

    @patch("src.services.ingredient_hierarchy_service.search_ingredients")
    def test_breadcrumb_formatting_with_ancestors(self, mock_search):
        """Display shows breadcrumb trail from root to parent."""
        mock_search.return_value = [
            {
                "id": 1,
                "display_name": "Semi-Sweet Chocolate Chips",
                "slug": "semi-sweet-chocolate-chips",
                "hierarchy_level": 2,
                "ancestors": [
                    {"id": 10, "display_name": "Chocolate"},
                    {"id": 100, "display_name": "Baking"},
                ],
            },
        ]
        from src.ui.forms.recipe_form import IngredientSelectionDialog

        results = IngredientSelectionDialog._search_ingredients_for_typeahead(
            None, "semi"
        )
        assert len(results) == 1
        # Ancestors are ordered parent-to-root, so reversed = root-to-parent
        expected = "Semi-Sweet Chocolate Chips  (Baking > Chocolate)"
        assert results[0]["typeahead_display"] == expected

    @patch("src.services.ingredient_hierarchy_service.search_ingredients")
    def test_breadcrumb_no_ancestors(self, mock_search):
        """Root-level ingredients show just the name (no breadcrumb suffix)."""
        mock_search.return_value = [
            {
                "id": 1,
                "display_name": "Salt",
                "slug": "salt",
                "hierarchy_level": 2,
                "ancestors": [],
            },
        ]
        from src.ui.forms.recipe_form import IngredientSelectionDialog

        results = IngredientSelectionDialog._search_ingredients_for_typeahead(
            None, "salt"
        )
        assert results[0]["typeahead_display"] == "Salt"

    @patch("src.services.ingredient_hierarchy_service.search_ingredients")
    def test_single_ancestor_breadcrumb(self, mock_search):
        """Single ancestor shows one-level breadcrumb."""
        mock_search.return_value = [
            {
                "id": 1,
                "display_name": "Granulated Sugar",
                "slug": "granulated-sugar",
                "hierarchy_level": 2,
                "ancestors": [{"id": 100, "display_name": "Sweeteners"}],
            },
        ]
        from src.ui.forms.recipe_form import IngredientSelectionDialog

        results = IngredientSelectionDialog._search_ingredients_for_typeahead(
            None, "sugar"
        )
        assert results[0]["typeahead_display"] == "Granulated Sugar  (Sweeteners)"

    @patch("src.services.ingredient_hierarchy_service.search_ingredients")
    def test_preserves_original_display_name(self, mock_search):
        """Original display_name is preserved for downstream use."""
        mock_search.return_value = [
            {
                "id": 1,
                "display_name": "Chocolate Chips",
                "slug": "chocolate-chips",
                "hierarchy_level": 2,
                "ancestors": [
                    {"id": 10, "display_name": "Chocolate"},
                    {"id": 100, "display_name": "Baking"},
                ],
            },
        ]
        from src.ui.forms.recipe_form import IngredientSelectionDialog

        results = IngredientSelectionDialog._search_ingredients_for_typeahead(
            None, "choc"
        )
        # Original display_name unmodified
        assert results[0]["display_name"] == "Chocolate Chips"
        # typeahead_display has breadcrumbs
        assert results[0]["typeahead_display"] == "Chocolate Chips  (Baking > Chocolate)"

    @patch("src.services.ingredient_hierarchy_service.search_ingredients")
    def test_callback_handles_service_error(self, mock_search):
        """Callback returns empty list on service error."""
        mock_search.side_effect = RuntimeError("DB error")
        from src.ui.forms.recipe_form import IngredientSelectionDialog

        results = IngredientSelectionDialog._search_ingredients_for_typeahead(
            None, "choc"
        )
        assert results == []

    @patch("src.services.ingredient_hierarchy_service.search_ingredients")
    def test_empty_results(self, mock_search):
        """Callback returns empty list when no matches."""
        mock_search.return_value = []
        from src.ui.forms.recipe_form import IngredientSelectionDialog

        results = IngredientSelectionDialog._search_ingredients_for_typeahead(
            None, "xyz"
        )
        assert results == []

    @patch("src.services.ingredient_hierarchy_service.search_ingredients")
    def test_special_characters_in_query(self, mock_search):
        """Special characters passed through to service unchanged."""
        mock_search.return_value = []
        from src.ui.forms.recipe_form import IngredientSelectionDialog

        IngredientSelectionDialog._search_ingredients_for_typeahead(
            None, "salt & pepper"
        )
        mock_search.assert_called_once_with("salt & pepper", limit=10)

    @patch("src.services.ingredient_hierarchy_service.search_ingredients")
    def test_result_has_required_keys(self, mock_search):
        """Results have id, display_name, slug, and typeahead_display."""
        mock_search.return_value = [
            {
                "id": 42,
                "display_name": "Butter",
                "slug": "butter",
                "hierarchy_level": 2,
                "ancestors": [{"id": 5, "display_name": "Dairy"}],
            },
        ]
        from src.ui.forms.recipe_form import IngredientSelectionDialog

        results = IngredientSelectionDialog._search_ingredients_for_typeahead(
            None, "but"
        )
        item = results[0]
        assert "id" in item
        assert "display_name" in item
        assert "slug" in item
        assert "typeahead_display" in item
