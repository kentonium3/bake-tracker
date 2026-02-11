"""
Type-ahead search entry widget with floating dropdown.

Reusable component that provides instant filtered search with
service-backed data fetching via caller-provided callbacks.

Features:
- Configurable minimum character threshold before search fires
- Debounce-based search triggering (default 300ms)
- Floating dropdown positioned below the entry field
- Mouse click and keyboard selection
- Escape, focus-out, and click-outside dismissal
- Configurable max results with truncation message
- No service imports -- all data via injected callbacks

Usage:
    from src.ui.widgets.type_ahead_entry import TypeAheadEntry

    entry = TypeAheadEntry(
        master=frame,
        items_callback=my_search_func,
        on_select_callback=my_select_handler,
    )
"""

import logging
from typing import Any, Callable, Dict, List, Optional

import customtkinter as ctk

logger = logging.getLogger(__name__)


class TypeAheadEntry(ctk.CTkFrame):
    """
    Type-ahead search entry with floating dropdown.

    A composite widget combining a CTkEntry with a floating CTkToplevel
    dropdown that displays filtered search results from a caller-provided
    callback. Supports mouse click and keyboard selection.

    The widget imports no service modules. All data comes through two
    injected callbacks: items_callback for searching and on_select_callback
    for handling selections.
    """

    def __init__(
        self,
        master: Any,
        items_callback: Callable[[str], List[Dict[str, Any]]],
        on_select_callback: Callable[[Dict[str, Any]], None],
        min_chars: int = 3,
        debounce_ms: int = 300,
        max_results: int = 10,
        placeholder_text: str = "Type at least 3 characters to search...",
        clear_on_select: bool = True,
        display_key: str = "display_name",
        **kwargs,
    ):
        """
        Initialize the TypeAheadEntry widget.

        Args:
            master: Parent widget
            items_callback: Called with query string, returns matching items
                as List[Dict]. Each dict must have a key matching display_key.
            on_select_callback: Called when user selects an item from dropdown.
                Receives the full item dict from items_callback.
            min_chars: Minimum characters before search fires (default 3)
            debounce_ms: Milliseconds to wait after last keystroke (default 300)
            max_results: Maximum items shown in dropdown (default 10)
            placeholder_text: Placeholder text in empty entry field
            clear_on_select: Whether to clear entry after selection (default True)
            display_key: Dict key used for display text in dropdown (default
                "display_name")
            **kwargs: Additional arguments passed to CTkFrame
        """
        super().__init__(master, fg_color="transparent")

        self._items_callback = items_callback
        self._on_select_callback = on_select_callback
        self.min_chars = min_chars
        self.debounce_ms = debounce_ms
        self.max_results = max_results
        self.clear_on_select = clear_on_select
        self._display_key = display_key

        # Internal state
        self._debounce_id: Optional[str] = None
        self._dropdown: Optional[ctk.CTkToplevel] = None
        self._dropdown_frame: Optional[ctk.CTkFrame] = None
        self._results: List[Dict[str, Any]] = []
        self._highlight_index: int = -1
        self._result_labels: List[ctk.CTkLabel] = []
        self._root_click_id: Optional[str] = None
        self._dropdown_visible: bool = False

        # Create entry widget
        self._entry = ctk.CTkEntry(
            self,
            placeholder_text=placeholder_text,
        )
        self._entry.pack(fill="x", expand=True)

        # Bind events
        self._entry.bind("<KeyRelease>", self._on_key_release)
        self._entry.bind("<Escape>", self._on_escape)
        self._entry.bind("<FocusOut>", self._on_focus_out)
        self._entry.bind("<Down>", self._on_arrow_down)
        self._entry.bind("<Up>", self._on_arrow_up)
        self._entry.bind("<Return>", self._on_enter)

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Clear entry text and close dropdown."""
        self._entry.delete(0, "end")
        self._hide_dropdown()

    def get_text(self) -> str:
        """Return current entry field text."""
        return self._entry.get()

    def set_text(self, text: str) -> None:
        """Set the entry field text programmatically."""
        self._entry.delete(0, "end")
        self._entry.insert(0, text)

    def set_focus(self) -> None:
        """Set keyboard focus to the entry field."""
        self._entry.focus_set()

    def destroy(self) -> None:
        """Clean up bindings, debounce, and toplevel before destroying."""
        if self._debounce_id:
            self.after_cancel(self._debounce_id)
            self._debounce_id = None
        self._unbind_root_click()
        if self._dropdown is not None and self._dropdown.winfo_exists():
            self._dropdown.destroy()
        self._dropdown = None
        super().destroy()

    # ------------------------------------------------------------------
    # Key event handlers
    # ------------------------------------------------------------------

    def _on_key_release(self, event) -> None:
        """Handle key release for debounced search triggering."""
        # Ignore navigation keys handled by dedicated bindings
        if event.keysym in (
            "Up", "Down", "Left", "Right", "Return", "Tab", "Escape",
            "Shift_L", "Shift_R", "Control_L", "Control_R",
            "Alt_L", "Alt_R", "Meta_L", "Meta_R", "Super_L", "Super_R",
        ):
            return

        query = self._entry.get().strip()

        # Below threshold: hide dropdown
        if len(query) < self.min_chars:
            self._hide_dropdown()
            return

        # Cancel pending debounce
        if self._debounce_id:
            self.after_cancel(self._debounce_id)

        # Schedule search after debounce delay
        self._debounce_id = self.after(
            self.debounce_ms, lambda: self._execute_search(query)
        )

    def _on_escape(self, event) -> None:
        """Close dropdown on Escape key."""
        if self._dropdown_visible:
            self._hide_dropdown()
            return "break"

    def _on_focus_out(self, event) -> None:
        """Handle focus leaving the entry field."""
        # Delay to allow dropdown clicks to process first
        self.after(150, self._check_focus_and_hide)

    def _on_arrow_down(self, event) -> str:
        """Move highlight to next item in dropdown."""
        if not self._dropdown_visible or not self._results:
            return ""
        max_idx = min(len(self._results), self.max_results) - 1
        self._highlight_index = min(self._highlight_index + 1, max_idx)
        self._update_highlight()
        return "break"

    def _on_arrow_up(self, event) -> str:
        """Move highlight to previous item in dropdown."""
        if not self._dropdown_visible or not self._results:
            return ""
        self._highlight_index = max(self._highlight_index - 1, 0)
        self._update_highlight()
        return "break"

    def _on_enter(self, event) -> Optional[str]:
        """Select highlighted item on Enter key."""
        if not self._dropdown_visible:
            return None
        if self._highlight_index < 0 or self._highlight_index >= len(self._results):
            return "break"
        item = self._results[self._highlight_index]
        self._select_item(item)
        return "break"

    # ------------------------------------------------------------------
    # Search execution
    # ------------------------------------------------------------------

    def _execute_search(self, query: str) -> None:
        """Execute the search callback and display results."""
        self._debounce_id = None

        try:
            results = self._items_callback(query)
        except Exception:
            logger.exception("Error in type-ahead items_callback")
            results = []

        self._results = results
        self._highlight_index = -1

        if not results:
            self._show_no_results(query)
        else:
            self._show_results(results)

    # ------------------------------------------------------------------
    # Dropdown management
    # ------------------------------------------------------------------

    def _create_dropdown(self) -> None:
        """Create or reuse the floating dropdown toplevel window."""
        if self._dropdown is not None and self._dropdown.winfo_exists():
            return

        self._dropdown = ctk.CTkToplevel(self)
        self._dropdown.overrideredirect(True)
        self._dropdown.wm_attributes("-topmost", True)
        self._dropdown.configure(fg_color=("gray92", "gray14"))
        # Associate with parent window
        try:
            self._dropdown.wm_transient(self.winfo_toplevel())
        except Exception:
            pass

        self._dropdown_frame = ctk.CTkFrame(
            self._dropdown, fg_color="transparent"
        )
        self._dropdown_frame.pack(fill="both", expand=True)

    def _position_dropdown(self, item_count: int) -> None:
        """Position the dropdown below the entry field."""
        self._entry.update_idletasks()

        x = self._entry.winfo_rootx()
        y = self._entry.winfo_rooty() + self._entry.winfo_height()
        width = self._entry.winfo_width()

        # Estimate height: ~32px per item
        item_height = 32
        height = item_count * item_height

        # Screen edge clamping
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        if x + width > screen_width:
            x = screen_width - width
        if y + height > screen_height:
            # Show above entry if no room below
            y = self._entry.winfo_rooty() - height

        x = max(0, x)
        y = max(0, y)

        self._dropdown.geometry(f"{width}x{height}+{x}+{y}")

    def _show_results(self, results: List[Dict[str, Any]]) -> None:
        """Display search results in the dropdown."""
        self._create_dropdown()
        self._clear_dropdown_children()

        display_results = results[: self.max_results]
        self._result_labels = []

        for result in display_results:
            text = result.get(self._display_key, str(result))
            label = ctk.CTkLabel(
                self._dropdown_frame,
                text=text,
                anchor="w",
                padx=8,
                pady=4,
                cursor="hand2",
                fg_color="transparent",
            )
            label.pack(fill="x")
            label.bind(
                "<Button-1>", lambda e, item=result: self._on_item_click(item)
            )
            # Hover effect
            label.bind("<Enter>", lambda e, lbl=label: self._on_label_hover(lbl, True))
            label.bind("<Leave>", lambda e, lbl=label: self._on_label_hover(lbl, False))
            self._result_labels.append(label)

        # Truncation message
        total_item_count = len(display_results)
        if len(results) > self.max_results:
            msg = (
                f"Showing {self.max_results} of {len(results)}+ results. "
                f"Refine search for more."
            )
            trunc_label = ctk.CTkLabel(
                self._dropdown_frame,
                text=msg,
                text_color="gray50",
                anchor="w",
                padx=8,
                pady=4,
                font=ctk.CTkFont(size=11),
            )
            trunc_label.pack(fill="x")
            total_item_count += 1

        self._position_dropdown(total_item_count)
        self._dropdown.deiconify()
        self._dropdown_visible = True
        self._bind_root_click()

    def _show_no_results(self, query: str) -> None:
        """Display 'no results' message in the dropdown."""
        self._create_dropdown()
        self._clear_dropdown_children()
        self._result_labels = []

        msg = f"No items match '{query}'"
        label = ctk.CTkLabel(
            self._dropdown_frame,
            text=msg,
            text_color="gray50",
            anchor="w",
            padx=8,
            pady=4,
            font=ctk.CTkFont(size=11, slant="italic"),
        )
        label.pack(fill="x")

        self._position_dropdown(1)
        self._dropdown.deiconify()
        self._dropdown_visible = True
        self._bind_root_click()

    def _hide_dropdown(self) -> None:
        """Hide the dropdown and reset state."""
        if self._dropdown is not None and self._dropdown.winfo_exists():
            self._dropdown.withdraw()
        self._dropdown_visible = False
        self._result_labels = []
        self._highlight_index = -1
        self._unbind_root_click()

    def _clear_dropdown_children(self) -> None:
        """Remove all children from the dropdown frame."""
        if self._dropdown_frame is not None:
            for child in self._dropdown_frame.winfo_children():
                child.destroy()

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _on_item_click(self, item: Dict[str, Any]) -> None:
        """Handle mouse click on a dropdown item."""
        self._select_item(item)

    def _select_item(self, item: Dict[str, Any]) -> None:
        """Execute selection: fire callback, optionally clear, hide dropdown."""
        self._hide_dropdown()
        if self.clear_on_select:
            self._entry.delete(0, "end")
        try:
            self._on_select_callback(item)
        except Exception:
            logger.exception("Error in type-ahead on_select_callback")

    # ------------------------------------------------------------------
    # Highlight management
    # ------------------------------------------------------------------

    def _update_highlight(self) -> None:
        """Update visual highlight on dropdown items."""
        for i, label in enumerate(self._result_labels):
            if i == self._highlight_index:
                label.configure(fg_color=("gray78", "gray30"))
            else:
                label.configure(fg_color="transparent")

    def _on_label_hover(self, label: ctk.CTkLabel, entering: bool) -> None:
        """Handle mouse hover on dropdown labels."""
        # Don't override keyboard highlight
        idx = self._result_labels.index(label) if label in self._result_labels else -1
        if idx == self._highlight_index:
            return
        if entering:
            label.configure(fg_color=("gray85", "gray25"))
        else:
            label.configure(fg_color="transparent")

    # ------------------------------------------------------------------
    # Click-outside detection
    # ------------------------------------------------------------------

    def _bind_root_click(self) -> None:
        """Bind click detection on root window for click-outside dismissal."""
        if self._root_click_id is not None:
            return  # Already bound
        try:
            self._root_click_id = self.winfo_toplevel().bind(
                "<Button-1>", self._on_root_click, add="+"
            )
        except Exception:
            pass

    def _unbind_root_click(self) -> None:
        """Unbind click-outside detection."""
        if self._root_click_id is not None:
            try:
                self.winfo_toplevel().unbind("<Button-1>", self._root_click_id)
            except Exception:
                pass
            self._root_click_id = None

    def _on_root_click(self, event) -> None:
        """Check if click is outside entry and dropdown, dismiss if so."""
        if not self._dropdown_visible:
            return

        click_x, click_y = event.x_root, event.y_root

        # Check if click is inside entry
        ex = self._entry.winfo_rootx()
        ey = self._entry.winfo_rooty()
        ew = self._entry.winfo_width()
        eh = self._entry.winfo_height()
        if ex <= click_x <= ex + ew and ey <= click_y <= ey + eh:
            return

        # Check if click is inside dropdown
        if self._dropdown is not None and self._dropdown.winfo_exists():
            dx = self._dropdown.winfo_rootx()
            dy = self._dropdown.winfo_rooty()
            dw = self._dropdown.winfo_width()
            dh = self._dropdown.winfo_height()
            if dx <= click_x <= dx + dw and dy <= click_y <= dy + dh:
                return

        # Click is outside both -- dismiss
        self._hide_dropdown()

    # ------------------------------------------------------------------
    # Focus management
    # ------------------------------------------------------------------

    def _check_focus_and_hide(self) -> None:
        """Hide dropdown if focus has truly left the widget."""
        if not self._dropdown_visible:
            return
        try:
            focused = self.focus_get()
        except Exception:
            focused = None

        # If focus is on entry, keep dropdown open
        if focused == self._entry:
            return

        # If focus is on a dropdown child, keep it open
        if (
            self._dropdown is not None
            and self._dropdown.winfo_exists()
            and focused is not None
        ):
            try:
                focus_root = str(focused)
                dropdown_root = str(self._dropdown)
                if focus_root.startswith(dropdown_root):
                    return
            except Exception:
                pass

        self._hide_dropdown()
