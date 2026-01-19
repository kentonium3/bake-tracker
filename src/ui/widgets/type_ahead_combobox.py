"""
Type-ahead filtering combobox widget.

This module provides an enhanced CTkComboBox with real-time type-ahead filtering.
Used for Category/Ingredient/Product dropdowns in inventory forms.

Usage:
    from src.ui.widgets.type_ahead_combobox import TypeAheadComboBox

    combo = TypeAheadComboBox(
        master=frame,
        values=['Flour', 'Sugar', 'Butter'],
        min_chars=2,
        command=on_select
    )
"""

import re

import customtkinter as ctk
from typing import List, Callable, Optional, Any


class TypeAheadComboBox(ctk.CTkFrame):
    """
    Enhanced CTkComboBox with type-ahead filtering.

    Features:
    - Real-time filtering as user types
    - Minimum character threshold before filtering
    - Word boundary prioritization in matches
    - Preserves full values list for reset

    This is a composite widget that wraps CTkComboBox in a CTkFrame.
    We don't subclass CTkComboBox directly to avoid interfering with
    its internal rendering and keyboard navigation.
    """

    def __init__(
        self,
        master: Any,
        values: Optional[List[str]] = None,
        min_chars: int = 2,
        command: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        """
        Initialize the TypeAheadComboBox.

        Args:
            master: Parent widget
            values: List of dropdown values
            min_chars: Minimum characters before filtering starts (default 2)
            command: Callback when selection changes
            **kwargs: Additional arguments passed to CTkComboBox
        """
        # Initialize frame with transparent background
        super().__init__(master, fg_color="transparent")

        self.full_values = values or []
        self.min_chars = min_chars
        self.filtered = False
        self._command = command

        # Create embedded combobox
        self._combobox = ctk.CTkComboBox(
            self, values=self.full_values, command=self._on_select, **kwargs
        )
        self._combobox.pack(fill="x", expand=True)

        # Get entry widget for key binding
        # Note: Using internal _entry attribute from CTkComboBox
        self._entry = self._combobox._entry

        # Bind events
        self._entry.bind("<KeyRelease>", self._on_key_release)
        self._entry.bind("<FocusOut>", self._on_focus_out)

    def _filter_values(self, typed: str) -> List[str]:
        """
        Filter values list based on typed text.

        Prioritizes word boundary matches over contains matches.
        Word boundary: matches at start of any word (e.g., "ap" matches "AP Flour")
        Contains: matches anywhere in string (e.g., "ap" matches "Maple")

        Args:
            typed: The text typed by the user

        Returns:
            Filtered list with word boundary matches first
        """
        if not typed:
            return []

        typed_lower = typed.lower()

        word_boundary = []
        contains = []

        for value in self.full_values:
            value_lower = value.lower()

            # Check word boundaries (starts with or after space, hyphen, slash)
            # Split on common word separators
            words = re.split(r"[\s\-/]+", value_lower)
            is_word_boundary = any(word.startswith(typed_lower) for word in words)

            if is_word_boundary:
                word_boundary.append(value)
            elif typed_lower in value_lower:
                contains.append(value)

        return word_boundary + contains

    def _on_key_release(self, event) -> None:
        """Handle key release for type-ahead filtering."""
        # Ignore navigation keys
        if event.keysym in ("Up", "Down", "Left", "Right", "Return", "Tab", "Escape"):
            return

        typed = self.get()

        # Reset filter if below threshold
        if len(typed) < self.min_chars:
            if self.filtered:
                self._combobox.configure(values=self.full_values)
                self.filtered = False
            return

        # Apply filter
        filtered = self._filter_values(typed)
        if filtered:
            self._combobox.configure(values=filtered)
            self.filtered = True
        else:
            # No matches - show all values so user can still select
            self._combobox.configure(values=self.full_values)
            self.filtered = False

    def _on_focus_out(self, event) -> None:
        """Handle focus out - reset filter."""
        if self.filtered:
            self._combobox.configure(values=self.full_values)
            self.filtered = False

    def _on_select(self, value: str) -> None:
        """Handle selection from dropdown."""
        # Reset filter when selection made
        if self.filtered:
            self._combobox.configure(values=self.full_values)
            self.filtered = False

        # Call user's command if provided
        if self._command:
            self._command(value)

    def reset_values(self, values: List[str]) -> None:
        """
        Update the full values list.

        Call this when underlying data changes (e.g., category selected,
        ingredient list needs updating).

        Args:
            values: New list of values
        """
        self.full_values = values
        self._combobox.configure(values=values)
        self.filtered = False

    def get(self) -> str:
        """Get current entry value."""
        return self._combobox.get()

    def set(self, value: str) -> None:
        """Set entry value."""
        self._combobox.set(value)

    def configure(self, **kwargs) -> None:
        """Configure the widget."""
        # Handle values separately to update full_values
        if "values" in kwargs:
            self.full_values = kwargs.pop("values")
            kwargs["values"] = self.full_values
            self.filtered = False

        # Guard against calls during parent __init__ before _combobox is created
        if kwargs and hasattr(self, "_combobox"):
            self._combobox.configure(**kwargs)

    def cget(self, attribute: str) -> Any:
        """Get widget attribute."""
        if attribute == "values":
            return self.full_values
        # Guard against calls during parent __init__ before _combobox is created
        # Fall back to CTkFrame's cget for frame-level attributes
        if hasattr(self, "_combobox"):
            return self._combobox.cget(attribute)
        return super().cget(attribute)
