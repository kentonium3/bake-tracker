"""
Recipes tab for the Seasonal Baking Tracker.

Provides full CRUD interface for managing recipes with cost calculations
and ingredient management.
"""

import customtkinter as ctk
from typing import Optional

from src.models.recipe import Recipe
from src.services import recipe_service
from src.services.database import session_scope
from src.utils.constants import (
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
from src.services.exceptions import ValidationError
from src.ui.forms.recipe_form import RecipeFormDialog
from src.ui.forms.variant_creation_dialog import VariantCreationDialog


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
        self.recipe_categories = self._load_recipe_categories()

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

    def _load_recipe_categories(self) -> list:
        """Load recipe categories from database.

        Returns:
            List of distinct category names from recipes table.
        """
        try:
            with session_scope() as session:
                categories = (
                    session.query(Recipe.category)
                    .distinct()
                    .filter(Recipe.category.isnot(None))
                    .order_by(Recipe.category)
                    .all()
                )
                return [cat[0] for cat in categories if cat[0]]
        except Exception:
            return []

    def _create_search_bar(self):
        """Create the search bar with category filter."""
        # Note: SearchBar adds "All Categories" internally, so don't add it here
        self.search_bar = SearchBar(
            self,
            search_callback=self._on_search,
            categories=self.recipe_categories,
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
            text="+ Add Recipe",
            command=self._add_recipe,
            width=150,
        )
        add_button.grid(row=0, column=0, padx=PADDING_MEDIUM)

        # Edit button
        self.edit_button = ctk.CTkButton(
            button_frame,
            text="Edit",
            command=self._edit_recipe,
            width=120,
            state="disabled",
        )
        self.edit_button.grid(row=0, column=1, padx=PADDING_MEDIUM)

        # Delete button
        self.delete_button = ctk.CTkButton(
            button_frame,
            text="Delete",
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
            text="View Details",
            command=self._view_details,
            width=150,
            state="disabled",
        )
        self.details_button.grid(row=0, column=3, padx=PADDING_MEDIUM)

        # Create Variant button (Feature 063)
        self.variant_button = ctk.CTkButton(
            button_frame,
            text="Create Variant",
            command=self._create_variant,
            width=130,
            state="disabled",
        )
        self.variant_button.grid(row=0, column=4, padx=PADDING_MEDIUM)

        # Readiness filter dropdown (T031 - Feature 037)
        readiness_label = ctk.CTkLabel(button_frame, text="Readiness:")
        readiness_label.grid(row=0, column=5, padx=(PADDING_LARGE, 5))

        self.readiness_var = ctk.StringVar(value="All")
        self.readiness_dropdown = ctk.CTkComboBox(
            button_frame,
            variable=self.readiness_var,
            values=["All", "Production Ready", "Experimental"],
            width=150,
            state="readonly",
            command=self._on_readiness_filter_changed,
        )
        self.readiness_dropdown.grid(row=0, column=6, padx=PADDING_MEDIUM)

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

    def _on_readiness_filter_changed(self, selection):
        """Handle readiness filter change (T031 - Feature 037)."""
        # Re-apply current search with new readiness filter
        search_text = self.search_bar.get_search_term()
        category = self.search_bar.get_category()
        self._on_search(search_text, category)

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

            # Apply readiness filter (T031 - Feature 037)
            readiness = self.readiness_var.get()
            if readiness == "Production Ready":
                recipes = [r for r in recipes if r.is_production_ready]
            elif readiness == "Experimental":
                recipes = [r for r in recipes if not r.is_production_ready]
            # "All" shows all recipes (no filtering)

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
        self.variant_button.configure(state="normal" if has_selection else "disabled")

        if recipe:
            self._update_status(f"Selected: {recipe.name}")
        else:
            self._update_status("Ready")

    def _on_row_double_click(self, recipe: Recipe):
        """
        Handle row double-click (opens edit dialog).

        Args:
            recipe: Double-clicked recipe
        """
        self.selected_recipe = recipe
        self._edit_recipe()

    def _add_recipe(self):
        """Show dialog to add a new recipe."""
        dialog = RecipeFormDialog(self, title="Add New Recipe")
        result = dialog.get_result()

        if result:
            try:
                # Extract ingredients, pending components, and yield types from result
                ingredients = result.pop("ingredients", [])
                pending_components = result.pop("pending_components", [])
                yield_types = result.pop("yield_types", [])

                # Map prep_time to estimated_time_minutes
                if "prep_time" in result:
                    result["estimated_time_minutes"] = result.pop("prep_time")

                # Create recipe
                new_recipe = recipe_service.create_recipe(
                    result,
                    ingredients,
                )

                # Add pending sub-recipe components
                for comp in pending_components:
                    try:
                        recipe_service.add_recipe_component(
                            new_recipe.id,
                            comp["recipe_id"],
                            quantity=comp["quantity"],
                        )
                    except Exception:
                        # Silently skip component errors (already handled in form validation)
                        pass

                # Save yield types (F044 - WP03 T008)
                yield_types_saved = self._save_yield_types(new_recipe.id, yield_types)

                # Show appropriate message based on yield type save result
                if yield_types_saved:
                    show_success(
                        "Success",
                        f"Recipe '{new_recipe.name}' added successfully",
                        parent=self,
                    )
                    self._update_status(f"Added: {new_recipe.name}", success=True)
                else:
                    show_error(
                        "Partial Success",
                        f"Recipe '{new_recipe.name}' was saved, but yield types could not be saved.\n\n"
                        "Please edit the recipe to add yield types again.",
                        parent=self,
                    )
                    self._update_status(
                        f"Added: {new_recipe.name} (yield types failed)", error=True
                    )

                self.refresh()
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
                # Extract ingredients and yield types from result
                ingredients = result.pop("ingredients", [])
                # Remove pending_components (edits save components directly in form)
                result.pop("pending_components", [])
                yield_types = result.pop("yield_types", [])

                # Map prep_time to estimated_time_minutes
                if "prep_time" in result:
                    result["estimated_time_minutes"] = result.pop("prep_time")

                # Update recipe
                updated_recipe = recipe_service.update_recipe(
                    self.selected_recipe.id,
                    result,
                    ingredients,
                )

                # Save yield types (F044 - WP03 T008)
                yield_types_saved = self._save_yield_types(self.selected_recipe.id, yield_types)

                # Show appropriate message based on yield type save result
                if yield_types_saved:
                    show_success(
                        "Success",
                        f"Recipe '{updated_recipe.name}' updated successfully",
                        parent=self,
                    )
                    self._update_status(f"Updated: {updated_recipe.name}", success=True)
                else:
                    show_error(
                        "Partial Success",
                        f"Recipe '{updated_recipe.name}' was saved, but yield types could not be saved.\n\n"
                        "Please edit the recipe to update yield types again.",
                        parent=self,
                    )
                    self._update_status(
                        f"Updated: {updated_recipe.name} (yield types failed)", error=True
                    )

                self.refresh()
            except Exception as e:
                show_error(
                    "Error",
                    f"Failed to update recipe: {str(e)}",
                    parent=self,
                )
                self._update_status("Failed to update recipe", error=True)

    def _delete_recipe(self):
        """Delete or archive the selected recipe after confirmation."""
        if not self.selected_recipe:
            return

        # Confirm deletion
        confirmed = show_confirmation(
            "Confirm Deletion",
            f"Are you sure you want to delete '{self.selected_recipe.name}'?\n\n"
            "If the recipe has historical usage, it will be archived. Otherwise, it will be permanently deleted.",
            parent=self,
        )

        if confirmed:
            try:
                recipe_service.delete_recipe(self.selected_recipe.id)
                show_success(
                    "Success",
                    f"Recipe '{self.selected_recipe.name}' has been successfully processed.",
                    parent=self,
                )
                self.selected_recipe = None
                self.refresh()
                self._update_status("Recipe processed successfully", success=True)
            except ValidationError as e:
                show_error(
                    "Cannot Delete Recipe",
                    str(e),
                    parent=self,
                )
                self._update_status("Failed to delete recipe", error=True)
            except Exception as e:
                show_error(
                    "Error",
                    f"An unexpected error occurred: {str(e)}",
                    parent=self,
                )
                self._update_status("Failed to delete recipe", error=True)

    def _create_variant(self):
        """
        Show dialog to create a variant of the selected recipe (Feature 063).

        Opens VariantCreationDialog with base recipe's FinishedUnits pre-loaded.
        """
        if not self.selected_recipe:
            return

        # Prevent creating variant of a variant
        if self.selected_recipe.base_recipe_id is not None:
            show_error(
                "Cannot Create Variant",
                "Cannot create a variant of a variant.\n"
                "Please select the base recipe to create variants.",
                parent=self,
            )
            return

        try:
            # Get base recipe's FinishedUnits
            base_fus = recipe_service.get_finished_units(self.selected_recipe.id)

            # Open variant creation dialog
            dialog = VariantCreationDialog(
                parent=self,
                base_recipe_id=self.selected_recipe.id,
                base_recipe_name=self.selected_recipe.name,
                base_finished_units=base_fus,
                on_save_callback=self._on_variant_created,
            )

        except Exception as e:
            show_error(
                "Error",
                f"Failed to open variant dialog: {str(e)}",
                parent=self,
            )

    def _on_variant_created(self, result: dict):
        """
        Callback when a variant is successfully created.

        Args:
            result: Dict with created variant info (id, name, variant_name, base_recipe_id)
        """
        self._update_status(f"Created variant: {result['name']}", success=True)
        self.refresh()

    def _save_yield_types(self, recipe_id: int, yield_types: list) -> bool:
        """
        Persist yield type changes for a recipe (F044 - WP03 T008).

        Handles:
        - Creating new yield types (id=None)
        - Updating existing yield types (id set)
        - Deleting removed yield types

        Returns:
            True if yield types were saved successfully, False otherwise.
        """
        from src.services import finished_unit_service
        import logging

        try:
            # Get existing yield types for this recipe
            existing_units = finished_unit_service.get_units_by_recipe(recipe_id)
            existing_ids = {unit.id for unit in existing_units}

            # Track which IDs we're keeping
            keeping_ids = set()

            for data in yield_types:
                if data["id"] is None:
                    # Create new
                    finished_unit_service.create_finished_unit(
                        display_name=data["display_name"],
                        recipe_id=recipe_id,
                        item_unit=data.get("item_unit"),
                        items_per_batch=data["items_per_batch"],
                        yield_type=data.get("yield_type", "SERVING"),  # Feature 083
                    )
                else:
                    # Update existing
                    keeping_ids.add(data["id"])
                    finished_unit_service.update_finished_unit(
                        data["id"],
                        display_name=data["display_name"],
                        item_unit=data.get("item_unit"),
                        items_per_batch=data["items_per_batch"],
                        yield_type=data.get("yield_type", "SERVING"),  # Feature 083
                    )

            # Delete removed yield types
            for unit in existing_units:
                if unit.id not in keeping_ids:
                    finished_unit_service.delete_finished_unit(unit.id)

            return True

        except Exception as e:
            # Log the error (F044 fix: don't silently swallow, return False for caller to handle)
            logging.exception(f"Error saving yield types for recipe {recipe_id}: {e}")
            return False

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

            # Show FinishedUnit yield types (Feature 056/063 - variant yield inheritance)
            # Use primitives to get display_name from recipe's FUs and yields from base
            recipe_fus = recipe_service.get_finished_units(recipe.id)
            base_yields = recipe_service.get_base_yield_structure(recipe.id)

            if recipe_fus and base_yields:
                details.append("Yield Types:")
                # Combine: variant's display_name with base's yield values
                for fu, y in zip(recipe_fus, base_yields):
                    items = y.get("items_per_batch")
                    unit = y.get("item_unit", "")
                    # Feature 083: Include yield_type in display
                    yield_type = fu.get("yield_type", "SERVING")
                    if items:
                        details.append(f"  - {fu['display_name']}: {items} {unit}/batch ({yield_type})")
                    else:
                        details.append(f"  - {fu['display_name']}: Yield not specified ({yield_type})")
            else:
                details.append("Yield Types: None defined (edit recipe to add)")

            if recipe.estimated_time_minutes:
                details.append(f"Prep Time: {recipe.estimated_time_minutes} minutes")

            details.append("")
            details.append("Cost Breakdown:")
            details.append(f"  Total Cost: ${recipe_data['total_cost']:.2f}")
            if recipe_fus and base_yields:
                # Show cost per unit for each yield type (use base yields for calculation)
                for fu, y in zip(recipe_fus, base_yields):
                    items = y.get("items_per_batch")
                    unit = y.get("item_unit", "")
                    if items and items > 0:
                        cost_per = recipe_data["total_cost"] / items
                        details.append(
                            f"  Cost per {unit} ({fu['display_name']}): ${cost_per:.4f}"
                        )

            details.append("")
            details.append("Ingredients:")

            for ing in recipe_data["ingredients"]:
                ing_name = ing["ingredient"].display_name
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
        """Refresh the recipe list and category filter."""
        try:
            # Reload categories in case new categories were added
            self.recipe_categories = self._load_recipe_categories()
            self.search_bar.update_categories(self.recipe_categories)

            recipes = recipe_service.get_all_recipes()

            # Apply readiness filter (T031 - Feature 037)
            readiness = self.readiness_var.get()
            if readiness == "Production Ready":
                recipes = [r for r in recipes if r.is_production_ready]
            elif readiness == "Experimental":
                recipes = [r for r in recipes if not r.is_production_ready]
            # "All" shows all recipes (no filtering)

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
