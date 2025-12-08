"""
Package form dialog for adding and editing packages.

Provides a form for creating and updating package records with FinishedGood selection.

Updated for Feature 006 Event Planning Restoration:
- Replaced Bundle references with FinishedGood
- Uses finished_good_service.get_all_finished_goods()

Updated for Feature 011 Packaging BOM Foundation:
- Added packaging section to allow adding packaging materials to packages
- Uses composition_service for packaging relationships
"""

import customtkinter as ctk
from typing import Optional, Dict, Any, List
from decimal import Decimal

from src.models.package import Package
from src.services import finished_good_service, ingredient_service, product_service
from src.services import composition_service
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
            cost = fg.total_cost if fg.total_cost else Decimal("0.00")
            fg_names.append(f"{fg.display_name} (${cost:.2f})")

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
    """Row widget for a single packaging material in the package (Feature 011)."""

    def __init__(
        self,
        parent,
        packaging_products: List,
        remove_callback,
        product_id: Optional[int] = None,
        quantity: float = 1.0,
    ):
        """
        Initialize Packaging row.

        Args:
            parent: Parent widget
            packaging_products: List of available packaging products
            remove_callback: Callback to remove this row
            product_id: Selected Product ID (None for new row)
            quantity: Packaging quantity (supports decimal)
        """
        super().__init__(parent, fg_color="transparent")

        self.packaging_products = packaging_products
        self.remove_callback = remove_callback

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=0)

        # Product dropdown
        product_names = []
        for product in packaging_products:
            ingredient_name = product.get("ingredient_name", "Unknown")
            brand = product.get("brand", "")
            package_size = product.get("package_size", "")
            product_names.append(f"{ingredient_name} - {brand} ({package_size})")

        self.product_combo = ctk.CTkComboBox(
            self,
            width=350,
            values=product_names if product_names else ["No packaging products available"],
            state="readonly" if product_names else "disabled",
        )
        if product_names:
            # Set selected product if provided
            if product_id:
                for i, product in enumerate(packaging_products):
                    if product.get("id") == product_id:
                        self.product_combo.set(product_names[i])
                        break
            else:
                self.product_combo.set(product_names[0])

        self.product_combo.grid(row=0, column=0, sticky="ew", padx=(0, PADDING_MEDIUM))

        # Quantity entry (supports decimal)
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
        Get packaging data from this row.

        Returns:
            Dictionary with product_id and quantity, or None if invalid
        """
        product_display = self.product_combo.get()
        if not product_display or product_display == "No packaging products available":
            return None

        # Find product by display name
        product = None
        for i, p in enumerate(self.packaging_products):
            ingredient_name = p.get("ingredient_name", "Unknown")
            brand = p.get("brand", "")
            package_size = p.get("package_size", "")
            expected_name = f"{ingredient_name} - {brand} ({package_size})"
            if expected_name == product_display:
                product = p
                break

        if not product:
            return None

        # Get quantity (supports decimal)
        try:
            quantity = float(self.quantity_entry.get().strip())
            if quantity <= 0:
                return None
        except ValueError:
            return None

        return {
            "product_id": product.get("id"),
            "quantity": quantity,
        }


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
                    products.append({
                        "id": product.id,
                        "ingredient_id": ingredient.id,
                        "ingredient_name": ingredient.display_name,
                        "brand": product.brand or "",
                        "package_size": product.package_size or "",
                    })
            return products
        except Exception:
            return []

    def _add_packaging_row(self, product_id: Optional[int] = None, quantity: float = 1.0):
        """
        Add a new Packaging row (Feature 011).

        Args:
            product_id: Optional Product ID to pre-select
            quantity: Packaging quantity (supports decimal)
        """
        row = PackagingRow(
            self.packaging_frame,
            self.available_packaging_products,
            self._remove_packaging_row,
            product_id=product_id,
            quantity=quantity,
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
        if self.package.id:
            try:
                packaging_comps = composition_service.get_package_packaging(self.package.id)
                for comp in packaging_comps:
                    if comp.packaging_product_id:
                        self._add_packaging_row(
                            product_id=comp.packaging_product_id,
                            quantity=comp.component_quantity,
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
