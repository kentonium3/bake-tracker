"""ShoppingListsTab - Placeholder for shopping list management.

Shopping list functionality will be implemented in a future release.
This tab serves as a placeholder within the SHOP mode structure.

Implements FR-023: Shopping list management (placeholder).
"""

from typing import Any
import customtkinter as ctk


class ShoppingListsTab(ctk.CTkFrame):
    """Placeholder tab for shopping list features.

    Displays a message indicating shopping lists are not yet implemented.
    """

    def __init__(self, master: Any, **kwargs):
        """Initialize ShoppingListsTab.

        Args:
            master: Parent widget
            **kwargs: Additional arguments passed to CTkFrame
        """
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._create_placeholder()

    def _create_placeholder(self) -> None:
        """Create the placeholder message."""
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.place(relx=0.5, rely=0.5, anchor="center")

        title = ctk.CTkLabel(
            container, text="Shopping Lists", font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(pady=(0, 20))

        message = ctk.CTkLabel(
            container,
            text="Shopping list management is not yet implemented.\n\n"
            "This tab will allow you to:\n"
            "- Create shopping lists for events\n"
            "- Track items needed for recipes\n"
            "- Manage purchases and inventory updates",
            font=ctk.CTkFont(size=14),
            justify="center",
        )
        message.pack()

        # Coming soon indicator
        indicator = ctk.CTkLabel(
            container, text="Coming Soon", font=ctk.CTkFont(size=12), text_color="gray"
        )
        indicator.pack(pady=(20, 0))

    def refresh(self) -> None:
        """Refresh the tab - no data to refresh."""
        pass
