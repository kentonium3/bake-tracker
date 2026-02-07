"""
Finished Good Builder dialog - multi-step wizard for creating/editing FinishedGoods.

Three-step accordion workflow:
  Step 1: Food Selection (FinishedUnits)
  Step 2: Materials Selection (MaterialUnits)
  Step 3: Review & Save

Feature 097: Finished Goods Builder UI
"""

from typing import Dict, List, Optional

import customtkinter as ctk

from src.models.assembly_type import AssemblyType
from src.services import finished_good_service, finished_unit_service
from src.ui.widgets.accordion_step import (
    AccordionStep,
    STATE_ACTIVE,
    STATE_LOCKED,
)
from src.ui.widgets.dialogs import show_confirmation


class FinishedGoodBuilderDialog(ctk.CTkToplevel):
    """Multi-step builder dialog for creating or editing a FinishedGood.

    Uses three AccordionStep instances with mutual exclusion and sequential
    progression. Only one step is expanded at a time.
    """

    def __init__(self, parent, finished_good=None):
        super().__init__(parent)

        self.title(
            "Create Finished Good"
            if not finished_good
            else f"Edit: {finished_good.display_name}"
        )
        self.geometry("700x750")
        self.minsize(600, 600)
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self.result = None
        self._finished_good = finished_good
        self._is_edit_mode = finished_good is not None
        self._has_changes = False

        # Step completion tracking
        self._step_completed = {1: False, 2: False, 3: False}

        # Food selection state: {component_key: {type, id, display_name, quantity}}
        self._food_selections: Dict[str, Dict] = {}
        # Material selection state (populated by WP04)
        self.material_selections: Dict[int, int] = {}

        # Food step UI widget references
        self._food_check_vars: Dict[str, ctk.StringVar] = {}
        self._food_qty_entries: Dict[str, ctk.CTkEntry] = {}
        self._food_item_list_frame: Optional[ctk.CTkScrollableFrame] = None
        self._food_error_label: Optional[ctk.CTkLabel] = None

        self._create_widgets()
        self._set_initial_state()
        self._center_on_parent(parent)

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _center_on_parent(self, parent) -> None:
        """Center the dialog on its parent window."""
        self.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        dialog_w = self.winfo_width()
        dialog_h = self.winfo_height()
        x = parent_x + (parent_w - dialog_w) // 2
        y = parent_y + (parent_h - dialog_h) // 2
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self) -> None:
        """Build the dialog layout: name entry, accordion steps, buttons."""
        # -- Name entry frame (always visible at top) --
        self.name_frame = ctk.CTkFrame(self)
        self.name_frame.pack(fill="x", padx=10, pady=(10, 5))

        name_label = ctk.CTkLabel(
            self.name_frame,
            text="Name:",
            font=ctk.CTkFont(weight="bold"),
        )
        name_label.pack(side="left", padx=(10, 5), pady=8)

        self.name_entry = ctk.CTkEntry(
            self.name_frame,
            placeholder_text="Enter finished good name...",
        )
        self.name_entry.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=8)
        self.name_entry.bind("<KeyRelease>", self._on_name_change)

        # -- Scrollable frame for accordion steps --
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # -- Three accordion steps --
        self.step1 = AccordionStep(
            self.scroll_frame,
            step_number=1,
            title="Food Selection",
            on_change_click=self._on_step_change,
        )
        self.step1.pack(fill="x", padx=5, pady=(5, 2))

        self.step2 = AccordionStep(
            self.scroll_frame,
            step_number=2,
            title="Materials",
            on_change_click=self._on_step_change,
        )
        self.step2.pack(fill="x", padx=5, pady=2)

        self.step3 = AccordionStep(
            self.scroll_frame,
            step_number=3,
            title="Review & Save",
            on_change_click=self._on_step_change,
        )
        self.step3.pack(fill="x", padx=5, pady=(2, 5))

        # -- Populate step content frames --
        self._create_food_step_content()

        # Placeholder labels for steps 2 and 3 (replaced by WP04, WP05)
        ctk.CTkLabel(
            self.step2.content_frame, text="Materials selection UI (WP04)", text_color="gray"
        ).pack(padx=20, pady=20)
        ctk.CTkLabel(
            self.step3.content_frame, text="Review & Save UI (WP05)", text_color="gray"
        ).pack(padx=20, pady=20)

        # -- Bottom button frame --
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.pack(fill="x", padx=10, pady=(5, 10))

        self.start_over_btn = ctk.CTkButton(
            self.button_frame,
            text="Start Over",
            fg_color="gray",
            width=100,
            command=self._on_start_over,
        )
        self.start_over_btn.pack(side="left", padx=5)

        cancel_btn = ctk.CTkButton(
            self.button_frame,
            text="Cancel",
            fg_color="gray",
            width=100,
            command=self._on_cancel,
        )
        cancel_btn.pack(side="right", padx=5)

    def _set_initial_state(self) -> None:
        """Set initial accordion states: step 1 active, steps 2-3 locked."""
        self.step1.set_state(STATE_ACTIVE)
        self.step2.set_state(STATE_LOCKED)
        self.step3.set_state(STATE_LOCKED)

        if self._is_edit_mode and self._finished_good:
            self.name_entry.insert(0, self._finished_good.display_name)

        # Load initial food items
        self._on_food_filter_changed()

    # =========================================================================
    # Step 1: Food Selection
    # =========================================================================

    def _create_food_step_content(self) -> None:
        """Build the food selection UI inside step 1's content frame."""
        content = self.step1.content_frame

        # -- Filter bar --
        filter_frame = ctk.CTkFrame(content, fg_color="transparent")
        filter_frame.pack(fill="x", padx=5, pady=(5, 2))

        # Category dropdown
        categories = self._get_distinct_categories()
        self._food_category_var = ctk.StringVar(value="All Categories")
        self._food_category_combo = ctk.CTkComboBox(
            filter_frame,
            values=categories,
            variable=self._food_category_var,
            width=160,
            command=lambda _: self._on_food_filter_changed(),
        )
        self._food_category_combo.pack(side="left", padx=(0, 5))

        # Bare/Assembly toggle
        self._food_type_var = ctk.StringVar(value="All")
        self._food_type_toggle = ctk.CTkSegmentedButton(
            filter_frame,
            values=["All", "Bare Items Only"],
            variable=self._food_type_var,
            command=lambda _: self._on_food_filter_changed(),
        )
        self._food_type_toggle.pack(side="left", padx=5)

        # Search entry
        self._food_search_var = ctk.StringVar()
        self._food_search_entry = ctk.CTkEntry(
            filter_frame,
            placeholder_text="Search by name...",
            textvariable=self._food_search_var,
            width=150,
        )
        self._food_search_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
        self._food_search_entry.bind("<KeyRelease>", lambda _: self._on_food_filter_changed())

        # -- Scrollable item list --
        self._food_item_list_frame = ctk.CTkScrollableFrame(content, height=250)
        self._food_item_list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # -- Error label (hidden by default) --
        self._food_error_label = ctk.CTkLabel(
            content, text="", text_color="red", anchor="w"
        )
        self._food_error_label.pack(fill="x", padx=10, pady=(0, 2))

        # -- Continue button --
        continue_btn = ctk.CTkButton(
            content,
            text="Continue",
            command=self._on_food_continue,
        )
        continue_btn.pack(anchor="e", padx=10, pady=(2, 5))

    def _get_distinct_categories(self) -> List[str]:
        """Get distinct category values from FinishedUnits for the dropdown."""
        try:
            units = finished_unit_service.get_all_finished_units()
        except Exception:
            return ["All Categories"]

        categories = sorted(
            {u.category for u in units if u.category}
        )
        return ["All Categories"] + categories

    def _query_food_items(self) -> List[Dict]:
        """Query FinishedGoods matching current filter state.

        Returns list of dicts with keys: key, id, display_name, category,
        assembly_type, comp_type, comp_id
        """
        category_filter = self._food_category_var.get()
        type_filter = self._food_type_var.get()
        search_text = self._food_search_var.get().strip().lower()

        try:
            all_fgs = finished_good_service.get_all_finished_goods()
        except Exception:
            return []

        items = []
        for fg in all_fgs:
            # Determine if bare or assembly
            is_bare = fg.assembly_type == AssemblyType.BARE

            # Type filter
            if type_filter == "Bare Items Only" and not is_bare:
                continue

            # Search filter
            if search_text and search_text not in fg.display_name.lower():
                continue

            # Category filter
            if category_filter != "All Categories":
                fg_category = self._get_fg_category(fg)
                if fg_category != category_filter:
                    continue

            # Determine component type and ID for Composition
            if is_bare and fg.components:
                # BARE wraps a single FinishedUnit
                fu_comp = next(
                    (c for c in fg.components if c.finished_unit_id),
                    None,
                )
                if fu_comp:
                    comp_type = "finished_unit"
                    comp_id = fu_comp.finished_unit_id
                else:
                    comp_type = "finished_good"
                    comp_id = fg.id
            else:
                comp_type = "finished_good"
                comp_id = fg.id

            key = f"{comp_type}:{comp_id}"
            items.append({
                "key": key,
                "id": fg.id,
                "display_name": fg.display_name,
                "category": self._get_fg_category(fg),
                "assembly_type": fg.assembly_type,
                "comp_type": comp_type,
                "comp_id": comp_id,
            })

        return items

    def _get_fg_category(self, fg) -> str:
        """Get the category for a FinishedGood.

        For BARE items: category from the wrapped FinishedUnit.
        For assemblies: 'Assemblies' group.
        """
        if fg.assembly_type == AssemblyType.BARE and fg.components:
            for comp in fg.components:
                if comp.finished_unit_id and comp.finished_unit_component:
                    return comp.finished_unit_component.category or ""
        return "Assemblies"

    def _on_food_filter_changed(self) -> None:
        """Re-query and re-render the food item list based on current filters."""
        items = self._query_food_items()
        self._render_food_items(items)

    def _render_food_items(self, items: List[Dict]) -> None:
        """Render the filtered food items as checkbox rows with quantity entries."""
        # Clear existing children
        for widget in self._food_item_list_frame.winfo_children():
            widget.destroy()
        self._food_check_vars.clear()
        self._food_qty_entries.clear()

        if not items:
            ctk.CTkLabel(
                self._food_item_list_frame,
                text="No items match the current filters.",
                text_color="gray",
            ).pack(padx=20, pady=20)
            return

        for item in items:
            key = item["key"]
            row = ctk.CTkFrame(self._food_item_list_frame, fg_color="transparent")
            row.pack(fill="x", padx=2, pady=1)

            # Checkbox
            is_selected = key in self._food_selections
            var = ctk.StringVar(value="1" if is_selected else "0")
            self._food_check_vars[key] = var

            cb = ctk.CTkCheckBox(
                row,
                text=item["display_name"],
                variable=var,
                onvalue="1",
                offvalue="0",
                command=lambda k=key, i=item: self._on_food_item_toggled(k, i),
            )
            cb.pack(side="left", fill="x", expand=True, padx=(0, 5))

            # Quantity entry
            qty_entry = ctk.CTkEntry(row, width=60, justify="center")
            qty_entry.pack(side="right", padx=(5, 0))
            self._food_qty_entries[key] = qty_entry

            if is_selected:
                qty_entry.insert(0, str(self._food_selections[key]["quantity"]))
                qty_entry.configure(state="normal")
            else:
                qty_entry.insert(0, "1")
                qty_entry.configure(state="disabled")

            qty_entry.bind(
                "<FocusOut>",
                lambda e, k=key: self._on_food_qty_changed(k),
            )
            qty_entry.bind(
                "<KeyRelease>",
                lambda e, k=key: self._on_food_qty_changed(k),
            )

    def _on_food_item_toggled(self, key: str, item: Dict) -> None:
        """Handle checkbox toggle for a food item."""
        var = self._food_check_vars.get(key)
        qty_entry = self._food_qty_entries.get(key)
        if not var or not qty_entry:
            return

        if var.get() == "1":
            # Selected
            qty_entry.configure(state="normal")
            qty_str = qty_entry.get().strip()
            qty = self._parse_quantity(qty_str)
            self._food_selections[key] = {
                "type": item["comp_type"],
                "id": item["comp_id"],
                "display_name": item["display_name"],
                "quantity": qty,
            }
        else:
            # Deselected
            qty_entry.configure(state="disabled")
            self._food_selections.pop(key, None)

        self._has_changes = True
        self._clear_food_error()

    def _on_food_qty_changed(self, key: str) -> None:
        """Handle quantity entry change for a food item."""
        if key not in self._food_selections:
            return
        qty_entry = self._food_qty_entries.get(key)
        if not qty_entry:
            return
        qty_str = qty_entry.get().strip()
        qty = self._parse_quantity(qty_str)
        self._food_selections[key]["quantity"] = qty
        self._has_changes = True

    @staticmethod
    def _parse_quantity(qty_str: str) -> int:
        """Parse a quantity string, returning 1 for invalid input."""
        try:
            val = int(qty_str)
            return max(1, min(val, 999))
        except (ValueError, TypeError):
            return 1

    def _on_food_continue(self) -> None:
        """Validate food selections and advance to step 2."""
        # Clean up: remove items with zero quantity
        to_remove = [
            k for k, v in self._food_selections.items() if v["quantity"] < 1
        ]
        for k in to_remove:
            self._food_selections.pop(k)

        if not self._food_selections:
            self._show_food_error("Select at least one food item")
            return

        count = len(self._food_selections)
        summary = f"{count} item{'s' if count != 1 else ''} selected"
        self.advance_to_step(2, summary)

    def _show_food_error(self, message: str) -> None:
        """Show an error message below the food list."""
        if self._food_error_label:
            self._food_error_label.configure(text=message)

    def _clear_food_error(self) -> None:
        """Clear the food error message."""
        if self._food_error_label:
            self._food_error_label.configure(text="")

    # =========================================================================
    # Step navigation
    # =========================================================================

    def _get_step(self, step_number: int) -> AccordionStep:
        """Return the AccordionStep for the given step number."""
        return {1: self.step1, 2: self.step2, 3: self.step3}[step_number]

    def _get_all_steps(self) -> List[AccordionStep]:
        """Return all accordion steps in order."""
        return [self.step1, self.step2, self.step3]

    def _collapse_all_steps(self) -> None:
        """Collapse all accordion steps."""
        for step in self._get_all_steps():
            step.collapse()

    def _get_current_step(self) -> Optional[int]:
        """Return the step number currently active (expanded), or None."""
        for step in self._get_all_steps():
            if step.state == STATE_ACTIVE:
                return step.step_number
        return None

    def _on_step_change(self, step_number: int) -> None:
        """Handle 'Change' button click: navigate back to a completed step."""
        self._collapse_all_steps()
        step = self._get_step(step_number)
        step.expand()
        # Re-render food items when going back to step 1
        if step_number == 1:
            self._on_food_filter_changed()

    def advance_to_step(self, step_number: int, summary: str = "") -> None:
        """Mark current step completed and advance to the next step.

        Args:
            step_number: The step to advance TO (2 or 3)
            summary: Summary text for the step being completed
        """
        current = step_number - 1
        if current >= 1:
            current_step = self._get_step(current)
            current_step.mark_completed(summary)
            self._step_completed[current] = True

        target_step = self._get_step(step_number)
        target_step.expand()
        self._has_changes = True

    # =========================================================================
    # Dialog controls
    # =========================================================================

    def _on_name_change(self, event=None) -> None:
        """Track that the name field has been modified."""
        self._has_changes = True

    def _on_cancel(self) -> None:
        """Handle Cancel / window close."""
        if self._has_changes:
            confirmed = show_confirmation(
                "Discard Changes?",
                "You have unsaved changes. Discard them?",
                parent=self,
            )
            if not confirmed:
                return
        self.result = None
        self.destroy()

    def _on_start_over(self) -> None:
        """Reset all state and return to step 1."""
        self._food_selections.clear()
        self.material_selections.clear()
        self._step_completed = {1: False, 2: False, 3: False}
        self._has_changes = False
        self.name_entry.delete(0, "end")

        self._collapse_all_steps()
        self.step1.set_state(STATE_ACTIVE)
        self.step1.set_summary("")
        self.step2.set_state(STATE_LOCKED)
        self.step2.set_summary("")
        self.step3.set_state(STATE_LOCKED)
        self.step3.set_summary("")

        # Reset food filters and re-render
        self._food_category_var.set("All Categories")
        self._food_type_var.set("All")
        self._food_search_var.set("")
        self._clear_food_error()
        self._on_food_filter_changed()

    @property
    def food_selections(self) -> Dict[str, Dict]:
        """Return the current food selections dict."""
        return self._food_selections

    @food_selections.setter
    def food_selections(self, value):
        """Allow setting food_selections for backward compatibility."""
        self._food_selections = value

    def get_result(self):
        """Wait for the dialog to close and return the result."""
        self.wait_window()
        return self.result
