"""
Production Dashboard tab for the Seasonal Baking Tracker.

Provides a unified view of recent production and assembly activity,
with sub-tabs for each type and navigation links to related tabs.

Feature 014 - Production & Assembly Recording UI
"""

import customtkinter as ctk
from datetime import datetime, timedelta

from src.ui.widgets.production_history_table import ProductionHistoryTable
from src.ui.widgets.assembly_history_table import AssemblyHistoryTable
from src.ui.service_integration import get_ui_service_integrator, OperationType
from src.services import batch_production_service, assembly_service
from src.utils.constants import PADDING_MEDIUM, PADDING_LARGE


class ProductionDashboardTab(ctk.CTkFrame):
    """
    Production Dashboard tab showing recent production and assembly runs.

    Features:
    - Sub-tabs for Production Runs and Assembly Runs
    - Recent activity from last 30 days
    - Navigation links to FinishedUnits and FinishedGoods tabs
    """

    def __init__(self, parent, **kwargs):
        """
        Initialize the Production Dashboard tab.

        Args:
            parent: Parent widget
        """
        super().__init__(parent, **kwargs)

        self.service_integrator = get_ui_service_integrator()

        self._setup_ui()
        self.refresh()

        # Grid the frame
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def _setup_ui(self):
        """Set up the tab UI layout."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header with title and navigation links
        self._create_header()

        # Tabview for Production/Assembly sub-tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(
            row=1, column=0, sticky="nsew", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )

        # Add tabs
        self.production_subtab = self.tabview.add("Production Runs")
        self.assembly_subtab = self.tabview.add("Assembly Runs")

        # Configure tab grids
        self.production_subtab.grid_columnconfigure(0, weight=1)
        self.production_subtab.grid_rowconfigure(0, weight=1)
        self.assembly_subtab.grid_columnconfigure(0, weight=1)
        self.assembly_subtab.grid_rowconfigure(0, weight=1)

        # Create tables in each tab
        self._create_production_table()
        self._create_assembly_table()

    def _create_header(self):
        """Create the header section with title and navigation links."""
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(
            row=0, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE
        )

        title = ctk.CTkLabel(
            header_frame,
            text="Production Dashboard",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.pack(side="left")

        # Navigation links frame
        nav_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        nav_frame.pack(side="right")

        ctk.CTkButton(
            nav_frame,
            text="Go to Finished Units",
            command=self._navigate_to_finished_units,
            width=150,
        ).pack(side="left", padx=PADDING_MEDIUM)

        ctk.CTkButton(
            nav_frame,
            text="Go to Finished Goods",
            command=self._navigate_to_finished_goods,
            width=150,
        ).pack(side="left", padx=PADDING_MEDIUM)

        # Refresh button
        ctk.CTkButton(
            nav_frame,
            text="Refresh",
            command=self.refresh,
            width=100,
        ).pack(side="left", padx=PADDING_MEDIUM)

    def _create_production_table(self):
        """Create the production runs table."""
        self.production_table = ProductionHistoryTable(
            self.production_subtab,
            on_row_double_click=self._on_production_double_click,
            height=400,
        )
        self.production_table.grid(
            row=0, column=0, sticky="nsew", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )

    def _create_assembly_table(self):
        """Create the assembly runs table."""
        self.assembly_table = AssemblyHistoryTable(
            self.assembly_subtab,
            on_row_double_click=self._on_assembly_double_click,
            height=400,
        )
        self.assembly_table.grid(
            row=0, column=0, sticky="nsew", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )

    def _load_production_runs(self):
        """Load recent production runs (last 30 days)."""
        start_date = datetime.utcnow() - timedelta(days=30)

        runs = self.service_integrator.execute_service_operation(
            operation_name="Load Recent Production",
            operation_type=OperationType.READ,
            service_function=lambda: batch_production_service.get_production_history(
                start_date=start_date,
                limit=100,
                include_consumptions=False,
            ),
            parent_widget=self,
            error_context="Loading recent production runs",
            suppress_exception=True,
        )

        if runs:
            self.production_table.set_data(runs)
        else:
            self.production_table.clear()

    def _load_assembly_runs(self):
        """Load recent assembly runs (last 30 days)."""
        start_date = datetime.utcnow() - timedelta(days=30)

        runs = self.service_integrator.execute_service_operation(
            operation_name="Load Recent Assembly",
            operation_type=OperationType.READ,
            service_function=lambda: assembly_service.get_assembly_history(
                start_date=start_date,
                limit=100,
                include_consumptions=False,
            ),
            parent_widget=self,
            error_context="Loading recent assembly runs",
            suppress_exception=True,
        )

        if runs:
            self.assembly_table.set_data(runs)
        else:
            self.assembly_table.clear()

    def _on_production_double_click(self, run):
        """Handle double-click on production run row."""
        # Optional: could open detail view for this run
        pass

    def _on_assembly_double_click(self, run):
        """Handle double-click on assembly run row."""
        # Optional: could open detail view for this run
        pass

    def _navigate_to_finished_units(self):
        """Navigate to the Finished Units tab."""
        main_window = self._get_main_window()
        if main_window and hasattr(main_window, "tabview"):
            main_window.tabview.set("Finished Units")

    def _navigate_to_finished_goods(self):
        """Navigate to the Finished Goods tab."""
        # Note: FinishedGoods tab may not exist yet in main_window
        # This is a placeholder for future implementation
        main_window = self._get_main_window()
        if main_window and hasattr(main_window, "switch_to_tab"):
            main_window.switch_to_tab("Finished Goods")

    def _get_main_window(self):
        """Traverse up widget hierarchy to find main window."""
        parent = self.master
        while parent:
            if hasattr(parent, "tabview"):
                return parent
            parent = getattr(parent, "master", None)
        return None

    def refresh(self):
        """Refresh both production and assembly tables."""
        self._load_production_runs()
        self._load_assembly_runs()
