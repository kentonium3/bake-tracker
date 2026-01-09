"""
Packages tab for the Seasonal Baking Tracker.

Provides full CRUD interface for managing gift packages.

Updated for Feature 006 Event Planning Restoration:
- Uses PackageFinishedGood instead of PackageBundle
- Displays FinishedGoods in package details
"""

import customtkinter as ctk
from typing import Optional
from decimal import Decimal

from src.models.package import Package
from src.services import package_service, composition_service
from src.services.package_service import PackageNotFoundError, PackageInUseError
from src.utils.constants import (
    PADDING_MEDIUM,
    PADDING_LARGE,
)
from src.ui.widgets.search_bar import SearchBar
from src.ui.widgets.data_table import PackageDataTable
from src.ui.widgets.dialogs import (
    show_confirmation,
    show_error,
    show_success,
)
from src.ui.forms.package_form import PackageFormDialog


class PackagesTab(ctk.CTkFrame):
    """
    Packages management tab with full CRUD capabilities.

    Provides interface for:
    - Viewing all packages in a searchable table
    - Adding new packages with bundles
    - Editing existing packages
    - Deleting packages
    - Filtering by name and template status
    """

    def __init__(self, parent):
        """
        Initialize the packages tab.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.selected_package: Optional[Package] = None

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Search bar
        self.grid_rowconfigure(1, weight=0)  # Action buttons
        self.grid_rowconfigure(2, weight=1)  # Data table
        self.grid_rowconfigure(3, weight=0)  # Status bar

        # Create UI components
        self._create_search_bar()
        self._create_action_buttons()
        self._create_data_table()
        self._create_status_bar()

        # Data will be loaded when tab is first selected (lazy loading)
        # self.refresh()

        # Grid the frame
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def _create_search_bar(self):
        """Create the search bar with filter."""
        self.search_bar = SearchBar(
            self,
            search_callback=self._on_search,
            categories=["All Packages", "Templates Only", "Regular Packages"],
            placeholder="Search by name...",
        )
        self.search_bar.grid(
            row=0, column=0, sticky="ew", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_MEDIUM)
        )

    def _create_action_buttons(self):
        """Create action buttons for CRUD operations."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_MEDIUM)

        # Add button
        add_button = ctk.CTkButton(
            button_frame,
            text="➕ Add Package",
            command=self._add_package,
            width=150,
        )
        add_button.grid(row=0, column=0, padx=PADDING_MEDIUM)

        # Edit button
        self.edit_button = ctk.CTkButton(
            button_frame,
            text="✏️ Edit",
            command=self._edit_package,
            width=120,
            state="disabled",
        )
        self.edit_button.grid(row=0, column=1, padx=PADDING_MEDIUM)

        # Delete button
        self.delete_button = ctk.CTkButton(
            button_frame,
            text="🗑️ Delete",
            command=self._delete_package,
            width=120,
            state="disabled",
            fg_color="darkred",
            hover_color="red",
        )
        self.delete_button.grid(row=0, column=2, padx=PADDING_MEDIUM)

        # View Details button
        self.view_button = ctk.CTkButton(
            button_frame,
            text="👁️ View Details",
            command=self._view_details,
            width=140,
            state="disabled",
        )
        self.view_button.grid(row=0, column=3, padx=PADDING_MEDIUM)

        # Refresh button
        refresh_button = ctk.CTkButton(
            button_frame,
            text="🔄 Refresh",
            command=self.refresh,
            width=120,
        )
        refresh_button.grid(row=0, column=4, padx=PADDING_MEDIUM)

    def _create_data_table(self):
        """Create the data table for displaying packages."""
        self.data_table = PackageDataTable(
            self,
            select_callback=self._on_row_select,
            double_click_callback=self._on_row_double_click,
        )
        self.data_table.grid(
            row=2, column=0, sticky="nsew", padx=PADDING_LARGE, pady=PADDING_MEDIUM
        )

    def _create_status_bar(self):
        """Create status bar for displaying info."""
        self.status_frame = ctk.CTkFrame(self, height=30)
        self.status_frame.grid(
            row=3, column=0, sticky="ew", padx=PADDING_LARGE, pady=(0, PADDING_LARGE)
        )
        self.status_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Ready",
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

    def _on_search(self, search_text: str, category: Optional[str] = None):
        """
        Handle search and filter.

        Args:
            search_text: Search query
            category: Selected category filter
        """
        # Determine template filter
        is_template = None
        if category == "Templates Only":
            is_template = True
        elif category == "Regular Packages":
            is_template = False

        # Get filtered packages
        try:
            packages = package_service.get_all_packages(
                name_search=search_text if search_text else None,
                is_template=is_template,
            )
            self.data_table.set_data(packages)
            self._update_status(f"Found {len(packages)} package(s)")
        except Exception as e:
            show_error("Search Error", f"Failed to search packages: {str(e)}", parent=self)
            self._update_status("Search failed", error=True)

    def _on_row_select(self, package: Optional[Package]):
        """
        Handle row selection.

        Args:
            package: Selected package (None if deselected)
        """
        self.selected_package = package

        # Enable/disable action buttons
        has_selection = package is not None
        self.edit_button.configure(state="normal" if has_selection else "disabled")
        self.delete_button.configure(state="normal" if has_selection else "disabled")
        self.view_button.configure(state="normal" if has_selection else "disabled")

    def _on_row_double_click(self, package: Package):
        """
        Handle row double-click (opens view details).

        Args:
            package: Double-clicked package
        """
        self._view_details()

    def _add_package(self):
        """Open dialog to add a new package."""
        dialog = PackageFormDialog(self, title="Add Package")
        self.wait_window(dialog)

        result = dialog.get_result()
        if result:
            try:
                package_data = result["package_data"]
                finished_good_items = result["finished_good_items"]
                packaging_items = result.get("packaging_items", [])  # Feature 011
                new_package = package_service.create_package(package_data, finished_good_items)

                # Feature 011: Add packaging compositions to the new package
                # Feature 026: Support for generic packaging requirements
                for pkg_item in packaging_items:
                    composition_service.add_packaging_to_package(
                        package_id=new_package.id,
                        packaging_product_id=pkg_item["product_id"],
                        quantity=pkg_item["quantity"],
                        is_generic=pkg_item.get("is_generic", False),
                    )

                show_success(
                    "Success", f"Package '{package_data['name']}' added successfully", parent=self
                )
                self.refresh()
            except Exception as e:
                show_error("Error", f"Failed to add package: {str(e)}", parent=self)

    def _edit_package(self):
        """Open dialog to edit the selected package."""
        if not self.selected_package:
            return

        dialog = PackageFormDialog(self, package=self.selected_package, title="Edit Package")
        self.wait_window(dialog)

        result = dialog.get_result()
        if result:
            try:
                package_data = result["package_data"]
                finished_good_items = result["finished_good_items"]
                packaging_items = result.get("packaging_items", [])  # Feature 011
                package_service.update_package(
                    self.selected_package.id, package_data, finished_good_items
                )

                # Feature 011: Update packaging compositions
                # First, remove existing packaging compositions
                try:
                    existing_packaging = composition_service.get_package_packaging(
                        self.selected_package.id
                    )
                    for comp in existing_packaging:
                        composition_service.remove_composition(comp.id)
                except Exception:
                    pass  # No existing packaging to remove

                # Then add new packaging compositions
                # Feature 026: Support for generic packaging requirements
                for pkg_item in packaging_items:
                    composition_service.add_packaging_to_package(
                        package_id=self.selected_package.id,
                        packaging_product_id=pkg_item["product_id"],
                        quantity=pkg_item["quantity"],
                        is_generic=pkg_item.get("is_generic", False),
                    )

                show_success("Success", "Package updated successfully", parent=self)
                self.refresh()
            except PackageNotFoundError:
                show_error("Error", "Package not found", parent=self)
                self.refresh()
            except Exception as e:
                show_error("Error", f"Failed to update package: {str(e)}", parent=self)

    def _delete_package(self):
        """Delete the selected package after confirmation."""
        if not self.selected_package:
            return

        # Confirm deletion
        if not show_confirmation(
            "Confirm Deletion",
            f"Are you sure you want to delete package '{self.selected_package.name}'?\n\n"
            "This action cannot be undone.",
            parent=self,
        ):
            return

        try:
            package_service.delete_package(self.selected_package.id)
            show_success("Success", "Package deleted successfully", parent=self)
            self.selected_package = None
            self.refresh()
        except PackageInUseError as e:
            show_error(
                "Cannot Delete",
                f"This package is used in {e.assignment_count} event assignment(s) and cannot be deleted.",
                parent=self,
            )
        except PackageNotFoundError:
            show_error("Error", "Package not found", parent=self)
            self.refresh()
        except Exception as e:
            show_error("Error", f"Failed to delete package: {str(e)}", parent=self)

    def _view_details(self):
        """View details of the selected package."""
        if not self.selected_package:
            return

        # Create details dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Package Details - {self.selected_package.name}")
        dialog.geometry("600x500")
        dialog.transient(self)
        dialog.grab_set()

        # Create scrollable frame
        scroll_frame = ctk.CTkScrollableFrame(dialog)
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Package name
        ctk.CTkLabel(
            scroll_frame, text=self.selected_package.name, font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", pady=(0, 10))

        # Template flag
        if self.selected_package.is_template:
            ctk.CTkLabel(
                scroll_frame,
                text="📋 Template Package",
                font=ctk.CTkFont(size=12),
                text_color="blue",
            ).pack(anchor="w", pady=(0, 10))

        # Description
        if self.selected_package.description:
            ctk.CTkLabel(scroll_frame, text="Description:", font=ctk.CTkFont(weight="bold")).pack(
                anchor="w", pady=(10, 5)
            )
            ctk.CTkLabel(
                scroll_frame, text=self.selected_package.description, wraplength=550, justify="left"
            ).pack(anchor="w", pady=(0, 10))

        # Finished Goods
        ctk.CTkLabel(scroll_frame, text="Finished Goods:", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", pady=(10, 5)
        )

        if self.selected_package.package_finished_goods:
            for pfg in self.selected_package.package_finished_goods:
                fg_name = pfg.finished_good.display_name if pfg.finished_good else "Unknown"

                ctk.CTkLabel(
                    scroll_frame,
                    text=f"  - {fg_name} x {pfg.quantity}",
                    font=ctk.CTkFont(size=12),
                ).pack(anchor="w", pady=2)
        else:
            ctk.CTkLabel(
                scroll_frame,
                text="  No finished goods",
                font=ctk.CTkFont(size=12),
                text_color="gray",
            ).pack(anchor="w", pady=2)

        # Feature 011: Packaging Materials
        ctk.CTkLabel(
            scroll_frame, text="📦 Packaging Materials:", font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", pady=(10, 5))

        try:
            packaging_comps = composition_service.get_package_packaging(self.selected_package.id)
            if packaging_comps:
                for comp in packaging_comps:
                    product = comp.packaging_product
                    if product and product.ingredient:
                        ing_name = product.ingredient.display_name
                        brand = product.brand or ""
                        qty = comp.component_quantity
                        ctk.CTkLabel(
                            scroll_frame,
                            text=f"  - {ing_name} ({brand}) x {qty:.1f}",
                            font=ctk.CTkFont(size=12),
                        ).pack(anchor="w", pady=2)
            else:
                ctk.CTkLabel(
                    scroll_frame,
                    text="  No packaging materials",
                    font=ctk.CTkFont(size=12),
                    text_color="gray",
                ).pack(anchor="w", pady=2)
        except Exception:
            ctk.CTkLabel(
                scroll_frame,
                text="  No packaging materials",
                font=ctk.CTkFont(size=12),
                text_color="gray",
            ).pack(anchor="w", pady=2)

        # Total cost
        total_cost = self.selected_package.calculate_cost()
        ctk.CTkLabel(
            scroll_frame,
            text=f"\nTotal Package Cost: ${total_cost:.2f}",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", pady=(15, 10))

        # Notes
        if self.selected_package.notes:
            ctk.CTkLabel(scroll_frame, text="Notes:", font=ctk.CTkFont(weight="bold")).pack(
                anchor="w", pady=(10, 5)
            )
            ctk.CTkLabel(
                scroll_frame, text=self.selected_package.notes, wraplength=550, justify="left"
            ).pack(anchor="w", pady=(0, 10))

        # Close button
        ctk.CTkButton(scroll_frame, text="Close", command=dialog.destroy, width=100).pack(
            pady=(20, 0)
        )

    def refresh(self):
        """Refresh the packages list."""
        try:
            packages = package_service.get_all_packages()
            self.data_table.set_data(packages)
            self._update_status(f"Loaded {len(packages)} package(s)")
        except Exception as e:
            show_error("Error", f"Failed to load packages: {str(e)}", parent=self)
            self._update_status("Failed to load packages", error=True)

    def _update_status(self, message: str, error: bool = False):
        """
        Update the status bar.

        Args:
            message: Status message
            error: Whether this is an error message
        """
        if error:
            self.status_label.configure(text=message, text_color="red")
        else:
            self.status_label.configure(text=message)
