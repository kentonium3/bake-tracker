"""
Tk 9.0 touchpad scroll fix for CustomTkinter.

Tk 9.0 introduced a new <TouchpadScroll> event for two-finger trackpad
gestures on macOS (TIP 684). These gestures no longer generate <MouseWheel>
events. CustomTkinter 5.2.2 only binds <MouseWheel>, so trackpad scrolling
is broken for all CTkScrollableFrame instances.

This module monkey-patches CTkScrollableFrame to also handle <TouchpadScroll>,
restoring trackpad scrolling on macOS with Tk 9.0+.

Call apply_touchpad_scroll_fix() once at app startup, before creating any
CTkScrollableFrame instances.
"""

import ctypes
import sys
import tkinter


def _has_touchpad_scroll_support() -> bool:
    """Check if the current Tk version supports <TouchpadScroll> (Tk 9.0+)."""
    try:
        return tkinter.TkVersion >= 9.0
    except Exception:
        return False


def _extract_touchpad_deltas(delta: int) -> tuple:
    """
    Extract Δx and Δy from the TouchpadScroll keycode field.

    Tk 9.0 packs both deltas into a 32-bit integer:
    - High 16 bits: Δx (horizontal)
    - Low 16 bits: Δy (vertical)
    Both are signed 16-bit values.
    """
    # Convert to unsigned 32-bit first to handle sign correctly
    unsigned = delta & 0xFFFFFFFF
    dx = ctypes.c_int16((unsigned >> 16) & 0xFFFF).value
    dy = ctypes.c_int16(unsigned & 0xFFFF).value
    return dx, dy


def apply_touchpad_scroll_fix() -> None:
    """
    Monkey-patch CTkScrollableFrame to handle <TouchpadScroll> events.

    Must be called after ctk.CTk() creates the root window but before
    any CTkScrollableFrame instances are created (or it patches the
    __init__ to bind on future instances).
    """
    if sys.platform != "darwin":
        return

    if not _has_touchpad_scroll_support():
        return

    from customtkinter.windows.widgets.ctk_scrollable_frame import CTkScrollableFrame

    _original_init = CTkScrollableFrame.__init__

    def _patched_init(self, *args, **kwargs):
        _original_init(self, *args, **kwargs)
        self.bind_all("<TouchpadScroll>", self._touchpad_scroll_all, add="+")

    def _touchpad_scroll_all(self, event):
        if self.check_if_master_is_canvas(event.widget):
            _dx, dy = _extract_touchpad_deltas(event.delta)
            if dy != 0:
                if self._parent_canvas.yview() != (0.0, 1.0):
                    self._parent_canvas.yview("scroll", -dy, "units")
            if _dx != 0 and self._shift_pressed:
                if self._parent_canvas.xview() != (0.0, 1.0):
                    self._parent_canvas.xview("scroll", -_dx, "units")

    CTkScrollableFrame.__init__ = _patched_init
    CTkScrollableFrame._touchpad_scroll_all = _touchpad_scroll_all
