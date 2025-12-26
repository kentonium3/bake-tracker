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
        columns = ("name", "city", "state", "zip", "status")
        self.tree = ttk.Treeview(
            list_container,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        self.tree.heading("name", text="Name", anchor="w")
        self.tree.heading("city", text="City", anchor="w")
        self.tree.heading("state", text="State", anchor="w")
        self.tree.heading("zip", text="ZIP", anchor="w")
        self.tree.heading("status", text="Status", anchor="w")

        self.tree.column("name", width=200, minwidth=150)
        self.tree.column("city", width=150, minwidth=100)
        self.tree.column("state", width=60, minwidth=50)
        self.tree.column("zip", width=80, minwidth=60)
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
            suppliers = supplier_service.get_all_suppliers(
                include_inactive=include_inactive
            )

            for supplier in suppliers:
                status = "Active" if supplier.get("is_active", True) else "Inactive"
                values = (
                    supplier.get("name", ""),
                    supplier.get("city", ""),
                    supplier.get("state", ""),
                    supplier.get("zip_code", ""),
                    status,
                )
                self.tree.insert(
                    "", "end",
                    iid=str(supplier["id"]),
                    values=values,
                    tags=("inactive",) if not supplier.get("is_active", True) else (),
                )

            # Style inactive rows
            self.tree.tag_configure("inactive", foreground="gray")

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to load suppliers: {str(e)}",
                parent=self,
            )

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
            except Exception:
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

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to update supplier status: {str(e)}",
                parent=self,
            )

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

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to delete supplier: {str(e)}",
                parent=self,
            )

    def _on_close(self):
        """Close the dialog."""
        self.destroy()


class SupplierFormDialog(ctk.CTkToplevel):
    """
    Dialog for adding or editing a supplier.
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
        self.geometry("400x350")
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

    def _setup_form(self):
        """Create form fields."""
        row = 0

        # Title
        title = "Add Supplier" if not self.supplier_id else "Edit Supplier"
        ctk.CTkLabel(
            self,
            text=title,
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=row, column=0, columnspan=2, padx=20, pady=(20, 15), sticky="w")
        row += 1

        # Name (required)
        ctk.CTkLabel(self, text="Name *").grid(
            row=row, column=0, padx=(20, 10), pady=5, sticky="w"
        )
        self.name_var = ctk.StringVar()
        self.name_entry = ctk.CTkEntry(
            self,
            textvariable=self.name_var,
            width=220,
            placeholder_text="e.g., Costco",
        )
        self.name_entry.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="w")
        row += 1

        # Street Address (optional)
        ctk.CTkLabel(self, text="Street Address").grid(
            row=row, column=0, padx=(20, 10), pady=5, sticky="w"
        )
        self.street_var = ctk.StringVar()
        self.street_entry = ctk.CTkEntry(
            self,
            textvariable=self.street_var,
            width=220,
            placeholder_text="e.g., 123 Main St",
        )
        self.street_entry.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="w")
        row += 1

        # City (required)
        ctk.CTkLabel(self, text="City *").grid(
            row=row, column=0, padx=(20, 10), pady=5, sticky="w"
        )
        self.city_var = ctk.StringVar()
        self.city_entry = ctk.CTkEntry(
            self,
            textvariable=self.city_var,
            width=220,
            placeholder_text="e.g., Issaquah",
        )
        self.city_entry.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="w")
        row += 1

        # State (required)
        ctk.CTkLabel(self, text="State *").grid(
            row=row, column=0, padx=(20, 10), pady=5, sticky="w"
        )
        self.state_var = ctk.StringVar()
        self.state_entry = ctk.CTkEntry(
            self,
            textvariable=self.state_var,
            width=60,
            placeholder_text="WA",
        )
        self.state_entry.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="w")
        row += 1

        # ZIP Code (required)
        ctk.CTkLabel(self, text="ZIP Code *").grid(
            row=row, column=0, padx=(20, 10), pady=5, sticky="w"
        )
        self.zip_var = ctk.StringVar()
        self.zip_entry = ctk.CTkEntry(
            self,
            textvariable=self.zip_var,
            width=100,
            placeholder_text="98027",
        )
        self.zip_entry.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="w")
        row += 1

        # Notes (optional)
        ctk.CTkLabel(self, text="Notes").grid(
            row=row, column=0, padx=(20, 10), pady=5, sticky="w"
        )
        self.notes_var = ctk.StringVar()
        self.notes_entry = ctk.CTkEntry(
            self,
            textvariable=self.notes_var,
            width=220,
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

            self.name_var.set(supplier.get("name", "") or "")
            self.street_var.set(supplier.get("street_address", "") or "")
            self.city_var.set(supplier.get("city", "") or "")
            self.state_var.set(supplier.get("state", "") or "")
            self.zip_var.set(supplier.get("zip_code", "") or "")
            self.notes_var.set(supplier.get("notes", "") or "")

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to load supplier: {str(e)}",
                parent=self,
            )
            self.destroy()

    def _validate(self) -> bool:
        """Validate form fields."""
        errors = []

        if not self.name_var.get().strip():
            errors.append("Name is required")

        if not self.city_var.get().strip():
            errors.append("City is required")

        state = self.state_var.get().strip()
        if not state:
            errors.append("State is required")
        elif len(state) != 2:
            errors.append("State must be a 2-letter code")

        if not self.zip_var.get().strip():
            errors.append("ZIP Code is required")

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

        try:
            if self.supplier_id:
                # Edit mode
                supplier_service.update_supplier(
                    self.supplier_id,
                    name=self.name_var.get().strip(),
                    street_address=self.street_var.get().strip() or None,
                    city=self.city_var.get().strip(),
                    state=self.state_var.get().strip(),
                    zip_code=self.zip_var.get().strip(),
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
                    city=self.city_var.get().strip(),
                    state=self.state_var.get().strip(),
                    zip_code=self.zip_var.get().strip(),
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

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to save supplier: {str(e)}",
                parent=self,
            )

    def _on_cancel(self):
        """Handle cancel button click."""
        self.result = None
        self.destroy()
