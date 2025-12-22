"""
Add/Edit Product Dialog for the Product Catalog.

Provides a modal dialog for:
- Adding new products with ingredient association
- Editing existing product attributes
- Selecting preferred supplier
- Category auto-population from ingredient
"""

import customtkinter as ctk
from tkinter import messagebox
from typing import Optional, Dict, Any, List

from src.services import (
    product_catalog_service,
    supplier_service,
    ingredient_service,
)


class AddProductDialog(ctk.CTkToplevel):
    """
    Dialog for adding or editing products.

    Supports two modes:
    - Add mode: Create new product (product_id=None)
    - Edit mode: Update existing product (product_id provided)

    Form fields:
    - Product Name (required)
    - Brand (optional)
    - Package Unit (required, e.g., lb, oz, each)
    - Package Quantity (required, e.g., 5 for "5 lb bag")
    - Ingredient (required, dropdown)
    - Category (read-only, auto-populated from ingredient)
    - Preferred Supplier (optional, dropdown)
    """

    def __init__(
        self,
        parent,
        product_id: Optional[int] = None,
        **kwargs,
    ):
        """
        Initialize the dialog.

        Args:
            parent: Parent widget
            product_id: Product ID for edit mode, None for add mode
        """
        super().__init__(parent, **kwargs)

        self.product_id = product_id
        self.result: Optional[bool] = None

        # Data stores
        self.ingredients: List[Dict[str, Any]] = []
        self.ingredients_map: Dict[str, Dict[str, Any]] = {}
        self.suppliers: List[Dict[str, Any]] = []
        self.suppliers_map: Dict[str, Dict[str, Any]] = {}

        # Window configuration
        self.title("Add Product" if not product_id else "Edit Product")
        self.geometry("500x550")
        self.resizable(False, False)

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        # Load reference data
        self._load_data()

        # Setup UI
        self._setup_ui()

        # Load product data if editing
        if product_id:
            self._load_product()

    def _load_data(self):
        """Load ingredients and suppliers for dropdowns."""
        try:
            # Load ingredients
            self.ingredients = ingredient_service.get_all_ingredients()
            self.ingredients_map = {ing["name"]: ing for ing in self.ingredients}

            # Load active suppliers
            self.suppliers = supplier_service.get_active_suppliers()
            self.suppliers_map = {sup["name"]: sup for sup in self.suppliers}

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to load reference data: {str(e)}",
                parent=self,
            )
            self.destroy()

    def _setup_ui(self):
        """Create form fields and buttons."""
        # Configure grid
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        row = 0

        # Title
        title_label = ctk.CTkLabel(
            self,
            text="Add Product" if not self.product_id else "Edit Product",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title_label.grid(row=row, column=0, columnspan=2, padx=20, pady=(20, 15), sticky="w")
        row += 1

        # Product Name (required)
        name_label = ctk.CTkLabel(self, text="Product Name *")
        name_label.grid(row=row, column=0, padx=(20, 10), pady=10, sticky="w")

        self.name_var = ctk.StringVar()
        self.name_entry = ctk.CTkEntry(
            self,
            textvariable=self.name_var,
            width=280,
            placeholder_text="e.g., All-Purpose Flour 25lb",
        )
        self.name_entry.grid(row=row, column=1, padx=(0, 20), pady=10, sticky="w")
        row += 1

        # Brand (optional)
        brand_label = ctk.CTkLabel(self, text="Brand")
        brand_label.grid(row=row, column=0, padx=(20, 10), pady=10, sticky="w")

        self.brand_var = ctk.StringVar()
        self.brand_entry = ctk.CTkEntry(
            self,
            textvariable=self.brand_var,
            width=280,
            placeholder_text="e.g., King Arthur",
        )
        self.brand_entry.grid(row=row, column=1, padx=(0, 20), pady=10, sticky="w")
        row += 1

        # Package Unit (required)
        unit_label = ctk.CTkLabel(self, text="Package Unit *")
        unit_label.grid(row=row, column=0, padx=(20, 10), pady=10, sticky="w")

        self.unit_var = ctk.StringVar()
        self.unit_entry = ctk.CTkEntry(
            self,
            textvariable=self.unit_var,
            width=280,
            placeholder_text="e.g., lb, oz, each, bag",
        )
        self.unit_entry.grid(row=row, column=1, padx=(0, 20), pady=10, sticky="w")
        row += 1

        # Package Quantity (required)
        qty_label = ctk.CTkLabel(self, text="Package Quantity *")
        qty_label.grid(row=row, column=0, padx=(20, 10), pady=10, sticky="w")

        self.quantity_var = ctk.StringVar()
        self.quantity_entry = ctk.CTkEntry(
            self,
            textvariable=self.quantity_var,
            width=280,
            placeholder_text="e.g., 25 (for 25 lb bag)",
        )
        self.quantity_entry.grid(row=row, column=1, padx=(0, 20), pady=10, sticky="w")
        row += 1

        # Ingredient (required)
        ing_label = ctk.CTkLabel(self, text="Ingredient *")
        ing_label.grid(row=row, column=0, padx=(20, 10), pady=10, sticky="w")

        self.ingredient_var = ctk.StringVar()
        ingredient_names = sorted(self.ingredients_map.keys())
        self.ingredient_dropdown = ctk.CTkComboBox(
            self,
            variable=self.ingredient_var,
            values=ingredient_names if ingredient_names else ["No ingredients available"],
            command=self._on_ingredient_change,
            width=280,
        )
        self.ingredient_dropdown.grid(row=row, column=1, padx=(0, 20), pady=10, sticky="w")
        if not ingredient_names:
            self.ingredient_dropdown.configure(state="disabled")
        row += 1

        # Category (read-only, auto-populated)
        cat_label = ctk.CTkLabel(self, text="Category")
        cat_label.grid(row=row, column=0, padx=(20, 10), pady=10, sticky="w")

        self.category_var = ctk.StringVar(value="(Select ingredient)")
        self.category_label = ctk.CTkLabel(
            self,
            textvariable=self.category_var,
            width=280,
            anchor="w",
        )
        self.category_label.grid(row=row, column=1, padx=(0, 20), pady=10, sticky="w")
        row += 1

        # Preferred Supplier (optional)
        sup_label = ctk.CTkLabel(self, text="Preferred Supplier")
        sup_label.grid(row=row, column=0, padx=(20, 10), pady=10, sticky="w")

        self.supplier_var = ctk.StringVar(value="None")
        supplier_names = ["None"] + sorted(self.suppliers_map.keys())
        self.supplier_dropdown = ctk.CTkComboBox(
            self,
            variable=self.supplier_var,
            values=supplier_names,
            width=280,
        )
        self.supplier_dropdown.grid(row=row, column=1, padx=(0, 20), pady=10, sticky="w")
        row += 1

        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=row, column=0, columnspan=2, padx=20, pady=30, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            width=120,
        )
        cancel_btn.grid(row=0, column=0, padx=10, pady=10, sticky="e")

        save_btn = ctk.CTkButton(
            button_frame,
            text="Save",
            command=self._on_save,
            width=120,
        )
        save_btn.grid(row=0, column=1, padx=10, pady=10, sticky="w")

    def _on_ingredient_change(self, choice: str):
        """Handle ingredient selection - update category display."""
        if choice in self.ingredients_map:
            ingredient = self.ingredients_map[choice]
            category = ingredient.get("category", "Unknown")
            self.category_var.set(category if category else "Uncategorized")
        else:
            self.category_var.set("(Select ingredient)")

    def _validate(self) -> bool:
        """Validate form fields before save."""
        errors = []

        # Product name required
        if not self.name_var.get().strip():
            errors.append("Product name is required")

        # Package unit required
        if not self.unit_var.get().strip():
            errors.append("Package unit is required")

        # Package quantity required and must be positive number
        qty_str = self.quantity_var.get().strip()
        if not qty_str:
            errors.append("Package quantity is required")
        else:
            try:
                qty = float(qty_str)
                if qty <= 0:
                    errors.append("Package quantity must be a positive number")
            except ValueError:
                errors.append("Package quantity must be a valid number")

        # Ingredient required
        ingredient_name = self.ingredient_var.get()
        if not ingredient_name or ingredient_name not in self.ingredients_map:
            errors.append("Please select an ingredient")

        if errors:
            messagebox.showerror(
                "Validation Error",
                "\n".join(errors),
                parent=self,
            )
            return False

        return True

    def _on_save(self):
        """Handle save button click."""
        if not self._validate():
            return

        # Get ingredient
        ingredient = self.ingredients_map[self.ingredient_var.get()]

        # Get supplier (optional)
        supplier_id = None
        supplier_name = self.supplier_var.get()
        if supplier_name != "None" and supplier_name in self.suppliers_map:
            supplier_id = self.suppliers_map[supplier_name]["id"]

        try:
            if self.product_id:
                # Edit mode - update existing product
                product_catalog_service.update_product(
                    self.product_id,
                    product_name=self.name_var.get().strip(),
                    brand=self.brand_var.get().strip() or None,
                    package_unit=self.unit_var.get().strip(),
                    package_quantity=float(self.quantity_var.get()),
                    ingredient_id=ingredient["id"],
                    preferred_supplier_id=supplier_id,
                )
                messagebox.showinfo(
                    "Success",
                    "Product updated successfully",
                    parent=self,
                )
            else:
                # Add mode - create new product
                product_catalog_service.create_product(
                    product_name=self.name_var.get().strip(),
                    ingredient_id=ingredient["id"],
                    package_unit=self.unit_var.get().strip(),
                    package_quantity=float(self.quantity_var.get()),
                    preferred_supplier_id=supplier_id,
                    brand=self.brand_var.get().strip() or None,
                )
                messagebox.showinfo(
                    "Success",
                    "Product created successfully",
                    parent=self,
                )

            self.result = True
            self.destroy()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to save product: {str(e)}",
                parent=self,
            )

    def _on_cancel(self):
        """Handle cancel button click."""
        self.result = None
        self.destroy()

    def _load_product(self):
        """Load existing product data for edit mode."""
        try:
            product = product_catalog_service.get_product_with_last_price(self.product_id)
            if not product:
                messagebox.showerror(
                    "Error",
                    "Product not found",
                    parent=self,
                )
                self.destroy()
                return

            # Populate form fields
            self.name_var.set(product.get("product_name", "") or "")
            self.brand_var.set(product.get("brand", "") or "")
            self.unit_var.set(product.get("package_unit", "") or "")

            package_qty = product.get("package_unit_quantity") or product.get("package_quantity")
            if package_qty:
                self.quantity_var.set(str(package_qty))

            # Find and set ingredient
            ingredient_id = product.get("ingredient_id")
            if ingredient_id:
                for name, ing in self.ingredients_map.items():
                    if ing["id"] == ingredient_id:
                        self.ingredient_var.set(name)
                        self._on_ingredient_change(name)
                        break

            # Find and set supplier
            supplier_id = product.get("preferred_supplier_id")
            if supplier_id:
                for name, sup in self.suppliers_map.items():
                    if sup["id"] == supplier_id:
                        self.supplier_var.set(name)
                        break

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to load product: {str(e)}",
                parent=self,
            )
            self.destroy()
