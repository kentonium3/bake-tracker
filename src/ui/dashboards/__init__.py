"""Dashboard widgets for mode architecture.

This module provides dashboard components for each mode:
- BaseDashboard: Abstract base class for all dashboards
- CatalogDashboard: Dashboard for CATALOG mode
- ObserveDashboard: Dashboard for OBSERVE mode
- PlanDashboard: Dashboard for PLAN mode
- MakeDashboard: Dashboard for MAKE mode
- PurchaseDashboard: Dashboard for PURCHASE mode
"""

from .base_dashboard import BaseDashboard
from .catalog_dashboard import CatalogDashboard
from .observe_dashboard import ObserveDashboard
from .plan_dashboard import PlanDashboard
from .make_dashboard import MakeDashboard
from .purchase_dashboard import PurchaseDashboard

__all__ = [
    "BaseDashboard",
    "CatalogDashboard",
    "ObserveDashboard",
    "PlanDashboard",
    "MakeDashboard",
    "PurchaseDashboard",
]
