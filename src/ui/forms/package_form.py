"""
Package form dialog for adding and editing packages.

Provides a form for creating and updating package records with FinishedGood selection.

Updated for Feature 006 Event Planning Restoration:
- Replaced Bundle references with FinishedGood
- Uses finished_good_service.get_all_finished_goods()

Updated for Feature 011 Packaging BOM Foundation:
- Added packaging section to allow adding packaging materials to packages
- Uses composition_service for packaging relationships

Updated for Feature 026 Deferred Packaging Decisions:
- Added toggle for Specific material vs Generic product
- Shows inventory summary for generic products
- Displays estimated cost with "Estimated" label
"""

import customtkinter as ctk
from typing import Optional, Dict, Any, List
from decimal import Decimal

from src.models.package import Package
from src.services import finished_good_service, ingredient_service, product_service
from src.services import composition_service, packaging_service
from src.utils.constants import (
    MAX_NAME_LENGTH,
    MAX_NOTES_LENGTH,
    PADDING_MEDIUM,
    PADDING_LARGE,
)
from src.ui.widgets.dialogs import show_error


class FinishedGoodRow(ctk.CTkFrame):
    """Row widget for a single FinishedGood in the package."""

    def __init__(
        self,
        parent,
        finished_goods: List,
        remove_callback,
        finished_good_id: Optional[int] = None,
        quantity: int = 1,
    ):
        """
        Initialize FinishedGood row.

        Args:
            parent: Parent widget
            finished_goods: List of available FinishedGoods
            remove_callback: Callback to remove this row
            finished_good_id: Selected FinishedGood ID (None for new row)
            quantity: FinishedGood quantity
        """
        super().__init__(parent, fg_color="transparent")

        self.finished_goods = finished_goods
        self.remove_callback = remove_callback

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=0)

        # FinishedGood dropdown
        fg_names = []
        for fg in finished_goods:
            fg_names.append(fg.display_name)

        self.fg_combo = ctk.CTkComboBox(
            self,
            width=350,
            values=fg_names if fg_names else ["No finished goods available"],
            state="readonly" if fg_names else "disabled",
        )
        if fg_names:
            # Set selected FinishedGood if provided
            if finished_good_id:
                for i, fg in enumerate(finished_goods):
                    if fg.id == finished_good_id:
                        self.fg_combo.set(fg_names[i])
                        break
            else:
                self.fg_combo.set(fg_names[0])

        self.fg_combo.grid(row=0, column=0, sticky="ew", padx=(0, PADDING_MEDIUM))

        # Quantity entry
        self.quantity_entry = ctk.CTkEntry(self, width=80, placeholder_text="Qty")
        self.quantity_entry.insert(0, str(quantity))
        self.quantity_entry.grid(row=0, column=1, padx=(0, PADDING_MEDIUM))

        # Remove button
        remove_button = ctk.CTkButton(
            self,
            text="X",
            width=30,
            command=lambda: remove_callback(self),
            fg_color="darkred",
            hover_color="red",
        )
        remove_button.grid(row=0, column=2)

    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Get FinishedGood data from this row.

        Returns:
            Dictionary with finished_good_id and quantity, or None if invalid
        """
        fg_name = self.fg_combo.get()
        if not fg_name or fg_name == "No finished goods available":
            return None

        # Extract FinishedGood name (remove cost suffix)
        if " ($" in fg_name:
            fg_name = fg_name.split(" ($")[0]

        # Find FinishedGood by name
        finished_good = None
        for fg in self.finished_goods:
            if fg.display_name == fg_name:
                finished_good = fg
                break

        if not finished_good:
            return None

        # Get quantity
        try:
            quantity = int(self.quantity_entry.get().strip())
            if quantity <= 0:
                return None
        except ValueError:
            return None

        return {
            "finished_good_id": finished_good.id,
            "quantity": quantity,
        }


class PackagingRow(ctk.CTkFrame):
    """
    Row widget for a single packaging material in the package.

    Feature 011: Basic packaging support with specific products
    Feature 026: Added support for generic product types with:
    - Toggle between Specific material and Generic product
    - Inventory summary for generic products
    - Estimated cost display
    """

    def __init__(
        self,
        parent,
        packaging_products: List,
        remove_callback,
        product_id: Optional[int] = None,
        quantity: float = 1.0,
        is_generic: bool = False,
        generic_product_name: Optional[str] = None,
    ):
        """
        Initialize Packaging row.

        Args:
            parent: Parent widget
            packaging_products: List of available packaging products
            remove_callback: Callback to remove this row
            product_id: Selected Product ID (None for new row)
            quantity: Packaging quantity (supports decimal)
            is_generic: Whether this is a generic requirement (Feature 026)
            generic_product_name: Product name for generic requirement
        """
        super().__init__(parent, fg_color="transparent")

        self.packaging_products = packaging_products
        self.remove_callback = remove_callback
        self._is_generic = is_generic

        # Configure grid - main row
        self.grid_columnconfigure(0, weight=1)

        # Create main content frame
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=0, sticky="ew")
        self.main_frame.grid_columnconfigure(1, weight=1)

        # Mode toggle (Specific / Generic)
        self.mode_var = ctk.StringVar(value="generic" if is_generic else "specific")
        mode_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        mode_frame.grid(row=0, column=0, padx=(0, PADDING_MEDIUM), pady=2)

        self.specific_radio = ctk.CTkRadioButton(
            mode_frame,
            text="Specific",
            variable=self.mode_var,
            value="specific",
            command=self._on_mode_change,
            width=80,
        )
        self.specific_radio.pack(side="left")

        self.generic_radio = ctk.CTkRadioButton(
            mode_frame,
            text="Generic",
            variable=self.mode_var,
            value="generic",
            command=self._on_mode_change,
            width=80,
        )
        self.generic_radio.pack(side="left", padx=(5, 0))

        # Content frame for dropdowns
        self.content_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.content_frame.grid(row=0, column=1, sticky="ew")
        self.content_frame.grid_columnconfigure(0, weight=1)

        # SPECIFIC mode: Product dropdown
        self._build_product_list()
        self.product_combo = ctk.CTkComboBox(
            self.content_frame,
            width=280,
            values=(
                self._product_names if self._product_names else ["No packaging products available"]
            ),
            state="readonly" if self._product_names else "disabled",
        )
        if self._product_names and not is_generic:
            if product_id:
                for i, product in enumerate(self.packaging_products):
                    if product.get("id") == product_id:
                        self.product_combo.set(self._product_names[i])
                        break
            else:
                self.product_combo.set(self._product_names[0])

        # GENERIC mode: Product type dropdown
        self._generic_products = self._load_generic_products()
        self.generic_combo = ctk.CTkComboBox(
            self.content_frame,
            width=280,
            values=(
                self._generic_products
                if self._generic_products
                else ["No generic products available"]
            ),
            state="readonly" if self._generic_products else "disabled",
            command=self._on_generic_selection_change,
        )
        if self._generic_products and is_generic:
            if generic_product_name and generic_product_name in self._generic_products:
                self.generic_combo.set(generic_product_name)
            else:
                self.generic_combo.set(self._generic_products[0])

        # Quantity entry (supports decimal)
        self.quantity_entry = ctk.CTkEntry(self.main_frame, width=60, placeholder_text="Qty")
        self.quantity_entry.insert(0, str(quantity))
        self.quantity_entry.grid(row=0, column=2, padx=PADDING_MEDIUM)
        # Bind quantity change to update cost
        self.quantity_entry.bind("<KeyRelease>", self._on_quantity_change)

        # Remove button
        remove_button = ctk.CTkButton(
            self.main_frame,
            text="X",
            width=30,
            command=lambda: remove_callback(self),
            fg_color="darkred",
            hover_color="red",
        )
        remove_button.grid(row=0, column=3)

        # Info frame for inventory summary and estimated cost (Generic mode only)
        self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.info_frame.grid(row=1, column=0, sticky="ew", padx=(170, 30), pady=(2, 0))

        self.inventory_label = ctk.CTkLabel(
            self.info_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        self.inventory_label.pack(side="left")

        self.cost_label = ctk.CTkLabel(
            self.info_frame,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#CC7700",  # Orange for "estimated"
        )
        self.cost_label.pack(side="right", padx=(20, 0))

        # Set initial mode
        self._on_mode_change()

    def _build_product_list(self):
        """Build list of product display names for specific mode."""
        self._product_names = []
        for product in self.packaging_products:
            ingredient_name = product.get("ingredient_name", "Unknown")
            brand = product.get("brand", "")
            package_size = product.get("package_size", "")
            self._product_names.append(f"{ingredient_name} - {brand} ({package_size})")

    def _load_generic_products(self) -> List[str]:
        """Load available generic product types."""
        try:
            return packaging_service.get_generic_products()
        except Exception:
            return []

    def _on_mode_change(self):
        """Handle mode toggle between Specific and Generic."""
        is_generic = self.mode_var.get() == "generic"
        self._is_generic = is_generic

        # Hide/show appropriate dropdowns
        if is_generic:
            self.product_combo.grid_forget()
            self.generic_combo.grid(row=0, column=0, sticky="ew")
            self.info_frame.grid()
            self._update_generic_info()
        else:
            self.generic_combo.grid_forget()
            self.product_combo.grid(row=0, column=0, sticky="ew")
            self.info_frame.grid_remove()
            self.inventory_label.configure(text="")
            self.cost_label.configure(text="")

    def _on_generic_selection_change(self, _=None):
        """Handle generic product selection change."""
        self._update_generic_info()

    def _on_quantity_change(self, _=None):
        """Handle quantity change to update cost."""
        if self._is_generic:
            self._update_generic_info()

    def _update_generic_info(self):
        """Update inventory summary and estimated cost for generic mode."""
        product_name = self.generic_combo.get()
        if not product_name or product_name == "No generic products available":
            self.inventory_label.configure(text="")
            self.cost_label.configure(text="")
            return

        try:
            # Get inventory summary
            summary = packaging_service.get_generic_inventory_summary(product_name)
            total = summary.get("total", 0)
            self.inventory_label.configure(text=f"Available: {int(total)}")

            # Get estimated cost
            try:
                qty = float(self.quantity_entry.get().strip())
                if qty > 0:
                    cost = packaging_service.get_estimated_cost(product_name, qty)
                    self.cost_label.configure(text=f"Est: ${cost:.2f}")
                else:
                    self.cost_label.configure(text="")
            except ValueError:
                self.cost_label.configure(text="")
        except Exception:
            self.inventory_label.configure(text="")
            self.cost_label.configure(text="")

    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Get packaging data from this row.

        Returns:
            Dictionary with product_id, quantity, is_generic, and optionally
            product_name for generic requirements. Returns None if invalid.
        """
        is_generic = self.mode_var.get() == "generic"

        # Get quantity (supports decimal)
        try:
            quantity = float(self.quantity_entry.get().strip())
            if quantity <= 0:
                return None
        except ValueError:
            return None

        if is_generic:
            # Generic mode: get product_name
            product_name = self.generic_combo.get()
            if not product_name or product_name == "No generic products available":
                return None

            # Find a template product with this product_name
            template_product_id = self._find_template_product_id(product_name)
            if not template_product_id:
                return None

            return {
                "product_id": template_product_id,
                "quantity": quantity,
                "is_generic": True,
                "product_name": product_name,
            }
        else:
            # Specific mode: get product from dropdown
            product_display = self.product_combo.get()
            if not product_display or product_display == "No packaging products available":
                return None

            # Find product by display name
            product = None
            for i, p in enumerate(self.packaging_products):
                if self._product_names[i] == product_display:
                    product = p
                    break

            if not product:
                return None

            return {
                "product_id": product.get("id"),
                "quantity": quantity,
                "is_generic": False,
            }

    def _find_template_product_id(self, product_name: str) -> Optional[int]:
        """Find a product ID to use as template for a generic product_name."""
        for product in self.packaging_products:
            # Check if this product has a matching product_name
            # We need to query the actual product to check its product_name
            prod_id = product.get("id")
            try:
                from src.services import product_service

                prod = product_service.get_product(prod_id)
                if prod and prod.product_name == product_name:
                    return prod_id
            except Exception:
                continue
        # If no match found, return the first product as template
        if self.packaging_products:
            return self.packaging_products[0].get("id")
        return None


class PackageFormDialog(ctk.CTkToplevel):
    """
    Dialog for creating or editing a package.

    Provides a form with FinishedGood selection and management.
    """

    def __init__(
        self,
        parent,
        package: Optional[Package] = None,
        title: str = "Add Package",
    ):
        """
        Initialize the package form dialog.

        Args:
            parent: Parent window
            package: Existing package to edit (None for new)
            title: Dialog title
        """
        super().__init__(parent)

        self.package = package
        self.result = None
        self.finished_good_rows: List[FinishedGoodRow] = []
        self.packaging_rows: List[PackagingRow] = []  # Feature 011

        # Load available FinishedGoods
        try:
            self.available_finished_goods = finished_good_service.get_all_finished_goods()
        except Exception:
            self.available_finished_goods = []

        # Feature 011: Load available packaging products
        self.available_packaging_products = self._load_packaging_products()

        # Configure window
        self.title(title)
        self.geometry("700x850")  # Increased height for packaging section
        self.resizable(False, False)

        # Center on parent
        self.transient(parent)

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create main frame
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=PADDING_LARGE, pady=PADDING_LARGE)
        main_frame.grid_columnconfigure(1, weight=1)

        # Create form fields
        self._create_form_fields(main_frame)

        # Create buttons
        self._create_buttons()

        # Populate if editing
        if self.package:
            self._populate_form()
        else:
            # Add one empty FinishedGood row for new packages
            self._add_finished_good_row()

        # Center dialog on parent and make visible
        self.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()
        x = max(0, parent_x + (parent_width - dialog_width) // 2)
        y = max(0, parent_y + (parent_height - dialog_height) // 2)
        self.geometry(f"+{x}+{y}")
        self.wait_visibility()
        self.grab_set()
        self.focus_force()

    def _create_form_fields(self, parent):
        """Create all form input fields."""
        row = 0

        # Name field (required)
        name_label = ctk.CTkLabel(parent, text="Package Name*:", anchor="w")
        name_label.grid(
            row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=(PADDING_MEDIUM, 5)
        )

        self.name_entry = ctk.CTkEntry(
            parent, width=500, placeholder_text="e.g., Deluxe Cookie Assortment, Standard Gift Box"
        )
        self.name_entry.grid(
            row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=(PADDING_MEDIUM, 5)
        )
        row += 1

        # Description field (optional)
        desc_label = ctk.CTkLabel(parent, text="Description:", anchor="w")
        desc_label.grid(row=row, column=0, sticky="nw", padx=PADDING_MEDIUM, pady=5)

        self.description_text = ctk.CTkTextbox(parent, width=500, height=80)
        self.description_text.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Template checkbox
        self.is_template_var = ctk.BooleanVar(value=False)
        template_check = ctk.CTkCheckBox(
            parent,
            text="Save as template (reusable across events)",
            variable=self.is_template_var,
        )
        template_check.grid(
            row=row, column=0, columnspan=2, sticky="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        row += 1

        # Finished Goods section
        fg_label = ctk.CTkLabel(
            parent,
            text="Finished Goods in Package",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        fg_label.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=PADDING_MEDIUM,
            pady=(PADDING_LARGE, PADDING_MEDIUM),
        )
        row += 1

        # Finished Goods list frame
        self.fg_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.fg_frame.grid(
            row=row, column=0, columnspan=2, sticky="ew", padx=PADDING_MEDIUM, pady=5
        )
        self.fg_frame.grid_columnconfigure(0, weight=1)
        row += 1

        # Add FinishedGood button
        add_button = ctk.CTkButton(
            parent,
            text="+ Add Finished Good",
            command=self._add_finished_good_row,
            width=180,
        )
        add_button.grid(
            row=row, column=0, columnspan=2, sticky="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        row += 1

        # Feature 011: Packaging section
        pkg_label = ctk.CTkLabel(
            parent,
            text="📦 Packaging Materials",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        pkg_label.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=PADDING_MEDIUM,
            pady=(PADDING_LARGE, PADDING_MEDIUM),
        )
        row += 1

        # Packaging list frame
        self.packaging_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.packaging_frame.grid(
            row=row, column=0, columnspan=2, sticky="ew", padx=PADDING_MEDIUM, pady=5
        )
        self.packaging_frame.grid_columnconfigure(0, weight=1)
        row += 1

        # Add Packaging button
        add_pkg_button = ctk.CTkButton(
            parent,
            text="+ Add Packaging",
            command=self._add_packaging_row,
            width=180,
        )
        add_pkg_button.grid(
            row=row, column=0, columnspan=2, sticky="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        row += 1

        # Notes field (optional)
        notes_label = ctk.CTkLabel(parent, text="Notes:", anchor="w")
        notes_label.grid(row=row, column=0, sticky="nw", padx=PADDING_MEDIUM, pady=5)

        self.notes_text = ctk.CTkTextbox(parent, width=500, height=100)
        self.notes_text.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Required field note
        required_note = ctk.CTkLabel(
            parent,
            text="* Required fields",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="gray",
        )
        required_note.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=PADDING_MEDIUM,
            pady=(PADDING_MEDIUM, 0),
        )

    def _add_finished_good_row(self, finished_good_id: Optional[int] = None, quantity: int = 1):
        """
        Add a new FinishedGood row.

        Args:
            finished_good_id: Optional FinishedGood ID to pre-select
            quantity: FinishedGood quantity
        """
        row = FinishedGoodRow(
            self.fg_frame,
            self.available_finished_goods,
            self._remove_finished_good_row,
            finished_good_id=finished_good_id,
            quantity=quantity,
        )
        row.grid(row=len(self.finished_good_rows), column=0, sticky="ew", pady=2)
        self.finished_good_rows.append(row)

    def _remove_finished_good_row(self, row: FinishedGoodRow):
        """
        Remove a FinishedGood row.

        Args:
            row: FinishedGoodRow to remove
        """
        if row in self.finished_good_rows:
            self.finished_good_rows.remove(row)
            row.destroy()

            # Re-grid remaining rows
            for i, remaining_row in enumerate(self.finished_good_rows):
                remaining_row.grid(row=i, column=0, sticky="ew", pady=2)

    def _load_packaging_products(self) -> List[Dict[str, Any]]:
        """
        Load all available packaging products (Feature 011).

        Returns:
            List of dicts with product info for packaging ingredients
        """
        try:
            # Get all packaging ingredients
            packaging_ingredients = ingredient_service.get_packaging_ingredients()

            # Get products for each packaging ingredient
            products = []
            for ingredient in packaging_ingredients:
                ingredient_products = product_service.get_products_for_ingredient(ingredient.id)
                for product in ingredient_products:
                    products.append(
                        {
                            "id": product.id,
                            "ingredient_id": ingredient.id,
                            "ingredient_name": ingredient.display_name,
                            "brand": product.brand or "",
                            "package_size": product.package_size or "",
                        }
                    )
            return products
        except Exception:
            return []

    def _add_packaging_row(
        self,
        product_id: Optional[int] = None,
        quantity: float = 1.0,
        is_generic: bool = False,
        generic_product_name: Optional[str] = None,
    ):
        """
        Add a new Packaging row.

        Feature 011: Basic packaging support
        Feature 026: Added is_generic and generic_product_name parameters

        Args:
            product_id: Optional Product ID to pre-select
            quantity: Packaging quantity (supports decimal)
            is_generic: Whether this is a generic requirement
            generic_product_name: Product name for generic requirement
        """
        row = PackagingRow(
            self.packaging_frame,
            self.available_packaging_products,
            self._remove_packaging_row,
            product_id=product_id,
            quantity=quantity,
            is_generic=is_generic,
            generic_product_name=generic_product_name,
        )
        row.grid(row=len(self.packaging_rows), column=0, sticky="ew", pady=2)
        self.packaging_rows.append(row)

    def _remove_packaging_row(self, row: PackagingRow):
        """
        Remove a Packaging row (Feature 011).

        Args:
            row: PackagingRow to remove
        """
        if row in self.packaging_rows:
            self.packaging_rows.remove(row)
            row.destroy()

            # Re-grid remaining rows
            for i, remaining_row in enumerate(self.packaging_rows):
                remaining_row.grid(row=i, column=0, sticky="ew", pady=2)

    def _create_buttons(self):
        """Create dialog buttons."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)
        button_frame.grid_columnconfigure((0, 1), weight=1)

        # Save button
        save_button = ctk.CTkButton(
            button_frame,
            text="Save",
            command=self._save,
            width=150,
        )
        save_button.grid(row=0, column=0, padx=PADDING_MEDIUM)

        # Cancel button
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._cancel,
            width=150,
            fg_color="gray",
            hover_color="darkgray",
        )
        cancel_button.grid(row=0, column=1, padx=PADDING_MEDIUM)

    def _populate_form(self):
        """Populate form fields with existing package data."""
        if not self.package:
            return

        self.name_entry.insert(0, self.package.name)

        if self.package.description:
            self.description_text.insert("1.0", self.package.description)

        self.is_template_var.set(self.package.is_template)

        if self.package.notes:
            self.notes_text.insert("1.0", self.package.notes)

        # Add FinishedGood rows
        if self.package.package_finished_goods:
            for pfg in self.package.package_finished_goods:
                self._add_finished_good_row(
                    finished_good_id=pfg.finished_good_id, quantity=pfg.quantity
                )

        # Feature 011: Add Packaging rows from existing compositions
        # Feature 026: Load is_generic flag and product_name
        if self.package.id:
            try:
                packaging_comps = composition_service.get_package_packaging(self.package.id)
                for comp in packaging_comps:
                    if comp.packaging_product_id:
                        # Feature 026: Get product_name for generic compositions
                        generic_product_name = None
                        if comp.is_generic and comp.packaging_product:
                            generic_product_name = comp.packaging_product.product_name
                        self._add_packaging_row(
                            product_id=comp.packaging_product_id,
                            quantity=comp.component_quantity,
                            is_generic=comp.is_generic,
                            generic_product_name=generic_product_name,
                        )
            except Exception:
                pass  # No existing packaging or error loading

    def _save(self):
        """Validate and save the package data."""
        # Validate and collect data
        data = self._validate_and_collect()
        if data is None:
            return

        # Set result and close
        self.result = data
        self.destroy()

    def _cancel(self):
        """Cancel the dialog."""
        self.result = None
        self.destroy()

    def _validate_and_collect(self) -> Optional[Dict[str, Any]]:
        """
        Validate form inputs and collect data.

        Returns:
            Dictionary with package data and finished_good_items list, or None if validation fails
        """
        # Get values
        name = self.name_entry.get().strip()
        description = self.description_text.get("1.0", "end-1c").strip()
        is_template = self.is_template_var.get()
        notes = self.notes_text.get("1.0", "end-1c").strip()

        # Validate required fields
        if not name:
            show_error(
                "Validation Error",
                "Package name is required",
                parent=self,
            )
            return None

        # Validate lengths
        if len(name) > MAX_NAME_LENGTH:
            show_error(
                "Validation Error",
                f"Name must be {MAX_NAME_LENGTH} characters or less",
                parent=self,
            )
            return None

        if notes and len(notes) > MAX_NOTES_LENGTH:
            show_error(
                "Validation Error",
                f"Notes must be {MAX_NOTES_LENGTH} characters or less",
                parent=self,
            )
            return None

        # Collect FinishedGood items
        finished_good_items = []
        for row in self.finished_good_rows:
            fg_data = row.get_data()
            if fg_data:
                finished_good_items.append(fg_data)

        # Validate at least one FinishedGood
        if not finished_good_items:
            show_error(
                "Validation Error",
                "Package must contain at least one finished good",
                parent=self,
            )
            return None

        # Feature 011: Collect Packaging items (optional)
        packaging_items = []
        for row in self.packaging_rows:
            pkg_data = row.get_data()
            if pkg_data:
                packaging_items.append(pkg_data)

        # Return validated data
        return {
            "package_data": {
                "name": name,
                "description": description if description else None,
                "is_template": is_template,
                "notes": notes if notes else None,
            },
            "finished_good_items": finished_good_items,
            "packaging_items": packaging_items,  # Feature 011
        }

    def get_result(self) -> Optional[Dict[str, Any]]:
        """Get the dialog result."""
        return self.result
