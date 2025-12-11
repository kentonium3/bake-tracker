"""
Record Assembly dialog for recording FinishedGood assembly.

Provides a modal dialog for recording assembly of FinishedGoods,
with component availability checking and confirmation.
"""

import customtkinter as ctk
from datetime import datetime
from typing import Optional, Dict, Any, List

from src.models.finished_good import FinishedGood
from src.models.event import Event
from src.ui.widgets.availability_display import AvailabilityDisplay
from src.ui.widgets.dialogs import show_error, show_confirmation
from src.ui.service_integration import get_ui_service_integrator, OperationType
from src.services import assembly_service, event_service
from src.utils.constants import PADDING_MEDIUM, PADDING_LARGE


class RecordAssemblyDialog(ctk.CTkToplevel):
    """
    Modal dialog for recording assembly of FinishedGoods.

    Shows component availability (FinishedUnits, nested FinishedGoods, packaging)
    and allows recording assembly with quantity and optional notes.
    """

    def __init__(self, parent, finished_good: FinishedGood):
        """
        Initialize the Record Assembly dialog.

        Args:
            parent: Parent widget
            finished_good: The FinishedGood to assemble
        """
        super().__init__(parent)

        self.finished_good = finished_good
        self.result: Optional[Dict[str, Any]] = None
        self._can_assemble = False
        self.service_integrator = get_ui_service_integrator()

        # Feature 016: Load events for event selector
        self.events: List[Event] = self._load_events()

        self._setup_window()
        self._create_widgets()
        self._setup_modal()
        self._check_availability()

    def get_result(self) -> Optional[Dict[str, Any]]:
        """Return the assembly result, or None if cancelled."""
        return self.result

    def _setup_window(self):
        """Configure the dialog window."""
        self.title(f"Record Assembly - {self.finished_good.display_name}")
        self.geometry("450x500")
        self.minsize(400, 450)
        self.resizable(True, True)

        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(4, weight=1)  # Availability expands (row 4 after event selector)

    def _setup_modal(self):
        """Set up modal behavior."""
        self.transient(self.master)
        self.wait_visibility()
        self.grab_set()
        self.focus_force()
        self._center_on_parent()

    def _center_on_parent(self):
        """Center the dialog on its parent."""
        self.update_idletasks()

        parent = self.master
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()

        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2

        # Ensure on screen
        x = max(0, x)
        y = max(0, y)

        self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        """Create all dialog widgets."""
        row = 0

        # Header
        header = ctk.CTkLabel(
            self,
            text=self.finished_good.display_name,
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        header.grid(row=row, column=0, columnspan=2, pady=PADDING_LARGE)
        row += 1

        # Feature 016: Event selector
        ctk.CTkLabel(self, text="Event (optional):").grid(
            row=row, column=0, sticky="e", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        event_options = ["(None - standalone)"] + [e.name for e in self.events]
        self.event_var = ctk.StringVar(value=event_options[0])
        self.event_dropdown = ctk.CTkOptionMenu(
            self,
            variable=self.event_var,
            values=event_options,
            width=250,
        )
        self.event_dropdown.grid(
            row=row, column=1, sticky="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        row += 1

        # Quantity
        ctk.CTkLabel(self, text="Quantity:").grid(
            row=row, column=0, sticky="e", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        self.quantity_entry = ctk.CTkEntry(self, width=100)
        self.quantity_entry.insert(0, "1")
        self.quantity_entry.grid(
            row=row, column=1, sticky="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        row += 1

        # Notes
        ctk.CTkLabel(self, text="Notes:").grid(
            row=row, column=0, sticky="ne", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        self.notes_textbox = ctk.CTkTextbox(self, height=60)
        self.notes_textbox.grid(
            row=row, column=1, sticky="ew", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        row += 1

        # Availability display
        self.availability_display = AvailabilityDisplay(
            self, title="Component Availability"
        )
        self.availability_display.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="nsew",
            padx=PADDING_MEDIUM,
            pady=PADDING_MEDIUM,
        )
        row += 1

        self._create_buttons(row)

    def _create_buttons(self, row: int):
        """Create the button row."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=row, column=0, columnspan=2, pady=PADDING_LARGE)

        self.refresh_btn = ctk.CTkButton(
            button_frame,
            text="Refresh Availability",
            command=self._check_availability,
            width=140,
        )
        self.refresh_btn.pack(side="left", padx=PADDING_MEDIUM)

        self.confirm_btn = ctk.CTkButton(
            button_frame,
            text="Confirm",
            command=self._on_confirm,
            width=100,
        )
        self.confirm_btn.pack(side="left", padx=PADDING_MEDIUM)

        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            width=100,
        )
        cancel_btn.pack(side="left", padx=PADDING_MEDIUM)

    def _check_availability(self):
        """Check component availability for the current quantity."""
        quantity = self._get_quantity()
        if quantity < 1:
            self.availability_display.clear()
            self._can_assemble = False
            self._update_confirm_button()
            return

        result = self.service_integrator.execute_service_operation(
            operation_name="Check Assembly Availability",
            operation_type=OperationType.READ,
            service_function=lambda: assembly_service.check_can_assemble(
                self.finished_good.id, quantity
            ),
            parent_widget=self,
            error_context="Checking component availability",
            suppress_exception=True,
        )

        if result:
            self.availability_display.set_availability(result)
            self._can_assemble = result.get("can_assemble", False)
        else:
            self._can_assemble = False

        self._update_confirm_button()

    def _update_confirm_button(self):
        """Update confirm button state based on availability."""
        state = "normal" if self._can_assemble else "disabled"
        self.confirm_btn.configure(state=state)

    def _on_confirm(self):
        """Handle confirm button click."""
        if not self._validate():
            return

        quantity = self._get_quantity()
        notes = self.notes_textbox.get("1.0", "end-1c").strip() or None
        event_id = self._get_selected_event_id()  # Feature 016

        # Confirmation dialog
        event_info = ""
        if event_id:
            selected_event = self.event_var.get()
            event_info = f"Event: {selected_event}\n"
        message = (
            f"Assemble {quantity} {self.finished_good.display_name}?\n\n"
            f"{event_info}"
            f"This will consume components from inventory.\n"
            f"This action cannot be undone."
        )
        if not show_confirmation("Confirm Assembly", message, parent=self):
            return

        result = self.service_integrator.execute_service_operation(
            operation_name="Record Assembly",
            operation_type=OperationType.CREATE,
            service_function=lambda: assembly_service.record_assembly(
                finished_good_id=self.finished_good.id,
                quantity=quantity,
                notes=notes,
                event_id=event_id,  # Feature 016
            ),
            parent_widget=self,
            success_message=f"Assembled {quantity} {self.finished_good.display_name}",
            error_context="Recording assembly",
            show_success_dialog=True,
        )

        if result:
            self.result = {
                "finished_good_id": self.finished_good.id,
                "quantity": quantity,
                "notes": notes,
                "event_id": event_id,  # Feature 016
                "assembly_run_id": result.get("assembly_run_id"),
            }
            self.destroy()

    def _on_cancel(self):
        """Handle cancel button click."""
        self.result = None
        self.destroy()

    def _validate(self) -> bool:
        """Validate inputs before recording."""
        quantity = self._get_quantity()
        if quantity < 1:
            show_error(
                "Validation Error", "Quantity must be at least 1.", parent=self
            )
            return False

        if not self._can_assemble:
            show_error(
                "Insufficient Components",
                "Cannot assemble - some components are insufficient.\n"
                "Check the availability display for details.",
                parent=self,
            )
            return False

        return True

    def _get_quantity(self) -> int:
        """Get the quantity value from the entry."""
        try:
            return int(self.quantity_entry.get())
        except ValueError:
            return 0

    def _load_events(self) -> List[Event]:
        """Load events sorted by date (nearest upcoming first)."""
        try:
            events = event_service.get_all_events()
            # Sort by event_date ascending; events without date go to end
            events.sort(key=lambda e: e.event_date or datetime.max.date())
            return events
        except Exception:
            # If event loading fails, return empty list
            return []

    def _get_selected_event_id(self) -> Optional[int]:
        """Get the event_id for the selected event, or None for standalone."""
        selected = self.event_var.get()
        if selected == "(None - standalone)":
            return None
        for event in self.events:
            if event.name == selected:
                return event.id
        return None
