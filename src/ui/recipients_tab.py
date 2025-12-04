"""
Recipients tab for the Seasonal Baking Tracker.

Provides full CRUD interface for managing gift package recipients.
"""

import customtkinter as ctk
from typing import Optional

from src.models.recipient import Recipient
from src.services import recipient_service
from src.services.recipient_service import RecipientNotFound, RecipientInUse
from src.utils.constants import (
    PADDING_MEDIUM,
    PADDING_LARGE,
)
from src.ui.widgets.search_bar import SearchBar
from src.ui.widgets.data_table import RecipientDataTable
from src.ui.widgets.dialogs import (
    show_confirmation,
    show_error,
    show_success,
)
from src.ui.forms.recipient_form import RecipientFormDialog


class RecipientsTab(ctk.CTkFrame):
    """
    Recipients management tab with full CRUD capabilities.

    Provides interface for:
    - Viewing all recipients in a searchable table
    - Adding new recipients
    - Editing existing recipients
    - Deleting recipients
    - Filtering by name/household
    """

    def __init__(self, parent):
        """
        Initialize the recipients tab.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.selected_recipient: Optional[Recipient] = None

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Search bar
        self.grid_rowconfigure(1, weight=0)  # Action buttons
        self.grid_rowconfigure(2, weight=1)  # Data table
        self.grid_rowconfigure(3, weight=0)  # Status bar

        # Create UI components
        self._create_search_bar()
        self._create_action_buttons()
        self._create_data_table()
        self._create_status_bar()

        # Load initial data
        self.refresh()

        # Grid the frame
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def _create_search_bar(self):
        """Create the search bar."""
        self.search_bar = SearchBar(
            self,
            search_callback=self._on_search,
            placeholder="Search by name or household...",
        )
        self.search_bar.grid(
            row=0, column=0, sticky="ew", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_MEDIUM)
        )

    def _create_action_buttons(self):
        """Create action buttons for CRUD operations."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_MEDIUM)

        # Add button
        add_button = ctk.CTkButton(
            button_frame,
            text="➕ Add Recipient",
            command=self._add_recipient,
            width=150,
        )
        add_button.grid(row=0, column=0, padx=PADDING_MEDIUM)

        # Edit button
        self.edit_button = ctk.CTkButton(
            button_frame,
            text="✏️ Edit",
            command=self._edit_recipient,
            width=120,
            state="disabled",
        )
        self.edit_button.grid(row=0, column=1, padx=PADDING_MEDIUM)

        # Delete button
        self.delete_button = ctk.CTkButton(
            button_frame,
            text="🗑️ Delete",
            command=self._delete_recipient,
            width=120,
            state="disabled",
            fg_color="darkred",
            hover_color="red",
        )
        self.delete_button.grid(row=0, column=2, padx=PADDING_MEDIUM)

        # Refresh button
        refresh_button = ctk.CTkButton(
            button_frame,
            text="🔄 Refresh",
            command=self.refresh,
            width=120,
        )
        refresh_button.grid(row=0, column=3, padx=PADDING_MEDIUM)

    def _create_data_table(self):
        """Create the data table for displaying recipients."""
        self.data_table = RecipientDataTable(
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

    def _on_search(self, search_text: str, category: Optional[str] = None):
        """
        Handle search.

        Args:
            search_text: Search query
            category: Not used for recipients
        """
        # Get filtered recipients
        try:
            recipients = recipient_service.get_all_recipients(
                name_search=search_text if search_text else None
            )
            self.data_table.set_data(recipients)
            self._update_status(f"Found {len(recipients)} recipient(s)")
        except Exception as e:
            show_error("Search Error", f"Failed to search recipients: {str(e)}", parent=self)
            self._update_status("Search failed", error=True)

    def _on_row_select(self, recipient: Optional[Recipient]):
        """
        Handle row selection.

        Args:
            recipient: Selected recipient (None if deselected)
        """
        self.selected_recipient = recipient

        # Enable/disable action buttons
        has_selection = recipient is not None
        self.edit_button.configure(state="normal" if has_selection else "disabled")
        self.delete_button.configure(state="normal" if has_selection else "disabled")

    def _on_row_double_click(self, recipient: Recipient):
        """
        Handle row double-click (opens edit dialog).

        Args:
            recipient: Double-clicked recipient
        """
        self._edit_recipient()

    def _add_recipient(self):
        """Open dialog to add a new recipient."""
        dialog = RecipientFormDialog(self, title="Add Recipient")
        self.wait_window(dialog)

        result = dialog.get_result()
        if result:
            try:
                recipient_service.create_recipient(result)
                show_success(
                    "Success", f"Recipient '{result['name']}' added successfully", parent=self
                )
                self.refresh()
            except Exception as e:
                show_error("Error", f"Failed to add recipient: {str(e)}", parent=self)

    def _edit_recipient(self):
        """Open dialog to edit the selected recipient."""
        if not self.selected_recipient:
            return

        dialog = RecipientFormDialog(
            self, recipient=self.selected_recipient, title="Edit Recipient"
        )
        self.wait_window(dialog)

        result = dialog.get_result()
        if result:
            try:
                recipient_service.update_recipient(self.selected_recipient.id, result)
                show_success("Success", "Recipient updated successfully", parent=self)
                self.refresh()
            except RecipientNotFound:
                show_error("Error", "Recipient not found", parent=self)
                self.refresh()
            except Exception as e:
                show_error("Error", f"Failed to update recipient: {str(e)}", parent=self)

    def _delete_recipient(self):
        """Delete the selected recipient after confirmation."""
        if not self.selected_recipient:
            return

        # Confirm deletion
        if not show_confirmation(
            "Confirm Deletion",
            f"Are you sure you want to delete recipient '{self.selected_recipient.name}'?\n\n"
            "This action cannot be undone.",
            parent=self,
        ):
            return

        try:
            recipient_service.delete_recipient(self.selected_recipient.id)
            show_success("Success", "Recipient deleted successfully", parent=self)
            self.selected_recipient = None
            self.refresh()
        except RecipientInUse as e:
            show_error(
                "Cannot Delete",
                f"This recipient is used in {e.event_count} event(s) and cannot be deleted.",
                parent=self,
            )
        except RecipientNotFound:
            show_error("Error", "Recipient not found", parent=self)
            self.refresh()
        except Exception as e:
            show_error("Error", f"Failed to delete recipient: {str(e)}", parent=self)

    def refresh(self):
        """Refresh the recipients list."""
        try:
            recipients = recipient_service.get_all_recipients()
            self.data_table.set_data(recipients)
            self._update_status(f"Loaded {len(recipients)} recipient(s)")
        except Exception as e:
            show_error("Error", f"Failed to load recipients: {str(e)}", parent=self)
            self._update_status("Failed to load recipients", error=True)

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
