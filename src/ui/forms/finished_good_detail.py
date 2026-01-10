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
from src.services import assembly_service, finished_good_service, packaging_service
from src.utils.constants import PADDING_MEDIUM, PADDING_LARGE


class FinishedGoodDetailDialog(ctk.CTkToplevel):
    """
    Modal dialog for displaying FinishedGood details and assembly history.

    Shows:
    - Name
    - Inventory count
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
        header_frame.grid(row=0, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)

        name_label = ctk.CTkLabel(
            header_frame,
            text=self.finished_good.display_name,
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        name_label.pack(anchor="w")

    def _create_info_section(self):
        """Create the info section with inventory."""
        info_frame = ctk.CTkFrame(self)
        info_frame.grid(row=1, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_MEDIUM)
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
        comp_frame.grid(row=3, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_MEDIUM)

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
                # Feature 026: Handle generic packaging with assignment status
                if comp.is_generic:
                    product_name = comp.packaging_product.product_name or "Unknown"
                    name = f"[Pkg] {product_name} (Generic)"
                else:
                    name = f"[Pkg] {comp.packaging_product.display_name}"
            elif comp.material_unit_id and comp.material_unit:
                # Feature 047: MaterialUnit component
                name = f"[MU] {comp.material_unit.name}"
            elif comp.material_id and comp.material:
                # Feature 047: Generic material placeholder
                name = f"[Mat] {comp.material.name} (selection pending)"
            else:
                name = "Unknown component"

            qty = comp.component_quantity or 0

            ctk.CTkLabel(row_frame, text=f"  {qty}x {name}").pack(side="left")

            # Feature 026: Show assignment status and button for generic packaging
            if comp.is_generic and comp.packaging_product_id:
                self._add_assignment_indicator(row_frame, comp)

            # Feature 047: Show pending status for generic materials
            if comp.is_generic and comp.material_id:
                self._add_material_pending_indicator(row_frame, comp)

    def _add_assignment_indicator(self, parent_frame, composition):
        """
        Add assignment status indicator and button for generic compositions.

        Feature 026: Deferred Packaging Decisions

        Args:
            parent_frame: The row frame to add widgets to
            composition: The Composition object with is_generic=True
        """
        try:
            is_assigned = packaging_service.is_fully_assigned(composition.id)

            if is_assigned:
                # Show green checkmark for assigned
                status_label = ctk.CTkLabel(
                    parent_frame,
                    text=" Assigned",
                    text_color="#00AA00",
                    font=ctk.CTkFont(size=11),
                )
                status_label.pack(side="left", padx=(10, 0))
            else:
                # Show orange "Pending" with assign button
                status_label = ctk.CTkLabel(
                    parent_frame,
                    text=" Pending",
                    text_color="#CC7700",
                    font=ctk.CTkFont(size=11),
                )
                status_label.pack(side="left", padx=(10, 0))

                # Assign button
                assign_btn = ctk.CTkButton(
                    parent_frame,
                    text="Assign",
                    width=60,
                    height=24,
                    font=ctk.CTkFont(size=11),
                    command=lambda c=composition: self._open_assignment_dialog(c),
                )
                assign_btn.pack(side="left", padx=(5, 0))
        except Exception:
            # If error checking status, show unknown
            pass

    def _open_assignment_dialog(self, composition):
        """
        Open the packaging assignment dialog for a generic composition.

        Feature 026: Deferred Packaging Decisions

        Args:
            composition: The Composition object to assign materials to
        """
        from src.ui.packaging_assignment_dialog import PackagingAssignmentDialog

        def on_assignment_complete():
            # Refresh the dialog to update assignment status
            self._refresh_composition_display()

        dialog = PackagingAssignmentDialog(
            self,
            composition_id=composition.id,
            on_complete_callback=on_assignment_complete,
        )
        self.wait_window(dialog)

    def _add_material_pending_indicator(self, parent_frame, composition):
        """
        Add pending indicator for generic material compositions.

        Feature 047: Materials Management System

        Generic materials are resolved at assembly time via material_assignments
        parameter. This indicator shows that selection is pending.

        Args:
            parent_frame: The row frame to add widgets to
            composition: The Composition object with is_generic=True and material_id
        """
        # Show orange "Pending" indicator - resolved at assembly time
        status_label = ctk.CTkLabel(
            parent_frame,
            text=" (select at assembly)",
            text_color="#CC7700",
            font=ctk.CTkFont(size=11),
        )
        status_label.pack(side="left", padx=(5, 0))

    def _refresh_composition_display(self):
        """Refresh the composition display after assignment changes."""
        # Find and clear the composition frame
        for widget in self.winfo_children():
            # Look for the scrollable frame that contains compositions
            if isinstance(widget, ctk.CTkScrollableFrame):
                # Clear all children except the header
                for child in widget.winfo_children():
                    child.destroy()
                # Repopulate
                self._populate_composition(widget)
                break

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
        button_frame.grid(row=6, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)

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
        self.inventory_label.configure(text=str(self.finished_good.inventory_count or 0))
