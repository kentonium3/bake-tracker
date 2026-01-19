"""EventStatusTab - Per-event progress tracking.

Shows a list of all events with progress columns:
- Event name and date
- Shopping progress %
- Production progress %
- Assembly progress %
- Packaging progress %

Implements FR-028: Event Status tab shows per-event progress tracking.
"""

from typing import Any
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk


class EventStatusTab(ctk.CTkFrame):
    """Tab showing per-event progress tracking.

    Displays all events with their completion status across
    shopping, production, assembly, and packaging stages.
    """

    def __init__(self, master: Any, **kwargs):
        """Initialize EventStatusTab.

        Args:
            master: Parent widget
            **kwargs: Additional arguments passed to CTkFrame
        """
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._create_header()
        self._create_event_list()

    def _create_header(self) -> None:
        """Create header with title and refresh button."""
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        title = ctk.CTkLabel(
            header, text="Event Status Overview", font=ctk.CTkFont(size=16, weight="bold")
        )
        title.pack(side="left")

        refresh_btn = ctk.CTkButton(header, text="Refresh", width=80, command=self.refresh)
        refresh_btn.pack(side="right")

    def _create_event_list(self) -> None:
        """Create the event list with progress columns."""
        # Container frame for treeview
        tree_frame = ctk.CTkFrame(self)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        # Create treeview
        columns = ("event", "date", "shopping", "production", "assembly", "packaging", "overall")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)

        # Configure columns
        column_configs = [
            ("event", "Event", 200),
            ("date", "Date", 100),
            ("shopping", "Shopping", 80),
            ("production", "Production", 80),
            ("assembly", "Assembly", 80),
            ("packaging", "Packaging", 80),
            ("overall", "Overall", 80),
        ]

        for col_id, heading, width in column_configs:
            self.tree.heading(col_id, text=heading)
            self.tree.column(col_id, width=width, anchor="center" if col_id != "event" else "w")

        # Scrollbars
        y_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        # Configure tags for color coding
        self.tree.tag_configure("complete", foreground="green")
        self.tree.tag_configure("in_progress", foreground="orange")
        self.tree.tag_configure("not_started", foreground="gray")

    def refresh(self) -> None:
        """Refresh the event list with current data."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            from src.services.event_service import (
                get_all_events,
                get_event_overall_progress,
            )

            events = get_all_events()

            for event in events:
                try:
                    progress = get_event_overall_progress(event.id)

                    # Calculate overall progress
                    shopping = progress.get("shopping_pct", 0)
                    production = progress.get("production_pct", 0)
                    assembly = progress.get("assembly_pct", 0)
                    packaging = progress.get("packaging_pct", 0)
                    overall = (shopping + production + assembly + packaging) // 4

                    # Determine tag based on overall progress
                    if overall >= 100:
                        tag = "complete"
                    elif overall > 0:
                        tag = "in_progress"
                    else:
                        tag = "not_started"

                    # Format date
                    date_str = str(event.event_date) if event.event_date else "TBD"

                    self.tree.insert(
                        "",
                        "end",
                        values=(
                            event.name,
                            date_str,
                            f"{shopping}%",
                            f"{production}%",
                            f"{assembly}%",
                            f"{packaging}%",
                            f"{overall}%",
                        ),
                        tags=(tag,),
                    )

                except Exception:
                    # Insert with error indication
                    self.tree.insert(
                        "",
                        "end",
                        values=(
                            event.name,
                            str(event.event_date) if event.event_date else "TBD",
                            "?",
                            "?",
                            "?",
                            "?",
                            "?",
                        ),
                        tags=("not_started",),
                    )

        except Exception:
            # Show error in empty state
            pass
