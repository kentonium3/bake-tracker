"""BaseDashboard - Abstract base class for mode dashboards.

Each mode has a dashboard at the top that shows:
- Mode name with inline statistics
- Compact single-line header format
"""

from typing import Any, Callable, Dict, List, Optional
from abc import ABC, abstractmethod
import customtkinter as ctk


class BaseDashboard(ctk.CTkFrame, ABC):
    """Abstract base class for mode-specific dashboards.

    A dashboard shows summary information at the top of each mode
    in a compact single-line format with inline statistics.

    Attributes:
        mode_name: Display name for the mode (e.g., "CATALOG")
        mode_icon: Optional icon/emoji for the mode
        stats_frame: Container for statistics widgets (legacy support)
        actions_frame: Container for quick action buttons (legacy support)
    """

    def __init__(self, master: Any, **kwargs):
        """Initialize BaseDashboard.

        Args:
            master: Parent widget
            **kwargs: Additional arguments passed to CTkFrame
        """
        super().__init__(master, **kwargs)

        # Mode identity - preserve if subclass already set, otherwise use defaults
        if not hasattr(self, "mode_name") or self.mode_name is None:
            self.mode_name: str = "Dashboard"
        if not hasattr(self, "mode_icon") or self.mode_icon is None:
            self.mode_icon: str = ""

        # Legacy stat tracking for backwards compatibility
        self._stats: Dict[str, ctk.CTkLabel] = {}
        self._stat_values: Dict[str, ctk.CTkLabel] = {}

        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Create compact header
        self._create_header()

        # Create content frame for legacy stats/actions (hidden by default)
        self._create_content()

    def _create_header(self) -> None:
        """Create the compact single-line dashboard header."""
        self.header_frame = ctk.CTkFrame(self, height=40, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(5, 0))
        self.header_frame.grid_propagate(False)  # Maintain fixed height

        # Single line with mode name and inline stats
        self.header_label = ctk.CTkLabel(
            self.header_frame,
            text=self._get_header_text(),
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        self.header_label.pack(side="left", padx=10, pady=8)

    def _create_content(self) -> None:
        """Create the content area for legacy stats/actions.

        This frame is kept for backwards compatibility with subclasses
        that use add_stat() and add_action() methods.
        Hidden by default to maximize vertical space for data grids.
        """
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        # Don't grid by default - will be shown when stats/actions are added
        self._content_visible = False

        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(1, weight=0)

        # Stats on the left (legacy)
        self.stats_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.stats_frame.grid(row=0, column=0, sticky="w", padx=5)

        # Actions on the right (legacy)
        self.actions_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.actions_frame.grid(row=0, column=1, sticky="e", padx=5)

    def _format_inline_stats(self) -> str:
        """Format statistics for inline display in header.

        Override in subclasses to return mode-specific stats string.
        Example: "413 ingredients - 153 products - 87 recipes"

        Returns:
            Formatted stats string, or empty string if no stats
        """
        return ""

    def _get_header_text(self) -> str:
        """Build complete header text with mode name and stats.

        Returns:
            Header text like "CATALOG  413 ingredients - 153 products"
        """
        prefix = f"{self.mode_icon} {self.mode_name}".strip()
        stats = self._format_inline_stats()
        if stats:
            return f"{prefix}  {stats}"
        return prefix

    def _update_header_text(self) -> None:
        """Refresh the header label with current stats."""
        if hasattr(self, "header_label"):
            self.header_label.configure(text=self._get_header_text())

    def on_show(self) -> None:
        """Called when this dashboard becomes visible.

        Automatically refreshes stats and updates header display.
        Subclasses should call super().on_show() if they override.
        """
        self._refresh_stats()
        self._update_header_text()

    def _refresh_stats(self) -> None:
        """Refresh statistics from database.

        Override in subclasses to query and update stats.
        Called automatically by on_show().
        """
        # Default implementation calls legacy refresh() for backwards compat
        try:
            self.refresh()
        except Exception:
            pass

    def set_title(self, title: str) -> None:
        """Set the dashboard title/mode name.

        Args:
            title: Title text to display (e.g., "CATALOG Dashboard")
        """
        # Extract mode name from title like "CATALOG Dashboard"
        if " Dashboard" in title:
            self.mode_name = title.replace(" Dashboard", "").strip()
        elif " - " in title:
            # Handle format like "OBSERVE Dashboard - Event Readiness"
            self.mode_name = title.split(" - ")[0].replace(" Dashboard", "").strip()
        else:
            self.mode_name = title
        self._update_header_text()

    def _show_content_frame(self) -> None:
        """Show the legacy content frame if not already visible."""
        if not self._content_visible:
            self.content_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))
            self._content_visible = True

    def add_stat(self, label: str, value: str = "0") -> ctk.CTkLabel:
        """Add a statistic display to the dashboard.

        Args:
            label: Stat label (e.g., "Ingredients")
            value: Initial value (default "0")

        Returns:
            The value label widget for later updates
        """
        self._show_content_frame()
        stat_frame = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        stat_frame.pack(side="left", padx=10)

        # Value (larger font)
        value_label = ctk.CTkLabel(
            stat_frame,
            text=value,
            font=ctk.CTkFont(size=18, weight="bold")
        )
        value_label.pack()

        # Label (smaller)
        label_widget = ctk.CTkLabel(
            stat_frame,
            text=label,
            font=ctk.CTkFont(size=11)
        )
        label_widget.pack()

        self._stats[label] = label_widget
        self._stat_values[label] = value_label

        return value_label

    def update_stat(self, label: str, value: str) -> None:
        """Update a statistic value.

        Args:
            label: Stat label to update
            value: New value to display
        """
        if label in self._stat_values:
            self._stat_values[label].configure(text=value)

    def get_stat_value(self, label: str) -> Optional[str]:
        """Get the current value of a statistic.

        Args:
            label: Stat label

        Returns:
            Current value string, or None if not found
        """
        if label in self._stat_values:
            return self._stat_values[label].cget("text")
        return None

    def add_action(self, text: str, callback: Callable) -> ctk.CTkButton:
        """Add a quick action button to the dashboard.

        Args:
            text: Button label
            callback: Function to call when clicked

        Returns:
            The created button widget
        """
        self._show_content_frame()
        button = ctk.CTkButton(
            self.actions_frame,
            text=text,
            width=100,
            command=callback
        )
        button.pack(side="left", padx=5)
        return button

    @abstractmethod
    def refresh(self) -> None:
        """Refresh the dashboard data.

        Must be implemented by subclasses to update their specific stats.
        """
        pass

    def clear_stats(self) -> None:
        """Clear all statistics from the dashboard."""
        for widget in self.stats_frame.winfo_children():
            widget.destroy()
        self._stats.clear()
        self._stat_values.clear()

    def clear_actions(self) -> None:
        """Clear all action buttons from the dashboard."""
        for widget in self.actions_frame.winfo_children():
            widget.destroy()
