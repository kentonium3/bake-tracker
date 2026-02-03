"""
Dialog for creating/editing a MaterialUnit.

Feature 084: MaterialUnit Schema Refactor - WP07.
MaterialUnits are now children of MaterialProduct, not Material.

Feature 085: Added unit dropdown for linear products with auto-conversion to cm.
"""

import customtkinter as ctk
from tkinter import messagebox
from typing import Optional, Dict

from src.services import material_unit_service
from src.services import material_catalog_service
from src.services.material_unit_converter import (
    get_linear_unit_options,
    convert_to_cm,
)
from src.services.exceptions import ValidationError, ServiceError
from src.ui.utils.error_handler import handle_error


class MaterialUnitDialog(ctk.CTkToplevel):
    """
    Dialog for creating or editing a MaterialUnit.

    Feature 084: MaterialUnits belong to MaterialProduct.
    - Create: Requires material_product_id
    - Edit: Loads existing unit data, only name/description editable
    """

    def __init__(
        self,
        parent,
        unit_id: Optional[int] = None,
        product_id: Optional[int] = None,
        unit_data: Optional[dict] = None,
    ):
        """
        Initialize the MaterialUnit dialog.

        Args:
            parent: Parent window
            unit_id: ID of existing unit to edit (None for new)
            product_id: ID of MaterialProduct (required for new units)
            unit_data: Pre-loaded unit data dict (optional, for edit mode)
        """
        super().__init__(parent)

        self.parent_window = parent
        self.unit_id = unit_id
        self.product_id = product_id
        self.unit_data = unit_data
        self.result = None  # Will be True if saved successfully

        # Feature 085: Detect if this is a linear product for unit dropdown
        self.base_unit_type = self._get_material_base_unit_type()
        self.unit_dropdown = None
        self._unit_code_map = None
        self.preview_label = None

        # Configure window
        self.title("Edit Unit" if unit_id else "Add Unit")
        # Feature 085: Increase height for linear products (unit dropdown + preview)
        height = 350 if self._is_linear_product() and not unit_id else 280
        self.geometry(f"400x{height}")
        self.resizable(False, False)

        # Center on parent
        self.transient(parent)

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create form
        self._create_form()
        self._create_buttons()

        # Populate if editing
        if unit_id and unit_data:
            self._populate_form()

        # Make dialog modal - use simpler pattern matching working dialogs
        self.update_idletasks()
        self.wait_visibility()
        self.grab_set()
        self.focus_force()

    def _create_form(self):
        """Create form fields."""
        form_frame = ctk.CTkFrame(self)
        form_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        form_frame.grid_columnconfigure(1, weight=1)

        row = 0

        # Name field (required)
        ctk.CTkLabel(form_frame, text="Name*:").grid(
            row=row, column=0, sticky="w", padx=10, pady=(10, 5)
        )
        self.name_entry = ctk.CTkEntry(
            form_frame, placeholder_text="e.g., 6-inch cut"
        )
        self.name_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=(10, 5))
        row += 1

        # Quantity per unit field (required, only for new units)
        ctk.CTkLabel(form_frame, text="Qty per Unit*:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        if self.unit_id:
            # Edit mode - show as read-only
            qty_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
            qty_frame.grid(row=row, column=1, sticky="w", padx=10, pady=5)
            qty_value = self.unit_data.get("quantity_per_unit", 1.0) if self.unit_data else 1.0

            # Feature 086: Smart quantity formatting based on base_unit_type
            if self.base_unit_type == "each":
                if qty_value == int(qty_value):
                    qty_display = str(int(qty_value))
                else:
                    qty_display = f"{qty_value:.2f}"
            else:
                # Linear/square types show 2 decimal places (cm precision)
                qty_display = f"{qty_value:.2f}"

            ctk.CTkLabel(
                qty_frame,
                text=qty_display,
                font=ctk.CTkFont(weight="bold"),
            ).pack(side="left")
            ctk.CTkLabel(
                qty_frame,
                text="  (cannot change after creation)",
                text_color="gray",
            ).pack(side="left")
            self.qty_entry = None
        else:
            # New mode - editable
            # Feature 085: T012 - Update placeholder based on product type
            if self._is_linear_product():
                placeholder = "e.g., 8 (then select unit)"
            else:
                placeholder = "e.g., 1.0"

            self.qty_entry = ctk.CTkEntry(
                form_frame, placeholder_text=placeholder
            )
            self.qty_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        row += 1

        # Feature 085: T010 - Add unit dropdown for linear products (new mode only)
        if self._is_linear_product() and not self.unit_id:
            ctk.CTkLabel(form_frame, text="Unit:").grid(
                row=row, column=0, sticky="w", padx=10, pady=5
            )

            # Get options from conversion service
            options = get_linear_unit_options()
            option_names = [name for _, name in options]

            # Store code mapping for conversion on save
            self._unit_code_map = {name: code for code, name in options}

            self.unit_dropdown = ctk.CTkComboBox(
                form_frame,
                values=option_names,
                width=200,
                command=self._update_conversion_preview,
            )
            self.unit_dropdown.set(option_names[0])  # Default to cm
            self.unit_dropdown.grid(row=row, column=1, sticky="w", padx=10, pady=5)
            row += 1

            # Feature 085: T012 - Add conversion preview label
            self.preview_label = ctk.CTkLabel(
                form_frame,
                text="",
                text_color="gray",
            )
            self.preview_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=10)

            # Bind quantity entry to update preview on keypress
            if self.qty_entry:
                self.qty_entry.bind("<KeyRelease>", self._update_conversion_preview)
            row += 1

        # Description field (optional)
        ctk.CTkLabel(form_frame, text="Description:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.desc_entry = ctk.CTkEntry(
            form_frame, placeholder_text="Optional description"
        )
        self.desc_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        row += 1

    def _create_buttons(self):
        """Create dialog buttons."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))

        # Cancel button
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.destroy,
            width=80,
            fg_color="gray",
        )
        cancel_button.pack(side="right", padx=5)

        # Save button
        save_button = ctk.CTkButton(
            button_frame,
            text="Save",
            command=self._on_save,
            width=80,
        )
        save_button.pack(side="right", padx=5)

    def _populate_form(self):
        """Pre-fill form when editing existing unit."""
        if not self.unit_data:
            return

        # Set name
        name = self.unit_data.get("name", "")
        if name:
            self.name_entry.insert(0, name)

        # Set description
        desc = self.unit_data.get("description", "")
        if desc:
            self.desc_entry.insert(0, desc)

    def _on_save(self):
        """Validate and save the unit."""
        name = self.name_entry.get().strip()
        description = self.desc_entry.get().strip() or None

        # Validate name
        if not name:
            messagebox.showerror("Validation Error", "Name is required.")
            return

        try:
            if self.unit_id:
                # Update existing unit
                material_unit_service.update_unit(
                    unit_id=self.unit_id,
                    name=name,
                    description=description,
                )
            else:
                # Create new unit - validate quantity
                qty_str = self.qty_entry.get().strip() if self.qty_entry else "1.0"
                try:
                    quantity = float(qty_str)
                    if quantity <= 0:
                        raise ValueError("Must be positive")
                except ValueError:
                    messagebox.showerror(
                        "Validation Error", "Quantity must be a positive number."
                    )
                    return

                # Feature 085: T011 - Convert to cm if linear product with dropdown
                if self.unit_dropdown and self._unit_code_map:
                    selected_display = self.unit_dropdown.get()
                    unit_code = self._unit_code_map.get(selected_display, "cm")
                    quantity_per_unit = convert_to_cm(quantity, unit_code)
                else:
                    # "each" type or no dropdown - use value as-is
                    quantity_per_unit = quantity

                if not self.product_id:
                    messagebox.showerror(
                        "Error", "Product must be saved before adding units."
                    )
                    return

                material_unit_service.create_unit(
                    material_product_id=self.product_id,
                    name=name,
                    quantity_per_unit=quantity_per_unit,
                    description=description,
                )

            self.result = True
            self.destroy()

        except ValidationError as e:
            error_msg = str(e.errors[0]) if e.errors else str(e)
            messagebox.showerror("Validation Error", error_msg)
        except material_unit_service.MaterialProductNotFoundError:
            messagebox.showerror("Error", "Product not found. Please save the product first.")
        except ServiceError as e:
            handle_error(e, parent=self, operation="Save unit")
        except Exception as e:
            handle_error(e, parent=self, operation="Save unit")

    def _get_material_base_unit_type(self) -> str:
        """
        Get the base_unit_type for the product's parent material.

        Feature 085: T009 - Detect linear product in dialog.

        Returns:
            The base_unit_type string ('linear_cm', 'square_cm', or 'each')
        """
        if not self.product_id:
            return "each"  # Default if no product

        try:
            # Get product first to get its material_id
            product = material_catalog_service.get_product(self.product_id)
            if not product:
                return "each"

            # material_id is a column value, not a relationship - safe to access
            material_id = product.material_id
            if not material_id:
                return "each"

            # Now get the material separately to avoid lazy loading issue
            material = material_catalog_service.get_material(material_id=material_id)
            if material:
                return material.base_unit_type or "each"
        except (ServiceError, Exception) as e:
            print(f"MaterialUnitDialog: Error getting material base unit type: {e}")
            # Fall through to default

        return "each"  # Default if not found

    def _is_linear_product(self) -> bool:
        """
        Check if this is a linear measurement product.

        Feature 085: T009 - Helper for conditional UI.

        Returns:
            True if the product's material has base_unit_type == 'linear_cm'
        """
        return self.base_unit_type == "linear_cm"

    def _update_conversion_preview(self, event=None):
        """
        Update the conversion preview label.

        Feature 085: T012 - Shows live conversion as user types.
        """
        if not self.preview_label or not self.unit_dropdown or not self._unit_code_map:
            return

        try:
            qty_str = self.qty_entry.get().strip() if self.qty_entry else ""
            if not qty_str:
                self.preview_label.configure(text="")
                return

            qty = float(qty_str)
            if qty <= 0:
                self.preview_label.configure(text="")
                return

            selected_display = self.unit_dropdown.get()
            unit_code = self._unit_code_map.get(selected_display, "cm")
            result_cm = convert_to_cm(qty, unit_code)
            self.preview_label.configure(
                text=f"= {result_cm:.2f} cm (stored value)"
            )
        except (ValueError, TypeError):
            self.preview_label.configure(text="")
