"""Dashboard widgets for mode architecture.

This module provides dashboard components for each mode:
- BaseDashboard: Abstract base class for all dashboards
- CatalogDashboard: Dashboard for CATALOG mode
- ObserveDashboard: Dashboard for OBSERVE mode
"""

from .base_dashboard import BaseDashboard
from .catalog_dashboard import CatalogDashboard
from .observe_dashboard import ObserveDashboard

__all__ = ["BaseDashboard", "CatalogDashboard", "ObserveDashboard"]
