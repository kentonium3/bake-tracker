"""
Bundles tab for the Seasonal Baking Tracker.

Provides full CRUD interface for managing bundles (bags/groups of finished goods)
with cost calculations and batch planning.
"""

import customtkinter as ctk
from typing import Optional

from src.models.finished_good import Bundle
from src.services import finished_good_service
from src.utils.constants import (
    PADDING_MEDIUM,
    PADDING_LARGE,
    COLOR_SUCCESS,
    COLOR_ERROR,
)
from src.ui.widgets.search_bar import SearchBar
from src.ui.widgets.data_table import BundleDataTable
from src.ui.widgets.dialogs import (
    show_confirmation,
    show_error,
    show_success,
    show_info,
)
from src.ui.forms.bundle_form import BundleFormDialog
from src.services.exceptions import ServiceError
from src.ui.utils.error_handler import handle_error


class BundlesTab(ctk.CTkFrame):
    """
    Bundles management tab with full CRUD capabilities.

    A bundle represents a bag/group of multiple items of the same
    finished good (e.g., "Bag of 4 Chocolate Chip Cookies").

    Provides interface for:
    - Viewing all bundles in a searchable table
    - Adding new bundles
    - Editing existing bundles
    - Deleting bundles
    - Viewing bundle details and costs
    """

    def __init__(self, parent):
        """
        Initialize the bundles tab.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.selected_bundle: Optional[Bundle] = None

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
            categories=None,  # No category filter for bundles
            placeholder="Search by bundle name...",
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
            text="+ Add Bundle",
            command=self._add_bundle,
            width=150,
        )
        add_button.grid(row=0, column=0, padx=PADDING_MEDIUM)

        # Edit button
        self.edit_button = ctk.CTkButton(
            button_frame,
            text="Edit",
            command=self._edit_bundle,
            width=120,
            state="disabled",
        )
        self.edit_button.grid(row=0, column=1, padx=PADDING_MEDIUM)

        # Delete button
        self.delete_button = ctk.CTkButton(
            button_frame,
            text="Delete",
            command=self._delete_bundle,
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
        """Create the data table for displaying bundles."""
        self.data_table = BundleDataTable(
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
            category: Not used for bundles
        """
        # Get filtered bundles
        try:
            bundles = finished_good_service.get_all_bundles(
                name_search=search_text if search_text else None,
            )
            self.data_table.set_data(bundles)
            self._update_status(f"Found {len(bundles)} bundle(s)")
        except ServiceError as e:
            handle_error(e, parent=self, operation="Search bundles")
            self._update_status("Search failed", error=True)
        except Exception as e:
            handle_error(e, parent=self, operation="Search bundles")
            self._update_status("Search failed", error=True)

    def _on_row_select(self, bundle: Optional[Bundle]):
        """
        Handle row selection.

        Args:
            bundle: Selected bundle (None if deselected)
        """
        self.selected_bundle = bundle

        # Enable/disable action buttons
        has_selection = bundle is not None
        self.edit_button.configure(state="normal" if has_selection else "disabled")
        self.delete_button.configure(state="normal" if has_selection else "disabled")
        self.details_button.configure(state="normal" if has_selection else "disabled")

        if bundle:
            self._update_status(f"Selected: {bundle.name}")
        else:
            self._update_status("Ready")

    def _on_row_double_click(self, bundle: Bundle):
        """
        Handle row double-click (view details).

        Args:
            bundle: Double-clicked bundle
        """
        self.selected_bundle = bundle
        self._view_details()

    def _add_bundle(self):
        """Show dialog to add a new bundle."""
        dialog = BundleFormDialog(self, title="Add New Bundle")
        result = dialog.get_result()

        if result:
            try:
                # Create bundle
                new_bundle = finished_good_service.create_bundle(result)

                show_success(
                    "Success",
                    f"Bundle '{new_bundle.name}' added successfully",
                    parent=self,
                )
                self.refresh()
                self._update_status(f"Added: {new_bundle.name}", success=True)
            except ServiceError as e:
                handle_error(e, parent=self, operation="Add bundle")
                self._update_status("Failed to add bundle", error=True)
            except Exception as e:
                handle_error(e, parent=self, operation="Add bundle")
                self._update_status("Failed to add bundle", error=True)

    def _edit_bundle(self):
        """Show dialog to edit the selected bundle."""
        if not self.selected_bundle:
            return

        try:
            # Reload bundle to avoid lazy loading issues
            bundle = finished_good_service.get_bundle(self.selected_bundle.id)

            dialog = BundleFormDialog(
                self,
                bundle=bundle,
                title=f"Edit Bundle: {bundle.name}",
            )
            result = dialog.get_result()
        except ServiceError as e:
            handle_error(e, parent=self, operation="Load bundle for editing")
            return
        except Exception as e:
            handle_error(e, parent=self, operation="Load bundle for editing")
            return

        if result:
            try:
                # Update bundle
                updated_bundle = finished_good_service.update_bundle(
                    self.selected_bundle.id,
                    result,
                )

                show_success(
                    "Success",
                    f"Bundle '{updated_bundle.name}' updated successfully",
                    parent=self,
                )
                self.refresh()
                self._update_status(f"Updated: {updated_bundle.name}", success=True)
            except ServiceError as e:
                handle_error(e, parent=self, operation="Update bundle")
                self._update_status("Failed to update bundle", error=True)
            except Exception as e:
                handle_error(e, parent=self, operation="Update bundle")
                self._update_status("Failed to update bundle", error=True)

    def _delete_bundle(self):
        """Delete the selected bundle after confirmation."""
        if not self.selected_bundle:
            return

        # Confirm deletion
        confirmed = show_confirmation(
            "Confirm Deletion",
            f"Are you sure you want to delete '{self.selected_bundle.name}'?\n\n"
            "This action cannot be undone.",
            parent=self,
        )

        if confirmed:
            try:
                finished_good_service.delete_bundle(self.selected_bundle.id)
                show_success(
                    "Success",
                    f"Bundle '{self.selected_bundle.name}' deleted successfully",
                    parent=self,
                )
                self.selected_bundle = None
                self.refresh()
                self._update_status("Bundle deleted", success=True)
            except ServiceError as e:
                handle_error(e, parent=self, operation="Delete bundle")
                self._update_status("Failed to delete bundle", error=True)
            except Exception as e:
                handle_error(e, parent=self, operation="Delete bundle")
                self._update_status("Failed to delete bundle", error=True)

    def _view_details(self):
        """Show detailed information about the selected bundle."""
        if not self.selected_bundle:
            return

        try:
            # Get bundle with relationships
            bundle = finished_good_service.get_bundle(self.selected_bundle.id)

            # Build details message
            details = []
            details.append(f"Bundle: {bundle.name}")
            details.append(f"Finished Good: {bundle.finished_good.display_name}")
            details.append(f"Quantity: {bundle.quantity} items")

            details.append("")
            details.append("Cost Information:")
            bundle_cost = bundle.calculate_cost()
            details.append(f"  Bundle Cost: ${bundle_cost:.2f}")

            cost_per_item = bundle.finished_good.get_cost_per_item()
            details.append(f"  Cost per Item: ${cost_per_item:.4f}")

            # Batch calculation
            details.append("")
            details.append("Batch Planning:")
            batches_needed = bundle.calculate_batches_needed()
            details.append(f"  Batches Needed: {batches_needed:.2f}")

            # Recipe info
            details.append("")
            details.append("Recipe Information:")
            details.append(f"  Recipe: {bundle.finished_good.recipe.name}")
            recipe_cost = bundle.finished_good.recipe.calculate_cost()
            details.append(f"  Recipe Cost: ${recipe_cost:.2f}")

            # Finished good info
            details.append("")
            details.append("Finished Good Info:")
            if bundle.finished_good.yield_mode.value == "discrete_count":
                details.append(f"  Type: Discrete Items")
                details.append(f"  Items per Batch: {bundle.finished_good.items_per_batch}")
                details.append(f"  Unit: {bundle.finished_good.item_unit}")
            else:
                details.append(f"  Type: Batch Portion")
                details.append(f"  Batch %: {bundle.finished_good.batch_percentage}%")

            if bundle.packaging_notes:
                details.append("")
                details.append("Packaging Notes:")
                details.append(f"  {bundle.packaging_notes}")

            show_info(
                f"Bundle Details: {bundle.name}",
                "\n".join(details),
                parent=self,
            )

        except ServiceError as e:
            handle_error(e, parent=self, operation="Load bundle details")
        except Exception as e:
            handle_error(e, parent=self, operation="Load bundle details")

    def refresh(self):
        """Refresh the bundle list."""
        try:
            bundles = finished_good_service.get_all_bundles()
            self.data_table.set_data(bundles)
            self._update_status(f"Loaded {len(bundles)} bundle(s)")
        except ServiceError as e:
            handle_error(e, parent=self, operation="Load bundles")
            self._update_status("Failed to load bundles", error=True)
        except Exception as e:
            handle_error(e, parent=self, operation="Load bundles")
            self._update_status("Failed to load bundles", error=True)

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
