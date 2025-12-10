"""
Assembly history table widget for displaying assembly run history.

Subclass of DataTable specialized for assembly run data display.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional, Callable

from src.ui.widgets.data_table import DataTable


class AssemblyHistoryTable(DataTable):
    """
    Specialized data table for displaying assembly run history.

    Columns: Date, Quantity, Cost
    """

    COLUMNS = [
        ("Date", 110),
        ("Quantity", 80),
        ("Cost", 90),
    ]

    def __init__(
        self,
        parent,
        on_row_select: Optional[Callable[[Any], None]] = None,
        on_row_double_click: Optional[Callable[[Any], None]] = None,
        height: int = 200,
    ):
        """
        Initialize assembly history table.

        Args:
            parent: Parent widget
            on_row_select: Callback for row selection
            on_row_double_click: Callback for row double-click
            height: Height of the table in pixels (default: 200)
        """
        super().__init__(
            parent,
            columns=self.COLUMNS,
            on_row_select=on_row_select,
            on_row_double_click=on_row_double_click,
            height=height,
        )

    def _get_row_values(self, row_data: Any) -> List[str]:
        """
        Extract assembly run-specific row values.

        Args:
            row_data: Assembly run dict from get_assembly_history()

        Returns:
            List of formatted values for each column
        """
        # Handle dict format from service
        if isinstance(row_data, dict):
            return [
                self._format_date(row_data.get("assembled_at")),
                str(row_data.get("quantity_assembled", 0)),
                self._format_currency(row_data.get("total_component_cost", "0")),
            ]

        # Handle object format (fallback)
        return [
            self._format_date(getattr(row_data, "assembled_at", None)),
            str(getattr(row_data, "quantity_assembled", 0)),
            self._format_currency(getattr(row_data, "total_component_cost", "0")),
        ]

    def _format_date(self, date_value: Any) -> str:
        """
        Format a date value for display.

        Args:
            date_value: ISO date string, datetime object, or None

        Returns:
            Formatted date string like "Dec 10, 2025"
        """
        if not date_value:
            return ""

        try:
            # Handle ISO string format from service
            if isinstance(date_value, str):
                # Parse ISO format: 2025-12-10T14:30:00
                dt = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
            elif isinstance(date_value, datetime):
                dt = date_value
            else:
                return str(date_value)

            return dt.strftime("%b %d, %Y")

        except (ValueError, AttributeError):
            return str(date_value) if date_value else ""

    def _format_currency(self, amount: Any) -> str:
        """
        Format a currency amount.

        Args:
            amount: Amount value (str, Decimal, float, or int)

        Returns:
            Formatted string like "$15.50"
        """
        try:
            if isinstance(amount, str):
                value = Decimal(amount)
            elif isinstance(amount, (int, float)):
                value = Decimal(str(amount))
            elif isinstance(amount, Decimal):
                value = amount
            else:
                return "$0.00"

            return f"${value:.2f}"

        except (ValueError, TypeError):
            return "$0.00"
