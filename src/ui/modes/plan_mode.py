"""PlanMode - Mode container for event planning.

PLAN mode contains 2 tabs for event management:
- Events: Event CRUD operations
- Planning Workspace: Calculate batch requirements

Implements User Story 8: PLAN Mode for Event Planning (Priority P3)
"""

from typing import Any, TYPE_CHECKING
import customtkinter as ctk

from src.ui.base.base_mode import BaseMode
from src.ui.dashboards.plan_dashboard import PlanDashboard
from src.ui.tabs.planning_workspace_tab import PlanningWorkspaceTab

if TYPE_CHECKING:
    from src.ui.events_tab import EventsTab


class PlanMode(BaseMode):
    """Mode container for event planning.

    Provides access to event management and planning calculations.
    """

    def __init__(self, master: Any, **kwargs):
        """Initialize PlanMode.

        Args:
            master: Parent widget
            **kwargs: Additional arguments passed to BaseMode
        """
        super().__init__(master, name="PLAN", **kwargs)

        # Tab references
        self.events_tab: "EventsTab" = None
        self.planning_workspace_tab: PlanningWorkspaceTab = None

        # Set up dashboard and tabs
        self.setup_dashboard()
        self.setup_tabs()

    def setup_dashboard(self) -> None:
        """Set up the PLAN dashboard with event stats (FR-008)."""
        dashboard = PlanDashboard(self)
        self.set_dashboard(dashboard)

    def setup_tabs(self) -> None:
        """Set up all 2 tabs for PLAN mode."""
        from src.ui.events_tab import EventsTab

        self.create_tabview()

        # Events tab (existing)
        events_frame = self.tabview.add("Events")
        events_frame.grid_columnconfigure(0, weight=1)
        events_frame.grid_rowconfigure(0, weight=1)
        self.events_tab = EventsTab(events_frame)
        self._tab_widgets["Events"] = self.events_tab

        # Planning Workspace tab (FR-021)
        planning_frame = self.tabview.add("Planning Workspace")
        planning_frame.grid_columnconfigure(0, weight=1)
        planning_frame.grid_rowconfigure(0, weight=1)
        self.planning_workspace_tab = PlanningWorkspaceTab(planning_frame)
        self.planning_workspace_tab.grid(row=0, column=0, sticky="nsew")
        self._tab_widgets["Planning Workspace"] = self.planning_workspace_tab

    def activate(self) -> None:
        """Called when PLAN mode becomes active."""
        super().activate()
        # Refresh events on activation
        if self.events_tab and hasattr(self.events_tab, 'refresh'):
            if not getattr(self.events_tab, '_data_loaded', False):
                self.events_tab._data_loaded = True
                self.after(10, self.events_tab.refresh)

    def refresh_all_tabs(self) -> None:
        """Refresh all tabs in PLAN mode."""
        if self.events_tab:
            self.events_tab.refresh()
        # planning_workspace_tab is placeholder, no data to refresh
