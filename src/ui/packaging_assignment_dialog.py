"""
Packaging Assignment Dialog for assigning specific materials to generic packaging requirements.

Feature 026: Deferred Packaging Decisions

This dialog allows users to:
- View available specific products matching a generic packaging requirement
- Select and specify quantities from available inventory
- See real-time running total with color-coded status
- Save assignments once totals match requirements
"""

import customtkinter as ctk
from typing import Optional, List, Dict, Any, Callable
from decimal import Decimal

from src.services import packaging_service
from src.utils.constants import PADDING_MEDIUM, PADDING_LARGE


class ProductAssignmentRow(ctk.CTkFrame):
    """Row widget for a single product assignment option."""

    def __init__(
        self,
        parent,
        product_info: Dict[str, Any],
        on_change_callback: Callable,
    ):
        """
        Initialize product assignment row.

        Args:
            parent: Parent widget
            product_info: Dict with brand, product_id, available, unit_cost
            on_change_callback: Callback when selection or quantity changes
        """
        super().__init__(parent, fg_color="transparent")

        self.product_info = product_info
        self.on_change_callback = on_change_callback

        self.grid_columnconfigure(1, weight=1)

        # Checkbox for selection
        self.selected_var = ctk.BooleanVar(value=False)
        self.checkbox = ctk.CTkCheckBox(
            self,
            text="",
            variable=self.selected_var,
            command=self._on_selection_change,
            width=24,
        )
        self.checkbox.grid(row=0, column=0, padx=(0, PADDING_MEDIUM))

        # Product info label
        brand = product_info.get("brand", "Unknown")
        available = product_info.get("available", 0)
        unit_cost = product_info.get("unit_cost", 0.0)
        info_text = f"{brand} - Available: {int(available)} @ ${unit_cost:.2f}/ea"

        self.info_label = ctk.CTkLabel(
            self,
            text=info_text,
            anchor="w",
        )
        self.info_label.grid(row=0, column=1, sticky="ew")

        # Quantity entry
        self.quantity_var = ctk.StringVar(value="0")
        self.quantity_entry = ctk.CTkEntry(
            self,
            width=60,
            textvariable=self.quantity_var,
            state="disabled",
        )
        self.quantity_entry.grid(row=0, column=2, padx=PADDING_MEDIUM)
        self.quantity_var.trace_add("write", self._on_quantity_change)

    def _on_selection_change(self):
        """Handle checkbox selection change."""
        if self.selected_var.get():
            self.quantity_entry.configure(state="normal")
            # Auto-fill with available quantity if empty or zero
            try:
                current = int(self.quantity_var.get())
                if current == 0:
                    available = self.product_info.get("available", 0)
                    self.quantity_var.set(str(int(available)))
            except ValueError:
                available = self.product_info.get("available", 0)
                self.quantity_var.set(str(int(available)))
        else:
            self.quantity_entry.configure(state="disabled")
            self.quantity_var.set("0")
        self.on_change_callback()

    def _on_quantity_change(self, *args):
        """Handle quantity value change."""
        self.on_change_callback()

    def get_assignment_data(self) -> Optional[Dict[str, Any]]:
        """
        Get assignment data if this row is selected.

        Returns:
            Dict with inventory_item_id and quantity, or None if not selected
        """
        if not self.selected_var.get():
            return None

        try:
            quantity = int(self.quantity_var.get())
            if quantity <= 0:
                return None

            return {
                "inventory_item_id": self.product_info.get("inventory_item_id"),
                "quantity": quantity,
            }
        except ValueError:
            return None

    def get_quantity(self) -> int:
        """Get current quantity value."""
        if not self.selected_var.get():
            return 0
        try:
            return max(0, int(self.quantity_var.get()))
        except ValueError:
            return 0

    def get_available(self) -> int:
        """Get available quantity for this product."""
        return int(self.product_info.get("available", 0))

    def is_valid(self) -> bool:
        """Check if this row has valid data."""
        if not self.selected_var.get():
            return True  # Unselected is always valid

        quantity = self.get_quantity()
        available = self.get_available()
        return 0 < quantity <= available


class PackagingAssignmentDialog(ctk.CTkToplevel):
    """
    Dialog for assigning specific materials to a generic packaging requirement.

    Shows available products matching the generic product type, allows
    quantity selection, and validates that assignments sum to requirement.
    """

    def __init__(
        self,
        parent,
        composition_id: int,
        on_complete_callback: Optional[Callable] = None,
    ):
        """
        Initialize the packaging assignment dialog.

        Args:
            parent: Parent window
            composition_id: ID of the generic composition to assign materials to
            on_complete_callback: Optional callback when assignment is completed
        """
        super().__init__(parent)

        self.composition_id = composition_id
        self.on_complete_callback = on_complete_callback
        self.result = False
        self.product_rows: List[ProductAssignmentRow] = []

        # Load composition data
        self._load_composition_data()

        # Configure window
        self.title("Assign Packaging Materials")
        self.geometry("550x500")
        self.resizable(False, True)

        # Setup UI
        self._setup_ui()

        # Modal behavior
        self.transient(parent)
        self.grab_set()

        # Center on parent
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

    def _load_composition_data(self):
        """Load composition and available inventory data."""
        try:
            summary = packaging_service.get_assignment_summary(self.composition_id)
            self.required_quantity = int(summary.get("required", 0))
            self.product_name = summary.get("product_name", "Unknown")

            # Get individual inventory items for assignment
            self.available_products = packaging_service.get_available_inventory_items(
                self.product_name
            )
            self.total_available = sum(p.get("available", 0) for p in self.available_products)

        except Exception as e:
            self.required_quantity = 0
            self.product_name = "Error loading"
            self.available_products = []
            self.total_available = 0
            print(f"Error loading composition data: {e}")

    def _setup_ui(self):
        """Set up the dialog UI."""
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_MEDIUM))

        title_label = ctk.CTkLabel(
            header_frame,
            text="Assign Materials",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title_label.pack(anchor="w")

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text=f"For: {self.product_name}",
            font=ctk.CTkFont(size=14),
            text_color="gray",
        )
        subtitle_label.pack(anchor="w")

        # Required quantity display
        req_label = ctk.CTkLabel(
            header_frame,
            text=f"Required: {self.required_quantity}",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        req_label.pack(anchor="w", pady=(PADDING_MEDIUM, 0))

        # Products list frame (scrollable)
        list_frame = ctk.CTkScrollableFrame(self, height=280)
        list_frame.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=PADDING_MEDIUM)

        if not self.available_products:
            no_products_label = ctk.CTkLabel(
                list_frame,
                text="No products available with matching inventory.",
                text_color="gray",
            )
            no_products_label.pack(pady=PADDING_LARGE)
        else:
            # Add header row
            header = ctk.CTkFrame(list_frame, fg_color="transparent")
            header.pack(fill="x", pady=(0, PADDING_MEDIUM))
            header.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(header, text="", width=24).grid(row=0, column=0)
            ctk.CTkLabel(header, text="Product", anchor="w", font=ctk.CTkFont(weight="bold")).grid(
                row=0, column=1, sticky="w", padx=PADDING_MEDIUM
            )
            ctk.CTkLabel(header, text="Qty", font=ctk.CTkFont(weight="bold")).grid(
                row=0, column=2, padx=PADDING_MEDIUM
            )

            # Add product rows
            for product in self.available_products:
                row = ProductAssignmentRow(
                    list_frame,
                    product,
                    self._on_quantity_change,
                )
                row.pack(fill="x", pady=2)
                self.product_rows.append(row)

        # Running total frame
        total_frame = ctk.CTkFrame(self)
        total_frame.pack(fill="x", padx=PADDING_LARGE, pady=PADDING_MEDIUM)

        self.total_label = ctk.CTkLabel(
            total_frame,
            text=f"Assigned: 0 / {self.required_quantity} needed",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.total_label.pack(pady=PADDING_MEDIUM)

        self.status_label = ctk.CTkLabel(
            total_frame,
            text="Select products and enter quantities",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self.status_label.pack()

        # Button frame
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=PADDING_LARGE, pady=PADDING_LARGE)

        self.save_button = ctk.CTkButton(
            button_frame,
            text="Save Assignment",
            command=self._save,
            state="disabled",
        )
        self.save_button.pack(side="left", padx=(0, PADDING_MEDIUM))

        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._cancel,
            fg_color="gray",
            hover_color="darkgray",
        )
        cancel_button.pack(side="left")

        # Initial update
        self._update_total_display()

    def _on_quantity_change(self):
        """Handle any quantity change in product rows."""
        self._update_total_display()

    def _update_total_display(self):
        """Update the running total and validation status."""
        total_assigned = sum(row.get_quantity() for row in self.product_rows)

        # Update total label
        self.total_label.configure(
            text=f"Assigned: {total_assigned} / {self.required_quantity} needed"
        )

        # Determine color and status
        all_valid = all(row.is_valid() for row in self.product_rows)

        if not all_valid:
            # Some row exceeds available
            color = "#CC0000"  # Red
            status = "Error: Some quantities exceed available inventory"
            can_save = False
        elif total_assigned == 0:
            color = "gray"
            status = "Select products and enter quantities"
            can_save = False
        elif total_assigned < self.required_quantity:
            color = "#CC7700"  # Orange
            remaining = self.required_quantity - total_assigned
            status = f"Need {remaining} more to complete assignment"
            can_save = False
        elif total_assigned > self.required_quantity:
            color = "#CC0000"  # Red
            excess = total_assigned - self.required_quantity
            status = f"Over by {excess} - reduce quantities"
            can_save = False
        else:
            color = "#00AA00"  # Green
            status = "Ready to save"
            can_save = True

        self.total_label.configure(text_color=color)
        self.status_label.configure(text=status)
        self.save_button.configure(state="normal" if can_save else "disabled")

    def _save(self):
        """Save the material assignments."""
        # Collect assignments
        assignments = []
        for row in self.product_rows:
            data = row.get_assignment_data()
            if data:
                assignments.append(data)

        if not assignments:
            return

        try:
            packaging_service.assign_materials(self.composition_id, assignments)
            self.result = True

            if self.on_complete_callback:
                self.on_complete_callback()

            self.destroy()

        except Exception as e:
            from src.ui.widgets.dialogs import show_error

            show_error("Assignment Error", str(e), parent=self)

    def _cancel(self):
        """Cancel and close the dialog."""
        self.result = False
        self.destroy()

    def get_result(self) -> bool:
        """Get whether assignment was successful."""
        return self.result
