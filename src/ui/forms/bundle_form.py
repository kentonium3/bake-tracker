"""
Bundle form dialog for adding and editing bundles.

Provides a form for creating and updating bundle records
(bags/groups of finished goods).
"""

import customtkinter as ctk
from typing import Optional, Dict, Any

from src.models.finished_good import Bundle
from src.services import finished_good_service
from src.services.exceptions import ServiceError
from src.utils.constants import (
    MAX_NAME_LENGTH,
    MAX_NOTES_LENGTH,
    PADDING_MEDIUM,
    PADDING_LARGE,
)
from src.ui.widgets.dialogs import show_error


class BundleFormDialog(ctk.CTkToplevel):
    """
    Dialog for creating or editing a bundle.

    A bundle represents a bag/group of multiple items of the same
    finished good (e.g., "Bag of 4 Chocolate Chip Cookies").
    """

    def __init__(
        self,
        parent,
        bundle: Optional[Bundle] = None,
        title: str = "Add Bundle",
    ):
        """
        Initialize the bundle form dialog.

        Args:
            parent: Parent window
            bundle: Existing bundle to edit (None for new)
            title: Dialog title
        """
        super().__init__(parent)

        self.bundle = bundle
        self.result = None

        # Load available finished goods
        try:
            self.available_finished_goods = finished_good_service.get_all_finished_goods()
        except (ServiceError, Exception):
            self.available_finished_goods = []

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
        if self.bundle:
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

        # Name field (required)
        name_label = ctk.CTkLabel(parent, text="Bundle Name*:", anchor="w")
        name_label.grid(
            row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=(PADDING_MEDIUM, 5)
        )

        self.name_entry = ctk.CTkEntry(
            parent, width=400, placeholder_text="e.g., Bag of 4 Chocolate Chip Cookies"
        )
        self.name_entry.grid(
            row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=(PADDING_MEDIUM, 5)
        )
        row += 1

        # Finished Good dropdown (required)
        fg_label = ctk.CTkLabel(parent, text="Finished Good*:", anchor="w")
        fg_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        fg_names = [fg.display_name for fg in self.available_finished_goods]
        self.finished_good_combo = ctk.CTkComboBox(
            parent,
            width=400,
            values=fg_names if fg_names else ["No finished goods available"],
            state="readonly" if fg_names else "disabled",
        )
        if fg_names:
            self.finished_good_combo.set(fg_names[0])
        self.finished_good_combo.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Quantity field (required)
        quantity_label = ctk.CTkLabel(parent, text="Quantity*:", anchor="w")
        quantity_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        quantity_frame = ctk.CTkFrame(parent, fg_color="transparent")
        quantity_frame.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)

        self.quantity_entry = ctk.CTkEntry(quantity_frame, width=100, placeholder_text="4")
        self.quantity_entry.pack(side="left", padx=(0, 10))

        quantity_help = ctk.CTkLabel(
            quantity_frame,
            text="Number of items per bundle/bag",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        quantity_help.pack(side="left")
        row += 1

        # Packaging notes field (optional)
        notes_label = ctk.CTkLabel(parent, text="Packaging Notes:", anchor="w")
        notes_label.grid(row=row, column=0, sticky="nw", padx=PADDING_MEDIUM, pady=5)

        self.notes_text = ctk.CTkTextbox(parent, width=400, height=120)
        self.notes_text.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Required field note
        required_note = ctk.CTkLabel(
            parent,
            text="* Required fields",
            font=ctk.CTkFont(size=11),
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
        """Populate form fields with existing bundle data."""
        if not self.bundle:
            return

        self.name_entry.insert(0, self.bundle.name)

        # Select finished good
        for idx, fg in enumerate(self.available_finished_goods):
            if fg.id == self.bundle.finished_good_id:
                self.finished_good_combo.set(fg.display_name)
                break

        self.quantity_entry.insert(0, str(self.bundle.quantity))

        if self.bundle.packaging_notes:
            self.notes_text.insert("1.0", self.bundle.packaging_notes)

    def _validate_form(self) -> Optional[Dict[str, Any]]:
        """
        Validate form inputs and return data dictionary.

        Returns:
            Dictionary of form data if valid, None otherwise
        """
        # Get values
        name = self.name_entry.get().strip()
        fg_name = self.finished_good_combo.get()
        quantity_str = self.quantity_entry.get().strip()
        packaging_notes = self.notes_text.get("1.0", "end-1c").strip() or None

        # Validate required fields
        if not name:
            show_error("Validation Error", "Bundle name is required", parent=self)
            return None

        if len(name) > MAX_NAME_LENGTH:
            show_error(
                "Validation Error",
                f"Bundle name must be {MAX_NAME_LENGTH} characters or less",
                parent=self,
            )
            return None

        # Find finished good ID
        finished_good_id = None
        for fg in self.available_finished_goods:
            if fg.name == fg_name:
                finished_good_id = fg.id
                break

        if not finished_good_id:
            show_error("Validation Error", "Please select a valid finished good", parent=self)
            return None

        # Validate quantity
        if not quantity_str:
            show_error("Validation Error", "Quantity is required", parent=self)
            return None

        try:
            quantity = int(quantity_str)
            if quantity <= 0:
                show_error("Validation Error", "Quantity must be greater than zero", parent=self)
                return None
        except ValueError:
            show_error("Validation Error", "Quantity must be a valid whole number", parent=self)
            return None

        if packaging_notes and len(packaging_notes) > MAX_NOTES_LENGTH:
            show_error(
                "Validation Error",
                f"Packaging notes must be {MAX_NOTES_LENGTH} characters or less",
                parent=self,
            )
            return None

        # Return validated data
        return {
            "name": name,
            "finished_good_id": finished_good_id,
            "quantity": quantity,
            "packaging_notes": packaging_notes,
        }

    def _save(self):
        """Handle save button click."""
        data = self._validate_form()
        if data:
            self.result = data
            self.destroy()

    def _cancel(self):
        """Handle cancel button click."""
        self.result = None
        self.destroy()

    def get_result(self) -> Optional[Dict[str, Any]]:
        """
        Wait for dialog to close and return result.

        Returns:
            Dictionary of form data if saved, None if cancelled
        """
        self.wait_window()
        return self.result
