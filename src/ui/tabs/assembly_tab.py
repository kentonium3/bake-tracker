"""AssemblyTab - Placeholder for assembly management.

Assembly features are not yet fully implemented. This tab serves as a placeholder
for future functionality that will manage assembly runs and finished goods creation.

Implements FR-025: Assembly tab is placeholder (coming soon).
"""

from typing import Any
import customtkinter as ctk


class AssemblyTab(ctk.CTkFrame):
    """Placeholder tab for assembly management features.

    Displays a message indicating assembly features are coming soon.
    """

    def __init__(self, master: Any, **kwargs):
        """Initialize AssemblyTab.

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
            container,
            text="Assembly",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(pady=(0, 20))

        message = ctk.CTkLabel(
            container,
            text="Assembly management features are under development.\n\n"
                 "This tab will allow you to:\n"
                 "- Create assembly runs from finished units\n"
                 "- Track finished goods production\n"
                 "- Manage assembly targets per event",
            font=ctk.CTkFont(size=14),
            justify="center"
        )
        message.pack()

        # Coming soon indicator
        indicator = ctk.CTkLabel(
            container,
            text="Coming Soon",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        indicator.pack(pady=(20, 0))

    def refresh(self) -> None:
        """Refresh the tab - no data to refresh."""
        pass
