"""Dashboard widgets for mode architecture.

This module provides dashboard components for each mode:
- BaseDashboard: Abstract base class for all dashboards
- CatalogDashboard: Dashboard for CATALOG mode
"""

from .base_dashboard import BaseDashboard
from .catalog_dashboard import CatalogDashboard

__all__ = ["BaseDashboard", "CatalogDashboard"]
