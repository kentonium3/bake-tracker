"""PlanMode - Mode container for event planning.

PLAN mode contains 3 tabs for event management:
- Events: Event CRUD operations (existing events/assignments)
- Planning: Create/edit/delete planning events (F068)
- Planning Workspace: Calculate batch requirements

Implements User Story 8: PLAN Mode for Event Planning (Priority P3)
Feature 068: Event Management & Planning Data Model
"""

from typing import Any, TYPE_CHECKING
import customtkinter as ctk

from src.ui.base.base_mode import BaseMode
from src.ui.dashboards.plan_dashboard import PlanDashboard
from src.ui.tabs.planning_workspace_tab import PlanningWorkspaceTab
from src.ui.planning_tab import PlanningTab
from src.ui.forms.event_planning_form import EventPlanningForm, DeleteEventDialog

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
        self.planning_tab: PlanningTab = None
        self.planning_workspace_tab: PlanningWorkspaceTab = None

        # Set up dashboard and tabs
        self.setup_dashboard()
        self.setup_tabs()

    def setup_dashboard(self) -> None:
        """Set up the PLAN dashboard with event stats (FR-008)."""
        dashboard = PlanDashboard(self)
        self.set_dashboard(dashboard)

    def setup_tabs(self) -> None:
        """Set up all 3 tabs for PLAN mode."""
        from src.ui.events_tab import EventsTab

        self.create_tabview()

        # Events tab (existing)
        events_frame = self.tabview.add("Events")
        events_frame.grid_columnconfigure(0, weight=1)
        events_frame.grid_rowconfigure(0, weight=1)
        self.events_tab = EventsTab(events_frame)
        self._tab_widgets["Events"] = self.events_tab

        # Planning tab (F068 - Event Management)
        planning_frame = self.tabview.add("Planning")
        planning_frame.grid_columnconfigure(0, weight=1)
        planning_frame.grid_rowconfigure(0, weight=1)
        self.planning_tab = PlanningTab(
            planning_frame,
            on_create_event=self._on_create_planning_event,
            on_edit_event=self._on_edit_planning_event,
            on_delete_event=self._on_delete_planning_event,
        )
        self.planning_tab.grid(row=0, column=0, sticky="nsew")
        self._tab_widgets["Planning"] = self.planning_tab

        # Planning Workspace tab (FR-021)
        workspace_frame = self.tabview.add("Planning Workspace")
        workspace_frame.grid_columnconfigure(0, weight=1)
        workspace_frame.grid_rowconfigure(0, weight=1)
        self.planning_workspace_tab = PlanningWorkspaceTab(workspace_frame)
        self.planning_workspace_tab.grid(row=0, column=0, sticky="nsew")
        self._tab_widgets["Planning Workspace"] = self.planning_workspace_tab

    def activate(self) -> None:
        """Called when PLAN mode becomes active."""
        super().activate()
        # Refresh events on activation
        if self.events_tab and hasattr(self.events_tab, "refresh"):
            if not getattr(self.events_tab, "_data_loaded", False):
                self.events_tab._data_loaded = True
                self.after(10, self.events_tab.refresh)
        # Refresh planning tab on activation
        if self.planning_tab and hasattr(self.planning_tab, "refresh"):
            if not getattr(self.planning_tab, "_data_loaded", False):
                self.planning_tab._data_loaded = True
                self.after(10, self.planning_tab.refresh)

    def refresh_all_tabs(self) -> None:
        """Refresh all tabs in PLAN mode."""
        if self.events_tab:
            self.events_tab.refresh()
        if self.planning_tab:
            self.planning_tab.refresh()
        # planning_workspace_tab is placeholder, no data to refresh

    # =========================================================================
    # Planning Tab Callbacks (F068)
    # =========================================================================

    def _on_create_planning_event(self) -> None:
        """Open Create Event dialog."""
        EventPlanningForm.create_event(
            master=self,
            on_save=self._on_planning_event_saved,
        )

    def _on_edit_planning_event(self, event) -> None:
        """Open Edit Event dialog."""
        EventPlanningForm.edit_event(
            master=self,
            event=event,
            on_save=self._on_planning_event_saved,
        )

    def _on_delete_planning_event(self, event) -> None:
        """Open Delete Event confirmation dialog."""
        DeleteEventDialog(
            master=self,
            event=event,
            on_confirm=lambda: self._on_planning_event_deleted(event.name),
        )

    def _on_planning_event_saved(self, result: dict) -> None:
        """Handle event save completion."""
        self.planning_tab.refresh()
        self.planning_tab._update_status(
            f"Event '{result['name']}' {result['action']}."
        )

    def _on_planning_event_deleted(self, event_name: str) -> None:
        """Handle event deletion."""
        self.planning_tab.refresh()
        self.planning_tab._update_status(f"Event '{event_name}' deleted.")
