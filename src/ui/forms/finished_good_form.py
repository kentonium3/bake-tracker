"""
Finished Good form dialog for adding and editing finished goods.

⚠️  DEPRECATED: This form is deprecated as of v0.4.0.
For individual consumable items, use FinishedUnitFormDialog instead.
This form will be updated to handle package assemblies only.

Provides a form for creating and updating finished good records
with smart field visibility based on yield mode.
"""

import customtkinter as ctk
from typing import Optional, Dict, Any

from src.utils.deprecation_warnings import warn_deprecated_ui_component

from src.models.finished_unit import FinishedUnit, YieldMode
from src.services import recipe_service
from src.utils.constants import (
    MAX_NAME_LENGTH,
    MAX_NOTES_LENGTH,
    PADDING_MEDIUM,
    PADDING_LARGE,
)
from src.ui.widgets.dialogs import show_error


class FinishedUnitFormDialog(ctk.CTkToplevel):
    """
    Dialog for creating or editing a finished unit (individual consumable item).

    Provides a form with smart field visibility based on yield mode.
    """

    def __init__(
        self,
        parent,
        finished_unit: Optional[FinishedUnit] = None,
        title: str = "Add Finished Unit",
    ):
        """
        Initialize the finished unit form dialog.

        Args:
            parent: Parent window
            finished_unit: Existing finished unit to edit (None for new)
            title: Dialog title
        """
        # Warn about deprecation
        warn_deprecated_ui_component(
            component_name="FinishedGoodFormDialog",
            replacement="FinishedUnitFormDialog (for individual items) or enhanced form (for assemblies)",
            removal_version="v0.5.0",
        )

        super().__init__(parent)

        self.finished_unit = finished_unit
        self.result = None
        self._initializing = True  # Flag to prevent auto-populate during init

        # Load available recipes
        try:
            self.available_recipes = recipe_service.get_all_recipes()
        except Exception:
            self.available_recipes = []

        # Configure window
        self.title(title)
        self.geometry("600x700")
        self.resizable(False, False)

        # Center on parent
        self.transient(parent)

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
        if self.finished_good:
            self._populate_form()
        else:
            # Set default yield mode
            self._on_yield_mode_change("discrete_count")

        # Mark initialization as complete
        self._initializing = False

        # Center dialog on parent and make visible
        self.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()
        x = max(0, parent_x + (parent_width - dialog_width) // 2)
        y = max(0, parent_y + (parent_height - dialog_height) // 2)
        self.geometry(f"+{x}+{y}")
        self.wait_visibility()
        self.grab_set()
        self.focus_force()

    def _create_form_fields(self, parent):
        """Create all form input fields."""
        row = 0

        # Name field (required)
        name_label = ctk.CTkLabel(parent, text="Name*:", anchor="w")
        name_label.grid(
            row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=(PADDING_MEDIUM, 5)
        )

        self.name_entry = ctk.CTkEntry(
            parent, width=400, placeholder_text="e.g., Sugar Cookie, 9-inch Chocolate Cake"
        )
        self.name_entry.grid(
            row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=(PADDING_MEDIUM, 5)
        )
        row += 1

        # Recipe dropdown (required)
        recipe_label = ctk.CTkLabel(parent, text="Recipe*:", anchor="w")
        recipe_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        recipe_names = [r.name for r in self.available_recipes]
        self.recipe_combo = ctk.CTkComboBox(
            parent,
            width=400,
            values=recipe_names if recipe_names else ["No recipes available"],
            state="readonly" if recipe_names else "disabled",
            command=self._on_recipe_change,
        )
        if recipe_names:
            self.recipe_combo.set(recipe_names[0])
        self.recipe_combo.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Category field (optional)
        category_label = ctk.CTkLabel(parent, text="Category:", anchor="w")
        category_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        categories = ["Cakes", "Cookies", "Candies", "Brownies", "Bars", "Breads", "Other"]
        self.category_combo = ctk.CTkComboBox(
            parent,
            width=400,
            values=[""] + categories,
            state="readonly",
        )
        self.category_combo.set("")
        self.category_combo.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Yield Mode section
        yield_mode_label = ctk.CTkLabel(
            parent,
            text="Yield Type",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        yield_mode_label.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=PADDING_MEDIUM,
            pady=(PADDING_LARGE, PADDING_MEDIUM),
        )
        row += 1

        # Yield mode radio buttons
        yield_mode_frame = ctk.CTkFrame(parent, fg_color="transparent")
        yield_mode_frame.grid(
            row=row, column=0, columnspan=2, sticky="ew", padx=PADDING_MEDIUM, pady=5
        )

        self.yield_mode_var = ctk.StringVar(value="discrete_count")

        discrete_radio = ctk.CTkRadioButton(
            yield_mode_frame,
            text="Discrete Items (cookies, truffles) - recipe yields fixed count",
            variable=self.yield_mode_var,
            value="discrete_count",
            command=lambda: self._on_yield_mode_change("discrete_count"),
        )
        discrete_radio.grid(row=0, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        batch_radio = ctk.CTkRadioButton(
            yield_mode_frame,
            text="Batch Portion (cakes) - finished good uses % of batch",
            variable=self.yield_mode_var,
            value="batch_portion",
            command=lambda: self._on_yield_mode_change("batch_portion"),
        )
        batch_radio.grid(row=1, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Container for mode-specific fields
        self.mode_fields_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.mode_fields_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=0, pady=5)
        self.mode_fields_frame.grid_columnconfigure(1, weight=1)
        row += 1

        # Create both sets of fields (will show/hide based on mode)
        self._create_discrete_fields()
        self._create_batch_fields()

        # Notes field (optional)
        notes_label = ctk.CTkLabel(parent, text="Notes:", anchor="w")
        notes_label.grid(row=row, column=0, sticky="nw", padx=PADDING_MEDIUM, pady=5)

        self.notes_text = ctk.CTkTextbox(parent, width=400, height=80)
        self.notes_text.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Required field note
        required_note = ctk.CTkLabel(
            parent,
            text="* Required fields",
            font=ctk.CTkFont(size=11),
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

    def _create_discrete_fields(self):
        """Create fields for discrete count mode."""
        self.discrete_frame = ctk.CTkFrame(self.mode_fields_frame, fg_color="transparent")
        self.discrete_frame.grid_columnconfigure(1, weight=1)

        row = 0

        # Items per batch
        items_label = ctk.CTkLabel(self.discrete_frame, text="Items per Batch*:", anchor="w")
        items_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        self.items_per_batch_entry = ctk.CTkEntry(
            self.discrete_frame, width=400, placeholder_text="e.g., 24 (recipe yields 24 cookies)"
        )
        self.items_per_batch_entry.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)
        row += 1

        # Item unit
        unit_label = ctk.CTkLabel(self.discrete_frame, text="Item Unit*:", anchor="w")
        unit_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        self.item_unit_entry = ctk.CTkEntry(
            self.discrete_frame, width=400, placeholder_text="e.g., cookie, truffle, piece"
        )
        self.item_unit_entry.grid(row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5)

    def _create_batch_fields(self):
        """Create fields for batch portion mode."""
        self.batch_frame = ctk.CTkFrame(self.mode_fields_frame, fg_color="transparent")
        self.batch_frame.grid_columnconfigure(1, weight=1)

        row = 0

        # Batch percentage
        pct_label = ctk.CTkLabel(self.batch_frame, text="Batch Percentage*:", anchor="w")
        pct_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        self.batch_percentage_entry = ctk.CTkEntry(
            self.batch_frame,
            width=400,
            placeholder_text="e.g., 100 (large cake uses 100% of batch), 25 (small cake uses 25%)",
        )
        self.batch_percentage_entry.grid(
            row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5
        )
        row += 1

        # Portion description
        desc_label = ctk.CTkLabel(self.batch_frame, text="Portion Description:", anchor="w")
        desc_label.grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=5)

        self.portion_description_entry = ctk.CTkEntry(
            self.batch_frame, width=400, placeholder_text="e.g., 9-inch round pan, 8x8 square"
        )
        self.portion_description_entry.grid(
            row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=5
        )

    def _on_yield_mode_change(self, mode: str):
        """Handle yield mode change - show/hide appropriate fields."""
        if mode == "discrete_count":
            self.discrete_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
            self.batch_frame.grid_forget()
            # Auto-populate items_per_batch when switching to discrete mode
            self._on_recipe_change(self.recipe_combo.get())
        else:
            self.batch_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
            self.discrete_frame.grid_forget()

    def _on_recipe_change(self, recipe_name: str):
        """
        Handle recipe selection change.

        Auto-populates items_per_batch field with recipe's yield_quantity
        when in discrete count mode.

        Args:
            recipe_name: Name of the selected recipe
        """
        # Skip auto-populate during form initialization
        if self._initializing:
            return

        # Only auto-populate if in discrete mode
        if self.yield_mode_var.get() == "discrete_count":
            # Find the selected recipe
            selected_recipe = None
            for recipe in self.available_recipes:
                if recipe.name == recipe_name:
                    selected_recipe = recipe
                    break

            # Auto-populate items_per_batch with recipe yield
            if selected_recipe:
                # Convert yield_quantity to int if it's a whole number, otherwise keep as float
                yield_qty = selected_recipe.yield_quantity
                if yield_qty == int(yield_qty):
                    display_value = str(int(yield_qty))
                else:
                    display_value = str(yield_qty)

                # Clear and update the field
                self.items_per_batch_entry.delete(0, "end")
                self.items_per_batch_entry.insert(0, display_value)

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
        """Populate form fields with existing finished good data."""
        if not self.finished_good:
            return

        self.name_entry.insert(0, self.finished_good.display_name)

        # Select recipe
        for idx, recipe in enumerate(self.available_recipes):
            if recipe.id == self.finished_good.recipe_id:
                self.recipe_combo.set(recipe.name)
                break

        if self.finished_good.category:
            self.category_combo.set(self.finished_good.category)

        # Set yield mode
        yield_mode = self.finished_good.yield_mode.value
        self.yield_mode_var.set(yield_mode)
        self._on_yield_mode_change(yield_mode)

        # Populate mode-specific fields
        if yield_mode == "discrete_count":
            if self.finished_good.items_per_batch:
                self.items_per_batch_entry.insert(0, str(self.finished_good.items_per_batch))
            if self.finished_good.item_unit:
                self.item_unit_entry.insert(0, self.finished_good.item_unit)
        else:
            if self.finished_good.batch_percentage:
                self.batch_percentage_entry.insert(0, str(self.finished_good.batch_percentage))
            if self.finished_good.portion_description:
                self.portion_description_entry.insert(0, self.finished_good.portion_description)

        if self.finished_good.notes:
            self.notes_text.insert("1.0", self.finished_good.notes)

    def _validate_form(self) -> Optional[Dict[str, Any]]:
        """
        Validate form inputs and return data dictionary.

        Returns:
            Dictionary of form data if valid, None otherwise
        """
        # Get values
        name = self.name_entry.get().strip()
        recipe_name = self.recipe_combo.get()
        category = self.category_combo.get().strip() or None
        yield_mode = self.yield_mode_var.get()
        notes = self.notes_text.get("1.0", "end-1c").strip() or None

        # Validate required fields
        if not name:
            show_error("Validation Error", "Name is required", parent=self)
            return None

        if len(name) > MAX_NAME_LENGTH:
            show_error(
                "Validation Error",
                f"Name must be {MAX_NAME_LENGTH} characters or less",
                parent=self,
            )
            return None

        # Find recipe ID
        recipe_id = None
        for recipe in self.available_recipes:
            if recipe.name == recipe_name:
                recipe_id = recipe.id
                break

        if not recipe_id:
            show_error("Validation Error", "Please select a valid recipe", parent=self)
            return None

        if notes and len(notes) > MAX_NOTES_LENGTH:
            show_error(
                "Validation Error",
                f"Notes must be {MAX_NOTES_LENGTH} characters or less",
                parent=self,
            )
            return None

        # Validate mode-specific fields
        items_per_batch = None
        item_unit = None
        batch_percentage = None
        portion_description = None

        if yield_mode == "discrete_count":
            items_str = self.items_per_batch_entry.get().strip()
            item_unit = self.item_unit_entry.get().strip()

            if not items_str:
                show_error("Validation Error", "Items per batch is required", parent=self)
                return None

            if not item_unit:
                show_error("Validation Error", "Item unit is required", parent=self)
                return None

            try:
                items_per_batch = int(items_str)
                if items_per_batch <= 0:
                    show_error(
                        "Validation Error", "Items per batch must be greater than zero", parent=self
                    )
                    return None
            except ValueError:
                show_error(
                    "Validation Error", "Items per batch must be a valid number", parent=self
                )
                return None

        else:  # batch_portion
            pct_str = self.batch_percentage_entry.get().strip()
            portion_description = self.portion_description_entry.get().strip() or None

            if not pct_str:
                show_error("Validation Error", "Batch percentage is required", parent=self)
                return None

            try:
                batch_percentage = float(pct_str)
                if batch_percentage <= 0:
                    show_error(
                        "Validation Error",
                        "Batch percentage must be greater than zero",
                        parent=self,
                    )
                    return None
            except ValueError:
                show_error(
                    "Validation Error", "Batch percentage must be a valid number", parent=self
                )
                return None

        # Return validated data
        return {
            "name": name,
            "recipe_id": recipe_id,
            "category": category,
            "yield_mode": yield_mode,
            "items_per_batch": items_per_batch,
            "item_unit": item_unit,
            "batch_percentage": batch_percentage,
            "portion_description": portion_description,
            "notes": notes,
        }

    def _save(self):
        """Handle save button click."""
        data = self._validate_form()
        if data:
            self.result = data
            self.destroy()

    def _cancel(self):
        """Handle cancel button click."""
        self.result = None
        self.destroy()

    def get_result(self) -> Optional[Dict[str, Any]]:
        """
        Wait for dialog to close and return result.

        Returns:
            Dictionary of form data if saved, None if cancelled
        """
        self.wait_window()
        return self.result


# Backward compatibility alias - finished_goods_tab.py imports this name
FinishedGoodFormDialog = FinishedUnitFormDialog
