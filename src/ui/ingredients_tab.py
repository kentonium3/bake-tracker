"""
My Ingredients tab for the Seasonal Baking Tracker.

Provides CRUD interface for managing generic ingredient catalog
(brand-agnostic ingredient definitions) using the v0.4.0 refactored architecture.
"""

import customtkinter as ctk
from typing import Optional, List, Dict, Any
from tkinter import messagebox

from src.services import ingredient_service, variant_service
from src.services.exceptions import (
    IngredientInUse,
    IngredientNotFoundBySlug,
    SlugAlreadyExists,
    ValidationError,
    DatabaseError,
    VariantInUse,
    VariantNotFound,
)
from src.utils.constants import PADDING_MEDIUM, PADDING_LARGE, VOLUME_UNITS, WEIGHT_UNITS


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
        self.selection_var = ctk.StringVar(value="")

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
        # Create scrollable frame with explicit minimum width
        self.list_frame = ctk.CTkScrollableFrame(
            self,
            label_text="Ingredient Catalog",
            width=700,  # Minimum width to prevent truncation
        )
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
            categories = set(ing["category"] for ing in self.ingredients if ing.get("category"))
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
            self.selection_var.set("")
            return

        # Hide empty label
        self.empty_label.grid_forget()

        # Restore selection if still present
        if self.selected_ingredient_slug and any(
            ing["slug"] == self.selected_ingredient_slug for ing in filtered_ingredients
        ):
            self.selection_var.set(self.selected_ingredient_slug)
        else:
            self.selection_var.set("")
            self._disable_selection_buttons()

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
            variable=self.selection_var,
            value=ingredient["slug"],
            command=lambda slug=ingredient["slug"]: self._on_ingredient_select(slug),
        )
        radio.grid(row=0, column=0, padx=(PADDING_MEDIUM, 5), pady=PADDING_MEDIUM)

        # Ingredient info
        name_text = ingredient["name"]
        category_text = ingredient.get("category", "Uncategorized")
        density = ingredient.get("density_g_per_ml")
        density_text = f"{density:.3f} g/ml" if density else "No density"

        info_text = f"{name_text} | Category: {category_text} | {density_text}"

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
            filtered = [ing for ing in filtered if search_text in ing["name"].lower()]

        # Apply category filter
        category = self.category_var.get()
        if category and category != "All Categories":
            filtered = [ing for ing in filtered if ing.get("category") == category]

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

    def select_ingredient(self, ingredient_slug: str, variant_id: Optional[int] = None) -> None:
        """
        Programmatically select an ingredient (and optional variant) from the list.

        Args:
            ingredient_slug: Slug of the ingredient to select.
            variant_id: Optional variant ID to highlight within the variants dialog.
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
        self.selection_var.set(ingredient_slug)
        self._enable_selection_buttons()
        self.update_status(f"Ingredient '{ingredient_slug}' selected")

        if variant_id is not None:
            self._view_variants(selected_variant_id=variant_id)

    def _on_ingredient_select(self, slug: str):
        """Handle ingredient selection."""
        self.selected_ingredient_slug = slug
        self.selection_var.set(slug)
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
        self.selection_var.set("")

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
                if self.selected_ingredient_slug:
                    self.selection_var.set(self.selected_ingredient_slug)
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
                    "name": ingredient_obj.name,
                    "category": ingredient_obj.category,
                    "density_volume_value": ingredient_obj.density_volume_value,
                    "density_volume_unit": ingredient_obj.density_volume_unit,
                    "density_weight_value": ingredient_obj.density_weight_value,
                    "density_weight_unit": ingredient_obj.density_weight_unit,
                }
            )

            dialog = IngredientFormDialog(
                self,
                ingredient=ingredient_data,
                title="Edit Ingredient",
            )
            self.wait_window(dialog)

            if dialog.result:
                # Update ingredient using service
                updated_obj = ingredient_service.update_ingredient(
                    self.selected_ingredient_slug,
                    dialog.result,
                )
                self.refresh()
                if updated_obj:
                    updated_name = getattr(
                        updated_obj, "name", dialog.result.get("name", "Ingredient")
                    )
                    self.selected_ingredient_slug = getattr(
                        updated_obj, "slug", self.selected_ingredient_slug
                    )
                    if self.selected_ingredient_slug:
                        self.selection_var.set(self.selected_ingredient_slug)
                    self.update_status(f"Ingredient '{updated_name}' updated successfully")
                else:
                    self.update_status("Ingredient updated successfully")
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
            name = ingredient.name  # Fixed: access attribute not dict key

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

        except IngredientNotFoundBySlug:
            messagebox.showerror("Error", "Ingredient not found")
            self.refresh()
        except IngredientInUse as e:
            messagebox.showerror(
                "Cannot Delete",
                f"Cannot delete this ingredient:\n\n{e}\n\n"
                "Delete associated variants/recipes first.",
            )
        except DatabaseError as e:
            messagebox.showerror("Database Error", f"Failed to delete ingredient: {e}")
        except Exception as e:
            # Catch-all for unexpected errors
            messagebox.showerror("Error", f"Unexpected error deleting ingredient: {e}")
            import traceback

            traceback.print_exc()

    def _view_variants(self, selected_variant_id: Optional[int] = None):
        """View variants for the selected ingredient."""
        if not self.selected_ingredient_slug:
            messagebox.showinfo(
                "No Selection", "Please select an ingredient first to view its variants."
            )
            return

        try:
            # Get ingredient details
            ingredient_obj = ingredient_service.get_ingredient(self.selected_ingredient_slug)

            # Convert to dict for dialog compatibility
            ingredient = {
                "id": ingredient_obj.id,
                "slug": ingredient_obj.slug,
                "name": ingredient_obj.name,
                "category": ingredient_obj.category,
                "density_g_per_ml": ingredient_obj.density_g_per_ml,
            }

            # Open variants dialog
            dialog = VariantsDialog(self, ingredient, initial_variant_id=selected_variant_id)
            self.wait_window(dialog)

            # Refresh in case variants changed
            self.refresh()

        except IngredientNotFoundBySlug:
            messagebox.showerror("Error", "Ingredient not found")
            self.refresh()
        except DatabaseError as e:
            messagebox.showerror("Database Error", f"Failed to load variants: {e}")

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

        if ingredient is not None and hasattr(ingredient, "to_dict"):
            ingredient = ingredient.to_dict()
        self.ingredient = ingredient
        self.result: Optional[Dict[str, Any]] = None

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
        self.name_entry = ctk.CTkEntry(form_frame, placeholder_text="e.g., All-Purpose Flour")
        self.name_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=(10, 5))
        row += 1

        # Category field (required)
        ctk.CTkLabel(form_frame, text="Category*:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.category_entry = ctk.CTkEntry(form_frame, placeholder_text="e.g., Flour")
        self.category_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
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

        self.name_entry.insert(0, self.ingredient.get("name", ""))
        self.category_entry.insert(0, self.ingredient.get("category", ""))

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
        # Get values
        name = self.name_entry.get().strip()
        category = self.category_entry.get().strip()

        # Validate required fields
        if not name:
            messagebox.showerror("Validation Error", "Name is required")
            return
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


class VariantsDialog(ctk.CTkToplevel):
    """
    Dialog for managing variants of an ingredient.

    Displays list of variants with add/edit/delete/preferred toggle operations.
    """

    def __init__(self, parent, ingredient: dict, initial_variant_id: Optional[int] = None):
        """
        Initialize the variants dialog.

        Args:
            parent: Parent window
            ingredient: Ingredient dict with id, slug, name
        """
        super().__init__(parent)

        self.ingredient = ingredient
        self.variants: List[dict] = []
        self.selected_variant_id: Optional[int] = None
        self.variant_selection_var = ctk.StringVar(value="")
        self.initial_variant_id = initial_variant_id

        # Configure window
        self.title(f"Variants - {ingredient['name']}")
        self.geometry("900x600")
        self.resizable(True, True)

        # Center on parent
        self.transient(parent)
        self.grab_set()

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Title
        self.grid_rowconfigure(1, weight=0)  # Buttons
        self.grid_rowconfigure(2, weight=1)  # Variant list
        self.grid_rowconfigure(3, weight=0)  # Close button

        # Create UI
        self._create_title()
        self._create_action_buttons()
        self._create_variant_list()
        self._create_close_button()

        # Load variants
        self.refresh()

    def _create_title(self):
        """Create title label."""
        title_text = f"Brand & Package Variants for: {self.ingredient['name']}"
        title_label = ctk.CTkLabel(
            self,
            text=title_text,
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title_label.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 10))

    def _create_action_buttons(self):
        """Create action buttons."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)

        # Add Variant button
        add_button = ctk.CTkButton(
            button_frame,
            text="➕ Add Variant",
            command=self._add_variant,
            width=140,
        )
        add_button.grid(row=0, column=0, padx=(0, 10))

        # Edit button
        self.edit_button = ctk.CTkButton(
            button_frame,
            text="✏️ Edit",
            command=self._edit_variant,
            width=100,
            state="disabled",
        )
        self.edit_button.grid(row=0, column=1, padx=(0, 10))

        # Delete button
        self.delete_button = ctk.CTkButton(
            button_frame,
            text="🗑️ Delete",
            command=self._delete_variant,
            width=100,
            state="disabled",
            fg_color="darkred",
            hover_color="red",
        )
        self.delete_button.grid(row=0, column=2, padx=(0, 10))

        # Refresh button
        refresh_button = ctk.CTkButton(
            button_frame,
            text="🔄 Refresh",
            command=self.refresh,
            width=100,
        )
        refresh_button.grid(row=0, column=3)

    def _create_variant_list(self):
        """Create scrollable variant list."""
        # Create scrollable frame
        self.list_frame = ctk.CTkScrollableFrame(
            self,
            label_text="Variants (Brand & Package)",
        )
        self.list_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        self.list_frame.grid_columnconfigure(0, weight=1)

        # Empty state label
        self.empty_label = ctk.CTkLabel(
            self.list_frame,
            text="No variants. Click 'Add Variant' to create one.",
            text_color="gray",
        )

    def _create_close_button(self):
        """Create close button."""
        close_button = ctk.CTkButton(
            self,
            text="Close",
            command=self.destroy,
            width=120,
        )
        close_button.grid(row=3, column=0, pady=(0, 20))

    def refresh(self):
        """Refresh variant list from database."""
        try:
            # Get variants for this ingredient (returns Variant objects)
            variant_objects = variant_service.get_variants_for_ingredient(self.ingredient["slug"])

            # Convert to dicts for UI compatibility
            self.variants = []
            for variant_obj in variant_objects:
                variant_dict = (
                    variant_obj.to_dict()
                    if hasattr(variant_obj, "to_dict")
                    else {
                        "id": variant_obj.id,
                        "brand": variant_obj.brand,
                        "purchase_unit": variant_obj.purchase_unit,
                        "purchase_quantity": variant_obj.purchase_quantity,
                        "package_size": getattr(variant_obj, "package_size", None),
                        "upc_code": getattr(variant_obj, "upc_code", None),
                        "gtin": getattr(variant_obj, "gtin", None),
                        "supplier": getattr(variant_obj, "supplier", None),
                    }
                )
                # Ensure expected keys exist
                variant_dict["brand"] = variant_obj.brand
                variant_dict["purchase_unit"] = variant_obj.purchase_unit
                variant_dict["purchase_quantity"] = variant_obj.purchase_quantity
                variant_dict["package_size"] = getattr(variant_obj, "package_size", None)
                variant_dict["upc_code"] = getattr(variant_obj, "upc_code", None)
                variant_dict["gtin"] = getattr(variant_obj, "gtin", None)
                variant_dict["supplier"] = getattr(variant_obj, "supplier", None)
                variant_dict["preferred"] = getattr(variant_obj, "preferred", False)
                variant_dict["id"] = variant_obj.id
                self.variants.append(variant_dict)

            # Update display
            self._update_variant_display()
            if self.initial_variant_id is not None:
                self.select_variant(self.initial_variant_id)
                self.initial_variant_id = None

        except DatabaseError as e:
            messagebox.showerror("Database Error", f"Failed to load variants: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh variants: {e}")
            import traceback

            traceback.print_exc()

    def _update_variant_display(self):
        """Update displayed variant list."""
        # Clear existing
        for widget in self.list_frame.winfo_children():
            if widget != self.empty_label:
                widget.destroy()

        # Show empty state if no variants
        if not self.variants:
            self.empty_label.grid(row=0, column=0, pady=50)
            self._disable_selection_buttons()
            self.variant_selection_var.set("")
            return

        # Hide empty label
        self.empty_label.grid_forget()

        # Restore selection if still present
        if self.selected_variant_id and any(
            variant["id"] == self.selected_variant_id for variant in self.variants
        ):
            self.variant_selection_var.set(str(self.selected_variant_id))
        else:
            self.selected_variant_id = None
            self.variant_selection_var.set("")
            self._disable_selection_buttons()

        # Display variants
        for idx, variant in enumerate(self.variants):
            self._create_variant_row(idx, variant)

    def select_variant(self, variant_id: int) -> None:
        """Programmatically select a variant within the dialog."""
        if not any(variant["id"] == variant_id for variant in self.variants):
            return

        self.selected_variant_id = variant_id
        self.variant_selection_var.set(str(variant_id))
        self._enable_selection_buttons()

    def _create_variant_row(self, row_idx: int, variant: dict):
        """Create a row displaying variant information."""
        row_frame = ctk.CTkFrame(self.list_frame)
        row_frame.grid(row=row_idx, column=0, sticky="ew", pady=2)
        row_frame.grid_columnconfigure(1, weight=1)

        # Selection radio
        radio = ctk.CTkRadioButton(
            row_frame,
            text="",
            variable=self.variant_selection_var,
            value=str(variant["id"]),
            command=lambda variant_id=variant["id"]: self._on_variant_select(variant_id),
        )
        radio.grid(row=0, column=0, padx=(10, 5), pady=10)

        # Preferred indicator
        preferred_text = "⭐" if variant.get("preferred") else ""
        if preferred_text:
            preferred_label = ctk.CTkLabel(
                row_frame,
                text=preferred_text,
                font=ctk.CTkFont(size=16),
            )
            preferred_label.grid(row=0, column=1, padx=(0, 5))

        # Variant info - use cleaner display format
        brand = variant.get("brand", "Generic")
        purchase_qty = variant.get("purchase_quantity") or 0
        purchase_unit = variant.get("purchase_unit", "")
        package_size = variant.get("package_size") or f"{purchase_qty} {purchase_unit}".strip()
        supplier = variant.get("supplier", "")

        # Build primary display name
        display_name = f"{brand}"
        if package_size and package_size != f"{purchase_qty} {purchase_unit}":
            display_name += f" - {package_size}"
        elif purchase_qty and purchase_unit:
            display_name += f" ({purchase_qty} {purchase_unit})"

        # Add supplier if available
        if supplier:
            display_name += f" [from {supplier}]"

        info_text = display_name

        info_label = ctk.CTkLabel(
            row_frame,
            text=info_text,
            anchor="w",
        )
        info_label.grid(
            row=0,
            column=2 if preferred_text else 1,
            sticky="ew",
            padx=10,
            pady=10,
        )

        # Mark as Preferred button
        if not variant.get("preferred"):
            mark_preferred_btn = ctk.CTkButton(
                row_frame,
                text="Mark Preferred",
                command=lambda vid=variant["id"]: self._toggle_preferred(vid),
                width=120,
                height=28,
            )
            mark_preferred_btn.grid(row=0, column=3, padx=5)

    def _on_variant_select(self, variant_id: int):
        """Handle variant selection."""
        self.selected_variant_id = variant_id
        self.variant_selection_var.set(str(variant_id))
        self._enable_selection_buttons()

    def _enable_selection_buttons(self):
        """Enable buttons that require selection."""
        self.edit_button.configure(state="normal")
        self.delete_button.configure(state="normal")

    def _disable_selection_buttons(self):
        """Disable buttons that require selection."""
        self.edit_button.configure(state="disabled")
        self.delete_button.configure(state="disabled")
        self.selected_variant_id = None
        self.variant_selection_var.set("")

    def _add_variant(self):
        """Add new variant."""
        dialog = VariantFormDialog(
            self,
            ingredient=self.ingredient,
            title="Add Variant",
        )
        self.wait_window(dialog)

        if dialog.result:
            try:
                # Create variant
                variant = variant_service.create_variant(
                    self.ingredient["slug"],  # Fixed: use slug not id
                    dialog.result,
                )
                variant_id_attr = getattr(variant, "id", None)
                if variant_id_attr is not None:
                    variant_id = int(variant_id_attr)
                    self.selected_variant_id = variant_id
                    self.variant_selection_var.set(str(variant_id))
                self.refresh()
                messagebox.showinfo(
                    "Success",
                    f"Variant '{variant.brand}' created!",
                )

            except ValidationError as e:
                messagebox.showerror("Validation Error", str(e))
            except DatabaseError as e:
                messagebox.showerror("Database Error", f"Failed to create variant: {e}")

    def _edit_variant(self):
        """Edit selected variant."""
        if not self.selected_variant_id:
            return

        try:
            # Get variant
            variant_obj = variant_service.get_variant(self.selected_variant_id)
            variant_data = (
                variant_obj.to_dict()
                if hasattr(variant_obj, "to_dict")
                else {
                    "id": variant_obj.id,
                    "brand": variant_obj.brand,
                    "purchase_quantity": variant_obj.purchase_quantity,
                    "purchase_unit": variant_obj.purchase_unit,
                    "package_size": getattr(variant_obj, "package_size", None),
                    "upc_code": getattr(variant_obj, "upc_code", None),
                    "gtin": getattr(variant_obj, "gtin", None),
                    "supplier": getattr(variant_obj, "supplier", None),
                }
            )

            dialog = VariantFormDialog(
                self,
                ingredient=self.ingredient,
                variant=variant_data,
                title="Edit Variant",
            )
            self.wait_window(dialog)

            if dialog.result:
                # Update variant
                variant_service.update_variant(
                    self.selected_variant_id,
                    dialog.result,
                )
                self.refresh()
                messagebox.showinfo("Success", "Variant updated!")

        except VariantNotFound:
            messagebox.showerror("Error", "Variant not found")
            self.refresh()
        except ValidationError as e:
            messagebox.showerror("Validation Error", str(e))
        except DatabaseError as e:
            messagebox.showerror("Database Error", f"Failed to update variant: {e}")

    def _delete_variant(self):
        """Delete selected variant."""
        if not self.selected_variant_id:
            return

        try:
            # Get variant for confirmation
            variant_obj = variant_service.get_variant(self.selected_variant_id)
            brand = getattr(variant_obj, "brand", "Variant")

            # Confirm
            result = messagebox.askyesno(
                "Confirm Deletion",
                f"Delete variant '{brand}'?\n\n" "This will fail if the variant has pantry items.",
            )

            if result:
                variant_service.delete_variant(self.selected_variant_id)
                self.selected_variant_id = None
                self.refresh()
                messagebox.showinfo("Success", "Variant deleted!")

        except VariantNotFound:
            messagebox.showerror("Error", "Variant not found")
            self.refresh()
        except VariantInUse as e:
            messagebox.showerror(
                "Cannot Delete",
                f"Cannot delete variant:\n\n{e}\n\nRemove pantry items first.",
            )
        except DatabaseError as e:
            messagebox.showerror("Database Error", f"Failed to delete variant: {e}")

    def _toggle_preferred(self, variant_id: int):
        """Toggle preferred status for variant."""
        try:
            variant_service.set_preferred_variant(variant_id)
            self.selected_variant_id = variant_id
            self.refresh()

        except VariantNotFound:
            messagebox.showerror("Error", "Variant not found")
            self.refresh()
        except DatabaseError as e:
            messagebox.showerror("Database Error", f"Failed to update preferred: {e}")


class VariantFormDialog(ctk.CTkToplevel):
    """
    Dialog for creating or editing a variant.

    Form for brand/package specific information.
    """

    def __init__(
        self,
        parent,
        ingredient: dict,
        variant: Optional[dict] = None,
        title: str = "Add Variant",
    ):
        """
        Initialize variant form dialog.

        Args:
            parent: Parent window
            ingredient: Ingredient dict
            variant: Existing variant dict (None for new)
            title: Dialog title
        """
        super().__init__(parent)

        self.ingredient = ingredient
        if variant is not None and hasattr(variant, "to_dict"):
            variant = variant.to_dict()
        self.variant = variant or {}
        self.result: Optional[Dict[str, Any]] = None

        # Configure window
        self.title(title)
        self.geometry("550x550")
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
        if self.variant:
            self._populate_form()

    def _create_form(self):
        """Create form fields."""
        form_frame = ctk.CTkFrame(self)
        form_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        form_frame.grid_columnconfigure(1, weight=1)

        row = 0

        # Ingredient name (read-only)
        ctk.CTkLabel(form_frame, text="Ingredient:").grid(
            row=row, column=0, sticky="w", padx=10, pady=(10, 5)
        )
        ingredient_label = ctk.CTkLabel(
            form_frame,
            text=self.ingredient["name"],
            font=ctk.CTkFont(weight="bold"),
        )
        ingredient_label.grid(row=row, column=1, sticky="w", padx=10, pady=(10, 5))
        row += 1

        # Brand (required)
        ctk.CTkLabel(form_frame, text="Brand*:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.brand_entry = ctk.CTkEntry(form_frame, placeholder_text="e.g., King Arthur")
        self.brand_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        row += 1

        # Purchase Quantity (required)
        ctk.CTkLabel(form_frame, text="Purchase Quantity*:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.purchase_qty_entry = ctk.CTkEntry(form_frame, placeholder_text="e.g., 25")
        self.purchase_qty_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        row += 1

        # Purchase Unit (required)
        ctk.CTkLabel(form_frame, text="Purchase Unit*:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.purchase_unit_var = ctk.StringVar(value="lb")
        self.purchase_unit_dropdown = ctk.CTkOptionMenu(
            form_frame,
            values=["lb", "oz", "g", "kg", "bag", "box", "count"],
            variable=self.purchase_unit_var,
        )
        self.purchase_unit_dropdown.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        row += 1

        # UPC/GTIN (optional)
        ctk.CTkLabel(form_frame, text="UPC/GTIN:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.upc_entry = ctk.CTkEntry(form_frame, placeholder_text="Optional barcode")
        self.upc_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        row += 1

        # Supplier (optional)
        ctk.CTkLabel(form_frame, text="Supplier:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.supplier_entry = ctk.CTkEntry(form_frame, placeholder_text="Optional supplier name")
        self.supplier_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        row += 1

        # Preferred (checkbox)
        ctk.CTkLabel(form_frame, text="Mark as Preferred:").grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        self.preferred_var = ctk.BooleanVar(value=False)
        self.preferred_checkbox = ctk.CTkCheckBox(
            form_frame,
            text="Set as preferred variant for this ingredient",
            variable=self.preferred_var,
        )
        self.preferred_checkbox.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        row += 1

        # Help text
        help_label = ctk.CTkLabel(
            form_frame,
            text="* Required fields\n\n"
            "Package size is calculated from quantity + unit.\n"
            "Example: 25 lb → '25 lb bag'\n"
            "Preferred variants are used by default in shopping lists.",
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
        """Populate form with existing variant data."""
        if not self.variant:
            return

        self.brand_entry.insert(0, self.variant.get("brand", ""))
        purchase_qty = self.variant.get("purchase_quantity", "")
        self.purchase_qty_entry.insert(0, str(purchase_qty) if purchase_qty is not None else "")
        self.purchase_unit_var.set(self.variant.get("purchase_unit", "lb"))
        upc_value = (
            self.variant.get("upc_code")
            or self.variant.get("gtin")
            or self.variant.get("upc")
            or ""
        )
        self.upc_entry.insert(0, upc_value)
        self.supplier_entry.insert(0, self.variant.get("supplier", ""))
        self.preferred_var.set(self.variant.get("preferred", False))

    def _save(self):
        """Validate and save form data."""
        # Get values
        brand = self.brand_entry.get().strip()
        purchase_qty_str = self.purchase_qty_entry.get().strip()
        purchase_unit = self.purchase_unit_var.get()
        upc = self.upc_entry.get().strip()
        supplier = self.supplier_entry.get().strip()
        preferred = self.preferred_var.get()

        # Validate required
        if not brand:
            messagebox.showerror("Validation Error", "Brand is required")
            return

        if not purchase_qty_str:
            messagebox.showerror("Validation Error", "Purchase quantity is required")
            return

        # Validate quantity
        try:
            purchase_qty = float(purchase_qty_str)
            if purchase_qty <= 0:
                messagebox.showerror("Validation Error", "Quantity must be positive")
                return
        except ValueError:
            messagebox.showerror("Validation Error", "Quantity must be a valid number")
            return

        # Build result
        result: Dict[str, Any] = {
            "brand": brand,
            "purchase_quantity": purchase_qty,
            "purchase_unit": purchase_unit,
            "preferred": preferred,
        }

        package_size = f"{purchase_qty:g} {purchase_unit}".strip()
        if package_size:
            result["package_size"] = package_size

        if upc:
            result["upc"] = upc
            result["upc_code"] = upc
            if len(upc) == 14:
                result["gtin"] = upc
        if supplier:
            result["supplier"] = supplier

        self.result = result

        self.destroy()

    def _cancel(self):
        """Cancel form."""
        self.result = None
        self.destroy()
