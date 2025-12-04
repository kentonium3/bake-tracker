"""
Event detail window for managing event planning.

Provides comprehensive interface for:
- Assigning packages to recipients
- Viewing recipe needs
- Generating shopping lists
- Event summary and cost tracking
"""

import customtkinter as ctk
from typing import Optional
from tkinter import messagebox

from src.models.event import Event, EventRecipientPackage
from src.services import event_service
from src.services.event_service import AssignmentNotFoundError
from src.utils.constants import (
    PADDING_MEDIUM,
    PADDING_LARGE,
)
from src.ui.widgets.dialogs import (
    show_confirmation,
    show_error,
    show_success,
)
from src.ui.forms.assignment_form import AssignmentFormDialog


class EventDetailWindow(ctk.CTkToplevel):
    """
    Event detail window with tabbed interface.

    Provides comprehensive event planning:
    - Assignments: Assign recipients to packages
    - Recipe Needs: View batch requirements
    - Shopping List: See what to buy
    - Summary: Overview and costs
    """

    def __init__(self, parent, event: Event):
        """
        Initialize the event detail window.

        Args:
            parent: Parent widget
            event: Event to display/edit
        """
        super().__init__(parent)

        self.event = event
        self.selected_assignment: Optional[EventRecipientPackage] = None

        # Configure window
        self.title(f"Event Planning - {event.name}")
        self.geometry("1000x700")

        # Center on parent
        self.transient(parent)

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Title
        self.grid_rowconfigure(1, weight=1)  # Tabview
        self.grid_rowconfigure(2, weight=0)  # Buttons

        # Create title
        self._create_title()

        # Create tabbed interface
        self._create_tabs()

        # Create buttons
        self._create_buttons()

        # Load initial data
        self.refresh()

    def _create_title(self):
        """Create title section."""
        title_frame = ctk.CTkFrame(self)
        title_frame.grid(row=0, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)
        title_frame.grid_columnconfigure(0, weight=1)

        # Event name
        name_label = ctk.CTkLabel(
            title_frame, text=self.event.name, font=ctk.CTkFont(size=20, weight="bold")
        )
        name_label.grid(row=0, column=0, sticky="w", padx=PADDING_MEDIUM)

        # Event details
        details_text = (
            f"Date: {self.event.event_date.strftime('%B %d, %Y')} | Year: {self.event.year}"
        )
        details_label = ctk.CTkLabel(title_frame, text=details_text, font=ctk.CTkFont(size=12))
        details_label.grid(row=1, column=0, sticky="w", padx=PADDING_MEDIUM)

    def _create_tabs(self):
        """Create tabbed interface."""
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(
            row=1, column=0, padx=PADDING_LARGE, pady=(0, PADDING_MEDIUM), sticky="nsew"
        )

        # Add tabs
        self.tabview.add("Assignments")
        self.tabview.add("Recipe Needs")
        self.tabview.add("Shopping List")
        self.tabview.add("Summary")

        # Create tab contents
        self._create_assignments_tab()
        self._create_recipe_needs_tab()
        self._create_shopping_list_tab()
        self._create_summary_tab()

    def _create_assignments_tab(self):
        """Create assignments tab."""
        tab_frame = self.tabview.tab("Assignments")
        tab_frame.grid_columnconfigure(0, weight=1)
        tab_frame.grid_rowconfigure(1, weight=1)

        # Action buttons
        button_frame = ctk.CTkFrame(tab_frame, fg_color="transparent")
        button_frame.grid(row=0, column=0, sticky="ew", pady=(0, PADDING_MEDIUM))

        add_button = ctk.CTkButton(
            button_frame,
            text="➕ Assign Package to Recipient",
            command=self._add_assignment,
            width=200,
        )
        add_button.grid(row=0, column=0, padx=PADDING_MEDIUM)

        self.edit_assignment_button = ctk.CTkButton(
            button_frame,
            text="✏️ Edit",
            command=self._edit_assignment,
            width=100,
            state="disabled",
        )
        self.edit_assignment_button.grid(row=0, column=1, padx=PADDING_MEDIUM)

        self.delete_assignment_button = ctk.CTkButton(
            button_frame,
            text="🗑️ Remove",
            command=self._delete_assignment,
            width=100,
            state="disabled",
            fg_color="darkred",
            hover_color="red",
        )
        self.delete_assignment_button.grid(row=0, column=2, padx=PADDING_MEDIUM)

        # Assignments list (scrollable frame)
        self.assignments_frame = ctk.CTkScrollableFrame(tab_frame, height=450)
        self.assignments_frame.grid(row=1, column=0, sticky="nsew")
        self.assignments_frame.grid_columnconfigure(0, weight=1)

    def _create_recipe_needs_tab(self):
        """Create recipe needs tab."""
        tab_frame = self.tabview.tab("Recipe Needs")
        tab_frame.grid_columnconfigure(0, weight=1)
        tab_frame.grid_rowconfigure(0, weight=1)

        # Recipe needs display (scrollable)
        self.recipe_needs_frame = ctk.CTkScrollableFrame(tab_frame)
        self.recipe_needs_frame.grid(row=0, column=0, sticky="nsew", pady=PADDING_MEDIUM)
        self.recipe_needs_frame.grid_columnconfigure(0, weight=1)

    def _create_shopping_list_tab(self):
        """Create shopping list tab."""
        tab_frame = self.tabview.tab("Shopping List")
        tab_frame.grid_columnconfigure(0, weight=1)
        tab_frame.grid_rowconfigure(1, weight=1)

        # Instructions
        instructions = ctk.CTkLabel(
            tab_frame,
            text="Shopping list compares what you need for this event vs current inventory on hand.",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="gray",
        )
        instructions.grid(row=0, column=0, sticky="w", pady=(0, PADDING_MEDIUM))

        # Shopping list display (scrollable)
        self.shopping_list_frame = ctk.CTkScrollableFrame(tab_frame)
        self.shopping_list_frame.grid(row=1, column=0, sticky="nsew", pady=PADDING_MEDIUM)
        self.shopping_list_frame.grid_columnconfigure(0, weight=1)

    def _create_summary_tab(self):
        """Create summary tab."""
        tab_frame = self.tabview.tab("Summary")
        tab_frame.grid_columnconfigure(0, weight=1)
        tab_frame.grid_rowconfigure(0, weight=1)

        # Summary display (scrollable)
        self.summary_frame = ctk.CTkScrollableFrame(tab_frame)
        self.summary_frame.grid(row=0, column=0, sticky="nsew", pady=PADDING_MEDIUM)
        self.summary_frame.grid_columnconfigure(0, weight=1)

    def _create_buttons(self):
        """Create bottom buttons."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=2, column=0, sticky="ew", padx=PADDING_LARGE, pady=PADDING_LARGE)
        button_frame.grid_columnconfigure(0, weight=1)

        close_button = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self.destroy,
            width=150,
        )
        close_button.grid(row=0, column=0, pady=5)

    def _add_assignment(self):
        """Add a new package assignment to recipient."""
        dialog = AssignmentFormDialog(
            self, event_id=self.event.id, title="Assign Package to Recipient"
        )
        self.wait_window(dialog)

        result = dialog.get_result()
        if result:
            try:
                event_service.assign_package_to_recipient(
                    self.event.id,
                    result["recipient_id"],
                    result["package_id"],
                    result.get("quantity", 1),
                    result.get("notes"),
                )
                show_success("Success", "Package assigned successfully", parent=self)
                self.refresh()
            except Exception as e:
                show_error("Error", f"Failed to assign package: {str(e)}", parent=self)

    def _edit_assignment(self):
        """Edit selected assignment."""
        if not self.selected_assignment:
            return

        dialog = AssignmentFormDialog(
            self,
            event_id=self.event.id,
            assignment=self.selected_assignment,
            title="Edit Assignment",
        )
        self.wait_window(dialog)

        result = dialog.get_result()
        if result:
            try:
                event_service.update_assignment(
                    self.selected_assignment.id,
                    result["package_id"],
                    result.get("quantity", 1),
                    result.get("notes"),
                )
                show_success("Success", "Assignment updated successfully", parent=self)
                self.refresh()
            except Exception as e:
                show_error("Error", f"Failed to update assignment: {str(e)}", parent=self)

    def _delete_assignment(self):
        """Delete selected assignment."""
        if not self.selected_assignment:
            return

        recipient_name = (
            self.selected_assignment.recipient.name
            if self.selected_assignment.recipient
            else "Unknown"
        )

        if not show_confirmation(
            "Confirm Removal", f"Remove package assignment for {recipient_name}?", parent=self
        ):
            return

        try:
            event_service.delete_assignment(self.selected_assignment.id)
            show_success("Success", "Assignment removed successfully", parent=self)
            self.selected_assignment = None
            self.refresh()
        except AssignmentNotFoundError:
            show_error("Error", "Assignment not found", parent=self)
            self.refresh()
        except Exception as e:
            show_error("Error", f"Failed to remove assignment: {str(e)}", parent=self)

    def refresh(self):
        """Refresh all tab contents."""
        self._refresh_assignments()
        self._refresh_recipe_needs()
        self._refresh_shopping_list()
        self._refresh_summary()

    def _refresh_assignments(self):
        """Refresh assignments tab."""
        # Clear existing
        for widget in self.assignments_frame.winfo_children():
            widget.destroy()

        # Get assignments
        try:
            assignments = event_service.get_event_assignments(self.event.id)

            if not assignments:
                label = ctk.CTkLabel(
                    self.assignments_frame,
                    text="No package assignments yet. Click 'Assign Package to Recipient' to get started.",
                    font=ctk.CTkFont(size=12, slant="italic"),
                    text_color="gray",
                )
                label.grid(row=0, column=0, pady=50)
                return

            # Header
            header_frame = ctk.CTkFrame(self.assignments_frame, fg_color=("gray85", "gray25"))
            header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
            header_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

            ctk.CTkLabel(header_frame, text="Recipient", font=ctk.CTkFont(weight="bold")).grid(
                row=0, column=0, padx=10, pady=8
            )
            ctk.CTkLabel(header_frame, text="Package", font=ctk.CTkFont(weight="bold")).grid(
                row=0, column=1, padx=10, pady=8
            )
            ctk.CTkLabel(header_frame, text="Quantity", font=ctk.CTkFont(weight="bold")).grid(
                row=0, column=2, padx=10, pady=8
            )
            ctk.CTkLabel(header_frame, text="Cost", font=ctk.CTkFont(weight="bold")).grid(
                row=0, column=3, padx=10, pady=8
            )

            # Rows
            for idx, assignment in enumerate(assignments, start=1):
                recipient_name = assignment.recipient.name if assignment.recipient else "Unknown"
                package_name = assignment.package.name if assignment.package else "Unknown"
                cost = assignment.calculate_cost()

                row_frame = ctk.CTkFrame(self.assignments_frame, fg_color="transparent")
                row_frame.grid(row=idx, column=0, sticky="ew", pady=2)
                row_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

                # Make row clickable
                def make_click_handler(asgn):
                    return lambda e: self._on_assignment_select(asgn)

                row_frame.bind("<Button-1>", make_click_handler(assignment))

                recipient_label = ctk.CTkLabel(row_frame, text=recipient_name)
                recipient_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
                recipient_label.bind("<Button-1>", make_click_handler(assignment))

                package_label = ctk.CTkLabel(row_frame, text=package_name)
                package_label.grid(row=0, column=1, padx=10, pady=5, sticky="w")
                package_label.bind("<Button-1>", make_click_handler(assignment))

                qty_label = ctk.CTkLabel(row_frame, text=str(assignment.quantity))
                qty_label.grid(row=0, column=2, padx=10, pady=5, sticky="w")
                qty_label.bind("<Button-1>", make_click_handler(assignment))

                cost_label = ctk.CTkLabel(row_frame, text=f"${cost:.2f}")
                cost_label.grid(row=0, column=3, padx=10, pady=5, sticky="w")
                cost_label.bind("<Button-1>", make_click_handler(assignment))

        except Exception as e:
            label = ctk.CTkLabel(
                self.assignments_frame,
                text=f"Error loading assignments: {str(e)}",
                text_color="red",
            )
            label.grid(row=0, column=0, pady=20)

    def _on_assignment_select(self, assignment: EventRecipientPackage):
        """Handle assignment selection."""
        self.selected_assignment = assignment
        self.edit_assignment_button.configure(state="normal")
        self.delete_assignment_button.configure(state="normal")

    def _refresh_recipe_needs(self):
        """Refresh recipe needs tab."""
        # Clear existing
        for widget in self.recipe_needs_frame.winfo_children():
            widget.destroy()

        try:
            recipe_needs = event_service.calculate_recipe_needs(self.event.id)

            if not recipe_needs:
                label = ctk.CTkLabel(
                    self.recipe_needs_frame,
                    text="No recipe needs calculated yet. Add package assignments first.",
                    font=ctk.CTkFont(size=12, slant="italic"),
                    text_color="gray",
                )
                label.grid(row=0, column=0, pady=50)
                return

            # Title
            title_label = ctk.CTkLabel(
                self.recipe_needs_frame,
                text="Recipes Needed for This Event",
                font=ctk.CTkFont(size=16, weight="bold"),
            )
            title_label.grid(row=0, column=0, sticky="w", pady=(0, 15))

            # Recipe list
            row = 1
            for recipe_id, data in recipe_needs.items():
                recipe = data["recipe"]
                batches = data["batches"]
                items = data["items"]

                frame = ctk.CTkFrame(self.recipe_needs_frame, fg_color=("gray90", "gray20"))
                frame.grid(row=row, column=0, sticky="ew", pady=5)
                frame.grid_columnconfigure(0, weight=1)

                name_label = ctk.CTkLabel(
                    frame, text=recipe.name, font=ctk.CTkFont(size=14, weight="bold")
                )
                name_label.grid(row=0, column=0, sticky="w", padx=15, pady=(10, 5))

                details_label = ctk.CTkLabel(
                    frame,
                    text=f"  • Batches needed: {batches:.2f}   |   Total items: {items}",
                    font=ctk.CTkFont(size=12),
                )
                details_label.grid(row=1, column=0, sticky="w", padx=15, pady=(0, 10))

                row += 1

        except Exception as e:
            label = ctk.CTkLabel(
                self.recipe_needs_frame,
                text=f"Error calculating recipe needs: {str(e)}",
                text_color="red",
            )
            label.grid(row=0, column=0, pady=20)

    def _format_single_variant(self, rec, show_preferred=False, recipe_unit="unit"):
        """Format columns for a single variant recommendation.

        Args:
            rec: Variant recommendation dict
            show_preferred: Whether to show [preferred] indicator
            recipe_unit: Unit for cost display (e.g., "cup")

        Returns:
            Tuple of (brand, package_size, cost_unit, est_cost) strings
        """
        if not rec:
            return ("", "", "", "")

        # Brand with [preferred] indicator (T010)
        brand = rec.get("brand", "")
        if show_preferred and rec.get("is_preferred"):
            brand = f"{brand} [preferred]"

        # Package size context: "25 lb bag"
        package_size = rec.get("package_size", "")

        # Cost per recipe unit: "$0.18/cup"
        cost_per_unit = rec.get("cost_per_recipe_unit")
        cost_available = rec.get("cost_available", True)
        if cost_per_unit and cost_available:
            cost_unit = f"${float(cost_per_unit):.2f}/{recipe_unit}"
        elif not cost_available:
            cost_unit = "Cost unknown"
        else:
            cost_unit = "-"

        # Estimated total cost
        total_cost = rec.get("total_cost")
        if total_cost and cost_available:
            est_cost = f"${float(total_cost):.2f}"
        else:
            est_cost = "-"

        return (brand, package_size, cost_unit, est_cost)

    def _refresh_shopping_list(self):
        """Refresh shopping list tab with variant recommendations (Feature 007)."""
        # Clear existing
        for widget in self.shopping_list_frame.winfo_children():
            widget.destroy()

        try:
            # Feature 007: Now returns dict with 'items' key
            shopping_data = event_service.get_shopping_list(self.event.id)

            if not shopping_data or not shopping_data.get("items"):
                label = ctk.CTkLabel(
                    self.shopping_list_frame,
                    text="No shopping needed. Add package assignments first.",
                    font=ctk.CTkFont(size=12, slant="italic"),
                    text_color="gray",
                )
                label.grid(row=0, column=0, pady=50)
                return

            # Title
            title_label = ctk.CTkLabel(
                self.shopping_list_frame,
                text="Shopping List",
                font=ctk.CTkFont(size=16, weight="bold"),
            )
            title_label.grid(row=0, column=0, sticky="w", pady=(0, 15))

            # Header (T008: Extended with variant columns)
            header_frame = ctk.CTkFrame(self.shopping_list_frame, fg_color=("gray85", "gray25"))
            header_frame.grid(row=1, column=0, sticky="ew", pady=(0, 5))
            header_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6, 7), weight=1)

            headers = [
                "Ingredient",
                "Needed",
                "On Hand",
                "To Buy",
                "Variant",
                "Package",
                "Cost/Unit",
                "Est. Cost",
            ]
            for col, header in enumerate(headers):
                ctk.CTkLabel(header_frame, text=header, font=ctk.CTkFont(weight="bold")).grid(
                    row=0, column=col, padx=8, pady=8
                )

            # Shopping items
            row = 2
            for item in shopping_data["items"]:
                shortfall = float(item.get("shortfall", 0))
                if shortfall <= 0:
                    continue  # Skip items we don't need to buy

                ingredient_name = item.get("ingredient_name", "Unknown")
                quantity_needed = float(item.get("quantity_needed", 0))
                quantity_on_hand = float(item.get("quantity_on_hand", 0))
                unit = item.get("unit", "")
                variant_status = item.get("variant_status", "none")

                # Format base columns
                needed_str = f"{quantity_needed:.2f} {unit}"
                on_hand_str = f"{quantity_on_hand:.2f} {unit}"
                to_buy_str = f"{shortfall:.2f} {unit}"

                # Handle different variant statuses (T009, T010, T011)
                if variant_status == "multiple":
                    # T009: Multiple variants - display as stacked rows
                    all_variants = item.get("all_variants", [])
                    if all_variants:
                        # First row with ingredient info
                        first_variant = all_variants[0]
                        v_cols = self._format_single_variant(
                            first_variant, show_preferred=False, recipe_unit=unit
                        )
                        self._create_shopping_row(
                            row,
                            ingredient_name,
                            needed_str,
                            on_hand_str,
                            to_buy_str,
                            *v_cols,
                        )
                        row += 1

                        # Additional variant rows (blank ingredient columns)
                        for variant in all_variants[1:]:
                            v_cols = self._format_single_variant(
                                variant, show_preferred=False, recipe_unit=unit
                            )
                            self._create_shopping_row(row, "", "", "", "", *v_cols, indent=True)
                            row += 1
                    else:
                        # No variants available
                        self._create_shopping_row(
                            row,
                            ingredient_name,
                            needed_str,
                            on_hand_str,
                            to_buy_str,
                            "No variant configured",
                            "",
                            "",
                            "",
                        )
                        row += 1

                elif variant_status == "preferred":
                    # T010: Show preferred variant with indicator
                    rec = item.get("variant_recommendation")
                    v_cols = self._format_single_variant(rec, show_preferred=True, recipe_unit=unit)
                    self._create_shopping_row(
                        row,
                        ingredient_name,
                        needed_str,
                        on_hand_str,
                        to_buy_str,
                        *v_cols,
                    )
                    row += 1

                elif variant_status == "none":
                    # T011: No variant configured fallback
                    self._create_shopping_row(
                        row,
                        ingredient_name,
                        needed_str,
                        on_hand_str,
                        to_buy_str,
                        "No variant configured",
                        "",
                        "",
                        "",
                    )
                    row += 1

                else:
                    # Sufficient or other status - just show basic info
                    self._create_shopping_row(
                        row,
                        ingredient_name,
                        needed_str,
                        on_hand_str,
                        to_buy_str,
                        variant_status.capitalize(),
                        "",
                        "",
                        "",
                    )
                    row += 1

            # T012: Total estimated cost at bottom
            total_estimated_cost = shopping_data.get("total_estimated_cost", 0)
            total_frame = ctk.CTkFrame(self.shopping_list_frame, fg_color=("gray90", "gray20"))
            total_frame.grid(row=row, column=0, sticky="ew", pady=(15, 0))
            total_frame.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                total_frame,
                text=f"Total Estimated Cost: ${float(total_estimated_cost):.2f}",
                font=ctk.CTkFont(size=14, weight="bold"),
            ).grid(row=0, column=0, columnspan=8, padx=15, pady=15)

            # Note about total calculation
            note_label = ctk.CTkLabel(
                total_frame,
                text="* Total includes only items with a preferred variant selected",
                font=ctk.CTkFont(size=10, slant="italic"),
                text_color="gray",
            )
            note_label.grid(row=1, column=0, columnspan=8, padx=15, pady=(0, 10))

        except Exception as e:
            label = ctk.CTkLabel(
                self.shopping_list_frame,
                text=f"Error generating shopping list: {str(e)}",
                text_color="red",
            )
            label.grid(row=0, column=0, pady=20)

    def _create_shopping_row(
        self,
        row,
        ingredient,
        needed,
        on_hand,
        to_buy,
        variant,
        package,
        cost_unit,
        est_cost,
        indent=False,
    ):
        """Create a single row in the shopping list table.

        Args:
            row: Grid row number
            ingredient: Ingredient name (blank for sub-rows)
            needed: Quantity needed string
            on_hand: Quantity on hand string
            to_buy: Quantity to buy string
            variant: Variant brand/status text
            package: Package size text
            cost_unit: Cost per unit text
            est_cost: Estimated total cost text
            indent: Whether this is an indented sub-row (for multiple variants)
        """
        # Different background for sub-rows to show grouping
        if indent:
            fg_color = ("gray95", "gray15")
        else:
            fg_color = "transparent"

        item_frame = ctk.CTkFrame(self.shopping_list_frame, fg_color=fg_color)
        item_frame.grid(row=row, column=0, sticky="ew", pady=1)
        item_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6, 7), weight=1)

        # Add slight indent for sub-rows
        indent_text = "  " if indent else ""

        ctk.CTkLabel(item_frame, text=ingredient).grid(row=0, column=0, padx=8, pady=5, sticky="w")
        ctk.CTkLabel(item_frame, text=needed).grid(row=0, column=1, padx=8, pady=5, sticky="w")
        ctk.CTkLabel(item_frame, text=on_hand).grid(row=0, column=2, padx=8, pady=5, sticky="w")
        ctk.CTkLabel(item_frame, text=to_buy).grid(row=0, column=3, padx=8, pady=5, sticky="w")
        ctk.CTkLabel(item_frame, text=f"{indent_text}{variant}").grid(
            row=0, column=4, padx=8, pady=5, sticky="w"
        )
        ctk.CTkLabel(item_frame, text=package).grid(row=0, column=5, padx=8, pady=5, sticky="w")
        ctk.CTkLabel(item_frame, text=cost_unit).grid(row=0, column=6, padx=8, pady=5, sticky="w")
        ctk.CTkLabel(item_frame, text=est_cost).grid(row=0, column=7, padx=8, pady=5, sticky="w")

    def _refresh_summary(self):
        """Refresh summary tab."""
        # Clear existing
        for widget in self.summary_frame.winfo_children():
            widget.destroy()

        try:
            # Event info
            ctk.CTkLabel(
                self.summary_frame, text="Event Summary", font=ctk.CTkFont(size=18, weight="bold")
            ).grid(row=0, column=0, sticky="w", pady=(0, 20))

            # Get fresh event data
            event = event_service.get_event(self.event.id)

            recipient_count = event.get_recipient_count()
            package_count = event.get_package_count()
            total_cost = event.get_total_cost()

            # Summary details
            info_frame = ctk.CTkFrame(self.summary_frame, fg_color=("gray90", "gray20"))
            info_frame.grid(row=1, column=0, sticky="ew", pady=10)
            info_frame.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                info_frame, text=f"Recipients: {recipient_count}", font=ctk.CTkFont(size=14)
            ).grid(row=0, column=0, sticky="w", padx=20, pady=5)

            ctk.CTkLabel(
                info_frame, text=f"Total Packages: {package_count}", font=ctk.CTkFont(size=14)
            ).grid(row=1, column=0, sticky="w", padx=20, pady=5)

            ctk.CTkLabel(
                info_frame,
                text=f"Estimated Total Cost: ${total_cost:.2f}",
                font=ctk.CTkFont(size=14, weight="bold"),
            ).grid(row=2, column=0, sticky="w", padx=20, pady=(5, 15))

            # Notes
            if event.notes:
                ctk.CTkLabel(
                    self.summary_frame, text="Notes:", font=ctk.CTkFont(size=14, weight="bold")
                ).grid(row=2, column=0, sticky="w", pady=(20, 5))

                notes_label = ctk.CTkLabel(
                    self.summary_frame,
                    text=event.notes,
                    font=ctk.CTkFont(size=12),
                    wraplength=900,
                    justify="left",
                )
                notes_label.grid(row=3, column=0, sticky="w", pady=(0, 10))

        except Exception as e:
            label = ctk.CTkLabel(
                self.summary_frame, text=f"Error loading summary: {str(e)}", text_color="red"
            )
            label.grid(row=0, column=0, pady=20)
