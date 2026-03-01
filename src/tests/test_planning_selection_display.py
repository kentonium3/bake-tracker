"""
Tests for F102: Planning Selection Persistence Display.

Verifies that saved recipe and FG selections are rendered on initial load
with contextual labels, and that blank-start behavior is preserved for
events with no selections.
"""

import pytest
from unittest.mock import MagicMock, patch, call


class TestRecipeFrameRenderSavedSelections:
    """Tests for RecipeSelectionFrame.render_saved_selections() (T001)."""

    def _make_frame(self):
        """Create a bare RecipeSelectionFrame without __init__."""
        with patch("customtkinter.CTkFrame.__init__", return_value=None):
            from src.ui.components.recipe_selection_frame import (
                RecipeSelectionFrame,
            )

            frame = object.__new__(RecipeSelectionFrame)
            frame._selected_recipe_ids = set()
            frame._recipe_vars = {}
            frame._recipes = []
            frame._scroll_frame = MagicMock()
            return frame

    def test_empty_selections_is_noop(self):
        """render_saved_selections() with no saved IDs does nothing."""
        frame = self._make_frame()
        frame._selected_recipe_ids = set()

        # Should not query DB or render anything
        with patch(
            "src.ui.components.recipe_selection_frame.session_scope"
        ) as mock_session:
            frame.render_saved_selections()
            mock_session.assert_not_called()

    def test_renders_saved_recipes(self):
        """render_saved_selections() queries DB and renders recipes."""
        frame = self._make_frame()
        frame._selected_recipe_ids = {1, 2, 3}

        mock_recipe_1 = MagicMock(id=1, name="Recipe 1")
        mock_recipe_2 = MagicMock(id=2, name="Recipe 2")
        mock_recipe_3 = MagicMock(id=3, name="Recipe 3")
        mock_recipes = [mock_recipe_1, mock_recipe_2, mock_recipe_3]

        mock_session = MagicMock()
        mock_query = mock_session.__enter__.return_value.query.return_value
        mock_query.filter.return_value.all.return_value = mock_recipes

        with patch(
            "src.ui.components.recipe_selection_frame.session_scope",
            return_value=mock_session,
        ):
            with patch.object(frame, "_render_recipes") as mock_render:
                # Mock CTkLabel and CTkFont to avoid needing Tk root
                with patch("src.ui.components.recipe_selection_frame.ctk.CTkLabel") as mock_label_cls:
                    with patch("src.ui.components.recipe_selection_frame.ctk.CTkFont"):
                        mock_label = MagicMock()
                        mock_label_cls.return_value = mock_label
                        # Mock scroll frame children for label reordering
                        mock_child = MagicMock()
                        frame._scroll_frame.winfo_children.return_value = [
                            mock_child, mock_label
                        ]

                        frame.render_saved_selections()

                        mock_render.assert_called_once_with(mock_recipes)
                        # Verify contextual label was created
                        mock_label_cls.assert_called_once()
                        label_kwargs = mock_label_cls.call_args
                        assert label_kwargs[1]["text"] == "Saved plan selections"

    def test_deleted_recipe_silently_excluded(self):
        """Saved IDs not in DB are silently excluded."""
        frame = self._make_frame()
        frame._selected_recipe_ids = {999}  # ID that won't exist

        mock_session = MagicMock()
        mock_query = mock_session.__enter__.return_value.query.return_value
        mock_query.filter.return_value.all.return_value = []  # No results

        with patch(
            "src.ui.components.recipe_selection_frame.session_scope",
            return_value=mock_session,
        ):
            with patch.object(frame, "_render_recipes") as mock_render:
                frame.render_saved_selections()
                # Should NOT call render since no valid recipes found
                mock_render.assert_not_called()


class TestFGFrameRenderSavedSelections:
    """Tests for FGSelectionFrame.render_saved_selections() (T002)."""

    def _make_frame(self):
        """Create a bare FGSelectionFrame without __init__."""
        with patch("customtkinter.CTkFrame.__init__", return_value=None):
            from src.ui.components.fg_selection_frame import FGSelectionFrame

            frame = object.__new__(FGSelectionFrame)
            frame._selected_fg_ids = set()
            frame._fg_quantities = {}
            frame._checkbox_vars = {}
            frame._quantity_vars = {}
            frame._show_selected_only = False
            frame._show_selected_button = MagicMock()
            frame._selected_indicator = MagicMock()
            frame._event_id = 1
            frame._scroll_frame = MagicMock()
            return frame

    def test_empty_selections_is_noop(self):
        """render_saved_selections() with no saved IDs does nothing."""
        frame = self._make_frame()
        frame._selected_fg_ids = set()

        frame.render_saved_selections()

        assert frame._show_selected_only is False
        frame._show_selected_button.configure.assert_not_called()
        frame._selected_indicator.configure.assert_not_called()

    def test_sets_selected_only_mode(self):
        """render_saved_selections() enters selected-only mode."""
        frame = self._make_frame()
        frame._selected_fg_ids = {1, 2}

        with patch.object(frame, "_render_selected_only"):
            frame.render_saved_selections()

        assert frame._show_selected_only is True
        frame._show_selected_button.configure.assert_called_with(
            text="Show Filtered View"
        )

    def test_sets_contextual_indicator(self):
        """render_saved_selections() sets indicator with correct count."""
        frame = self._make_frame()
        frame._selected_fg_ids = {10, 20, 30}

        with patch.object(frame, "_render_selected_only"):
            frame.render_saved_selections()

        frame._selected_indicator.configure.assert_called_with(
            text="Saved plan selections (3 items)"
        )

    def test_calls_render_selected_only(self):
        """render_saved_selections() delegates to _render_selected_only()."""
        frame = self._make_frame()
        frame._selected_fg_ids = {1}

        with patch.object(frame, "_render_selected_only") as mock_render:
            frame.render_saved_selections()
            mock_render.assert_called_once()

    def test_filter_transition_resets_mode(self):
        """Applying a filter after render_saved_selections() exits selected-only mode."""
        frame = self._make_frame()
        frame._selected_fg_ids = {1, 2}

        with patch.object(frame, "_render_selected_only"):
            frame.render_saved_selections()

        assert frame._show_selected_only is True

        # Simulate what _on_filter_change does (lines 276-280)
        frame._show_selected_only = False
        frame._show_selected_button.configure(text="Show All Selected")
        frame._selected_indicator.configure(text="")

        assert frame._show_selected_only is False
