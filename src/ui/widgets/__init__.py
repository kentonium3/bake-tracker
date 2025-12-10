"""
Widget exports for the UI package.
"""

from src.ui.widgets.availability_display import AvailabilityDisplay
from src.ui.widgets.production_history_table import ProductionHistoryTable
from src.ui.widgets.assembly_history_table import AssemblyHistoryTable
from src.ui.widgets.data_table import (
    DataTable,
    IngredientDataTable,
    RecipeDataTable,
    FinishedGoodDataTable,
    BundleDataTable,
    PackageDataTable,
    RecipientDataTable,
    EventDataTable,
)

__all__ = [
    # Base widget
    "DataTable",
    # Feature 014 widgets
    "AvailabilityDisplay",
    "ProductionHistoryTable",
    "AssemblyHistoryTable",
    # Existing data tables
    "IngredientDataTable",
    "RecipeDataTable",
    "FinishedGoodDataTable",
    "BundleDataTable",
    "PackageDataTable",
    "RecipientDataTable",
    "EventDataTable",
]
