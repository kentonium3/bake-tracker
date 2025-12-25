"""
Inventory tab for displaying and managing inventory items.

Provides interface for:
- Viewing inventory in aggregate or detail mode
- Adding new inventory items (lots)
- Editing existing inventory items
- Deleting inventory items
- Filtering by location
- Expiration alerts (visual indicators)
"""

import customtkinter as ctk
from tkinter import messagebox
from datetime import date
from typing import Optional, List, Dict, Any

from decimal import Decimal, InvalidOperation
from src.services import inventory_item_service, ingredient_service, product_service, supplier_service, purchase_service

# WP10: Units where decimal quantities are unusual
COUNT_BASED_UNITS = ['count', 'bag', 'box', 'package', 'bottle', 'can', 'jar', 'carton']
from src.services.exceptions import (
    InventoryItemNotFound,
    ValidationError as ServiceValidationError,
    DatabaseError,
)
from src.database import session_scope
from src.models import Ingredient
from src.ui.session_state import get_session_state
from src.ui.widgets.type_ahead_combobox import TypeAheadComboBox
from src.ui.widgets.dropdown_builders import (
    build_ingredient_dropdown_values,
    build_product_dropdown_values,
    strip_star_prefix,
    is_separator,
    is_create_new_option,
)


class InventoryTab(ctk.CTkFrame):
    """
    Inventory tab for inventory management.

    Displays inventory items in two modes:
    - Aggregate: Grouped by ingredient showing totals
    - Detail: Individual inventory items (lots) with purchase dates

    Features:
    - Location filter
    - Expiration alerts (yellow < 14 days, red expired)
    - CRUD operations for inventory items
    """

    def __init__(self, parent):
        """Initialize the inventory tab."""
        super().__init__(parent)

        # State
        self.inventory_items = []  # All inventory items
        self.filtered_items = []  # Items after filtering
        self.view_mode = "detail"  # "aggregate" or "detail"
        self._data_loaded = False  # Lazy loading flag

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Header - fixed height
        self.grid_rowconfigure(1, weight=0)  # Controls - fixed height
        self.grid_rowconfigure(2, weight=1)  # Item list - expandable

        # Create UI components
        self._create_header()
        self._create_controls()
        self._create_item_list()

        # Configure parent to expand
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        # Grid the frame to fill parent
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Show loading message - data will be loaded when tab is selected
        self._show_initial_state()

    def _create_header(self):
        """Create the header with title."""
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header_frame,
            text="My Pantry",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        subtitle = ctk.CTkLabel(
            header_frame,
            text="View and manage your pantry with lot tracking and FIFO visibility",
            font=ctk.CTkFont(size=12),
        )
        subtitle.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")

    def _create_controls(self):
        """Create control buttons and filters."""
        controls_frame = ctk.CTkFrame(self)
        controls_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        controls_frame.grid_columnconfigure(6, weight=1)

        # Row 0: Search and filters
        # Search entry
        self.search_entry = ctk.CTkEntry(
            controls_frame,
            placeholder_text="Search by ingredient or brand...",
            width=250,
        )
        self.search_entry.grid(row=0, column=0, padx=5, pady=5)
        self.search_entry.bind("<KeyRelease>", self._on_search)

        # Category filter
        cat_label = ctk.CTkLabel(controls_frame, text="Category:")
        cat_label.grid(row=0, column=1, padx=(15, 5), pady=5)

        self.category_var = ctk.StringVar(value="All Categories")
        self.category_dropdown = ctk.CTkOptionMenu(
            controls_frame,
            variable=self.category_var,
            values=["All Categories"],
            command=self._on_category_change,
            width=180,
        )
        self.category_dropdown.grid(row=0, column=2, padx=5, pady=5)

        # View mode toggle
        view_label = ctk.CTkLabel(controls_frame, text="View:")
        view_label.grid(row=0, column=3, padx=(15, 5), pady=5)

        self.view_mode_var = ctk.StringVar(value="Detail")
        view_mode_dropdown = ctk.CTkOptionMenu(
            controls_frame,
            variable=self.view_mode_var,
            values=["Detail", "Aggregate"],
            command=self._on_view_mode_change,
            width=100,
        )
        view_mode_dropdown.grid(row=0, column=4, padx=5, pady=5)

        # Refresh button
        refresh_button = ctk.CTkButton(
            controls_frame,
            text="Refresh",
            command=self.refresh,
            width=80,
        )
        refresh_button.grid(row=0, column=5, padx=5, pady=5)

        # Row 1: Action buttons
        # Add Inventory Item button
        add_button = ctk.CTkButton(
            controls_frame,
            text="Add Inventory Item",
            command=self._add_inventory_item,
            width=140,
        )
        add_button.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        # Record Usage button (FIFO consumption)
        consume_button = ctk.CTkButton(
            controls_frame,
            text="Record Usage",
            command=self._consume_ingredient,
            width=120,
            fg_color="darkorange",
            hover_color="orange",
        )
        consume_button.grid(row=1, column=1, padx=5, pady=5, sticky="w")

    def _create_item_list(self):
        """Create scrollable list for displaying inventory items."""
        # Container to ensure proper expansion
        list_container = ctk.CTkFrame(self)
        list_container.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
        list_container.grid_columnconfigure(0, weight=1)
        list_container.grid_rowconfigure(0, weight=1)

        # Scrollable frame with minimum height, expands with container
        self.scrollable_frame = ctk.CTkScrollableFrame(
            list_container,
            height=400,  # Minimum height
        )
        self.scrollable_frame.pack(fill="both", expand=True)
        self.scrollable_frame.grid_columnconfigure(0, weight=1)

    def refresh(self):
        """Refresh inventory list from database."""
        try:
            # Get all inventory items from service (returns InventoryItem instances)
            self.inventory_items = inventory_item_service.get_inventory_items()

            # Update category dropdown with unique ingredient categories
            categories = set()
            for item in self.inventory_items:
                product = getattr(item, "product", None)
                ingredient = getattr(product, "ingredient", None) if product else None
                category = getattr(ingredient, "category", None) if ingredient else None
                if category:
                    categories.add(category)
            category_list = ["All Categories"] + sorted(categories)
            self.category_dropdown.configure(values=category_list)

            # Apply filters
            self._apply_filters()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to load inventory items: {str(e)}",
                parent=self,
            )

    def _apply_filters(self):
        """Apply search and category filters and update display."""
        self.filtered_items = list(self.inventory_items)

        # Apply search filter
        search_text = self.search_entry.get().lower().strip()
        if search_text:
            filtered = []
            for item in self.filtered_items:
                product = getattr(item, "product", None)
                ingredient = getattr(product, "ingredient", None) if product else None
                ingredient_name = getattr(ingredient, "display_name", "") or ""
                brand = getattr(product, "brand", "") or ""
                if search_text in ingredient_name.lower() or search_text in brand.lower():
                    filtered.append(item)
            self.filtered_items = filtered

        # Apply category filter
        selected_category = self.category_var.get()
        if selected_category and selected_category != "All Categories":
            filtered = []
            for item in self.filtered_items:
                product = getattr(item, "product", None)
                ingredient = getattr(product, "ingredient", None) if product else None
                category = getattr(ingredient, "category", None) if ingredient else None
                if category == selected_category:
                    filtered.append(item)
            self.filtered_items = filtered

        # Update display based on view mode
        self._update_display()

    def _on_search(self, event=None):
        """Handle search text change."""
        self._apply_filters()

    def _on_category_change(self, value: str):
        """Handle category filter change."""
        self._apply_filters()

    def _update_display(self):
        """Update the display based on current view mode."""
        # Clear existing widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if not self.filtered_items:
            self._show_empty_state()
            return

        if self.view_mode == "aggregate":
            self._display_aggregate_view()
        else:
            self._display_detail_view()

        # Note: Removed update_idletasks() call - it blocks the UI thread
        # and causes freezing with many widgets. CustomTkinter handles
        # scroll region updates automatically.

    def _show_initial_state(self):
        """Show initial state - data loads automatically when tab is selected."""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        initial_label = ctk.CTkLabel(
            self.scrollable_frame,
            text="Loading inventory...",
            font=ctk.CTkFont(size=16),
            text_color="gray",
        )
        initial_label.grid(row=0, column=0, padx=20, pady=50)

    def _show_empty_state(self):
        """Show empty state message."""
        empty_label = ctk.CTkLabel(
            self.scrollable_frame,
            text="No inventory items.\nClick 'Add Inventory Item' to record purchases.",
            font=ctk.CTkFont(size=16),
        )
        empty_label.grid(row=0, column=0, padx=20, pady=50)

    def _display_aggregate_view(self):
        """Display inventory items grouped by ingredient with totals."""
        # Group items by ingredient
        from collections import defaultdict

        ingredient_groups = defaultdict(list)

        for item in self.filtered_items:
            product = getattr(item, "product", None)
            ingredient = getattr(product, "ingredient", None) if product else None
            ingredient_slug = getattr(ingredient, "slug", None)
            if ingredient_slug:
                ingredient_groups[ingredient_slug].append(item)

        # Create header
        self._create_aggregate_header()

        # Limit rows to prevent UI freeze
        # CustomTkinter is slow with many widgets - keep this low
        MAX_DISPLAY_ROWS = 25
        sorted_groups = sorted(ingredient_groups.items())
        display_groups = sorted_groups[:MAX_DISPLAY_ROWS]

        # Display each ingredient group
        for idx, (ingredient_slug, items) in enumerate(display_groups):
            self._create_aggregate_row(idx + 1, ingredient_slug, items)

        # Show truncation warning if needed
        if len(sorted_groups) > MAX_DISPLAY_ROWS:
            warning_frame = ctk.CTkFrame(self.scrollable_frame)
            warning_frame.grid(row=MAX_DISPLAY_ROWS + 1, column=0, padx=5, pady=10, sticky="ew")
            warning_label = ctk.CTkLabel(
                warning_frame,
                text=f"Showing {MAX_DISPLAY_ROWS} of {len(sorted_groups)} ingredients. Use filters to narrow results.",
                text_color="orange",
                font=ctk.CTkFont(size=12, weight="bold"),
            )
            warning_label.grid(row=0, column=0, padx=10, pady=5)

    def _create_aggregate_header(self):
        """Create header for aggregate view."""
        header_frame = ctk.CTkFrame(self.scrollable_frame)
        header_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        headers = [
            ("Ingredient", 0, 300),
            ("Total Quantity", 1, 150),
            ("# Lots", 2, 100),
            ("Oldest Purchase", 3, 150),
            ("Actions", 4, 150),
        ]

        for text, col, width in headers:
            label = ctk.CTkLabel(
                header_frame,
                text=text,
                font=ctk.CTkFont(weight="bold"),
                width=width,
            )
            label.grid(row=0, column=col, padx=5, pady=5, sticky="w")

    def _create_aggregate_row(self, row_idx: int, ingredient_slug: str, items):
        """Create a row for aggregated ingredient."""
        row_frame = ctk.CTkFrame(self.scrollable_frame)
        row_frame.grid(row=row_idx, column=0, padx=5, pady=2, sticky="ew")
        row_frame.grid_columnconfigure(1, weight=1)

        # Get ingredient info from already-loaded items (no DB query needed)
        ingredient_obj = None
        if items:
            product = getattr(items[0], "product", None)
            ingredient_obj = getattr(product, "ingredient", None) if product else None

        ingredient_name = getattr(ingredient_obj, "display_name", ingredient_slug)

        # Feature 011: Check if packaging ingredient
        is_packaging = getattr(ingredient_obj, "is_packaging", False) if ingredient_obj else False
        type_indicator = "📦 " if is_packaging else ""

        # Calculate total quantity from already-loaded items (no DB query needed)
        from decimal import Decimal
        unit_totals = {}
        for item in items:
            product = getattr(item, "product", None)
            unit = getattr(product, "package_unit", None) if product else None
            qty = getattr(item, "quantity", 0) or 0
            if unit and qty > 0:
                if unit not in unit_totals:
                    unit_totals[unit] = Decimal("0.0")
                unit_totals[unit] += Decimal(str(qty))

        if unit_totals:
            # Format as "25 lb + 3 cup" style display
            qty_parts = []
            for unit, total in unit_totals.items():
                if total > 0:
                    if total == int(total):
                        qty_parts.append(f"{int(total)} {unit}")
                    else:
                        qty_parts.append(f"{float(total):.1f} {unit}")
            qty_display = " + ".join(qty_parts) if qty_parts else "0"
        else:
            qty_display = "0"

        # Get lot count and oldest purchase date
        lot_count = len(items)
        oldest_date = min(
            (item.purchase_date for item in items if getattr(item, "purchase_date", None)),
            default=None,
        )
        oldest_str = oldest_date.strftime("%Y-%m-%d") if oldest_date else "N/A"

        # Check for expiration warnings
        warning_color = self._get_expiration_warning_color(items)
        if warning_color:
            row_frame.configure(fg_color=warning_color)

        # Ingredient name (with packaging indicator if applicable)
        name_label = ctk.CTkLabel(
            row_frame,
            text=f"{type_indicator}{ingredient_name}",
            width=300,
            anchor="w",
        )
        name_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # Total quantity
        qty_label = ctk.CTkLabel(
            row_frame,
            text=qty_display,
            width=150,
            anchor="w",
        )
        qty_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Lot count
        lot_label = ctk.CTkLabel(
            row_frame,
            text=str(lot_count),
            width=100,
            anchor="w",
        )
        lot_label.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        # Oldest purchase
        date_label = ctk.CTkLabel(
            row_frame,
            text=oldest_str,
            width=150,
            anchor="w",
        )
        date_label.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        # Actions
        actions_frame = ctk.CTkFrame(row_frame)
        actions_frame.grid(row=0, column=4, padx=5, pady=5)

        view_details_btn = ctk.CTkButton(
            actions_frame,
            text="View Details",
            command=lambda: self._view_ingredient_details(ingredient_slug),
            width=120,
        )
        view_details_btn.grid(row=0, column=0, padx=2)

    def _display_detail_view(self):
        """Display individual inventory items (lots)."""
        # Create header
        self._create_detail_header()

        # Sort items by purchase date (FIFO order - oldest first)
        sorted_items = sorted(
            self.filtered_items,
            key=lambda x: getattr(x, "purchase_date", None) or date.today(),
        )

        # Limit rows to prevent UI freeze with large datasets
        # CustomTkinter is slow with many widgets - keep this low
        MAX_DISPLAY_ROWS = 25
        display_items = sorted_items[:MAX_DISPLAY_ROWS]

        # Display each item
        for idx, item in enumerate(display_items):
            self._create_detail_row(idx + 1, item)

        # Show truncation warning if needed
        if len(sorted_items) > MAX_DISPLAY_ROWS:
            warning_frame = ctk.CTkFrame(self.scrollable_frame)
            warning_frame.grid(row=MAX_DISPLAY_ROWS + 1, column=0, padx=5, pady=10, sticky="ew")
            warning_label = ctk.CTkLabel(
                warning_frame,
                text=f"Showing {MAX_DISPLAY_ROWS} of {len(sorted_items)} items. Use search or filters to narrow results.",
                text_color="orange",
                font=ctk.CTkFont(size=12, weight="bold"),
            )
            warning_label.grid(row=0, column=0, padx=10, pady=5)

    def _create_detail_header(self):
        """Create header for detail view."""
        header_frame = ctk.CTkFrame(self.scrollable_frame)
        header_frame.grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        headers = [
            ("Brand", 0, 180),
            ("Product", 1, 330),  # 50% wider for longer descriptions
            ("Quantity", 2, 140),
            ("Purchase Date", 3, 100),
            ("Expiration", 4, 100),
            ("Actions", 5, 160),
        ]

        for text, col, width in headers:
            label = ctk.CTkLabel(
                header_frame,
                text=text,
                font=ctk.CTkFont(weight="bold"),
                width=width,
                anchor="w",  # Left justify header text
            )
            label.grid(row=0, column=col, padx=3, pady=3, sticky="w")

    def _truncate_text(self, text: str, max_chars: int = 25) -> str:
        """Truncate text and add ellipsis if too long."""
        if not text:
            return ""
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 1] + "..."

    def _create_detail_row(self, row_idx: int, item: dict):
        """Create a row for individual inventory item."""
        row_frame = ctk.CTkFrame(self.scrollable_frame)
        row_frame.grid(row=row_idx, column=0, padx=2, pady=1, sticky="ew")
        row_frame.grid_columnconfigure(1, weight=1)

        # Get ingredient and product info
        product_obj = getattr(item, "product", None)
        ingredient_obj = getattr(product_obj, "ingredient", None) if product_obj else None

        # Feature 011: Check if packaging ingredient
        is_packaging = getattr(ingredient_obj, "is_packaging", False) if ingredient_obj else False
        type_indicator = "📦 " if is_packaging else ""

        # Product column: Brand name
        brand = getattr(product_obj, "brand", "Unknown") if product_obj else "Unknown"
        product_display = f"{type_indicator}{brand}"

        # Description column: Product name + package info
        # Falls back to ingredient name in brackets if product_name is empty
        product_name = getattr(product_obj, "product_name", None) or ""
        ingredient_name = getattr(ingredient_obj, "display_name", "") if ingredient_obj else ""
        package_qty = getattr(product_obj, "package_unit_quantity", None)
        package_unit = getattr(product_obj, "package_unit", "") or ""
        package_type = getattr(product_obj, "package_type", None) or ""

        # Build description: "Product Name - 25 lb bag" or "[Ingredient] - 25 lb bag"
        desc_parts = []
        if product_name:
            desc_parts.append(product_name)
        elif ingredient_name:
            # Fallback: show ingredient name in brackets to indicate it's not a product name
            desc_parts.append(f"[{ingredient_name}]")
        if package_qty and package_unit:
            size_str = f"{package_qty:g} {package_unit}"
            if package_type:
                size_str += f" {package_type}"
            desc_parts.append(size_str)
        description = " - ".join(desc_parts) if desc_parts else "N/A"

        # Check expiration status
        expiration_date = getattr(item, "expiration_date", None)
        warning_color = None
        expiration_text = "None"

        if expiration_date:
            expiration_text = expiration_date.strftime("%Y-%m-%d")
            days_until_expiry = (expiration_date - date.today()).days

            if days_until_expiry < 0:
                warning_color = "#8B0000"  # Dark red for expired
                expiration_text = f"EXPIRED"
            elif days_until_expiry <= 14:
                warning_color = "#DAA520"  # Goldenrod for expiring soon
                expiration_text = f"⚠️ {expiration_text}"

        if warning_color:
            row_frame.configure(fg_color=warning_color)

        # Column 0: Product (brand)
        product_label = ctk.CTkLabel(
            row_frame,
            text=self._truncate_text(product_display, 22),
            width=180,
            anchor="w",
        )
        product_label.grid(row=0, column=0, padx=3, pady=3, sticky="w")

        # Column 1: Product (product name + package info)
        desc_label = ctk.CTkLabel(
            row_frame,
            text=self._truncate_text(description, 42),  # More chars for wider column
            width=330,
            anchor="w",
        )
        desc_label.grid(row=0, column=1, padx=3, pady=3, sticky="w")

        # Column 2: Quantity - show as "X pkg (Y unit)" format
        qty_value = getattr(item, "quantity", 0) or 0

        # Format total quantity
        if qty_value == int(qty_value):
            qty_total = str(int(qty_value))
        else:
            qty_total = f"{qty_value:.1f}"

        # Calculate packages if package size is known
        if package_qty and package_qty > 0:
            packages = qty_value / float(package_qty)
            if packages == int(packages):
                pkg_text = str(int(packages))
            else:
                pkg_text = f"{packages:.1f}"
            qty_display = f"{pkg_text} pkg ({qty_total} {package_unit})"
        else:
            qty_display = f"{qty_total} {package_unit}".strip()

        qty_label = ctk.CTkLabel(
            row_frame,
            text=qty_display,
            width=140,
            anchor="w",
            font=ctk.CTkFont(weight="bold"),
        )
        qty_label.grid(row=0, column=2, padx=3, pady=3, sticky="w")

        # Column 3: Purchase date
        purchase_date = getattr(item, "purchase_date", None)
        purchase_str = purchase_date.strftime("%Y-%m-%d") if purchase_date else "N/A"
        purchase_label = ctk.CTkLabel(
            row_frame,
            text=purchase_str,
            width=100,
            anchor="w",
        )
        purchase_label.grid(row=0, column=3, padx=3, pady=3, sticky="w")

        # Column 4: Expiration date
        exp_label = ctk.CTkLabel(
            row_frame,
            text=expiration_text,
            width=100,
            anchor="w",
        )
        exp_label.grid(row=0, column=4, padx=3, pady=3, sticky="w")

        # Column 5: Actions
        actions_frame = ctk.CTkFrame(row_frame)
        actions_frame.grid(row=0, column=5, padx=3, pady=3)

        item_id = getattr(item, "id", None)
        edit_btn = ctk.CTkButton(
            actions_frame,
            text="Edit",
            command=lambda id=item_id: self._edit_inventory_item(id),
            width=70,
        )
        edit_btn.grid(row=0, column=0, padx=2)

        delete_btn = ctk.CTkButton(
            actions_frame,
            text="Delete",
            command=lambda id=item_id: self._delete_inventory_item(id),
            width=70,
            fg_color="darkred",
            hover_color="red",
        )
        delete_btn.grid(row=0, column=1, padx=2)

    def _get_expiration_warning_color(self, items: List[dict]) -> Optional[str]:
        """Get warning color based on expiration dates in items."""
        has_expired = False
        has_expiring_soon = False

        for item in items:
            expiration_date = getattr(item, "expiration_date", None)
            if expiration_date:
                days_until_expiry = (expiration_date - date.today()).days
                if days_until_expiry < 0:
                    has_expired = True
                elif days_until_expiry <= 14:
                    has_expiring_soon = True

        if has_expired:
            return "#8B0000"  # Dark red
        elif has_expiring_soon:
            return "#DAA520"  # Goldenrod
        return None

    def _on_view_mode_change(self, value: str):
        """Handle view mode change."""
        self.view_mode = value.lower()
        self._update_display()

    def _view_ingredient_details(self, ingredient_slug: str):
        """Switch to detail view filtered to specific ingredient."""
        # Switch to detail mode
        self.view_mode = "detail"
        self.view_mode_var.set("Detail")

        # Filter to specific ingredient
        self.filtered_items = [
            item
            for item in self.inventory_items
            if getattr(getattr(item, "product", None), "ingredient", None)
            and item.product.ingredient.slug == ingredient_slug
        ]

        self._update_display()

    def filter_by_ingredient(self, ingredient_slug: str) -> None:
        """
        Public helper to focus the view on a specific ingredient.

        Args:
            ingredient_slug: Slug of the ingredient to filter by.
        """
        if not ingredient_slug:
            return

        if not any(
            getattr(getattr(item, "product", None), "ingredient", None)
            and item.product.ingredient.slug == ingredient_slug
            for item in self.inventory_items
        ):
            self.refresh()

        if not any(
            getattr(getattr(item, "product", None), "ingredient", None)
            and item.product.ingredient.slug == ingredient_slug
            for item in self.inventory_items
        ):
            messagebox.showinfo(
                "No Inventory Items",
                f"No inventory found for ingredient '{ingredient_slug}'.",
                parent=self,
            )
            return

        self.view_mode = "detail"
        self.view_mode_var.set("Detail")
        # Clear filters to show the specific ingredient
        self.search_entry.delete(0, "end")
        self.category_var.set("All Categories")

        self.filtered_items = [
            item
            for item in self.inventory_items
            if getattr(getattr(item, "product", None), "ingredient", None)
            and item.product.ingredient.slug == ingredient_slug
        ]
        self._update_display()

    def _add_inventory_item(self):
        """Open dialog to add new inventory item."""
        dialog = InventoryItemFormDialog(self, title="Add Inventory Item")
        self.wait_window(dialog)

        if not dialog.result:
            return

        try:
            # Create inventory item via service (F028: includes supplier and price)
            inventory_item_service.add_to_inventory(
                product_id=dialog.result["product_id"],
                quantity=dialog.result["quantity"],
                supplier_id=dialog.result["supplier_id"],  # F028
                unit_price=dialog.result["unit_price"],  # F028
                purchase_date=dialog.result["purchase_date"],
                expiration_date=dialog.result.get("expiration_date"),
                location=dialog.result.get("location"),
                notes=dialog.result.get("notes"),
            )

            messagebox.showinfo(
                "Success",
                "Inventory item added successfully",
                parent=self,
            )
            self.refresh()

        except ServiceValidationError as e:
            messagebox.showerror("Validation Error", str(e), parent=self)
        except DatabaseError as e:
            messagebox.showerror("Database Error", str(e), parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add inventory item: {str(e)}", parent=self)

    def _edit_inventory_item(self, inventory_item_id: int):
        """Open dialog to edit inventory item."""
        try:
            # Get current item data
            item = next((i for i in self.inventory_items if i.id == inventory_item_id), None)
            if not item:
                messagebox.showerror("Error", "Inventory item not found", parent=self)
                return

            dialog = InventoryItemFormDialog(
                self,
                title="Edit Inventory Item",
                item=self._serialize_inventory_item(item),
            )
            self.wait_window(dialog)

            if not dialog.result:
                return

            # Update inventory item via service
            inventory_item_service.update_inventory_item(inventory_item_id, dialog.result)

            messagebox.showinfo(
                "Success",
                "Inventory item updated successfully",
                parent=self,
            )
            self.refresh()

        except InventoryItemNotFound:
            messagebox.showerror("Error", "Inventory item not found", parent=self)
            self.refresh()
        except ServiceValidationError as e:
            messagebox.showerror("Validation Error", str(e), parent=self)
        except DatabaseError as e:
            messagebox.showerror("Database Error", str(e), parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update inventory item: {str(e)}", parent=self)

    def _delete_inventory_item(self, inventory_item_id: int):
        """Delete inventory item after confirmation."""
        result = messagebox.askyesno(
            "Confirm Delete",
            "Are you sure you want to delete this inventory item?",
            parent=self,
        )

        if result:
            try:
                inventory_item_service.delete_inventory_item(inventory_item_id)
                messagebox.showinfo(
                    "Success",
                    "Inventory item deleted successfully",
                    parent=self,
                )
                self.refresh()

            except InventoryItemNotFound:
                messagebox.showerror("Error", "Inventory item not found", parent=self)
                self.refresh()
            except DatabaseError as e:
                messagebox.showerror("Database Error", str(e), parent=self)
            except Exception as e:
                messagebox.showerror(
                    "Error", f"Failed to delete inventory item: {str(e)}", parent=self
                )

    def _consume_ingredient(self):
        """Open dialog to consume ingredient using FIFO logic."""
        dialog = ConsumeIngredientDialog(self)
        self.wait_window(dialog)

        if dialog.result:
            self.refresh()

    def _serialize_inventory_item(self, item) -> dict:
        """Convert an InventoryItem ORM instance to a simple dict for dialog usage."""
        product = getattr(item, "product", None)
        ingredient = getattr(product, "ingredient", None) if product else None

        return {
            "id": item.id,
            "product_id": item.product_id,
            "quantity": item.quantity,
            "purchase_date": item.purchase_date,
            "expiration_date": item.expiration_date,
            "location": item.location,
            "notes": item.notes,
            "product_brand": getattr(product, "brand", None),
            "product_package_unit_quantity": getattr(product, "package_unit_quantity", None),
            "product_package_unit": getattr(product, "package_unit", None),
            "ingredient_name": getattr(ingredient, "display_name", None),
        }


class InventoryItemFormDialog(ctk.CTkToplevel):
    """
    Dialog for creating or editing an inventory item.

    Form fields:
    - Ingredient (dropdown)
    - Product (dropdown, filtered by ingredient)
    - Supplier (dropdown, required for new items) - F028
    - Price (entry with suggestion hint, required for new items) - F028
    - Quantity (required, > 0)
    - Purchase Date (required)
    - Expiration Date (optional, >= purchase_date)
    - Location (optional)
    - Notes (optional)
    """

    def __init__(self, parent, title="Inventory Item", item: Optional[dict] = None):
        """
        Initialize the form dialog.

        Args:
            parent: Parent widget
            title: Dialog title
            item: Existing inventory item data for editing (None for new)
        """
        super().__init__(parent)

        self.title(title)
        self.geometry("500x700")  # Increased height for new fields
        self.resizable(False, False)

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        self.item = item
        self.result: Optional[Dict[str, Any]] = None
        self.ingredients: List[Dict[str, Any]] = []
        self.products: List[Dict[str, Any]] = []
        self.suppliers: List[Dict[str, Any]] = []  # F028
        self.session_state = get_session_state()  # F029: Session memory

        # Load data
        self._load_ingredients()
        self._load_suppliers()  # F028

        # Create form
        self._create_form()

        # Populate if editing
        if self.item:
            self._populate_form()

    def _load_ingredients(self):
        """Load ingredients from service."""
        try:
            self.ingredients = ingredient_service.get_all_ingredients()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load ingredients: {str(e)}", parent=self)
            self.destroy()

    def _load_suppliers(self):
        """Load active suppliers from service (F028)."""
        try:
            self.suppliers = supplier_service.get_active_suppliers()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load suppliers: {str(e)}", parent=self)
            self.destroy()

    def _create_form(self):
        """Create form fields."""
        # Configure grid
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        row = 0

        # F029: Category dropdown (type-ahead, min_chars=1)
        cat_label = ctk.CTkLabel(self, text="Category:*")
        cat_label.grid(row=row, column=0, padx=10, pady=10, sticky="w")

        # Load categories from ingredients
        categories = sorted(set(ing.get("category", "") for ing in self.ingredients if ing.get("category")))

        # F029: Apply session memory for category
        default_category = ""
        if not self.item and categories:
            last_category = self.session_state.get_last_category()
            if last_category and last_category in categories:
                default_category = last_category
            else:
                default_category = categories[0] if categories else ""

        self.category_combo = TypeAheadComboBox(
            self,
            values=categories if categories else [],
            min_chars=1,
            command=self._on_category_selected,
        )
        self.category_combo.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
        if default_category:
            self.category_combo.set(default_category)
        row += 1

        # F029: Ingredient dropdown (type-ahead, min_chars=2, filtered by category)
        ing_label = ctk.CTkLabel(self, text="Ingredient:*")
        ing_label.grid(row=row, column=0, padx=10, pady=10, sticky="w")

        self.ingredient_combo = TypeAheadComboBox(
            self,
            values=[],  # Populated when category selected
            min_chars=2,
            command=self._on_ingredient_selected,
        )
        self.ingredient_combo.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
        self.ingredient_combo.configure(state="disabled")
        self.selected_ingredient = None  # Track selected ingredient object
        row += 1

        # F029: Product dropdown (type-ahead, min_chars=2, filtered by ingredient)
        product_label = ctk.CTkLabel(self, text="Product:*")
        product_label.grid(row=row, column=0, padx=10, pady=10, sticky="w")

        self.product_combo = TypeAheadComboBox(
            self,
            values=[],  # Populated when ingredient selected
            min_chars=2,
            command=self._on_product_selected,
        )
        self.product_combo.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
        self.product_combo.configure(state="disabled")
        self.selected_product = None  # Track selected product object
        row += 1

        # F029/WP08: Inline product creation frame (hidden initially)
        self.inline_create_row = row  # Track row for dynamic positioning
        self.inline_create_expanded = False
        self.inline_create_frame = ctk.CTkFrame(
            self,
            border_width=1,
            corner_radius=5,
            fg_color=("gray90", "gray20"),
        )
        self._setup_inline_create_form()
        # Do NOT grid initially - hidden until expanded
        row += 1

        # Trigger cascading load if category is pre-selected
        if default_category and not self.item:
            self._on_category_selected(default_category)

        # F028: Supplier dropdown (required for new items)
        # F029: Pre-select from session memory with star indicator
        supplier_label = ctk.CTkLabel(self, text="Supplier:*")
        supplier_label.grid(row=row, column=0, padx=10, pady=10, sticky="w")

        supplier_names = [s["display_name"] for s in self.suppliers]

        # F029: Check session state for last supplier
        default_supplier = ""
        self._session_supplier_display = None  # Track session-selected supplier for star
        if not self.item and supplier_names:
            last_supplier_id = self.session_state.get_last_supplier_id()
            if last_supplier_id:
                # Find supplier with matching ID
                for s in self.suppliers:
                    if s["id"] == last_supplier_id:
                        # Pre-select with star indicator
                        default_supplier = self._format_supplier_with_star(s["display_name"])
                        self._session_supplier_display = s["display_name"]
                        break
            # Fall back to first supplier if no session match
            if not default_supplier:
                default_supplier = supplier_names[0]

        self.supplier_var = ctk.StringVar(value=default_supplier if not self.item else "")
        self.supplier_dropdown = ctk.CTkOptionMenu(
            self,
            variable=self.supplier_var,
            values=supplier_names if supplier_names else ["No suppliers"],
            command=self._on_supplier_change,
        )
        self.supplier_dropdown.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
        row += 1

        # F028: Price entry with suggestion hint
        price_label = ctk.CTkLabel(self, text="Unit Price ($):*")
        price_label.grid(row=row, column=0, padx=10, pady=(10, 0), sticky="w")

        self.price_var = ctk.StringVar(value="")
        self.price_entry = ctk.CTkEntry(self, textvariable=self.price_var, placeholder_text="0.00")
        self.price_entry.grid(row=row, column=1, padx=10, pady=(10, 0), sticky="ew")
        # WP09: Bind Key to clear hint on manual edit
        self.price_entry.bind('<Key>', self._on_price_key)
        # WP10: Bind FocusOut for price validation
        self.price_entry.bind('<FocusOut>', self._on_price_focus_out)
        row += 1

        # F028: Price hint label (shows last paid price)
        self.price_hint_label = ctk.CTkLabel(
            self,
            text="",
            font=("", 11),
            text_color="gray",
        )
        self.price_hint_label.grid(row=row, column=1, padx=10, pady=(0, 10), sticky="w")
        row += 1

        # Trigger initial price hint if supplier is pre-selected
        if default_supplier and not self.item:
            self._on_supplier_change(default_supplier)

        # Quantity
        qty_label = ctk.CTkLabel(self, text="Quantity:*")
        qty_label.grid(row=row, column=0, padx=10, pady=10, sticky="w")

        self.quantity_entry = ctk.CTkEntry(self, placeholder_text="e.g., 25")
        self.quantity_entry.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
        # WP10: Bind FocusOut for quantity validation
        self.quantity_entry.bind('<FocusOut>', self._on_quantity_focus_out)
        row += 1

        # Purchase Date
        purchase_label = ctk.CTkLabel(self, text="Purchase Date:*")
        purchase_label.grid(row=row, column=0, padx=10, pady=10, sticky="w")

        self.purchase_date_entry = ctk.CTkEntry(self, placeholder_text="YYYY-MM-DD")
        self.purchase_date_entry.grid(row=row, column=1, padx=10, pady=10, sticky="ew")

        # Set default to today
        self.purchase_date_entry.insert(0, date.today().strftime("%Y-%m-%d"))
        row += 1

        # Expiration Date
        exp_label = ctk.CTkLabel(self, text="Expiration Date:")
        exp_label.grid(row=row, column=0, padx=10, pady=10, sticky="w")

        self.expiration_date_entry = ctk.CTkEntry(self, placeholder_text="YYYY-MM-DD (optional)")
        self.expiration_date_entry.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
        row += 1

        # Location
        location_label = ctk.CTkLabel(self, text="Location:")
        location_label.grid(row=row, column=0, padx=10, pady=10, sticky="w")

        self.location_entry = ctk.CTkEntry(self, placeholder_text="e.g., Main Storage")
        self.location_entry.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
        row += 1

        # Notes
        notes_label = ctk.CTkLabel(self, text="Notes:")
        notes_label.grid(row=row, column=0, padx=10, pady=10, sticky="nw")

        self.notes_text = ctk.CTkTextbox(self, height=100)
        self.notes_text.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
        row += 1

        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=row, column=0, columnspan=2, padx=10, pady=20, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.destroy,
        )
        cancel_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        save_btn = ctk.CTkButton(
            button_frame,
            text="Save",
            command=self._save,
        )
        save_btn.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

    def _on_category_selected(self, selected_value: str):
        """Handle category selection - load ingredients for this category (F029)."""
        # Strip star if present
        category = strip_star_prefix(selected_value).strip()
        if not category:
            return

        # Load ingredients for this category using dropdown builder with recency
        try:
            with session_scope() as session:
                ingredient_values = build_ingredient_dropdown_values(category, session)

            self.ingredient_combo.reset_values(ingredient_values)
            self.ingredient_combo.configure(state="normal")

            # Clear downstream selections
            self.ingredient_combo.set("")
            self.product_combo.set("")
            self.product_combo.configure(state="disabled")
            self.selected_ingredient = None
            self.selected_product = None

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load ingredients: {str(e)}", parent=self)

    def _on_ingredient_selected(self, selected_value: str):
        """Handle ingredient selection - load products for this ingredient (F029)."""
        # Handle separator selection
        if is_separator(selected_value):
            self.ingredient_combo.set("")
            return

        # Strip star if present
        ingredient_name = strip_star_prefix(selected_value).strip()
        if not ingredient_name:
            return

        # Find ingredient by display_name from our loaded ingredients
        ingredient = next(
            (ing for ing in self.ingredients if ing["name"] == ingredient_name),
            None,
        )
        if not ingredient:
            return

        self.selected_ingredient = ingredient

        # Load products for this ingredient using dropdown builder with recency
        try:
            with session_scope() as session:
                # Find the ingredient ID
                ing_obj = session.query(Ingredient).filter_by(
                    display_name=ingredient_name
                ).first()

                if not ing_obj:
                    self.product_combo.reset_values([])
                    self.product_combo.configure(state="disabled")
                    return

                product_values = build_product_dropdown_values(ing_obj.id, session)

            self.product_combo.reset_values(product_values)
            self.product_combo.configure(state="normal")

            # Clear product selection
            self.product_combo.set("")
            self.selected_product = None

            # Also load products dict for validation
            product_objects = product_service.get_products_for_ingredient(ingredient["slug"])
            self.products = [
                {
                    "id": p.id,
                    "name": p.name,
                    "brand": p.brand,
                    "package_unit_quantity": p.package_unit_quantity,
                    "package_unit": p.package_unit,
                }
                for p in product_objects
            ]

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load products: {str(e)}", parent=self)

    def _on_product_selected(self, selected_value: str):
        """Handle product selection (F029)."""
        # Ignore separator selection
        if is_separator(selected_value):
            self.product_combo.set("")
            return

        # WP08: Check for create new option - trigger inline form
        if is_create_new_option(selected_value):
            self.product_combo.set("")
            self._toggle_inline_create()
            return

        # Strip star if present
        product_name = strip_star_prefix(selected_value).strip()
        if not product_name:
            return

        # Find product by name from our loaded products
        product = next(
            (p for p in self.products
             if p.get("brand") == product_name
             or self._format_product_display(p) == selected_value.replace("⭐ ", "")),
            None,
        )

        if product:
            self.selected_product = product
            # Trigger price hint update
            self._on_supplier_change(self.supplier_var.get())

    def _format_product_display(self, product: dict) -> str:
        """Format a product dictionary into a human-readable label."""
        brand = product.get("brand") or "Unknown"
        quantity = product.get("package_unit_quantity")
        unit = product.get("package_unit") or ""
        if quantity:
            return f"{brand} - {quantity} {unit}".strip()
        return brand

    def _format_supplier_with_star(self, display_name: str) -> str:
        """Format supplier display name with star indicator for session memory (F029)."""
        return f"* {display_name}"

    def _strip_star_from_supplier(self, display_name: str) -> str:
        """Remove star indicator from supplier display name (F029)."""
        if display_name.startswith("* "):
            return display_name[2:]
        return display_name

    # ==========================================================================
    # WP08: Inline Product Creation Methods
    # ==========================================================================

    def _setup_inline_create_form(self):
        """Setup inline product creation form (WP08)."""
        form_frame = ctk.CTkFrame(self.inline_create_frame, fg_color="transparent")
        form_frame.pack(fill="both", expand=True, padx=10, pady=10)
        form_frame.grid_columnconfigure(1, weight=1)

        # Header
        header = ctk.CTkLabel(
            form_frame,
            text="Create New Product",
            font=ctk.CTkFont(weight="bold"),
        )
        header.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky="w")

        # Ingredient (read-only display)
        ctk.CTkLabel(form_frame, text="Ingredient:").grid(
            row=1, column=0, padx=5, pady=5, sticky="w"
        )
        self.inline_ingredient_label = ctk.CTkLabel(
            form_frame, text="", text_color="gray"
        )
        self.inline_ingredient_label.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Product Name (required)
        ctk.CTkLabel(form_frame, text="Product Name:*").grid(
            row=2, column=0, padx=5, pady=5, sticky="w"
        )
        self.inline_name_entry = ctk.CTkEntry(
            form_frame, placeholder_text="e.g., Gold Medal AP Flour"
        )
        self.inline_name_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # Package Unit + Quantity on same row
        ctk.CTkLabel(form_frame, text="Package:*").grid(
            row=3, column=0, padx=5, pady=5, sticky="w"
        )
        package_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        package_frame.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        self.inline_qty_entry = ctk.CTkEntry(package_frame, width=80, placeholder_text="Qty")
        self.inline_qty_entry.pack(side="left", padx=(0, 5))

        self.inline_unit_combo = ctk.CTkComboBox(
            package_frame,
            values=["lb", "oz", "kg", "g", "fl oz", "ml", "L", "count", "bag", "box"],
            width=100,
        )
        self.inline_unit_combo.pack(side="left")

        # Preferred Supplier (optional, pre-filled from session)
        ctk.CTkLabel(form_frame, text="Preferred Supplier:").grid(
            row=4, column=0, padx=5, pady=5, sticky="w"
        )
        supplier_names = [s["display_name"] for s in self.suppliers]
        self.inline_supplier_combo = ctk.CTkComboBox(
            form_frame,
            values=supplier_names if supplier_names else [""],
        )
        self.inline_supplier_combo.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        # Buttons
        btn_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=100,
            fg_color="gray",
            command=self._cancel_inline_create,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Create Product",
            width=120,
            command=self._create_product_inline,
        ).pack(side="left", padx=5)

    def _toggle_inline_create(self):
        """Toggle inline product creation form (accordion) (WP08)."""
        if self.inline_create_expanded:
            # Collapse
            self.inline_create_frame.grid_forget()
            self.inline_create_expanded = False
            self.product_combo.configure(state="normal")
        else:
            # Expand
            self.inline_create_frame.grid(
                row=self.inline_create_row,
                column=0,
                columnspan=2,
                sticky="ew",
                padx=10,
                pady=5,
            )
            self.inline_create_expanded = True
            self.product_combo.configure(state="disabled")
            self._prefill_inline_form()
            self.inline_name_entry.focus_set()

    def _prefill_inline_form(self):
        """Pre-fill inline creation form with smart defaults (WP08)."""
        from src.utils.category_defaults import get_default_unit_for_category

        # Clear previous values
        self.inline_name_entry.delete(0, "end")
        self.inline_qty_entry.delete(0, "end")

        # Pre-fill ingredient (read-only display)
        if self.selected_ingredient:
            self.inline_ingredient_label.configure(
                text=self.selected_ingredient.get("name", "")
            )

            # Pre-fill unit from category defaults
            category = self.selected_ingredient.get("category", "")
            if category:
                default_unit = get_default_unit_for_category(category)
                self.inline_unit_combo.set(default_unit)

        # Pre-fill supplier from session
        last_supplier_id = self.session_state.get_last_supplier_id()
        if last_supplier_id:
            for s in self.suppliers:
                if s["id"] == last_supplier_id:
                    self.inline_supplier_combo.set(f"⭐ {s['display_name']}")
                    break
        else:
            # Default to first supplier if any
            if self.suppliers:
                self.inline_supplier_combo.set(self.suppliers[0]["display_name"])

    def _create_product_inline(self):
        """Create product from inline form (WP08)."""
        from decimal import Decimal, InvalidOperation

        # Validate required fields
        name = self.inline_name_entry.get().strip()
        if not name:
            messagebox.showerror(
                "Validation Error", "Product name is required", parent=self
            )
            self.inline_name_entry.focus_set()
            return

        unit = self.inline_unit_combo.get().strip()
        if not unit:
            messagebox.showerror(
                "Validation Error", "Package unit is required", parent=self
            )
            return

        qty_str = self.inline_qty_entry.get().strip()
        if not qty_str:
            messagebox.showerror(
                "Validation Error", "Package quantity is required", parent=self
            )
            self.inline_qty_entry.focus_set()
            return

        try:
            qty = Decimal(qty_str)
            if qty <= 0:
                raise ValueError("Quantity must be positive")
        except (InvalidOperation, ValueError):
            messagebox.showerror(
                "Validation Error",
                "Package quantity must be a positive number",
                parent=self,
            )
            self.inline_qty_entry.focus_set()
            return

        if not self.selected_ingredient:
            messagebox.showerror("Error", "No ingredient selected", parent=self)
            return

        # Get preferred supplier (optional)
        supplier_display = self.inline_supplier_combo.get().replace("⭐ ", "").strip()
        preferred_supplier_id = None
        if supplier_display:
            supplier = next(
                (s for s in self.suppliers if s["display_name"] == supplier_display),
                None,
            )
            if supplier:
                preferred_supplier_id = supplier["id"]

        # Create product via service
        try:
            new_product = product_service.create_product(
                name=name,
                ingredient_slug=self.selected_ingredient.get("slug"),
                brand=name,  # Use name as brand for simplicity
                package_unit=unit,
                package_unit_quantity=float(qty),
                preferred_supplier_id=preferred_supplier_id,
            )

            # Success - rebuild dropdown and select new product
            with session_scope() as session:
                # Find the ingredient ID
                ing_obj = session.query(Ingredient).filter_by(
                    display_name=self.selected_ingredient.get("name")
                ).first()

                if ing_obj:
                    product_values = build_product_dropdown_values(ing_obj.id, session)
                    self.product_combo.reset_values(product_values)

            # Select the new product (it's "recent" so should have star)
            self.product_combo.set(f"⭐ {name}")

            # Update products list for tracking
            self.products.append({
                "id": new_product.id,
                "name": new_product.name,
                "brand": new_product.brand,
                "package_unit": new_product.package_unit,
                "package_unit_quantity": new_product.package_unit_quantity,
            })
            self.selected_product = self.products[-1]

            # Collapse form
            self._cancel_inline_create()

            # Trigger price hint update
            self._on_supplier_change(self.supplier_var.get())

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to create product: {str(e)}",
                parent=self,
            )
            # Keep form expanded for correction

    def _cancel_inline_create(self):
        """Cancel inline product creation (WP08)."""
        # Clear form
        self.inline_name_entry.delete(0, "end")
        self.inline_qty_entry.delete(0, "end")
        self.inline_unit_combo.set("")
        self.inline_supplier_combo.set("")

        # Collapse
        self.inline_create_frame.grid_forget()
        self.inline_create_expanded = False

        # Re-enable product dropdown and focus
        self.product_combo.configure(state="normal")
        self.product_combo.focus_set()

    # ==========================================================================
    # End WP08 Methods
    # ==========================================================================

    def _get_selected_product_id(self) -> Optional[int]:
        """Get product_id from current product dropdown selection (F028, F029)."""
        # F029: Use tracked selected_product from type-ahead combo
        if self.selected_product:
            return self.selected_product.get("id")

        # Fallback: try to match from combo value
        product_display = self.product_combo.get().strip()
        if not product_display:
            return None

        # Strip star prefix if present
        product_display = strip_star_prefix(product_display)

        product = next(
            (p for p in self.products
             if self._format_product_display(p) == product_display
             or p.get("brand") == product_display),
            None,
        )
        return product["id"] if product else None

    def _get_selected_supplier_id(self) -> Optional[int]:
        """Get supplier_id from current supplier dropdown selection (F028, F029)."""
        supplier_name = self.supplier_var.get().strip()
        if not supplier_name or supplier_name == "No suppliers":
            return None
        # F029: Strip star indicator if present
        supplier_name = self._strip_star_from_supplier(supplier_name)
        supplier = next(
            (s for s in self.suppliers if s["display_name"] == supplier_name),
            None,
        )
        return supplier["id"] if supplier else None

    def _on_supplier_change(self, selected_value: str):
        """Handle supplier selection change - update price hint (F028)."""
        product_id = self._get_selected_product_id()
        supplier_id = self._get_selected_supplier_id()

        if not product_id or not supplier_id:
            self.price_hint_label.configure(text="")
            return

        try:
            # Try supplier-specific price first
            result = purchase_service.get_last_price_at_supplier(product_id, supplier_id)

            if result:
                # History at this supplier
                price = result["unit_price"]
                date_str = result["purchase_date"]
                self.price_var.set(price)
                self.price_hint_label.configure(text=f"(last paid: ${price} on {date_str})")
            else:
                # Fallback to any supplier
                result = purchase_service.get_last_price_any_supplier(product_id)
                if result:
                    price = result["unit_price"]
                    date_str = result["purchase_date"]
                    supplier_name = result["supplier_name"]
                    self.price_var.set(price)
                    self.price_hint_label.configure(text=f"(last paid: ${price} at {supplier_name} on {date_str})")
                else:
                    # No history
                    self.price_var.set("")
                    self.price_hint_label.configure(text="(no purchase history)")
        except Exception as e:
            self.price_hint_label.configure(text="(error loading price)")

    def _populate_form(self):  # noqa: C901
        """Populate form with existing item data."""
        if not self.item:
            return

        try:
            # F029: For editing, we need to set category first, then ingredient, then product
            ingredient_name = self.item.get("ingredient_name")
            if ingredient_name:
                # Find the category for this ingredient
                ingredient = next(
                    (ing for ing in self.ingredients if ing["name"] == ingredient_name),
                    None,
                )
                if ingredient:
                    category = ingredient.get("category", "")
                    if category:
                        self.category_combo.set(category)
                        self._on_category_selected(category)

                    # Set ingredient
                    self.ingredient_combo.set(ingredient_name)
                    self._on_ingredient_selected(ingredient_name)

            product_id = self.item.get("product_id")
            display = None
            if product_id and self.products:
                for product in self.products:
                    if product["id"] == product_id:
                        display = self._format_product_display(product)
                        self.selected_product = product
                        break
            if display:
                self.product_combo.set(display)

            # Set quantity
            self.quantity_entry.delete(0, "end")
            self.quantity_entry.insert(0, str(self.item.get("quantity", "")))

            # Set purchase date
            purchase_date = self.item.get("purchase_date")
            if purchase_date:
                self.purchase_date_entry.delete(0, "end")
                self.purchase_date_entry.insert(0, purchase_date.strftime("%Y-%m-%d"))

            # Set expiration date
            expiration_date = self.item.get("expiration_date")
            if expiration_date:
                self.expiration_date_entry.delete(0, "end")
                self.expiration_date_entry.insert(0, expiration_date.strftime("%Y-%m-%d"))

            # Set location
            location = self.item.get("location")
            if location:
                self.location_entry.delete(0, "end")
                self.location_entry.insert(0, location)

            # Set notes
            notes = self.item.get("notes")
            if notes:
                self.notes_text.delete("1.0", "end")
                self.notes_text.insert("1.0", notes)

            # Prevent editing immutable fields (F029: use combo boxes)
            self.category_combo.configure(state="disabled")
            self.ingredient_combo.configure(state="disabled")
            self.product_combo.configure(state="disabled")
            self.purchase_date_entry.configure(state="disabled")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to populate form: {str(e)}", parent=self)

    def _save(self):  # noqa: C901
        """Validate and save form data."""
        from decimal import Decimal

        # Get values (F029: use combo boxes)
        category = strip_star_prefix(self.category_combo.get()).strip()
        ingredient_name = strip_star_prefix(self.ingredient_combo.get()).strip()
        product_display = strip_star_prefix(self.product_combo.get()).strip()
        quantity_str = self.quantity_entry.get().strip()
        purchase_date_str = self.purchase_date_entry.get().strip()
        expiration_date_str = self.expiration_date_entry.get().strip()
        location = self.location_entry.get().strip()
        notes = self.notes_text.get("1.0", "end").strip()

        # Validate required fields (F029: check for category too)
        if not category:
            messagebox.showerror("Validation Error", "Please select a category", parent=self)
            return

        if not ingredient_name:
            messagebox.showerror("Validation Error", "Please select an ingredient", parent=self)
            return

        if not product_display or is_separator(product_display) or is_create_new_option(product_display):
            messagebox.showerror("Validation Error", "Please select a product", parent=self)
            return

        if not quantity_str:
            messagebox.showerror("Validation Error", "Quantity is required", parent=self)
            return

        if not purchase_date_str:
            messagebox.showerror("Validation Error", "Purchase date is required", parent=self)
            return

        is_editing = self.item is not None
        item_data: Dict[str, Any] = self.item or {}

        # Parse and validate quantity
        try:
            quantity = Decimal(quantity_str)
            if quantity <= 0:
                messagebox.showerror(
                    "Validation Error", "Quantity must be greater than 0", parent=self
                )
                return
        except Exception:
            messagebox.showerror("Validation Error", "Invalid quantity format", parent=self)
            return

        # Parse purchase date
        if is_editing and item_data.get("purchase_date"):
            purchase_date = item_data["purchase_date"]
        else:
            try:
                purchase_date = date.fromisoformat(purchase_date_str)
            except Exception:
                messagebox.showerror(
                    "Validation Error",
                    "Invalid purchase date format (use YYYY-MM-DD)",
                    parent=self,
                )
                return

        # Parse expiration date (optional)
        expiration_date = None
        if expiration_date_str:
            try:
                expiration_date = date.fromisoformat(expiration_date_str)
                if expiration_date < purchase_date:
                    messagebox.showerror(
                        "Validation Error",
                        "Expiration date must be after purchase date",
                        parent=self,
                    )
                    return
            except Exception:
                messagebox.showerror(
                    "Validation Error",
                    "Invalid expiration date format (use YYYY-MM-DD)",
                    parent=self,
                )
                return

        # Determine product ID
        if is_editing:
            product_id = item_data.get("product_id")
        else:
            product = next(
                (p for p in self.products if self._format_product_display(p) == product_display),
                None,
            )
            if not product:
                messagebox.showerror("Validation Error", "Selected product not found", parent=self)
                return
            product_id = product["id"]

        # F028: Validate supplier (required for new items)
        supplier_id = None
        if not is_editing:
            supplier_id = self._get_selected_supplier_id()
            if not supplier_id:
                messagebox.showerror("Validation Error", "Please select a supplier", parent=self)
                return

        # F028: Validate and parse price (required for new items)
        unit_price = None
        if not is_editing:
            price_str = self.price_var.get().strip()
            if not price_str:
                messagebox.showerror("Validation Error", "Unit price is required", parent=self)
                return

            try:
                unit_price = Decimal(price_str)
            except Exception:
                messagebox.showerror("Validation Error", "Invalid price format", parent=self)
                return

            # F028 FR-008: Reject negative prices
            if unit_price < 0:
                messagebox.showerror("Validation Error", "Price cannot be negative", parent=self)
                return

            # F028 FR-007: Warn on zero price
            if unit_price == Decimal("0"):
                confirm = messagebox.askyesno(
                    "Confirm Zero Price",
                    "Price is $0.00. This may indicate a donation or free sample.\n\nProceed with zero price?",
                    parent=self,
                )
                if not confirm:
                    return

        # Build result
        self.result = {
            "quantity": quantity,
        }

        if not is_editing:
            self.result["product_id"] = product_id
            self.result["supplier_id"] = supplier_id  # F028
            self.result["unit_price"] = unit_price  # F028
            self.result["purchase_date"] = purchase_date

        if expiration_date:
            self.result["expiration_date"] = expiration_date
        if location:
            self.result["location"] = location
        if notes:
            self.result["notes"] = notes

        # F029: Update session state on successful add (not edit)
        if not is_editing:
            if supplier_id:
                self.session_state.update_supplier(supplier_id)
            if category:
                self.session_state.update_category(category)

        self.destroy()

    # WP09: Clear price hint when user types

    def _on_price_key(self, event):
        """Clear hint when user types in price field (WP09)."""
        # Ignore navigation keys
        if event.keysym not in ('Tab', 'Return', 'Escape', 'Up', 'Down', 'Left', 'Right'):
            self.price_hint_label.configure(text="")

    # WP10: Validation methods for price and quantity

    def _on_price_focus_out(self, event):
        """Validate price when focus leaves field."""
        self._validate_price()

    def _on_quantity_focus_out(self, event):
        """Validate quantity when focus leaves field."""
        self._validate_quantity()

    def _validate_price(self) -> bool:
        """Validate price value.

        Returns:
            True if valid or empty, False if invalid.
        """
        price_str = self.price_entry.get().strip()
        if not price_str:
            return True  # Empty is OK, will be caught on submit

        try:
            price = Decimal(price_str)
        except InvalidOperation:
            return True  # Invalid format caught on submit

        # Check for negative price
        if price < 0:
            messagebox.showerror(
                "Invalid Price",
                "Price cannot be negative.",
                parent=self,
            )
            self.price_entry.focus_set()
            return False

        # Check for high price (> $100)
        if price > 100:
            if not self._confirm_high_price(price):
                self.price_entry.focus_set()
                return False

        return True

    def _confirm_high_price(self, price: Decimal) -> bool:
        """Ask user to confirm high price.

        Args:
            price: The price value to confirm.

        Returns:
            True if user confirms, False if user cancels.
        """
        return messagebox.askyesno(
            "Confirm High Price",
            f"Price is ${price:.2f} (over $100).\n\nIs this correct?",
            parent=self,
        )

    def _validate_quantity(self) -> bool:
        """Validate quantity value.

        Returns:
            True if valid or empty, False if invalid.
        """
        qty_str = self.quantity_entry.get().strip()
        if not qty_str:
            return True  # Empty OK, caught on submit

        try:
            qty = Decimal(qty_str)
        except InvalidOperation:
            return True  # Invalid format caught on submit

        # Check for count-based unit with decimal quantity
        if self.selected_product and self._is_count_based_unit():
            if qty != qty.to_integral_value():
                if not self._confirm_decimal_quantity(qty):
                    self.quantity_entry.focus_set()
                    return False

        return True

    def _confirm_decimal_quantity(self, qty: Decimal) -> bool:
        """Ask user to confirm decimal quantity for count-based unit.

        Args:
            qty: The quantity value to confirm.

        Returns:
            True if user confirms, False if user cancels.
        """
        return messagebox.askyesno(
            "Confirm Decimal Quantity",
            f"Package quantities are usually whole numbers.\n\n"
            f"You entered {qty}. Continue?",
            parent=self,
        )

    def _is_count_based_unit(self) -> bool:
        """Check if selected product uses count-based unit.

        Returns:
            True if the product's package_unit is count-based, False otherwise.
        """
        if not self.selected_product:
            return False
        unit = self.selected_product.get("package_unit", "").lower()
        return unit in COUNT_BASED_UNITS


class ConsumeIngredientDialog(ctk.CTkToplevel):
    """
    Dialog for consuming ingredients using FIFO logic.

    Features:
    - Ingredient selection
    - Quantity input
    - FIFO preview showing which lots will be consumed
    - Insufficient inventory warnings
    - Consumption result display with breakdown
    """

    def __init__(self, parent):
        """
        Initialize the consumption dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.title("Consume Ingredient")
        self.geometry("700x650")
        self.resizable(False, False)

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        self.result: Optional[Dict[str, Any]] = None
        self.ingredients = []
        self.preview_data = None

        # Load data
        self._load_ingredients()

        # Create form
        self._create_form()

    def _load_ingredients(self):
        """Load ingredients that have inventory items."""
        try:
            # Get all ingredients
            all_ingredients = ingredient_service.get_all_ingredients()

            # Filter to only ingredients with inventory items
            self.ingredients = []
            for ing in all_ingredients:
                try:
                    totals = inventory_item_service.get_total_quantity(ing["slug"])
                    if totals:  # Dict with at least one unit
                        # Format as "X unit, Y unit2" for display
                        parts = [f"{float(qty):.2f} {unit}" for unit, qty in totals.items()]
                        ing["total_quantity_display"] = ", ".join(parts)
                        self.ingredients.append(ing)
                except Exception:
                    continue

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load ingredients: {str(e)}", parent=self)
            self.destroy()

    def _create_form(self):
        """Create form fields."""
        # Configure grid
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        row = 0

        # Title
        title_label = ctk.CTkLabel(
            self,
            text="Consume Ingredient (FIFO)",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title_label.grid(row=row, column=0, columnspan=2, padx=10, pady=(10, 20), sticky="w")
        row += 1

        # Ingredient dropdown
        ing_label = ctk.CTkLabel(self, text="Ingredient:*")
        ing_label.grid(row=row, column=0, padx=10, pady=10, sticky="w")

        ingredient_names = [
            f"{ing['name']} (Available: {ing.get('total_quantity_display', 'N/A')})"
            for ing in self.ingredients
        ]
        self.ingredient_var = ctk.StringVar(
            value="" if not self.ingredients else ingredient_names[0]
        )
        self.ingredient_dropdown = ctk.CTkOptionMenu(
            self,
            variable=self.ingredient_var,
            values=ingredient_names if ingredient_names else ["No ingredients with inventory"],
            command=self._on_ingredient_change,
        )
        self.ingredient_dropdown.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
        row += 1

        # Quantity
        qty_label = ctk.CTkLabel(self, text="Quantity to Consume:*")
        qty_label.grid(row=row, column=0, padx=10, pady=10, sticky="w")

        self.quantity_entry = ctk.CTkEntry(self, placeholder_text="e.g., 10")
        self.quantity_entry.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
        self.quantity_entry.bind("<KeyRelease>", lambda e: self._update_preview())
        row += 1

        # Preview button
        preview_button = ctk.CTkButton(
            self,
            text="Show FIFO Preview",
            command=self._update_preview,
            width=150,
        )
        preview_button.grid(row=row, column=0, columnspan=2, padx=10, pady=10)
        row += 1

        # Preview frame
        preview_frame = ctk.CTkFrame(self)
        preview_frame.grid(row=row, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        preview_frame.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(row, weight=1)

        # Scrollable preview area
        self.preview_text = ctk.CTkTextbox(preview_frame, height=300)
        self.preview_text.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        preview_frame.grid_rowconfigure(0, weight=1)
        self.preview_text.configure(state="disabled")

        row += 1

        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=row, column=0, columnspan=2, padx=10, pady=20, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.destroy,
        )
        cancel_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.consume_btn = ctk.CTkButton(
            button_frame,
            text="Consume",
            command=self._execute_consumption,
            fg_color="darkorange",
            hover_color="orange",
        )
        self.consume_btn.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.consume_btn.configure(state="disabled")

    def _on_ingredient_change(self, value: str):
        """Handle ingredient selection change."""
        # Clear preview when ingredient changes
        self._clear_preview()

    def _clear_preview(self):
        """Clear the preview display."""
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.configure(state="disabled")
        self.preview_data = None
        self.consume_btn.configure(state="disabled")

    def _update_preview(self):  # noqa: C901
        """Update FIFO preview based on current selections."""
        from decimal import Decimal

        # Get selected ingredient
        ingredient_display = self.ingredient_var.get().strip()
        if not ingredient_display or ingredient_display == "No ingredients with inventory":
            self._show_preview_message("Please select an ingredient first.")
            return

        # Extract ingredient name from display (remove availability info)
        ingredient_name = ingredient_display.split(" (Available:")[0]
        ingredient = next((ing for ing in self.ingredients if ing["name"] == ingredient_name), None)
        if not ingredient:
            self._show_preview_message("Selected ingredient not found.")
            return

        # Get quantity
        quantity_str = self.quantity_entry.get().strip()
        if not quantity_str:
            self._show_preview_message("Please enter a quantity to consume.")
            return

        try:
            quantity = Decimal(quantity_str)
            if quantity <= 0:
                self._show_preview_message("Quantity must be greater than 0.")
                return
        except Exception:
            self._show_preview_message("Invalid quantity format.")
            return

        # Call service to get FIFO preview (dry run)
        try:
            # Get the target unit from the preferred product's package_unit
            preferred = product_service.get_preferred_product(ingredient["slug"])
            if preferred:
                target_unit = preferred.package_unit or "unit"
            else:
                # Fall back to first product's package_unit
                products = product_service.get_products_for_ingredient(ingredient["slug"])
                target_unit = products[0].package_unit if products else "unit"

            result = inventory_item_service.consume_fifo(ingredient["slug"], quantity, target_unit)
            self.preview_data = result

            # Build preview message
            preview_message = f"FIFO Consumption Preview for {ingredient['name']}\n"
            preview_message += "=" * 60 + "\n\n"

            if result["satisfied"]:
                preview_message += f"✓ Requested: {quantity} {target_unit}\n"
                preview_message += (
                    f"✓ Will consume: {result['consumed']} {target_unit}\n"
                )
                preview_message += "✓ Status: SATISFIED\n\n"

                preview_message += f"Will consume from {len(result['breakdown'])} lot(s):\n"
                preview_message += "-" * 60 + "\n"

                for idx, lot_consumption in enumerate(result["breakdown"], 1):
                    preview_message += f"\nLot {idx}:\n"
                    preview_message += f"  Purchase Date: {lot_consumption['lot_date']}\n"
                    preview_message += f"  Quantity Consumed: {lot_consumption['quantity_consumed']} {lot_consumption['unit']}\n"
                    preview_message += f"  Remaining in Lot: {lot_consumption['remaining_in_lot']} {lot_consumption['unit']}\n"

                self._show_preview_message(preview_message, success=True)
                self.consume_btn.configure(state="normal")

            else:
                # Insufficient inventory
                preview_message += f"⚠ Requested: {quantity} {target_unit}\n"
                preview_message += (
                    f"⚠ Available: {result['consumed']} {target_unit}\n"
                )
                preview_message += (
                    f"⚠ Shortfall: {result['shortfall']} {target_unit}\n"
                )
                preview_message += "⚠ Status: INSUFFICIENT INVENTORY\n\n"

                if result["breakdown"]:
                    preview_message += (
                        f"Can partially consume from {len(result['breakdown'])} lot(s):\n"
                    )
                    preview_message += "-" * 60 + "\n"

                    for idx, lot_consumption in enumerate(result["breakdown"], 1):
                        preview_message += f"\nLot {idx}:\n"
                        preview_message += f"  Purchase Date: {lot_consumption['lot_date']}\n"
                        preview_message += f"  Quantity Consumed: {lot_consumption['quantity_consumed']} {lot_consumption['unit']}\n"
                        preview_message += f"  Remaining in Lot: {lot_consumption['remaining_in_lot']} {lot_consumption['unit']}\n"

                self._show_preview_message(preview_message, warning=True)
                # Allow consumption even with shortfall (partial consumption)
                self.consume_btn.configure(state="normal")

        except Exception as e:
            self._show_preview_message(f"Error generating preview: {str(e)}", error=True)
            self.consume_btn.configure(state="disabled")

    def _show_preview_message(self, message: str, success=False, warning=False, error=False):
        """Display message in preview area."""
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", message)
        self.preview_text.configure(state="disabled")

    def _execute_consumption(self):
        """Execute the FIFO consumption."""
        if not self.preview_data:
            messagebox.showerror("Error", "Please generate preview first", parent=self)
            return

        # Confirm consumption
        ingredient_display = self.ingredient_var.get().strip()
        ingredient_name = ingredient_display.split(" (Available:")[0]
        quantity_str = self.quantity_entry.get().strip()

        if self.preview_data["satisfied"]:
            confirm_msg = f"Consume {quantity_str} from {ingredient_name}?\n\n"
            confirm_msg += f"This will consume from {len(self.preview_data['breakdown'])} lot(s)."
        else:
            confirm_msg = f"Partial consumption: {quantity_str} requested but only {self.preview_data['consumed']} available.\n\n"
            confirm_msg += f"Shortfall: {self.preview_data['shortfall']}\n\n"
            confirm_msg += "Proceed with partial consumption?"

        result = messagebox.askyesno("Confirm Consumption", confirm_msg, parent=self)

        if result:
            # Show success message with breakdown
            success_msg = "Consumption Complete!\n\n"
            success_msg += f"Ingredient: {ingredient_name}\n"
            success_msg += f"Consumed: {self.preview_data['consumed']}\n"

            if self.preview_data["shortfall"] > 0:
                success_msg += f"Shortfall: {self.preview_data['shortfall']}\n"

            success_msg += f"\nLots Updated: {len(self.preview_data['breakdown'])}\n"

            messagebox.showinfo("Success", success_msg, parent=self)

            # Set result and close
            self.result = {
                "ingredient": ingredient_name,
                "consumed": self.preview_data["consumed"],
                "breakdown": self.preview_data["breakdown"],
            }
            self.destroy()
