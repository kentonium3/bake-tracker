"""
Database models package.

This package contains all SQLAlchemy ORM models for the application.
"""

from .base import Base, BaseModel
from .ingredient import Ingredient  # Refactored model
from .product import Product  # Refactored from Variant
from .purchase import Purchase
from .pantry_item import PantryItem
from .unit_conversion import UnitConversion
from .ingredient_alias import IngredientAlias  # Supporting model
from .ingredient_crosswalk import IngredientCrosswalk  # Supporting model
from .variant_packaging import ProductPackaging, VariantPackaging  # Refactored model + alias
from .recipe import Recipe, RecipeIngredient
from .inventory_snapshot import InventorySnapshot, SnapshotIngredient
from .finished_good import FinishedGood
from .assembly_type import AssemblyType

# Note: Bundle and YieldMode moved to legacy compatibility or removed in refactoring
from .finished_unit import FinishedUnit
from .composition import Composition
from .package import (
    Package,
    PackageFinishedGood,
)  # Re-enabled Feature 006: Uses FinishedGood not Bundle
from .recipient import Recipient
from .event import Event, EventRecipientPackage  # Re-enabled Feature 006
from .package_status import PackageStatus  # Feature 008
from .production_record import ProductionRecord  # Feature 008

__all__ = [
    "Base",
    "BaseModel",
    # Core Models
    "Ingredient",
    "Product",
    "Purchase",
    "PantryItem",
    "UnitConversion",
    # Supporting Models
    "IngredientAlias",
    "IngredientCrosswalk",
    "ProductPackaging",
    "VariantPackaging",  # Backward compatibility alias
    # Existing Models
    "Recipe",
    "RecipeIngredient",
    "InventorySnapshot",
    "SnapshotIngredient",
    "FinishedGood",
    "AssemblyType",
    "FinishedUnit",
    "Composition",
    # Package re-enabled in Feature 006 (uses FinishedGood not Bundle)
    "Package",
    "PackageFinishedGood",
    "Recipient",
    # Event models re-enabled in Feature 006
    "Event",
    "EventRecipientPackage",
    # Production tracking Feature 008
    "PackageStatus",
    "ProductionRecord",
]
