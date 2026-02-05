"""
Event form dialog for adding and editing events.

Provides a form for creating and updating event records.
"""

import customtkinter as ctk
from typing import Optional, Dict, Any
from datetime import datetime, date

from src.models.event import Event
from src.utils.constants import (
    MAX_NAME_LENGTH,
    MAX_NOTES_LENGTH,
    PADDING_MEDIUM,
    PADDING_LARGE,
)
from src.ui.widgets.dialogs import show_error


class EventFormDialog(ctk.CTkToplevel):
    """
    Dialog for creating or editing an event.

    Provides a form with event details and date selection.
    """

    def __init__(
        self,
        parent,
        event: Optional[Event] = None,
        clone_from: Optional[Event] = None,
        title: str = "Add Event",
    ):
        """
        Initialize the event form dialog.

        Args:
            parent: Parent window
            event: Existing event to edit (None for new)
            clone_from: Event to clone from (for clone operation)
            title: Dialog title
        """
        super().__init__(parent)

        self.event = event
        self.clone_from = clone_from
        self.result = None

        # Configure window
        self.title(title)
        self.geometry("600x500")
        self.resizable(False, False)

        # Center on parent
        self.transient(parent)

        # Button frame - pack FIRST with side="bottom" to ensure always visible
        self._create_buttons()

        # Create main frame (packs after buttons, fills remaining space)
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.pack(
            side="top", fill="both", expand=True, padx=PADDING_LARGE, pady=PADDING_LARGE
        )
        main_frame.grid_columnconfigure(1, weight=1)

        # Create form fields
        self._create_form_fields(main_frame)

        # Populate if editing or cloning
        if self.event:
            self._populate_form()
        elif self.clone_from:
            self._populate_from_clone()

        # Center dialog on parent and make visible
        self.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()
        x = max(0, parent_x + (parent_width - dialog_width) // 2)
        y = max(0, parent_y + (parent_height - dialog_height) // 2)
        self.geometry(f"+{x}+{y}")
        self.wait_visibility()
        self.grab_set()
        self.focus_force()

    def _create_form_fields(self, parent):
        """Create all form input fields."""
        row = 0

        # Name field (required)
        name_label = ctk.CTkLabel(parent, text="Event Name*:", anchor="w")
        name_label.grid(
            row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=(PADDING_MEDIUM, 5)
        )

        self.name_entry = ctk.CTkEntry(
            parent, width=400, placeholder_text="e.g., Christmas 2024, Teacher Gifts 2024"
        )
        self.name_entry.grid(
            row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=(PADDING_MEDIUM, 5)
        )
        row += 1

        # Year field (required)
        year_label = ctk.CTkLabel(parent, text="Year*:", anchor="w")
        year_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        current_year = datetime.now().year
        years = [str(year) for year in range(current_year - 1, current_year + 3)]
        self.year_combo = ctk.CTkComboBox(
            parent,
            width=400,
            values=years,
            state="readonly",
        )
        self.year_combo.set(str(current_year))
        self.year_combo.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Event date section (required)
        date_label = ctk.CTkLabel(parent, text="Event Date*:", anchor="w")
        date_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        # Date input frame
        date_frame = ctk.CTkFrame(parent, fg_color="transparent")
        date_frame.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)

        # Month dropdown
        months = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        self.month_combo = ctk.CTkComboBox(
            date_frame,
            width=120,
            values=months,
            state="readonly",
        )
        self.month_combo.set("December")
        self.month_combo.grid(row=0, column=0, padx=(0, 5))

        # Day entry
        self.day_entry = ctk.CTkEntry(date_frame, width=60, placeholder_text="Day")
        current_day = datetime.now().day
        self.day_entry.insert(0, str(current_day))
        self.day_entry.grid(row=0, column=1, padx=(0, 5))

        # Year is already set above
        row += 1

        # Expected attendees field (optional)
        attendees_label = ctk.CTkLabel(parent, text="Expected Attendees:", anchor="w")
        attendees_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        self.attendees_entry = ctk.CTkEntry(
            parent, width=400, placeholder_text="Leave empty if unknown"
        )
        self.attendees_entry.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Notes field (optional)
        notes_label = ctk.CTkLabel(parent, text="Notes:", anchor="w")
        notes_label.grid(row=row, column=0, sticky="nw", padx=PADDING_MEDIUM, pady=5)

        self.notes_text = ctk.CTkTextbox(parent, width=400, height=120)
        self.notes_text.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Required field note
        required_note = ctk.CTkLabel(
            parent,
            text="* Required fields",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="gray",
        )
        required_note.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=PADDING_MEDIUM,
            pady=(PADDING_MEDIUM, 0),
        )

    def _create_buttons(self):
        """Create dialog buttons - packed first to ensure always visible."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(side="bottom", fill="x", padx=PADDING_LARGE, pady=PADDING_LARGE)

        # Cancel button (pack right side first)
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._cancel,
            width=150,
            fg_color="gray",
            hover_color="darkgray",
        )
        cancel_button.pack(side="right", padx=PADDING_MEDIUM)

        # Save button
        save_button = ctk.CTkButton(
            button_frame,
            text="Save",
            command=self._save,
            width=150,
        )
        save_button.pack(side="right", padx=PADDING_MEDIUM)

    def _populate_form(self):
        """Populate form fields with existing event data."""
        if not self.event:
            return

        self.name_entry.insert(0, self.event.name)
        self.year_combo.set(str(self.event.year))

        if self.event.event_date:
            self.month_combo.set(self.event.event_date.strftime("%B"))
            self.day_entry.delete(0, "end")
            self.day_entry.insert(0, str(self.event.event_date.day))

        if self.event.expected_attendees:
            self.attendees_entry.insert(0, str(self.event.expected_attendees))

        if self.event.notes:
            self.notes_text.insert("1.0", self.event.notes)

    def _populate_from_clone(self):
        """Populate form with default values for cloning."""
        if not self.clone_from:
            return

        # Suggest a new name (add year to old name)
        current_year = datetime.now().year
        new_name = f"{self.clone_from.name.split(' ')[0]} {current_year + 1}"
        self.name_entry.insert(0, new_name)

        # Set next year
        self.year_combo.set(str(current_year + 1))

        # Keep same month/day from source event
        if self.clone_from.event_date:
            self.month_combo.set(self.clone_from.event_date.strftime("%B"))
            self.day_entry.delete(0, "end")
            self.day_entry.insert(0, str(self.clone_from.event_date.day))

        # Copy expected attendees if set
        if self.clone_from.expected_attendees:
            self.attendees_entry.insert(0, str(self.clone_from.expected_attendees))

        # Don't copy notes

    def _save(self):
        """Validate and save the event data."""
        # Validate and collect data
        data = self._validate_and_collect()
        if data is None:
            return

        # Set result and close
        self.result = data
        self.destroy()

    def _cancel(self):
        """Cancel the dialog."""
        self.result = None
        self.destroy()

    def _validate_and_collect(self) -> Optional[Dict[str, Any]]:
        """
        Validate form inputs and collect data.

        Returns:
            Dictionary with event data, or None if validation fails
        """
        # Get values
        name = self.name_entry.get().strip()
        year_str = self.year_combo.get()
        month_str = self.month_combo.get()
        day_str = self.day_entry.get().strip()
        attendees_str = self.attendees_entry.get().strip()
        notes = self.notes_text.get("1.0", "end-1c").strip()

        # Validate required fields
        if not name:
            show_error(
                "Validation Error",
                "Event name is required",
                parent=self,
            )
            return None

        if not year_str or not year_str.isdigit():
            show_error(
                "Validation Error",
                "Valid year is required",
                parent=self,
            )
            return None

        year = int(year_str)

        # Validate date
        if not month_str or not day_str or not day_str.isdigit():
            show_error(
                "Validation Error",
                "Valid event date is required (month and day)",
                parent=self,
            )
            return None

        day = int(day_str)

        # Convert month name to number
        months = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        try:
            month = months.index(month_str) + 1
        except ValueError:
            show_error(
                "Validation Error",
                "Invalid month selected",
                parent=self,
            )
            return None

        # Create date object
        try:
            event_date = date(year, month, day)
        except ValueError as e:
            show_error(
                "Validation Error",
                f"Invalid date: {str(e)}",
                parent=self,
            )
            return None

        # Validate lengths
        if len(name) > MAX_NAME_LENGTH:
            show_error(
                "Validation Error",
                f"Name must be {MAX_NAME_LENGTH} characters or less",
                parent=self,
            )
            return None

        if notes and len(notes) > MAX_NOTES_LENGTH:
            show_error(
                "Validation Error",
                f"Notes must be {MAX_NOTES_LENGTH} characters or less",
                parent=self,
            )
            return None

        # Validate expected attendees (optional, must be positive if provided)
        expected_attendees = None
        if attendees_str:
            try:
                expected_attendees = int(attendees_str)
                if expected_attendees <= 0:
                    show_error(
                        "Validation Error",
                        "Expected attendees must be a positive number",
                        parent=self,
                    )
                    return None
            except ValueError:
                show_error(
                    "Validation Error",
                    "Expected attendees must be a number",
                    parent=self,
                )
                return None

        # Return validated data
        return {
            "name": name,
            "year": year,
            "event_date": event_date,
            "expected_attendees": expected_attendees,
            "notes": notes if notes else None,
        }

    def get_result(self) -> Optional[Dict[str, Any]]:
        """Get the dialog result."""
        return self.result
