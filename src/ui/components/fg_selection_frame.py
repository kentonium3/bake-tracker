"""
FGSelectionFrame - UI component for selecting finished goods.

Part of F070: Finished Goods Filtering for Event Planning.
"""

from typing import Callable, Dict, List, Optional

import customtkinter as ctk

from src.models.finished_good import FinishedGood


class FGSelectionFrame(ctk.CTkFrame):
    """
    Frame for selecting finished goods from available list.

    Displays checkboxes for each available FG with live count and Save/Cancel buttons.
    """

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        on_save: Optional[Callable[[List[int]], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        """
        Initialize FG selection frame.

        Args:
            parent: Parent widget
            on_save: Callback when Save clicked, receives list of selected FG IDs
            on_cancel: Callback when Cancel clicked
            **kwargs: Additional CTkFrame arguments
        """
        super().__init__(parent, **kwargs)

        self._on_save = on_save
        self._on_cancel = on_cancel

        # Track checkboxes and their variables
        self._checkbox_vars: Dict[int, ctk.BooleanVar] = {}  # fg_id -> BooleanVar
        self._checkboxes: Dict[int, ctk.CTkCheckBox] = {}  # fg_id -> checkbox widget
        self._fg_data: Dict[int, FinishedGood] = {}  # fg_id -> FG object

        # Event name for header
        self._event_name: str = ""

        # Build UI
        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create the UI components."""
        # Header label
        self._header_label = ctk.CTkLabel(
            self,
            text="Select Finished Goods",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self._header_label.pack(pady=(10, 5), padx=10, anchor="w")

        # Count label
        self._count_label = ctk.CTkLabel(
            self,
            text="0 of 0 selected",
            font=ctk.CTkFont(size=12),
        )
        self._count_label.pack(pady=(0, 10), padx=10, anchor="w")

        # Scrollable frame for checkboxes
        self._scroll_frame = ctk.CTkScrollableFrame(
            self,
            height=200,
        )
        self._scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Button frame
        self._button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._button_frame.pack(fill="x", padx=10, pady=10)

        self._cancel_button = ctk.CTkButton(
            self._button_frame,
            text="Cancel",
            width=80,
            command=self._handle_cancel,
        )
        self._cancel_button.pack(side="right", padx=(5, 0))

        self._save_button = ctk.CTkButton(
            self._button_frame,
            text="Save",
            width=80,
            command=self._handle_save,
        )
        self._save_button.pack(side="right")

    def populate_finished_goods(
        self,
        finished_goods: List[FinishedGood],
        event_name: str = "",
    ) -> None:
        """
        Populate the frame with finished goods.

        Args:
            finished_goods: List of available FinishedGood objects to display
            event_name: Name of the event (for header display)
        """
        self._event_name = event_name

        # Update header
        if event_name:
            self._header_label.configure(text=f"Finished Goods for {event_name}")
        else:
            self._header_label.configure(text="Select Finished Goods")

        # Clear existing checkboxes
        for widget in self._scroll_frame.winfo_children():
            widget.destroy()
        self._checkbox_vars.clear()
        self._checkboxes.clear()
        self._fg_data.clear()

        # Handle empty list
        if not finished_goods:
            empty_label = ctk.CTkLabel(
                self._scroll_frame,
                text="No finished goods available",
                font=ctk.CTkFont(size=12, slant="italic"),
            )
            empty_label.pack(pady=20)
            self._update_count()
            return

        # Create checkboxes for each FG
        for fg in finished_goods:
            var = ctk.BooleanVar(value=False)
            self._checkbox_vars[fg.id] = var
            self._fg_data[fg.id] = fg

            checkbox = ctk.CTkCheckBox(
                self._scroll_frame,
                text=fg.display_name,
                variable=var,
                command=self._update_count,
            )
            checkbox.pack(anchor="w", pady=2, padx=5)
            self._checkboxes[fg.id] = checkbox

        # Update count display
        self._update_count()

    def set_selected(self, fg_ids: List[int]) -> None:
        """
        Set which FGs are selected.

        Args:
            fg_ids: List of FG IDs to mark as selected
        """
        selected_set = set(fg_ids)
        for fg_id, var in self._checkbox_vars.items():
            var.set(fg_id in selected_set)
        self._update_count()

    def get_selected(self) -> List[int]:
        """
        Get list of selected FG IDs.

        Returns:
            List of FG IDs that are currently checked
        """
        return [
            fg_id
            for fg_id, var in self._checkbox_vars.items()
            if var.get()
        ]

    def _update_count(self) -> None:
        """Update the count label with current selection."""
        selected_count = sum(1 for var in self._checkbox_vars.values() if var.get())
        total_count = len(self._checkbox_vars)
        self._count_label.configure(text=f"{selected_count} of {total_count} selected")

    def _handle_save(self) -> None:
        """Handle Save button click."""
        if self._on_save:
            selected_ids = self.get_selected()
            self._on_save(selected_ids)

    def _handle_cancel(self) -> None:
        """Handle Cancel button click."""
        if self._on_cancel:
            self._on_cancel()
