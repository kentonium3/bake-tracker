"""ShopView - Shopping phase UI for Planning Workspace.

Displays shopping list with Need/Have/Buy columns.

Implements User Story 2: Shop phase shows Need/Have/Buy columns.
"""

from decimal import Decimal
from typing import Any, Optional
import customtkinter as ctk

from src.services.planning import (
    get_shopping_list,
    mark_shopping_complete,
    is_shopping_complete,
    ShoppingListItem,
)


class ShoppingListRow(ctk.CTkFrame):
    """Single row in the shopping list table."""

    def __init__(
        self,
        parent: Any,
        item: ShoppingListItem,
        **kwargs
    ):
        """Initialize ShoppingListRow.

        Args:
            parent: Parent widget
            item: Shopping list item data
            **kwargs: Additional arguments passed to CTkFrame
        """
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)

        # Configure grid columns
        self.grid_columnconfigure(0, weight=2)  # Ingredient name
        self.grid_columnconfigure(1, weight=1)  # Need
        self.grid_columnconfigure(2, weight=1)  # Have
        self.grid_columnconfigure(3, weight=1)  # Buy

        # Ingredient name
        name_label = ctk.CTkLabel(
            self,
            text=item.ingredient_name,
            anchor="w",
        )
        name_label.grid(row=0, column=0, sticky="ew", padx=5, pady=3)

        # Format quantity with unit
        def format_qty(qty: Decimal, unit: str) -> str:
            # Show whole numbers without decimals
            if qty == int(qty):
                return f"{int(qty)} {unit}"
            return f"{qty:.2f} {unit}"

        # Need column
        need_label = ctk.CTkLabel(
            self,
            text=format_qty(item.needed, item.unit),
            anchor="e",
        )
        need_label.grid(row=0, column=1, sticky="ew", padx=5, pady=3)

        # Have column
        have_label = ctk.CTkLabel(
            self,
            text=format_qty(item.in_stock, item.unit),
            anchor="e",
        )
        have_label.grid(row=0, column=2, sticky="ew", padx=5, pady=3)

        # Buy column with color coding
        buy_color = ("#00AA00", "#00CC00") if item.is_sufficient else ("#CC0000", "#FF3333")
        buy_label = ctk.CTkLabel(
            self,
            text=format_qty(item.to_buy, item.unit),
            anchor="e",
            text_color=buy_color,
        )
        buy_label.grid(row=0, column=3, sticky="ew", padx=5, pady=3)


class TableHeader(ctk.CTkFrame):
    """Header row for the shopping list table."""

    def __init__(self, parent: Any, **kwargs):
        """Initialize TableHeader."""
        kwargs.setdefault("fg_color", ("gray80", "gray30"))
        super().__init__(parent, **kwargs)

        # Configure grid columns (match ShoppingListRow)
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=1)

        headers = ["Ingredient", "Need", "Have", "Buy"]
        for i, header in enumerate(headers):
            label = ctk.CTkLabel(
                self,
                text=header,
                font=ctk.CTkFont(weight="bold"),
                anchor="w" if i == 0 else "e",
            )
            label.grid(row=0, column=i, sticky="ew", padx=5, pady=5)


class ShopView(ctk.CTkFrame):
    """Shopping phase view for the Planning Workspace.

    Shows shopping list with Need/Have/Buy columns and
    allows marking shopping as complete.
    """

    def __init__(
        self,
        parent: Any,
        event_id: Optional[int] = None,
        **kwargs
    ):
        """Initialize ShopView.

        Args:
            parent: Parent widget
            event_id: Event ID to show shopping list for
            **kwargs: Additional arguments passed to CTkFrame
        """
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)

        self.event_id = event_id
        self._items: list[ShoppingListItem] = []
        self._show_all = True

        self._setup_ui()

        if event_id:
            self.after(100, self._load_shopping_list)

    def _setup_ui(self) -> None:
        """Set up the view UI."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Header with title and controls
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_frame.grid_columnconfigure(1, weight=1)

        title = ctk.CTkLabel(
            header_frame,
            text="Shopping List",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        # Filter toggle
        self.filter_var = ctk.StringVar(value="all")
        filter_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        filter_frame.grid(row=0, column=1, padx=20)

        all_radio = ctk.CTkRadioButton(
            filter_frame,
            text="Show All",
            variable=self.filter_var,
            value="all",
            command=self._on_filter_change,
        )
        all_radio.pack(side="left", padx=5)

        buy_radio = ctk.CTkRadioButton(
            filter_frame,
            text="Items to Buy Only",
            variable=self.filter_var,
            value="buy",
            command=self._on_filter_change,
        )
        buy_radio.pack(side="left", padx=5)

        # Mark complete button
        self.complete_btn = ctk.CTkButton(
            header_frame,
            text="Mark Shopping Complete",
            command=self._on_mark_complete,
            width=180,
        )
        self.complete_btn.grid(row=0, column=2)

        # Summary line
        self.summary_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self.summary_label.grid(row=1, column=0, sticky="w", pady=(0, 10))

        # Results container
        self.results_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.results_frame.grid(row=2, column=0, sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.results_frame.grid_rowconfigure(1, weight=1)

        # Placeholder message
        self.placeholder = ctk.CTkLabel(
            self.results_frame,
            text="No shopping list available. Calculate a plan first.",
            font=ctk.CTkFont(size=14),
            text_color="gray",
        )
        self.placeholder.grid(row=0, column=0, pady=50)

        # Table header (hidden initially)
        self.table_header = TableHeader(self.results_frame)

        # Scrollable results table
        self.table_scroll = ctk.CTkScrollableFrame(
            self.results_frame,
            fg_color="transparent",
        )

    def _load_shopping_list(self) -> None:
        """Load shopping list from service."""
        if not self.event_id:
            return

        try:
            self._items = get_shopping_list(self.event_id)
            self._display_list()
            self._update_complete_button()
        except Exception as e:
            print(f"Error loading shopping list: {e}")
            self._show_empty_message("Error loading shopping list")

    def _display_list(self) -> None:
        """Display the shopping list."""
        # Filter items based on toggle
        items = self._items
        if self.filter_var.get() == "buy":
            items = [i for i in items if not i.is_sufficient]

        if not items:
            if self._items:
                # Have items but all filtered out
                self._show_empty_message("All items are in stock!")
            else:
                self._show_empty_message("No shopping list available. Calculate a plan first.")
            return

        # Hide placeholder
        self.placeholder.grid_remove()

        # Show table header
        self.table_header.grid(row=0, column=0, sticky="ew", pady=(0, 2))

        # Clear existing rows
        for widget in self.table_scroll.winfo_children():
            widget.destroy()

        # Show table
        self.table_scroll.grid(row=1, column=0, sticky="nsew")

        # Add rows
        for item in items:
            row = ShoppingListRow(self.table_scroll, item)
            row.pack(fill="x", pady=1)

        # Update summary
        need_count = sum(1 for i in self._items if not i.is_sufficient)
        total_count = len(self._items)
        self.summary_label.configure(
            text=f"{need_count} items to buy | {total_count - need_count} items in stock | "
                 f"{total_count} total ingredients"
        )

    def _show_empty_message(self, message: str) -> None:
        """Show empty state message.

        Args:
            message: Message to display
        """
        self.table_header.grid_remove()
        self.table_scroll.grid_remove()
        self.placeholder.configure(text=message, text_color="gray")
        self.placeholder.grid()

    def _on_filter_change(self) -> None:
        """Handle filter radio button change."""
        self._display_list()

    def _on_mark_complete(self) -> None:
        """Handle mark complete button click."""
        if not self.event_id:
            return

        try:
            result = mark_shopping_complete(self.event_id)
            if result:
                self._update_complete_button()
                self._show_success("Shopping marked as complete!")
            else:
                self._show_error("Failed to mark shopping complete")
        except Exception as e:
            self._show_error(str(e))

    def _update_complete_button(self) -> None:
        """Update the complete button state."""
        if not self.event_id:
            return

        try:
            is_complete = is_shopping_complete(self.event_id)
            if is_complete:
                self.complete_btn.configure(
                    text="Shopping Complete",
                    state="disabled",
                    fg_color=("#00AA00", "#00CC00"),
                )
            else:
                self.complete_btn.configure(
                    text="Mark Shopping Complete",
                    state="normal",
                    fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"],
                )
        except Exception:
            pass

    def _show_success(self, message: str) -> None:
        """Show success message.

        Args:
            message: Success message
        """
        # Simple print for now - could be enhanced with toast
        print(f"Success: {message}")

    def _show_error(self, message: str) -> None:
        """Show error message.

        Args:
            message: Error message
        """
        print(f"Error: {message}")

    def set_event(self, event_id: int) -> None:
        """Set the event ID and reload.

        Args:
            event_id: Event database ID
        """
        self.event_id = event_id
        self._items = []
        self._load_shopping_list()

    def refresh(self) -> None:
        """Refresh the view."""
        self._load_shopping_list()
