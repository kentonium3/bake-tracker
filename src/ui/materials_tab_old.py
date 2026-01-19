"""
Materials tab for the Seasonal Baking Tracker.

Provides CRUD interface for managing materials catalog (ribbons, boxes, bags, tissue)
using the 3-level mandatory hierarchy: Category > Subcategory > Material > Product.
Part of Feature 047: Materials Management System.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import date

from src.services import (
    material_catalog_service,
    material_purchase_service,
    material_unit_service,
    supplier_service,
)
from src.services.exceptions import ValidationError, DatabaseError
from src.utils.constants import PADDING_MEDIUM, PADDING_LARGE


class MaterialsTab(ctk.CTkFrame):
    """
    Materials catalog management tab.

    Provides interface for:
    - Viewing material hierarchy (Category > Subcategory > Material)
    - Managing products for each material
    - Recording purchases and adjusting inventory
    - Creating and managing MaterialUnits
    """

    def __init__(self, parent):
        """Initialize the materials tab."""
        super().__init__(parent)

        self.selected_category_id: Optional[int] = None
        self.selected_subcategory_id: Optional[int] = None
        self.selected_material_id: Optional[int] = None
        self.selected_product_id: Optional[int] = None
        self._data_loaded = False

        # Configure grid - two panels (left: hierarchy, right: details)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=0)  # Title
        self.grid_rowconfigure(1, weight=1)  # Main content
        self.grid_rowconfigure(2, weight=0)  # Status bar

        # Create UI components
        self._create_title()
        self._create_left_panel()
        self._create_right_panel()
        self._create_status_bar()

        # Grid the frame
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Show initial state
        self._show_initial_state()

    def _create_title(self):
        """Create the title label."""
        title_label = ctk.CTkLabel(
            self,
            text="Materials Catalog",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title_label.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            padx=PADDING_LARGE,
            pady=(PADDING_LARGE, PADDING_MEDIUM),
        )

    def _create_left_panel(self):
        """Create the left panel with hierarchy tree."""
        left_frame = ctk.CTkFrame(self)
        left_frame.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(PADDING_LARGE, PADDING_MEDIUM),
            pady=PADDING_MEDIUM,
        )
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(1, weight=1)

        # Toolbar
        toolbar = ctk.CTkFrame(left_frame, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        ctk.CTkButton(toolbar, text="+ Category", command=self._add_category, width=100).pack(
            side="left", padx=2
        )
        ctk.CTkButton(toolbar, text="+ Subcategory", command=self._add_subcategory, width=100).pack(
            side="left", padx=2
        )
        ctk.CTkButton(toolbar, text="+ Material", command=self._add_material, width=100).pack(
            side="left", padx=2
        )
        ctk.CTkButton(toolbar, text="Refresh", command=self.refresh, width=80).pack(
            side="right", padx=2
        )

        # Tree view
        tree_container = ctk.CTkFrame(left_frame)
        tree_container.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        tree_container.grid_columnconfigure(0, weight=1)
        tree_container.grid_rowconfigure(0, weight=1)

        self.hierarchy_tree = ttk.Treeview(tree_container, selectmode="browse", show="tree")
        self.hierarchy_tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            tree_container, orient="vertical", command=self.hierarchy_tree.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.hierarchy_tree.configure(yscrollcommand=scrollbar.set)

        self.hierarchy_tree.bind("<<TreeviewSelect>>", self._on_hierarchy_select)
        self.hierarchy_tree.bind("<Double-1>", self._on_hierarchy_double_click)

    def _create_right_panel(self):
        """Create the right panel with details view."""
        right_frame = ctk.CTkFrame(self)
        right_frame.grid(
            row=1,
            column=1,
            sticky="nsew",
            padx=(PADDING_MEDIUM, PADDING_LARGE),
            pady=PADDING_MEDIUM,
        )
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(0, weight=0)  # Detail header
        right_frame.grid_rowconfigure(1, weight=1)  # Products list
        right_frame.grid_rowconfigure(2, weight=0)  # Units section

        # Detail header
        self.detail_header = ctk.CTkLabel(
            right_frame,
            text="Select a material to view details",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.detail_header.grid(row=0, column=0, sticky="w", padx=10, pady=10)

        # Products section
        products_frame = ctk.CTkFrame(right_frame)
        products_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        products_frame.grid_columnconfigure(0, weight=1)
        products_frame.grid_rowconfigure(1, weight=1)

        # Products toolbar
        products_toolbar = ctk.CTkFrame(products_frame, fg_color="transparent")
        products_toolbar.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(products_toolbar, text="Products", font=ctk.CTkFont(weight="bold")).pack(
            side="left", padx=5
        )
        self.add_product_btn = ctk.CTkButton(
            products_toolbar,
            text="+ Product",
            command=self._add_product,
            width=80,
            state="disabled",
        )
        self.add_product_btn.pack(side="left", padx=5)
        self.record_purchase_btn = ctk.CTkButton(
            products_toolbar,
            text="Record Purchase",
            command=self._record_purchase,
            width=120,
            state="disabled",
        )
        self.record_purchase_btn.pack(side="left", padx=5)
        self.adjust_inventory_btn = ctk.CTkButton(
            products_toolbar,
            text="Adjust Inventory",
            command=self._adjust_inventory,
            width=120,
            state="disabled",
        )
        self.adjust_inventory_btn.pack(side="left", padx=5)

        # Products tree
        products_container = ctk.CTkFrame(products_frame)
        products_container.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        products_container.grid_columnconfigure(0, weight=1)
        products_container.grid_rowconfigure(0, weight=1)

        columns = ("name", "supplier", "inventory", "unit_cost")
        self.products_tree = ttk.Treeview(
            products_container, columns=columns, show="headings", selectmode="browse"
        )
        self.products_tree.heading("name", text="Name")
        self.products_tree.heading("supplier", text="Supplier")
        self.products_tree.heading("inventory", text="Inventory")
        self.products_tree.heading("unit_cost", text="Unit Cost")
        self.products_tree.column("name", width=150)
        self.products_tree.column("supplier", width=100)
        self.products_tree.column("inventory", width=100)
        self.products_tree.column("unit_cost", width=80)
        self.products_tree.grid(row=0, column=0, sticky="nsew")

        products_scrollbar = ttk.Scrollbar(
            products_container, orient="vertical", command=self.products_tree.yview
        )
        products_scrollbar.grid(row=0, column=1, sticky="ns")
        self.products_tree.configure(yscrollcommand=products_scrollbar.set)
        self.products_tree.bind("<<TreeviewSelect>>", self._on_product_select)

        # Units section
        units_frame = ctk.CTkFrame(right_frame)
        units_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        units_frame.grid_columnconfigure(0, weight=1)
        units_frame.grid_rowconfigure(1, weight=1)

        # Units toolbar
        units_toolbar = ctk.CTkFrame(units_frame, fg_color="transparent")
        units_toolbar.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(units_toolbar, text="Material Units", font=ctk.CTkFont(weight="bold")).pack(
            side="left", padx=5
        )
        self.add_unit_btn = ctk.CTkButton(
            units_toolbar, text="+ Unit", command=self._add_unit, width=80, state="disabled"
        )
        self.add_unit_btn.pack(side="left", padx=5)

        # Units tree
        units_container = ctk.CTkFrame(units_frame)
        units_container.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        units_container.grid_columnconfigure(0, weight=1)
        units_container.grid_rowconfigure(0, weight=1)

        unit_columns = ("name", "qty_per_unit", "available", "cost")
        self.units_tree = ttk.Treeview(
            units_container, columns=unit_columns, show="headings", selectmode="browse", height=4
        )
        self.units_tree.heading("name", text="Name")
        self.units_tree.heading("qty_per_unit", text="Qty/Unit")
        self.units_tree.heading("available", text="Available")
        self.units_tree.heading("cost", text="Cost/Unit")
        self.units_tree.column("name", width=150)
        self.units_tree.column("qty_per_unit", width=80)
        self.units_tree.column("available", width=80)
        self.units_tree.column("cost", width=80)
        self.units_tree.grid(row=0, column=0, sticky="nsew")

        units_scrollbar = ttk.Scrollbar(
            units_container, orient="vertical", command=self.units_tree.yview
        )
        units_scrollbar.grid(row=0, column=1, sticky="ns")
        self.units_tree.configure(yscrollcommand=units_scrollbar.set)

    def _create_status_bar(self):
        """Create the status bar."""
        self.status_label = ctk.CTkLabel(self, text="Ready", anchor="w")
        self.status_label.grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=PADDING_LARGE, pady=5
        )

    def _show_initial_state(self):
        """Show initial empty state."""
        self._set_status("Select a material from the hierarchy")

    def _set_status(self, message: str):
        """Update status bar."""
        self.status_label.configure(text=message)

    # =========================================================================
    # Data Loading
    # =========================================================================

    def refresh(self):
        """Refresh all data in the tab."""
        self._load_hierarchy()
        self._clear_details()
        self._set_status("Data refreshed")

    def _load_hierarchy(self):
        """Load the material hierarchy tree."""
        self.hierarchy_tree.delete(*self.hierarchy_tree.get_children())

        try:
            categories = material_catalog_service.list_categories()

            for cat in categories:
                cat_id = f"cat_{cat.id}"
                self.hierarchy_tree.insert("", "end", cat_id, text=cat.name, tags=("category",))

                subcats = material_catalog_service.list_subcategories(cat.id)
                for subcat in subcats:
                    subcat_id = f"subcat_{subcat.id}"
                    self.hierarchy_tree.insert(
                        cat_id, "end", subcat_id, text=subcat.name, tags=("subcategory",)
                    )

                    materials = material_catalog_service.list_materials(subcat.id)
                    for mat in materials:
                        mat_id = f"mat_{mat.id}"
                        product_count = len(mat.products) if mat.products else 0
                        display_text = f"{mat.name} ({product_count} products)"
                        self.hierarchy_tree.insert(
                            subcat_id, "end", mat_id, text=display_text, tags=("material",)
                        )

            self._data_loaded = True

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load hierarchy: {e}")

    def _clear_details(self):
        """Clear the details panel."""
        self.selected_material_id = None
        self.selected_product_id = None
        self.detail_header.configure(text="Select a material to view details")
        self.products_tree.delete(*self.products_tree.get_children())
        self.units_tree.delete(*self.units_tree.get_children())
        self._disable_product_buttons()
        self._disable_unit_buttons()

    def _disable_product_buttons(self):
        """Disable product-related buttons."""
        self.add_product_btn.configure(state="disabled")
        self.record_purchase_btn.configure(state="disabled")
        self.adjust_inventory_btn.configure(state="disabled")

    def _enable_product_buttons(self):
        """Enable product-related buttons."""
        self.add_product_btn.configure(state="normal")

    def _disable_unit_buttons(self):
        """Disable unit-related buttons."""
        self.add_unit_btn.configure(state="disabled")

    def _enable_unit_buttons(self):
        """Enable unit-related buttons."""
        self.add_unit_btn.configure(state="normal")

    # =========================================================================
    # Event Handlers
    # =========================================================================

    def _on_hierarchy_select(self, event):
        """Handle hierarchy tree selection."""
        selection = self.hierarchy_tree.selection()
        if not selection:
            return

        item_id = selection[0]

        if item_id.startswith("mat_"):
            material_id = int(item_id.replace("mat_", ""))
            self._load_material_details(material_id)
        elif item_id.startswith("subcat_"):
            self.selected_subcategory_id = int(item_id.replace("subcat_", ""))
            self._clear_details()
        elif item_id.startswith("cat_"):
            self.selected_category_id = int(item_id.replace("cat_", ""))
            self._clear_details()

    def _on_hierarchy_double_click(self, event):
        """Handle double-click on hierarchy item to edit."""
        selection = self.hierarchy_tree.selection()
        if not selection:
            return

        item_id = selection[0]

        if item_id.startswith("mat_"):
            self._edit_material(int(item_id.replace("mat_", "")))
        elif item_id.startswith("subcat_"):
            self._edit_subcategory(int(item_id.replace("subcat_", "")))
        elif item_id.startswith("cat_"):
            self._edit_category(int(item_id.replace("cat_", "")))

    def _on_product_select(self, event):
        """Handle product selection."""
        selection = self.products_tree.selection()
        if selection:
            self.selected_product_id = int(selection[0])
            self.record_purchase_btn.configure(state="normal")
            self.adjust_inventory_btn.configure(state="normal")
        else:
            self.selected_product_id = None
            self.record_purchase_btn.configure(state="disabled")
            self.adjust_inventory_btn.configure(state="disabled")

    # =========================================================================
    # Material Details
    # =========================================================================

    def _load_material_details(self, material_id: int):
        """Load details for a selected material."""
        try:
            material = material_catalog_service.get_material(material_id=material_id)
            if not material:
                return

            self.selected_material_id = material_id
            self.detail_header.configure(text=f"{material.name} ({material.base_unit})")
            self._enable_product_buttons()
            self._enable_unit_buttons()

            self._load_products(material_id)
            self._load_units(material_id)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load material details: {e}")

    def _load_products(self, material_id: int):
        """Load products for a material."""
        self.products_tree.delete(*self.products_tree.get_children())

        try:
            products = material_catalog_service.list_products(material_id)

            for prod in products:
                supplier_name = prod.supplier.name if prod.supplier else "-"
                inventory = f"{prod.current_inventory:.1f} {prod.material.base_unit if prod.material else ''}"
                unit_cost = f"${prod.weighted_avg_cost:.4f}" if prod.weighted_avg_cost else "-"

                self.products_tree.insert(
                    "",
                    "end",
                    str(prod.id),
                    values=(prod.display_name, supplier_name, inventory, unit_cost),
                )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load products: {e}")

    def _load_units(self, material_id: int):
        """Load MaterialUnits for a material."""
        self.units_tree.delete(*self.units_tree.get_children())

        try:
            units = material_unit_service.list_units(material_id)

            for unit in units:
                try:
                    available = material_unit_service.get_available_inventory(unit.id)
                    cost = material_unit_service.get_current_cost(unit.id)
                    cost_str = f"${cost:.4f}" if cost else "-"
                except Exception:
                    available = 0
                    cost_str = "-"

                self.units_tree.insert(
                    "",
                    "end",
                    str(unit.id),
                    values=(unit.name, f"{unit.quantity_per_unit:.1f}", str(available), cost_str),
                )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load units: {e}")

    # =========================================================================
    # CRUD Operations - Categories
    # =========================================================================

    def _add_category(self):
        """Add a new category."""
        dialog = CategoryDialog(self, title="Add Category")
        if dialog.result:
            try:
                material_catalog_service.create_category(dialog.result["name"])
                self.refresh()
                self._set_status(f"Category '{dialog.result['name']}' created")
            except ValidationError as e:
                messagebox.showerror("Validation Error", str(e))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create category: {e}")

    def _edit_category(self, category_id: int):
        """Edit a category."""
        try:
            category = material_catalog_service.get_category(category_id=category_id)
            if not category:
                return

            dialog = CategoryDialog(
                self, title="Edit Category", initial_data={"name": category.name}
            )
            if dialog.result:
                material_catalog_service.update_category(category_id, name=dialog.result["name"])
                self.refresh()
                self._set_status(f"Category updated")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update category: {e}")

    # =========================================================================
    # CRUD Operations - Subcategories
    # =========================================================================

    def _add_subcategory(self):
        """Add a new subcategory."""
        # Need to select a category first
        selection = self.hierarchy_tree.selection()
        if not selection:
            messagebox.showwarning("Selection Required", "Please select a category first")
            return

        item_id = selection[0]
        if item_id.startswith("cat_"):
            category_id = int(item_id.replace("cat_", ""))
        elif item_id.startswith("subcat_"):
            # Get parent category
            parent = self.hierarchy_tree.parent(item_id)
            category_id = int(parent.replace("cat_", ""))
        else:
            messagebox.showwarning("Selection Required", "Please select a category or subcategory")
            return

        dialog = SubcategoryDialog(self, title="Add Subcategory")
        if dialog.result:
            try:
                material_catalog_service.create_subcategory(category_id, dialog.result["name"])
                self.refresh()
                self._set_status(f"Subcategory '{dialog.result['name']}' created")
            except ValidationError as e:
                messagebox.showerror("Validation Error", str(e))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create subcategory: {e}")

    def _edit_subcategory(self, subcategory_id: int):
        """Edit a subcategory."""
        try:
            subcat = material_catalog_service.get_subcategory(subcategory_id=subcategory_id)
            if not subcat:
                return

            dialog = SubcategoryDialog(
                self, title="Edit Subcategory", initial_data={"name": subcat.name}
            )
            if dialog.result:
                material_catalog_service.update_subcategory(
                    subcategory_id, name=dialog.result["name"]
                )
                self.refresh()
                self._set_status(f"Subcategory updated")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update subcategory: {e}")

    # =========================================================================
    # CRUD Operations - Materials
    # =========================================================================

    def _add_material(self):
        """Add a new material."""
        selection = self.hierarchy_tree.selection()
        if not selection:
            messagebox.showwarning("Selection Required", "Please select a subcategory first")
            return

        item_id = selection[0]
        if item_id.startswith("subcat_"):
            subcategory_id = int(item_id.replace("subcat_", ""))
        elif item_id.startswith("mat_"):
            # Get parent subcategory
            parent = self.hierarchy_tree.parent(item_id)
            subcategory_id = int(parent.replace("subcat_", ""))
        else:
            messagebox.showwarning("Selection Required", "Please select a subcategory or material")
            return

        dialog = MaterialDialog(self, title="Add Material")
        if dialog.result:
            try:
                material_catalog_service.create_material(
                    subcategory_id,
                    dialog.result["name"],
                    dialog.result["base_unit"],
                )
                self.refresh()
                self._set_status(f"Material '{dialog.result['name']}' created")
            except ValidationError as e:
                messagebox.showerror("Validation Error", str(e))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create material: {e}")

    def _edit_material(self, material_id: int):
        """Edit a material."""
        try:
            material = material_catalog_service.get_material(material_id=material_id)
            if not material:
                return

            dialog = MaterialDialog(
                self,
                title="Edit Material",
                initial_data={"name": material.name, "base_unit": material.base_unit},
            )
            if dialog.result:
                material_catalog_service.update_material(material_id, name=dialog.result["name"])
                self.refresh()
                self._set_status(f"Material updated")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update material: {e}")

    # =========================================================================
    # CRUD Operations - Products
    # =========================================================================

    def _add_product(self):
        """Add a new product."""
        if not self.selected_material_id:
            return

        try:
            suppliers = supplier_service.get_all_suppliers()
            supplier_names = [s["name"] for s in suppliers]
            supplier_map = {s["name"]: s["id"] for s in suppliers}

            dialog = ProductDialog(self, title="Add Product", suppliers=supplier_names)
            if dialog.result:
                supplier_id = (
                    supplier_map.get(dialog.result["supplier"])
                    if dialog.result["supplier"]
                    else None
                )
                material_catalog_service.create_product(
                    material_id=self.selected_material_id,
                    name=dialog.result["name"],
                    package_quantity=dialog.result["package_quantity"],
                    package_unit=dialog.result["package_unit"],
                    supplier_id=supplier_id,
                )
                self._load_products(self.selected_material_id)
                self.refresh()
                self._set_status(f"Product '{dialog.result['name']}' created")
        except ValidationError as e:
            messagebox.showerror("Validation Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create product: {e}")

    # =========================================================================
    # Purchase Recording
    # =========================================================================

    def _record_purchase(self):
        """Record a purchase for selected product."""
        if not self.selected_product_id:
            messagebox.showwarning("Selection Required", "Please select a product first")
            return

        try:
            suppliers = supplier_service.get_all_suppliers()
            supplier_names = [s["name"] for s in suppliers]
            supplier_map = {s["name"]: s["id"] for s in suppliers}

            dialog = PurchaseDialog(self, title="Record Purchase", suppliers=supplier_names)
            if dialog.result:
                supplier_id = supplier_map.get(dialog.result["supplier"])
                if not supplier_id:
                    messagebox.showerror("Error", "Please select a supplier")
                    return

                material_purchase_service.record_purchase(
                    product_id=self.selected_product_id,
                    supplier_id=supplier_id,
                    purchase_date=dialog.result["date"],
                    packages_purchased=dialog.result["packages"],
                    package_price=Decimal(str(dialog.result["price"])),
                    notes=dialog.result.get("notes"),
                )
                self._load_products(self.selected_material_id)
                self._load_units(self.selected_material_id)
                self._set_status("Purchase recorded successfully")
        except ValidationError as e:
            messagebox.showerror("Validation Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to record purchase: {e}")

    # =========================================================================
    # Inventory Adjustment
    # =========================================================================

    def _adjust_inventory(self):
        """Adjust inventory for selected product."""
        if not self.selected_product_id:
            messagebox.showwarning("Selection Required", "Please select a product first")
            return

        dialog = AdjustInventoryDialog(self, title="Adjust Inventory")
        if dialog.result:
            try:
                if dialog.result["mode"] == "set":
                    material_purchase_service.adjust_inventory(
                        product_id=self.selected_product_id,
                        new_quantity=dialog.result["value"],
                        notes=dialog.result.get("notes"),
                    )
                else:  # percentage
                    material_purchase_service.adjust_inventory(
                        product_id=self.selected_product_id,
                        percentage=dialog.result["value"],
                        notes=dialog.result.get("notes"),
                    )
                self._load_products(self.selected_material_id)
                self._load_units(self.selected_material_id)
                self._set_status("Inventory adjusted successfully")
            except ValidationError as e:
                messagebox.showerror("Validation Error", str(e))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to adjust inventory: {e}")

    # =========================================================================
    # MaterialUnit Operations
    # =========================================================================

    def _add_unit(self):
        """Add a new MaterialUnit."""
        if not self.selected_material_id:
            return

        dialog = UnitDialog(self, title="Add Material Unit")
        if dialog.result:
            try:
                material_unit_service.create_unit(
                    material_id=self.selected_material_id,
                    name=dialog.result["name"],
                    quantity_per_unit=dialog.result["quantity_per_unit"],
                    description=dialog.result.get("description"),
                )
                self._load_units(self.selected_material_id)
                self._set_status(f"Unit '{dialog.result['name']}' created")
            except ValidationError as e:
                messagebox.showerror("Validation Error", str(e))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create unit: {e}")


# =============================================================================
# Dialog Classes
# =============================================================================


class CategoryDialog(ctk.CTkToplevel):
    """Dialog for creating/editing categories."""

    def __init__(self, parent, title: str, initial_data: dict = None):
        super().__init__(parent)
        self.title(title)
        self.geometry("300x150")
        self.result = None

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Form
        ctk.CTkLabel(self, text="Category Name:").pack(padx=20, pady=(20, 5))
        self.name_entry = ctk.CTkEntry(self, width=250)
        self.name_entry.pack(padx=20, pady=5)

        if initial_data:
            self.name_entry.insert(0, initial_data.get("name", ""))

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Save", command=self._save).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)

        self.wait_window()

    def _save(self):
        name = self.name_entry.get().strip()
        if name:
            self.result = {"name": name}
        self.destroy()


class SubcategoryDialog(CategoryDialog):
    """Dialog for creating/editing subcategories (same as category)."""

    pass


class MaterialDialog(ctk.CTkToplevel):
    """Dialog for creating/editing materials."""

    BASE_UNITS = ["linear_inches", "each", "sheets", "sq_inches"]

    def __init__(self, parent, title: str, initial_data: dict = None):
        super().__init__(parent)
        self.title(title)
        self.geometry("350x200")
        self.result = None

        self.transient(parent)
        self.grab_set()

        # Name
        ctk.CTkLabel(self, text="Material Name:").pack(padx=20, pady=(20, 5))
        self.name_entry = ctk.CTkEntry(self, width=300)
        self.name_entry.pack(padx=20, pady=5)

        # Base Unit
        ctk.CTkLabel(self, text="Base Unit:").pack(padx=20, pady=(10, 5))
        self.unit_var = ctk.StringVar(value=self.BASE_UNITS[0])
        self.unit_dropdown = ctk.CTkOptionMenu(
            self, values=self.BASE_UNITS, variable=self.unit_var, width=300
        )
        self.unit_dropdown.pack(padx=20, pady=5)

        if initial_data:
            self.name_entry.insert(0, initial_data.get("name", ""))
            if initial_data.get("base_unit") in self.BASE_UNITS:
                self.unit_var.set(initial_data["base_unit"])

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Save", command=self._save).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)

        self.wait_window()

    def _save(self):
        name = self.name_entry.get().strip()
        if name:
            self.result = {"name": name, "base_unit": self.unit_var.get()}
        self.destroy()


class ProductDialog(ctk.CTkToplevel):
    """Dialog for creating products."""

    def __init__(self, parent, title: str, suppliers: List[str]):
        super().__init__(parent)
        self.title(title)
        self.geometry("400x300")
        self.result = None

        self.transient(parent)
        self.grab_set()

        # Name
        ctk.CTkLabel(self, text="Product Name:").pack(padx=20, pady=(20, 5))
        self.name_entry = ctk.CTkEntry(self, width=350)
        self.name_entry.pack(padx=20, pady=5)

        # Package Quantity
        ctk.CTkLabel(self, text="Package Quantity:").pack(padx=20, pady=(10, 5))
        self.qty_entry = ctk.CTkEntry(self, width=350)
        self.qty_entry.pack(padx=20, pady=5)

        # Package Unit
        ctk.CTkLabel(self, text="Package Unit:").pack(padx=20, pady=(10, 5))
        self.unit_entry = ctk.CTkEntry(self, width=350)
        self.unit_entry.insert(0, "inches")
        self.unit_entry.pack(padx=20, pady=5)

        # Supplier
        ctk.CTkLabel(self, text="Supplier:").pack(padx=20, pady=(10, 5))
        self.supplier_var = ctk.StringVar(value=suppliers[0] if suppliers else "")
        self.supplier_dropdown = ctk.CTkOptionMenu(
            self, values=suppliers or ["(none)"], variable=self.supplier_var, width=350
        )
        self.supplier_dropdown.pack(padx=20, pady=5)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Save", command=self._save).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)

        self.wait_window()

    def _save(self):
        name = self.name_entry.get().strip()
        qty_str = self.qty_entry.get().strip()
        try:
            qty = float(qty_str)
            if name and qty > 0:
                self.result = {
                    "name": name,
                    "package_quantity": qty,
                    "package_unit": self.unit_entry.get().strip(),
                    "supplier": self.supplier_var.get(),
                }
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity")
            return
        self.destroy()


class PurchaseDialog(ctk.CTkToplevel):
    """Dialog for recording purchases."""

    def __init__(self, parent, title: str, suppliers: List[str]):
        super().__init__(parent)
        self.title(title)
        self.geometry("400x350")
        self.result = None

        self.transient(parent)
        self.grab_set()

        # Supplier
        ctk.CTkLabel(self, text="Supplier:").pack(padx=20, pady=(20, 5))
        self.supplier_var = ctk.StringVar(value=suppliers[0] if suppliers else "")
        self.supplier_dropdown = ctk.CTkOptionMenu(
            self, values=suppliers or ["(none)"], variable=self.supplier_var, width=350
        )
        self.supplier_dropdown.pack(padx=20, pady=5)

        # Date
        ctk.CTkLabel(self, text="Purchase Date (YYYY-MM-DD):").pack(padx=20, pady=(10, 5))
        self.date_entry = ctk.CTkEntry(self, width=350)
        self.date_entry.insert(0, date.today().isoformat())
        self.date_entry.pack(padx=20, pady=5)

        # Packages
        ctk.CTkLabel(self, text="Number of Packages:").pack(padx=20, pady=(10, 5))
        self.packages_entry = ctk.CTkEntry(self, width=350)
        self.packages_entry.pack(padx=20, pady=5)

        # Price
        ctk.CTkLabel(self, text="Total Price ($):").pack(padx=20, pady=(10, 5))
        self.price_entry = ctk.CTkEntry(self, width=350)
        self.price_entry.pack(padx=20, pady=5)

        # Notes
        ctk.CTkLabel(self, text="Notes (optional):").pack(padx=20, pady=(10, 5))
        self.notes_entry = ctk.CTkEntry(self, width=350)
        self.notes_entry.pack(padx=20, pady=5)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Save", command=self._save).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)

        self.wait_window()

    def _save(self):
        try:
            date_str = self.date_entry.get().strip()
            purchase_date = date.fromisoformat(date_str)
            packages = int(self.packages_entry.get().strip())
            price = float(self.price_entry.get().strip())

            if packages > 0 and price >= 0:
                self.result = {
                    "supplier": self.supplier_var.get(),
                    "date": purchase_date,
                    "packages": packages,
                    "price": price,
                    "notes": self.notes_entry.get().strip() or None,
                }
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
            return
        self.destroy()


class AdjustInventoryDialog(ctk.CTkToplevel):
    """Dialog for adjusting inventory."""

    def __init__(self, parent, title: str):
        super().__init__(parent)
        self.title(title)
        self.geometry("350x250")
        self.result = None

        self.transient(parent)
        self.grab_set()

        # Mode selection
        ctk.CTkLabel(self, text="Adjustment Type:").pack(padx=20, pady=(20, 5))
        self.mode_var = ctk.StringVar(value="set")
        ctk.CTkRadioButton(
            self, text="Set to specific value", variable=self.mode_var, value="set"
        ).pack(padx=20, pady=2, anchor="w")
        ctk.CTkRadioButton(
            self, text="Set to percentage", variable=self.mode_var, value="percentage"
        ).pack(padx=20, pady=2, anchor="w")

        # Value
        ctk.CTkLabel(self, text="Value:").pack(padx=20, pady=(10, 5))
        self.value_entry = ctk.CTkEntry(self, width=300)
        self.value_entry.pack(padx=20, pady=5)

        # Notes
        ctk.CTkLabel(self, text="Notes (optional):").pack(padx=20, pady=(10, 5))
        self.notes_entry = ctk.CTkEntry(self, width=300)
        self.notes_entry.pack(padx=20, pady=5)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Save", command=self._save).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)

        self.wait_window()

    def _save(self):
        try:
            value = float(self.value_entry.get().strip())
            self.result = {
                "mode": self.mode_var.get(),
                "value": value,
                "notes": self.notes_entry.get().strip() or None,
            }
        except ValueError:
            messagebox.showerror("Error", "Invalid value")
            return
        self.destroy()


class UnitDialog(ctk.CTkToplevel):
    """Dialog for creating MaterialUnits."""

    def __init__(self, parent, title: str):
        super().__init__(parent)
        self.title(title)
        self.geometry("350x250")
        self.result = None

        self.transient(parent)
        self.grab_set()

        # Name
        ctk.CTkLabel(self, text="Unit Name:").pack(padx=20, pady=(20, 5))
        self.name_entry = ctk.CTkEntry(self, width=300)
        self.name_entry.pack(padx=20, pady=5)

        # Quantity per unit
        ctk.CTkLabel(self, text="Quantity per Unit (base units consumed):").pack(
            padx=20, pady=(10, 5)
        )
        self.qty_entry = ctk.CTkEntry(self, width=300)
        self.qty_entry.pack(padx=20, pady=5)

        # Description
        ctk.CTkLabel(self, text="Description (optional):").pack(padx=20, pady=(10, 5))
        self.desc_entry = ctk.CTkEntry(self, width=300)
        self.desc_entry.pack(padx=20, pady=5)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Save", command=self._save).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)

        self.wait_window()

    def _save(self):
        name = self.name_entry.get().strip()
        try:
            qty = float(self.qty_entry.get().strip())
            if name and qty > 0:
                self.result = {
                    "name": name,
                    "quantity_per_unit": qty,
                    "description": self.desc_entry.get().strip() or None,
                }
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity")
            return
        self.destroy()
