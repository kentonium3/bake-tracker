"""
Database models package.

This package contains all SQLAlchemy ORM models for the application.
"""

from .base import Base, BaseModel
from .ingredient import Ingredient  # Refactored model
from .product import Product
from .purchase import Purchase
from .inventory_item import InventoryItem
from .ingredient_alias import IngredientAlias  # Supporting model
from .ingredient_crosswalk import IngredientCrosswalk  # Supporting model
from .product_packaging import ProductPackaging
from .recipe import Recipe, RecipeIngredient, RecipeComponent
from .inventory_snapshot import InventorySnapshot, SnapshotIngredient
from .finished_good import FinishedGood
from .assembly_type import AssemblyType

# Note: Bundle and YieldMode moved to legacy compatibility or removed in refactoring
from .finished_unit import FinishedUnit
from .composition import Composition
from .composition_assignment import CompositionAssignment  # Feature 026
from .package import (
    Package,
    PackageFinishedGood,
)  # Re-enabled Feature 006: Uses FinishedGood not Bundle
from .recipient import Recipient
from .event import (
    Event,
    EventRecipientPackage,
    FulfillmentStatus,
    EventProductionTarget,
    EventAssemblyTarget,
)  # Re-enabled Feature 006, extended Feature 016
from .package_status import PackageStatus  # Feature 008
from .production_record import ProductionRecord  # Feature 008
from .production_run import ProductionRun  # Feature 013
from .production_consumption import ProductionConsumption  # Feature 013
from .production_loss import ProductionLoss  # Feature 025
from .enums import ProductionStatus, LossCategory  # Feature 025
from .assembly_run import AssemblyRun  # Feature 013
from .assembly_finished_unit_consumption import AssemblyFinishedUnitConsumption  # Feature 013
from .assembly_packaging_consumption import AssemblyPackagingConsumption  # Feature 013
from .unit import Unit  # Feature 022

__all__ = [
    "Base",
    "BaseModel",
    # Core Models
    "Ingredient",
    "Product",
    "Purchase",
    "InventoryItem",
    # Supporting Models
    "IngredientAlias",
    "IngredientCrosswalk",
    "ProductPackaging",
    # Existing Models
    "Recipe",
    "RecipeIngredient",
    "RecipeComponent",
    "InventorySnapshot",
    "SnapshotIngredient",
    "FinishedGood",
    "AssemblyType",
    "FinishedUnit",
    "Composition",
    "CompositionAssignment",  # Feature 026
    # Package re-enabled in Feature 006 (uses FinishedGood not Bundle)
    "Package",
    "PackageFinishedGood",
    "Recipient",
    # Event models re-enabled in Feature 006, extended Feature 016
    "Event",
    "EventRecipientPackage",
    "FulfillmentStatus",
    "EventProductionTarget",
    "EventAssemblyTarget",
    # Production tracking Feature 008
    "PackageStatus",
    "ProductionRecord",
    # Production tracking Feature 013
    "ProductionRun",
    "ProductionConsumption",
    "AssemblyRun",
    "AssemblyFinishedUnitConsumption",
    "AssemblyPackagingConsumption",
    # Production loss tracking Feature 025
    "ProductionLoss",
    "ProductionStatus",
    "LossCategory",
    # Unit reference table Feature 022
    "Unit",
]
