"""
Tests for RecipeSelectionFrame UI component (F069).

Tests cover:
- _get_display_name for base vs variant recipes
- get_selected_ids / set_selected logic
- Visual distinction patterns
"""

import pytest
from unittest.mock import MagicMock, patch


class TestGetDisplayName:
    """Tests for _get_display_name method."""

    def test_base_recipe_shows_name_only(self):
        """Base recipes should display their name without modification."""
        # Create mock recipe
        recipe = MagicMock()
        recipe.name = "Chocolate Chip Cookies"
        recipe.base_recipe_id = None  # Base recipe
        recipe.variant_name = None

        # Create frame instance with mocked parent
        with patch("customtkinter.CTkFrame.__init__", return_value=None):
            from src.ui.components.recipe_selection_frame import RecipeSelectionFrame

            frame = object.__new__(RecipeSelectionFrame)
            frame._recipes = []
            frame._recipe_vars = {}

            result = frame._get_display_name(recipe)

        assert result == "Chocolate Chip Cookies"

    def test_variant_recipe_shows_indent_and_label(self):
        """Variant recipes should show indentation and variant label."""
        # Create mock recipe
        recipe = MagicMock()
        recipe.name = "Chocolate Chip Cookies"
        recipe.base_recipe_id = 1  # This is a variant
        recipe.variant_name = "Raspberry"

        # Create frame instance with mocked parent
        with patch("customtkinter.CTkFrame.__init__", return_value=None):
            from src.ui.components.recipe_selection_frame import RecipeSelectionFrame

            frame = object.__new__(RecipeSelectionFrame)
            frame._recipes = []
            frame._recipe_vars = {}

            result = frame._get_display_name(recipe)

        assert result == "    Chocolate Chip Cookies (variant: Raspberry)"

    def test_variant_recipe_without_variant_name_shows_default(self):
        """Variant recipes without variant_name should show 'variant' as default."""
        # Create mock recipe
        recipe = MagicMock()
        recipe.name = "Sugar Cookies"
        recipe.base_recipe_id = 2  # This is a variant
        recipe.variant_name = None  # No variant name

        # Create frame instance with mocked parent
        with patch("customtkinter.CTkFrame.__init__", return_value=None):
            from src.ui.components.recipe_selection_frame import RecipeSelectionFrame

            frame = object.__new__(RecipeSelectionFrame)
            frame._recipes = []
            frame._recipe_vars = {}

            result = frame._get_display_name(recipe)

        assert result == "    Sugar Cookies (variant: variant)"

    def test_variant_recipe_with_empty_variant_name_shows_default(self):
        """Variant recipes with empty variant_name should show 'variant' as default."""
        # Create mock recipe
        recipe = MagicMock()
        recipe.name = "Oatmeal Cookies"
        recipe.base_recipe_id = 3  # This is a variant
        recipe.variant_name = ""  # Empty variant name

        # Create frame instance with mocked parent
        with patch("customtkinter.CTkFrame.__init__", return_value=None):
            from src.ui.components.recipe_selection_frame import RecipeSelectionFrame

            frame = object.__new__(RecipeSelectionFrame)
            frame._recipes = []
            frame._recipe_vars = {}

            result = frame._get_display_name(recipe)

        assert result == "    Oatmeal Cookies (variant: variant)"


class TestSelectionLogic:
    """Tests for get_selected_ids and set_selected methods."""

    def test_get_selected_ids_returns_checked_ids(self):
        """get_selected_ids returns IDs of checked recipes only."""
        with patch("customtkinter.CTkFrame.__init__", return_value=None):
            with patch("customtkinter.BooleanVar") as MockBoolVar:
                from src.ui.components.recipe_selection_frame import RecipeSelectionFrame

                frame = object.__new__(RecipeSelectionFrame)
                frame._selected_recipe_ids = set()

                # Mock BooleanVars
                var1 = MagicMock()
                var1.get.return_value = True
                var2 = MagicMock()
                var2.get.return_value = False
                var3 = MagicMock()
                var3.get.return_value = True

                frame._recipe_vars = {1: var1, 2: var2, 3: var3}

                result = frame.get_selected_ids()

        assert set(result) == {1, 3}

    def test_get_selected_ids_returns_empty_when_none_selected(self):
        """get_selected_ids returns empty list when no recipes selected."""
        with patch("customtkinter.CTkFrame.__init__", return_value=None):
            from src.ui.components.recipe_selection_frame import RecipeSelectionFrame

            frame = object.__new__(RecipeSelectionFrame)
            frame._selected_recipe_ids = set()

            # Mock BooleanVars - all unchecked
            var1 = MagicMock()
            var1.get.return_value = False
            var2 = MagicMock()
            var2.get.return_value = False

            frame._recipe_vars = {1: var1, 2: var2}

            result = frame.get_selected_ids()

        assert result == []

    def test_set_selected_checks_specified_ids(self):
        """set_selected checks specified IDs and unchecks others."""
        with patch("customtkinter.CTkFrame.__init__", return_value=None):
            from src.ui.components.recipe_selection_frame import RecipeSelectionFrame

            frame = object.__new__(RecipeSelectionFrame)

            # Mock BooleanVars
            var1 = MagicMock()
            var2 = MagicMock()
            var3 = MagicMock()

            frame._recipe_vars = {1: var1, 2: var2, 3: var3}
            frame._count_label = MagicMock()

            # Select recipes 1 and 3
            frame.set_selected([1, 3])

        var1.set.assert_called_once_with(True)
        var2.set.assert_called_once_with(False)
        var3.set.assert_called_once_with(True)

    def test_set_selected_with_empty_list_unchecks_all(self):
        """set_selected with empty list unchecks all recipes."""
        with patch("customtkinter.CTkFrame.__init__", return_value=None):
            from src.ui.components.recipe_selection_frame import RecipeSelectionFrame

            frame = object.__new__(RecipeSelectionFrame)

            # Mock BooleanVars
            var1 = MagicMock()
            var2 = MagicMock()

            frame._recipe_vars = {1: var1, 2: var2}
            frame._count_label = MagicMock()

            # Select none
            frame.set_selected([])

        var1.set.assert_called_once_with(False)
        var2.set.assert_called_once_with(False)

    def test_set_selected_ignores_unknown_ids(self):
        """set_selected ignores IDs not in the recipe list."""
        with patch("customtkinter.CTkFrame.__init__", return_value=None):
            from src.ui.components.recipe_selection_frame import RecipeSelectionFrame

            frame = object.__new__(RecipeSelectionFrame)

            # Mock BooleanVars
            var1 = MagicMock()
            var2 = MagicMock()

            frame._recipe_vars = {1: var1, 2: var2}
            frame._count_label = MagicMock()

            # Select ID 99 which doesn't exist
            frame.set_selected([99])

        # Both should be unchecked (99 is ignored)
        var1.set.assert_called_once_with(False)
        var2.set.assert_called_once_with(False)


class TestCallbacks:
    """Tests for save and cancel callback handling."""

    def test_handle_save_calls_callback_with_selected_ids(self):
        """_handle_save calls on_save callback with selected IDs."""
        with patch("customtkinter.CTkFrame.__init__", return_value=None):
            from src.ui.components.recipe_selection_frame import RecipeSelectionFrame

            frame = object.__new__(RecipeSelectionFrame)
            frame._selected_recipe_ids = set()

            # Mock
            callback = MagicMock()
            frame._on_save = callback

            var1 = MagicMock()
            var1.get.return_value = True
            var2 = MagicMock()
            var2.get.return_value = False

            frame._recipe_vars = {1: var1, 2: var2}

            frame._handle_save()

        callback.assert_called_once_with([1])

    def test_handle_save_does_nothing_without_callback(self):
        """_handle_save does nothing when callback is None."""
        with patch("customtkinter.CTkFrame.__init__", return_value=None):
            from src.ui.components.recipe_selection_frame import RecipeSelectionFrame

            frame = object.__new__(RecipeSelectionFrame)
            frame._on_save = None
            frame._recipe_vars = {}

            # Should not raise
            frame._handle_save()

    def test_handle_cancel_calls_callback(self):
        """_handle_cancel calls on_cancel callback."""
        with patch("customtkinter.CTkFrame.__init__", return_value=None):
            from src.ui.components.recipe_selection_frame import RecipeSelectionFrame

            frame = object.__new__(RecipeSelectionFrame)

            callback = MagicMock()
            frame._on_cancel = callback

            frame._handle_cancel()

        callback.assert_called_once_with()

    def test_handle_cancel_does_nothing_without_callback(self):
        """_handle_cancel does nothing when callback is None."""
        with patch("customtkinter.CTkFrame.__init__", return_value=None):
            from src.ui.components.recipe_selection_frame import RecipeSelectionFrame

            frame = object.__new__(RecipeSelectionFrame)
            frame._on_cancel = None

            # Should not raise
            frame._handle_cancel()
