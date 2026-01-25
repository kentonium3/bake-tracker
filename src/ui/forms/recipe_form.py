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
from src.services.unit_service import get_units_for_dropdown

# Feature 031: Import hierarchy service for leaf-only filtering
from src.services import ingredient_hierarchy_service
from src.utils.constants import (
    ALL_UNITS,
    WEIGHT_UNITS,
    VOLUME_UNITS,
    COUNT_UNITS,
    MAX_NAME_LENGTH,
    MAX_NOTES_LENGTH,
    PADDING_SMALL,
    PADDING_MEDIUM,
    PADDING_LARGE,
)
from src.services.database import session_scope
from src.ui.widgets.dialogs import show_error, show_confirmation


class IngredientSelectionDialog(ctk.CTkToplevel):
    """
    Dialog for selecting an ingredient using the tree widget (Feature 031).

    Provides hierarchical browsing of ingredients with leaf-only selection
    for recipe ingredient assignment.
    """

    def __init__(self, parent, title: str = "Select Ingredient"):
        """
        Initialize the ingredient selection dialog.

        Args:
            parent: Parent window
            title: Dialog title
        """
        super().__init__(parent)

        self.result: Optional[Dict[str, Any]] = None

        # Configure window
        self.title(title)
        self.geometry("500x500")
        self.resizable(True, True)

        # Center on parent
        self.transient(parent)
        self.grab_set()

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create tree widget
        self._create_tree_widget()

        # Create buttons
        self._create_buttons()

        # Center dialog
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

    def _create_tree_widget(self):
        """Create the ingredient tree widget."""
        from src.ui.widgets.ingredient_tree_widget import IngredientTreeWidget

        tree_frame = ctk.CTkFrame(self)
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        self.tree_widget = IngredientTreeWidget(
            tree_frame,
            on_select_callback=self._on_tree_select,
            leaf_only=True,  # Only allow leaf selection for recipes
            show_search=True,
            show_breadcrumb=True,
        )
        self.tree_widget.grid(row=0, column=0, sticky="nsew")

        # Help text
        help_label = ctk.CTkLabel(
            self,
            text="Select a specific ingredient (not a category). Use search to find ingredients quickly.",
            text_color="gray",
            font=ctk.CTkFont(size=11),
        )
        help_label.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 5))

    def _create_buttons(self):
        """Create dialog buttons."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        button_frame.grid_columnconfigure((0, 1), weight=1)

        # Select button
        self.select_button = ctk.CTkButton(
            button_frame,
            text="Select",
            command=self._on_select,
            width=120,
            state="disabled",  # Disabled until selection
        )
        self.select_button.grid(row=0, column=0, padx=5)

        # Cancel button
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            width=120,
            fg_color="gray",
            hover_color="darkgray",
        )
        cancel_button.grid(row=0, column=1, padx=5)

    def _on_tree_select(self, ingredient_data: Optional[Dict[str, Any]]):
        """Handle tree selection."""
        if ingredient_data and ingredient_data.get("is_leaf", False):
            self._selected_ingredient = ingredient_data
            self.select_button.configure(state="normal")
        else:
            self._selected_ingredient = None
            self.select_button.configure(state="disabled")

    def _on_select(self):
        """Handle select button click."""
        if hasattr(self, "_selected_ingredient") and self._selected_ingredient:
            self.result = self._selected_ingredient
            self.destroy()

    def _on_cancel(self):
        """Handle cancel button click."""
        self.result = None
        self.destroy()

    def get_result(self) -> Optional[Dict[str, Any]]:
        """
        Wait for dialog to close and return result.

        Returns:
            Dictionary with ingredient data if selected, None if cancelled
        """
        self.wait_window()
        return self.result


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
            ingredients: List of available ingredients (should be leaf-only)
            remove_callback: Callback to remove this row
            ingredient_id: Selected ingredient ID (None for new row)
            quantity: Ingredient quantity
            unit: Unit of measurement (defaults to "cup" if None)
        """
        super().__init__(parent)

        self.remove_callback = remove_callback
        self.ingredients = ingredients
        self._selected_ingredient_id: Optional[int] = ingredient_id

        # Configure grid (Quantity / Unit / Ingredient / Browse / Remove)
        self.grid_columnconfigure(0, weight=1)  # Quantity
        self.grid_columnconfigure(1, weight=2)  # Unit dropdown
        self.grid_columnconfigure(2, weight=3)  # Ingredient dropdown
        self.grid_columnconfigure(3, weight=0)  # Browse button
        self.grid_columnconfigure(4, weight=0)  # Remove button

        # Quantity entry
        self.quantity_entry = ctk.CTkEntry(self, width=100, placeholder_text="Quantity")
        self.quantity_entry.insert(0, str(quantity))
        self.quantity_entry.grid(row=0, column=0, padx=(0, PADDING_MEDIUM), pady=5)

        # Unit dropdown - shows measurement units (weight, volume, count) from DB
        # No package units - recipes use measurements, not packaging
        available_units = get_units_for_dropdown(["weight", "volume", "count"])
        self._last_valid_unit = unit if unit else "cup"
        self.unit_combo = ctk.CTkComboBox(
            self,
            values=available_units,
            state="readonly",
            width=100,
            command=self._on_unit_selected,
        )
        # Set unit: use provided unit or default to "cup"
        self.unit_combo.set(self._last_valid_unit)
        self.unit_combo.grid(row=0, column=1, padx=PADDING_MEDIUM, pady=5, sticky="ew")

        # Ingredient dropdown (leaf ingredients only - Feature 031)
        ingredient_names = [i.display_name for i in ingredients]
        self.ingredient_combo = ctk.CTkComboBox(
            self,
            values=ingredient_names if ingredient_names else ["No ingredients available"],
            state="readonly" if ingredient_names else "disabled",
            width=200,
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
                if ingredients:
                    self._selected_ingredient_id = ingredients[0].id

        self.ingredient_combo.grid(row=0, column=2, padx=PADDING_MEDIUM, pady=5, sticky="ew")
        # Bind selection change to update tracked ID
        self.ingredient_combo.configure(command=self._on_ingredient_selected)

        # Browse button (Feature 031) - opens tree dialog for hierarchical selection
        browse_button = ctk.CTkButton(
            self,
            text="...",
            width=30,
            command=self._browse_ingredients,
        )
        browse_button.grid(row=0, column=3, padx=(0, PADDING_MEDIUM), pady=5)

        # Remove button
        remove_button = ctk.CTkButton(
            self,
            text="✕",
            width=30,
            command=lambda: remove_callback(self),
            fg_color="darkred",
            hover_color="red",
        )
        remove_button.grid(row=0, column=4, padx=(0, 0), pady=5)

    def _on_ingredient_selected(self, selected_name: str):
        """Handle ingredient dropdown selection (Feature 031)."""
        for ing in self.ingredients:
            if ing.display_name == selected_name:
                self._selected_ingredient_id = ing.id
                break

    def _browse_ingredients(self):
        """Open tree dialog to browse and select ingredient (Feature 031)."""
        dialog = IngredientSelectionDialog(
            self.winfo_toplevel(),
            title="Select Ingredient",
        )
        result = dialog.get_result()

        if result:
            # Update the combo box with selected ingredient
            display_name = result.get("display_name", "")
            ingredient_id = result.get("id")

            if display_name and ingredient_id:
                self._selected_ingredient_id = ingredient_id
                # Check if ingredient is in our list, add if not
                if display_name not in [i.display_name for i in self.ingredients]:
                    # Need to refresh or add to dropdown
                    current_values = list(self.ingredient_combo.cget("values"))
                    if display_name not in current_values:
                        current_values.append(display_name)
                        self.ingredient_combo.configure(values=current_values)
                self.ingredient_combo.set(display_name)

    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Get ingredient data from this row.

        Returns:
            Dictionary with ingredient_id, quantity, and unit, or None if invalid
        """
        # Feature 031: Use tracked ingredient ID (supports tree selection)
        ingredient_id = self._selected_ingredient_id
        if not ingredient_id:
            # Fallback: try to find by display name
            selected_name = self.ingredient_combo.get()
            for ing in self.ingredients:
                if ing.display_name == selected_name:
                    ingredient_id = ing.id
                    break

        if not ingredient_id:
            return None

        # Get selected unit from dropdown
        unit = self.unit_combo.get()
        if not unit or unit.startswith("--"):
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

        # Find the ingredient (from local list or by ID)
        ingredient = None
        for ing in self.ingredients:
            if ing.id == ingredient_id:
                ingredient = ing
                break

        # If not in local list, fetch from database
        if not ingredient:
            try:
                ingredient = ingredient_crud_service.get_ingredient_by_id(ingredient_id)
            except Exception:
                pass

        if ingredient:
            # Get package_unit from preferred product (if available)
            preferred_product = ingredient.get_preferred_product()
            if preferred_product and hasattr(preferred_product, "package_unit"):
                package_unit_type = get_unit_type(preferred_product.package_unit)

                # Check if cross-type conversion is needed (volume↔weight)
                if recipe_unit_type != package_unit_type:
                    if (recipe_unit_type == "volume" and package_unit_type == "weight") or (
                        recipe_unit_type == "weight" and package_unit_type == "volume"
                    ):
                        # Density is required for volume↔weight conversion
                        if ingredient.get_density_g_per_ml() is None:
                            from src.ui.widgets.dialogs import show_error

                            show_error(
                                "Density Required",
                                f"'{ingredient.display_name}' requires density data for {recipe_unit_type}↔{package_unit_type} conversion.\n\n"
                                f"Please edit the ingredient and add density before using it with {unit} in recipes.",
                                parent=self.winfo_toplevel(),
                            )
                            return None

        return {
            "ingredient_id": ingredient_id,
            "quantity": quantity,
            "unit": unit,
        }

    def _on_unit_selected(self, selected_value: str):
        """Handle unit selection, preventing category headers from being selected."""
        if selected_value.startswith("--"):
            # Revert to last valid selection
            self.unit_combo.set(self._last_valid_unit)
        else:
            # Update last valid selection
            self._last_valid_unit = selected_value


class YieldTypeRow(ctk.CTkFrame):
    """Row widget for a single yield type in the Recipe Edit form."""

    def __init__(
        self,
        parent,
        remove_callback,
        finished_unit_id: Optional[int] = None,
        display_name: str = "",
        item_unit: str = "",
        items_per_batch: int = 1,
        readonly_structure: bool = False,
    ):
        """
        Initialize yield type row.

        Args:
            parent: Parent widget
            remove_callback: Callback to remove this row
            finished_unit_id: ID if editing existing (None for new)
            display_name: Yield type name (e.g., "Large Cookie")
            item_unit: Unit of the finished item (e.g., "cookie", "piece")
            items_per_batch: Number of items per batch
            readonly_structure: If True, structural fields (unit, quantity) are read-only
                                but display_name remains editable. Used for variants (F066).
        """
        super().__init__(parent)

        self.remove_callback = remove_callback
        self.finished_unit_id = finished_unit_id
        self.readonly_structure = readonly_structure

        # Configure grid (Name / Unit / Quantity / Remove)
        self.grid_columnconfigure(0, weight=3)  # Name (wider)
        self.grid_columnconfigure(1, weight=1)  # Unit
        self.grid_columnconfigure(2, weight=1)  # Quantity
        self.grid_columnconfigure(3, weight=0)  # Remove button

        # Name entry (Description) - always editable (T014)
        self.name_entry = ctk.CTkEntry(
            self, width=200, placeholder_text="Description (e.g., Large Cookie)"
        )
        if display_name:
            self.name_entry.insert(0, display_name)
        self.name_entry.grid(row=0, column=0, padx=(0, PADDING_MEDIUM), pady=5, sticky="ew")

        # Unit entry (Item Unit) - read-only for variants (T013)
        self.unit_entry = ctk.CTkEntry(self, width=100, placeholder_text="Unit (e.g., cookie)")
        if item_unit:
            self.unit_entry.insert(0, item_unit)
        self.unit_entry.grid(row=0, column=1, padx=PADDING_MEDIUM, pady=5)
        if readonly_structure:
            self.unit_entry.configure(state="readonly", fg_color="gray25", text_color="gray60")

        # Items per batch entry (Quantity) - read-only for variants (T013)
        self.quantity_entry = ctk.CTkEntry(self, width=80, placeholder_text="Qty/batch")
        if items_per_batch:
            self.quantity_entry.insert(0, str(items_per_batch))
        self.quantity_entry.grid(row=0, column=2, padx=PADDING_MEDIUM, pady=5)
        if readonly_structure:
            self.quantity_entry.configure(state="readonly", fg_color="gray25", text_color="gray60")

        # Remove button (exposed for T019 - disable when only one row)
        # Hidden for variants since they can't remove inherited yields (T013)
        self.remove_button = ctk.CTkButton(
            self,
            text="X",
            width=30,
            command=lambda: remove_callback(self),
            fg_color="darkred",
            hover_color="red",
        )
        self.remove_button.grid(row=0, column=3, padx=(PADDING_MEDIUM, 0), pady=5)
        if readonly_structure:
            self.remove_button.grid_remove()  # Hide for variants

    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Get yield type data from this row.

        Returns:
            Dictionary with id, display_name, item_unit, items_per_batch, or None if invalid
        """
        name = self.name_entry.get().strip()
        unit = self.unit_entry.get().strip()
        quantity_str = self.quantity_entry.get().strip()

        # Validate name
        if not name:
            return None

        # Validate unit
        if not unit:
            return None

        # Validate quantity
        try:
            items_per_batch = int(quantity_str)
            if items_per_batch <= 0:
                return None
        except ValueError:
            return None

        return {
            "id": self.finished_unit_id,
            "display_name": name,
            "item_unit": unit,
            "items_per_batch": items_per_batch,
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
        self.yield_type_rows: List[YieldTypeRow] = []

        # F066: Variant detection for conditional UI
        self.is_variant = False
        self.base_recipe_name = None
        if self.recipe and self.recipe.base_recipe_id:
            self.is_variant = True
            # Fetch base recipe name for display
            try:
                with session_scope() as session:
                    base_recipe = session.get(Recipe, self.recipe.base_recipe_id)
                    if base_recipe:
                        self.base_recipe_name = base_recipe.name
            except Exception:
                self.base_recipe_name = f"Recipe #{self.recipe.base_recipe_id}"

        # Sub-recipe tracking
        self.current_components: List[RecipeComponent] = []  # For existing recipe
        self.pending_components: List[Dict] = []  # For new recipe

        # Load available ingredients (Feature 032: use get_leaf_ingredients directly)
        try:
            leaf_dicts = ingredient_hierarchy_service.get_leaf_ingredients()
            # Convert to ingredient objects for compatibility with existing code
            from src.models.ingredient import Ingredient
            from src.services.database import session_scope
            from sqlalchemy.orm import joinedload

            with session_scope() as session:
                leaf_ids = [d.get("id") for d in leaf_dicts if d.get("id")]
                # Eager-load products relationship to avoid DetachedInstanceError
                # when get_preferred_product() is called after session closes
                self.available_ingredients = (
                    session.query(Ingredient)
                    .options(joinedload(Ingredient.products))
                    .filter(Ingredient.id.in_(leaf_ids))
                    .all()
                )
        except Exception:
            self.available_ingredients = []

        # Load recipe categories from database
        self.recipe_categories = self._load_recipe_categories()

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

    def _load_recipe_categories(self) -> List[str]:
        """Load recipe categories from database.

        Returns:
            List of distinct category names, or default if empty.
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
                cat_list = [cat[0] for cat in categories if cat[0]]
                return cat_list if cat_list else ["Uncategorized"]
        except Exception:
            return ["Uncategorized"]

    def _create_form_fields(self, parent):
        """Create all form input fields."""
        row = 0

        # F066: Variant banner if editing a variant recipe
        if self.is_variant:
            variant_banner = ctk.CTkFrame(parent, fg_color=("lightblue", "darkblue"))
            variant_banner.grid(
                row=row,
                column=0,
                columnspan=2,
                sticky="ew",
                padx=PADDING_MEDIUM,
                pady=(0, PADDING_MEDIUM),
            )

            banner_text = f"Variant of: {self.base_recipe_name or 'Unknown'}"
            banner_label = ctk.CTkLabel(
                variant_banner,
                text=banner_text,
                font=ctk.CTkFont(weight="bold"),
            )
            banner_label.pack(padx=PADDING_MEDIUM, pady=5)

            row += 1

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
            values=self.recipe_categories,
            state="readonly",
        )
        self.category_combo.set(self.recipe_categories[0])
        self.category_combo.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Production Readiness (T030 - Feature 037)
        ready_frame = ctk.CTkFrame(parent, fg_color="transparent")
        ready_frame.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=PADDING_MEDIUM,
            pady=(PADDING_MEDIUM, 5),
        )

        self.production_ready_var = ctk.BooleanVar(value=True)
        self.production_ready_checkbox = ctk.CTkCheckBox(
            ready_frame,
            text="Production Ready",
            variable=self.production_ready_var,
            onvalue=True,
            offvalue=False,
        )
        self.production_ready_checkbox.pack(side="left")

        ready_hint = ctk.CTkLabel(
            ready_frame,
            text="(Uncheck for experimental/test recipes)",
            text_color="gray",
        )
        ready_hint.pack(side="left", padx=10)
        row += 1

        # Yield Information section (combined yield qty/unit + yield types)
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

        # F067: Updated help text with consistent "Finished Unit" terminology
        yield_types_info = ctk.CTkLabel(
            parent,
            text="Each row defines a Finished Unit and quantity per batch for this recipe.",
            text_color="gray",
            font=ctk.CTkFont(size=11),
        )
        yield_types_info.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=PADDING_MEDIUM,
            pady=(PADDING_SMALL, 5),
        )
        row += 1

        # F066: Inheritance explanatory text for variants
        if self.is_variant:
            inheritance_note = ctk.CTkLabel(
                parent,
                text="Yield structure inherited from base recipe. Only display names can be edited.",
                text_color="gray",
                font=ctk.CTkFont(size=11),
            )
            inheritance_note.grid(
                row=row,
                column=0,
                columnspan=2,
                sticky="w",
                padx=PADDING_MEDIUM,
                pady=(0, 5),
            )
            row += 1

        # F067: Column labels for yield inputs
        labels_frame = ctk.CTkFrame(parent, fg_color="transparent")
        labels_frame.grid(
            row=row, column=0, columnspan=2, sticky="ew", padx=PADDING_MEDIUM
        )
        # Configure columns to match YieldTypeRow proportions
        labels_frame.grid_columnconfigure(0, weight=3)  # Name column (wider)
        labels_frame.grid_columnconfigure(1, weight=1)  # Unit column
        labels_frame.grid_columnconfigure(2, weight=1)  # Qty column
        labels_frame.grid_columnconfigure(3, weight=0)  # Spacer for remove button area

        name_label = ctk.CTkLabel(
            labels_frame, text="Finished Unit Name", font=ctk.CTkFont(size=11)
        )
        name_label.grid(row=0, column=0, sticky="w", padx=(0, PADDING_MEDIUM))

        unit_label = ctk.CTkLabel(
            labels_frame, text="Unit", font=ctk.CTkFont(size=11)
        )
        unit_label.grid(row=0, column=1, sticky="w", padx=PADDING_MEDIUM)

        qty_label = ctk.CTkLabel(
            labels_frame, text="Qty/Batch", font=ctk.CTkFont(size=11)
        )
        qty_label.grid(row=0, column=2, sticky="w", padx=PADDING_MEDIUM)
        row += 1

        # Yield types container
        self.yield_types_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.yield_types_frame.grid(
            row=row, column=0, columnspan=2, sticky="ew", padx=PADDING_MEDIUM, pady=5
        )
        self.yield_types_frame.grid_columnconfigure(0, weight=1)
        row += 1

        # Add yield type button (hidden for variants - F066)
        if not self.is_variant:
            add_yield_type_button = ctk.CTkButton(
                parent,
                text="+ Add Yield Type",
                command=self._add_yield_type_row,
                width=150,
            )
            add_yield_type_button.grid(row=row, column=0, columnspan=2, padx=PADDING_MEDIUM, pady=5)
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
            text="+ Add Ingredient",
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

        # Prep time (optional) - moved here from Yield Information section
        prep_time_label = ctk.CTkLabel(parent, text="Prep Time (min):", anchor="w")
        prep_time_label.grid(
            row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=(PADDING_LARGE, 5)
        )

        self.prep_time_entry = ctk.CTkEntry(
            parent,
            width=100,
            placeholder_text="e.g., 30",
        )
        self.prep_time_entry.grid(
            row=row, column=1, sticky="w", padx=PADDING_MEDIUM, pady=(PADDING_LARGE, 5)
        )
        row += 1

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

        # Name and quantity label
        name_text = f"• {component['recipe_name']} ({component['quantity']}x)"
        name_label = ctk.CTkLabel(row_frame, text=name_text, anchor="w")
        name_label.grid(row=0, column=0, sticky="w", padx=5)

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

    def _add_yield_type_row(
        self,
        finished_unit_id: Optional[int] = None,
        display_name: str = "",
        item_unit: str = "",
        items_per_batch: int = 1,
    ):
        """
        Add a new yield type row.

        Args:
            finished_unit_id: ID if editing existing (None for new)
            display_name: Yield type name
            item_unit: Unit of the finished item (e.g., "cookie", "piece")
            items_per_batch: Number of items per batch
        """
        row = YieldTypeRow(
            self.yield_types_frame,
            self._remove_yield_type_row,
            finished_unit_id,
            display_name,
            item_unit,
            items_per_batch,
            readonly_structure=self.is_variant,  # F066: structural fields read-only for variants
        )
        row.grid(row=len(self.yield_type_rows), column=0, sticky="ew", pady=2)
        self.yield_type_rows.append(row)
        self._update_remove_buttons()

        # Explicitly re-apply readonly state for variants (belt-and-suspenders)
        if self.is_variant:
            row.unit_entry.configure(state="readonly", fg_color="gray25", text_color="gray60")
            row.quantity_entry.configure(state="readonly", fg_color="gray25", text_color="gray60")
            row.remove_button.grid_remove()

    def _remove_yield_type_row(self, row: YieldTypeRow):
        """
        Remove a yield type row after confirmation.

        Args:
            row: Row to remove
        """
        if row in self.yield_type_rows:
            # Check if row has data (existing yield type or filled-in new row)
            name = row.name_entry.get().strip()
            has_data = name or row.finished_unit_id is not None

            if has_data:
                # Confirm deletion (F044 fix: FR-008 compliance)
                confirmed = show_confirmation(
                    "Remove Yield Type",
                    f"Are you sure you want to remove the yield type '{name or 'this entry'}'?\n\n"
                    "This change will be saved when you save the recipe.",
                    parent=self,
                )
                if not confirmed:
                    return

            self.yield_type_rows.remove(row)
            row.destroy()
            # Re-grid remaining rows
            for idx, remaining_row in enumerate(self.yield_type_rows):
                remaining_row.grid(row=idx, column=0, sticky="ew", pady=2)
            # Update remove button states (T019)
            self._update_remove_buttons()

    def _update_remove_buttons(self):
        """
        Enable/disable Remove buttons based on row count.

        When only one yield type row exists, disable its Remove button
        to enforce the "at least one yield type" requirement.
        """
        row_count = len(self.yield_type_rows)
        for row in self.yield_type_rows:
            if row_count <= 1:
                row.remove_button.configure(state="disabled")
            else:
                row.remove_button.configure(state="normal")

    def _populate_form(self):
        """Populate form fields with existing recipe data."""
        if not self.recipe:
            return

        # Basic fields
        self.name_entry.insert(0, self.recipe.name)
        self.category_combo.set(self.recipe.category)
        if self.recipe.estimated_time_minutes:
            self.prep_time_entry.insert(0, str(self.recipe.estimated_time_minutes))
        if self.recipe.notes:
            self.notes_text.insert("1.0", self.recipe.notes)

        # Production readiness (T030 - Feature 037)
        if self.recipe.is_production_ready:
            self.production_ready_var.set(True)
        else:
            self.production_ready_var.set(False)

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
        except Exception:
            pass

        # Load yield types (F044 - WP03 T009)
        try:
            from src.services import finished_unit_service

            yield_types = finished_unit_service.get_units_by_recipe(self.recipe.id)
            for yt in yield_types:
                self._add_yield_type_row(
                    finished_unit_id=yt.id,
                    display_name=yt.display_name,
                    item_unit=yt.item_unit or "",
                    items_per_batch=yt.items_per_batch or 1,
                )
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

        # Validate yield types (Feature 056 - T018: require at least one complete yield type)
        yield_types = []
        for idx, row in enumerate(self.yield_type_rows):
            # Get raw values for validation
            row_name = row.name_entry.get().strip()
            row_unit = row.unit_entry.get().strip()
            row_quantity_str = row.quantity_entry.get().strip()

            # Skip completely empty rows (not an error, just not entered)
            if not row_name and not row_unit and not row_quantity_str:
                continue

            # Check for partial rows (some fields but not all)
            has_name = bool(row_name)
            has_unit = bool(row_unit)
            has_qty = bool(row_quantity_str)

            if not all([has_name, has_unit, has_qty]):
                # Partial row - show specific error
                missing_fields = []
                if not has_name:
                    missing_fields.append("Description")
                if not has_unit:
                    missing_fields.append("Unit")
                if not has_qty:
                    missing_fields.append("Quantity")

                show_error(
                    "Validation Error",
                    f"Yield type row {idx + 1} is incomplete.\n"
                    f"Missing: {', '.join(missing_fields)}",
                    parent=self,
                )
                return None

            # Validate quantity is a positive integer
            try:
                items_per_batch = int(row_quantity_str)
            except ValueError:
                show_error(
                    "Validation Error",
                    f"Yield type '{row_name}': Quantity must be a whole number.",
                    parent=self,
                )
                return None

            if items_per_batch <= 0:
                show_error(
                    "Validation Error",
                    f"Yield type '{row_name}': Quantity must be greater than zero.",
                    parent=self,
                )
                return None

            yield_types.append(
                {
                    "id": row.finished_unit_id,
                    "display_name": row_name,
                    "item_unit": row_unit,
                    "items_per_batch": items_per_batch,
                }
            )

        # Feature 056 - T018: Require at least one complete yield type
        if not yield_types:
            show_error(
                "Validation Error",
                "At least one yield type is required.\n\n"
                "Add a row with Description (e.g., 'Large Cookie'), "
                "Unit (e.g., 'cookie'), and Quantity per batch (e.g., 24).",
                parent=self,
            )
            return None

        # Return validated data (T041 - include pending components, Feature 056 - yield_types only)
        return {
            "name": name,
            "category": category,
            "prep_time": prep_time,
            "notes": notes,
            "ingredients": ingredients,
            "pending_components": self.pending_components,  # For new recipes
            "is_production_ready": self.production_ready_var.get(),  # T030 - Feature 037
            "yield_types": yield_types,  # F044 - WP03
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
