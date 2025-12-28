"""
My Ingredients tab for the Seasonal Baking Tracker.

Provides CRUD interface for managing generic ingredient catalog
(brand-agnostic ingredient definitions) using the v0.4.0 refactored architecture.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import unicodedata
from typing import Optional, List, Dict, Any
from tkinter import messagebox


def normalize_for_search(text: str) -> str:
    """
    Normalize text for search by removing diacriticals and converting to lowercase.

    Examples:
        "Crème Brûlée" -> "creme brulee"
        "Café" -> "cafe"
        "Jalapeño" -> "jalapeno"
    """
    if not text:
        return ""

    # Normalize to NFKD form (canonical decomposition)
    nfkd = unicodedata.normalize("NFKD", text)

    # Remove combining marks (accents)
    ascii_text = nfkd.encode("ASCII", "ignore").decode("ASCII")

    # Convert to lowercase for case-insensitive matching
    return ascii_text.lower()

from src.services import ingredient_service, product_service
from src.services.unit_service import get_units_for_dropdown
from src.services.exceptions import (
    IngredientInUse,
    IngredientNotFoundBySlug,
    SlugAlreadyExists,
    ValidationError,
    DatabaseError,
    ProductInUse,
    ProductNotFound,
)
from src.utils.constants import (
    PADDING_MEDIUM,
    PADDING_LARGE,
    VOLUME_UNITS,
    WEIGHT_UNITS,
    PACKAGE_TYPES,
)
from src.services import ingredient_service


class IngredientsTab(ctk.CTkFrame):
    """
    Ingredient catalog management tab.

    Provides interface for:
    - Viewing all generic ingredients
    - Adding new ingredients
    - Editing existing ingredients
    - Deleting ingredients (with dependency checks)
    - Searching by name
    - Filtering by category
    """

    def __init__(self, parent):
        """
        Initialize the ingredients tab.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.selected_ingredient_slug: Optional[str] = None
        self.ingredients: List[dict] = []
        self._data_loaded = False  # Lazy loading flag

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Title
        self.grid_rowconfigure(1, weight=0)  # Search/filter
        self.grid_rowconfigure(2, weight=0)  # Action buttons
        self.grid_rowconfigure(3, weight=1)  # Ingredient list
        self.grid_rowconfigure(4, weight=0)  # Status bar

        # Create UI components
        self._create_title()
        self._create_search_filter()
        self._create_action_buttons()
        self._create_ingredient_list()
        self._create_status_bar()

        # Grid the frame
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Show initial state - data will be loaded when tab is selected
        self._show_initial_state()

    def _create_title(self):
        """Create the title label."""
        title_label = ctk.CTkLabel(
            self,
            text="My Ingredients",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title_label.grid(
            row=0, column=0, sticky="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_MEDIUM)
        )

    def _create_search_filter(self):
        """Create search and filter controls."""
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.grid(row=1, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_MEDIUM)
        search_frame.grid_columnconfigure(0, weight=1)

        # Search entry
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search by ingredient name...",
            height=36,
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, PADDING_MEDIUM))
        self.search_entry.bind("<KeyRelease>", self._on_search)

        # Category filter dropdown
        self.category_var = ctk.StringVar(value="All Categories")
        self.category_dropdown = ctk.CTkOptionMenu(
            search_frame,
            values=["All Categories"],  # Will be populated dynamically
            variable=self.category_var,
            command=self._on_category_change,
            width=200,
        )
        self.category_dropdown.grid(row=0, column=1, padx=(0, PADDING_MEDIUM))

        # Clear button
        clear_button = ctk.CTkButton(
            search_frame,
            text="Clear",
            command=self._clear_filters,
            width=100,
        )
        clear_button.grid(row=0, column=2)

    def _create_action_buttons(self):
        """Create action buttons for CRUD operations."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=2, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_MEDIUM)

        # Add button
        add_button = ctk.CTkButton(
            button_frame,
            text="➕ Add Ingredient",
            command=self._add_ingredient,
            width=150,
            height=36,
        )
        add_button.grid(row=0, column=0, padx=(0, PADDING_MEDIUM))

        # Edit button
        self.edit_button = ctk.CTkButton(
            button_frame,
            text="✏️ Edit",
            command=self._edit_ingredient,
            width=120,
            height=36,
            state="disabled",
        )
        self.edit_button.grid(row=0, column=1, padx=(0, PADDING_MEDIUM))

    def _create_ingredient_list(self):
        """Create the ingredient list using ttk.Treeview for performance."""
        # Container frame for grid and scrollbar
        grid_container = ctk.CTkFrame(self)
        grid_container.grid(
            row=3,
            column=0,
            sticky="nsew",
            padx=PADDING_LARGE,
            pady=PADDING_MEDIUM,
        )
        grid_container.grid_columnconfigure(0, weight=1)
        grid_container.grid_rowconfigure(0, weight=1)

        # Track current sort state
        self.sort_column = "name"
        self.sort_ascending = True

        # Define columns - no Type column per correction spec
        columns = ("category", "name", "density")
        self.tree = ttk.Treeview(
            grid_container,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=20,  # Show more rows (default is 10)
        )

        # Configure column headings with click-to-sort
        self.tree.heading("category", text="Category", anchor="w",
                          command=lambda: self._on_header_click("category"))
        self.tree.heading("name", text="Name", anchor="w",
                          command=lambda: self._on_header_click("name"))
        self.tree.heading("density", text="Density", anchor="w",
                          command=lambda: self._on_header_click("density_display"))

        # Configure column widths
        self.tree.column("category", width=150, minwidth=100)
        self.tree.column("name", width=350, minwidth=200)
        self.tree.column("density", width=150, minwidth=100)

        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(
            grid_container,
            orient="vertical",
            command=self.tree.yview,
        )
        x_scrollbar = ttk.Scrollbar(
            grid_container,
            orient="horizontal",
            command=self.tree.xview,
        )
        self.tree.configure(
            yscrollcommand=y_scrollbar.set,
            xscrollcommand=x_scrollbar.set,
        )

        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar.grid(row=1, column=0, sticky="ew")

        # Configure tag for packaging items
        self.tree.tag_configure("packaging", foreground="#0066cc")

        # Bind events
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def _on_header_click(self, sort_key: str):
        """Handle column header click for sorting."""
        if self.sort_column == sort_key:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = sort_key
            self.sort_ascending = True
        self._update_ingredient_display()

    def _on_double_click(self, event):
        """Handle double-click on ingredient row to open edit dialog."""
        selection = self.tree.selection()
        if selection:
            slug = selection[0]
            self.selected_ingredient_slug = slug
            self._enable_selection_buttons()
            self._edit_ingredient()

    def _on_tree_select(self, event):
        """Handle tree selection change."""
        selection = self.tree.selection()
        if selection:
            self.selected_ingredient_slug = selection[0]
            self._enable_selection_buttons()
        else:
            self._disable_selection_buttons()

    def _create_status_bar(self):
        """Create status bar for displaying messages."""
        self.status_label = ctk.CTkLabel(
            self,
            text="Ready",
            anchor="w",
            height=30,
        )
        self.status_label.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=PADDING_LARGE,
            pady=(PADDING_MEDIUM, PADDING_LARGE),
        )

    def refresh(self):
        """Refresh the ingredient list from the database."""
        try:
            # Get all ingredients from service
            self.ingredients = ingredient_service.get_all_ingredients()

            # Update category dropdown from actual database categories
            # (same approach as Products tab for consistency)
            categories = sorted(set(
                ing.get("category", "")
                for ing in self.ingredients
                if ing.get("category")
            ))
            category_list = ["All Categories"] + categories
            self.category_dropdown.configure(values=category_list)

            # Update display
            self._update_ingredient_display()

            # Update status
            count = len(self.ingredients)
            self.update_status(f"{count} ingredient{'s' if count != 1 else ''} loaded")

        except DatabaseError as e:
            messagebox.showerror("Database Error", f"Failed to load ingredients: {e}")
            self.update_status("Error loading ingredients")

    def _show_initial_state(self):
        """Show initial loading state."""
        # Clear any existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.update_status("Loading...")

    def _update_ingredient_display(self):
        """Update the displayed list of ingredients based on current filters."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Apply filters
        filtered_ingredients = self._apply_filters(self.ingredients)

        # Populate grid with all ingredients (Treeview handles large datasets well)
        for ingredient in filtered_ingredients:
            category = ingredient.get("category", "Uncategorized")
            name = ingredient["name"]
            is_packaging = ingredient.get("is_packaging", False)
            density = ingredient.get("density_display", "—")
            if density == "Not set":
                density = "—"

            values = (category, name, density)
            tags = ("packaging",) if is_packaging else ()

            # Use slug as the item ID for easy lookup
            self.tree.insert("", "end", iid=ingredient["slug"], values=values, tags=tags)

        # Restore selection if still present
        if self.selected_ingredient_slug:
            try:
                self.tree.selection_set(self.selected_ingredient_slug)
                self._enable_selection_buttons()
            except tk.TclError:
                # Item not in filtered list
                self.selected_ingredient_slug = None
                self._disable_selection_buttons()
        else:
            self._disable_selection_buttons()

        # Update status with count
        count = len(filtered_ingredients)
        total = len(self.ingredients)
        if count < total:
            self.update_status(f"Showing {count} of {total} ingredients")
        else:
            self.update_status(f"{count} ingredient{'s' if count != 1 else ''}")

    def _apply_filters(self, ingredients: List[dict]) -> List[dict]:
        """Apply search, category filters, and sorting to ingredient list."""
        filtered = ingredients

        # Apply search filter with diacritical normalization
        # (e.g., "creme" matches "crème", "cafe" matches "café")
        search_text = normalize_for_search(self.search_entry.get())
        if search_text:
            filtered = [
                ing for ing in filtered
                if search_text in normalize_for_search(ing["name"])
            ]

        # Apply category filter
        category = self.category_var.get()
        if category and category != "All Categories":
            filtered = [ing for ing in filtered if ing.get("category") == category]

        # Sort by selected column
        sort_key = getattr(self, "sort_column", "name")
        ascending = getattr(self, "sort_ascending", True)
        filtered = sorted(
            filtered,
            key=lambda x: (x.get(sort_key) or "").lower() if isinstance(x.get(sort_key), str) else str(x.get(sort_key, "")),
            reverse=not ascending,
        )

        return filtered

    def _on_search(self, event=None):
        """Handle search text change."""
        self._update_ingredient_display()

    def _on_category_change(self, category: str):
        """Handle category filter change."""
        self._update_ingredient_display()

    def _clear_filters(self):
        """Clear all filters and refresh display."""
        self.search_entry.delete(0, "end")
        self.category_var.set("All Categories")
        self._update_ingredient_display()

    def select_ingredient(self, ingredient_slug: str) -> None:
        """
        Programmatically select an ingredient from the list.

        Args:
            ingredient_slug: Slug of the ingredient to select.
        """
        if not ingredient_slug:
            return

        if not any(ing["slug"] == ingredient_slug for ing in self.ingredients):
            self.refresh()

        if not any(ing["slug"] == ingredient_slug for ing in self.ingredients):
            self.update_status(f"Ingredient '{ingredient_slug}' not found")
            return

        self.selected_ingredient_slug = ingredient_slug
        self._update_ingredient_display()
        # Treeview selection is handled in _update_ingredient_display()
        self.update_status(f"Ingredient '{ingredient_slug}' selected")

    def _enable_selection_buttons(self):
        """Enable buttons that require a selection."""
        self.edit_button.configure(state="normal")

    def _disable_selection_buttons(self):
        """Disable buttons that require a selection."""
        self.edit_button.configure(state="disabled")
        self.selected_ingredient_slug = None

    def _add_ingredient(self):
        """Open dialog to add a new ingredient."""
        dialog = IngredientFormDialog(self, title="Add Ingredient")
        self.wait_window(dialog)

        if dialog.result:
            try:
                # Create ingredient using service
                ingredient_obj = ingredient_service.create_ingredient(dialog.result)
                ingredient_name = getattr(
                    ingredient_obj, "name", dialog.result.get("name", "Ingredient")
                )
                self.selected_ingredient_slug = getattr(ingredient_obj, "slug", None)
                self.refresh()
                # Selection is restored by refresh() -> _update_ingredient_display()
                self.update_status(f"Ingredient '{ingredient_name}' added successfully")
                messagebox.showinfo("Success", f"Ingredient '{ingredient_name}' created!")

            except ValidationError as e:
                messagebox.showerror("Validation Error", str(e))
            except SlugAlreadyExists as e:
                messagebox.showerror("Duplicate Ingredient", str(e))
            except DatabaseError as e:
                messagebox.showerror("Database Error", f"Failed to create ingredient: {e}")

    def _edit_ingredient(self):
        """Open dialog to edit the selected ingredient."""
        if not self.selected_ingredient_slug:
            return

        try:
            # Get current ingredient data
            ingredient_obj = ingredient_service.get_ingredient(self.selected_ingredient_slug)
            ingredient_data = (
                ingredient_obj.to_dict()
                if hasattr(ingredient_obj, "to_dict")
                else {
                    "name": ingredient_obj.display_name,
                    "category": ingredient_obj.category,
                    "density_volume_value": ingredient_obj.density_volume_value,
                    "density_volume_unit": ingredient_obj.density_volume_unit,
                    "density_weight_value": ingredient_obj.density_weight_value,
                    "density_weight_unit": ingredient_obj.density_weight_unit,
                }
            )
            # Store slug in ingredient_data for delete operation
            ingredient_data["slug"] = self.selected_ingredient_slug

            dialog = IngredientFormDialog(
                self,
                ingredient=ingredient_data,
                title="Edit Ingredient",
            )
            self.wait_window(dialog)

            # Check if ingredient was deleted
            if dialog.deleted:
                self.selected_ingredient_slug = None
                self.refresh()
                return

            if dialog.result:
                # Update ingredient using service
                updated_obj = ingredient_service.update_ingredient(
                    self.selected_ingredient_slug,
                    dialog.result,
                )
                if updated_obj:
                    updated_name = getattr(
                        updated_obj, "name", dialog.result.get("name", "Ingredient")
                    )
                    self.selected_ingredient_slug = getattr(
                        updated_obj, "slug", self.selected_ingredient_slug
                    )
                    self.update_status(f"Ingredient '{updated_name}' updated successfully")
                else:
                    self.update_status("Ingredient updated successfully")
                self.refresh()
                # Selection is restored by refresh() -> _update_ingredient_display()
                messagebox.showinfo("Success", "Ingredient updated!")

        except IngredientNotFoundBySlug:
            messagebox.showerror("Error", "Ingredient not found")
            self.refresh()
        except ValidationError as e:
            messagebox.showerror("Validation Error", str(e))
        except DatabaseError as e:
            messagebox.showerror("Database Error", f"Failed to update ingredient: {e}")

    def _delete_ingredient(self):
        """Delete the selected ingredient after confirmation."""
        if not self.selected_ingredient_slug:
            return

        try:
            # Get ingredient name for confirmation
            ingredient = ingredient_service.get_ingredient(self.selected_ingredient_slug)
            name = ingredient.display_name  # Fixed: Ingredient uses display_name not name

            # Confirm deletion
            result = messagebox.askyesno(
                "Confirm Deletion",
                f"Are you sure you want to delete '{name}'?\n\n"
                "This will fail if the ingredient has products or is used in recipes.",
            )

            if result:
                # Delete using service
                ingredient_service.delete_ingredient(self.selected_ingredient_slug)
                self.selected_ingredient_slug = None
                self.refresh()
                self.update_status(f"Ingredient '{name}' deleted successfully")
                messagebox.showinfo("Success", "Ingredient deleted!")

        except IngredientNotFoundBySlug:
            messagebox.showerror("Error", "Ingredient not found")
            self.refresh()
        except IngredientInUse as e:
            messagebox.showerror(
                "Cannot Delete",
                f"Cannot delete this ingredient:\n\n{e}\n\n"
                "Delete associated products/recipes first.",
            )
        except DatabaseError as e:
            messagebox.showerror("Database Error", f"Failed to delete ingredient: {e}")
        except Exception as e:
            # Catch-all for unexpected errors
            messagebox.showerror("Error", f"Unexpected error deleting ingredient: {e}")
            import traceback

            traceback.print_exc()

    def update_status(self, message: str):
        """Update the status bar message."""
        self.status_label.configure(text=message)


class IngredientFormDialog(ctk.CTkToplevel):
    """
    Dialog for creating or editing a generic ingredient.

    Simplified form for the v0.4.0 architecture (no brand, quantity, etc.).
    """

    def __init__(
        self,
        parent,
        ingredient: Optional[dict] = None,
        title: str = "Add Ingredient",
    ):
        """
        Initialize the ingredient form dialog.

        Args:
            parent: Parent window
            ingredient: Existing ingredient dict to edit (None for new)
            title: Dialog title
        """
        super().__init__(parent)

        # Store reference to parent tab for accessing data
        self.parent_tab = parent

        if ingredient is not None and hasattr(ingredient, "to_dict"):
            ingredient = ingredient.to_dict()
        self.ingredient = ingredient
        self.result: Optional[Dict[str, Any]] = None
        self.deleted = False  # Track if item was deleted

        # Configure window
        self.title(title)
        self.geometry("550x580")
        self.resizable(False, False)

        # Center on parent
        self.transient(parent)
        self.grab_set()

        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Create form
        self._create_form()
        self._create_buttons()

        # Populate if editing
        if self.ingredient:
            self._populate_form()

    def _create_form(self):
        """Create form fields."""
        form_frame = ctk.CTkFrame(self)
        form_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        form_frame.grid_columnconfigure(1, weight=1)

        row = 0

        # Name field - editable when adding, read-only when editing
        # (Name is tied to slug which is used as FK, so editing is not supported)
        if self.ingredient:
            # Editing mode - show name as read-only label
            ctk.CTkLabel(form_frame, text="Name:").grid(
                row=row, column=0, sticky="w", padx=10, pady=(10, 5)
            )
            # Get name from either 'name' or 'display_name' key
            ingredient_name = self.ingredient.get("name") or self.ingredient.get("display_name", "")
            self.name_label = ctk.CTkLabel(
                form_frame,
                text=ingredient_name,
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w",
            )
            self.name_label.grid(row=row, column=1, sticky="ew", padx=10, pady=(10, 5))
            self.name_entry = None  # No entry when editing
        else:
            # Add mode - editable entry
            ctk.CTkLabel(form_frame, text="Name*:").grid(
                row=row, column=0, sticky="w", padx=10, pady=(10, 5)
            )
            self.name_entry = ctk.CTkEntry(form_frame, placeholder_text="e.g., All-Purpose Flour")
            self.name_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=(10, 5))
        row += 1

        # Feature 011: Is Packaging checkbox
        ctk.CTkLabel(form_frame, text="Type:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.is_packaging_var = ctk.BooleanVar(value=False)
        self.is_packaging_checkbox = ctk.CTkCheckBox(
            form_frame,
            text="This is a packaging material (bags, boxes, ribbon, etc.)",
            variable=self.is_packaging_var,
            command=self._on_packaging_checkbox_change,
        )
        self.is_packaging_checkbox.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        row += 1

        # Category field (required) - now a dropdown that changes based on is_packaging
        # Load food categories from database for consistency with other dropdowns
        self.food_categories_from_db = sorted(set(
            ing.get("category", "") for ing in self.parent_tab.ingredients
            if ing.get("category") and not ing.get("is_packaging")
        )) or ["Uncategorized"]

        ctk.CTkLabel(form_frame, text="Category*:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.category_var = ctk.StringVar(value="")
        self.category_dropdown = ctk.CTkComboBox(
            form_frame,
            values=self.food_categories_from_db,
            variable=self.category_var,
            width=250,
        )
        self.category_dropdown.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        row += 1

        # Density section (4-field input)
        ctk.CTkLabel(form_frame, text="Density (optional):").grid(
            row=row, column=0, sticky="nw", padx=10, pady=5
        )

        # Create density frame for 4-field layout
        density_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        density_frame.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        row += 1

        # Volume value entry
        self.density_volume_value_entry = ctk.CTkEntry(
            density_frame,
            width=70,
            placeholder_text="1.0",
        )
        self.density_volume_value_entry.grid(row=0, column=0, padx=(0, 5))

        # Volume unit dropdown
        self.density_volume_unit_var = ctk.StringVar(value="")
        self.density_volume_unit_dropdown = ctk.CTkComboBox(
            density_frame,
            values=[""] + VOLUME_UNITS,
            variable=self.density_volume_unit_var,
            width=90,
        )
        self.density_volume_unit_dropdown.grid(row=0, column=1, padx=(0, 10))

        # Equals label
        ctk.CTkLabel(
            density_frame,
            text="=",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=2, padx=10)

        # Weight value entry
        self.density_weight_value_entry = ctk.CTkEntry(
            density_frame,
            width=70,
            placeholder_text="4.25",
        )
        self.density_weight_value_entry.grid(row=0, column=3, padx=(10, 5))

        # Weight unit dropdown
        self.density_weight_unit_var = ctk.StringVar(value="")
        self.density_weight_unit_dropdown = ctk.CTkComboBox(
            density_frame,
            values=[""] + WEIGHT_UNITS,
            variable=self.density_weight_unit_var,
            width=90,
        )
        self.density_weight_unit_dropdown.grid(row=0, column=4)

        # Density error label (hidden by default)
        self.density_error_label = ctk.CTkLabel(
            form_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#F44336",  # Red
        )
        self.density_error_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=0)
        row += 1

        # Help text
        help_label = ctk.CTkLabel(
            form_frame,
            text="* Required fields\n\n"
            "Density is used for volume-weight conversions.\n"
            "Example: 1 cup = 4.25 oz (for flour)\n"
            "Leave all density fields blank if not applicable.",
            text_color="gray",
            justify="left",
        )
        help_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=10)

    def _create_buttons(self):
        """Create Save, Cancel, and Delete buttons."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        button_frame.grid_columnconfigure(0, weight=1)  # Left side expands

        # Delete button on left (only when editing)
        if self.ingredient:
            delete_button = ctk.CTkButton(
                button_frame,
                text="Delete",
                command=self._delete,
                width=100,
                fg_color="#8B0000",
                hover_color="#B22222",
            )
            delete_button.grid(row=0, column=0, sticky="w")

        # Cancel and Save buttons on right
        right_buttons = ctk.CTkFrame(button_frame, fg_color="transparent")
        right_buttons.grid(row=0, column=1, sticky="e")

        cancel_button = ctk.CTkButton(
            right_buttons,
            text="Cancel",
            command=self._cancel,
            width=120,
        )
        cancel_button.grid(row=0, column=0, padx=(0, 10))

        save_button = ctk.CTkButton(
            right_buttons,
            text="Save",
            command=self._save,
            width=120,
        )
        save_button.grid(row=0, column=1)

    def _on_packaging_checkbox_change(self):
        """Handle packaging checkbox change - update category dropdown options."""
        if self.is_packaging_var.get():
            # Packaging ingredient - show packaging categories from database
            packaging_categories = ingredient_service.get_distinct_ingredient_categories(
                include_packaging=True
            )
            if not packaging_categories:
                packaging_categories = ["Other Packaging"]  # Default if no packaging exists
            self.category_dropdown.configure(values=packaging_categories)
            # Clear current selection if it's not a packaging category
            current = self.category_var.get()
            if current and current not in packaging_categories:
                self.category_var.set("")
        else:
            # Food ingredient - show food categories from database
            self.category_dropdown.configure(values=self.food_categories_from_db)
            # Clear current selection if it's not in the database categories
            current = self.category_var.get()
            if current and current not in self.food_categories_from_db:
                self.category_var.set("")

    def _populate_form(self):
        """Populate form with existing ingredient data."""
        if not self.ingredient:
            return

        # Name is shown as read-only label in edit mode (set during _create_form)

        # Feature 011: Set is_packaging checkbox and update category dropdown
        is_packaging = self.ingredient.get("is_packaging", False)
        self.is_packaging_var.set(is_packaging)
        self._on_packaging_checkbox_change()  # Update dropdown options

        # Set category value
        category = self.ingredient.get("category", "")
        self.category_var.set(category)

        # Populate 4-field density
        if self.ingredient.get("density_volume_value") is not None:
            self.density_volume_value_entry.insert(
                0, str(self.ingredient["density_volume_value"])
            )
        if self.ingredient.get("density_volume_unit"):
            self.density_volume_unit_var.set(self.ingredient["density_volume_unit"])
        if self.ingredient.get("density_weight_value") is not None:
            self.density_weight_value_entry.insert(
                0, str(self.ingredient["density_weight_value"])
            )
        if self.ingredient.get("density_weight_unit"):
            self.density_weight_unit_var.set(self.ingredient["density_weight_unit"])

    def _get_density_values(self):
        """Get density values from form fields.

        Returns:
            Tuple of (volume_value, volume_unit, weight_value, weight_unit)
        """
        # Get volume value
        volume_value_str = self.density_volume_value_entry.get().strip()
        volume_value = float(volume_value_str) if volume_value_str else None

        # Get volume unit
        volume_unit = self.density_volume_unit_var.get()
        volume_unit = volume_unit if volume_unit else None

        # Get weight value
        weight_value_str = self.density_weight_value_entry.get().strip()
        weight_value = float(weight_value_str) if weight_value_str else None

        # Get weight unit
        weight_unit = self.density_weight_unit_var.get()
        weight_unit = weight_unit if weight_unit else None

        return volume_value, volume_unit, weight_value, weight_unit

    def _validate_density_input(self):
        """Validate density input fields.

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            volume_value, volume_unit, weight_value, weight_unit = self._get_density_values()
        except ValueError:
            return False, "Please enter valid numbers for density values"

        from src.services.ingredient_service import validate_density_fields
        return validate_density_fields(volume_value, volume_unit, weight_value, weight_unit)

    def _save(self):
        """Validate and save the form data."""
        # Get values - name is only editable when adding (not editing)
        if self.name_entry:
            # Add mode - get name from entry
            name = self.name_entry.get().strip()
            if not name:
                messagebox.showerror("Validation Error", "Name is required")
                return
        else:
            # Edit mode - name is read-only, use existing name
            name = self.ingredient.get("name") or self.ingredient.get("display_name", "")

        category = self.category_var.get().strip()  # Now using dropdown
        is_packaging = self.is_packaging_var.get()  # Feature 011

        # Validate required fields
        if not category:
            messagebox.showerror("Validation Error", "Category is required")
            return

        # Validate density fields
        is_valid, error = self._validate_density_input()
        if not is_valid:
            self.density_error_label.configure(text=error)
            return

        # Clear error on success
        self.density_error_label.configure(text="")

        # Get density values
        try:
            volume_value, volume_unit, weight_value, weight_unit = self._get_density_values()
        except ValueError:
            self.density_error_label.configure(text="Please enter valid numbers")
            return

        # Build result dict
        result: Dict[str, Any] = {
            "name": name,
            "category": category,
            "is_packaging": is_packaging,  # Feature 011
        }

        # Add density fields if any are provided
        if volume_value is not None:
            result["density_volume_value"] = volume_value
        if volume_unit:
            result["density_volume_unit"] = volume_unit
        if weight_value is not None:
            result["density_weight_value"] = weight_value
        if weight_unit:
            result["density_weight_unit"] = weight_unit

        self.result = result

        self.destroy()

    def _cancel(self):
        """Cancel the form."""
        self.result = None
        self.destroy()

    def _delete(self):
        """Delete the ingredient after confirmation."""
        if not self.ingredient:
            return

        # Get ingredient name for confirmation
        name = self.ingredient.get("name") or self.ingredient.get("display_name", "")
        slug = self.ingredient.get("slug")

        if not slug:
            messagebox.showerror("Error", "Cannot delete: ingredient slug not found")
            return

        # Confirm deletion
        result = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete '{name}'?\n\n"
            "This will fail if the ingredient has products or is used in recipes.",
        )

        if result:
            try:
                # Delete using service
                ingredient_service.delete_ingredient(slug)
                self.deleted = True
                self.result = None
                messagebox.showinfo("Success", f"Ingredient '{name}' deleted!")
                self.destroy()

            except IngredientNotFoundBySlug:
                messagebox.showerror("Error", "Ingredient not found")
            except IngredientInUse as e:
                messagebox.showerror(
                    "Cannot Delete",
                    f"Cannot delete this ingredient:\n\n{e}\n\n"
                    "Delete associated products/recipes first.",
                )
            except DatabaseError as e:
                messagebox.showerror("Database Error", f"Failed to delete ingredient: {e}")

