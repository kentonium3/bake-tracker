"""Recipe selection frame for event planning.

This module provides a reusable UI component for selecting recipes
for an event. It displays a scrollable list of recipes with checkboxes,
visual distinction between base and variant recipes, and real-time
selection count.

Feature: F069 - Recipe Selection for Event Planning
Feature: F100 - Recipe Category Filter-First Selection (WP02)
"""

from typing import Callable, Dict, List, Optional, Set

import customtkinter as ctk

from src.models.recipe import Recipe
from src.services import recipe_category_service, recipe_service
from src.services.database import session_scope


class RecipeSelectionFrame(ctk.CTkFrame):
    """
    A frame for selecting recipes for an event.

    Displays a category filter dropdown and a scrollable list of recipes
    with checkboxes, visual distinction between base and variant recipes,
    and real-time selection count. Starts blank until a category is selected.

    Attributes:
        on_save: Callback when Save is clicked, receives list of selected recipe IDs
        on_cancel: Callback when Cancel is clicked
    """

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        on_save: Optional[Callable[[List[int]], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        """
        Initialize the recipe selection frame.

        Args:
            parent: Parent widget
            on_save: Callback when Save is clicked, receives list of selected recipe IDs
            on_cancel: Callback when Cancel is clicked
            **kwargs: Additional CTkFrame arguments
        """
        super().__init__(parent, **kwargs)

        self._on_save = on_save
        self._on_cancel = on_cancel
        self._recipes: List[Recipe] = []
        self._recipe_vars: Dict[int, ctk.BooleanVar] = {}
        self._selected_recipe_ids: Set[int] = set()  # Persists across category changes
        self._event_name: str = ""

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the frame layout."""
        # Header label
        self._header_label = ctk.CTkLabel(
            self,
            text="Recipe Selection",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self._header_label.pack(pady=(10, 5), padx=10, anchor="w")

        # Selection count label
        self._count_label = ctk.CTkLabel(
            self,
            text="0 of 0 recipes selected",
            font=ctk.CTkFont(size=12),
        )
        self._count_label.pack(pady=(0, 5), padx=10, anchor="w")

        # Filter frame with category dropdown
        self._filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._filter_frame.pack(fill="x", padx=10, pady=(0, 5))

        filter_label = ctk.CTkLabel(
            self._filter_frame,
            text="Category:",
            font=ctk.CTkFont(size=12),
        )
        filter_label.pack(side="left", padx=(0, 5))

        self._category_var = ctk.StringVar(value="")
        self._category_dropdown = ctk.CTkComboBox(
            self._filter_frame,
            variable=self._category_var,
            values=[],  # Populated later via populate_categories()
            command=self._on_category_change,
            width=200,
            state="readonly",
        )
        self._category_dropdown.pack(side="left")

        # Scrollable frame for checkboxes
        self._scroll_frame = ctk.CTkScrollableFrame(
            self,
            height=300,
        )
        self._scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Placeholder label (shown until a category is selected)
        self._placeholder_label = ctk.CTkLabel(
            self._scroll_frame,
            text="Select recipe category to see available recipes",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color=("gray50", "gray60"),
        )
        self._placeholder_label.pack(pady=40)

        # Button frame
        self._button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._button_frame.pack(fill="x", padx=10, pady=10)

        self._cancel_button = ctk.CTkButton(
            self._button_frame,
            text="Cancel",
            width=100,
            command=self._handle_cancel,
        )
        self._cancel_button.pack(side="right", padx=(5, 0))

        self._save_button = ctk.CTkButton(
            self._button_frame,
            text="Save",
            width=100,
            command=self._handle_save,
        )
        self._save_button.pack(side="right")

    def populate_categories(self) -> None:
        """Load category options into the dropdown."""
        with session_scope() as session:
            categories = recipe_category_service.list_categories(session=session)

        category_names = ["All Categories"] + [c.name for c in categories]
        self._category_dropdown.configure(values=category_names)

        # If no categories exist, auto-select "All Categories"
        if not categories:
            self._category_var.set("All Categories")
            self._on_category_change("All Categories")

    def _on_category_change(self, choice: str) -> None:
        """
        Handle category dropdown change.

        Saves current selections, loads recipes for the chosen category,
        and re-renders the checkbox list.

        Args:
            choice: Selected category name from dropdown
        """
        # Save current selections before re-render
        self._save_current_selections()

        if choice == "All Categories":
            recipes = recipe_service.get_all_recipes(include_archived=False)
        else:
            recipes = recipe_service.get_recipes_by_category(choice)

        self._render_recipes(recipes)

    def populate_recipes(self, recipes: List[Recipe], event_name: str = "") -> None:
        """
        Populate the frame with recipe checkboxes.

        Compatibility wrapper that delegates to _render_recipes().

        Args:
            recipes: List of Recipe objects to display
            event_name: Optional event name to display in header
        """
        # Update header
        self._event_name = event_name
        if event_name:
            self._header_label.configure(text=f"Recipe Selection for {event_name}")
        else:
            self._header_label.configure(text="Recipe Selection")

        self._render_recipes(recipes)

    def _render_recipes(self, recipes: List[Recipe]) -> None:
        """
        Render recipe checkboxes in the scroll frame.

        Clears existing checkboxes and creates new ones for the given recipes.
        Restores selection state from the persistence set.

        Args:
            recipes: List of Recipe objects to display
        """
        # Clear existing checkboxes and placeholder
        for widget in self._scroll_frame.winfo_children():
            widget.destroy()
        self._recipe_vars.clear()

        # Store recipes
        self._recipes = recipes

        # Handle empty list
        if not recipes:
            empty_label = ctk.CTkLabel(
                self._scroll_frame,
                text="No recipes available",
                font=ctk.CTkFont(size=12, slant="italic"),
            )
            empty_label.pack(pady=20)
            self._update_count()
            return

        # Create checkbox for each recipe, restoring selection state
        for recipe in recipes:
            display_name = self._get_display_name(recipe)

            var = ctk.BooleanVar(value=recipe.id in self._selected_recipe_ids)
            self._recipe_vars[recipe.id] = var

            checkbox = ctk.CTkCheckBox(
                self._scroll_frame,
                text=display_name,
                variable=var,
                command=self._update_count,
            )
            checkbox.pack(anchor="w", pady=2, padx=5)

        self._update_count()

    def _get_display_name(self, recipe: Recipe) -> str:
        """
        Get display name for a recipe with visual distinction.

        Base recipes display as: "Recipe Name"
        Variants display as: "    Recipe Name (variant: Variant Label)"

        Args:
            recipe: Recipe object

        Returns:
            Formatted display name string
        """
        if recipe.base_recipe_id is not None:
            # This is a variant recipe
            variant_label = recipe.variant_name or "variant"
            return f"    {recipe.name} (variant: {variant_label})"
        else:
            # This is a base recipe
            return recipe.name

    def _save_current_selections(self) -> None:
        """Save current checkbox state to persistence set."""
        for recipe_id, var in self._recipe_vars.items():
            if var.get():
                self._selected_recipe_ids.add(recipe_id)
            else:
                self._selected_recipe_ids.discard(recipe_id)

    def _update_count(self) -> None:
        """Update the selection count label and sync persistence set."""
        # Sync current visible state to persistence set
        for recipe_id, var in self._recipe_vars.items():
            if var.get():
                self._selected_recipe_ids.add(recipe_id)
            else:
                self._selected_recipe_ids.discard(recipe_id)

        total_selected = len(self._selected_recipe_ids)
        visible_total = len(self._recipe_vars)
        visible_selected = sum(1 for var in self._recipe_vars.values() if var.get())
        self._count_label.configure(
            text=f"{visible_selected} of {visible_total} shown selected ({total_selected} total)"
        )

    def get_selected_ids(self) -> List[int]:
        """
        Get ALL selected recipe IDs (including those not currently visible).

        Returns:
            List of recipe IDs that are selected
        """
        self._save_current_selections()
        return list(self._selected_recipe_ids)

    def set_selected(self, recipe_ids: List[int]) -> None:
        """
        Set which recipes are selected (checked).

        Updates both the persistence set and visible checkboxes.

        Args:
            recipe_ids: List of recipe IDs to check (others will be unchecked)
        """
        self._selected_recipe_ids = set(recipe_ids)
        # Restore visible checkboxes
        for recipe_id, var in self._recipe_vars.items():
            var.set(recipe_id in self._selected_recipe_ids)
        self._update_count()

    def clear_selections(self) -> None:
        """Clear all selections and return to blank state."""
        self._selected_recipe_ids.clear()
        for var in self._recipe_vars.values():
            var.set(False)
        self._update_count()

    def _handle_save(self) -> None:
        """Handle Save button click."""
        if self._on_save:
            selected_ids = self.get_selected_ids()
            self._on_save(selected_ids)

    def _handle_cancel(self) -> None:
        """Handle Cancel button click."""
        if self._on_cancel:
            self._on_cancel()
