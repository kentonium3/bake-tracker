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

from src.ui.widgets.accordion_step import (
    AccordionStep,
    STATE_ACTIVE,
    STATE_COMPLETED,
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

        # Selection state (populated by later WPs)
        self.food_selections: Dict[int, int] = {}  # {finished_unit_id: quantity}
        self.material_selections: Dict[int, int] = {}  # {material_unit_id: quantity}

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

        # Placeholder labels in content frames (replaced by WP03, WP04, WP05)
        ctk.CTkLabel(
            self.step1.content_frame, text="Food selection UI (WP03)", text_color="gray"
        ).pack(padx=20, pady=20)
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

    # -- Step navigation --

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

    def advance_to_step(self, step_number: int, summary: str = "") -> None:
        """Mark current step completed and advance to the next step.

        Called by step content UIs (WP03, WP04, WP05) when user clicks Continue.

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

    # -- Dialog controls --

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
        self.food_selections.clear()
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

    def get_result(self):
        """Wait for the dialog to close and return the result."""
        self.wait_window()
        return self.result
