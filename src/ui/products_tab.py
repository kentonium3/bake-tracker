"""
Products tab for displaying and managing the product catalog.

Provides interface for:
- Viewing products with filters (ingredient, category, supplier, search)
- Adding new products
- Editing product details
- Hiding/unhiding products (soft delete)
- Viewing purchase history
- Managing suppliers
"""

import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from typing import Optional, List, Dict, Any

from src.services import (
    product_catalog_service,
    supplier_service,
    ingredient_service,
    ingredient_hierarchy_service,
)


class ProductsTab(ctk.CTkFrame):
    """
    Products tab for product catalog management.

    Displays products in a grid with:
    - Toolbar with Add Product and Refresh buttons
    - Filters for Ingredient, Category, and Supplier
    - Search box for text search
    - Show Hidden checkbox for visibility toggle
    - Treeview grid displaying product list
    - Double-click to open product detail
    - Context menu for Edit/Hide/Delete actions
    """

    def __init__(self, parent):
        """Initialize the products tab."""
        super().__init__(parent)

        # State
        self.products: List[Dict[str, Any]] = []
        self.ingredients: List[Dict[str, Any]] = []
        self.suppliers: List[Dict[str, Any]] = []
        self._data_loaded = False
        # Feature 032: Hierarchy filter state
        self._l0_map: Dict[str, Dict[str, Any]] = {}  # L0 name -> ingredient dict
        self._l1_map: Dict[str, Dict[str, Any]] = {}  # L1 name -> ingredient dict
        self._l2_map: Dict[str, Dict[str, Any]] = {}  # L2 name -> ingredient dict
        self._hierarchy_path_cache: Dict[int, str] = {}  # ingredient_id -> path string

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Header - fixed height
        self.grid_rowconfigure(1, weight=0)  # Toolbar - fixed height
        self.grid_rowconfigure(2, weight=0)  # Filters - fixed height
        self.grid_rowconfigure(3, weight=0)  # Search - fixed height
        self.grid_rowconfigure(4, weight=1)  # Grid - expandable

        # Create UI components
        self._create_header()
        self._create_toolbar()
        self._create_filters()
        self._create_search()
        self._create_grid()

        # Configure parent to expand
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        # Grid the frame to fill parent
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Show loading state - data loaded on tab selection
        self._show_initial_state()

    def _create_header(self):
        """Create the header with title."""
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header_frame,
            text="Product Catalog",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        subtitle = ctk.CTkLabel(
            header_frame,
            text="Manage products, suppliers, and purchase history",
            font=ctk.CTkFont(size=12),
        )
        subtitle.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")

    def _create_toolbar(self):
        """Create toolbar with action buttons."""
        toolbar_frame = ctk.CTkFrame(self)
        toolbar_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        # Add Product button
        self.add_btn = ctk.CTkButton(
            toolbar_frame,
            text="Add Product",
            command=self._on_add_product,
            width=120,
        )
        self.add_btn.pack(side="left", padx=5, pady=5)

    def _create_filters(self):
        """Create filter controls with cascading hierarchy filters."""
        filter_frame = ctk.CTkFrame(self)
        filter_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        # Feature 032: Cascading hierarchy filters (L0 -> L1 -> L2)
        # L0 (Root Category) filter
        l0_label = ctk.CTkLabel(filter_frame, text="Category:")
        l0_label.pack(side="left", padx=(5, 2), pady=5)

        self.l0_filter_var = ctk.StringVar(value="All Categories")
        self.l0_filter_dropdown = ctk.CTkOptionMenu(
            filter_frame,
            variable=self.l0_filter_var,
            values=["All Categories"],
            command=self._on_l0_filter_change,
            width=150,
        )
        self.l0_filter_dropdown.pack(side="left", padx=5, pady=5)

        # L1 (Subcategory) filter - initially disabled
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

        # L2 (Leaf Ingredient) filter - initially disabled
        l2_label = ctk.CTkLabel(filter_frame, text="Ingredient:")
        l2_label.pack(side="left", padx=(10, 2), pady=5)

        self.l2_filter_var = ctk.StringVar(value="All")
        self.l2_filter_dropdown = ctk.CTkOptionMenu(
            filter_frame,
            variable=self.l2_filter_var,
            values=["All"],
            command=self._on_filter_change,
            width=150,
            state="disabled",
        )
        self.l2_filter_dropdown.pack(side="left", padx=5, pady=5)

        # Brand filter
        brand_label = ctk.CTkLabel(filter_frame, text="Brand:")
        brand_label.pack(side="left", padx=(15, 2), pady=5)

        self.brand_var = ctk.StringVar(value="All")
        self.brand_dropdown = ctk.CTkOptionMenu(
            filter_frame,
            variable=self.brand_var,
            values=["All"],
            command=self._on_filter_change,
            width=150,
        )
        self.brand_dropdown.pack(side="left", padx=5, pady=5)

        # Supplier filter
        sup_label = ctk.CTkLabel(filter_frame, text="Supplier:")
        sup_label.pack(side="left", padx=(15, 2), pady=5)

        self.supplier_var = ctk.StringVar(value="All")
        self.supplier_dropdown = ctk.CTkOptionMenu(
            filter_frame,
            variable=self.supplier_var,
            values=["All"],
            command=self._on_filter_change,
            width=150,
        )
        self.supplier_dropdown.pack(side="left", padx=5, pady=5)

    def _create_search(self):
        """Create search box and Show Hidden checkbox."""
        search_frame = ctk.CTkFrame(self)
        search_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew")

        # Search label and entry
        search_label = ctk.CTkLabel(search_frame, text="Search:")
        search_label.pack(side="left", padx=(5, 2), pady=5)

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._on_search_change)
        self.search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            width=250,
            placeholder_text="Search products...",
        )
        self.search_entry.pack(side="left", padx=5, pady=5)

        # Show Hidden checkbox
        self.show_hidden_var = ctk.BooleanVar(value=False)
        self.show_hidden_cb = ctk.CTkCheckBox(
            search_frame,
            text="Show Hidden",
            variable=self.show_hidden_var,
            command=self._on_filter_change,
        )
        self.show_hidden_cb.pack(side="left", padx=20, pady=5)

        # Product count label
        self.count_label = ctk.CTkLabel(
            search_frame,
            text="",
            font=ctk.CTkFont(size=12),
        )
        self.count_label.pack(side="right", padx=10, pady=5)

    def _create_grid(self):
        """Create the product grid using ttk.Treeview."""
        # Container frame for grid and scrollbar
        grid_container = ctk.CTkFrame(self)
        grid_container.grid(row=4, column=0, padx=10, pady=5, sticky="nsew")
        grid_container.grid_columnconfigure(0, weight=1)
        grid_container.grid_rowconfigure(0, weight=1)

        # Define columns - Feature 032: hierarchy_path replaces category
        columns = (
            "hierarchy_path",
            "product_name",
            "brand",
            "package",
            "supplier",
        )
        self.tree = ttk.Treeview(
            grid_container,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        # Configure column headings
        self.tree.heading("hierarchy_path", text="Ingredient Hierarchy", anchor="w")
        self.tree.heading("product_name", text="Product", anchor="w")
        self.tree.heading("brand", text="Brand", anchor="w")
        self.tree.heading("package", text="Package", anchor="w")
        self.tree.heading("supplier", text="Supplier", anchor="w")

        # Configure column widths
        self.tree.column("hierarchy_path", width=280, minwidth=200)
        self.tree.column("product_name", width=180, minwidth=120)
        self.tree.column("brand", width=120, minwidth=80)
        self.tree.column("package", width=100, minwidth=80)
        self.tree.column("supplier", width=150, minwidth=100)

        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(
            grid_container,
            orient="vertical",
            command=self.tree.yview,
        )
        x_scrollbar = ttk.Scrollbar(
            grid_container,
            orient="horizontal",
            command=self.tree.xview,
        )
        self.tree.configure(
            yscrollcommand=y_scrollbar.set,
            xscrollcommand=x_scrollbar.set,
        )

        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar.grid(row=1, column=0, sticky="ew")

        # Configure tag for hidden products (grayed out)
        self.tree.tag_configure("hidden", foreground="gray")

        # Bind events
        self.tree.bind("<Double-1>", self._on_product_double_click)
        self.tree.bind("<Button-3>", self._on_right_click)  # Right-click (macOS/Linux)
        self.tree.bind("<Button-2>", self._on_right_click)  # Middle-click (some systems)

    def _show_initial_state(self):
        """Show initial loading state."""
        # Clear any existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.count_label.configure(text="Loading products...")

    def refresh(self):
        """Refresh product list and filter dropdowns from database."""
        try:
            # Load filter data
            self._load_filter_data()

            # Load products
            self._load_products()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to load products: {str(e)}",
                parent=self,
            )

    def _load_filter_data(self):
        """Load data for filter dropdowns."""
        try:
            # Load ingredients for cache
            self.ingredients = ingredient_service.get_all_ingredients()

            # Feature 032: Populate L0 (root categories) dropdown
            root_ingredients = ingredient_hierarchy_service.get_root_ingredients()
            self._l0_map = {ing.get("display_name", ing.get("name", "?")): ing for ing in root_ingredients}
            l0_values = ["All Categories"] + sorted(self._l0_map.keys())
            self.l0_filter_dropdown.configure(values=l0_values)

            # Reset L1 and L2 dropdowns
            self._l1_map = {}
            self._l2_map = {}
            self.l1_filter_dropdown.configure(values=["All"], state="disabled")
            self.l2_filter_dropdown.configure(values=["All"], state="disabled")
            self.l1_filter_var.set("All")
            self.l2_filter_var.set("All")

            # Build hierarchy path cache
            self._build_hierarchy_path_cache()

            # Load all products to extract unique brands
            all_products = product_catalog_service.get_products(include_hidden=True)
            self.brands = sorted(set(
                p.get("brand", "")
                for p in all_products
                if p.get("brand")
            ))
            brand_values = ["All"] + self.brands
            self.brand_dropdown.configure(values=brand_values)

            # Load active suppliers
            self.suppliers = supplier_service.get_active_suppliers()
            supplier_names = ["All"] + [sup["name"] for sup in self.suppliers]
            self.supplier_dropdown.configure(values=supplier_names)

        except Exception as e:
            # Log error but continue - filters will have limited options
            print(f"Warning: Failed to load filter data: {e}")

    def _load_products(self):
        """Load and display products based on current filters."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Build filter params
        params: Dict[str, Any] = {
            "include_hidden": self.show_hidden_var.get(),
        }

        # Add supplier filter
        if self.supplier_var.get() != "All":
            supplier = self._get_supplier_by_name(self.supplier_var.get())
            if supplier:
                params["supplier_id"] = supplier["id"]

        # Add search
        search = self.search_var.get().strip()
        if search:
            params["search"] = search

        # Fetch products from service
        try:
            self.products = product_catalog_service.get_products(**params)
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to fetch products: {str(e)}",
                parent=self,
            )
            self.products = []

        # Apply brand filter (not supported by service, filter in UI)
        if self.brand_var.get() != "All":
            selected_brand = self.brand_var.get()
            self.products = [p for p in self.products if p.get("brand") == selected_brand]

        # Feature 032: Apply hierarchy filters
        self.products = self._apply_hierarchy_filters(self.products)

        # Populate grid - Feature 032: hierarchy_path replaces category
        for p in self.products:
            # Build package display string (e.g., "28 oz can")
            pkg_qty = p.get("package_unit_quantity", "")
            pkg_unit = p.get("package_unit", "")
            pkg_type = p.get("package_type", "")
            if pkg_qty and pkg_unit:
                # Format quantity nicely (remove .0 for whole numbers)
                if isinstance(pkg_qty, float) and pkg_qty == int(pkg_qty):
                    pkg_qty = int(pkg_qty)
                package_display = f"{pkg_qty} {pkg_unit}"
                if pkg_type:
                    package_display += f" {pkg_type}"
            else:
                package_display = ""

            # Feature 032: Get hierarchy path for display
            ingredient_id = p.get("ingredient_id")
            hierarchy_path = self._hierarchy_path_cache.get(ingredient_id, "--")

            values = (
                hierarchy_path,
                p.get("product_name", ""),
                p.get("brand", ""),
                package_display,
                p.get("preferred_supplier_name", "") or "",
            )
            tags = ("hidden",) if p.get("is_hidden") else ()
            self.tree.insert("", "end", iid=str(p["id"]), values=values, tags=tags)

        # Update count label
        visible_count = len([p for p in self.products if not p.get("is_hidden")])
        hidden_count = len([p for p in self.products if p.get("is_hidden")])

        if hidden_count > 0 and self.show_hidden_var.get():
            self.count_label.configure(
                text=f"{visible_count} products ({hidden_count} hidden)"
            )
        else:
            self.count_label.configure(text=f"{len(self.products)} products")

    def _get_ingredient_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find ingredient by name."""
        return next(
            (ing for ing in self.ingredients if ing["name"] == name),
            None,
        )

    def _get_supplier_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find supplier by name."""
        return next(
            (sup for sup in self.suppliers if sup["name"] == name),
            None,
        )

    def _on_filter_change(self, *args):
        """Handle filter dropdown or checkbox change."""
        self._load_products()

    # Feature 032: Hierarchy filter and path helper methods
    def _build_hierarchy_path_cache(self):
        """Build cache mapping ingredient_id to hierarchy path string."""
        self._hierarchy_path_cache = {}
        for ingredient in self.ingredients:
            ing_id = ingredient.get("id")
            if not ing_id:
                continue
            try:
                ancestors = ingredient_hierarchy_service.get_ancestors(ing_id)
                # Build path from root to leaf
                path_parts = []
                for ancestor in reversed(ancestors):
                    path_parts.append(ancestor.get("display_name", "?"))
                path_parts.append(ingredient.get("display_name", ingredient.get("name", "?")))
                self._hierarchy_path_cache[ing_id] = " -> ".join(path_parts)
            except Exception:
                self._hierarchy_path_cache[ing_id] = ingredient.get("display_name", "--")

    def _on_l0_filter_change(self, value: str):
        """Handle L0 (category) filter change - cascade to L1."""
        if value == "All Categories":
            # Reset L1 and L2
            self._l1_map = {}
            self._l2_map = {}
            self.l1_filter_dropdown.configure(values=["All"], state="disabled")
            self.l2_filter_dropdown.configure(values=["All"], state="disabled")
            self.l1_filter_var.set("All")
            self.l2_filter_var.set("All")
        elif value in self._l0_map:
            # Populate L1 with children of selected L0
            l0_id = self._l0_map[value].get("id")
            subcategories = ingredient_hierarchy_service.get_children(l0_id)
            self._l1_map = {sub.get("display_name", "?"): sub for sub in subcategories}
            if subcategories:
                l1_values = ["All"] + sorted(self._l1_map.keys())
                self.l1_filter_dropdown.configure(values=l1_values, state="normal")
            else:
                self.l1_filter_dropdown.configure(values=["All"], state="disabled")
            self.l1_filter_var.set("All")
            # Reset L2
            self._l2_map = {}
            self.l2_filter_dropdown.configure(values=["All"], state="disabled")
            self.l2_filter_var.set("All")
        self._load_products()

    def _on_l1_filter_change(self, value: str):
        """Handle L1 (subcategory) filter change - cascade to L2."""
        if value == "All":
            # Reset L2
            self._l2_map = {}
            self.l2_filter_dropdown.configure(values=["All"], state="disabled")
            self.l2_filter_var.set("All")
        elif value in self._l1_map:
            # Populate L2 with children of selected L1
            l1_id = self._l1_map[value].get("id")
            leaves = ingredient_hierarchy_service.get_children(l1_id)
            self._l2_map = {leaf.get("display_name", "?"): leaf for leaf in leaves}
            if leaves:
                l2_values = ["All"] + sorted(self._l2_map.keys())
                self.l2_filter_dropdown.configure(values=l2_values, state="normal")
            else:
                self.l2_filter_dropdown.configure(values=["All"], state="disabled")
            self.l2_filter_var.set("All")
        self._load_products()

    def _apply_hierarchy_filters(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply hierarchy filters to product list."""
        l0_val = self.l0_filter_var.get()
        l1_val = self.l1_filter_var.get()
        l2_val = self.l2_filter_var.get()

        # If all filters are "All", return unfiltered
        if l0_val == "All Categories" and l1_val == "All" and l2_val == "All":
            return products

        # Build set of matching ingredient IDs
        matching_ids = None

        if l2_val != "All" and l2_val in self._l2_map:
            # Exact L2 ingredient match
            matching_ids = {self._l2_map[l2_val].get("id")}
        elif l1_val != "All" and l1_val in self._l1_map:
            # All L2 descendants under this L1
            l1_id = self._l1_map[l1_val].get("id")
            matching_ids = self._get_all_leaf_descendants(l1_id)
        elif l0_val != "All Categories" and l0_val in self._l0_map:
            # All L2 descendants under this L0
            l0_id = self._l0_map[l0_val].get("id")
            matching_ids = self._get_all_leaf_descendants(l0_id)

        if matching_ids is None:
            return products

        return [p for p in products if p.get("ingredient_id") in matching_ids]

    def _get_all_leaf_descendants(self, parent_id: int) -> set:
        """Get all leaf (L2) ingredient IDs under a parent."""
        descendants = set()
        try:
            children = ingredient_hierarchy_service.get_children(parent_id)
            for child in children:
                level = child.get("hierarchy_level", 2)
                if level == 2:
                    # This is a leaf
                    descendants.add(child.get("id"))
                else:
                    # Recurse to get leaves under this node
                    descendants.update(self._get_all_leaf_descendants(child.get("id")))
        except Exception:
            pass
        return descendants

    def _on_search_change(self, *args):
        """Handle search text change."""
        # Debounce could be added here for performance
        self._load_products()

    def _on_add_product(self):
        """Open dialog to add new product."""
        from src.ui.forms.add_product_dialog import AddProductDialog

        dialog = AddProductDialog(self)
        self.wait_window(dialog)

        if dialog.result:
            self._load_products()

    def _on_product_double_click(self, event):
        """Handle double-click on product row."""
        selection = self.tree.selection()
        if selection:
            product_id = int(selection[0])
            self._open_product_detail(product_id)

    def _open_product_detail(self, product_id: int):
        """Open product detail dialog."""
        from src.ui.forms.product_detail_dialog import ProductDetailDialog

        dialog = ProductDetailDialog(self, product_id=product_id)
        self.wait_window(dialog)

        if dialog.result:
            self._load_products()

    def _on_right_click(self, event):
        """Handle right-click to show context menu."""
        # Identify the row under cursor
        item = self.tree.identify_row(event.y)
        if not item:
            return

        # Select the item
        self.tree.selection_set(item)

        # Get product info to determine Hide/Unhide label
        product = self._get_product_by_id(int(item))
        is_hidden = product.get("is_hidden", False) if product else False

        # Create context menu
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Edit", command=self._on_edit_product)
        menu.add_command(
            label="Unhide" if is_hidden else "Hide",
            command=self._on_toggle_hidden,
        )
        menu.add_separator()
        menu.add_command(label="Delete", command=self._on_delete_product)

        # Display menu at cursor position
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Find product by ID in current list."""
        return next(
            (p for p in self.products if p["id"] == product_id),
            None,
        )

    def _on_edit_product(self):
        """Open product for editing."""
        selection = self.tree.selection()
        if not selection:
            return

        product_id = int(selection[0])
        self._open_product_detail(product_id)

    def _on_toggle_hidden(self):
        """Toggle hidden status of selected product."""
        selection = self.tree.selection()
        if not selection:
            return

        product_id = int(selection[0])
        product = self._get_product_by_id(product_id)
        if not product:
            return

        try:
            if product.get("is_hidden"):
                product_catalog_service.unhide_product(product_id)
                messagebox.showinfo(
                    "Success",
                    f"Product '{product.get('product_name', 'Unknown')}' is now visible.",
                    parent=self,
                )
            else:
                product_catalog_service.hide_product(product_id)
                messagebox.showinfo(
                    "Success",
                    f"Product '{product.get('product_name', 'Unknown')}' is now hidden.",
                    parent=self,
                )

            self._load_products()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to update product visibility: {str(e)}",
                parent=self,
            )

    def _on_delete_product(self):
        """Delete selected product with force delete option for dependencies."""
        selection = self.tree.selection()
        if not selection:
            return

        product_id = int(selection[0])
        product = self._get_product_by_id(product_id)
        if not product:
            return

        product_name = product.get("product_name") or product.get("display_name", "Unknown")

        # Try normal delete first
        try:
            product_catalog_service.delete_product(product_id)
            messagebox.showinfo(
                "Success",
                f"Product '{product_name}' deleted successfully.",
                parent=self,
            )
            self._load_products()
            return

        except ValueError:
            # Has dependencies - analyze them
            pass
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to delete product: {str(e)}",
                parent=self,
            )
            return

        # Analyze dependencies
        try:
            deps = product_catalog_service.analyze_product_dependencies(product_id)

            # Check if used in recipes - BLOCKED
            if deps.is_used_in_recipes:
                self._show_recipe_block_dialog(deps)
                return

            # Not in recipes - show force delete confirmation
            self._show_force_delete_confirmation(deps)

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to analyze dependencies: {str(e)}",
                parent=self,
            )

    def _show_recipe_block_dialog(self, deps):
        """Show dialog explaining product cannot be deleted (ingredient used in recipes)."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Cannot Delete Product")
        dialog.geometry("500x400")
        dialog.transient(self)
        dialog.grab_set()

        # Center on parent
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - 500) // 2
        y = self.winfo_rooty() + (self.winfo_height() - 400) // 2
        dialog.geometry(f"+{x}+{y}")

        # Header
        header = ctk.CTkLabel(
            dialog,
            text="Cannot Delete Product",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="red",
        )
        header.pack(pady=15)

        # Product info
        product_label = ctk.CTkLabel(
            dialog,
            text=f"Product: {deps.product_name}\nBrand: {deps.brand}",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        product_label.pack(pady=10)

        # Explanation
        explanation = ctk.CTkLabel(
            dialog,
            text=f"This product's ingredient is used in {deps.recipe_count} recipe(s):",
            font=ctk.CTkFont(size=11),
        )
        explanation.pack(pady=5)

        # Recipe list
        recipe_frame = ctk.CTkScrollableFrame(dialog, height=120)
        recipe_frame.pack(padx=20, pady=10, fill="both", expand=True)

        for recipe in deps.recipes:
            recipe_label = ctk.CTkLabel(
                recipe_frame,
                text=f"  {recipe}",
                anchor="w",
            )
            recipe_label.pack(anchor="w", padx=10, pady=2)

        # Instructions
        instructions = ctk.CTkLabel(
            dialog,
            text=(
                "Products whose ingredients are used in recipes cannot be deleted.\n\n"
                "To remove this product:\n"
                "1. Remove the ingredient from all recipes listed above, OR\n"
                "2. Use 'Hide' to keep it but hide from lists"
            ),
            justify="left",
        )
        instructions.pack(pady=15, padx=20)

        # OK button
        ok_btn = ctk.CTkButton(
            dialog,
            text="OK",
            command=dialog.destroy,
            width=150,
        )
        ok_btn.pack(pady=15)

    def _show_force_delete_confirmation(self, deps):
        """Show detailed force delete confirmation dialog."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Confirm Force Delete")
        dialog.geometry("550x500")
        dialog.transient(self)
        dialog.grab_set()

        # Center on parent
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - 550) // 2
        y = self.winfo_rooty() + (self.winfo_height() - 500) // 2
        dialog.geometry(f"+{x}+{y}")

        # Header
        header = ctk.CTkLabel(
            dialog,
            text="Force Delete Product",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="orange",
        )
        header.pack(pady=15)

        # Product info frame
        product_frame = ctk.CTkFrame(dialog)
        product_frame.pack(padx=20, pady=10, fill="x")

        product_label = ctk.CTkLabel(
            product_frame,
            text=f"Product: {deps.product_name}\nBrand: {deps.brand}",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        product_label.pack(pady=10)

        # Risk level indicator
        risk_color = {"LOW": "green", "MEDIUM": "orange"}
        risk_label = ctk.CTkLabel(
            product_frame,
            text=f"Risk Level: {deps.deletion_risk_level}",
            text_color=risk_color.get(deps.deletion_risk_level, "gray"),
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        risk_label.pack(pady=(0, 10))

        # Scrollable details
        details_frame = ctk.CTkScrollableFrame(dialog, height=200)
        details_frame.pack(padx=20, pady=10, fill="both", expand=True)

        # Build warning message
        warning_lines = ["This will permanently delete:\n"]

        # Purchases
        if deps.purchase_count > 0:
            warning_lines.append(f"  {deps.purchase_count} Purchase Record(s):")
            for p in deps.purchases:
                supplier = p.get("supplier") or "No supplier"
                price = f"${p['price']:.2f}" if p.get("price", 0) > 0 else "No price"
                warning_lines.append(
                    f"      {p.get('date', 'Unknown date')}: {p.get('quantity', 0)} pkg, "
                    f"{price}, {supplier}"
                )
            warning_lines.append("")

        # Inventory
        if deps.inventory_count > 0:
            warning_lines.append(f"  {deps.inventory_count} Inventory Item(s):")
            for i in deps.inventory_items:
                location = i.get("location") or "No location"
                warning_lines.append(f"      {i.get('qty', 0)} remaining, {location}")
            warning_lines.append("")

        # Add specific warnings
        if deps.has_valid_purchases:
            warning_lines.append("  WARNING: Has purchases with price data - cost history will be lost")
        if deps.has_supplier_data:
            warning_lines.append("  WARNING: Has supplier information - this data will be lost")

        warning_lines.append("\n  This action CANNOT be undone!")

        warning_text = "\n".join(warning_lines)

        details_label = ctk.CTkLabel(
            details_frame,
            text=warning_text,
            justify="left",
            anchor="w",
        )
        details_label.pack(padx=10, pady=10, fill="both")

        # Buttons
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=15)

        def on_confirm():
            dialog.destroy()
            self._execute_force_delete(deps.product_id)

        def on_cancel():
            dialog.destroy()

        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=on_cancel,
            width=150,
        )
        cancel_btn.pack(side="left", padx=10)

        delete_btn = ctk.CTkButton(
            button_frame,
            text="Delete Permanently",
            command=on_confirm,
            fg_color="#cc0000",
            hover_color="#990000",
            width=150,
        )
        delete_btn.pack(side="left", padx=10)

    def _execute_force_delete(self, product_id: int):
        """Execute the force delete after confirmation."""
        try:
            deps = product_catalog_service.force_delete_product(
                product_id,
                confirmed=True,
            )

            messagebox.showinfo(
                "Deleted",
                f"Product '{deps.product_name}' and all related data deleted.\n\n"
                f"Deleted: {deps.purchase_count} purchases, "
                f"{deps.inventory_count} inventory items",
                parent=self,
            )
            self._load_products()

        except ValueError as e:
            # Should not happen (already checked recipes) but handle anyway
            messagebox.showerror("Cannot Delete", str(e), parent=self)
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Force delete failed: {str(e)}",
                parent=self,
            )
