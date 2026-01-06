"""PurchasesTab - Placeholder for purchase tracking.

Purchase tracking functionality will be implemented in a future release.
This tab serves as a placeholder within the SHOP mode structure.

Implements FR-022: Purchase tracking (placeholder).
"""

from typing import Any
import customtkinter as ctk


class PurchasesTab(ctk.CTkFrame):
    """Placeholder tab for purchase tracking features.

    Displays a message indicating purchases are not yet implemented.
    """

    def __init__(self, master: Any, **kwargs):
        """Initialize PurchasesTab.

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
            text="Purchases",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(pady=(0, 20))

        message = ctk.CTkLabel(
            container,
            text="Purchase tracking is not yet implemented.\n\n"
                 "This tab will allow you to:\n"
                 "- Record purchases from suppliers\n"
                 "- Track purchase history and costs\n"
                 "- Link purchases to inventory items",
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
