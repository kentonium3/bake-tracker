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
from src.services import (
    finished_good_service,
    finished_unit_service,
    material_catalog_service,
    material_unit_service,
)
from src.services.exceptions import CircularReferenceError, ValidationError
from src.services.finished_good_service import InvalidComponentError
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
        self.geometry("700x620")
        self.minsize(600, 600)
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self.result = None
        self._finished_good = finished_good
        self._is_edit_mode = finished_good is not None
        self._finished_good_id = finished_good.id if finished_good else None
        self._has_changes = False
        self._search_debounce_id = None
        self._prev_food_type = ""
        self._prev_food_category = "All Categories"

        # Step completion tracking
        self._step_completed = {1: False, 2: False, 3: False}

        # Food selection state: {component_key: {type, id, display_name, quantity}}
        self._food_selections: Dict[str, Dict] = {}
        # Material selection state: {material_unit_id: {id, name, quantity}}
        self._material_selections: Dict[int, Dict] = {}

        # Food step UI widget references
        self._food_check_vars: Dict[str, ctk.StringVar] = {}
        self._food_qty_entries: Dict[str, ctk.CTkEntry] = {}
        self._food_item_list_frame: Optional[ctk.CTkScrollableFrame] = None
        self._food_error_label: Optional[ctk.CTkLabel] = None

        # Material step UI widget references
        self._mat_check_vars: Dict[int, ctk.StringVar] = {}
        self._mat_qty_entries: Dict[int, ctk.CTkEntry] = {}
        self._mat_item_list_frame: Optional[ctk.CTkScrollableFrame] = None

        # Review step UI widget references
        self._review_summary_frame: Optional[ctk.CTkScrollableFrame] = None
        self._review_total_label: Optional[ctk.CTkLabel] = None
        self.notes_text: Optional[ctk.CTkTextbox] = None
        self._tags_entry: Optional[ctk.CTkEntry] = None
        self._save_error_label: Optional[ctk.CTkLabel] = None

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

        # -- Assembly type selector (Bare / Bundle) --
        self.type_frame = ctk.CTkFrame(self)
        self.type_frame.pack(fill="x", padx=10, pady=(0, 5))

        type_label = ctk.CTkLabel(
            self.type_frame,
            text="Type:",
            font=ctk.CTkFont(weight="bold"),
        )
        type_label.pack(side="left", padx=(10, 5), pady=8)

        self._assembly_type_var = ctk.StringVar(
            value=self._finished_good.assembly_type.get_display_name()
            if self._is_edit_mode and self._finished_good.assembly_type
            else "Bundle"
        )
        self.assembly_type_selector = ctk.CTkSegmentedButton(
            self.type_frame,
            values=[at.get_display_name() for at in AssemblyType],
            variable=self._assembly_type_var,
        )
        self.assembly_type_selector.pack(side="left", padx=(0, 10), pady=8)

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
        self._create_materials_step_content()
        self._create_review_step_content()

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
        """Set initial accordion states based on create/edit mode."""
        if self._is_edit_mode and self._finished_good:
            self._load_existing_data(self._finished_good)
        else:
            self.step1.set_state(STATE_ACTIVE)
            self.step2.set_state(STATE_LOCKED)
            self.step3.set_state(STATE_LOCKED)

    # =========================================================================
    # Edit mode loading
    # =========================================================================

    def _load_existing_data(self, fg) -> None:
        """Load existing FinishedGood data into the builder for editing."""
        # Reload via service to get fresh data with eager-loaded components
        try:
            fg = finished_good_service.get_finished_good_by_id(fg.id)
        except Exception:
            pass  # Fall back to the passed object

        # Populate name
        self.name_entry.insert(0, fg.display_name)

        # Populate notes (strip "Tags: ..." prefix if present)
        if fg.notes and self.notes_text:
            notes = fg.notes
            if notes.startswith("Tags: "):
                lines = notes.split("\n", 1)
                notes = lines[1] if len(lines) > 1 else ""
            self.notes_text.insert("1.0", notes)

        # Populate selections from components
        self._populate_selections_from_components(fg)

        # Mark steps 1 and 2 as completed, open step 3
        food_count = len(self._food_selections)
        mat_count = len(self._material_selections)

        self.step1.mark_completed(
            f"{food_count} item{'s' if food_count != 1 else ''} selected"
        )
        self._step_completed[1] = True

        if mat_count > 0:
            self.step2.mark_completed(
                f"{mat_count} material{'s' if mat_count != 1 else ''} selected"
            )
        else:
            self.step2.mark_completed("No materials")
        self._step_completed[2] = True

        self.step3.expand()
        self._refresh_review_summary()
        self._has_changes = False

    def _populate_selections_from_components(self, fg) -> None:
        """Convert existing Composition records into builder selection state."""
        for comp in fg.components:
            comp_type = comp.component_type
            comp_name = comp.component_name
            qty = int(comp.component_quantity)

            if comp_type == "finished_unit":
                key = f"finished_unit:{comp.finished_unit_id}"
                self._food_selections[key] = {
                    "type": "finished_unit",
                    "id": comp.finished_unit_id,
                    "display_name": comp_name,
                    "quantity": qty,
                }
            elif comp_type == "finished_good":
                key = f"finished_good:{comp.finished_good_id}"
                self._food_selections[key] = {
                    "type": "finished_good",
                    "id": comp.finished_good_id,
                    "display_name": comp_name,
                    "quantity": qty,
                }
            elif comp_type == "material_unit":
                self._material_selections[comp.material_unit_id] = {
                    "id": comp.material_unit_id,
                    "name": comp_name,
                    "quantity": qty,
                }
            # packaging_product type is not managed by builder (legacy)

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

        # Item type filter toggle
        self._food_type_var = ctk.StringVar(value="")
        self._food_type_toggle = ctk.CTkSegmentedButton(
            filter_frame,
            values=["Finished Units", "Existing Assemblies", "Both"],
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
        self._food_search_entry.bind("<KeyRelease>", self._on_search_key_release)

        # -- Scrollable item list --
        self._food_item_list_frame = ctk.CTkScrollableFrame(content, height=180)
        self._food_item_list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # -- Blank-start placeholder (removed when items load) --
        self._food_placeholder_label = ctk.CTkLabel(
            self._food_item_list_frame,
            text="Select item type above to see available items",
            text_color="gray",
            wraplength=400,
        )
        self._food_placeholder_label.pack(padx=20, pady=40)

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
        """Query items matching current filter state.

        Filter mapping:
        - "Finished Units": FinishedUnits only (atomic recipe outputs)
        - "Existing Assemblies": FinishedGoods where assembly_type=BUNDLE
        - "Both": FinishedUnits + BUNDLE FinishedGoods
        - "" (empty): No query (blank start)

        Returns list of dicts with keys: key, id, display_name, category,
        assembly_type, comp_type, comp_id
        """
        type_filter = self._food_type_var.get()
        category_filter = self._food_category_var.get()
        search_text = self._food_search_var.get().strip().lower()

        # Blank start: no filter selected yet
        if not type_filter:
            return []

        items = []

        # Include FinishedUnits when "Finished Units" or "Both"
        if type_filter in ("Finished Units", "Both"):
            try:
                all_units = finished_unit_service.get_all_finished_units(
                    name_search=search_text if search_text else None,
                    category=category_filter if category_filter != "All Categories" else None,
                )
            except Exception:
                all_units = []

            for fu in all_units:
                key = f"finished_unit:{fu.id}"
                items.append({
                    "key": key,
                    "id": fu.id,
                    "display_name": fu.display_name,
                    "category": fu.category or "",
                    "assembly_type": AssemblyType.BARE,
                    "comp_type": "finished_unit",
                    "comp_id": fu.id,
                })

        # Include assembled FinishedGoods when "Existing Assemblies" or "Both"
        if type_filter in ("Existing Assemblies", "Both"):
            try:
                all_fgs = finished_good_service.get_all_finished_goods(
                    name_search=search_text if search_text else None,
                    assembly_type=AssemblyType.BUNDLE,
                )
            except Exception:
                all_fgs = []

            for fg in all_fgs:
                # Self-reference prevention in edit mode
                if self._is_edit_mode and fg.id == self._finished_good_id:
                    continue

                # In-memory category filter for FGs (service doesn't support it)
                if category_filter != "All Categories":
                    fg_category = self._get_fg_category(fg)
                    if fg_category != category_filter:
                        continue

                key = f"finished_good:{fg.id}"
                items.append({
                    "key": key,
                    "id": fg.id,
                    "display_name": fg.display_name,
                    "category": self._get_fg_category(fg),
                    "assembly_type": fg.assembly_type,
                    "comp_type": "finished_good",
                    "comp_id": fg.id,
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

    def _on_search_key_release(self, event=None) -> None:
        """Debounce search input by 300ms."""
        if self._search_debounce_id:
            self.after_cancel(self._search_debounce_id)
        self._search_debounce_id = self.after(300, self._on_food_search_changed)

    def _on_food_search_changed(self) -> None:
        """Handle search text changes (no warning dialog, just re-query)."""
        self._search_debounce_id = None
        type_filter = self._food_type_var.get()
        if not type_filter:
            return
        items = self._query_food_items()
        self._render_food_items(items)

    def _on_food_filter_changed(self) -> None:
        """Re-query and re-render the food item list based on current filters.

        Shows a confirmation dialog if selections exist and the type or category
        filter has changed. If cancelled, reverts to previous filter values.
        """
        current_type = self._food_type_var.get()
        current_category = self._food_category_var.get()

        # Check if selections exist and filter actually changed
        if self._food_selections and (
            current_type != self._prev_food_type
            or current_category != self._prev_food_category
        ):
            confirmed = show_confirmation(
                "Clear Selections?",
                "Changing filters will clear your current selections. Continue?",
                parent=self,
            )
            if not confirmed:
                # Revert to previous values
                self._food_type_var.set(self._prev_food_type)
                self._food_category_var.set(self._prev_food_category)
                return

            # Clear selections on confirm
            self._food_selections.clear()

        # Update previous values
        self._prev_food_type = current_type
        self._prev_food_category = current_category

        # Skip query if no filter selected (blank start)
        if not current_type:
            return

        # Query and render
        items = self._query_food_items()
        self._render_food_items(items)

    def _render_food_items(self, items: List[Dict]) -> None:
        """Render the filtered food items as checkbox rows with quantity entries."""
        # Remove placeholder if present
        if self._food_placeholder_label is not None:
            self._food_placeholder_label.destroy()
            self._food_placeholder_label = None

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
        # Re-render items when going back to a step
        if step_number == 1:
            self._on_food_filter_changed()
        elif step_number == 2:
            self._on_material_filter_changed()
        elif step_number == 3:
            self._refresh_review_summary()

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

        # Populate content when entering a step
        if step_number == 2:
            self._on_material_filter_changed()
        elif step_number == 3:
            self._refresh_review_summary()

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
        self._material_selections.clear()
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

        # Reset food filters to blank-start state
        self._food_category_var.set("All Categories")
        self._food_type_var.set("")
        self._food_search_var.set("")
        self._prev_food_type = ""
        self._prev_food_category = "All Categories"
        self._clear_food_error()

        # Clear items and re-show placeholder
        for widget in self._food_item_list_frame.winfo_children():
            widget.destroy()
        self._food_placeholder_label = ctk.CTkLabel(
            self._food_item_list_frame,
            text="Select item type above to see available items",
            text_color="gray",
            wraplength=400,
        )
        self._food_placeholder_label.pack(padx=20, pady=40)

        # Reset material filters
        self._mat_category_var.set("All Categories")
        self._mat_search_var.set("")

        # Reset review state
        if self.notes_text:
            self.notes_text.delete("1.0", "end")
        if self._tags_entry:
            self._tags_entry.delete(0, "end")
        self._clear_save_error()

    @property
    def food_selections(self) -> Dict[str, Dict]:
        """Return the current food selections dict."""
        return self._food_selections

    @food_selections.setter
    def food_selections(self, value):
        """Allow setting food_selections for backward compatibility."""
        self._food_selections = value

    @property
    def material_selections(self) -> Dict[int, Dict]:
        """Return the current material selections dict."""
        return self._material_selections

    @material_selections.setter
    def material_selections(self, value):
        """Allow setting material_selections."""
        self._material_selections = value

    # =========================================================================
    # Step 2: Materials Selection
    # =========================================================================

    def _create_materials_step_content(self) -> None:
        """Build the materials selection UI inside step 2's content frame."""
        content = self.step2.content_frame

        # -- Filter bar --
        filter_frame = ctk.CTkFrame(content, fg_color="transparent")
        filter_frame.pack(fill="x", padx=5, pady=(5, 2))

        # Category dropdown
        categories = self._get_material_categories()
        self._mat_category_var = ctk.StringVar(value="All Categories")
        self._mat_category_combo = ctk.CTkComboBox(
            filter_frame,
            values=categories,
            variable=self._mat_category_var,
            width=160,
            command=lambda _: self._on_material_filter_changed(),
        )
        self._mat_category_combo.pack(side="left", padx=(0, 5))

        # Search entry
        self._mat_search_var = ctk.StringVar()
        self._mat_search_entry = ctk.CTkEntry(
            filter_frame,
            placeholder_text="Search materials...",
            textvariable=self._mat_search_var,
            width=180,
        )
        self._mat_search_entry.pack(
            side="left", fill="x", expand=True, padx=(5, 0)
        )
        self._mat_search_entry.bind(
            "<KeyRelease>", lambda _: self._on_material_filter_changed()
        )

        # -- Scrollable item list --
        self._mat_item_list_frame = ctk.CTkScrollableFrame(content, height=180)
        self._mat_item_list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # -- Button frame: Skip (left) and Continue (right) --
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(2, 5))

        skip_btn = ctk.CTkButton(
            btn_frame,
            text="Skip - No Materials Needed",
            fg_color="gray",
            command=self._on_materials_skip,
        )
        skip_btn.pack(side="left")

        continue_btn = ctk.CTkButton(
            btn_frame,
            text="Continue",
            command=self._on_materials_continue,
        )
        continue_btn.pack(side="right")

    def _get_material_categories(self) -> List[str]:
        """Get material category names for the dropdown."""
        try:
            categories = material_catalog_service.list_categories()
        except Exception:
            return ["All Categories"]

        names = sorted(cat.name for cat in categories if cat.name)
        return ["All Categories"] + names

    def _query_material_items(self) -> List[Dict]:
        """Query MaterialUnits matching current filter state.

        Returns list of dicts with keys: id, name, category_name, product_name
        """
        category_filter = self._mat_category_var.get()
        search_text = self._mat_search_var.get().strip().lower()

        try:
            units = material_unit_service.list_units(include_relationships=True)
        except Exception:
            return []

        items = []
        for unit in units:
            product = unit.material_product
            if not product or product.is_hidden:
                continue

            material = product.material if product else None
            subcategory = material.subcategory if material else None
            category = subcategory.category if subcategory else None
            category_name = category.name if category else ""

            # Category filter
            if category_filter != "All Categories":
                if category_name != category_filter:
                    continue

            # Search filter
            if search_text and search_text not in unit.name.lower():
                continue

            items.append({
                "id": unit.id,
                "name": unit.name,
                "category_name": category_name,
                "product_name": product.name if product else "",
            })

        return items

    def _on_material_filter_changed(self) -> None:
        """Re-query and re-render the material item list."""
        items = self._query_material_items()
        self._render_material_items(items)

    def _render_material_items(self, items: List[Dict]) -> None:
        """Render filtered MaterialUnits as checkbox rows with quantity entries."""
        for widget in self._mat_item_list_frame.winfo_children():
            widget.destroy()
        self._mat_check_vars.clear()
        self._mat_qty_entries.clear()

        if not items:
            ctk.CTkLabel(
                self._mat_item_list_frame,
                text="No materials match the current filters.",
                text_color="gray",
            ).pack(padx=20, pady=20)
            return

        for item in items:
            unit_id = item["id"]
            row = ctk.CTkFrame(self._mat_item_list_frame, fg_color="transparent")
            row.pack(fill="x", padx=2, pady=1)

            # Checkbox
            is_selected = unit_id in self._material_selections
            var = ctk.StringVar(value="1" if is_selected else "0")
            self._mat_check_vars[unit_id] = var

            cb = ctk.CTkCheckBox(
                row,
                text=item["name"],
                variable=var,
                onvalue="1",
                offvalue="0",
                command=lambda uid=unit_id, i=item: self._on_material_item_toggled(
                    uid, i
                ),
            )
            cb.pack(side="left", fill="x", expand=True, padx=(0, 5))

            # Quantity entry
            qty_entry = ctk.CTkEntry(row, width=60, justify="center")
            qty_entry.pack(side="right", padx=(5, 0))
            self._mat_qty_entries[unit_id] = qty_entry

            if is_selected:
                qty_entry.insert(
                    0, str(self._material_selections[unit_id]["quantity"])
                )
                qty_entry.configure(state="normal")
            else:
                qty_entry.insert(0, "1")
                qty_entry.configure(state="disabled")

            qty_entry.bind(
                "<FocusOut>",
                lambda e, uid=unit_id: self._on_material_qty_changed(uid),
            )
            qty_entry.bind(
                "<KeyRelease>",
                lambda e, uid=unit_id: self._on_material_qty_changed(uid),
            )

    def _on_material_item_toggled(self, unit_id: int, item: Dict) -> None:
        """Handle checkbox toggle for a material item."""
        var = self._mat_check_vars.get(unit_id)
        qty_entry = self._mat_qty_entries.get(unit_id)
        if not var or not qty_entry:
            return

        if var.get() == "1":
            qty_entry.configure(state="normal")
            qty_str = qty_entry.get().strip()
            qty = self._parse_quantity(qty_str)
            self._material_selections[unit_id] = {
                "id": unit_id,
                "name": item["name"],
                "quantity": qty,
            }
        else:
            qty_entry.configure(state="disabled")
            self._material_selections.pop(unit_id, None)

        self._has_changes = True

    def _on_material_qty_changed(self, unit_id: int) -> None:
        """Handle quantity entry change for a material item."""
        if unit_id not in self._material_selections:
            return
        qty_entry = self._mat_qty_entries.get(unit_id)
        if not qty_entry:
            return
        qty_str = qty_entry.get().strip()
        qty = self._parse_quantity(qty_str)
        self._material_selections[unit_id]["quantity"] = qty
        self._has_changes = True

    def _on_materials_skip(self) -> None:
        """Skip materials — advance to step 3 with no materials."""
        self._material_selections.clear()
        self.advance_to_step(3, "No materials")

    def _on_materials_continue(self) -> None:
        """Continue from materials step to step 3."""
        if self._material_selections:
            count = len(self._material_selections)
            summary = f"{count} material{'s' if count != 1 else ''} selected"
        else:
            summary = "No materials"
        self.advance_to_step(3, summary)

    # =========================================================================
    # Step 3: Review & Save
    # =========================================================================

    def _create_review_step_content(self) -> None:
        """Build the review & save UI inside step 3's content frame."""
        content = self.step3.content_frame

        # -- Component summary (scrollable) --
        self._review_summary_frame = ctk.CTkScrollableFrame(
            content, height=140
        )
        self._review_summary_frame.pack(
            fill="both", expand=True, padx=5, pady=(5, 2)
        )

        # -- Total line --
        self._review_total_label = ctk.CTkLabel(
            content, text="", anchor="w"
        )
        self._review_total_label.pack(fill="x", padx=10, pady=(2, 5))

        # -- Notes section --
        notes_label = ctk.CTkLabel(
            content, text="Notes:", font=ctk.CTkFont(weight="bold")
        )
        notes_label.pack(fill="x", padx=10, pady=(5, 0), anchor="w")

        self.notes_text = ctk.CTkTextbox(content, height=50)
        self.notes_text.pack(fill="x", padx=10, pady=(2, 5))

        # -- Tags section --
        tags_label = ctk.CTkLabel(
            content, text="Tags (auto-generated, editable):",
            font=ctk.CTkFont(weight="bold"),
        )
        tags_label.pack(fill="x", padx=10, pady=(5, 0), anchor="w")

        self._tags_entry = ctk.CTkEntry(
            content, placeholder_text="Auto-generated from component names..."
        )
        self._tags_entry.pack(fill="x", padx=10, pady=(2, 5))

        # -- Error label (above save button) --
        self._save_error_label = ctk.CTkLabel(
            content, text="", text_color="red", anchor="w"
        )
        self._save_error_label.pack(fill="x", padx=10, pady=(0, 2))

        # -- Save button --
        save_btn = ctk.CTkButton(
            content,
            text="Save Finished Good",
            command=self._on_save,
        )
        save_btn.pack(anchor="e", padx=10, pady=(2, 10))

    def _refresh_review_summary(self) -> None:
        """Rebuild the review summary display from current selections."""
        # Clear existing summary content
        for widget in self._review_summary_frame.winfo_children():
            widget.destroy()

        # -- Food Items section --
        ctk.CTkLabel(
            self._review_summary_frame,
            text="Food Items",
            font=ctk.CTkFont(weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=5, pady=(5, 2))

        for sel in self._food_selections.values():
            ctk.CTkLabel(
                self._review_summary_frame,
                text=f"  {sel['display_name']} x {sel['quantity']}",
                anchor="w",
            ).pack(fill="x", padx=10, pady=1)

        # -- Separator --
        separator = ctk.CTkFrame(
            self._review_summary_frame, height=2, fg_color="gray50"
        )
        separator.pack(fill="x", padx=5, pady=5)

        # -- Materials section --
        if self._material_selections:
            ctk.CTkLabel(
                self._review_summary_frame,
                text="Materials",
                font=ctk.CTkFont(weight="bold"),
                anchor="w",
            ).pack(fill="x", padx=5, pady=(2, 2))

            for sel in self._material_selections.values():
                ctk.CTkLabel(
                    self._review_summary_frame,
                    text=f"  {sel['name']} x {sel['quantity']}",
                    anchor="w",
                ).pack(fill="x", padx=10, pady=1)
        else:
            ctk.CTkLabel(
                self._review_summary_frame,
                text="No materials",
                text_color="gray",
                anchor="w",
            ).pack(fill="x", padx=5, pady=(2, 2))

        # -- Total line --
        food_count = len(self._food_selections)
        mat_count = len(self._material_selections)
        self._review_total_label.configure(
            text=f"Total: {food_count} food item{'s' if food_count != 1 else ''}"
            f", {mat_count} material{'s' if mat_count != 1 else ''}"
        )

        # -- Auto-generate tags --
        tags = self._generate_tags()
        if self._tags_entry:
            self._tags_entry.delete(0, "end")
            self._tags_entry.insert(0, tags)

        self._clear_save_error()

    # =========================================================================
    # Tags generation
    # =========================================================================

    _SKIP_WORDS = frozenset({
        "the", "and", "or", "a", "an", "of", "in", "for", "with", "x",
    })

    def _generate_tags(self) -> str:
        """Auto-generate tags from component display names."""
        words = set()
        for sel in self._food_selections.values():
            for word in sel["display_name"].lower().split():
                if word not in self._SKIP_WORDS and len(word) > 1:
                    words.add(word)
        for sel in self._material_selections.values():
            for word in sel["name"].lower().split():
                if word not in self._SKIP_WORDS and len(word) > 1:
                    words.add(word)
        return ", ".join(sorted(words))

    # =========================================================================
    # Save operation
    # =========================================================================

    def _build_component_list(self) -> List[Dict]:
        """Convert selections to service component format."""
        components = []
        sort_order = 0
        for sel in self._food_selections.values():
            components.append({
                "type": sel["type"],
                "id": sel["id"],
                "quantity": sel["quantity"],
                "sort_order": sort_order,
            })
            sort_order += 1
        for sel in self._material_selections.values():
            components.append({
                "type": "material_unit",
                "id": sel["id"],
                "quantity": sel["quantity"],
                "sort_order": sort_order,
            })
            sort_order += 1
        return components

    def _build_notes(self) -> Optional[str]:
        """Combine tags and notes text into a single notes string."""
        notes_text = self.notes_text.get("1.0", "end-1c").strip() if self.notes_text else ""
        tags_text = self._tags_entry.get().strip() if self._tags_entry else ""
        parts = []
        if tags_text:
            parts.append(f"Tags: {tags_text}")
        if notes_text:
            parts.append(notes_text)
        combined = "\n".join(parts).strip()
        return combined or None

    def _on_save(self) -> None:
        """Validate and save the FinishedGood via the service."""
        name = self.name_entry.get().strip()
        if not name:
            self._show_save_error("Name is required")
            return

        components = self._build_component_list()
        if not components:
            self._show_save_error("At least one food item is required")
            return

        selected_type = AssemblyType.from_display_name(self._assembly_type_var.get())
        if not selected_type:
            selected_type = AssemblyType.BUNDLE

        try:
            if self._is_edit_mode:
                fg = finished_good_service.update_finished_good(
                    self._finished_good_id,
                    display_name=name,
                    assembly_type=selected_type,
                    components=components,
                    notes=self._build_notes(),
                )
            else:
                fg = finished_good_service.create_finished_good(
                    display_name=name,
                    assembly_type=selected_type,
                    components=components,
                    notes=self._build_notes(),
                )
            self.result = {
                "finished_good_id": fg.id,
                "display_name": fg.display_name,
            }
            self.destroy()
        except ValidationError as e:
            errors = e.errors if hasattr(e, "errors") else [str(e)]
            self._show_save_error("; ".join(str(err) for err in errors))
        except InvalidComponentError:
            self._show_save_error(
                "One or more components are no longer available"
            )
        except CircularReferenceError:
            self._show_save_error("Cannot create circular reference")
        except Exception as e:
            self._show_save_error(f"Save failed: {e}")

    def _show_save_error(self, message: str) -> None:
        """Display error message above the Save button."""
        if self._save_error_label:
            self._save_error_label.configure(text=message)

    def _clear_save_error(self) -> None:
        """Clear save error message."""
        if self._save_error_label:
            self._save_error_label.configure(text="")

    def get_result(self):
        """Wait for the dialog to close and return the result."""
        self.wait_window()
        return self.result
