"""CatalogDashboard - Dashboard for CATALOG mode.

Shows entity counts for:
- Ingredients
- Products
- Recipes
- Finished Units
- Finished Goods
- Packages

Implements FR-007: Mode dashboard displays relevant statistics.
"""

from typing import Any
import customtkinter as ctk

from src.ui.dashboards.base_dashboard import BaseDashboard


class CatalogDashboard(BaseDashboard):
    """Dashboard showing catalog entity counts.

    Displays counts for all entity types managed in CATALOG mode.
    """

    def __init__(self, master: Any, **kwargs):
        """Initialize CatalogDashboard.

        Args:
            master: Parent widget
            **kwargs: Additional arguments passed to BaseDashboard
        """
        super().__init__(master, **kwargs)
        self.set_title("CATALOG Dashboard")
        self._create_stats()

    def _create_stats(self) -> None:
        """Create statistic displays for each entity type."""
        self.add_stat("Ingredients", "0")
        self.add_stat("Products", "0")
        self.add_stat("Recipes", "0")
        self.add_stat("Finished Units", "0")
        self.add_stat("Finished Goods", "0")
        self.add_stat("Packages", "0")

    def refresh(self) -> None:
        """Refresh dashboard with current entity counts."""
        try:
            from src.services.ingredient_service import get_all_ingredients
            from src.services.product_catalog_service import get_all_products
            from src.services.recipe_service import get_all_recipes
            from src.services.finished_unit_service import get_all_finished_units
            from src.services.finished_goods_service import get_all_finished_goods
            from src.services.package_service import get_all_packages

            # Get counts (use len() of results)
            ingredients = get_all_ingredients()
            self.update_stat("Ingredients", str(len(ingredients)))

            products = get_all_products()
            self.update_stat("Products", str(len(products)))

            recipes = get_all_recipes()
            self.update_stat("Recipes", str(len(recipes)))

            finished_units = get_all_finished_units()
            self.update_stat("Finished Units", str(len(finished_units)))

            finished_goods = get_all_finished_goods()
            self.update_stat("Finished Goods", str(len(finished_goods)))

            packages = get_all_packages()
            self.update_stat("Packages", str(len(packages)))

        except Exception:
            # Silently handle errors - dashboard stats are non-critical
            pass
