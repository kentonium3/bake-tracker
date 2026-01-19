"""
Recipients tab for the Seasonal Baking Tracker.

Provides full CRUD interface for managing gift package recipients.

Feature 017 - Added package history view.
"""

import customtkinter as ctk
from datetime import date
from typing import Optional

from src.models.recipient import Recipient
from src.services import recipient_service, event_service
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

        # Data will be loaded when tab is first selected (lazy loading)
        # self.refresh()

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

        # Feature 017: View History button
        self.history_button = ctk.CTkButton(
            button_frame,
            text="📋 View History",
            command=self._view_history,
            width=130,
            state="disabled",
        )
        self.history_button.grid(row=0, column=3, padx=PADDING_MEDIUM)

        # Refresh button
        refresh_button = ctk.CTkButton(
            button_frame,
            text="🔄 Refresh",
            command=self.refresh,
            width=120,
        )
        refresh_button.grid(row=0, column=4, padx=PADDING_MEDIUM)

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
        self.history_button.configure(state="normal" if has_selection else "disabled")

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

    # =========================================================================
    # Feature 017: Recipient History
    # =========================================================================

    def _view_history(self):
        """Open dialog to view selected recipient's package history (Feature 017)."""
        if not self.selected_recipient:
            return

        dialog = RecipientHistoryDialog(self, self.selected_recipient)
        self.wait_window(dialog)


# Feature 017: Dialog for viewing recipient package history


class RecipientHistoryDialog(ctk.CTkToplevel):
    """
    Dialog for viewing a recipient's package history across all events.

    Feature 017 - WP06 (T024-T026)
    """

    def __init__(self, parent, recipient: Recipient):
        """
        Initialize the recipient history dialog.

        Args:
            parent: Parent window
            recipient: Recipient to show history for
        """
        super().__init__(parent)

        self.recipient = recipient

        # Configure window
        self.title(f"Package History - {recipient.name}")
        self.geometry("700x500")
        self.resizable(True, True)

        # Center on parent
        self.transient(parent)

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Create header
        self._create_header()

        # Create history display
        self._create_history_display()

        # Create close button
        self._create_buttons()

        # Load history data
        self._load_history()

        # Center dialog on parent
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

    def _create_header(self):
        """Create the header section."""
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)

        ctk.CTkLabel(
            header_frame,
            text=f"Package History for {self.recipient.name}",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w")

        if self.recipient.household_name:
            ctk.CTkLabel(
                header_frame,
                text=f"Household: {self.recipient.household_name}",
                font=ctk.CTkFont(size=12),
                text_color="gray",
            ).pack(anchor="w")

    def _create_history_display(self):
        """Create the scrollable history display area."""
        self.history_frame = ctk.CTkScrollableFrame(self)
        self.history_frame.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=PADDING_LARGE,
            pady=(0, PADDING_MEDIUM),
        )
        self.history_frame.grid_columnconfigure(0, weight=1)

    def _create_buttons(self):
        """Create dialog buttons."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=2, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)
        button_frame.grid_columnconfigure(0, weight=1)

        close_button = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self.destroy,
            width=150,
        )
        close_button.grid(row=0, column=0)

    def _load_history(self):
        """Load and display recipient's package history (T025)."""
        try:
            history = event_service.get_recipient_history(self.recipient.id)
        except Exception as e:
            ctk.CTkLabel(
                self.history_frame,
                text=f"Error loading history: {e}",
                text_color="red",
            ).pack(pady=20)
            return

        if not history:
            ctk.CTkLabel(
                self.history_frame,
                text="No package history for this recipient",
                text_color="gray",
                font=ctk.CTkFont(size=14, slant="italic"),
            ).pack(pady=50)
            return

        # T026: Sort by event date descending (service should already sort, but ensure)
        history.sort(
            key=lambda r: r["event"].event_date if r.get("event") else date.min,
            reverse=True,
        )

        # Create table header
        header_frame = ctk.CTkFrame(self.history_frame, fg_color=("gray85", "gray25"))
        header_frame.pack(fill="x", pady=(0, 5))

        columns = [
            ("Event", 150),
            ("Date", 100),
            ("Package", 150),
            ("Qty", 50),
            ("Status", 100),
        ]

        for col_name, width in columns:
            ctk.CTkLabel(
                header_frame,
                text=col_name,
                width=width,
                font=ctk.CTkFont(weight="bold"),
                anchor="w",
            ).pack(side="left", padx=5, pady=8)

        # Data rows
        for record in history:
            self._create_history_row(record)

        # Summary at bottom
        self._create_summary(history)

    def _create_history_row(self, record: dict):
        """Create a single history row (T025)."""
        row_frame = ctk.CTkFrame(self.history_frame, fg_color="transparent")
        row_frame.pack(fill="x", pady=1)

        # Event name
        event_name = record["event"].name if record.get("event") else "Unknown"
        ctk.CTkLabel(row_frame, text=event_name, width=150, anchor="w").pack(side="left", padx=5)

        # Event date
        event_date_str = ""
        if record.get("event") and record["event"].event_date:
            event_date_str = record["event"].event_date.strftime("%Y-%m-%d")
        ctk.CTkLabel(row_frame, text=event_date_str, width=100, anchor="w").pack(
            side="left", padx=5
        )

        # Package name
        package_name = record["package"].name if record.get("package") else "Unknown"
        ctk.CTkLabel(row_frame, text=package_name, width=150, anchor="w").pack(side="left", padx=5)

        # Quantity
        ctk.CTkLabel(row_frame, text=str(record.get("quantity", 1)), width=50, anchor="w").pack(
            side="left", padx=5
        )

        # Status with color coding
        status = record.get("fulfillment_status", "pending") or "pending"
        status_colors = {
            "pending": ("#D4A574", "black"),  # Orange
            "ready": ("#90EE90", "black"),  # Green
            "delivered": ("#87CEEB", "black"),  # Blue
        }
        bg_color, text_color = status_colors.get(status, (None, None))

        status_label = ctk.CTkLabel(
            row_frame,
            text=f"  {status.capitalize()}  ",
            width=100,
            anchor="w",
        )
        if bg_color:
            status_label.configure(fg_color=bg_color, text_color=text_color, corner_radius=3)
        status_label.pack(side="left", padx=5)

    def _create_summary(self, history: list):
        """Create summary section at the bottom."""
        summary_frame = ctk.CTkFrame(self.history_frame, fg_color=("gray90", "gray20"))
        summary_frame.pack(fill="x", pady=(15, 0))

        # Count events and packages
        event_ids = set(r["event"].id for r in history if r.get("event"))
        total_packages = sum(r.get("quantity", 1) for r in history)

        # Count by status
        status_counts = {"pending": 0, "ready": 0, "delivered": 0}
        for r in history:
            status = r.get("fulfillment_status", "pending") or "pending"
            if status in status_counts:
                status_counts[status] += r.get("quantity", 1)

        ctk.CTkLabel(
            summary_frame,
            text=f"Total: {total_packages} package(s) across {len(event_ids)} event(s)",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Status breakdown
        status_text = (
            f"Pending: {status_counts['pending']} | "
            f"Ready: {status_counts['ready']} | "
            f"Delivered: {status_counts['delivered']}"
        )
        ctk.CTkLabel(
            summary_frame,
            text=status_text,
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).pack(anchor="w", padx=10, pady=(0, 10))
