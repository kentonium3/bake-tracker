"""StandardTabLayout - Consistent layout pattern for all tabs.

Implements FR-012 through FR-017:
- FR-012: All tabs follow StandardTabLayout pattern
- FR-013: Action buttons in top-left
- FR-014: Refresh button in top-right
- FR-015: Search and filter controls below action bar
- FR-016: Data grid in main content area
- FR-017: Status bar at bottom
"""

from typing import Callable, List, Dict, Any, Optional
import customtkinter as ctk


class StandardTabLayout(ctk.CTkFrame):
    """Standard layout pattern for all tabs with consistent regions.

    Layout:
        Row 0: [action_bar (W)] [refresh_area (E)]
        Row 1: [filter_bar (EW)]
        Row 2: [content_area (NSEW, weight=1)]
        Row 3: [status_bar (EW)]

    Attributes:
        action_bar: Frame for Add/Edit/Delete buttons
        refresh_area: Frame for Refresh button
        filter_bar: Frame for search and filter controls
        content_area: Frame for main content (data grid)
        status_bar: Frame for status information
    """

    def __init__(self, master: Any, **kwargs):
        """Initialize StandardTabLayout.

        Args:
            master: Parent widget
            **kwargs: Additional arguments passed to CTkFrame
        """
        super().__init__(master, **kwargs)

        # Configure grid weights
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)
        self.grid_rowconfigure(2, weight=1)  # Content area expands

        # Create layout regions
        self._create_action_bar()
        self._create_refresh_area()
        self._create_filter_bar()
        self._create_content_area()
        self._create_status_bar()

        # Storage for widgets
        self._action_buttons: List[ctk.CTkButton] = []
        self._refresh_callback: Optional[Callable] = None
        self._search_entry: Optional[ctk.CTkEntry] = None
        self._filter_widgets: List[Any] = []

    def _create_action_bar(self) -> None:
        """Create action bar in top-left (FR-013)."""
        self.action_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.action_bar.grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=5)

    def _create_refresh_area(self) -> None:
        """Create refresh button area in top-right (FR-014)."""
        self.refresh_area = ctk.CTkFrame(self, fg_color="transparent")
        self.refresh_area.grid(row=0, column=2, sticky="e", padx=5, pady=5)

        self._refresh_button = ctk.CTkButton(
            self.refresh_area,
            text="Refresh",
            width=80,
            command=self._on_refresh
        )
        self._refresh_button.pack(side="right")

    def _create_filter_bar(self) -> None:
        """Create filter bar below action bar (FR-015)."""
        self.filter_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.filter_bar.grid(row=1, column=0, columnspan=3, sticky="ew", padx=5, pady=(0, 5))

        # Default search entry
        search_label = ctk.CTkLabel(self.filter_bar, text="Search:")
        search_label.pack(side="left", padx=(0, 5))

        self._search_entry = ctk.CTkEntry(self.filter_bar, width=200, placeholder_text="Type to search...")
        self._search_entry.pack(side="left", padx=(0, 10))

    def _create_content_area(self) -> None:
        """Create main content area (FR-016)."""
        self.content_area = ctk.CTkFrame(self)
        self.content_area.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)

        # Configure content area to expand
        self.content_area.grid_columnconfigure(0, weight=1)
        self.content_area.grid_rowconfigure(0, weight=1)

    def _create_status_bar(self) -> None:
        """Create status bar at bottom (FR-017)."""
        self.status_bar = ctk.CTkFrame(self, fg_color="transparent", height=25)
        self.status_bar.grid(row=3, column=0, columnspan=3, sticky="ew", padx=5, pady=(0, 5))

        self._status_label = ctk.CTkLabel(
            self.status_bar,
            text="Ready",
            anchor="w"
        )
        self._status_label.pack(side="left", fill="x", expand=True)

    def _on_refresh(self) -> None:
        """Handle refresh button click."""
        if self._refresh_callback:
            self._refresh_callback()

    def set_action_buttons(self, buttons: List[Dict[str, Any]]) -> None:
        """Set action buttons in the action bar.

        Args:
            buttons: List of button configs with keys:
                - text: Button label
                - command: Callback function
                - width: Optional button width (default 80)
                - state: Optional "normal" or "disabled" (default "normal")

        Example:
            layout.set_action_buttons([
                {"text": "Add", "command": self.add_item},
                {"text": "Edit", "command": self.edit_item},
                {"text": "Delete", "command": self.delete_item}
            ])
        """
        # Clear existing buttons
        for btn in self._action_buttons:
            btn.destroy()
        self._action_buttons.clear()

        # Create new buttons
        for config in buttons:
            btn = ctk.CTkButton(
                self.action_bar,
                text=config.get("text", "Button"),
                command=config.get("command"),
                width=config.get("width", 80),
                state=config.get("state", "normal")
            )
            btn.pack(side="left", padx=(0, 5))
            self._action_buttons.append(btn)

    def set_refresh_callback(self, callback: Callable) -> None:
        """Set the callback for the refresh button.

        Args:
            callback: Function to call when refresh is clicked
        """
        self._refresh_callback = callback

    def set_filters(self, filters: List[Any]) -> None:
        """Add filter widgets to the filter bar.

        Args:
            filters: List of widget instances to add to filter bar
        """
        # Store reference to filter widgets
        self._filter_widgets = filters

        # Add each filter to the filter bar
        for widget in filters:
            widget.pack(side="left", padx=(0, 10))

    def set_content(self, widget: Any) -> None:
        """Set the main content widget.

        Args:
            widget: Widget to place in content area (typically a Treeview or frame)
        """
        # Clear existing content
        for child in self.content_area.winfo_children():
            child.destroy()

        # Add new content
        widget.grid(row=0, column=0, sticky="nsew")

    def set_status(self, text: str) -> None:
        """Update the status bar text.

        Args:
            text: Status message to display
        """
        self._status_label.configure(text=text)

    def get_search_text(self) -> str:
        """Get the current search text.

        Returns:
            Current text in the search entry
        """
        if self._search_entry:
            return self._search_entry.get()
        return ""

    def clear_search(self) -> None:
        """Clear the search entry."""
        if self._search_entry:
            self._search_entry.delete(0, "end")

    def get_action_button(self, index: int) -> Optional[ctk.CTkButton]:
        """Get an action button by index.

        Args:
            index: Button index (0-based)

        Returns:
            The button at the given index, or None if not found
        """
        if 0 <= index < len(self._action_buttons):
            return self._action_buttons[index]
        return None

    def enable_action_button(self, index: int) -> None:
        """Enable an action button by index.

        Args:
            index: Button index (0-based)
        """
        btn = self.get_action_button(index)
        if btn:
            btn.configure(state="normal")

    def disable_action_button(self, index: int) -> None:
        """Disable an action button by index.

        Args:
            index: Button index (0-based)
        """
        btn = self.get_action_button(index)
        if btn:
            btn.configure(state="disabled")
