"""BaseDashboard - Abstract base class for mode dashboards.

Each mode has a dashboard at the top that shows:
- Mode-specific statistics and counts
- Quick action buttons
- Collapsible interface to save screen space
"""

from typing import Any, Callable, Dict, List, Optional
from abc import ABC, abstractmethod
import customtkinter as ctk


class BaseDashboard(ctk.CTkFrame, ABC):
    """Abstract base class for mode-specific dashboards.

    A dashboard shows summary information at the top of each mode.
    It can be collapsed to save screen space.

    Attributes:
        is_collapsed: Whether the dashboard content is hidden
        stats_frame: Container for statistics widgets
        actions_frame: Container for quick action buttons
    """

    def __init__(self, master: Any, **kwargs):
        """Initialize BaseDashboard.

        Args:
            master: Parent widget
            **kwargs: Additional arguments passed to CTkFrame
        """
        super().__init__(master, **kwargs)

        self.is_collapsed: bool = False
        self._stats: Dict[str, ctk.CTkLabel] = {}
        self._stat_values: Dict[str, ctk.CTkLabel] = {}

        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Create header with toggle button
        self._create_header()

        # Create content frame (can be collapsed)
        self._create_content()

    def _create_header(self) -> None:
        """Create the dashboard header with title and toggle button."""
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        self.header_frame.grid_columnconfigure(1, weight=1)

        # Toggle button
        self._toggle_button = ctk.CTkButton(
            self.header_frame,
            text="-",
            width=30,
            height=25,
            command=self.toggle
        )
        self._toggle_button.grid(row=0, column=0, padx=(0, 10))

        # Dashboard title
        self._title_label = ctk.CTkLabel(
            self.header_frame,
            text="Dashboard",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self._title_label.grid(row=0, column=1, sticky="w")

        # Refresh button on the right
        self._refresh_button = ctk.CTkButton(
            self.header_frame,
            text="Refresh",
            width=70,
            height=25,
            command=self.refresh
        )
        self._refresh_button.grid(row=0, column=2)

    def _create_content(self) -> None:
        """Create the collapsible content area."""
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))

        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(1, weight=0)

        # Stats on the left
        self.stats_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.stats_frame.grid(row=0, column=0, sticky="w", padx=5)

        # Actions on the right
        self.actions_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.actions_frame.grid(row=0, column=1, sticky="e", padx=5)

    def set_title(self, title: str) -> None:
        """Set the dashboard title.

        Args:
            title: Title text to display
        """
        self._title_label.configure(text=title)

    def add_stat(self, label: str, value: str = "0") -> ctk.CTkLabel:
        """Add a statistic display to the dashboard.

        Args:
            label: Stat label (e.g., "Ingredients")
            value: Initial value (default "0")

        Returns:
            The value label widget for later updates
        """
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
        button = ctk.CTkButton(
            self.actions_frame,
            text=text,
            width=100,
            command=callback
        )
        button.pack(side="left", padx=5)
        return button

    def collapse(self) -> None:
        """Collapse the dashboard content."""
        if not self.is_collapsed:
            self.content_frame.grid_remove()
            self._toggle_button.configure(text="+")
            self.is_collapsed = True

    def expand(self) -> None:
        """Expand the dashboard content."""
        if self.is_collapsed:
            self.content_frame.grid()
            self._toggle_button.configure(text="-")
            self.is_collapsed = False

    def toggle(self) -> None:
        """Toggle the collapsed state."""
        if self.is_collapsed:
            self.expand()
        else:
            self.collapse()

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
