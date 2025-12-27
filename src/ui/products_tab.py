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
        self.categories: List[str] = []
        self._data_loaded = False

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
        """Create filter controls for ingredient, category, and supplier."""
        filter_frame = ctk.CTkFrame(self)
        filter_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        # Ingredient filter
        ing_label = ctk.CTkLabel(filter_frame, text="Ingredient:")
        ing_label.pack(side="left", padx=(5, 2), pady=5)

        self.ingredient_var = ctk.StringVar(value="All")
        self.ingredient_dropdown = ctk.CTkOptionMenu(
            filter_frame,
            variable=self.ingredient_var,
            values=["All"],
            command=self._on_filter_change,
            width=150,
        )
        self.ingredient_dropdown.pack(side="left", padx=5, pady=5)

        # Category filter
        cat_label = ctk.CTkLabel(filter_frame, text="Category:")
        cat_label.pack(side="left", padx=(15, 2), pady=5)

        self.category_var = ctk.StringVar(value="All")
        self.category_dropdown = ctk.CTkOptionMenu(
            filter_frame,
            variable=self.category_var,
            values=["All"],
            command=self._on_filter_change,
            width=120,
        )
        self.category_dropdown.pack(side="left", padx=5, pady=5)

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

        # Define columns (ingredient included but hidden)
        columns = (
            "brand",
            "product_name",
            "ingredient",
            "category",
            "supplier",
            "last_price",
            "last_purchase",
        )
        # Display columns excludes ingredient (hidden)
        display_columns = (
            "brand",
            "product_name",
            "category",
            "supplier",
            "last_price",
            "last_purchase",
        )
        self.tree = ttk.Treeview(
            grid_container,
            columns=columns,
            displaycolumns=display_columns,
            show="headings",
            selectmode="browse",
        )

        # Configure column headings
        self.tree.heading("brand", text="Brand", anchor="w")
        self.tree.heading("product_name", text="Product Name", anchor="w")
        self.tree.heading("ingredient", text="Ingredient", anchor="w")  # Hidden
        self.tree.heading("category", text="Category", anchor="w")
        self.tree.heading("supplier", text="Preferred Supplier", anchor="w")
        self.tree.heading("last_price", text="Last Price", anchor="e")
        self.tree.heading("last_purchase", text="Last Purchase", anchor="w")

        # Configure column widths
        self.tree.column("brand", width=120, minwidth=80)
        self.tree.column("product_name", width=200, minwidth=150)
        self.tree.column("ingredient", width=0)  # Hidden via displaycolumns
        self.tree.column("category", width=100, minwidth=80)
        self.tree.column("supplier", width=150, minwidth=100)
        self.tree.column("last_price", width=80, minwidth=60, anchor="e")
        self.tree.column("last_purchase", width=100, minwidth=80)

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
            # Load ingredients
            self.ingredients = ingredient_service.get_all_ingredients()
            ingredient_names = ["All"] + [ing["name"] for ing in self.ingredients]
            self.ingredient_dropdown.configure(values=ingredient_names)

            # Extract unique categories from ingredients
            self.categories = sorted(set(
                ing.get("category", "")
                for ing in self.ingredients
                if ing.get("category")
            ))
            category_values = ["All"] + self.categories
            self.category_dropdown.configure(values=category_values)

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

        # Add ingredient filter
        if self.ingredient_var.get() != "All":
            ingredient = self._get_ingredient_by_name(self.ingredient_var.get())
            if ingredient:
                params["ingredient_id"] = ingredient["id"]

        # Add category filter
        if self.category_var.get() != "All":
            params["category"] = self.category_var.get()

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

        # Populate grid
        for p in self.products:
            values = (
                p.get("brand", ""),
                p.get("product_name", ""),
                p.get("ingredient_name", ""),  # Hidden column
                p.get("category", ""),
                p.get("preferred_supplier_name", ""),
                f"${p['last_price']:.2f}" if p.get("last_price") else "N/A",
                p.get("last_purchase_date", "N/A") or "N/A",
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
        """Delete selected product after confirmation."""
        selection = self.tree.selection()
        if not selection:
            return

        product_id = int(selection[0])
        product = self._get_product_by_id(product_id)
        if not product:
            return

        product_name = product.get("product_name") or product.get("display_name", "Unknown")

        # Confirm deletion
        result = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete '{product_name}'?\n\n"
            "Note: Products with purchase history or inventory cannot be deleted. "
            "Use 'Hide' instead.",
            parent=self,
        )

        if not result:
            return

        try:
            product_catalog_service.delete_product(product_id)
            messagebox.showinfo(
                "Success",
                f"Product '{product_name}' deleted successfully.",
                parent=self,
            )
            self._load_products()

        except ValueError as e:
            # Expected when product has dependencies
            messagebox.showwarning(
                "Cannot Delete",
                str(e),
                parent=self,
            )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to delete product: {str(e)}",
                parent=self,
            )
