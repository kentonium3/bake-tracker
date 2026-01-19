"""ModeManager - Coordinates mode switching and state preservation.

Implements FR-001 through FR-005:
- FR-001: 6-mode workflow (OBSERVE, CATALOG, PLAN, PURCHASE, MAKE, DELIVER)
- FR-002: Visual highlighting of active mode
- FR-003: Keyboard shortcuts Ctrl+1-6
- FR-004: Tab state preservation per mode
- FR-005: OBSERVE as default mode on launch
"""

from typing import Dict, Optional, Callable, TYPE_CHECKING
import customtkinter as ctk

if TYPE_CHECKING:
    from ui.base.base_mode import BaseMode


class ModeManager:
    """Coordinates mode switching and state preservation.

    Manages the 6-mode workflow navigation:
    - OBSERVE (Ctrl+1): Dashboard, Event Status, Reports
    - CATALOG (Ctrl+2): Ingredients, Products, Recipes, etc.
    - PLAN (Ctrl+3): Events, Planning Workspace
    - PURCHASE (Ctrl+4): Inventory, Purchases, Shopping Lists
    - MAKE (Ctrl+5): Production Runs, Assembly, Packaging, Recipients
    - DELIVER (Ctrl+6): Delivery workflows (placeholder)

    Attributes:
        current_mode: Name of the currently active mode
        modes: Dictionary of registered mode widgets
        mode_tab_state: Per-mode tab index for state preservation
    """

    # Mode order matches Ctrl+1-6 shortcuts
    MODE_ORDER = ["OBSERVE", "CATALOG", "PLAN", "PURCHASE", "MAKE", "DELIVER"]

    def __init__(self):
        """Initialize ModeManager."""
        self.current_mode: str = "OBSERVE"  # FR-005: Default mode
        self.modes: Dict[str, "BaseMode"] = {}
        self.mode_tab_state: Dict[str, int] = {
            "OBSERVE": 0,
            "CATALOG": 0,
            "PLAN": 0,
            "PURCHASE": 0,
            "MAKE": 0,
            "DELIVER": 0,
        }
        self._mode_buttons: Dict[str, ctk.CTkButton] = {}
        self._on_mode_change_callback: Optional[Callable[[str], None]] = None
        self._content_frame: Optional[ctk.CTkFrame] = None
        self._unsaved_changes_check: Optional[Callable[[], bool]] = None
        self._confirm_discard_callback: Optional[Callable[[], bool]] = None

    def set_content_frame(self, frame: ctk.CTkFrame) -> None:
        """Set the content frame where mode widgets are displayed.

        Args:
            frame: CTkFrame that will contain mode content
        """
        self._content_frame = frame

    def register_mode(self, name: str, mode: "BaseMode") -> None:
        """Register a mode widget.

        Args:
            name: Mode name (CATALOG, PLAN, PURCHASE, MAKE, OBSERVE)
            mode: BaseMode instance

        Raises:
            ValueError: If mode name is not valid
        """
        if name not in self.MODE_ORDER:
            raise ValueError(f"Invalid mode name: {name}. Must be one of {self.MODE_ORDER}")
        self.modes[name] = mode

    def register_mode_button(self, name: str, button: ctk.CTkButton) -> None:
        """Register a mode button for highlighting.

        Args:
            name: Mode name
            button: Button widget for this mode
        """
        self._mode_buttons[name] = button

    def set_on_mode_change_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback to be called when mode changes.

        Args:
            callback: Function taking mode name as argument
        """
        self._on_mode_change_callback = callback

    def set_unsaved_changes_callbacks(
        self, check_callback: Callable[[], bool], confirm_callback: Callable[[], bool]
    ) -> None:
        """Set callbacks for unsaved changes checking.

        Args:
            check_callback: Returns True if there are unsaved changes
            confirm_callback: Shows confirmation dialog, returns True if user wants to proceed
        """
        self._unsaved_changes_check = check_callback
        self._confirm_discard_callback = confirm_callback

    def switch_mode(self, target_mode: str) -> bool:
        """Switch to a different mode.

        Implements FR-004: Tab state preservation.
        Checks for unsaved changes if callbacks are configured.

        Args:
            target_mode: Name of mode to switch to

        Returns:
            True if switch succeeded, False if cancelled or invalid
        """
        if target_mode not in self.modes:
            return False
        if target_mode == self.current_mode:
            return False

        # Check for unsaved changes (edge case handling)
        if self._unsaved_changes_check and self._confirm_discard_callback:
            if self._unsaved_changes_check():
                if not self._confirm_discard_callback():
                    return False  # User cancelled the switch

        # Save current mode's tab state
        current = self.modes.get(self.current_mode)
        if current:
            current.deactivate()
            self.mode_tab_state[self.current_mode] = current.get_current_tab_index()
            current.pack_forget()

        # Activate target mode
        target = self.modes[target_mode]
        target.pack(fill="both", expand=True)

        # Restore tab state
        saved_index = self.mode_tab_state.get(target_mode, 0)
        target.set_current_tab_index(saved_index)
        target.activate()

        # Update current mode
        self.current_mode = target_mode

        # Update button highlighting
        self._update_mode_bar_highlight()

        # Notify callback
        if self._on_mode_change_callback:
            self._on_mode_change_callback(target_mode)

        return True

    def get_current_mode(self) -> Optional["BaseMode"]:
        """Get the currently active mode widget.

        Returns:
            The current BaseMode instance, or None if not set
        """
        return self.modes.get(self.current_mode)

    def get_mode(self, name: str) -> Optional["BaseMode"]:
        """Get a mode widget by name.

        Args:
            name: Mode name

        Returns:
            The BaseMode instance, or None if not found
        """
        return self.modes.get(name)

    def save_tab_state(self) -> None:
        """Save current mode's tab state."""
        current = self.modes.get(self.current_mode)
        if current:
            self.mode_tab_state[self.current_mode] = current.get_current_tab_index()

    def restore_tab_state(self) -> None:
        """Restore current mode's tab state."""
        current = self.modes.get(self.current_mode)
        if current:
            saved_index = self.mode_tab_state.get(self.current_mode, 0)
            current.set_current_tab_index(saved_index)

    def _update_mode_bar_highlight(self) -> None:
        """Update mode button highlighting (FR-002)."""
        for mode_name, button in self._mode_buttons.items():
            if mode_name == self.current_mode:
                # Active mode - highlighted
                button.configure(
                    fg_color=("#3B82F6", "#1D4ED8"),  # Blue
                    hover_color=("#2563EB", "#1E40AF"),
                    text_color=("white", "white"),
                )
            else:
                # Inactive mode - muted
                button.configure(
                    fg_color=("gray75", "gray30"),
                    hover_color=("gray65", "gray40"),
                    text_color=("gray20", "gray90"),
                )

    def get_mode_index(self, mode_name: str) -> int:
        """Get the index of a mode (for keyboard shortcuts).

        Args:
            mode_name: Mode name

        Returns:
            Index (1-6), or 0 if not found
        """
        try:
            return self.MODE_ORDER.index(mode_name) + 1
        except ValueError:
            return 0

    def get_mode_by_index(self, index: int) -> Optional[str]:
        """Get mode name by index (1-6).

        Args:
            index: Mode index (1-6)

        Returns:
            Mode name, or None if invalid index
        """
        if 1 <= index <= len(self.MODE_ORDER):
            return self.MODE_ORDER[index - 1]
        return None

    def initialize_default_mode(self) -> None:
        """Initialize to default OBSERVE mode (FR-005)."""
        if "OBSERVE" in self.modes:
            # Show OBSERVE mode
            observe = self.modes["OBSERVE"]
            observe.pack(fill="both", expand=True)
            observe.activate()
            self.current_mode = "OBSERVE"
            self._update_mode_bar_highlight()
