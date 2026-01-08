"""BaseMode - Abstract base class for mode containers.

Implements mode container functionality for the 5-mode workflow:
- CATALOG, PLAN, SHOP, PRODUCE, OBSERVE

Each mode contains:
- A dashboard at the top with mode-specific summary info
- A tabview with mode-specific tabs
- State management for tab selection
"""

from typing import Any, Optional, Dict, List, TYPE_CHECKING
from abc import ABC, abstractmethod
import customtkinter as ctk

if TYPE_CHECKING:
    from ui.dashboards.base_dashboard import BaseDashboard


class BaseMode(ctk.CTkFrame, ABC):
    """Abstract base class for mode containers.

    A mode is a top-level navigation container representing a work activity.
    Each mode contains a dashboard and a set of tabs.

    Attributes:
        name: Mode identifier (CATALOG, PLAN, SHOP, PRODUCE, OBSERVE)
        dashboard: Mode-specific dashboard widget
        tabview: CTkTabview containing mode's tabs
        current_tab_index: Currently selected tab index (for state preservation)
    """

    def __init__(
        self,
        master: Any,
        name: str,
        **kwargs
    ):
        """Initialize BaseMode.

        Args:
            master: Parent widget
            name: Mode identifier (e.g., "CATALOG", "PLAN")
            **kwargs: Additional arguments passed to CTkFrame
        """
        super().__init__(master, **kwargs)

        self.name = name
        self.dashboard: Optional["BaseDashboard"] = None
        self.tabview: Optional[ctk.CTkTabview] = None
        self._tab_names: List[str] = []
        self._tab_widgets: Dict[str, Any] = {}
        self._current_tab_index: int = 0

        # Configure grid for mode layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # Tabview row expands

    def set_dashboard(self, dashboard: "BaseDashboard") -> None:
        """Set the mode's dashboard widget.

        Args:
            dashboard: BaseDashboard instance for this mode
        """
        self.dashboard = dashboard
        self.dashboard.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))

    def create_tabview(self) -> ctk.CTkTabview:
        """Create and configure the mode's tabview.

        Returns:
            The created CTkTabview instance
        """
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 10))

        # Bind tab change event for state tracking
        self.tabview.configure(command=self._on_tab_changed)

        return self.tabview

    def add_tab(self, name: str, tab_widget: Any) -> ctk.CTkFrame:
        """Add a tab to the mode's tabview.

        Args:
            name: Tab name/label
            tab_widget: Widget to place in the tab

        Returns:
            The tab frame container
        """
        if self.tabview is None:
            self.create_tabview()

        # Add tab to tabview
        tab_frame = self.tabview.add(name)
        self._tab_names.append(name)

        # Configure tab frame
        tab_frame.grid_columnconfigure(0, weight=1)
        tab_frame.grid_rowconfigure(0, weight=1)

        # Place widget in tab
        tab_widget.grid(row=0, column=0, sticky="nsew")
        self._tab_widgets[name] = tab_widget

        return tab_frame

    def get_tab_widget(self, name: str) -> Optional[Any]:
        """Get a tab's widget by name.

        Args:
            name: Tab name

        Returns:
            The widget in the tab, or None if not found
        """
        return self._tab_widgets.get(name)

    def _on_tab_changed(self) -> None:
        """Handle tab selection change."""
        if self.tabview:
            current_tab = self.tabview.get()
            if current_tab in self._tab_names:
                self._current_tab_index = self._tab_names.index(current_tab)

    def get_current_tab_index(self) -> int:
        """Get the currently selected tab index.

        Returns:
            Index of the current tab (0-based)
        """
        return self._current_tab_index

    def set_current_tab_index(self, index: int) -> None:
        """Set the current tab by index (for state restoration).

        Args:
            index: Tab index to select (0-based)
        """
        if self.tabview and 0 <= index < len(self._tab_names):
            self._current_tab_index = index
            self.tabview.set(self._tab_names[index])

    def get_current_tab_name(self) -> Optional[str]:
        """Get the name of the currently selected tab.

        Returns:
            Name of the current tab, or None if no tabs
        """
        if self.tabview:
            return self.tabview.get()
        return None

    def set_current_tab_by_name(self, name: str) -> None:
        """Set the current tab by name.

        Args:
            name: Tab name to select
        """
        if self.tabview and name in self._tab_names:
            self.tabview.set(name)
            self._current_tab_index = self._tab_names.index(name)

    def activate(self) -> None:
        """Called when mode becomes active.

        Override in subclasses for mode-specific activation logic.
        Default behavior: refresh the dashboard.
        """
        self.refresh_dashboard()

    def deactivate(self) -> None:
        """Called when mode becomes inactive.

        Override in subclasses for mode-specific deactivation logic.
        Default behavior: no-op.
        """
        pass

    def refresh_dashboard(self) -> None:
        """Refresh the mode's dashboard data and update header display."""
        if self.dashboard:
            # Call on_show() to refresh stats AND update header text
            if hasattr(self.dashboard, "on_show"):
                self.dashboard.on_show()
            else:
                self.dashboard.refresh()

    def refresh_current_tab(self) -> None:
        """Refresh the currently active tab."""
        current_tab = self.get_current_tab_name()
        if current_tab:
            widget = self._tab_widgets.get(current_tab)
            if widget and hasattr(widget, "refresh"):
                widget.refresh()

    def refresh_all_tabs(self) -> None:
        """Refresh all tabs in the mode."""
        for widget in self._tab_widgets.values():
            if hasattr(widget, "refresh"):
                widget.refresh()

    @abstractmethod
    def setup_tabs(self) -> None:
        """Set up the mode's tabs.

        Must be implemented by subclasses to add their specific tabs.
        """
        pass

    @abstractmethod
    def setup_dashboard(self) -> None:
        """Set up the mode's dashboard.

        Must be implemented by subclasses to create their specific dashboard.
        """
        pass
