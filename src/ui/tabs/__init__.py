"""Tab widgets for mode-specific content.

This module provides tab implementations that are placed within mode containers.
Each tab follows the StandardTabLayout pattern for consistent UX.

Tabs are organized by their parent mode:
- CATALOG tabs: Ingredients, Products, Recipes, etc.
- PLAN tabs: Events, Planning Workspace
- SHOP tabs: Shopping Lists, Purchases, Inventory
- PRODUCE tabs: Production Runs, Assembly, Packaging, Recipients
- OBSERVE tabs: Dashboard, Event Status, Reports

Tab widgets are added as they are implemented.
"""

from .event_status_tab import EventStatusTab
from .reports_tab import ReportsTab

__all__ = ["EventStatusTab", "ReportsTab"]
