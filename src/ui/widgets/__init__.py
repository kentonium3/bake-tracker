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
from src.ui.widgets.event_card import EventCard
from src.ui.widgets.type_ahead_combobox import TypeAheadComboBox

__all__ = [
    # Base widget
    "DataTable",
    # Feature 014 widgets
    "AvailabilityDisplay",
    "ProductionHistoryTable",
    "AssemblyHistoryTable",
    # Feature 018 widgets
    "EventCard",
    # Existing data tables
    "IngredientDataTable",
    "RecipeDataTable",
    "FinishedGoodDataTable",
    "BundleDataTable",
    "PackageDataTable",
    "RecipientDataTable",
    "EventDataTable",
    # Feature 029 widgets
    "TypeAheadComboBox",
]
