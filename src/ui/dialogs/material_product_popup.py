"""
Read-only popup showing MaterialProduct details.

Feature 084: MaterialUnit Schema Refactor - WP08.
Popup opened when clicking a unit row in Units tab.
"""

import customtkinter as ctk
from typing import Optional

from src.services import material_catalog_service, material_unit_service
from src.services.exceptions import ServiceError


class MaterialProductPopup(ctk.CTkToplevel):
    """
    Read-only popup showing MaterialProduct details.

    Feature 084: Shows product info including its MaterialUnits.
    Used when clicking a row in the Units tab.
    """

    def __init__(self, parent, product_id: int):
        """
        Initialize the MaterialProduct popup.

        Args:
            parent: Parent window
            product_id: ID of the MaterialProduct to display
        """
        super().__init__(parent)

        self.product_id = product_id

        # Modal pattern - hide while building
        self.withdraw()

        # Load product data
        self.product = material_catalog_service.get_product(product_id)
        if not self.product:
            self.destroy()
            return

        # Get material info
        self.material = None
        if hasattr(self.product, 'material'):
            self.material = self.product.material
        elif hasattr(self.product, 'material_id') and self.product.material_id:
            # Try to get material via service
            try:
                from src.services.database import session_scope
                from src.models.material import Material
                with session_scope() as session:
                    self.material = session.query(Material).get(self.product.material_id)
            except (ServiceError, Exception):
                pass

        # Window setup
        product_name = getattr(self.product, 'name', 'Product')
        self.title(f"Product: {product_name}")
        self.geometry("450x450")
        self.resizable(False, False)

        # Center on parent
        self.transient(parent)

        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        self._create_widgets()

        # Show dialog after UI is complete
        self.deiconify()
        self.update()
        try:
            self.wait_visibility()
            self.grab_set()
        except (ServiceError, Exception):
            if not self.winfo_exists():
                return
        self.lift()
        self.focus_force()

    def _create_widgets(self):
        """Create read-only display widgets."""
        # Header
        product_name = getattr(self.product, 'name', 'Unknown Product')
        header = ctk.CTkLabel(
            self,
            text=product_name,
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        header.pack(pady=(20, 10))

        # Details frame
        details_frame = ctk.CTkFrame(self)
        details_frame.pack(fill="x", padx=20, pady=10)

        # Material
        material_name = getattr(self.material, 'name', 'N/A') if self.material else 'N/A'
        self._add_field(details_frame, "Material:", material_name)

        # Brand
        brand = getattr(self.product, 'brand', None) or 'N/A'
        self._add_field(details_frame, "Brand:", brand)

        # Package info
        pkg_qty = getattr(self.product, 'package_quantity', None)
        pkg_unit = getattr(self.product, 'package_unit', None)
        if pkg_qty and pkg_unit:
            self._add_field(details_frame, "Package:", f"{pkg_qty} {pkg_unit}")

        # Quantity in base units
        base_units = getattr(self.product, 'quantity_in_base_units', None)
        if base_units:
            self._add_field(details_frame, "Base Units:", f"{base_units:.4f}")

        # Supplier
        supplier_name = 'N/A'
        if hasattr(self.product, 'supplier') and self.product.supplier:
            supplier_name = getattr(self.product.supplier, 'name', 'N/A')
        self._add_field(details_frame, "Supplier:", supplier_name)

        # SKU
        sku = getattr(self.product, 'sku', None)
        if sku:
            self._add_field(details_frame, "SKU:", sku)

        # Units section header
        units_label = ctk.CTkLabel(
            self,
            text="Material Units",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        units_label.pack(anchor="w", padx=25, pady=(15, 5))

        # List units in scrollable frame
        units_frame = ctk.CTkScrollableFrame(self, height=120)
        units_frame.pack(fill="x", padx=20, pady=5)

        # Get units for this product
        try:
            units = material_unit_service.list_units(self.product_id)
            if units:
                for unit in units:
                    unit_name = getattr(unit, 'name', 'Unknown')
                    qty = getattr(unit, 'quantity_per_unit', 1.0)
                    unit_text = f"  {unit_name} ({qty:.4f})"
                    ctk.CTkLabel(units_frame, text=unit_text, anchor="w").pack(anchor="w", padx=5)
            else:
                ctk.CTkLabel(
                    units_frame,
                    text="No units defined",
                    text_color="gray"
                ).pack(anchor="w", padx=5)
        except (ServiceError, Exception) as e:
            ctk.CTkLabel(
                units_frame,
                text=f"Error loading units: {e}",
                text_color="red"
            ).pack(anchor="w", padx=5)

        # Info label
        info_label = ctk.CTkLabel(
            self,
            text="To add/edit units, edit the MaterialProduct.",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="gray",
        )
        info_label.pack(pady=(10, 5))

        # Close button
        ctk.CTkButton(
            self,
            text="Close",
            command=self.destroy,
            width=100,
        ).pack(pady=15)

    def _add_field(self, parent, label: str, value: str):
        """Add a label-value pair."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=2)
        ctk.CTkLabel(frame, text=label, width=100, anchor="e").pack(side="left", padx=5)
        ctk.CTkLabel(frame, text=value, anchor="w").pack(side="left", padx=5)
