"""Tests for the FinishedGoodBuilderDialog shell and navigation."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def ctk_root():
    """Create a CTk root window for dialog testing."""
    import customtkinter as ctk

    if os.environ.get("BAKE_TRACKER_UI_TESTS") != "1":
        if sys.platform != "win32" and not (
            os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
        ):
            pytest.skip(
                "UI tests require a display; set BAKE_TRACKER_UI_TESTS=1 to force"
            )

    try:
        root = ctk.CTk()
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"CTk unavailable in this environment: {exc}")
    root.withdraw()
    yield root
    root.destroy()


class TestDialogCreation:
    """Tests for dialog construction (T005, T006)."""

    def test_dialog_creates_in_create_mode(self, ctk_root):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog
        from src.ui.widgets.accordion_step import STATE_ACTIVE, STATE_LOCKED

        dialog = FinishedGoodBuilderDialog(ctk_root)
        assert dialog.step1.state == STATE_ACTIVE
        assert dialog.step2.state == STATE_LOCKED
        assert dialog.step3.state == STATE_LOCKED
        assert dialog.result is None
        assert not dialog._is_edit_mode
        dialog.destroy()

    def test_dialog_creates_in_edit_mode(self, ctk_root):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        fg = MagicMock()
        fg.display_name = "Test Gift Box"
        dialog = FinishedGoodBuilderDialog(ctk_root, finished_good=fg)
        assert dialog._is_edit_mode
        assert dialog.name_entry.get() == "Test Gift Box"
        dialog.destroy()

    def test_three_accordion_steps_exist(self, ctk_root):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog
        from src.ui.widgets.accordion_step import AccordionStep

        dialog = FinishedGoodBuilderDialog(ctk_root)
        assert isinstance(dialog.step1, AccordionStep)
        assert isinstance(dialog.step2, AccordionStep)
        assert isinstance(dialog.step3, AccordionStep)
        assert dialog.step1.step_number == 1
        assert dialog.step2.step_number == 2
        assert dialog.step3.step_number == 3
        dialog.destroy()

    def test_scroll_frame_exists(self, ctk_root):
        import customtkinter as ctk

        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        assert isinstance(dialog.scroll_frame, ctk.CTkScrollableFrame)
        dialog.destroy()


class TestStepNavigation:
    """Tests for step navigation logic (T007)."""

    def test_advance_to_step_2(self, ctk_root):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog
        from src.ui.widgets.accordion_step import STATE_ACTIVE, STATE_COMPLETED

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog.advance_to_step(2, "3 items selected")
        assert dialog.step1.state == STATE_COMPLETED
        assert dialog.step2.state == STATE_ACTIVE
        assert dialog._step_completed[1] is True
        dialog.destroy()

    def test_advance_to_step_3(self, ctk_root):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog
        from src.ui.widgets.accordion_step import STATE_ACTIVE, STATE_COMPLETED

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog.advance_to_step(2, "3 items")
        dialog.advance_to_step(3, "2 materials")
        assert dialog.step1.state == STATE_COMPLETED
        assert dialog.step2.state == STATE_COMPLETED
        assert dialog.step3.state == STATE_ACTIVE
        dialog.destroy()

    def test_mutual_exclusion(self, ctk_root):
        """Only one step should be expanded at a time."""
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        # Initially step1 active
        assert dialog.step1.is_expanded
        assert not dialog.step2.is_expanded

        dialog.advance_to_step(2, "done")
        assert not dialog.step1.is_expanded
        assert dialog.step2.is_expanded
        assert not dialog.step3.is_expanded
        dialog.destroy()

    def test_change_button_goes_back(self, ctk_root):
        """Clicking Change on step 1 from step 2 should expand step 1."""
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog
        from src.ui.widgets.accordion_step import STATE_ACTIVE

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog.advance_to_step(2, "3 items")
        dialog.advance_to_step(3, "2 materials")

        # Simulate "Change" click on step 1
        dialog._on_step_change(1)
        assert dialog.step1.state == STATE_ACTIVE
        assert dialog.step1.is_expanded
        assert not dialog.step2.is_expanded
        assert not dialog.step3.is_expanded
        dialog.destroy()

    def test_get_current_step(self, ctk_root):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        assert dialog._get_current_step() == 1

        dialog.advance_to_step(2, "done")
        assert dialog._get_current_step() == 2
        dialog.destroy()


class TestDialogControls:
    """Tests for Cancel, Start Over, and name entry (T008)."""

    def test_start_over_resets_all(self, ctk_root):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog
        from src.ui.widgets.accordion_step import STATE_ACTIVE, STATE_LOCKED

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog.name_entry.insert(0, "Test Name")
        dialog.food_selections[1] = 2
        dialog.material_selections[5] = 3
        dialog.advance_to_step(2, "3 items")
        dialog.advance_to_step(3, "2 materials")

        dialog._on_start_over()

        assert dialog.step1.state == STATE_ACTIVE
        assert dialog.step2.state == STATE_LOCKED
        assert dialog.step3.state == STATE_LOCKED
        assert dialog.name_entry.get() == ""
        assert len(dialog.food_selections) == 0
        assert len(dialog.material_selections) == 0
        assert not dialog._has_changes
        dialog.destroy()

    def test_cancel_with_no_changes_closes(self, ctk_root):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog._has_changes = False
        dialog._on_cancel()
        # Dialog should be destroyed (result is None)
        assert dialog.result is None

    @patch("src.ui.builders.finished_good_builder.show_confirmation")
    def test_cancel_with_changes_prompts(self, mock_confirm, ctk_root):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        mock_confirm.return_value = False  # User says "Keep Editing"
        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog._has_changes = True
        dialog._on_cancel()
        mock_confirm.assert_called_once()
        # Dialog should still exist since user declined
        assert dialog.winfo_exists()
        dialog.destroy()

    @patch("src.ui.builders.finished_good_builder.show_confirmation")
    def test_cancel_with_changes_confirmed_closes(self, mock_confirm, ctk_root):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        mock_confirm.return_value = True  # User confirms discard
        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog._has_changes = True
        dialog._on_cancel()
        mock_confirm.assert_called_once()
        assert dialog.result is None

    def test_name_change_sets_has_changes(self, ctk_root):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        assert not dialog._has_changes
        dialog._on_name_change()
        assert dialog._has_changes
        dialog.destroy()

    def test_advance_sets_has_changes(self, ctk_root):
        from src.ui.builders.finished_good_builder import FinishedGoodBuilderDialog

        dialog = FinishedGoodBuilderDialog(ctk_root)
        dialog._has_changes = False
        dialog.advance_to_step(2, "done")
        assert dialog._has_changes
        dialog.destroy()
