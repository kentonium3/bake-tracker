"""PurchasesTab - Purchase history tracking with filtering and sorting.

Displays purchase history with:
- Date range filter (Last 30 days, Last 90 days, Last year, All time)
- Supplier filter
- Product search
- Sortable columns
- Context menu for CRUD operations

Implements FR-022: Purchase tracking (Feature 042).
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Optional, List, Dict
from decimal import Decimal

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

        # State
        self.purchases: List[Dict] = []
        self.filtered_purchases: List[Dict] = []
        self._data_loaded = False
        self._sort_column = "purchase_date"
        self._sort_reverse = True  # Default: newest first

        # Supplier map for ID lookup
        self._supplier_map: Dict[str, int] = {}  # name -> id

        # Grid configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Header - fixed height
        self.grid_rowconfigure(1, weight=0)  # Controls - fixed height
        self.grid_rowconfigure(2, weight=1)  # Content - expandable

        # Create UI components
        self._create_header()
        self._create_controls()
        self._create_purchase_list()
        self._create_context_menu()

        # Configure parent to expand
        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(0, weight=1)

        # Grid the frame to fill parent
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Keyboard shortcut for new purchase (Ctrl+N / Cmd+N)
        self.bind("<Control-n>", lambda e: self._on_add_purchase())
        self.bind("<Command-n>", lambda e: self._on_add_purchase())  # macOS

        # Show initial state
        self._show_initial_state()

    def _create_header(self) -> None:
        """Create the header with title and subtitle."""
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))

        title = ctk.CTkLabel(
            header_frame, text="Purchase History", font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            header_frame,
            text="View, add, and manage your purchases",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        subtitle.pack(anchor="w")

    def _create_controls(self) -> None:
        """Create filter controls and action buttons."""
        controls_frame = ctk.CTkFrame(self)
        controls_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        controls_frame.grid_columnconfigure(10, weight=1)  # Spacer column

        # Add Purchase button
        add_btn = ctk.CTkButton(
            controls_frame, text="+ Add Purchase", command=self._on_add_purchase, width=120
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
            width=130,
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
            width=150,
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
            width=200,
        )
        self.search_entry.grid(row=0, column=6, padx=5, pady=5)
        self.search_entry.bind("<KeyRelease>", self._on_search_change)

        # Clear filters button
        clear_btn = ctk.CTkButton(
            controls_frame, text="Clear", command=self._clear_filters, width=60
        )
        clear_btn.grid(row=0, column=7, padx=10, pady=5)

    def _create_purchase_list(self) -> None:
        """Create the purchase list treeview."""
        # Container for treeview and scrollbar
        list_frame = ctk.CTkFrame(self, fg_color="transparent")
        list_frame.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)

        # Configure ttk.Treeview style
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)

        # Define columns
        columns = ("date", "product", "supplier", "qty", "price", "total", "remaining")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")

        # Column configurations with sortable headers
        col_config = {
            "date": ("Date", 100, "w"),
            "product": ("Product", 200, "w"),
            "supplier": ("Supplier", 120, "w"),
            "qty": ("Qty", 60, "e"),
            "price": ("Unit Price", 80, "e"),
            "total": ("Total", 80, "e"),
            "remaining": ("Remaining", 80, "e"),
        }

        for col, (title, width, anchor) in col_config.items():
            self.tree.heading(
                col, text=title, anchor=anchor, command=lambda c=col: self._sort_by_column(c)
            )
            self.tree.column(col, width=width, minwidth=width - 20, anchor=anchor)

        # Scrollbars
        y_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        x_scrollbar = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)

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
        self.context_menu.add_command(label="View Details", command=self._on_view_details)
        self.context_menu.add_command(label="Edit", command=self._on_edit)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete", command=self._on_delete)

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
            "All time": "all_time",
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
                date_range=date_range, supplier_id=supplier_id, search_query=search
            )
            self.filtered_purchases = self.purchases.copy()
            self._apply_sort()
            self._refresh_tree()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load purchases: {str(e)}", parent=self)

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
            "remaining": "remaining_inventory",
        }

        sort_key = key_map.get(self._sort_column, "purchase_date")

        def get_sort_value(item):
            value = item.get(sort_key)
            # Handle None values
            if value is None:
                return "" if isinstance(item.get(sort_key, ""), str) else Decimal("0")
            return value

        self.filtered_purchases.sort(key=get_sort_value, reverse=self._sort_reverse)

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
                "", "end", iid="empty", values=("", "No purchases found", "", "", "", "", "")
            )
            return

        # Insert purchases
        for purchase in self.filtered_purchases:
            purchase_id = purchase["id"]
            date_str = (
                purchase["purchase_date"].strftime("%Y-%m-%d") if purchase["purchase_date"] else ""
            )
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
                    remaining,
                ),
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
                "Error", "Purchase not found. It may have been deleted.", parent=self
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
                    date_str = (
                        usage["depleted_at"].strftime("%m/%d/%Y")
                        if usage.get("depleted_at")
                        else ""
                    )
                    if date_str:
                        message += f"  - {usage['recipe_name']}: {usage['quantity_used']:.1f} ({date_str})\n"
                    else:
                        message += f"  - {usage['recipe_name']}: {usage['quantity_used']:.1f}\n"
                if len(usage_history) > 5:
                    message += f"  ... and {len(usage_history) - 5} more\n"

            message += (
                "\nYou can edit this purchase instead, or manually adjust inventory if needed."
            )

            messagebox.showerror("Cannot Delete", message, parent=self)

        except Exception:
            messagebox.showerror(
                "Cannot Delete",
                f"This purchase cannot be deleted.\n\nReason: {reason}",
                parent=self,
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
                message += (
                    f"\nThis will also remove {remaining:.1f} {package_unit}(s) from inventory.\n"
                )

            message += "\nThis action cannot be undone."

            result = messagebox.askyesno("Confirm Delete", message, parent=self)

            if result:
                # Re-validate before executing (race condition protection)
                can_delete, reason = can_delete_purchase(purchase_id)
                if can_delete:
                    self._execute_delete(purchase_id)
                else:
                    messagebox.showerror(
                        "Cannot Delete",
                        f"Purchase can no longer be deleted.\n\nReason: {reason}",
                        parent=self,
                    )

        except PurchaseNotFound:
            messagebox.showerror(
                "Error", "Purchase not found. It may have been deleted.", parent=self
            )
            self._load_purchases()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load purchase details: {str(e)}", parent=self)

    def _execute_delete(self, purchase_id: int) -> None:
        """Execute the deletion."""
        try:
            from src.services.purchase_service import delete_purchase

            delete_purchase(purchase_id)
            self._load_purchases()
        except Exception as e:
            messagebox.showerror(
                "Delete Failed", f"Failed to delete purchase: {str(e)}", parent=self
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

    def refresh(self) -> None:
        """Refresh the tab with current data."""
        self._data_loaded = True
        self._populate_supplier_dropdown()
        self._load_purchases()
