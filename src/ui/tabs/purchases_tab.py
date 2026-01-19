"""PurchasesTab - Purchase history tracking with filtering and sorting.

Displays purchase history with:
- Date range filter (Last 30 days, Last 90 days, Last year, All time)
- Supplier filter
- Product search
- Sortable columns
- Context menu for CRUD operations

Also displays Material Inventory (Feature 059):
- MaterialInventoryItem lots in a separate tab
- Filtering by product, depletion status
- Sortable columns

Implements FR-022: Purchase tracking (Feature 042).
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Optional, List, Dict
from decimal import Decimal
from datetime import datetime

import customtkinter as ctk

from src.services.purchase_service import (
    get_purchases_filtered,
    get_purchase,
    get_remaining_inventory,
    can_delete_purchase,
    get_purchase_usage_history,
)
from src.services.supplier_service import get_all_suppliers
from src.services.exceptions import PurchaseNotFound
from src.services.material_inventory_service import list_inventory_items
from src.services.material_catalog_service import list_products as list_material_products


class PurchasesTab(ctk.CTkFrame):
    """Tab for viewing and managing purchase history.

    Displays purchases in a treeview with filtering, sorting, and
    context menu for CRUD operations.
    """

    def __init__(self, master: Any, **kwargs):
        """Initialize PurchasesTab.

        Args:
            master: Parent widget
            **kwargs: Additional arguments passed to CTkFrame
        """
        super().__init__(master, **kwargs)

        # State for Food Purchases
        self.purchases: List[Dict] = []
        self.filtered_purchases: List[Dict] = []
        self._data_loaded = False
        self._sort_column = "purchase_date"
        self._sort_reverse = True  # Default: newest first

        # Supplier map for ID lookup
        self._supplier_map: Dict[str, int] = {}  # name -> id

        # State for Materials Inventory (Feature 059)
        self._materials_items: List[Dict] = []
        self._materials_sort_column = "purchase_date"
        self._materials_sort_reverse = True  # Default: newest first
        self._materials_product_map: Dict[str, int] = {}  # name -> id
        self._materials_filter_updating = False  # Re-entry guard

        # Grid configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Header - fixed height
        self.grid_rowconfigure(1, weight=0)  # Tab selector - fixed height
        self.grid_rowconfigure(2, weight=1)  # Content - expandable

        # Create UI components
        self._create_header()
        self._create_tab_selector()
        self._create_food_section()
        self._create_materials_section()

        # Configure parent to expand
        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(0, weight=1)

        # Grid the frame to fill parent
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Keyboard shortcut for new purchase (Ctrl+N / Cmd+N)
        self.bind("<Control-n>", lambda e: self._on_add_purchase())
        self.bind("<Command-n>", lambda e: self._on_add_purchase())  # macOS

        # Show initial state (Food tab by default)
        self._show_food_section()

    def _create_header(self) -> None:
        """Create the header with title and subtitle."""
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))

        title = ctk.CTkLabel(
            header_frame,
            text="Purchase History",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            header_frame,
            text="View, add, and manage your purchases",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        subtitle.pack(anchor="w")

    def _create_tab_selector(self) -> None:
        """Create tab selector buttons for Food/Materials sections."""
        tab_frame = ctk.CTkFrame(self, fg_color="transparent")
        tab_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(5, 0))

        self._tab_var = ctk.StringVar(value="food")

        self._food_tab_btn = ctk.CTkButton(
            tab_frame,
            text="Food Purchases",
            command=self._show_food_section,
            width=140,
            fg_color=("gray75", "gray25"),
            hover_color=("gray65", "gray35"),
        )
        self._food_tab_btn.pack(side="left", padx=(0, 5))

        self._materials_tab_btn = ctk.CTkButton(
            tab_frame,
            text="Material Inventory",
            command=self._show_materials_section,
            width=140,
            fg_color="transparent",
            hover_color=("gray65", "gray35"),
        )
        self._materials_tab_btn.pack(side="left")

    def _show_food_section(self) -> None:
        """Show the Food Purchases section."""
        self._tab_var.set("food")
        self._food_tab_btn.configure(fg_color=("gray75", "gray25"))
        self._materials_tab_btn.configure(fg_color="transparent")
        self._materials_section_frame.grid_remove()
        self._food_section_frame.grid()
        self._show_initial_state()

    def _show_materials_section(self) -> None:
        """Show the Materials Inventory section."""
        self._tab_var.set("materials")
        self._materials_tab_btn.configure(fg_color=("gray75", "gray25"))
        self._food_tab_btn.configure(fg_color="transparent")
        self._food_section_frame.grid_remove()
        self._materials_section_frame.grid()
        self._populate_materials_product_filter()
        self._refresh_materials_display()

    def _create_food_section(self) -> None:
        """Create the Food Purchases section (original content)."""
        self._food_section_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._food_section_frame.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
        self._food_section_frame.grid_columnconfigure(0, weight=1)
        self._food_section_frame.grid_rowconfigure(0, weight=0)  # Controls
        self._food_section_frame.grid_rowconfigure(1, weight=1)  # List

        self._create_controls()
        self._create_purchase_list()
        self._create_context_menu()

    def _create_controls(self) -> None:
        """Create filter controls and action buttons for Food section."""
        controls_frame = ctk.CTkFrame(self._food_section_frame)
        controls_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        controls_frame.grid_columnconfigure(10, weight=1)  # Spacer column

        # Add Purchase button
        add_btn = ctk.CTkButton(
            controls_frame,
            text="+ Add Purchase",
            command=self._on_add_purchase,
            width=120
        )
        add_btn.grid(row=0, column=0, padx=5, pady=5)

        # Date range filter
        date_label = ctk.CTkLabel(controls_frame, text="Date Range:")
        date_label.grid(row=0, column=1, padx=(20, 5), pady=5)

        self.date_range_var = ctk.StringVar(value="Last 30 days")
        date_dropdown = ctk.CTkOptionMenu(
            controls_frame,
            variable=self.date_range_var,
            values=["Last 30 days", "Last 90 days", "Last year", "All time"],
            command=self._on_filter_change,
            width=130
        )
        date_dropdown.grid(row=0, column=2, padx=5, pady=5)

        # Supplier filter
        supplier_label = ctk.CTkLabel(controls_frame, text="Supplier:")
        supplier_label.grid(row=0, column=3, padx=(20, 5), pady=5)

        self.supplier_var = ctk.StringVar(value="All")
        self.supplier_dropdown = ctk.CTkOptionMenu(
            controls_frame,
            variable=self.supplier_var,
            values=["All"],
            command=self._on_filter_change,
            width=150
        )
        self.supplier_dropdown.grid(row=0, column=4, padx=5, pady=5)

        # Search entry
        search_label = ctk.CTkLabel(controls_frame, text="Search:")
        search_label.grid(row=0, column=5, padx=(20, 5), pady=5)

        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            controls_frame,
            placeholder_text="Search products...",
            textvariable=self.search_var,
            width=200
        )
        self.search_entry.grid(row=0, column=6, padx=5, pady=5)
        self.search_entry.bind("<KeyRelease>", self._on_search_change)

        # Clear filters button
        clear_btn = ctk.CTkButton(
            controls_frame,
            text="Clear",
            command=self._clear_filters,
            width=60
        )
        clear_btn.grid(row=0, column=7, padx=10, pady=5)

    def _create_purchase_list(self) -> None:
        """Create the purchase list treeview for Food section."""
        # Container for treeview and scrollbar
        list_frame = ctk.CTkFrame(self._food_section_frame, fg_color="transparent")
        list_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)

        # Configure ttk.Treeview style
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)

        # Define columns
        columns = ("date", "product", "supplier", "qty", "price", "total", "remaining")
        self.tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        # Column configurations with sortable headers
        col_config = {
            "date": ("Date", 100, "w"),
            "product": ("Product", 200, "w"),
            "supplier": ("Supplier", 120, "w"),
            "qty": ("Qty", 60, "e"),
            "price": ("Unit Price", 80, "e"),
            "total": ("Total", 80, "e"),
            "remaining": ("Remaining", 80, "e")
        }

        for col, (title, width, anchor) in col_config.items():
            self.tree.heading(
                col,
                text=title,
                anchor=anchor,
                command=lambda c=col: self._sort_by_column(c)
            )
            self.tree.column(col, width=width, minwidth=width - 20, anchor=anchor)

        # Scrollbars
        y_scrollbar = ttk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self.tree.yview
        )
        x_scrollbar = ttk.Scrollbar(
            list_frame,
            orient="horizontal",
            command=self.tree.xview
        )
        self.tree.configure(
            yscrollcommand=y_scrollbar.set,
            xscrollcommand=x_scrollbar.set
        )

        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar.grid(row=1, column=0, sticky="ew")

        # Bind events
        self.tree.bind("<Double-1>", lambda e: self._on_view_details())
        self.tree.bind("<<TreeviewSelect>>", self._on_item_select)

        # Keyboard shortcuts
        self.tree.bind("<Delete>", lambda e: self._on_delete())
        self.tree.bind("<BackSpace>", lambda e: self._on_delete())  # macOS

        # Track selected purchase ID
        self.selected_purchase_id: Optional[int] = None

    def _create_context_menu(self) -> None:
        """Create right-click context menu."""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(
            label="View Details",
            command=self._on_view_details
        )
        self.context_menu.add_command(
            label="Edit",
            command=self._on_edit
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="Delete",
            command=self._on_delete
        )

        # Bind right-click (platform-specific)
        self.tree.bind("<Button-3>", self._show_context_menu)  # Windows/Linux
        self.tree.bind("<Button-2>", self._show_context_menu)  # macOS

    def _show_initial_state(self) -> None:
        """Show initial loading/empty state."""
        # Clear tree and show message
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _show_context_menu(self, event) -> None:
        """Show context menu at click position."""
        # Select row under cursor
        row_id = self.tree.identify_row(event.y)
        if row_id:
            self.tree.selection_set(row_id)
            self._on_item_select(None)
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()

    def _on_item_select(self, event) -> None:
        """Handle item selection."""
        selection = self.tree.selection()
        if selection:
            # Purchase ID is stored in the item's iid
            try:
                self.selected_purchase_id = int(selection[0])
            except (ValueError, TypeError):
                self.selected_purchase_id = None

    def _map_date_range(self, display_value: str) -> str:
        """Map display value to service parameter."""
        mapping = {
            "Last 30 days": "last_30_days",
            "Last 90 days": "last_90_days",
            "Last year": "last_year",
            "All time": "all_time"
        }
        return mapping.get(display_value, "last_30_days")

    def _get_supplier_id(self, supplier_name: str) -> Optional[int]:
        """Get supplier ID from name."""
        if supplier_name == "All":
            return None
        return self._supplier_map.get(supplier_name)

    def _on_filter_change(self, *args) -> None:
        """Handle filter changes."""
        self._load_purchases()

    def _on_search_change(self, event) -> None:
        """Handle search text changes."""
        self._load_purchases()

    def _clear_filters(self) -> None:
        """Reset all filters to defaults."""
        self.date_range_var.set("Last 30 days")
        self.supplier_var.set("All")
        self.search_var.set("")
        self._load_purchases()

    def _load_purchases(self) -> None:
        """Load purchases from service with current filters."""
        try:
            date_range = self._map_date_range(self.date_range_var.get())
            supplier_id = self._get_supplier_id(self.supplier_var.get())
            search = self.search_var.get().strip() or None

            self.purchases = get_purchases_filtered(
                date_range=date_range,
                supplier_id=supplier_id,
                search_query=search
            )
            self.filtered_purchases = self.purchases.copy()
            self._apply_sort()
            self._refresh_tree()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to load purchases: {str(e)}",
                parent=self
            )

    def _apply_sort(self) -> None:
        """Apply current sort to filtered_purchases."""
        if not self.filtered_purchases:
            return

        # Map column names to dict keys
        key_map = {
            "date": "purchase_date",
            "product": "product_name",
            "supplier": "supplier_name",
            "qty": "quantity_purchased",
            "price": "unit_price",
            "total": "total_cost",
            "remaining": "remaining_inventory"
        }

        sort_key = key_map.get(self._sort_column, "purchase_date")

        def get_sort_value(item):
            value = item.get(sort_key)
            # Handle None values
            if value is None:
                return "" if isinstance(item.get(sort_key, ""), str) else Decimal("0")
            return value

        self.filtered_purchases.sort(
            key=get_sort_value,
            reverse=self._sort_reverse
        )

    def _sort_by_column(self, column: str) -> None:
        """Sort by clicked column header."""
        if self._sort_column == column:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = column
            # Default sort direction based on column type
            self._sort_reverse = column in ("date", "qty", "price", "total", "remaining")

        self._apply_sort()
        self._refresh_tree()

    def _refresh_tree(self) -> None:
        """Refresh treeview with current filtered data."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.filtered_purchases:
            # Show empty state message
            self.tree.insert(
                "",
                "end",
                iid="empty",
                values=("", "No purchases found", "", "", "", "", "")
            )
            return

        # Insert purchases
        for purchase in self.filtered_purchases:
            purchase_id = purchase["id"]
            date_str = purchase["purchase_date"].strftime("%Y-%m-%d") if purchase["purchase_date"] else ""
            qty = f"{purchase['quantity_purchased']:.1f}"
            price = f"${purchase['unit_price']:.2f}" if purchase["unit_price"] else ""
            total = f"${purchase['total_cost']:.2f}" if purchase["total_cost"] else ""
            remaining = f"{purchase['remaining_inventory']:.1f}"

            self.tree.insert(
                "",
                "end",
                iid=str(purchase_id),
                values=(
                    date_str,
                    purchase["product_name"],
                    purchase["supplier_name"],
                    qty,
                    price,
                    total,
                    remaining
                )
            )

    def _populate_supplier_dropdown(self) -> None:
        """Populate supplier dropdown with available suppliers."""
        try:
            suppliers = get_all_suppliers()
            self._supplier_map = {}
            supplier_names = ["All"]

            for supplier in suppliers:
                name = supplier.get("name", "Unknown")
                supplier_id = supplier.get("id")
                if name and supplier_id:
                    self._supplier_map[name] = supplier_id
                    supplier_names.append(name)

            self.supplier_dropdown.configure(values=sorted(supplier_names))

        except Exception:
            # Silently handle - dropdown will just have "All"
            pass

    def _get_purchase_id_from_selection(self) -> Optional[int]:
        """Get purchase ID from current tree selection."""
        selection = self.tree.selection()
        if not selection or selection[0] == "empty":
            return None
        try:
            return int(selection[0])
        except (ValueError, TypeError):
            return None

    # =========================================================================
    # Action Handlers (placeholders for WP03-WP06)
    # =========================================================================

    def _on_add_purchase(self) -> None:
        """Open Add Purchase dialog."""
        from src.ui.dialogs.add_purchase_dialog import AddPurchaseDialog
        dialog = AddPurchaseDialog(self, on_save=self._load_purchases)
        dialog.focus()

    def _on_edit(self) -> None:
        """Open Edit Purchase dialog."""
        purchase_id = self._get_purchase_id_from_selection()
        if not purchase_id:
            return

        from src.ui.dialogs.edit_purchase_dialog import EditPurchaseDialog
        dialog = EditPurchaseDialog(self, purchase_id, on_save=self._load_purchases)
        dialog.focus()

    def _on_delete(self) -> None:
        """Handle delete action with validation."""
        purchase_id = self._get_purchase_id_from_selection()
        if not purchase_id:
            return

        try:
            # Check if can delete
            can_delete, reason = can_delete_purchase(purchase_id)

            if not can_delete:
                self._show_delete_blocked_dialog(purchase_id, reason)
            else:
                self._show_delete_confirmation_dialog(purchase_id)

        except PurchaseNotFound:
            messagebox.showerror(
                "Error",
                "Purchase not found. It may have been deleted.",
                parent=self
            )
            self._load_purchases()

    def _show_delete_blocked_dialog(self, purchase_id: int, reason: str) -> None:
        """Show dialog explaining why deletion is blocked."""
        try:
            purchase = get_purchase(purchase_id)
            usage_history = get_purchase_usage_history(purchase_id)

            message = "Cannot Delete Purchase\n\n"
            message += f"{purchase.product.display_name}\n"
            message += f"Purchased: {purchase.purchase_date}\n\n"
            message += f"Reason: {reason}\n\n"

            if usage_history:
                message += "Usage Details:\n"
                for usage in usage_history[:5]:
                    date_str = usage['depleted_at'].strftime('%m/%d/%Y') if usage.get('depleted_at') else ""
                    if date_str:
                        message += f"  - {usage['recipe_name']}: {usage['quantity_used']:.1f} ({date_str})\n"
                    else:
                        message += f"  - {usage['recipe_name']}: {usage['quantity_used']:.1f}\n"
                if len(usage_history) > 5:
                    message += f"  ... and {len(usage_history) - 5} more\n"

            message += "\nYou can edit this purchase instead, or manually adjust inventory if needed."

            messagebox.showerror("Cannot Delete", message, parent=self)

        except Exception:
            messagebox.showerror(
                "Cannot Delete",
                f"This purchase cannot be deleted.\n\nReason: {reason}",
                parent=self
            )

    def _show_delete_confirmation_dialog(self, purchase_id: int) -> None:
        """Show confirmation dialog for deletion."""
        try:
            purchase = get_purchase(purchase_id)
            remaining = get_remaining_inventory(purchase_id)

            # Build confirmation message
            message = "Delete this purchase?\n\n"
            message += f"{purchase.product.display_name}\n"
            message += f"Purchased: {purchase.purchase_date}\n"
            if purchase.unit_price:
                message += f"Price: ${purchase.unit_price:.2f}\n"

            if remaining > 0:
                package_unit = purchase.product.package_unit or "unit"
                message += f"\nThis will also remove {remaining:.1f} {package_unit}(s) from inventory.\n"

            message += "\nThis action cannot be undone."

            result = messagebox.askyesno(
                "Confirm Delete",
                message,
                parent=self
            )

            if result:
                # Re-validate before executing (race condition protection)
                can_delete, reason = can_delete_purchase(purchase_id)
                if can_delete:
                    self._execute_delete(purchase_id)
                else:
                    messagebox.showerror(
                        "Cannot Delete",
                        f"Purchase can no longer be deleted.\n\nReason: {reason}",
                        parent=self
                    )

        except PurchaseNotFound:
            messagebox.showerror(
                "Error",
                "Purchase not found. It may have been deleted.",
                parent=self
            )
            self._load_purchases()
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to load purchase details: {str(e)}",
                parent=self
            )

    def _execute_delete(self, purchase_id: int) -> None:
        """Execute the deletion."""
        try:
            from src.services.purchase_service import delete_purchase
            delete_purchase(purchase_id)
            self._load_purchases()
        except Exception as e:
            messagebox.showerror(
                "Delete Failed",
                f"Failed to delete purchase: {str(e)}",
                parent=self
            )

    def _on_view_details(self) -> None:
        """Open View Details dialog."""
        purchase_id = self._get_purchase_id_from_selection()
        if not purchase_id:
            return

        def on_edit(pid: int) -> None:
            """Callback to open edit dialog from details view."""
            from src.ui.dialogs.edit_purchase_dialog import EditPurchaseDialog
            dialog = EditPurchaseDialog(self, pid, on_save=self._load_purchases)
            dialog.focus()

        from src.ui.dialogs.purchase_details_dialog import PurchaseDetailsDialog
        dialog = PurchaseDetailsDialog(self, purchase_id, on_edit=on_edit)
        dialog.focus()

    # =========================================================================
    # Materials Inventory Section (Feature 059)
    # =========================================================================

    def _create_materials_section(self) -> None:
        """Create the Materials Inventory section."""
        self._materials_section_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._materials_section_frame.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
        self._materials_section_frame.grid_columnconfigure(0, weight=1)
        self._materials_section_frame.grid_rowconfigure(0, weight=0)  # Filter controls
        self._materials_section_frame.grid_rowconfigure(1, weight=1)  # Treeview
        self._materials_section_frame.grid_rowconfigure(2, weight=0)  # Status bar

        self._create_materials_filter_controls()
        self._create_materials_treeview()
        self._create_materials_status_bar()

        # Initially hidden (Food tab shown first)
        self._materials_section_frame.grid_remove()

    def _create_materials_filter_controls(self) -> None:
        """Create filter controls for Materials section."""
        filter_frame = ctk.CTkFrame(self._materials_section_frame)
        filter_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # Product filter dropdown
        product_label = ctk.CTkLabel(filter_frame, text="Product:")
        product_label.pack(side="left", padx=(0, 5))

        self._materials_product_var = ctk.StringVar(value="All Products")
        self._materials_product_dropdown = ctk.CTkComboBox(
            filter_frame,
            variable=self._materials_product_var,
            values=["All Products"],
            command=self._on_materials_filter_change,
            width=200,
        )
        self._materials_product_dropdown.pack(side="left", padx=(0, 20))

        # Show depleted checkbox
        self._materials_show_depleted_var = ctk.BooleanVar(value=False)
        self._materials_show_depleted_cb = ctk.CTkCheckBox(
            filter_frame,
            text="Show Depleted",
            variable=self._materials_show_depleted_var,
            command=self._on_materials_filter_change,
        )
        self._materials_show_depleted_cb.pack(side="left", padx=(0, 20))

        # Clear filters button
        clear_btn = ctk.CTkButton(
            filter_frame,
            text="Clear Filters",
            command=self._clear_materials_filters,
            width=100,
        )
        clear_btn.pack(side="right")

    def _create_materials_treeview(self) -> None:
        """Create the Materials treeview with columns."""
        # Container for treeview and scrollbar
        tree_frame = ctk.CTkFrame(self._materials_section_frame, fg_color="transparent")
        tree_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        # Define columns
        self._materials_columns = (
            "id", "product", "brand", "date", "qty_purchased",
            "qty_remaining", "cost_per_unit", "value"
        )

        # Column configurations
        self._materials_col_config = {
            "id": {"width": 0, "anchor": "center", "text": "ID"},  # Hidden
            "product": {"width": 200, "anchor": "w", "text": "Product"},
            "brand": {"width": 120, "anchor": "w", "text": "Brand"},
            "date": {"width": 100, "anchor": "center", "text": "Purchased"},
            "qty_purchased": {"width": 100, "anchor": "e", "text": "Qty Purchased"},
            "qty_remaining": {"width": 100, "anchor": "e", "text": "Qty Remaining"},
            "cost_per_unit": {"width": 90, "anchor": "e", "text": "Cost/Unit"},
            "value": {"width": 90, "anchor": "e", "text": "Value"},
        }

        # Configure ttk.Treeview style
        style = ttk.Style()
        style.configure("Materials.Treeview", rowheight=25)

        # Create Treeview
        self._materials_tree = ttk.Treeview(
            tree_frame,
            columns=self._materials_columns,
            show="headings",
            selectmode="browse",
            style="Materials.Treeview",
        )

        # Configure columns with sortable headers
        for col, config in self._materials_col_config.items():
            self._materials_tree.heading(
                col,
                text=config["text"],
                anchor=config["anchor"],
                command=lambda c=col: self._on_materials_column_click(c),
            )
            self._materials_tree.column(
                col,
                width=config["width"],
                anchor=config["anchor"],
                stretch=col != "id",  # ID doesn't stretch
            )

        # Hide ID column
        self._materials_tree.column("id", width=0, stretch=False)

        # Scrollbars
        y_scrollbar = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self._materials_tree.yview
        )
        x_scrollbar = ttk.Scrollbar(
            tree_frame, orient="horizontal", command=self._materials_tree.xview
        )
        self._materials_tree.configure(
            yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set
        )

        # Grid layout
        self._materials_tree.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar.grid(row=1, column=0, sticky="ew")

        # Empty state label (hidden by default)
        self._materials_empty_label = ctk.CTkLabel(
            tree_frame,
            text="No material inventory items.\nPurchase materials to see them here.",
            font=ctk.CTkFont(size=14),
            text_color="gray",
        )

        # Bind events for materials treeview
        self._materials_tree.bind("<Double-1>", self._on_materials_double_click)
        self._materials_tree.bind("<Button-3>", self._show_materials_context_menu)  # Win/Linux
        self._materials_tree.bind("<Button-2>", self._show_materials_context_menu)  # macOS

        # Create context menu for materials
        self._materials_context_menu = tk.Menu(self, tearoff=0)
        self._materials_context_menu.add_command(
            label="Adjust Quantity",
            command=self._on_adjust_material,
        )

    def _create_materials_status_bar(self) -> None:
        """Create status bar for Materials section."""
        status_frame = ctk.CTkFrame(self._materials_section_frame, fg_color="transparent")
        status_frame.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="ew")

        self._materials_count_label = ctk.CTkLabel(
            status_frame,
            text="0 items",
            font=ctk.CTkFont(size=12),
        )
        self._materials_count_label.pack(side="left")

    def _populate_materials_product_filter(self) -> None:
        """Load products for filter dropdown."""
        try:
            products = list_material_products(include_hidden=False)
            self._materials_product_map = {}
            product_names = ["All Products"]

            for product in products:
                name = product.get("display_name") or product.get("name", "Unknown")
                product_id = product.get("id")
                if name and product_id:
                    self._materials_product_map[name] = product_id
                    product_names.append(name)

            self._materials_product_dropdown.configure(values=sorted(product_names))
        except Exception:
            # Silently handle - dropdown will just have "All Products"
            pass

    def _on_materials_filter_change(self, *args) -> None:
        """Handle filter change with re-entry guard."""
        if self._materials_filter_updating:
            return
        self._materials_filter_updating = True
        try:
            self._refresh_materials_display()
        finally:
            self._materials_filter_updating = False

    def _clear_materials_filters(self) -> None:
        """Reset all Materials filters to defaults."""
        self._materials_product_var.set("All Products")
        self._materials_show_depleted_var.set(False)
        self._refresh_materials_display()

    def _on_materials_column_click(self, column: str) -> None:
        """Handle column header click for sorting."""
        if self._materials_sort_column == column:
            # Toggle direction if same column
            self._materials_sort_reverse = not self._materials_sort_reverse
        else:
            # New column, default to ascending (except date which defaults DESC)
            self._materials_sort_column = column
            self._materials_sort_reverse = column == "date"

        self._refresh_materials_display()

    def _get_materials_sort_key(self, column: str):
        """Return a sort key function for the given column."""
        key_map = {
            "id": lambda x: x.get("id", 0),
            "product": lambda x: (x.get("product_name") or "").lower(),
            "brand": lambda x: (x.get("brand") or "").lower(),
            "date": lambda x: x.get("purchase_date") or datetime.min,
            "qty_purchased": lambda x: float(x.get("quantity_purchased") or 0),
            "qty_remaining": lambda x: float(x.get("quantity_remaining") or 0),
            "cost_per_unit": lambda x: float(x.get("cost_per_unit") or 0),
            "value": lambda x: float(x.get("quantity_remaining") or 0) * float(x.get("cost_per_unit") or 0),
        }
        return key_map.get(column, lambda x: 0)

    def _update_materials_sort_indicators(self) -> None:
        """Update column headers to show sort direction."""
        for col in self._materials_columns:
            base_text = self._materials_col_config[col]["text"]
            if col == self._materials_sort_column:
                indicator = " \u25BC" if self._materials_sort_reverse else " \u25B2"
                self._materials_tree.heading(col, text=base_text + indicator)
            else:
                self._materials_tree.heading(col, text=base_text)

    def _show_materials_empty_state(self, show: bool) -> None:
        """Show or hide the empty state message."""
        if show:
            # Hide treeview, show empty message
            self._materials_tree.grid_remove()
            self._materials_empty_label.place(relx=0.5, rely=0.5, anchor="center")
        else:
            # Show treeview, hide empty message
            self._materials_empty_label.place_forget()
            self._materials_tree.grid()

    def _update_materials_count(self, count: int, total: int = None) -> None:
        """Update the item count display."""
        if total is not None and total != count:
            text = f"{count} of {total} items"
        else:
            text = f"{count} item{'s' if count != 1 else ''}"
        self._materials_count_label.configure(text=text)

    def _get_product_id_by_name(self, product_name: str) -> Optional[int]:
        """Get product ID from display name."""
        return self._materials_product_map.get(product_name)

    def _refresh_materials_display(self) -> None:
        """Load and display material inventory items."""
        try:
            # Build filter parameters
            product_filter = self._materials_product_var.get()
            product_id = None
            if product_filter != "All Products":
                product_id = self._get_product_id_by_name(product_filter)

            include_depleted = self._materials_show_depleted_var.get()

            # Fetch data from service
            self._materials_items = list_inventory_items(
                product_id=product_id,
                include_depleted=include_depleted,
            )

            # Apply local sorting
            sort_key = self._get_materials_sort_key(self._materials_sort_column)
            self._materials_items.sort(key=sort_key, reverse=self._materials_sort_reverse)

            # Clear existing items
            for item in self._materials_tree.get_children():
                self._materials_tree.delete(item)

            # Check for empty state
            if not self._materials_items:
                self._show_materials_empty_state(True)
                self._update_materials_count(0)
                return

            self._show_materials_empty_state(False)

            # Insert new items
            for item in self._materials_items:
                # Format values
                date_str = ""
                if item.get("purchase_date"):
                    date_str = item["purchase_date"].strftime("%Y-%m-%d")

                qty_purchased = f"{float(item.get('quantity_purchased', 0)):.2f}"
                qty_remaining = f"{float(item.get('quantity_remaining', 0)):.2f}"

                cost = item.get("cost_per_unit")
                cost_str = f"${float(cost):.4f}" if cost else "$0.0000"

                remaining = float(item.get("quantity_remaining", 0))
                value = remaining * float(cost or 0)
                value_str = f"${value:.2f}"

                values = (
                    item["id"],
                    item.get("product_name", "Unknown"),
                    item.get("brand", ""),
                    date_str,
                    qty_purchased,
                    qty_remaining,
                    cost_str,
                    value_str,
                )
                self._materials_tree.insert("", "end", iid=str(item["id"]), values=values)

            # Update UI state
            self._update_materials_count(len(self._materials_items))
            self._update_materials_sort_indicators()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to load material inventory: {str(e)}",
                parent=self,
            )

    def refresh(self) -> None:
        """Refresh the tab with current data."""
        self._data_loaded = True
        self._populate_supplier_dropdown()
        self._load_purchases()
        # Also refresh materials if that tab is active
        if self._tab_var.get() == "materials":
            self._populate_materials_product_filter()
            self._refresh_materials_display()

    # =========================================================================
    # Materials Context Menu and Adjustment Dialog (Feature 059)
    # =========================================================================

    def _get_selected_material_item(self) -> Optional[Dict]:
        """Get the selected material inventory item dict."""
        selection = self._materials_tree.selection()
        if not selection:
            return None

        try:
            item_id = int(selection[0])
            # Find the item in our cached list
            for item in self._materials_items:
                if item["id"] == item_id:
                    return item
        except (ValueError, TypeError):
            pass
        return None

    def _show_materials_context_menu(self, event) -> None:
        """Show context menu at click position."""
        row_id = self._materials_tree.identify_row(event.y)
        if row_id:
            self._materials_tree.selection_set(row_id)
            try:
                self._materials_context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self._materials_context_menu.grab_release()

    def _on_materials_double_click(self, event) -> None:
        """Handle double-click on materials treeview row."""
        self._on_adjust_material()

    def _on_adjust_material(self) -> None:
        """Open the Material Adjustment Dialog for the selected item."""
        item = self._get_selected_material_item()
        if not item:
            return

        from src.ui.dialogs.material_adjustment_dialog import MaterialAdjustmentDialog

        dialog = MaterialAdjustmentDialog(
            self,
            inventory_item=item,
            on_save=lambda result: self._refresh_materials_display(),
        )
        dialog.focus()
