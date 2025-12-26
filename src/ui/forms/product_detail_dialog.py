"""
Product Detail Dialog for viewing product information and purchase history.

Provides a modal dialog for:
- Viewing product attributes
- Viewing purchase history sorted by date
- Editing product via AddProductDialog
- Hiding/unhiding products
- Deleting products (with dependency check)
"""

import customtkinter as ctk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any, List

from src.services import product_catalog_service


class ProductDetailDialog(ctk.CTkToplevel):
    """
    Dialog for viewing product details and purchase history.

    Features:
    - Product information display (name, brand, ingredient, category, etc.)
    - Edit button to open AddProductDialog
    - Hide/Unhide button to toggle visibility
    - Delete button with dependency checking
    - Purchase history grid sorted by date (newest first)
    - Empty state message when no purchases exist
    """

    def __init__(
        self,
        parent,
        product_id: int,
        **kwargs,
    ):
        """
        Initialize the dialog.

        Args:
            parent: Parent widget
            product_id: ID of product to display
        """
        super().__init__(parent, **kwargs)

        self.product_id = product_id
        self.product: Optional[Dict[str, Any]] = None
        self.result: Optional[bool] = None

        # Window configuration
        self.title("Product Details")
        self.geometry("700x600")
        self.resizable(True, True)
        self.minsize(600, 500)

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        # Configure grid for main layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)  # History section expands

        # Setup UI
        self._setup_info_section()
        self._setup_buttons()
        self._setup_history_section()

        # Load data
        self._load_product()

    def _setup_info_section(self):
        """Create product information display section."""
        info_frame = ctk.CTkFrame(self)
        info_frame.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")
        info_frame.grid_columnconfigure(1, weight=1)
        info_frame.grid_columnconfigure(3, weight=1)

        # Product name (large header)
        self.name_label = ctk.CTkLabel(
            info_frame,
            text="Loading...",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.name_label.grid(
            row=0, column=0, columnspan=4, padx=15, pady=(15, 5), sticky="w"
        )

        # Status indicator (hidden badge)
        self.status_label = ctk.CTkLabel(
            info_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self.status_label.grid(row=1, column=0, columnspan=4, padx=15, pady=(0, 15), sticky="w")

        # Details grid
        row = 2

        # Brand
        ctk.CTkLabel(info_frame, text="Brand:", anchor="e").grid(
            row=row, column=0, padx=(15, 5), pady=5, sticky="e"
        )
        self.brand_label = ctk.CTkLabel(info_frame, text="", anchor="w")
        self.brand_label.grid(row=row, column=1, padx=5, pady=5, sticky="w")

        # Ingredient
        ctk.CTkLabel(info_frame, text="Ingredient:", anchor="e").grid(
            row=row, column=2, padx=(15, 5), pady=5, sticky="e"
        )
        self.ingredient_label = ctk.CTkLabel(info_frame, text="", anchor="w")
        self.ingredient_label.grid(row=row, column=3, padx=(5, 15), pady=5, sticky="w")
        row += 1

        # Category
        ctk.CTkLabel(info_frame, text="Category:", anchor="e").grid(
            row=row, column=0, padx=(15, 5), pady=5, sticky="e"
        )
        self.category_label = ctk.CTkLabel(info_frame, text="", anchor="w")
        self.category_label.grid(row=row, column=1, padx=5, pady=5, sticky="w")

        # Package
        ctk.CTkLabel(info_frame, text="Package:", anchor="e").grid(
            row=row, column=2, padx=(15, 5), pady=5, sticky="e"
        )
        self.package_label = ctk.CTkLabel(info_frame, text="", anchor="w")
        self.package_label.grid(row=row, column=3, padx=(5, 15), pady=5, sticky="w")
        row += 1

        # Preferred Supplier
        ctk.CTkLabel(info_frame, text="Preferred Supplier:", anchor="e").grid(
            row=row, column=0, padx=(15, 5), pady=5, sticky="e"
        )
        self.supplier_label = ctk.CTkLabel(info_frame, text="", anchor="w")
        self.supplier_label.grid(row=row, column=1, padx=5, pady=5, sticky="w")

        # Last Price
        ctk.CTkLabel(info_frame, text="Last Price:", anchor="e").grid(
            row=row, column=2, padx=(15, 5), pady=5, sticky="e"
        )
        self.price_label = ctk.CTkLabel(info_frame, text="", anchor="w")
        self.price_label.grid(row=row, column=3, padx=(5, 15), pady=(5, 15), sticky="w")

    def _setup_buttons(self):
        """Create action buttons."""
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=1, column=0, padx=15, pady=5, sticky="ew")

        # Edit button
        self.edit_btn = ctk.CTkButton(
            button_frame,
            text="Edit",
            command=self._on_edit,
            width=100,
        )
        self.edit_btn.pack(side="left", padx=5, pady=5)

        # Hide/Unhide button
        self.hide_btn = ctk.CTkButton(
            button_frame,
            text="Hide",
            command=self._on_toggle_hidden,
            width=100,
        )
        self.hide_btn.pack(side="left", padx=5, pady=5)

        # Delete button
        self.delete_btn = ctk.CTkButton(
            button_frame,
            text="Delete",
            command=self._on_delete,
            width=100,
            fg_color="darkred",
            hover_color="red",
        )
        self.delete_btn.pack(side="left", padx=5, pady=5)

        # Close button
        close_btn = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self._on_close,
            width=100,
        )
        close_btn.pack(side="right", padx=5, pady=5)

    def _setup_history_section(self):
        """Create purchase history section."""
        # Section header
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=2, column=0, padx=15, pady=(10, 5), sticky="ew")

        ctk.CTkLabel(
            header_frame,
            text="Purchase History",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(side="left", padx=10, pady=5)

        self.history_count_label = ctk.CTkLabel(
            header_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self.history_count_label.pack(side="left", padx=5, pady=5)

        # History container
        history_container = ctk.CTkFrame(self)
        history_container.grid(row=3, column=0, padx=15, pady=(0, 15), sticky="nsew")
        history_container.grid_columnconfigure(0, weight=1)
        history_container.grid_rowconfigure(0, weight=1)

        # Treeview for purchase history
        columns = ("date", "supplier", "location", "price", "quantity")
        self.history_tree = ttk.Treeview(
            history_container,
            columns=columns,
            show="headings",
            height=8,
        )

        self.history_tree.heading("date", text="Date", anchor="w")
        self.history_tree.heading("supplier", text="Supplier", anchor="w")
        self.history_tree.heading("location", text="Location", anchor="w")
        self.history_tree.heading("price", text="Unit Price", anchor="e")
        self.history_tree.heading("quantity", text="Qty", anchor="e")

        self.history_tree.column("date", width=100, minwidth=80)
        self.history_tree.column("supplier", width=150, minwidth=100)
        self.history_tree.column("location", width=150, minwidth=100)
        self.history_tree.column("price", width=80, minwidth=60, anchor="e")
        self.history_tree.column("quantity", width=50, minwidth=40, anchor="e")

        # Scrollbars
        y_scrollbar = ttk.Scrollbar(
            history_container,
            orient="vertical",
            command=self.history_tree.yview,
        )
        self.history_tree.configure(yscrollcommand=y_scrollbar.set)

        self.history_tree.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")

        # Empty state label (shown when no history)
        self.empty_label = ctk.CTkLabel(
            history_container,
            text="No purchase history for this product.",
            font=ctk.CTkFont(size=14),
            text_color="gray",
        )

    def _load_product(self):
        """Load product data and purchase history."""
        try:
            self.product = product_catalog_service.get_product_with_last_price(
                self.product_id
            )

            if not self.product:
                messagebox.showerror(
                    "Error",
                    "Product not found",
                    parent=self,
                )
                self.destroy()
                return

            self._update_info_display()
            self._update_hide_button()
            self._load_history()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to load product: {str(e)}",
                parent=self,
            )
            self.destroy()

    def _update_info_display(self):
        """Update product information display."""
        if not self.product:
            return

        # Product name
        name = self.product.get("product_name") or self.product.get("display_name", "Unknown")
        self.name_label.configure(text=name)

        # Status (hidden indicator)
        if self.product.get("is_hidden"):
            self.status_label.configure(text="[HIDDEN]", text_color="orange")
        else:
            self.status_label.configure(text="")

        # Brand
        brand = self.product.get("brand", "")
        self.brand_label.configure(text=brand if brand else "N/A")

        # Ingredient
        ingredient = self.product.get("ingredient_name", "")
        self.ingredient_label.configure(text=ingredient if ingredient else "N/A")

        # Category
        category = self.product.get("category", "")
        self.category_label.configure(text=category if category else "Uncategorized")

        # Package info
        unit = self.product.get("package_unit", "")
        qty = self.product.get("package_unit_quantity") or self.product.get("package_quantity")
        if unit and qty:
            package = f"{qty} {unit}"
        elif unit:
            package = unit
        else:
            package = "N/A"
        self.package_label.configure(text=package)

        # Preferred supplier
        supplier = self.product.get("preferred_supplier_name", "")
        self.supplier_label.configure(text=supplier if supplier else "None")

        # Last price
        last_price = self.product.get("last_price")
        if last_price is not None:
            self.price_label.configure(text=f"${float(last_price):.2f}")
        else:
            self.price_label.configure(text="N/A")

    def _update_hide_button(self):
        """Update hide button text based on current state."""
        if self.product and self.product.get("is_hidden"):
            self.hide_btn.configure(text="Unhide")
        else:
            self.hide_btn.configure(text="Hide")

    def _load_history(self):
        """Load and display purchase history."""
        # Clear existing items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        try:
            # Get purchase history (already sorted by date DESC in service)
            history = product_catalog_service.get_purchase_history(self.product_id)

            if not history:
                # Show empty state
                self.history_tree.grid_remove()
                self.empty_label.grid(row=0, column=0, pady=30)
                self.history_count_label.configure(text="(0 purchases)")
            else:
                # Show history grid
                self.empty_label.grid_remove()
                self.history_tree.grid(row=0, column=0, sticky="nsew")
                self.history_count_label.configure(text=f"({len(history)} purchases)")

                for purchase in history:
                    date_str = purchase.get("purchase_date", "")
                    if hasattr(date_str, "strftime"):
                        date_str = date_str.strftime("%Y-%m-%d")

                    supplier_name = purchase.get("supplier_name", "Unknown")
                    location = purchase.get("supplier_location", "")
                    unit_price = purchase.get("unit_price")
                    quantity = purchase.get("quantity_purchased", "")

                    values = (
                        date_str,
                        supplier_name,
                        location,
                        f"${float(unit_price):.2f}" if unit_price is not None else "N/A",
                        str(quantity),
                    )
                    self.history_tree.insert("", "end", values=values)

        except Exception as e:
            messagebox.showwarning(
                "Warning",
                f"Failed to load purchase history: {str(e)}",
                parent=self,
            )

    def _on_edit(self):
        """Open AddProductDialog in edit mode."""
        from src.ui.forms.add_product_dialog import AddProductDialog

        dialog = AddProductDialog(self, product_id=self.product_id)
        self.wait_window(dialog)

        if dialog.result:
            self._load_product()  # Refresh after edit
            self.result = True  # Signal parent to refresh

    def _on_toggle_hidden(self):
        """Toggle product visibility."""
        if not self.product:
            return

        try:
            if self.product.get("is_hidden"):
                product_catalog_service.unhide_product(self.product_id)
                messagebox.showinfo(
                    "Success",
                    "Product is now visible.",
                    parent=self,
                )
            else:
                product_catalog_service.hide_product(self.product_id)
                messagebox.showinfo(
                    "Success",
                    "Product is now hidden.",
                    parent=self,
                )

            self._load_product()  # Refresh
            self.result = True  # Signal parent to refresh

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to update product visibility: {str(e)}",
                parent=self,
            )

    def _on_delete(self):
        """Delete product after confirmation and dependency check."""
        if not self.product:
            return

        product_name = self.product.get("product_name") or self.product.get(
            "display_name", "Unknown"
        )

        # Confirm deletion
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete '{product_name}'?\n\n"
            "This cannot be undone.\n\n"
            "Note: Products with purchase history or inventory cannot be deleted. "
            "Use 'Hide' instead.",
            parent=self,
        ):
            return

        try:
            product_catalog_service.delete_product(self.product_id)
            messagebox.showinfo(
                "Success",
                f"Product '{product_name}' deleted successfully.",
                parent=self,
            )
            self.result = True  # Signal parent to refresh
            self.destroy()

        except ValueError as e:
            # Product has dependencies
            if messagebox.askyesno(
                "Cannot Delete",
                f"{str(e)}\n\nWould you like to hide the product instead?",
                parent=self,
            ):
                self._on_toggle_hidden()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to delete product: {str(e)}",
                parent=self,
            )

    def _on_close(self):
        """Close the dialog."""
        self.destroy()
