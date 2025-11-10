"""
My Ingredients tab for the Seasonal Baking Tracker.

Provides CRUD interface for managing generic ingredient catalog
(brand-agnostic ingredient definitions) using the v0.4.0 refactored architecture.
"""

import customtkinter as ctk
from typing import Optional, List
from tkinter import messagebox

from src.services import ingredient_service
from src.services.exceptions import NotFound, ValidationError, DatabaseError
from src.utils.constants import PADDING_MEDIUM, PADDING_LARGE


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

        # Load initial data
        self.refresh()

        # Grid the frame
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def _create_title(self):
        """Create the title label."""
        title_label = ctk.CTkLabel(
            self,
            text="My Ingredients",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title_label.grid(row=0, column=0, sticky="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_MEDIUM))

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

        # Delete button
        self.delete_button = ctk.CTkButton(
            button_frame,
            text="🗑️ Delete",
            command=self._delete_ingredient,
            width=120,
            height=36,
            state="disabled",
            fg_color="darkred",
            hover_color="red",
        )
        self.delete_button.grid(row=0, column=2, padx=(0, PADDING_MEDIUM))

        # View Variants button (for WP02)
        self.variants_button = ctk.CTkButton(
            button_frame,
            text="📦 View Variants",
            command=self._view_variants,
            width=150,
            height=36,
            state="disabled",
        )
        self.variants_button.grid(row=0, column=3, padx=(0, PADDING_MEDIUM))

        # Refresh button
        refresh_button = ctk.CTkButton(
            button_frame,
            text="🔄 Refresh",
            command=self.refresh,
            width=100,
            height=36,
        )
        refresh_button.grid(row=0, column=4)

    def _create_ingredient_list(self):
        """Create the scrollable list for displaying ingredients."""
        # Create scrollable frame
        self.list_frame = ctk.CTkScrollableFrame(self, label_text="Ingredient Catalog")
        self.list_frame.grid(
            row=3,
            column=0,
            sticky="nsew",
            padx=PADDING_LARGE,
            pady=PADDING_MEDIUM,
        )
        self.list_frame.grid_columnconfigure(0, weight=1)

        # Empty state label (shown when no ingredients)
        self.empty_label = ctk.CTkLabel(
            self.list_frame,
            text="No ingredients found. Click 'Add Ingredient' to get started.",
            text_color="gray",
        )

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

            # Update category dropdown with unique categories
            categories = set(ing['category'] for ing in self.ingredients if ing.get('category'))
            category_list = ["All Categories"] + sorted(categories)
            self.category_dropdown.configure(values=category_list)

            # Update display
            self._update_ingredient_display()

            # Update status
            count = len(self.ingredients)
            self.update_status(f"{count} ingredient{'s' if count != 1 else ''} loaded")

        except DatabaseError as e:
            messagebox.showerror("Database Error", f"Failed to load ingredients: {e}")
            self.update_status("Error loading ingredients")

    def _update_ingredient_display(self):
        """Update the displayed list of ingredients based on current filters."""
        # Clear existing items
        for widget in self.list_frame.winfo_children():
            if widget != self.empty_label:
                widget.destroy()

        # Apply filters
        filtered_ingredients = self._apply_filters(self.ingredients)

        # Show empty state if no ingredients
        if not filtered_ingredients:
            self.empty_label.grid(row=0, column=0, pady=50)
            self._disable_selection_buttons()
            return

        # Hide empty label
        self.empty_label.grid_forget()

        # Display ingredients
        for idx, ingredient in enumerate(filtered_ingredients):
            self._create_ingredient_row(idx, ingredient)

    def _create_ingredient_row(self, row_idx: int, ingredient: dict):
        """Create a row displaying ingredient information."""
        # Create frame for row
        row_frame = ctk.CTkFrame(self.list_frame)
        row_frame.grid(row=row_idx, column=0, sticky="ew", pady=2)
        row_frame.grid_columnconfigure(1, weight=1)

        # Selection radio button
        radio = ctk.CTkRadioButton(
            row_frame,
            text="",
            variable=ctk.StringVar(value=""),
            value=ingredient['slug'],
            command=lambda: self._on_ingredient_select(ingredient['slug']),
        )
        radio.grid(row=0, column=0, padx=(PADDING_MEDIUM, 5), pady=PADDING_MEDIUM)

        # Ingredient info
        name_text = ingredient['name']
        category_text = ingredient.get('category', 'Uncategorized')
        recipe_unit = ingredient.get('recipe_unit', 'N/A')
        density = ingredient.get('density_g_per_ml')
        density_text = f"{density:.3f} g/ml" if density else "No density"

        info_text = f"{name_text} | Category: {category_text} | Unit: {recipe_unit} | {density_text}"

        info_label = ctk.CTkLabel(
            row_frame,
            text=info_text,
            anchor="w",
        )
        info_label.grid(row=0, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

    def _apply_filters(self, ingredients: List[dict]) -> List[dict]:
        """Apply search and category filters to ingredient list."""
        filtered = ingredients

        # Apply search filter
        search_text = self.search_entry.get().lower()
        if search_text:
            filtered = [
                ing for ing in filtered
                if search_text in ing['name'].lower()
            ]

        # Apply category filter
        category = self.category_var.get()
        if category and category != "All Categories":
            filtered = [
                ing for ing in filtered
                if ing.get('category') == category
            ]

        return filtered

    def _on_search(self, event=None):
        """Handle search text change."""
        self._update_ingredient_display()

    def _on_category_change(self, category: str):
        """Handle category filter change."""
        self._update_ingredient_display()

    def _clear_filters(self):
        """Clear all filters and refresh display."""
        self.search_entry.delete(0, 'end')
        self.category_var.set("All Categories")
        self._update_ingredient_display()

    def _on_ingredient_select(self, slug: str):
        """Handle ingredient selection."""
        self.selected_ingredient_slug = slug
        self._enable_selection_buttons()

    def _enable_selection_buttons(self):
        """Enable buttons that require a selection."""
        self.edit_button.configure(state="normal")
        self.delete_button.configure(state="normal")
        self.variants_button.configure(state="normal")

    def _disable_selection_buttons(self):
        """Disable buttons that require a selection."""
        self.edit_button.configure(state="disabled")
        self.delete_button.configure(state="disabled")
        self.variants_button.configure(state="disabled")
        self.selected_ingredient_slug = None

    def _add_ingredient(self):
        """Open dialog to add a new ingredient."""
        dialog = IngredientFormDialog(self, title="Add Ingredient")
        self.wait_window(dialog)

        if dialog.result:
            try:
                # Create ingredient using service
                ingredient = ingredient_service.create_ingredient(dialog.result)
                self.refresh()
                self.update_status(f"Ingredient '{ingredient['name']}' added successfully")
                messagebox.showinfo("Success", f"Ingredient '{ingredient['name']}' created!")

            except ValidationError as e:
                messagebox.showerror("Validation Error", str(e))
            except DatabaseError as e:
                messagebox.showerror("Database Error", f"Failed to create ingredient: {e}")

    def _edit_ingredient(self):
        """Open dialog to edit the selected ingredient."""
        if not self.selected_ingredient_slug:
            return

        try:
            # Get current ingredient data
            ingredient = ingredient_service.get_ingredient(self.selected_ingredient_slug)

            dialog = IngredientFormDialog(
                self,
                ingredient=ingredient,
                title="Edit Ingredient",
            )
            self.wait_window(dialog)

            if dialog.result:
                # Update ingredient using service
                updated = ingredient_service.update_ingredient(
                    self.selected_ingredient_slug,
                    dialog.result,
                )
                self.refresh()
                self.update_status(f"Ingredient '{updated['name']}' updated successfully")
                messagebox.showinfo("Success", "Ingredient updated!")

        except NotFound:
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
            name = ingredient['name']

            # Confirm deletion
            result = messagebox.askyesno(
                "Confirm Deletion",
                f"Are you sure you want to delete '{name}'?\n\n"
                "This will fail if the ingredient has variants or is used in recipes.",
            )

            if result:
                # Delete using service
                ingredient_service.delete_ingredient(self.selected_ingredient_slug)
                self.selected_ingredient_slug = None
                self.refresh()
                self.update_status(f"Ingredient '{name}' deleted successfully")
                messagebox.showinfo("Success", "Ingredient deleted!")

        except NotFound:
            messagebox.showerror("Error", "Ingredient not found")
            self.refresh()
        except ValidationError as e:
            messagebox.showerror(
                "Cannot Delete",
                f"Cannot delete this ingredient:\n\n{e}\n\n"
                "Delete associated variants/recipes first.",
            )
        except DatabaseError as e:
            messagebox.showerror("Database Error", f"Failed to delete ingredient: {e}")

    def _view_variants(self):
        """View variants for the selected ingredient (WP02 feature)."""
        if not self.selected_ingredient_slug:
            return

        # Placeholder for WP02
        messagebox.showinfo(
            "Coming Soon",
            "Variant management will be implemented in WP02.\n\n"
            "You'll be able to add and manage brand-specific variants here.",
        )

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

        self.ingredient = ingredient
        self.result = None

        # Configure window
        self.title(title)
        self.geometry("500x500")
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

        # Name field (required)
        ctk.CTkLabel(form_frame, text="Name*:").grid(
            row=row, column=0, sticky="w", padx=10, pady=(10, 5)
        )
        self.name_entry = ctk.CTkEntry(
            form_frame, placeholder_text="e.g., All-Purpose Flour"
        )
        self.name_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=(10, 5))
        row += 1

        # Category field (required)
        ctk.CTkLabel(form_frame, text="Category*:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.category_entry = ctk.CTkEntry(
            form_frame, placeholder_text="e.g., Flour"
        )
        self.category_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        row += 1

        # Recipe Unit field (required)
        ctk.CTkLabel(form_frame, text="Recipe Unit*:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.recipe_unit_var = ctk.StringVar(value="cup")
        self.recipe_unit_dropdown = ctk.CTkOptionMenu(
            form_frame,
            values=["cup", "oz", "lb", "g", "kg", "tsp", "tbsp", "ml", "l", "count"],
            variable=self.recipe_unit_var,
        )
        self.recipe_unit_dropdown.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        row += 1

        # Density field (optional)
        ctk.CTkLabel(form_frame, text="Density (g/ml):").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.density_entry = ctk.CTkEntry(
            form_frame, placeholder_text="Optional, e.g., 0.48"
        )
        self.density_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        row += 1

        # Help text
        help_label = ctk.CTkLabel(
            form_frame,
            text="* Required fields\n\n"
            "Density is used for volume-weight conversions.\n"
            "Leave blank if not applicable.",
            text_color="gray",
            justify="left",
        )
        help_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=10)

    def _create_buttons(self):
        """Create Save and Cancel buttons."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))

        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._cancel,
            width=120,
        )
        cancel_button.grid(row=0, column=0, padx=(0, 10))

        save_button = ctk.CTkButton(
            button_frame,
            text="Save",
            command=self._save,
            width=120,
        )
        save_button.grid(row=0, column=1)

    def _populate_form(self):
        """Populate form with existing ingredient data."""
        if not self.ingredient:
            return

        self.name_entry.insert(0, self.ingredient.get('name', ''))
        self.category_entry.insert(0, self.ingredient.get('category', ''))
        self.recipe_unit_var.set(self.ingredient.get('recipe_unit', 'cup'))

        density = self.ingredient.get('density_g_per_ml')
        if density is not None:
            self.density_entry.insert(0, str(density))

    def _save(self):
        """Validate and save the form data."""
        # Get values
        name = self.name_entry.get().strip()
        category = self.category_entry.get().strip()
        recipe_unit = self.recipe_unit_var.get()
        density_str = self.density_entry.get().strip()

        # Validate required fields
        if not name:
            messagebox.showerror("Validation Error", "Name is required")
            return
        if not category:
            messagebox.showerror("Validation Error", "Category is required")
            return

        # Validate density if provided
        density = None
        if density_str:
            try:
                density = float(density_str)
                if density < 0:
                    messagebox.showerror("Validation Error", "Density must be non-negative")
                    return
            except ValueError:
                messagebox.showerror("Validation Error", "Density must be a valid number")
                return

        # Build result dict
        self.result = {
            "name": name,
            "category": category,
            "recipe_unit": recipe_unit,
        }

        if density is not None:
            self.result["density_g_per_ml"] = density

        self.destroy()

    def _cancel(self):
        """Cancel the form."""
        self.result = None
        self.destroy()
