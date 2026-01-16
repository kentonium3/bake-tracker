"""DeliverMode - Placeholder mode for future delivery workflows.

DELIVER mode will contain features for:
- Tracking deliveries to recipients
- Managing delivery schedules
- Recording delivery completion

This is a placeholder implementation for F055 navigation restructure.
"""

from typing import Any
import customtkinter as ctk

from src.ui.base.base_mode import BaseMode


class DeliverMode(BaseMode):
    """Placeholder mode for delivery workflows.

    Shows a placeholder message until delivery features are implemented.
    """

    def __init__(self, master: Any, **kwargs):
        """Initialize DeliverMode.

        Args:
            master: Parent widget
            **kwargs: Additional arguments passed to BaseMode
        """
        super().__init__(master, name="DELIVER", **kwargs)

        # Set up placeholder content
        self.setup_dashboard()
        self.setup_tabs()

    def setup_dashboard(self) -> None:
        """No dashboard for placeholder mode."""
        # Skip dashboard - placeholder mode doesn't need it
        pass

    def setup_tabs(self) -> None:
        """Create placeholder content instead of tabs."""
        # Create a simple frame for the placeholder
        placeholder_frame = ctk.CTkFrame(self)
        placeholder_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        placeholder_frame.grid_columnconfigure(0, weight=1)
        placeholder_frame.grid_rowconfigure(0, weight=1)

        # Placeholder message
        placeholder_label = ctk.CTkLabel(
            placeholder_frame,
            text="Delivery workflows coming soon",
            font=ctk.CTkFont(size=18),
        )
        placeholder_label.grid(row=0, column=0, sticky="nsew")

    def activate(self) -> None:
        """Called when DELIVER mode becomes active."""
        # No special activation needed for placeholder
        pass

    def refresh_all_tabs(self) -> None:
        """Nothing to refresh in placeholder mode."""
        pass

    def get_current_tab_index(self) -> int:
        """Return 0 since there are no tabs."""
        return 0

    def set_current_tab_index(self, index: int) -> None:
        """No-op since there are no tabs."""
        pass
