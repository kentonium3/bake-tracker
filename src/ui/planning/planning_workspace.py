"""PlanningWorkspace - Main container for the Planning Workspace.

Provides a wizard-style layout with sidebar navigation and phase-specific
content views for the planning workflow.

Implements:
- FR-021: Planning Workspace shows calculated batch requirements
- FR-034-036: Flexible navigation with contextual warnings
- FR-040: Stale plan warning banner
- SC-011: User can see shopping, production, and assembly status in one workspace
"""

from typing import Any, Optional
import customtkinter as ctk

from src.services.planning import (
    calculate_plan,
    check_staleness,
    get_plan_summary,
    PlanningError,
    EventNotConfiguredError,
    EventNotFoundError,
)
from .phase_sidebar import PhaseSidebar, PlanPhase, PhaseStatus
from .calculate_view import CalculateView
from .shop_view import ShopView
from .produce_view import ProduceView
from .assemble_view import AssembleView


class StalePlanBanner(ctk.CTkFrame):
    """Warning banner shown when the plan may be outdated.

    Implements FR-040: Stale plan warning banner.
    """

    def __init__(
        self,
        parent: Any,
        on_recalculate: callable,
        **kwargs
    ):
        """Initialize StalePlanBanner.

        Args:
            parent: Parent widget
            on_recalculate: Callback when Recalculate button is clicked
            **kwargs: Additional arguments passed to CTkFrame
        """
        # Yellow/warning background
        kwargs.setdefault("fg_color", ("#FFF3CD", "#664D03"))
        kwargs.setdefault("corner_radius", 6)
        super().__init__(parent, **kwargs)

        self.on_recalculate = on_recalculate
        self._reason = ""

        self._setup_ui()

        # Start hidden
        self.grid_remove()

    def _setup_ui(self) -> None:
        """Set up the banner UI."""
        self.grid_columnconfigure(1, weight=1)

        # Warning icon
        icon = ctk.CTkLabel(
            self,
            text="\u26a0",  # Warning sign
            font=ctk.CTkFont(size=18),
            text_color=("#856404", "#FFC107"),
        )
        icon.grid(row=0, column=0, padx=(10, 5), pady=8)

        # Message
        self.message_label = ctk.CTkLabel(
            self,
            text="Plan may be outdated",
            font=ctk.CTkFont(size=13),
            text_color=("#856404", "#FFC107"),
            anchor="w",
        )
        self.message_label.grid(row=0, column=1, sticky="ew", padx=5, pady=8)

        # Recalculate button
        recalc_btn = ctk.CTkButton(
            self,
            text="Recalculate",
            command=self._handle_recalculate,
            width=100,
            height=28,
            fg_color=("#856404", "#FFC107"),
            text_color=("white", "black"),
            hover_color=("#6c5303", "#E0A800"),
        )
        recalc_btn.grid(row=0, column=2, padx=10, pady=8)

    def _handle_recalculate(self) -> None:
        """Handle Recalculate button click."""
        self.on_recalculate()

    def show(self, reason: str = "") -> None:
        """Show the banner with an optional reason.

        Args:
            reason: Reason the plan is stale
        """
        self._reason = reason
        if reason:
            self.message_label.configure(text=f"Plan may be outdated: {reason}")
        else:
            self.message_label.configure(text="Plan may be outdated")
        self.grid()

    def hide(self) -> None:
        """Hide the banner."""
        self.grid_remove()


class PrerequisiteWarningDialog(ctk.CTkToplevel):
    """Dialog shown when navigating to a phase with incomplete prerequisites.

    Implements FR-034-035: Warn on incomplete prerequisites.
    """

    def __init__(
        self,
        parent: Any,
        message: str,
        target_phase: PlanPhase,
        prerequisite_phase: PlanPhase,
        on_continue: callable,
        on_go_to_prerequisite: callable,
    ):
        """Initialize PrerequisiteWarningDialog.

        Args:
            parent: Parent widget
            message: Warning message to display
            target_phase: The phase user is trying to navigate to
            prerequisite_phase: The prerequisite phase that's incomplete
            on_continue: Callback when user chooses to continue anyway
            on_go_to_prerequisite: Callback when user chooses to go to prerequisite
        """
        super().__init__(parent)

        self.on_continue = on_continue
        self.on_go_to_prerequisite = on_go_to_prerequisite

        # Configure window
        self.title("Incomplete Prerequisites")
        self.geometry("400x180")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - 400) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - 180) // 2
        self.geometry(f"+{x}+{y}")

        self._setup_ui(message, prerequisite_phase)

    def _setup_ui(self, message: str, prerequisite_phase: PlanPhase) -> None:
        """Set up the dialog UI."""
        self.grid_columnconfigure(0, weight=1)

        # Warning icon and message
        icon_frame = ctk.CTkFrame(self, fg_color="transparent")
        icon_frame.grid(row=0, column=0, pady=(20, 10), padx=20, sticky="ew")
        icon_frame.grid_columnconfigure(1, weight=1)

        icon = ctk.CTkLabel(
            icon_frame,
            text="\u26a0",  # Warning sign
            font=ctk.CTkFont(size=32),
            text_color="#FFD700",
        )
        icon.grid(row=0, column=0, padx=(0, 15))

        msg_label = ctk.CTkLabel(
            icon_frame,
            text=message,
            font=ctk.CTkFont(size=14),
            wraplength=300,
            justify="left",
        )
        msg_label.grid(row=0, column=1, sticky="w")

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=1, column=0, pady=(10, 20), padx=20)

        # Phase name mapping
        phase_names = {
            PlanPhase.CALCULATE: "Calculate",
            PlanPhase.SHOP: "Shop",
            PlanPhase.PRODUCE: "Produce",
            PlanPhase.ASSEMBLE: "Assemble",
        }

        go_to_btn = ctk.CTkButton(
            btn_frame,
            text=f"Go to {phase_names[prerequisite_phase]}",
            command=self._handle_go_to,
            width=140,
        )
        go_to_btn.pack(side="left", padx=5)

        continue_btn = ctk.CTkButton(
            btn_frame,
            text="Continue Anyway",
            command=self._handle_continue,
            width=140,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
        )
        continue_btn.pack(side="left", padx=5)

    def _handle_continue(self) -> None:
        """Handle Continue Anyway button."""
        self.destroy()
        self.on_continue()

    def _handle_go_to(self) -> None:
        """Handle Go to prerequisite button."""
        self.destroy()
        self.on_go_to_prerequisite()


class PlaceholderView(ctk.CTkFrame):
    """Placeholder view for phases not yet implemented (WP08)."""

    def __init__(self, parent: Any, phase: PlanPhase, **kwargs):
        """Initialize PlaceholderView.

        Args:
            parent: Parent widget
            phase: The phase this placeholder represents
            **kwargs: Additional arguments passed to CTkFrame
        """
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)

        self.phase = phase

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Phase name mapping
        phase_names = {
            PlanPhase.CALCULATE: "Calculate Requirements",
            PlanPhase.SHOP: "Shopping List",
            PlanPhase.PRODUCE: "Production Tracking",
            PlanPhase.ASSEMBLE: "Assembly Checklist",
        }

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.place(relx=0.5, rely=0.5, anchor="center")

        title = ctk.CTkLabel(
            container,
            text=phase_names[phase],
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title.pack(pady=(0, 15))

        subtitle = ctk.CTkLabel(
            container,
            text="Phase view implementation coming in WP08",
            font=ctk.CTkFont(size=14),
            text_color="gray",
        )
        subtitle.pack()


class PlanningWorkspace(ctk.CTkFrame):
    """Main container for the Planning Workspace.

    Provides a wizard-style layout with:
    - Left sidebar (20%): Phase navigation with status indicators
    - Right content (80%): Phase-specific views

    The workspace orchestrates the planning workflow through
    Calculate -> Shop -> Produce -> Assemble phases.
    """

    def __init__(
        self,
        parent: Any,
        event_id: Optional[int] = None,
        **kwargs
    ):
        """Initialize PlanningWorkspace.

        Args:
            parent: Parent widget
            event_id: Optional event ID to load immediately
            **kwargs: Additional arguments passed to CTkFrame
        """
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)

        self.event_id = event_id
        self.current_phase = PlanPhase.CALCULATE
        self._views: dict[PlanPhase, ctk.CTkFrame] = {}
        self._plan_data: dict = {}

        self._setup_layout()
        self._setup_views()

        # Load initial data if event_id provided
        if event_id:
            self.after(100, self._load_plan_data)

    def _setup_layout(self) -> None:
        """Set up the main layout with sidebar and content area."""
        self.grid_columnconfigure(0, weight=0, minsize=180)  # Sidebar
        self.grid_columnconfigure(1, weight=1)  # Content
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = PhaseSidebar(
            self,
            on_phase_select=self._handle_phase_select,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # Content container
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.content_container.grid_columnconfigure(0, weight=1)
        self.content_container.grid_rowconfigure(1, weight=1)

        # Stale plan banner (row 0)
        self.stale_banner = StalePlanBanner(
            self.content_container,
            on_recalculate=self._handle_recalculate,
        )
        self.stale_banner.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        # View container (row 1)
        self.view_container = ctk.CTkFrame(
            self.content_container,
            fg_color="transparent"
        )
        self.view_container.grid(row=1, column=0, sticky="nsew")
        self.view_container.grid_columnconfigure(0, weight=1)
        self.view_container.grid_rowconfigure(0, weight=1)

    def _setup_views(self) -> None:
        """Set up phase views with real implementations."""
        # Calculate view
        self._views[PlanPhase.CALCULATE] = CalculateView(
            self.view_container,
            event_id=self.event_id,
            on_calculated=self._on_plan_calculated,
        )
        self._views[PlanPhase.CALCULATE].grid(row=0, column=0, sticky="nsew")
        self._views[PlanPhase.CALCULATE].grid_remove()

        # Shop view
        self._views[PlanPhase.SHOP] = ShopView(
            self.view_container,
            event_id=self.event_id,
        )
        self._views[PlanPhase.SHOP].grid(row=0, column=0, sticky="nsew")
        self._views[PlanPhase.SHOP].grid_remove()

        # Produce view
        self._views[PlanPhase.PRODUCE] = ProduceView(
            self.view_container,
            event_id=self.event_id,
        )
        self._views[PlanPhase.PRODUCE].grid(row=0, column=0, sticky="nsew")
        self._views[PlanPhase.PRODUCE].grid_remove()

        # Assemble view
        self._views[PlanPhase.ASSEMBLE] = AssembleView(
            self.view_container,
            event_id=self.event_id,
        )
        self._views[PlanPhase.ASSEMBLE].grid(row=0, column=0, sticky="nsew")
        self._views[PlanPhase.ASSEMBLE].grid_remove()

        # Show initial phase
        self._show_view(PlanPhase.CALCULATE)
        self.sidebar.update_active_phase(PlanPhase.CALCULATE)

    def _on_plan_calculated(self) -> None:
        """Handle plan calculation completion - refresh other views."""
        # Refresh shopping list since plan changed
        if PlanPhase.SHOP in self._views:
            self._views[PlanPhase.SHOP].refresh()
        # Update phase statuses
        self._load_plan_data()

    def _show_view(self, phase: PlanPhase) -> None:
        """Show the view for a specific phase.

        Args:
            phase: The phase to show
        """
        # Hide all views
        for view in self._views.values():
            view.grid_remove()

        # Show requested view
        if phase in self._views:
            self._views[phase].grid()

    def _handle_phase_select(self, phase: PlanPhase) -> None:
        """Handle phase selection from sidebar.

        Args:
            phase: The selected phase
        """
        # Check prerequisites and warn if incomplete
        warning = self._check_prerequisites(phase)
        if warning:
            prereq_phase = self._get_prerequisite_phase(phase)
            PrerequisiteWarningDialog(
                self,
                message=warning,
                target_phase=phase,
                prerequisite_phase=prereq_phase,
                on_continue=lambda: self.switch_to_phase(phase),
                on_go_to_prerequisite=lambda: self.switch_to_phase(prereq_phase),
            )
        else:
            self.switch_to_phase(phase)

    def switch_to_phase(self, phase: PlanPhase) -> None:
        """Switch to a specific phase.

        Args:
            phase: The phase to switch to
        """
        self.current_phase = phase
        self._show_view(phase)
        self.sidebar.update_active_phase(phase)

    def _check_prerequisites(self, target_phase: PlanPhase) -> Optional[str]:
        """Check if prerequisites are complete for the target phase.

        Args:
            target_phase: The phase to check prerequisites for

        Returns:
            Warning message if prerequisites incomplete, None otherwise
        """
        if not self.event_id:
            if target_phase != PlanPhase.CALCULATE:
                return "No event selected. Select an event first."
            return None

        if target_phase == PlanPhase.SHOP:
            if not self._has_calculated_plan():
                return "No plan calculated yet. Calculate first?"
        elif target_phase == PlanPhase.PRODUCE:
            if not self._is_shopping_complete():
                return "Shopping not marked complete. Continue anyway?"
        elif target_phase == PlanPhase.ASSEMBLE:
            if not self._is_production_started():
                return "Production not started. Continue anyway?"

        return None

    def _get_prerequisite_phase(self, target_phase: PlanPhase) -> PlanPhase:
        """Get the prerequisite phase for a target phase.

        Args:
            target_phase: The target phase

        Returns:
            The prerequisite phase
        """
        prereqs = {
            PlanPhase.SHOP: PlanPhase.CALCULATE,
            PlanPhase.PRODUCE: PlanPhase.SHOP,
            PlanPhase.ASSEMBLE: PlanPhase.PRODUCE,
        }
        return prereqs.get(target_phase, PlanPhase.CALCULATE)

    def _has_calculated_plan(self) -> bool:
        """Check if a plan has been calculated."""
        return bool(self._plan_data.get("plan_id"))

    def _is_shopping_complete(self) -> bool:
        """Check if shopping is complete."""
        # Will be implemented when plan data includes shopping status
        return self._plan_data.get("shopping_complete", False)

    def _is_production_started(self) -> bool:
        """Check if production has started."""
        # Will be implemented when progress tracking is wired
        return self._plan_data.get("production_started", False)

    def _load_plan_data(self) -> None:
        """Load plan data for the current event."""
        if not self.event_id:
            return

        try:
            # Check staleness
            is_stale, reason = check_staleness(self.event_id)
            if is_stale:
                self.stale_banner.show(reason or "")
            else:
                self.stale_banner.hide()

            # Get plan summary for status updates
            try:
                summary = get_plan_summary(self.event_id)
                self._update_phase_statuses(summary)
            except PlanningError:
                # No plan yet, that's ok
                pass

        except EventNotFoundError:
            # Event doesn't exist
            self._show_error("Event not found")
        except EventNotConfiguredError:
            # Event needs output_mode set
            self._show_info("Event needs configuration before planning")
        except Exception as e:
            # Unexpected error
            self._show_error(str(e))

    def _update_phase_statuses(self, summary) -> None:
        """Update phase status indicators from plan summary.

        Args:
            summary: PlanSummary from planning service
        """
        # Map service PhaseStatus to sidebar PhaseStatus
        from src.services.planning import PhaseStatus as ServicePhaseStatus
        status_map = {
            ServicePhaseStatus.NOT_STARTED: PhaseStatus.NOT_STARTED,
            ServicePhaseStatus.IN_PROGRESS: PhaseStatus.IN_PROGRESS,
            ServicePhaseStatus.COMPLETE: PhaseStatus.COMPLETE,
        }

        statuses = {}
        for phase, service_status in summary.phase_statuses.items():
            # Convert service PlanPhase to sidebar PlanPhase
            phase_map = {
                "requirements": PlanPhase.CALCULATE,
                "shopping": PlanPhase.SHOP,
                "production": PlanPhase.PRODUCE,
                "assembly": PlanPhase.ASSEMBLE,
            }
            sidebar_phase = phase_map.get(phase.value if hasattr(phase, 'value') else phase)
            if sidebar_phase:
                statuses[sidebar_phase] = status_map.get(
                    service_status, PhaseStatus.NOT_STARTED
                )

        self.sidebar.update_all_statuses(statuses)

    def _handle_recalculate(self) -> None:
        """Handle recalculate button click."""
        if not self.event_id:
            return

        try:
            self._plan_data = calculate_plan(self.event_id, force_recalculate=True)
            self.stale_banner.hide()
            self._load_plan_data()  # Refresh statuses
        except PlanningError as e:
            self._show_error(str(e))

    def _show_error(self, message: str) -> None:
        """Show an error message (simple implementation).

        Args:
            message: Error message
        """
        # For now, just print - could be enhanced with a toast notification
        print(f"Planning error: {message}")

    def _show_info(self, message: str) -> None:
        """Show an info message (simple implementation).

        Args:
            message: Info message
        """
        print(f"Planning info: {message}")

    def set_event(self, event_id: int) -> None:
        """Set the event to work with.

        Args:
            event_id: Event database ID
        """
        self.event_id = event_id
        self._plan_data = {}

        # Update all views with new event
        for phase, view in self._views.items():
            if hasattr(view, 'set_event'):
                view.set_event(event_id)

        self._load_plan_data()
        # Reset to Calculate phase
        self.switch_to_phase(PlanPhase.CALCULATE)

    def refresh(self) -> None:
        """Refresh the workspace data."""
        self._load_plan_data()
        # Refresh current view
        if self.current_phase in self._views:
            view = self._views[self.current_phase]
            if hasattr(view, 'refresh'):
                view.refresh()
