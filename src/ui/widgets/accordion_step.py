"""
AccordionStep widget for multi-step wizard UIs.

Provides a collapsible step with three states: locked, active, completed.
Used by the Finished Goods Builder dialog to guide users through a
multi-step creation/edit flow.
"""

from typing import Callable, Optional

import customtkinter as ctk


# State constants
STATE_LOCKED = "locked"
STATE_ACTIVE = "active"
STATE_COMPLETED = "completed"

# Unicode status icons
_ICON_LOCK = "\u2022"  # Bullet (simpler than emoji for cross-platform)
_ICON_ARROW = "\u25B6"  # Right-pointing triangle
_ICON_CHECK = "\u2713"  # Checkmark


class AccordionStep(ctk.CTkFrame):
    """A collapsible step widget for multi-step wizard UIs.

    Each step has a header (step number, title, status icon, summary, Change button)
    and a content frame where the caller adds step-specific widgets.

    States:
        locked: Greyed out, not interactive, content hidden
        active: Highlighted, content visible, Change button hidden
        completed: Normal color, content hidden, Change button visible, summary shown
    """

    def __init__(
        self,
        parent,
        step_number: int,
        title: str,
        on_change_click: Optional[Callable[[int], None]] = None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)

        self.step_number = step_number
        self._title = title
        self._on_change_click = on_change_click
        self._state = STATE_LOCKED

        self._build_header()
        self._build_content()
        self._update_visual_state()

    def _build_header(self) -> None:
        """Build the header frame with step number, title, icon, summary, and Change button."""
        self.header_frame = ctk.CTkFrame(self, corner_radius=6)
        self.header_frame.pack(fill="x", padx=5, pady=(5, 0))

        # Step number label
        self._step_number_label = ctk.CTkLabel(
            self.header_frame,
            text=str(self.step_number),
            width=30,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="center",
        )
        self._step_number_label.pack(side="left", padx=(10, 5), pady=8)

        # Title label
        self._title_label = ctk.CTkLabel(
            self.header_frame,
            text=self._title,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        self._title_label.pack(side="left", padx=(0, 5), pady=8)

        # Status icon label
        self._status_icon_label = ctk.CTkLabel(
            self.header_frame,
            text="",
            width=25,
            anchor="center",
        )
        self._status_icon_label.pack(side="left", padx=(5, 5), pady=8)

        # Change button (packed on right side, initially hidden)
        self._change_button = ctk.CTkButton(
            self.header_frame,
            text="Change",
            width=70,
            height=28,
            command=self._handle_change_click,
        )
        # Not packed initially - shown only in completed state

        # Summary label (takes remaining space, packed after icon)
        self._summary_label = ctk.CTkLabel(
            self.header_frame,
            text="",
            anchor="w",
            text_color="gray",
        )
        self._summary_label.pack(side="left", expand=True, fill="x", padx=(5, 5), pady=8)

    def _build_content(self) -> None:
        """Build the content frame (initially hidden)."""
        self.content_frame = ctk.CTkFrame(self, corner_radius=4)
        # Content starts hidden; expand() will pack it

    # -- State management --

    @property
    def state(self) -> str:
        """Return the current state."""
        return self._state

    def set_state(self, state: str) -> None:
        """Set the widget state and update visual indicators.

        Args:
            state: One of STATE_LOCKED, STATE_ACTIVE, STATE_COMPLETED
        """
        if state not in (STATE_LOCKED, STATE_ACTIVE, STATE_COMPLETED):
            raise ValueError(f"Invalid state: {state!r}")
        self._state = state
        self._update_visual_state()

    def _update_visual_state(self) -> None:
        """Refresh all visual elements based on current state."""
        if self._state == STATE_LOCKED:
            self._status_icon_label.configure(text=_ICON_LOCK)
            self._title_label.configure(
                text_color=("gray60", "gray40"),
            )
            self._step_number_label.configure(
                text_color=("gray60", "gray40"),
            )
            self._status_icon_label.configure(
                text_color=("gray60", "gray40"),
            )
            self.header_frame.configure(
                fg_color=("gray88", "gray20"),
            )
            self._change_button.pack_forget()
            self.content_frame.pack_forget()

        elif self._state == STATE_ACTIVE:
            self._status_icon_label.configure(text=_ICON_ARROW)
            self._title_label.configure(
                text_color=("gray10", "gray90"),
            )
            self._step_number_label.configure(
                text_color=("gray10", "gray90"),
            )
            self._status_icon_label.configure(
                text_color=("gray10", "gray90"),
            )
            self.header_frame.configure(
                fg_color=("gray78", "gray28"),
            )
            self._change_button.pack_forget()
            self.content_frame.pack(
                fill="both", expand=True, padx=10, pady=(0, 10)
            )

        elif self._state == STATE_COMPLETED:
            self._status_icon_label.configure(text=_ICON_CHECK)
            self._title_label.configure(
                text_color=("gray10", "gray90"),
            )
            self._step_number_label.configure(
                text_color=("gray10", "gray90"),
            )
            self._status_icon_label.configure(
                text_color=("green", "green"),
            )
            self.header_frame.configure(
                fg_color=("gray82", "gray25"),
            )
            self.content_frame.pack_forget()
            self._change_button.pack(side="right", padx=(5, 10), pady=8)

    # -- Summary --

    def set_summary(self, text: str) -> None:
        """Update the summary label text shown in the header."""
        self._summary_label.configure(text=text)

    # -- Expand / Collapse --

    def expand(self) -> None:
        """Show the content frame and set state to active."""
        self.set_state(STATE_ACTIVE)

    def collapse(self) -> None:
        """Hide the content frame. Does not change state."""
        self.content_frame.pack_forget()

    @property
    def is_expanded(self) -> bool:
        """Return True if the content frame is currently visible (packed)."""
        return bool(self.content_frame.winfo_manager())

    # -- Convenience --

    def mark_completed(self, summary: str) -> None:
        """Collapse content, set completed state, and display summary.

        Args:
            summary: Text to display in the header (e.g., "3 items selected")
        """
        self.collapse()
        self.set_state(STATE_COMPLETED)
        self.set_summary(summary)

    # -- Internal --

    def _handle_change_click(self) -> None:
        """Handle the Change button click."""
        if self._on_change_click is not None:
            self._on_change_click(self.step_number)
