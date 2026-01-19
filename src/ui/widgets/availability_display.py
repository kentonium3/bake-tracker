"""
Availability display widget for showing ingredient/component availability.

Provides a color-coded display of availability check results with status indicators.
Used by production and assembly recording dialogs.
"""

import customtkinter as ctk
from typing import List, Dict, Any
from decimal import Decimal

from src.utils.constants import (
    COLOR_SUCCESS,
    COLOR_ERROR,
    PADDING_SMALL,
    PADDING_MEDIUM,
)


class AvailabilityDisplay(ctk.CTkFrame):
    """
    Reusable widget for displaying availability check results.

    Shows a list of items with color-coded status indicators:
    - Green checkmark for sufficient items
    - Red X for insufficient items with details on needed vs available
    """

    def __init__(self, parent, title: str = "Availability"):
        """
        Initialize the availability display.

        Args:
            parent: Parent widget
            title: Header title for the display
        """
        super().__init__(parent)

        self._items: List[Dict[str, Any]] = []
        self._is_sufficient = True
        self._item_widgets: List[ctk.CTkFrame] = []

        self._setup_ui(title)

    def _setup_ui(self, title: str):
        """Set up the widget UI."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header frame with title and overall status
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=PADDING_SMALL, pady=PADDING_SMALL)
        header_frame.grid_columnconfigure(0, weight=1)

        self._title_label = ctk.CTkLabel(
            header_frame,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        self._title_label.grid(row=0, column=0, sticky="w")

        self._status_label = ctk.CTkLabel(
            header_frame,
            text="",
            font=ctk.CTkFont(size=12),
            anchor="e",
        )
        self._status_label.grid(row=0, column=1, sticky="e", padx=PADDING_MEDIUM)

        # Scrollable frame for item list
        self._scrollable_frame = ctk.CTkScrollableFrame(self, height=150)
        self._scrollable_frame.grid(
            row=1, column=0, sticky="nsew", padx=PADDING_SMALL, pady=PADDING_SMALL
        )
        self._scrollable_frame.grid_columnconfigure(0, weight=1)

    def set_availability(self, result: Dict[str, Any]) -> None:
        """
        Set availability data from a check result.

        Handles both production (can_produce) and assembly (can_assemble) formats.

        Args:
            result: Availability check result dict with keys:
                - "can_produce" or "can_assemble" (bool)
                - "missing" (List[Dict]): List of insufficient items
        """
        self.clear()

        # Determine overall status (supports both production and assembly)
        can_proceed = result.get("can_produce", result.get("can_assemble", False))
        self._is_sufficient = can_proceed
        missing_items = result.get("missing", [])

        # Update status label
        if can_proceed:
            self._status_label.configure(
                text="All items available",
                text_color=COLOR_SUCCESS,
            )
        else:
            self._status_label.configure(
                text=f"{len(missing_items)} item(s) insufficient",
                text_color=COLOR_ERROR,
            )

        # If there are missing items, display them
        if missing_items:
            for idx, item in enumerate(missing_items):
                self._create_item_row(idx, item, is_sufficient=False)
        else:
            # Show a "ready" message
            ready_label = ctk.CTkLabel(
                self._scrollable_frame,
                text="All required items are available.",
                text_color=COLOR_SUCCESS,
                anchor="w",
            )
            ready_label.grid(row=0, column=0, sticky="ew", padx=PADDING_SMALL, pady=PADDING_SMALL)

    def _create_item_row(self, row_index: int, item: Dict[str, Any], is_sufficient: bool):
        """
        Create a row for an availability item.

        Args:
            row_index: Row index in the grid
            item: Item data dict
            is_sufficient: Whether the item has sufficient availability
        """
        row_frame = ctk.CTkFrame(self._scrollable_frame, fg_color="transparent")
        row_frame.grid(row=row_index, column=0, sticky="ew", pady=2)
        row_frame.grid_columnconfigure(1, weight=1)

        # Status icon
        icon = "\u2713" if is_sufficient else "\u2717"  # checkmark or X
        color = COLOR_SUCCESS if is_sufficient else COLOR_ERROR

        icon_label = ctk.CTkLabel(
            row_frame,
            text=icon,
            text_color=color,
            font=ctk.CTkFont(size=14, weight="bold"),
            width=20,
        )
        icon_label.grid(row=0, column=0, padx=(PADDING_SMALL, PADDING_MEDIUM))

        # Item name - handle different formats
        item_name = self._get_item_name(item)

        name_label = ctk.CTkLabel(
            row_frame,
            text=item_name,
            text_color=color,
            anchor="w",
        )
        name_label.grid(row=0, column=1, sticky="w")

        # Need vs Have display for insufficient items
        if not is_sufficient:
            needed = self._format_quantity(item.get("needed", 0))
            available = self._format_quantity(item.get("available", 0))
            unit = item.get("unit", "")

            if unit:
                detail_text = f"Need: {needed} {unit} | Have: {available} {unit}"
            else:
                detail_text = f"Need: {needed} | Have: {available}"

            detail_label = ctk.CTkLabel(
                row_frame,
                text=detail_text,
                text_color=color,
                font=ctk.CTkFont(size=11),
                anchor="e",
            )
            detail_label.grid(row=0, column=2, sticky="e", padx=PADDING_SMALL)

        self._item_widgets.append(row_frame)

    def _get_item_name(self, item: Dict[str, Any]) -> str:
        """
        Extract the item name from various data formats.

        Handles:
        - Production: "ingredient_name"
        - Assembly: "component_name" with "component_type"

        Args:
            item: Item data dict

        Returns:
            Display name for the item
        """
        # Production format
        if "ingredient_name" in item:
            return item["ingredient_name"]

        # Assembly format
        if "component_name" in item:
            component_type = item.get("component_type", "")
            name = item["component_name"]

            # Add type prefix for clarity
            type_prefixes = {
                "finished_unit": "[FU]",
                "finished_good": "[FG]",
                "packaging": "[Pkg]",
            }
            prefix = type_prefixes.get(component_type, "")
            return f"{prefix} {name}".strip()

        # Fallback
        return item.get("name", "Unknown item")

    def _format_quantity(self, value: Any) -> str:
        """
        Format a quantity value for display.

        Args:
            value: Quantity value (int, float, Decimal, or str)

        Returns:
            Formatted string
        """
        if isinstance(value, (int, float)):
            # Remove unnecessary decimals
            if value == int(value):
                return str(int(value))
            return f"{value:.2f}".rstrip("0").rstrip(".")
        elif isinstance(value, Decimal):
            # Handle Decimal
            if value == value.to_integral_value():
                return str(int(value))
            return f"{value:.2f}".rstrip("0").rstrip(".")
        else:
            # Assume string
            return str(value)

    def is_sufficient(self) -> bool:
        """
        Check if all items have sufficient availability.

        Returns:
            True if all items are available, False otherwise
        """
        return self._is_sufficient

    def clear(self) -> None:
        """Clear all displayed items."""
        for widget in self._item_widgets:
            widget.destroy()
        self._item_widgets = []

        # Also clear any direct children of the scrollable frame
        for child in self._scrollable_frame.winfo_children():
            child.destroy()

        self._is_sufficient = True
        self._status_label.configure(text="", text_color=("gray70", "gray30"))
