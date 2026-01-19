"""
Production history table widget for displaying production run history.

Subclass of DataTable specialized for production run data display.

Feature 025: Added Loss and Status columns with visual indicators for
production loss tracking.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional, Callable

from src.ui.widgets.data_table import DataTable


# Feature 025: Status display mapping with visual indicators
# Using text prefixes for accessibility (not color-only)
STATUS_DISPLAY = {
    "complete": ("Complete", "complete"),
    "partial_loss": ("! Partial Loss", "partial_loss"),
    "total_loss": ("!! Total Loss", "total_loss"),
}

# Feature 025: Color definitions for status styling
STATUS_COLORS = {
    "complete": "#28A745",  # Green - success
    "partial_loss": "#FFC107",  # Amber/orange - warning
    "total_loss": "#DC3545",  # Red - error
}


class ProductionHistoryTable(DataTable):
    """
    Specialized data table for displaying production run history.

    Columns: Date, Batches, Yield, Cost, Loss, Status

    Feature 025: Added Loss and Status columns with visual indicators
    to display production loss tracking information.
    """

    COLUMNS = [
        ("Date", 110),
        ("Batches", 70),
        ("Yield", 100),
        ("Cost", 90),
        ("Loss", 60),  # Feature 025: Loss quantity column
        ("Status", 110),  # Feature 025: Production status column
    ]

    def __init__(
        self,
        parent,
        on_row_select: Optional[Callable[[Any], None]] = None,
        on_row_double_click: Optional[Callable[[Any], None]] = None,
        height: int = 200,
    ):
        """
        Initialize production history table.

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

    def _create_row(self, row_index: int, row_data: Any):
        """
        Create a data row with status-based visual indicators.

        Feature 025: T028 - Override base class to apply color styling
        to the Status column based on production_status value.

        Args:
            row_index: Index of the row
            row_data: Data for the row (production run dict)
        """
        # Call base class to create the row
        super()._create_row(row_index, row_data)

        # Apply status-based color styling to the Status column (last column, index 5)
        if row_index < len(self.row_widgets):
            _, row_widgets_list = self.row_widgets[row_index]

            # Get status from row data
            if isinstance(row_data, dict):
                production_status = row_data.get("production_status", "complete")
            else:
                production_status = getattr(row_data, "production_status", "complete")

            # Apply color to Status column (index 5)
            status_column_index = 5
            if status_column_index < len(row_widgets_list):
                status_color = self._get_status_color(production_status)
                status_label = row_widgets_list[status_column_index]
                status_label.configure(text_color=status_color)

    def _get_row_values(self, row_data: Any) -> List[str]:
        """
        Extract production run-specific row values.

        Args:
            row_data: Production run dict from get_production_history()

        Returns:
            List of formatted values for each column

        Feature 025: Added Loss and Status columns.
        """
        # Handle dict format from service
        if isinstance(row_data, dict):
            return [
                self._format_date(row_data.get("produced_at")),
                str(row_data.get("num_batches", 0)),
                self._format_yield(
                    row_data.get("actual_yield", 0),
                    row_data.get("expected_yield", 0),
                ),
                self._format_currency(row_data.get("total_ingredient_cost", "0")),
                # Feature 025: Loss column
                self._format_loss(row_data.get("loss_quantity", 0)),
                # Feature 025: Status column
                self._format_status(row_data.get("production_status", "complete")),
            ]

        # Handle object format (fallback)
        return [
            self._format_date(getattr(row_data, "produced_at", None)),
            str(getattr(row_data, "num_batches", 0)),
            self._format_yield(
                getattr(row_data, "actual_yield", 0),
                getattr(row_data, "expected_yield", 0),
            ),
            self._format_currency(getattr(row_data, "total_ingredient_cost", "0")),
            # Feature 025: Loss column
            self._format_loss(getattr(row_data, "loss_quantity", 0)),
            # Feature 025: Status column
            self._format_status(getattr(row_data, "production_status", "complete")),
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

    def _format_yield(self, actual: Any, expected: Any) -> str:
        """
        Format yield as "actual / expected".

        Args:
            actual: Actual yield value
            expected: Expected yield value

        Returns:
            Formatted string like "24 / 24"
        """
        actual_val = int(actual) if actual else 0
        expected_val = int(expected) if expected else 0
        return f"{actual_val} / {expected_val}"

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

    # =========================================================================
    # Feature 025: Loss tracking formatting methods
    # =========================================================================

    def _format_loss(self, loss_quantity: Any) -> str:
        """
        Format loss quantity for display.

        Feature 025: T026, T029 - Shows loss quantity or "-" for no loss.

        Args:
            loss_quantity: Loss quantity value (int, float, or None)

        Returns:
            Formatted string: number if > 0, "-" otherwise
        """
        try:
            qty = int(loss_quantity) if loss_quantity else 0
            return str(qty) if qty > 0 else "-"
        except (ValueError, TypeError):
            return "-"

    def _format_status(self, production_status: Any) -> str:
        """
        Format production status for display.

        Feature 025: T027 - Shows human-readable status with accessibility prefix.

        Args:
            production_status: Status value (string enum: complete, partial_loss, total_loss)

        Returns:
            Formatted display string with accessibility prefix
        """
        if not production_status:
            return "Complete"

        status_key = str(production_status).lower()
        display_text, _ = STATUS_DISPLAY.get(status_key, ("Unknown", "unknown"))
        return display_text

    def _get_status_color(self, production_status: Any) -> str:
        """
        Get the color for a production status.

        Feature 025: T028 - Returns color code for visual indicators.

        Args:
            production_status: Status value (string enum)

        Returns:
            Hex color code for the status
        """
        if not production_status:
            return STATUS_COLORS["complete"]

        status_key = str(production_status).lower()
        return STATUS_COLORS.get(status_key, STATUS_COLORS["complete"])
