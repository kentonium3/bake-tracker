"""
Ingredient form dialog for adding and editing ingredients.

Provides a comprehensive form for creating and updating ingredient records
with validation and error handling.
"""

import customtkinter as ctk
from typing import Optional, Dict, Any, List

from src.models.ingredient import Ingredient
from src.services.unit_service import get_units_by_category
from src.services import ingredient_service
from src.utils.constants import (
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


def _get_categories_from_database() -> List[str]:
    """Load categories from existing ingredients in database."""
    try:
        ingredients = ingredient_service.get_all_ingredients()
        categories = sorted(set(
            ing.get("category", "")
            for ing in ingredients
            if ing.get("category")
        ))
        return categories if categories else ["Uncategorized"]
    except Exception:
        return ["Uncategorized"]


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

        # Category field (required) - uses database categories for consistency
        category_label = ctk.CTkLabel(parent, text="Category*:", anchor="w")
        category_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        self.db_categories = _get_categories_from_database()
        self.category_combo = ctk.CTkComboBox(
            parent,
            width=400,
            values=self.db_categories,
            state="readonly",
        )
        self.category_combo.set(self.db_categories[0] if self.db_categories else "")
        self.category_combo.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Purchase information section
        purchase_label = ctk.CTkLabel(
            parent,
            text="Purchase Information",
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

        # Package type (optional)
        package_type_label = ctk.CTkLabel(parent, text="Package Type:", anchor="w")
        package_type_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        package_types = [""] + PACKAGE_UNITS  # Empty string for "none"
        self.package_type_combo = ctk.CTkComboBox(
            parent,
            width=400,
            values=package_types,
            state="readonly",
        )
        self.package_type_combo.set("")  # Optional
        self.package_type_combo.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Package quantity (required)
        package_qty_label = ctk.CTkLabel(parent, text="Quantity per Package*:", anchor="w")
        package_qty_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        self.package_unit_quantity_entry = ctk.CTkEntry(
            parent,
            width=400,
            placeholder_text="e.g., 25 (how much in each package)",
        )
        self.package_unit_quantity_entry.grid(
            row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5
        )
        row += 1

        # Package unit (required)
        package_unit_label = ctk.CTkLabel(parent, text="Package Unit*:", anchor="w")
        package_unit_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        standard_units = WEIGHT_UNITS + VOLUME_UNITS + COUNT_UNITS
        self.package_unit_combo = ctk.CTkComboBox(
            parent,
            width=400,
            values=standard_units,
            state="readonly",
        )
        self.package_unit_combo.set("lb")  # Common default
        self.package_unit_combo.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Volume/Weight Equivalency section
        equivalency_label = ctk.CTkLabel(
            parent,
            text="Volume ↔ Weight Equivalency (Optional)",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        equivalency_label.grid(
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
            text="Define how volume relates to weight for this ingredient (e.g., 1 cup = 200 grams).\nRequired only when recipes use different unit types (volume/weight) than purchase unit.",
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

        # Equivalency input: Volume = Weight
        equiv_frame = ctk.CTkFrame(parent, fg_color="transparent")
        equiv_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        equiv_frame.grid_columnconfigure(1, weight=1)
        equiv_frame.grid_columnconfigure(3, weight=1)

        # Volume quantity
        self.equiv_volume_qty_entry = ctk.CTkEntry(
            equiv_frame,
            width=80,
            placeholder_text="1",
        )
        self.equiv_volume_qty_entry.grid(row=0, column=0, padx=(0, 5))

        # Volume unit dropdown - populated from unit reference table
        volume_units = [u.code for u in get_units_by_category("volume")]
        self.equiv_volume_unit_combo = ctk.CTkComboBox(
            equiv_frame,
            width=100,
            values=volume_units,
            state="readonly",
        )
        self.equiv_volume_unit_combo.set("cup")
        self.equiv_volume_unit_combo.grid(row=0, column=1, padx=(0, 10))

        # Equals label
        equals_label = ctk.CTkLabel(equiv_frame, text="=")
        equals_label.grid(row=0, column=2, padx=10)

        # Weight quantity
        self.equiv_weight_qty_entry = ctk.CTkEntry(
            equiv_frame,
            width=80,
            placeholder_text="200",
        )
        self.equiv_weight_qty_entry.grid(row=0, column=3, padx=(10, 5))

        # Weight unit dropdown - populated from unit reference table
        weight_units = [u.code for u in get_units_by_category("weight")]
        self.equiv_weight_unit_combo = ctk.CTkComboBox(
            equiv_frame,
            width=100,
            values=weight_units,
            state="readonly",
        )
        self.equiv_weight_unit_combo.set("g")
        self.equiv_weight_unit_combo.grid(row=0, column=4)

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

        self.name_entry.insert(0, self.ingredient.display_name)
        if self.ingredient.brand:
            self.brand_entry.insert(0, self.ingredient.brand)
        self.category_combo.set(self.ingredient.category)

        # Package information
        if self.ingredient.package_type:
            self.package_type_combo.set(self.ingredient.package_type)
        self.package_unit_quantity_entry.insert(0, str(self.ingredient.package_unit_quantity))
        self.package_unit_combo.set(self.ingredient.package_unit)

        # Equivalency (convert density back to equivalency format)
        if self.ingredient.density_g_per_cup:
            # Display as: 1 cup = X grams
            self.equiv_volume_qty_entry.insert(0, "1")
            self.equiv_volume_unit_combo.set("cup")
            self.equiv_weight_qty_entry.insert(0, str(self.ingredient.density_g_per_cup))
            self.equiv_weight_unit_combo.set("g")

        # Inventory
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
        package_type = self.package_type_combo.get().strip() or None
        package_unit_quantity_str = self.package_unit_quantity_entry.get().strip()
        package_unit = self.package_unit_combo.get()

        # Get equivalency values
        equiv_vol_qty_str = self.equiv_volume_qty_entry.get().strip()
        equiv_vol_unit = self.equiv_volume_unit_combo.get()
        equiv_wt_qty_str = self.equiv_weight_qty_entry.get().strip()
        equiv_wt_unit = self.equiv_weight_unit_combo.get()

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

        # Validate package quantity (required)
        try:
            package_unit_quantity = float(package_unit_quantity_str)
            if package_unit_quantity <= 0:
                show_error(
                    "Validation Error",
                    "Quantity per package must be greater than zero",
                    parent=self,
                )
                return None
        except ValueError:
            show_error(
                "Validation Error", "Quantity per package must be a valid number", parent=self
            )
            return None

        # Validate equivalency and convert to density (g/cup) - optional
        density_g_per_cup = None
        has_volume = bool(equiv_vol_qty_str)
        has_weight = bool(equiv_wt_qty_str)

        # If user entered equivalency data, validate and convert
        if has_volume or has_weight:
            # Both fields must be filled if one is filled
            if not (has_volume and has_weight):
                show_error(
                    "Validation Error",
                    "Both volume and weight must be specified for equivalency",
                    parent=self,
                )
                return None

            try:
                equiv_vol_qty = float(equiv_vol_qty_str)
                equiv_wt_qty = float(equiv_wt_qty_str)

                if equiv_vol_qty <= 0 or equiv_wt_qty <= 0:
                    show_error(
                        "Validation Error",
                        "Equivalency values must be greater than zero",
                        parent=self,
                    )
                    return None

                # Convert equivalency to density (g/cup)
                from src.services.unit_converter import convert_standard_units

                # Convert volume to cups
                success, vol_in_cups, error = convert_standard_units(
                    equiv_vol_qty, equiv_vol_unit, "cup"
                )
                if not success:
                    show_error(
                        "Validation Error", f"Invalid volume unit conversion: {error}", parent=self
                    )
                    return None

                # Convert weight to grams
                success, wt_in_grams, error = convert_standard_units(
                    equiv_wt_qty, equiv_wt_unit, "g"
                )
                if not success:
                    show_error(
                        "Validation Error", f"Invalid weight unit conversion: {error}", parent=self
                    )
                    return None

                # Calculate density (g/cup)
                density_g_per_cup = wt_in_grams / vol_in_cups

            except ValueError:
                show_error(
                    "Validation Error", "Equivalency values must be valid numbers", parent=self
                )
                return None

        # Validate inventory quantity
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
            "package_type": package_type,
            "package_unit_quantity": package_unit_quantity,
            "package_unit": package_unit,
            "density_g_per_cup": density_g_per_cup,
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
