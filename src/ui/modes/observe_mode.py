"""ObserveMode - Mode container for progress observation.

OBSERVE mode contains 3 tabs for monitoring progress:
- Dashboard: Overall activity summary
- Event Status: Per-event progress tracking
- Reports: Placeholder for future reporting features

This is the default mode on application launch (FR-005).

Implements User Story 5: OBSERVE Mode for Progress Tracking (Priority P2)
"""

from typing import Any, TYPE_CHECKING
import customtkinter as ctk

from src.ui.base.base_mode import BaseMode
from src.ui.dashboards.observe_dashboard import ObserveDashboard
from src.ui.tabs.event_status_tab import EventStatusTab
from src.ui.tabs.reports_tab import ReportsTab

if TYPE_CHECKING:
    from src.ui.dashboard_tab import DashboardTab


class ObserveMode(BaseMode):
    """Mode container for progress observation.

    Default mode on application launch. Shows overall event progress
    and per-event status tracking.
    """

    def __init__(self, master: Any, **kwargs):
        """Initialize ObserveMode.

        Args:
            master: Parent widget
            **kwargs: Additional arguments passed to BaseMode
        """
        super().__init__(master, name="OBSERVE", **kwargs)

        # Tab references
        self.dashboard_tab: "DashboardTab" = None
        self.event_status_tab: EventStatusTab = None
        self.reports_tab: ReportsTab = None

        # Set up dashboard and tabs
        self.setup_dashboard()
        self.setup_tabs()

    def setup_dashboard(self) -> None:
        """Set up the OBSERVE dashboard with progress indicators (FR-011)."""
        dashboard = ObserveDashboard(self)
        self.set_dashboard(dashboard)

    def setup_tabs(self) -> None:
        """Set up all 3 tabs for OBSERVE mode."""
        from src.ui.dashboard_tab import DashboardTab

        self.create_tabview()

        # Dashboard tab (existing summary view)
        dashboard_frame = self.tabview.add("Dashboard")
        dashboard_frame.grid_columnconfigure(0, weight=1)
        dashboard_frame.grid_rowconfigure(0, weight=1)
        self.dashboard_tab = DashboardTab(dashboard_frame)
        self._tab_widgets["Dashboard"] = self.dashboard_tab

        # Event Status tab (FR-028)
        event_status_frame = self.tabview.add("Event Status")
        event_status_frame.grid_columnconfigure(0, weight=1)
        event_status_frame.grid_rowconfigure(0, weight=1)
        self.event_status_tab = EventStatusTab(event_status_frame)
        self.event_status_tab.grid(row=0, column=0, sticky="nsew")
        self._tab_widgets["Event Status"] = self.event_status_tab

        # Reports tab (placeholder - FR-028a)
        reports_frame = self.tabview.add("Reports")
        reports_frame.grid_columnconfigure(0, weight=1)
        reports_frame.grid_rowconfigure(0, weight=1)
        self.reports_tab = ReportsTab(reports_frame)
        self.reports_tab.grid(row=0, column=0, sticky="nsew")
        self._tab_widgets["Reports"] = self.reports_tab

    def activate(self) -> None:
        """Called when OBSERVE mode becomes active (FR-005 default)."""
        super().activate()
        # Refresh event status on activation
        if self.event_status_tab:
            self.after(10, self.event_status_tab.refresh)

    def refresh_all_tabs(self) -> None:
        """Refresh all tabs in OBSERVE mode."""
        if self.dashboard_tab:
            self.dashboard_tab.refresh()
        if self.event_status_tab:
            self.event_status_tab.refresh()
        # reports_tab has no data to refresh
