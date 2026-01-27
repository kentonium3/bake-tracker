"""
Tests for FGSelectionFrame UI component.

F070: Finished Goods Filtering for Event Planning
F071: Finished Goods Quantity Specification
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

        # Use get_selected_ids for checkbox-only check
        selected = frame.get_selected_ids()
        assert mock_fgs[0].id in selected
        assert mock_fgs[1].id in selected
        assert mock_fgs[2].id not in selected

    def test_get_selected_ids_returns_checked_fg_ids(self, mock_ctk_root, mock_fgs):
        """get_selected_ids returns IDs of checked FGs (ignoring quantity)."""
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

        selected = frame.get_selected_ids()
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

        # Select some first (with quantities for get_selected to work)
        frame.set_selected_with_quantities([(mock_fgs[0].id, 5), (mock_fgs[1].id, 10)])
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

    def test_save_calls_callback_with_selected_tuples(self, mock_ctk_root, mock_fgs):
        """Save button calls on_save with (fg_id, quantity) tuples."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        on_save = MagicMock()
        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=on_save,
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)
        frame.set_selected_with_quantities([(mock_fgs[0].id, 5)])

        frame._handle_save()

        on_save.assert_called_once_with([(mock_fgs[0].id, 5)])

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
# F071: Quantity Specification Tests
# ============================================================================


class TestQuantityInputs:
    """Tests for quantity input fields (F071)."""

    def test_quantity_entries_created_for_each_fg(self, mock_ctk_root, mock_fgs):
        """Quantity entry field created for each FG."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        assert len(frame._quantity_vars) == len(mock_fgs)
        assert len(frame._quantity_entries) == len(mock_fgs)
        for fg in mock_fgs:
            assert fg.id in frame._quantity_vars
            assert fg.id in frame._quantity_entries

    def test_feedback_labels_created_for_each_fg(self, mock_ctk_root, mock_fgs):
        """Feedback label created for each FG."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        assert len(frame._feedback_labels) == len(mock_fgs)
        for fg in mock_fgs:
            assert fg.id in frame._feedback_labels

    def test_quantity_vars_cleared_on_repopulate(self, mock_ctk_root, mock_fgs):
        """Quantity variables cleared when repopulating."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs[:2])
        frame._quantity_vars[mock_fgs[0].id].set("10")

        # Repopulate
        frame.populate_finished_goods(mock_fgs)

        # Old value should be gone
        assert frame._quantity_vars[mock_fgs[0].id].get() == ""


class TestSetSelectedWithQuantities:
    """Tests for set_selected_with_quantities method (F071)."""

    def test_sets_checkbox_and_quantity(self, mock_ctk_root, mock_fgs):
        """Sets both checkbox and quantity for specified FGs."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        frame.set_selected_with_quantities([(mock_fgs[0].id, 10), (mock_fgs[1].id, 25)])

        assert frame._checkbox_vars[mock_fgs[0].id].get() is True
        assert frame._quantity_vars[mock_fgs[0].id].get() == "10"
        assert frame._checkbox_vars[mock_fgs[1].id].get() is True
        assert frame._quantity_vars[mock_fgs[1].id].get() == "25"
        assert frame._checkbox_vars[mock_fgs[2].id].get() is False
        assert frame._quantity_vars[mock_fgs[2].id].get() == ""

    def test_clears_unspecified_fgs(self, mock_ctk_root, mock_fgs):
        """Clears checkbox and quantity for FGs not in list."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        # Set all first
        frame.set_selected_with_quantities([
            (mock_fgs[0].id, 5),
            (mock_fgs[1].id, 10),
            (mock_fgs[2].id, 15),
        ])

        # Now set only one
        frame.set_selected_with_quantities([(mock_fgs[1].id, 20)])

        assert frame._checkbox_vars[mock_fgs[0].id].get() is False
        assert frame._quantity_vars[mock_fgs[0].id].get() == ""
        assert frame._checkbox_vars[mock_fgs[1].id].get() is True
        assert frame._quantity_vars[mock_fgs[1].id].get() == "20"
        assert frame._checkbox_vars[mock_fgs[2].id].get() is False

    def test_updates_count_display(self, mock_ctk_root, mock_fgs):
        """Updates count display after setting selection."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        frame.set_selected_with_quantities([(mock_fgs[0].id, 5), (mock_fgs[1].id, 10)])

        assert "2 of 3" in frame._count_label.cget("text")


class TestGetSelectedWithQuantities:
    """Tests for get_selected returning (fg_id, quantity) tuples (F071)."""

    def test_returns_tuples_for_valid_entries(self, mock_ctk_root, mock_fgs):
        """Returns (fg_id, quantity) tuples for valid entries."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        frame._checkbox_vars[mock_fgs[0].id].set(True)
        frame._quantity_vars[mock_fgs[0].id].set("10")
        frame._checkbox_vars[mock_fgs[1].id].set(True)
        frame._quantity_vars[mock_fgs[1].id].set("25")

        selected = frame.get_selected()

        assert (mock_fgs[0].id, 10) in selected
        assert (mock_fgs[1].id, 25) in selected
        assert len(selected) == 2

    def test_excludes_unchecked_fgs(self, mock_ctk_root, mock_fgs):
        """Excludes FGs with unchecked checkbox even if quantity set."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        # Set quantity but don't check checkbox
        frame._checkbox_vars[mock_fgs[0].id].set(False)
        frame._quantity_vars[mock_fgs[0].id].set("10")

        selected = frame.get_selected()
        assert len(selected) == 0

    def test_excludes_empty_quantities(self, mock_ctk_root, mock_fgs):
        """Excludes FGs with empty quantity field."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        frame._checkbox_vars[mock_fgs[0].id].set(True)
        frame._quantity_vars[mock_fgs[0].id].set("")

        selected = frame.get_selected()
        assert len(selected) == 0

    def test_excludes_invalid_quantities(self, mock_ctk_root, mock_fgs):
        """Excludes FGs with invalid quantity values."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        # Zero
        frame._checkbox_vars[mock_fgs[0].id].set(True)
        frame._quantity_vars[mock_fgs[0].id].set("0")

        # Negative
        frame._checkbox_vars[mock_fgs[1].id].set(True)
        frame._quantity_vars[mock_fgs[1].id].set("-5")

        # Non-integer
        frame._checkbox_vars[mock_fgs[2].id].set(True)
        frame._quantity_vars[mock_fgs[2].id].set("abc")

        selected = frame.get_selected()
        assert len(selected) == 0

    def test_excludes_decimal_quantities(self, mock_ctk_root, mock_fgs):
        """Excludes FGs with decimal quantity values."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        frame._checkbox_vars[mock_fgs[0].id].set(True)
        frame._quantity_vars[mock_fgs[0].id].set("3.5")

        selected = frame.get_selected()
        assert len(selected) == 0


class TestQuantityValidation:
    """Tests for quantity validation feedback (F071)."""

    def test_empty_is_valid(self, mock_ctk_root, mock_fgs):
        """Empty quantity field shows no error."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        frame._quantity_vars[mock_fgs[0].id].set("")
        frame._validate_quantity(mock_fgs[0].id)

        assert frame._feedback_labels[mock_fgs[0].id].cget("text") == ""

    def test_positive_integer_is_valid(self, mock_ctk_root, mock_fgs):
        """Positive integer shows no error."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        frame._quantity_vars[mock_fgs[0].id].set("42")
        frame._validate_quantity(mock_fgs[0].id)

        assert frame._feedback_labels[mock_fgs[0].id].cget("text") == ""

    def test_zero_shows_error(self, mock_ctk_root, mock_fgs):
        """Zero quantity shows error message."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        frame._quantity_vars[mock_fgs[0].id].set("0")
        frame._validate_quantity(mock_fgs[0].id)

        assert "Must be > 0" in frame._feedback_labels[mock_fgs[0].id].cget("text")

    def test_negative_shows_error(self, mock_ctk_root, mock_fgs):
        """Negative quantity shows error message."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        frame._quantity_vars[mock_fgs[0].id].set("-5")
        frame._validate_quantity(mock_fgs[0].id)

        assert "Must be > 0" in frame._feedback_labels[mock_fgs[0].id].cget("text")

    def test_non_integer_shows_error(self, mock_ctk_root, mock_fgs):
        """Non-integer quantity shows error message."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        frame._quantity_vars[mock_fgs[0].id].set("abc")
        frame._validate_quantity(mock_fgs[0].id)

        assert "Integer only" in frame._feedback_labels[mock_fgs[0].id].cget("text")

    def test_decimal_shows_error(self, mock_ctk_root, mock_fgs):
        """Decimal quantity shows error message."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        frame._quantity_vars[mock_fgs[0].id].set("3.5")
        frame._validate_quantity(mock_fgs[0].id)

        assert "Integer only" in frame._feedback_labels[mock_fgs[0].id].cget("text")


class TestHasValidationErrors:
    """Tests for has_validation_errors method (F071)."""

    def test_no_errors_when_all_valid(self, mock_ctk_root, mock_fgs):
        """Returns False when all checked FGs have valid quantities."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)
        frame.set_selected_with_quantities([(mock_fgs[0].id, 10)])

        assert frame.has_validation_errors() is False

    def test_no_errors_when_nothing_checked(self, mock_ctk_root, mock_fgs):
        """Returns False when nothing is checked."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)

        assert frame.has_validation_errors() is False

    def test_error_when_checked_but_empty(self, mock_ctk_root, mock_fgs):
        """Returns True when checked FG has empty quantity."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)
        frame._checkbox_vars[mock_fgs[0].id].set(True)
        frame._quantity_vars[mock_fgs[0].id].set("")

        assert frame.has_validation_errors() is True

    def test_error_when_checked_but_zero(self, mock_ctk_root, mock_fgs):
        """Returns True when checked FG has zero quantity."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)
        frame._checkbox_vars[mock_fgs[0].id].set(True)
        frame._quantity_vars[mock_fgs[0].id].set("0")

        assert frame.has_validation_errors() is True

    def test_error_when_checked_but_non_integer(self, mock_ctk_root, mock_fgs):
        """Returns True when checked FG has non-integer quantity."""
        from src.ui.components.fg_selection_frame import FGSelectionFrame

        frame = FGSelectionFrame(
            mock_ctk_root,
            on_save=MagicMock(),
            on_cancel=MagicMock(),
        )
        frame.populate_finished_goods(mock_fgs)
        frame._checkbox_vars[mock_fgs[0].id].set(True)
        frame._quantity_vars[mock_fgs[0].id].set("abc")

        assert frame.has_validation_errors() is True


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
