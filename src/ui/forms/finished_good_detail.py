"""
FinishedGood detail dialog for viewing and managing assembly.

Provides a modal dialog showing FinishedGood details, composition,
assembly history, and access to Record Assembly functionality.
"""

import customtkinter as ctk
from typing import Optional, Callable

from src.models.finished_good import FinishedGood
from src.ui.widgets.assembly_history_table import AssemblyHistoryTable
from src.ui.service_integration import get_ui_service_integrator, OperationType
from src.services import assembly_service, finished_good_service
from src.utils.constants import PADDING_MEDIUM, PADDING_LARGE


class FinishedGoodDetailDialog(ctk.CTkToplevel):
    """
    Modal dialog for displaying FinishedGood details and assembly history.

    Shows:
    - Name
    - Inventory count, total cost
    - Composition (BOM - FinishedUnits, nested FinishedGoods, packaging)
    - Assembly history table
    - Record Assembly button
    """

    def __init__(
        self,
        parent,
        finished_good: FinishedGood,
        on_inventory_changed: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize the FinishedGood detail dialog.

        Args:
            parent: Parent widget
            finished_good: The FinishedGood to display
            on_inventory_changed: Optional callback when inventory changes
        """
        super().__init__(parent)

        self.finished_good = finished_good
        self._on_inventory_changed = on_inventory_changed
        self._has_composition = False
        self.service_integrator = get_ui_service_integrator()

        self._setup_window()
        self._create_widgets()
        self._load_data()
        self._setup_modal()

    def _setup_window(self):
        """Configure the dialog window."""
        self.title(f"Details - {self.finished_good.display_name}")
        self.geometry("550x650")
        self.minsize(500, 550)
        self.resizable(True, True)

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)  # History table expands

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
        self._create_header()
        self._create_info_section()
        self._create_composition_section()
        self._create_history_section()
        self._create_buttons()

    def _create_header(self):
        """Create the header section with name."""
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(
            row=0, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE
        )

        name_label = ctk.CTkLabel(
            header_frame,
            text=self.finished_good.display_name,
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        name_label.pack(anchor="w")

    def _create_info_section(self):
        """Create the info section with inventory and cost."""
        info_frame = ctk.CTkFrame(self)
        info_frame.grid(
            row=1, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_MEDIUM
        )
        info_frame.grid_columnconfigure(1, weight=1)

        row = 0

        # Inventory count
        ctk.CTkLabel(info_frame, text="In Stock:").grid(
            row=row, column=0, sticky="e", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        self.inventory_label = ctk.CTkLabel(
            info_frame,
            text=str(self.finished_good.inventory_count or 0),
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.inventory_label.grid(
            row=row, column=1, sticky="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        row += 1

        # Total cost
        ctk.CTkLabel(info_frame, text="Total Cost:").grid(
            row=row, column=0, sticky="e", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )
        cost = self.finished_good.total_cost or 0
        self.cost_label = ctk.CTkLabel(info_frame, text=f"${cost:.2f}")
        self.cost_label.grid(
            row=row, column=1, sticky="w", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )

    def _create_composition_section(self):
        """Create the composition (BOM) display section."""
        # Section header
        comp_header = ctk.CTkLabel(
            self,
            text="Composition",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        comp_header.grid(
            row=2,
            column=0,
            sticky="w",
            padx=PADDING_LARGE,
            pady=(PADDING_LARGE, PADDING_MEDIUM),
        )

        # Composition frame (scrollable for many components)
        comp_frame = ctk.CTkScrollableFrame(self, height=120)
        comp_frame.grid(
            row=3, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_MEDIUM
        )

        # Load and display components
        self._populate_composition(comp_frame)

    def _populate_composition(self, parent_frame):
        """Populate the composition frame with component rows."""
        # Get composition from relationships
        compositions = getattr(self.finished_good, "compositions", [])

        if not compositions:
            no_comp = ctk.CTkLabel(
                parent_frame, text="No components defined", text_color=("gray60", "gray40")
            )
            no_comp.pack(anchor="w")
            self._has_composition = False
            return

        self._has_composition = True

        for comp in compositions:
            row_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)

            # Determine component name and type
            if comp.finished_unit_id and comp.finished_unit:
                name = f"[FU] {comp.finished_unit.display_name}"
            elif comp.finished_good_id and comp.finished_good:
                name = f"[FG] {comp.finished_good.display_name}"
            elif comp.packaging_product_id and comp.packaging_product:
                name = f"[Pkg] {comp.packaging_product.display_name}"
            else:
                name = "Unknown component"

            qty = comp.component_quantity or 0

            ctk.CTkLabel(row_frame, text=f"  {qty}x {name}").pack(side="left")

    def _create_history_section(self):
        """Create the assembly history section."""
        # Section header
        history_header = ctk.CTkLabel(
            self,
            text="Assembly History",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        history_header.grid(
            row=4,
            column=0,
            sticky="w",
            padx=PADDING_LARGE,
            pady=(PADDING_LARGE, PADDING_MEDIUM),
        )

        # History table
        self.history_table = AssemblyHistoryTable(
            self,
            on_row_select=self._on_history_select,
            height=150,
        )
        self.history_table.grid(
            row=5, column=0, sticky="nsew", padx=PADDING_LARGE, pady=PADDING_MEDIUM
        )

    def _create_buttons(self):
        """Create the button row."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(
            row=6, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE
        )

        # Record Assembly button
        self.record_btn = ctk.CTkButton(
            button_frame,
            text="Record Assembly",
            command=self._open_record_assembly,
            width=150,
        )
        self.record_btn.pack(side="left", padx=PADDING_MEDIUM)

        # Disable if no composition
        if not self._has_composition:
            self.record_btn.configure(state="disabled")
            note = ctk.CTkLabel(
                button_frame,
                text="(No components defined)",
                text_color=("gray60", "gray40"),
            )
            note.pack(side="left", padx=PADDING_MEDIUM)

        # Close button
        close_btn = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self.destroy,
            width=100,
        )
        close_btn.pack(side="right", padx=PADDING_MEDIUM)

    def _load_data(self):
        """Load initial data (assembly history)."""
        self._load_history()

    def _load_history(self):
        """Load assembly history for this FinishedGood."""
        history = self.service_integrator.execute_service_operation(
            operation_name="Load Assembly History",
            operation_type=OperationType.READ,
            service_function=lambda: assembly_service.get_assembly_history(
                finished_good_id=self.finished_good.id,
                limit=50,
                include_consumptions=False,
            ),
            parent_widget=self,
            error_context="Loading assembly history",
            suppress_exception=True,
        )

        if history:
            self.history_table.set_data(history)
        else:
            self.history_table.clear()

    def _on_history_select(self, run):
        """Handle assembly run selection."""
        # Optional: could show run details
        pass

    def _open_record_assembly(self):
        """Open the Record Assembly dialog."""
        from src.ui.forms.record_assembly_dialog import RecordAssemblyDialog

        dialog = RecordAssemblyDialog(self, self.finished_good)
        self.wait_window(dialog)

        result = dialog.get_result()
        if result:
            self._after_assembly_success()

    def _after_assembly_success(self):
        """Handle successful assembly recording."""
        # Refresh FinishedGood data
        self._reload_finished_good()

        # Refresh history table
        self._load_history()

        # Notify parent
        if self._on_inventory_changed:
            self._on_inventory_changed()

    def _reload_finished_good(self):
        """Reload FinishedGood data from database."""
        updated = self.service_integrator.execute_service_operation(
            operation_name="Reload FinishedGood",
            operation_type=OperationType.READ,
            service_function=lambda: finished_good_service.get_finished_good_by_id(
                self.finished_good.id
            ),
            parent_widget=self,
            error_context="Reloading finished good data",
            suppress_exception=True,
        )

        if updated:
            self.finished_good = updated
            self._update_info_display()

    def _update_info_display(self):
        """Update the info section with current data."""
        self.inventory_label.configure(
            text=str(self.finished_good.inventory_count or 0)
        )
        cost = self.finished_good.total_cost or 0
        self.cost_label.configure(text=f"${cost:.2f}")
