"""
Inventory tab for displaying and managing inventory items.

Provides interface for:
- Viewing inventory in aggregate or detail mode
- Adding new inventory items (lots)
- Editing existing inventory items
- Deleting inventory items
- Filtering by location
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from typing import Optional, List, Dict, Any
import unicodedata


def normalize_for_search(text: str) -> str:
    """
    Normalize text for search by removing diacriticals and converting to lowercase.

    Examples:
        "Crème Brûlée" -> "creme brulee"
        "Café" -> "cafe"
    """
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = nfkd.encode("ASCII", "ignore").decode("ASCII")
    return ascii_text.lower()

from decimal import Decimal, InvalidOperation
from src.services import inventory_item_service, ingredient_service, product_service, supplier_service, purchase_service, ingredient_hierarchy_service

# WP10: Units where decimal quantities are unusual
COUNT_BASED_UNITS = ['count', 'bag', 'box', 'package', 'bottle', 'can', 'jar', 'carton']
from src.services.exceptions import (
    InventoryItemNotFound,
    ValidationError as ServiceValidationError,
    DatabaseError,
)
from src.services.database import session_scope
from src.models import Ingredient
from src.ui.session_state import get_session_state
from src.ui.widgets.type_ahead_combobox import TypeAheadComboBox
from src.ui.widgets.dropdown_builders import (
    build_ingredient_dropdown_values,
    build_product_dropdown_values,
    strip_star_prefix,
    is_separator,
    is_create_new_option,
)


class InventoryTab(ctk.CTkFrame):
    """
    Inventory tab for inventory management.

    Displays inventory items in two modes:
    - Aggregate: Grouped by ingredient showing totals
    - Detail: Individual inventory items (lots) with purchase dates

    Features:
    - Location filter
    - CRUD operations for inventory items
    """

    def __init__(self, parent):
        """Initialize the inventory tab."""
        super().__init__(parent)

        # State
        self.inventory_items = []  # All inventory items
        self.filtered_items = []  # Items after filtering
        self.view_mode = "detail"  # "aggregate" or "detail"
        self._data_loaded = False  # Lazy loading flag
        # Feature 032: Hierarchy filter state
        self._l0_map: Dict[str, Dict[str, Any]] = {}  # L0 name -> ingredient dict
        self._l1_map: Dict[str, Dict[str, Any]] = {}  # L1 name -> ingredient dict
        self._l2_map: Dict[str, Dict[str, Any]] = {}  # L2 name -> ingredient dict
        self._hierarchy_path_cache: Dict[int, str] = {}  # ingredient_id -> path string
        # Feature 034: Re-entry guard for cascading filter updates
        self._updating_filters = False

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Header - fixed height
        self.grid_rowconfigure(1, weight=0)  # Controls - fixed height
        self.grid_rowconfigure(2, weight=1)  # Item list - expandable

        # Create UI components
        self._create_header()
        self._create_controls()
        self._create_item_list()

        # Configure parent to expand
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        # Grid the frame to fill parent
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Show loading message - data will be loaded when tab is selected
        self._show_initial_state()

    def _create_header(self):
        """Create the header with title."""
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header_frame,
            text="My Pantry",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        subtitle = ctk.CTkLabel(
            header_frame,
            text="View and manage your pantry with lot tracking and FIFO visibility",
            font=ctk.CTkFont(size=12),
        )
        subtitle.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")

    def _create_controls(self):
        """Create control buttons and filters."""
        controls_frame = ctk.CTkFrame(self)
        controls_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        controls_frame.grid_columnconfigure(10, weight=1)

        # Row 0: Search and filters
        # Search entry
        self.search_entry = ctk.CTkEntry(
            controls_frame,
            placeholder_text="Search by ingredient or brand...",
            width=250,
        )
        self.search_entry.grid(row=0, column=0, padx=5, pady=5)
        self.search_entry.bind("<KeyRelease>", self._on_search)

        # Feature 032: Cascading hierarchy filters (L0 -> L1 -> L2)
        # L0 (Root Category) filter
        l0_label = ctk.CTkLabel(controls_frame, text="Category:")
        l0_label.grid(row=0, column=1, padx=(15, 5), pady=5)

        self.l0_filter_var = ctk.StringVar(value="All Categories")
        self.l0_filter_dropdown = ctk.CTkOptionMenu(
            controls_frame,
            variable=self.l0_filter_var,
            values=["All Categories"],
            command=self._on_l0_filter_change,
            width=150,
        )
        self.l0_filter_dropdown.grid(row=0, column=2, padx=5, pady=5)

        # L1 (Subcategory) filter - initially disabled
        l1_label = ctk.CTkLabel(controls_frame, text="Subcategory:")
        l1_label.grid(row=0, column=3, padx=(10, 5), pady=5)

        self.l1_filter_var = ctk.StringVar(value="All")
        self.l1_filter_dropdown = ctk.CTkOptionMenu(
            controls_frame,
            variable=self.l1_filter_var,
            values=["All"],
            command=self._on_l1_filter_change,
            width=150,
            state="disabled",
        )
        self.l1_filter_dropdown.grid(row=0, column=4, padx=5, pady=5)

        # L2 (Leaf Ingredient) filter - initially disabled
        l2_label = ctk.CTkLabel(controls_frame, text="Ingredient:")
        l2_label.grid(row=0, column=5, padx=(10, 5), pady=5)

        self.l2_filter_var = ctk.StringVar(value="All")
        self.l2_filter_dropdown = ctk.CTkOptionMenu(
            controls_frame,
            variable=self.l2_filter_var,
            values=["All"],
            command=self._on_l2_filter_change,
            width=150,
            state="disabled",
        )
        self.l2_filter_dropdown.grid(row=0, column=6, padx=5, pady=5)

        # Feature 034: Clear Filters button
        clear_button = ctk.CTkButton(
            controls_frame,
            text="Clear",
            command=self._clear_hierarchy_filters,
            width=60,
        )
        clear_button.grid(row=0, column=7, padx=10, pady=5)

        # Brand filter
        brand_label = ctk.CTkLabel(controls_frame, text="Brand:")
        brand_label.grid(row=0, column=8, padx=(15, 5), pady=5)

        self.brand_var = ctk.StringVar(value="All Brands")
        self.brand_dropdown = ctk.CTkOptionMenu(
            controls_frame,
            variable=self.brand_var,
            values=["All Brands"],
            command=self._on_brand_change,
            width=140,
        )
        self.brand_dropdown.grid(row=0, column=9, padx=5, pady=5)

        # View mode toggle
        view_label = ctk.CTkLabel(controls_frame, text="View:")
        view_label.grid(row=0, column=10, padx=(15, 5), pady=5)

        self.view_mode_var = ctk.StringVar(value="Detail")
        view_mode_dropdown = ctk.CTkOptionMenu(
            controls_frame,
            variable=self.view_mode_var,
            values=["Detail", "Aggregate"],
            command=self._on_view_mode_change,
            width=100,
        )
        view_mode_dropdown.grid(row=0, column=11, padx=5, pady=5)

        # Row 1: Action buttons
        # Add Inventory Item button
        add_button = ctk.CTkButton(
            controls_frame,
            text="Add Inventory Item",
            command=self._add_inventory_item,
            width=140,
        )
        add_button.grid(row=1, column=0, padx=5, pady=5, sticky="w")

    def _create_item_list(self):
        """Create item list using ttk.Treeview for performance."""
        # Container for grid and scrollbar (transparent to match other tabs)
        grid_container = ctk.CTkFrame(self, fg_color="transparent")
        grid_container.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        grid_container.grid_columnconfigure(0, weight=1)
        grid_container.grid_rowconfigure(0, weight=1)
        self.grid_container = grid_container  # Store reference for view switching

        # Configure ttk.Treeview style for compact row height
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)  # Compact row height

        # Define columns for detail view - exactly 5 columns
        columns = ("hierarchy_path", "product", "brand", "qty_remaining", "purchased")
        self.tree = ttk.Treeview(
            grid_container,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=20,  # Show more rows (default is 10)
        )

        # Configure column headings
        self.tree.heading("hierarchy_path", text="Ingredient Hierarchy", anchor="w")
        self.tree.heading("product", text="Product", anchor="w")
        self.tree.heading("brand", text="Brand", anchor="w")
        self.tree.heading("qty_remaining", text="Qty Remaining", anchor="w")
        self.tree.heading("purchased", text="Purchased", anchor="w")

        # Configure column widths
        self.tree.column("hierarchy_path", width=220, minwidth=150)
        self.tree.column("product", width=200, minwidth=150)
        self.tree.column("brand", width=120, minwidth=80)
        self.tree.column("qty_remaining", width=160, minwidth=120)
        self.tree.column("purchased", width=100, minwidth=80)

        # Add scrollbars for tree
        self.y_scrollbar = ttk.Scrollbar(
            grid_container,
            orient="vertical",
            command=self.tree.yview,
        )
        self.x_scrollbar = ttk.Scrollbar(
            grid_container,
            orient="horizontal",
            command=self.tree.xview,
        )
        self.tree.configure(
            yscrollcommand=self.y_scrollbar.set,
            xscrollcommand=self.x_scrollbar.set,
        )

        # Grid layout for tree (detail view - default)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.y_scrollbar.grid(row=0, column=1, sticky="ns")
        self.x_scrollbar.grid(row=1, column=0, sticky="ew")

        # Configure tags for visual differentiation
        self.tree.tag_configure("packaging", foreground="#0066cc")

        # Bind events
        self.tree.bind("<Double-1>", self._on_item_double_click)
        self.tree.bind("<<TreeviewSelect>>", self._on_item_select)

        # Track selected item for actions
        self.selected_item_id: Optional[int] = None

    def refresh(self):
        """Refresh inventory list from database."""
        try:
            # Get all inventory items from service (returns InventoryItem instances)
            self.inventory_items = inventory_item_service.get_inventory_items()

            # Preserve current filter selections
            current_l0 = self.l0_filter_var.get()
            current_brand = self.brand_var.get()

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

            # Extract brands from inventory
            brands = set()
            for item in self.inventory_items:
                product = getattr(item, "product", None)
                brand = getattr(product, "brand", None) if product else None
                if brand:
                    brands.add(brand)

            brand_list = ["All Brands"] + sorted(brands)
            self.brand_dropdown.configure(values=brand_list)

            # Restore filter selections
            if current_l0 in l0_values:
                self.l0_filter_var.set(current_l0)
            else:
                self.l0_filter_var.set("All Categories")

            if current_brand in brand_list:
                self.brand_var.set(current_brand)
            else:
                self.brand_var.set("All Brands")

            # Apply filters
            self._apply_filters()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to load inventory items: {str(e)}",
                parent=self,
            )

    def _apply_filters(self):
        """Apply search, hierarchy, and brand filters and update display."""
        self.filtered_items = list(self.inventory_items)

        # Apply search filter with diacritical normalization
        search_text = normalize_for_search(self.search_entry.get())
        if search_text:
            filtered = []
            for item in self.filtered_items:
                product = getattr(item, "product", None)
                ingredient = getattr(product, "ingredient", None) if product else None
                ingredient_name = getattr(ingredient, "display_name", "") or ""
                brand = getattr(product, "brand", "") or ""
                # Normalize both for comparison
                if (search_text in normalize_for_search(ingredient_name) or
                        search_text in normalize_for_search(brand)):
                    filtered.append(item)
            self.filtered_items = filtered

        # Feature 032: Apply hierarchy filters
        self.filtered_items = self._apply_hierarchy_filters(self.filtered_items)

        # Apply brand filter
        selected_brand = self.brand_var.get()
        if selected_brand and selected_brand != "All Brands":
            filtered = []
            for item in self.filtered_items:
                product = getattr(item, "product", None)
                brand = getattr(product, "brand", None) if product else None
                if brand == selected_brand:
                    filtered.append(item)
            self.filtered_items = filtered

        # Sort by ingredient name alphabetically (case-insensitive)
        self.filtered_items.sort(
            key=lambda item: (
                getattr(
                    getattr(getattr(item, "product", None), "ingredient", None),
                    "display_name", ""
                ) or ""
            ).lower()
        )

        # Update display based on view mode
        self._update_display()

    def _on_search(self, event=None):
        """Handle search text change."""
        self._apply_filters()

    # Feature 032: Hierarchy filter handlers
    def _build_hierarchy_path_cache(self):
        """Build cache mapping ingredient_id to hierarchy path string."""
        self._hierarchy_path_cache = {}
        # Get all ingredients for the cache
        try:
            all_ingredients = ingredient_service.get_all_ingredients()
            for ingredient in all_ingredients:
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
        except Exception:
            pass

    def _on_l0_filter_change(self, value: str):
        """Handle L0 (category) filter change - cascade to L1.

        Feature 034: Added re-entry guard to prevent recursive updates.
        """
        if self._updating_filters:
            return
        self._updating_filters = True
        try:
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
        finally:
            self._updating_filters = False
        self._apply_filters()

    def _on_l1_filter_change(self, value: str):
        """Handle L1 (subcategory) filter change - cascade to L2.

        Feature 034: Added re-entry guard to prevent recursive updates.
        """
        if self._updating_filters:
            return
        self._updating_filters = True
        try:
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
        finally:
            self._updating_filters = False
        self._apply_filters()

    def _on_l2_filter_change(self, value: str):
        """Handle L2 (ingredient) filter change."""
        self._apply_filters()

    def _clear_hierarchy_filters(self):
        """Clear all hierarchy filters and refresh inventory list.

        Feature 034: Reset all L0/L1/L2 filters to default state.
        """
        self._updating_filters = True
        try:
            # Reset hierarchy filter selections
            self.l0_filter_var.set("All Categories")
            self.l1_filter_var.set("All")
            self.l2_filter_var.set("All")

            # Clear hierarchy maps
            self._l1_map = {}
            self._l2_map = {}

            # Reset L1 and L2 dropdowns to disabled
            self.l1_filter_dropdown.configure(values=["All"], state="disabled")
            self.l2_filter_dropdown.configure(values=["All"], state="disabled")

            # Also reset brand filter and search
            self.brand_var.set("All Brands")
            self.search_entry.delete(0, "end")
        finally:
            self._updating_filters = False

        # Refresh the inventory list
        self._apply_filters()

    def _apply_hierarchy_filters(self, items: List) -> List:
        """Apply hierarchy filters to inventory items."""
        l0_val = self.l0_filter_var.get()
        l1_val = self.l1_filter_var.get()
        l2_val = self.l2_filter_var.get()

        # If all filters are "All", return unfiltered
        if l0_val == "All Categories" and l1_val == "All" and l2_val == "All":
            return items

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
            return items

        # Filter by ingredient_id through product relationship
        filtered = []
        for item in items:
            product = getattr(item, "product", None)
            ingredient = getattr(product, "ingredient", None) if product else None
            ingredient_id = getattr(ingredient, "id", None) if ingredient else None
            if ingredient_id in matching_ids:
                filtered.append(item)
        return filtered

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

    def _on_brand_change(self, value: str):
        """Handle brand filter change."""
        self._apply_filters()

    def _update_display(self):
        """Update the display based on current view mode."""
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        if self.view_mode == "aggregate":
            # Reconfigure tree columns for aggregate view (no Purchased column)
            self.tree.configure(columns=("hierarchy_path", "product", "brand", "qty_remaining"))
            self.tree.heading("hierarchy_path", text="Ingredient Hierarchy", anchor="w")
            self.tree.heading("product", text="Product", anchor="w")
            self.tree.heading("brand", text="Brand", anchor="w")
            self.tree.heading("qty_remaining", text="Qty Remaining", anchor="w")
            self.tree.column("hierarchy_path", width=220, minwidth=150)
            self.tree.column("product", width=250, minwidth=150)
            self.tree.column("brand", width=140, minwidth=100)
            self.tree.column("qty_remaining", width=160, minwidth=120)

            if self.filtered_items:
                self._display_aggregate_view()
        else:
            # Reconfigure tree columns for detail view (with Purchased column)
            self.tree.configure(columns=("hierarchy_path", "product", "brand", "qty_remaining", "purchased"))
            self.tree.heading("hierarchy_path", text="Ingredient Hierarchy", anchor="w")
            self.tree.heading("product", text="Product", anchor="w")
            self.tree.heading("brand", text="Brand", anchor="w")
            self.tree.heading("qty_remaining", text="Qty Remaining", anchor="w")
            self.tree.heading("purchased", text="Purchased", anchor="w")
            self.tree.column("hierarchy_path", width=220, minwidth=150)
            self.tree.column("product", width=200, minwidth=150)
            self.tree.column("brand", width=120, minwidth=80)
            self.tree.column("qty_remaining", width=160, minwidth=120)
            self.tree.column("purchased", width=100, minwidth=80)

            if self.filtered_items:
                self._display_detail_view()

    def _show_initial_state(self):
        """Show initial state - tree is shown by default, data loads when tab is selected."""
        # Tree is already gridded and visible by default
        # Just clear any existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _show_empty_state(self):
        """Show empty state - tree is already empty, nothing to do."""
        # Tree is already cleared in _update_display, just leave it empty
        pass

    def _display_aggregate_view(self):
        """Display inventory items grouped by product with totals in Treeview."""
        # Group items by product (not ingredient)
        from collections import defaultdict
        from decimal import Decimal

        product_groups = defaultdict(list)

        for item in self.filtered_items:
            product = getattr(item, "product", None)
            product_id = getattr(product, "id", None)
            if product_id:
                product_groups[product_id].append(item)

        # Build and display aggregated data
        aggregated = []
        for product_id, items in product_groups.items():
            first_item = items[0]
            product = getattr(first_item, "product", None)
            ingredient = getattr(product, "ingredient", None) if product else None

            # Sum quantities for this product
            total_qty = sum(
                Decimal(str(getattr(item, "quantity", 0) or 0))
                for item in items
            )

            # Get product details
            ingredient_name = getattr(ingredient, "display_name", "Unknown") if ingredient else "Unknown"
            ingredient_id = getattr(ingredient, "id", None) if ingredient else None
            # Use hierarchy path from cache, fallback to ingredient name
            hierarchy_path = self._hierarchy_path_cache.get(ingredient_id, ingredient_name) if ingredient_id else ingredient_name
            is_packaging = getattr(ingredient, "is_packaging", False) if ingredient else False
            brand = getattr(product, "brand", "") or ""
            product_name = getattr(product, "product_name", "") or ""
            package_qty = getattr(product, "package_unit_quantity", None)
            package_unit = getattr(product, "package_unit", "") or ""
            package_type = getattr(product, "package_type", "") or ""

            # Build product description
            desc_parts = []
            if product_name:
                desc_parts.append(product_name)
            elif ingredient_name:
                desc_parts.append(f"[{ingredient_name}]")
            if package_qty and package_unit:
                size_str = f"{package_qty:g} {package_unit}"
                if package_type:
                    size_str += f" {package_type}"
                desc_parts.append(size_str)
            description = " - ".join(desc_parts) if desc_parts else "N/A"

            # Format quantity display (same as detail view)
            pkg_type_display = package_type if package_type else "pkg"
            pkg_unit_display = package_unit if package_unit else "unit"

            if package_qty and package_qty > 0:
                packages = float(total_qty) / float(package_qty)
                total_amount = float(total_qty)

                # Format package count (1 decimal max, remove trailing zeros)
                if packages == int(packages):
                    pkg_count = str(int(packages))
                else:
                    pkg_count = f"{packages:.1f}".rstrip('0').rstrip('.')

                pkg_type_text = pkg_type_display if packages == 1 else f"{pkg_type_display}s"

                # Format total amount (1 decimal max for small, 0 for large)
                if total_amount > 100:
                    total_text = f"{total_amount:.0f}"
                elif total_amount == int(total_amount):
                    total_text = str(int(total_amount))
                else:
                    total_text = f"{total_amount:.1f}".rstrip('0').rstrip('.')

                qty_display = f"{pkg_count} {pkg_type_text} ({total_text} {pkg_unit_display})"
            else:
                # Fallback if no package info (1 decimal max)
                if total_qty == int(total_qty):
                    qty_display = str(int(total_qty))
                else:
                    qty_display = f"{float(total_qty):.1f}".rstrip('0').rstrip('.')

            aggregated.append({
                'hierarchy_path': hierarchy_path,
                'description': description,
                'brand': f"📦 {brand}" if is_packaging else brand,
                'qty_display': qty_display,
                'is_packaging': is_packaging,
            })

        # Sort by hierarchy path, then product description
        aggregated.sort(key=lambda x: (x['hierarchy_path'].lower(), x['description'].lower()))

        # Populate Treeview - no row limit needed, handles large datasets well
        for item_data in aggregated:
            tags = ("packaging",) if item_data['is_packaging'] else ()
            self.tree.insert("", "end", values=(
                item_data['hierarchy_path'],
                item_data['description'],
                item_data['brand'],
                item_data['qty_display'],
            ), tags=tags)

    def _display_detail_view(self):
        """Display individual inventory items in Treeview (lots)."""
        # Sort items by purchase date (FIFO order - oldest first)
        sorted_items = sorted(
            self.filtered_items,
            key=lambda x: getattr(x, "purchase_date", None) or date.today(),
        )

        # Populate Treeview - no row limit needed, handles large datasets well
        for item in sorted_items:
            # Get ingredient and product info
            product_obj = getattr(item, "product", None)
            ingredient_obj = getattr(product_obj, "ingredient", None) if product_obj else None

            # Brand
            brand = getattr(product_obj, "brand", "Unknown") if product_obj else "Unknown"
            is_packaging = getattr(ingredient_obj, "is_packaging", False) if ingredient_obj else False
            if is_packaging:
                brand = f"📦 {brand}"

            # Product description and hierarchy path
            product_name = getattr(product_obj, "product_name", None) or ""
            ingredient_name = getattr(ingredient_obj, "display_name", "") if ingredient_obj else ""
            ingredient_id = getattr(ingredient_obj, "id", None) if ingredient_obj else None
            # Use hierarchy path from cache, fallback to ingredient name
            hierarchy_path = self._hierarchy_path_cache.get(ingredient_id, ingredient_name) if ingredient_id else ingredient_name
            package_qty = getattr(product_obj, "package_unit_quantity", None)
            package_unit = getattr(product_obj, "package_unit", "") or ""
            package_type = getattr(product_obj, "package_type", None) or ""

            desc_parts = []
            if product_name:
                desc_parts.append(product_name)
            elif ingredient_name:
                desc_parts.append(f"[{ingredient_name}]")
            if package_qty and package_unit:
                size_str = f"{package_qty:g} {package_unit}"
                if package_type:
                    size_str += f" {package_type}"
                desc_parts.append(size_str)
            description = " - ".join(desc_parts) if desc_parts else "N/A"

            # Qty Remaining format: {qty} {package_type}(s) ({total} {package_unit})
            # Example: "2.5 jars (70 oz)" or "1 can (28 oz)"
            qty_value = getattr(item, "quantity", 0) or 0
            pkg_type_display = package_type if package_type else "pkg"
            pkg_unit_display = package_unit if package_unit else "unit"

            if package_qty and package_qty > 0:
                # Calculate packages remaining
                packages = qty_value / float(package_qty)
                # Calculate total amount
                total_amount = qty_value  # quantity is already in base units

                # Format package count (1 decimal max, remove trailing zeros)
                if packages == int(packages):
                    pkg_count = str(int(packages))
                else:
                    pkg_count = f"{packages:.1f}".rstrip('0').rstrip('.')

                # Handle singular/plural for package type
                if packages == 1:
                    pkg_type_text = pkg_type_display
                else:
                    pkg_type_text = f"{pkg_type_display}s"

                # Format total amount (1 decimal max for small, 0 for large)
                if total_amount > 100:
                    total_text = f"{total_amount:.0f}"
                elif total_amount == int(total_amount):
                    total_text = str(int(total_amount))
                else:
                    total_text = f"{total_amount:.1f}".rstrip('0').rstrip('.')

                qty_display = f"{pkg_count} {pkg_type_text} ({total_text} {pkg_unit_display})"
            else:
                # Fallback if no package info (1 decimal max)
                if qty_value == int(qty_value):
                    qty_display = str(int(qty_value))
                else:
                    qty_display = f"{float(qty_value):.1f}".rstrip('0').rstrip('.')

            # Purchase date
            purchase_date = getattr(item, "purchase_date", None)
            purchase_str = purchase_date.strftime("%Y-%m-%d") if purchase_date else ""

            # Tags for visual styling
            tags = []
            if is_packaging:
                tags.append("packaging")

            # Column order: hierarchy_path, product, brand, qty_remaining, purchased (exactly 5)
            values = (hierarchy_path, description, brand, qty_display, purchase_str)
            item_id = getattr(item, "id", None)

            # Use item ID as the tree item ID for easy lookup
            self.tree.insert("", "end", iid=str(item_id), values=values, tags=tuple(tags))

    def _on_item_double_click(self, event):
        """Handle double-click on inventory item to open edit dialog."""
        selection = self.tree.selection()
        if selection:
            item_id = int(selection[0])
            self._edit_inventory_item(item_id)

    def _on_item_select(self, event):
        """Handle tree selection change."""
        selection = self.tree.selection()
        if selection:
            self.selected_item_id = int(selection[0])
        else:
            self.selected_item_id = None

    def _truncate_text(self, text: str, max_chars: int = 25) -> str:
        """Truncate text and add ellipsis if too long."""
        if not text:
            return ""
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 1] + "..."

    def _get_expiration_warning_color(self, items: List[dict]) -> Optional[str]:
        """Get warning color based on expiration dates in items."""
        has_expired = False
        has_expiring_soon = False

        for item in items:
            expiration_date = getattr(item, "expiration_date", None)
            if expiration_date:
                days_until_expiry = (expiration_date - date.today()).days
                if days_until_expiry < 0:
                    has_expired = True
                elif days_until_expiry <= 14:
                    has_expiring_soon = True

        if has_expired:
            return "#8B0000"  # Dark red
        elif has_expiring_soon:
            return "#DAA520"  # Goldenrod
        return None

    def _on_view_mode_change(self, value: str):
        """Handle view mode change."""
        self.view_mode = value.lower()
        self._update_display()

    def _view_ingredient_details(self, ingredient_slug: str):
        """Switch to detail view filtered to specific ingredient."""
        # Switch to detail mode
        self.view_mode = "detail"
        self.view_mode_var.set("Detail")

        # Filter to specific ingredient
        self.filtered_items = [
            item
            for item in self.inventory_items
            if getattr(getattr(item, "product", None), "ingredient", None)
            and item.product.ingredient.slug == ingredient_slug
        ]

        self._update_display()

    def filter_by_ingredient(self, ingredient_slug: str) -> None:
        """
        Public helper to focus the view on a specific ingredient.

        Args:
            ingredient_slug: Slug of the ingredient to filter by.
        """
        if not ingredient_slug:
            return

        if not any(
            getattr(getattr(item, "product", None), "ingredient", None)
            and item.product.ingredient.slug == ingredient_slug
            for item in self.inventory_items
        ):
            self.refresh()

        if not any(
            getattr(getattr(item, "product", None), "ingredient", None)
            and item.product.ingredient.slug == ingredient_slug
            for item in self.inventory_items
        ):
            messagebox.showinfo(
                "No Inventory Items",
                f"No inventory found for ingredient '{ingredient_slug}'.",
                parent=self,
            )
            return

        self.view_mode = "detail"
        self.view_mode_var.set("Detail")
        # Clear filters to show the specific ingredient
        self.search_entry.delete(0, "end")
        # Feature 032: Reset hierarchy filters
        self.l0_filter_var.set("All Categories")
        self.l1_filter_var.set("All")
        self.l2_filter_var.set("All")
        self.l1_filter_dropdown.configure(state="disabled")
        self.l2_filter_dropdown.configure(state="disabled")

        self.filtered_items = [
            item
            for item in self.inventory_items
            if getattr(getattr(item, "product", None), "ingredient", None)
            and item.product.ingredient.slug == ingredient_slug
        ]
        self._update_display()

    def _add_inventory_item(self):
        """Open dialog to add new inventory item."""
        dialog = InventoryItemFormDialog(self, title="Add Inventory Item")
        self.wait_window(dialog)

        if not dialog.result:
            return

        try:
            # Create inventory item via service (F028: includes supplier and price)
            inventory_item_service.add_to_inventory(
                product_id=dialog.result["product_id"],
                quantity=dialog.result["quantity"],
                supplier_id=dialog.result["supplier_id"],  # F028
                unit_price=dialog.result["unit_price"],  # F028
                purchase_date=dialog.result["purchase_date"],
                expiration_date=dialog.result.get("expiration_date"),
                location=dialog.result.get("location"),
                notes=dialog.result.get("notes"),
            )

            messagebox.showinfo(
                "Success",
                "Inventory item added successfully",
                parent=self,
            )
            self.refresh()

        except ServiceValidationError as e:
            messagebox.showerror("Validation Error", str(e), parent=self)
        except DatabaseError as e:
            messagebox.showerror("Database Error", str(e), parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add inventory item: {str(e)}", parent=self)

    def _edit_inventory_item(self, inventory_item_id: int):
        """Open dialog to edit inventory item."""
        try:
            # Get current item data
            item = next((i for i in self.inventory_items if i.id == inventory_item_id), None)
            if not item:
                messagebox.showerror("Error", "Inventory item not found", parent=self)
                return

            dialog = InventoryItemFormDialog(
                self,
                title="Edit Inventory Item",
                item=self._serialize_inventory_item(item),
            )
            self.wait_window(dialog)

            # Check if item was deleted
            if dialog.deleted:
                self.selected_item_id = None
                self.refresh()
                return

            if not dialog.result:
                return

            # Update inventory item via service
            # Extract supplier_id before passing to update (it's handled separately)
            supplier_id = dialog.result.pop("supplier_id", None)
            inventory_item_service.update_inventory_item(inventory_item_id, dialog.result)

            # Update supplier via purchase record if provided
            if supplier_id is not None:
                inventory_item_service.update_inventory_supplier(inventory_item_id, supplier_id)

            messagebox.showinfo(
                "Success",
                "Inventory item updated successfully",
                parent=self,
            )
            self.refresh()

        except InventoryItemNotFound:
            messagebox.showerror("Error", "Inventory item not found", parent=self)
            self.refresh()
        except ServiceValidationError as e:
            messagebox.showerror("Validation Error", str(e), parent=self)
        except DatabaseError as e:
            messagebox.showerror("Database Error", str(e), parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update inventory item: {str(e)}", parent=self)

    def _delete_inventory_item(self, inventory_item_id: int):
        """Delete inventory item after confirmation."""
        result = messagebox.askyesno(
            "Confirm Delete",
            "Are you sure you want to delete this inventory item?",
            parent=self,
        )

        if result:
            try:
                inventory_item_service.delete_inventory_item(inventory_item_id)
                messagebox.showinfo(
                    "Success",
                    "Inventory item deleted successfully",
                    parent=self,
                )
                self.refresh()

            except InventoryItemNotFound:
                messagebox.showerror("Error", "Inventory item not found", parent=self)
                self.refresh()
            except DatabaseError as e:
                messagebox.showerror("Database Error", str(e), parent=self)
            except Exception as e:
                messagebox.showerror(
                    "Error", f"Failed to delete inventory item: {str(e)}", parent=self
                )

    def _serialize_inventory_item(self, item) -> dict:
        """Convert an InventoryItem ORM instance to a simple dict for dialog usage."""
        product = getattr(item, "product", None)
        ingredient = getattr(product, "ingredient", None) if product else None
        purchase = getattr(item, "purchase", None)
        supplier = getattr(purchase, "supplier", None) if purchase else None

        return {
            "id": item.id,
            "product_id": item.product_id,
            "quantity": item.quantity,
            "purchase_date": item.purchase_date,
            "expiration_date": item.expiration_date,
            "location": item.location,
            "notes": item.notes,
            "product_brand": getattr(product, "brand", None),
            "product_package_unit_quantity": getattr(product, "package_unit_quantity", None),
            "product_package_unit": getattr(product, "package_unit", None),
            "ingredient_name": getattr(ingredient, "display_name", None),
            # Purchase/Supplier info for edit form
            "purchase_id": getattr(item, "purchase_id", None),
            "supplier_id": getattr(supplier, "id", None) if supplier else None,
            "supplier_name": getattr(supplier, "name", None) if supplier else None,
            "unit_price": getattr(purchase, "unit_price", None) if purchase else None,
        }


class InventoryItemFormDialog(ctk.CTkToplevel):
    """
    Dialog for creating or editing an inventory item.

    Form fields:
    - Ingredient (dropdown)
    - Product (dropdown, filtered by ingredient)
    - Supplier (dropdown, required for new items) - F028
    - Price (entry with suggestion hint, required for new items) - F028
    - Quantity (required, > 0)
    - Purchase Date (required)
    - Location (optional)
    - Notes (optional)
    """

    def __init__(self, parent, title="Inventory Item", item: Optional[dict] = None):
        """
        Initialize the form dialog.

        Args:
            parent: Parent widget
            title: Dialog title
            item: Existing inventory item data for editing (None for new)
        """
        super().__init__(parent)

        self.title(title)
        # Taller height when editing to accommodate expanded calculator section
        height = 900 if item else 700
        self.geometry(f"500x{height}")
        self.resizable(False, False)

        # Mark as transient (child of parent) but don't grab yet
        # Grabbing before form is built causes apparent freeze
        self.transient(parent)

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        self.item = item
        self.result: Optional[Dict[str, Any]] = None
        self.deleted = False  # Track if item was deleted
        self.parent_tab = parent  # Reference to parent tab for delete callback
        self.ingredients: List[Dict[str, Any]] = []
        self.products: List[Dict[str, Any]] = []
        self.suppliers: List[Dict[str, Any]] = []  # F028
        self.session_state = get_session_state()  # F029: Session memory

        # Calculator state (for editing mode)
        self._calc_collapsed = True
        self._calc_calculating = False  # Prevent recursive calculation updates
        self._calc_new_qty = None  # Calculated new quantity for save

        # Load data
        self._load_ingredients()
        self._load_suppliers()  # F028

        # Create form
        self._create_form()

        # Populate if editing
        if self.item:
            self._populate_form()

        # Now that form is fully built, grab events to make dialog modal
        # This prevents apparent freeze during initialization
        self.update_idletasks()
        self.grab_set()

    def _load_ingredients(self):
        """Load ingredients from service."""
        try:
            self.ingredients = ingredient_service.get_all_ingredients()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load ingredients: {str(e)}", parent=self)
            self.destroy()

    def _load_suppliers(self):
        """Load active suppliers from service (F028)."""
        try:
            self.suppliers = supplier_service.get_active_suppliers()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load suppliers: {str(e)}", parent=self)
            self.destroy()

    def _create_form(self):
        """Create form fields."""
        # Configure grid
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        row = 0

        # F029: Category dropdown (type-ahead, min_chars=1)
        cat_label = ctk.CTkLabel(self, text="Category:*")
        cat_label.grid(row=row, column=0, padx=10, pady=10, sticky="w")

        # Load categories from ingredients
        categories = sorted(set(ing.get("category", "") for ing in self.ingredients if ing.get("category")))

        # F029: Apply session memory for category
        default_category = ""
        if not self.item and categories:
            last_category = self.session_state.get_last_category()
            if last_category and last_category in categories:
                default_category = last_category
            else:
                default_category = categories[0] if categories else ""

        self.category_combo = TypeAheadComboBox(
            self,
            values=categories if categories else [],
            min_chars=1,
            command=self._on_category_selected,
        )
        self.category_combo.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
        if default_category:
            self.category_combo.set(default_category)
        row += 1

        # F029: Ingredient dropdown (type-ahead, min_chars=2, filtered by category)
        ing_label = ctk.CTkLabel(self, text="Ingredient:*")
        ing_label.grid(row=row, column=0, padx=10, pady=10, sticky="w")

        self.ingredient_combo = TypeAheadComboBox(
            self,
            values=[],  # Populated when category selected
            min_chars=2,
            command=self._on_ingredient_selected,
        )
        self.ingredient_combo.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
        self.ingredient_combo.configure(state="disabled")
        self.selected_ingredient = None  # Track selected ingredient object
        row += 1

        # F029: Product dropdown (type-ahead, min_chars=2, filtered by ingredient)
        product_label = ctk.CTkLabel(self, text="Product:*")
        product_label.grid(row=row, column=0, padx=10, pady=10, sticky="w")

        self.product_combo = TypeAheadComboBox(
            self,
            values=[],  # Populated when ingredient selected
            min_chars=2,
            command=self._on_product_selected,
        )
        self.product_combo.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
        self.product_combo.configure(state="disabled")
        self.selected_product = None  # Track selected product object
        row += 1

        # F029/WP08: Inline product creation frame (hidden initially)
        self.inline_create_row = row  # Track row for dynamic positioning
        self.inline_create_expanded = False
        self.inline_create_frame = ctk.CTkFrame(
            self,
            border_width=1,
            corner_radius=5,
            fg_color=("gray90", "gray20"),
        )
        self._setup_inline_create_form()
        # Do NOT grid initially - hidden until expanded
        row += 1

        # Trigger cascading load if category is pre-selected
        if default_category and not self.item:
            self._on_category_selected(default_category)

        # Feature 032: Hierarchy display labels (read-only)
        hierarchy_frame = ctk.CTkFrame(self, fg_color=("gray90", "gray20"), corner_radius=5)
        hierarchy_frame.grid(row=row, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        hierarchy_frame.grid_columnconfigure(1, weight=1)
        hierarchy_frame.grid_columnconfigure(3, weight=1)
        hierarchy_frame.grid_columnconfigure(5, weight=1)

        # L0 (Category)
        l0_label = ctk.CTkLabel(hierarchy_frame, text="Category:", font=ctk.CTkFont(size=11))
        l0_label.grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")
        self.hierarchy_l0_value = ctk.CTkLabel(
            hierarchy_frame, text="--", font=ctk.CTkFont(size=11), text_color="gray"
        )
        self.hierarchy_l0_value.grid(row=0, column=1, padx=(0, 15), pady=5, sticky="w")

        # L1 (Subcategory)
        l1_label = ctk.CTkLabel(hierarchy_frame, text="Subcategory:", font=ctk.CTkFont(size=11))
        l1_label.grid(row=0, column=2, padx=(0, 5), pady=5, sticky="w")
        self.hierarchy_l1_value = ctk.CTkLabel(
            hierarchy_frame, text="--", font=ctk.CTkFont(size=11), text_color="gray"
        )
        self.hierarchy_l1_value.grid(row=0, column=3, padx=(0, 15), pady=5, sticky="w")

        # L2 (Ingredient)
        l2_label = ctk.CTkLabel(hierarchy_frame, text="Ingredient:", font=ctk.CTkFont(size=11))
        l2_label.grid(row=0, column=4, padx=(0, 5), pady=5, sticky="w")
        self.hierarchy_l2_value = ctk.CTkLabel(
            hierarchy_frame, text="--", font=ctk.CTkFont(size=11), text_color="gray"
        )
        self.hierarchy_l2_value.grid(row=0, column=5, padx=(0, 10), pady=5, sticky="w")
        row += 1

        # F028: Supplier dropdown (required for new items)
        # F029: Pre-select from session memory with star indicator
        supplier_label = ctk.CTkLabel(self, text="Supplier:*")
        supplier_label.grid(row=row, column=0, padx=10, pady=10, sticky="w")

        supplier_names = [s["display_name"] for s in self.suppliers]

        # F029: Check session state for last supplier
        default_supplier = ""
        self._session_supplier_display = None  # Track session-selected supplier for star
        if not self.item and supplier_names:
            last_supplier_id = self.session_state.get_last_supplier_id()
            if last_supplier_id:
                # Find supplier with matching ID
                for s in self.suppliers:
                    if s["id"] == last_supplier_id:
                        # Pre-select with star indicator
                        default_supplier = self._format_supplier_with_star(s["display_name"])
                        self._session_supplier_display = s["display_name"]
                        break
            # Fall back to first supplier if no session match
            if not default_supplier:
                default_supplier = supplier_names[0]

        self.supplier_var = ctk.StringVar(value=default_supplier if not self.item else "")
        self.supplier_dropdown = ctk.CTkOptionMenu(
            self,
            variable=self.supplier_var,
            values=supplier_names if supplier_names else ["No suppliers"],
            command=self._on_supplier_change,
        )
        self.supplier_dropdown.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
        row += 1

        # F028: Price entry with suggestion hint
        price_label = ctk.CTkLabel(self, text="Unit Price ($):*")
        price_label.grid(row=row, column=0, padx=10, pady=(10, 0), sticky="w")

        self.price_var = ctk.StringVar(value="")
        self.price_entry = ctk.CTkEntry(self, textvariable=self.price_var, placeholder_text="0.00")
        self.price_entry.grid(row=row, column=1, padx=10, pady=(10, 0), sticky="ew")
        # WP09: Bind Key to clear hint on manual edit
        self.price_entry.bind('<Key>', self._on_price_key)
        # WP10: Bind FocusOut for price validation
        self.price_entry.bind('<FocusOut>', self._on_price_focus_out)
        row += 1

        # F028: Price hint label (shows last paid price)
        self.price_hint_label = ctk.CTkLabel(
            self,
            text="",
            font=("", 11),
            text_color="gray",
        )
        self.price_hint_label.grid(row=row, column=1, padx=10, pady=(0, 10), sticky="w")
        row += 1

        # Trigger initial price hint if supplier is pre-selected
        if default_supplier and not self.item:
            self._on_supplier_change(default_supplier)

        # Quantity Remaining (current stock level, not original purchase amount)
        qty_label = ctk.CTkLabel(self, text="Quantity Remaining:*")
        qty_label.grid(row=row, column=0, padx=10, pady=10, sticky="w")

        self.quantity_entry = ctk.CTkEntry(self, placeholder_text="e.g., 25")
        self.quantity_entry.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
        # WP10: Bind FocusOut for quantity validation
        self.quantity_entry.bind('<FocusOut>', self._on_quantity_focus_out)
        row += 1

        # Calculator section (only for editing mode)
        if self.item:
            self._create_calculator_section(row)
            row += 1

        # Purchase Date
        purchase_label = ctk.CTkLabel(self, text="Purchase Date:*")
        purchase_label.grid(row=row, column=0, padx=10, pady=10, sticky="w")

        self.purchase_date_entry = ctk.CTkEntry(self, placeholder_text="YYYY-MM-DD")
        self.purchase_date_entry.grid(row=row, column=1, padx=10, pady=10, sticky="ew")

        # Set default to today
        self.purchase_date_entry.insert(0, date.today().strftime("%Y-%m-%d"))
        row += 1

        # Location
        location_label = ctk.CTkLabel(self, text="Location:")
        location_label.grid(row=row, column=0, padx=10, pady=10, sticky="w")

        self.location_entry = ctk.CTkEntry(self, placeholder_text="e.g., Main Storage")
        self.location_entry.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
        row += 1

        # Notes
        notes_label = ctk.CTkLabel(self, text="Notes:")
        notes_label.grid(row=row, column=0, padx=10, pady=10, sticky="nw")

        self.notes_text = ctk.CTkTextbox(self, height=100)
        self.notes_text.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
        row += 1

        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=row, column=0, columnspan=2, padx=10, pady=20, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)  # Left side expands

        # Delete button on left (only when editing)
        if self.item:
            delete_btn = ctk.CTkButton(
                button_frame,
                text="Delete",
                command=self._delete,
                width=100,
                fg_color="#8B0000",
                hover_color="#B22222",
            )
            delete_btn.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # Cancel and Save buttons on right
        right_buttons = ctk.CTkFrame(button_frame, fg_color="transparent")
        right_buttons.grid(row=0, column=1, sticky="e")

        cancel_btn = ctk.CTkButton(
            right_buttons,
            text="Cancel",
            command=self.destroy,
            width=100,
        )
        cancel_btn.grid(row=0, column=0, padx=5, pady=5)

        save_btn = ctk.CTkButton(
            right_buttons,
            text="Save",
            command=self._save,
            width=100,
        )
        save_btn.grid(row=0, column=1, padx=5, pady=5)

    def _on_category_selected(self, selected_value: str):
        """Handle category selection - load ingredients for this category (F029)."""
        # Strip star if present
        category = strip_star_prefix(selected_value).strip()
        if not category:
            return

        # Load ingredients for this category using dropdown builder with recency
        try:
            with session_scope() as session:
                ingredient_values = build_ingredient_dropdown_values(category, session)

            self.ingredient_combo.reset_values(ingredient_values)
            self.ingredient_combo.configure(state="normal")

            # Clear downstream selections
            self.ingredient_combo.set("")
            self.product_combo.set("")
            self.product_combo.configure(state="disabled")
            self.selected_ingredient = None
            self.selected_product = None

            # Feature 032: Clear hierarchy labels when category changes
            self._clear_hierarchy_labels()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load ingredients: {str(e)}", parent=self)

    # Feature 032: Hierarchy label methods
    def _update_hierarchy_labels(self, ingredient_id: int):
        """Update hierarchy display labels based on ingredient."""
        if not ingredient_id:
            self._clear_hierarchy_labels()
            return

        try:
            # Get ingredient details
            ingredient = next(
                (ing for ing in self.ingredients if ing.get("id") == ingredient_id),
                None,
            )
            # Get ancestors
            ancestors = ingredient_hierarchy_service.get_ancestors(ingredient_id)

            # L2 is the ingredient itself
            l2_name = ingredient.get("display_name", "--") if ingredient else "--"

            # L1 and L0 from ancestors
            if len(ancestors) >= 2:
                l0_name = ancestors[1].get("display_name", "--")
                l1_name = ancestors[0].get("display_name", "--")
            elif len(ancestors) == 1:
                l0_name = ancestors[0].get("display_name", "--")
                l1_name = "--"
            else:
                l0_name = "--"
                l1_name = "--"

            self.hierarchy_l0_value.configure(text=l0_name)
            self.hierarchy_l1_value.configure(text=l1_name)
            self.hierarchy_l2_value.configure(text=l2_name)
        except Exception:
            self._clear_hierarchy_labels()

    def _clear_hierarchy_labels(self):
        """Clear hierarchy display labels to default."""
        self.hierarchy_l0_value.configure(text="--")
        self.hierarchy_l1_value.configure(text="--")
        self.hierarchy_l2_value.configure(text="--")

    def _on_ingredient_selected(self, selected_value: str):
        """Handle ingredient selection - load products for this ingredient (F029)."""
        # Handle separator selection
        if is_separator(selected_value):
            self.ingredient_combo.set("")
            return

        # Strip star if present
        ingredient_name = strip_star_prefix(selected_value).strip()
        if not ingredient_name:
            return

        # Find ingredient by display_name from our loaded ingredients
        ingredient = next(
            (ing for ing in self.ingredients if ing["name"] == ingredient_name),
            None,
        )
        if not ingredient:
            return

        self.selected_ingredient = ingredient

        # Feature 032: Update hierarchy labels
        self._update_hierarchy_labels(ingredient.get("id"))

        # Load products for this ingredient using dropdown builder with recency
        try:
            with session_scope() as session:
                # Find the ingredient ID
                ing_obj = session.query(Ingredient).filter_by(
                    display_name=ingredient_name
                ).first()

                if not ing_obj:
                    self.product_combo.reset_values([])
                    self.product_combo.configure(state="disabled")
                    return

                product_values = build_product_dropdown_values(ing_obj.id, session)

            self.product_combo.reset_values(product_values)
            self.product_combo.configure(state="normal")

            # Clear product selection
            self.product_combo.set("")
            self.selected_product = None

            # Also load products dict for validation
            product_objects = product_service.get_products_for_ingredient(ingredient["slug"])
            self.products = [
                {
                    "id": p.id,
                    "name": p.display_name,
                    "brand": p.brand,
                    "package_unit_quantity": p.package_unit_quantity,
                    "package_unit": p.package_unit,
                }
                for p in product_objects
            ]

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load products: {str(e)}", parent=self)

    def _on_product_selected(self, selected_value: str):
        """Handle product selection (F029)."""
        # Ignore separator selection
        if is_separator(selected_value):
            self.product_combo.set("")
            return

        # WP08: Check for create new option - trigger inline form
        if is_create_new_option(selected_value):
            self.product_combo.set("")
            self._toggle_inline_create()
            return

        # Strip star if present
        product_name = strip_star_prefix(selected_value).strip()
        if not product_name:
            return

        # Find product by name from our loaded products
        product = next(
            (p for p in self.products
             if p.get("brand") == product_name
             or self._format_product_display(p) == selected_value.replace("⭐ ", "")),
            None,
        )

        if product:
            self.selected_product = product
            # Trigger price hint update
            self._on_supplier_change(self.supplier_var.get())

    def _format_product_display(self, product: dict) -> str:
        """Format a product dictionary into a human-readable label."""
        brand = product.get("brand") or "Unknown"
        quantity = product.get("package_unit_quantity")
        unit = product.get("package_unit") or ""
        if quantity:
            return f"{brand} - {quantity} {unit}".strip()
        return brand

    def _format_supplier_with_star(self, display_name: str) -> str:
        """Format supplier display name with star indicator for session memory (F029)."""
        return f"* {display_name}"

    def _strip_star_from_supplier(self, display_name: str) -> str:
        """Remove star indicator from supplier display name (F029)."""
        if display_name.startswith("* "):
            return display_name[2:]
        return display_name

    # ==========================================================================
    # WP08: Inline Product Creation Methods
    # ==========================================================================

    def _setup_inline_create_form(self):
        """Setup inline product creation form (WP08)."""
        form_frame = ctk.CTkFrame(self.inline_create_frame, fg_color="transparent")
        form_frame.pack(fill="both", expand=True, padx=10, pady=10)
        form_frame.grid_columnconfigure(1, weight=1)

        # Header
        header = ctk.CTkLabel(
            form_frame,
            text="Create New Product",
            font=ctk.CTkFont(weight="bold"),
        )
        header.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky="w")

        # Ingredient (read-only display)
        ctk.CTkLabel(form_frame, text="Ingredient:").grid(
            row=1, column=0, padx=5, pady=5, sticky="w"
        )
        self.inline_ingredient_label = ctk.CTkLabel(
            form_frame, text="", text_color="gray"
        )
        self.inline_ingredient_label.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Product Name (required)
        ctk.CTkLabel(form_frame, text="Product Name:*").grid(
            row=2, column=0, padx=5, pady=5, sticky="w"
        )
        self.inline_name_entry = ctk.CTkEntry(
            form_frame, placeholder_text="e.g., Gold Medal AP Flour"
        )
        self.inline_name_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # Package Unit + Quantity on same row
        ctk.CTkLabel(form_frame, text="Package:*").grid(
            row=3, column=0, padx=5, pady=5, sticky="w"
        )
        package_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        package_frame.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        self.inline_qty_entry = ctk.CTkEntry(package_frame, width=80, placeholder_text="Qty")
        self.inline_qty_entry.pack(side="left", padx=(0, 5))

        self.inline_unit_combo = ctk.CTkComboBox(
            package_frame,
            values=["lb", "oz", "kg", "g", "fl oz", "ml", "L", "count", "bag", "box"],
            width=100,
        )
        self.inline_unit_combo.pack(side="left")

        # Preferred Supplier (optional, pre-filled from session)
        ctk.CTkLabel(form_frame, text="Preferred Supplier:").grid(
            row=4, column=0, padx=5, pady=5, sticky="w"
        )
        supplier_names = [s["display_name"] for s in self.suppliers]
        self.inline_supplier_combo = ctk.CTkComboBox(
            form_frame,
            values=supplier_names if supplier_names else [""],
        )
        self.inline_supplier_combo.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        # Buttons
        btn_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=100,
            fg_color="gray",
            command=self._cancel_inline_create,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Create Product",
            width=120,
            command=self._create_product_inline,
        ).pack(side="left", padx=5)

    def _toggle_inline_create(self):
        """Toggle inline product creation form (accordion) (WP08)."""
        if self.inline_create_expanded:
            # Collapse
            self.inline_create_frame.grid_forget()
            self.inline_create_expanded = False
            self.product_combo.configure(state="normal")
        else:
            # Expand
            self.inline_create_frame.grid(
                row=self.inline_create_row,
                column=0,
                columnspan=2,
                sticky="ew",
                padx=10,
                pady=5,
            )
            self.inline_create_expanded = True
            self.product_combo.configure(state="disabled")
            self._prefill_inline_form()
            self.inline_name_entry.focus_set()

    def _prefill_inline_form(self):
        """Pre-fill inline creation form with smart defaults (WP08)."""
        from src.utils.category_defaults import get_default_unit_for_category

        # Clear previous values
        self.inline_name_entry.delete(0, "end")
        self.inline_qty_entry.delete(0, "end")

        # Pre-fill ingredient (read-only display)
        if self.selected_ingredient:
            self.inline_ingredient_label.configure(
                text=self.selected_ingredient.get("name", "")
            )

            # Pre-fill unit from category defaults
            category = self.selected_ingredient.get("category", "")
            if category:
                default_unit = get_default_unit_for_category(category)
                self.inline_unit_combo.set(default_unit)

        # Pre-fill supplier from session
        last_supplier_id = self.session_state.get_last_supplier_id()
        if last_supplier_id:
            for s in self.suppliers:
                if s["id"] == last_supplier_id:
                    self.inline_supplier_combo.set(f"⭐ {s['display_name']}")
                    break
        else:
            # Default to first supplier if any
            if self.suppliers:
                self.inline_supplier_combo.set(self.suppliers[0]["display_name"])

    def _create_product_inline(self):
        """Create product from inline form (WP08)."""
        from decimal import Decimal, InvalidOperation

        # Validate required fields
        name = self.inline_name_entry.get().strip()
        if not name:
            messagebox.showerror(
                "Validation Error", "Product name is required", parent=self
            )
            self.inline_name_entry.focus_set()
            return

        unit = self.inline_unit_combo.get().strip()
        if not unit:
            messagebox.showerror(
                "Validation Error", "Package unit is required", parent=self
            )
            return

        qty_str = self.inline_qty_entry.get().strip()
        if not qty_str:
            messagebox.showerror(
                "Validation Error", "Package quantity is required", parent=self
            )
            self.inline_qty_entry.focus_set()
            return

        try:
            qty = Decimal(qty_str)
            if qty <= 0:
                raise ValueError("Quantity must be positive")
        except (InvalidOperation, ValueError):
            messagebox.showerror(
                "Validation Error",
                "Package quantity must be a positive number",
                parent=self,
            )
            self.inline_qty_entry.focus_set()
            return

        if not self.selected_ingredient:
            messagebox.showerror("Error", "No ingredient selected", parent=self)
            return

        # Get preferred supplier (optional)
        supplier_display = self.inline_supplier_combo.get().replace("⭐ ", "").strip()
        preferred_supplier_id = None
        if supplier_display:
            supplier = next(
                (s for s in self.suppliers if s["display_name"] == supplier_display),
                None,
            )
            if supplier:
                preferred_supplier_id = supplier["id"]

        # Create product via service
        try:
            product_data = {
                "brand": name,  # Use entered name as brand
                "package_unit": unit,
                "package_unit_quantity": qty,  # Already a Decimal
            }
            if preferred_supplier_id:
                product_data["preferred_supplier_id"] = preferred_supplier_id

            new_product = product_service.create_product(
                self.selected_ingredient.get("slug"),
                product_data,
            )

            # Success - rebuild dropdown and select new product
            with session_scope() as session:
                # Find the ingredient ID
                ing_obj = session.query(Ingredient).filter_by(
                    display_name=self.selected_ingredient.get("name")
                ).first()

                if ing_obj:
                    product_values = build_product_dropdown_values(ing_obj.id, session)
                    self.product_combo.reset_values(product_values)

            # Select the new product (it's "recent" so should have star)
            self.product_combo.set(f"⭐ {name}")

            # Update products list for tracking
            self.products.append({
                "id": new_product.id,
                "name": new_product.display_name,
                "brand": new_product.brand,
                "package_unit": new_product.package_unit,
                "package_unit_quantity": new_product.package_unit_quantity,
            })
            self.selected_product = self.products[-1]

            # Collapse form
            self._cancel_inline_create()

            # Trigger price hint update
            self._on_supplier_change(self.supplier_var.get())

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to create product: {str(e)}",
                parent=self,
            )
            # Keep form expanded for correction

    def _cancel_inline_create(self):
        """Cancel inline product creation (WP08)."""
        # Clear form
        self.inline_name_entry.delete(0, "end")
        self.inline_qty_entry.delete(0, "end")
        self.inline_unit_combo.set("")
        self.inline_supplier_combo.set("")

        # Collapse
        self.inline_create_frame.grid_forget()
        self.inline_create_expanded = False

        # Re-enable product dropdown and focus
        self.product_combo.configure(state="normal")
        self.product_combo.focus_set()

    # ==========================================================================
    # End WP08 Methods
    # ==========================================================================

    def _get_selected_product_id(self) -> Optional[int]:
        """Get product_id from current product dropdown selection (F028, F029)."""
        # F029: Use tracked selected_product from type-ahead combo
        if self.selected_product:
            return self.selected_product.get("id")

        # Fallback: try to match from combo value
        product_display = self.product_combo.get().strip()
        if not product_display:
            return None

        # Strip star prefix if present
        product_display = strip_star_prefix(product_display)

        product = next(
            (p for p in self.products
             if self._format_product_display(p) == product_display
             or p.get("brand") == product_display),
            None,
        )
        return product["id"] if product else None

    def _get_selected_supplier_id(self) -> Optional[int]:
        """Get supplier_id from current supplier dropdown selection (F028, F029)."""
        supplier_name = self.supplier_var.get().strip()
        if not supplier_name or supplier_name == "No suppliers":
            return None
        # F029: Strip star indicator if present
        supplier_name = self._strip_star_from_supplier(supplier_name)
        supplier = next(
            (s for s in self.suppliers if s["display_name"] == supplier_name),
            None,
        )
        return supplier["id"] if supplier else None

    def _on_supplier_change(self, selected_value: str):
        """Handle supplier selection change - update price hint (F028)."""
        product_id = self._get_selected_product_id()
        supplier_id = self._get_selected_supplier_id()

        if not product_id or not supplier_id:
            self.price_hint_label.configure(text="")
            return

        try:
            # Try supplier-specific price first
            result = purchase_service.get_last_price_at_supplier(product_id, supplier_id)

            if result:
                # History at this supplier
                price = result["unit_price"]
                date_str = result["purchase_date"]
                self.price_var.set(price)
                self.price_hint_label.configure(text=f"(last paid: ${price} on {date_str})")
            else:
                # Fallback to any supplier
                result = purchase_service.get_last_price_any_supplier(product_id)
                if result:
                    price = result["unit_price"]
                    date_str = result["purchase_date"]
                    supplier_name = result["supplier_name"]
                    self.price_var.set(price)
                    self.price_hint_label.configure(text=f"(last paid: ${price} at {supplier_name} on {date_str})")
                else:
                    # No history
                    self.price_var.set("")
                    self.price_hint_label.configure(text="(no purchase history)")
        except Exception as e:
            self.price_hint_label.configure(text="(error loading price)")

    def _populate_form(self):  # noqa: C901
        """Populate form with existing item data."""
        if not self.item:
            return

        try:
            # F029: For editing, we need to set category first, then ingredient, then product
            ingredient_name = self.item.get("ingredient_name")
            if ingredient_name:
                # Find the category for this ingredient
                ingredient = next(
                    (ing for ing in self.ingredients if ing["name"] == ingredient_name),
                    None,
                )
                if ingredient:
                    category = ingredient.get("category", "")
                    if category:
                        self.category_combo.set(category)
                        self._on_category_selected(category)

                    # Set ingredient
                    self.ingredient_combo.set(ingredient_name)
                    self._on_ingredient_selected(ingredient_name)

            product_id = self.item.get("product_id")
            display = None
            if product_id and self.products:
                for product in self.products:
                    if product["id"] == product_id:
                        display = self._format_product_display(product)
                        self.selected_product = product
                        break
            if display:
                self.product_combo.set(display)

            # Set quantity
            self.quantity_entry.delete(0, "end")
            self.quantity_entry.insert(0, str(self.item.get("quantity", "")))

            # Set purchase date
            purchase_date = self.item.get("purchase_date")
            if purchase_date:
                self.purchase_date_entry.delete(0, "end")
                self.purchase_date_entry.insert(0, purchase_date.strftime("%Y-%m-%d"))

            # Set location
            location = self.item.get("location")
            if location:
                self.location_entry.delete(0, "end")
                self.location_entry.insert(0, location)

            # Set notes
            notes = self.item.get("notes")
            if notes:
                self.notes_text.delete("1.0", "end")
                self.notes_text.insert("1.0", notes)

            # Set supplier from purchase record (if linked)
            supplier_name = self.item.get("supplier_name")
            if supplier_name:
                # Find matching supplier in dropdown
                supplier_display = next(
                    (s["display_name"] for s in self.suppliers if s["name"] == supplier_name),
                    None,
                )
                if supplier_display:
                    self.supplier_var.set(supplier_display)
                    # Trigger price hint update
                    self._on_supplier_change(supplier_display)

            # Prevent editing immutable fields (F029: use combo boxes)
            self.category_combo.configure(state="disabled")
            self.ingredient_combo.configure(state="disabled")
            self.product_combo.configure(state="disabled")
            self.purchase_date_entry.configure(state="disabled")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to populate form: {str(e)}", parent=self)

    def _save(self):  # noqa: C901
        """Validate and save form data."""
        from decimal import Decimal

        # Get values (F029: use combo boxes)
        category = strip_star_prefix(self.category_combo.get()).strip()
        ingredient_name = strip_star_prefix(self.ingredient_combo.get()).strip()
        product_display = strip_star_prefix(self.product_combo.get()).strip()
        quantity_str = self.quantity_entry.get().strip()
        purchase_date_str = self.purchase_date_entry.get().strip()
        location = self.location_entry.get().strip()
        notes = self.notes_text.get("1.0", "end").strip()

        # Validate required fields (F029: check for category too)
        if not category:
            messagebox.showerror("Validation Error", "Please select a category", parent=self)
            return

        if not ingredient_name:
            messagebox.showerror("Validation Error", "Please select an ingredient", parent=self)
            return

        if not product_display or is_separator(product_display) or is_create_new_option(product_display):
            messagebox.showerror("Validation Error", "Please select a product", parent=self)
            return

        if not quantity_str:
            messagebox.showerror("Validation Error", "Quantity is required", parent=self)
            return

        if not purchase_date_str:
            messagebox.showerror("Validation Error", "Purchase date is required", parent=self)
            return

        is_editing = self.item is not None
        item_data: Dict[str, Any] = self.item or {}

        # Parse and validate quantity
        # If calculator was used (editing mode), use calculated quantity
        if is_editing and hasattr(self, '_calc_new_qty') and self._calc_new_qty is not None:
            quantity = self._calc_new_qty
            # Allow zero for fully consumed items
            if quantity < 0:
                messagebox.showerror(
                    "Validation Error", "Quantity cannot be negative", parent=self
                )
                return
        else:
            try:
                quantity = Decimal(quantity_str)
                if quantity <= 0:
                    messagebox.showerror(
                        "Validation Error", "Quantity must be greater than 0", parent=self
                    )
                    return
            except Exception:
                messagebox.showerror("Validation Error", "Invalid quantity format", parent=self)
                return

        # Parse purchase date
        if is_editing and item_data.get("purchase_date"):
            purchase_date = item_data["purchase_date"]
        else:
            try:
                purchase_date = date.fromisoformat(purchase_date_str)
            except Exception:
                messagebox.showerror(
                    "Validation Error",
                    "Invalid purchase date format (use YYYY-MM-DD)",
                    parent=self,
                )
                return

        # Determine product ID
        if is_editing:
            product_id = item_data.get("product_id")
        else:
            product = next(
                (p for p in self.products if self._format_product_display(p) == product_display),
                None,
            )
            if not product:
                messagebox.showerror("Validation Error", "Selected product not found", parent=self)
                return
            product_id = product["id"]

        # F028: Validate supplier (required for new items)
        supplier_id = None
        if not is_editing:
            supplier_id = self._get_selected_supplier_id()
            if not supplier_id:
                messagebox.showerror("Validation Error", "Please select a supplier", parent=self)
                return

        # F028: Validate and parse price (required for new items)
        unit_price = None
        if not is_editing:
            price_str = self.price_var.get().strip()
            if not price_str:
                messagebox.showerror("Validation Error", "Unit price is required", parent=self)
                return

            try:
                unit_price = Decimal(price_str)
            except Exception:
                messagebox.showerror("Validation Error", "Invalid price format", parent=self)
                return

            # F028 FR-008: Reject negative prices
            if unit_price < 0:
                messagebox.showerror("Validation Error", "Price cannot be negative", parent=self)
                return

            # F028 FR-007: Warn on zero price
            if unit_price == Decimal("0"):
                confirm = messagebox.askyesno(
                    "Confirm Zero Price",
                    "Price is $0.00. This may indicate a donation or free sample.\n\nProceed with zero price?",
                    parent=self,
                )
                if not confirm:
                    return

        # Build result
        self.result = {
            "quantity": quantity,
        }

        if not is_editing:
            self.result["product_id"] = product_id
            self.result["supplier_id"] = supplier_id  # F028
            self.result["unit_price"] = unit_price  # F028
            self.result["purchase_date"] = purchase_date
        else:
            # For editing, include supplier_id so it can be updated via purchase record
            supplier_id = self._get_selected_supplier_id()
            if supplier_id is not None:
                self.result["supplier_id"] = supplier_id

        if location:
            self.result["location"] = location
        if notes:
            self.result["notes"] = notes

        # F029: Update session state on successful add (not edit)
        if not is_editing:
            if supplier_id:
                self.session_state.update_supplier(supplier_id)
            if category:
                self.session_state.update_category(category)

        self.destroy()

    def _delete(self):
        """Delete the inventory item after confirmation."""
        if not self.item:
            return

        item_id = self.item.get("id")
        if not item_id:
            messagebox.showerror("Error", "Cannot delete: item ID not found", parent=self)
            return

        # Build description for confirmation message
        brand = self.item.get("product_brand", "Unknown")
        ingredient = self.item.get("ingredient_name", "Unknown")
        quantity = self.item.get("quantity", "?")
        unit = self.item.get("product_package_unit", "")
        description = f"{brand} {ingredient} ({quantity} {unit})"

        # Confirm deletion
        result = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete this inventory item?\n\n"
            f"{description}\n\n"
            "This action cannot be undone.",
            parent=self,
        )

        if result:
            try:
                # Delete using service
                inventory_item_service.delete_inventory_item(item_id)
                self.deleted = True
                self.result = None
                messagebox.showinfo("Success", "Inventory item deleted!", parent=self)
                self.destroy()

            except InventoryItemNotFound:
                messagebox.showerror("Error", "Inventory item not found", parent=self)
            except DatabaseError as e:
                messagebox.showerror("Database Error", f"Failed to delete: {e}", parent=self)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete inventory item: {e}", parent=self)

    # WP09: Clear price hint when user types

    def _on_price_key(self, event):
        """Clear hint when user types in price field (WP09)."""
        # Ignore navigation keys
        if event.keysym not in ('Tab', 'Return', 'Escape', 'Up', 'Down', 'Left', 'Right'):
            self.price_hint_label.configure(text="")

    # WP10: Validation methods for price and quantity

    def _on_price_focus_out(self, event):
        """Validate price when focus leaves field."""
        self._validate_price()

    def _on_quantity_focus_out(self, event):
        """Validate quantity when focus leaves field."""
        self._validate_quantity()

    # =========================================================================
    # Calculator Section (for editing mode)
    # =========================================================================

    def _create_calculator_section(self, row: int):
        """Create the quantity update calculator section (editing mode only)."""
        from decimal import Decimal, InvalidOperation

        # Get current quantity and package info for calculations
        self._calc_current_qty = Decimal(str(self.item.get("quantity", 0)))
        product = self.selected_product or {}
        self._calc_package_unit = product.get("package_unit", "units")
        self._calc_package_qty = Decimal(str(product.get("package_unit_quantity", 1)))

        # Main calculator frame
        self.calc_frame = ctk.CTkFrame(self, border_width=1, corner_radius=5)
        self.calc_frame.grid(row=row, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.calc_frame.grid_columnconfigure(1, weight=1)

        # Toggle button (collapsed by default)
        self.calc_toggle_btn = ctk.CTkButton(
            self.calc_frame,
            text="▶ Update Quantity",
            command=self._toggle_calculator,
            width=150,
            fg_color="transparent",
            text_color=("gray40", "gray60"),
            hover_color=("gray80", "gray30"),
            anchor="w",
        )
        self.calc_toggle_btn.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        # Calculator inputs frame (hidden initially)
        self.calc_inputs_frame = ctk.CTkFrame(self.calc_frame, fg_color="transparent")
        # Don't grid yet - will show on expand

        # Current quantity display
        current_display = f"Current: {self._calc_current_qty:.2f} {self._calc_package_unit}"
        self.calc_current_label = ctk.CTkLabel(
            self.calc_inputs_frame,
            text=current_display,
            font=ctk.CTkFont(weight="bold"),
        )
        self.calc_current_label.grid(row=0, column=0, columnspan=3, pady=(5, 10), sticky="w")

        # Field 1: Remaining %
        remaining_label = ctk.CTkLabel(self.calc_inputs_frame, text="Remaining %:")
        remaining_label.grid(row=1, column=0, padx=(5, 10), pady=3, sticky="w")

        self._calc_pct_var = ctk.StringVar()
        self._calc_pct_var.trace_add("write", self._on_calc_pct_change)
        self._calc_pct_entry = ctk.CTkEntry(
            self.calc_inputs_frame,
            textvariable=self._calc_pct_var,
            width=80,
            placeholder_text="0-100",
        )
        self._calc_pct_entry.grid(row=1, column=1, pady=3, sticky="w")

        pct_suffix = ctk.CTkLabel(self.calc_inputs_frame, text="%")
        pct_suffix.grid(row=1, column=2, padx=(3, 10), pady=3, sticky="w")

        # Field 2: New Quantity
        new_qty_label = ctk.CTkLabel(self.calc_inputs_frame, text="New Qty:")
        new_qty_label.grid(row=2, column=0, padx=(5, 10), pady=3, sticky="w")

        self._calc_new_qty_var = ctk.StringVar()
        self._calc_new_qty_var.trace_add("write", self._on_calc_new_qty_change)
        self._calc_new_qty_entry = ctk.CTkEntry(
            self.calc_inputs_frame,
            textvariable=self._calc_new_qty_var,
            width=80,
        )
        self._calc_new_qty_entry.grid(row=2, column=1, pady=3, sticky="w")

        qty_suffix = ctk.CTkLabel(self.calc_inputs_frame, text=self._calc_package_unit)
        qty_suffix.grid(row=2, column=2, padx=(3, 10), pady=3, sticky="w")

        # Field 3: Amount Used
        used_label = ctk.CTkLabel(self.calc_inputs_frame, text="Used:")
        used_label.grid(row=3, column=0, padx=(5, 10), pady=3, sticky="w")

        self._calc_used_var = ctk.StringVar()
        self._calc_used_var.trace_add("write", self._on_calc_used_change)
        self._calc_used_entry = ctk.CTkEntry(
            self.calc_inputs_frame,
            textvariable=self._calc_used_var,
            width=80,
        )
        self._calc_used_entry.grid(row=3, column=1, pady=3, sticky="w")

        # Unit dropdown for amount used
        unit_options = [self._calc_package_unit]
        self._calc_used_unit_var = ctk.StringVar(value=self._calc_package_unit)
        self._calc_used_unit_dropdown = ctk.CTkOptionMenu(
            self.calc_inputs_frame,
            variable=self._calc_used_unit_var,
            values=unit_options,
            width=60,
        )
        self._calc_used_unit_dropdown.grid(row=3, column=2, padx=(3, 10), pady=3, sticky="w")

        # Result preview label
        self._calc_result_label = ctk.CTkLabel(
            self.calc_inputs_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=("green", "lightgreen"),
        )
        self._calc_result_label.grid(row=4, column=0, columnspan=3, pady=(10, 5), sticky="w")

    def _toggle_calculator(self):
        """Toggle calculator section collapsed/expanded."""
        if self._calc_collapsed:
            # Expand
            self.calc_inputs_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
            self.calc_toggle_btn.configure(text="▼ Update Quantity")
            self._calc_collapsed = False
        else:
            # Collapse
            self.calc_inputs_frame.grid_forget()
            self.calc_toggle_btn.configure(text="▶ Update Quantity")
            self._calc_collapsed = True
            # Clear calculator state
            self._calc_new_qty = None

    def _on_calc_pct_change(self, *args):
        """Handle remaining percentage input change."""
        if self._calc_calculating:
            return
        self._calc_calculating = True
        try:
            pct_str = self._calc_pct_var.get().strip()
            if not pct_str:
                self._clear_calc_fields()
                return

            pct = float(pct_str)
            if not 0 <= pct <= 100:
                self._calc_result_label.configure(text="% must be 0-100", text_color="red")
                return

            # Calculate new quantity
            new_qty = self._calc_current_qty * (Decimal(str(pct)) / 100)
            amount_used = self._calc_current_qty - new_qty

            # Update other fields (show as calculated)
            self._calc_new_qty_var.set(f"{new_qty:.2f}")
            self._calc_used_var.set(f"{amount_used:.2f}")

            # Store for save
            self._calc_new_qty = new_qty

            # Update preview
            self._calc_result_label.configure(
                text=f"→ New: {new_qty:.2f} {self._calc_package_unit}",
                text_color=("green", "lightgreen"),
            )
        except (ValueError, Exception):
            self._calc_result_label.configure(text="Invalid input", text_color="red")
        finally:
            self._calc_calculating = False

    def _on_calc_new_qty_change(self, *args):
        """Handle new quantity input change."""
        if self._calc_calculating:
            return
        self._calc_calculating = True
        try:
            qty_str = self._calc_new_qty_var.get().strip()
            if not qty_str:
                self._clear_calc_fields()
                return

            new_qty = Decimal(qty_str)
            if new_qty < 0:
                self._calc_result_label.configure(text="Qty cannot be negative", text_color="red")
                return

            # Calculate percentage and amount used
            if self._calc_current_qty > 0:
                pct = (new_qty / self._calc_current_qty) * 100
                self._calc_pct_var.set(f"{pct:.1f}")
            amount_used = self._calc_current_qty - new_qty
            self._calc_used_var.set(f"{amount_used:.2f}")

            # Store for save
            self._calc_new_qty = new_qty

            # Update preview
            self._calc_result_label.configure(
                text=f"→ New: {new_qty:.2f} {self._calc_package_unit}",
                text_color=("green", "lightgreen"),
            )
        except (ValueError, Exception):
            self._calc_result_label.configure(text="Invalid input", text_color="red")
        finally:
            self._calc_calculating = False

    def _on_calc_used_change(self, *args):
        """Handle amount used input change."""
        if self._calc_calculating:
            return
        self._calc_calculating = True
        try:
            used_str = self._calc_used_var.get().strip()
            if not used_str:
                self._clear_calc_fields()
                return

            amount_used = Decimal(used_str)
            if amount_used < 0:
                self._calc_result_label.configure(text="Used cannot be negative", text_color="red")
                return

            new_qty = self._calc_current_qty - amount_used
            if new_qty < 0:
                self._calc_result_label.configure(text="Used exceeds current qty", text_color="red")
                return

            # Calculate percentage
            if self._calc_current_qty > 0:
                pct = (new_qty / self._calc_current_qty) * 100
                self._calc_pct_var.set(f"{pct:.1f}")
            self._calc_new_qty_var.set(f"{new_qty:.2f}")

            # Store for save
            self._calc_new_qty = new_qty

            # Update preview
            self._calc_result_label.configure(
                text=f"→ New: {new_qty:.2f} {self._calc_package_unit}",
                text_color=("green", "lightgreen"),
            )
        except (ValueError, Exception):
            self._calc_result_label.configure(text="Invalid input", text_color="red")
        finally:
            self._calc_calculating = False

    def _clear_calc_fields(self):
        """Clear calculator fields and result."""
        self._calc_calculating = True
        self._calc_pct_var.set("")
        self._calc_new_qty_var.set("")
        self._calc_used_var.set("")
        self._calc_result_label.configure(text="")
        self._calc_new_qty = None
        self._calc_calculating = False

    def _validate_price(self) -> bool:
        """Validate price value.

        Returns:
            True if valid or empty, False if invalid.
        """
        price_str = self.price_entry.get().strip()
        if not price_str:
            return True  # Empty is OK, will be caught on submit

        try:
            price = Decimal(price_str)
        except InvalidOperation:
            return True  # Invalid format caught on submit

        # Check for negative price
        if price < 0:
            messagebox.showerror(
                "Invalid Price",
                "Price cannot be negative.",
                parent=self,
            )
            self.price_entry.focus_set()
            return False

        # Check for high price (>= $100) per FR-027
        if price >= 100:
            if not self._confirm_high_price(price):
                self.price_entry.focus_set()
                return False

        return True

    def _confirm_high_price(self, price: Decimal) -> bool:
        """Ask user to confirm high price.

        Args:
            price: The price value to confirm.

        Returns:
            True if user confirms, False if user cancels.
        """
        return messagebox.askyesno(
            "Confirm High Price",
            f"Price is ${price:.2f} (over $100).\n\nIs this correct?",
            parent=self,
        )

    def _validate_quantity(self) -> bool:
        """Validate quantity value.

        Returns:
            True if valid or empty, False if invalid.
        """
        qty_str = self.quantity_entry.get().strip()
        if not qty_str:
            return True  # Empty OK, caught on submit

        try:
            qty = Decimal(qty_str)
        except InvalidOperation:
            return True  # Invalid format caught on submit

        # Check for count-based unit with decimal quantity
        if self.selected_product and self._is_count_based_unit():
            if qty != qty.to_integral_value():
                if not self._confirm_decimal_quantity(qty):
                    self.quantity_entry.focus_set()
                    return False

        return True

    def _confirm_decimal_quantity(self, qty: Decimal) -> bool:
        """Ask user to confirm decimal quantity for count-based unit.

        Args:
            qty: The quantity value to confirm.

        Returns:
            True if user confirms, False if user cancels.
        """
        return messagebox.askyesno(
            "Confirm Decimal Quantity",
            f"Package quantities are usually whole numbers.\n\n"
            f"You entered {qty}. Continue?",
            parent=self,
        )

    def _is_count_based_unit(self) -> bool:
        """Check if selected product uses count-based unit.

        Returns:
            True if the product's package_unit is count-based, False otherwise.
        """
        if not self.selected_product:
            return False
        unit = self.selected_product.get("package_unit", "").lower()
        return unit in COUNT_BASED_UNITS
