"""
Database models package.

This package contains all SQLAlchemy ORM models for the application.
"""

from .base import Base, BaseModel
from .ingredient import Ingredient  # Refactored model
from .product import Product
from .purchase import Purchase
from .supplier import Supplier  # Feature 027: Product Catalog Management
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
    OutputMode,  # Feature 039
)  # Re-enabled Feature 006, extended Feature 016
from .production_plan_snapshot import ProductionPlanSnapshot  # Feature 039
from .package_status import PackageStatus  # Feature 008
from .production_record import ProductionRecord  # Feature 008
from .production_run import ProductionRun  # Feature 013
from .production_consumption import ProductionConsumption  # Feature 013
from .production_loss import ProductionLoss  # Feature 025
from .enums import ProductionStatus, LossCategory, DepletionReason  # Feature 025, Feature 041
from .inventory_depletion import InventoryDepletion  # Feature 041
from .assembly_run import AssemblyRun  # Feature 013
from .recipe_snapshot import RecipeSnapshot  # Feature 037
from .planning_snapshot import PlanningSnapshot  # Feature 064 (stub, full impl in WP04)
from .finished_unit_snapshot import FinishedUnitSnapshot  # Feature 064
from .assembly_finished_unit_consumption import AssemblyFinishedUnitConsumption  # Feature 013
from .assembly_packaging_consumption import AssemblyPackagingConsumption  # Feature 013
from .assembly_finished_good_consumption import AssemblyFinishedGoodConsumption  # Feature 060
from .unit import Unit  # Feature 022
from .finished_goods_adjustment import FinishedGoodsAdjustment  # Feature 061

# Feature 047: Materials Management System
from .material_category import MaterialCategory
from .material_subcategory import MaterialSubcategory
from .material import Material
from .material_product import MaterialProduct
from .material_unit import MaterialUnit
from .planning_snapshot import PlanningSnapshot  # Feature 064 (stub, full impl in WP04)
from .material_unit_snapshot import MaterialUnitSnapshot  # Feature 064
from .material_purchase import MaterialPurchase
from .material_consumption import MaterialConsumption

# Feature 058: Materials FIFO Foundation
from .material_inventory_item import MaterialInventoryItem

__all__ = [
    "Base",
    "BaseModel",
    # Core Models
    "Ingredient",
    "Product",
    "Purchase",
    "Supplier",  # Feature 027
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
    "OutputMode",  # Feature 039
    "ProductionPlanSnapshot",  # Feature 039
    # Production tracking Feature 008
    "PackageStatus",
    "ProductionRecord",
    # Production tracking Feature 013
    "ProductionRun",
    "ProductionConsumption",
    "AssemblyRun",
    "AssemblyFinishedUnitConsumption",
    "AssemblyPackagingConsumption",
    "AssemblyFinishedGoodConsumption",  # Feature 060
    # Production loss tracking Feature 025
    "ProductionLoss",
    "ProductionStatus",
    "LossCategory",
    # Inventory depletion tracking Feature 041
    "DepletionReason",
    "InventoryDepletion",
    # Unit reference table Feature 022
    "Unit",
    # Recipe snapshot Feature 037
    "RecipeSnapshot",
    # Feature 064: FinishedGoods Snapshot Architecture
    "PlanningSnapshot",
    "FinishedUnitSnapshot",
    # Feature 047: Materials Management System
    "MaterialCategory",
    "MaterialSubcategory",
    "Material",
    "MaterialProduct",
    "MaterialUnit",
    "PlanningSnapshot",
    "MaterialUnitSnapshot",
    "MaterialPurchase",
    "MaterialConsumption",
    # Feature 058: Materials FIFO Foundation
    "MaterialInventoryItem",
    # Feature 061: Finished Goods Inventory Service
    "FinishedGoodsAdjustment",
]
