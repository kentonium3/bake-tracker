"""
Search bar widget for filtering and searching data.

Provides a reusable search/filter component with optional category dropdown.
"""

import customtkinter as ctk
from typing import Callable, Optional, List


class SearchBar(ctk.CTkFrame):
    """
    Reusable search bar widget with optional category filter.

    Provides a search entry field and optional category dropdown.
    """

    def __init__(
        self,
        parent,
        search_callback: Callable[[str, Optional[str]], None],
        categories: Optional[List[str]] = None,
        placeholder: str = "Search...",
    ):
        """
        Initialize the search bar.

        Args:
            parent: Parent widget
            search_callback: Callback function(search_term, category)
            categories: List of categories for dropdown (optional)
            placeholder: Placeholder text for search entry
        """
        super().__init__(parent, fg_color="transparent")

        self.search_callback = search_callback
        self.categories = categories

        # Configure grid
        self.grid_columnconfigure(0, weight=0)  # Category dropdown
        self.grid_columnconfigure(1, weight=1)  # Search entry
        self.grid_columnconfigure(2, weight=0)  # Search button

        # Category dropdown (if categories provided)
        if categories:
            self.category_var = ctk.StringVar(value="All Categories")
            self.category_dropdown = ctk.CTkOptionMenu(
                self,
                variable=self.category_var,
                values=["All Categories"] + categories,
                width=150,
                command=self._on_category_changed,
            )
            self.category_dropdown.grid(row=0, column=0, padx=(0, 10), sticky="w")

        # Search entry
        self.search_entry = ctk.CTkEntry(
            self,
            placeholder_text=placeholder,
            height=35,
        )
        self.search_entry.grid(row=0, column=1, sticky="ew")
        self.search_entry.bind("<Return>", lambda e: self._on_search())
        self.search_entry.bind("<KeyRelease>", lambda e: self._on_key_release())

        # Search button
        self.search_button = ctk.CTkButton(
            self,
            text="Search",
            width=100,
            command=self._on_search,
        )
        self.search_button.grid(row=0, column=2, padx=(10, 0), sticky="e")

    def _on_search(self):
        """Handle search button click."""
        search_term = self.search_entry.get().strip()
        category = self._get_selected_category()
        self.search_callback(search_term, category)

    def _on_category_changed(self, value):
        """Handle category dropdown selection change."""
        # Trigger search when category changes
        self._on_search()

    def _on_key_release(self):
        """Handle key release in search entry (for live search)."""
        # Optionally implement live search here
        # For now, users must press Enter or click Search button
        pass

    def _get_selected_category(self) -> Optional[str]:
        """
        Get the selected category.

        Returns:
            Selected category, or None if "All Categories" selected
        """
        if not self.categories:
            return None

        category = self.category_var.get()
        if category == "All Categories":
            return None
        return category

    def clear(self):
        """Clear the search entry."""
        self.search_entry.delete(0, "end")
        if self.categories:
            self.category_var.set("All Categories")

    def get_search_term(self) -> str:
        """
        Get the current search term.

        Returns:
            Search term string
        """
        return self.search_entry.get().strip()

    def get_category(self) -> Optional[str]:
        """
        Get the selected category.

        Returns:
            Selected category, or None if all categories
        """
        return self._get_selected_category()
