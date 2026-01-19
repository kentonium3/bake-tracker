"""ReportsTab - Placeholder for future reporting features.

Reports are not yet defined. This tab serves as a placeholder
for future functionality that will be expanded in later releases.

Implements FR-028a: Reports tab is placeholder (not yet defined).
"""

from typing import Any
import customtkinter as ctk


class ReportsTab(ctk.CTkFrame):
    """Placeholder tab for reporting features.

    Displays a message indicating reports are not yet implemented.
    """

    def __init__(self, master: Any, **kwargs):
        """Initialize ReportsTab.

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

        title = ctk.CTkLabel(container, text="Reports", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(pady=(0, 20))

        message = ctk.CTkLabel(
            container,
            text="Reporting features are not yet defined.\n\n"
            "This tab will be expanded in a future release\n"
            "to include customizable reports and analytics.",
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
