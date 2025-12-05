"""
Assignment form dialog for assigning packages to recipients for events.

Provides a form for creating and updating event-recipient-package assignments.
"""

import customtkinter as ctk
from typing import Optional, Dict, Any

from src.models.event import EventRecipientPackage
from src.services import recipient_service, package_service
from src.utils.constants import (
    MAX_NOTES_LENGTH,
    PADDING_MEDIUM,
    PADDING_LARGE,
)
from src.ui.widgets.dialogs import show_error


class AssignmentFormDialog(ctk.CTkToplevel):
    """
    Dialog for creating or editing a recipient-package assignment for an event.
    """

    def __init__(
        self,
        parent,
        event_id: int,
        assignment: Optional[EventRecipientPackage] = None,
        title: str = "Assign Package to Recipient",
    ):
        """
        Initialize the assignment form dialog.

        Args:
            parent: Parent window
            event_id: Event ID this assignment is for
            assignment: Existing assignment to edit (None for new)
            title: Dialog title
        """
        super().__init__(parent)

        self.event_id = event_id
        self.assignment = assignment
        self.result = None

        # Load available recipients and packages
        try:
            self.available_recipients = recipient_service.get_all_recipients()
            self.available_packages = package_service.get_all_packages()
        except Exception:
            self.available_recipients = []
            self.available_packages = []

        # Configure window
        self.title(title)
        self.geometry("600x500")
        self.resizable(False, False)

        # Center on parent
        self.transient(parent)

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
        if self.assignment:
            self._populate_form()

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

        # Recipient dropdown (required)
        recipient_label = ctk.CTkLabel(parent, text="Recipient*:", anchor="w")
        recipient_label.grid(
            row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=(PADDING_MEDIUM, 5)
        )

        recipient_names = [r.name for r in self.available_recipients]
        self.recipient_combo = ctk.CTkComboBox(
            parent,
            width=400,
            values=recipient_names if recipient_names else ["No recipients available"],
            state="readonly" if recipient_names else "disabled",
        )
        if recipient_names:
            self.recipient_combo.set(recipient_names[0])
        self.recipient_combo.grid(
            row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=(PADDING_MEDIUM, 5)
        )
        row += 1

        # Show last year's package if available
        if not self.assignment:
            self.last_year_label = ctk.CTkLabel(
                parent, text="", font=ctk.CTkFont(size=11, slant="italic"), text_color="gray"
            )
            self.last_year_label.grid(
                row=row, column=1, sticky="w", padx=PADDING_MEDIUM, pady=(0, 10)
            )
            row += 1

            # Update last year's info when recipient changes
            self.recipient_combo.configure(command=self._on_recipient_change)

        # Package dropdown (required)
        package_label = ctk.CTkLabel(parent, text="Package*:", anchor="w")
        package_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        package_names = [f"{p.name} (${p.calculate_cost():.2f})" for p in self.available_packages]
        self.package_combo = ctk.CTkComboBox(
            parent,
            width=400,
            values=package_names if package_names else ["No packages available"],
            state="readonly" if package_names else "disabled",
        )
        if package_names:
            self.package_combo.set(package_names[0])
        self.package_combo.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Quantity field (required)
        qty_label = ctk.CTkLabel(parent, text="Quantity*:", anchor="w")
        qty_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        self.quantity_entry = ctk.CTkEntry(parent, width=400, placeholder_text="1")
        self.quantity_entry.insert(0, "1")
        self.quantity_entry.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Notes field (optional)
        notes_label = ctk.CTkLabel(parent, text="Notes:", anchor="w")
        notes_label.grid(row=row, column=0, sticky="nw", padx=PADDING_MEDIUM, pady=5)

        self.notes_text = ctk.CTkTextbox(parent, width=400, height=100)
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

    def _on_recipient_change(self, recipient_name: str):
        """Update last year's package info when recipient changes."""
        if self.assignment:
            return  # Only for new assignments

        # Find recipient
        recipient = None
        for r in self.available_recipients:
            if r.name == recipient_name:
                recipient = r
                break

        if not recipient:
            return

        # Get recipient history
        try:
            from src.services import event_service

            history = event_service.get_recipient_history(recipient.id)

            if history:
                # Show most recent (first in list)
                recent = history[0]
                event = recent["event"]
                package = recent["package"]

                self.last_year_label.configure(text=f"Last received: {package.name} ({event.name})")
            else:
                self.last_year_label.configure(text="No previous packages")

        except Exception:
            pass

    def _populate_form(self):
        """Populate form fields with existing assignment data."""
        if not self.assignment:
            return

        # Set recipient (disabled for editing)
        if self.assignment.recipient:
            for r in self.available_recipients:
                if r.id == self.assignment.recipient_id:
                    self.recipient_combo.set(r.name)
                    break
            self.recipient_combo.configure(state="disabled")  # Can't change recipient

        # Set package
        if self.assignment.package:
            for p in self.available_packages:
                if p.id == self.assignment.package_id:
                    cost = p.calculate_cost()
                    self.package_combo.set(f"{p.name} (${cost:.2f})")
                    break

        # Set quantity
        self.quantity_entry.delete(0, "end")
        self.quantity_entry.insert(0, str(self.assignment.quantity))

        # Set notes
        if self.assignment.notes:
            self.notes_text.insert("1.0", self.assignment.notes)

    def _save(self):
        """Validate and save the assignment data."""
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
            Dictionary with assignment data, or None if validation fails
        """
        # Get values
        recipient_name = self.recipient_combo.get()
        package_name = self.package_combo.get()
        quantity_str = self.quantity_entry.get().strip()
        notes = self.notes_text.get("1.0", "end-1c").strip()

        # Validate recipient
        if not recipient_name or recipient_name == "No recipients available":
            show_error(
                "Validation Error",
                "Please select a recipient",
                parent=self,
            )
            return None

        recipient = None
        for r in self.available_recipients:
            if r.name == recipient_name:
                recipient = r
                break

        if not recipient:
            show_error(
                "Validation Error",
                "Selected recipient not found",
                parent=self,
            )
            return None

        # Validate package
        if not package_name or package_name == "No packages available":
            show_error(
                "Validation Error",
                "Please select a package",
                parent=self,
            )
            return None

        # Extract package name (remove cost suffix)
        if " ($" in package_name:
            package_name = package_name.split(" ($")[0]

        package = None
        for p in self.available_packages:
            if p.name == package_name:
                package = p
                break

        if not package:
            show_error(
                "Validation Error",
                "Selected package not found",
                parent=self,
            )
            return None

        # Validate quantity
        try:
            quantity = int(quantity_str)
            if quantity <= 0:
                raise ValueError("Quantity must be greater than 0")
        except ValueError as e:
            show_error(
                "Validation Error",
                "Quantity must be a positive number",
                parent=self,
            )
            return None

        # Validate notes length
        if notes and len(notes) > MAX_NOTES_LENGTH:
            show_error(
                "Validation Error",
                f"Notes must be {MAX_NOTES_LENGTH} characters or less",
                parent=self,
            )
            return None

        # Return validated data
        return {
            "recipient_id": recipient.id,
            "package_id": package.id,
            "quantity": quantity,
            "notes": notes if notes else None,
        }

    def get_result(self) -> Optional[Dict[str, Any]]:
        """Get the dialog result."""
        return self.result
