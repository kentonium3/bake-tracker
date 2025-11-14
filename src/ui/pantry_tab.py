"""
My Pantry tab for displaying and managing pantry inventory.

Provides interface for:
- Viewing pantry inventory in aggregate or detail mode
- Adding new pantry items (lots)
- Editing existing pantry items
- Deleting pantry items
- Filtering by location
- Expiration alerts (visual indicators)
"""

import customtkinter as ctk
from tkinter import messagebox
from datetime import date
from typing import Optional, List, Dict, Any

from src.services import pantry_service, ingredient_service, variant_service
from src.services.exceptions import (
    PantryItemNotFound,
    ValidationError as ServiceValidationError,
    DatabaseError,
)


class PantryTab(ctk.CTkFrame):
    """
    My Pantry tab for inventory management.

    Displays pantry items in two modes:
    - Aggregate: Grouped by ingredient showing totals
    - Detail: Individual pantry items (lots) with purchase dates

    Features:
    - Location filter
    - Expiration alerts (yellow < 14 days, red expired)
    - CRUD operations for pantry items
    """

    def __init__(self, parent):
        """Initialize the pantry tab."""
        super().__init__(parent)

        # State
        self.pantry_items = []  # All pantry items
        self.filtered_items = []  # Items after filtering
        self.view_mode = "detail"  # "aggregate" or "detail"
        self.selected_location = "All Locations"

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Header - fixed height
        self.grid_rowconfigure(1, weight=0)  # Controls - fixed height
        self.grid_rowconfigure(2, weight=1)  # Item list - expandable

        # Create UI components
        self._create_header()
        self._create_controls()
        self._create_item_list()

        # Grid the frame
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Initial load
        self.refresh()

    def _create_header(self):
        """Create the header with title."""
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header_frame,
            text="My Pantry - Inventory Management",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        subtitle = ctk.CTkLabel(
            header_frame,
            text="View and manage your pantry inventory with lot tracking and FIFO visibility",
            font=ctk.CTkFont(size=12),
        )
        subtitle.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")

    def _create_controls(self):
        """Create control buttons and filters."""
        controls_frame = ctk.CTkFrame(self)
        controls_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        controls_frame.grid_columnconfigure(4, weight=1)

        # Add Pantry Item button
        add_button = ctk.CTkButton(
            controls_frame,
            text="Add Pantry Item",
            command=self._add_pantry_item,
            width=150,
        )
        add_button.grid(row=0, column=0, padx=5, pady=5)

        # Consume Ingredient button
        consume_button = ctk.CTkButton(
            controls_frame,
            text="Consume Ingredient",
            command=self._consume_ingredient,
            width=150,
            fg_color="darkorange",
            hover_color="orange",
        )
        consume_button.grid(row=1, column=0, padx=5, pady=5)

        # View mode toggle
        view_label = ctk.CTkLabel(controls_frame, text="View Mode:")
        view_label.grid(row=0, column=1, padx=(20, 5), pady=5)

        self.view_mode_var = ctk.StringVar(value="Detail")
        view_mode_dropdown = ctk.CTkOptionMenu(
            controls_frame,
            variable=self.view_mode_var,
            values=["Detail", "Aggregate"],
            command=self._on_view_mode_change,
            width=120,
        )
        view_mode_dropdown.grid(row=0, column=2, padx=5, pady=5)

        # Location filter
        location_label = ctk.CTkLabel(controls_frame, text="Location:")
        location_label.grid(row=0, column=3, padx=(20, 5), pady=5)

        self.location_var = ctk.StringVar(value="All Locations")
        self.location_dropdown = ctk.CTkOptionMenu(
            controls_frame,
            variable=self.location_var,
            values=["All Locations"],
            command=self._on_location_change,
            width=150,
        )
        self.location_dropdown.grid(row=0, column=4, padx=5, pady=5, sticky="w")

        # Refresh button
        refresh_button = ctk.CTkButton(
            controls_frame,
            text="Refresh",
            command=self.refresh,
            width=100,
        )
        refresh_button.grid(row=0, column=5, padx=5, pady=5, sticky="e")

    def _create_item_list(self):
        """Create scrollable list for displaying pantry items."""
        # Container frame - make taller and wider
        list_frame = ctk.CTkFrame(self)
        list_frame.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)

        # Scrollable frame - wider minimum width
        self.scrollable_frame = ctk.CTkScrollableFrame(list_frame, height=500, width=1000)
        self.scrollable_frame.grid(row=0, column=0, sticky="nsew")
        self.scrollable_frame.grid_columnconfigure(0, weight=1)

    def refresh(self):
        """Refresh pantry list from database."""
        try:
            # Get all pantry items from service (returns PantryItem instances)
            self.pantry_items = pantry_service.get_pantry_items()

            # Update location dropdown with unique locations
            locations = sorted(
                {
                    str(item.location)
                    for item in self.pantry_items
                    if getattr(item, "location", None)
                }
            )
            location_list = ["All Locations"] + locations
            self.location_dropdown.configure(values=location_list)

            # Apply filters
            self._apply_filters()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to load pantry items: {str(e)}",
                parent=self,
            )

    def _apply_filters(self):
        """Apply location filter and update display."""
        # Filter by location
        if self.selected_location == "All Locations":
            self.filtered_items = list(self.pantry_items)
        else:
            self.filtered_items = [
                item
                for item in self.pantry_items
                if (item.location or "") == self.selected_location
            ]

        # Update display based on view mode
        self._update_display()

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

    def _show_empty_state(self):
        """Show empty state message."""
        empty_label = ctk.CTkLabel(
            self.scrollable_frame,
            text="No pantry inventory.\nClick 'Add Pantry Item' to record purchases.",
            font=ctk.CTkFont(size=16),
        )
        empty_label.grid(row=0, column=0, padx=20, pady=50)

    def _display_aggregate_view(self):
        """Display pantry items grouped by ingredient with totals."""
        # Group items by ingredient
        from collections import defaultdict

        ingredient_groups = defaultdict(list)

        for item in self.filtered_items:
            variant = getattr(item, "variant", None)
            ingredient = getattr(variant, "ingredient", None) if variant else None
            ingredient_slug = getattr(ingredient, "slug", None)
            if ingredient_slug:
                ingredient_groups[ingredient_slug].append(item)

        # Create header
        self._create_aggregate_header()

        # Display each ingredient group
        for idx, (ingredient_slug, items) in enumerate(sorted(ingredient_groups.items())):
            self._create_aggregate_row(idx + 1, ingredient_slug, items)

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

        # Get ingredient info
        ingredient_obj = None
        try:
            ingredient_obj = ingredient_service.get_ingredient(ingredient_slug)
        except Exception:
            ingredient_obj = None

        ingredient_name = getattr(ingredient_obj, "name", ingredient_slug)

        # Calculate total quantity using new service function
        try:
            unit_totals = pantry_service.get_total_quantity(ingredient_slug)
            if unit_totals:
                # Format as "25 lb + 3 cup" style display
                qty_parts = []
                for unit, total in unit_totals.items():
                    if total > 0:
                        if total == int(total):
                            qty_parts.append(f"{int(total)} {unit}")
                        else:
                            qty_parts.append(f"{total:.1f} {unit}")

                qty_display = " + ".join(qty_parts) if qty_parts else "0"
            else:
                qty_display = "0"
        except Exception:
            qty_display = "N/A"

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

        # Ingredient name
        name_label = ctk.CTkLabel(
            row_frame,
            text=ingredient_name,
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
        """Display individual pantry items (lots)."""
        # Create header
        self._create_detail_header()

        # Sort items by purchase date (FIFO order - oldest first)
        sorted_items = sorted(
            self.filtered_items,
            key=lambda x: getattr(x, "purchase_date", None) or date.today(),
        )

        # Display each item
        for idx, item in enumerate(sorted_items):
            self._create_detail_row(idx + 1, item)

    def _create_detail_header(self):
        """Create header for detail view."""
        header_frame = ctk.CTkFrame(self.scrollable_frame)
        header_frame.grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        header_frame.grid_columnconfigure(2, weight=1)

        headers = [
            ("Ingredient", 0, 180),
            ("Variant", 1, 200),
            ("Quantity", 2, 120),  # Wider quantity column
            ("Purchase Date", 3, 110),
            ("Expiration", 4, 110),
            ("Location", 5, 120),
            ("Actions", 6, 180),
        ]

        for text, col, width in headers:
            label = ctk.CTkLabel(
                header_frame,
                text=text,
                font=ctk.CTkFont(weight="bold"),
                width=width,
            )
            label.grid(row=0, column=col, padx=3, pady=3, sticky="w")

    def _create_detail_row(self, row_idx: int, item: dict):
        """Create a row for individual pantry item."""
        row_frame = ctk.CTkFrame(self.scrollable_frame)
        row_frame.grid(row=row_idx, column=0, padx=2, pady=1, sticky="ew")  # Denser spacing
        row_frame.grid_columnconfigure(2, weight=1)

        # Get ingredient and variant info
        variant_obj = getattr(item, "variant", None)
        ingredient_obj = getattr(variant_obj, "ingredient", None) if variant_obj else None

        ingredient_name = getattr(ingredient_obj, "name", "Unknown")
        brand = getattr(variant_obj, "brand", "Unknown") if variant_obj else "Unknown"
        # Get package size info for variant display (purchase_quantity = package size)
        package_size = getattr(variant_obj, "purchase_quantity", None)
        inventory_unit = getattr(variant_obj, "purchase_unit", "") or ""

        # Create descriptive variant name showing brand and package size
        if package_size and inventory_unit:
            variant_name = f"{brand} ({package_size} {inventory_unit} package)".strip()
        else:
            variant_name = brand

        # Check expiration status
        expiration_date = getattr(item, "expiration_date", None)
        warning_color = None
        expiration_text = "None"

        if expiration_date:
            expiration_text = expiration_date.strftime("%Y-%m-%d")
            days_until_expiry = (expiration_date - date.today()).days

            if days_until_expiry < 0:
                warning_color = "#8B0000"  # Dark red for expired
                expiration_text = f"EXPIRED ({expiration_text})"
            elif days_until_expiry <= 14:
                warning_color = "#DAA520"  # Goldenrod for expiring soon
                expiration_text = f"⚠️ {expiration_text}"

        if warning_color:
            row_frame.configure(fg_color=warning_color)

        # Ingredient name
        ing_label = ctk.CTkLabel(
            row_frame,
            text=ingredient_name,
            width=180,  # Match header width
            anchor="w",
        )
        ing_label.grid(row=0, column=0, padx=3, pady=3, sticky="w")

        # Variant
        variant_label = ctk.CTkLabel(
            row_frame,
            text=variant_name,
            width=200,  # Match header width
            anchor="w",
        )
        variant_label.grid(row=0, column=1, padx=3, pady=3, sticky="w")

        # Quantity - improved formatting
        qty_value = getattr(item, "quantity", 0)
        if isinstance(qty_value, (int, float)) and qty_value != 0:
            # Format numbers nicely - remove trailing zeros
            if qty_value == int(qty_value):
                qty_text = str(int(qty_value))
            else:
                qty_text = f"{qty_value:.1f}"
        else:
            qty_text = "0"

        qty_label = ctk.CTkLabel(
            row_frame,
            text=f"{qty_text} {inventory_unit}".strip(),
            width=120,  # Wider to match header
            anchor="w",
            font=ctk.CTkFont(weight="bold"),  # Make quantity more prominent
        )
        qty_label.grid(row=0, column=2, padx=3, pady=3, sticky="w")

        # Purchase date
        purchase_date = getattr(item, "purchase_date", None)
        purchase_str = purchase_date.strftime("%Y-%m-%d") if purchase_date else "N/A"
        purchase_label = ctk.CTkLabel(
            row_frame,
            text=purchase_str,
            width=110,  # Match header width
            anchor="w",
        )
        purchase_label.grid(row=0, column=3, padx=3, pady=3, sticky="w")

        # Expiration date
        exp_label = ctk.CTkLabel(
            row_frame,
            text=expiration_text,
            width=110,  # Match header width
            anchor="w",
        )
        exp_label.grid(row=0, column=4, padx=3, pady=3, sticky="w")

        # Location
        location_label = ctk.CTkLabel(
            row_frame,
            text=getattr(item, "location", "N/A"),
            width=120,  # Match header width
            anchor="w",
        )
        location_label.grid(row=0, column=5, padx=3, pady=3, sticky="w")

        # Actions
        actions_frame = ctk.CTkFrame(row_frame)
        actions_frame.grid(row=0, column=6, padx=3, pady=3)

        edit_btn = ctk.CTkButton(
            actions_frame,
            text="Edit",
            command=lambda: self._edit_pantry_item(item["id"]),
            width=80,
        )
        edit_btn.grid(row=0, column=0, padx=2)

        delete_btn = ctk.CTkButton(
            actions_frame,
            text="Delete",
            command=lambda: self._delete_pantry_item(item["id"]),
            width=80,
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

    def _on_location_change(self, value: str):
        """Handle location filter change."""
        self.selected_location = value
        self._apply_filters()

    def _view_ingredient_details(self, ingredient_slug: str):
        """Switch to detail view filtered to specific ingredient."""
        # Switch to detail mode
        self.view_mode = "detail"
        self.view_mode_var.set("Detail")

        # Filter to specific ingredient
        self.filtered_items = [
            item
            for item in self.pantry_items
            if getattr(getattr(item, "variant", None), "ingredient", None)
            and item.variant.ingredient.slug == ingredient_slug
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
            getattr(getattr(item, "variant", None), "ingredient", None)
            and item.variant.ingredient.slug == ingredient_slug
            for item in self.pantry_items
        ):
            self.refresh()

        if not any(
            getattr(getattr(item, "variant", None), "ingredient", None)
            and item.variant.ingredient.slug == ingredient_slug
            for item in self.pantry_items
        ):
            messagebox.showinfo(
                "No Pantry Items",
                f"No pantry inventory found for ingredient '{ingredient_slug}'.",
                parent=self,
            )
            return

        self.view_mode = "detail"
        self.view_mode_var.set("Detail")
        self.selected_location = "All Locations"
        self.location_var.set("All Locations")

        self.filtered_items = [
            item
            for item in self.pantry_items
            if getattr(getattr(item, "variant", None), "ingredient", None)
            and item.variant.ingredient.slug == ingredient_slug
        ]
        self._update_display()

    def _add_pantry_item(self):
        """Open dialog to add new pantry item."""
        dialog = PantryItemFormDialog(self, title="Add Pantry Item")
        self.wait_window(dialog)

        if not dialog.result:
            return

        try:
            # Create pantry item via service
            pantry_service.add_to_pantry(
                variant_id=dialog.result["variant_id"],
                quantity=dialog.result["quantity"],
                purchase_date=dialog.result["purchase_date"],
                expiration_date=dialog.result.get("expiration_date"),
                location=dialog.result.get("location"),
                notes=dialog.result.get("notes"),
            )

            messagebox.showinfo(
                "Success",
                "Pantry item added successfully",
                parent=self,
            )
            self.refresh()

        except ServiceValidationError as e:
            messagebox.showerror("Validation Error", str(e), parent=self)
        except DatabaseError as e:
            messagebox.showerror("Database Error", str(e), parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add pantry item: {str(e)}", parent=self)

    def _edit_pantry_item(self, pantry_item_id: int):
        """Open dialog to edit pantry item."""
        try:
            # Get current item data
            item = next((i for i in self.pantry_items if i.id == pantry_item_id), None)
            if not item:
                messagebox.showerror("Error", "Pantry item not found", parent=self)
                return

            dialog = PantryItemFormDialog(
                self,
                title="Edit Pantry Item",
                item=self._serialize_pantry_item(item),
            )
            self.wait_window(dialog)

            if not dialog.result:
                return

            # Update pantry item via service
            pantry_service.update_pantry_item(pantry_item_id, dialog.result)

            messagebox.showinfo(
                "Success",
                "Pantry item updated successfully",
                parent=self,
            )
            self.refresh()

        except PantryItemNotFound:
            messagebox.showerror("Error", "Pantry item not found", parent=self)
            self.refresh()
        except ServiceValidationError as e:
            messagebox.showerror("Validation Error", str(e), parent=self)
        except DatabaseError as e:
            messagebox.showerror("Database Error", str(e), parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update pantry item: {str(e)}", parent=self)

    def _delete_pantry_item(self, pantry_item_id: int):
        """Delete pantry item after confirmation."""
        result = messagebox.askyesno(
            "Confirm Delete",
            "Are you sure you want to delete this pantry item?",
            parent=self,
        )

        if result:
            try:
                pantry_service.delete_pantry_item(pantry_item_id)
                messagebox.showinfo(
                    "Success",
                    "Pantry item deleted successfully",
                    parent=self,
                )
                self.refresh()

            except PantryItemNotFound:
                messagebox.showerror("Error", "Pantry item not found", parent=self)
                self.refresh()
            except DatabaseError as e:
                messagebox.showerror("Database Error", str(e), parent=self)
            except Exception as e:
                messagebox.showerror(
                    "Error", f"Failed to delete pantry item: {str(e)}", parent=self
                )

    def _consume_ingredient(self):
        """Open dialog to consume ingredient using FIFO logic."""
        dialog = ConsumeIngredientDialog(self)
        self.wait_window(dialog)

        if dialog.result:
            self.refresh()

    def _serialize_pantry_item(self, item) -> dict:
        """Convert a PantryItem ORM instance to a simple dict for dialog usage."""
        variant = getattr(item, "variant", None)
        ingredient = getattr(variant, "ingredient", None) if variant else None

        return {
            "id": item.id,
            "variant_id": item.variant_id,
            "quantity": item.quantity,
            "purchase_date": item.purchase_date,
            "expiration_date": item.expiration_date,
            "location": item.location,
            "notes": item.notes,
            "variant_brand": getattr(variant, "brand", None),
            "variant_purchase_quantity": getattr(variant, "purchase_quantity", None),
            "variant_purchase_unit": getattr(variant, "purchase_unit", None),
            "ingredient_name": getattr(ingredient, "name", None),
        }


class PantryItemFormDialog(ctk.CTkToplevel):
    """
    Dialog for creating or editing a pantry item.

    Form fields:
    - Ingredient (dropdown)
    - Variant (dropdown, filtered by ingredient)
    - Quantity (required, > 0)
    - Purchase Date (required)
    - Expiration Date (optional, >= purchase_date)
    - Location (optional)
    - Notes (optional)
    """

    def __init__(self, parent, title="Pantry Item", item: Optional[dict] = None):
        """
        Initialize the form dialog.

        Args:
            parent: Parent widget
            title: Dialog title
            item: Existing pantry item data for editing (None for new)
        """
        super().__init__(parent)

        self.title(title)
        self.geometry("500x600")
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
        self.variants: List[Dict[str, Any]] = []

        # Load data
        self._load_ingredients()

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

    def _create_form(self):
        """Create form fields."""
        # Configure grid
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        row = 0

        # Ingredient dropdown
        ing_label = ctk.CTkLabel(self, text="Ingredient:*")
        ing_label.grid(row=row, column=0, padx=10, pady=10, sticky="w")

        ingredient_names = [ing["name"] for ing in self.ingredients]
        default_ingredient = ingredient_names[0] if ingredient_names else ""
        self.ingredient_var = ctk.StringVar(value=default_ingredient if not self.item else "")
        self.ingredient_dropdown = ctk.CTkOptionMenu(
            self,
            variable=self.ingredient_var,
            values=ingredient_names if ingredient_names else ["No ingredients"],
            command=self._on_ingredient_change,
        )
        self.ingredient_dropdown.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
        row += 1

        # Variant dropdown (populated when ingredient selected)
        variant_label = ctk.CTkLabel(self, text="Variant:*")
        variant_label.grid(row=row, column=0, padx=10, pady=10, sticky="w")

        self.variant_var = ctk.StringVar(value="")
        self.variant_dropdown = ctk.CTkOptionMenu(
            self,
            variable=self.variant_var,
            values=["Select ingredient first"],
        )
        self.variant_dropdown.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
        self.variant_dropdown.configure(state="disabled")
        row += 1

        # Now that variant_dropdown exists, we can safely call _on_ingredient_change
        if default_ingredient and not self.item:
            self._on_ingredient_change(default_ingredient)

        # Quantity
        qty_label = ctk.CTkLabel(self, text="Quantity:*")
        qty_label.grid(row=row, column=0, padx=10, pady=10, sticky="w")

        self.quantity_entry = ctk.CTkEntry(self, placeholder_text="e.g., 25")
        self.quantity_entry.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
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

        self.location_entry = ctk.CTkEntry(self, placeholder_text="e.g., Main Pantry")
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

    def _on_ingredient_change(self, ingredient_name: str):
        """Handle ingredient selection change."""
        # Find ingredient
        ingredient = next((ing for ing in self.ingredients if ing["name"] == ingredient_name), None)
        if not ingredient:
            return

        # Load variants for this ingredient
        try:
            variant_objects = variant_service.get_variants_for_ingredient(ingredient["slug"])
            self.variants = [
                {
                    "id": v.id,
                    "brand": v.brand,
                    "purchase_quantity": v.purchase_quantity,
                    "purchase_unit": v.purchase_unit,
                }
                for v in variant_objects
            ]

            if self.variants:
                variant_names = [self._format_variant_display(v) for v in self.variants]
                self.variant_dropdown.configure(values=variant_names, state="normal")
                self.variant_var.set(variant_names[0])
            else:
                self.variant_dropdown.configure(values=["No variants available"], state="disabled")
                self.variant_var.set("No variants available")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load variants: {str(e)}", parent=self)

    def _format_variant_display(self, variant: dict) -> str:
        """Format a variant dictionary into a human-readable label."""
        brand = variant.get("brand") or "Unknown"
        quantity = variant.get("purchase_quantity")
        unit = variant.get("purchase_unit") or ""
        if quantity:
            return f"{brand} - {quantity} {unit}".strip()
        return brand

    def _populate_form(self):  # noqa: C901
        """Populate form with existing item data."""
        if not self.item:
            return

        try:
            ingredient_name = self.item.get("ingredient_name")
            if ingredient_name:
                self.ingredient_var.set(ingredient_name)
                self._on_ingredient_change(ingredient_name)

            variant_id = self.item.get("variant_id")
            display = None
            if variant_id and self.variants:
                for variant in self.variants:
                    if variant["id"] == variant_id:
                        display = self._format_variant_display(variant)
                        break
            if display:
                self.variant_var.set(display)

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

            # Prevent editing immutable fields
            self.ingredient_dropdown.configure(state="disabled")
            self.variant_dropdown.configure(state="disabled")
            self.purchase_date_entry.configure(state="disabled")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to populate form: {str(e)}", parent=self)

    def _save(self):  # noqa: C901
        """Validate and save form data."""
        from decimal import Decimal

        # Get values
        ingredient_name = self.ingredient_var.get().strip()
        variant_display = self.variant_var.get().strip()
        quantity_str = self.quantity_entry.get().strip()
        purchase_date_str = self.purchase_date_entry.get().strip()
        expiration_date_str = self.expiration_date_entry.get().strip()
        location = self.location_entry.get().strip()
        notes = self.notes_text.get("1.0", "end").strip()

        # Validate required fields
        if not ingredient_name or ingredient_name == "No ingredients":
            messagebox.showerror("Validation Error", "Please select an ingredient", parent=self)
            return

        if not variant_display or variant_display in [
            "Select ingredient first",
            "No variants available",
        ]:
            messagebox.showerror("Validation Error", "Please select a variant", parent=self)
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

        # Determine variant ID
        if is_editing:
            variant_id = item_data.get("variant_id")
        else:
            variant = next(
                (v for v in self.variants if self._format_variant_display(v) == variant_display),
                None,
            )
            if not variant:
                messagebox.showerror("Validation Error", "Selected variant not found", parent=self)
                return
            variant_id = variant["id"]

        # Build result
        self.result = {
            "quantity": quantity,
        }

        if not is_editing:
            self.result["variant_id"] = variant_id
            self.result["purchase_date"] = purchase_date

        if expiration_date:
            self.result["expiration_date"] = expiration_date
        if location:
            self.result["location"] = location
        if notes:
            self.result["notes"] = notes

        self.destroy()


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
        """Load ingredients that have pantry items."""
        try:
            # Get all ingredients
            all_ingredients = ingredient_service.get_all_ingredients()

            # Filter to only ingredients with pantry items
            self.ingredients = []
            for ing in all_ingredients:
                try:
                    total = pantry_service.get_total_quantity(ing["slug"])
                    if total > 0:
                        ing["total_quantity"] = total
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
            f"{ing['name']} (Available: {ing['total_quantity']} {ing.get('recipe_unit', '')})"
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
            result = pantry_service.consume_fifo(ingredient["slug"], quantity)
            self.preview_data = result

            # Build preview message
            preview_message = f"FIFO Consumption Preview for {ingredient['name']}\n"
            preview_message += "=" * 60 + "\n\n"

            if result["satisfied"]:
                preview_message += f"✓ Requested: {quantity} {ingredient.get('recipe_unit', '')}\n"
                preview_message += (
                    f"✓ Will consume: {result['consumed']} {ingredient.get('recipe_unit', '')}\n"
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
                preview_message += f"⚠ Requested: {quantity} {ingredient.get('recipe_unit', '')}\n"
                preview_message += (
                    f"⚠ Available: {result['consumed']} {ingredient.get('recipe_unit', '')}\n"
                )
                preview_message += (
                    f"⚠ Shortfall: {result['shortfall']} {ingredient.get('recipe_unit', '')}\n"
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
