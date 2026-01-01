"""
Add/Edit Product Dialog for the Product Catalog.

Provides a modal dialog for:
- Adding new products with ingredient association
- Editing existing product attributes
- Selecting preferred supplier
- Hierarchical ingredient selection (Category -> Subcategory -> Ingredient)

Feature 031: Ingredient Hierarchy - Cascading dropdown selection
"""

import customtkinter as ctk
from tkinter import messagebox
from typing import Optional, Dict, Any, List

from src.services import (
    product_catalog_service,
    supplier_service,
)
from src.services import ingredient_hierarchy_service
from src.utils.constants import PACKAGE_TYPES, MEASUREMENT_UNITS


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

        # Data stores - Feature 031: Hierarchical ingredient selection
        self.categories: List[Dict[str, Any]] = []  # Level 0
        self.categories_map: Dict[str, Dict[str, Any]] = {}
        self.subcategories: List[Dict[str, Any]] = []  # Level 1 (filtered by category)
        self.subcategories_map: Dict[str, Dict[str, Any]] = {}
        self.ingredients: List[Dict[str, Any]] = []  # Level 2 (filtered by subcategory)
        self.ingredients_map: Dict[str, Dict[str, Any]] = {}
        self.selected_ingredient: Optional[Dict[str, Any]] = None

        # Supplier data
        self.suppliers: List[Dict[str, Any]] = []
        self.suppliers_map: Dict[str, Dict[str, Any]] = {}

        # Window configuration
        self.title("Add Product" if not product_id else "Edit Product")
        self.geometry("500x680")  # Extra height for hierarchical dropdowns
        self.resizable(False, False)

        # Hide window while building UI
        self.withdraw()

        # Make dialog modal - set transient first
        self.transient(parent)

        # Load reference data
        if not self._load_data():
            return  # Dialog destroyed due to error

        # Setup UI
        try:
            self._setup_ui()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to setup UI: {str(e)}", parent=parent)
            self.destroy()
            return

        # Load product data if editing
        if product_id:
            try:
                self._load_product()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load product: {str(e)}", parent=self)
                # Don't destroy - let user close manually or try again

        # Center on parent (after UI is built so size is known)
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        # Now show the fully-built dialog
        self.deiconify()
        self.update()
        try:
            self.wait_visibility()
            self.grab_set()
        except Exception:
            # Window may have been closed before becoming visible
            if not self.winfo_exists():
                return
        self.lift()
        self.focus_force()

    def _load_data(self) -> bool:
        """Load categories and suppliers for dropdowns.

        Returns:
            True if data loaded successfully, False if error occurred
        """
        try:
            # Feature 031: Load root categories (level 0)
            self.categories = ingredient_hierarchy_service.get_root_ingredients()
            # Note: to_dict() returns "display_name", not "name"
            self.categories_map = {cat["display_name"]: cat for cat in self.categories}

            # Load active suppliers
            self.suppliers = supplier_service.get_active_suppliers()
            self.suppliers_map = {sup["name"]: sup for sup in self.suppliers}

            return True

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to load reference data: {str(e)}",
                parent=self,
            )
            self.destroy()
            return False

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
        title_label.grid(row=row, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="w")
        row += 1

        # Product Name (required)
        name_label = ctk.CTkLabel(self, text="Product Name *")
        name_label.grid(row=row, column=0, padx=(20, 10), pady=5, sticky="w")

        self.name_var = ctk.StringVar()
        self.name_entry = ctk.CTkEntry(
            self,
            textvariable=self.name_var,
            width=280,
            placeholder_text="e.g., All-Purpose Flour 25lb",
        )
        self.name_entry.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="w")
        row += 1

        # Brand (optional)
        brand_label = ctk.CTkLabel(self, text="Brand")
        brand_label.grid(row=row, column=0, padx=(20, 10), pady=5, sticky="w")

        self.brand_var = ctk.StringVar()
        self.brand_entry = ctk.CTkEntry(
            self,
            textvariable=self.brand_var,
            width=280,
            placeholder_text="e.g., King Arthur",
        )
        self.brand_entry.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="w")
        row += 1

        # Package Type (optional)
        type_label = ctk.CTkLabel(self, text="Package Type")
        type_label.grid(row=row, column=0, padx=(20, 10), pady=5, sticky="w")

        self.package_type_var = ctk.StringVar(value="")
        package_type_values = [""] + PACKAGE_TYPES  # Empty option for optional field
        self.package_type_dropdown = ctk.CTkOptionMenu(
            self,
            variable=self.package_type_var,
            values=package_type_values,
            width=280,
        )
        self.package_type_dropdown.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="w")
        row += 1

        # Package Quantity (required) - comes first for natural reading ("24 oz")
        qty_label = ctk.CTkLabel(self, text="Package Quantity *")
        qty_label.grid(row=row, column=0, padx=(20, 10), pady=5, sticky="w")

        self.quantity_var = ctk.StringVar()
        self.quantity_entry = ctk.CTkEntry(
            self,
            textvariable=self.quantity_var,
            width=280,
            placeholder_text="e.g., 25 (for 25 lb bag)",
        )
        self.quantity_entry.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="w")
        row += 1

        # Package Unit (required) - comes after quantity for natural reading
        unit_label = ctk.CTkLabel(self, text="Package Unit *")
        unit_label.grid(row=row, column=0, padx=(20, 10), pady=5, sticky="w")

        self.unit_var = ctk.StringVar(value="")
        self.unit_dropdown = ctk.CTkOptionMenu(
            self,
            variable=self.unit_var,
            values=MEASUREMENT_UNITS,
            width=280,
        )
        self.unit_dropdown.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="w")
        row += 1

        # Feature 031: Hierarchical ingredient selection
        # Category dropdown (Level 0)
        cat_label = ctk.CTkLabel(self, text="Category *")
        cat_label.grid(row=row, column=0, padx=(20, 10), pady=5, sticky="w")

        self.category_var = ctk.StringVar()
        category_names = sorted(self.categories_map.keys())
        self.category_dropdown = ctk.CTkComboBox(
            self,
            variable=self.category_var,
            values=category_names if category_names else ["No categories"],
            command=self._on_category_change,
            width=280,
        )
        self.category_dropdown.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="w")
        if not category_names:
            self.category_dropdown.configure(state="disabled")
        row += 1

        # Subcategory dropdown (Level 1)
        subcat_label = ctk.CTkLabel(self, text="Subcategory *")
        subcat_label.grid(row=row, column=0, padx=(20, 10), pady=5, sticky="w")

        self.subcategory_var = ctk.StringVar()
        self.subcategory_dropdown = ctk.CTkComboBox(
            self,
            variable=self.subcategory_var,
            values=["(Select category first)"],
            command=self._on_subcategory_change,
            width=280,
            state="disabled",
        )
        self.subcategory_dropdown.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="w")
        row += 1

        # Ingredient dropdown (Level 2 - leaves)
        ing_label = ctk.CTkLabel(self, text="Ingredient *")
        ing_label.grid(row=row, column=0, padx=(20, 10), pady=5, sticky="w")

        self.ingredient_var = ctk.StringVar()
        self.ingredient_dropdown = ctk.CTkComboBox(
            self,
            variable=self.ingredient_var,
            values=["(Select subcategory first)"],
            command=self._on_ingredient_change,
            width=280,
            state="disabled",
        )
        self.ingredient_dropdown.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="w")
        row += 1

        # Preferred Supplier (optional)
        sup_label = ctk.CTkLabel(self, text="Preferred Supplier")
        sup_label.grid(row=row, column=0, padx=(20, 10), pady=5, sticky="w")

        self.supplier_var = ctk.StringVar(value="None")
        supplier_names = ["None"] + sorted(self.suppliers_map.keys())
        self.supplier_dropdown = ctk.CTkComboBox(
            self,
            variable=self.supplier_var,
            values=supplier_names,
            width=280,
        )
        self.supplier_dropdown.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="w")
        row += 1

        # GTIN (optional)
        gtin_label = ctk.CTkLabel(self, text="GTIN")
        gtin_label.grid(row=row, column=0, padx=(20, 10), pady=5, sticky="w")

        self.gtin_var = ctk.StringVar()
        self.gtin_entry = ctk.CTkEntry(
            self,
            textvariable=self.gtin_var,
            width=280,
            placeholder_text="e.g., 071012010615",
        )
        self.gtin_entry.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="w")
        row += 1

        # UPC (optional)
        upc_label = ctk.CTkLabel(self, text="UPC")
        upc_label.grid(row=row, column=0, padx=(20, 10), pady=5, sticky="w")

        self.upc_var = ctk.StringVar()
        self.upc_entry = ctk.CTkEntry(
            self,
            textvariable=self.upc_var,
            width=280,
            placeholder_text="e.g., 012345678901",
        )
        self.upc_entry.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="w")
        row += 1

        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=row, column=0, columnspan=2, padx=20, pady=20, sticky="ew")
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

    def _on_category_change(self, choice: str):
        """Handle category selection - populate subcategory dropdown."""
        # Reset downstream selections
        self.subcategory_var.set("")
        self.ingredient_var.set("")
        self.subcategories_map.clear()
        self.ingredients_map.clear()
        self.selected_ingredient = None

        if choice not in self.categories_map:
            self.subcategory_dropdown.configure(values=["(Select category first)"], state="disabled")
            self.ingredient_dropdown.configure(values=["(Select subcategory first)"], state="disabled")
            return

        # Get subcategories (children of selected category)
        category = self.categories_map[choice]
        try:
            self.subcategories = ingredient_hierarchy_service.get_children(category["id"])
            self.subcategories_map = {sub["display_name"]: sub for sub in self.subcategories}

            if self.subcategories:
                subcat_names = sorted(self.subcategories_map.keys())
                self.subcategory_dropdown.configure(values=subcat_names, state="normal")
            else:
                self.subcategory_dropdown.configure(values=["(No subcategories)"], state="disabled")

            self.ingredient_dropdown.configure(values=["(Select subcategory first)"], state="disabled")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load subcategories: {e}", parent=self)

    def _on_subcategory_change(self, choice: str):
        """Handle subcategory selection - populate ingredient dropdown."""
        # Reset ingredient selection
        self.ingredient_var.set("")
        self.ingredients_map.clear()
        self.selected_ingredient = None

        if choice not in self.subcategories_map:
            self.ingredient_dropdown.configure(values=["(Select subcategory first)"], state="disabled")
            return

        # Get leaf ingredients (children of selected subcategory)
        subcategory = self.subcategories_map[choice]
        try:
            self.ingredients = ingredient_hierarchy_service.get_children(subcategory["id"])
            self.ingredients_map = {ing["display_name"]: ing for ing in self.ingredients}

            if self.ingredients:
                ing_names = sorted(self.ingredients_map.keys())
                self.ingredient_dropdown.configure(values=ing_names, state="normal")
            else:
                self.ingredient_dropdown.configure(values=["(No ingredients)"], state="disabled")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load ingredients: {e}", parent=self)

    def _on_ingredient_change(self, choice: str):
        """Handle ingredient selection - store selected ingredient."""
        if choice in self.ingredients_map:
            self.selected_ingredient = self.ingredients_map[choice]
        else:
            self.selected_ingredient = None

    def _set_ingredient_by_id(self, ingredient_id: int):
        """
        Set all three dropdowns based on an ingredient ID.

        Used when editing a product to populate the hierarchy from the saved ingredient.
        Walks up the ancestor chain to find category and subcategory.
        """
        try:
            # Get the ingredient and its ancestors
            ingredient = ingredient_hierarchy_service.get_ingredient_by_id(ingredient_id)
            if not ingredient:
                print(f"Warning: Ingredient {ingredient_id} not found")
                return

            ancestors = ingredient_hierarchy_service.get_ancestors(ingredient_id)

            # Ancestors are ordered from immediate parent to root
            # For a leaf ingredient: [subcategory, category]
            if len(ancestors) >= 2:
                subcategory = ancestors[0]  # Immediate parent (level 1)
                category = ancestors[1]     # Grandparent (level 0)
            elif len(ancestors) == 1:
                subcategory = ancestors[0]
                category = None
            else:
                subcategory = None
                category = None

            # Set category dropdown
            if category and category["display_name"] in self.categories_map:
                self.category_var.set(category["display_name"])
                self._on_category_change(category["display_name"])

                # Set subcategory dropdown (after category change populates subcategories_map)
                if subcategory and subcategory["display_name"] in self.subcategories_map:
                    self.subcategory_var.set(subcategory["display_name"])
                    self._on_subcategory_change(subcategory["display_name"])

                    # Set ingredient dropdown (after subcategory change populates ingredients_map)
                    if ingredient["display_name"] in self.ingredients_map:
                        self.ingredient_var.set(ingredient["display_name"])
                        self._on_ingredient_change(ingredient["display_name"])
                    else:
                        print(f"Warning: Ingredient '{ingredient['display_name']}' not in ingredients_map")
                else:
                    print(f"Warning: Subcategory '{subcategory['display_name'] if subcategory else 'None'}' not in subcategories_map")
            else:
                print(f"Warning: Category '{category['display_name'] if category else 'None'}' not in categories_map")

        except Exception as e:
            # Log but don't fail - user can still select manually
            import traceback
            print(f"Warning: Could not set ingredient hierarchy: {e}")
            traceback.print_exc()

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

        # Ingredient required (must complete all three dropdowns)
        if not self.selected_ingredient:
            if not self.category_var.get() or self.category_var.get() not in self.categories_map:
                errors.append("Please select a category")
            elif not self.subcategory_var.get() or self.subcategory_var.get() not in self.subcategories_map:
                errors.append("Please select a subcategory")
            else:
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

        # Get ingredient (already validated in _validate)
        ingredient = self.selected_ingredient

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
                    package_type=self.package_type_var.get() or None,
                    package_unit=self.unit_var.get(),
                    package_unit_quantity=float(self.quantity_var.get()),
                    ingredient_id=ingredient["id"],
                    preferred_supplier_id=supplier_id,
                    gtin=self.gtin_var.get().strip() or None,
                    upc_code=self.upc_var.get().strip() or None,
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
                    package_type=self.package_type_var.get() or None,
                    package_unit=self.unit_var.get(),
                    package_unit_quantity=float(self.quantity_var.get()),
                    preferred_supplier_id=supplier_id,
                    brand=self.brand_var.get().strip() or None,
                    gtin=self.gtin_var.get().strip() or None,
                    upc_code=self.upc_var.get().strip() or None,
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
            self.package_type_var.set(product.get("package_type", "") or "")
            self.unit_var.set(product.get("package_unit", "") or "")

            package_qty = product.get("package_unit_quantity") or product.get("package_quantity")
            if package_qty:
                self.quantity_var.set(str(package_qty))

            # GTIN and UPC
            self.gtin_var.set(product.get("gtin", "") or "")
            self.upc_var.set(product.get("upc_code", "") or "")

            # Feature 031: Find and set hierarchical ingredient selection
            ingredient_id = product.get("ingredient_id")
            if ingredient_id:
                self._set_ingredient_by_id(ingredient_id)

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
