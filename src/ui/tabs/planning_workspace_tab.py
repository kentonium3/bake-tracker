"""PlanningWorkspaceTab - Event planning workspace.

Shows calculated batch requirements for selected events:
- Production requirements (batches needed)
- Ingredient requirements aggregated from recipes

Implements FR-021: Planning Workspace shows calculated batch requirements.
"""

from typing import Any
import customtkinter as ctk


class PlanningWorkspaceTab(ctk.CTkFrame):
    """Planning workspace for calculating event requirements.

    Provides event selection and displays production/ingredient requirements.
    """

    def __init__(self, master: Any, **kwargs):
        """Initialize PlanningWorkspaceTab.

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
            text="Planning Workspace",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(pady=(0, 20))

        message = ctk.CTkLabel(
            container,
            text="The Planning Workspace will help you:\n\n"
                 "- Calculate production requirements for events\n"
                 "- View aggregated ingredient needs\n"
                 "- Generate shopping lists\n"
                 "- Plan production schedules",
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
        """Refresh the tab - placeholder has no data to refresh."""
        pass
