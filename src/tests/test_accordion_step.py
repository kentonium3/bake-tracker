"""Tests for the AccordionStep widget."""

import os
import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def ctk_root():
    """Create a CTk root window for widget testing."""
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


class TestAccordionStepInitialState:
    """Tests for AccordionStep initial state (T001, T002)."""

    def test_initial_state_is_locked(self, ctk_root):
        from src.ui.widgets.accordion_step import AccordionStep, STATE_LOCKED

        step = AccordionStep(ctk_root, step_number=1, title="Food Selection")
        assert step.state == STATE_LOCKED

    def test_initial_content_not_visible(self, ctk_root):
        from src.ui.widgets.accordion_step import AccordionStep

        step = AccordionStep(ctk_root, step_number=1, title="Food Selection")
        assert not step.is_expanded

    def test_step_number_stored(self, ctk_root):
        from src.ui.widgets.accordion_step import AccordionStep

        step = AccordionStep(ctk_root, step_number=2, title="Materials")
        assert step.step_number == 2

    def test_content_frame_exposed(self, ctk_root):
        """Content frame should be publicly accessible for adding child widgets."""
        import customtkinter as ctk

        from src.ui.widgets.accordion_step import AccordionStep

        step = AccordionStep(ctk_root, step_number=1, title="Test")
        assert isinstance(step.content_frame, ctk.CTkFrame)

    def test_header_frame_exists(self, ctk_root):
        """Header frame should be publicly accessible."""
        import customtkinter as ctk

        from src.ui.widgets.accordion_step import AccordionStep

        step = AccordionStep(ctk_root, step_number=1, title="Test")
        assert isinstance(step.header_frame, ctk.CTkFrame)


class TestAccordionStepStateTransitions:
    """Tests for state machine transitions (T002)."""

    def test_set_state_active(self, ctk_root):
        from src.ui.widgets.accordion_step import AccordionStep, STATE_ACTIVE

        step = AccordionStep(ctk_root, step_number=1, title="Food Selection")
        step.set_state(STATE_ACTIVE)
        assert step.state == STATE_ACTIVE
        assert step.is_expanded

    def test_set_state_completed(self, ctk_root):
        from src.ui.widgets.accordion_step import (
            AccordionStep,
            STATE_ACTIVE,
            STATE_COMPLETED,
        )

        step = AccordionStep(ctk_root, step_number=1, title="Food Selection")
        step.set_state(STATE_ACTIVE)
        step.set_state(STATE_COMPLETED)
        assert step.state == STATE_COMPLETED
        assert not step.is_expanded

    def test_set_state_locked(self, ctk_root):
        from src.ui.widgets.accordion_step import (
            AccordionStep,
            STATE_ACTIVE,
            STATE_LOCKED,
        )

        step = AccordionStep(ctk_root, step_number=1, title="Food Selection")
        step.set_state(STATE_ACTIVE)
        step.set_state(STATE_LOCKED)
        assert step.state == STATE_LOCKED
        assert not step.is_expanded

    def test_set_state_invalid_raises(self, ctk_root):
        from src.ui.widgets.accordion_step import AccordionStep

        step = AccordionStep(ctk_root, step_number=1, title="Test")
        with pytest.raises(ValueError, match="Invalid state"):
            step.set_state("invalid")

    def test_active_shows_arrow_icon(self, ctk_root):
        from src.ui.widgets.accordion_step import (
            AccordionStep,
            STATE_ACTIVE,
            _ICON_ARROW,
        )

        step = AccordionStep(ctk_root, step_number=1, title="Test")
        step.set_state(STATE_ACTIVE)
        assert step._status_icon_label.cget("text") == _ICON_ARROW

    def test_completed_shows_check_icon(self, ctk_root):
        from src.ui.widgets.accordion_step import (
            AccordionStep,
            STATE_COMPLETED,
            _ICON_CHECK,
        )

        step = AccordionStep(ctk_root, step_number=1, title="Test")
        step.set_state(STATE_COMPLETED)
        assert step._status_icon_label.cget("text") == _ICON_CHECK

    def test_locked_shows_lock_icon(self, ctk_root):
        from src.ui.widgets.accordion_step import AccordionStep, _ICON_LOCK

        step = AccordionStep(ctk_root, step_number=1, title="Test")
        # Initial state is locked
        assert step._status_icon_label.cget("text") == _ICON_LOCK


class TestAccordionStepExpandCollapse:
    """Tests for expand/collapse behavior (T003)."""

    def test_expand_shows_content(self, ctk_root):
        from src.ui.widgets.accordion_step import AccordionStep

        step = AccordionStep(ctk_root, step_number=1, title="Test")
        step.expand()
        assert step.is_expanded

    def test_expand_sets_active_state(self, ctk_root):
        from src.ui.widgets.accordion_step import AccordionStep, STATE_ACTIVE

        step = AccordionStep(ctk_root, step_number=1, title="Test")
        step.expand()
        assert step.state == STATE_ACTIVE

    def test_collapse_hides_content(self, ctk_root):
        from src.ui.widgets.accordion_step import AccordionStep

        step = AccordionStep(ctk_root, step_number=1, title="Test")
        step.expand()
        assert step.is_expanded
        step.collapse()
        assert not step.is_expanded

    def test_collapse_does_not_change_state(self, ctk_root):
        from src.ui.widgets.accordion_step import AccordionStep, STATE_ACTIVE

        step = AccordionStep(ctk_root, step_number=1, title="Test")
        step.expand()
        step.collapse()
        # State remains active; caller decides whether to set completed/locked
        assert step.state == STATE_ACTIVE


class TestAccordionStepMarkCompleted:
    """Tests for mark_completed convenience method (T003)."""

    def test_mark_completed_convenience(self, ctk_root):
        from src.ui.widgets.accordion_step import AccordionStep, STATE_COMPLETED

        step = AccordionStep(ctk_root, step_number=1, title="Food Selection")
        step.expand()
        step.mark_completed("3 items selected")
        assert step.state == STATE_COMPLETED
        assert not step.is_expanded
        assert step._summary_label.cget("text") == "3 items selected"

    def test_set_summary_updates_label(self, ctk_root):
        from src.ui.widgets.accordion_step import AccordionStep

        step = AccordionStep(ctk_root, step_number=1, title="Test")
        step.set_summary("5 materials chosen")
        assert step._summary_label.cget("text") == "5 materials chosen"


class TestAccordionStepChangeButton:
    """Tests for Change button callback (T003)."""

    def test_change_button_callback(self, ctk_root):
        from src.ui.widgets.accordion_step import AccordionStep, STATE_COMPLETED

        callback = MagicMock()
        step = AccordionStep(
            ctk_root,
            step_number=2,
            title="Materials",
            on_change_click=callback,
        )
        step.set_state(STATE_COMPLETED)
        step._handle_change_click()
        callback.assert_called_once_with(2)

    def test_change_button_no_callback(self, ctk_root):
        """Change button click should not raise if no callback provided."""
        from src.ui.widgets.accordion_step import AccordionStep, STATE_COMPLETED

        step = AccordionStep(ctk_root, step_number=1, title="Test")
        step.set_state(STATE_COMPLETED)
        step._handle_change_click()  # Should not raise

    def test_change_button_hidden_when_locked(self, ctk_root):
        from src.ui.widgets.accordion_step import AccordionStep

        step = AccordionStep(ctk_root, step_number=1, title="Test")
        # Locked state: change button should not be packed
        assert step._change_button.winfo_manager() == ""

    def test_change_button_hidden_when_active(self, ctk_root):
        from src.ui.widgets.accordion_step import AccordionStep, STATE_ACTIVE

        step = AccordionStep(ctk_root, step_number=1, title="Test")
        step.set_state(STATE_ACTIVE)
        assert step._change_button.winfo_manager() == ""

    def test_change_button_visible_when_completed(self, ctk_root):
        from src.ui.widgets.accordion_step import AccordionStep, STATE_COMPLETED

        step = AccordionStep(ctk_root, step_number=1, title="Test")
        step.set_state(STATE_COMPLETED)
        assert step._change_button.winfo_manager() != ""
