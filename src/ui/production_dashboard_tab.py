"""
Production Dashboard tab for the Seasonal Baking Tracker.

Provides a unified view of recent production and assembly activity,
with sub-tabs for each type and navigation links to related tabs.

Feature 014 - Production & Assembly Recording UI
Feature 017 - Event Progress tracking added
"""

import customtkinter as ctk
from datetime import datetime, timedelta
from tkinter import messagebox

from src.ui.widgets.production_history_table import ProductionHistoryTable
from src.ui.widgets.assembly_history_table import AssemblyHistoryTable
from src.ui.service_integration import get_ui_service_integrator, OperationType
from src.services import batch_production_service, assembly_service, event_service
from src.utils.constants import PADDING_MEDIUM, PADDING_LARGE


class ProductionDashboardTab(ctk.CTkFrame):
    """
    Production Dashboard tab showing recent production and assembly runs.

    Features:
    - Event progress tracking with production/assembly progress bars (Feature 017)
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
        self.events_map = {}  # Feature 017: Map event names to IDs
        self._current_event_id = None  # Feature 017: Currently selected event

        self._setup_ui()
        self.refresh()

        # Grid the frame
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def _setup_ui(self):
        """Set up the tab UI layout."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # Adjusted for event progress section

        # Header with title and navigation links
        self._create_header()

        # Event Progress Section (Feature 017)
        self._create_event_progress_section()

        # Tabview for Production/Assembly sub-tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(
            row=2, column=0, sticky="nsew", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
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

    # =========================================================================
    # Feature 017: Event Progress Section
    # =========================================================================

    def _create_event_progress_section(self):
        """Create the event progress section (Feature 017)."""
        # Main progress frame
        self.progress_frame = ctk.CTkFrame(self)
        self.progress_frame.grid(
            row=1, column=0, sticky="ew", padx=PADDING_MEDIUM, pady=(0, PADDING_MEDIUM)
        )

        # Event selector row
        selector_row = ctk.CTkFrame(self.progress_frame, fg_color="transparent")
        selector_row.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

        ctk.CTkLabel(
            selector_row,
            text="Event Progress:",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(side="left")

        self.event_var = ctk.StringVar(value="Select Event")
        self.event_selector = ctk.CTkComboBox(
            selector_row,
            variable=self.event_var,
            values=["Select Event"],
            command=self._on_event_selected,
            width=250,
        )
        self.event_selector.pack(side="left", padx=(PADDING_MEDIUM, 0))

        # Production Progress Section
        self.production_progress_frame = ctk.CTkFrame(
            self.progress_frame, fg_color="transparent"
        )
        self.production_progress_frame.pack(fill="x", padx=PADDING_MEDIUM, pady=5)

        ctk.CTkLabel(
            self.production_progress_frame,
            text="Recipe Production:",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w")

        # Container for production progress bars
        self.production_bars_frame = ctk.CTkScrollableFrame(
            self.production_progress_frame, height=100
        )
        self.production_bars_frame.pack(fill="x", pady=5)

        # Assembly Progress Section
        self.assembly_progress_frame = ctk.CTkFrame(
            self.progress_frame, fg_color="transparent"
        )
        self.assembly_progress_frame.pack(fill="x", padx=PADDING_MEDIUM, pady=5)

        ctk.CTkLabel(
            self.assembly_progress_frame,
            text="Finished Good Assembly:",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w")

        # Container for assembly progress bars
        self.assembly_bars_frame = ctk.CTkScrollableFrame(
            self.assembly_progress_frame, height=100
        )
        self.assembly_bars_frame.pack(fill="x", pady=5)

        # Initially show placeholder
        self._show_progress_placeholder()

    def _populate_event_selector(self):
        """Populate event selector with available events."""
        try:
            events = event_service.get_all_events()
            self.events_map = {event.name: event.id for event in events}
            event_names = ["Select Event"] + list(self.events_map.keys())
            self.event_selector.configure(values=event_names)
        except Exception as e:
            print(f"Error loading events: {e}")
            self.events_map = {}

    def _on_event_selected(self, event_name: str):
        """Handle event selection from dropdown."""
        if event_name == "Select Event":
            self._show_progress_placeholder()
            self._current_event_id = None
            return

        event_id = self.events_map.get(event_name)
        if event_id:
            self._current_event_id = event_id
            self._load_event_progress(event_id)

    def _show_progress_placeholder(self):
        """Show placeholder when no event is selected."""
        # Clear production bars
        for widget in self.production_bars_frame.winfo_children():
            widget.destroy()
        ctk.CTkLabel(
            self.production_bars_frame,
            text="Select an event to view production progress",
            text_color="gray",
        ).pack(pady=10)

        # Clear assembly bars
        for widget in self.assembly_bars_frame.winfo_children():
            widget.destroy()
        ctk.CTkLabel(
            self.assembly_bars_frame,
            text="Select an event to view assembly progress",
            text_color="gray",
        ).pack(pady=10)

    def _load_event_progress(self, event_id: int):
        """Load and display progress for selected event."""
        try:
            prod_progress = event_service.get_production_progress(event_id)
            asm_progress = event_service.get_assembly_progress(event_id)

            # Check if any targets exist
            if not prod_progress and not asm_progress:
                self._display_no_targets(event_id)
                return

            self._display_production_progress(prod_progress)
            self._display_assembly_progress(asm_progress)

        except Exception as e:
            print(f"Error loading event progress: {e}")
            self._show_progress_placeholder()

    def _display_production_progress(self, progress_data: list):
        """Display production progress bars."""
        # Clear existing
        for widget in self.production_bars_frame.winfo_children():
            widget.destroy()

        if not progress_data:
            ctk.CTkLabel(
                self.production_bars_frame,
                text="No production targets for this event",
                text_color="gray",
            ).pack(pady=10)
            return

        for item in progress_data:
            row = ctk.CTkFrame(self.production_bars_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)

            # Recipe name
            ctk.CTkLabel(row, text=item["recipe_name"], width=150, anchor="w").pack(
                side="left", padx=5
            )

            # Progress bar - cap at 1.0 for visual
            progress_pct = min(item["progress_pct"], 100) / 100
            progress_bar = ctk.CTkProgressBar(row, width=200)
            progress_bar.set(progress_pct)
            progress_bar.pack(side="left", padx=5)

            # Text label: "2/4 (50%)"
            pct_display = item["progress_pct"]
            label_text = (
                f"{item['produced_batches']}/{item['target_batches']} ({pct_display:.0f}%)"
            )

            # Color code: green if complete
            label_color = "green" if item.get("is_complete") else None

            ctk.CTkLabel(row, text=label_text, text_color=label_color).pack(
                side="left", padx=5
            )

    def _display_assembly_progress(self, progress_data: list):
        """Display assembly progress bars."""
        # Clear existing
        for widget in self.assembly_bars_frame.winfo_children():
            widget.destroy()

        if not progress_data:
            ctk.CTkLabel(
                self.assembly_bars_frame,
                text="No assembly targets for this event",
                text_color="gray",
            ).pack(pady=10)
            return

        for item in progress_data:
            row = ctk.CTkFrame(self.assembly_bars_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)

            # Finished good name
            ctk.CTkLabel(
                row, text=item["finished_good_name"], width=150, anchor="w"
            ).pack(side="left", padx=5)

            # Progress bar
            progress_pct = min(item["progress_pct"], 100) / 100
            progress_bar = ctk.CTkProgressBar(row, width=200)
            progress_bar.set(progress_pct)
            progress_bar.pack(side="left", padx=5)

            # Text label
            pct_display = item["progress_pct"]
            label_text = (
                f"{item['assembled_quantity']}/{item['target_quantity']} ({pct_display:.0f}%)"
            )
            label_color = "green" if item.get("is_complete") else None

            ctk.CTkLabel(row, text=label_text, text_color=label_color).pack(
                side="left", padx=5
            )

    def _display_no_targets(self, event_id: int):
        """Display message when event has no targets."""
        # Clear progress sections
        for widget in self.production_bars_frame.winfo_children():
            widget.destroy()
        for widget in self.assembly_bars_frame.winfo_children():
            widget.destroy()

        # Create centered message in production frame
        no_targets_frame = ctk.CTkFrame(
            self.production_bars_frame, fg_color="transparent"
        )
        no_targets_frame.pack(expand=True, fill="both", pady=10)

        ctk.CTkLabel(
            no_targets_frame,
            text="No production or assembly targets set for this event",
            font=ctk.CTkFont(size=14),
            text_color="gray",
        ).pack(pady=5)

        ctk.CTkButton(
            no_targets_frame,
            text="Set Targets in Event Detail",
            command=lambda: self._navigate_to_event_detail(event_id),
        ).pack(pady=5)

    def _navigate_to_event_detail(self, event_id: int):
        """Navigate to Events tab for target management."""
        main_window = self._get_main_window()
        if main_window and hasattr(main_window, "switch_to_tab"):
            main_window.switch_to_tab("Events")
            messagebox.showinfo(
                "Set Targets",
                "Select the event and click 'View Details' to set production targets.",
            )

    # =========================================================================
    # End Feature 017
    # =========================================================================

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
        """Refresh event selector, progress display, and history tables."""
        # Feature 017: Refresh event selector
        self._populate_event_selector()

        # If an event was selected, refresh its progress
        if self._current_event_id:
            self._load_event_progress(self._current_event_id)

        # Refresh history tables
        self._load_production_runs()
        self._load_assembly_runs()
