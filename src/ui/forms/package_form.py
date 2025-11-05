"""
Package form dialog for adding and editing packages.

Provides a form for creating and updating package records with bundle selection.
"""

import customtkinter as ctk
from typing import Optional, Dict, Any, List

from src.models.package import Package
from src.services import finished_good_service
from src.utils.constants import (
    MAX_NAME_LENGTH,
    MAX_NOTES_LENGTH,
    PADDING_MEDIUM,
    PADDING_LARGE,
)
from src.ui.widgets.dialogs import show_error


class BundleRow(ctk.CTkFrame):
    """Row widget for a single bundle in the package."""

    def __init__(
        self,
        parent,
        bundles: List,
        remove_callback,
        bundle_id: Optional[int] = None,
        quantity: int = 1,
    ):
        """
        Initialize bundle row.

        Args:
            parent: Parent widget
            bundles: List of available bundles
            remove_callback: Callback to remove this row
            bundle_id: Selected bundle ID (None for new row)
            quantity: Bundle quantity
        """
        super().__init__(parent, fg_color="transparent")

        self.bundles = bundles
        self.remove_callback = remove_callback

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=0)

        # Bundle dropdown
        bundle_names = [f"{b.name} (${b.calculate_cost():.2f})" for b in bundles]
        self.bundle_combo = ctk.CTkComboBox(
            self,
            width=350,
            values=bundle_names if bundle_names else ["No bundles available"],
            state="readonly" if bundle_names else "disabled",
        )
        if bundle_names:
            # Set selected bundle if provided
            if bundle_id:
                for i, bundle in enumerate(bundles):
                    if bundle.id == bundle_id:
                        self.bundle_combo.set(bundle_names[i])
                        break
            else:
                self.bundle_combo.set(bundle_names[0])

        self.bundle_combo.grid(row=0, column=0, sticky="ew", padx=(0, PADDING_MEDIUM))

        # Quantity entry
        self.quantity_entry = ctk.CTkEntry(self, width=80, placeholder_text="Qty")
        self.quantity_entry.insert(0, str(quantity))
        self.quantity_entry.grid(row=0, column=1, padx=(0, PADDING_MEDIUM))

        # Remove button
        remove_button = ctk.CTkButton(
            self,
            text="✕",
            width=30,
            command=lambda: remove_callback(self),
            fg_color="darkred",
            hover_color="red",
        )
        remove_button.grid(row=0, column=2)

    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Get bundle data from this row.

        Returns:
            Dictionary with bundle_id and quantity, or None if invalid
        """
        bundle_name = self.bundle_combo.get()
        if not bundle_name or bundle_name == "No bundles available":
            return None

        # Extract bundle name (remove cost suffix)
        if " ($" in bundle_name:
            bundle_name = bundle_name.split(" ($")[0]

        # Find bundle by name
        bundle = None
        for b in self.bundles:
            if b.name == bundle_name:
                bundle = b
                break

        if not bundle:
            return None

        # Get quantity
        try:
            quantity = int(self.quantity_entry.get().strip())
            if quantity <= 0:
                return None
        except ValueError:
            return None

        return {
            "bundle_id": bundle.id,
            "quantity": quantity,
        }


class PackageFormDialog(ctk.CTkToplevel):
    """
    Dialog for creating or editing a package.

    Provides a form with bundle selection and management.
    """

    def __init__(
        self,
        parent,
        package: Optional[Package] = None,
        title: str = "Add Package",
    ):
        """
        Initialize the package form dialog.

        Args:
            parent: Parent window
            package: Existing package to edit (None for new)
            title: Dialog title
        """
        super().__init__(parent)

        self.package = package
        self.result = None
        self.bundle_rows: List[BundleRow] = []

        # Load available bundles
        try:
            self.available_bundles = finished_good_service.get_all_bundles()
        except Exception:
            self.available_bundles = []

        # Configure window
        self.title(title)
        self.geometry("700x700")
        self.resizable(False, False)

        # Center on parent
        self.transient(parent)
        self.grab_set()

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create main frame
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=PADDING_LARGE, pady=PADDING_LARGE)
        main_frame.grid_columnconfigure(1, weight=1)

        # Create form fields
        self._create_form_fields(main_frame)

        # Create buttons
        self._create_buttons()

        # Populate if editing
        if self.package:
            self._populate_form()
        else:
            # Add one empty bundle row for new packages
            self._add_bundle_row()

    def _create_form_fields(self, parent):
        """Create all form input fields."""
        row = 0

        # Name field (required)
        name_label = ctk.CTkLabel(parent, text="Package Name*:", anchor="w")
        name_label.grid(
            row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=(PADDING_MEDIUM, 5)
        )

        self.name_entry = ctk.CTkEntry(
            parent, width=500, placeholder_text="e.g., Deluxe Cookie Assortment, Standard Gift Box"
        )
        self.name_entry.grid(
            row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=(PADDING_MEDIUM, 5)
        )
        row += 1

        # Description field (optional)
        desc_label = ctk.CTkLabel(parent, text="Description:", anchor="w")
        desc_label.grid(row=row, column=0, sticky="nw", padx=PADDING_MEDIUM, pady=5)

        self.description_text = ctk.CTkTextbox(parent, width=500, height=80)
        self.description_text.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Template checkbox
        self.is_template_var = ctk.BooleanVar(value=False)
        template_check = ctk.CTkCheckBox(
            parent,
            text="Save as template (reusable across events)",
            variable=self.is_template_var,
        )
        template_check.grid(
            row=row, column=0, columnspan=2, sticky="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        row += 1

        # Bundles section
        bundles_label = ctk.CTkLabel(
            parent,
            text="Bundles in Package",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        bundles_label.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=PADDING_MEDIUM,
            pady=(PADDING_LARGE, PADDING_MEDIUM),
        )
        row += 1

        # Bundles list frame
        self.bundles_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.bundles_frame.grid(
            row=row, column=0, columnspan=2, sticky="ew", padx=PADDING_MEDIUM, pady=5
        )
        self.bundles_frame.grid_columnconfigure(0, weight=1)
        row += 1

        # Add bundle button
        add_button = ctk.CTkButton(
            parent,
            text="+ Add Bundle",
            command=self._add_bundle_row,
            width=150,
        )
        add_button.grid(
            row=row, column=0, columnspan=2, sticky="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        row += 1

        # Notes field (optional)
        notes_label = ctk.CTkLabel(parent, text="Notes:", anchor="w")
        notes_label.grid(row=row, column=0, sticky="nw", padx=PADDING_MEDIUM, pady=5)

        self.notes_text = ctk.CTkTextbox(parent, width=500, height=100)
        self.notes_text.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Required field note
        required_note = ctk.CTkLabel(
            parent,
            text="* Required fields",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="gray",
        )
        required_note.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=PADDING_MEDIUM,
            pady=(PADDING_MEDIUM, 0),
        )

    def _add_bundle_row(self, bundle_id: Optional[int] = None, quantity: int = 1):
        """
        Add a new bundle row.

        Args:
            bundle_id: Optional bundle ID to pre-select
            quantity: Bundle quantity
        """
        row = BundleRow(
            self.bundles_frame,
            self.available_bundles,
            self._remove_bundle_row,
            bundle_id=bundle_id,
            quantity=quantity,
        )
        row.grid(row=len(self.bundle_rows), column=0, sticky="ew", pady=2)
        self.bundle_rows.append(row)

    def _remove_bundle_row(self, row: BundleRow):
        """
        Remove a bundle row.

        Args:
            row: BundleRow to remove
        """
        if row in self.bundle_rows:
            self.bundle_rows.remove(row)
            row.destroy()

            # Re-grid remaining rows
            for i, remaining_row in enumerate(self.bundle_rows):
                remaining_row.grid(row=i, column=0, sticky="ew", pady=2)

    def _create_buttons(self):
        """Create dialog buttons."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)
        button_frame.grid_columnconfigure((0, 1), weight=1)

        # Save button
        save_button = ctk.CTkButton(
            button_frame,
            text="Save",
            command=self._save,
            width=150,
        )
        save_button.grid(row=0, column=0, padx=PADDING_MEDIUM)

        # Cancel button
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._cancel,
            width=150,
            fg_color="gray",
            hover_color="darkgray",
        )
        cancel_button.grid(row=0, column=1, padx=PADDING_MEDIUM)

    def _populate_form(self):
        """Populate form fields with existing package data."""
        if not self.package:
            return

        self.name_entry.insert(0, self.package.name)

        if self.package.description:
            self.description_text.insert("1.0", self.package.description)

        self.is_template_var.set(self.package.is_template)

        if self.package.notes:
            self.notes_text.insert("1.0", self.package.notes)

        # Add bundle rows
        if self.package.package_bundles:
            for pb in self.package.package_bundles:
                self._add_bundle_row(bundle_id=pb.bundle_id, quantity=pb.quantity)

    def _save(self):
        """Validate and save the package data."""
        # Validate and collect data
        data = self._validate_and_collect()
        if data is None:
            return

        # Set result and close
        self.result = data
        self.destroy()

    def _cancel(self):
        """Cancel the dialog."""
        self.result = None
        self.destroy()

    def _validate_and_collect(self) -> Optional[Dict[str, Any]]:
        """
        Validate form inputs and collect data.

        Returns:
            Dictionary with package data and bundle_items list, or None if validation fails
        """
        # Get values
        name = self.name_entry.get().strip()
        description = self.description_text.get("1.0", "end-1c").strip()
        is_template = self.is_template_var.get()
        notes = self.notes_text.get("1.0", "end-1c").strip()

        # Validate required fields
        if not name:
            show_error(
                "Validation Error",
                "Package name is required",
                parent=self,
            )
            return None

        # Validate lengths
        if len(name) > MAX_NAME_LENGTH:
            show_error(
                "Validation Error",
                f"Name must be {MAX_NAME_LENGTH} characters or less",
                parent=self,
            )
            return None

        if notes and len(notes) > MAX_NOTES_LENGTH:
            show_error(
                "Validation Error",
                f"Notes must be {MAX_NOTES_LENGTH} characters or less",
                parent=self,
            )
            return None

        # Collect bundle items
        bundle_items = []
        for row in self.bundle_rows:
            bundle_data = row.get_data()
            if bundle_data:
                bundle_items.append(bundle_data)

        # Validate at least one bundle
        if not bundle_items:
            show_error(
                "Validation Error",
                "Package must contain at least one bundle",
                parent=self,
            )
            return None

        # Return validated data
        return {
            "package_data": {
                "name": name,
                "description": description if description else None,
                "is_template": is_template,
                "notes": notes if notes else None,
            },
            "bundle_items": bundle_items,
        }

    def get_result(self) -> Optional[Dict[str, Any]]:
        """Get the dialog result."""
        return self.result
