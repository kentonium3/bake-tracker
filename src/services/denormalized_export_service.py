"""
Denormalized Export Service - Export AI-friendly views with context fields.

Provides denormalized exports for external augmentation by AI assistants.
Each view includes:
- All relevant fields from the primary entity
- Context fields from related entities (names, categories, etc.)
- _meta section documenting editable vs readonly fields

Usage:
    from src.services.denormalized_export_service import export_products_view

    # Export products view with context
    result = export_products_view("view_products.json")
    print(f"Exported {result.record_count} products")
"""

import json
from dataclasses import dataclass
from datetime import datetime
from src.utils.datetime_utils import utc_now
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy.orm import Session, joinedload

from src.models.ingredient import Ingredient
from src.models.inventory_item import InventoryItem
from src.models.product import Product
from src.models.purchase import Purchase
from src.services.database import session_scope


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class ExportResult:
    """Result of a view export operation."""

    view_type: str
    record_count: int
    output_path: str
    export_date: str


# ============================================================================
# Constants - Editable/Readonly Field Definitions
# ============================================================================

# Products view field definitions
PRODUCTS_VIEW_EDITABLE = [
    "brand",
    "product_name",
    "package_size",
    "package_type",
    "package_unit",
    "package_unit_quantity",
    "upc_code",
    "gtin",
    "notes",
    "preferred",
    "is_hidden",
]

PRODUCTS_VIEW_READONLY = [
    "id",
    "uuid",
    "ingredient_id",
    "ingredient_slug",
    "ingredient_name",
    "ingredient_category",
    "preferred_supplier_id",
    "preferred_supplier_name",
    "last_purchase_price",
    "last_purchase_date",
    "inventory_quantity",
    "date_added",
    "last_modified",
]

# Inventory view field definitions
INVENTORY_VIEW_EDITABLE = [
    "quantity",
    "location",
    "expiration_date",
    "opened_date",
    "notes",
    "lot_or_batch",
]

INVENTORY_VIEW_READONLY = [
    "id",
    "uuid",
    "product_id",
    "product_slug",
    "product_name",
    "brand",
    "package_unit",
    "package_unit_quantity",
    "ingredient_id",
    "ingredient_slug",
    "ingredient_name",
    "purchase_id",
    "purchase_date",
    "unit_cost",
    "last_updated",
]

# Purchases view field definitions
PURCHASES_VIEW_EDITABLE = [
    "notes",
]

PURCHASES_VIEW_READONLY = [
    "id",
    "uuid",
    "product_id",
    "product_slug",
    "product_name",
    "brand",
    "ingredient_slug",
    "ingredient_name",
    "supplier_id",
    "supplier_name",
    "supplier_city",
    "supplier_state",
    "purchase_date",
    "unit_price",
    "quantity_purchased",
    "total_cost",
    "created_at",
]


# ============================================================================
# Helper Functions
# ============================================================================


def _get_most_recent_purchase(product: Product) -> Optional[Purchase]:
    """Get the most recent purchase for a product."""
    if not product.purchases:
        return None
    return max(product.purchases, key=lambda p: p.purchase_date)


def _get_inventory_quantity(product: Product) -> float:
    """Get total inventory quantity for a product."""
    if not product.inventory_items:
        return 0.0
    return sum(item.quantity for item in product.inventory_items)


def _build_product_slug(product: Product) -> Optional[str]:
    """Build a composite slug for product identification."""
    if not product.ingredient:
        return None
    return f"{product.ingredient.slug}:{product.brand}:{product.package_unit_quantity}:{product.package_unit}"


# ============================================================================
# Products View Export
# ============================================================================


def export_products_view(
    output_path: str,
    session: Optional[Session] = None,
) -> ExportResult:
    """
    Export products with ingredient and supplier context for AI augmentation.

    Creates a view file with all product fields plus context fields:
    - ingredient_slug, ingredient_name, ingredient_category
    - preferred_supplier_name (from preferred_supplier)
    - last_purchase_price, last_purchase_date (from most recent purchase)
    - inventory_quantity (sum from inventory_items)

    Args:
        output_path: Path for the output JSON file
        session: Optional SQLAlchemy session for transactional composition

    Returns:
        ExportResult with export metadata
    """
    if session is not None:
        return _export_products_view_impl(output_path, session)
    with session_scope() as sess:
        return _export_products_view_impl(output_path, sess)


def _export_products_view_impl(output_path: str, session: Session) -> ExportResult:
    """Internal implementation of products view export."""
    # Query products with eager loading
    products = (
        session.query(Product)
        .options(
            joinedload(Product.ingredient),
            joinedload(Product.preferred_supplier),
            joinedload(Product.purchases),
            joinedload(Product.inventory_items),
        )
        .all()
    )

    export_date = utc_now().isoformat() + "Z"
    records = []

    for p in products:
        # Get context from relationships
        recent_purchase = _get_most_recent_purchase(p)
        inventory_qty = _get_inventory_quantity(p)

        records.append({
            # Primary fields
            "id": p.id,
            "uuid": str(p.uuid) if p.uuid else None,
            # Product fields
            "brand": p.brand,
            "product_name": p.product_name,
            "package_size": p.package_size,
            "package_type": p.package_type,
            "package_unit": p.package_unit,
            "package_unit_quantity": p.package_unit_quantity,
            "upc_code": p.upc_code,
            "gtin": p.gtin,
            "notes": p.notes,
            "preferred": p.preferred,
            "is_hidden": p.is_hidden,
            # Ingredient context (readonly)
            "ingredient_id": p.ingredient_id,
            "ingredient_slug": p.ingredient.slug if p.ingredient else None,
            "ingredient_name": p.ingredient.display_name if p.ingredient else None,
            "ingredient_category": p.ingredient.category if p.ingredient else None,
            # Supplier context (readonly)
            "preferred_supplier_id": p.preferred_supplier_id,
            "preferred_supplier_name": (
                p.preferred_supplier.name if p.preferred_supplier else None
            ),
            # Purchase context (readonly)
            "last_purchase_price": (
                str(recent_purchase.unit_price) if recent_purchase else None
            ),
            "last_purchase_date": (
                recent_purchase.purchase_date.isoformat()
                if recent_purchase and recent_purchase.purchase_date
                else None
            ),
            # Inventory context (readonly)
            "inventory_quantity": inventory_qty,
            # Timestamps
            "date_added": p.date_added.isoformat() if p.date_added else None,
            "last_modified": p.last_modified.isoformat() if p.last_modified else None,
        })

    view_data = {
        "version": "1.0",
        "view_type": "products",
        "export_date": export_date,
        "_meta": {
            "editable_fields": PRODUCTS_VIEW_EDITABLE,
            "readonly_fields": PRODUCTS_VIEW_READONLY,
        },
        "records": records,
    }

    # Write to file
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(view_data, f, indent=2, ensure_ascii=False, default=str)

    return ExportResult(
        view_type="products",
        record_count=len(records),
        output_path=str(output),
        export_date=export_date,
    )


# ============================================================================
# Inventory View Export
# ============================================================================


def export_inventory_view(
    output_path: str,
    session: Optional[Session] = None,
) -> ExportResult:
    """
    Export inventory items with product and purchase context.

    Creates a view file with all inventory fields plus context fields:
    - product_slug, product_name, brand, package_unit
    - ingredient_slug, ingredient_name
    - purchase_date, unit_cost (from associated purchase if available)

    Args:
        output_path: Path for the output JSON file
        session: Optional SQLAlchemy session for transactional composition

    Returns:
        ExportResult with export metadata
    """
    if session is not None:
        return _export_inventory_view_impl(output_path, session)
    with session_scope() as sess:
        return _export_inventory_view_impl(output_path, sess)


def _export_inventory_view_impl(output_path: str, session: Session) -> ExportResult:
    """Internal implementation of inventory view export."""
    # Query inventory items with eager loading
    items = (
        session.query(InventoryItem)
        .options(
            joinedload(InventoryItem.product).joinedload(Product.ingredient),
            joinedload(InventoryItem.purchase),
        )
        .all()
    )

    export_date = utc_now().isoformat() + "Z"
    records = []

    for item in items:
        product = item.product
        ingredient = product.ingredient if product else None
        purchase = item.purchase

        records.append({
            # Primary fields
            "id": item.id,
            "uuid": str(item.uuid) if item.uuid else None,
            # Inventory editable fields
            "quantity": item.quantity,
            "location": item.location,
            "expiration_date": (
                item.expiration_date.isoformat() if item.expiration_date else None
            ),
            "opened_date": (
                item.opened_date.isoformat() if item.opened_date else None
            ),
            "notes": item.notes,
            "lot_or_batch": item.lot_or_batch,
            # Product context (readonly)
            "product_id": item.product_id,
            "product_slug": _build_product_slug(product) if product else None,
            "product_name": product.product_name if product else None,
            "brand": product.brand if product else None,
            "package_unit": product.package_unit if product else None,
            "package_unit_quantity": product.package_unit_quantity if product else None,
            # Ingredient context (readonly)
            "ingredient_id": ingredient.id if ingredient else None,
            "ingredient_slug": ingredient.slug if ingredient else None,
            "ingredient_name": ingredient.display_name if ingredient else None,
            # Purchase context (readonly)
            "purchase_id": item.purchase_id,
            "purchase_date": (
                item.purchase_date.isoformat() if item.purchase_date else None
            ),
            "unit_cost": item.unit_cost,
            # Timestamps
            "last_updated": (
                item.last_updated.isoformat() if item.last_updated else None
            ),
        })

    view_data = {
        "version": "1.0",
        "view_type": "inventory",
        "export_date": export_date,
        "_meta": {
            "editable_fields": INVENTORY_VIEW_EDITABLE,
            "readonly_fields": INVENTORY_VIEW_READONLY,
        },
        "records": records,
    }

    # Write to file
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(view_data, f, indent=2, ensure_ascii=False, default=str)

    return ExportResult(
        view_type="inventory",
        record_count=len(records),
        output_path=str(output),
        export_date=export_date,
    )


# ============================================================================
# Purchases View Export
# ============================================================================


def export_purchases_view(
    output_path: str,
    session: Optional[Session] = None,
) -> ExportResult:
    """
    Export purchases with product and supplier details.

    Creates a view file with all purchase fields plus context fields:
    - product_slug, product_name, brand
    - ingredient_slug, ingredient_name
    - supplier_name, supplier_city, supplier_state

    Args:
        output_path: Path for the output JSON file
        session: Optional SQLAlchemy session for transactional composition

    Returns:
        ExportResult with export metadata
    """
    if session is not None:
        return _export_purchases_view_impl(output_path, session)
    with session_scope() as sess:
        return _export_purchases_view_impl(output_path, sess)


def _export_purchases_view_impl(output_path: str, session: Session) -> ExportResult:
    """Internal implementation of purchases view export."""
    # Query purchases with eager loading
    purchases = (
        session.query(Purchase)
        .options(
            joinedload(Purchase.product).joinedload(Product.ingredient),
            joinedload(Purchase.supplier),
        )
        .all()
    )

    export_date = utc_now().isoformat() + "Z"
    records = []

    for p in purchases:
        product = p.product
        ingredient = product.ingredient if product else None
        supplier = p.supplier

        records.append({
            # Primary fields
            "id": p.id,
            "uuid": str(p.uuid) if p.uuid else None,
            # Purchase fields (readonly - historical data)
            "purchase_date": (
                p.purchase_date.isoformat() if p.purchase_date else None
            ),
            "unit_price": str(p.unit_price) if p.unit_price else None,
            "quantity_purchased": p.quantity_purchased,
            "total_cost": str(p.total_cost) if p.unit_price else None,
            "notes": p.notes,  # Editable
            "created_at": p.created_at.isoformat() if p.created_at else None,
            # Product context (readonly)
            "product_id": p.product_id,
            "product_slug": _build_product_slug(product) if product else None,
            "product_name": product.product_name if product else None,
            "brand": product.brand if product else None,
            # Ingredient context (readonly)
            "ingredient_slug": ingredient.slug if ingredient else None,
            "ingredient_name": ingredient.display_name if ingredient else None,
            # Supplier context (readonly)
            "supplier_id": p.supplier_id,
            "supplier_name": supplier.name if supplier else None,
            "supplier_city": supplier.city if supplier else None,
            "supplier_state": supplier.state if supplier else None,
        })

    view_data = {
        "version": "1.0",
        "view_type": "purchases",
        "export_date": export_date,
        "_meta": {
            "editable_fields": PURCHASES_VIEW_EDITABLE,
            "readonly_fields": PURCHASES_VIEW_READONLY,
        },
        "records": records,
    }

    # Write to file
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(view_data, f, indent=2, ensure_ascii=False, default=str)

    return ExportResult(
        view_type="purchases",
        record_count=len(records),
        output_path=str(output),
        export_date=export_date,
    )


# ============================================================================
# Convenience Function
# ============================================================================


def export_all_views(
    output_dir: str,
    session: Optional[Session] = None,
) -> Dict[str, ExportResult]:
    """
    Export all denormalized views to a directory.

    Args:
        output_dir: Directory for output files
        session: Optional SQLAlchemy session for transactional composition

    Returns:
        Dictionary mapping view_type to ExportResult
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results = {}

    # Export all views
    results["products"] = export_products_view(
        str(output_path / "view_products.json"),
        session=session,
    )
    results["inventory"] = export_inventory_view(
        str(output_path / "view_inventory.json"),
        session=session,
    )
    results["purchases"] = export_purchases_view(
        str(output_path / "view_purchases.json"),
        session=session,
    )

    return results
