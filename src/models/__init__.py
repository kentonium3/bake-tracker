"""
Database models package.

This package contains all SQLAlchemy ORM models for the application.
"""

from .base import Base, BaseModel
from .ingredient import Ingredient  # LEGACY - for migration compatibility
from .product import Product  # NEW
from .product_variant import ProductVariant  # NEW
from .purchase_history import PurchaseHistory  # NEW
from .pantry_item import PantryItem  # NEW
from .unit_conversion import UnitConversion  # NEW
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
    "Ingredient",
    # New Product/Pantry Models
    "Product",
    "ProductVariant",
    "PurchaseHistory",
    "PantryItem",
    "UnitConversion",
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
