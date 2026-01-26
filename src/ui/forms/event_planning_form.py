"""
Event Planning Form - Create/Edit event dialogs.

Feature 068: Event Management & Planning Data Model

Usage in Planning Tab:
----------------------
```python
from src.ui.forms.event_planning_form import EventPlanningForm, DeleteEventDialog

# Create event
def on_create():
    EventPlanningForm.create_event(
        master=self,
        on_save=lambda result: self._on_event_saved(result),
    )

# Edit event
def on_edit(event: Event):
    EventPlanningForm.edit_event(
        master=self,
        event=event,
        on_save=lambda result: self._on_event_saved(result),
    )

# Delete event
def on_delete(event: Event):
    DeleteEventDialog(
        master=self,
        event=event,
        on_confirm=lambda: self._on_event_deleted(),
    )
```
"""

import customtkinter as ctk
from typing import Optional, Callable, Dict, Any
from datetime import datetime

from src.services import event_service
from src.services.database import session_scope
from src.services.exceptions import ValidationError
from src.models import Event


__all__ = ["EventPlanningForm", "DeleteEventDialog"]


class EventPlanningForm(ctk.CTkToplevel):
    """
    Form dialog for event creation and editing.

    Handles common form setup, validation, and save logic.
    Use factory methods create_event() and edit_event() for easy instantiation.
    """

    def __init__(
        self,
        master,
        event: Optional[Event] = None,
        on_save: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        """
        Initialize event form.

        Args:
            master: Parent window
            event: Event to edit (None for create mode)
            on_save: Callback with save result dict
            on_cancel: Callback on cancel
        """
        super().__init__(master, **kwargs)

        self.event = event
        self._on_save = on_save
        self._on_cancel = on_cancel

        # Determine mode
        self.is_edit_mode = event is not None

        # Configure window
        self.title("Edit Event" if self.is_edit_mode else "Create Event")
        self.geometry("450x400")
        self.resizable(False, False)

        # Make modal
        self.transient(master)
        self.grab_set()

        # Build UI
        self._create_widgets()
        self._layout_widgets()

        # Populate if editing
        if self.is_edit_mode:
            self._populate_form()

        # Focus first field
        self.name_entry.focus_set()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self) -> None:
        """Create form widgets."""
        # Form title
        title_text = "Edit Event" if self.is_edit_mode else "Create New Event"
        self.title_label = ctk.CTkLabel(
            self,
            text=title_text,
            font=ctk.CTkFont(size=18, weight="bold"),
        )

        # Name field
        self.name_label = ctk.CTkLabel(self, text="Event Name *")
        self.name_entry = ctk.CTkEntry(
            self, width=300, placeholder_text="e.g., Christmas 2026"
        )

        # Date field
        self.date_label = ctk.CTkLabel(self, text="Event Date * (YYYY-MM-DD)")
        self.date_entry = ctk.CTkEntry(
            self, width=300, placeholder_text="2026-12-20"
        )

        # Expected Attendees field
        self.attendees_label = ctk.CTkLabel(self, text="Expected Attendees (optional)")
        self.attendees_entry = ctk.CTkEntry(
            self, width=300, placeholder_text="Leave empty if unknown"
        )

        # Notes field
        self.notes_label = ctk.CTkLabel(self, text="Notes (optional)")
        self.notes_entry = ctk.CTkTextbox(self, width=300, height=60)

        # Validation message
        self.validation_label = ctk.CTkLabel(
            self,
            text="",
            text_color="red",
            wraplength=350,
        )

        # Buttons
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.save_button = ctk.CTkButton(
            self.button_frame,
            text="Save",
            command=self._on_save_click,
            width=100,
        )
        self.cancel_button = ctk.CTkButton(
            self.button_frame,
            text="Cancel",
            command=self._on_close,
            width=100,
            fg_color="gray",
        )

        # Bind key events to clear validation on typing
        self.name_entry.bind("<Key>", self._clear_validation_on_change)
        self.date_entry.bind("<Key>", self._clear_validation_on_change)
        self.attendees_entry.bind("<Key>", self._clear_validation_on_change)

    def _layout_widgets(self) -> None:
        """Position widgets in form."""
        padding = {"padx": 20, "pady": 5}

        self.title_label.pack(pady=(20, 10))

        self.name_label.pack(anchor="w", **padding)
        self.name_entry.pack(**padding)

        self.date_label.pack(anchor="w", **padding)
        self.date_entry.pack(**padding)

        self.attendees_label.pack(anchor="w", **padding)
        self.attendees_entry.pack(**padding)

        self.notes_label.pack(anchor="w", **padding)
        self.notes_entry.pack(**padding)

        self.validation_label.pack(pady=5)

        self.button_frame.pack(pady=15)
        self.save_button.pack(side="left", padx=10)
        self.cancel_button.pack(side="left", padx=10)

    def _populate_form(self) -> None:
        """Populate form with existing event data."""
        if not self.event:
            return

        self.name_entry.insert(0, self.event.name or "")

        if self.event.event_date:
            self.date_entry.insert(0, self.event.event_date.strftime("%Y-%m-%d"))

        if self.event.expected_attendees:
            self.attendees_entry.insert(0, str(self.event.expected_attendees))

        if self.event.notes:
            self.notes_entry.insert("1.0", self.event.notes)

    def _validate(self) -> Optional[str]:
        """
        Validate form input.

        Returns:
            Error message if validation fails, None if valid
        """
        # Name is required
        name = self.name_entry.get().strip()
        if not name:
            return "Event name is required."

        # Date is required
        date_str = self.date_entry.get().strip()
        if not date_str:
            return "Event date is required."

        # Date format validation
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return "Invalid date format. Please use YYYY-MM-DD."

        # Attendees must be positive if provided
        attendees_str = self.attendees_entry.get().strip()
        if attendees_str:
            try:
                attendees = int(attendees_str)
                if attendees <= 0:
                    return "Expected attendees must be a positive number."
            except ValueError:
                return "Expected attendees must be a number."

        return None  # All valid

    def _clear_validation_on_change(self, event=None) -> None:
        """Clear validation message when user types."""
        self.validation_label.configure(text="")

    def _on_save_click(self) -> None:
        """Handle save button click."""
        # Validate
        error = self._validate()
        if error:
            self.validation_label.configure(text=error)
            return

        # Clear validation message
        self.validation_label.configure(text="")

        # Get form data
        name = self.name_entry.get().strip()
        date_str = self.date_entry.get().strip()
        attendees_str = self.attendees_entry.get().strip()
        notes = self.notes_entry.get("1.0", "end-1c").strip()

        # Parse date
        try:
            event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            self.validation_label.configure(text="Invalid date format. Use YYYY-MM-DD.")
            return

        # Parse attendees
        expected_attendees = None
        if attendees_str:
            try:
                expected_attendees = int(attendees_str)
            except ValueError:
                self.validation_label.configure(
                    text="Expected attendees must be a number."
                )
                return

        # Save
        try:
            with session_scope() as session:
                if self.is_edit_mode:
                    # Update existing
                    result = event_service.update_planning_event(
                        session,
                        self.event.id,
                        name=name,
                        event_date=event_date,
                        expected_attendees=expected_attendees if attendees_str else 0,
                        notes=notes or None,
                    )
                    session.commit()
                    result_data = {
                        "id": result.id,
                        "name": result.name,
                        "action": "updated",
                    }
                else:
                    # Create new
                    result = event_service.create_planning_event(
                        session,
                        name=name,
                        event_date=event_date,
                        expected_attendees=expected_attendees,
                        notes=notes or None,
                    )
                    session.commit()
                    result_data = {
                        "id": result.id,
                        "name": result.name,
                        "action": "created",
                    }

            # Callback and close
            if self._on_save:
                self._on_save(result_data)
            self.destroy()

        except ValidationError as e:
            self.validation_label.configure(text=str(e))
        except Exception as e:
            self.validation_label.configure(text=f"Error saving: {e}")

    def _on_close(self) -> None:
        """Handle cancel/close."""
        if self._on_cancel:
            self._on_cancel()
        self.destroy()

    @classmethod
    def create_event(
        cls,
        master,
        on_save: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
    ) -> "EventPlanningForm":
        """
        Factory method to create a Create Event dialog.

        Args:
            master: Parent window
            on_save: Callback with created event data
            on_cancel: Callback on cancel

        Returns:
            EventPlanningForm instance in create mode
        """
        return cls(master, event=None, on_save=on_save, on_cancel=on_cancel)

    @classmethod
    def edit_event(
        cls,
        master,
        event: Event,
        on_save: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
    ) -> "EventPlanningForm":
        """
        Factory method to create an Edit Event dialog.

        Args:
            master: Parent window
            event: Event to edit
            on_save: Callback with updated event data
            on_cancel: Callback on cancel

        Returns:
            EventPlanningForm instance in edit mode
        """
        return cls(master, event=event, on_save=on_save, on_cancel=on_cancel)


class DeleteEventDialog(ctk.CTkToplevel):
    """
    Confirmation dialog for event deletion.

    Shows event name and warns about cascade deletion before confirming.
    """

    def __init__(
        self,
        master,
        event: Event,
        on_confirm: Optional[Callable[[], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        """
        Initialize delete confirmation dialog.

        Args:
            master: Parent window
            event: Event to delete
            on_confirm: Callback when delete confirmed
            on_cancel: Callback on cancel
        """
        super().__init__(master, **kwargs)

        self.event = event
        self._on_confirm = on_confirm
        self._on_cancel = on_cancel

        # Configure window
        self.title("Delete Event")
        self.geometry("400x200")
        self.resizable(False, False)

        # Make modal
        self.transient(master)
        self.grab_set()

        # Build UI
        self._create_widgets()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        # Warning icon/message
        warning_label = ctk.CTkLabel(
            self,
            text="Delete Event?",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        warning_label.pack(pady=(20, 10))

        # Event name
        name_label = ctk.CTkLabel(
            self,
            text=f'"{self.event.name}"',
            font=ctk.CTkFont(size=14),
        )
        name_label.pack(pady=5)

        # Warning text
        info_label = ctk.CTkLabel(
            self,
            text="This will also delete all associated\nrecipes, finished goods, and batch decisions.",
            text_color="gray",
        )
        info_label.pack(pady=10)

        # Error label (initially hidden)
        self.error_label = ctk.CTkLabel(
            self,
            text="",
            text_color="red",
        )
        self.error_label.pack(pady=5)

        # Buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=15)

        delete_button = ctk.CTkButton(
            button_frame,
            text="Delete",
            command=self._on_delete_click,
            fg_color="darkred",
            hover_color="red",
            width=100,
        )
        delete_button.pack(side="left", padx=10)

        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._on_close,
            fg_color="gray",
            width=100,
        )
        cancel_button.pack(side="left", padx=10)

    def _on_delete_click(self) -> None:
        """Handle delete confirmation."""
        try:
            with session_scope() as session:
                event_service.delete_planning_event(session, self.event.id)
                session.commit()

            if self._on_confirm:
                self._on_confirm()
            self.destroy()

        except Exception as e:
            self.error_label.configure(text=f"Error deleting: {e}")

    def _on_close(self) -> None:
        """Handle cancel/close."""
        if self._on_cancel:
            self._on_cancel()
        self.destroy()
