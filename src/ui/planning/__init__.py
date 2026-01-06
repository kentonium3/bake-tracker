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
from .phase_sidebar import PhaseSidebar, StatusIndicator

__all__ = [
    "PlanningWorkspace",
    "PhaseSidebar",
    "StatusIndicator",
]
