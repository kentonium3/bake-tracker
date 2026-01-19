"""MakeMode - Mode container for production workflow.

MAKE mode contains 4 tabs for managing production activities:
- Production Runs: Record and track batch production
- Assembly: Create finished goods from finished units
- Packaging: Create gift packages for recipients
- Recipients: Manage gift package recipients

Implements User Story 6: MAKE Mode for Production Workflow (Priority P2)
"""

from typing import Any, TYPE_CHECKING
import customtkinter as ctk

from src.ui.base.base_mode import BaseMode
from src.ui.dashboards.make_dashboard import MakeDashboard
from src.ui.tabs.assembly_tab import AssemblyTab
from src.ui.tabs.packaging_tab import PackagingTab

if TYPE_CHECKING:
    from src.ui.production_dashboard_tab import ProductionDashboardTab
    from src.ui.recipients_tab import RecipientsTab


class MakeMode(BaseMode):
    """Mode container for production workflow.

    Provides access to production, assembly, packaging, and recipient
    management with a dashboard showing production statistics.
    """

    def __init__(self, master: Any, **kwargs):
        """Initialize MakeMode.

        Args:
            master: Parent widget
            **kwargs: Additional arguments passed to BaseMode
        """
        super().__init__(master, name="MAKE", **kwargs)

        # Tab references
        self.production_tab: "ProductionDashboardTab" = None
        self.assembly_tab: AssemblyTab = None
        self.packaging_tab: PackagingTab = None
        self.recipients_tab: "RecipientsTab" = None

        # Set up dashboard and tabs
        self.setup_dashboard()
        self.setup_tabs()

    def setup_dashboard(self) -> None:
        """Set up the MAKE dashboard with production stats (FR-010)."""
        dashboard = MakeDashboard(self)
        self.set_dashboard(dashboard)

    def setup_tabs(self) -> None:
        """Set up all 4 tabs for MAKE mode."""
        from src.ui.production_dashboard_tab import ProductionDashboardTab
        from src.ui.recipients_tab import RecipientsTab

        self.create_tabview()

        # Production Runs tab (existing functionality)
        production_frame = self.tabview.add("Production Runs")
        production_frame.grid_columnconfigure(0, weight=1)
        production_frame.grid_rowconfigure(0, weight=1)
        self.production_tab = ProductionDashboardTab(production_frame)
        self._tab_widgets["Production Runs"] = self.production_tab

        # Assembly tab (placeholder - FR-025)
        assembly_frame = self.tabview.add("Assembly")
        assembly_frame.grid_columnconfigure(0, weight=1)
        assembly_frame.grid_rowconfigure(0, weight=1)
        self.assembly_tab = AssemblyTab(assembly_frame)
        self.assembly_tab.grid(row=0, column=0, sticky="nsew")
        self._tab_widgets["Assembly"] = self.assembly_tab

        # Packaging tab (placeholder - FR-026)
        packaging_frame = self.tabview.add("Packaging")
        packaging_frame.grid_columnconfigure(0, weight=1)
        packaging_frame.grid_rowconfigure(0, weight=1)
        self.packaging_tab = PackagingTab(packaging_frame)
        self.packaging_tab.grid(row=0, column=0, sticky="nsew")
        self._tab_widgets["Packaging"] = self.packaging_tab

        # Recipients tab (existing functionality)
        recipients_frame = self.tabview.add("Recipients")
        recipients_frame.grid_columnconfigure(0, weight=1)
        recipients_frame.grid_rowconfigure(0, weight=1)
        self.recipients_tab = RecipientsTab(recipients_frame)
        self._tab_widgets["Recipients"] = self.recipients_tab

    def activate(self) -> None:
        """Called when MAKE mode becomes active."""
        super().activate()
        # Lazy load data for production tab on first activation
        if self.production_tab:
            if not getattr(self.production_tab, "_data_loaded", False):
                self.production_tab._data_loaded = True
                self.after(10, self.production_tab.refresh)

    def refresh_all_tabs(self) -> None:
        """Refresh all tabs in MAKE mode."""
        if self.production_tab:
            self.production_tab.refresh()
        if self.assembly_tab:
            self.assembly_tab.refresh()
        if self.packaging_tab:
            self.packaging_tab.refresh()
        if self.recipients_tab:
            self.recipients_tab.refresh()
