"""
Inventory tab for the Seasonal Baking Tracker.

Provides full CRUD interface for managing ingredient inventory with
search, filter, and quantity adjustment capabilities.
"""

import customtkinter as ctk
from typing import Optional, List

from src.models.ingredient import Ingredient
from src.services import inventory_service
from src.utils.constants import (
    INGREDIENT_CATEGORIES,
    PADDING_MEDIUM,
    PADDING_LARGE,
    COLOR_SUCCESS,
    COLOR_ERROR,
)
from src.ui.widgets.search_bar import SearchBar
from src.ui.widgets.data_table import IngredientDataTable
from src.ui.widgets.dialogs import (
    show_confirmation,
    show_error,
    show_success,
    CustomInputDialog,
)
from src.ui.forms.ingredient_form import IngredientFormDialog


class InventoryTab(ctk.CTkFrame):
    """
    Inventory management tab with full CRUD capabilities.

    Provides interface for:
    - Viewing all ingredients in a searchable table
    - Adding new ingredients
    - Editing existing ingredients
    - Deleting ingredients
    - Adjusting quantities
    - Filtering by category
    """

    def __init__(self, parent):
        """
        Initialize the inventory tab.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.selected_ingredient: Optional[Ingredient] = None

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
            categories=["All Categories"] + INGREDIENT_CATEGORIES,
            placeholder="Search by name or brand...",
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
            text="➕ Add Ingredient",
            command=self._add_ingredient,
            width=150,
        )
        add_button.grid(row=0, column=0, padx=PADDING_MEDIUM)

        # Edit button
        self.edit_button = ctk.CTkButton(
            button_frame,
            text="✏️ Edit",
            command=self._edit_ingredient,
            width=120,
            state="disabled",
        )
        self.edit_button.grid(row=0, column=1, padx=PADDING_MEDIUM)

        # Delete button
        self.delete_button = ctk.CTkButton(
            button_frame,
            text="🗑️ Delete",
            command=self._delete_ingredient,
            width=120,
            state="disabled",
            fg_color="darkred",
            hover_color="red",
        )
        self.delete_button.grid(row=0, column=2, padx=PADDING_MEDIUM)

        # Adjust Quantity button
        self.adjust_button = ctk.CTkButton(
            button_frame,
            text="📊 Adjust Quantity",
            command=self._adjust_quantity,
            width=150,
            state="disabled",
        )
        self.adjust_button.grid(row=0, column=3, padx=PADDING_MEDIUM)

        # Refresh button
        refresh_button = ctk.CTkButton(
            button_frame,
            text="🔄 Refresh",
            command=self.refresh,
            width=120,
        )
        refresh_button.grid(row=0, column=4, padx=PADDING_MEDIUM)

    def _create_data_table(self):
        """Create the data table for displaying ingredients."""
        self.data_table = IngredientDataTable(
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

        # Get filtered ingredients
        try:
            ingredients = inventory_service.get_all_ingredients(
                name_search=search_text if search_text else None,
                category=category_filter,
            )
            self.data_table.set_data(ingredients)
            self._update_status(f"Found {len(ingredients)} ingredient(s)")
        except Exception as e:
            show_error("Search Error", f"Failed to search ingredients: {str(e)}", parent=self)
            self._update_status("Search failed", error=True)

    def _on_row_select(self, ingredient: Optional[Ingredient]):
        """
        Handle row selection.

        Args:
            ingredient: Selected ingredient (None if deselected)
        """
        self.selected_ingredient = ingredient

        # Enable/disable action buttons
        has_selection = ingredient is not None
        self.edit_button.configure(state="normal" if has_selection else "disabled")
        self.delete_button.configure(state="normal" if has_selection else "disabled")
        self.adjust_button.configure(state="normal" if has_selection else "disabled")

        if ingredient:
            self._update_status(f"Selected: {ingredient.name}")
        else:
            self._update_status("Ready")

    def _on_row_double_click(self, ingredient: Ingredient):
        """
        Handle row double-click (edit).

        Args:
            ingredient: Double-clicked ingredient
        """
        self.selected_ingredient = ingredient
        self._edit_ingredient()

    def _add_ingredient(self):
        """Show dialog to add a new ingredient."""
        dialog = IngredientFormDialog(self, title="Add New Ingredient")
        result = dialog.get_result()

        if result:
            try:
                new_ingredient = inventory_service.create_ingredient(**result)
                show_success(
                    "Success",
                    f"Ingredient '{new_ingredient.name}' added successfully",
                    parent=self,
                )
                self.refresh()
                self._update_status(f"Added: {new_ingredient.name}", success=True)
            except Exception as e:
                show_error(
                    "Error",
                    f"Failed to add ingredient: {str(e)}",
                    parent=self,
                )
                self._update_status("Failed to add ingredient", error=True)

    def _edit_ingredient(self):
        """Show dialog to edit the selected ingredient."""
        if not self.selected_ingredient:
            return

        dialog = IngredientFormDialog(
            self,
            ingredient=self.selected_ingredient,
            title=f"Edit Ingredient: {self.selected_ingredient.name}",
        )
        result = dialog.get_result()

        if result:
            try:
                updated_ingredient = inventory_service.update_ingredient(
                    self.selected_ingredient.id,
                    **result,
                )
                show_success(
                    "Success",
                    f"Ingredient '{updated_ingredient.name}' updated successfully",
                    parent=self,
                )
                self.refresh()
                self._update_status(f"Updated: {updated_ingredient.name}", success=True)
            except Exception as e:
                show_error(
                    "Error",
                    f"Failed to update ingredient: {str(e)}",
                    parent=self,
                )
                self._update_status("Failed to update ingredient", error=True)

    def _delete_ingredient(self):
        """Delete the selected ingredient after confirmation."""
        if not self.selected_ingredient:
            return

        # Confirm deletion
        confirmed = show_confirmation(
            "Confirm Deletion",
            f"Are you sure you want to delete '{self.selected_ingredient.name}'?\n\n"
            "This action cannot be undone.",
            parent=self,
        )

        if confirmed:
            try:
                inventory_service.delete_ingredient(self.selected_ingredient.id)
                show_success(
                    "Success",
                    f"Ingredient '{self.selected_ingredient.name}' deleted successfully",
                    parent=self,
                )
                self.selected_ingredient = None
                self.refresh()
                self._update_status("Ingredient deleted", success=True)
            except Exception as e:
                show_error(
                    "Error",
                    f"Failed to delete ingredient: {str(e)}",
                    parent=self,
                )
                self._update_status("Failed to delete ingredient", error=True)

    def _adjust_quantity(self):
        """Show dialog to adjust quantity of selected ingredient."""
        if not self.selected_ingredient:
            return

        current_qty = self.selected_ingredient.quantity
        dialog = CustomInputDialog(
            self,
            title="Adjust Quantity",
            prompt=f"Current quantity: {current_qty} {self.selected_ingredient.purchase_unit}\n"
            f"Enter new quantity:",
            default_value=str(current_qty),
        )
        result = dialog.get_input()

        if result is not None:
            try:
                new_quantity = float(result)
                if new_quantity < 0:
                    show_error(
                        "Validation Error",
                        "Quantity cannot be negative",
                        parent=self,
                    )
                    return

                updated_ingredient = inventory_service.update_quantity(
                    self.selected_ingredient.id,
                    new_quantity,
                )
                show_success(
                    "Success",
                    f"Quantity updated: {current_qty} → {new_quantity} {self.selected_ingredient.purchase_unit}",
                    parent=self,
                )
                self.refresh()
                self._update_status(
                    f"Quantity adjusted for {updated_ingredient.name}",
                    success=True,
                )
            except ValueError:
                show_error(
                    "Validation Error",
                    "Please enter a valid number",
                    parent=self,
                )
            except Exception as e:
                show_error(
                    "Error",
                    f"Failed to update quantity: {str(e)}",
                    parent=self,
                )
                self._update_status("Failed to adjust quantity", error=True)

    def refresh(self):
        """Refresh the ingredient list."""
        try:
            ingredients = inventory_service.get_all_ingredients()
            self.data_table.set_data(ingredients)
            self._update_status(f"Loaded {len(ingredients)} ingredient(s)")
        except Exception as e:
            show_error(
                "Error",
                f"Failed to load ingredients: {str(e)}",
                parent=self,
            )
            self._update_status("Failed to load ingredients", error=True)

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
