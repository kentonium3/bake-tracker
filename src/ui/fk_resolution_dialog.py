"""
FK Resolution Dialog for handling missing foreign key references during import.

Provides a UI for users to resolve missing FK references by:
- Creating a new entity
- Mapping to an existing entity
- Skipping records that reference this FK

Implements the FKResolverCallback protocol from fk_resolver_service.
"""

from tkinter import messagebox
from typing import Dict, List, Optional

import customtkinter as ctk

from src.services.fk_resolver_service import (
    MissingFK,
    Resolution,
    ResolutionChoice,
    find_similar_entities,
)


class FKResolutionDialog(ctk.CTkToplevel):
    """Main dialog for resolving missing FK references.

    Shows the missing FK info and offers three resolution options:
    - Create New: Opens a form to create the missing entity
    - Map to Existing: Shows fuzzy search to map to an existing entity
    - Skip Records: Skip all records referencing this FK
    """

    def __init__(self, parent, missing: MissingFK, records_already_imported: int = 0):
        """Initialize the FK resolution dialog.

        Args:
            parent: Parent window
            missing: MissingFK instance with details about the missing reference
            records_already_imported: Number of records already imported (for cancel handling)
        """
        super().__init__(parent)

        self.missing = missing
        self.result: Optional[Resolution] = None
        self._records_already_imported = records_already_imported

        self.title("Resolve Missing Reference")
        self.geometry("500x350")
        self.resizable(False, False)

        self._setup_ui()

        # Modal behavior
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        # Focus the dialog
        self.focus_force()

        # Bind Escape key
        self.bind("<Escape>", lambda e: self._on_cancel())

    def _setup_ui(self):
        """Set up the dialog UI."""
        # Title
        title_label = ctk.CTkLabel(
            self,
            text="Missing Reference Found",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title_label.pack(pady=(20, 10))

        # Info frame
        info_frame = ctk.CTkFrame(self)
        info_frame.pack(fill="x", padx=20, pady=10)

        entity_type_label = ctk.CTkLabel(
            info_frame,
            text=f"Missing {self.missing.entity_type.title()}:",
            font=ctk.CTkFont(size=12),
        )
        entity_type_label.pack(anchor="w", padx=10, pady=(10, 0))

        value_label = ctk.CTkLabel(
            info_frame,
            text=f"'{self.missing.missing_value}'",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        value_label.pack(anchor="w", padx=20, pady=(0, 5))

        affected_label = ctk.CTkLabel(
            info_frame,
            text=f"Affects {self.missing.affected_record_count} record(s)",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        affected_label.pack(anchor="w", padx=10, pady=(0, 10))

        # Instructions
        instructions = ctk.CTkLabel(
            self,
            text="Choose how to resolve this missing reference:",
            font=ctk.CTkFont(size=12),
        )
        instructions.pack(pady=10)

        # Option buttons frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)

        create_btn = ctk.CTkButton(
            btn_frame,
            text="Create New",
            width=130,
            command=self._on_create,
        )
        create_btn.pack(side="left", padx=5)

        map_btn = ctk.CTkButton(
            btn_frame,
            text="Map to Existing",
            width=130,
            command=self._on_map,
        )
        map_btn.pack(side="left", padx=5)

        skip_btn = ctk.CTkButton(
            btn_frame,
            text="Skip Records",
            width=130,
            fg_color="gray",
            command=self._on_skip,
        )
        skip_btn.pack(side="left", padx=5)

        # Cancel button
        cancel_btn = ctk.CTkButton(
            self,
            text="Cancel Import",
            width=120,
            fg_color="darkred",
            hover_color="red",
            command=self._on_cancel,
        )
        cancel_btn.pack(pady=20)

    def _on_create(self):
        """Handle Create New button click."""
        create_dialog = CreateEntityDialog(
            self, self.missing.entity_type, self.missing.missing_value
        )
        self.wait_window(create_dialog)

        if create_dialog.entity_data:
            self.result = Resolution(
                choice=ResolutionChoice.CREATE,
                entity_type=self.missing.entity_type,
                missing_value=self.missing.missing_value,
                created_entity=create_dialog.entity_data,
            )
            self.destroy()

    def _on_map(self):
        """Handle Map to Existing button click."""
        map_dialog = MapEntityDialog(self, self.missing)
        self.wait_window(map_dialog)

        if map_dialog.selected_id:
            self.result = Resolution(
                choice=ResolutionChoice.MAP,
                entity_type=self.missing.entity_type,
                missing_value=self.missing.missing_value,
                mapped_id=map_dialog.selected_id,
            )
            self.destroy()

    def _on_skip(self):
        """Handle Skip Records button click."""
        if messagebox.askyesno(
            "Confirm Skip",
            f"Are you sure you want to skip all {self.missing.affected_record_count} "
            f"record(s) that reference '{self.missing.missing_value}'?",
            parent=self,
        ):
            self.result = Resolution(
                choice=ResolutionChoice.SKIP,
                entity_type=self.missing.entity_type,
                missing_value=self.missing.missing_value,
            )
            self.destroy()

    def _on_cancel(self):
        """Handle Cancel Import button click."""
        if self._records_already_imported > 0:
            # Show keep/rollback choice per spec
            response = messagebox.askyesnocancel(
                "Cancel Import",
                f"{self._records_already_imported} record(s) have already been imported.\n\n"
                "Yes = Keep imported records, cancel remaining\n"
                "No = Rollback all changes\n"
                "Cancel = Continue import",
                icon="warning",
                parent=self,
            )
            if response is True:  # Yes - keep
                self.result = Resolution(
                    choice=ResolutionChoice.SKIP,
                    entity_type="__cancel_keep__",
                    missing_value="",
                )
                self.destroy()
            elif response is False:  # No - rollback
                self.result = Resolution(
                    choice=ResolutionChoice.SKIP,
                    entity_type="__cancel_rollback__",
                    missing_value="",
                )
                self.destroy()
            # else Cancel - do nothing, continue
        else:
            # No records imported yet, just close
            if messagebox.askyesno(
                "Cancel Import",
                "Are you sure you want to cancel the import?",
                parent=self,
            ):
                self.result = Resolution(
                    choice=ResolutionChoice.SKIP,
                    entity_type="__cancel_rollback__",
                    missing_value="",
                )
                self.destroy()


class MapEntityDialog(ctk.CTkToplevel):
    """Dialog for mapping to an existing entity via fuzzy search."""

    def __init__(self, parent, missing: MissingFK):
        """Initialize the map entity dialog.

        Args:
            parent: Parent window
            missing: MissingFK instance
        """
        super().__init__(parent)

        self.missing = missing
        self.selected_id: Optional[int] = None
        self.similar_entities: List[Dict] = []

        self.title(f"Select Existing {missing.entity_type.title()}")
        self.geometry("450x400")
        self.resizable(True, True)
        self.minsize(400, 300)

        self._setup_ui()

        # Modal behavior
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        # Initial search
        self._do_search()

        # Focus search entry
        self.search_entry.focus_set()

        # Bind Escape key
        self.bind("<Escape>", lambda e: self.destroy())

    def _setup_ui(self):
        """Set up the dialog UI."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Search frame
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="ew")

        ctk.CTkLabel(
            search_frame,
            text="Search:",
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(0, 10))

        self.search_var = ctk.StringVar(value=self.missing.missing_value)
        self.search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            width=300,
        )
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<KeyRelease>", self._on_search_key)
        self.search_entry.bind("<Return>", lambda e: self._do_search())

        search_btn = ctk.CTkButton(
            search_frame,
            text="Search",
            width=70,
            command=self._do_search,
        )
        search_btn.pack(side="left", padx=(10, 0))

        # Results frame
        results_label = ctk.CTkLabel(
            self,
            text="Select an existing entity:",
            font=ctk.CTkFont(size=12),
        )
        results_label.grid(row=0, column=0, padx=20, pady=(60, 5), sticky="w")

        self.results_frame = ctk.CTkScrollableFrame(self)
        self.results_frame.grid(row=1, column=0, padx=20, pady=(5, 10), sticky="nsew")

        # Status label
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        self.status_label.grid(row=2, column=0, padx=20, pady=5)

        # Button frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=3, column=0, padx=20, pady=(5, 15), sticky="e")

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=80,
            fg_color="gray",
            command=self.destroy,
        ).pack(side="right")

    def _on_search_key(self, event):
        """Handle search entry key release with debounce."""
        # Simple debounce - search on Enter or after typing
        if event.keysym == "Return":
            self._do_search()

    def _do_search(self):
        """Perform the fuzzy search."""
        search_term = self.search_var.get().strip()

        # Clear existing results
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        if not search_term:
            self.status_label.configure(text="Enter a search term")
            return

        # Perform search
        self.similar_entities = find_similar_entities(
            self.missing.entity_type, search_term, limit=10
        )

        if not self.similar_entities:
            self.status_label.configure(text="No matching entities found")
            no_results_label = ctk.CTkLabel(
                self.results_frame,
                text="No results found. Try a different search term.",
                text_color="gray",
            )
            no_results_label.pack(pady=20)
            return

        self.status_label.configure(text=f"Found {len(self.similar_entities)} match(es)")

        # Display results as clickable buttons
        for entity in self.similar_entities:
            result_btn = ctk.CTkButton(
                self.results_frame,
                text=entity["display"],
                anchor="w",
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray75", "gray25"),
                command=lambda e=entity: self._select_entity(e),
            )
            result_btn.pack(fill="x", pady=2)

    def _select_entity(self, entity: Dict):
        """Handle entity selection."""
        self.selected_id = entity["id"]
        self.destroy()


class CreateEntityDialog(ctk.CTkToplevel):
    """Dialog for creating a new entity with entity-specific forms."""

    def __init__(self, parent, entity_type: str, default_value: str):
        """Initialize the create entity dialog.

        Args:
            parent: Parent window
            entity_type: Type of entity to create (supplier, ingredient, product)
            default_value: Default value to pre-fill (usually the missing value)
        """
        super().__init__(parent)

        self.entity_type = entity_type
        self.default_value = default_value
        self.entity_data: Optional[Dict] = None

        self.title(f"Create New {entity_type.title()}")
        self.resizable(False, False)

        self._setup_ui()

        # Modal behavior
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        # Bind Escape key
        self.bind("<Escape>", lambda e: self.destroy())

    def _setup_ui(self):
        """Set up the dialog UI based on entity type."""
        if self.entity_type == "supplier":
            self._setup_supplier_form()
        elif self.entity_type == "ingredient":
            self._setup_ingredient_form()
        elif self.entity_type == "product":
            self._setup_product_form()
        else:
            # Fallback for unknown entity types
            self._setup_generic_form()

    def _setup_supplier_form(self):
        """Set up the supplier creation form."""
        self.geometry("400x350")

        # Title
        ctk.CTkLabel(
            self,
            text="Create New Supplier",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(15, 10))

        # Form frame
        form_frame = ctk.CTkFrame(self)
        form_frame.pack(fill="x", padx=20, pady=10)

        # Name (pre-filled)
        ctk.CTkLabel(form_frame, text="Name:*").pack(anchor="w", padx=10, pady=(10, 0))
        self.name_var = ctk.StringVar(value=self.default_value)
        ctk.CTkEntry(form_frame, textvariable=self.name_var, width=300).pack(padx=10, pady=(0, 5))

        # City
        ctk.CTkLabel(form_frame, text="City:*").pack(anchor="w", padx=10, pady=(5, 0))
        self.city_var = ctk.StringVar()
        ctk.CTkEntry(form_frame, textvariable=self.city_var, width=300).pack(padx=10, pady=(0, 5))

        # State
        ctk.CTkLabel(form_frame, text="State (2-letter):*").pack(anchor="w", padx=10, pady=(5, 0))
        self.state_var = ctk.StringVar()
        ctk.CTkEntry(form_frame, textvariable=self.state_var, width=100).pack(
            anchor="w", padx=10, pady=(0, 5)
        )

        # ZIP Code
        ctk.CTkLabel(form_frame, text="ZIP Code:*").pack(anchor="w", padx=10, pady=(5, 0))
        self.zip_var = ctk.StringVar()
        ctk.CTkEntry(form_frame, textvariable=self.zip_var, width=150).pack(
            anchor="w", padx=10, pady=(0, 10)
        )

        # Required fields note
        ctk.CTkLabel(
            self,
            text="* Required fields",
            font=ctk.CTkFont(size=10),
            text_color="gray",
        ).pack(pady=5)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(
            btn_frame,
            text="Create",
            width=100,
            command=self._on_submit_supplier,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=100,
            fg_color="gray",
            command=self.destroy,
        ).pack(side="left", padx=5)

    def _on_submit_supplier(self):
        """Validate and submit supplier form."""
        name = self.name_var.get().strip()
        city = self.city_var.get().strip()
        state = self.state_var.get().strip().upper()
        zip_code = self.zip_var.get().strip()

        # Validate required fields
        if not name:
            messagebox.showerror("Validation Error", "Name is required.", parent=self)
            return
        if not city:
            messagebox.showerror("Validation Error", "City is required.", parent=self)
            return
        if not state or len(state) != 2:
            messagebox.showerror("Validation Error", "State must be a 2-letter code.", parent=self)
            return
        if not zip_code:
            messagebox.showerror("Validation Error", "ZIP Code is required.", parent=self)
            return

        self.entity_data = {
            "name": name,
            "city": city,
            "state": state,
            "zip_code": zip_code,
        }
        self.destroy()

    def _setup_ingredient_form(self):
        """Set up the ingredient creation form."""
        self.geometry("400x350")

        # Title
        ctk.CTkLabel(
            self,
            text="Create New Ingredient",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(15, 10))

        # Form frame
        form_frame = ctk.CTkFrame(self)
        form_frame.pack(fill="x", padx=20, pady=10)

        # Slug (pre-filled)
        ctk.CTkLabel(form_frame, text="Slug:*").pack(anchor="w", padx=10, pady=(10, 0))
        self.slug_var = ctk.StringVar(value=self.default_value)
        ctk.CTkEntry(form_frame, textvariable=self.slug_var, width=300).pack(padx=10, pady=(0, 5))

        # Display Name
        ctk.CTkLabel(form_frame, text="Display Name:*").pack(anchor="w", padx=10, pady=(5, 0))
        self.display_name_var = ctk.StringVar()
        ctk.CTkEntry(form_frame, textvariable=self.display_name_var, width=300).pack(
            padx=10, pady=(0, 5)
        )

        # Category
        ctk.CTkLabel(form_frame, text="Category:*").pack(anchor="w", padx=10, pady=(5, 0))
        self.category_var = ctk.StringVar()
        ctk.CTkEntry(form_frame, textvariable=self.category_var, width=300).pack(
            padx=10, pady=(0, 5)
        )

        # Description (optional)
        ctk.CTkLabel(form_frame, text="Description:").pack(anchor="w", padx=10, pady=(5, 0))
        self.description_var = ctk.StringVar()
        ctk.CTkEntry(form_frame, textvariable=self.description_var, width=300).pack(
            padx=10, pady=(0, 10)
        )

        # Required fields note
        ctk.CTkLabel(
            self,
            text="* Required fields",
            font=ctk.CTkFont(size=10),
            text_color="gray",
        ).pack(pady=5)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(
            btn_frame,
            text="Create",
            width=100,
            command=self._on_submit_ingredient,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=100,
            fg_color="gray",
            command=self.destroy,
        ).pack(side="left", padx=5)

    def _on_submit_ingredient(self):
        """Validate and submit ingredient form."""
        slug = self.slug_var.get().strip()
        display_name = self.display_name_var.get().strip()
        category = self.category_var.get().strip()
        description = self.description_var.get().strip()

        # Validate required fields
        if not slug:
            messagebox.showerror("Validation Error", "Slug is required.", parent=self)
            return
        if not display_name:
            messagebox.showerror("Validation Error", "Display Name is required.", parent=self)
            return
        if not category:
            messagebox.showerror("Validation Error", "Category is required.", parent=self)
            return

        self.entity_data = {
            "slug": slug,
            "display_name": display_name,
            "category": category,
        }
        if description:
            self.entity_data["description"] = description
        self.destroy()

    def _setup_product_form(self):
        """Set up the product creation form."""
        self.geometry("400x400")

        # Title
        ctk.CTkLabel(
            self,
            text="Create New Product",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(15, 10))

        # Form frame
        form_frame = ctk.CTkFrame(self)
        form_frame.pack(fill="x", padx=20, pady=10)

        # Ingredient Slug (pre-filled)
        ctk.CTkLabel(form_frame, text="Ingredient Slug:*").pack(anchor="w", padx=10, pady=(10, 0))
        self.ingredient_slug_var = ctk.StringVar(value=self.default_value)
        ctk.CTkEntry(form_frame, textvariable=self.ingredient_slug_var, width=300).pack(
            padx=10, pady=(0, 5)
        )

        # Brand
        ctk.CTkLabel(form_frame, text="Brand:").pack(anchor="w", padx=10, pady=(5, 0))
        self.brand_var = ctk.StringVar()
        ctk.CTkEntry(form_frame, textvariable=self.brand_var, width=300).pack(padx=10, pady=(0, 5))

        # Package Unit
        ctk.CTkLabel(form_frame, text="Package Unit (e.g., oz, lb):*").pack(
            anchor="w", padx=10, pady=(5, 0)
        )
        self.package_unit_var = ctk.StringVar()
        ctk.CTkEntry(form_frame, textvariable=self.package_unit_var, width=150).pack(
            anchor="w", padx=10, pady=(0, 5)
        )

        # Package Unit Quantity
        ctk.CTkLabel(form_frame, text="Package Unit Quantity:*").pack(
            anchor="w", padx=10, pady=(5, 0)
        )
        self.package_qty_var = ctk.StringVar()
        ctk.CTkEntry(form_frame, textvariable=self.package_qty_var, width=150).pack(
            anchor="w", padx=10, pady=(0, 5)
        )

        # Product Name (optional)
        ctk.CTkLabel(form_frame, text="Product Name:").pack(anchor="w", padx=10, pady=(5, 0))
        self.product_name_var = ctk.StringVar()
        ctk.CTkEntry(form_frame, textvariable=self.product_name_var, width=300).pack(
            padx=10, pady=(0, 10)
        )

        # Required fields note
        ctk.CTkLabel(
            self,
            text="* Required fields",
            font=ctk.CTkFont(size=10),
            text_color="gray",
        ).pack(pady=5)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(
            btn_frame,
            text="Create",
            width=100,
            command=self._on_submit_product,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=100,
            fg_color="gray",
            command=self.destroy,
        ).pack(side="left", padx=5)

    def _on_submit_product(self):
        """Validate and submit product form."""
        ingredient_slug = self.ingredient_slug_var.get().strip()
        brand = self.brand_var.get().strip()
        package_unit = self.package_unit_var.get().strip()
        package_qty_str = self.package_qty_var.get().strip()
        product_name = self.product_name_var.get().strip()

        # Validate required fields
        if not ingredient_slug:
            messagebox.showerror("Validation Error", "Ingredient Slug is required.", parent=self)
            return
        if not package_unit:
            messagebox.showerror("Validation Error", "Package Unit is required.", parent=self)
            return
        if not package_qty_str:
            messagebox.showerror(
                "Validation Error", "Package Unit Quantity is required.", parent=self
            )
            return

        try:
            package_qty = float(package_qty_str)
            if package_qty <= 0:
                raise ValueError("Must be positive")
        except ValueError:
            messagebox.showerror(
                "Validation Error",
                "Package Unit Quantity must be a positive number.",
                parent=self,
            )
            return

        self.entity_data = {
            "ingredient_slug": ingredient_slug,
            "package_unit": package_unit,
            "package_unit_quantity": package_qty,
        }
        if brand:
            self.entity_data["brand"] = brand
        if product_name:
            self.entity_data["product_name"] = product_name
        self.destroy()

    def _setup_generic_form(self):
        """Set up a generic form for unknown entity types."""
        self.geometry("400x200")

        ctk.CTkLabel(
            self,
            text=f"Create New {self.entity_type.title()}",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(15, 10))

        ctk.CTkLabel(
            self,
            text=f"Entity type '{self.entity_type}' is not supported for creation.",
            text_color="red",
        ).pack(pady=20)

        ctk.CTkButton(
            self,
            text="Close",
            width=100,
            command=self.destroy,
        ).pack(pady=15)


class UIFKResolver:
    """UI implementation of FKResolverCallback protocol.

    Uses FKResolutionDialog to prompt the user for each missing FK.
    """

    def __init__(self, parent_window):
        """Initialize the UI FK resolver.

        Args:
            parent_window: Parent window for dialogs
        """
        self.parent = parent_window
        self._records_imported = 0

    def set_records_imported(self, count: int):
        """Update the count of records already imported."""
        self._records_imported = count

    def resolve(self, missing: MissingFK) -> Resolution:
        """Prompt user to resolve a missing FK reference.

        Args:
            missing: MissingFK instance with details about the missing reference

        Returns:
            Resolution with user's choice
        """
        dialog = FKResolutionDialog(
            self.parent, missing, records_already_imported=self._records_imported
        )
        self.parent.wait_window(dialog)

        if dialog.result:
            return dialog.result
        else:
            # Dialog closed without selection - treat as skip
            return Resolution(
                choice=ResolutionChoice.SKIP,
                entity_type=missing.entity_type,
                missing_value=missing.missing_value,
            )
