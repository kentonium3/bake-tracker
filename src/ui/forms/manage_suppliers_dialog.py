"""
Manage Suppliers Dialog for CRUD operations on suppliers.

Provides a modal dialog for:
- Viewing all suppliers (with active/inactive filter)
- Adding new suppliers
- Editing existing suppliers
- Toggling active/inactive status
- Deleting suppliers (when no purchases exist)
"""

import customtkinter as ctk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any, List

from src.services import supplier_service
from src.services.exceptions import ServiceError
from src.ui.utils.error_handler import handle_error


class ManageSuppliersDialog(ctk.CTkToplevel):
    """
    Dialog for managing suppliers.

    Features:
    - List view of all suppliers with sortable columns
    - Active/Inactive status toggle
    - Add/Edit/Delete operations
    - Filter to show/hide inactive suppliers
    """

    def __init__(self, parent, **kwargs):
        """Initialize the dialog."""
        super().__init__(parent, **kwargs)

        self.result: Optional[bool] = None
        self.selected_supplier_id: Optional[int] = None

        # Window configuration
        self.title("Manage Suppliers")
        self.geometry("800x500")
        self.resizable(True, True)
        self.minsize(700, 400)

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Setup UI
        self._setup_toolbar()
        self._setup_list()
        self._setup_buttons()

        # Load data
        self._load_suppliers()

    def _setup_toolbar(self):
        """Create toolbar with filter options."""
        toolbar = ctk.CTkFrame(self)
        toolbar.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")

        # Title
        ctk.CTkLabel(
            toolbar,
            text="Suppliers",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(side="left", padx=10, pady=5)

        # Show inactive checkbox
        self.show_inactive_var = ctk.BooleanVar(value=True)
        self.show_inactive_cb = ctk.CTkCheckBox(
            toolbar,
            text="Show inactive",
            variable=self.show_inactive_var,
            command=self._load_suppliers,
        )
        self.show_inactive_cb.pack(side="right", padx=10, pady=5)

    def _setup_list(self):
        """Create supplier list view."""
        list_container = ctk.CTkFrame(self)
        list_container.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        list_container.grid_columnconfigure(0, weight=1)
        list_container.grid_rowconfigure(0, weight=1)

        # Treeview
        columns = ("name", "type", "location", "status")
        self.tree = ttk.Treeview(
            list_container,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        self.tree.heading("name", text="Name", anchor="w")
        self.tree.heading("type", text="Type", anchor="w")
        self.tree.heading("location", text="Location / URL", anchor="w")
        self.tree.heading("status", text="Status", anchor="w")

        self.tree.column("name", width=200, minwidth=150)
        self.tree.column("type", width=80, minwidth=70)
        self.tree.column("location", width=250, minwidth=150)
        self.tree.column("status", width=80, minwidth=60)

        # Scrollbar
        scrollbar = ttk.Scrollbar(
            list_container,
            orient="vertical",
            command=self.tree.yview,
        )
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Bind selection event
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._on_double_click)

    def _setup_buttons(self):
        """Create action buttons."""
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        # Left side - CRUD buttons
        left_frame = ctk.CTkFrame(button_frame, fg_color="transparent")
        left_frame.pack(side="left")

        self.add_btn = ctk.CTkButton(
            left_frame,
            text="Add",
            command=self._on_add,
            width=80,
        )
        self.add_btn.pack(side="left", padx=5, pady=5)

        self.edit_btn = ctk.CTkButton(
            left_frame,
            text="Edit",
            command=self._on_edit,
            width=80,
            state="disabled",
        )
        self.edit_btn.pack(side="left", padx=5, pady=5)

        self.toggle_btn = ctk.CTkButton(
            left_frame,
            text="Deactivate",
            command=self._on_toggle_active,
            width=100,
            state="disabled",
        )
        self.toggle_btn.pack(side="left", padx=5, pady=5)

        self.delete_btn = ctk.CTkButton(
            left_frame,
            text="Delete",
            command=self._on_delete,
            width=80,
            fg_color="darkred",
            hover_color="red",
            state="disabled",
        )
        self.delete_btn.pack(side="left", padx=5, pady=5)

        # Right side - Close button
        self.close_btn = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self._on_close,
            width=80,
        )
        self.close_btn.pack(side="right", padx=5, pady=5)

    def _load_suppliers(self):
        """Load suppliers into the list."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            include_inactive = self.show_inactive_var.get()
            suppliers = supplier_service.get_all_suppliers(include_inactive=include_inactive)

            for supplier in suppliers:
                status = "Active" if supplier.get("is_active", True) else "Inactive"

                # Format type display
                is_online = (
                    supplier.get("is_online", False) or supplier.get("supplier_type") == "online"
                )
                type_display = "Online" if is_online else "Store"

                # Format location/URL display
                if is_online:
                    location_display = supplier.get("website_url") or "Online"
                else:
                    city = supplier.get("city", "")
                    state = supplier.get("state", "")
                    location_display = f"{city}, {state}" if city and state else state or city or ""

                values = (
                    supplier.get("name", ""),
                    type_display,
                    location_display,
                    status,
                )
                self.tree.insert(
                    "",
                    "end",
                    iid=str(supplier["id"]),
                    values=values,
                    tags=("inactive",) if not supplier.get("is_active", True) else (),
                )

            # Style inactive rows
            self.tree.tag_configure("inactive", foreground="gray")

        except ServiceError as e:
            handle_error(e, parent=self, operation="Load suppliers")
        except Exception as e:
            handle_error(e, parent=self, operation="Load suppliers")

    def _on_select(self, event):
        """Handle row selection."""
        selection = self.tree.selection()
        if selection:
            self.selected_supplier_id = int(selection[0])
            self._update_button_states()
        else:
            self.selected_supplier_id = None
            self._update_button_states()

    def _on_double_click(self, event):
        """Handle double-click to edit."""
        if self.selected_supplier_id:
            self._on_edit()

    def _update_button_states(self):
        """Update button states based on selection."""
        if self.selected_supplier_id:
            self.edit_btn.configure(state="normal")
            self.delete_btn.configure(state="normal")
            self.toggle_btn.configure(state="normal")

            # Update toggle button text based on current status
            try:
                supplier = supplier_service.get_supplier(self.selected_supplier_id)
                if supplier and supplier.get("is_active", True):
                    self.toggle_btn.configure(text="Deactivate")
                else:
                    self.toggle_btn.configure(text="Activate")
            except (ServiceError, Exception):
                pass
        else:
            self.edit_btn.configure(state="disabled")
            self.delete_btn.configure(state="disabled")
            self.toggle_btn.configure(state="disabled")
            self.toggle_btn.configure(text="Deactivate")

    def _on_add(self):
        """Open add supplier dialog."""
        dialog = SupplierFormDialog(self)
        self.wait_window(dialog)

        if dialog.result:
            self._load_suppliers()
            self.result = True

    def _on_edit(self):
        """Open edit supplier dialog."""
        if not self.selected_supplier_id:
            return

        dialog = SupplierFormDialog(self, supplier_id=self.selected_supplier_id)
        self.wait_window(dialog)

        if dialog.result:
            self._load_suppliers()
            self.result = True

    def _on_toggle_active(self):
        """Toggle supplier active/inactive status."""
        if not self.selected_supplier_id:
            return

        try:
            supplier = supplier_service.get_supplier(self.selected_supplier_id)
            if not supplier:
                return

            if supplier.get("is_active", True):
                # Deactivate
                if messagebox.askyesno(
                    "Confirm Deactivate",
                    f"Deactivate '{supplier['name']}'?\n\n"
                    "This will also clear this supplier as the preferred "
                    "supplier on any products.",
                    parent=self,
                ):
                    supplier_service.deactivate_supplier(self.selected_supplier_id)
                    messagebox.showinfo(
                        "Success",
                        f"Supplier '{supplier['name']}' has been deactivated.",
                        parent=self,
                    )
                    self._load_suppliers()
                    self.result = True
            else:
                # Reactivate
                supplier_service.reactivate_supplier(self.selected_supplier_id)
                messagebox.showinfo(
                    "Success",
                    f"Supplier '{supplier['name']}' has been reactivated.",
                    parent=self,
                )
                self._load_suppliers()
                self.result = True

        except ServiceError as e:
            handle_error(e, parent=self, operation="Update supplier status")
        except Exception as e:
            handle_error(e, parent=self, operation="Update supplier status")

    def _on_delete(self):
        """Delete selected supplier."""
        if not self.selected_supplier_id:
            return

        try:
            supplier = supplier_service.get_supplier(self.selected_supplier_id)
            if not supplier:
                return

            if not messagebox.askyesno(
                "Confirm Delete",
                f"Delete '{supplier['name']}'?\n\n"
                "This cannot be undone.\n\n"
                "Note: Suppliers with purchase history cannot be deleted. "
                "Use 'Deactivate' instead.",
                parent=self,
            ):
                return

            supplier_service.delete_supplier(self.selected_supplier_id)
            messagebox.showinfo(
                "Success",
                f"Supplier '{supplier['name']}' has been deleted.",
                parent=self,
            )
            self._load_suppliers()
            self.result = True

        except ValueError as e:
            # Has purchases - offer to deactivate instead
            if messagebox.askyesno(
                "Cannot Delete",
                f"{str(e)}\n\nWould you like to deactivate the supplier instead?",
                parent=self,
            ):
                self._on_toggle_active()

        except ServiceError as e:
            handle_error(e, parent=self, operation="Delete supplier")
        except Exception as e:
            handle_error(e, parent=self, operation="Delete supplier")

    def _on_close(self):
        """Close the dialog."""
        self.destroy()


class SupplierFormDialog(ctk.CTkToplevel):
    """
    Dialog for adding or editing a supplier.

    Supports two supplier types:
    - Physical Store: Requires city, state, zip code
    - Online Vendor: Only requires name (URL recommended)
    """

    def __init__(self, parent, supplier_id: Optional[int] = None, **kwargs):
        """
        Initialize the form dialog.

        Args:
            parent: Parent widget
            supplier_id: Supplier ID for edit mode, None for add mode
        """
        super().__init__(parent, **kwargs)

        self.supplier_id = supplier_id
        self.result: Optional[bool] = None

        # Window configuration
        self.title("Add Supplier" if not supplier_id else "Edit Supplier")
        self.geometry("450x450")
        self.resizable(False, False)

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        # Configure grid
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        # Setup UI
        self._setup_form()

        # Load data if editing
        if supplier_id:
            self._load_supplier()
        else:
            # Default to physical store for new suppliers
            self._on_type_change()

    def _setup_form(self):
        """Create form fields."""
        row = 0

        # Title
        title = "Add Supplier" if not self.supplier_id else "Edit Supplier"
        ctk.CTkLabel(
            self,
            text=title,
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=row, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="w")
        row += 1

        # Supplier Type (radio buttons)
        type_frame = ctk.CTkFrame(self, fg_color="transparent")
        type_frame.grid(row=row, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="w")

        ctk.CTkLabel(type_frame, text="Type:").pack(side="left", padx=(0, 10))

        self.type_var = ctk.StringVar(value="physical")
        self.physical_radio = ctk.CTkRadioButton(
            type_frame,
            text="Physical Store",
            variable=self.type_var,
            value="physical",
            command=self._on_type_change,
        )
        self.physical_radio.pack(side="left", padx=5)

        self.online_radio = ctk.CTkRadioButton(
            type_frame,
            text="Online Vendor",
            variable=self.type_var,
            value="online",
            command=self._on_type_change,
        )
        self.online_radio.pack(side="left", padx=5)
        row += 1

        # Name (required)
        ctk.CTkLabel(self, text="Name *").grid(row=row, column=0, padx=(20, 10), pady=5, sticky="w")
        self.name_var = ctk.StringVar()
        self.name_entry = ctk.CTkEntry(
            self,
            textvariable=self.name_var,
            width=250,
            placeholder_text="e.g., Costco or King Arthur Baking",
        )
        self.name_entry.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="w")
        row += 1

        # Website URL (optional for physical, recommended for online)
        self.url_label = ctk.CTkLabel(self, text="Website URL")
        self.url_label.grid(row=row, column=0, padx=(20, 10), pady=5, sticky="w")
        self.url_var = ctk.StringVar()
        self.url_entry = ctk.CTkEntry(
            self,
            textvariable=self.url_var,
            width=250,
            placeholder_text="https://www.example.com",
        )
        self.url_entry.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="w")
        row += 1

        # Street Address (optional, physical only)
        self.street_label = ctk.CTkLabel(self, text="Street Address")
        self.street_label.grid(row=row, column=0, padx=(20, 10), pady=5, sticky="w")
        self.street_var = ctk.StringVar()
        self.street_entry = ctk.CTkEntry(
            self,
            textvariable=self.street_var,
            width=250,
            placeholder_text="e.g., 123 Main St",
        )
        self.street_entry.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="w")
        row += 1

        # City (required for physical)
        self.city_label = ctk.CTkLabel(self, text="City *")
        self.city_label.grid(row=row, column=0, padx=(20, 10), pady=5, sticky="w")
        self.city_var = ctk.StringVar()
        self.city_entry = ctk.CTkEntry(
            self,
            textvariable=self.city_var,
            width=250,
            placeholder_text="e.g., Waltham",
        )
        self.city_entry.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="w")
        row += 1

        # State (required for physical)
        self.state_label = ctk.CTkLabel(self, text="State *")
        self.state_label.grid(row=row, column=0, padx=(20, 10), pady=5, sticky="w")
        self.state_var = ctk.StringVar()
        self.state_entry = ctk.CTkEntry(
            self,
            textvariable=self.state_var,
            width=60,
            placeholder_text="MA",
        )
        self.state_entry.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="w")
        row += 1

        # ZIP Code (required for physical)
        self.zip_label = ctk.CTkLabel(self, text="ZIP Code *")
        self.zip_label.grid(row=row, column=0, padx=(20, 10), pady=5, sticky="w")
        self.zip_var = ctk.StringVar()
        self.zip_entry = ctk.CTkEntry(
            self,
            textvariable=self.zip_var,
            width=100,
            placeholder_text="02451",
        )
        self.zip_entry.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="w")
        row += 1

        # Notes (optional)
        ctk.CTkLabel(self, text="Notes").grid(row=row, column=0, padx=(20, 10), pady=5, sticky="w")
        self.notes_var = ctk.StringVar()
        self.notes_entry = ctk.CTkEntry(
            self,
            textvariable=self.notes_var,
            width=250,
            placeholder_text="Optional notes",
        )
        self.notes_entry.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="w")
        row += 1

        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=row, column=0, columnspan=2, padx=20, pady=20, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            width=100,
        ).grid(row=0, column=0, padx=5, pady=5, sticky="e")

        ctk.CTkButton(
            button_frame,
            text="Save",
            command=self._on_save,
            width=100,
        ).grid(row=0, column=1, padx=5, pady=5, sticky="w")

    def _on_type_change(self):
        """Handle supplier type change - enable/disable location fields."""
        is_online = self.type_var.get() == "online"

        if is_online:
            # Online vendor: disable location fields, highlight URL
            self.street_entry.configure(state="disabled")
            self.city_entry.configure(state="disabled")
            self.state_entry.configure(state="disabled")
            self.zip_entry.configure(state="disabled")

            # Update labels to show optional
            self.street_label.configure(text="Street Address")
            self.city_label.configure(text="City")
            self.state_label.configure(text="State")
            self.zip_label.configure(text="ZIP Code")

            # Highlight URL as recommended
            self.url_label.configure(text="Website URL *")
        else:
            # Physical store: enable location fields
            self.street_entry.configure(state="normal")
            self.city_entry.configure(state="normal")
            self.state_entry.configure(state="normal")
            self.zip_entry.configure(state="normal")

            # Update labels to show required
            self.street_label.configure(text="Street Address")
            self.city_label.configure(text="City *")
            self.state_label.configure(text="State *")
            self.zip_label.configure(text="ZIP Code *")

            # URL is optional for physical
            self.url_label.configure(text="Website URL")

    def _load_supplier(self):
        """Load existing supplier data for edit mode."""
        try:
            supplier = supplier_service.get_supplier(self.supplier_id)
            if not supplier:
                messagebox.showerror(
                    "Error",
                    "Supplier not found",
                    parent=self,
                )
                self.destroy()
                return

            # Set supplier type first (affects field enable/disable)
            supplier_type = supplier.get("supplier_type", "physical") or "physical"
            self.type_var.set(supplier_type)
            self._on_type_change()  # Update field states

            self.name_var.set(supplier.get("name", "") or "")
            self.url_var.set(supplier.get("website_url", "") or "")
            self.street_var.set(supplier.get("street_address", "") or "")
            self.city_var.set(supplier.get("city", "") or "")
            self.state_var.set(supplier.get("state", "") or "")
            self.zip_var.set(supplier.get("zip_code", "") or "")
            self.notes_var.set(supplier.get("notes", "") or "")

        except ServiceError as e:
            handle_error(e, parent=self, operation="Load supplier")
            self.destroy()
        except Exception as e:
            handle_error(e, parent=self, operation="Load supplier")
            self.destroy()

    def _validate(self) -> bool:
        """Validate form fields based on supplier type."""
        errors = []
        is_online = self.type_var.get() == "online"

        # Name always required
        if not self.name_var.get().strip():
            errors.append("Name is required")

        # URL validation (if provided)
        url = self.url_var.get().strip()
        if url and not url.startswith(("http://", "https://")):
            errors.append("Website URL must start with http:// or https://")

        # Physical store validations
        if not is_online:
            if not self.city_var.get().strip():
                errors.append("City is required for physical stores")

            state = self.state_var.get().strip()
            if not state:
                errors.append("State is required for physical stores")
            elif len(state) != 2:
                errors.append("State must be a 2-letter code")

            if not self.zip_var.get().strip():
                errors.append("ZIP Code is required for physical stores")

        if errors:
            messagebox.showerror(
                "Validation Error",
                "\n".join(errors),
                parent=self,
            )
            return False

        return True

    def _on_save(self):
        """Handle save button click."""
        if not self._validate():
            return

        is_online = self.type_var.get() == "online"

        try:
            if self.supplier_id:
                # Edit mode
                supplier_service.update_supplier(
                    self.supplier_id,
                    name=self.name_var.get().strip(),
                    supplier_type=self.type_var.get(),
                    website_url=self.url_var.get().strip() or None,
                    street_address=self.street_var.get().strip() or None,
                    city=(
                        self.city_var.get().strip() or None
                        if is_online
                        else self.city_var.get().strip()
                    ),
                    state=(
                        self.state_var.get().strip() or None
                        if is_online
                        else self.state_var.get().strip()
                    ),
                    zip_code=(
                        self.zip_var.get().strip() or None
                        if is_online
                        else self.zip_var.get().strip()
                    ),
                    notes=self.notes_var.get().strip() or None,
                )
                messagebox.showinfo(
                    "Success",
                    "Supplier updated successfully",
                    parent=self,
                )
            else:
                # Add mode
                supplier_service.create_supplier(
                    name=self.name_var.get().strip(),
                    supplier_type=self.type_var.get(),
                    website_url=self.url_var.get().strip() or None,
                    city=self.city_var.get().strip() or None,
                    state=self.state_var.get().strip() or None,
                    zip_code=self.zip_var.get().strip() or None,
                    street_address=self.street_var.get().strip() or None,
                    notes=self.notes_var.get().strip() or None,
                )
                messagebox.showinfo(
                    "Success",
                    "Supplier created successfully",
                    parent=self,
                )

            self.result = True
            self.destroy()

        except ServiceError as e:
            handle_error(e, parent=self, operation="Save supplier")
        except Exception as e:
            handle_error(e, parent=self, operation="Save supplier")

    def _on_cancel(self):
        """Handle cancel button click."""
        self.result = None
        self.destroy()
