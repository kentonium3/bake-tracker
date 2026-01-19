"""PlanningWorkspaceTab - Event planning workspace.

Shows calculated batch requirements for selected events:
- Production requirements (batches needed)
- Ingredient requirements aggregated from recipes
- Shopping lists with Need/Have/Buy columns
- Production and assembly progress tracking

Implements FR-021: Planning Workspace shows calculated batch requirements.
"""

from typing import Any, Optional
import customtkinter as ctk

from src.ui.planning import PlanningWorkspace
from src.services import event_service


class EventSelector(ctk.CTkFrame):
    """Event selector dropdown for the planning workspace."""

    def __init__(self, parent: Any, on_event_selected: callable, **kwargs):
        """Initialize EventSelector.

        Args:
            parent: Parent widget
            on_event_selected: Callback when an event is selected
            **kwargs: Additional arguments passed to CTkFrame
        """
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)

        self.on_event_selected = on_event_selected
        self._events: list = []
        self._event_map: dict[str, int] = {}  # display name -> event_id

        self._setup_ui()
        self._load_events()

    def _setup_ui(self) -> None:
        """Set up the selector UI."""
        self.grid_columnconfigure(1, weight=1)

        label = ctk.CTkLabel(
            self,
            text="Event:",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        label.grid(row=0, column=0, padx=(0, 10), pady=5)

        self.dropdown = ctk.CTkComboBox(
            self,
            values=["Select an event..."],
            command=self._handle_selection,
            width=300,
            state="readonly",
        )
        self.dropdown.grid(row=0, column=1, sticky="w", pady=5)
        self.dropdown.set("Select an event...")

    def _load_events(self) -> None:
        """Load available events from the database."""
        try:
            self._events = event_service.get_all_events()
            if self._events:
                values = []
                self._event_map = {}
                for event in self._events:
                    # Format: "Event Name (Date)"
                    display = f"{event.name}"
                    if event.event_date:
                        display += f" ({event.event_date.strftime('%Y-%m-%d')})"
                    values.append(display)
                    self._event_map[display] = event.id
                self.dropdown.configure(values=["Select an event..."] + values)
        except Exception as e:
            print(f"Error loading events: {e}")

    def _handle_selection(self, choice: str) -> None:
        """Handle event selection.

        Args:
            choice: Selected dropdown value
        """
        if choice == "Select an event..." or choice not in self._event_map:
            return
        event_id = self._event_map[choice]
        self.on_event_selected(event_id)

    def refresh(self) -> None:
        """Refresh the event list."""
        self._load_events()


class PlanningWorkspaceTab(ctk.CTkFrame):
    """Planning workspace for calculating event requirements.

    Provides event selection and displays production/ingredient requirements
    through the PlanningWorkspace component.
    """

    def __init__(self, master: Any, **kwargs):
        """Initialize PlanningWorkspaceTab.

        Args:
            master: Parent widget
            **kwargs: Additional arguments passed to CTkFrame
        """
        super().__init__(master, **kwargs)

        self._current_event_id: Optional[int] = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the tab UI."""
        # Event selector (row 0)
        self.event_selector = EventSelector(
            self,
            on_event_selected=self._handle_event_selected,
        )
        self.event_selector.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))

        # Planning workspace (row 1)
        self.workspace = PlanningWorkspace(self, event_id=None)
        self.workspace.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 10))

    def _handle_event_selected(self, event_id: int) -> None:
        """Handle event selection.

        Args:
            event_id: Selected event ID
        """
        self._current_event_id = event_id
        self.workspace.set_event(event_id)

    def refresh(self) -> None:
        """Refresh the tab data."""
        self.event_selector.refresh()
        if self._current_event_id:
            self.workspace.refresh()
