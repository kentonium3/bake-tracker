"""
Unit tests for TypeAheadComboBox widget.

Tests cover:
- Filter algorithm correctness
- Word boundary prioritization
- Case-insensitive matching
- reset_values functionality
- min_chars threshold behavior

Note: Full widget tests require a Tk root. These tests focus on
the filtering algorithm which can be tested without GUI.
"""

import pytest

# Mock Tkinter before importing the widget
from unittest.mock import MagicMock, patch


class MockEntry:
    """Mock for CTkEntry widget."""

    def __init__(self):
        self._bindings = {}

    def bind(self, event, callback):
        self._bindings[event] = callback


class MockComboBox:
    """Mock for CTkComboBox widget."""

    def __init__(self, master, **kwargs):
        self.values = kwargs.get("values", [])
        self._command = kwargs.get("command")
        self._entry = MockEntry()
        self._current_value = ""

    def pack(self, **kwargs):
        pass

    def configure(self, **kwargs):
        if "values" in kwargs:
            self.values = kwargs["values"]

    def get(self):
        return self._current_value

    def set(self, value):
        self._current_value = value

    def cget(self, attribute):
        if attribute == "values":
            return self.values
        return None


class MockFrame:
    """Mock for CTkFrame widget."""

    def __init__(self, master, **kwargs):
        pass


@pytest.fixture
def mock_ctk():
    """Patch customtkinter before importing TypeAheadComboBox."""
    mock_module = MagicMock()
    mock_module.CTkFrame = MockFrame
    mock_module.CTkComboBox = MockComboBox

    with patch.dict("sys.modules", {"customtkinter": mock_module}):
        yield mock_module


@pytest.fixture
def widget_class(mock_ctk):
    """Import TypeAheadComboBox with mocked customtkinter."""
    # Import after mocking
    from src.ui.widgets.type_ahead_combobox import TypeAheadComboBox

    return TypeAheadComboBox


class TestFilterAlgorithm:
    """Test the filtering algorithm directly."""

    def test_word_boundary_priority(self, widget_class):
        """Word boundary matches should come before contains matches."""
        # Create widget with test values
        widget = widget_class.__new__(widget_class)
        widget.full_values = ["AP Flour", "Maple Syrup", "Apple Cider"]
        widget.min_chars = 2
        widget.filtered = False
        widget._command = None

        # Test filter
        result = widget._filter_values("ap")

        # 'AP Flour' and 'Apple' start with 'ap' (word boundary)
        # 'Maple' contains 'ap' but not at word boundary
        assert "AP Flour" in result
        assert "Apple Cider" in result
        assert "Maple Syrup" in result

        # Word boundary matches should come first
        ap_flour_idx = result.index("AP Flour")
        apple_idx = result.index("Apple Cider")
        maple_idx = result.index("Maple Syrup")

        # Both word boundary matches before contains match
        assert ap_flour_idx < maple_idx
        assert apple_idx < maple_idx

    def test_case_insensitive(self, widget_class):
        """Matching should be case-insensitive."""
        widget = widget_class.__new__(widget_class)
        widget.full_values = ["FLOUR", "flour", "Flour"]
        widget.min_chars = 2
        widget.filtered = False
        widget._command = None

        result = widget._filter_values("flour")
        assert len(result) == 3
        assert "FLOUR" in result
        assert "flour" in result
        assert "Flour" in result

    def test_case_insensitive_typed(self, widget_class):
        """Typed text matching should be case-insensitive."""
        widget = widget_class.__new__(widget_class)
        widget.full_values = ["Sugar", "Syrup"]
        widget.min_chars = 2
        widget.filtered = False
        widget._command = None

        # Uppercase typed text should match lowercase values
        result = widget._filter_values("SU")
        assert len(result) == 1
        assert "Sugar" in result

    def test_empty_typed_returns_empty(self, widget_class):
        """Empty typed string returns empty list."""
        widget = widget_class.__new__(widget_class)
        widget.full_values = ["Flour", "Sugar"]
        widget.min_chars = 2
        widget.filtered = False
        widget._command = None

        result = widget._filter_values("")
        assert result == []

    def test_no_matches_returns_empty(self, widget_class):
        """No matches returns empty list."""
        widget = widget_class.__new__(widget_class)
        widget.full_values = ["Flour", "Sugar"]
        widget.min_chars = 2
        widget.filtered = False
        widget._command = None

        result = widget._filter_values("xyz")
        assert result == []

    def test_single_character_match(self, widget_class):
        """Single character match at word boundary."""
        widget = widget_class.__new__(widget_class)
        widget.full_values = ["Flour", "Sugar", "Salt"]
        widget.min_chars = 1
        widget.filtered = False
        widget._command = None

        result = widget._filter_values("s")
        assert len(result) == 2
        assert "Sugar" in result
        assert "Salt" in result
        assert "Flour" not in result

    def test_multi_word_values(self, widget_class):
        """Multi-word values match on any word."""
        widget = widget_class.__new__(widget_class)
        widget.full_values = [
            "All-Purpose Flour",
            "Bread Flour",
            "King Arthur Flour",
        ]
        widget.min_chars = 2
        widget.filtered = False
        widget._command = None

        # "ki" should match "King" at word boundary
        result = widget._filter_values("ki")
        assert len(result) == 1
        assert "King Arthur Flour" in result

    def test_hyphenated_word_boundary(self, widget_class):
        """Hyphenated words split correctly."""
        widget = widget_class.__new__(widget_class)
        widget.full_values = ["All-Purpose Flour", "Self-Rising Flour"]
        widget.min_chars = 2
        widget.filtered = False
        widget._command = None

        # Note: Our simple split() won't handle hyphens as word boundaries
        # "all-purpose" is one word, so "pu" won't be word boundary
        result = widget._filter_values("pu")

        # "pu" is contained in "purpose" but not at word boundary
        assert "All-Purpose Flour" in result


class TestResetValues:
    """Test reset_values functionality."""

    def test_reset_values_updates_list(self, widget_class):
        """reset_values should update full_values."""
        widget = widget_class.__new__(widget_class)
        widget.full_values = ["A", "B"]
        widget.min_chars = 2
        widget.filtered = True
        widget._command = None
        widget._combobox = MockComboBox(None, values=["A", "B"])

        widget.reset_values(["X", "Y", "Z"])

        assert widget.full_values == ["X", "Y", "Z"]
        assert widget._combobox.values == ["X", "Y", "Z"]
        assert widget.filtered is False

    def test_reset_values_clears_filter_state(self, widget_class):
        """reset_values should clear filtered state."""
        widget = widget_class.__new__(widget_class)
        widget.full_values = ["A", "B"]
        widget.min_chars = 2
        widget.filtered = True
        widget._command = None
        widget._combobox = MockComboBox(None, values=["A"])

        widget.reset_values(["X", "Y"])

        assert widget.filtered is False


class TestMinChars:
    """Test min_chars threshold behavior."""

    def test_min_chars_default(self, widget_class):
        """Default min_chars should be 2."""
        widget = widget_class.__new__(widget_class)
        widget.min_chars = 2  # Default
        widget.full_values = ["Flour", "Sugar"]
        widget.filtered = False
        widget._command = None

        # Single character should not filter (below threshold)
        # This is tested in _on_key_release, not _filter_values
        # _filter_values always returns results regardless of min_chars
        result = widget._filter_values("f")
        assert len(result) == 1  # Still matches

    def test_min_chars_one(self, widget_class):
        """min_chars=1 for category dropdowns."""
        widget = widget_class.__new__(widget_class)
        widget.min_chars = 1
        widget.full_values = ["Baking", "Dairy", "Spices"]
        widget.filtered = False
        widget._command = None

        # With min_chars=1, single character triggers filter
        result = widget._filter_values("d")
        assert len(result) == 1
        assert "Dairy" in result


class TestWidgetInterface:
    """Test widget interface methods."""

    def test_get_returns_combobox_value(self, widget_class):
        """get() should return combobox value."""
        widget = widget_class.__new__(widget_class)
        widget._combobox = MockComboBox(None)
        widget._combobox._current_value = "Test Value"

        assert widget.get() == "Test Value"

    def test_set_updates_combobox_value(self, widget_class):
        """set() should update combobox value."""
        widget = widget_class.__new__(widget_class)
        widget._combobox = MockComboBox(None)

        widget.set("New Value")

        assert widget._combobox._current_value == "New Value"

    def test_configure_updates_values(self, widget_class):
        """configure(values=...) should update full_values."""
        widget = widget_class.__new__(widget_class)
        widget.full_values = ["A", "B"]
        widget.filtered = True
        widget._combobox = MockComboBox(None, values=["A", "B"])

        widget.configure(values=["X", "Y", "Z"])

        assert widget.full_values == ["X", "Y", "Z"]
        assert widget.filtered is False

    def test_cget_values(self, widget_class):
        """cget('values') should return full_values."""
        widget = widget_class.__new__(widget_class)
        widget.full_values = ["A", "B", "C"]
        widget._combobox = MockComboBox(None)

        assert widget.cget("values") == ["A", "B", "C"]
