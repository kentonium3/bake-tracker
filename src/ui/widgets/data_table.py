"""
Data table widget for displaying tabular data.

Provides a scrollable table with column headers and row selection.
"""

import customtkinter as ctk
from typing import List, Tuple, Callable, Optional, Any


class DataTable(ctk.CTkFrame):
    """
    Reusable data table widget with scrolling and selection.

    Displays tabular data with column headers, supports row selection,
    and provides callbacks for row clicks and double-clicks.
    """

    def __init__(
        self,
        parent,
        columns: List[Tuple[str, int]],
        on_row_select: Optional[Callable[[Any], None]] = None,
        on_row_double_click: Optional[Callable[[Any], None]] = None,
    ):
        """
        Initialize the data table.

        Args:
            parent: Parent widget
            columns: List of (column_name, width) tuples
            on_row_select: Callback for row selection (receives row data)
            on_row_double_click: Callback for row double-click (receives row data)
        """
        super().__init__(parent)

        self.columns = columns
        self.on_row_select = on_row_select
        self.on_row_double_click = on_row_double_click
        self.data = []
        self.row_widgets = []
        self.selected_row = None

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Create header
        self._create_header()

        # Create scrollable frame for data
        self._create_data_frame()

    def _create_header(self):
        """Create the table header row."""
        header_frame = ctk.CTkFrame(self, fg_color=("gray85", "gray25"))
        header_frame.grid(row=0, column=0, sticky="ew")

        for i, (col_name, col_width) in enumerate(self.columns):
            header_label = ctk.CTkLabel(
                header_frame,
                text=col_name,
                width=col_width,
                font=ctk.CTkFont(weight="bold"),
            )
            header_label.grid(row=0, column=i, padx=5, pady=8, sticky="w")

    def _create_data_frame(self):
        """Create the scrollable frame for data rows."""
        # Create scrollable frame
        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.grid(row=1, column=0, sticky="nsew")

        # Configure columns
        for i, (_, col_width) in enumerate(self.columns):
            self.scrollable_frame.grid_columnconfigure(i, minsize=col_width)

    def set_data(self, data: List[Any]):
        """
        Set the table data and refresh the display.

        Args:
            data: List of data items to display
        """
        self.data = data
        self.selected_row = None
        self._refresh_rows()

    def _refresh_rows(self):
        """Refresh the data rows."""
        # Clear existing rows
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.row_widgets = []

        # Create new rows
        for row_index, row_data in enumerate(self.data):
            self._create_row(row_index, row_data)

    def _create_row(self, row_index: int, row_data: Any):
        """
        Create a data row.

        Args:
            row_index: Index of the row
            row_data: Data for the row
        """
        # Create frame for the row
        row_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        row_frame.grid(row=row_index, column=0, columnspan=len(self.columns), sticky="ew")

        # Store reference
        row_widgets_list = []

        # Get row values
        row_values = self._get_row_values(row_data)

        # Create cells
        for col_index, (col_value, (_, col_width)) in enumerate(zip(row_values, self.columns)):
            cell_label = ctk.CTkLabel(
                row_frame,
                text=str(col_value),
                width=col_width,
                anchor="w",
            )
            cell_label.grid(row=0, column=col_index, padx=5, pady=4, sticky="w")

            # Bind click events
            cell_label.bind("<Button-1>", lambda e, idx=row_index: self._on_row_click(idx))
            cell_label.bind(
                "<Double-Button-1>", lambda e, idx=row_index: self._on_row_double_click_event(idx)
            )

            row_widgets_list.append(cell_label)

        # Bind click event to row frame as well
        row_frame.bind("<Button-1>", lambda e, idx=row_index: self._on_row_click(idx))
        row_frame.bind(
            "<Double-Button-1>", lambda e, idx=row_index: self._on_row_double_click_event(idx)
        )

        self.row_widgets.append((row_frame, row_widgets_list))

    def _get_row_values(self, row_data: Any) -> List[str]:
        """
        Extract row values from data.

        Override this method in subclasses for custom data formatting.

        Args:
            row_data: Row data object

        Returns:
            List of string values for each column
        """
        # Default implementation: assume row_data is a dict or object
        values = []
        for col_name, _ in self.columns:
            if isinstance(row_data, dict):
                value = row_data.get(col_name, "")
            else:
                # Try to get attribute
                value = getattr(row_data, col_name.lower().replace(" ", "_"), "")
            values.append(value)
        return values

    def _on_row_click(self, row_index: int):
        """
        Handle row click event.

        Args:
            row_index: Index of clicked row
        """
        # Deselect previous row
        if self.selected_row is not None and self.selected_row < len(self.row_widgets):
            prev_frame, prev_widgets = self.row_widgets[self.selected_row]
            prev_frame.configure(fg_color="transparent")

        # Select new row
        self.selected_row = row_index
        if row_index < len(self.row_widgets):
            row_frame, row_widgets = self.row_widgets[row_index]
            row_frame.configure(fg_color=("gray75", "gray30"))

        # Call callback
        if self.on_row_select and row_index < len(self.data):
            self.on_row_select(self.data[row_index])

    def _on_row_double_click_event(self, row_index: int):
        """
        Handle row double-click event.

        Args:
            row_index: Index of double-clicked row
        """
        if self.on_row_double_click and row_index < len(self.data):
            self.on_row_double_click(self.data[row_index])

    def get_selected_row(self) -> Optional[Any]:
        """
        Get the currently selected row data.

        Returns:
            Selected row data, or None if no selection
        """
        if self.selected_row is not None and self.selected_row < len(self.data):
            return self.data[self.selected_row]
        return None

    def clear_selection(self):
        """Clear the current row selection."""
        if self.selected_row is not None and self.selected_row < len(self.row_widgets):
            row_frame, _ = self.row_widgets[self.selected_row]
            row_frame.configure(fg_color="transparent")
        self.selected_row = None

    def clear(self):
        """Clear all data from the table."""
        self.data = []
        self.selected_row = None
        self._refresh_rows()


class IngredientDataTable(DataTable):
    """
    Specialized data table for displaying ingredients.
    """

    def _get_row_values(self, row_data: Any) -> List[str]:
        """
        Extract ingredient-specific row values.

        Args:
            row_data: Ingredient object

        Returns:
            List of formatted values
        """
        return [
            row_data.name,
            row_data.brand or "",
            row_data.category,
            f"{row_data.quantity:.2f}",
            f"${row_data.unit_cost:.2f}",
            f"${row_data.total_value:.2f}",
        ]


class RecipeDataTable(DataTable):
    """
    Specialized data table for displaying recipes.
    """

    def _get_row_values(self, row_data: Any) -> List[str]:
        """
        Extract recipe-specific row values.

        Args:
            row_data: Recipe object

        Returns:
            List of formatted values
        """
        total_cost = row_data.calculate_cost() if hasattr(row_data, "calculate_cost") else 0.0
        cost_per_unit = (
            row_data.get_cost_per_unit() if hasattr(row_data, "get_cost_per_unit") else 0.0
        )

        return [
            row_data.name,
            row_data.category,
            f"{row_data.yield_quantity:.0f} {row_data.yield_unit}",
            f"${total_cost:.2f}",
            f"${cost_per_unit:.4f}",
        ]
