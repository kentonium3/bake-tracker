"""
Denormalized Export Service - Export AI-friendly context-rich files with enriched fields.

Provides denormalized exports for external augmentation by AI assistants.
Each context-rich export includes:
- All relevant fields from the primary entity
- Context fields from related entities (names, categories, etc.)
- _meta section documenting editable vs readonly fields

Usage:
    from src.services.denormalized_export_service import export_products_context_rich

    # Export products with context for AI augmentation
    result = export_products_context_rich("aug_products.json")
    print(f"Exported {result.record_count} products")
"""

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from src.utils.datetime_utils import utc_now
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy.orm import Session, joinedload

from sqlalchemy import func

from src.models.composition import Composition
from src.models.finished_good import FinishedGood
from src.models.finished_unit import FinishedUnit
from src.models.ingredient import Ingredient
from src.models.inventory_item import InventoryItem
from src.models.material import Material
from src.models.material_category import MaterialCategory
from src.models.material_product import MaterialProduct
from src.models.material_subcategory import MaterialSubcategory
from src.models.product import Product
from src.models.purchase import Purchase
from src.models.recipe import Recipe, RecipeIngredient
from src.services.database import session_scope


# ============================================================================
# Helpers
# ============================================================================


def _format_money(value) -> Optional[str]:
    """Format a currency-like value as a 2-decimal string (e.g., '12.99')."""
    if value is None:
        return None
    try:
        dec = value if isinstance(value, Decimal) else Decimal(str(value))
        return format(dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f")
    except (InvalidOperation, ValueError, TypeError):
        # Fall back to the original string representation
        return str(value)


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class ExportResult:
    """Result of a context-rich export operation."""

    export_type: str
    record_count: int
    output_path: str
    export_date: str


# ============================================================================
# Constants - Editable/Readonly Field Definitions
# ============================================================================

# Products context-rich field definitions
PRODUCTS_CONTEXT_RICH_EDITABLE = [
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

PRODUCTS_CONTEXT_RICH_READONLY = [
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

# Inventory context-rich field definitions
INVENTORY_CONTEXT_RICH_EDITABLE = [
    "quantity",
    "location",
    "expiration_date",
    "opened_date",
    "notes",
    "lot_or_batch",
]

INVENTORY_CONTEXT_RICH_READONLY = [
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

# Purchases context-rich field definitions
PURCHASES_CONTEXT_RICH_EDITABLE = [
    "notes",
]

PURCHASES_CONTEXT_RICH_READONLY = [
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

# Ingredients context-rich field definitions
INGREDIENTS_CONTEXT_RICH_EDITABLE = [
    "description",
    "notes",
    "density_volume_value",
    "density_volume_unit",
    "density_weight_value",
    "density_weight_unit",
]

INGREDIENTS_CONTEXT_RICH_READONLY = [
    "id",
    "uuid",
    "slug",
    "display_name",
    "category",
    "category_hierarchy",
    "hierarchy_level",
    "parent_ingredient_id",
    "product_count",
    "products",
    "inventory_total",
    "average_cost",
    "date_added",
    "last_modified",
]

# Materials context-rich field definitions
MATERIALS_CONTEXT_RICH_EDITABLE = [
    "description",
    "notes",
]

MATERIALS_CONTEXT_RICH_READONLY = [
    "id",
    "uuid",
    "slug",
    "name",
    "base_unit_type",
    "category_hierarchy",
    "subcategory_id",
    "product_count",
    "products",
    # Note: total_inventory and total_inventory_value removed
    # Inventory is now tracked at MaterialUnit level via FIFO
]

# Recipes context-rich field definitions
RECIPES_CONTEXT_RICH_EDITABLE = [
    "notes",
    "source",
    "estimated_time_minutes",
]

# F056: yield_quantity, yield_unit, yield_description removed
# Yield data is now in FinishedUnit records
RECIPES_CONTEXT_RICH_READONLY = [
    "id",
    "uuid",
    "name",
    "category",
    "is_archived",
    "is_production_ready",
    "base_recipe_id",
    "variant_name",
    "ingredients",
    "recipe_components",
    "total_cost",
    "cost_per_unit",
    "date_added",
    "last_modified",
]

# Material Products context-rich field definitions
MATERIAL_PRODUCTS_CONTEXT_RICH_EDITABLE = [
    "name",
    "brand",
    "package_quantity",
    "package_unit",
    "notes",
    "is_hidden",
]

MATERIAL_PRODUCTS_CONTEXT_RICH_READONLY = [
    "id",
    "uuid",
    "slug",
    "material_id",
    "material_slug",
    "material_name",
    "material_category",
    "material_subcategory",
    "supplier_id",
    "supplier_name",
    "sku",
    "quantity_in_base_units",
    # Note: current_inventory, weighted_avg_cost, inventory_value removed
    # Inventory is now tracked at MaterialUnit level via FIFO
]

# Finished Units context-rich field definitions
FINISHED_UNITS_CONTEXT_RICH_EDITABLE = [
    "description",
    "production_notes",
    "notes",
]

FINISHED_UNITS_CONTEXT_RICH_READONLY = [
    "id",
    "uuid",
    "slug",
    "display_name",
    "recipe_id",
    "recipe_slug",
    "recipe_name",
    "recipe_category",
    "yield_mode",
    "items_per_batch",
    "item_unit",
    "batch_percentage",
    "portion_description",
    "category",
    "inventory_count",
    "created_at",
    "updated_at",
]

# Finished Goods context-rich field definitions
FINISHED_GOODS_CONTEXT_RICH_EDITABLE = [
    "description",
    "packaging_instructions",
    "notes",
]

FINISHED_GOODS_CONTEXT_RICH_READONLY = [
    "id",
    "uuid",
    "slug",
    "display_name",
    "assembly_type",
    "inventory_count",
    "components",
    "created_at",
    "updated_at",
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


def _build_ingredient_hierarchy_path(ingredient: Ingredient) -> str:
    """
    Build full category hierarchy path for an ingredient.

    For ingredients using the self-referential hierarchy (Feature 031),
    walks up the parent chain to build a path like:
    "Chocolate > Dark Chocolate > Semi-Sweet Chips"

    Falls back to the legacy category field if no parent hierarchy exists.

    Args:
        ingredient: The ingredient to build the path for

    Returns:
        Hierarchy path as " > "-separated string, or empty string if no hierarchy
    """
    if ingredient is None:
        return ""

    # Build path from current ingredient up to root
    path_parts = []

    # Start with the current ingredient
    current = ingredient
    while current is not None:
        path_parts.insert(0, current.display_name or current.slug or "")
        current = current.parent if hasattr(current, "parent") else None

    # If we only have the leaf (no parent hierarchy), use the category field
    if len(path_parts) == 1 and ingredient.category:
        return f"{ingredient.category} > {ingredient.display_name}"

    return " > ".join(path_parts) if path_parts else ""


def _build_material_hierarchy_path(material: Material) -> str:
    """
    Build full category hierarchy path for a material.

    Materials use a 3-level hierarchy: Category > Subcategory > Material
    Example: "Ribbons > Satin > Red Satin Ribbon"

    Args:
        material: The material to build the path for

    Returns:
        Hierarchy path as " > "-separated string, or empty string if no hierarchy
    """
    if material is None:
        return ""

    path_parts = []

    # Build path: Category > Subcategory > Material
    if material.subcategory:
        if material.subcategory.category:
            path_parts.append(material.subcategory.category.name)
        path_parts.append(material.subcategory.name)

    path_parts.append(material.name)

    return " > ".join(path_parts) if path_parts else ""


def _calculate_ingredient_inventory_total(ingredient: Ingredient, session: Session) -> float:
    """
    Sum current_quantity across all inventory items for ingredient's products.

    Args:
        ingredient: The ingredient to calculate inventory for
        session: SQLAlchemy session

    Returns:
        Total inventory quantity across all products for this ingredient
    """
    if ingredient is None:
        return 0.0

    # Only leaf ingredients can have products
    if not ingredient.is_leaf:
        return 0.0

    total = (
        session.query(func.sum(InventoryItem.quantity))
        .join(Product)
        .filter(
            Product.ingredient_id == ingredient.id,
            InventoryItem.quantity > 0,
        )
        .scalar()
    )
    return float(total) if total else 0.0


def _calculate_ingredient_average_cost(ingredient: Ingredient, session: Session) -> Optional[float]:
    """
    Calculate weighted average cost per unit for an ingredient.

    Uses the most recent purchase prices from all products linked to this ingredient.

    Args:
        ingredient: The ingredient to calculate average cost for
        session: SQLAlchemy session

    Returns:
        Weighted average cost per unit, or None if no purchase history
    """
    if ingredient is None:
        return None

    # Only leaf ingredients can have products
    if not ingredient.is_leaf:
        return None

    # Get all inventory items with costs for this ingredient's products
    items = (
        session.query(InventoryItem.quantity, InventoryItem.unit_cost)
        .join(Product)
        .filter(
            Product.ingredient_id == ingredient.id,
            InventoryItem.quantity > 0,
            InventoryItem.unit_cost.isnot(None),
        )
        .all()
    )

    if not items:
        return None

    total_cost = sum(item.quantity * (item.unit_cost or 0) for item in items)
    total_quantity = sum(item.quantity for item in items)

    if total_quantity == 0:
        return None

    return round(total_cost / total_quantity, 4)


def _calculate_material_inventory_total(material: Material) -> float:
    """
    Calculate total inventory for a material from MaterialUnit records.

    Note: As of Feature 058, inventory is tracked at MaterialUnit level via FIFO.
    MaterialProduct no longer has current_inventory field.

    Args:
        material: The material to calculate inventory for

    Returns:
        Total inventory in base units (currently returns 0.0 - to be implemented
        when MaterialUnit query is available)
    """
    # TODO: Implement MaterialUnit-based inventory query when service is available
    # For now, return 0.0 since the old model fields have been removed
    return 0.0


def _calculate_material_inventory_value(material: Material) -> float:
    """
    Calculate total inventory value for a material from MaterialUnit records.

    Note: As of Feature 058, inventory value is calculated from MaterialUnit FIFO costs.
    MaterialProduct no longer has inventory_value field.

    Args:
        material: The material to calculate value for

    Returns:
        Total inventory value (currently returns 0.0 - to be implemented
        when MaterialUnit query is available)
    """
    # TODO: Implement MaterialUnit-based value query when service is available
    # For now, return 0.0 since the old model fields have been removed
    return 0.0


def _calculate_recipe_cost(recipe: Recipe, session: Session) -> float:
    """
    Calculate total recipe cost from ingredient costs.

    Uses each RecipeIngredient's calculate_cost() method which handles
    unit conversions and density-based calculations.

    Args:
        recipe: The recipe to calculate cost for
        session: SQLAlchemy session (unused but kept for consistency)

    Returns:
        Total cost of all ingredients in the recipe
    """
    if recipe is None:
        return 0.0

    return recipe.calculate_cost()


def _get_last_purchase_price(product: Product) -> Optional[str]:
    """Get the last purchase price for a product as formatted string."""
    recent = _get_most_recent_purchase(product)
    if recent and recent.unit_price is not None:
        return _format_money(recent.unit_price)
    return None


# ============================================================================
# Products View Export
# ============================================================================


def export_products_context_rich(
    output_path: str,
    session: Optional[Session] = None,
) -> ExportResult:
    """
    Export products with ingredient and supplier context for AI augmentation.

    Creates a context-rich file with all product fields plus context fields:
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
        return _export_products_context_rich_impl(output_path, session)
    with session_scope() as sess:
        return _export_products_context_rich_impl(output_path, sess)


def _export_products_context_rich_impl(output_path: str, session: Session) -> ExportResult:
    """Internal implementation of products context-rich export."""
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

        records.append(
            {
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
                    _format_money(recent_purchase.unit_price) if recent_purchase else None
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
            }
        )

    export_data = {
        "version": "1.0",
        "export_type": "products",
        "export_date": export_date,
        "_meta": {
            "editable_fields": PRODUCTS_CONTEXT_RICH_EDITABLE,
            "readonly_fields": PRODUCTS_CONTEXT_RICH_READONLY,
        },
        "records": records,
    }

    # Write to file
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

    return ExportResult(
        export_type="products",
        record_count=len(records),
        output_path=str(output),
        export_date=export_date,
    )


# ============================================================================
# Inventory View Export
# ============================================================================


def export_inventory_context_rich(
    output_path: str,
    session: Optional[Session] = None,
) -> ExportResult:
    """
    Export inventory items with product and purchase context.

    Creates a context-rich file with all inventory fields plus context fields:
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
        return _export_inventory_context_rich_impl(output_path, session)
    with session_scope() as sess:
        return _export_inventory_context_rich_impl(output_path, sess)


def _export_inventory_context_rich_impl(output_path: str, session: Session) -> ExportResult:
    """Internal implementation of inventory context-rich export."""
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

        records.append(
            {
                # Primary fields
                "id": item.id,
                "uuid": str(item.uuid) if item.uuid else None,
                # Inventory editable fields
                "quantity": item.quantity,
                "location": item.location,
                "expiration_date": (
                    item.expiration_date.isoformat() if item.expiration_date else None
                ),
                "opened_date": (item.opened_date.isoformat() if item.opened_date else None),
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
                "purchase_date": (item.purchase_date.isoformat() if item.purchase_date else None),
                "unit_cost": item.unit_cost,
                # Timestamps
                "last_updated": (item.last_updated.isoformat() if item.last_updated else None),
            }
        )

    export_data = {
        "version": "1.0",
        "export_type": "inventory",
        "export_date": export_date,
        "_meta": {
            "editable_fields": INVENTORY_CONTEXT_RICH_EDITABLE,
            "readonly_fields": INVENTORY_CONTEXT_RICH_READONLY,
        },
        "records": records,
    }

    # Write to file
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

    return ExportResult(
        export_type="inventory",
        record_count=len(records),
        output_path=str(output),
        export_date=export_date,
    )


# ============================================================================
# Purchases View Export
# ============================================================================


def export_purchases_context_rich(
    output_path: str,
    session: Optional[Session] = None,
) -> ExportResult:
    """
    Export purchases with product and supplier details.

    Creates a context-rich file with all purchase fields plus context fields:
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
        return _export_purchases_context_rich_impl(output_path, session)
    with session_scope() as sess:
        return _export_purchases_context_rich_impl(output_path, sess)


def _export_purchases_context_rich_impl(output_path: str, session: Session) -> ExportResult:
    """Internal implementation of purchases context-rich export."""
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

        records.append(
            {
                # Primary fields
                "id": p.id,
                "uuid": str(p.uuid) if p.uuid else None,
                # Purchase fields (readonly - historical data)
                "purchase_date": (p.purchase_date.isoformat() if p.purchase_date else None),
                "unit_price": _format_money(p.unit_price) if p.unit_price is not None else None,
                "quantity_purchased": p.quantity_purchased,
                "total_cost": _format_money(p.total_cost) if p.total_cost is not None else None,
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
            }
        )

    export_data = {
        "version": "1.0",
        "export_type": "purchases",
        "export_date": export_date,
        "_meta": {
            "editable_fields": PURCHASES_CONTEXT_RICH_EDITABLE,
            "readonly_fields": PURCHASES_CONTEXT_RICH_READONLY,
        },
        "records": records,
    }

    # Write to file
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

    return ExportResult(
        export_type="purchases",
        record_count=len(records),
        output_path=str(output),
        export_date=export_date,
    )


# ============================================================================
# Ingredients View Export
# ============================================================================


def export_ingredients_context_rich(
    output_path: str,
    session: Optional[Session] = None,
) -> ExportResult:
    """
    Export ingredients with context for AI augmentation.

    Creates a context-rich file with all ingredient fields plus context fields:
    - category_hierarchy: Full path (e.g., "Chocolate > Dark Chocolate > Semi-Sweet Chips")
    - products: Nested array of related products with purchase info
    - inventory_total: Sum of inventory across all products
    - average_cost: Weighted average cost per unit

    Args:
        output_path: Path for the output JSON file
        session: Optional SQLAlchemy session for transactional composition

    Returns:
        ExportResult with export metadata
    """
    if session is not None:
        return _export_ingredients_context_rich_impl(output_path, session)
    with session_scope() as sess:
        return _export_ingredients_context_rich_impl(output_path, sess)


def _export_ingredients_context_rich_impl(output_path: str, session: Session) -> ExportResult:
    """Internal implementation of ingredients context-rich export."""
    # Query ingredients with eager loading
    ingredients = (
        session.query(Ingredient)
        .options(
            joinedload(Ingredient.products).joinedload(Product.purchases),
            joinedload(Ingredient.parent),
        )
        .all()
    )

    export_date = utc_now().isoformat() + "Z"
    records = []

    for ing in ingredients:
        # Build nested products array
        products_data = []
        for p in ing.products:
            products_data.append(
                {
                    "id": p.id,
                    "brand": p.brand,
                    "product_name": p.product_name,
                    "package_size": p.package_size,
                    "package_unit": p.package_unit,
                    "package_unit_quantity": p.package_unit_quantity,
                    "preferred": p.preferred,
                    "last_purchase_price": _get_last_purchase_price(p),
                }
            )

        records.append(
            {
                # Primary fields (readonly)
                "id": ing.id,
                "uuid": str(ing.uuid) if ing.uuid else None,
                "slug": ing.slug,
                "display_name": ing.display_name,
                "category": ing.category,
                "category_hierarchy": _build_ingredient_hierarchy_path(ing),
                "hierarchy_level": ing.hierarchy_level,
                "parent_ingredient_id": ing.parent_ingredient_id,
                # Editable fields
                "description": ing.description,
                "notes": ing.notes,
                "density_volume_value": ing.density_volume_value,
                "density_volume_unit": ing.density_volume_unit,
                "density_weight_value": ing.density_weight_value,
                "density_weight_unit": ing.density_weight_unit,
                # Computed fields (readonly)
                "product_count": len(ing.products),
                "products": products_data,
                "inventory_total": _calculate_ingredient_inventory_total(ing, session),
                "average_cost": _calculate_ingredient_average_cost(ing, session),
                # Timestamps
                "date_added": ing.date_added.isoformat() if ing.date_added else None,
                "last_modified": ing.last_modified.isoformat() if ing.last_modified else None,
            }
        )

    export_data = {
        "version": "1.0",
        "export_type": "ingredients",
        "export_date": export_date,
        "_meta": {
            "editable_fields": INGREDIENTS_CONTEXT_RICH_EDITABLE,
            "readonly_fields": INGREDIENTS_CONTEXT_RICH_READONLY,
        },
        "records": records,
    }

    # Write to file
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

    return ExportResult(
        export_type="ingredients",
        record_count=len(records),
        output_path=str(output),
        export_date=export_date,
    )


# ============================================================================
# Materials View Export
# ============================================================================


def export_materials_context_rich(
    output_path: str,
    session: Optional[Session] = None,
) -> ExportResult:
    """
    Export materials with context for AI augmentation.

    Creates a context-rich file with all material fields plus context fields:
    - category_hierarchy: Full path (e.g., "Ribbons > Satin > Red Satin Ribbon")
    - products: Nested array of related products

    Note: As of Feature 058, total_inventory and total_inventory_value are
    no longer included. Inventory is tracked at MaterialUnit level via FIFO.

    Args:
        output_path: Path for the output JSON file
        session: Optional SQLAlchemy session for transactional composition

    Returns:
        ExportResult with export metadata
    """
    if session is not None:
        return _export_materials_context_rich_impl(output_path, session)
    with session_scope() as sess:
        return _export_materials_context_rich_impl(output_path, sess)


def _export_materials_context_rich_impl(output_path: str, session: Session) -> ExportResult:
    """Internal implementation of materials context-rich export."""
    # Query materials with eager loading
    materials = (
        session.query(Material)
        .options(
            joinedload(Material.subcategory).joinedload(MaterialSubcategory.category),
            joinedload(Material.products).joinedload(MaterialProduct.supplier),
        )
        .all()
    )

    export_date = utc_now().isoformat() + "Z"
    records = []

    for mat in materials:
        # Build nested products array
        # Note: current_inventory and weighted_avg_cost removed from products
        # Inventory is now tracked at MaterialUnit level via FIFO
        products_data = []
        for p in mat.products:
            products_data.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "slug": p.slug,
                    "brand": p.brand,
                    "sku": p.sku,
                    "package_quantity": p.package_quantity,
                    "package_unit": p.package_unit,
                    "supplier_name": p.supplier.name if p.supplier else None,
                }
            )

        records.append(
            {
                # Primary fields (readonly)
                "id": mat.id,
                "uuid": str(mat.uuid) if mat.uuid else None,
                "slug": mat.slug,
                "name": mat.name,
                "base_unit_type": mat.base_unit_type,
                "category_hierarchy": _build_material_hierarchy_path(mat),
                "subcategory_id": mat.subcategory_id,
                # Editable fields
                "description": mat.description,
                "notes": mat.notes,
                # Computed fields (readonly)
                "product_count": len(mat.products),
                "products": products_data,
                # Note: total_inventory and total_inventory_value removed
                # Inventory is now tracked at MaterialUnit level via FIFO
            }
        )

    export_data = {
        "version": "1.0",
        "export_type": "materials",
        "export_date": export_date,
        "_meta": {
            "editable_fields": MATERIALS_CONTEXT_RICH_EDITABLE,
            "readonly_fields": MATERIALS_CONTEXT_RICH_READONLY,
        },
        "records": records,
    }

    # Write to file
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

    return ExportResult(
        export_type="materials",
        record_count=len(records),
        output_path=str(output),
        export_date=export_date,
    )


# ============================================================================
# Recipes View Export
# ============================================================================


def export_recipes_context_rich(
    output_path: str,
    session: Optional[Session] = None,
) -> ExportResult:
    """
    Export recipes with full ingredient details and computed costs.

    Creates a context-rich file with all recipe fields plus context fields:
    - ingredients: Nested array with ingredient details and costs
    - recipe_components: Nested array of sub-recipes (if any)
    - total_cost: Computed total cost of all ingredients
    - cost_per_unit: Cost divided by items_per_batch (from FinishedUnit)

    Args:
        output_path: Path for the output JSON file
        session: Optional SQLAlchemy session for transactional composition

    Returns:
        ExportResult with export metadata
    """
    if session is not None:
        return _export_recipes_context_rich_impl(output_path, session)
    with session_scope() as sess:
        return _export_recipes_context_rich_impl(output_path, sess)


def _export_recipes_context_rich_impl(output_path: str, session: Session) -> ExportResult:
    """Internal implementation of recipes context-rich export."""
    # Query recipes with eager loading
    recipes = (
        session.query(Recipe)
        .options(
            joinedload(Recipe.recipe_ingredients).joinedload(RecipeIngredient.ingredient),
            joinedload(Recipe.recipe_components),
        )
        .all()
    )

    export_date = utc_now().isoformat() + "Z"
    records = []

    for recipe in recipes:
        # Build nested ingredients array
        ingredients_data = []
        for ri in recipe.recipe_ingredients:
            ingredient_cost = ri.calculate_cost()
            ingredients_data.append(
                {
                    "ingredient_id": ri.ingredient_id,
                    "ingredient_slug": ri.ingredient.slug if ri.ingredient else None,
                    "ingredient_name": ri.ingredient.display_name if ri.ingredient else None,
                    "quantity": float(ri.quantity),
                    "unit": ri.unit,
                    "notes": ri.notes,
                    "estimated_cost": round(ingredient_cost, 2) if ingredient_cost else None,
                }
            )

        # Build nested recipe_components array (sub-recipes)
        components_data = []
        for rc in recipe.recipe_components:
            components_data.append(
                {
                    "component_recipe_id": rc.component_recipe_id,
                    "component_recipe_name": (
                        rc.component_recipe.name if rc.component_recipe else None
                    ),
                    "quantity": float(rc.quantity),
                    "notes": rc.notes,
                    "sort_order": rc.sort_order,
                }
            )

        # Calculate costs
        total_cost = _calculate_recipe_cost(recipe, session)
        # F056: Use FinishedUnit.items_per_batch for cost_per_unit calculation
        cost_per_unit = None
        if recipe.finished_units:
            primary_unit = recipe.finished_units[0]
            if primary_unit.items_per_batch and primary_unit.items_per_batch > 0:
                cost_per_unit = round(total_cost / primary_unit.items_per_batch, 2)

        # F056: yield_quantity, yield_unit, yield_description removed
        records.append(
            {
                # Primary fields (readonly)
                "id": recipe.id,
                "uuid": str(recipe.uuid) if recipe.uuid else None,
                "name": recipe.name,
                "category": recipe.category,
                "is_archived": recipe.is_archived,
                "is_production_ready": recipe.is_production_ready,
                "base_recipe_id": recipe.base_recipe_id,
                "variant_name": recipe.variant_name,
                # Editable fields
                "source": recipe.source,
                "estimated_time_minutes": recipe.estimated_time_minutes,
                "notes": recipe.notes,
                # Nested relationships (readonly)
                "ingredients": ingredients_data,
                "recipe_components": components_data,
                # Computed fields (readonly)
                "total_cost": round(total_cost, 2) if total_cost else None,
                "cost_per_unit": cost_per_unit,
                # Timestamps
                "date_added": recipe.date_added.isoformat() if recipe.date_added else None,
                "last_modified": recipe.last_modified.isoformat() if recipe.last_modified else None,
            }
        )

    export_data = {
        "version": "1.0",
        "export_type": "recipes",
        "export_date": export_date,
        "_meta": {
            "editable_fields": RECIPES_CONTEXT_RICH_EDITABLE,
            "readonly_fields": RECIPES_CONTEXT_RICH_READONLY,
        },
        "records": records,
    }

    # Write to file
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

    return ExportResult(
        export_type="recipes",
        record_count=len(records),
        output_path=str(output),
        export_date=export_date,
    )


# ============================================================================
# Material Products Context-Rich Export
# ============================================================================


def export_material_products_context_rich(
    output_path: str,
    session: Optional[Session] = None,
) -> ExportResult:
    """
    Export material products with context for AI augmentation.

    Creates a context-rich file with all material product fields plus context fields:
    - material_slug, material_name, material_category, material_subcategory
    - supplier_name

    Args:
        output_path: Path for the output JSON file
        session: Optional SQLAlchemy session for transactional composition

    Returns:
        ExportResult with export metadata
    """
    if session is not None:
        return _export_material_products_context_rich_impl(output_path, session)
    with session_scope() as sess:
        return _export_material_products_context_rich_impl(output_path, sess)


def _export_material_products_context_rich_impl(output_path: str, session: Session) -> ExportResult:
    """Internal implementation of material products context-rich export."""
    # Query material products with eager loading
    products = (
        session.query(MaterialProduct)
        .options(
            joinedload(MaterialProduct.material)
            .joinedload(Material.subcategory)
            .joinedload(MaterialSubcategory.category),
            joinedload(MaterialProduct.supplier),
        )
        .all()
    )

    export_date = utc_now().isoformat() + "Z"
    records = []

    for p in products:
        material = p.material
        subcategory = material.subcategory if material else None
        category = subcategory.category if subcategory else None
        supplier = p.supplier

        records.append(
            {
                # Primary fields (readonly)
                "id": p.id,
                "uuid": str(p.uuid) if p.uuid else None,
                "slug": p.slug,
                # Material context (readonly)
                "material_id": p.material_id,
                "material_slug": material.slug if material else None,
                "material_name": material.name if material else None,
                "material_category": category.name if category else None,
                "material_subcategory": subcategory.name if subcategory else None,
                # Supplier context (readonly)
                "supplier_id": p.supplier_id,
                "supplier_name": supplier.name if supplier else None,
                # Editable fields
                "name": p.name,
                "brand": p.brand,
                "package_quantity": p.package_quantity,
                "package_unit": p.package_unit,
                "notes": p.notes,
                "is_hidden": p.is_hidden,
                # Additional readonly fields
                "sku": p.sku,
                "quantity_in_base_units": p.quantity_in_base_units,
                # Note: current_inventory, weighted_avg_cost, inventory_value removed
                # Inventory is now tracked at MaterialUnit level via FIFO
            }
        )

    export_data = {
        "version": "1.0",
        "export_type": "material_products",
        "export_date": export_date,
        "_meta": {
            "editable_fields": MATERIAL_PRODUCTS_CONTEXT_RICH_EDITABLE,
            "readonly_fields": MATERIAL_PRODUCTS_CONTEXT_RICH_READONLY,
        },
        "records": records,
    }

    # Write to file
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

    return ExportResult(
        export_type="material_products",
        record_count=len(records),
        output_path=str(output),
        export_date=export_date,
    )


# ============================================================================
# Finished Units Context-Rich Export
# ============================================================================


def export_finished_units_context_rich(
    output_path: str,
    session: Optional[Session] = None,
) -> ExportResult:
    """
    Export finished units with recipe context for AI augmentation.

    Creates a context-rich file with all finished unit fields plus context fields:
    - recipe_slug, recipe_name, recipe_category

    Args:
        output_path: Path for the output JSON file
        session: Optional SQLAlchemy session for transactional composition

    Returns:
        ExportResult with export metadata
    """
    if session is not None:
        return _export_finished_units_context_rich_impl(output_path, session)
    with session_scope() as sess:
        return _export_finished_units_context_rich_impl(output_path, sess)


def _export_finished_units_context_rich_impl(output_path: str, session: Session) -> ExportResult:
    """Internal implementation of finished units context-rich export."""
    # Query finished units with eager loading
    units = (
        session.query(FinishedUnit)
        .options(
            joinedload(FinishedUnit.recipe),
        )
        .all()
    )

    export_date = utc_now().isoformat() + "Z"
    records = []

    for unit in units:
        recipe = unit.recipe

        records.append(
            {
                # Primary fields (readonly)
                "id": unit.id,
                "uuid": str(unit.uuid) if unit.uuid else None,
                "slug": unit.slug,
                "display_name": unit.display_name,
                # Recipe context (readonly)
                "recipe_id": unit.recipe_id,
                "recipe_slug": recipe.slug if recipe and hasattr(recipe, "slug") else None,
                "recipe_name": recipe.name if recipe else None,
                "recipe_category": recipe.category if recipe else None,
                # Yield info (readonly)
                "yield_mode": unit.yield_mode.value if unit.yield_mode else None,
                "items_per_batch": unit.items_per_batch,
                "item_unit": unit.item_unit,
                "batch_percentage": float(unit.batch_percentage) if unit.batch_percentage else None,
                "portion_description": unit.portion_description,
                # Editable fields
                "description": unit.description,
                "production_notes": unit.production_notes,
                "notes": unit.notes,
                # Additional readonly fields
                "category": unit.category,
                "inventory_count": unit.inventory_count,
                # Timestamps
                "created_at": unit.created_at.isoformat() if unit.created_at else None,
                "updated_at": unit.updated_at.isoformat() if unit.updated_at else None,
            }
        )

    export_data = {
        "version": "1.0",
        "export_type": "finished_units",
        "export_date": export_date,
        "_meta": {
            "editable_fields": FINISHED_UNITS_CONTEXT_RICH_EDITABLE,
            "readonly_fields": FINISHED_UNITS_CONTEXT_RICH_READONLY,
        },
        "records": records,
    }

    # Write to file
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

    return ExportResult(
        export_type="finished_units",
        record_count=len(records),
        output_path=str(output),
        export_date=export_date,
    )


# ============================================================================
# Finished Goods Context-Rich Export
# ============================================================================


def export_finished_goods_context_rich(
    output_path: str,
    session: Optional[Session] = None,
) -> ExportResult:
    """
    Export finished goods with component context for AI augmentation.

    Creates a context-rich file with all finished good fields plus context fields:
    - components: Nested array with component details

    Args:
        output_path: Path for the output JSON file
        session: Optional SQLAlchemy session for transactional composition

    Returns:
        ExportResult with export metadata
    """
    if session is not None:
        return _export_finished_goods_context_rich_impl(output_path, session)
    with session_scope() as sess:
        return _export_finished_goods_context_rich_impl(output_path, sess)


def _export_finished_goods_context_rich_impl(output_path: str, session: Session) -> ExportResult:
    """Internal implementation of finished goods context-rich export."""
    # Query finished goods with eager loading
    goods = (
        session.query(FinishedGood)
        .options(
            joinedload(FinishedGood.components).joinedload(Composition.finished_unit_component),
            joinedload(FinishedGood.components).joinedload(Composition.finished_good_component),
        )
        .all()
    )

    export_date = utc_now().isoformat() + "Z"
    records = []

    for good in goods:
        # Build nested components array
        components_data = []
        for comp in good.components:
            component_info = {
                "composition_id": comp.id,
                "quantity": comp.component_quantity,
                "notes": comp.component_notes,
                "sort_order": comp.sort_order,
            }
            if comp.finished_unit_component:
                component_info["type"] = "finished_unit"
                component_info["component_slug"] = comp.finished_unit_component.slug
                component_info["component_name"] = comp.finished_unit_component.display_name
            elif comp.finished_good_component:
                component_info["type"] = "finished_good"
                component_info["component_slug"] = comp.finished_good_component.slug
                component_info["component_name"] = comp.finished_good_component.display_name
            components_data.append(component_info)

        # Sort components by sort_order
        components_data.sort(key=lambda x: x.get("sort_order", 999))

        records.append(
            {
                # Primary fields (readonly)
                "id": good.id,
                "uuid": str(good.uuid) if good.uuid else None,
                "slug": good.slug,
                "display_name": good.display_name,
                "assembly_type": good.assembly_type.value if good.assembly_type else None,
                # Editable fields
                "description": good.description,
                "packaging_instructions": good.packaging_instructions,
                "notes": good.notes,
                # Additional readonly fields
                "inventory_count": good.inventory_count,
                "components": components_data,
                # Timestamps
                "created_at": good.created_at.isoformat() if good.created_at else None,
                "updated_at": good.updated_at.isoformat() if good.updated_at else None,
            }
        )

    export_data = {
        "version": "1.0",
        "export_type": "finished_goods",
        "export_date": export_date,
        "_meta": {
            "editable_fields": FINISHED_GOODS_CONTEXT_RICH_EDITABLE,
            "readonly_fields": FINISHED_GOODS_CONTEXT_RICH_READONLY,
        },
        "records": records,
    }

    # Write to file
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

    return ExportResult(
        export_type="finished_goods",
        record_count=len(records),
        output_path=str(output),
        export_date=export_date,
    )


# ============================================================================
# Convenience Function
# ============================================================================


def export_all_context_rich(
    output_dir: str,
    session: Optional[Session] = None,
) -> Dict[str, ExportResult]:
    """
    Export all context-rich files to a directory.

    Args:
        output_dir: Directory for output files
        session: Optional SQLAlchemy session for transactional composition

    Returns:
        Dictionary mapping entity type to ExportResult
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results = {}

    # Export all context-rich files
    results["products"] = export_products_context_rich(
        str(output_path / "aug_products.json"),
        session=session,
    )
    results["inventory"] = export_inventory_context_rich(
        str(output_path / "aug_inventory.json"),
        session=session,
    )
    results["purchases"] = export_purchases_context_rich(
        str(output_path / "aug_purchases.json"),
        session=session,
    )
    results["ingredients"] = export_ingredients_context_rich(
        str(output_path / "aug_ingredients.json"),
        session=session,
    )
    results["materials"] = export_materials_context_rich(
        str(output_path / "aug_materials.json"),
        session=session,
    )
    results["recipes"] = export_recipes_context_rich(
        str(output_path / "aug_recipes.json"),
        session=session,
    )
    results["material_products"] = export_material_products_context_rich(
        str(output_path / "aug_material_products.json"),
        session=session,
    )
    results["finished_units"] = export_finished_units_context_rich(
        str(output_path / "aug_finished_units.json"),
        session=session,
    )
    results["finished_goods"] = export_finished_goods_context_rich(
        str(output_path / "aug_finished_goods.json"),
        session=session,
    )

    return results
