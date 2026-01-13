"""
Materials tab for the Seasonal Baking Tracker.

Provides CRUD interface for managing materials catalog (ribbons, boxes, bags, tissue)
using the 3-level mandatory hierarchy: Category > Subcategory > Material > Product.

Feature 048: Rebuilt Materials UI with 3 sub-tabs matching Ingredients tab pattern:
- Materials Catalog: View/edit material definitions with L0/L1/Name columns
- Material Products: View/edit products linked to materials
- Material Units: View/edit units with computed inventory and cost

Part of Feature 047: Materials Management System.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import date
import unicodedata

from src.services import (
    material_catalog_service,
    material_purchase_service,
    material_unit_service,
    supplier_service,
)
from src.services.exceptions import ValidationError, DatabaseError
from src.utils.constants import PADDING_MEDIUM, PADDING_LARGE


def normalize_for_search(text: str) -> str:
    """
    Normalize text for search by removing diacriticals and converting to lowercase.

    Examples:
        "Creme Brulee" -> "creme brulee"
        "Cafe" -> "cafe"
    """
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = nfkd.encode("ASCII", "ignore").decode("ASCII")
    return ascii_text.lower()


def _get_value(obj: Any, key: str):
    """Safely get attribute or dict value for service return objects/dicts."""
    if hasattr(obj, key):
        return getattr(obj, key)
    if isinstance(obj, dict):
        return obj.get(key)
    return None


class MaterialsTab(ctk.CTkFrame):
    """
    Materials catalog management tab with 3 sub-tabs.

    Sub-tabs:
    - Materials Catalog: View/manage material definitions (L0/L1/Name/Unit)
    - Material Products: View/manage products linked to materials
    - Material Units: View/manage units with inventory and cost

    Pattern matches IngredientsTab for consistency.
    """

    def __init__(self, parent):
        """Initialize the materials tab."""
        super().__init__(parent)

        self._data_loaded = False

        # Configure grid - single column layout with title and tabview
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Title
        self.grid_rowconfigure(1, weight=1)  # Tabview

        # Create UI components
        self._create_title()
        self._create_tabview()

        # Grid the frame
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def _create_title(self):
        """Create the title label."""
        title_label = ctk.CTkLabel(
            self,
            text="Materials Catalog",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title_label.grid(
            row=0, column=0, sticky="w",
            padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_MEDIUM)
        )

    def _create_tabview(self):
        """Create the 3-tab container for Materials, Products, and Units."""
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=PADDING_LARGE, pady=PADDING_MEDIUM)

        # Add tabs
        self.tabview.add("Materials Catalog")
        self.tabview.add("Material Products")
        self.tabview.add("Material Units")

        # Get tab frames
        catalog_tab = self.tabview.tab("Materials Catalog")
        products_tab = self.tabview.tab("Material Products")
        units_tab = self.tabview.tab("Material Units")

        # Configure tab frames to expand
        catalog_tab.grid_columnconfigure(0, weight=1)
        catalog_tab.grid_rowconfigure(0, weight=1)
        products_tab.grid_columnconfigure(0, weight=1)
        products_tab.grid_rowconfigure(0, weight=1)
        units_tab.grid_columnconfigure(0, weight=1)
        units_tab.grid_rowconfigure(0, weight=1)

        # Create inner tab classes
        self.catalog_tab = MaterialsCatalogTab(catalog_tab, self)
        self.products_tab = MaterialProductsTab(products_tab, self)
        self.units_tab = MaterialUnitsTab(units_tab, self)

    def refresh(self):
        """Refresh all sub-tabs."""
        self._data_loaded = True
        self.catalog_tab.refresh()
        self.products_tab.refresh()
        self.units_tab.refresh()


# Valid base unit types for materials
MATERIAL_BASE_UNITS = ["each", "linear_inches", "square_inches"]


class MaterialFormDialog(ctk.CTkToplevel):
    """
    Dialog for creating or editing a material.

    Feature 048: Modal dialog matching IngredientFormDialog pattern.
    """

    def __init__(
        self,
        parent,
        material: Optional[Dict[str, Any]] = None,
        title: str = "Add Material",
    ):
        """
        Initialize the material form dialog.

        Args:
            parent: Parent window
            material: Existing material dict to edit (None for new)
            title: Dialog title
        """
        super().__init__(parent)

        # Modal pattern - hide while building
        self.withdraw()

        self.parent_tab = parent
        self.material = material
        self.result: Optional[Dict[str, Any]] = None
        self.deleted = False

        # Configure window
        self.title(title)
        self.geometry("500x400")
        self.resizable(False, False)

        # Center on parent
        self.transient(parent)

        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Create form
        self._create_form()
        self._create_buttons()

        # Populate if editing
        if self.material:
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

        # Name field - always editable (spec User Story 2, Acceptance 4)
        ctk.CTkLabel(form_frame, text="Name*:").grid(
            row=row, column=0, sticky="w", padx=10, pady=(10, 5)
        )
        self.name_entry = ctk.CTkEntry(
            form_frame, placeholder_text="e.g., Red Satin Ribbon"
        )
        self.name_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=(10, 5))
        row += 1

        # Category (L0) dropdown
        ctk.CTkLabel(form_frame, text="Category*:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self._l0_options = self._build_l0_options()
        self.l0_var = ctk.StringVar(value="(Select category)")
        self.l0_dropdown = ctk.CTkComboBox(
            form_frame,
            values=["(Select category)"] + list(self._l0_options.keys()),
            variable=self.l0_var,
            command=self._on_l0_change,
            width=250,
        )
        self.l0_dropdown.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        row += 1

        # Subcategory (L1) dropdown
        ctk.CTkLabel(form_frame, text="Subcategory*:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self._l1_options: Dict[str, int] = {}
        self.l1_var = ctk.StringVar(value="(Select category first)")
        self.l1_dropdown = ctk.CTkComboBox(
            form_frame,
            values=["(Select category first)"],
            variable=self.l1_var,
            width=250,
            state="disabled",
        )
        self.l1_dropdown.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        row += 1

        # Computed level display (FR-016)
        ctk.CTkLabel(form_frame, text="Level:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.level_label = ctk.CTkLabel(
            form_frame, text="L2 - Material", anchor="w"
        )
        self.level_label.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        row += 1

        # Base Unit dropdown - disabled in edit mode (cannot change after creation per service)
        if self.material:
            # Edit mode - show as read-only with note
            ctk.CTkLabel(form_frame, text="Default Unit:").grid(
                row=row, column=0, sticky="w", padx=10, pady=5
            )
            self.base_unit_var = ctk.StringVar(value=self.material.get("base_unit", "each"))
            unit_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
            unit_frame.grid(row=row, column=1, sticky="w", padx=10, pady=5)
            ctk.CTkLabel(
                unit_frame,
                text=self.material.get("base_unit", "each"),
                font=ctk.CTkFont(weight="bold"),
            ).pack(side="left")
            ctk.CTkLabel(
                unit_frame,
                text="  (cannot change after creation)",
                text_color="gray",
            ).pack(side="left")
            self.base_unit_dropdown = None
        else:
            # Add mode - editable dropdown
            ctk.CTkLabel(form_frame, text="Default Unit*:").grid(
                row=row, column=0, sticky="w", padx=10, pady=5
            )
            self.base_unit_var = ctk.StringVar(value="each")
            self.base_unit_dropdown = ctk.CTkOptionMenu(
                form_frame,
                values=MATERIAL_BASE_UNITS,
                variable=self.base_unit_var,
                width=150,
            )
            self.base_unit_dropdown.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        row += 1

        # Notes field
        ctk.CTkLabel(form_frame, text="Notes:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.notes_entry = ctk.CTkEntry(
            form_frame, placeholder_text="Optional notes"
        )
        self.notes_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        row += 1

    def _create_buttons(self):
        """Create dialog buttons."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))

        # Delete button (only in edit mode) - left side, red
        if self.material:
            delete_button = ctk.CTkButton(
                button_frame,
                text="Delete",
                command=self._delete,
                width=80,
                fg_color="#dc3545",
                hover_color="#c82333",
            )
            delete_button.pack(side="left", padx=5)

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
            command=self._save,
            width=80,
        )
        save_button.pack(side="right", padx=5)

    def _build_l0_options(self) -> Dict[str, int]:
        """Build L0 category options from database."""
        options = {}
        try:
            categories = material_catalog_service.list_categories()
            for cat in categories:
                name = _get_value(cat, "name")
                cat_id = _get_value(cat, "id")
                if name is not None and cat_id is not None:
                    options[name] = cat_id
        except Exception as e:
            print(f"Error loading categories: {e}")
        return options

    def _on_l0_change(self, value: str):
        """Handle L0 category selection change - cascade to L1."""
        if value == "(Select category)" or value not in self._l0_options:
            self.l1_dropdown.configure(
                values=["(Select category first)"],
                state="disabled"
            )
            self.l1_var.set("(Select category first)")
            self._l1_options = {}
            return

        # Get subcategories for selected category
        category_id = self._l0_options[value]
        try:
            subcategories = material_catalog_service.list_subcategories(category_id)
            self._l1_options = {}
            for sub in subcategories:
                name = _get_value(sub, "name")
                sub_id = _get_value(sub, "id")
                if name is not None and sub_id is not None:
                    self._l1_options[name] = sub_id

            if self._l1_options:
                self.l1_dropdown.configure(
                    values=list(self._l1_options.keys()),
                    state="normal"
                )
                self.l1_var.set(list(self._l1_options.keys())[0])
            else:
                self.l1_dropdown.configure(
                    values=["(No subcategories)"],
                    state="disabled"
                )
                self.l1_var.set("(No subcategories)")
        except Exception as e:
            print(f"Error loading subcategories: {e}")
            self.l1_dropdown.configure(
                values=["(Error loading)"],
                state="disabled"
            )
            self.l1_var.set("(Error loading)")

    def _populate_form(self):
        """Pre-fill form when editing existing material."""
        if not self.material:
            return

        # Set name
        name = self.material.get("name", "")
        if name:
            self.name_entry.insert(0, name)

        # Set L0 category
        l0_name = self.material.get("l0_name", "")
        if l0_name and l0_name in self._l0_options:
            self.l0_var.set(l0_name)
            self._on_l0_change(l0_name)

            # Set L1 subcategory after cascade
            l1_name = self.material.get("l1_name", "")
            if l1_name and l1_name in self._l1_options:
                self.l1_var.set(l1_name)

        # Base unit is already set in _create_form for edit mode (read-only display)

        # Set notes
        notes = self.material.get("notes", "")
        if notes:
            self.notes_entry.insert(0, notes)

    def _save(self):
        """Validate and save the material."""
        # Get name from entry (always editable now)
        name = self.name_entry.get().strip()

        # Validate name
        if not name:
            messagebox.showerror("Error", "Name is required.")
            return

        # Get subcategory
        l1_selection = self.l1_var.get()
        if l1_selection not in self._l1_options:
            messagebox.showerror("Error", "Please select a valid subcategory.")
            return

        subcategory_id = self._l1_options[l1_selection]
        base_unit = self.base_unit_var.get()
        notes = self.notes_entry.get().strip() or None

        # Build result
        self.result = {
            "name": name,
            "subcategory_id": subcategory_id,
            "base_unit_type": base_unit,
            "notes": notes,
        }

        # Include ID if editing
        if self.material:
            self.result["id"] = self.material.get("id")

        self.destroy()

    def _delete(self):
        """Delete the material with confirmation."""
        if not self.material:
            return

        name = self.material.get("name", "this material")
        material_id = self.material.get("id")

        if not messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete '{name}'?\n\nThis cannot be undone."
        ):
            return

        try:
            material_catalog_service.delete_material(material_id)
            self.deleted = True
            self.destroy()
        except ValidationError as e:
            messagebox.showerror("Cannot Delete", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete material: {e}")


class MaterialProductFormDialog(ctk.CTkToplevel):
    """
    Dialog for creating or editing a material product.

    Feature 048: Modal dialog matching MaterialFormDialog pattern.
    """

    def __init__(
        self,
        parent,
        product: Optional[Dict[str, Any]] = None,
        title: str = "Add Product",
        material_id: Optional[int] = None,
    ):
        """
        Initialize the product form dialog.

        Args:
            parent: Parent window
            product: Existing product dict to edit (None for new)
            title: Dialog title
            material_id: Pre-select this material (for add from material context)
        """
        super().__init__(parent)

        # Modal pattern - hide while building
        self.withdraw()

        self.parent_tab = parent
        self.product = product
        self.material_id = material_id
        self.result: Optional[Dict[str, Any]] = None

        # Configure window
        self.title(title)
        self.geometry("500x450")
        self.resizable(False, False)

        # Center on parent
        self.transient(parent)

        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Load materials and suppliers for dropdowns
        self._load_dropdown_data()

        # Create form
        self._create_form()
        self._create_buttons()

        # Populate if editing
        if self.product:
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

    def _load_dropdown_data(self):
        """Load materials and suppliers for dropdowns."""
        # Load materials
        self._materials: Dict[str, Dict[str, Any]] = {}
        try:
            categories = material_catalog_service.list_categories()
            for cat in categories:
                cat_id = _get_value(cat, "id")
                subcategories = material_catalog_service.list_subcategories(cat_id)
                for subcat in subcategories:
                    sub_id = _get_value(subcat, "id")
                    mats = material_catalog_service.list_materials(sub_id)
                    for mat in mats:
                        name = _get_value(mat, "name")
                        mat_id = _get_value(mat, "id")
                        base_unit = _get_value(mat, "base_unit_type") or "each"
                        if name is None or mat_id is None:
                            continue
                        self._materials[name] = {
                            "id": mat_id,
                            "base_unit": base_unit,
                        }
        except Exception as e:
            print(f"Error loading materials: {e}")

        # Load suppliers
        self._suppliers: Dict[str, int] = {}
        try:
            suppliers = supplier_service.get_all_suppliers()
            for sup in suppliers:
                # supplier_service may return dicts or ORM objects
                if isinstance(sup, dict):
                    self._suppliers[sup["name"]] = sup["id"]
                else:
                    self._suppliers[sup.name] = sup.id
        except Exception as e:
            print(f"Error loading suppliers: {e}")

    def _create_form(self):
        """Create form fields."""
        form_frame = ctk.CTkFrame(self)
        form_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        form_frame.grid_columnconfigure(1, weight=1)

        row = 0

        # Material dropdown (required)
        ctk.CTkLabel(form_frame, text="Material*:").grid(
            row=row, column=0, sticky="w", padx=10, pady=(10, 5)
        )
        material_names = sorted(self._materials.keys())
        self.material_var = ctk.StringVar(value="(Select material)")

        # Pre-select material if provided
        if self.material_id:
            for name, data in self._materials.items():
                if data["id"] == self.material_id:
                    self.material_var.set(name)
                    break

        self.material_dropdown = ctk.CTkComboBox(
            form_frame,
            values=["(Select material)"] + material_names,
            variable=self.material_var,
            command=self._on_material_change,
            width=280,
        )
        self.material_dropdown.grid(row=row, column=1, sticky="w", padx=10, pady=(10, 5))
        row += 1

        # Product Name (required) - always editable (spec User Story 4, Acceptance 4)
        ctk.CTkLabel(form_frame, text="Name*:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.name_entry = ctk.CTkEntry(
            form_frame, placeholder_text="e.g., Red Satin Ribbon 50yd"
        )
        self.name_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        row += 1

        # Package Quantity (required)
        ctk.CTkLabel(form_frame, text="Package Qty*:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.qty_entry = ctk.CTkEntry(
            form_frame, placeholder_text="e.g., 50"
        )
        self.qty_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        row += 1

        # Package Unit (defaults to material's base_unit)
        ctk.CTkLabel(form_frame, text="Package Unit:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.unit_entry = ctk.CTkEntry(
            form_frame, placeholder_text="e.g., yards"
        )
        self.unit_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        row += 1

        # Supplier dropdown (optional)
        ctk.CTkLabel(form_frame, text="Supplier:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        supplier_names = ["(None)"] + sorted(self._suppliers.keys())
        self.supplier_var = ctk.StringVar(value="(None)")
        self.supplier_dropdown = ctk.CTkOptionMenu(
            form_frame,
            values=supplier_names,
            variable=self.supplier_var,
            width=200,
        )
        self.supplier_dropdown.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        row += 1

        # SKU (optional)
        ctk.CTkLabel(form_frame, text="SKU:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.sku_entry = ctk.CTkEntry(
            form_frame, placeholder_text="Optional product SKU"
        )
        self.sku_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        row += 1

        # Notes (optional)
        ctk.CTkLabel(form_frame, text="Notes:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.notes_entry = ctk.CTkEntry(
            form_frame, placeholder_text="Optional notes"
        )
        self.notes_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        row += 1

    def _on_material_change(self, value: str):
        """Handle material selection - set default package unit."""
        if value in self._materials:
            base_unit = self._materials[value].get("base_unit", "each")
            # Only set if empty
            if not self.unit_entry.get():
                self.unit_entry.delete(0, "end")
                self.unit_entry.insert(0, base_unit)

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
            command=self._save,
            width=80,
        )
        save_button.pack(side="right", padx=5)

    def _populate_form(self):
        """Pre-fill form when editing existing product."""
        if not self.product:
            return

        # Set name
        name = self.product.get("name", "")
        if name:
            self.name_entry.insert(0, name)

        # Set material
        material_name = self.product.get("material_name", "")
        if material_name and material_name in self._materials:
            self.material_var.set(material_name)

        # Set package quantity
        qty = self.product.get("package_quantity", "")
        if qty:
            self.qty_entry.insert(0, str(qty))

        # Set package unit
        unit = self.product.get("package_unit", "")
        if unit:
            self.unit_entry.insert(0, unit)

        # Set supplier
        supplier = self.product.get("supplier_name", "")
        if supplier and supplier in self._suppliers:
            self.supplier_var.set(supplier)

        # Set SKU
        sku = self.product.get("sku", "")
        if sku:
            self.sku_entry.insert(0, sku)

        # Set notes
        notes = self.product.get("notes", "")
        if notes:
            self.notes_entry.insert(0, notes)

    def _save(self):
        """Validate and save the product."""
        # Validate material
        material_name = self.material_var.get()
        if material_name not in self._materials:
            messagebox.showerror("Error", "Please select a material.")
            return

        material_id = self._materials[material_name]["id"]

        # Get name from entry (always editable now)
        name = self.name_entry.get().strip()

        # Validate name
        if not name:
            messagebox.showerror("Error", "Product name is required.")
            return

        # Validate package quantity
        qty_str = self.qty_entry.get().strip()
        try:
            package_quantity = float(qty_str)
            if package_quantity <= 0:
                raise ValueError("Must be positive")
        except ValueError:
            messagebox.showerror("Error", "Package quantity must be a positive number.")
            return

        # Get optional fields
        package_unit = self.unit_entry.get().strip() or self._materials[material_name].get("base_unit", "each")

        supplier_name = self.supplier_var.get()
        supplier_id = self._suppliers.get(supplier_name) if supplier_name != "(None)" else None

        sku = self.sku_entry.get().strip() or None
        notes = self.notes_entry.get().strip() or None

        # Build result
        self.result = {
            "name": name,
            "material_id": material_id,
            "package_quantity": package_quantity,
            "package_unit": package_unit,
            "supplier_id": supplier_id,
            "sku": sku,
            "notes": notes,
        }

        # Include ID if editing
        if self.product:
            self.result["id"] = self.product.get("id")

        self.destroy()


class RecordPurchaseDialog(ctk.CTkToplevel):
    """
    Dialog for recording a material product purchase.

    Feature 048: Modal dialog with auto-calculation of total units and unit cost.
    """

    def __init__(
        self,
        parent,
        product: Dict[str, Any],
    ):
        """
        Initialize the purchase dialog.

        Args:
            parent: Parent window
            product: Product dict with id, name, package_quantity, package_unit, material_name
        """
        super().__init__(parent)

        # Modal pattern - hide while building
        self.withdraw()

        self.parent_tab = parent
        self.product = product
        self.result: Optional[Dict[str, Any]] = None

        # Get package quantity for calculations
        self.package_quantity = float(product.get("package_quantity", 1) or 1)
        self.package_unit = product.get("package_unit", "each") or product.get("base_unit", "each")

        # Configure window
        self.title(f"Record Purchase - {product.get('name', '')}")
        self.geometry("450x420")
        self.resizable(False, False)

        # Center on parent
        self.transient(parent)

        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Load suppliers
        self._load_suppliers()

        # Create form
        self._create_form()
        self._create_buttons()

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

    def _load_suppliers(self):
        """Load suppliers for dropdown."""
        self._suppliers: Dict[str, int] = {}
        try:
            suppliers = supplier_service.get_all_suppliers()
            for sup in suppliers:
                # supplier_service may return dicts or ORM objects
                if isinstance(sup, dict):
                    self._suppliers[sup["name"]] = sup["id"]
                else:
                    self._suppliers[sup.name] = sup.id
        except Exception as e:
            print(f"Error loading suppliers: {e}")

    def _create_form(self):
        """Create form fields."""
        form_frame = ctk.CTkFrame(self)
        form_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        form_frame.grid_columnconfigure(1, weight=1)

        row = 0

        # Product info (read-only)
        ctk.CTkLabel(form_frame, text="Product:").grid(
            row=row, column=0, sticky="w", padx=10, pady=(10, 5)
        )
        ctk.CTkLabel(
            form_frame,
            text=self.product.get("name", ""),
            font=ctk.CTkFont(weight="bold"),
            anchor="w",
        ).grid(row=row, column=1, sticky="ew", padx=10, pady=(10, 5))
        row += 1

        # Package info
        ctk.CTkLabel(form_frame, text="Package:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        ctk.CTkLabel(
            form_frame,
            text=f"{self.package_quantity:,.1f} {self.package_unit} per package",
            anchor="w",
        ).grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        row += 1

        # Supplier dropdown (required)
        ctk.CTkLabel(form_frame, text="Supplier*:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        supplier_names = sorted(self._suppliers.keys()) or ["(none available)"]
        self.supplier_var = ctk.StringVar(value=supplier_names[0] if supplier_names else "")
        self.supplier_dropdown = ctk.CTkOptionMenu(
            form_frame,
            values=supplier_names,
            variable=self.supplier_var,
            width=200,
        )
        self.supplier_dropdown.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        row += 1

        # Purchase Date
        ctk.CTkLabel(form_frame, text="Date*:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.date_entry = ctk.CTkEntry(form_frame)
        self.date_entry.insert(0, date.today().isoformat())
        self.date_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        row += 1

        # Packages purchased
        ctk.CTkLabel(form_frame, text="Packages*:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.packages_entry = ctk.CTkEntry(
            form_frame, placeholder_text="Number of packages"
        )
        self.packages_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        self.packages_entry.bind("<KeyRelease>", self._update_calculations)
        row += 1

        # Total Price
        ctk.CTkLabel(form_frame, text="Total Price*:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.price_entry = ctk.CTkEntry(
            form_frame, placeholder_text="$0.00"
        )
        self.price_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        self.price_entry.bind("<KeyRelease>", self._update_calculations)
        row += 1

        # Calculated fields frame
        calc_frame = ctk.CTkFrame(form_frame, fg_color=("gray90", "gray20"))
        calc_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        calc_frame.grid_columnconfigure(1, weight=1)

        # Total units (calculated)
        ctk.CTkLabel(calc_frame, text="Total Units:").grid(
            row=0, column=0, sticky="w", padx=10, pady=5
        )
        self.total_units_label = ctk.CTkLabel(calc_frame, text="-", anchor="w")
        self.total_units_label.grid(row=0, column=1, sticky="ew", padx=10, pady=5)

        # Unit cost (calculated)
        ctk.CTkLabel(calc_frame, text="Unit Cost:").grid(
            row=1, column=0, sticky="w", padx=10, pady=5
        )
        self.unit_cost_label = ctk.CTkLabel(calc_frame, text="-", anchor="w")
        self.unit_cost_label.grid(row=1, column=1, sticky="ew", padx=10, pady=5)

        row += 1

        # Notes
        ctk.CTkLabel(form_frame, text="Notes:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.notes_entry = ctk.CTkEntry(
            form_frame, placeholder_text="Optional notes"
        )
        self.notes_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)

    def _update_calculations(self, event=None):
        """Update calculated fields based on input."""
        try:
            packages = int(self.packages_entry.get().strip())
            total_units = packages * self.package_quantity
            self.total_units_label.configure(
                text=f"{total_units:,.1f} {self.package_unit}"
            )
        except (ValueError, TypeError):
            self.total_units_label.configure(text="-")
            self.unit_cost_label.configure(text="-")
            return

        try:
            price = float(self.price_entry.get().strip())
            if total_units > 0:
                unit_cost = price / total_units
                self.unit_cost_label.configure(text=f"${unit_cost:.4f}")
            else:
                self.unit_cost_label.configure(text="-")
        except (ValueError, TypeError):
            self.unit_cost_label.configure(text="-")

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
            text="Record",
            command=self._save,
            width=80,
        )
        save_button.pack(side="right", padx=5)

    def _save(self):
        """Validate and save the purchase."""
        # Validate supplier
        supplier_name = self.supplier_var.get()
        if supplier_name not in self._suppliers:
            messagebox.showerror("Error", "Please select a supplier.")
            return
        supplier_id = self._suppliers[supplier_name]

        # Validate date
        try:
            purchase_date = date.fromisoformat(self.date_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD.")
            return

        # Validate packages
        try:
            packages = int(self.packages_entry.get().strip())
            if packages <= 0:
                raise ValueError("Must be positive")
        except ValueError:
            messagebox.showerror("Error", "Packages must be a positive integer.")
            return

        # Validate price
        try:
            price = float(self.price_entry.get().strip())
            if price < 0:
                raise ValueError("Must be non-negative")
        except ValueError:
            messagebox.showerror("Error", "Price must be a non-negative number.")
            return

        notes = self.notes_entry.get().strip() or None

        # Build result
        self.result = {
            "product_id": self.product.get("id"),
            "supplier_id": supplier_id,
            "purchase_date": purchase_date,
            "packages_purchased": packages,
            "total_price": price,
            "notes": notes,
        }

        self.destroy()


class AdjustInventoryDialog(ctk.CTkToplevel):
    """
    Dialog for adjusting material product inventory.

    Feature 048: Modal dialog for set-to-value or set-to-percentage adjustments.
    """

    def __init__(
        self,
        parent,
        product: Dict[str, Any],
    ):
        """
        Initialize the adjust inventory dialog.

        Args:
            parent: Parent window
            product: Product dict with id, name, inventory, base_unit
        """
        super().__init__(parent)

        # Modal pattern - hide while building
        self.withdraw()

        self.parent_tab = parent
        self.product = product
        self.result: Optional[Dict[str, Any]] = None

        self.current_inventory = float(product.get("inventory", 0) or 0)
        self.base_unit = product.get("base_unit", "units")

        # Configure window
        self.title(f"Adjust Inventory - {product.get('name', '')}")
        self.geometry("400x350")
        self.resizable(False, False)

        # Center on parent
        self.transient(parent)

        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Create form
        self._create_form()
        self._create_buttons()

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

        # Product info (read-only)
        ctk.CTkLabel(form_frame, text="Product:").grid(
            row=row, column=0, sticky="w", padx=10, pady=(10, 5)
        )
        ctk.CTkLabel(
            form_frame,
            text=self.product.get("name", ""),
            font=ctk.CTkFont(weight="bold"),
            anchor="w",
        ).grid(row=row, column=1, sticky="ew", padx=10, pady=(10, 5))
        row += 1

        # Current inventory (read-only)
        ctk.CTkLabel(form_frame, text="Current:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        ctk.CTkLabel(
            form_frame,
            text=f"{self.current_inventory:,.1f} {self.base_unit}",
            anchor="w",
        ).grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        row += 1

        # Mode selection
        ctk.CTkLabel(form_frame, text="Adjustment:").grid(
            row=row, column=0, sticky="nw", padx=10, pady=(15, 5)
        )
        mode_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        mode_frame.grid(row=row, column=1, sticky="ew", padx=10, pady=(15, 5))

        self.mode_var = ctk.StringVar(value="set")
        ctk.CTkRadioButton(
            mode_frame,
            text="Set to specific value",
            variable=self.mode_var,
            value="set",
            command=self._update_preview,
        ).pack(anchor="w", pady=2)
        ctk.CTkRadioButton(
            mode_frame,
            text="Set to percentage of current",
            variable=self.mode_var,
            value="percentage",
            command=self._update_preview,
        ).pack(anchor="w", pady=2)
        row += 1

        # Value entry
        ctk.CTkLabel(form_frame, text="Value*:").grid(
            row=row, column=0, sticky="w", padx=10, pady=(15, 5)
        )
        self.value_entry = ctk.CTkEntry(
            form_frame, placeholder_text="Enter value"
        )
        self.value_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=(15, 5))
        self.value_entry.bind("<KeyRelease>", self._update_preview)
        row += 1

        # Preview
        ctk.CTkLabel(form_frame, text="Preview:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.preview_label = ctk.CTkLabel(
            form_frame,
            text="-",
            anchor="w",
            font=ctk.CTkFont(weight="bold"),
        )
        self.preview_label.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        row += 1

        # Notes
        ctk.CTkLabel(form_frame, text="Notes:").grid(
            row=row, column=0, sticky="w", padx=10, pady=(15, 5)
        )
        self.notes_entry = ctk.CTkEntry(
            form_frame, placeholder_text="Reason for adjustment"
        )
        self.notes_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=(15, 5))

    def _update_preview(self, event=None):
        """Update the preview based on mode and value."""
        try:
            value = float(self.value_entry.get().strip())
            mode = self.mode_var.get()

            if mode == "set":
                new_qty = value
            else:  # percentage
                new_qty = self.current_inventory * (value / 100)

            self.preview_label.configure(
                text=f"{new_qty:,.1f} {self.base_unit}"
            )
        except (ValueError, TypeError):
            self.preview_label.configure(text="-")

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
            text="Adjust",
            command=self._save,
            width=80,
        )
        save_button.pack(side="right", padx=5)

    def _save(self):
        """Validate and save the adjustment."""
        # Validate value
        try:
            value = float(self.value_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Value must be a number.")
            return

        mode = self.mode_var.get()
        notes = self.notes_entry.get().strip() or None

        # Build result
        self.result = {
            "product_id": self.product.get("id"),
            "mode": mode,
            "value": value,
            "notes": notes,
        }

        self.destroy()


class MaterialUnitFormDialog(ctk.CTkToplevel):
    """
    Dialog for creating or editing a material unit.

    Feature 048: Modal dialog for unit management.
    """

    def __init__(
        self,
        parent,
        unit: Optional[Dict[str, Any]] = None,
        title: str = "Add Unit",
        material_id: Optional[int] = None,
    ):
        """
        Initialize the unit form dialog.

        Args:
            parent: Parent window
            unit: Existing unit dict to edit (None for new)
            title: Dialog title
            material_id: Pre-select this material (for add from material context)
        """
        super().__init__(parent)

        # Modal pattern - hide while building
        self.withdraw()

        self.parent_tab = parent
        self.unit = unit
        self.material_id = material_id
        self.result: Optional[Dict[str, Any]] = None

        # Configure window
        self.title(title)
        self.geometry("450x350")
        self.resizable(False, False)

        # Center on parent
        self.transient(parent)

        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Load materials for dropdown
        self._load_materials()

        # Create form
        self._create_form()
        self._create_buttons()

        # Populate if editing
        if self.unit:
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

    def _load_materials(self):
        """Load materials for dropdown."""
        self._materials: Dict[str, Dict[str, Any]] = {}
        try:
            categories = material_catalog_service.list_categories()
            for cat in categories:
                cat_id = _get_value(cat, "id")
                subcategories = material_catalog_service.list_subcategories(cat_id)
                for subcat in subcategories:
                    sub_id = _get_value(subcat, "id")
                    mats = material_catalog_service.list_materials(sub_id)
                    for mat in mats:
                        name = _get_value(mat, "name")
                        mat_id = _get_value(mat, "id")
                        base_unit = _get_value(mat, "base_unit_type") or "each"
                        if name is None or mat_id is None:
                            continue
                        self._materials[name] = {
                            "id": mat_id,
                            "base_unit": base_unit,
                        }
        except Exception as e:
            print(f"Error loading materials: {e}")

    def _create_form(self):
        """Create form fields."""
        form_frame = ctk.CTkFrame(self)
        form_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        form_frame.grid_columnconfigure(1, weight=1)

        row = 0

        # Material dropdown (required)
        ctk.CTkLabel(form_frame, text="Material*:").grid(
            row=row, column=0, sticky="w", padx=10, pady=(10, 5)
        )
        material_names = sorted(self._materials.keys())
        self.material_var = ctk.StringVar(value="(Select material)")

        # Pre-select material if provided
        if self.material_id:
            for name, data in self._materials.items():
                if data["id"] == self.material_id:
                    self.material_var.set(name)
                    break

        self.material_dropdown = ctk.CTkComboBox(
            form_frame,
            values=["(Select material)"] + material_names,
            variable=self.material_var,
            width=250,
        )
        self.material_dropdown.grid(row=row, column=1, sticky="w", padx=10, pady=(10, 5))
        row += 1

        # Unit Name (required) - editable when adding, read-only when editing
        if self.unit:
            # Edit mode - show name as read-only label
            ctk.CTkLabel(form_frame, text="Name:").grid(
                row=row, column=0, sticky="w", padx=10, pady=5
            )
            self.name_label = ctk.CTkLabel(
                form_frame,
                text=self.unit.get("name", ""),
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w",
            )
            self.name_label.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
            self.name_entry = None
        else:
            # Add mode - editable entry
            ctk.CTkLabel(form_frame, text="Name*:").grid(
                row=row, column=0, sticky="w", padx=10, pady=5
            )
            self.name_entry = ctk.CTkEntry(
                form_frame, placeholder_text="e.g., Standard Bow"
            )
            self.name_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        row += 1

        # Quantity per Unit (required)
        ctk.CTkLabel(form_frame, text="Qty/Unit*:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.qty_entry = ctk.CTkEntry(
            form_frame, placeholder_text="Base units consumed per unit"
        )
        self.qty_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        row += 1

        # Description (optional)
        ctk.CTkLabel(form_frame, text="Description:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.description_entry = ctk.CTkEntry(
            form_frame, placeholder_text="Optional description"
        )
        self.description_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
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
            command=self._save,
            width=80,
        )
        save_button.pack(side="right", padx=5)

    def _populate_form(self):
        """Pre-fill form when editing existing unit."""
        if not self.unit:
            return

        # Set material
        material_name = self.unit.get("material_name", "")
        if material_name and material_name in self._materials:
            self.material_var.set(material_name)

        # Set quantity per unit
        qty = self.unit.get("quantity_per_unit", "")
        if qty:
            self.qty_entry.insert(0, str(qty))

        # Set description
        description = self.unit.get("description", "")
        if description:
            self.description_entry.insert(0, description)

    def _save(self):
        """Validate and save the unit."""
        # Validate material
        material_name = self.material_var.get()
        if material_name not in self._materials:
            messagebox.showerror("Error", "Please select a material.")
            return

        material_id = self._materials[material_name]["id"]

        # Get name
        if self.unit:
            name = self.unit.get("name", "")
        else:
            name = self.name_entry.get().strip() if self.name_entry else ""

        # Validate name
        if not name:
            messagebox.showerror("Error", "Unit name is required.")
            return

        # Validate quantity per unit
        qty_str = self.qty_entry.get().strip()
        try:
            quantity_per_unit = float(qty_str)
            if quantity_per_unit <= 0:
                raise ValueError("Must be positive")
        except ValueError:
            messagebox.showerror("Error", "Quantity must be a positive number.")
            return

        # Get optional fields
        description = self.description_entry.get().strip() or None

        # Build result
        self.result = {
            "name": name,
            "material_id": material_id,
            "quantity_per_unit": quantity_per_unit,
            "description": description,
        }

        # Include ID if editing
        if self.unit:
            self.result["id"] = self.unit.get("id")

        self.destroy()


class MaterialsCatalogTab:
    """
    Inner class for Materials Catalog sub-tab.

    Displays materials in a flat grid with columns:
    - Category (L0)
    - Subcategory (L1)
    - Material Name
    - Default Unit
    """

    def __init__(self, parent_frame: ctk.CTkFrame, parent_tab: MaterialsTab):
        """
        Initialize the Materials Catalog tab.

        Args:
            parent_frame: The CTkTabview tab frame to build UI in
            parent_tab: The parent MaterialsTab for coordination
        """
        self.parent_frame = parent_frame
        self.parent_tab = parent_tab
        self.selected_material_id: Optional[int] = None
        self.materials: List[Dict[str, Any]] = []

        # Sorting state
        self.sort_column = "name"
        self.sort_ascending = True

        # Configure grid layout: filter, buttons, grid, status
        self.parent_frame.grid_columnconfigure(0, weight=1)
        self.parent_frame.grid_rowconfigure(0, weight=0)  # Filter
        self.parent_frame.grid_rowconfigure(1, weight=0)  # Buttons
        self.parent_frame.grid_rowconfigure(2, weight=1)  # Grid
        self.parent_frame.grid_rowconfigure(3, weight=0)  # Status

        self._create_filter_bar()
        self._create_action_buttons()
        self._create_grid()
        self._create_status_bar()

    def _create_filter_bar(self):
        """Create search and filter controls."""
        filter_frame = ctk.CTkFrame(self.parent_frame)
        filter_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # Search entry
        search_label = ctk.CTkLabel(filter_frame, text="Search:")
        search_label.pack(side="left", padx=(5, 2), pady=5)

        self.search_entry = ctk.CTkEntry(
            filter_frame,
            placeholder_text="Search materials...",
            width=200,
        )
        self.search_entry.pack(side="left", padx=5, pady=5)
        self.search_entry.bind("<KeyRelease>", self._on_search)

        # L0 Category filter
        l0_label = ctk.CTkLabel(filter_frame, text="Category:")
        l0_label.pack(side="left", padx=(15, 2), pady=5)

        self.l0_filter_var = ctk.StringVar(value="All Categories")
        self.l0_filter_dropdown = ctk.CTkOptionMenu(
            filter_frame,
            variable=self.l0_filter_var,
            values=["All Categories"],
            command=self._on_l0_filter_change,
            width=150,
        )
        self.l0_filter_dropdown.pack(side="left", padx=5, pady=5)

        # L1 Subcategory filter
        l1_label = ctk.CTkLabel(filter_frame, text="Subcategory:")
        l1_label.pack(side="left", padx=(10, 2), pady=5)

        self.l1_filter_var = ctk.StringVar(value="All")
        self.l1_filter_dropdown = ctk.CTkOptionMenu(
            filter_frame,
            variable=self.l1_filter_var,
            values=["All"],
            command=self._on_l1_filter_change,
            width=150,
            state="disabled",
        )
        self.l1_filter_dropdown.pack(side="left", padx=5, pady=5)

        # Level filter dropdown (FR-004)
        self.level_filter_var = ctk.StringVar(value="All Levels")
        self.level_filter_dropdown = ctk.CTkOptionMenu(
            filter_frame,
            values=[
                "All Levels",
                "Root Categories (L0)",
                "Subcategories (L1)",
                "Leaf Materials (L2)",
            ],
            variable=self.level_filter_var,
            command=self._on_level_filter_change,
            width=160,
        )
        self.level_filter_dropdown.pack(side="left", padx=(15, 5), pady=5)

        # Clear button
        clear_button = ctk.CTkButton(
            filter_frame,
            text="Clear",
            command=self._clear_filters,
            width=60,
        )
        clear_button.pack(side="left", padx=10, pady=5)

    def _create_action_buttons(self):
        """Create action buttons for CRUD operations."""
        button_frame = ctk.CTkFrame(self.parent_frame, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

        # Add Material button
        add_button = ctk.CTkButton(
            button_frame,
            text="+ Add Material",
            command=self._add_material,
            width=130,
            height=36,
        )
        add_button.grid(row=0, column=0, padx=(0, PADDING_MEDIUM))

        # Edit button
        self.edit_button = ctk.CTkButton(
            button_frame,
            text="Edit",
            command=self._edit_material,
            width=100,
            height=36,
            state="disabled",
        )
        self.edit_button.grid(row=0, column=1, padx=(0, PADDING_MEDIUM))

    def _create_grid(self):
        """Create the materials grid using ttk.Treeview."""
        grid_container = ctk.CTkFrame(self.parent_frame)
        grid_container.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        grid_container.grid_columnconfigure(0, weight=1)
        grid_container.grid_rowconfigure(0, weight=1)

        # Define columns: l0, l1, name, base_unit
        columns = ("l0", "l1", "name", "base_unit")
        self.tree = ttk.Treeview(
            grid_container,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        # Configure column headings with click-to-sort
        self.tree.heading(
            "l0", text="Category (L0)", anchor="w",
            command=lambda: self._on_header_click("l0")
        )
        self.tree.heading(
            "l1", text="Subcategory (L1)", anchor="w",
            command=lambda: self._on_header_click("l1")
        )
        self.tree.heading(
            "name", text="Material Name", anchor="w",
            command=lambda: self._on_header_click("name")
        )
        self.tree.heading(
            "base_unit", text="Default Unit", anchor="w",
            command=lambda: self._on_header_click("base_unit")
        )

        # Configure column widths
        self.tree.column("l0", width=150, minwidth=100)
        self.tree.column("l1", width=150, minwidth=100)
        self.tree.column("name", width=200, minwidth=150)
        self.tree.column("base_unit", width=100, minwidth=80)

        # Add vertical scrollbar
        y_scrollbar = ttk.Scrollbar(
            grid_container,
            orient="vertical",
            command=self.tree.yview,
        )
        self.tree.configure(yscrollcommand=y_scrollbar.set)

        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")

        # Bind events
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def _create_status_bar(self):
        """Create status bar for displaying messages."""
        self.status_label = ctk.CTkLabel(
            self.parent_frame,
            text="Ready",
            anchor="w",
            height=30,
        )
        self.status_label.grid(
            row=3, column=0, sticky="ew",
            padx=5, pady=(5, 10),
        )

    def refresh(self):
        """Refresh the materials list from the database."""
        try:
            # Load all materials with hierarchy info
            self.materials = self._load_all_materials()
            self._load_filter_dropdowns()
            self._update_display()
            count = len(self.materials)
            self.update_status(f"{count} material{'s' if count != 1 else ''} loaded")
        except Exception as e:
            self.update_status(f"Error loading materials: {e}")

    def _load_all_materials(self) -> List[Dict[str, Any]]:
        """Load all materials with their hierarchy info.

        FR-004: Include hierarchy_level for level filtering:
        - Level 0: Categories
        - Level 1: Subcategories
        - Level 2: Leaf Materials
        """
        materials = []
        try:
            categories = material_catalog_service.list_categories()
            for cat in categories:
                cat_id = _get_value(cat, "id")
                cat_name = _get_value(cat, "name") or ""
                # Add L0 category
                materials.append({
                    "id": f"cat_{cat_id}",  # Prefix to avoid ID collision
                    "name": "",  # Name column empty for L0
                    "base_unit": "",
                    "l0_name": cat_name,
                    "l0_id": cat_id,
                    "l1_name": "",
                    "l1_id": None,
                    "hierarchy_level": 0,
                })

                subcategories = material_catalog_service.list_subcategories(cat_id)
                for subcat in subcategories:
                    sub_id = _get_value(subcat, "id")
                    sub_name = _get_value(subcat, "name") or ""
                    # Add L1 subcategory
                    materials.append({
                        "id": f"subcat_{sub_id}",  # Prefix to avoid ID collision
                        "name": "",  # Name column empty for L1
                        "base_unit": "",
                        "l0_name": cat_name,
                        "l0_id": cat_id,
                        "l1_name": sub_name,
                        "l1_id": sub_id,
                        "hierarchy_level": 1,
                    })

                    mats = material_catalog_service.list_materials(sub_id)
                    for mat in mats:
                        mat_id = _get_value(mat, "id")
                        mat_name = _get_value(mat, "name")
                        base_unit = mat.get("base_unit_type", "") if isinstance(mat, dict) else _get_value(mat, "base_unit_type") or ""
                        # Add L2 material
                        materials.append({
                            "id": mat_id,
                            "name": mat_name,
                            "base_unit": base_unit,
                            "l0_name": cat_name,
                            "l0_id": cat_id,
                            "l1_name": sub_name,
                            "l1_id": sub_id,
                            "hierarchy_level": 2,
                        })
        except Exception as e:
            print(f"Error loading materials: {e}")
        return materials

    def _load_filter_dropdowns(self):
        """Load data for filter dropdowns."""
        try:
            categories = material_catalog_service.list_categories()
            l0_names = ["All Categories"] + sorted(
                [_get_value(c, "name") or "" for c in categories]
            )
            self.l0_filter_dropdown.configure(values=l0_names)
        except Exception:
            pass

    def _update_display(self):
        """Update the displayed list based on current filters."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Apply filters
        filtered = self._apply_filters()

        # Populate grid
        for mat in filtered:
            values = (
                mat.get("l0_name", ""),
                mat.get("l1_name", ""),
                mat.get("name", ""),
                mat.get("base_unit", ""),
            )
            self.tree.insert("", "end", iid=str(mat["id"]), values=values)

        # Update status
        count = len(filtered)
        total = len(self.materials)
        if count < total:
            self.update_status(f"Showing {count} of {total} materials")
        else:
            self.update_status(f"{count} material{'s' if count != 1 else ''}")

    def _apply_filters(self) -> List[Dict[str, Any]]:
        """Apply search, dropdown filters, level filter, and sorting."""
        filtered = self.materials

        # Level filter (FR-004)
        selected_level = self._get_selected_level()
        if selected_level is not None:
            filtered = [m for m in filtered if m.get("hierarchy_level") == selected_level]

        # L0 filter
        l0_filter = self.l0_filter_var.get()
        if l0_filter and l0_filter != "All Categories":
            filtered = [m for m in filtered if m.get("l0_name") == l0_filter]

        # L1 filter
        l1_filter = self.l1_filter_var.get()
        if l1_filter and l1_filter != "All":
            filtered = [m for m in filtered if m.get("l1_name") == l1_filter]

        # Search filter - search across l0_name, l1_name, and name
        search_text = normalize_for_search(self.search_entry.get())
        if search_text:
            filtered = [
                m for m in filtered
                if search_text in normalize_for_search(m.get("name", ""))
                or search_text in normalize_for_search(m.get("l0_name", ""))
                or search_text in normalize_for_search(m.get("l1_name", ""))
            ]

        # Apply sorting
        sort_key_map = {
            "l0": "l0_name",
            "l1": "l1_name",
            "name": "name",
            "base_unit": "base_unit",
        }
        sort_field = sort_key_map.get(self.sort_column, "name")
        filtered = sorted(
            filtered,
            key=lambda m: (m.get(sort_field) or "").lower(),
            reverse=not self.sort_ascending,
        )

        return filtered

    def _get_selected_level(self) -> Optional[int]:
        """Convert level filter dropdown value to hierarchy level number.

        FR-004: Maps dropdown text to hierarchy_level values.

        Returns:
            0 for L0, 1 for L1, 2 for L2, or None for All Levels
        """
        value = self.level_filter_var.get()
        level_map = {
            "All Levels": None,
            "Root Categories (L0)": 0,
            "Subcategories (L1)": 1,
            "Leaf Materials (L2)": 2,
        }
        return level_map.get(value)

    def _on_search(self, event=None):
        """Handle search entry changes."""
        self._update_display()

    def _on_l0_filter_change(self, value: str):
        """Handle L0 category filter change."""
        if value == "All Categories":
            self.l1_filter_dropdown.configure(values=["All"], state="disabled")
            self.l1_filter_var.set("All")
        else:
            # Get subcategories for selected category (only from L1+ items with non-empty l1_name)
            subcats = [
                m["l1_name"] for m in self.materials
                if m.get("l0_name") == value and m.get("l1_name")
            ]
            unique_subcats = sorted(set(subcats))
            self.l1_filter_dropdown.configure(
                values=["All"] + unique_subcats,
                state="normal"
            )
            self.l1_filter_var.set("All")
        self._update_display()

    def _on_l1_filter_change(self, value: str):
        """Handle L1 subcategory filter change."""
        self._update_display()

    def _on_level_filter_change(self, value: str):
        """Handle level filter change (FR-004)."""
        self._update_display()

    def _clear_filters(self):
        """Clear all filters."""
        self.search_entry.delete(0, "end")
        self.l0_filter_var.set("All Categories")
        self.l1_filter_dropdown.configure(values=["All"], state="disabled")
        self.l1_filter_var.set("All")
        self.level_filter_var.set("All Levels")
        self._update_display()

    def _on_header_click(self, sort_key: str):
        """Handle column header click for sorting."""
        if self.sort_column == sort_key:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = sort_key
            self.sort_ascending = True
        self._update_display()

    def _on_tree_select(self, event=None):
        """Handle tree selection change."""
        selection = self.tree.selection()
        if selection:
            item_id = selection[0]
            # L0/L1 items have string IDs like "cat_1" or "subcat_1"
            # Only L2 materials have integer IDs and can be edited
            if item_id.startswith("cat_") or item_id.startswith("subcat_"):
                self.selected_material_id = None
                self._disable_selection_buttons()
            else:
                self.selected_material_id = int(item_id)
                self._enable_selection_buttons()
        else:
            self.selected_material_id = None
            self._disable_selection_buttons()

    def _on_double_click(self, event):
        """Handle double-click to edit."""
        selection = self.tree.selection()
        if selection:
            item_id = selection[0]
            # Only allow editing L2 materials (integer IDs)
            if not item_id.startswith("cat_") and not item_id.startswith("subcat_"):
                self.selected_material_id = int(item_id)
                self._edit_material()

    def _enable_selection_buttons(self):
        """Enable buttons that require selection."""
        self.edit_button.configure(state="normal")

    def _disable_selection_buttons(self):
        """Disable buttons that require selection."""
        self.edit_button.configure(state="disabled")

    def _add_material(self):
        """Open dialog to add a new material."""
        dialog = MaterialFormDialog(
            self.parent_frame,
            material=None,
            title="Add Material"
        )
        self.parent_frame.wait_window(dialog)

        if dialog.result:
            try:
                material_catalog_service.create_material(
                    subcategory_id=dialog.result["subcategory_id"],
                    name=dialog.result["name"],
                    base_unit_type=dialog.result["base_unit_type"],
                    notes=dialog.result.get("notes"),
                )
                self.refresh()
                self.update_status(f"Created material: {dialog.result['name']}")
            except ValidationError as e:
                messagebox.showerror("Error", str(e))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create material: {e}")

    def _edit_material(self):
        """Open dialog to edit selected material."""
        if not self.selected_material_id:
            return

        # Find material data by ID
        material_data = None
        for mat in self.materials:
            if mat["id"] == self.selected_material_id:
                material_data = mat
                break

        if not material_data:
            self.update_status("Material not found")
            return

        dialog = MaterialFormDialog(
            self.parent_frame,
            material=material_data,
            title="Edit Material"
        )
        self.parent_frame.wait_window(dialog)

        # Check if deleted
        if dialog.deleted:
            self.selected_material_id = None
            self._disable_selection_buttons()
            self.refresh()
            self.update_status("Material deleted")
            return

        # Check if saved
        if dialog.result:
            try:
                material_catalog_service.update_material(
                    material_id=dialog.result["id"],
                    subcategory_id=dialog.result["subcategory_id"],
                    base_unit_type=dialog.result["base_unit_type"],
                    notes=dialog.result.get("notes"),
                )
                self.refresh()
                self.update_status(f"Updated material: {dialog.result['name']}")
            except ValidationError as e:
                messagebox.showerror("Error", str(e))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update material: {e}")

    def update_status(self, message: str):
        """Update the status bar message."""
        self.status_label.configure(text=message)


class MaterialProductsTab:
    """
    Inner class for Material Products sub-tab.

    Displays products in a flat grid with columns:
    - Material
    - Product Name
    - Inventory
    - Unit Cost
    - Supplier
    """

    def __init__(self, parent_frame: ctk.CTkFrame, parent_tab: MaterialsTab):
        """
        Initialize the Material Products tab.

        Args:
            parent_frame: The CTkTabview tab frame to build UI in
            parent_tab: The parent MaterialsTab for coordination
        """
        self.parent_frame = parent_frame
        self.parent_tab = parent_tab
        self.selected_product_id: Optional[int] = None
        self.products: List[Dict[str, Any]] = []

        # Sorting state
        self.sort_column = "name"
        self.sort_ascending = True

        # Configure grid layout: filter, buttons, grid, status
        self.parent_frame.grid_columnconfigure(0, weight=1)
        self.parent_frame.grid_rowconfigure(0, weight=0)  # Filter
        self.parent_frame.grid_rowconfigure(1, weight=0)  # Buttons
        self.parent_frame.grid_rowconfigure(2, weight=1)  # Grid
        self.parent_frame.grid_rowconfigure(3, weight=0)  # Status

        self._create_filter_bar()
        self._create_action_buttons()
        self._create_grid()
        self._create_status_bar()

    def _create_filter_bar(self):
        """Create search and filter controls."""
        filter_frame = ctk.CTkFrame(self.parent_frame)
        filter_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # Search entry
        search_label = ctk.CTkLabel(filter_frame, text="Search:")
        search_label.pack(side="left", padx=(5, 2), pady=5)

        self.search_entry = ctk.CTkEntry(
            filter_frame,
            placeholder_text="Search products...",
            width=200,
        )
        self.search_entry.pack(side="left", padx=5, pady=5)
        self.search_entry.bind("<KeyRelease>", self._on_search)

        # Material filter
        mat_label = ctk.CTkLabel(filter_frame, text="Material:")
        mat_label.pack(side="left", padx=(15, 2), pady=5)

        self.material_filter_var = ctk.StringVar(value="All Materials")
        self.material_filter_dropdown = ctk.CTkOptionMenu(
            filter_frame,
            variable=self.material_filter_var,
            values=["All Materials"],
            command=self._on_material_filter_change,
            width=180,
        )
        self.material_filter_dropdown.pack(side="left", padx=5, pady=5)

        # Clear button
        clear_button = ctk.CTkButton(
            filter_frame,
            text="Clear",
            command=self._clear_filters,
            width=60,
        )
        clear_button.pack(side="left", padx=10, pady=5)

    def _create_action_buttons(self):
        """Create action buttons for CRUD operations."""
        button_frame = ctk.CTkFrame(self.parent_frame, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

        # Add Product button
        add_button = ctk.CTkButton(
            button_frame,
            text="+ Add Product",
            command=self._add_product,
            width=130,
            height=36,
        )
        add_button.grid(row=0, column=0, padx=(0, PADDING_MEDIUM))

        # Edit button
        self.edit_button = ctk.CTkButton(
            button_frame,
            text="Edit",
            command=self._edit_product,
            width=100,
            height=36,
            state="disabled",
        )
        self.edit_button.grid(row=0, column=1, padx=(0, PADDING_MEDIUM))

        # Record Purchase button
        self.purchase_button = ctk.CTkButton(
            button_frame,
            text="Record Purchase",
            command=self._record_purchase,
            width=130,
            height=36,
            state="disabled",
        )
        self.purchase_button.grid(row=0, column=2, padx=(0, PADDING_MEDIUM))

        # Adjust Inventory button
        self.adjust_button = ctk.CTkButton(
            button_frame,
            text="Adjust Inventory",
            command=self._adjust_inventory,
            width=130,
            height=36,
            state="disabled",
        )
        self.adjust_button.grid(row=0, column=3, padx=(0, PADDING_MEDIUM))

    def _create_grid(self):
        """Create the products grid using ttk.Treeview."""
        grid_container = ctk.CTkFrame(self.parent_frame)
        grid_container.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        grid_container.grid_columnconfigure(0, weight=1)
        grid_container.grid_rowconfigure(0, weight=1)

        # Define columns: material, name, inventory, unit_cost, supplier
        columns = ("material", "name", "inventory", "unit_cost", "supplier")
        self.tree = ttk.Treeview(
            grid_container,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        # Configure column headings with click-to-sort
        self.tree.heading(
            "material", text="Material", anchor="w",
            command=lambda: self._on_header_click("material")
        )
        self.tree.heading(
            "name", text="Product Name", anchor="w",
            command=lambda: self._on_header_click("name")
        )
        self.tree.heading(
            "inventory", text="Inventory", anchor="e",
            command=lambda: self._on_header_click("inventory")
        )
        self.tree.heading(
            "unit_cost", text="Unit Cost", anchor="e",
            command=lambda: self._on_header_click("unit_cost")
        )
        self.tree.heading(
            "supplier", text="Supplier", anchor="w",
            command=lambda: self._on_header_click("supplier")
        )

        # Configure column widths
        self.tree.column("material", width=150, minwidth=100)
        self.tree.column("name", width=150, minwidth=100)
        self.tree.column("inventory", width=120, minwidth=80, anchor="e")
        self.tree.column("unit_cost", width=100, minwidth=80, anchor="e")
        self.tree.column("supplier", width=120, minwidth=100)

        # Add vertical scrollbar
        y_scrollbar = ttk.Scrollbar(
            grid_container,
            orient="vertical",
            command=self.tree.yview,
        )
        self.tree.configure(yscrollcommand=y_scrollbar.set)

        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")

        # Bind events
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def _create_status_bar(self):
        """Create status bar for displaying messages."""
        self.status_label = ctk.CTkLabel(
            self.parent_frame,
            text="Ready",
            anchor="w",
            height=30,
        )
        self.status_label.grid(
            row=3, column=0, sticky="ew",
            padx=5, pady=(5, 10),
        )

    def refresh(self):
        """Refresh the products list from the database."""
        try:
            self.products = self._load_all_products()
            self._load_material_dropdown()
            self._update_display()
            count = len(self.products)
            self.update_status(f"{count} product{'s' if count != 1 else ''} loaded")
        except Exception as e:
            self.update_status(f"Error loading products: {e}")

    def _load_all_products(self) -> List[Dict[str, Any]]:
        """Load all products with material and supplier info."""
        products = []
        try:
            # Service returns ORM objects - use _get_value helper for safe access
            categories = material_catalog_service.list_categories()
            for cat in categories:
                cat_id = _get_value(cat, "id")
                subcategories = material_catalog_service.list_subcategories(cat_id)
                for subcat in subcategories:
                    subcat_id = _get_value(subcat, "id")
                    mats = material_catalog_service.list_materials(subcat_id)
                    for mat in mats:
                        mat_id = _get_value(mat, "id")
                        mat_name = _get_value(mat, "name")
                        mat_base_unit = _get_value(mat, "base_unit_type") or ""
                        prods = material_catalog_service.list_products(mat_id)
                        for prod in prods:
                            products.append({
                                "id": _get_value(prod, "id"),
                                "name": _get_value(prod, "name"),
                                "material_name": mat_name,
                                "material_id": mat_id,
                                "base_unit": mat_base_unit,
                                "package_quantity": _get_value(prod, "package_quantity") or 1,
                                "package_unit": _get_value(prod, "package_unit") or mat_base_unit or "each",
                                "inventory": _get_value(prod, "current_inventory") or 0,
                                "unit_cost": _get_value(prod, "weighted_avg_cost") or 0,
                                "supplier_name": _get_value(prod, "supplier_name") or "",
                                "supplier_id": _get_value(prod, "supplier_id"),
                                "sku": _get_value(prod, "sku") or "",
                                "notes": _get_value(prod, "notes") or "",
                            })
        except Exception as e:
            print(f"Error loading products: {e}")
            import traceback
            traceback.print_exc()
        return products

    def _load_material_dropdown(self):
        """Load materials for filter dropdown."""
        material_names = sorted(set(p["material_name"] for p in self.products))
        self.material_filter_dropdown.configure(
            values=["All Materials"] + material_names
        )

    def _update_display(self):
        """Update the displayed list based on current filters."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Apply filters
        filtered = self._apply_filters()

        # Populate grid
        for prod in filtered:
            # Format inventory as "4,724.5 inches"
            inventory = prod.get("inventory", 0) or 0
            base_unit = prod.get("base_unit", "")
            inventory_display = f"{inventory:,.1f} {base_unit}".strip()

            # Format cost as "$0.0016" or "-"
            unit_cost = prod.get("unit_cost", 0)
            cost_display = f"${unit_cost:.4f}" if unit_cost else "-"

            values = (
                prod.get("material_name", ""),
                prod.get("name", ""),
                inventory_display,
                cost_display,
                prod.get("supplier_name", "") or "-",
            )
            self.tree.insert("", "end", iid=str(prod["id"]), values=values)

        # Update status
        count = len(filtered)
        total = len(self.products)
        if count < total:
            self.update_status(f"Showing {count} of {total} products")
        else:
            self.update_status(f"{count} product{'s' if count != 1 else ''}")

    def _apply_filters(self) -> List[Dict[str, Any]]:
        """Apply search, dropdown filters, and sorting."""
        filtered = self.products

        # Material filter
        mat_filter = self.material_filter_var.get()
        if mat_filter and mat_filter != "All Materials":
            filtered = [p for p in filtered if p.get("material_name") == mat_filter]

        # Search filter
        search_text = normalize_for_search(self.search_entry.get())
        if search_text:
            filtered = [
                p for p in filtered
                if search_text in normalize_for_search(p.get("name", ""))
            ]

        # Apply sorting
        sort_key_map = {
            "material": "material_name",
            "name": "name",
            "inventory": "inventory",
            "unit_cost": "unit_cost",
            "supplier": "supplier_name",
        }
        sort_field = sort_key_map.get(self.sort_column, "name")

        def get_sort_value(p):
            val = p.get(sort_field)
            if sort_field in ("inventory", "unit_cost"):
                return val if val is not None else 0
            return (val or "").lower()

        filtered = sorted(filtered, key=get_sort_value, reverse=not self.sort_ascending)

        return filtered

    def _on_search(self, event=None):
        """Handle search entry changes."""
        self._update_display()

    def _on_material_filter_change(self, value: str):
        """Handle material filter change."""
        self._update_display()

    def _clear_filters(self):
        """Clear all filters."""
        self.search_entry.delete(0, "end")
        self.material_filter_var.set("All Materials")
        self._update_display()

    def _on_header_click(self, sort_key: str):
        """Handle column header click for sorting."""
        if self.sort_column == sort_key:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = sort_key
            self.sort_ascending = True
        self._update_display()

    def _on_tree_select(self, event=None):
        """Handle tree selection change."""
        selection = self.tree.selection()
        if selection:
            self.selected_product_id = int(selection[0])
            self._enable_selection_buttons()
        else:
            self.selected_product_id = None
            self._disable_selection_buttons()

    def _on_double_click(self, event):
        """Handle double-click to edit."""
        selection = self.tree.selection()
        if selection:
            self.selected_product_id = int(selection[0])
            self._edit_product()

    def _enable_selection_buttons(self):
        """Enable buttons that require selection."""
        self.edit_button.configure(state="normal")
        self.purchase_button.configure(state="normal")
        self.adjust_button.configure(state="normal")

    def _disable_selection_buttons(self):
        """Disable buttons that require selection."""
        self.edit_button.configure(state="disabled")
        self.purchase_button.configure(state="disabled")
        self.adjust_button.configure(state="disabled")

    def _add_product(self):
        """Open dialog to add a new product."""
        dialog = MaterialProductFormDialog(
            self.parent_frame,
            product=None,
            title="Add Product",
        )
        self.parent_frame.wait_window(dialog)

        if dialog.result:
            try:
                material_catalog_service.create_product(
                    material_id=dialog.result["material_id"],
                    name=dialog.result["name"],
                    package_quantity=dialog.result["package_quantity"],
                    package_unit=dialog.result["package_unit"],
                    supplier_id=dialog.result.get("supplier_id"),
                    sku=dialog.result.get("sku"),
                    notes=dialog.result.get("notes"),
                )
                self.refresh()
                self.update_status(f"Created product: {dialog.result['name']}")
            except ValidationError as e:
                messagebox.showerror("Error", str(e))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create product: {e}")

    def _edit_product(self):
        """Open dialog to edit selected product."""
        if not self.selected_product_id:
            return

        # Find product data by ID
        product_data = None
        for prod in self.products:
            if prod["id"] == self.selected_product_id:
                product_data = prod
                break

        if not product_data:
            self.update_status("Product not found")
            return

        dialog = MaterialProductFormDialog(
            self.parent_frame,
            product=product_data,
            title="Edit Product",
        )
        self.parent_frame.wait_window(dialog)

        if dialog.result:
            try:
                material_catalog_service.update_product(
                    product_id=dialog.result["id"],
                    material_id=dialog.result["material_id"],
                    package_quantity=dialog.result["package_quantity"],
                    package_unit=dialog.result["package_unit"],
                    supplier_id=dialog.result.get("supplier_id"),
                    sku=dialog.result.get("sku"),
                    notes=dialog.result.get("notes"),
                )
                self.refresh()
                self.update_status(f"Updated product: {dialog.result['name']}")
            except ValidationError as e:
                messagebox.showerror("Error", str(e))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update product: {e}")

    def _record_purchase(self):
        """Open dialog to record a purchase."""
        if not self.selected_product_id:
            return

        # Find product data by ID
        product_data = None
        for prod in self.products:
            if prod["id"] == self.selected_product_id:
                product_data = prod
                break

        if not product_data:
            self.update_status("Product not found")
            return

        dialog = RecordPurchaseDialog(
            self.parent_frame,
            product=product_data,
        )
        self.parent_frame.wait_window(dialog)

        if dialog.result:
            try:
                material_purchase_service.record_purchase(
                    product_id=dialog.result["product_id"],
                    supplier_id=dialog.result["supplier_id"],
                    purchase_date=dialog.result["purchase_date"],
                    packages_purchased=dialog.result["packages_purchased"],
                    package_price=dialog.result["total_price"],
                    notes=dialog.result.get("notes"),
                )
                self.refresh()
                self.update_status(f"Recorded purchase for: {product_data['name']}")
            except ValidationError as e:
                messagebox.showerror("Error", str(e))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to record purchase: {e}")

    def _adjust_inventory(self):
        """Open dialog to adjust inventory for selected product."""
        if not self.selected_product_id:
            return

        # Find product data by ID
        product_data = None
        for prod in self.products:
            if prod["id"] == self.selected_product_id:
                product_data = prod
                break

        if not product_data:
            self.update_status("Product not found")
            return

        dialog = AdjustInventoryDialog(
            self.parent_frame,
            product=product_data,
        )
        self.parent_frame.wait_window(dialog)

        if dialog.result:
            try:
                mode = dialog.result["mode"]
                value = dialog.result["value"]
                notes = dialog.result.get("notes")

                if mode == "set":
                    material_purchase_service.adjust_inventory(
                        product_id=dialog.result["product_id"],
                        new_quantity=value,
                        notes=notes,
                    )
                else:  # percentage
                    material_purchase_service.adjust_inventory(
                        product_id=dialog.result["product_id"],
                        percentage=value,
                        notes=notes,
                    )
                self.refresh()
                self.update_status(f"Adjusted inventory for: {product_data['name']}")
            except ValidationError as e:
                messagebox.showerror("Error", str(e))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to adjust inventory: {e}")

    def update_status(self, message: str):
        """Update the status bar message."""
        self.status_label.configure(text=message)


class MaterialUnitsTab:
    """
    Inner class for Material Units sub-tab.

    Displays units in a flat grid with columns:
    - Material
    - Unit Name
    - Qty/Unit
    - Available (computed)
    - Cost/Unit (computed)
    """

    def __init__(self, parent_frame: ctk.CTkFrame, parent_tab: MaterialsTab):
        """
        Initialize the Material Units tab.

        Args:
            parent_frame: The CTkTabview tab frame to build UI in
            parent_tab: The parent MaterialsTab for coordination
        """
        self.parent_frame = parent_frame
        self.parent_tab = parent_tab
        self.selected_unit_id: Optional[int] = None
        self.units: List[Dict[str, Any]] = []

        # Sorting state
        self.sort_column = "name"
        self.sort_ascending = True

        # Configure grid layout: filter, buttons, grid, status
        self.parent_frame.grid_columnconfigure(0, weight=1)
        self.parent_frame.grid_rowconfigure(0, weight=0)  # Filter
        self.parent_frame.grid_rowconfigure(1, weight=0)  # Buttons
        self.parent_frame.grid_rowconfigure(2, weight=1)  # Grid
        self.parent_frame.grid_rowconfigure(3, weight=0)  # Status

        self._create_filter_bar()
        self._create_action_buttons()
        self._create_grid()
        self._create_status_bar()

    def _create_filter_bar(self):
        """Create search and filter controls."""
        filter_frame = ctk.CTkFrame(self.parent_frame)
        filter_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # Search entry
        search_label = ctk.CTkLabel(filter_frame, text="Search:")
        search_label.pack(side="left", padx=(5, 2), pady=5)

        self.search_entry = ctk.CTkEntry(
            filter_frame,
            placeholder_text="Search units...",
            width=200,
        )
        self.search_entry.pack(side="left", padx=5, pady=5)
        self.search_entry.bind("<KeyRelease>", self._on_search)

        # Material filter
        mat_label = ctk.CTkLabel(filter_frame, text="Material:")
        mat_label.pack(side="left", padx=(15, 2), pady=5)

        self.material_filter_var = ctk.StringVar(value="All Materials")
        self.material_filter_dropdown = ctk.CTkOptionMenu(
            filter_frame,
            variable=self.material_filter_var,
            values=["All Materials"],
            command=self._on_material_filter_change,
            width=180,
        )
        self.material_filter_dropdown.pack(side="left", padx=5, pady=5)

        # Clear button
        clear_button = ctk.CTkButton(
            filter_frame,
            text="Clear",
            command=self._clear_filters,
            width=60,
        )
        clear_button.pack(side="left", padx=10, pady=5)

    def _create_action_buttons(self):
        """Create action buttons for CRUD operations."""
        button_frame = ctk.CTkFrame(self.parent_frame, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

        # Add Unit button
        add_button = ctk.CTkButton(
            button_frame,
            text="+ Add Unit",
            command=self._add_unit,
            width=110,
            height=36,
        )
        add_button.grid(row=0, column=0, padx=(0, PADDING_MEDIUM))

        # Edit button
        self.edit_button = ctk.CTkButton(
            button_frame,
            text="Edit",
            command=self._edit_unit,
            width=100,
            height=36,
            state="disabled",
        )
        self.edit_button.grid(row=0, column=1, padx=(0, PADDING_MEDIUM))

    def _create_grid(self):
        """Create the units grid using ttk.Treeview."""
        grid_container = ctk.CTkFrame(self.parent_frame)
        grid_container.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        grid_container.grid_columnconfigure(0, weight=1)
        grid_container.grid_rowconfigure(0, weight=1)

        # Define columns: material, name, qty_per_unit, available, cost
        columns = ("material", "name", "qty_per_unit", "available", "cost")
        self.tree = ttk.Treeview(
            grid_container,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        # Configure column headings with click-to-sort
        self.tree.heading(
            "material", text="Material", anchor="w",
            command=lambda: self._on_header_click("material")
        )
        self.tree.heading(
            "name", text="Unit Name", anchor="w",
            command=lambda: self._on_header_click("name")
        )
        self.tree.heading(
            "qty_per_unit", text="Qty/Unit", anchor="e",
            command=lambda: self._on_header_click("qty_per_unit")
        )
        self.tree.heading(
            "available", text="Available", anchor="e",
            command=lambda: self._on_header_click("available")
        )
        self.tree.heading(
            "cost", text="Cost/Unit", anchor="e",
            command=lambda: self._on_header_click("cost")
        )

        # Configure column widths
        self.tree.column("material", width=150, minwidth=100)
        self.tree.column("name", width=150, minwidth=100)
        self.tree.column("qty_per_unit", width=80, minwidth=60, anchor="e")
        self.tree.column("available", width=80, minwidth=60, anchor="e")
        self.tree.column("cost", width=100, minwidth=80, anchor="e")

        # Add vertical scrollbar
        y_scrollbar = ttk.Scrollbar(
            grid_container,
            orient="vertical",
            command=self.tree.yview,
        )
        self.tree.configure(yscrollcommand=y_scrollbar.set)

        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")

        # Bind events
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def _create_status_bar(self):
        """Create status bar for displaying messages."""
        self.status_label = ctk.CTkLabel(
            self.parent_frame,
            text="Ready",
            anchor="w",
            height=30,
        )
        self.status_label.grid(
            row=3, column=0, sticky="ew",
            padx=5, pady=(5, 10),
        )

    def refresh(self):
        """Refresh the units list from the database."""
        try:
            self.units = self._load_all_units()
            self._load_material_dropdown()
            self._update_display()
            count = len(self.units)
            self.update_status(f"{count} unit{'s' if count != 1 else ''} loaded")
        except Exception as e:
            self.update_status(f"Error loading units: {e}")

    def _load_all_units(self) -> List[Dict[str, Any]]:
        """Load all units with material info and computed values."""
        units = []
        try:
            # Service returns ORM objects - use _get_value helper for safe access
            categories = material_catalog_service.list_categories()
            for cat in categories:
                cat_id = _get_value(cat, "id")
                subcategories = material_catalog_service.list_subcategories(cat_id)
                for subcat in subcategories:
                    subcat_id = _get_value(subcat, "id")
                    mats = material_catalog_service.list_materials(subcat_id)
                    for mat in mats:
                        mat_id = _get_value(mat, "id")
                        mat_name = _get_value(mat, "name")
                        # Get units for this material
                        mat_units = material_unit_service.list_units(mat_id)
                        for unit in mat_units:
                            unit_id = _get_value(unit, "id")
                            unit_name = _get_value(unit, "name")
                            qty = _get_value(unit, "quantity_per_unit") or 1
                            desc = _get_value(unit, "description") or ""
                            # Get computed values
                            try:
                                available = material_unit_service.get_available_inventory(unit_id)
                            except Exception:
                                available = 0
                            try:
                                cost = material_unit_service.get_current_cost(unit_id)
                            except Exception:
                                cost = None
                            units.append({
                                "id": unit_id,
                                "name": unit_name,
                                "material_name": mat_name,
                                "material_id": mat_id,
                                "quantity_per_unit": qty,
                                "description": desc,
                                "available": available,
                                "cost": cost,
                            })
        except Exception as e:
            print(f"Error loading units: {e}")
        return units

    def _load_material_dropdown(self):
        """Load materials for filter dropdown."""
        material_names = sorted(set(u["material_name"] for u in self.units))
        self.material_filter_dropdown.configure(
            values=["All Materials"] + material_names
        )

    def _update_display(self):
        """Update the displayed list based on current filters."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Apply filters
        filtered = self._apply_filters()

        # Populate grid
        for unit in filtered:
            qty = unit.get("quantity_per_unit", 1)
            available = unit.get("available", 0)
            cost = unit.get("cost")
            cost_display = f"${cost:.4f}" if cost is not None else "-"

            values = (
                unit.get("material_name", ""),
                unit.get("name", ""),
                str(qty),
                str(available),
                cost_display,
            )
            self.tree.insert("", "end", iid=str(unit["id"]), values=values)

        # Update status
        count = len(filtered)
        total = len(self.units)
        if count < total:
            self.update_status(f"Showing {count} of {total} units")
        else:
            self.update_status(f"{count} unit{'s' if count != 1 else ''}")

    def _apply_filters(self) -> List[Dict[str, Any]]:
        """Apply search, dropdown filters, and sorting."""
        filtered = self.units

        # Material filter
        mat_filter = self.material_filter_var.get()
        if mat_filter and mat_filter != "All Materials":
            filtered = [u for u in filtered if u.get("material_name") == mat_filter]

        # Search filter
        search_text = normalize_for_search(self.search_entry.get())
        if search_text:
            filtered = [
                u for u in filtered
                if search_text in normalize_for_search(u.get("name", ""))
            ]

        # Apply sorting
        sort_key_map = {
            "material": "material_name",
            "name": "name",
            "qty_per_unit": "quantity_per_unit",
            "available": "available",
            "cost": "cost",
        }
        sort_field = sort_key_map.get(self.sort_column, "name")

        def get_sort_value(u):
            val = u.get(sort_field)
            if sort_field in ("quantity_per_unit", "available", "cost"):
                return val if val is not None else 0
            return (val or "").lower()

        filtered = sorted(filtered, key=get_sort_value, reverse=not self.sort_ascending)

        return filtered

    def _on_search(self, event=None):
        """Handle search entry changes."""
        self._update_display()

    def _on_material_filter_change(self, value: str):
        """Handle material filter change."""
        self._update_display()

    def _clear_filters(self):
        """Clear all filters."""
        self.search_entry.delete(0, "end")
        self.material_filter_var.set("All Materials")
        self._update_display()

    def _on_header_click(self, sort_key: str):
        """Handle column header click for sorting."""
        if self.sort_column == sort_key:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = sort_key
            self.sort_ascending = True
        self._update_display()

    def _on_tree_select(self, event=None):
        """Handle tree selection change."""
        selection = self.tree.selection()
        if selection:
            self.selected_unit_id = int(selection[0])
            self._enable_selection_buttons()
        else:
            self.selected_unit_id = None
            self._disable_selection_buttons()

    def _on_double_click(self, event):
        """Handle double-click to edit."""
        selection = self.tree.selection()
        if selection:
            self.selected_unit_id = int(selection[0])
            self._edit_unit()

    def _enable_selection_buttons(self):
        """Enable buttons that require selection."""
        self.edit_button.configure(state="normal")

    def _disable_selection_buttons(self):
        """Disable buttons that require selection."""
        self.edit_button.configure(state="disabled")

    def _add_unit(self):
        """Open dialog to add a new unit."""
        dialog = MaterialUnitFormDialog(
            self.parent_frame,
            unit=None,
            title="Add Unit",
        )
        self.parent_frame.wait_window(dialog)

        if dialog.result:
            try:
                material_unit_service.create_unit(
                    material_id=dialog.result["material_id"],
                    name=dialog.result["name"],
                    quantity_per_unit=dialog.result["quantity_per_unit"],
                    description=dialog.result.get("description"),
                )
                self.refresh()
                self.update_status(f"Created unit: {dialog.result['name']}")
            except ValidationError as e:
                messagebox.showerror("Error", str(e))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create unit: {e}")

    def _edit_unit(self):
        """Open dialog to edit selected unit."""
        if not self.selected_unit_id:
            return

        # Find unit data by ID
        unit_data = None
        for unit in self.units:
            if unit["id"] == self.selected_unit_id:
                unit_data = unit
                break

        if not unit_data:
            self.update_status("Unit not found")
            return

        dialog = MaterialUnitFormDialog(
            self.parent_frame,
            unit=unit_data,
            title="Edit Unit",
        )
        self.parent_frame.wait_window(dialog)

        if dialog.result:
            try:
                material_unit_service.update_unit(
                    unit_id=dialog.result["id"],
                    material_id=dialog.result["material_id"],
                    quantity_per_unit=dialog.result["quantity_per_unit"],
                    description=dialog.result.get("description"),
                )
                self.refresh()
                self.update_status(f"Updated unit: {dialog.result['name']}")
            except ValidationError as e:
                messagebox.showerror("Error", str(e))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update unit: {e}")

    def update_status(self, message: str):
        """Update the status bar message."""
        self.status_label.configure(text=message)
