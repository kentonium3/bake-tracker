"""PlanMode - Mode container for event planning.

PLAN mode contains 2 tabs for event management:
- Events: Event CRUD operations (existing events/assignments)
- Planning: Create/edit/delete planning events with integrated workspace (F068+)

Implements User Story 8: PLAN Mode for Event Planning (Priority P3)
Feature 068: Event Management & Planning Data Model
"""

from typing import Any, TYPE_CHECKING
import customtkinter as ctk

from src.ui.base.base_mode import BaseMode
from src.ui.dashboards.plan_dashboard import PlanDashboard
from src.ui.planning_tab import PlanningTab
from src.ui.forms.event_form import EventFormDialog
from src.ui.forms.event_planning_form import DeleteEventDialog
from src.services import event_service
from src.services.exceptions import ServiceError
from src.ui.utils import ui_session
from src.ui.utils.error_handler import handle_error
from src.ui.widgets.dialogs import show_success

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
        self.events_tab = EventsTab(
            events_frame,
            on_data_changed=self._on_events_tab_data_changed,
        )
        self._tab_widgets["Events"] = self.events_tab

        # Planning tab (F068+ - Event Management with integrated workspace)
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

    # =========================================================================
    # Events Tab Callbacks
    # =========================================================================

    def _on_events_tab_data_changed(self) -> None:
        """Called when Events tab data changes - refresh Planning tab."""
        if self.planning_tab:
            self.planning_tab.refresh()

    # =========================================================================
    # Planning Tab Callbacks (F068)
    # =========================================================================

    def _on_create_planning_event(self) -> None:
        """Open Create Event dialog (unified form used by both tabs)."""
        dialog = EventFormDialog(self, title="Create Event")
        self.wait_window(dialog)

        result = dialog.get_result()
        if result:
            try:
                with ui_session() as session:
                    event_service.create_planning_event(
                        session,
                        name=result["name"],
                        event_date=result["event_date"],
                        expected_attendees=result.get("expected_attendees"),
                        notes=result.get("notes"),
                    )
                    session.commit()
                show_success("Success", f"Event '{result['name']}' created", parent=self)
                self.refresh_all_tabs()
                self.planning_tab._update_status(f"Event '{result['name']}' created.")
            except ServiceError as e:
                handle_error(e, parent=self, operation="Create event")
            except Exception as e:
                handle_error(e, parent=self, operation="Create event")

    def _on_edit_planning_event(self, event) -> None:
        """Open Edit Event dialog (unified form used by both tabs)."""
        dialog = EventFormDialog(self, event=event, title="Edit Event")
        self.wait_window(dialog)

        result = dialog.get_result()
        if result:
            try:
                with ui_session() as session:
                    event_service.update_event(event.id, session=session, **result)
                show_success("Success", "Event updated", parent=self)
                self.refresh_all_tabs()
                self.planning_tab._update_status(f"Event '{result['name']}' updated.")
            except ServiceError as e:
                handle_error(e, parent=self, operation="Update event")
            except Exception as e:
                handle_error(e, parent=self, operation="Update event")

    def _on_delete_planning_event(self, event) -> None:
        """Open Delete Event confirmation dialog."""
        DeleteEventDialog(
            master=self,
            event=event,
            on_confirm=lambda: self._on_planning_event_deleted(event.name),
        )

    def _on_planning_event_deleted(self, event_name: str) -> None:
        """Handle event deletion."""
        self.refresh_all_tabs()
        self.planning_tab._update_status(f"Event '{event_name}' deleted.")
