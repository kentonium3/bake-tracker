"""
Finished Units tab for the Seasonal Baking Tracker.

Provides full CRUD interface for managing individual consumable items (finished units)
with cost calculations and batch planning.
"""

import customtkinter as ctk
import logging
from typing import Optional
from contextlib import contextmanager

# Conditional imports for forward compatibility
try:
    from src.models.finished_unit import FinishedUnit

    HAS_FINISHED_UNIT_MODEL = True
except ImportError:
    # Fall back to FinishedGood model until FinishedUnit is implemented
    from src.models.finished_good import FinishedGood as FinishedUnit

    HAS_FINISHED_UNIT_MODEL = False

try:
    from src.services import finished_unit_service

    HAS_FINISHED_UNIT_SERVICE = True
except ImportError:
    # Fall back to finished_good_service until FinishedUnit service is implemented
    from src.services import finished_good_service as finished_unit_service

    HAS_FINISHED_UNIT_SERVICE = False
from src.utils.constants import (
    RECIPE_CATEGORIES,
    PADDING_MEDIUM,
    PADDING_LARGE,
    COLOR_SUCCESS,
    COLOR_ERROR,
)
from src.ui.widgets.search_bar import SearchBar
from src.ui.widgets.data_table import FinishedGoodDataTable as FinishedUnitDataTable
from src.ui.widgets.dialogs import (
    show_confirmation,
    show_error,
    show_success,
    show_info,
)

# Conditional import for form dialog
try:
    from src.ui.forms.finished_unit_form import FinishedUnitFormDialog

    HAS_FINISHED_UNIT_FORM = True
except ImportError:
    # Fall back to FinishedGood form until FinishedUnit form is implemented
    from src.ui.forms.finished_good_form import FinishedGoodFormDialog as FinishedUnitFormDialog

    HAS_FINISHED_UNIT_FORM = False
from src.ui.service_integration import get_ui_service_integrator, OperationType


# Constants for UI sizing
class ButtonWidths:
    """Button width constants for consistent UI sizing."""

    ADD_BUTTON = 180
    STANDARD_BUTTON = 120
    DETAILS_BUTTON = 150


# Constants for status messages
class StatusMessages:
    """Status message constants for internationalization and consistency."""

    READY = "Ready"
    SEARCH_FAILED = "Search failed"
    FAILED_TO_ADD = "Failed to add finished unit"
    FAILED_TO_UPDATE = "Failed to update finished unit"
    FAILED_TO_DELETE = "Failed to delete finished unit"
    FAILED_TO_LOAD = "Failed to load finished units"
    DELETED_SUCCESS = "Finished unit deleted"
    SELECTION_STALE = "Selected item no longer exists"

    @staticmethod
    def found_units(count: int) -> str:
        return f"Found {count} finished unit(s)"

    @staticmethod
    def selected_unit(name: str) -> str:
        return f"Selected: {name}"

    @staticmethod
    def added_unit(name: str) -> str:
        return f"Added: {name}"

    @staticmethod
    def updated_unit(name: str) -> str:
        return f"Updated: {name}"

    @staticmethod
    def loaded_units(count: int) -> str:
        return f"Loaded {count} finished unit(s)"


class FinishedUnitsTab(ctk.CTkFrame):
    """
    Finished Units management tab with full CRUD capabilities.

    Provides interface for:
    - Viewing all finished units (individual consumable items) in a searchable table
    - Adding new finished units
    - Editing existing finished units
    - Deleting finished units
    - Viewing finished unit details and costs
    - Filtering by category
    """

    def __init__(self, parent):
        """
        Initialize the finished units tab.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.selected_finished_unit: Optional[FinishedUnit] = None
        self.service_integrator = get_ui_service_integrator()

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

    @contextmanager
    def status_context(self, operation_message: str, success_message: Optional[str] = None):
        """
        Context manager for status updates during operations.

        Args:
            operation_message: Message to show while operation is in progress
            success_message: Message to show on successful completion (optional)

        Usage:
            with self.status_context("Creating finished unit", "Unit created successfully"):
                # operation code here
                pass
        """
        # Set initial status
        self._update_status(operation_message)
        try:
            yield
            # Operation succeeded
            if success_message:
                self._update_status(success_message, success=True)
        except Exception as e:
            # Operation failed
            error_msg = getattr(e, "message", str(e))
            self._update_status(f"{operation_message} failed: {error_msg}", error=True)
            raise  # Re-raise the exception

    def _create_search_bar(self):
        """Create the search bar with category filter."""
        self.search_bar = SearchBar(
            self,
            search_callback=self._on_search,
            categories=["All Categories"] + RECIPE_CATEGORIES,
            placeholder="Search by finished unit name...",
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
            text="+ Add Finished Unit",
            command=self._add_finished_unit,
            width=ButtonWidths.ADD_BUTTON,
        )
        add_button.grid(row=0, column=0, padx=PADDING_MEDIUM)

        # Edit button
        self.edit_button = ctk.CTkButton(
            button_frame,
            text="Edit",
            command=self._edit_finished_unit,
            width=ButtonWidths.STANDARD_BUTTON,
            state="disabled",
        )
        self.edit_button.grid(row=0, column=1, padx=PADDING_MEDIUM)

        # Delete button
        self.delete_button = ctk.CTkButton(
            button_frame,
            text="Delete",
            command=self._delete_finished_unit,
            width=ButtonWidths.STANDARD_BUTTON,
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
            width=ButtonWidths.DETAILS_BUTTON,
            state="disabled",
        )
        self.details_button.grid(row=0, column=3, padx=PADDING_MEDIUM)

        # Refresh button
        refresh_button = ctk.CTkButton(
            button_frame,
            text="Refresh",
            command=self.refresh,
            width=ButtonWidths.STANDARD_BUTTON,
        )
        refresh_button.grid(row=0, column=4, padx=PADDING_MEDIUM)

    def _create_data_table(self):
        """Create the data table for displaying finished goods."""
        self.data_table = FinishedUnitDataTable(
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
            text=StatusMessages.READY,
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

    def _on_search(self, search_text: str, category: Optional[str] = None) -> None:
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

        # Get filtered finished units with service integration
        try:
            finished_units = self.service_integrator.execute_service_operation(
                operation_name="Search Finished Units",
                operation_type=OperationType.SEARCH,
                service_function=lambda: finished_unit_service.get_all_finished_units(
                    name_search=search_text if search_text else None, category=category_filter
                ),
                parent_widget=self,
                error_context="Searching finished units",
                log_level=logging.DEBUG,  # Reduce log noise for frequent operations
            )

            self.data_table.set_data(finished_units)
            self._update_status(StatusMessages.found_units(len(finished_units)))

        except Exception as e:
            # Error already handled by service integrator
            logging.exception("Search operation failed after service integrator handling")
            self._update_status(StatusMessages.SEARCH_FAILED, error=True)

    def _on_row_select(self, finished_unit: Optional[FinishedUnit]) -> None:
        """
        Handle row selection.

        Args:
            finished_unit: Selected finished unit (None if deselected)
        """
        self.selected_finished_unit = finished_unit

        # Enable/disable action buttons
        has_selection = finished_unit is not None
        self.edit_button.configure(state="normal" if has_selection else "disabled")
        self.delete_button.configure(state="normal" if has_selection else "disabled")
        self.details_button.configure(state="normal" if has_selection else "disabled")

        if finished_unit:
            self._update_status(StatusMessages.selected_unit(finished_unit.display_name))
        else:
            self._update_status(StatusMessages.READY)

    def _on_row_double_click(self, finished_unit: FinishedUnit) -> None:
        """
        Handle row double-click (view details).

        Args:
            finished_unit: Double-clicked finished good
        """
        self.selected_finished_unit = finished_unit
        self._view_details()

    def _add_finished_unit(self):
        """Show dialog to add a new finished unit."""
        dialog = FinishedUnitFormDialog(self, title="Add New Finished Unit")
        self.wait_window(dialog)
        result = dialog.get_result()

        if result:
            # Validate required fields before service call
            if not self._validate_finished_unit_data(result, "create"):
                return

            # Use service integrator for consistent error handling and logging
            try:
                new_unit = self.service_integrator.execute_service_operation(
                    operation_name="Create Finished Unit",
                    operation_type=OperationType.CREATE,
                    service_function=lambda: finished_unit_service.create_finished_unit(result),
                    parent_widget=self,
                    success_message=f"Finished unit '{result.get('display_name', 'New Unit')}' added successfully",
                    error_context="Creating finished unit",
                    show_success_dialog=True,
                )

                self.refresh()
                self._update_status(StatusMessages.added_unit(new_unit.display_name), success=True)

            except Exception as e:
                # Error already handled by service integrator
                logging.exception(
                    "Add finished unit operation failed after service integrator handling"
                )
                self._update_status(StatusMessages.FAILED_TO_ADD, error=True)

    def _edit_finished_unit(self):
        """Show dialog to edit the selected finished unit."""
        if not self._validate_selected_unit():
            return

        # Load finished unit for editing with service integration
        try:
            unit = self.service_integrator.execute_service_operation(
                operation_name="Load Finished Unit for Edit",
                operation_type=OperationType.READ,
                service_function=lambda: finished_unit_service.get_finished_unit_by_id(
                    self.selected_finished_unit.id
                ),
                parent_widget=self,
                error_context="Loading finished unit for editing",
            )

            dialog = FinishedUnitFormDialog(
                self,
                finished_unit=unit,
                title=f"Edit Finished Unit: {unit.display_name}",
            )
            result = dialog.get_result()

        except Exception as e:
            # Error already handled by service integrator
            logging.exception(
                "Edit finished unit dialog creation failed after service integrator handling"
            )
            return

        if result:
            try:
                updated_unit = self.service_integrator.execute_service_operation(
                    operation_name="Update Finished Unit",
                    operation_type=OperationType.UPDATE,
                    service_function=lambda: finished_unit_service.update_finished_unit(
                        self.selected_finished_unit.id, result
                    ),
                    parent_widget=self,
                    success_message=f"Finished unit '{result.get('display_name', 'Unit')}' updated successfully",
                    error_context="Updating finished unit",
                    show_success_dialog=True,
                )

                self.refresh()
                self._update_status(
                    StatusMessages.updated_unit(updated_unit.display_name), success=True
                )

            except Exception as e:
                # Error already handled by service integrator
                logging.exception(
                    "Update finished unit operation failed after service integrator handling"
                )
                self._update_status(StatusMessages.FAILED_TO_UPDATE, error=True)

    def _delete_finished_unit(self):
        """Delete the selected finished unit after confirmation."""
        if not self._validate_selected_unit():
            return

        # Confirm deletion
        confirmed = show_confirmation(
            "Confirm Deletion",
            f"Are you sure you want to delete '{self.selected_finished_unit.display_name}'?\n\n"
            "This will remove the finished unit.\n"
            "This action cannot be undone.",
            parent=self,
        )

        if confirmed:
            try:
                self.service_integrator.execute_service_operation(
                    operation_name="Delete Finished Unit",
                    operation_type=OperationType.DELETE,
                    service_function=lambda: finished_unit_service.delete_finished_unit(
                        self.selected_finished_unit.id
                    ),
                    parent_widget=self,
                    success_message=f"Finished unit '{self.selected_finished_unit.display_name}' deleted successfully",
                    error_context="Deleting finished unit",
                    show_success_dialog=True,
                )

                self.selected_finished_unit = None
                self.refresh()
                self._update_status(StatusMessages.DELETED_SUCCESS, success=True)

            except Exception as e:
                # Error already handled by service integrator with user-friendly messages
                logging.exception(
                    "Delete finished unit operation failed after service integrator handling"
                )
                self._update_status(StatusMessages.FAILED_TO_DELETE, error=True)

    def _view_details(self):
        """Open the FinishedUnit detail dialog for the selected unit."""
        if not self._validate_selected_unit():
            return

        try:
            # Get finished unit with relationships using service integrator
            fg = self.service_integrator.execute_service_operation(
                operation_name="Load Finished Unit Details",
                operation_type=OperationType.READ,
                service_function=lambda: finished_unit_service.get_finished_unit_by_id(
                    self.selected_finished_unit.id
                ),
                parent_widget=self,
                error_context="Loading finished unit details",
            )

            if not fg:
                return

            # Open detail dialog with callback for inventory refresh
            from src.ui.forms.finished_unit_detail import FinishedUnitDetailDialog

            dialog = FinishedUnitDetailDialog(
                self,
                fg,
                on_inventory_changed=self.refresh,
            )
            self.wait_window(dialog)

        except Exception as e:
            # Error already handled by service integrator
            logging.exception("View details operation failed after service integrator handling")
            pass

    def refresh(self):
        """
        Refresh the finished units list.

        Note: This performs a full refresh which is inefficient for large datasets.
        Consider using incremental update methods for better performance.
        """
        try:
            finished_units = self.service_integrator.execute_service_operation(
                operation_name="Load All Finished Units",
                operation_type=OperationType.READ,
                service_function=lambda: finished_unit_service.get_all_finished_units(),
                parent_widget=self,
                error_context="Loading finished units",
                log_level=logging.DEBUG,  # Reduce log noise for frequent operations
            )

            self.data_table.set_data(finished_units)
            self._update_status(StatusMessages.loaded_units(len(finished_units)))

        except Exception as e:
            # Error already handled by service integrator
            logging.exception(
                "Load finished units operation failed after service integrator handling"
            )
            self._update_status(StatusMessages.FAILED_TO_LOAD, error=True)

    def _add_item_to_table(self, item: FinishedUnit) -> None:
        """
        Add a single item to the table without full refresh.

        TODO: Implement incremental add when data_table supports it.
        For now, falls back to full refresh.
        """
        # Placeholder for future incremental update
        self.refresh()

    def _update_item_in_table(self, item: FinishedUnit) -> None:
        """
        Update a single item in the table without full refresh.

        TODO: Implement incremental update when data_table supports it.
        For now, falls back to full refresh.
        """
        # Placeholder for future incremental update
        self.refresh()

    def _remove_item_from_table(self, item_id: int) -> None:
        """
        Remove a single item from the table without full refresh.

        TODO: Implement incremental removal when data_table supports it.
        For now, falls back to full refresh.
        """
        # Placeholder for future incremental update
        self.refresh()

    def _validate_selected_unit(self) -> bool:
        """
        Validate that the selected unit still exists to prevent race conditions.

        Returns:
            True if selection is valid, False otherwise
        """
        if not self.selected_finished_unit:
            return False

        try:
            # Attempt to reload the selected unit to verify it still exists
            unit = self.service_integrator.execute_service_operation(
                operation_name="Validate Selected Unit",
                operation_type=OperationType.READ,
                service_function=lambda: finished_unit_service.get_finished_unit_by_id(
                    self.selected_finished_unit.id
                ),
                parent_widget=self,
                error_context="Validating selected unit",
                suppress_exception=True,  # Don't show error dialogs for validation checks
            )

            if not unit:
                # Clear stale selection
                self.selected_finished_unit = None
                self._update_status(StatusMessages.SELECTION_STALE, error=True)
                return False

            return True

        except Exception as e:
            # Selection is invalid, clear it
            logging.debug(f"Selected unit validation failed: {e}")
            self.selected_finished_unit = None
            self._update_status(StatusMessages.SELECTION_STALE, error=True)
            return False

    def _validate_finished_unit_data(self, form_data: dict, operation_type: str) -> bool:
        """
        Validate finished unit form data before service operations.

        Args:
            form_data: Form data dictionary from dialog
            operation_type: Type of operation ("create", "update")

        Returns:
            True if validation passes, False if validation fails
        """
        if not form_data:
            show_error("Validation Error", "No form data provided.", parent=self)
            return False

        # Validate required fields
        required_fields = [("display_name", "Display Name"), ("recipe_id", "Recipe")]

        for field_name, field_display in required_fields:
            if not form_data.get(field_name):
                show_error("Validation Error", f"'{field_display}' is required.", parent=self)
                return False

        # Validate display_name format
        display_name = form_data.get("display_name", "").strip()
        if len(display_name) < 2:
            show_error(
                "Validation Error", "Display Name must be at least 2 characters long.", parent=self
            )
            return False

        if len(display_name) > 100:
            show_error(
                "Validation Error", "Display Name cannot exceed 100 characters.", parent=self
            )
            return False

        # Validate slug if provided
        slug = form_data.get("slug", "").strip()
        if slug and not slug.replace("_", "").replace("-", "").isalnum():
            show_error(
                "Validation Error",
                "Slug must only contain letters, numbers, hyphens, and underscores.",
                parent=self,
            )
            return False

        # Validate numerical fields
        try:
            # Validate batch_percentage if provided
            batch_percentage = form_data.get("batch_percentage")
            if batch_percentage is not None:
                batch_percentage = float(batch_percentage)
                if batch_percentage <= 0 or batch_percentage > 100:
                    show_error(
                        "Validation Error",
                        "Batch percentage must be between 0 and 100.",
                        parent=self,
                    )
                    return False

            # Validate items_per_batch if provided
            items_per_batch = form_data.get("items_per_batch")
            if items_per_batch is not None:
                items_per_batch = int(items_per_batch)
                if items_per_batch <= 0:
                    show_error(
                        "Validation Error", "Items per batch must be greater than 0.", parent=self
                    )
                    return False

        except (ValueError, TypeError) as e:
            show_error(
                "Validation Error", f"Invalid numerical value in form data: {e}", parent=self
            )
            return False

        # Validate yield_mode consistency
        yield_mode = form_data.get("yield_mode")
        if yield_mode == "discrete_count":
            if not form_data.get("items_per_batch") or not form_data.get("item_unit"):
                show_error(
                    "Validation Error",
                    "Discrete count mode requires 'Items per Batch' and 'Item Unit'.",
                    parent=self,
                )
                return False
        elif yield_mode == "percentage_based":
            if not form_data.get("batch_percentage"):
                show_error(
                    "Validation Error",
                    "Percentage-based mode requires 'Batch Percentage'.",
                    parent=self,
                )
                return False

        # Additional validation for updates
        if operation_type == "update":
            # Could add specific update validation here if needed
            pass

        return True

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
