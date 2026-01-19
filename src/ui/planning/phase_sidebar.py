"""PhaseSidebar - Navigation sidebar for Planning Workspace.

Provides phase navigation buttons with status indicators for the
planning workflow: Calculate, Shop, Produce, Assemble.

Implements FR-024: Visual status for each phase.
"""

from enum import Enum
from typing import Any, Callable, Optional
import customtkinter as ctk


class PlanPhase(Enum):
    """Planning workflow phases."""

    CALCULATE = "calculate"
    SHOP = "shop"
    PRODUCE = "produce"
    ASSEMBLE = "assemble"


class PhaseStatus(Enum):
    """Status indicators for each phase."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    BLOCKED = "blocked"


# Status indicator colors
STATUS_COLORS = {
    PhaseStatus.NOT_STARTED: "#808080",  # Gray
    PhaseStatus.IN_PROGRESS: "#FFD700",  # Yellow/Gold
    PhaseStatus.COMPLETE: "#00AA00",  # Green
    PhaseStatus.BLOCKED: "#CC0000",  # Red
}

# Status indicator symbols (unicode)
STATUS_SYMBOLS = {
    PhaseStatus.NOT_STARTED: "\u25cb",  # White circle
    PhaseStatus.IN_PROGRESS: "\u25d0",  # Circle with left half black
    PhaseStatus.COMPLETE: "\u25cf",  # Black circle (filled)
    PhaseStatus.BLOCKED: "\u26a0",  # Warning sign
}

# Phase display names (FR-022/FR-023: Use Purchase/Make terminology)
PHASE_NAMES = {
    PlanPhase.CALCULATE: "Calculate",
    PlanPhase.SHOP: "Purchase",
    PlanPhase.PRODUCE: "Make",
    PlanPhase.ASSEMBLE: "Assemble",
}


class StatusIndicator(ctk.CTkLabel):
    """Small status indicator showing phase completion status.

    Uses unicode symbols with color-coding:
    - Gray circle: Not started
    - Yellow half-circle: In progress
    - Green filled circle: Complete
    - Red warning: Blocked
    """

    def __init__(self, parent: Any, status: PhaseStatus = PhaseStatus.NOT_STARTED, **kwargs):
        """Initialize StatusIndicator.

        Args:
            parent: Parent widget
            status: Initial status
            **kwargs: Additional arguments passed to CTkLabel
        """
        super().__init__(
            parent,
            text=STATUS_SYMBOLS[status],
            text_color=STATUS_COLORS[status],
            font=ctk.CTkFont(size=16),
            width=24,
            **kwargs,
        )
        self._status = status

    @property
    def status(self) -> PhaseStatus:
        """Get current status."""
        return self._status

    def set_status(self, status: PhaseStatus) -> None:
        """Update the status indicator.

        Args:
            status: New status to display
        """
        self._status = status
        self.configure(text=STATUS_SYMBOLS[status], text_color=STATUS_COLORS[status])


class PhaseButton(ctk.CTkFrame):
    """Navigation button for a planning phase with status indicator."""

    def __init__(
        self, parent: Any, phase: PlanPhase, on_click: Callable[[PlanPhase], None], **kwargs
    ):
        """Initialize PhaseButton.

        Args:
            parent: Parent widget
            phase: The phase this button represents
            on_click: Callback when button is clicked
            **kwargs: Additional arguments passed to CTkFrame
        """
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.phase = phase
        self.on_click = on_click
        self._is_active = False

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        # Status indicator
        self.indicator = StatusIndicator(self)
        self.indicator.grid(row=0, column=0, padx=(5, 8), pady=5)

        # Button
        self.button = ctk.CTkButton(
            self,
            text=PHASE_NAMES[phase],
            command=self._handle_click,
            anchor="w",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            corner_radius=6,
        )
        self.button.grid(row=0, column=1, sticky="ew", padx=(0, 5), pady=2)

    def _handle_click(self) -> None:
        """Handle button click."""
        self.on_click(self.phase)

    def set_active(self, active: bool) -> None:
        """Set whether this button shows as active/selected.

        Args:
            active: True to show as active/selected
        """
        self._is_active = active
        if active:
            self.button.configure(
                fg_color=("gray75", "gray25"),
                text_color=("gray10", "gray90"),
            )
        else:
            self.button.configure(
                fg_color="transparent",
                text_color=("gray10", "gray90"),
            )

    def set_status(self, status: PhaseStatus) -> None:
        """Update the phase status indicator.

        Args:
            status: New status
        """
        self.indicator.set_status(status)


class PhaseSidebar(ctk.CTkFrame):
    """Navigation sidebar with phase buttons and status indicators.

    Provides navigation between planning phases with visual feedback
    on completion status.
    """

    def __init__(self, parent: Any, on_phase_select: Callable[[PlanPhase], None], **kwargs):
        """Initialize PhaseSidebar.

        Args:
            parent: Parent widget
            on_phase_select: Callback when a phase is selected
            **kwargs: Additional arguments passed to CTkFrame
        """
        # Set a subtle background color to distinguish sidebar
        kwargs.setdefault("fg_color", ("gray85", "gray20"))
        kwargs.setdefault("corner_radius", 0)
        super().__init__(parent, **kwargs)

        self.on_phase_select = on_phase_select
        self._buttons: dict[PlanPhase, PhaseButton] = {}
        self._active_phase: Optional[PlanPhase] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the sidebar UI."""
        self.grid_columnconfigure(0, weight=1)

        # Title
        title = ctk.CTkLabel(
            self,
            text="Planning",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.grid(row=0, column=0, pady=(15, 10), padx=10, sticky="w")

        # Separator
        separator = ctk.CTkFrame(self, height=2, fg_color=("gray70", "gray40"))
        separator.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

        # Phase buttons
        for i, phase in enumerate(PlanPhase):
            button = PhaseButton(
                self,
                phase=phase,
                on_click=self._handle_phase_click,
            )
            button.grid(row=i + 2, column=0, sticky="ew", padx=5, pady=2)
            self._buttons[phase] = button

        # Spacer to push buttons to top
        spacer = ctk.CTkFrame(self, fg_color="transparent")
        spacer.grid(row=len(PlanPhase) + 2, column=0, sticky="nsew")
        self.grid_rowconfigure(len(PlanPhase) + 2, weight=1)

    def _handle_phase_click(self, phase: PlanPhase) -> None:
        """Handle phase button click.

        Args:
            phase: The clicked phase
        """
        self.on_phase_select(phase)

    def update_active_phase(self, phase: PlanPhase) -> None:
        """Update which phase shows as active/selected.

        Args:
            phase: The phase to mark as active
        """
        self._active_phase = phase
        for p, button in self._buttons.items():
            button.set_active(p == phase)

    def update_phase_status(self, phase: PlanPhase, status: PhaseStatus) -> None:
        """Update the status indicator for a phase.

        Args:
            phase: The phase to update
            status: New status
        """
        if phase in self._buttons:
            self._buttons[phase].set_status(status)

    def update_all_statuses(self, statuses: dict[PlanPhase, PhaseStatus]) -> None:
        """Update all phase statuses at once.

        Args:
            statuses: Dict mapping phases to their statuses
        """
        for phase, status in statuses.items():
            self.update_phase_status(phase, status)
