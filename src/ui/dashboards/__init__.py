"""Dashboard widgets for mode architecture.

This module provides dashboard components for each mode:
- BaseDashboard: Abstract base class for all dashboards
- CatalogDashboard: Dashboard for CATALOG mode
- ObserveDashboard: Dashboard for OBSERVE mode
- PlanDashboard: Dashboard for PLAN mode
- ProduceDashboard: Dashboard for PRODUCE mode
- ShopDashboard: Dashboard for SHOP mode
"""

from .base_dashboard import BaseDashboard
from .catalog_dashboard import CatalogDashboard
from .observe_dashboard import ObserveDashboard
from .plan_dashboard import PlanDashboard
from .produce_dashboard import ProduceDashboard
from .shop_dashboard import ShopDashboard

__all__ = [
    "BaseDashboard",
    "CatalogDashboard",
    "ObserveDashboard",
    "PlanDashboard",
    "ProduceDashboard",
    "ShopDashboard",
]
