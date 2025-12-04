"""
Recipes tab for the Seasonal Baking Tracker.

Provides full CRUD interface for managing recipes with cost calculations
and ingredient management.
"""

import customtkinter as ctk
from typing import Optional

from src.models.recipe import Recipe
from src.services import recipe_service
from src.utils.constants import (
    RECIPE_CATEGORIES,
    PADDING_MEDIUM,
    PADDING_LARGE,
    COLOR_SUCCESS,
    COLOR_ERROR,
)
from src.ui.widgets.search_bar import SearchBar
from src.ui.widgets.data_table import RecipeDataTable
from src.ui.widgets.dialogs import (
    show_confirmation,
    show_error,
    show_success,
    show_info,
)
from src.ui.forms.recipe_form import RecipeFormDialog


class RecipesTab(ctk.CTkFrame):
    """
    Recipes management tab with full CRUD capabilities.

    Provides interface for:
    - Viewing all recipes in a searchable table
    - Adding new recipes with ingredients
    - Editing existing recipes
    - Deleting recipes
    - Viewing recipe details and costs
    - Filtering by category
    """

    def __init__(self, parent):
        """
        Initialize the recipes tab.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.selected_recipe: Optional[Recipe] = None

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
            placeholder="Search by recipe name...",
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
            text="➕ Add Recipe",
            command=self._add_recipe,
            width=150,
        )
        add_button.grid(row=0, column=0, padx=PADDING_MEDIUM)

        # Edit button
        self.edit_button = ctk.CTkButton(
            button_frame,
            text="✏️ Edit",
            command=self._edit_recipe,
            width=120,
            state="disabled",
        )
        self.edit_button.grid(row=0, column=1, padx=PADDING_MEDIUM)

        # Delete button
        self.delete_button = ctk.CTkButton(
            button_frame,
            text="🗑️ Delete",
            command=self._delete_recipe,
            width=120,
            state="disabled",
            fg_color="darkred",
            hover_color="red",
        )
        self.delete_button.grid(row=0, column=2, padx=PADDING_MEDIUM)

        # View Details button
        self.details_button = ctk.CTkButton(
            button_frame,
            text="📋 View Details",
            command=self._view_details,
            width=150,
            state="disabled",
        )
        self.details_button.grid(row=0, column=3, padx=PADDING_MEDIUM)

        # Refresh button
        refresh_button = ctk.CTkButton(
            button_frame,
            text="🔄 Refresh",
            command=self.refresh,
            width=120,
        )
        refresh_button.grid(row=0, column=4, padx=PADDING_MEDIUM)

    def _create_data_table(self):
        """Create the data table for displaying recipes."""
        self.data_table = RecipeDataTable(
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

        # Get filtered recipes
        try:
            recipes = recipe_service.get_all_recipes(
                name_search=search_text if search_text else None,
                category=category_filter,
            )
            self.data_table.set_data(recipes)
            self._update_status(f"Found {len(recipes)} recipe(s)")
        except Exception as e:
            show_error("Search Error", f"Failed to search recipes: {str(e)}", parent=self)
            self._update_status("Search failed", error=True)

    def _on_row_select(self, recipe: Optional[Recipe]):
        """
        Handle row selection.

        Args:
            recipe: Selected recipe (None if deselected)
        """
        self.selected_recipe = recipe

        # Enable/disable action buttons
        has_selection = recipe is not None
        self.edit_button.configure(state="normal" if has_selection else "disabled")
        self.delete_button.configure(state="normal" if has_selection else "disabled")
        self.details_button.configure(state="normal" if has_selection else "disabled")

        if recipe:
            self._update_status(f"Selected: {recipe.name}")
        else:
            self._update_status("Ready")

    def _on_row_double_click(self, recipe: Recipe):
        """
        Handle row double-click (view details).

        Args:
            recipe: Double-clicked recipe
        """
        self.selected_recipe = recipe
        self._view_details()

    def _add_recipe(self):
        """Show dialog to add a new recipe."""
        dialog = RecipeFormDialog(self, title="Add New Recipe")
        result = dialog.get_result()

        if result:
            try:
                # Extract ingredients from result
                ingredients = result.pop("ingredients", [])

                # Map prep_time to estimated_time_minutes
                if "prep_time" in result:
                    result["estimated_time_minutes"] = result.pop("prep_time")

                # Create recipe
                new_recipe = recipe_service.create_recipe(
                    result,
                    ingredients,
                )

                show_success(
                    "Success",
                    f"Recipe '{new_recipe.name}' added successfully",
                    parent=self,
                )
                self.refresh()
                self._update_status(f"Added: {new_recipe.name}", success=True)
            except Exception as e:
                show_error(
                    "Error",
                    f"Failed to add recipe: {str(e)}",
                    parent=self,
                )
                self._update_status("Failed to add recipe", error=True)

    def _edit_recipe(self):
        """Show dialog to edit the selected recipe."""
        if not self.selected_recipe:
            return

        try:
            # Reload recipe with ingredients to avoid lazy loading issues
            recipe = recipe_service.get_recipe(self.selected_recipe.id)

            dialog = RecipeFormDialog(
                self,
                recipe=recipe,
                title=f"Edit Recipe: {recipe.name}",
            )
            result = dialog.get_result()
        except Exception as e:
            show_error(
                "Error",
                f"Failed to load recipe for editing: {str(e)}",
                parent=self,
            )
            return

        if result:
            try:
                # Extract ingredients from result
                ingredients = result.pop("ingredients", [])

                # Map prep_time to estimated_time_minutes
                if "prep_time" in result:
                    result["estimated_time_minutes"] = result.pop("prep_time")

                # Update recipe
                updated_recipe = recipe_service.update_recipe(
                    self.selected_recipe.id,
                    result,
                    ingredients,
                )

                show_success(
                    "Success",
                    f"Recipe '{updated_recipe.name}' updated successfully",
                    parent=self,
                )
                self.refresh()
                self._update_status(f"Updated: {updated_recipe.name}", success=True)
            except Exception as e:
                show_error(
                    "Error",
                    f"Failed to update recipe: {str(e)}",
                    parent=self,
                )
                self._update_status("Failed to update recipe", error=True)

    def _delete_recipe(self):
        """Delete the selected recipe after confirmation."""
        if not self.selected_recipe:
            return

        # Confirm deletion
        confirmed = show_confirmation(
            "Confirm Deletion",
            f"Are you sure you want to delete '{self.selected_recipe.name}'?\n\n"
            "This will remove the recipe and all its ingredient associations.\n"
            "This action cannot be undone.",
            parent=self,
        )

        if confirmed:
            try:
                recipe_service.delete_recipe(self.selected_recipe.id)
                show_success(
                    "Success",
                    f"Recipe '{self.selected_recipe.name}' deleted successfully",
                    parent=self,
                )
                self.selected_recipe = None
                self.refresh()
                self._update_status("Recipe deleted", success=True)
            except Exception as e:
                show_error(
                    "Error",
                    f"Failed to delete recipe: {str(e)}",
                    parent=self,
                )
                self._update_status("Failed to delete recipe", error=True)

    def _view_details(self):
        """Show detailed information about the selected recipe."""
        if not self.selected_recipe:
            return

        try:
            # Get recipe with calculated costs
            recipe_data = recipe_service.get_recipe_with_costs(self.selected_recipe.id)
            recipe = recipe_data["recipe"]

            # Build details message
            details = []
            details.append(f"Recipe: {recipe.name}")
            details.append(f"Category: {recipe.category}")
            details.append(f"Yields: {recipe.yield_quantity} {recipe.yield_unit}")

            if recipe.estimated_time_minutes:
                details.append(f"Prep Time: {recipe.estimated_time_minutes} minutes")

            details.append("")
            details.append("Cost Breakdown:")
            details.append(f"  Total Cost: ${recipe_data['total_cost']:.2f}")
            details.append(f"  Cost per {recipe.yield_unit}: ${recipe_data['cost_per_unit']:.4f}")

            details.append("")
            details.append("Ingredients:")

            for ing in recipe_data["ingredients"]:
                ing_name = ing["ingredient"].name
                ing_qty = ing["quantity"]
                ing_unit = ing["unit"]
                ing_cost = ing["cost"]
                packages_needed = ing["packages_needed"]

                # Get package information from ingredient
                ingredient = ing["ingredient"]

                # Format package display
                if packages_needed > 0:
                    if ingredient.package_type:
                        # Use package type if available
                        package_label = self._pluralize_package(
                            ingredient.package_type, packages_needed
                        )
                        package_info = f" → {packages_needed:.2f} {package_label}"
                    else:
                        # Use generic "packages"
                        package_label = "package" if packages_needed == 1 else "packages"
                        package_info = f" → {packages_needed:.2f} {package_label}"
                else:
                    package_info = ""

                details.append(
                    f"  • {ing_qty} {ing_unit} {ing_name}{package_info} (${ing_cost:.2f})"
                )

            if recipe.notes:
                details.append("")
                details.append("Notes:")
                details.append(f"  {recipe.notes}")

            show_info(
                f"Recipe Details: {recipe.name}",
                "\n".join(details),
                parent=self,
            )

        except Exception as e:
            show_error(
                "Error",
                f"Failed to load recipe details: {str(e)}",
                parent=self,
            )

    def refresh(self):
        """Refresh the recipe list."""
        try:
            recipes = recipe_service.get_all_recipes()
            self.data_table.set_data(recipes)
            self._update_status(f"Loaded {len(recipes)} recipe(s)")
        except Exception as e:
            show_error(
                "Error",
                f"Failed to load recipes: {str(e)}",
                parent=self,
            )
            self._update_status("Failed to load recipes", error=True)

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

    def _pluralize_package(self, word: str, count: float) -> str:
        """
        Simple pluralization helper for package types.

        Args:
            word: Singular word
            count: Count to determine singular/plural

        Returns:
            Pluralized word
        """
        if count == 1:
            return word

        # Handle common irregular plurals
        irregular = {
            "box": "boxes",
            "can": "cans",
            "jar": "jars",
            "bag": "bags",
            "bottle": "bottles",
            "bar": "bars",
            "package": "packages",
        }

        word_lower = word.lower()
        if word_lower in irregular:
            return irregular[word_lower]

        # Default: add 's'
        return f"{word}s"
