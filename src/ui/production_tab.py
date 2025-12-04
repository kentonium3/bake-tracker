"""
Production Tab - Dashboard for production tracking.

Provides:
- Event list with production progress
- Recipe production recording
- Package status management
- Cost comparison display
"""

import customtkinter as ctk
from typing import Optional, Dict, List

from src.services import production_service
from src.utils.constants import PADDING_MEDIUM


class ProductionTab(ctk.CTkFrame):
    """
    Production tracking dashboard tab.

    Displays active events with production progress and allows
    recording production and managing package status.
    """

    def __init__(self, parent, **kwargs):
        """Initialize the production tab."""
        super().__init__(parent, **kwargs)

        self.selected_event_id: Optional[int] = None
        self._recipe_id_map: Dict[str, int] = {}

        self._setup_ui()
        self._load_data()

        # Grid the frame
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def _setup_ui(self):
        """Initialize UI components."""
        # Configure grid - two-column layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        # Left panel - Event list
        self.event_panel = ctk.CTkFrame(self)
        self.event_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Right panel - Detail view
        self.detail_panel = ctk.CTkFrame(self)
        self.detail_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        self._setup_event_panel()
        self._setup_detail_panel()

    def _setup_event_panel(self):
        """Setup event list with progress indicators."""
        # Configure grid
        self.event_panel.grid_columnconfigure(0, weight=1)
        self.event_panel.grid_rowconfigure(2, weight=1)

        # Header
        header = ctk.CTkLabel(
            self.event_panel,
            text="Active Events",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        header.grid(row=0, column=0, pady=PADDING_MEDIUM)

        # Refresh button
        refresh_btn = ctk.CTkButton(
            self.event_panel, text="Refresh", command=self._load_data, width=100
        )
        refresh_btn.grid(row=1, column=0, pady=5)

        # Event list frame (scrollable)
        self.event_list_frame = ctk.CTkScrollableFrame(self.event_panel)
        self.event_list_frame.grid(
            row=2, column=0, sticky="nsew", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
        )

    def _setup_detail_panel(self):
        """Setup detail view placeholder."""
        # Configure grid
        self.detail_panel.grid_columnconfigure(0, weight=1)
        self.detail_panel.grid_rowconfigure(0, weight=1)

        self.detail_label = ctk.CTkLabel(
            self.detail_panel,
            text="Select an event to view details",
            font=ctk.CTkFont(size=14),
        )
        self.detail_label.grid(row=0, column=0, pady=20)

    def _load_data(self):
        """Load dashboard summary data."""
        # Clear existing event cards
        for widget in self.event_list_frame.winfo_children():
            widget.destroy()

        try:
            summaries = production_service.get_dashboard_summary()

            if not summaries:
                no_data = ctk.CTkLabel(
                    self.event_list_frame, text="No events with packages found"
                )
                no_data.pack(pady=20)
                return

            for summary in summaries:
                self._create_event_card(summary)

        except Exception as e:
            error_label = ctk.CTkLabel(
                self.event_list_frame,
                text=f"Error loading data: {str(e)}",
                text_color="red",
            )
            error_label.pack(pady=20)

    def _create_event_card(self, summary: dict):
        """Create a clickable event card with progress."""
        card = ctk.CTkFrame(self.event_list_frame)
        card.pack(fill="x", pady=5, padx=5)

        # Event name and date
        name_label = ctk.CTkLabel(
            card,
            text=f"{summary['event_name']}",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        name_label.pack(anchor="w", padx=10, pady=(10, 0))

        date_label = ctk.CTkLabel(
            card, text=f"Date: {summary['event_date']}", font=ctk.CTkFont(size=12)
        )
        date_label.pack(anchor="w", padx=10)

        # Recipe progress
        recipe_text = (
            f"Recipes: {summary['recipes_complete']}/{summary['recipes_total']}"
        )
        recipe_label = ctk.CTkLabel(card, text=recipe_text)
        recipe_label.pack(anchor="w", padx=10)

        # Package progress
        pkg_text = (
            f"Packages: {summary['packages_delivered']} delivered, "
            f"{summary['packages_assembled']} assembled, "
            f"{summary['packages_pending']} pending"
        )
        pkg_label = ctk.CTkLabel(card, text=pkg_text, font=ctk.CTkFont(size=11))
        pkg_label.pack(anchor="w", padx=10)

        # Cost summary
        actual = float(summary["actual_cost"])
        planned = float(summary["planned_cost"])
        cost_text = f"Cost: ${actual:.2f} / ${planned:.2f} planned"
        cost_label = ctk.CTkLabel(card, text=cost_text, font=ctk.CTkFont(size=11))
        cost_label.pack(anchor="w", padx=10)

        # Completion indicator
        if summary["is_complete"]:
            status_label = ctk.CTkLabel(card, text="COMPLETE", text_color="green")
        else:
            status_label = ctk.CTkLabel(card, text="In Progress", text_color="orange")
        status_label.pack(anchor="w", padx=10, pady=(0, 10))

        # Make card clickable
        event_id = summary["event_id"]
        card.bind("<Button-1>", lambda e, eid=event_id: self._select_event(eid))
        for child in card.winfo_children():
            child.bind("<Button-1>", lambda e, eid=event_id: self._select_event(eid))

    def _select_event(self, event_id: int):
        """Handle event selection."""
        self.selected_event_id = event_id
        self._load_event_detail(event_id)

    def _load_event_detail(self, event_id: int):
        """Load detailed view for selected event."""
        # Clear detail panel
        for widget in self.detail_panel.winfo_children():
            widget.destroy()

        try:
            progress = production_service.get_production_progress(event_id)

            # Event header
            header = ctk.CTkLabel(
                self.detail_panel,
                text=f"Event: {progress['event_name']}",
                font=ctk.CTkFont(size=18, weight="bold"),
            )
            header.pack(pady=PADDING_MEDIUM)

            # Production recording form
            self._create_production_form(event_id, progress)

            # Recipe progress list
            self._create_recipe_progress_list(progress["recipes"])

        except Exception as e:
            error_label = ctk.CTkLabel(
                self.detail_panel, text=f"Error: {str(e)}", text_color="red"
            )
            error_label.pack(pady=20)

    def _create_production_form(self, event_id: int, progress: dict):
        """Create form to record production."""
        form_frame = ctk.CTkFrame(self.detail_panel)
        form_frame.pack(fill="x", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

        form_header = ctk.CTkLabel(
            form_frame,
            text="Record Production",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        form_header.pack(pady=5)

        # Recipe dropdown
        recipe_label = ctk.CTkLabel(form_frame, text="Recipe:")
        recipe_label.pack(anchor="w", padx=10)

        recipe_names = [r["recipe_name"] for r in progress["recipes"]]
        recipe_ids = [r["recipe_id"] for r in progress["recipes"]]

        if not recipe_names:
            no_recipes = ctk.CTkLabel(
                form_frame, text="No recipes found for this event"
            )
            no_recipes.pack(pady=10)
            return

        self.recipe_var = ctk.StringVar(value=recipe_names[0] if recipe_names else "")
        self.recipe_dropdown = ctk.CTkComboBox(
            form_frame, values=recipe_names, variable=self.recipe_var, width=200
        )
        self.recipe_dropdown.pack(padx=10, pady=5)
        self._recipe_id_map = dict(zip(recipe_names, recipe_ids))

        # Batch count
        batch_label = ctk.CTkLabel(form_frame, text="Batches:")
        batch_label.pack(anchor="w", padx=10)

        self.batch_entry = ctk.CTkEntry(form_frame, width=100, placeholder_text="1")
        self.batch_entry.pack(padx=10, pady=5)

        # Record button
        record_btn = ctk.CTkButton(
            form_frame,
            text="Record Production",
            command=lambda: self._record_production(event_id),
        )
        record_btn.pack(pady=PADDING_MEDIUM)

        # Status message
        self.status_label = ctk.CTkLabel(form_frame, text="")
        self.status_label.pack(pady=5)

    def _record_production(self, event_id: int):
        """Handle production recording."""
        try:
            recipe_name = self.recipe_var.get()
            recipe_id = self._recipe_id_map.get(recipe_name)

            if not recipe_id:
                self.status_label.configure(
                    text="Please select a recipe", text_color="red"
                )
                return

            batches_str = self.batch_entry.get()
            batches = int(batches_str) if batches_str else 1

            if batches <= 0:
                self.status_label.configure(
                    text="Batches must be greater than 0", text_color="red"
                )
                return

            # Call service
            record = production_service.record_production(
                event_id=event_id, recipe_id=recipe_id, batches=batches
            )

            self.status_label.configure(
                text=f"Recorded {batches} batch(es). Cost: ${float(record.actual_cost):.2f}",
                text_color="green",
            )

            # Clear the batch entry
            self.batch_entry.delete(0, "end")

            # Refresh data
            self._load_data()
            self._load_event_detail(event_id)

        except ValueError:
            self.status_label.configure(
                text="Please enter a valid number of batches", text_color="red"
            )
        except Exception as e:
            self.status_label.configure(text=f"Error: {str(e)}", text_color="red")

    def _create_recipe_progress_list(self, recipes: List[dict]):
        """Display recipe progress list."""
        list_frame = ctk.CTkFrame(self.detail_panel)
        list_frame.pack(fill="both", expand=True, padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

        header = ctk.CTkLabel(
            list_frame,
            text="Recipe Progress",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        header.pack(pady=5)

        if not recipes:
            no_recipes = ctk.CTkLabel(list_frame, text="No recipes for this event")
            no_recipes.pack(pady=10)
            return

        # Scrollable frame for recipes
        scroll_frame = ctk.CTkScrollableFrame(list_frame, height=200)
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        for recipe in recipes:
            row = ctk.CTkFrame(scroll_frame)
            row.pack(fill="x", pady=2)

            name = ctk.CTkLabel(row, text=recipe["recipe_name"], width=150, anchor="w")
            name.pack(side="left", padx=5)

            progress_text = (
                f"{recipe['batches_produced']}/{recipe['batches_required']} batches"
            )
            progress = ctk.CTkLabel(row, text=progress_text)
            progress.pack(side="left", padx=5)

            if recipe["is_complete"]:
                status = ctk.CTkLabel(row, text="Done", text_color="green")
            else:
                status = ctk.CTkLabel(row, text="Pending", text_color="orange")
            status.pack(side="right", padx=5)

    def refresh(self):
        """Public method to refresh tab data."""
        self._load_data()
        if self.selected_event_id:
            self._load_event_detail(self.selected_event_id)
