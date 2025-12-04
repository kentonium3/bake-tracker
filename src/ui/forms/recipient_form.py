"""
Recipient form dialog for adding and editing recipients.

Provides a form for creating and updating recipient records.
"""

import customtkinter as ctk
from typing import Optional, Dict, Any

from src.models.recipient import Recipient
from src.utils.constants import (
    MAX_NAME_LENGTH,
    MAX_NOTES_LENGTH,
    PADDING_MEDIUM,
    PADDING_LARGE,
)
from src.ui.widgets.dialogs import show_error


class RecipientFormDialog(ctk.CTkToplevel):
    """
    Dialog for creating or editing a recipient.

    Provides a form for recipient information entry.
    """

    def __init__(
        self,
        parent,
        recipient: Optional[Recipient] = None,
        title: str = "Add Recipient",
    ):
        """
        Initialize the recipient form dialog.

        Args:
            parent: Parent window
            recipient: Existing recipient to edit (None for new)
            title: Dialog title
        """
        super().__init__(parent)

        self.recipient = recipient
        self.result = None

        # Configure window
        self.title(title)
        self.geometry("550x550")
        self.resizable(False, False)

        # Center on parent
        self.transient(parent)
        self.grab_set()

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create main frame
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=PADDING_LARGE, pady=PADDING_LARGE)
        main_frame.grid_columnconfigure(1, weight=1)

        # Create form fields
        self._create_form_fields(main_frame)

        # Create buttons
        self._create_buttons()

        # Populate if editing
        if self.recipient:
            self._populate_form()

    def _create_form_fields(self, parent):
        """Create all form input fields."""
        row = 0

        # Name field (required)
        name_label = ctk.CTkLabel(parent, text="Name*:", anchor="w")
        name_label.grid(
            row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=(PADDING_MEDIUM, 5)
        )

        self.name_entry = ctk.CTkEntry(
            parent, width=400, placeholder_text="e.g., John Smith, The Johnson Family"
        )
        self.name_entry.grid(
            row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=(PADDING_MEDIUM, 5)
        )
        row += 1

        # Household name field (optional)
        household_label = ctk.CTkLabel(parent, text="Household Name:", anchor="w")
        household_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        self.household_entry = ctk.CTkEntry(
            parent, width=400, placeholder_text="e.g., The Smiths, Johnson Household"
        )
        self.household_entry.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Address field (optional, multiline)
        address_label = ctk.CTkLabel(parent, text="Address:", anchor="w")
        address_label.grid(row=row, column=0, sticky="nw", padx=PADDING_MEDIUM, pady=5)

        self.address_text = ctk.CTkTextbox(parent, width=400, height=100)
        self.address_text.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
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
        """Create dialog buttons."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)
        button_frame.grid_columnconfigure((0, 1), weight=1)

        # Save button
        save_button = ctk.CTkButton(
            button_frame,
            text="Save",
            command=self._save,
            width=150,
        )
        save_button.grid(row=0, column=0, padx=PADDING_MEDIUM)

        # Cancel button
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._cancel,
            width=150,
            fg_color="gray",
            hover_color="darkgray",
        )
        cancel_button.grid(row=0, column=1, padx=PADDING_MEDIUM)

    def _populate_form(self):
        """Populate form fields with existing recipient data."""
        if not self.recipient:
            return

        self.name_entry.insert(0, self.recipient.name)

        if self.recipient.household_name:
            self.household_entry.insert(0, self.recipient.household_name)

        if self.recipient.address:
            self.address_text.insert("1.0", self.recipient.address)

        if self.recipient.notes:
            self.notes_text.insert("1.0", self.recipient.notes)

    def _save(self):
        """Validate and save the recipient data."""
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
            Dictionary with recipient data, or None if validation fails
        """
        # Get values
        name = self.name_entry.get().strip()
        household_name = self.household_entry.get().strip()
        address = self.address_text.get("1.0", "end-1c").strip()
        notes = self.notes_text.get("1.0", "end-1c").strip()

        # Validate required fields
        if not name:
            show_error(
                "Validation Error",
                "Name is required",
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

        if household_name and len(household_name) > MAX_NAME_LENGTH:
            show_error(
                "Validation Error",
                f"Household name must be {MAX_NAME_LENGTH} characters or less",
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

        # Return validated data
        return {
            "name": name,
            "household_name": household_name if household_name else None,
            "address": address if address else None,
            "notes": notes if notes else None,
        }

    def get_result(self) -> Optional[Dict[str, Any]]:
        """Get the dialog result."""
        return self.result
