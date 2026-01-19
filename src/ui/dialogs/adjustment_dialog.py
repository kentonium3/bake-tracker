"""
Manual Inventory Adjustment Dialog.

Provides a modal dialog for recording manual inventory depletions
with live preview of quantity and cost impact.
"""

import customtkinter as ctk
from decimal import Decimal, InvalidOperation
from typing import Optional, Callable


from src.models.enums import DepletionReason


class AdjustmentDialog(ctk.CTkToplevel):
    """
    Modal dialog for manual inventory adjustments.

    Displays current inventory information and allows the user to enter
    a depletion amount, select a reason, and optionally add notes.
    Provides live preview showing the resulting quantity and cost impact.

    Args:
        parent: Parent window
        inventory_item: The InventoryItem to adjust
        on_apply: Callback function when adjustment is applied.
                  Called with (inventory_item_id, quantity, reason, notes).
    """

    # Reason labels for dropdown - only show manual depletion reasons
    REASON_LABELS = {
        DepletionReason.SPOILAGE: "Spoilage/Waste",
        DepletionReason.GIFT: "Gift/Donation",
        DepletionReason.CORRECTION: "Physical Count Correction",
        DepletionReason.AD_HOC_USAGE: "Ad Hoc Usage (Testing/Personal)",
        DepletionReason.OTHER: "Other (specify in notes)",
    }

    def __init__(
        self,
        parent,
        inventory_item,
        on_apply: Optional[Callable] = None,
    ):
        super().__init__(parent)
        self.inventory_item = inventory_item
        self.on_apply = on_apply

        self.title("Adjust Inventory")
        self.geometry("450x500")
        self.resizable(False, False)

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Store current values for calculations
        self._extract_inventory_info()

        # Initialize UI
        self._create_widgets()
        self._layout_widgets()
        self._bind_events()

        # Center on parent
        self.update_idletasks()
        self._center_on_parent(parent)

        # Focus on quantity entry
        self.qty_entry.focus_set()

    def _extract_inventory_info(self):
        """Extract and store inventory item information for display and calculations."""
        # Handle both ORM objects and dicts
        if hasattr(self.inventory_item, "product"):
            # ORM object
            product = self.inventory_item.product
            self.product_name = (
                product.display_name if hasattr(product, "display_name") else product.product_name
            )
            self.purchase_date = self.inventory_item.purchase_date
            self.current_quantity = Decimal(str(self.inventory_item.quantity))
            self.unit = product.package_unit or "units"
            self.unit_cost = Decimal(str(self.inventory_item.unit_cost or 0))
        else:
            # Dict (from service layer)
            self.product_name = self.inventory_item.get(
                "product_name", self.inventory_item.get("display_name", "Unknown")
            )
            self.purchase_date = self.inventory_item.get("purchase_date", "N/A")
            self.current_quantity = Decimal(str(self.inventory_item.get("quantity", 0)))
            self.unit = self.inventory_item.get("package_unit", "units")
            self.unit_cost = Decimal(str(self.inventory_item.get("unit_cost", 0)))

    def _create_widgets(self):
        """Create all dialog widgets."""
        # Current inventory info section
        self.info_frame = ctk.CTkFrame(self)

        self.product_label = ctk.CTkLabel(
            self.info_frame,
            text=f"Product: {self.product_name}",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.date_label = ctk.CTkLabel(
            self.info_frame,
            text=f"Purchase Date: {self.purchase_date}",
        )
        self.quantity_label = ctk.CTkLabel(
            self.info_frame,
            text=f"Current Quantity: {self.current_quantity} {self.unit}",
        )
        self.cost_label = ctk.CTkLabel(
            self.info_frame,
            text=f"Unit Cost: ${self.unit_cost:.2f}/{self.unit}",
        )

        # Adjustment input section
        self.input_frame = ctk.CTkFrame(self)

        self.qty_label = ctk.CTkLabel(
            self.input_frame,
            text="Reduce By:",
        )
        self.qty_entry = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="Enter amount",
            width=150,
        )
        self.qty_unit_label = ctk.CTkLabel(
            self.input_frame,
            text=self.unit,
        )

        # Reason dropdown
        self.reason_label = ctk.CTkLabel(
            self.input_frame,
            text="Reason:",
        )

        # Create dropdown values from enum
        self.reason_options = list(self.REASON_LABELS.values())
        self.reason_var = ctk.StringVar(value=self.reason_options[0])

        self.reason_dropdown = ctk.CTkComboBox(
            self.input_frame,
            values=self.reason_options,
            variable=self.reason_var,
            width=250,
            state="readonly",
        )

        # Notes field
        self.notes_label = ctk.CTkLabel(
            self.input_frame,
            text="Notes (optional):",
        )
        self.notes_entry = ctk.CTkTextbox(
            self.input_frame,
            height=80,
            width=300,
        )

        # Preview section
        self.preview_frame = ctk.CTkFrame(self)

        self.preview_title = ctk.CTkLabel(
            self.preview_frame,
            text="Preview:",
            font=ctk.CTkFont(weight="bold"),
        )
        self.new_qty_label = ctk.CTkLabel(
            self.preview_frame,
            text="New Quantity: --",
        )
        self.cost_impact_label = ctk.CTkLabel(
            self.preview_frame,
            text="Cost Impact: --",
        )

        # Button frame
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")

        self.cancel_button = ctk.CTkButton(
            self.button_frame,
            text="Cancel",
            command=self._on_cancel,
            fg_color="gray",
        )
        self.apply_button = ctk.CTkButton(
            self.button_frame,
            text="Apply Adjustment",
            command=self._on_apply,
        )

    def _layout_widgets(self):
        """Layout all widgets."""
        # Info section
        self.info_frame.pack(fill="x", padx=20, pady=(20, 10))
        self.product_label.pack(anchor="w")
        self.date_label.pack(anchor="w")
        self.quantity_label.pack(anchor="w")
        self.cost_label.pack(anchor="w")

        # Input section
        self.input_frame.pack(fill="x", padx=20, pady=10)
        self.qty_label.pack(anchor="w")
        qty_row = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        qty_row.pack(fill="x", pady=5)
        self.qty_entry.pack(in_=qty_row, side="left")
        self.qty_unit_label.pack(in_=qty_row, side="left", padx=5)

        self.reason_label.pack(anchor="w", pady=(10, 0))
        self.reason_dropdown.pack(anchor="w", pady=5)

        self.notes_label.pack(anchor="w", pady=(10, 0))
        self.notes_entry.pack(fill="x", pady=5)

        # Preview section
        self.preview_frame.pack(fill="x", padx=20, pady=10)
        self.preview_title.pack(anchor="w")
        self.new_qty_label.pack(anchor="w")
        self.cost_impact_label.pack(anchor="w")

        # Buttons
        self.button_frame.pack(fill="x", padx=20, pady=20)
        self.cancel_button.pack(side="left", padx=5)
        self.apply_button.pack(side="right", padx=5)

    def _bind_events(self):
        """Bind event handlers."""
        # Live preview on key release
        self.qty_entry.bind("<KeyRelease>", self._update_preview)
        # Update notes requirement on reason change
        self.reason_dropdown.configure(command=self._on_reason_change)

    def _on_reason_change(self, _):
        """Handle reason dropdown change."""
        self._update_notes_requirement()

    def _update_notes_requirement(self):
        """Update notes label based on selected reason."""
        reason = self._get_selected_reason()
        if reason == DepletionReason.OTHER:
            self.notes_label.configure(text="Notes (required):")
        else:
            self.notes_label.configure(text="Notes (optional):")

    def _get_selected_reason(self) -> DepletionReason:
        """Get the DepletionReason enum from dropdown selection."""
        label = self.reason_var.get()
        for reason, lbl in self.REASON_LABELS.items():
            if lbl == label:
                return reason
        return DepletionReason.OTHER

    def _update_preview(self, event=None):
        """Update preview labels based on current input."""
        try:
            qty_text = self.qty_entry.get().strip()
            if not qty_text:
                self.new_qty_label.configure(
                    text="New Quantity: --",
                    text_color=("gray10", "gray90"),
                )
                self.cost_impact_label.configure(text="Cost Impact: --")
                return

            qty = Decimal(qty_text)
            if qty <= 0:
                self.new_qty_label.configure(
                    text="New Quantity: (enter positive value)",
                    text_color="orange",
                )
                self.cost_impact_label.configure(text="Cost Impact: --")
                return

            new_qty = self.current_quantity - qty
            cost_impact = qty * self.unit_cost

            if new_qty < 0:
                self.new_qty_label.configure(
                    text="New Quantity: ERROR (exceeds available)",
                    text_color="red",
                )
            else:
                self.new_qty_label.configure(
                    text=f"New Quantity: {new_qty} {self.unit}",
                    text_color=("gray10", "gray90"),
                )
            self.cost_impact_label.configure(
                text=f"Cost Impact: ${cost_impact:.2f}",
            )
        except InvalidOperation:
            self.new_qty_label.configure(
                text="New Quantity: (invalid input)",
                text_color="orange",
            )
            self.cost_impact_label.configure(text="Cost Impact: --")
        except ValueError:
            self.new_qty_label.configure(
                text="New Quantity: (invalid input)",
                text_color="orange",
            )
            self.cost_impact_label.configure(text="Cost Impact: --")

    def _on_cancel(self):
        """Handle cancel button click."""
        self.destroy()

    def _on_apply(self):
        """Handle apply button click."""
        # Validate and collect values
        try:
            qty_text = self.qty_entry.get().strip()
            if not qty_text:
                self._show_validation_error("Please enter an amount to reduce")
                return

            quantity = Decimal(qty_text)
            if quantity <= 0:
                self._show_validation_error("Amount must be greater than zero")
                return

            if quantity > self.current_quantity:
                self._show_validation_error(
                    f"Amount cannot exceed current quantity ({self.current_quantity} {self.unit})"
                )
                return

            reason = self._get_selected_reason()
            notes = self.notes_entry.get("1.0", "end-1c").strip() or None

            # Validate notes required for OTHER reason
            if reason == DepletionReason.OTHER and not notes:
                self._show_validation_error(
                    "Notes are required when selecting 'Other' as the reason"
                )
                return

            # Get inventory item ID
            if hasattr(self.inventory_item, "id"):
                inventory_item_id = self.inventory_item.id
            else:
                inventory_item_id = self.inventory_item.get("id")

            if self.on_apply:
                self.on_apply(
                    inventory_item_id=inventory_item_id,
                    quantity=quantity,
                    reason=reason,
                    notes=notes,
                )
            self.destroy()

        except (ValueError, InvalidOperation):
            self._show_validation_error("Please enter a valid number")

    def _show_validation_error(self, message: str):
        """Display a validation error in the preview area."""
        self.new_qty_label.configure(
            text=message,
            text_color="red",
        )

    def _center_on_parent(self, parent):
        """Center dialog on parent window."""
        parent.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_x(), parent.winfo_y()
        w, h = self.winfo_width(), self.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"+{x}+{y}")
