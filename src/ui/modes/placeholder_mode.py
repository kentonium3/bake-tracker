"""PlaceholderMode - Temporary mode container for transition.

This module provides a placeholder mode that wraps existing tab widgets
during the F038 UI Mode Restructure transition. Each placeholder mode
will be replaced with a proper mode implementation in WP03-WP07.
"""

from typing import Any, List, Tuple, Optional
import customtkinter as ctk

from src.ui.base.base_mode import BaseMode
from src.ui.dashboards.base_dashboard import BaseDashboard


class PlaceholderDashboard(BaseDashboard):
    """Placeholder dashboard for modes pending full implementation."""

    def __init__(self, master: Any, mode_name: str, **kwargs):
        """Initialize PlaceholderDashboard.

        Args:
            master: Parent widget
            mode_name: Name of the mode this dashboard belongs to
            **kwargs: Additional arguments passed to BaseDashboard
        """
        super().__init__(master, **kwargs)
        self._mode_name = mode_name
        self.set_title(f"{mode_name} Dashboard")
        self.add_stat("Status", "Active")

    def refresh(self) -> None:
        """Refresh the dashboard - placeholder does nothing."""
        pass


class PlaceholderMode(BaseMode):
    """Placeholder mode container for F038 transition.

    Wraps existing tab widgets in a mode container structure.
    Will be replaced with proper mode implementations.
    """

    def __init__(
        self,
        master: Any,
        name: str,
        tab_configs: List[Tuple[str, Any]],
        **kwargs
    ):
        """Initialize PlaceholderMode.

        Args:
            master: Parent widget
            name: Mode name (CATALOG, PLAN, etc.)
            tab_configs: List of (tab_name, tab_widget) tuples
            **kwargs: Additional arguments passed to BaseMode
        """
        super().__init__(master, name, **kwargs)
        self._tab_configs = tab_configs
        self._tabs_initialized = False

    def setup_dashboard(self) -> None:
        """Set up a placeholder dashboard."""
        dashboard = PlaceholderDashboard(self, self.name)
        self.set_dashboard(dashboard)

    def setup_tabs(self) -> None:
        """Set up tabs from the provided configurations."""
        if self._tabs_initialized:
            return

        self.create_tabview()
        for tab_name, tab_widget in self._tab_configs:
            self.add_tab(tab_name, tab_widget)

        self._tabs_initialized = True

    def add_tab_widget(self, name: str, widget: Any) -> None:
        """Add a tab widget after initialization.

        Args:
            name: Tab name
            widget: Widget to add to the tab
        """
        if self.tabview is None:
            self.create_tabview()
        self.add_tab(name, widget)

    def initialize(self) -> None:
        """Initialize the mode (dashboard + tabs)."""
        self.setup_dashboard()
        self.setup_tabs()
