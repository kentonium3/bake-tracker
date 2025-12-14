"""
Recipe form dialog for adding and editing recipes.

Provides a comprehensive form for creating and updating recipe records
with ingredient management and cost calculations.
"""

import customtkinter as ctk
from typing import Optional, Dict, Any, List
from decimal import Decimal

from src.models.recipe import Recipe, RecipeComponent
from src.models.ingredient import Ingredient
from src.services import ingredient_crud_service, recipe_service
from src.utils.constants import (
    RECIPE_CATEGORIES,
    ALL_UNITS,
    WEIGHT_UNITS,
    VOLUME_UNITS,
    COUNT_UNITS,
    MAX_NAME_LENGTH,
    MAX_NOTES_LENGTH,
    PADDING_MEDIUM,
    PADDING_LARGE,
)
from src.ui.widgets.dialogs import show_error, show_confirmation


class RecipeIngredientRow(ctk.CTkFrame):
    """Row widget for a single recipe ingredient."""

    def __init__(
        self,
        parent,
        ingredients: List[Ingredient],
        remove_callback,
        ingredient_id: Optional[int] = None,
        quantity: float = 1.0,
        unit: Optional[str] = None,
    ):
        """
        Initialize ingredient row.

        Args:
            parent: Parent widget
            ingredients: List of available ingredients
            remove_callback: Callback to remove this row
            ingredient_id: Selected ingredient ID (None for new row)
            quantity: Ingredient quantity
            unit: Unit of measurement (None to use ingredient's default recipe_unit)
        """
        super().__init__(parent)

        self.remove_callback = remove_callback
        self.ingredients = ingredients

        # Configure grid (Quantity / Unit / Ingredient - traditional recipe format)
        self.grid_columnconfigure(0, weight=1)  # Quantity
        self.grid_columnconfigure(1, weight=2)  # Unit dropdown
        self.grid_columnconfigure(2, weight=3)  # Ingredient dropdown
        self.grid_columnconfigure(3, weight=0)  # Remove button

        # Quantity entry
        self.quantity_entry = ctk.CTkEntry(self, width=100, placeholder_text="Quantity")
        self.quantity_entry.insert(0, str(quantity))
        self.quantity_entry.grid(row=0, column=0, padx=(0, PADDING_MEDIUM), pady=5)

        # Unit dropdown - shows all recipe units
        available_units = WEIGHT_UNITS + VOLUME_UNITS + COUNT_UNITS
        self.unit_combo = ctk.CTkComboBox(
            self,
            values=available_units,
            state="readonly",
            width=100,
        )
        # Set unit: use provided unit or default to "cup"
        default_unit = unit if unit else "cup"
        self.unit_combo.set(default_unit)
        self.unit_combo.grid(row=0, column=1, padx=PADDING_MEDIUM, pady=5, sticky="ew")

        # Ingredient dropdown (no unit suffix)
        ingredient_names = [i.display_name for i in ingredients]
        self.ingredient_combo = ctk.CTkComboBox(
            self,
            values=ingredient_names if ingredient_names else ["No ingredients available"],
            state="readonly" if ingredient_names else "disabled",
        )
        if ingredient_names:
            # Set selected ingredient or default to first
            if ingredient_id:
                for idx, ing in enumerate(ingredients):
                    if ing.id == ingredient_id:
                        self.ingredient_combo.set(ingredient_names[idx])
                        break
            else:
                self.ingredient_combo.set(ingredient_names[0])

        self.ingredient_combo.grid(row=0, column=2, padx=PADDING_MEDIUM, pady=5, sticky="ew")

        # Remove button
        remove_button = ctk.CTkButton(
            self,
            text="✕",
            width=30,
            command=lambda: remove_callback(self),
            fg_color="darkred",
            hover_color="red",
        )
        remove_button.grid(row=0, column=3, padx=(PADDING_MEDIUM, 0), pady=5)

    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Get ingredient data from this row.

        Returns:
            Dictionary with ingredient_id, quantity, and unit, or None if invalid
        """
        if not self.ingredients:
            return None

        # Get selected ingredient by name
        selected_name = self.ingredient_combo.get()
        ingredient = None
        for ing in self.ingredients:
            if ing.name == selected_name:
                ingredient = ing
                break

        if not ingredient:
            return None

        # Get selected unit from dropdown
        unit = self.unit_combo.get()
        if not unit:
            return None

        # Get quantity
        try:
            quantity = float(self.quantity_entry.get())
            if quantity <= 0:
                return None
        except ValueError:
            return None

        # Validate density requirement for cross-type unit conversions
        from src.services.unit_converter import get_unit_type

        recipe_unit_type = get_unit_type(unit)
        purchase_unit_type = get_unit_type(ingredient.purchase_unit)

        # Check if cross-type conversion is needed (volume↔weight)
        if recipe_unit_type != purchase_unit_type:
            if (recipe_unit_type == "volume" and purchase_unit_type == "weight") or (
                recipe_unit_type == "weight" and purchase_unit_type == "volume"
            ):
                # Density is required for volume↔weight conversion
                if not ingredient.has_density_data():
                    from src.ui.widgets.dialogs import show_error

                    show_error(
                        "Density Required",
                        f"'{ingredient.display_name}' requires density data for {recipe_unit_type}↔{purchase_unit_type} conversion.\n\n"
                        f"Please edit the ingredient and add density (g/cup) before using it with {unit} in recipes.",
                        parent=self.winfo_toplevel(),
                    )
                    return None

        return {
            "ingredient_id": ingredient.id,
            "quantity": quantity,
            "unit": unit,
        }


class RecipeFormDialog(ctk.CTkToplevel):
    """
    Dialog for creating or editing a recipe.

    Provides a comprehensive form with validation for all recipe fields
    and ingredient management.
    """

    def __init__(
        self,
        parent,
        recipe: Optional[Recipe] = None,
        title: str = "Add Recipe",
    ):
        """
        Initialize the recipe form dialog.

        Args:
            parent: Parent window
            recipe: Existing recipe to edit (None for new)
            title: Dialog title
        """
        super().__init__(parent)

        self.recipe = recipe
        self.result = None
        self.ingredient_rows: List[RecipeIngredientRow] = []

        # Sub-recipe tracking
        self.current_components: List[RecipeComponent] = []  # For existing recipe
        self.pending_components: List[Dict] = []  # For new recipe

        # Load available ingredients
        try:
            self.available_ingredients = ingredient_crud_service.get_all_ingredients()
        except Exception:
            self.available_ingredients = []

        # Configure window
        self.title(title)
        self.geometry("700x750")
        self.resizable(False, False)

        # Center on parent
        self.transient(parent)

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create main scrollable frame
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=PADDING_LARGE, pady=PADDING_LARGE)
        main_frame.grid_columnconfigure(1, weight=1)

        # Create form fields
        self._create_form_fields(main_frame)

        # Create buttons
        self._create_buttons()

        # Populate if editing
        if self.recipe:
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

        # Basic Information section
        basic_label = ctk.CTkLabel(
            parent,
            text="Basic Information",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        basic_label.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=PADDING_MEDIUM,
            pady=(0, PADDING_MEDIUM),
        )
        row += 1

        # Name field (required)
        name_label = ctk.CTkLabel(parent, text="Recipe Name*:", anchor="w")
        name_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        self.name_entry = ctk.CTkEntry(
            parent, width=450, placeholder_text="e.g., Chocolate Chip Cookies"
        )
        self.name_entry.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Category field (required)
        category_label = ctk.CTkLabel(parent, text="Category*:", anchor="w")
        category_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        self.category_combo = ctk.CTkComboBox(
            parent,
            width=450,
            values=RECIPE_CATEGORIES,
            state="readonly",
        )
        self.category_combo.set(RECIPE_CATEGORIES[0])
        self.category_combo.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Yield section
        yield_label = ctk.CTkLabel(
            parent,
            text="Yield Information",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        yield_label.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=PADDING_MEDIUM,
            pady=(PADDING_LARGE, PADDING_MEDIUM),
        )
        row += 1

        # Yield quantity (required)
        yield_qty_label = ctk.CTkLabel(parent, text="Yield Quantity*:", anchor="w")
        yield_qty_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        self.yield_quantity_entry = ctk.CTkEntry(
            parent,
            width=450,
            placeholder_text="e.g., 24 (number of items produced)",
        )
        self.yield_quantity_entry.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Yield unit (required)
        yield_unit_label = ctk.CTkLabel(parent, text="Yield Unit*:", anchor="w")
        yield_unit_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        yield_units = (
            ["dozen", "each", "piece", "batch"] + COUNT_UNITS + WEIGHT_UNITS + VOLUME_UNITS
        )
        self.yield_unit_combo = ctk.CTkComboBox(
            parent,
            width=450,
            values=yield_units,
            state="readonly",
        )
        self.yield_unit_combo.set("each")
        self.yield_unit_combo.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Prep time (optional)
        prep_time_label = ctk.CTkLabel(parent, text="Prep Time (min):", anchor="w")
        prep_time_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        self.prep_time_entry = ctk.CTkEntry(
            parent,
            width=450,
            placeholder_text="e.g., 30 (minutes)",
        )
        self.prep_time_entry.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Ingredients section
        ingredients_label = ctk.CTkLabel(
            parent,
            text="Recipe Ingredients",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        ingredients_label.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=PADDING_MEDIUM,
            pady=(PADDING_LARGE, PADDING_MEDIUM),
        )
        row += 1

        # Ingredients container
        self.ingredients_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.ingredients_frame.grid(
            row=row, column=0, columnspan=2, sticky="ew", padx=PADDING_MEDIUM, pady=5
        )
        self.ingredients_frame.grid_columnconfigure(0, weight=1)
        row += 1

        # Add ingredient button
        add_ingredient_button = ctk.CTkButton(
            parent,
            text="➕ Add Ingredient",
            command=self._add_ingredient_row,
            width=150,
        )
        add_ingredient_button.grid(row=row, column=0, columnspan=2, padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Sub-Recipes Section (T034)
        subrecipes_label = ctk.CTkLabel(
            parent,
            text="Sub-Recipes",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        subrecipes_label.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=PADDING_MEDIUM,
            pady=(PADDING_LARGE, PADDING_MEDIUM),
        )
        row += 1

        # Sub-recipe selection frame (T035, T036, T037)
        subrecipe_select_frame = ctk.CTkFrame(parent, fg_color="transparent")
        subrecipe_select_frame.grid(
            row=row, column=0, columnspan=2, sticky="ew", padx=PADDING_MEDIUM, pady=5
        )
        row += 1

        # Recipe dropdown (T035)
        self.subrecipe_dropdown = ctk.CTkComboBox(
            subrecipe_select_frame,
            values=self._get_available_recipes(),
            width=300,
            state="readonly",
        )
        self.subrecipe_dropdown.pack(side="left", padx=(0, PADDING_MEDIUM))

        # Quantity entry (T036)
        self.subrecipe_qty_entry = ctk.CTkEntry(
            subrecipe_select_frame,
            width=60,
            placeholder_text="1.0",
        )
        self.subrecipe_qty_entry.insert(0, "1.0")
        self.subrecipe_qty_entry.pack(side="left", padx=(0, 5))

        # Batches label
        batches_label = ctk.CTkLabel(subrecipe_select_frame, text="batches")
        batches_label.pack(side="left", padx=(0, PADDING_MEDIUM))

        # Add button (T037)
        add_subrecipe_btn = ctk.CTkButton(
            subrecipe_select_frame,
            text="Add",
            width=60,
            command=self._on_add_subrecipe,
        )
        add_subrecipe_btn.pack(side="left")

        # Sub-recipe list frame (T038)
        self.subrecipes_list_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.subrecipes_list_frame.grid(
            row=row, column=0, columnspan=2, sticky="ew", padx=PADDING_MEDIUM, pady=5
        )
        self.subrecipes_list_frame.grid_columnconfigure(0, weight=1)
        row += 1

        # Cost summary section (T040)
        cost_label = ctk.CTkLabel(
            parent,
            text="Cost Summary",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        cost_label.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=PADDING_MEDIUM,
            pady=(PADDING_LARGE, PADDING_MEDIUM),
        )
        row += 1

        # Cost summary frame
        self.cost_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.cost_frame.grid(
            row=row, column=0, columnspan=2, sticky="ew", padx=PADDING_MEDIUM, pady=5
        )
        row += 1

        # Cost labels
        self.direct_cost_label = ctk.CTkLabel(
            self.cost_frame, text="Direct ingredients: $0.00", anchor="w"
        )
        self.direct_cost_label.pack(fill="x", padx=PADDING_MEDIUM)

        self.component_cost_label = ctk.CTkLabel(
            self.cost_frame, text="Sub-recipes: $0.00", anchor="w"
        )
        self.component_cost_label.pack(fill="x", padx=PADDING_MEDIUM)

        self.total_cost_label = ctk.CTkLabel(
            self.cost_frame,
            text="Total: $0.00",
            font=ctk.CTkFont(weight="bold"),
            anchor="w",
        )
        self.total_cost_label.pack(fill="x", padx=PADDING_MEDIUM, pady=(5, 0))

        self.per_unit_cost_label = ctk.CTkLabel(
            self.cost_frame, text="Per unit: $0.00", anchor="w"
        )
        self.per_unit_cost_label.pack(fill="x", padx=PADDING_MEDIUM)

        # Notes (optional)
        notes_label = ctk.CTkLabel(parent, text="Notes:", anchor="w")
        notes_label.grid(row=row, column=0, sticky="nw", padx=PADDING_MEDIUM, pady=5)

        self.notes_text = ctk.CTkTextbox(parent, width=450, height=80)
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

    # Sub-recipe helper methods (T035-T042)

    def _get_available_recipes(self) -> List[str]:
        """Get recipes that can be added as components (T035)."""
        try:
            all_recipes = recipe_service.get_all_recipes()
        except Exception:
            return []

        # Filter out current recipe and existing components
        current_id = self.recipe.id if self.recipe else None
        existing_ids = set()

        # Get IDs of existing components
        for comp in self.current_components:
            existing_ids.add(comp.component_recipe_id)
        for comp in self.pending_components:
            existing_ids.add(comp["recipe_id"])

        available = []
        for recipe in all_recipes:
            if recipe.id == current_id:
                continue
            if recipe.id in existing_ids:
                continue
            available.append(recipe.name)

        return sorted(available)

    def _on_add_subrecipe(self):
        """Handle adding a sub-recipe (T037)."""
        recipe_name = self.subrecipe_dropdown.get()
        if not recipe_name:
            show_error("Selection Required", "Please select a recipe to add.", parent=self)
            return

        # Validate quantity
        try:
            quantity = float(self.subrecipe_qty_entry.get())
        except ValueError:
            show_error("Invalid Quantity", "Quantity must be a valid number.", parent=self)
            return

        if quantity <= 0:
            show_error("Invalid Quantity", "Quantity must be greater than 0.", parent=self)
            return

        # Find recipe by name
        try:
            component_recipe = recipe_service.get_recipe_by_name(recipe_name)
        except Exception:
            component_recipe = None

        if not component_recipe:
            show_error("Recipe Not Found", f"Recipe '{recipe_name}' not found.", parent=self)
            return

        # If editing existing recipe, add via service
        if self.recipe and self.recipe.id:
            try:
                recipe_service.add_recipe_component(
                    self.recipe.id,
                    component_recipe.id,
                    quantity=quantity,
                )
                # Reload components
                self.current_components = recipe_service.get_recipe_components(self.recipe.id)
            except Exception as e:
                error_msg = str(e)
                # User-friendly messages (T042)
                if "circular reference" in error_msg.lower():
                    show_error(
                        "Cannot Add Recipe",
                        f"Cannot add '{recipe_name}'.\n\n"
                        "This would create a circular reference "
                        "(recipes cannot contain each other).",
                        parent=self,
                    )
                elif "depth" in error_msg.lower():
                    show_error(
                        "Cannot Add Recipe",
                        f"Cannot add '{recipe_name}'.\n\n"
                        "This would exceed the maximum nesting depth of 3 levels.",
                        parent=self,
                    )
                elif "already" in error_msg.lower():
                    show_error(
                        "Already Added",
                        f"'{recipe_name}' is already a component of this recipe.",
                        parent=self,
                    )
                else:
                    show_error("Error", error_msg, parent=self)
                return
        else:
            # For new recipe, add to pending list
            self.pending_components.append(
                {
                    "recipe_id": component_recipe.id,
                    "recipe_name": recipe_name,
                    "quantity": quantity,
                }
            )

        # Refresh display
        self._refresh_subrecipes_display()
        self._update_cost_summary()

        # Reset inputs
        self.subrecipe_dropdown.set("")
        self.subrecipe_qty_entry.delete(0, "end")
        self.subrecipe_qty_entry.insert(0, "1.0")

    def _refresh_subrecipes_display(self):
        """Refresh the sub-recipes list display (T038)."""
        # Clear existing rows
        for widget in self.subrecipes_list_frame.winfo_children():
            widget.destroy()

        # Combine current and pending components
        components = []
        for comp in self.current_components:
            components.append(
                {
                    "type": "saved",
                    "recipe_id": comp.component_recipe_id,
                    "recipe_name": comp.component_recipe.name,
                    "quantity": comp.quantity,
                }
            )
        for comp in self.pending_components:
            components.append(
                {
                    "type": "pending",
                    "recipe_id": comp["recipe_id"],
                    "recipe_name": comp["recipe_name"],
                    "quantity": comp["quantity"],
                }
            )

        # Add rows for each component
        for idx, comp in enumerate(components):
            self._add_subrecipe_row(idx, comp)

        # Update dropdown options
        self.subrecipe_dropdown.configure(values=self._get_available_recipes())

    def _add_subrecipe_row(self, idx: int, component: Dict):
        """Add a row for a sub-recipe component (T038, T039)."""
        row_frame = ctk.CTkFrame(self.subrecipes_list_frame, fg_color="transparent")
        row_frame.grid(row=idx, column=0, sticky="ew", pady=2)
        row_frame.grid_columnconfigure(0, weight=1)

        # Calculate cost if saved
        cost = 0.0
        if component["type"] == "saved" and self.recipe:
            try:
                cost_info = recipe_service.calculate_total_cost_with_components(
                    component["recipe_id"]
                )
                cost = cost_info.get("total_cost", 0) * component["quantity"]
            except Exception:
                pass

        # Name and quantity label
        name_text = f"• {component['recipe_name']} ({component['quantity']}x)"
        name_label = ctk.CTkLabel(row_frame, text=name_text, anchor="w")
        name_label.grid(row=0, column=0, sticky="w", padx=5)

        # Cost label
        cost_label = ctk.CTkLabel(row_frame, text=f"${cost:.2f}", width=70, anchor="e")
        cost_label.grid(row=0, column=1, padx=5)

        # Remove button (T039)
        comp_recipe_id = component["recipe_id"]
        remove_btn = ctk.CTkButton(
            row_frame,
            text="Remove",
            width=60,
            fg_color="darkred",
            hover_color="red",
            command=lambda rid=comp_recipe_id: self._on_remove_component(rid),
        )
        remove_btn.grid(row=0, column=2, padx=5)

    def _on_remove_component(self, component_recipe_id: int):
        """Handle removing a sub-recipe (T039)."""
        if self.recipe and self.recipe.id:
            try:
                recipe_service.remove_recipe_component(self.recipe.id, component_recipe_id)
                # Reload components
                self.current_components = recipe_service.get_recipe_components(self.recipe.id)
            except Exception as e:
                show_error("Error", str(e), parent=self)
                return
        else:
            # Remove from pending
            self.pending_components = [
                c for c in self.pending_components if c["recipe_id"] != component_recipe_id
            ]

        # Refresh
        self._refresh_subrecipes_display()
        self._update_cost_summary()

    def _update_cost_summary(self):
        """Update the cost summary display (T040)."""
        if not self.recipe or not self.recipe.id:
            # Can't calculate costs for unsaved recipe
            self.direct_cost_label.configure(text="Direct ingredients: --")
            self.component_cost_label.configure(text="Sub-recipes: --")
            self.total_cost_label.configure(text="Total: --")
            self.per_unit_cost_label.configure(text="Per unit: --")
            return

        try:
            cost_info = recipe_service.calculate_total_cost_with_components(self.recipe.id)

            direct_cost = cost_info.get("direct_ingredient_cost", 0)
            component_cost = cost_info.get("total_component_cost", 0)
            total_cost = cost_info.get("total_cost", 0)
            per_unit = cost_info.get("cost_per_unit", 0)

            self.direct_cost_label.configure(text=f"Direct ingredients: ${direct_cost:.2f}")
            self.component_cost_label.configure(text=f"Sub-recipes: ${component_cost:.2f}")
            self.total_cost_label.configure(text=f"Total: ${total_cost:.2f}")
            self.per_unit_cost_label.configure(text=f"Per unit: ${per_unit:.2f}")
        except Exception:
            # Silently handle errors
            self.direct_cost_label.configure(text="Direct ingredients: $0.00")
            self.component_cost_label.configure(text="Sub-recipes: $0.00")
            self.total_cost_label.configure(text="Total: $0.00")
            self.per_unit_cost_label.configure(text="Per unit: $0.00")

    def _create_buttons(self):
        """Create dialog buttons."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)
        button_frame.grid_columnconfigure((0, 1), weight=1)

        # Save button
        save_button = ctk.CTkButton(
            button_frame,
            text="Save Recipe",
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

    def _add_ingredient_row(
        self,
        ingredient_id: Optional[int] = None,
        quantity: float = 1.0,
        unit: Optional[str] = None,
    ):
        """
        Add a new ingredient row.

        Args:
            ingredient_id: Ingredient to select (None for default)
            quantity: Ingredient quantity
            unit: Unit of measurement (None for default)
        """
        if not self.available_ingredients:
            show_error(
                "No Ingredients",
                "No ingredients available. Please add ingredients first.",
                parent=self,
            )
            return

        row = RecipeIngredientRow(
            self.ingredients_frame,
            self.available_ingredients,
            self._remove_ingredient_row,
            ingredient_id,
            quantity,
            unit,
        )
        row.grid(row=len(self.ingredient_rows), column=0, sticky="ew", pady=2)
        self.ingredient_rows.append(row)

    def _remove_ingredient_row(self, row: RecipeIngredientRow):
        """
        Remove an ingredient row.

        Args:
            row: Row to remove
        """
        if row in self.ingredient_rows:
            self.ingredient_rows.remove(row)
            row.destroy()
            # Re-grid remaining rows
            for idx, remaining_row in enumerate(self.ingredient_rows):
                remaining_row.grid(row=idx, column=0, sticky="ew", pady=2)

    def _populate_form(self):
        """Populate form fields with existing recipe data."""
        if not self.recipe:
            return

        # Basic fields
        self.name_entry.insert(0, self.recipe.name)
        self.category_combo.set(self.recipe.category)
        self.yield_quantity_entry.insert(0, str(self.recipe.yield_quantity))
        self.yield_unit_combo.set(self.recipe.yield_unit)
        if self.recipe.estimated_time_minutes:
            self.prep_time_entry.insert(0, str(self.recipe.estimated_time_minutes))
        if self.recipe.notes:
            self.notes_text.insert("1.0", self.recipe.notes)

        # Recipe ingredients
        for recipe_ingredient in self.recipe.recipe_ingredients:
            self._add_ingredient_row(
                ingredient_id=recipe_ingredient.ingredient_id,
                quantity=float(recipe_ingredient.quantity),
                unit=recipe_ingredient.unit,
            )

        # Recipe components (T041)
        try:
            self.current_components = recipe_service.get_recipe_components(self.recipe.id)
            self._refresh_subrecipes_display()
            self._update_cost_summary()
        except Exception:
            pass

    def _validate_form(self) -> Optional[Dict[str, Any]]:
        """
        Validate form inputs and return data dictionary.

        Returns:
            Dictionary of form data if valid, None otherwise
        """
        # Get values
        name = self.name_entry.get().strip()
        category = self.category_combo.get()
        yield_quantity_str = self.yield_quantity_entry.get().strip()
        yield_unit = self.yield_unit_combo.get()
        prep_time_str = self.prep_time_entry.get().strip()
        notes = self.notes_text.get("1.0", "end-1c").strip() or None

        # Validate required fields
        if not name:
            show_error("Validation Error", "Recipe name is required", parent=self)
            return None

        if len(name) > MAX_NAME_LENGTH:
            show_error(
                "Validation Error",
                f"Name must be {MAX_NAME_LENGTH} characters or less",
                parent=self,
            )
            return None

        if notes and len(notes) > MAX_NOTES_LENGTH:
            show_error(
                "Validation Error",
                f"Notes must be {MAX_NOTES_LENGTH} characters or less",
                parent=self,
            )
            return None

        # Validate yield quantity
        try:
            yield_quantity = float(yield_quantity_str)
            if yield_quantity <= 0:
                show_error(
                    "Validation Error",
                    "Yield quantity must be greater than zero",
                    parent=self,
                )
                return None
        except ValueError:
            show_error(
                "Validation Error",
                "Yield quantity must be a valid number",
                parent=self,
            )
            return None

        # Validate prep time (optional)
        prep_time = None
        if prep_time_str:
            try:
                prep_time = int(prep_time_str)
                if prep_time < 0:
                    show_error(
                        "Validation Error",
                        "Prep time cannot be negative",
                        parent=self,
                    )
                    return None
            except ValueError:
                show_error(
                    "Validation Error",
                    "Prep time must be a valid whole number",
                    parent=self,
                )
                return None

        # Validate ingredients
        ingredients = []
        for row in self.ingredient_rows:
            data = row.get_data()
            if data:
                ingredients.append(data)

        if not ingredients:
            confirmed = show_confirmation(
                "No Ingredients",
                "This recipe has no ingredients. Continue anyway?",
                parent=self,
            )
            if not confirmed:
                return None

        # Return validated data (T041 - include pending components)
        return {
            "name": name,
            "category": category,
            "yield_quantity": yield_quantity,
            "yield_unit": yield_unit,
            "prep_time": prep_time,
            "notes": notes,
            "ingredients": ingredients,
            "pending_components": self.pending_components,  # For new recipes
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
