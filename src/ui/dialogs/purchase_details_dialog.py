"""PurchaseDetailsDialog - Modal dialog for viewing purchase details.

Provides read-only view of purchase details with:
- Purchase info (product, date, supplier, price, notes)
- Inventory tracking (original, used, remaining)
- Usage history table (date, recipe, quantity, cost)
- Edit Purchase button to open edit dialog

Implements User Story 6: View Purchase Details (Feature 042).
"""

import customtkinter as ctk
from tkinter import ttk, messagebox
from decimal import Decimal
from typing import Optional, Callable, Any, List, Dict

from src.services.purchase_service import (
    get_purchase,
    get_remaining_inventory,
    get_purchase_usage_history,
)
from src.services.exceptions import PurchaseNotFound


class PurchaseDetailsDialog(ctk.CTkToplevel):
    """Modal dialog for viewing purchase details.

    Displays purchase information, inventory tracking, and usage history
    in a read-only view. Provides Edit button to open edit dialog.
    """

    def __init__(
        self,
        parent,
        purchase_id: int,
        on_edit: Optional[Callable[[int], None]] = None,
    ):
        """Initialize PurchaseDetailsDialog.

        Args:
            parent: Parent window
            purchase_id: ID of purchase to view
            on_edit: Callback function when Edit button is clicked,
                     receives purchase_id as parameter
        """
        super().__init__(parent)
        self.purchase_id = purchase_id
        self.on_edit = on_edit

        self.title("Purchase Details")
        self.geometry("550x650")
        self.resizable(False, False)

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Data storage
        self.purchase: Optional[Any] = None
        self.remaining: Decimal = Decimal("0")
        self.usage_history: List[Dict] = []

        # Load data
        if not self._load_data():
            return  # Dialog will be destroyed if purchase not found

        # Create UI
        self._create_widgets()
        self._layout_widgets()
        self._bind_events()

        # Center on parent
        self.update_idletasks()
        self._center_on_parent(parent)

    def _center_on_parent(self, parent) -> None:
        """Center dialog on parent window."""
        parent.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()

        w = self.winfo_width()
        h = self.winfo_height()

        x = px + (pw - w) // 2
        y = py + (ph - h) // 2

        self.geometry(f"+{x}+{y}")

    def _load_data(self) -> bool:
        """Load purchase data from services.

        Returns:
            True if data loaded successfully, False otherwise.
        """
        try:
            self.purchase = get_purchase(self.purchase_id)
            self.remaining = get_remaining_inventory(self.purchase_id)
            self.usage_history = get_purchase_usage_history(self.purchase_id)
            return True
        except PurchaseNotFound:
            messagebox.showerror(
                "Error",
                "Purchase not found. It may have been deleted.",
                parent=self.master
            )
            self.destroy()
            return False
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to load purchase details: {str(e)}",
                parent=self.master
            )
            self.destroy()
            return False

    def _create_widgets(self) -> None:
        """Create all dialog widgets."""
        # Info section
        self.info_frame = self._create_info_section()

        # Inventory tracking section
        self.inventory_frame = self._create_inventory_section()

        # Usage history section
        self.usage_frame = self._create_usage_section()

        # Buttons
        self.button_frame = self._create_buttons()

    def _create_info_section(self) -> ctk.CTkFrame:
        """Create purchase info section (T041)."""
        info_frame = ctk.CTkFrame(self)

        # Product name (large, bold)
        product_label = ctk.CTkLabel(
            info_frame,
            text=self.purchase.product.display_name,
            font=ctk.CTkFont(size=18, weight="bold")
        )
        product_label.pack(anchor="w", padx=15, pady=(15, 10))

        # Details grid
        details = [
            ("Date:", self.purchase.purchase_date.strftime("%B %d, %Y") if self.purchase.purchase_date else ""),
            ("Supplier:", self.purchase.supplier.name if self.purchase.supplier else "Unknown"),
            ("Quantity:", f"{self.purchase.quantity_purchased} package(s)"),
            ("Unit Price:", f"${self.purchase.unit_price:.2f}" if self.purchase.unit_price else "$0.00"),
            ("Total Cost:", f"${self.purchase.total_cost:.2f}" if self.purchase.total_cost else "$0.00"),
        ]

        for label, value in details:
            row = ctk.CTkFrame(info_frame, fg_color="transparent")
            ctk.CTkLabel(row, text=label, width=100, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=value, anchor="w").pack(side="left")
            row.pack(fill="x", padx=15, pady=2)

        # Notes (if present)
        if self.purchase.notes:
            notes_label = ctk.CTkLabel(info_frame, text="Notes:", anchor="w")
            notes_label.pack(anchor="w", padx=15, pady=(10, 2))
            notes_box = ctk.CTkTextbox(info_frame, height=60, width=480)
            notes_box.insert("1.0", self.purchase.notes)
            notes_box.configure(state="disabled")
            notes_box.pack(padx=15, pady=(0, 10))

        return info_frame

    def _create_inventory_section(self) -> ctk.CTkFrame:
        """Create inventory tracking section (T042)."""
        inv_frame = ctk.CTkFrame(self)

        ctk.CTkLabel(
            inv_frame,
            text="Inventory Tracking",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        # Calculate quantities
        package_qty = Decimal(str(self.purchase.product.package_unit_quantity or 1))
        original = Decimal(str(self.purchase.quantity_purchased)) * package_qty
        remaining = self.remaining
        used = original - remaining
        used_pct = (used / original * 100) if original > 0 else Decimal("0")

        unit = self.purchase.product.package_unit or "unit"

        # Display rows
        rows = [
            ("Original:", f"{original:.1f} {unit}(s)", None),
            ("Used:", f"{used:.1f} {unit}(s) ({used_pct:.0f}%)", None),
            ("Remaining:", f"{remaining:.1f} {unit}(s)", self._get_remaining_color(remaining, original)),
        ]

        for label, value, color in rows:
            row = ctk.CTkFrame(inv_frame, fg_color="transparent")
            ctk.CTkLabel(row, text=label, width=100, anchor="w").pack(side="left")
            if color:
                ctk.CTkLabel(row, text=value, anchor="w", text_color=color).pack(side="left")
            else:
                ctk.CTkLabel(row, text=value, anchor="w").pack(side="left")
            row.pack(fill="x", padx=15, pady=2)

        return inv_frame

    def _get_remaining_color(self, remaining: Decimal, original: Decimal) -> Optional[str]:
        """Get color for remaining quantity based on level."""
        if remaining == 0:
            return "red"
        elif original > 0 and remaining < original * Decimal("0.2"):
            return "orange"
        return None

    def _create_usage_section(self) -> ctk.CTkFrame:
        """Create usage history section (T043)."""
        usage_frame = ctk.CTkFrame(self)

        ctk.CTkLabel(
            usage_frame,
            text="Usage History",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        if not self.usage_history:
            ctk.CTkLabel(
                usage_frame,
                text="No usage recorded yet",
                text_color="gray"
            ).pack(anchor="w", padx=15, pady=(0, 10))
            return usage_frame

        # Create container for treeview
        tree_container = ctk.CTkFrame(usage_frame, fg_color="transparent")
        tree_container.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        # Create treeview for usage
        columns = ("date", "recipe", "quantity", "cost")
        self.usage_tree = ttk.Treeview(
            tree_container,
            columns=columns,
            show="headings",
            height=8
        )

        self.usage_tree.heading("date", text="Date")
        self.usage_tree.heading("recipe", text="Recipe")
        self.usage_tree.heading("quantity", text="Qty Used")
        self.usage_tree.heading("cost", text="Cost")

        self.usage_tree.column("date", width=100)
        self.usage_tree.column("recipe", width=200)
        self.usage_tree.column("quantity", width=80, anchor="e")
        self.usage_tree.column("cost", width=80, anchor="e")

        # Scrollbar
        scrollbar = ttk.Scrollbar(
            tree_container,
            orient="vertical",
            command=self.usage_tree.yview
        )
        self.usage_tree.configure(yscrollcommand=scrollbar.set)

        # Populate (limit to 50)
        for usage in self.usage_history[:50]:
            date_str = ""
            if usage.get("depleted_at"):
                date_str = usage["depleted_at"].strftime("%m/%d/%Y")

            cost_str = ""
            if usage.get("cost") is not None:
                cost_str = f"${usage['cost']:.2f}"

            self.usage_tree.insert("", "end", values=(
                date_str,
                usage.get("recipe_name", "Unknown"),
                f"{usage.get('quantity_used', 0):.1f}",
                cost_str
            ))

        self.usage_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        if len(self.usage_history) > 50:
            ctk.CTkLabel(
                usage_frame,
                text=f"Showing 50 of {len(self.usage_history)} usage records",
                text_color="gray"
            ).pack(anchor="w", padx=15, pady=(0, 10))

        return usage_frame

    def _create_buttons(self) -> ctk.CTkFrame:
        """Create button section (T044)."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")

        edit_btn = ctk.CTkButton(
            button_frame,
            text="Edit Purchase",
            command=self._on_edit_click,
            width=120
        )
        edit_btn.pack(side="left", padx=10)

        close_btn = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self.destroy,
            width=100,
            fg_color="gray"
        )
        close_btn.pack(side="right", padx=10)

        return button_frame

    def _layout_widgets(self) -> None:
        """Layout all widgets."""
        self.info_frame.pack(fill="x", padx=10, pady=5)
        self.inventory_frame.pack(fill="x", padx=10, pady=5)
        self.usage_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.button_frame.pack(fill="x", padx=10, pady=(10, 15))

    def _bind_events(self) -> None:
        """Bind event handlers."""
        # Escape to close
        self.bind("<Escape>", lambda e: self.destroy())

    def _on_edit_click(self) -> None:
        """Handle Edit button click."""
        self.destroy()
        if self.on_edit:
            self.on_edit(self.purchase_id)
