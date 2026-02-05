"""
Events tab for the Seasonal Baking Tracker.

Provides interface for managing events and viewing event summaries.
"""

import customtkinter as ctk
from typing import Optional, Callable
from datetime import datetime

from src.models.event import Event
from src.services import event_service
from src.services.event_service import EventNotFoundError
from src.ui.utils import ui_session
from src.utils.constants import (
    PADDING_MEDIUM,
    PADDING_LARGE,
)
from src.ui.widgets.search_bar import SearchBar
from src.ui.widgets.data_table import EventDataTable
from src.ui.widgets.dialogs import (
    show_confirmation,
    show_error,
    show_success,
)
from src.ui.forms.event_form import EventFormDialog
from src.ui.event_detail_window import EventDetailWindow
from src.ui.utils import ui_session
from src.services.exceptions import ServiceError
from src.ui.utils.error_handler import handle_error


class EventsTab(ctk.CTkFrame):
    """
    Events management tab with CRUD capabilities.

    Provides interface for:
    - Viewing all events in a table
    - Creating new events
    - Editing existing events
    - Cloning events from previous years
    - Deleting events
    - Viewing event details (assignments, costs, shopping list)
    """

    def __init__(self, parent, on_data_changed: Optional[Callable[[], None]] = None):
        """
        Initialize the events tab.

        Args:
            parent: Parent widget
            on_data_changed: Optional callback invoked after any data mutation
        """
        super().__init__(parent)

        self.selected_event: Optional[Event] = None
        self._on_data_changed = on_data_changed

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Filter bar
        self.grid_rowconfigure(1, weight=0)  # Action buttons
        self.grid_rowconfigure(2, weight=1)  # Data table
        self.grid_rowconfigure(3, weight=0)  # Status bar

        # Create UI components
        self._create_filter_bar()
        self._create_action_buttons()
        self._create_data_table()
        self._create_status_bar()

        # Data will be loaded when tab is first selected (lazy loading)
        # self.refresh()

        # Grid the frame
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def _create_filter_bar(self):
        """Create the filter bar with year selector."""
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.grid(
            row=0, column=0, sticky="ew", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_MEDIUM)
        )

        # Year filter label
        year_label = ctk.CTkLabel(filter_frame, text="Filter by Year:")
        year_label.grid(row=0, column=0, padx=PADDING_MEDIUM)

        # Year selector (dropdown with recent years + All)
        current_year = datetime.now().year
        years = ["All Years"] + [str(year) for year in range(current_year, current_year - 5, -1)]

        self.year_filter_var = ctk.StringVar(value="All Years")
        self.year_combo = ctk.CTkComboBox(
            filter_frame,
            values=years,
            variable=self.year_filter_var,
            width=150,
            command=self._on_year_filter_change,
        )
        self.year_combo.grid(row=0, column=1, padx=PADDING_MEDIUM)

    def _create_action_buttons(self):
        """Create action buttons for CRUD operations."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_MEDIUM)

        # Add button
        add_button = ctk.CTkButton(
            button_frame,
            text="➕ Add Event",
            command=self._add_event,
            width=150,
        )
        add_button.grid(row=0, column=0, padx=PADDING_MEDIUM)

        # Edit button
        self.edit_button = ctk.CTkButton(
            button_frame,
            text="✏️ Edit",
            command=self._edit_event,
            width=120,
            state="disabled",
        )
        self.edit_button.grid(row=0, column=1, padx=PADDING_MEDIUM)

        # Clone button
        self.clone_button = ctk.CTkButton(
            button_frame,
            text="📋 Clone",
            command=self._clone_event,
            width=120,
            state="disabled",
        )
        self.clone_button.grid(row=0, column=2, padx=PADDING_MEDIUM)

        # View Details button
        self.view_button = ctk.CTkButton(
            button_frame,
            text="👁️ View Details",
            command=self._view_details,
            width=140,
            state="disabled",
        )
        self.view_button.grid(row=0, column=3, padx=PADDING_MEDIUM)

        # Delete button
        self.delete_button = ctk.CTkButton(
            button_frame,
            text="🗑️ Delete",
            command=self._delete_event,
            width=120,
            state="disabled",
            fg_color="darkred",
            hover_color="red",
        )
        self.delete_button.grid(row=0, column=4, padx=PADDING_MEDIUM)

        # Refresh button
        refresh_button = ctk.CTkButton(
            button_frame,
            text="🔄 Refresh",
            command=self.refresh,
            width=120,
        )
        refresh_button.grid(row=0, column=5, padx=PADDING_MEDIUM)

    def _create_data_table(self):
        """Create the data table for displaying events."""
        self.data_table = EventDataTable(
            self,
            select_callback=self._on_row_select,
            double_click_callback=self._on_row_double_click,
        )
        self.data_table.grid(
            row=2, column=0, sticky="nsew", padx=PADDING_LARGE, pady=PADDING_MEDIUM
        )

    def _create_status_bar(self):
        """Create status bar for displaying info."""
        self.status_frame = ctk.CTkFrame(self, height=30)
        self.status_frame.grid(
            row=3, column=0, sticky="ew", padx=PADDING_LARGE, pady=(0, PADDING_LARGE)
        )
        self.status_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Ready",
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

    def _on_year_filter_change(self, selected_year: str):
        """
        Handle year filter change.

        Args:
            selected_year: Selected year or "All Years"
        """
        self.refresh()

    def _on_row_select(self, event: Optional[Event]):
        """
        Handle row selection.

        Args:
            event: Selected event (None if deselected)
        """
        self.selected_event = event

        # Enable/disable action buttons
        has_selection = event is not None
        self.edit_button.configure(state="normal" if has_selection else "disabled")
        self.clone_button.configure(state="normal" if has_selection else "disabled")
        self.view_button.configure(state="normal" if has_selection else "disabled")
        self.delete_button.configure(state="normal" if has_selection else "disabled")

    def _on_row_double_click(self, event: Event):
        """
        Handle row double-click (opens view details).

        Args:
            event: Double-clicked event
        """
        self._view_details()

    def _add_event(self):
        """Open dialog to add a new event."""
        dialog = EventFormDialog(self, title="Add Event")
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
                show_success("Success", f"Event '{result['name']}' added successfully", parent=self)
                self.refresh()
                self._notify_data_changed()
            except ServiceError as e:
                handle_error(e, parent=self, operation="Add event")
            except Exception as e:
                handle_error(e, parent=self, operation="Add event")

    def _edit_event(self):
        """Open dialog to edit the selected event."""
        if not self.selected_event:
            return

        dialog = EventFormDialog(self, event=self.selected_event, title="Edit Event")
        self.wait_window(dialog)

        result = dialog.get_result()
        if result:
            try:
                with ui_session() as session:
                    event_service.update_event(self.selected_event.id, session=session, **result)
                show_success("Success", "Event updated successfully", parent=self)
                self.refresh()
                self._notify_data_changed()
            except EventNotFoundError as e:
                handle_error(e, parent=self, operation="Update event")
                self.refresh()
            except ServiceError as e:
                handle_error(e, parent=self, operation="Update event")
            except Exception as e:
                handle_error(e, parent=self, operation="Update event")

    def _clone_event(self):
        """Clone the selected event to a new year."""
        if not self.selected_event:
            return

        # For now, show a simple dialog for the new year
        # In a more complete implementation, this would be a custom form
        dialog = EventFormDialog(
            self, clone_from=self.selected_event, title=f"Clone Event: {self.selected_event.name}"
        )
        self.wait_window(dialog)

        result = dialog.get_result()
        if result:
            try:
                with ui_session() as session:
                    event_service.clone_event(
                        self.selected_event.id,
                        result["name"],
                        result["year"],
                        result["event_date"],
                        session=session,
                    )
                show_success(
                    "Success", f"Event '{result['name']}' cloned successfully", parent=self
                )
                self.refresh()
                self._notify_data_changed()
            except ServiceError as e:
                handle_error(e, parent=self, operation="Clone event")
            except Exception as e:
                handle_error(e, parent=self, operation="Clone event")

    def _delete_event(self):
        """Delete the selected event after confirmation."""
        if not self.selected_event:
            return

        # Confirm deletion
        if not show_confirmation(
            "Confirm Deletion",
            f"Are you sure you want to delete event '{self.selected_event.name}'?\n\n"
            "This will also delete all package assignments for this event.\n"
            "This action cannot be undone.",
            parent=self,
        ):
            return

        try:
            with ui_session() as session:
                event_service.delete_event(self.selected_event.id, session=session)
            show_success("Success", "Event deleted successfully", parent=self)
            self.selected_event = None
            self.refresh()
            self._notify_data_changed()
        except EventNotFoundError as e:
            handle_error(e, parent=self, operation="Delete event")
            self.refresh()
        except ServiceError as e:
            handle_error(e, parent=self, operation="Delete event")
        except Exception as e:
            handle_error(e, parent=self, operation="Delete event")

    def _view_details(self):
        """View details of the selected event."""
        if not self.selected_event:
            return

        # Open event detail window
        detail_window = EventDetailWindow(self, self.selected_event)
        self.wait_window(detail_window)

        # Refresh in case assignments changed
        self.refresh()

    def refresh(self):
        """Refresh the events list."""
        try:
            # Get selected year filter
            year_filter = self.year_filter_var.get()
            year = None if year_filter == "All Years" else int(year_filter)

            with ui_session() as session:
                if year is not None:
                    events = event_service.get_events_by_year(year, session=session)
                else:
                    events = event_service.get_all_events(session=session)
            self.data_table.set_data(events)
            self._update_status(f"Loaded {len(events)} event(s)")
        except ServiceError as e:
            handle_error(e, parent=self, operation="Load events")
            self._update_status("Failed to load events", error=True)
        except Exception as e:
            handle_error(e, parent=self, operation="Load events")
            self._update_status("Failed to load events", error=True)

    def _notify_data_changed(self) -> None:
        """Notify listeners that event data has changed."""
        if self._on_data_changed:
            self._on_data_changed()

    def _update_status(self, message: str, error: bool = False):
        """
        Update the status bar.

        Args:
            message: Status message
            error: Whether this is an error message
        """
        if error:
            self.status_label.configure(text=message, text_color="red")
        else:
            self.status_label.configure(text=message)
