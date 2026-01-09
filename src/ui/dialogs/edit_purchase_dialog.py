"""EditPurchaseDialog - Modal dialog for editing existing purchases.

Provides form for editing purchase details with:
- Read-only product display (cannot be changed)
- Date picker (validates not future)
- Quantity entry with validation (new >= consumed)
- Unit price with FIFO recalculation on change
- Supplier dropdown
- Notes text area
- Live preview of changes and their impact

Implements User Story 4: Edit Purchase (Feature 042).
"""

import customtkinter as ctk
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, Callable, Dict, Any, List

from src.services.supplier_service import get_all_suppliers
from src.services.purchase_service import (
    get_purchase,
    can_edit_purchase,
    update_purchase,
    get_remaining_inventory,
)
from src.services.exceptions import PurchaseNotFound


class EditPurchaseDialog(ctk.CTkToplevel):
    """Modal dialog for editing an existing purchase.

    Provides form fields for editable purchase details with validation,
    read-only product display, and live preview of changes.
    """

    def __init__(
        self,
        parent,
        purchase_id: int,
        on_save: Optional[Callable] = None,
    ):
        """Initialize EditPurchaseDialog.

        Args:
            parent: Parent window
            purchase_id: ID of purchase to edit
            on_save: Callback function when purchase is saved successfully
        """
        super().__init__(parent)
        self.purchase_id = purchase_id
        self.on_save = on_save

        self.title("Edit Purchase")
        self.geometry("500x650")
        self.resizable(False, False)

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Data storage
        self.purchase: Optional[Dict[str, Any]] = None
        self.suppliers: List[Dict[str, Any]] = []
        self.supplier_map: Dict[str, Dict[str, Any]] = {}  # name -> supplier dict
        self.consumed_qty: Decimal = Decimal("0")
        self.remaining_qty: Decimal = Decimal("0")

        # Load data
        if not self._load_purchase():
            return  # Dialog will be destroyed if purchase not found
        self._load_suppliers()
        self._calculate_consumed_quantity()

        # Create UI
        self._create_widgets()
        self._layout_widgets()
        self._pre_fill_fields()
        self._bind_events()

        # Center on parent
        self.update_idletasks()
        self._center_on_parent(parent)

        # Focus on date entry (first editable field)
        self.date_entry.focus_set()

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

    def _load_purchase(self) -> bool:
        """Load purchase data from service.

        Returns:
            True if purchase loaded successfully, False otherwise.
        """
        try:
            purchase = get_purchase(self.purchase_id)
            # Convert to dict for easier access
            self.purchase = {
                "id": purchase.id,
                "product_id": purchase.product_id,
                "product_name": purchase.product.product_name,
                "product_brand": purchase.product.brand,
                "product_display_name": purchase.product.display_name,
                "package_unit": purchase.product.package_unit,
                "package_unit_quantity": Decimal(str(purchase.product.package_unit_quantity)),
                "purchase_date": purchase.purchase_date,
                "quantity_purchased": Decimal(str(purchase.quantity_purchased)),
                "unit_price": Decimal(str(purchase.unit_price)) if purchase.unit_price else Decimal("0"),
                "total_cost": Decimal(str(purchase.total_cost)) if purchase.total_cost else Decimal("0"),
                "supplier_id": purchase.supplier_id,
                "supplier_name": purchase.supplier.name if purchase.supplier else "",
                "notes": purchase.notes or "",
            }
            return True
        except PurchaseNotFound:
            from tkinter import messagebox
            messagebox.showerror(
                "Error",
                "Purchase not found. It may have been deleted.",
                parent=self.master
            )
            self.destroy()
            return False
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror(
                "Error",
                f"Failed to load purchase: {str(e)}",
                parent=self.master
            )
            self.destroy()
            return False

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

    def _calculate_consumed_quantity(self) -> None:
        """Calculate consumed and remaining quantities for this purchase."""
        try:
            self.remaining_qty = get_remaining_inventory(self.purchase_id)
            # Consumed = total purchased units - remaining
            total_units = (
                self.purchase["quantity_purchased"]
                * self.purchase["package_unit_quantity"]
            )
            self.consumed_qty = total_units - self.remaining_qty
        except Exception:
            self.consumed_qty = Decimal("0")
            self.remaining_qty = Decimal("0")

    def _create_widgets(self) -> None:
        """Create all dialog widgets."""
        # Title
        self.title_label = ctk.CTkLabel(
            self,
            text="Edit Purchase",
            font=ctk.CTkFont(size=18, weight="bold")
        )

        # Form frame
        self.form_frame = ctk.CTkFrame(self)

        # Product display (read-only) - T029
        self.product_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.product_title_label = ctk.CTkLabel(
            self.product_frame,
            text="Product",
            anchor="w"
        )
        self.product_name_label = ctk.CTkLabel(
            self.product_frame,
            text="",
            font=ctk.CTkFont(weight="bold"),
            anchor="w"
        )
        self.product_readonly_hint = ctk.CTkLabel(
            self.product_frame,
            text="(cannot be changed)",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )

        # Date entry
        self.date_label = ctk.CTkLabel(
            self.form_frame,
            text="Purchase Date *",
            anchor="w"
        )
        self.date_var = ctk.StringVar()
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

        # Quantity entry with consumed info - T030
        self.qty_label = ctk.CTkLabel(
            self.form_frame,
            text="Quantity *",
            anchor="w"
        )
        self.qty_var = ctk.StringVar()
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
        self.consumed_info_label = ctk.CTkLabel(
            self.form_frame,
            text="",
            font=ctk.CTkFont(size=10),
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

        # Preview frame - T031
        self.preview_frame = ctk.CTkFrame(self)
        self.preview_title = ctk.CTkLabel(
            self.preview_frame,
            text="Changes Preview",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.preview_label = ctk.CTkLabel(
            self.preview_frame,
            text="No changes detected",
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
            text="Save Changes",
            command=self._on_save,
            width=120
        )

    def _layout_widgets(self) -> None:
        """Layout all widgets using grid."""
        # Title
        self.title_label.pack(pady=(15, 10))

        # Form frame
        self.form_frame.pack(fill="x", padx=20, pady=10)

        # Product row (read-only) - T029
        self.product_frame.grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 10))
        self.product_title_label.pack(anchor="w")
        self.product_name_label.pack(anchor="w", pady=(2, 0))
        self.product_readonly_hint.pack(anchor="w")

        # Date row
        self.date_label.grid(row=2, column=0, sticky="w", padx=10, pady=(10, 2))
        self.date_entry.grid(row=3, column=0, sticky="w", padx=10, pady=(0, 2))
        self.date_hint.grid(row=3, column=1, sticky="w", padx=5, pady=(0, 2))

        # Quantity row
        self.qty_label.grid(row=4, column=0, sticky="w", padx=10, pady=(10, 2))
        self.qty_entry.grid(row=5, column=0, sticky="w", padx=10, pady=(0, 2))
        self.qty_unit_label.grid(row=5, column=1, sticky="w", padx=5, pady=(0, 2))
        self.consumed_info_label.grid(row=6, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 10))

        # Price row
        self.price_label.grid(row=7, column=0, sticky="w", padx=10, pady=(10, 2))
        self.price_entry.grid(row=8, column=0, sticky="w", padx=10, pady=(0, 2))
        self.price_hint.grid(row=8, column=1, columnspan=2, sticky="w", padx=5, pady=(0, 2))

        # Supplier row
        self.supplier_label.grid(row=9, column=0, sticky="w", padx=10, pady=(10, 2))
        self.supplier_combo.grid(row=10, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 10))

        # Notes row
        self.notes_label.grid(row=11, column=0, sticky="w", padx=10, pady=(10, 2))
        self.notes_text.grid(row=12, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 10))

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

    def _pre_fill_fields(self) -> None:
        """Pre-fill form fields with existing purchase data (T028)."""
        if not self.purchase:
            return

        # Product (read-only display)
        self.product_name_label.configure(text=self.purchase["product_display_name"])

        # Update unit label
        package_unit = self.purchase.get("package_unit", "package")
        self.qty_unit_label.configure(text=f"{package_unit}(s)")

        # Date
        if self.purchase["purchase_date"]:
            self.date_var.set(self.purchase["purchase_date"].strftime("%Y-%m-%d"))

        # Quantity
        self.qty_var.set(str(self.purchase["quantity_purchased"]))

        # Show consumed info
        package_unit_qty = self.purchase["package_unit_quantity"]
        consumed_packages = self.consumed_qty / package_unit_qty if package_unit_qty else Decimal("0")
        self.consumed_info_label.configure(
            text=f"Consumed: {self.consumed_qty:.1f} {package_unit}(s) "
                 f"(min: {consumed_packages:.1f} packages)"
        )

        # Unit price
        if self.purchase["unit_price"]:
            self.price_var.set(f"{self.purchase['unit_price']:.2f}")

        # Show FIFO recalc warning
        self.price_hint.configure(text="Price change will trigger FIFO cost recalculation")

        # Supplier
        if self.purchase["supplier_name"]:
            self.supplier_var.set(self.purchase["supplier_name"])

        # Notes
        if self.purchase["notes"]:
            self.notes_text.insert("1.0", self.purchase["notes"])

    def _bind_events(self) -> None:
        """Bind event handlers."""
        # Update preview on field changes
        self.date_var.trace_add("write", lambda *args: self._update_preview())
        self.qty_var.trace_add("write", lambda *args: self._update_preview())
        self.price_var.trace_add("write", lambda *args: self._update_preview())
        self.supplier_var.trace_add("write", lambda *args: self._update_preview())

        # Escape to close
        self.bind("<Escape>", lambda e: self.destroy())

        # Enter to save
        self.bind("<Return>", lambda e: self._on_save())

    def _update_preview(self) -> None:
        """Update preview with detected changes (T031)."""
        if not self.purchase:
            return

        changes = []

        try:
            # Date change?
            new_date_str = self.date_var.get().strip()
            if new_date_str:
                try:
                    new_date = datetime.strptime(new_date_str, "%Y-%m-%d").date()
                    old_date = self.purchase["purchase_date"]
                    if new_date != old_date:
                        changes.append(f"Date: {old_date} -> {new_date}")
                except ValueError:
                    pass

            # Quantity change?
            qty_str = self.qty_var.get().strip()
            if qty_str:
                try:
                    new_qty = Decimal(qty_str)
                    old_qty = self.purchase["quantity_purchased"]
                    if new_qty != old_qty:
                        changes.append(f"Quantity: {old_qty} -> {new_qty}")
                        # Calculate inventory impact
                        package_unit_qty = self.purchase["package_unit_quantity"]
                        diff = (new_qty - old_qty) * package_unit_qty
                        package_unit = self.purchase.get("package_unit", "unit")
                        if diff > 0:
                            changes.append(f"  +{diff:.1f} {package_unit}(s) to inventory")
                        else:
                            changes.append(f"  {diff:.1f} {package_unit}(s) from inventory")
                except (ValueError, InvalidOperation):
                    pass

            # Price change?
            price_str = self.price_var.get().strip()
            if price_str:
                try:
                    new_price = Decimal(price_str)
                    old_price = self.purchase["unit_price"]
                    if new_price != old_price:
                        changes.append(f"Unit price: ${old_price:.2f} -> ${new_price:.2f}")
                        changes.append("  FIFO costs will be recalculated")
                except (ValueError, InvalidOperation):
                    pass

            # Supplier change?
            new_supplier = self.supplier_var.get()
            old_supplier = self.purchase["supplier_name"]
            if new_supplier and new_supplier != old_supplier:
                changes.append(f"Supplier: {old_supplier} -> {new_supplier}")

            # Notes change? (check on save, not preview)

            if changes:
                self.preview_label.configure(
                    text="\n".join(changes),
                    text_color="blue"
                )
            else:
                self.preview_label.configure(
                    text="No changes detected",
                    text_color="gray"
                )

        except Exception:
            self.preview_label.configure(
                text="Enter valid values to see preview",
                text_color="orange"
            )

    def _validate(self) -> tuple:
        """Validate all form fields.

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        # Date valid and not future?
        date_str = self.date_var.get().strip()
        try:
            purchase_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if purchase_date > date.today():
                return False, "Purchase date cannot be in the future"
        except ValueError:
            return False, "Invalid date format (use YYYY-MM-DD)"

        # Quantity valid? (whole packages only - model uses Integer) - T030
        qty_str = self.qty_var.get().strip()
        try:
            qty = Decimal(qty_str)
            if qty <= 0:
                return False, "Quantity must be greater than 0"
            # Must be a whole number (packages come in whole units)
            if qty != qty.to_integral_value():
                return False, "Quantity must be a whole number (whole packages only)"

            # Check against consumed quantity
            package_unit_qty = self.purchase["package_unit_quantity"]
            new_total_units = qty * package_unit_qty
            if new_total_units < self.consumed_qty:
                min_packages = self.consumed_qty / package_unit_qty
                return False, (
                    f"Cannot reduce below {min_packages:.1f} packages "
                    f"({self.consumed_qty:.1f} units already consumed)"
                )

            # Also use server-side validation
            can_edit, reason = can_edit_purchase(self.purchase_id, qty)
            if not can_edit:
                return False, reason

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
        """Handle save button click (T032)."""
        self._clear_error()

        # Validate
        is_valid, error = self._validate()
        if not is_valid:
            self._show_error(error)
            return

        # Build updates dict - only include changed fields
        updates: Dict[str, Any] = {}

        # Date
        new_date = datetime.strptime(self.date_var.get().strip(), "%Y-%m-%d").date()
        if new_date != self.purchase["purchase_date"]:
            updates["purchase_date"] = new_date

        # Quantity
        new_qty = Decimal(self.qty_var.get().strip())
        if new_qty != self.purchase["quantity_purchased"]:
            updates["quantity_purchased"] = new_qty

        # Price
        new_price = Decimal(self.price_var.get().strip())
        if new_price != self.purchase["unit_price"]:
            updates["unit_price"] = new_price

        # Supplier
        new_supplier_name = self.supplier_var.get()
        new_supplier = self.supplier_map.get(new_supplier_name)
        if new_supplier:
            new_supplier_id = new_supplier.get("id")
            if new_supplier_id and new_supplier_id != self.purchase["supplier_id"]:
                updates["supplier_id"] = new_supplier_id

        # Notes
        new_notes = self.notes_text.get("1.0", "end-1c").strip() or None
        old_notes = self.purchase["notes"] or None
        if new_notes != old_notes:
            updates["notes"] = new_notes

        # If no changes, just close
        if not updates:
            self.destroy()
            return

        try:
            # Apply updates via service
            update_purchase(self.purchase_id, updates)

            # Callback to refresh list
            if self.on_save:
                self.on_save()

            self.destroy()

        except Exception as e:
            self._show_error(f"Failed to save: {str(e)}")
