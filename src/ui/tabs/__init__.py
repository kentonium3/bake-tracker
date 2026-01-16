"""Tab widgets for mode-specific content.

This module provides tab implementations that are placed within mode containers.
Each tab follows the StandardTabLayout pattern for consistent UX.

Tabs are organized by their parent mode:
- CATALOG tabs: Ingredients, Products, Recipes, etc. (+ group tabs F055)
- PLAN tabs: Events, Planning Workspace
- SHOP tabs: Shopping Lists, Purchases, Inventory
- PRODUCE tabs: Production Runs, Assembly, Packaging, Recipients
- OBSERVE tabs: Dashboard, Event Status, Reports

Tab widgets are added as they are implemented.
"""

from .assembly_tab import AssemblyTab
from .event_status_tab import EventStatusTab
from .packaging_tab import PackagingTab
from .planning_workspace_tab import PlanningWorkspaceTab
from .purchases_tab import PurchasesTab
from .reports_tab import ReportsTab
from .shopping_lists_tab import ShoppingListsTab

# Feature 055: Group tabs for Catalog mode navigation restructure
from .ingredients_group_tab import IngredientsGroupTab
from .recipes_group_tab import RecipesGroupTab
from .packaging_group_tab import PackagingGroupTab

__all__ = [
    "AssemblyTab",
    "EventStatusTab",
    "PackagingTab",
    "PlanningWorkspaceTab",
    "PurchasesTab",
    "ReportsTab",
    "ShoppingListsTab",
    # Feature 055 group tabs
    "IngredientsGroupTab",
    "RecipesGroupTab",
    "PackagingGroupTab",
]
