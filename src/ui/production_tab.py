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

            # Create scrollable container for all detail content
            scroll_container = ctk.CTkScrollableFrame(self.detail_panel)
            scroll_container.pack(fill="both", expand=True, padx=5, pady=5)

            # Event header
            header = ctk.CTkLabel(
                scroll_container,
                text=f"Event: {progress['event_name']}",
                font=ctk.CTkFont(size=18, weight="bold"),
            )
            header.pack(pady=PADDING_MEDIUM)

            # Progress indicators (WP06 T027)
            self._create_progress_indicators(scroll_container, progress)

            # Cost summary (WP06 T025)
            self._create_cost_summary(scroll_container, progress)

            # Production recording form
            self._create_production_form(scroll_container, event_id, progress)

            # Recipe progress list
            self._create_recipe_progress_list(scroll_container, progress["recipes"])

            # Package status controls (WP06 T024)
            self._create_package_status_section(scroll_container, event_id, progress)

        except Exception as e:
            error_label = ctk.CTkLabel(
                self.detail_panel, text=f"Error: {str(e)}", text_color="red"
            )
            error_label.pack(pady=20)

    def _create_production_form(self, parent, event_id: int, progress: dict):
        """Create form to record production."""
        form_frame = ctk.CTkFrame(parent)
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

    def _create_recipe_progress_list(self, parent, recipes: List[dict]):
        """Display recipe progress list."""
        list_frame = ctk.CTkFrame(parent)
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

    # =========================================================================
    # WP06: Progress Indicators, Cost Summary, Package Status
    # =========================================================================

    def _create_progress_indicators(self, parent, progress: dict):
        """Create visual progress bars (T027)."""
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", padx=PADDING_MEDIUM, pady=5)

        # Recipe progress bar
        recipes = progress.get("recipes", [])
        recipes_complete = sum(1 for r in recipes if r.get("is_complete", False))
        recipes_total = len(recipes)
        recipe_pct = recipes_complete / recipes_total if recipes_total > 0 else 0

        recipe_frame = ctk.CTkFrame(section)
        recipe_frame.pack(fill="x", pady=2)

        ctk.CTkLabel(
            recipe_frame, text=f"Recipes: {recipes_complete}/{recipes_total}", width=120
        ).pack(side="left", padx=5)

        recipe_bar = ctk.CTkProgressBar(recipe_frame, width=200)
        recipe_bar.set(recipe_pct)
        recipe_bar.pack(side="left", padx=5)

        if recipe_pct >= 1.0:
            ctk.CTkLabel(recipe_frame, text="Complete", text_color="green").pack(
                side="left", padx=5
            )

        # Package delivery progress
        packages = progress.get("packages", {})
        delivered = packages.get("delivered", 0)
        assembled = packages.get("assembled", 0)
        total = packages.get("total", 0)
        delivery_pct = delivered / total if total > 0 else 0

        delivery_frame = ctk.CTkFrame(section)
        delivery_frame.pack(fill="x", pady=2)

        ctk.CTkLabel(
            delivery_frame, text=f"Delivered: {delivered}/{total}", width=120
        ).pack(side="left", padx=5)

        delivery_bar = ctk.CTkProgressBar(delivery_frame, width=200)
        delivery_bar.set(delivery_pct)
        delivery_bar.pack(side="left", padx=5)

        # Assembly progress (assembled + delivered)
        assembly_frame = ctk.CTkFrame(section)
        assembly_frame.pack(fill="x", pady=2)

        assembled_plus_delivered = assembled + delivered
        assembly_pct = assembled_plus_delivered / total if total > 0 else 0

        ctk.CTkLabel(
            assembly_frame,
            text=f"Assembled: {assembled_plus_delivered}/{total}",
            width=120,
        ).pack(side="left", padx=5)

        assembly_bar = ctk.CTkProgressBar(assembly_frame, width=200)
        assembly_bar.set(assembly_pct)
        assembly_bar.pack(side="left", padx=5)

    def _create_cost_summary(self, parent, progress: dict):
        """Create cost comparison display (T025)."""
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", padx=PADDING_MEDIUM, pady=5)

        header = ctk.CTkLabel(
            section, text="Cost Summary", font=ctk.CTkFont(size=14, weight="bold")
        )
        header.pack(pady=5)

        costs = progress.get("costs", {})
        actual = float(costs.get("actual_total", 0))
        planned = float(costs.get("planned_total", 0))
        variance = actual - planned

        # Actual cost (larger font)
        ctk.CTkLabel(
            section, text=f"Actual Cost: ${actual:.2f}", font=ctk.CTkFont(size=16)
        ).pack()

        # Planned cost
        ctk.CTkLabel(
            section, text=f"Planned Cost: ${planned:.2f}", font=ctk.CTkFont(size=14)
        ).pack()

        # Variance with color coding
        if variance > 0:
            variance_text = f"Over budget: +${variance:.2f}"
            color = "red"
        elif variance < 0:
            variance_text = f"Under budget: ${abs(variance):.2f}"
            color = "green"
        else:
            variance_text = "On budget"
            color = "gray"

        ctk.CTkLabel(
            section,
            text=variance_text,
            text_color=color,
            font=ctk.CTkFont(size=12),
        ).pack()

        # Drill-down button
        event_id = progress.get("event_id")
        if event_id:
            breakdown_btn = ctk.CTkButton(
                section,
                text="View Recipe Breakdown",
                command=lambda: self._show_cost_breakdown(event_id),
                width=150,
            )
            breakdown_btn.pack(pady=5)

    def _show_cost_breakdown(self, event_id: int):
        """Show detailed recipe cost breakdown in a popup (T026)."""
        try:
            breakdown = production_service.get_recipe_cost_breakdown(event_id)

            # Create popup window
            popup = ctk.CTkToplevel(self)
            popup.title("Recipe Cost Breakdown")
            popup.geometry("550x400")
            popup.transient(self)
            popup.grab_set()

            # Header
            header = ctk.CTkLabel(
                popup, text="Cost by Recipe", font=ctk.CTkFont(size=16, weight="bold")
            )
            header.pack(pady=10)

            # Scrollable frame for recipes
            scroll = ctk.CTkScrollableFrame(popup)
            scroll.pack(fill="both", expand=True, padx=10, pady=10)

            # Table header
            header_frame = ctk.CTkFrame(scroll)
            header_frame.pack(fill="x", pady=5)

            ctk.CTkLabel(header_frame, text="Recipe", width=150, anchor="w").pack(
                side="left", padx=2
            )
            ctk.CTkLabel(header_frame, text="Actual", width=70, anchor="e").pack(
                side="left", padx=2
            )
            ctk.CTkLabel(header_frame, text="Planned", width=70, anchor="e").pack(
                side="left", padx=2
            )
            ctk.CTkLabel(header_frame, text="Variance", width=100, anchor="e").pack(
                side="left", padx=2
            )

            # Recipe rows
            for recipe in breakdown:
                row = ctk.CTkFrame(scroll)
                row.pack(fill="x", pady=1)

                actual = float(recipe.get("actual_cost", 0))
                planned = float(recipe.get("planned_cost", 0))
                variance = float(recipe.get("variance", 0))
                variance_pct = recipe.get("variance_percent", 0)

                ctk.CTkLabel(
                    row, text=recipe.get("recipe_name", ""), width=150, anchor="w"
                ).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=f"${actual:.2f}", width=70, anchor="e").pack(
                    side="left", padx=2
                )
                ctk.CTkLabel(row, text=f"${planned:.2f}", width=70, anchor="e").pack(
                    side="left", padx=2
                )

                # Variance with color
                if variance > 0:
                    var_text = f"+${variance:.2f} ({variance_pct:+.1f}%)"
                    color = "red"
                elif variance < 0:
                    var_text = f"${variance:.2f} ({variance_pct:+.1f}%)"
                    color = "green"
                else:
                    var_text = "$0.00 (0%)"
                    color = "gray"

                ctk.CTkLabel(
                    row, text=var_text, width=100, anchor="e", text_color=color
                ).pack(side="left", padx=2)

            # Close button
            close_btn = ctk.CTkButton(popup, text="Close", command=popup.destroy)
            close_btn.pack(pady=10)

        except Exception as e:
            self._show_error(f"Error loading breakdown: {e}")

    def _create_package_status_section(self, parent, event_id: int, progress: dict):
        """Create package status controls (T024)."""
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", padx=PADDING_MEDIUM, pady=5)

        header = ctk.CTkLabel(
            section, text="Package Status", font=ctk.CTkFont(size=14, weight="bold")
        )
        header.pack(pady=5)

        # Get assignments for this event
        try:
            assignments = self._get_event_assignments(event_id)

            if not assignments:
                ctk.CTkLabel(section, text="No package assignments found").pack(pady=5)
                return

            # Scrollable frame for packages
            pkg_scroll = ctk.CTkScrollableFrame(section, height=150)
            pkg_scroll.pack(fill="x", padx=5, pady=5)

            for assignment in assignments:
                self._create_package_row(pkg_scroll, assignment, event_id)

        except Exception as e:
            error = ctk.CTkLabel(section, text=f"Error: {e}", text_color="red")
            error.pack()

    def _get_event_assignments(self, event_id: int) -> List[dict]:
        """Get package assignments for an event."""
        from src.services.database import session_scope
        from src.models import EventRecipientPackage

        with session_scope() as session:
            assignments = (
                session.query(EventRecipientPackage)
                .filter(EventRecipientPackage.event_id == event_id)
                .all()
            )

            result = []
            for a in assignments:
                result.append(
                    {
                        "id": a.id,
                        "recipient_name": a.recipient.name if a.recipient else "Unknown",
                        "package_name": a.package.name if a.package else "Unknown",
                        "status": a.status.value if a.status else "pending",
                        "delivered_to": a.delivered_to,
                    }
                )
            return result

    def _create_package_row(self, parent, assignment: dict, event_id: int):
        """Create a row for one package assignment."""
        row = ctk.CTkFrame(parent)
        row.pack(fill="x", pady=2, padx=5)

        # Recipient and package name
        info_text = f"{assignment['recipient_name']} - {assignment['package_name']}"
        info = ctk.CTkLabel(row, text=info_text, width=200, anchor="w")
        info.pack(side="left", padx=5)

        # Current status
        status = assignment["status"]
        status_label = ctk.CTkLabel(row, text=status.upper(), width=80)

        if status == "delivered":
            status_label.configure(text_color="green")
        elif status == "assembled":
            status_label.configure(text_color="blue")
        else:
            status_label.configure(text_color="gray")

        status_label.pack(side="left", padx=5)

        # Action buttons based on current status
        if status == "pending":
            assemble_btn = ctk.CTkButton(
                row,
                text="Mark Assembled",
                width=120,
                command=lambda: self._update_status(
                    assignment["id"], "assembled", event_id
                ),
            )
            assemble_btn.pack(side="right", padx=2)

        elif status == "assembled":
            deliver_btn = ctk.CTkButton(
                row,
                text="Mark Delivered",
                width=120,
                command=lambda: self._show_delivery_dialog(assignment["id"], event_id),
            )
            deliver_btn.pack(side="right", padx=2)

        elif status == "delivered":
            if assignment.get("delivered_to"):
                note = ctk.CTkLabel(
                    row,
                    text=f"({assignment['delivered_to']})",
                    font=ctk.CTkFont(size=10),
                )
                note.pack(side="right", padx=5)

    def _update_status(self, assignment_id: int, new_status: str, event_id: int):
        """Update package status via service."""
        from src.models import PackageStatus
        from src.services.production_service import (
            IncompleteProductionError,
            InvalidStatusTransitionError,
        )

        status_map = {
            "pending": PackageStatus.PENDING,
            "assembled": PackageStatus.ASSEMBLED,
            "delivered": PackageStatus.DELIVERED,
        }

        try:
            production_service.update_package_status(
                assignment_id=assignment_id, new_status=status_map[new_status]
            )

            # Refresh view
            self._load_data()
            self._load_event_detail(event_id)

        except IncompleteProductionError as e:
            missing = ", ".join(r["recipe_name"] for r in e.missing_recipes)
            self._show_error(f"Cannot assemble: Missing production for {missing}")

        except InvalidStatusTransitionError as e:
            self._show_error(
                f"Cannot change from {e.current.value} to {e.target.value}"
            )

        except Exception as e:
            self._show_error(str(e))

    def _show_delivery_dialog(self, assignment_id: int, event_id: int):
        """Show dialog to optionally add delivery note."""
        dialog = ctk.CTkInputDialog(
            title="Mark as Delivered",
            text="Optional delivery note (e.g., 'Left with neighbor'):",
        )
        note = dialog.get_input()

        from src.models import PackageStatus

        try:
            production_service.update_package_status(
                assignment_id=assignment_id,
                new_status=PackageStatus.DELIVERED,
                delivered_to=note if note else None,
            )
            self._load_data()
            self._load_event_detail(event_id)
        except Exception as e:
            self._show_error(str(e))

    def _show_error(self, message: str):
        """Show error message to user."""
        from tkinter import messagebox

        messagebox.showerror("Error", message, parent=self)
