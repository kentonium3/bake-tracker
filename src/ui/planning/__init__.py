"""Planning UI module for the Planning Workspace (Feature 039).

This module provides UI components for the planning workflow:
- PlanningWorkspace: Main container with wizard layout
- PhaseSidebar: Navigation sidebar with phase status indicators
- Phase views: Calculate, Shop, Produce, Assemble views

Usage:
    from src.ui.planning import PlanningWorkspace

    # In a tab or frame
    workspace = PlanningWorkspace(parent, event_id=123)
    workspace.pack(fill="both", expand=True)
"""

from .planning_workspace import PlanningWorkspace
from .phase_sidebar import PhaseSidebar, StatusIndicator, PlanPhase, PhaseStatus
from .calculate_view import CalculateView
from .shop_view import ShopView
from .produce_view import ProduceView
from .assemble_view import AssembleView

__all__ = [
    "PlanningWorkspace",
    "PhaseSidebar",
    "StatusIndicator",
    "PlanPhase",
    "PhaseStatus",
    "CalculateView",
    "ShopView",
    "ProduceView",
    "AssembleView",
]
