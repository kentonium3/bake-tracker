"""
Production Dashboard tab for the Seasonal Baking Tracker.

Provides a unified view of event production status and recent activity,
with sub-tabs for production and assembly history.

Feature 014 - Production & Assembly Recording UI
Feature 017 - Event Progress tracking added
Feature 018 - Multi-Event Production Dashboard (replaces single-event selector)
"""

import logging
import customtkinter as ctk
from datetime import datetime, timedelta
from tkinter import messagebox

from src.ui.widgets.production_history_table import ProductionHistoryTable
from src.ui.widgets.assembly_history_table import AssemblyHistoryTable
from src.ui.widgets.event_card import EventCard
from src.ui.service_integration import get_ui_service_integrator, OperationType
from src.services import batch_production_service, assembly_service, event_service
from src.utils.constants import PADDING_MEDIUM, PADDING_LARGE

logger = logging.getLogger(__name__)


class ProductionDashboardTab(ctk.CTkFrame):
    """
    Production Dashboard tab showing multi-event status board and history.

    Features (Feature 018):
    - Multi-event status board with EventCard widgets
    - Filter by Active & Future, Past, All Events, or date range
    - Quick actions for recording production/assembly
    - Sub-tabs for Production Runs and Assembly Runs history
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
        self._event_cards = []  # Feature 018: Track EventCard widgets
        self._data_loaded = False  # Lazy loading flag

        self._setup_ui()
        # Data will be loaded when tab is first selected (lazy loading)
        # self.refresh()

        # Grid the frame
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def _setup_ui(self):
        """Set up the tab UI layout."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=0)  # Event cards section
        self.grid_rowconfigure(3, weight=1)  # History tables get remaining space

        # Header with title and navigation links
        self._create_header()

        # Filter controls (Feature 018 - replaces single event selector)
        self._create_filter_controls()

        # Event cards container (Feature 018)
        self._create_event_cards_container()

        # Tabview for Production/Assembly sub-tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=3, column=0, sticky="nsew", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

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
        header_frame.grid(row=0, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)

        title = ctk.CTkLabel(
            header_frame,
            text="Production Dashboard",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.pack(side="left")

        # Navigation links frame
        nav_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        nav_frame.pack(side="right")

        # Create Event button (Feature 018)
        ctk.CTkButton(
            nav_frame,
            text="Create Event",
            command=self._on_create_event,
            width=120,
            fg_color="#28A745",  # Green for primary action
        ).pack(side="left", padx=PADDING_MEDIUM)

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

    # =========================================================================
    # Feature 018: Filter Controls
    # =========================================================================

    def _create_filter_controls(self):
        """Create filter controls for event selection (Feature 018)."""
        self.filter_frame = ctk.CTkFrame(self)
        self.filter_frame.grid(
            row=1, column=0, sticky="ew", padx=PADDING_MEDIUM, pady=(0, PADDING_MEDIUM)
        )

        # Filter type dropdown
        filter_row = ctk.CTkFrame(self.filter_frame, fg_color="transparent")
        filter_row.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

        ctk.CTkLabel(
            filter_row,
            text="Show Events:",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left")

        self.filter_type_var = ctk.StringVar(value="Active & Future")
        self.filter_dropdown = ctk.CTkComboBox(
            filter_row,
            variable=self.filter_type_var,
            values=["Active & Future", "Past Events", "All Events"],
            command=self._on_filter_change,
            width=150,
        )
        self.filter_dropdown.pack(side="left", padx=(PADDING_MEDIUM, PADDING_LARGE))

        # Date range controls
        ctk.CTkLabel(filter_row, text="From:").pack(side="left")
        self.date_from_var = ctk.StringVar(value="")
        self.date_from_entry = ctk.CTkEntry(
            filter_row,
            textvariable=self.date_from_var,
            placeholder_text="YYYY-MM-DD",
            width=100,
        )
        self.date_from_entry.pack(side="left", padx=(5, PADDING_MEDIUM))

        ctk.CTkLabel(filter_row, text="To:").pack(side="left")
        self.date_to_var = ctk.StringVar(value="")
        self.date_to_entry = ctk.CTkEntry(
            filter_row,
            textvariable=self.date_to_var,
            placeholder_text="YYYY-MM-DD",
            width=100,
        )
        self.date_to_entry.pack(side="left", padx=(5, PADDING_MEDIUM))

        # Apply date filter button
        ctk.CTkButton(
            filter_row,
            text="Apply",
            width=60,
            command=self._apply_date_filter,
        ).pack(side="left", padx=(0, PADDING_MEDIUM))

        # Clear date filter button
        ctk.CTkButton(
            filter_row,
            text="Clear",
            width=60,
            fg_color="gray50",
            command=self._clear_date_filter,
        ).pack(side="left")

    # =========================================================================
    # Feature 018: Event Cards Container
    # =========================================================================

    def _create_event_cards_container(self):
        """Create scrollable container for EventCard widgets (Feature 018)."""
        # Container frame with label
        cards_section = ctk.CTkFrame(self, fg_color="transparent")
        cards_section.grid(
            row=2, column=0, sticky="nsew", padx=PADDING_MEDIUM, pady=(0, PADDING_MEDIUM)
        )
        cards_section.grid_columnconfigure(0, weight=1)
        cards_section.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            cards_section,
            text="Event Status Board",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, PADDING_MEDIUM))

        # Scrollable frame for cards
        self.cards_container = ctk.CTkScrollableFrame(
            cards_section,
            height=280,
        )
        self.cards_container.grid(row=1, column=0, sticky="nsew")
        self.cards_container.grid_columnconfigure(0, weight=1)

        # Track card widgets for cleanup
        self._event_cards = []

    # =========================================================================
    # Feature 018: Event Cards Rebuild
    # =========================================================================

    def _rebuild_event_cards(self):
        """Rebuild event cards based on current filter (Feature 018)."""
        # Clear existing cards
        for card in self._event_cards:
            card.destroy()
        self._event_cards = []

        # Clear any empty state widgets
        for widget in self.cards_container.winfo_children():
            widget.destroy()

        # Determine filter parameters
        filter_text = self.filter_type_var.get()
        filter_type_map = {
            "Active & Future": "active_future",
            "Past Events": "past",
            "All Events": "all",
        }
        filter_type = filter_type_map.get(filter_text, "active_future")

        # Parse date range
        date_from = self._parse_date(self.date_from_var.get())
        date_to = self._parse_date(self.date_to_var.get())

        # Fetch events with progress
        try:
            events_data = event_service.get_events_with_progress(
                filter_type=filter_type,
                date_from=date_from,
                date_to=date_to,
            )
        except Exception as e:
            logger.error(f"Error loading events: {e}", exc_info=True)
            self._show_error_message(str(e))
            return

        # Handle empty results
        if not events_data:
            self._show_empty_state(filter_type)
            return

        # Create EventCard for each event
        callbacks = self._get_event_card_callbacks()

        for event_data in events_data:
            card = EventCard(
                self.cards_container,
                event_data,
                callbacks,
            )
            card.pack(fill="x", padx=5, pady=5)
            self._event_cards.append(card)

    def _parse_date(self, date_str: str):
        """Parse date string (YYYY-MM-DD) to date object."""
        if not date_str or not date_str.strip():
            return None
        try:
            return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
        except ValueError:
            return None

    # =========================================================================
    # Feature 018: Filter Change Handlers
    # =========================================================================

    def _on_filter_change(self, value: str):
        """Handle filter dropdown change (Feature 018)."""
        self._rebuild_event_cards()

    def _apply_date_filter(self):
        """Apply custom date range filter (Feature 018)."""
        # Validate date format
        date_from = self._parse_date(self.date_from_var.get())
        date_to = self._parse_date(self.date_to_var.get())

        if self.date_from_var.get() and not date_from:
            messagebox.showwarning(
                "Invalid Date",
                "From date must be in YYYY-MM-DD format",
            )
            return

        if self.date_to_var.get() and not date_to:
            messagebox.showwarning(
                "Invalid Date",
                "To date must be in YYYY-MM-DD format",
            )
            return

        # Validate date range order
        if date_from and date_to and date_from > date_to:
            messagebox.showwarning(
                "Invalid Date Range",
                "From date must be before or equal to To date",
            )
            return

        self._rebuild_event_cards()

    def _clear_date_filter(self):
        """Clear date range filter (Feature 018)."""
        self.date_from_var.set("")
        self.date_to_var.set("")
        self._rebuild_event_cards()

    # =========================================================================
    # Feature 018: Quick Action Callbacks
    # =========================================================================

    def _get_event_card_callbacks(self) -> dict:
        """Get callback functions for EventCard quick actions (Feature 018)."""
        return {
            "on_record_production": self._on_record_production,
            "on_record_assembly": self._on_record_assembly,
            "on_shopping_list": self._on_shopping_list,
            "on_event_detail": self._on_event_detail,
            "on_fulfillment_click": self._on_fulfillment_click,
        }

    def _on_record_production(self, event_id: int):
        """Open Record Production dialog with event pre-selected."""
        from src.ui.dialogs.record_production_dialog import RecordProductionDialog

        dialog = RecordProductionDialog(
            self,
            event_id=event_id,
            on_success=self.refresh,
        )
        dialog.grab_set()

    def _on_record_assembly(self, event_id: int):
        """Open Record Assembly dialog with event pre-selected."""
        from src.ui.dialogs.record_assembly_dialog import RecordAssemblyDialog

        dialog = RecordAssemblyDialog(
            self,
            event_id=event_id,
            on_success=self.refresh,
        )
        dialog.grab_set()

    def _on_shopping_list(self, event_id: int):
        """Navigate to shopping list for event."""
        main_window = self._get_main_window()
        if main_window and hasattr(main_window, "switch_to_tab"):
            main_window.switch_to_tab("Reports")
            messagebox.showinfo(
                "Shopping List",
                "Use the Reports tab to generate a shopping list for this event.",
            )

    def _on_event_detail(self, event_id: int):
        """Open Event Detail window for event."""
        from src.ui.event_detail_window import EventDetailWindow

        # Get event name for window title
        event_name = None
        for card in self._event_cards:
            if card.event_data.get("event_id") == event_id:
                event_name = card.event_data.get("event_name")
                break

        EventDetailWindow(
            self,
            event_id=event_id,
            event_name=event_name,
            on_close=self.refresh,
        )

    def _on_fulfillment_click(self, event_id: int, status: str):
        """Handle click on fulfillment status - open event detail."""
        self._on_event_detail(event_id)

    def _on_create_event(self):
        """Open dialog to create new event (Feature 018)."""
        main_window = self._get_main_window()
        if main_window and hasattr(main_window, "switch_to_tab"):
            main_window.switch_to_tab("Events")
            messagebox.showinfo(
                "Create Event",
                "Use the Events tab to create a new event.",
            )

    # =========================================================================
    # Feature 018: Empty State and Error Handlers
    # =========================================================================

    def _show_empty_state(self, filter_type: str):
        """Show empty state message in cards container (Feature 018)."""
        # Clear any existing content
        for widget in self.cards_container.winfo_children():
            widget.destroy()

        empty_frame = ctk.CTkFrame(self.cards_container, fg_color="transparent")
        empty_frame.pack(expand=True, fill="both", pady=50)

        # Different messages based on filter
        if filter_type == "active_future":
            message = "No upcoming events found.\nCreate your first event to get started!"
            show_create = True
        elif filter_type == "past":
            message = "No past events found."
            show_create = False
        else:
            message = "No events found.\nCreate your first event to get started!"
            show_create = True

        ctk.CTkLabel(
            empty_frame,
            text=message,
            font=ctk.CTkFont(size=14),
            text_color="gray60",
            justify="center",
        ).pack(pady=10)

        if show_create:
            ctk.CTkButton(
                empty_frame,
                text="Create Event",
                command=self._on_create_event,
            ).pack(pady=10)

    def _show_error_message(self, error: str):
        """Show error message in cards container (Feature 018)."""
        for widget in self.cards_container.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.cards_container,
            text=f"Error loading events: {error}",
            text_color="red",
        ).pack(pady=20)

    # =========================================================================
    # History Tables (Existing Functionality)
    # =========================================================================

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
        pass

    def _on_assembly_double_click(self, run):
        """Handle double-click on assembly run row."""
        pass

    # =========================================================================
    # Navigation
    # =========================================================================

    def _navigate_to_finished_units(self):
        """Navigate to the Finished Units tab."""
        main_window = self._get_main_window()
        if main_window and hasattr(main_window, "tabview"):
            main_window.tabview.set("Finished Units")

    def _navigate_to_finished_goods(self):
        """Navigate to the Finished Goods tab."""
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
        """Refresh event cards and history tables (Feature 018 enhanced)."""
        # Rebuild event cards
        self._rebuild_event_cards()

        # Refresh history tables
        self._load_production_runs()
        self._load_assembly_runs()
