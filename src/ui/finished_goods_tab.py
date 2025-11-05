"""
Finished Goods tab for the Seasonal Baking Tracker.

Provides full CRUD interface for managing finished goods with cost calculations
and batch planning.
"""

import customtkinter as ctk
from typing import Optional

from src.models.finished_good import FinishedGood
from src.services import finished_good_service
from src.utils.constants import (
    RECIPE_CATEGORIES,
    PADDING_MEDIUM,
    PADDING_LARGE,
    COLOR_SUCCESS,
    COLOR_ERROR,
)
from src.ui.widgets.search_bar import SearchBar
from src.ui.widgets.data_table import FinishedGoodDataTable
from src.ui.widgets.dialogs import (
    show_confirmation,
    show_error,
    show_success,
    show_info,
)
from src.ui.forms.finished_good_form import FinishedGoodFormDialog


class FinishedGoodsTab(ctk.CTkFrame):
    """
    Finished Goods management tab with full CRUD capabilities.

    Provides interface for:
    - Viewing all finished goods in a searchable table
    - Adding new finished goods
    - Editing existing finished goods
    - Deleting finished goods
    - Viewing finished good details and costs
    - Filtering by category
    """

    def __init__(self, parent):
        """
        Initialize the finished goods tab.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.selected_finished_good: Optional[FinishedGood] = None

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
        """Create the search bar with category filter."""
        self.search_bar = SearchBar(
            self,
            search_callback=self._on_search,
            categories=["All Categories"] + RECIPE_CATEGORIES,
            placeholder="Search by finished good name...",
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
            text="+ Add Finished Good",
            command=self._add_finished_good,
            width=180,
        )
        add_button.grid(row=0, column=0, padx=PADDING_MEDIUM)

        # Edit button
        self.edit_button = ctk.CTkButton(
            button_frame,
            text="Edit",
            command=self._edit_finished_good,
            width=120,
            state="disabled",
        )
        self.edit_button.grid(row=0, column=1, padx=PADDING_MEDIUM)

        # Delete button
        self.delete_button = ctk.CTkButton(
            button_frame,
            text="Delete",
            command=self._delete_finished_good,
            width=120,
            state="disabled",
            fg_color="darkred",
            hover_color="red",
        )
        self.delete_button.grid(row=0, column=2, padx=PADDING_MEDIUM)

        # View Details button
        self.details_button = ctk.CTkButton(
            button_frame,
            text="View Details",
            command=self._view_details,
            width=150,
            state="disabled",
        )
        self.details_button.grid(row=0, column=3, padx=PADDING_MEDIUM)

        # Refresh button
        refresh_button = ctk.CTkButton(
            button_frame,
            text="Refresh",
            command=self.refresh,
            width=120,
        )
        refresh_button.grid(row=0, column=4, padx=PADDING_MEDIUM)

    def _create_data_table(self):
        """Create the data table for displaying finished goods."""
        self.data_table = FinishedGoodDataTable(
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
        Handle search and filter.

        Args:
            search_text: Search query
            category: Selected category filter
        """
        # Determine category filter
        category_filter = None
        if category and category != "All Categories":
            category_filter = category

        # Get filtered finished goods
        try:
            finished_goods = finished_good_service.get_all_finished_goods(
                name_search=search_text if search_text else None,
                category=category_filter,
            )
            self.data_table.set_data(finished_goods)
            self._update_status(f"Found {len(finished_goods)} finished good(s)")
        except Exception as e:
            show_error("Search Error", f"Failed to search finished goods: {str(e)}", parent=self)
            self._update_status("Search failed", error=True)

    def _on_row_select(self, finished_good: Optional[FinishedGood]):
        """
        Handle row selection.

        Args:
            finished_good: Selected finished good (None if deselected)
        """
        self.selected_finished_good = finished_good

        # Enable/disable action buttons
        has_selection = finished_good is not None
        self.edit_button.configure(state="normal" if has_selection else "disabled")
        self.delete_button.configure(state="normal" if has_selection else "disabled")
        self.details_button.configure(state="normal" if has_selection else "disabled")

        if finished_good:
            self._update_status(f"Selected: {finished_good.name}")
        else:
            self._update_status("Ready")

    def _on_row_double_click(self, finished_good: FinishedGood):
        """
        Handle row double-click (view details).

        Args:
            finished_good: Double-clicked finished good
        """
        self.selected_finished_good = finished_good
        self._view_details()

    def _add_finished_good(self):
        """Show dialog to add a new finished good."""
        dialog = FinishedGoodFormDialog(self, title="Add New Finished Good")
        result = dialog.get_result()

        if result:
            try:
                # Create finished good
                new_fg = finished_good_service.create_finished_good(result)

                show_success(
                    "Success",
                    f"Finished good '{new_fg.name}' added successfully",
                    parent=self,
                )
                self.refresh()
                self._update_status(f"Added: {new_fg.name}", success=True)
            except Exception as e:
                show_error(
                    "Error",
                    f"Failed to add finished good: {str(e)}",
                    parent=self,
                )
                self._update_status("Failed to add finished good", error=True)

    def _edit_finished_good(self):
        """Show dialog to edit the selected finished good."""
        if not self.selected_finished_good:
            return

        try:
            # Reload finished good to avoid lazy loading issues
            fg = finished_good_service.get_finished_good(self.selected_finished_good.id)

            dialog = FinishedGoodFormDialog(
                self,
                finished_good=fg,
                title=f"Edit Finished Good: {fg.name}",
            )
            result = dialog.get_result()
        except Exception as e:
            show_error(
                "Error",
                f"Failed to load finished good for editing: {str(e)}",
                parent=self,
            )
            return

        if result:
            try:
                # Update finished good
                updated_fg = finished_good_service.update_finished_good(
                    self.selected_finished_good.id,
                    result,
                )

                show_success(
                    "Success",
                    f"Finished good '{updated_fg.name}' updated successfully",
                    parent=self,
                )
                self.refresh()
                self._update_status(f"Updated: {updated_fg.name}", success=True)
            except Exception as e:
                show_error(
                    "Error",
                    f"Failed to update finished good: {str(e)}",
                    parent=self,
                )
                self._update_status("Failed to update finished good", error=True)

    def _delete_finished_good(self):
        """Delete the selected finished good after confirmation."""
        if not self.selected_finished_good:
            return

        # Confirm deletion
        confirmed = show_confirmation(
            "Confirm Deletion",
            f"Are you sure you want to delete '{self.selected_finished_good.name}'?\n\n"
            "This will remove the finished good.\n"
            "This action cannot be undone.",
            parent=self,
        )

        if confirmed:
            try:
                finished_good_service.delete_finished_good(self.selected_finished_good.id)
                show_success(
                    "Success",
                    f"Finished good '{self.selected_finished_good.name}' deleted successfully",
                    parent=self,
                )
                self.selected_finished_good = None
                self.refresh()
                self._update_status("Finished good deleted", success=True)
            except finished_good_service.FinishedGoodInUse as e:
                show_error(
                    "Cannot Delete",
                    f"This finished good is used in {e.bundle_count} bundle(s).\n\n"
                    "Please delete those bundles first.",
                    parent=self,
                )
                self._update_status("Cannot delete - in use", error=True)
            except Exception as e:
                show_error(
                    "Error",
                    f"Failed to delete finished good: {str(e)}",
                    parent=self,
                )
                self._update_status("Failed to delete finished good", error=True)

    def _view_details(self):
        """Show detailed information about the selected finished good."""
        if not self.selected_finished_good:
            return

        try:
            # Get finished good with relationships
            fg = finished_good_service.get_finished_good(self.selected_finished_good.id)

            # Build details message
            details = []
            details.append(f"Finished Good: {fg.name}")
            details.append(f"Recipe: {fg.recipe.name}")

            if fg.category:
                details.append(f"Category: {fg.category}")

            details.append("")
            details.append(f"Yield Mode: {fg.yield_mode.value.replace('_', ' ').title()}")

            if fg.yield_mode.value == "discrete_count":
                details.append(f"Items per Batch: {fg.items_per_batch}")
                details.append(f"Item Unit: {fg.item_unit}")
            else:
                details.append(f"Batch Percentage: {fg.batch_percentage}%")
                if fg.portion_description:
                    details.append(f"Portion: {fg.portion_description}")

            details.append("")
            details.append("Cost Information:")
            cost_per_item = fg.get_cost_per_item()
            details.append(f"  Cost per Item: ${cost_per_item:.4f}")

            # Recipe cost breakdown
            recipe_cost = fg.recipe.calculate_cost()
            details.append(f"  Recipe Total Cost: ${recipe_cost:.2f}")

            # Batch calculation example
            details.append("")
            details.append("Batch Planning:")
            if fg.yield_mode.value == "discrete_count":
                details.append(f"  Example: Need 50 items → {fg.calculate_batches_needed(50):.2f} batches")
            else:
                details.append(f"  Example: Need 2 items → {fg.calculate_batches_needed(2):.2f} batches")

            if fg.notes:
                details.append("")
                details.append("Notes:")
                details.append(f"  {fg.notes}")

            show_info(
                f"Finished Good Details: {fg.name}",
                "\n".join(details),
                parent=self,
            )

        except Exception as e:
            show_error(
                "Error",
                f"Failed to load finished good details: {str(e)}",
                parent=self,
            )

    def refresh(self):
        """Refresh the finished good list."""
        try:
            finished_goods = finished_good_service.get_all_finished_goods()
            self.data_table.set_data(finished_goods)
            self._update_status(f"Loaded {len(finished_goods)} finished good(s)")
        except Exception as e:
            show_error(
                "Error",
                f"Failed to load finished goods: {str(e)}",
                parent=self,
            )
            self._update_status("Failed to load finished goods", error=True)

    def _update_status(self, message: str, success: bool = False, error: bool = False):
        """
        Update status bar message.

        Args:
            message: Status message
            success: Whether this is a success message (green)
            error: Whether this is an error message (red)
        """
        self.status_label.configure(text=message)

        # Set color based on message type
        if success:
            self.status_label.configure(text_color=COLOR_SUCCESS)
        elif error:
            self.status_label.configure(text_color=COLOR_ERROR)
        else:
            self.status_label.configure(text_color=("gray10", "gray90"))  # Default theme colors
