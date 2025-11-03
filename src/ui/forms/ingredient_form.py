"""
Ingredient form dialog for adding and editing ingredients.

Provides a comprehensive form for creating and updating ingredient records
with validation and error handling.
"""

import customtkinter as ctk
from typing import Optional, Dict, Any

from src.models.ingredient import Ingredient
from src.utils.constants import (
    INGREDIENT_CATEGORIES,
    ALL_UNITS,
    PACKAGE_UNITS,
    WEIGHT_UNITS,
    VOLUME_UNITS,
    COUNT_UNITS,
    MAX_NAME_LENGTH,
    MAX_BRAND_LENGTH,
    MAX_NOTES_LENGTH,
    PADDING_MEDIUM,
    PADDING_LARGE,
)
from src.ui.widgets.dialogs import show_error


class IngredientFormDialog(ctk.CTkToplevel):
    """
    Dialog for creating or editing an ingredient.

    Provides a comprehensive form with validation for all ingredient fields.
    """

    def __init__(
        self,
        parent,
        ingredient: Optional[Ingredient] = None,
        title: str = "Add Ingredient",
    ):
        """
        Initialize the ingredient form dialog.

        Args:
            parent: Parent window
            ingredient: Existing ingredient to edit (None for new)
            title: Dialog title
        """
        super().__init__(parent)

        self.ingredient = ingredient
        self.result = None

        # Configure window
        self.title(title)
        self.geometry("600x700")
        self.resizable(False, False)

        # Center on parent
        self.transient(parent)
        self.grab_set()

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create main frame
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=PADDING_LARGE, pady=PADDING_LARGE)
        main_frame.grid_columnconfigure(1, weight=1)

        # Create form fields
        self._create_form_fields(main_frame)

        # Create buttons
        self._create_buttons()

        # Populate if editing
        if self.ingredient:
            self._populate_form()

    def _create_form_fields(self, parent):
        """Create all form input fields."""
        row = 0

        # Name field (required)
        name_label = ctk.CTkLabel(parent, text="Name*:", anchor="w")
        name_label.grid(
            row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=(PADDING_MEDIUM, 5)
        )

        self.name_entry = ctk.CTkEntry(
            parent, width=400, placeholder_text="e.g., All-Purpose Flour"
        )
        self.name_entry.grid(
            row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=(PADDING_MEDIUM, 5)
        )
        row += 1

        # Brand field (optional)
        brand_label = ctk.CTkLabel(parent, text="Brand:", anchor="w")
        brand_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        self.brand_entry = ctk.CTkEntry(parent, width=400, placeholder_text="e.g., King Arthur")
        self.brand_entry.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Category field (required)
        category_label = ctk.CTkLabel(parent, text="Category*:", anchor="w")
        category_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        self.category_combo = ctk.CTkComboBox(
            parent,
            width=400,
            values=INGREDIENT_CATEGORIES,
            state="readonly",
        )
        self.category_combo.set(INGREDIENT_CATEGORIES[0])
        self.category_combo.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Purchase unit section
        purchase_label = ctk.CTkLabel(
            parent,
            text="Purchase Unit Information",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        purchase_label.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=PADDING_MEDIUM,
            pady=(PADDING_LARGE, PADDING_MEDIUM),
        )
        row += 1

        # Purchase unit (required)
        purchase_unit_label = ctk.CTkLabel(parent, text="Purchase Unit*:", anchor="w")
        purchase_unit_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        self.purchase_unit_combo = ctk.CTkComboBox(
            parent,
            width=400,
            values=PACKAGE_UNITS,
            state="readonly",
        )
        self.purchase_unit_combo.set(PACKAGE_UNITS[0])
        self.purchase_unit_combo.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Purchase unit size (optional)
        purchase_size_label = ctk.CTkLabel(parent, text="Purchase Unit Size:", anchor="w")
        purchase_size_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        self.purchase_size_entry = ctk.CTkEntry(
            parent,
            width=400,
            placeholder_text="e.g., 25 lb or 72 oz",
        )
        self.purchase_size_entry.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Unit Conversion section
        conversion_label = ctk.CTkLabel(
            parent,
            text="Unit Conversion Information",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        conversion_label.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=PADDING_MEDIUM,
            pady=(PADDING_LARGE, PADDING_MEDIUM),
        )
        row += 1

        # Help text
        help_text = ctk.CTkLabel(
            parent,
            text="For flexible recipe units, enter density below. Recipe unit & conversion factor are optional.",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            wraplength=400,
            anchor="w",
            justify="left",
        )
        help_text.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=PADDING_MEDIUM,
            pady=(0, PADDING_MEDIUM),
        )
        row += 1

        # Density (grams per cup)
        density_label = ctk.CTkLabel(parent, text="Density (g/cup):", anchor="w")
        density_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        self.density_entry = ctk.CTkEntry(
            parent,
            width=400,
            placeholder_text="e.g., 200 for sugar, 120 for flour (optional)",
        )
        self.density_entry.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Recipe unit (optional)
        recipe_unit_label = ctk.CTkLabel(parent, text="Default Recipe Unit:", anchor="w")
        recipe_unit_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        # Group units by type for easier selection
        recipe_units = [""] + WEIGHT_UNITS + VOLUME_UNITS + COUNT_UNITS
        self.recipe_unit_combo = ctk.CTkComboBox(
            parent,
            width=400,
            values=recipe_units,
            state="readonly",
        )
        self.recipe_unit_combo.set("")  # Optional
        self.recipe_unit_combo.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Conversion factor (required only if recipe_unit is set)
        conversion_factor_label = ctk.CTkLabel(parent, text="Conversion Factor*:", anchor="w")
        conversion_factor_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        self.conversion_entry = ctk.CTkEntry(
            parent,
            width=400,
            placeholder_text="e.g., 100 (1 bag = 100 cups)",
        )
        self.conversion_entry.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Inventory section
        inventory_label = ctk.CTkLabel(
            parent,
            text="Inventory & Cost",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        inventory_label.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=PADDING_MEDIUM,
            pady=(PADDING_LARGE, PADDING_MEDIUM),
        )
        row += 1

        # Quantity (required)
        quantity_label = ctk.CTkLabel(parent, text="Quantity*:", anchor="w")
        quantity_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        self.quantity_entry = ctk.CTkEntry(
            parent,
            width=400,
            placeholder_text="e.g., 2.5 (in purchase units)",
        )
        self.quantity_entry.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Unit cost (required)
        unit_cost_label = ctk.CTkLabel(parent, text="Unit Cost*:", anchor="w")
        unit_cost_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        self.unit_cost_entry = ctk.CTkEntry(
            parent,
            width=400,
            placeholder_text="e.g., 18.99 (cost per purchase unit)",
        )
        self.unit_cost_entry.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Notes (optional)
        notes_label = ctk.CTkLabel(parent, text="Notes:", anchor="w")
        notes_label.grid(row=row, column=0, sticky="nw", padx=PADDING_MEDIUM, pady=5)

        self.notes_text = ctk.CTkTextbox(parent, width=400, height=80)
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

    def _create_buttons(self):
        """Create dialog buttons."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)
        button_frame.grid_columnconfigure((0, 1), weight=1)

        # Save button
        save_button = ctk.CTkButton(
            button_frame,
            text="Save",
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

    def _populate_form(self):
        """Populate form fields with existing ingredient data."""
        if not self.ingredient:
            return

        self.name_entry.insert(0, self.ingredient.name)
        if self.ingredient.brand:
            self.brand_entry.insert(0, self.ingredient.brand)
        self.category_combo.set(self.ingredient.category)
        self.purchase_unit_combo.set(self.ingredient.purchase_unit)
        if self.ingredient.purchase_unit_size:
            self.purchase_size_entry.insert(0, self.ingredient.purchase_unit_size)

        # Density
        if self.ingredient.density_g_per_cup:
            self.density_entry.insert(0, str(self.ingredient.density_g_per_cup))

        # Recipe unit (optional)
        if self.ingredient.recipe_unit:
            self.recipe_unit_combo.set(self.ingredient.recipe_unit)
        else:
            self.recipe_unit_combo.set("")

        self.conversion_entry.insert(0, str(self.ingredient.conversion_factor))
        self.quantity_entry.insert(0, str(self.ingredient.quantity))
        self.unit_cost_entry.insert(0, str(self.ingredient.unit_cost))
        if self.ingredient.notes:
            self.notes_text.insert("1.0", self.ingredient.notes)

    def _validate_form(self) -> Optional[Dict[str, Any]]:
        """
        Validate form inputs and return data dictionary.

        Returns:
            Dictionary of form data if valid, None otherwise
        """
        # Get values
        name = self.name_entry.get().strip()
        brand = self.brand_entry.get().strip() or None
        category = self.category_combo.get()
        purchase_unit = self.purchase_unit_combo.get()
        purchase_unit_size = self.purchase_size_entry.get().strip() or None
        density_str = self.density_entry.get().strip()
        recipe_unit = self.recipe_unit_combo.get().strip()
        if not recipe_unit:  # Empty string means None
            recipe_unit = None
        conversion_factor_str = self.conversion_entry.get().strip()
        quantity_str = self.quantity_entry.get().strip()
        unit_cost_str = self.unit_cost_entry.get().strip()
        notes = self.notes_text.get("1.0", "end-1c").strip() or None

        # Validate required fields
        if not name:
            show_error("Validation Error", "Name is required", parent=self)
            return None

        if len(name) > MAX_NAME_LENGTH:
            show_error(
                "Validation Error",
                f"Name must be {MAX_NAME_LENGTH} characters or less",
                parent=self,
            )
            return None

        if brand and len(brand) > MAX_BRAND_LENGTH:
            show_error(
                "Validation Error",
                f"Brand must be {MAX_BRAND_LENGTH} characters or less",
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

        # Validate density (optional)
        density = None
        if density_str:
            try:
                density = float(density_str)
                if density <= 0:
                    show_error(
                        "Validation Error", "Density must be greater than zero", parent=self
                    )
                    return None
            except ValueError:
                show_error("Validation Error", "Density must be a valid number", parent=self)
                return None

        # Validate conversion factor (required)
        try:
            conversion_factor = float(conversion_factor_str)
            if conversion_factor <= 0:
                show_error(
                    "Validation Error", "Conversion factor must be greater than zero", parent=self
                )
                return None
        except ValueError:
            show_error("Validation Error", "Conversion factor must be a valid number", parent=self)
            return None

        try:
            quantity = float(quantity_str)
            if quantity < 0:
                show_error("Validation Error", "Quantity cannot be negative", parent=self)
                return None
        except ValueError:
            show_error("Validation Error", "Quantity must be a valid number", parent=self)
            return None

        try:
            unit_cost = float(unit_cost_str)
            if unit_cost < 0:
                show_error("Validation Error", "Unit cost cannot be negative", parent=self)
                return None
        except ValueError:
            show_error("Validation Error", "Unit cost must be a valid number", parent=self)
            return None

        # Return validated data
        return {
            "name": name,
            "brand": brand,
            "category": category,
            "purchase_unit": purchase_unit,
            "purchase_unit_size": purchase_unit_size,
            "density_g_per_cup": density,
            "recipe_unit": recipe_unit,
            "conversion_factor": conversion_factor,
            "quantity": quantity,
            "unit_cost": unit_cost,
            "notes": notes,
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
