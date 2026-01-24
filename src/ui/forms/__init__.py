"""
Forms package for the Seasonal Baking Tracker.

Contains form dialogs for adding and editing entities.

Updated for Feature 006 Event Planning Restoration:
- Removed BundleFormDialog (Bundle concept eliminated)
"""

from .ingredient_form import IngredientFormDialog
from .recipe_form import RecipeFormDialog
from .finished_good_form import FinishedUnitFormDialog

# BundleFormDialog removed - Bundle concept eliminated in Feature 006
from .package_form import PackageFormDialog
from .recipient_form import RecipientFormDialog
from .event_form import EventFormDialog
from .assignment_form import AssignmentFormDialog

# Feature 014 - Production & Assembly Recording UI
from .record_production_dialog import RecordProductionDialog
from .finished_unit_detail import FinishedUnitDetailDialog
from .record_assembly_dialog import RecordAssemblyDialog
from .finished_good_detail import FinishedGoodDetailDialog

# Feature 063 - Variant Yield Inheritance
from .variant_creation_dialog import VariantCreationDialog

__all__ = [
    "IngredientFormDialog",
    "RecipeFormDialog",
    "FinishedUnitFormDialog",
    # BundleFormDialog removed - Bundle concept eliminated
    "PackageFormDialog",
    "RecipientFormDialog",
    "EventFormDialog",
    "AssignmentFormDialog",
    # Feature 014 - Production & Assembly Recording UI
    "RecordProductionDialog",
    "FinishedUnitDetailDialog",
    "RecordAssemblyDialog",
    "FinishedGoodDetailDialog",
    # Feature 063 - Variant Yield Inheritance
    "VariantCreationDialog",
]
