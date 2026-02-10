"""
Tests for TypeAheadEntry widget.

Tests the core widget logic: debounce, callback invocation, selection flow,
dismissal, and edge cases. Uses mock callbacks to verify behavior without
requiring real service layers.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

# Guard against missing display -- tkinter requires a display
try:
    import tkinter as tk

    _root = tk.Tk()
    _root.withdraw()
    _HAS_DISPLAY = True
except Exception:
    _HAS_DISPLAY = False

pytestmark = pytest.mark.skipif(
    not _HAS_DISPLAY, reason="No display available for tkinter tests"
)


@pytest.fixture
def root():
    """Provide a hidden tkinter root window for testing."""
    if not _HAS_DISPLAY:
        pytest.skip("No display")
    # Reuse the module-level root to avoid multiple Tk instances
    yield _root


@pytest.fixture
def mock_items_callback():
    """Provide a mock items_callback that returns sample results."""
    callback = MagicMock()
    callback.return_value = [
        {"display_name": "Chocolate Chips", "id": 1, "slug": "chocolate-chips"},
        {"display_name": "Chocolate (baking)", "id": 2, "slug": "chocolate-baking"},
        {"display_name": "Cocoa Powder", "id": 3, "slug": "cocoa-powder"},
    ]
    return callback


@pytest.fixture
def mock_select_callback():
    """Provide a mock on_select_callback."""
    return MagicMock()


@pytest.fixture
def widget(root, mock_items_callback, mock_select_callback):
    """Create a TypeAheadEntry widget for testing."""
    from src.ui.widgets.type_ahead_entry import TypeAheadEntry

    w = TypeAheadEntry(
        master=root,
        items_callback=mock_items_callback,
        on_select_callback=mock_select_callback,
        min_chars=3,
        debounce_ms=50,  # Short debounce for faster tests
        max_results=10,
    )
    w.pack()
    yield w
    w.destroy()


class TestTypeAheadEntryInit:
    """Test widget initialization."""

    def test_creates_without_error(self, widget):
        assert widget is not None

    def test_entry_widget_exists(self, widget):
        assert widget._entry is not None

    def test_dropdown_starts_hidden(self, widget):
        assert widget._dropdown_visible is False
        assert widget._dropdown is None

    def test_highlight_starts_at_negative_one(self, widget):
        assert widget._highlight_index == -1

    def test_results_start_empty(self, widget):
        assert widget._results == []

    def test_default_parameters(self, root, mock_items_callback, mock_select_callback):
        from src.ui.widgets.type_ahead_entry import TypeAheadEntry

        w = TypeAheadEntry(
            master=root,
            items_callback=mock_items_callback,
            on_select_callback=mock_select_callback,
        )
        assert w.min_chars == 3
        assert w.debounce_ms == 300
        assert w.max_results == 10
        assert w.clear_on_select is True
        assert w._display_key == "display_name"
        w.destroy()


class TestPublicMethods:
    """Test public API methods."""

    def test_get_text_returns_entry_content(self, widget):
        widget._entry.insert(0, "test query")
        assert widget.get_text() == "test query"

    def test_clear_empties_entry(self, widget):
        widget._entry.insert(0, "something")
        widget.clear()
        assert widget.get_text() == ""

    def test_set_focus_sets_entry_focus(self, widget, root):
        widget.set_focus()
        root.update_idletasks()
        # Focus set completes without error


class TestDebounce:
    """Test debounce search triggering."""

    def test_search_not_called_below_min_chars(self, widget, mock_items_callback):
        widget._entry.insert(0, "ab")
        widget._on_key_release(MagicMock(keysym="b"))
        # Process pending after() callbacks
        widget.update_idletasks()
        mock_items_callback.assert_not_called()

    def test_search_called_at_min_chars(self, widget, mock_items_callback, root):
        widget._entry.insert(0, "cho")
        widget._on_key_release(MagicMock(keysym="o"))
        # Wait for debounce
        time.sleep(0.1)
        root.update()
        mock_items_callback.assert_called_once_with("cho")

    def test_rapid_typing_cancels_pending_search(
        self, widget, mock_items_callback, root
    ):
        # Type rapidly -- each keystroke should cancel the previous debounce
        for char in "choc":
            widget._entry.insert("end", char)
            widget._on_key_release(MagicMock(keysym=char))

        # Wait for debounce to fire
        time.sleep(0.1)
        root.update()

        # Should only be called once (with the final text)
        assert mock_items_callback.call_count == 1
        mock_items_callback.assert_called_with("choc")

    def test_navigation_keys_ignored(self, widget, mock_items_callback):
        widget._entry.insert(0, "chocolate")
        for key in ("Up", "Down", "Return", "Tab", "Escape", "Shift_L"):
            widget._on_key_release(MagicMock(keysym=key))
        mock_items_callback.assert_not_called()


class TestDropdown:
    """Test dropdown display."""

    def test_results_create_dropdown(self, widget, root):
        widget._execute_search("cho")
        assert widget._dropdown_visible is True
        assert widget._dropdown is not None

    def test_results_populate_labels(self, widget, root):
        widget._execute_search("cho")
        assert len(widget._result_labels) == 3

    def test_no_results_shows_message(self, widget, mock_items_callback, root):
        mock_items_callback.return_value = []
        widget._execute_search("xyz")
        assert widget._dropdown_visible is True
        # No result labels (message is not in _result_labels)
        assert len(widget._result_labels) == 0

    def test_truncation_message_shown(self, widget, mock_items_callback, root):
        # Return more than max_results
        widget.max_results = 2
        mock_items_callback.return_value = [
            {"display_name": f"Item {i}", "id": i} for i in range(5)
        ]
        widget._execute_search("item")
        # Only max_results labels shown
        assert len(widget._result_labels) == 2

    def test_hide_dropdown_resets_state(self, widget, root):
        widget._execute_search("cho")
        assert widget._dropdown_visible is True
        widget._hide_dropdown()
        assert widget._dropdown_visible is False
        assert widget._highlight_index == -1
        assert widget._result_labels == []

    def test_callback_error_shows_no_results(self, widget, mock_items_callback, root):
        mock_items_callback.side_effect = RuntimeError("Service error")
        widget._execute_search("cho")
        assert widget._dropdown_visible is True
        assert len(widget._result_labels) == 0


class TestSelection:
    """Test item selection."""

    def test_click_fires_callback(self, widget, mock_select_callback, root):
        widget._execute_search("cho")
        item = widget._results[0]
        widget._on_item_click(item)
        mock_select_callback.assert_called_once_with(item)

    def test_click_hides_dropdown(self, widget, mock_select_callback, root):
        widget._execute_search("cho")
        widget._on_item_click(widget._results[0])
        assert widget._dropdown_visible is False

    def test_clear_on_select_true(self, widget, root):
        widget.clear_on_select = True
        widget._entry.insert(0, "cho")
        widget._execute_search("cho")
        widget._on_item_click(widget._results[0])
        assert widget.get_text() == ""

    def test_clear_on_select_false(self, widget, root):
        widget.clear_on_select = False
        widget._entry.insert(0, "cho")
        widget._execute_search("cho")
        widget._on_item_click(widget._results[0])
        assert widget.get_text() == "cho"

    def test_select_callback_error_doesnt_crash(
        self, widget, mock_select_callback, root
    ):
        mock_select_callback.side_effect = RuntimeError("Handler error")
        widget._execute_search("cho")
        # Should not raise
        widget._on_item_click(widget._results[0])


class TestKeyboardNavigation:
    """Test keyboard navigation."""

    def test_arrow_down_highlights_first_item(self, widget, root):
        widget._execute_search("cho")
        widget._on_arrow_down(MagicMock())
        assert widget._highlight_index == 0

    def test_arrow_down_advances_highlight(self, widget, root):
        widget._execute_search("cho")
        widget._on_arrow_down(MagicMock())
        widget._on_arrow_down(MagicMock())
        assert widget._highlight_index == 1

    def test_arrow_down_clamps_at_last(self, widget, root):
        widget._execute_search("cho")
        # Move past last item
        for _ in range(10):
            widget._on_arrow_down(MagicMock())
        assert widget._highlight_index == 2  # 3 items, last index is 2

    def test_arrow_up_clamps_at_first(self, widget, root):
        widget._execute_search("cho")
        widget._on_arrow_down(MagicMock())  # Go to index 0
        widget._on_arrow_up(MagicMock())  # Try to go before 0
        assert widget._highlight_index == 0

    def test_enter_with_no_highlight_does_nothing(
        self, widget, mock_select_callback, root
    ):
        widget._execute_search("cho")
        assert widget._highlight_index == -1
        widget._on_enter(MagicMock())
        mock_select_callback.assert_not_called()

    def test_enter_selects_highlighted_item(
        self, widget, mock_select_callback, root
    ):
        widget._execute_search("cho")
        widget._on_arrow_down(MagicMock())
        widget._on_arrow_down(MagicMock())
        widget._on_enter(MagicMock())
        expected_item = widget._results[1]
        mock_select_callback.assert_called_once_with(expected_item)

    def test_arrow_down_with_no_dropdown_does_nothing(self, widget):
        result = widget._on_arrow_down(MagicMock())
        assert result == ""
        assert widget._highlight_index == -1

    def test_escape_hides_dropdown(self, widget, root):
        widget._execute_search("cho")
        widget._on_escape(MagicMock())
        assert widget._dropdown_visible is False


class TestDismissal:
    """Test dropdown dismissal."""

    def test_escape_closes_dropdown(self, widget, root):
        widget._execute_search("cho")
        assert widget._dropdown_visible is True
        widget._on_escape(MagicMock())
        assert widget._dropdown_visible is False

    def test_hide_dropdown_when_already_hidden(self, widget):
        # Should not raise
        widget._hide_dropdown()
        assert widget._dropdown_visible is False


class TestClickOutside:
    """Test click-outside detection (T010)."""

    def test_root_click_binding_set_on_show(self, widget, root):
        widget._execute_search("cho")
        assert widget._root_click_id is not None

    def test_root_click_binding_cleared_on_hide(self, widget, root):
        widget._execute_search("cho")
        widget._hide_dropdown()
        assert widget._root_click_id is None

    def test_click_outside_closes_dropdown(self, widget, root):
        widget._execute_search("cho")
        assert widget._dropdown_visible is True
        # Simulate click far outside both entry and dropdown
        event = MagicMock()
        event.x_root = -100
        event.y_root = -100
        widget._on_root_click(event)
        assert widget._dropdown_visible is False

    def test_click_on_entry_keeps_dropdown_open(self, widget, root):
        widget._execute_search("cho")
        assert widget._dropdown_visible is True
        # Mock entry geometry to simulate realistic coordinates
        with patch.object(widget._entry, "winfo_rootx", return_value=100), \
             patch.object(widget._entry, "winfo_rooty", return_value=200), \
             patch.object(widget._entry, "winfo_width", return_value=300), \
             patch.object(widget._entry, "winfo_height", return_value=30):
            event = MagicMock()
            event.x_root = 150  # Inside entry bounds
            event.y_root = 210
            widget._on_root_click(event)
        assert widget._dropdown_visible is True

    def test_click_on_dropdown_keeps_it_open(self, widget, root):
        widget._execute_search("cho")
        assert widget._dropdown_visible is True
        # Mock dropdown geometry to simulate realistic coordinates
        with patch.object(widget._entry, "winfo_rootx", return_value=100), \
             patch.object(widget._entry, "winfo_rooty", return_value=200), \
             patch.object(widget._entry, "winfo_width", return_value=300), \
             patch.object(widget._entry, "winfo_height", return_value=30), \
             patch.object(widget._dropdown, "winfo_rootx", return_value=100), \
             patch.object(widget._dropdown, "winfo_rooty", return_value=230), \
             patch.object(widget._dropdown, "winfo_width", return_value=300), \
             patch.object(widget._dropdown, "winfo_height", return_value=96):
            event = MagicMock()
            event.x_root = 150  # Inside dropdown bounds
            event.y_root = 260
            widget._on_root_click(event)
        assert widget._dropdown_visible is True

    def test_click_outside_when_not_visible_is_noop(self, widget):
        # Should not raise when no dropdown visible
        event = MagicMock()
        event.x_root = -100
        event.y_root = -100
        widget._on_root_click(event)
        assert widget._dropdown_visible is False


class TestMultipleInstances:
    """Test that multiple TypeAheadEntry widgets maintain independent state (T011)."""

    def test_independent_state(self, root, mock_items_callback, mock_select_callback):
        from src.ui.widgets.type_ahead_entry import TypeAheadEntry

        cb1 = MagicMock(return_value=[{"display_name": "A1", "id": 1}])
        cb2 = MagicMock(return_value=[{"display_name": "B1", "id": 2}])
        sel1 = MagicMock()
        sel2 = MagicMock()

        w1 = TypeAheadEntry(master=root, items_callback=cb1,
                            on_select_callback=sel1, debounce_ms=50)
        w2 = TypeAheadEntry(master=root, items_callback=cb2,
                            on_select_callback=sel2, debounce_ms=50)
        w1.pack()
        w2.pack()

        try:
            # Search on w1 only
            w1._execute_search("aaa")
            assert w1._dropdown_visible is True
            assert w2._dropdown_visible is False

            # w1 results don't affect w2
            assert len(w1._results) == 1
            assert len(w2._results) == 0

            # Search on w2
            w2._execute_search("bbb")
            assert w2._dropdown_visible is True
            assert len(w2._results) == 1

            # w1 still has its own state
            assert w1._dropdown_visible is True
            assert w1._results[0]["display_name"] == "A1"
            assert w2._results[0]["display_name"] == "B1"

            # Highlight on w1 doesn't affect w2
            w1._on_arrow_down(MagicMock())
            assert w1._highlight_index == 0
            assert w2._highlight_index == -1
        finally:
            w1.destroy()
            w2.destroy()


class TestKeyboardWorkflow:
    """Test complete keyboard-only workflow (type -> arrow -> enter)."""

    def test_full_keyboard_selection_workflow(
        self, widget, mock_items_callback, mock_select_callback, root
    ):
        # Step 1: Execute search (simulating debounce completion)
        widget._execute_search("cho")
        assert widget._dropdown_visible is True
        assert widget._highlight_index == -1

        # Step 2: Arrow down to first item
        widget._on_arrow_down(MagicMock())
        assert widget._highlight_index == 0

        # Step 3: Arrow down to second item
        widget._on_arrow_down(MagicMock())
        assert widget._highlight_index == 1

        # Step 4: Enter selects second item
        widget._on_enter(MagicMock())
        expected_item = {"display_name": "Chocolate (baking)", "id": 2,
                         "slug": "chocolate-baking"}
        mock_select_callback.assert_called_once_with(expected_item)
        assert widget._dropdown_visible is False

    def test_arrow_up_with_no_dropdown_does_nothing(self, widget):
        result = widget._on_arrow_up(MagicMock())
        assert result == ""
        assert widget._highlight_index == -1

    def test_enter_returns_break_when_dropdown_visible(self, widget, root):
        widget._execute_search("cho")
        # No highlight, but dropdown visible -- should return "break"
        result = widget._on_enter(MagicMock())
        assert result == "break"

    def test_arrow_handlers_return_break(self, widget, root):
        widget._execute_search("cho")
        assert widget._on_arrow_down(MagicMock()) == "break"
        assert widget._on_arrow_up(MagicMock()) == "break"


class TestEdgeCases:
    """Test edge cases."""

    def test_special_characters_in_query(self, widget, mock_items_callback):
        # Call _execute_search directly to avoid root.update() segfault risk
        widget._execute_search("salt & pepper")
        mock_items_callback.assert_called_once_with("salt & pepper")

    def test_whitespace_only_below_threshold(self, widget, mock_items_callback):
        widget._entry.insert(0, "   ")
        widget._on_key_release(MagicMock(keysym="space"))
        widget.update_idletasks()
        mock_items_callback.assert_not_called()

    def test_custom_display_key(self, widget, mock_items_callback, root):
        # Reconfigure the fixture widget to use a different display_key
        widget._display_key = "name"
        mock_items_callback.return_value = [{"name": "Test Item", "id": 1}]
        widget._execute_search("test")
        assert len(widget._result_labels) == 1

    def test_highlight_resets_on_new_search(self, widget, root):
        widget._execute_search("cho")
        widget._on_arrow_down(MagicMock())
        widget._on_arrow_down(MagicMock())
        assert widget._highlight_index == 1
        # New search resets
        widget._execute_search("cho")
        assert widget._highlight_index == -1


class TestCleanup:
    """Test widget destruction and cleanup.

    IMPORTANT: These tests create/destroy separate widgets which can corrupt
    tkinter state. They run LAST to avoid affecting other test classes.
    """

    def test_destroy_cancels_debounce(self, widget):
        # Use the fixture widget to avoid creating additional CTkToplevel windows
        widget._entry.insert(0, "cho")
        widget._on_key_release(MagicMock(keysym="o"))
        assert widget._debounce_id is not None
        # Destroy before debounce fires -- should not crash
        widget.destroy()

    def test_destroy_cleans_up_dropdown(self, widget):
        widget._execute_search("cho")
        assert widget._dropdown is not None
        dropdown = widget._dropdown
        widget.destroy()
        # Dropdown should be destroyed
        assert not dropdown.winfo_exists()
