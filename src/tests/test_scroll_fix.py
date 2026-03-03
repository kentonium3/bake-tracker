"""Tests for Tk 9.0 touchpad scroll fix utilities."""

from src.utils.scroll_fix import _extract_touchpad_deltas, _has_touchpad_scroll_support


class TestExtractTouchpadDeltas:
    """Tests for delta extraction from TouchpadScroll keycode."""

    def test_positive_vertical_only(self):
        """Scroll down: dy > 0, dx = 0."""
        # Low 16 bits = 5 (dy), high 16 bits = 0 (dx)
        delta = 5
        dx, dy = _extract_touchpad_deltas(delta)
        assert dx == 0
        assert dy == 5

    def test_negative_vertical_only(self):
        """Scroll up: dy < 0, dx = 0."""
        # -3 as signed 16-bit = 0xFFFD, packed in low bits
        delta = 0x0000FFFD
        dx, dy = _extract_touchpad_deltas(delta)
        assert dx == 0
        assert dy == -3

    def test_positive_horizontal_only(self):
        """Scroll right: dx > 0, dy = 0."""
        # High 16 bits = 7 (dx), low 16 bits = 0 (dy)
        delta = 7 << 16
        dx, dy = _extract_touchpad_deltas(delta)
        assert dx == 7
        assert dy == 0

    def test_negative_horizontal_only(self):
        """Scroll left: dx < 0, dy = 0."""
        # -2 as unsigned 16-bit = 0xFFFE, packed in high bits
        delta = 0xFFFE0000
        dx, dy = _extract_touchpad_deltas(delta)
        assert dx == -2
        assert dy == 0

    def test_both_axes(self):
        """Diagonal scroll: both dx and dy set."""
        # dx = 3 (high), dy = -4 (low)
        # -4 as unsigned 16-bit = 0xFFFC
        delta = (3 << 16) | 0xFFFC
        dx, dy = _extract_touchpad_deltas(delta)
        assert dx == 3
        assert dy == -4

    def test_zero_delta(self):
        """No movement."""
        dx, dy = _extract_touchpad_deltas(0)
        assert dx == 0
        assert dy == 0

    def test_both_negative(self):
        """Both axes negative."""
        # dx = -1 (0xFFFF), dy = -1 (0xFFFF)
        delta = 0xFFFFFFFF
        dx, dy = _extract_touchpad_deltas(delta)
        assert dx == -1
        assert dy == -1


class TestHasTouchpadScrollSupport:
    """Tests for Tk version detection."""

    def test_returns_bool(self):
        """Function returns a boolean."""
        result = _has_touchpad_scroll_support()
        assert isinstance(result, bool)
