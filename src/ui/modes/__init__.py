"""Mode containers for the 5-mode workflow architecture.

This module provides mode implementations:
- CATALOG: Ingredients, Products, Recipes, Finished Units, Finished Goods, Packages
- PLAN: Events, Planning Workspace
- SHOP: Shopping Lists, Purchases, Inventory
- PRODUCE: Production Runs, Assembly, Packaging, Recipients
- OBSERVE: Dashboard, Event Status, Reports

Mode containers are added as they are implemented.
"""

from .placeholder_mode import PlaceholderMode, PlaceholderDashboard
from .catalog_mode import CatalogMode

__all__ = ["PlaceholderMode", "PlaceholderDashboard", "CatalogMode"]
