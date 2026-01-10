"""
Record Assembly dialog for recording FinishedGood assembly.

Provides a modal dialog for recording assembly of FinishedGoods,
with component availability checking and confirmation.

Feature 026: Added pending packaging check and bypass option.
"""

import customtkinter as ctk
from datetime import datetime
from typing import Optional, Dict, Any, List

from src.models.finished_good import FinishedGood
from src.models.event import Event
from src.ui.widgets.availability_display import AvailabilityDisplay
from src.ui.widgets.dialogs import show_error, show_confirmation
from src.ui.service_integration import get_ui_service_integrator, OperationType
from src.services import assembly_service, event_service, packaging_service, material_consumption_service
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

        # Feature 047: Check for pending material requirements
        pending_materials = self._check_pending_materials()
        material_assignments: Optional[Dict[int, int]] = None

        if pending_materials:
            # Show material assignment dialog
            dialog = PendingMaterialsDialog(self, pending_materials)
            self.wait_window(dialog)

            if dialog.result == "cancel":
                return
            elif dialog.result == "assigned":
                material_assignments = dialog.assignments
            # Note: Materials don't have bypass option - they must be assigned

        # Feature 026: Check for pending packaging requirements
        pending_packaging = self._check_pending_packaging()
        packaging_bypassed = False
        packaging_bypass_notes = None

        if pending_packaging:
            # Show pending packaging dialog
            result = self._show_pending_packaging_dialog(pending_packaging)
            if result == "cancel":
                return
            elif result == "assign":
                # User chose to assign - open assignment dialog for each pending
                self._open_assignment_dialogs(pending_packaging)
                # After assignment, re-check if still pending
                pending_packaging = self._check_pending_packaging()
                if pending_packaging:
                    # Still pending, ask again
                    result = self._show_pending_packaging_dialog(pending_packaging)
                    if result == "cancel":
                        return
                    elif result == "bypass":
                        packaging_bypassed = True
                        packaging_bypass_notes = "User bypassed packaging assignment"
            elif result == "bypass":
                packaging_bypassed = True
                packaging_bypass_notes = "User bypassed packaging assignment"

        # Confirmation dialog
        event_info = ""
        if event_id:
            selected_event = self.event_var.get()
            event_info = f"Event: {selected_event}\n"
        bypass_warning = ""
        if packaging_bypassed:
            bypass_warning = "\nNote: Packaging assignment was bypassed.\n"
        message = (
            f"Assemble {quantity} {self.finished_good.display_name}?\n\n"
            f"{event_info}"
            f"{bypass_warning}"
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
                packaging_bypassed=packaging_bypassed,  # Feature 026
                packaging_bypass_notes=packaging_bypass_notes,  # Feature 026
                material_assignments=material_assignments,  # Feature 047
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
                "packaging_bypassed": packaging_bypassed,  # Feature 026
                "material_assignments": material_assignments,  # Feature 047
            }
            self.destroy()

    def _check_pending_materials(self) -> List[Dict[str, Any]]:
        """
        Check for pending generic material requirements.

        Feature 047: Check if assembly has generic materials needing product selection.

        Returns:
            List of pending material dicts with available_products
        """
        try:
            pending = material_consumption_service.get_pending_materials(
                finished_good_id=self.finished_good.id
            )
            return pending
        except Exception:
            # Don't block assembly if check fails
            return []

    def _check_pending_packaging(self) -> List[Dict[str, Any]]:
        """
        Check for pending generic packaging requirements.

        Feature 026: Check if assembly has unassigned generic packaging.

        Returns:
            List of pending requirement dicts
        """
        try:
            pending = packaging_service.get_pending_requirements(
                assembly_id=self.finished_good.id
            )
            return pending
        except Exception:
            # Don't block assembly if check fails
            return []

    def _show_pending_packaging_dialog(self, pending: List[Dict[str, Any]]) -> str:
        """
        Show dialog for pending packaging with three options.

        Feature 026: Prompt user about unassigned packaging.

        Args:
            pending: List of pending requirement dicts

        Returns:
            "assign", "bypass", or "cancel"
        """
        dialog = PendingPackagingDialog(self, pending)
        self.wait_window(dialog)
        return dialog.result

    def _open_assignment_dialogs(self, pending: List[Dict[str, Any]]):
        """
        Open assignment dialogs for pending packaging.

        Feature 026: Allow quick assignment from record assembly flow.

        Args:
            pending: List of pending requirement dicts
        """
        from src.ui.packaging_assignment_dialog import PackagingAssignmentDialog

        for req in pending:
            composition_id = req.get("composition_id")
            if composition_id:
                dialog = PackagingAssignmentDialog(
                    self, composition_id=composition_id
                )
                self.wait_window(dialog)

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


class PendingPackagingDialog(ctk.CTkToplevel):
    """
    Dialog shown when assembly has pending generic packaging.

    Feature 026: Prompts user with three options:
    - Assign Materials: Open assignment dialog for pending items
    - Record Anyway: Bypass and record assembly with flag
    - Cancel: Abort assembly

    Attributes:
        result: "assign", "bypass", or "cancel"
    """

    def __init__(self, parent, pending: List[Dict[str, Any]]):
        """
        Initialize the pending packaging dialog.

        Args:
            parent: Parent widget
            pending: List of pending requirement dicts
        """
        super().__init__(parent)

        self.pending = pending
        self.result = "cancel"

        self._setup_window()
        self._create_widgets()
        self._setup_modal()

    def _setup_window(self):
        """Configure the dialog window."""
        self.title("Unassigned Packaging")
        self.geometry("400x300")
        self.resizable(False, False)

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

        x = max(0, x)
        y = max(0, y)

        self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        """Create all dialog widgets."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)

        ctk.CTkLabel(
            header_frame,
            text="Unassigned Packaging",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack()

        # Message
        count = len(self.pending)
        item_word = "item" if count == 1 else "items"
        message = (
            f"This assembly has {count} generic packaging {item_word}\n"
            f"that have not been assigned to specific materials.\n\n"
            f"You can assign materials now, or record the\n"
            f"assembly anyway (for later reconciliation)."
        )
        ctk.CTkLabel(
            header_frame,
            text=message,
            justify="center",
        ).pack(pady=(PADDING_MEDIUM, 0))

        # Pending items list
        list_frame = ctk.CTkFrame(self)
        list_frame.grid(
            row=1, column=0, sticky="nsew",
            padx=PADDING_LARGE, pady=PADDING_MEDIUM
        )

        for req in self.pending[:5]:  # Show at most 5
            product_name = req.get("product_name", "Unknown")
            required = req.get("required", 0)
            item_text = f"  - {product_name}: {required} needed"
            ctk.CTkLabel(
                list_frame,
                text=item_text,
                text_color="gray60",
            ).pack(anchor="w", padx=PADDING_MEDIUM, pady=2)

        if len(self.pending) > 5:
            ctk.CTkLabel(
                list_frame,
                text=f"  ... and {len(self.pending) - 5} more",
                text_color="gray60",
            ).pack(anchor="w", padx=PADDING_MEDIUM, pady=2)

        # Buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=3, column=0, pady=PADDING_LARGE)

        ctk.CTkButton(
            button_frame,
            text="Assign Materials",
            command=self._on_assign,
            width=120,
            fg_color="#28A745",
            hover_color="#218838",
        ).pack(side="left", padx=PADDING_MEDIUM)

        ctk.CTkButton(
            button_frame,
            text="Record Anyway",
            command=self._on_bypass,
            width=120,
            fg_color="#FFA500",
            hover_color="#CC8400",
        ).pack(side="left", padx=PADDING_MEDIUM)

        ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            width=80,
        ).pack(side="left", padx=PADDING_MEDIUM)

    def _on_assign(self):
        """Handle Assign Materials button."""
        self.result = "assign"
        self.destroy()

    def _on_bypass(self):
        """Handle Record Anyway button."""
        self.result = "bypass"
        self.destroy()

    def _on_cancel(self):
        """Handle Cancel button."""
        self.result = "cancel"
        self.destroy()


class PendingMaterialsDialog(ctk.CTkToplevel):
    """
    Dialog for selecting products for generic material compositions.

    Feature 047: Materials Management System

    When a FinishedGood has generic material compositions (material_id without
    material_unit_id), the user must select which product to consume at assembly time.
    Unlike packaging, there is no bypass option - materials must be assigned.

    Attributes:
        result: "assigned" or "cancel"
        assignments: Dict[composition_id, product_id] when result is "assigned"
    """

    def __init__(self, parent, pending: List[Dict[str, Any]]):
        """
        Initialize the pending materials dialog.

        Args:
            parent: Parent widget
            pending: List of pending material dicts from get_pending_materials()
        """
        super().__init__(parent)

        self.pending = pending
        self.result = "cancel"
        self.assignments: Dict[int, int] = {}
        self._product_vars: Dict[int, ctk.StringVar] = {}  # composition_id -> StringVar
        self._product_maps: Dict[int, Dict[str, int]] = {}  # composition_id -> {name: product_id}

        self._setup_window()
        self._create_widgets()
        self._setup_modal()

    def _setup_window(self):
        """Configure the dialog window."""
        self.title("Select Material Products")
        self.geometry("500x400")
        self.resizable(False, True)

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

        x = max(0, x)
        y = max(0, y)

        self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        """Create all dialog widgets."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)

        ctk.CTkLabel(
            header_frame,
            text="Select Products for Materials",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack()

        ctk.CTkLabel(
            header_frame,
            text="This assembly uses generic materials. Please select\nwhich product to consume for each material.",
            justify="center",
        ).pack(pady=(PADDING_MEDIUM, 0))

        # Scrollable frame for material selections
        scroll_frame = ctk.CTkScrollableFrame(self)
        scroll_frame.grid(
            row=1, column=0, sticky="nsew",
            padx=PADDING_LARGE, pady=PADDING_MEDIUM
        )
        scroll_frame.grid_columnconfigure(1, weight=1)

        row = 0
        for mat_info in self.pending:
            self._create_material_row(scroll_frame, mat_info, row)
            row += 1

        # Buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=2, column=0, pady=PADDING_LARGE)

        ctk.CTkButton(
            button_frame,
            text="Confirm",
            command=self._on_confirm,
            width=100,
            fg_color="#28A745",
            hover_color="#218838",
        ).pack(side="left", padx=PADDING_MEDIUM)

        ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            width=100,
        ).pack(side="left", padx=PADDING_MEDIUM)

    def _create_material_row(self, parent, mat_info: Dict[str, Any], row: int):
        """Create a row for selecting a product for a material."""
        composition_id = mat_info.get("composition_id")
        material_name = mat_info.get("material_name", "Unknown Material")
        quantity_needed = mat_info.get("quantity_needed", 0)
        available_products = mat_info.get("available_products", [])

        # Material label
        label_text = f"{material_name} ({quantity_needed} units needed)"
        ctk.CTkLabel(
            parent, text=label_text, anchor="w"
        ).grid(row=row, column=0, sticky="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

        # Product dropdown
        if available_products:
            product_names = []
            product_map = {}
            for prod in available_products:
                name = prod.get("name", "Unknown")
                inventory = prod.get("inventory", 0)
                cost = prod.get("unit_cost", 0)
                display = f"{name} ({inventory:.0f} avail, ${cost:.4f}/unit)"
                product_names.append(display)
                product_map[display] = prod.get("id")

            self._product_maps[composition_id] = product_map

            var = ctk.StringVar(value=product_names[0] if product_names else "")
            self._product_vars[composition_id] = var

            dropdown = ctk.CTkOptionMenu(
                parent,
                variable=var,
                values=product_names,
                width=280,
            )
            dropdown.grid(row=row, column=1, sticky="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)
        else:
            ctk.CTkLabel(
                parent,
                text="No products with inventory",
                text_color="#CC0000",
            ).grid(row=row, column=1, sticky="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

    def _on_confirm(self):
        """Handle Confirm button - validate and build assignments."""
        assignments = {}

        for composition_id, var in self._product_vars.items():
            selected = var.get()
            product_map = self._product_maps.get(composition_id, {})
            product_id = product_map.get(selected)

            if not product_id:
                show_error(
                    "Selection Required",
                    "Please select a product for all materials.",
                    parent=self,
                )
                return

            assignments[composition_id] = product_id

        self.assignments = assignments
        self.result = "assigned"
        self.destroy()

    def _on_cancel(self):
        """Handle Cancel button."""
        self.result = "cancel"
        self.destroy()
