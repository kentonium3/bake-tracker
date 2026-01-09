"""AddPurchaseDialog - Modal dialog for recording new purchases.

Provides form for entering purchase details with:
- Product dropdown with search
- Date picker (defaults to today, validates not future)
- Quantity entry (whole packages only)
- Unit price with auto-fill from last purchase
- Supplier dropdown with preferred supplier default
- Notes text area
- Live preview of total cost and inventory impact

Implements User Story 3: Add New Purchase (Feature 042).
"""

import customtkinter as ctk
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, Callable, Dict, Any, List

from src.services.product_catalog_service import get_products
from src.services.supplier_service import get_all_suppliers
from src.services.purchase_service import (
    record_purchase,
    get_last_price_at_supplier,
    get_last_price_any_supplier,
)


class AddPurchaseDialog(ctk.CTkToplevel):
    """Modal dialog for adding a new purchase.

    Provides form fields for all purchase details with validation,
    auto-fill from previous purchases, and live preview.
    """

    def __init__(
        self,
        parent,
        on_save: Optional[Callable] = None,
    ):
        """Initialize AddPurchaseDialog.

        Args:
            parent: Parent window
            on_save: Callback function when purchase is saved successfully
        """
        super().__init__(parent)
        self.on_save = on_save

        self.title("Add Purchase")
        self.geometry("500x600")
        self.resizable(False, False)

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Data storage
        self.products: List[Dict[str, Any]] = []
        self.suppliers: List[Dict[str, Any]] = []
        self.product_map: Dict[str, Dict[str, Any]] = {}  # display_name -> product dict
        self.supplier_map: Dict[str, Dict[str, Any]] = {}  # name -> supplier dict

        # Load data
        self._load_products()
        self._load_suppliers()

        # Create UI
        self._create_widgets()
        self._layout_widgets()
        self._bind_events()

        # Center on parent
        self.update_idletasks()
        self._center_on_parent(parent)

        # Focus on product dropdown
        self.product_combo.focus_set()

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

    def _load_products(self) -> None:
        """Load products from service."""
        try:
            self.products = get_products(include_hidden=False)
            self.product_map = {}
            for p in self.products:
                display_name = p.get("display_name", p.get("product_name", "Unknown"))
                self.product_map[display_name] = p
        except Exception:
            self.products = []
            self.product_map = {}

    def _load_suppliers(self) -> None:
        """Load suppliers from service."""
        try:
            self.suppliers = get_all_suppliers()
            self.supplier_map = {}
            for s in self.suppliers:
                name = s.get("name", "Unknown")
                self.supplier_map[name] = s
        except Exception:
            self.suppliers = []
            self.supplier_map = {}

    def _create_widgets(self) -> None:
        """Create all dialog widgets."""
        # Title
        self.title_label = ctk.CTkLabel(
            self,
            text="Add New Purchase",
            font=ctk.CTkFont(size=18, weight="bold")
        )

        # Form frame
        self.form_frame = ctk.CTkFrame(self)

        # Product selection
        self.product_label = ctk.CTkLabel(
            self.form_frame,
            text="Product *",
            anchor="w"
        )
        product_names = sorted(self.product_map.keys())
        self.product_var = ctk.StringVar()
        self.product_combo = ctk.CTkComboBox(
            self.form_frame,
            variable=self.product_var,
            values=product_names,
            width=350,
            command=self._on_product_selected
        )

        # Date entry
        self.date_label = ctk.CTkLabel(
            self.form_frame,
            text="Purchase Date *",
            anchor="w"
        )
        self.date_var = ctk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        self.date_entry = ctk.CTkEntry(
            self.form_frame,
            textvariable=self.date_var,
            width=150,
            placeholder_text="YYYY-MM-DD"
        )
        self.date_hint = ctk.CTkLabel(
            self.form_frame,
            text="Format: YYYY-MM-DD",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )

        # Quantity entry
        self.qty_label = ctk.CTkLabel(
            self.form_frame,
            text="Quantity *",
            anchor="w"
        )
        self.qty_var = ctk.StringVar(value="1")
        self.qty_entry = ctk.CTkEntry(
            self.form_frame,
            textvariable=self.qty_var,
            width=100
        )
        self.qty_unit_label = ctk.CTkLabel(
            self.form_frame,
            text="package(s)",
            text_color="gray"
        )

        # Unit price entry
        self.price_label = ctk.CTkLabel(
            self.form_frame,
            text="Unit Price *",
            anchor="w"
        )
        self.price_var = ctk.StringVar()
        self.price_entry = ctk.CTkEntry(
            self.form_frame,
            textvariable=self.price_var,
            width=100,
            placeholder_text="0.00"
        )
        self.price_hint = ctk.CTkLabel(
            self.form_frame,
            text="",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )

        # Supplier dropdown
        self.supplier_label = ctk.CTkLabel(
            self.form_frame,
            text="Supplier *",
            anchor="w"
        )
        supplier_names = sorted(self.supplier_map.keys())
        self.supplier_var = ctk.StringVar()
        self.supplier_combo = ctk.CTkComboBox(
            self.form_frame,
            variable=self.supplier_var,
            values=supplier_names,
            width=250
        )

        # Notes text area
        self.notes_label = ctk.CTkLabel(
            self.form_frame,
            text="Notes (optional)",
            anchor="w"
        )
        self.notes_text = ctk.CTkTextbox(
            self.form_frame,
            height=60,
            width=350
        )

        # Preview frame
        self.preview_frame = ctk.CTkFrame(self)
        self.preview_title = ctk.CTkLabel(
            self.preview_frame,
            text="Preview",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.preview_label = ctk.CTkLabel(
            self.preview_frame,
            text="Select a product to see preview",
            text_color="gray",
            justify="left"
        )

        # Error label
        self.error_label = ctk.CTkLabel(
            self,
            text="",
            text_color="red"
        )

        # Button frame
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.cancel_btn = ctk.CTkButton(
            self.button_frame,
            text="Cancel",
            command=self.destroy,
            width=100,
            fg_color="gray"
        )
        self.save_btn = ctk.CTkButton(
            self.button_frame,
            text="Add Purchase",
            command=self._on_save,
            width=120
        )

    def _layout_widgets(self) -> None:
        """Layout all widgets using grid."""
        # Title
        self.title_label.pack(pady=(15, 10))

        # Form frame
        self.form_frame.pack(fill="x", padx=20, pady=10)

        # Product row
        self.product_label.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 2))
        self.product_combo.grid(row=1, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 10))

        # Date row
        self.date_label.grid(row=2, column=0, sticky="w", padx=10, pady=(10, 2))
        self.date_entry.grid(row=3, column=0, sticky="w", padx=10, pady=(0, 2))
        self.date_hint.grid(row=3, column=1, sticky="w", padx=5, pady=(0, 2))

        # Quantity row
        self.qty_label.grid(row=4, column=0, sticky="w", padx=10, pady=(10, 2))
        self.qty_entry.grid(row=5, column=0, sticky="w", padx=10, pady=(0, 10))
        self.qty_unit_label.grid(row=5, column=1, sticky="w", padx=5, pady=(0, 10))

        # Price row
        self.price_label.grid(row=6, column=0, sticky="w", padx=10, pady=(10, 2))
        self.price_entry.grid(row=7, column=0, sticky="w", padx=10, pady=(0, 2))
        self.price_hint.grid(row=7, column=1, columnspan=2, sticky="w", padx=5, pady=(0, 2))

        # Supplier row
        self.supplier_label.grid(row=8, column=0, sticky="w", padx=10, pady=(10, 2))
        self.supplier_combo.grid(row=9, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 10))

        # Notes row
        self.notes_label.grid(row=10, column=0, sticky="w", padx=10, pady=(10, 2))
        self.notes_text.grid(row=11, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 10))

        # Preview frame
        self.preview_frame.pack(fill="x", padx=20, pady=10)
        self.preview_title.pack(anchor="w", padx=10, pady=(5, 2))
        self.preview_label.pack(anchor="w", padx=10, pady=(0, 10))

        # Error label
        self.error_label.pack(pady=5)

        # Buttons
        self.button_frame.pack(fill="x", padx=20, pady=(10, 20))
        self.cancel_btn.pack(side="left", padx=10)
        self.save_btn.pack(side="right", padx=10)

    def _bind_events(self) -> None:
        """Bind event handlers."""
        # Update preview on field changes
        self.qty_var.trace_add("write", lambda *args: self._update_preview())
        self.price_var.trace_add("write", lambda *args: self._update_preview())

        # Escape to close
        self.bind("<Escape>", lambda e: self.destroy())

        # Enter to save
        self.bind("<Return>", lambda e: self._on_save())

    def _on_product_selected(self, product_name: str) -> None:
        """Handle product selection - auto-fill price and supplier."""
        product = self.product_map.get(product_name)
        if not product:
            return

        product_id = product.get("id")
        if not product_id:
            return

        # Update unit label
        package_unit = product.get("package_unit", "package")
        self.qty_unit_label.configure(text=f"{package_unit}(s)")

        # Try to auto-fill price from last purchase at selected supplier
        supplier_name = self.supplier_var.get()
        supplier = self.supplier_map.get(supplier_name)
        price_filled = False

        if supplier:
            supplier_id = supplier.get("id")
            if supplier_id:
                last_price = get_last_price_at_supplier(product_id, supplier_id)
                if last_price:
                    self.price_var.set(f"{Decimal(last_price['unit_price']):.2f}")
                    self.price_hint.configure(
                        text=f"Last: ${last_price['unit_price']} on {last_price['purchase_date']}"
                    )
                    price_filled = True

        # Fallback: get last price from any supplier
        if not price_filled:
            last_price = get_last_price_any_supplier(product_id)
            if last_price:
                self.price_var.set(f"{Decimal(last_price['unit_price']):.2f}")
                self.price_hint.configure(
                    text=f"Last: ${last_price['unit_price']} at {last_price['supplier_name']}"
                )
            else:
                self.price_hint.configure(text="No price history")

        # Auto-fill supplier from preferred if not already selected
        if not self.supplier_var.get():
            preferred_supplier_id = product.get("preferred_supplier_id")
            if preferred_supplier_id:
                # Find supplier by ID
                for name, sup in self.supplier_map.items():
                    if sup.get("id") == preferred_supplier_id:
                        self.supplier_var.set(name)
                        break

        self._update_preview()

    def _update_preview(self) -> None:
        """Update preview with calculated values."""
        try:
            qty_str = self.qty_var.get().strip()
            price_str = self.price_var.get().strip()

            if not qty_str or not price_str:
                self.preview_label.configure(
                    text="Enter quantity and price to see preview",
                    text_color="gray"
                )
                return

            qty = Decimal(qty_str)
            price = Decimal(price_str)

            if qty <= 0:
                self.preview_label.configure(
                    text="Quantity must be greater than 0",
                    text_color="orange"
                )
                return

            total = qty * price

            # Get product info for inventory preview
            product_name = self.product_var.get()
            product = self.product_map.get(product_name)

            if product:
                package_unit_qty = Decimal(str(product.get("package_unit_quantity", 1)))
                package_unit = product.get("package_unit", "units")
                inventory_units = qty * package_unit_qty

                preview_text = (
                    f"Total Cost: ${total:.2f}\n"
                    f"Inventory: +{inventory_units:.1f} {package_unit}"
                )
            else:
                preview_text = f"Total Cost: ${total:.2f}"

            self.preview_label.configure(text=preview_text, text_color="green")

        except (InvalidOperation, ValueError):
            self.preview_label.configure(
                text="Enter valid numbers",
                text_color="orange"
            )

    def _validate(self) -> tuple:
        """Validate all form fields.

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        # Product selected?
        product_name = self.product_var.get()
        if not product_name or product_name not in self.product_map:
            return False, "Please select a product"

        # Date valid and not future?
        date_str = self.date_var.get().strip()
        try:
            purchase_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if purchase_date > date.today():
                return False, "Purchase date cannot be in the future"
        except ValueError:
            return False, "Invalid date format (use YYYY-MM-DD)"

        # Quantity valid? (whole packages only - model uses Integer)
        qty_str = self.qty_var.get().strip()
        try:
            qty = Decimal(qty_str)
            if qty <= 0:
                return False, "Quantity must be greater than 0"
            # Must be a whole number (packages come in whole units)
            if qty != qty.to_integral_value():
                return False, "Quantity must be a whole number (whole packages only)"
        except (InvalidOperation, ValueError):
            return False, "Invalid quantity - enter a number"

        # Price valid?
        price_str = self.price_var.get().strip()
        try:
            price = Decimal(price_str)
            if price < 0:
                return False, "Price cannot be negative"
        except (InvalidOperation, ValueError):
            return False, "Invalid price - enter a number"

        # Supplier selected?
        supplier_name = self.supplier_var.get()
        if not supplier_name or supplier_name not in self.supplier_map:
            return False, "Please select a supplier"

        return True, ""

    def _show_error(self, message: str) -> None:
        """Display error message."""
        self.error_label.configure(text=message)

    def _clear_error(self) -> None:
        """Clear error message."""
        self.error_label.configure(text="")

    def _on_save(self) -> None:
        """Handle save button click."""
        self._clear_error()

        # Validate
        is_valid, error = self._validate()
        if not is_valid:
            self._show_error(error)
            return

        # Get form values
        product = self.product_map[self.product_var.get()]
        supplier = self.supplier_map[self.supplier_var.get()]
        purchase_date = datetime.strptime(self.date_var.get().strip(), "%Y-%m-%d").date()
        quantity = Decimal(self.qty_var.get().strip())
        unit_price = Decimal(self.price_var.get().strip())
        notes = self.notes_text.get("1.0", "end-1c").strip() or None

        try:
            # Record purchase using service
            record_purchase(
                product_id=product["id"],
                quantity=quantity,
                total_cost=quantity * unit_price,
                purchase_date=purchase_date,
                store=supplier["name"],
                notes=notes
            )

            # Callback to refresh list
            if self.on_save:
                self.on_save()

            self.destroy()

        except Exception as e:
            self._show_error(f"Failed to save: {str(e)}")
