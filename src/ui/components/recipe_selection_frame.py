"""Recipe selection frame for event planning.

This module provides a reusable UI component for selecting recipes
for an event. It displays a scrollable list of recipes with checkboxes,
visual distinction between base and variant recipes, and real-time
selection count.

Feature: F069 - Recipe Selection for Event Planning
"""

from typing import Callable, Dict, List, Optional

import customtkinter as ctk

from src.models.recipe import Recipe


class RecipeSelectionFrame(ctk.CTkFrame):
    """
    A frame for selecting recipes for an event.

    Displays a scrollable list of recipes with checkboxes,
    visual distinction between base and variant recipes,
    and real-time selection count.

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
        self._count_label.pack(pady=(0, 10), padx=10, anchor="w")

        # Scrollable frame for checkboxes
        self._scroll_frame = ctk.CTkScrollableFrame(
            self,
            height=300,
        )
        self._scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)

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

    def populate_recipes(self, recipes: List[Recipe], event_name: str = "") -> None:
        """
        Populate the frame with recipe checkboxes.

        Args:
            recipes: List of Recipe objects to display
            event_name: Optional event name to display in header
        """
        # Clear existing checkboxes
        for widget in self._scroll_frame.winfo_children():
            widget.destroy()
        self._recipe_vars.clear()

        # Update header
        self._event_name = event_name
        if event_name:
            self._header_label.configure(text=f"Recipe Selection for {event_name}")
        else:
            self._header_label.configure(text="Recipe Selection")

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

        # Create checkbox for each recipe
        for recipe in recipes:
            display_name = self._get_display_name(recipe)

            var = ctk.BooleanVar(value=False)
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

    def _update_count(self) -> None:
        """Update the selection count label."""
        selected = sum(1 for var in self._recipe_vars.values() if var.get())
        total = len(self._recipe_vars)
        self._count_label.configure(text=f"{selected} of {total} recipes selected")

    def get_selected_ids(self) -> List[int]:
        """
        Get IDs of all currently selected recipes.

        Returns:
            List of recipe IDs that are checked
        """
        return [
            recipe_id
            for recipe_id, var in self._recipe_vars.items()
            if var.get()
        ]

    def set_selected(self, recipe_ids: List[int]) -> None:
        """
        Set which recipes are selected (checked).

        Args:
            recipe_ids: List of recipe IDs to check (others will be unchecked)
        """
        selected_set = set(recipe_ids)
        for recipe_id, var in self._recipe_vars.items():
            var.set(recipe_id in selected_set)
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
