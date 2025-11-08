"""
Database models package.

This package contains all SQLAlchemy ORM models for the application.
"""

from .base import Base, BaseModel
from .ingredient_legacy import Ingredient as IngredientLegacy  # LEGACY - for migration compatibility
from .ingredient import Ingredient  # NEW refactored model
from .variant import Variant  # NEW
from .purchase import Purchase  # NEW
from .pantry_item import PantryItem  # NEW
from .unit_conversion import UnitConversion  # NEW
from .ingredient_alias import IngredientAlias  # NEW supporting model
from .ingredient_crosswalk import IngredientCrosswalk  # NEW supporting model
from .variant_packaging import VariantPackaging  # NEW supporting model
from .recipe import Recipe, RecipeIngredient
from .inventory_snapshot import InventorySnapshot, SnapshotIngredient
from .finished_good import FinishedGood, Bundle, YieldMode
from .package import Package, PackageBundle
from .recipient import Recipient
from .event import Event, EventRecipientPackage

__all__ = [
    "Base",
    "BaseModel",
    # Legacy
    "IngredientLegacy",
    # New Ingredient/Variant/Pantry Models
    "Ingredient",
    "Variant",
    "Purchase",
    "PantryItem",
    "UnitConversion",
    # New Supporting Models
    "IngredientAlias",
    "IngredientCrosswalk",
    "VariantPackaging",
    # Existing Models
    "Recipe",
    "RecipeIngredient",
    "InventorySnapshot",
    "SnapshotIngredient",
    "FinishedGood",
    "Bundle",
    "YieldMode",
    "Package",
    "PackageBundle",
    "Recipient",
    "Event",
    "EventRecipientPackage",
]
