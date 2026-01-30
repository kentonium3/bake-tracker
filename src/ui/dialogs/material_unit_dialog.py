"""
Dialog for creating/editing a MaterialUnit.

Feature 084: MaterialUnit Schema Refactor - WP07.
MaterialUnits are now children of MaterialProduct, not Material.
"""

import customtkinter as ctk
from tkinter import messagebox
from typing import Optional

from src.services import material_unit_service
from src.services.exceptions import ValidationError


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

        # Modal pattern - hide while building
        self.withdraw()

        self.parent_window = parent
        self.unit_id = unit_id
        self.product_id = product_id
        self.unit_data = unit_data
        self.result = None  # Will be True if saved successfully

        # Configure window
        self.title("Edit Unit" if unit_id else "Add Unit")
        self.geometry("400x280")
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

        # Show dialog after UI is complete
        self.deiconify()
        self.update()
        try:
            self.wait_visibility()
            self.grab_set()
        except Exception:
            if not self.winfo_exists():
                return
        self.lift()
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
            ctk.CTkLabel(
                qty_frame,
                text=f"{qty_value:.4f}",
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
            self.qty_entry = ctk.CTkEntry(
                form_frame, placeholder_text="e.g., 0.1524 (6 inches in meters)"
            )
            self.qty_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
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
                    quantity_per_unit = float(qty_str)
                    if quantity_per_unit <= 0:
                        raise ValueError("Must be positive")
                except ValueError:
                    messagebox.showerror(
                        "Validation Error", "Quantity per Unit must be a positive number."
                    )
                    return

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
            error_msg = str(e.messages[0]) if e.messages else str(e)
            messagebox.showerror("Validation Error", error_msg)
        except material_unit_service.MaterialProductNotFoundError:
            messagebox.showerror("Error", "Product not found. Please save the product first.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save unit: {e}")
