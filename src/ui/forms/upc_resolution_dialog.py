"""
UPC Resolution Dialog for resolving unknown UPCs during purchase import.

Feature 040: Part of BT Mobile import workflow.

Provides a modal dialog for:
- Viewing unmatched UPC scan details
- Mapping UPC to existing product
- Creating new product with scanned UPC
- Skipping unmatched UPCs
"""

import logging
from typing import List, Dict, Callable, Optional, Any
from decimal import Decimal
from datetime import datetime, date

import customtkinter as ctk
from tkinter import messagebox

from src.services.database import session_scope
from src.services import product_catalog_service
from src.models import Product, Supplier
from src.models.purchase import Purchase
from src.models.inventory_item import InventoryItem

logger = logging.getLogger(__name__)


class UPCResolutionDialog(ctk.CTkToplevel):
    """
    Dialog for resolving unknown UPCs from BT Mobile purchase imports.

    Allows users to:
    - Map unknown UPC to an existing product (updates Product.upc_code)
    - Create a new product with the scanned UPC
    - Skip the UPC without processing

    Processes one UPC at a time with progress tracking.
    """

    def __init__(
        self,
        parent,
        unmatched_purchases: List[Dict],
        default_supplier: Optional[str] = None,
        on_complete: Optional[Callable[[int, int, int], None]] = None,
    ):
        """
        Initialize the dialog.

        Args:
            parent: Parent widget
            unmatched_purchases: List of purchase data dicts with unmatched UPCs
            default_supplier: Default supplier name for created purchases
            on_complete: Callback(mapped_count, created_count, skipped_count)
        """
        super().__init__(parent)

        self._purchases = unmatched_purchases
        self._default_supplier = default_supplier
        self._current_index = 0
        self._mapped_count = 0
        self._created_count = 0
        self._skipped_count = 0
        self._on_complete = on_complete

        # Product search data
        self._products: List[Dict[str, Any]] = []

        # Window configuration
        self.title("Resolve Unknown UPCs")
        self.geometry("550x480")
        self.resizable(False, False)

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        # Setup UI
        self._setup_ui()

        # Load product list for search
        self._load_products()

        # Show first purchase
        self._show_current_purchase()

    def _setup_ui(self):
        """Set up the dialog UI."""
        # Header
        self._header_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self._header_label.pack(pady=(15, 10))

        # Progress indicator
        self._progress_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self._progress_label.pack(pady=(0, 10))

        # UPC info frame
        self._info_frame = ctk.CTkFrame(self)
        self._info_frame.pack(fill="x", padx=20, pady=10)

        # UPC label
        ctk.CTkLabel(
            self._info_frame,
            text="UPC Code:",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=10, pady=5)

        self._upc_value = ctk.CTkLabel(
            self._info_frame,
            text="",
            font=ctk.CTkFont(family="Courier", size=16),
        )
        self._upc_value.grid(row=0, column=1, sticky="w", padx=10, pady=5)

        # Price label
        ctk.CTkLabel(
            self._info_frame,
            text="Unit Price:",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=1, column=0, sticky="w", padx=10, pady=5)

        self._price_value = ctk.CTkLabel(self._info_frame, text="")
        self._price_value.grid(row=1, column=1, sticky="w", padx=10, pady=5)

        # Quantity label
        ctk.CTkLabel(
            self._info_frame,
            text="Quantity:",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=2, column=0, sticky="w", padx=10, pady=5)

        self._qty_value = ctk.CTkLabel(self._info_frame, text="")
        self._qty_value.grid(row=2, column=1, sticky="w", padx=10, pady=5)

        # Scanned time label
        ctk.CTkLabel(
            self._info_frame,
            text="Scanned At:",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=3, column=0, sticky="w", padx=10, pady=5)

        self._time_value = ctk.CTkLabel(self._info_frame, text="")
        self._time_value.grid(row=3, column=1, sticky="w", padx=10, pady=5)

        self._info_frame.grid_columnconfigure(1, weight=1)

        # Product search section (for Map to Existing)
        self._search_frame = ctk.CTkFrame(self)
        self._search_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            self._search_frame,
            text="Map to Existing Product:",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Search entry
        search_row = ctk.CTkFrame(self._search_frame, fg_color="transparent")
        search_row.pack(fill="x", padx=10, pady=5)

        self._search_entry = ctk.CTkEntry(
            search_row,
            placeholder_text="Type to search products...",
            width=300,
        )
        self._search_entry.pack(side="left", padx=(0, 10))
        self._search_entry.bind("<KeyRelease>", self._on_search_changed)

        # Product dropdown
        self._product_var = ctk.StringVar(value="Select a product...")
        self._product_menu = ctk.CTkOptionMenu(
            self._search_frame,
            variable=self._product_var,
            values=["(No products found)"],
            width=400,
            command=self._on_product_selected,
        )
        self._product_menu.pack(padx=10, pady=5)

        # Map button
        self._map_btn = ctk.CTkButton(
            self._search_frame,
            text="Map to Selected Product",
            command=self._on_map_existing,
            state="disabled",
        )
        self._map_btn.pack(pady=10)

        # Action buttons frame
        self._button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._button_frame.pack(fill="x", padx=20, pady=15)

        # Create New button
        self._create_btn = ctk.CTkButton(
            self._button_frame,
            text="Create New Product...",
            command=self._on_create_new,
            fg_color="#2e7d32",
            hover_color="#1b5e20",
        )
        self._create_btn.pack(side="left", padx=5)

        # Skip button
        self._skip_btn = ctk.CTkButton(
            self._button_frame,
            text="Skip This UPC",
            command=self._on_skip,
            fg_color="#757575",
            hover_color="#616161",
        )
        self._skip_btn.pack(side="left", padx=5)

        # Close button
        self._close_btn = ctk.CTkButton(
            self._button_frame,
            text="Close (Skip All Remaining)",
            command=self._on_close,
            fg_color="#d32f2f",
            hover_color="#b71c1c",
        )
        self._close_btn.pack(side="right", padx=5)

        # Status label
        self._status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        self._status_label.pack(pady=(5, 10))

    def _load_products(self):
        """Load products for search/selection."""
        try:
            self._products = product_catalog_service.get_products(include_hidden=False)
            self._update_product_menu()
        except Exception as e:
            logger.error(f"Failed to load products: {e}")
            self._products = []

    def _update_product_menu(self, search_term: str = ""):
        """Update product dropdown with filtered results."""
        if search_term:
            search_lower = search_term.lower()
            filtered = [
                p for p in self._products
                if search_lower in p.get("display_name", "").lower()
                or search_lower in (p.get("brand") or "").lower()
                or search_lower in (p.get("ingredient_name") or "").lower()
            ]
        else:
            filtered = self._products[:50]  # Limit initial display

        if filtered:
            # Format: "Product Name (Brand) - Ingredient"
            values = []
            self._product_id_map = {}
            for p in filtered[:30]:  # Limit dropdown items
                label = p.get("display_name", "Unknown")
                if p.get("brand"):
                    label = f"{p['brand']} {label}"
                if p.get("ingredient_name"):
                    label += f" - {p['ingredient_name']}"
                values.append(label)
                self._product_id_map[label] = p.get("id")

            self._product_menu.configure(values=values)
            self._product_var.set(values[0] if len(values) == 1 else "Select a product...")
        else:
            self._product_menu.configure(values=["(No products found)"])
            self._product_var.set("(No products found)")
            self._product_id_map = {}

    def _on_search_changed(self, event):
        """Handle search entry change."""
        search_term = self._search_entry.get().strip()
        self._update_product_menu(search_term)

    def _on_product_selected(self, choice):
        """Handle product selection from dropdown."""
        if choice and choice != "Select a product..." and choice != "(No products found)":
            self._map_btn.configure(state="normal")
        else:
            self._map_btn.configure(state="disabled")

    @property
    def _current_purchase(self) -> Dict:
        """Get current purchase being processed."""
        if 0 <= self._current_index < len(self._purchases):
            return self._purchases[self._current_index]
        return {}

    def _show_current_purchase(self):
        """Display current purchase details."""
        if self._current_index >= len(self._purchases):
            self._complete()
            return

        purchase = self._current_purchase
        total = len(self._purchases)
        current = self._current_index + 1

        # Update header
        self._header_label.configure(
            text=f"Resolve Unknown UPCs ({total - self._current_index} remaining)"
        )
        self._progress_label.configure(text=f"Processing {current} of {total}")

        # Update UPC info
        self._upc_value.configure(text=purchase.get("upc", "Unknown"))

        price = purchase.get("unit_price", 0)
        self._price_value.configure(text=f"${price:.2f}" if price else "Not specified")

        qty = purchase.get("quantity_purchased", 1)
        self._qty_value.configure(text=str(qty))

        scanned_at = purchase.get("scanned_at", "")
        if scanned_at:
            try:
                if scanned_at.endswith("Z"):
                    scanned_at = scanned_at[:-1] + "+00:00"
                dt = datetime.fromisoformat(scanned_at)
                self._time_value.configure(text=dt.strftime("%Y-%m-%d %H:%M"))
            except Exception:
                self._time_value.configure(text=scanned_at)
        else:
            self._time_value.configure(text="Not specified")

        # Reset search and selection
        self._search_entry.delete(0, "end")
        self._update_product_menu()
        self._map_btn.configure(state="disabled")

        # Update status
        self._update_status()

    def _update_status(self):
        """Update status label with counts."""
        self._status_label.configure(
            text=f"Mapped: {self._mapped_count}  |  Created: {self._created_count}  |  Skipped: {self._skipped_count}"
        )

    def _on_map_existing(self):
        """Handle mapping UPC to existing product."""
        selected = self._product_var.get()
        if selected in ("Select a product...", "(No products found)"):
            messagebox.showwarning("Selection Required", "Please select a product first.")
            return

        product_id = self._product_id_map.get(selected)
        if not product_id:
            messagebox.showerror("Error", "Could not find selected product.")
            return

        try:
            with session_scope() as session:
                product = session.query(Product).get(product_id)
                if not product:
                    messagebox.showerror("Error", "Product not found in database.")
                    return

                # Update product UPC for future matching
                product.upc_code = self._current_purchase.get("upc")

                # Create purchase and inventory item
                self._create_purchase_for_product(product.id, session)

                session.commit()

            self._mapped_count += 1
            logger.info(
                f"Mapped UPC {self._current_purchase.get('upc')} to product {product_id}"
            )
            self._advance_to_next()

        except Exception as e:
            logger.error(f"Failed to map UPC: {e}")
            messagebox.showerror("Error", f"Failed to map UPC: {str(e)}")

    def _on_create_new(self):
        """Handle creating new product with UPC."""
        # Import AddProductDialog here to avoid circular imports
        from src.ui.forms.add_product_dialog import AddProductDialog

        try:
            dialog = AddProductDialog(self, product_id=None)
            dialog.wait_window()

            if dialog.result:
                # Get the newly created product ID
                # AddProductDialog stores the created product in self.product_id after save
                new_product_id = getattr(dialog, "created_product_id", None)

                if new_product_id:
                    # Update the UPC and create purchase
                    with session_scope() as session:
                        product = session.query(Product).get(new_product_id)
                        if product:
                            product.upc_code = self._current_purchase.get("upc")
                            self._create_purchase_for_product(product.id, session)
                            session.commit()

                    self._created_count += 1
                    logger.info(
                        f"Created product {new_product_id} with UPC {self._current_purchase.get('upc')}"
                    )
                    self._advance_to_next()
                else:
                    # Product created but we don't have the ID
                    # This can happen if AddProductDialog doesn't expose created_product_id
                    messagebox.showinfo(
                        "Product Created",
                        "Product was created. Please map the UPC to it using the dropdown above."
                    )
                    self._load_products()  # Refresh product list
            else:
                # Dialog cancelled
                pass

        except Exception as e:
            logger.error(f"Failed to create product: {e}")
            messagebox.showerror("Error", f"Failed to create product: {str(e)}")

    def _on_skip(self):
        """Handle skipping current UPC."""
        upc = self._current_purchase.get("upc", "Unknown")
        price = self._current_purchase.get("unit_price", "N/A")

        logger.info(f"Skipped UPC resolution: {upc} (price: {price})")

        self._skipped_count += 1
        self._advance_to_next()

    def _on_close(self):
        """Handle closing dialog (skips all remaining)."""
        remaining = len(self._purchases) - self._current_index
        if remaining > 0:
            if not messagebox.askyesno(
                "Confirm Close",
                f"Skip the remaining {remaining} unmatched UPCs and close?"
            ):
                return

            # Log all remaining as skipped
            for i in range(self._current_index, len(self._purchases)):
                purchase = self._purchases[i]
                logger.info(
                    f"Skipped UPC resolution (batch): {purchase.get('upc')} "
                    f"(price: {purchase.get('unit_price')})"
                )
                self._skipped_count += 1

        self._complete()

    def _create_purchase_for_product(self, product_id: int, session):
        """Create Purchase and InventoryItem for the current purchase."""
        purchase_data = self._current_purchase

        # Resolve supplier
        supplier_name = purchase_data.get("supplier") or self._default_supplier
        supplier = None
        if supplier_name:
            supplier = session.query(Supplier).filter_by(name=supplier_name).first()
            if not supplier:
                supplier = Supplier(name=supplier_name)
                session.add(supplier)
                session.flush()

        # Parse date
        scanned_at = purchase_data.get("scanned_at")
        if scanned_at:
            try:
                if scanned_at.endswith("Z"):
                    scanned_at = scanned_at[:-1] + "+00:00"
                purchase_date = datetime.fromisoformat(scanned_at).date()
            except ValueError:
                purchase_date = date.today()
        else:
            purchase_date = date.today()

        # Parse price and quantity
        unit_price = Decimal(str(purchase_data.get("unit_price", 0)))
        quantity_purchased = int(purchase_data.get("quantity_purchased", 1))

        # Create Purchase
        purchase = Purchase(
            product_id=product_id,
            supplier_id=supplier.id if supplier else None,
            purchase_date=purchase_date,
            unit_price=unit_price,
            quantity_purchased=quantity_purchased,
            notes=purchase_data.get("notes"),
        )
        session.add(purchase)
        session.flush()

        # Create InventoryItem
        inventory_item = InventoryItem(
            product_id=product_id,
            purchase_id=purchase.id,
            quantity=float(quantity_purchased),
            unit_cost=float(unit_price),
            purchase_date=purchase_date,
        )
        session.add(inventory_item)

    def _advance_to_next(self):
        """Move to next unmatched purchase or complete."""
        self._current_index += 1
        if self._current_index >= len(self._purchases):
            self._complete()
        else:
            self._show_current_purchase()

    def _complete(self):
        """Finish resolution process."""
        logger.info(
            f"UPC resolution complete: mapped={self._mapped_count}, "
            f"created={self._created_count}, skipped={self._skipped_count}"
        )

        if self._on_complete:
            self._on_complete(
                self._mapped_count,
                self._created_count,
                self._skipped_count,
            )

        # Show summary
        messagebox.showinfo(
            "UPC Resolution Complete",
            f"Resolution complete:\n\n"
            f"  Mapped to existing: {self._mapped_count}\n"
            f"  New products created: {self._created_count}\n"
            f"  Skipped: {self._skipped_count}"
        )

        self.destroy()
