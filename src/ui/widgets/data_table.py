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
        height: int = 500,
    ):
        """
        Initialize the data table.

        Args:
            parent: Parent widget
            columns: List of (column_name, width) tuples
            on_row_select: Callback for row selection (receives row data)
            on_row_double_click: Callback for row double-click (receives row data)
            height: Height of the scrollable data area in pixels (default: 500)
        """
        super().__init__(parent)

        self.columns = columns
        self.on_row_select = on_row_select
        self.on_row_double_click = on_row_double_click
        self.data = []
        self.row_widgets = []
        self.selected_row = None
        self.table_height = height

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
                anchor="w",  # Left-justify header text to match data
            )
            header_label.grid(row=0, column=i, padx=5, pady=8, sticky="w")

    def _create_data_frame(self):
        """Create the scrollable frame for data rows."""
        # Create scrollable frame with specified height
        self.scrollable_frame = ctk.CTkScrollableFrame(self, height=self.table_height)
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
        row_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent", height=25)
        row_frame.grid(row=row_index, column=0, columnspan=len(self.columns), sticky="ew", pady=0)

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
                height=20,  # Fixed compact height
                anchor="w",
            )
            cell_label.grid(
                row=0, column=col_index, padx=5, pady=0, sticky="w"
            )  # Zero padding for compact spacing

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

    def __init__(
        self,
        parent,
        select_callback: Optional[Callable[[Any], None]] = None,
        double_click_callback: Optional[Callable[[Any], None]] = None,
        height: int = 500,
    ):
        """
        Initialize ingredient data table.

        Args:
            parent: Parent widget
            select_callback: Callback for row selection
            double_click_callback: Callback for row double-click
            height: Height of the table in pixels (default: 500)
        """
        columns = [
            ("Name", 180),
            ("Brand", 140),
            ("Category", 110),
            ("Quantity", 200),
            ("Unit Cost", 100),
            ("Total Value", 120),
        ]
        super().__init__(
            parent,
            columns=columns,
            on_row_select=select_callback,
            on_row_double_click=double_click_callback,
            height=height,
        )

    def _get_row_values(self, row_data: Any) -> List[str]:
        """
        Extract ingredient-specific row values.

        Args:
            row_data: Ingredient object

        Returns:
            List of formatted values
        """
        # Format quantity with package information
        total_qty = row_data.total_quantity_in_package_units

        if row_data.package_type:
            # Use package type if available
            package_label = self._pluralize(row_data.package_type, row_data.quantity)
            quantity_display = f"{row_data.quantity:.1f} {package_label} ({total_qty:.1f} {row_data.package_unit})"
        else:
            # Use generic "packages" if no package type
            package_label = "package" if row_data.quantity == 1 else "packages"
            quantity_display = f"{row_data.quantity:.1f} {package_label} ({total_qty:.1f} {row_data.package_unit})"

        return [
            row_data.name,
            row_data.brand or "",
            row_data.category,
            quantity_display,
            f"${row_data.unit_cost:.2f}",
            f"${row_data.total_value:.2f}",
        ]

    def _pluralize(self, word: str, count: float) -> str:
        """
        Simple pluralization helper.

        Args:
            word: Singular word
            count: Count to determine singular/plural

        Returns:
            Pluralized word
        """
        if count == 1:
            return word

        # Handle common irregular plurals
        irregular = {
            "box": "boxes",
            "can": "cans",
            "jar": "jars",
            "bag": "bags",
            "bottle": "bottles",
            "bar": "bars",
            "package": "packages",
        }

        word_lower = word.lower()
        if word_lower in irregular:
            return irregular[word_lower]

        # Default: add 's'
        return f"{word}s"


class RecipeDataTable(DataTable):
    """
    Specialized data table for displaying recipes.
    """

    def __init__(
        self,
        parent,
        select_callback: Optional[Callable[[Any], None]] = None,
        double_click_callback: Optional[Callable[[Any], None]] = None,
        height: int = 500,
    ):
        """
        Initialize recipe data table.

        Args:
            parent: Parent widget
            select_callback: Callback for row selection
            double_click_callback: Callback for row double-click
            height: Height of the table in pixels (default: 500)
        """
        # Feature 045: Cost columns removed (costs tracked on instances, not definitions)
        columns = [
            ("Name", 250),
            ("Category", 120),
            ("Yield", 150),
        ]
        super().__init__(
            parent,
            columns=columns,
            on_row_select=select_callback,
            on_row_double_click=double_click_callback,
            height=height,
        )

    def _get_row_values(self, row_data: Any) -> List[str]:
        """
        Extract recipe-specific row values.

        Args:
            row_data: Recipe object

        Returns:
            List of formatted values
        """
        # Feature 045: Cost columns removed (costs tracked on instances, not definitions)
        return [
            row_data.name,
            row_data.category,
            f"{row_data.yield_quantity:.0f} {row_data.yield_unit}",
        ]


class FinishedGoodDataTable(DataTable):
    """
    Specialized data table for displaying finished goods.
    """

    def __init__(
        self,
        parent,
        select_callback: Optional[Callable[[Any], None]] = None,
        double_click_callback: Optional[Callable[[Any], None]] = None,
        height: int = 500,
    ):
        """
        Initialize finished good data table.

        Args:
            parent: Parent widget
            select_callback: Callback for row selection
            double_click_callback: Callback for row double-click
            height: Height of the table in pixels (default: 500)
        """
        # Feature 045: Cost columns removed (costs tracked on instances, not definitions)
        columns = [
            ("Name", 280),
            ("Recipe", 220),
            ("Category", 120),
            ("Type", 100),
            ("Yield Info", 180),
        ]
        super().__init__(
            parent,
            columns=columns,
            on_row_select=select_callback,
            on_row_double_click=double_click_callback,
            height=height,
        )

    def _get_row_values(self, row_data: Any) -> List[str]:
        """
        Extract finished good-specific row values.

        Args:
            row_data: FinishedGood object

        Returns:
            List of formatted values
        """
        # Get yield info based on mode
        if row_data.yield_mode.value == "discrete_count":
            yield_info = f"{row_data.items_per_batch} {row_data.item_unit}/batch"
            type_display = "Discrete Items"
        else:
            yield_info = f"{row_data.batch_percentage}% of batch"
            type_display = "Batch Portion"

        # Feature 045: Cost columns removed (costs tracked on instances, not definitions)
        return [
            row_data.display_name,
            row_data.recipe.name if row_data.recipe else "N/A",
            row_data.category or "",
            type_display,
            yield_info,
        ]


class BundleDataTable(DataTable):
    """
    Specialized data table for displaying bundles.
    """

    def __init__(
        self,
        parent,
        select_callback: Optional[Callable[[Any], None]] = None,
        double_click_callback: Optional[Callable[[Any], None]] = None,
        height: int = 500,
    ):
        """
        Initialize bundle data table.

        Args:
            parent: Parent widget
            select_callback: Callback for row selection
            double_click_callback: Callback for row double-click
            height: Height of the table in pixels (default: 500)
        """
        columns = [
            ("Bundle Name", 250),
            ("Finished Good", 220),
            ("Quantity", 100),
            ("Cost", 100),
        ]
        super().__init__(
            parent,
            columns=columns,
            on_row_select=select_callback,
            on_row_double_click=double_click_callback,
            height=height,
        )

    def _get_row_values(self, row_data: Any) -> List[str]:
        """
        Extract bundle-specific row values.

        Args:
            row_data: Bundle object

        Returns:
            List of formatted values
        """
        # Calculate bundle cost
        cost = row_data.calculate_cost() if hasattr(row_data, "calculate_cost") else 0.0

        # Format quantity with unit from finished good
        if row_data.finished_good:
            if row_data.finished_good.yield_mode.value == "discrete_count":
                quantity_display = f"{row_data.quantity} {row_data.finished_good.item_unit}"
            else:
                quantity_display = f"{row_data.quantity} item(s)"
        else:
            quantity_display = str(row_data.quantity)

        return [
            row_data.display_name,
            row_data.finished_good.display_name if row_data.finished_good else "N/A",
            quantity_display,
            f"${cost:.2f}",
        ]


class PackageDataTable(DataTable):
    """
    Specialized data table for displaying packages.

    Updated for Feature 006: Uses FinishedGoods instead of Bundles.
    """

    def __init__(
        self,
        parent,
        select_callback: Optional[Callable[[Any], None]] = None,
        double_click_callback: Optional[Callable[[Any], None]] = None,
        height: int = 500,
    ):
        """
        Initialize package data table.

        Args:
            parent: Parent widget
            select_callback: Callback for row selection
            double_click_callback: Callback for row double-click
            height: Height of the table in pixels (default: 500)
        """
        columns = [
            ("Package Name", 250),
            ("Items", 80),
            ("Template", 80),
            ("Cost", 100),
        ]
        super().__init__(
            parent,
            columns=columns,
            on_row_select=select_callback,
            on_row_double_click=double_click_callback,
            height=height,
        )

    def _get_row_values(self, row_data: Any) -> List[str]:
        """
        Extract package-specific row values.

        Args:
            row_data: Package object

        Returns:
            List of formatted values
        """
        # Calculate package cost
        cost = row_data.calculate_cost() if hasattr(row_data, "calculate_cost") else 0.0

        # Item count (FinishedGoods in package)
        item_count = row_data.get_item_count() if hasattr(row_data, "get_item_count") else 0

        # Template flag
        template_display = "Yes" if row_data.is_template else "No"

        return [
            row_data.name,
            str(item_count),
            template_display,
            f"${cost:.2f}",
        ]


class RecipientDataTable(DataTable):
    """
    Specialized data table for displaying recipients.
    """

    def __init__(
        self,
        parent,
        select_callback: Optional[Callable[[Any], None]] = None,
        double_click_callback: Optional[Callable[[Any], None]] = None,
        height: int = 500,
    ):
        """
        Initialize recipient data table.

        Args:
            parent: Parent widget
            select_callback: Callback for row selection
            double_click_callback: Callback for row double-click
            height: Height of the table in pixels (default: 500)
        """
        columns = [
            ("Name", 220),
            ("Household", 220),
            ("Address", 300),
        ]
        super().__init__(
            parent,
            columns=columns,
            on_row_select=select_callback,
            on_row_double_click=double_click_callback,
            height=height,
        )

    def _get_row_values(self, row_data: Any) -> List[str]:
        """
        Extract recipient-specific row values.

        Args:
            row_data: Recipient object

        Returns:
            List of formatted values
        """
        return [
            row_data.name,
            row_data.household_name or "",
            row_data.address or "",
        ]


class EventDataTable(DataTable):
    """
    Specialized data table for displaying events.
    """

    def __init__(
        self,
        parent,
        select_callback: Optional[Callable[[Any], None]] = None,
        double_click_callback: Optional[Callable[[Any], None]] = None,
        height: int = 500,
    ):
        """
        Initialize event data table.

        Args:
            parent: Parent widget
            select_callback: Callback for row selection
            double_click_callback: Callback for row double-click
            height: Height of the table in pixels (default: 500)
        """
        columns = [
            ("Event Name", 300),
            ("Date", 100),
            ("Year", 60),
            ("Recipients", 80),
            ("Packages", 80),
            ("Cost", 100),
        ]
        super().__init__(
            parent,
            columns=columns,
            on_row_select=select_callback,
            on_row_double_click=double_click_callback,
            height=height,
        )

    def _get_row_values(self, row_data: Any) -> List[str]:
        """
        Extract event-specific row values.

        Args:
            row_data: Event object

        Returns:
            List of formatted values
        """
        # Format date
        event_date = row_data.event_date.strftime("%m/%d/%Y") if row_data.event_date else ""

        # Get counts
        recipient_count = (
            row_data.get_recipient_count() if hasattr(row_data, "get_recipient_count") else 0
        )
        package_count = (
            row_data.get_package_count() if hasattr(row_data, "get_package_count") else 0
        )

        # Calculate cost
        cost = row_data.get_total_cost() if hasattr(row_data, "get_total_cost") else 0.0

        return [
            row_data.name,
            event_date,
            str(row_data.year),
            str(recipient_count),
            str(package_count),
            f"${cost:.2f}",
        ]
