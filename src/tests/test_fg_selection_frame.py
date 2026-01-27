"""
Tests for FGSelectionFrame UI component (F070).
"""

import pytest
from unittest.mock import MagicMock, patch


class TestFGSelectionFrameInit:
    """Tests for FGSelectionFrame initialization."""

    def test_creates_with_callbacks(self, mock_ctk_root):
        """Frame initializes with save and cancel callbacks."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        on_save = MagicMock()
        on_cancel = MagicMock()

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=on_save,
            on_cancel=on_cancel,
        )

        assert frame._on_save is on_save
        assert frame._on_cancel is on_cancel

    def test_has_required_widgets(self, mock_ctk_root):
        """Frame contains all required UI elements."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )

        assert frame._header_label is not None
        assert frame._scroll_frame is not None
        assert frame._count_label is not None
        assert frame._save_button is not None
        assert frame._cancel_button is not None


class TestPopulateFinishedGoods:
    """Tests for populate_finished_goods method."""

    def test_displays_fg_names(self, mock_ctk_root, mock_fgs):
        """Populates checkboxes with FG display names."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )

        frame.populate_finished_goods(mock_fgs, "Test Event")

        assert len(frame._checkbox_vars) == len(mock_fgs)
        for fg in mock_fgs:
            assert fg.id in frame._checkbox_vars

    def test_updates_header_with_event_name(self, mock_ctk_root, mock_fgs):
        """Updates header label with event name."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )

        frame.populate_finished_goods(mock_fgs, "Holiday Event")

        # Header should include event name
        header_text = frame._header_label.cget("text")
        assert "Holiday Event" in header_text

    def test_clears_previous_checkboxes(self, mock_ctk_root, mock_fgs):
        """Clears existing checkboxes when repopulated."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )

        # Populate twice with different data
        frame.populate_finished_goods(mock_fgs[:2], "Event 1")
        first_count = len(frame._checkbox_vars)

        frame.populate_finished_goods(mock_fgs, "Event 2")
        second_count = len(frame._checkbox_vars)

        assert first_count == 2
        assert second_count == len(mock_fgs)

    def test_handles_empty_list(self, mock_ctk_root):
        """Handles empty finished goods list gracefully."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )

        frame.populate_finished_goods([], "Test Event")

        assert len(frame._checkbox_vars) == 0
        assert "0 of 0" in frame._count_label.cget("text")


class TestSelection:
    """Tests for selection methods."""

    def test_set_selected_checks_specified_fgs(self, mock_ctk_root, mock_fgs):
        """set_selected checks only specified FG IDs."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        # Select first two
        frame.set_selected([mock_fgs[0].id, mock_fgs[1].id])

        selected = frame.get_selected()
        assert mock_fgs[0].id in selected
        assert mock_fgs[1].id in selected
        assert mock_fgs[2].id not in selected

    def test_get_selected_returns_checked_fg_ids(self, mock_ctk_root, mock_fgs):
        """get_selected returns IDs of checked FGs."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        # Manually set checkbox values
        frame._checkbox_vars[mock_fgs[0].id].set(True)
        frame._checkbox_vars[mock_fgs[2].id].set(True)

        selected = frame.get_selected()
        assert set(selected) == {mock_fgs[0].id, mock_fgs[2].id}

    def test_set_selected_with_empty_list_unchecks_all(self, mock_ctk_root, mock_fgs):
        """set_selected with empty list unchecks all FGs."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        # Select some first
        frame.set_selected([mock_fgs[0].id, mock_fgs[1].id])
        assert len(frame.get_selected()) == 2

        # Clear selection
        frame.set_selected([])
        assert len(frame.get_selected()) == 0


class TestCountDisplay:
    """Tests for count display."""

    def test_count_updates_on_selection(self, mock_ctk_root, mock_fgs):
        """Count label updates when selection changes."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        # Initial count
        assert "0 of" in frame._count_label.cget("text")

        # Select one
        frame.set_selected([mock_fgs[0].id])
        assert "1 of" in frame._count_label.cget("text")

    def test_count_shows_total(self, mock_ctk_root, mock_fgs):
        """Count label shows total number of FGs."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        count_text = frame._count_label.cget("text")
        assert f"of {len(mock_fgs)}" in count_text


class TestCallbacks:
    """Tests for button callbacks."""

    def test_save_calls_callback_with_selected_ids(self, mock_ctk_root, mock_fgs):
        """Save button calls on_save with selected FG IDs."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        on_save = MagicMock()
        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=on_save,
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)
        frame.set_selected([mock_fgs[0].id])

        frame._handle_save()

        on_save.assert_called_once_with([mock_fgs[0].id])

    def test_cancel_calls_callback(self, mock_ctk_root, mock_fgs):
        """Cancel button calls on_cancel."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        on_cancel = MagicMock()
        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=on_cancel,
        )

        frame._handle_cancel()

        on_cancel.assert_called_once()

    def test_save_with_no_callback_does_not_error(self, mock_ctk_root, mock_fgs):
        """Save with no callback doesn't raise error."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=None,
            on_cancel=None,
        )
        frame.populate_finished_goods(mock_fgs)

        # Should not raise
        frame._handle_save()
        frame._handle_cancel()


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_ctk_root():
    """Create a mock CTk root for testing."""
    # We need to actually create a Tk instance for CTkFrame to work
    import customtkinter as ctk

    root = ctk.CTk()
    root.withdraw()  # Hide the window
    yield root
    root.destroy()


@pytest.fixture
def mock_fgs():
    """Create mock FinishedGood objects for testing."""
    fgs = []
    for i in range(3):
        fg = MagicMock()
        fg.id = i + 1
        fg.display_name = f"Test FG {i + 1}"
        fgs.append(fg)
    return fgs
