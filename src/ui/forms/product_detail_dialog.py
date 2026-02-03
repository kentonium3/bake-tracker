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
from src.services.exceptions import ServiceError
from src.ui.utils.error_handler import handle_error


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
        self.name_label.grid(row=0, column=0, columnspan=4, padx=15, pady=(15, 5), sticky="w")

        # Status indicator (hidden badge)
        self.status_label = ctk.CTkLabel(
            info_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self.status_label.grid(row=1, column=0, columnspan=4, padx=15, pady=(0, 15), sticky="w")

        # Details grid (tighter spacing with pady=3)
        row = 2

        # ID and Brand
        ctk.CTkLabel(info_frame, text="ID:", anchor="e").grid(
            row=row, column=0, padx=(15, 5), pady=3, sticky="e"
        )
        self.id_label = ctk.CTkLabel(info_frame, text="", anchor="w")
        self.id_label.grid(row=row, column=1, padx=5, pady=3, sticky="w")

        ctk.CTkLabel(info_frame, text="Brand:", anchor="e").grid(
            row=row, column=2, padx=(15, 5), pady=3, sticky="e"
        )
        self.brand_label = ctk.CTkLabel(info_frame, text="", anchor="w")
        self.brand_label.grid(row=row, column=3, padx=(5, 15), pady=3, sticky="w")
        row += 1

        # GTIN and Ingredient
        ctk.CTkLabel(info_frame, text="GTIN:", anchor="e").grid(
            row=row, column=0, padx=(15, 5), pady=3, sticky="e"
        )
        self.gtin_label = ctk.CTkLabel(info_frame, text="", anchor="w")
        self.gtin_label.grid(row=row, column=1, padx=5, pady=3, sticky="w")

        ctk.CTkLabel(info_frame, text="Ingredient:", anchor="e").grid(
            row=row, column=2, padx=(15, 5), pady=3, sticky="e"
        )
        self.ingredient_label = ctk.CTkLabel(info_frame, text="", anchor="w")
        self.ingredient_label.grid(row=row, column=3, padx=(5, 15), pady=3, sticky="w")
        row += 1

        # UPC and Category
        ctk.CTkLabel(info_frame, text="UPC:", anchor="e").grid(
            row=row, column=0, padx=(15, 5), pady=3, sticky="e"
        )
        self.upc_label = ctk.CTkLabel(info_frame, text="", anchor="w")
        self.upc_label.grid(row=row, column=1, padx=5, pady=3, sticky="w")

        ctk.CTkLabel(info_frame, text="Category:", anchor="e").grid(
            row=row, column=2, padx=(15, 5), pady=3, sticky="e"
        )
        self.category_label = ctk.CTkLabel(info_frame, text="", anchor="w")
        self.category_label.grid(row=row, column=3, padx=(5, 15), pady=3, sticky="w")
        row += 1

        # Package and Preferred Supplier
        ctk.CTkLabel(info_frame, text="Package:", anchor="e").grid(
            row=row, column=0, padx=(15, 5), pady=3, sticky="e"
        )
        self.package_label = ctk.CTkLabel(info_frame, text="", anchor="w")
        self.package_label.grid(row=row, column=1, padx=5, pady=3, sticky="w")

        ctk.CTkLabel(info_frame, text="Preferred Supplier:", anchor="e").grid(
            row=row, column=2, padx=(15, 5), pady=3, sticky="e"
        )
        self.supplier_label = ctk.CTkLabel(info_frame, text="", anchor="w")
        self.supplier_label.grid(row=row, column=3, padx=(5, 15), pady=3, sticky="w")
        row += 1

        # Last Price (single field, last row)
        ctk.CTkLabel(info_frame, text="Last Price:", anchor="e").grid(
            row=row, column=0, padx=(15, 5), pady=(3, 10), sticky="e"
        )
        self.price_label = ctk.CTkLabel(info_frame, text="", anchor="w")
        self.price_label.grid(row=row, column=1, padx=5, pady=(3, 10), sticky="w")

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
            self.product = product_catalog_service.get_product_with_last_price(self.product_id)

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

        except ServiceError as e:
            handle_error(e, parent=self, operation="Load product")
            self.destroy()
        except Exception as e:
            handle_error(e, parent=self, operation="Load product")
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

        # ID
        product_id = self.product.get("id", "")
        self.id_label.configure(text=str(product_id) if product_id else "N/A")

        # Brand
        brand = self.product.get("brand", "")
        self.brand_label.configure(text=brand if brand else "N/A")

        # GTIN
        gtin = self.product.get("gtin", "")
        self.gtin_label.configure(text=gtin if gtin else "(none)")

        # UPC
        upc = self.product.get("upc_code", "")
        self.upc_label.configure(text=upc if upc else "(none)")

        # Ingredient
        ingredient = self.product.get("ingredient_name", "")
        self.ingredient_label.configure(text=ingredient if ingredient else "N/A")

        # Category
        category = self.product.get("category", "")
        self.category_label.configure(text=category if category else "Uncategorized")

        # Package info (qty unit type, e.g. "25 lb bag")
        unit = self.product.get("package_unit", "")
        qty = self.product.get("package_unit_quantity") or self.product.get("package_quantity")
        pkg_type = self.product.get("package_type", "")

        parts = []
        if qty:
            parts.append(str(qty))
        if unit:
            parts.append(unit)
        if pkg_type:
            parts.append(pkg_type)
        package = " ".join(parts) if parts else "N/A"
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

        except ServiceError as e:
            handle_error(e, parent=self, operation="Load purchase history", level="warning")
        except Exception as e:
            handle_error(e, parent=self, operation="Load purchase history", level="warning")

    def _on_edit(self):
        """Open AddProductDialog in edit mode."""
        from src.ui.forms.add_product_dialog import AddProductDialog

        # Release grab before opening child dialog to avoid modal conflict
        self.grab_release()

        dialog = AddProductDialog(self, product_id=self.product_id)

        # Only wait if dialog was successfully created (not destroyed during init)
        if dialog.winfo_exists():
            self.wait_window(dialog)

        # Re-acquire grab after child dialog closes (if this window still exists)
        if self.winfo_exists():
            self.grab_set()

            if hasattr(dialog, "result") and dialog.result:
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

        except ServiceError as e:
            handle_error(e, parent=self, operation="Update product visibility")
        except Exception as e:
            handle_error(e, parent=self, operation="Update product visibility")

    def _on_delete(self):
        """Delete product with force delete option for dependencies."""
        if not self.product:
            return

        product_name = self.product.get("product_name") or self.product.get(
            "display_name", "Unknown"
        )

        # Try normal delete first
        try:
            product_catalog_service.delete_product(self.product_id)
            messagebox.showinfo(
                "Success",
                f"Product '{product_name}' deleted successfully.",
                parent=self,
            )
            self.result = True  # Signal parent to refresh
            self.destroy()
            return

        except ValueError:
            # Has dependencies - analyze them
            pass
        except ServiceError as e:
            handle_error(e, parent=self, operation="Delete product")
            return
        except Exception as e:
            handle_error(e, parent=self, operation="Delete product")
            return

        # Analyze dependencies
        try:
            deps = product_catalog_service.analyze_product_dependencies(self.product_id)

            # Check if used in recipes - BLOCKED
            if deps.is_used_in_recipes:
                self._show_recipe_block_dialog(deps)
                return

            # Not in recipes - show force delete confirmation
            self._show_force_delete_confirmation(deps)

        except ServiceError as e:
            handle_error(e, parent=self, operation="Analyze dependencies")
        except Exception as e:
            handle_error(e, parent=self, operation="Analyze dependencies")

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
            warning_lines.append(
                "  WARNING: Has purchases with price data - cost history will be lost"
            )
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
            self.result = True  # Signal parent to refresh
            self.destroy()

        except ValueError as e:
            # Should not happen (already checked recipes) but handle anyway
            messagebox.showerror("Cannot Delete", str(e), parent=self)
        except ServiceError as e:
            handle_error(e, parent=self, operation="Force delete product")
        except Exception as e:
            handle_error(e, parent=self, operation="Force delete product")

    def _on_close(self):
        """Close the dialog."""
        self.destroy()
