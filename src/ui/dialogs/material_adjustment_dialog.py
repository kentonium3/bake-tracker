"""Material Adjustment Dialog - Manual inventory adjustments for materials.

Provides a modal dialog for adjusting material inventory quantities with:
- "each" materials: Add/Subtract/Set operations with direct quantity input
- "variable" materials (linear_cm, square_cm): Percentage input for "what percentage remains"
- Live preview with color coding (green for increase, red for decrease)
- Notes field for audit trail

Part of Feature 059: Materials Purchase Integration & Workflows.
"""

import customtkinter as ctk
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional, Dict, Any, Callable, Tuple

from src.services.exceptions import ServiceError
from src.ui.utils.error_handler import handle_error


class MaterialAdjustmentDialog(ctk.CTkToplevel):
    """Dialog for adjusting material inventory quantities.

    Supports two adjustment modes based on material type:
    - "each" materials: Add/Subtract/Set operations
    - "variable" materials (linear_cm, square_cm): Percentage-based adjustment

    Args:
        parent: Parent window
        inventory_item: Dict with inventory item data including:
            - id: Item ID
            - product_name: Display name
            - quantity_remaining: Current quantity
            - base_unit_type: "each", "linear_cm", or "square_cm"
        on_save: Callback when adjustment is saved
    """

    def __init__(
        self,
        parent,
        inventory_item: Dict[str, Any],
        on_save: Optional[Callable] = None,
    ):
        """Initialize the adjustment dialog."""
        super().__init__(parent)

        self._inventory_item = inventory_item
        self._on_save = on_save
        self._result = None

        # Store values for calculations
        self._current_qty = Decimal(str(inventory_item.get("quantity_remaining", 0)))
        self._base_unit_type = inventory_item.get("base_unit_type", "each")

        self._setup_window()
        self._create_widgets()
        self._setup_modal()

    def _setup_window(self) -> None:
        """Configure window properties."""
        self.title("Adjust Inventory")
        self.geometry("400x380")
        self.resizable(False, False)

        # Center on parent
        self.update_idletasks()
        parent_x = self.master.winfo_rootx()
        parent_y = self.master.winfo_rooty()
        parent_w = self.master.winfo_width()
        parent_h = self.master.winfo_height()

        x = parent_x + (parent_w - 400) // 2
        y = parent_y + (parent_h - 380) // 2
        self.geometry(f"+{x}+{y}")

    def _setup_modal(self) -> None:
        """Set up modal behavior (CRITICAL ORDER)."""
        self.transient(self.master)
        self.grab_set()
        self.wait_visibility()
        self.focus_force()

    def _create_widgets(self) -> None:
        """Create all dialog widgets."""
        # Header with item info
        self._create_header()

        # Adjustment controls (type-specific)
        if self._base_unit_type == "each":
            self._create_each_controls()
        else:
            self._create_variable_controls()

        # Preview section
        self._create_preview()

        # Notes field
        self._create_notes()

        # Action buttons
        self._create_buttons()

        # Initial preview update
        self._update_preview()

    def _create_header(self) -> None:
        """Create header with item info."""
        header_frame = ctk.CTkFrame(self)
        header_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            header_frame,
            text=self._inventory_item.get("product_name", "Unknown Product"),
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            header_frame,
            text=f"Item ID: {self._inventory_item.get('id')}",
            text_color="gray",
        ).pack(anchor="w")

    def _create_each_controls(self) -> None:
        """Create controls for 'each' material adjustments."""
        self._controls_frame = ctk.CTkFrame(self)
        self._controls_frame.pack(fill="x", padx=20, pady=10)

        # Adjustment type selection
        ctk.CTkLabel(
            self._controls_frame,
            text="Adjustment Type:",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w")

        self._adjustment_type_var = ctk.StringVar(value="add")

        types_frame = ctk.CTkFrame(self._controls_frame, fg_color="transparent")
        types_frame.pack(fill="x", pady=5)

        for value, label in [("add", "Add"), ("subtract", "Subtract"), ("set", "Set To")]:
            ctk.CTkRadioButton(
                types_frame,
                text=label,
                variable=self._adjustment_type_var,
                value=value,
                command=self._update_preview,
            ).pack(side="left", padx=10)

        # Quantity input
        ctk.CTkLabel(
            self._controls_frame,
            text="Quantity:",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w", pady=(10, 0))

        self._quantity_var = ctk.StringVar(value="0")
        self._quantity_var.trace_add("write", lambda *args: self._update_preview())

        self._quantity_entry = ctk.CTkEntry(
            self._controls_frame,
            textvariable=self._quantity_var,
            width=100,
        )
        self._quantity_entry.pack(anchor="w", pady=5)

        # Unit label
        ctk.CTkLabel(
            self._controls_frame,
            text=f"(in {self._base_unit_type})",
            text_color="gray",
        ).pack(anchor="w")

    def _create_variable_controls(self) -> None:
        """Create controls for 'variable' material adjustments (percentage)."""
        self._controls_frame = ctk.CTkFrame(self)
        self._controls_frame.pack(fill="x", padx=20, pady=10)

        # Explanation
        unit_label = "cm" if self._base_unit_type == "linear_cm" else "cm\u00b2"
        ctk.CTkLabel(
            self._controls_frame,
            text=f"Current: {self._current_qty:.2f} {unit_label}",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            self._controls_frame,
            text="Enter percentage remaining (0-100):",
            text_color="gray",
        ).pack(anchor="w", pady=(5, 0))

        # Percentage input
        percentage_frame = ctk.CTkFrame(self._controls_frame, fg_color="transparent")
        percentage_frame.pack(fill="x", pady=10)

        self._percentage_var = ctk.StringVar(value="100")
        self._percentage_var.trace_add("write", lambda *args: self._update_preview())

        self._percentage_entry = ctk.CTkEntry(
            percentage_frame,
            textvariable=self._percentage_var,
            width=80,
        )
        self._percentage_entry.pack(side="left")

        ctk.CTkLabel(percentage_frame, text="%").pack(side="left", padx=5)

        # Quick preset buttons
        presets_frame = ctk.CTkFrame(self._controls_frame, fg_color="transparent")
        presets_frame.pack(fill="x", pady=5)

        for pct in [100, 75, 50, 25, 0]:
            ctk.CTkButton(
                presets_frame,
                text=f"{pct}%",
                width=50,
                command=lambda p=pct: self._set_percentage(p),
            ).pack(side="left", padx=2)

    def _set_percentage(self, pct: int) -> None:
        """Set percentage to a preset value."""
        self._percentage_var.set(str(pct))

    def _create_preview(self) -> None:
        """Create the preview display section."""
        self._preview_frame = ctk.CTkFrame(self)
        self._preview_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            self._preview_frame,
            text="Preview:",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w")

        # Current -> New display
        self._preview_label = ctk.CTkLabel(
            self._preview_frame,
            text="",
            font=ctk.CTkFont(size=14),
        )
        self._preview_label.pack(anchor="w", pady=5)

        # Warning label (for invalid adjustments)
        self._warning_label = ctk.CTkLabel(
            self._preview_frame,
            text="",
            text_color="red",
        )
        self._warning_label.pack(anchor="w")

    def _create_notes(self) -> None:
        """Create the notes input field."""
        notes_frame = ctk.CTkFrame(self)
        notes_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            notes_frame,
            text="Reason (optional):",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w")

        self._notes_var = ctk.StringVar()
        self._notes_entry = ctk.CTkEntry(
            notes_frame,
            textvariable=self._notes_var,
            placeholder_text="e.g., Physical inventory count, damaged goods...",
            width=350,
        )
        self._notes_entry.pack(fill="x", pady=5)

    def _create_buttons(self) -> None:
        """Create Save and Cancel buttons."""
        buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=20, pady=20)

        self._cancel_btn = ctk.CTkButton(
            buttons_frame,
            text="Cancel",
            command=self._on_cancel,
            fg_color="gray",
        )
        self._cancel_btn.pack(side="right", padx=5)

        self._save_btn = ctk.CTkButton(
            buttons_frame,
            text="Save Adjustment",
            command=self._on_save_click,
        )
        self._save_btn.pack(side="right", padx=5)

    def _calculate_each_adjustment(self) -> Optional[Decimal]:
        """Calculate new quantity for 'each' adjustment."""
        try:
            value = Decimal(self._quantity_var.get() or "0")
        except (InvalidOperation, ValueError):
            return None

        adj_type = self._adjustment_type_var.get()

        if adj_type == "add":
            return self._current_qty + value
        elif adj_type == "subtract":
            return self._current_qty - value
        elif adj_type == "set":
            return value
        return None

    def _calculate_variable_adjustment(self) -> Optional[Decimal]:
        """Calculate new quantity for percentage adjustment."""
        try:
            pct = Decimal(self._percentage_var.get() or "0")
        except (InvalidOperation, ValueError):
            return None

        if pct < 0 or pct > 100:
            return None

        new_qty = (self._current_qty * pct) / Decimal("100")
        return new_qty.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _update_preview(self) -> None:
        """Update the preview display based on current inputs."""
        if self._base_unit_type == "each":
            new_qty = self._calculate_each_adjustment()
        else:
            new_qty = self._calculate_variable_adjustment()

        unit = self._base_unit_type
        if unit == "linear_cm":
            unit = "cm"
        elif unit == "square_cm":
            unit = "cm\u00b2"

        if new_qty is None:
            self._preview_label.configure(
                text=f"{self._current_qty:.2f} \u2192 ???",
                text_color="gray",
            )
            self._warning_label.configure(text="Invalid input")
            self._save_btn.configure(state="disabled")
            return

        # Determine color based on change
        if new_qty < 0:
            color = "red"
            self._warning_label.configure(text="Cannot result in negative quantity!")
            self._save_btn.configure(state="disabled")
        elif new_qty < self._current_qty:
            color = "red"  # Decrease
            self._warning_label.configure(text="")
            self._save_btn.configure(state="normal")
        elif new_qty > self._current_qty:
            color = "green"  # Increase
            self._warning_label.configure(text="")
            self._save_btn.configure(state="normal")
        else:
            color = "gray"  # No change
            self._warning_label.configure(text="")
            self._save_btn.configure(state="normal")

        self._preview_label.configure(
            text=f"{self._current_qty:.2f} {unit} \u2192 {new_qty:.2f} {unit}",
            text_color=color,
        )

    def _validate_inputs(self) -> Tuple[bool, str]:
        """Validate all inputs before saving.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if self._base_unit_type == "each":
            # Validate quantity is a valid number
            try:
                value = Decimal(self._quantity_var.get() or "0")
                if value < 0:
                    return False, "Quantity cannot be negative"
            except (InvalidOperation, ValueError):
                return False, "Invalid quantity value"

            # Validate result won't be negative
            new_qty = self._calculate_each_adjustment()
            if new_qty is None:
                return False, "Unable to calculate new quantity"
            if new_qty < 0:
                return False, f"Adjustment would result in negative quantity ({new_qty})"

        else:
            # Validate percentage
            try:
                pct = Decimal(self._percentage_var.get() or "0")
                if pct < 0 or pct > 100:
                    return False, "Percentage must be between 0 and 100"
            except (InvalidOperation, ValueError):
                return False, "Invalid percentage value"

        return True, ""

    def _on_save_click(self) -> None:
        """Handle save button click."""
        # Validate first
        is_valid, error = self._validate_inputs()
        if not is_valid:
            self._warning_label.configure(text=error)
            return

        from src.services.material_inventory_service import adjust_inventory

        item_id = self._inventory_item["id"]
        notes = self._notes_var.get().strip() or None

        try:
            if self._base_unit_type == "each":
                # Determine adjustment type and value
                adj_type = self._adjustment_type_var.get()
                value = Decimal(self._quantity_var.get() or "0")

                result = adjust_inventory(
                    inventory_item_id=item_id,
                    adjustment_type=adj_type,
                    value=value,
                    notes=notes,
                )
            else:
                # Variable material - percentage
                percentage = Decimal(self._percentage_var.get() or "100")

                result = adjust_inventory(
                    inventory_item_id=item_id,
                    adjustment_type="percentage",
                    value=percentage,
                    notes=notes,
                )

            self._result = result

            # Call callback if provided
            if self._on_save:
                self._on_save(result)

            self.destroy()

        except ServiceError as e:
            handle_error(e, parent=self, operation="Adjust inventory")
        except Exception as e:
            handle_error(e, parent=self, operation="Adjust inventory")

    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        self._result = None
        self.destroy()

    def wait_for_result(self) -> Optional[Dict[str, Any]]:
        """Block until dialog closes and return result."""
        self.wait_window()
        return self._result
