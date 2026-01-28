"""
Coordinated Export Service - Export database to individual entity files with manifest.

Provides normalized exports for database backup and migration. Each entity type
exports to its own JSON file with FK resolution fields (id + slug/name) for
portable import resolution.

Usage:
    from src.services.coordinated_export_service import export_complete

    # Export to directory with manifest
    manifest = export_complete("export_2025-12-25/")
    print(f"Exported {len(manifest.files)} files")

    # Export with ZIP archive
    zip_path = export_complete("export_2025-12-25/", create_zip=True)
"""

import hashlib
import json
import logging
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from src.utils.datetime_utils import utc_now
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy.orm import Session, joinedload

logger = logging.getLogger(__name__)

from src.models.ingredient import Ingredient
from src.models.inventory_item import InventoryItem
from src.models.product import Product
from src.models.purchase import Purchase
from src.models.recipe import Recipe, RecipeIngredient, RecipeComponent
from src.models.supplier import Supplier
from src.models.material_category import MaterialCategory
from src.models.material_subcategory import MaterialSubcategory
from src.models.material import Material
from src.models.material_product import MaterialProduct
from src.models.material_unit import MaterialUnit
from src.models.material_purchase import MaterialPurchase
from src.models.material_inventory_item import MaterialInventoryItem
from src.models.finished_good import FinishedGood
from src.models.finished_unit import FinishedUnit
from src.models.event import Event, EventProductionTarget, EventAssemblyTarget
from src.models.production_run import ProductionRun
from src.models.inventory_depletion import InventoryDepletion
from src.services.database import session_scope
from src.utils.constants import APP_NAME, APP_VERSION


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class FileEntry:
    """Metadata for a single exported file."""

    filename: str
    entity_type: str
    record_count: int
    sha256: str
    dependencies: List[str]
    import_order: int


@dataclass
class ExportManifest:
    """Manifest for a coordinated export set."""

    version: str = "1.0"
    export_date: str = ""
    source: str = ""
    files: List[FileEntry] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert manifest to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "export_date": self.export_date,
            "source": self.source,
            "files": [
                {
                    "filename": f.filename,
                    "entity_type": f.entity_type,
                    "record_count": f.record_count,
                    "sha256": f.sha256,
                    "dependencies": f.dependencies,
                    "import_order": f.import_order,
                }
                for f in self.files
            ],
        }


# ============================================================================
# Constants
# ============================================================================

# Dependency order for import: (import_order, dependencies)
DEPENDENCY_ORDER = {
    "suppliers": (1, []),
    "ingredients": (2, []),
    "products": (3, ["ingredients"]),
    "recipes": (4, ["ingredients"]),
    "finished_units": (5, ["recipes"]),  # Feature 056: Must be after recipes
    "purchases": (6, ["products", "suppliers"]),
    "inventory_items": (7, ["products", "purchases"]),
    # Feature 047: Materials Management System
    "material_categories": (8, []),
    "material_subcategories": (9, ["material_categories"]),
    "materials": (10, ["material_subcategories"]),
    "material_products": (11, ["materials", "suppliers"]),
    "material_units": (12, ["materials"]),
    "material_purchases": (13, ["material_products", "suppliers"]),
    # Feature 058: Material inventory items (FIFO)
    "material_inventory_items": (14, ["material_products", "material_purchases"]),
    # Feature 049: Complete backup entities
    "finished_goods": (15, []),
    "events": (16, []),
    "production_runs": (17, ["recipes", "events", "finished_units"]),
    "inventory_depletions": (18, ["inventory_items"]),
}


# ============================================================================
# Helper Functions
# ============================================================================


def _calculate_checksum(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file."""
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _resolve_recipe(
    recipe_slug: Optional[str],
    recipe_name: Optional[str],
    session: Session,
    context: str = "",
) -> Optional[int]:
    """Resolve recipe to ID using slug -> previous_slug -> name fallback.

    Feature 080: Centralized recipe resolution with fallback chain for imports.

    Args:
        recipe_slug: Recipe slug from import data
        recipe_name: Recipe name from import data (fallback)
        session: Database session
        context: Context string for logging (e.g., "FinishedUnit 'Cookies'")

    Returns:
        Recipe ID if found, None otherwise
    """
    from src.models.recipe import Recipe

    if not recipe_slug and not recipe_name:
        logger.warning(f"{context}: No recipe_slug or recipe_name provided")
        return None

    # Try slug first
    if recipe_slug:
        recipe = session.query(Recipe).filter(Recipe.slug == recipe_slug).first()
        if recipe:
            return recipe.id

        # Try previous_slug
        recipe = session.query(Recipe).filter(Recipe.previous_slug == recipe_slug).first()
        if recipe:
            logger.info(
                f"{context}: Resolved recipe '{recipe_slug}' via previous_slug fallback"
            )
            return recipe.id

    # Try name (legacy fallback)
    if recipe_name:
        recipe = session.query(Recipe).filter(Recipe.name == recipe_name).first()
        if recipe:
            if recipe_slug:
                logger.info(
                    f"{context}: Resolved recipe via name fallback "
                    f"(slug '{recipe_slug}' not found)"
                )
            return recipe.id

    # Not found
    logger.error(
        f"{context}: Recipe not found - slug='{recipe_slug}', name='{recipe_name}'"
    )
    return None


def _write_entity_file(
    output_dir: Path,
    entity_type: str,
    records: List[Dict],
) -> FileEntry:
    """
    Write entity records to JSON file and return FileEntry.

    Args:
        output_dir: Directory to write file to
        entity_type: Type of entity (e.g., "suppliers")
        records: List of record dictionaries

    Returns:
        FileEntry with metadata including checksum
    """
    filename = f"{entity_type}.json"
    file_path = output_dir / filename

    data = {
        "version": "1.0",
        "entity_type": entity_type,
        "records": records,
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    import_order, dependencies = DEPENDENCY_ORDER.get(entity_type, (99, []))

    return FileEntry(
        filename=filename,
        entity_type=entity_type,
        record_count=len(records),
        sha256=_calculate_checksum(file_path),
        dependencies=dependencies,
        import_order=import_order,
    )


# ============================================================================
# Entity Export Functions
# ============================================================================


def _export_suppliers(output_dir: Path, session: Session) -> FileEntry:
    """Export all suppliers to JSON file."""
    suppliers = session.query(Supplier).all()

    records = []
    for s in suppliers:
        records.append(
            {
                "uuid": str(s.uuid) if s.uuid else None,
                "name": s.name,
                "slug": s.slug,
                "supplier_type": s.supplier_type,
                "website_url": s.website_url,
                "street_address": s.street_address,
                "city": s.city,
                "state": s.state,
                "zip_code": s.zip_code,
                "notes": s.notes,
                "is_active": s.is_active,
            }
        )

    return _write_entity_file(output_dir, "suppliers", records)


def _export_ingredients(output_dir: Path, session: Session) -> FileEntry:
    """Export all ingredients to JSON file."""
    ingredients = session.query(Ingredient).all()

    records = []
    for i in ingredients:
        records.append(
            {
                "uuid": str(i.uuid) if i.uuid else None,
                "slug": i.slug,
                "display_name": i.display_name,
                "category": i.category,
                "description": i.description,
                "notes": i.notes,
                # Hierarchy fields (Feature 031)
                "hierarchy_level": i.hierarchy_level,
                "parent_slug": i.parent.slug if i.parent else None,
                # Density fields
                "density_volume_value": i.density_volume_value,
                "density_volume_unit": i.density_volume_unit,
                "density_weight_value": i.density_weight_value,
                "density_weight_unit": i.density_weight_unit,
                # Industry standard fields
                "foodon_id": i.foodon_id,
                "foodex2_code": i.foodex2_code,
                "langual_terms": i.langual_terms,
                "fdc_ids": i.fdc_ids,
                "moisture_pct": i.moisture_pct,
                "allergens": i.allergens,
                # Timestamps
                "date_added": i.date_added.isoformat() if i.date_added else None,
                "last_modified": i.last_modified.isoformat() if i.last_modified else None,
            }
        )

    return _write_entity_file(output_dir, "ingredients", records)


def _export_products(output_dir: Path, session: Session) -> FileEntry:
    """Export all products to JSON file with FK resolution fields."""
    products = (
        session.query(Product)
        .options(
            joinedload(Product.ingredient),
            joinedload(Product.preferred_supplier),
        )
        .all()
    )

    records = []
    for p in products:
        records.append(
            {
                "uuid": str(p.uuid) if p.uuid else None,
                # FK resolved by slug
                "ingredient_slug": p.ingredient.slug if p.ingredient else None,
                # Product fields
                "brand": p.brand,
                "product_name": p.product_name,
                "package_size": p.package_size,
                "package_type": p.package_type,
                "package_unit": p.package_unit,
                "package_unit_quantity": p.package_unit_quantity,
                "upc_code": p.upc_code,
                "supplier": p.supplier,
                "supplier_sku": p.supplier_sku,
                "preferred": p.preferred,
                # Feature 027 fields
                "preferred_supplier_slug": (
                    p.preferred_supplier.slug if p.preferred_supplier else None
                ),
                "is_hidden": p.is_hidden,
                # F057: Provisional product flag and slug
                "is_provisional": p.is_provisional,
                "slug": p.slug,
                # Industry standard fields
                "gtin": p.gtin,
                "brand_owner": p.brand_owner,
                "gpc_brick_code": p.gpc_brick_code,
                "net_content_value": p.net_content_value,
                "net_content_uom": p.net_content_uom,
                "country_of_sale": p.country_of_sale,
                "off_id": p.off_id,
                "notes": p.notes,
                # Timestamps
                "date_added": p.date_added.isoformat() if p.date_added else None,
                "last_modified": p.last_modified.isoformat() if p.last_modified else None,
            }
        )

    return _write_entity_file(output_dir, "products", records)


def _export_recipes(output_dir: Path, session: Session) -> FileEntry:
    """Export all recipes with ingredients and components to JSON file."""
    recipes = (
        session.query(Recipe)
        .options(
            joinedload(Recipe.recipe_ingredients).joinedload(RecipeIngredient.ingredient),
            joinedload(Recipe.recipe_components).joinedload(RecipeComponent.component_recipe),
        )
        .all()
    )

    records = []
    for r in recipes:
        # Build ingredient list with FK resolution fields
        ingredients = []
        for ri in r.recipe_ingredients:
            ingredients.append(
                {
                    "ingredient_slug": ri.ingredient.slug if ri.ingredient else None,
                    "quantity": ri.quantity,
                    "unit": ri.unit,
                    "notes": ri.notes,
                }
            )

        # Build component list with FK resolution fields
        # Feature 080: Add component_recipe_slug for portable identification
        components = []
        for rc in r.recipe_components:
            components.append(
                {
                    "component_recipe_slug": (
                        rc.component_recipe.slug if rc.component_recipe else None
                    ),
                    "component_recipe_name": (
                        rc.component_recipe.name if rc.component_recipe else None
                    ),
                    "quantity": rc.quantity,
                    "notes": rc.notes,
                    "sort_order": rc.sort_order,
                }
            )

        # F056: yield_quantity, yield_unit, yield_description removed
        # Yield data is now in FinishedUnit records
        # Feature 080: Add slug and previous_slug for portable identification
        records.append(
            {
                "uuid": str(r.uuid) if r.uuid else None,
                "name": r.name,
                "slug": r.slug,
                "previous_slug": r.previous_slug,
                "category": r.category,
                "source": r.source,
                "estimated_time_minutes": r.estimated_time_minutes,
                "notes": r.notes,
                "is_archived": r.is_archived,
                "is_production_ready": r.is_production_ready,
                # Nested data
                "ingredients": ingredients,
                "components": components,
                # Timestamps
                "date_added": r.date_added.isoformat() if r.date_added else None,
                "last_modified": r.last_modified.isoformat() if r.last_modified else None,
            }
        )

    return _write_entity_file(output_dir, "recipes", records)


def _export_purchases(output_dir: Path, session: Session) -> FileEntry:
    """Export all purchases to JSON file with FK resolution fields."""
    purchases = (
        session.query(Purchase)
        .options(
            joinedload(Purchase.product).joinedload(Product.ingredient),
            joinedload(Purchase.supplier),
        )
        .all()
    )

    records = []
    for p in purchases:
        # Build product resolution key
        product_slug = None
        if p.product and p.product.ingredient:
            product_slug = f"{p.product.ingredient.slug}:{p.product.brand}:{p.product.package_unit_quantity}:{p.product.package_unit}"

        records.append(
            {
                "uuid": str(p.uuid) if p.uuid else None,
                # FK resolved by slugs
                "product_slug": product_slug,
                "supplier_slug": p.supplier.slug if p.supplier else None,
                # Purchase fields
                "purchase_date": p.purchase_date.isoformat() if p.purchase_date else None,
                "unit_price": str(p.unit_price) if p.unit_price else None,
                "quantity_purchased": p.quantity_purchased,
                "notes": p.notes,
                # Timestamps
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
        )

    return _write_entity_file(output_dir, "purchases", records)


def _export_inventory_items(output_dir: Path, session: Session) -> FileEntry:
    """Export all inventory items to JSON file with FK resolution fields."""
    items = (
        session.query(InventoryItem)
        .options(
            joinedload(InventoryItem.product).joinedload(Product.ingredient),
            joinedload(InventoryItem.purchase),
        )
        .all()
    )

    records = []
    for item in items:
        # Build product resolution key
        product_slug = None
        if item.product and item.product.ingredient:
            product_slug = f"{item.product.ingredient.slug}:{item.product.brand}:{item.product.package_unit_quantity}:{item.product.package_unit}"

        records.append(
            {
                "uuid": str(item.uuid) if item.uuid else None,
                # FK resolved by slug
                "product_slug": product_slug,
                # Inventory fields
                "quantity": item.quantity,
                "unit_cost": item.unit_cost,
                "purchase_date": item.purchase_date.isoformat() if item.purchase_date else None,
                "expiration_date": (
                    item.expiration_date.isoformat() if item.expiration_date else None
                ),
                "opened_date": item.opened_date.isoformat() if item.opened_date else None,
                "location": item.location,
                "lot_or_batch": item.lot_or_batch,
                "notes": item.notes,
                # Timestamps
                "last_updated": item.last_updated.isoformat() if item.last_updated else None,
            }
        )

    return _write_entity_file(output_dir, "inventory_items", records)


# ============================================================================
# Material Export Functions (Feature 047)
# ============================================================================


def _export_material_categories(output_dir: Path, session: Session) -> FileEntry:
    """Export all material categories to JSON file."""
    categories = session.query(MaterialCategory).all()

    records = []
    for c in categories:
        records.append(
            {
                "uuid": str(c.uuid) if c.uuid else None,
                "name": c.name,
                "slug": c.slug,
                "description": c.description,
                "sort_order": c.sort_order,
            }
        )

    return _write_entity_file(output_dir, "material_categories", records)


def _export_material_subcategories(output_dir: Path, session: Session) -> FileEntry:
    """Export all material subcategories to JSON file with FK resolution."""
    subcategories = (
        session.query(MaterialSubcategory).options(joinedload(MaterialSubcategory.category)).all()
    )

    records = []
    for s in subcategories:
        records.append(
            {
                "uuid": str(s.uuid) if s.uuid else None,
                "category_slug": s.category.slug if s.category else None,
                "name": s.name,
                "slug": s.slug,
                "description": s.description,
                "sort_order": s.sort_order,
            }
        )

    return _write_entity_file(output_dir, "material_subcategories", records)


def _export_materials(output_dir: Path, session: Session) -> FileEntry:
    """Export all materials to JSON file with FK resolution."""
    materials = session.query(Material).options(joinedload(Material.subcategory)).all()

    records = []
    for m in materials:
        records.append(
            {
                "uuid": str(m.uuid) if m.uuid else None,
                "subcategory_slug": m.subcategory.slug if m.subcategory else None,
                "name": m.name,
                "slug": m.slug,
                "base_unit_type": m.base_unit_type,
                "description": m.description,
            }
        )

    return _write_entity_file(output_dir, "materials", records)


def _export_material_products(output_dir: Path, session: Session) -> FileEntry:
    """Export all material products to JSON file with FK resolution."""
    products = (
        session.query(MaterialProduct)
        .options(
            joinedload(MaterialProduct.material),
            joinedload(MaterialProduct.supplier),
        )
        .all()
    )

    records = []
    for p in products:
        # Feature 058: Removed current_inventory, weighted_avg_cost, inventory_value
        # These are now tracked via MaterialInventoryItem (FIFO)
        records.append(
            {
                "uuid": str(p.uuid) if p.uuid else None,
                "material_slug": p.material.slug if p.material else None,
                "name": p.name,
                "slug": p.slug,
                "brand": p.brand,
                "package_quantity": p.package_quantity,
                "package_unit": p.package_unit,
                "quantity_in_base_units": p.quantity_in_base_units,
                "supplier_slug": p.supplier.slug if p.supplier else None,
                "sku": p.sku,
                "is_hidden": p.is_hidden,
                "notes": p.notes,
            }
        )

    return _write_entity_file(output_dir, "material_products", records)


def _export_material_units(output_dir: Path, session: Session) -> FileEntry:
    """Export all material units to JSON file with FK resolution."""
    units = session.query(MaterialUnit).options(joinedload(MaterialUnit.material)).all()

    records = []
    for u in units:
        records.append(
            {
                "uuid": str(u.uuid) if u.uuid else None,
                "material_slug": u.material.slug if u.material else None,
                "name": u.name,
                "slug": u.slug,
                "quantity_per_unit": u.quantity_per_unit,
                "description": u.description,
            }
        )

    return _write_entity_file(output_dir, "material_units", records)


def _export_material_purchases(output_dir: Path, session: Session) -> FileEntry:
    """Export all material purchases to JSON file with FK resolution."""
    purchases = (
        session.query(MaterialPurchase)
        .options(
            joinedload(MaterialPurchase.product),
            joinedload(MaterialPurchase.supplier),
        )
        .all()
    )

    records = []
    for p in purchases:
        records.append(
            {
                "uuid": str(p.uuid) if p.uuid else None,
                "product_slug": p.product.slug if p.product else None,
                "supplier_slug": p.supplier.slug if p.supplier else None,
                "purchase_date": p.purchase_date.isoformat() if p.purchase_date else None,
                "packages_purchased": p.packages_purchased,
                "package_price": str(p.package_price) if p.package_price else None,
                "units_added": p.units_added,
                "unit_cost": str(p.unit_cost) if p.unit_cost else None,
                "notes": p.notes,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
        )

    return _write_entity_file(output_dir, "material_purchases", records)


def _export_material_inventory_items(output_dir: Path, session: Session) -> FileEntry:
    """Export all material inventory items (FIFO lots) to JSON file with FK resolution.

    Feature 058: MaterialInventoryItem tracks individual inventory lots for FIFO.
    """
    items = (
        session.query(MaterialInventoryItem)
        .options(
            joinedload(MaterialInventoryItem.product),
            joinedload(MaterialInventoryItem.purchase),
        )
        .all()
    )

    records = []
    for item in items:
        records.append(
            {
                "uuid": str(item.uuid) if item.uuid else None,
                "product_slug": item.product.slug if item.product else None,
                "purchase_uuid": (
                    str(item.purchase.uuid) if item.purchase and item.purchase.uuid else None
                ),
                "quantity_purchased": item.quantity_purchased,
                "quantity_remaining": item.quantity_remaining,
                "cost_per_unit": str(item.cost_per_unit) if item.cost_per_unit else None,
                "purchase_date": item.purchase_date.isoformat() if item.purchase_date else None,
                "location": item.location,
                "notes": item.notes,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
        )

    return _write_entity_file(output_dir, "material_inventory_items", records)


# ============================================================================
# Complete Backup Export Functions (Feature 049)
# ============================================================================


def _export_finished_goods(output_dir: Path, session: Session) -> FileEntry:
    """Export all finished goods to JSON file."""
    goods = session.query(FinishedGood).all()

    records = []
    for g in goods:
        records.append(
            {
                "uuid": str(g.uuid) if g.uuid else None,
                "slug": g.slug,
                "display_name": g.display_name,
                "description": g.description,
                "assembly_type": g.assembly_type.value if g.assembly_type else None,
                "packaging_instructions": g.packaging_instructions,
                "inventory_count": g.inventory_count,
                "notes": g.notes,
                "created_at": g.created_at.isoformat() if g.created_at else None,
                "updated_at": g.updated_at.isoformat() if g.updated_at else None,
            }
        )

    return _write_entity_file(output_dir, "finished_goods", records)


def _export_finished_units(output_dir: Path, session: Session) -> FileEntry:
    """Export all finished units to JSON file with FK resolution.

    Feature 056: FinishedUnits are the single source of truth for yield tracking.
    Feature 080: Recipe reference uses recipe_slug for portable identification,
    with recipe_name kept for backward compatibility.
    """
    units = session.query(FinishedUnit).options(joinedload(FinishedUnit.recipe)).all()

    records = []
    for fu in units:
        records.append(
            {
                "uuid": str(fu.uuid) if fu.uuid else None,
                "slug": fu.slug,
                "display_name": fu.display_name,
                # Feature 080: FK resolved by recipe slug (preferred) or name (backward compat)
                "recipe_slug": fu.recipe.slug if fu.recipe else None,
                "recipe_name": fu.recipe.name if fu.recipe else None,
                "category": fu.category,
                "yield_mode": fu.yield_mode.value if fu.yield_mode else None,
                "items_per_batch": fu.items_per_batch,
                "item_unit": fu.item_unit,
                "batch_percentage": float(fu.batch_percentage) if fu.batch_percentage else None,
                "portion_description": fu.portion_description,
                "inventory_count": fu.inventory_count,
                "description": fu.description,
                "notes": fu.notes,
            }
        )

    return _write_entity_file(output_dir, "finished_units", records)


def _export_events(output_dir: Path, session: Session) -> FileEntry:
    """Export all events with production/assembly targets to JSON file."""
    events = (
        session.query(Event)
        .options(
            joinedload(Event.production_targets).joinedload(EventProductionTarget.recipe),
            joinedload(Event.assembly_targets).joinedload(EventAssemblyTarget.finished_good),
        )
        .all()
    )

    records = []
    for e in events:
        # Build production targets list
        # Feature 080: Add recipe_slug for portable identification
        production_targets = []
        for pt in e.production_targets:
            production_targets.append(
                {
                    "recipe_slug": pt.recipe.slug if pt.recipe else None,
                    "recipe_name": pt.recipe.name if pt.recipe else None,
                    "target_batches": pt.target_batches,
                    "notes": pt.notes,
                }
            )

        # Build assembly targets list
        assembly_targets = []
        for at in e.assembly_targets:
            assembly_targets.append(
                {
                    "finished_good_slug": at.finished_good.slug if at.finished_good else None,
                    "target_quantity": at.target_quantity,
                    "notes": at.notes,
                }
            )

        records.append(
            {
                "uuid": str(e.uuid) if e.uuid else None,
                "name": e.name,
                "event_date": e.event_date.isoformat() if e.event_date else None,
                "year": e.year,
                "output_mode": e.output_mode.value if e.output_mode else None,
                "notes": e.notes,
                "date_added": e.date_added.isoformat() if e.date_added else None,
                "last_modified": e.last_modified.isoformat() if e.last_modified else None,
                # Nested targets
                "production_targets": production_targets,
                "assembly_targets": assembly_targets,
            }
        )

    return _write_entity_file(output_dir, "events", records)


def _export_production_runs(output_dir: Path, session: Session) -> FileEntry:
    """Export all production runs to JSON file with FK resolution.

    Feature 080: Recipe reference uses recipe_slug for portable identification,
    with recipe_name kept for backward compatibility.
    """
    runs = (
        session.query(ProductionRun)
        .options(
            joinedload(ProductionRun.recipe),
            joinedload(ProductionRun.event),
            joinedload(ProductionRun.finished_unit),
        )
        .all()
    )

    records = []
    for r in runs:
        records.append(
            {
                "uuid": str(r.uuid) if r.uuid else None,
                # Feature 080: FK resolved by slug (preferred) or name (backward compat)
                "recipe_slug": r.recipe.slug if r.recipe else None,
                "recipe_name": r.recipe.name if r.recipe else None,
                "finished_unit_slug": r.finished_unit.slug if r.finished_unit else None,
                "event_name": r.event.name if r.event else None,
                # Production data
                "num_batches": r.num_batches,
                "expected_yield": r.expected_yield,
                "actual_yield": r.actual_yield,
                "produced_at": r.produced_at.isoformat() if r.produced_at else None,
                "notes": r.notes,
                "production_status": r.production_status,
                "loss_quantity": r.loss_quantity,
                # Cost data
                "total_ingredient_cost": (
                    str(r.total_ingredient_cost) if r.total_ingredient_cost else None
                ),
                "per_unit_cost": str(r.per_unit_cost) if r.per_unit_cost else None,
            }
        )

    return _write_entity_file(output_dir, "production_runs", records)


def _export_inventory_depletions(output_dir: Path, session: Session) -> FileEntry:
    """Export all inventory depletions to JSON file with FK resolution."""
    depletions = (
        session.query(InventoryDepletion)
        .options(
            joinedload(InventoryDepletion.inventory_item),
        )
        .all()
    )

    records = []
    for d in depletions:
        # Build inventory item resolution
        inventory_item_ref = None
        if d.inventory_item and d.inventory_item.product:
            product = d.inventory_item.product
            if product.ingredient:
                inventory_item_ref = f"{product.ingredient.slug}:{product.brand}:{product.package_unit_quantity}:{product.package_unit}"

        records.append(
            {
                "uuid": str(d.uuid) if d.uuid else None,
                # FK resolved by reference
                "inventory_item_ref": inventory_item_ref,
                # Depletion data
                "quantity_depleted": str(d.quantity_depleted) if d.quantity_depleted else None,
                "depletion_reason": d.depletion_reason,
                "depletion_date": d.depletion_date.isoformat() if d.depletion_date else None,
                "notes": d.notes,
                "cost": str(d.cost) if d.cost else None,
                # Audit fields
                "created_by": d.created_by,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
        )

    return _write_entity_file(output_dir, "inventory_depletions", records)


# ============================================================================
# Main Export Functions
# ============================================================================


def export_complete(
    output_path: str,
    create_zip: bool = False,
    session: Optional[Session] = None,
) -> ExportManifest:
    """
    Export complete database to individual entity files with manifest.

    Creates a directory containing:
    - manifest.json - Export metadata with checksums and import order
    - suppliers.json - All suppliers
    - ingredients.json - All ingredients
    - products.json - All products with ingredient FK resolution
    - recipes.json - All recipes with ingredient/component FK resolution
    - purchases.json - All purchases with product/supplier FK resolution
    - inventory_items.json - All inventory items with product FK resolution

    Args:
        output_path: Directory path for export files
        create_zip: If True, create ZIP archive and return path
        session: Optional SQLAlchemy session for transactional composition

    Returns:
        ExportManifest with metadata for all exported files
    """
    if session is not None:
        return _export_complete_impl(output_path, create_zip, session)
    with session_scope() as sess:
        return _export_complete_impl(output_path, create_zip, sess)


def _export_complete_impl(
    output_path: str,
    create_zip: bool,
    session: Session,
) -> ExportManifest:
    """Internal implementation of complete export."""
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize manifest
    manifest = ExportManifest(
        version="1.0",
        export_date=utc_now().isoformat() + "Z",
        source=f"{APP_NAME} v{APP_VERSION}",
    )

    # Export in dependency order
    manifest.files.append(_export_suppliers(output_dir, session))
    manifest.files.append(_export_ingredients(output_dir, session))
    manifest.files.append(_export_products(output_dir, session))
    manifest.files.append(_export_recipes(output_dir, session))
    # Feature 056: FinishedUnits after recipes (they reference recipes)
    manifest.files.append(_export_finished_units(output_dir, session))
    manifest.files.append(_export_purchases(output_dir, session))
    manifest.files.append(_export_inventory_items(output_dir, session))

    # Feature 047: Materials Management System
    manifest.files.append(_export_material_categories(output_dir, session))
    manifest.files.append(_export_material_subcategories(output_dir, session))
    manifest.files.append(_export_materials(output_dir, session))
    manifest.files.append(_export_material_products(output_dir, session))
    manifest.files.append(_export_material_units(output_dir, session))
    manifest.files.append(_export_material_purchases(output_dir, session))
    manifest.files.append(_export_material_inventory_items(output_dir, session))

    # Feature 049: Complete backup entities
    manifest.files.append(_export_finished_goods(output_dir, session))
    manifest.files.append(_export_events(output_dir, session))
    manifest.files.append(_export_production_runs(output_dir, session))
    manifest.files.append(_export_inventory_depletions(output_dir, session))

    # Sort files by import_order
    manifest.files.sort(key=lambda f: f.import_order)

    # Write manifest
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)

    # Create ZIP if requested
    if create_zip:
        zip_path = output_dir.with_suffix(".zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in output_dir.iterdir():
                zf.write(file, file.name)
        return manifest

    return manifest


def validate_export(export_path: str) -> Dict:
    """
    Validate an export directory by checking manifest checksums.

    Args:
        export_path: Path to export directory or ZIP file

    Returns:
        Dictionary with validation results:
        - valid: True if all checksums match
        - files_checked: Number of files validated
        - errors: List of any checksum mismatches
    """
    export_dir = Path(export_path)

    # Handle ZIP files
    if export_dir.suffix == ".zip":
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(export_dir, "r") as zf:
                zf.extractall(tmp)
            return validate_export(tmp)

    # Load manifest
    manifest_path = export_dir / "manifest.json"
    if not manifest_path.exists():
        return {
            "valid": False,
            "files_checked": 0,
            "errors": ["manifest.json not found"],
        }

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    errors = []
    files_checked = 0

    for file_entry in manifest_data.get("files", []):
        filename = file_entry["filename"]
        expected_checksum = file_entry["sha256"]
        file_path = export_dir / filename

        if not file_path.exists():
            errors.append(f"File not found: {filename}")
            continue

        actual_checksum = _calculate_checksum(file_path)
        files_checked += 1

        if actual_checksum != expected_checksum:
            errors.append(
                f"Checksum mismatch for {filename}: "
                f"expected {expected_checksum[:8]}..., got {actual_checksum[:8]}..."
            )

    return {
        "valid": len(errors) == 0,
        "files_checked": files_checked,
        "errors": errors,
    }


# ============================================================================
# Coordinated Import (Backup Restore)
# ============================================================================


def import_complete(
    import_path: str,
    session: Optional[Session] = None,
) -> Dict:
    """
    Import a complete backup from a coordinated export directory.

    Reads the manifest.json to determine import order, then imports each
    entity file in sequence. Uses replace mode - all existing data is cleared
    before import.

    Args:
        import_path: Path to export directory or manifest.json file

    Returns:
        Dictionary with import results:
        - successful: Total records imported
        - files_imported: Number of entity files processed
        - entity_counts: Per-entity record counts
        - errors: List of any import errors
    """
    if session is not None:
        return _import_complete_impl(import_path, session)
    with session_scope() as sess:
        return _import_complete_impl(import_path, sess)


def _import_complete_impl(
    import_path: str,
    session: Session,
) -> Dict:
    """Internal implementation of complete import."""
    from src.services import import_export_service

    import_dir = Path(import_path)

    # Handle if user selected manifest.json directly
    if import_dir.is_file() and import_dir.name == "manifest.json":
        import_dir = import_dir.parent

    # Load manifest
    manifest_path = import_dir / "manifest.json"
    if not manifest_path.exists():
        return {
            "successful": 0,
            "files_imported": 0,
            "entity_counts": {},
            "errors": [f"manifest.json not found in {import_dir}"],
        }

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    # Get files in import order
    files = manifest_data.get("files", [])
    files.sort(key=lambda f: f.get("import_order", 999))

    result = {
        "successful": 0,
        "files_imported": 0,
        "entity_counts": {},
        "errors": [],
        # F057: Track provisional products created during import
        "provisional_products_created": 0,
    }

    # Clear existing data first (replace mode)
    # Delete in reverse dependency order to avoid FK constraint violations
    from src.models.supplier import Supplier
    from src.models.ingredient import Ingredient
    from src.models.product import Product
    from src.models.recipe import Recipe, RecipeIngredient, RecipeComponent
    from src.models.purchase import Purchase
    from src.models.inventory_item import InventoryItem
    from src.models.material import Material
    from src.models.material_category import MaterialCategory
    from src.models.material_subcategory import MaterialSubcategory
    from src.models.material_product import MaterialProduct
    from src.models.material_unit import MaterialUnit
    from src.models.material_purchase import MaterialPurchase
    from src.models.finished_good import FinishedGood
    from src.models.event import Event
    from src.models.production_run import ProductionRun
    from src.models.inventory_depletion import InventoryDepletion

    # Delete in reverse dependency order
    session.query(InventoryDepletion).delete()
    session.query(ProductionRun).delete()
    session.query(Event).delete()
    session.query(FinishedGood).delete()
    session.query(FinishedUnit).delete()  # Feature 056: After ProductionRun (which references it)
    session.query(MaterialPurchase).delete()
    session.query(MaterialUnit).delete()
    session.query(MaterialProduct).delete()
    session.query(Material).delete()
    session.query(MaterialSubcategory).delete()
    session.query(MaterialCategory).delete()
    session.query(InventoryItem).delete()
    session.query(Purchase).delete()
    session.query(RecipeComponent).delete()
    session.query(RecipeIngredient).delete()
    session.query(Recipe).delete()
    session.query(Product).delete()
    session.query(Ingredient).delete()
    session.query(Supplier).delete()
    session.flush()

    # Import each file in dependency order
    for file_info in files:
        filename = file_info.get("filename")
        entity_type = file_info.get("entity_type")

        file_path = import_dir / filename
        if not file_path.exists():
            result["errors"].append(f"Missing file: {filename}")
            continue

        try:
            # Load the entity file
            with open(file_path, "r", encoding="utf-8") as f:
                entity_data = json.load(f)

            records = entity_data.get("records", [])
            record_count = len(records)

            # Import records for this entity type
            imported = _import_entity_records(entity_type, records, session)

            result["successful"] += imported
            result["files_imported"] += 1
            result["entity_counts"][entity_type] = imported

        except Exception as e:
            result["errors"].append(f"Error importing {filename}: {str(e)}")

    return result


def _parse_date(date_str: Optional[str]):
    """Parse ISO date string to Python date object.

    Args:
        date_str: Date string in ISO format (YYYY-MM-DD) or None

    Returns:
        date object or None if input is None/empty
    """
    if not date_str:
        return None
    from datetime import date

    # Handle both date-only and datetime strings
    date_part = date_str.split("T")[0] if "T" in date_str else date_str
    try:
        parts = date_part.split("-")
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError):
        return None


def _import_entity_records(
    entity_type: str,
    records: List[Dict],
    session: Session,
) -> int:
    """Import records for a specific entity type.

    Args:
        entity_type: Type of entity (e.g., "suppliers", "ingredients")
        records: List of record dictionaries
        session: Database session

    Returns:
        Number of records successfully imported
    """
    from src.models.supplier import Supplier
    from src.models.ingredient import Ingredient
    from src.models.product import Product
    from src.models.recipe import Recipe, RecipeIngredient, RecipeComponent
    from src.models.purchase import Purchase
    from src.models.inventory_item import InventoryItem
    from src.models.material import Material
    from src.models.material_category import MaterialCategory
    from src.models.material_subcategory import MaterialSubcategory
    from src.models.material_product import MaterialProduct
    from src.models.material_unit import MaterialUnit
    from src.models.material_purchase import MaterialPurchase
    from src.models.material_inventory_item import MaterialInventoryItem
    from src.models.finished_good import FinishedGood
    from src.models.event import Event
    from src.models.production_run import ProductionRun
    from src.models.inventory_depletion import InventoryDepletion

    imported_count = 0

    # Sort ingredients by hierarchy_level to ensure parents are imported before children
    if entity_type == "ingredients":
        records = sorted(records, key=lambda r: r.get("hierarchy_level", 2))

    for record in records:
        try:
            if entity_type == "suppliers":
                # Generate slug from name if not present (backward compatibility)
                name = record.get("name", "")
                slug = record.get("slug")
                if not slug and name:
                    from src.services.material_catalog_service import slugify

                    slug = slugify(name)
                obj = Supplier(
                    name=name,
                    slug=slug,
                    supplier_type=record.get("supplier_type", "physical"),
                    website_url=record.get("website_url"),
                    street_address=record.get("street_address"),
                    city=record.get("city"),
                    state=record.get("state"),
                    zip_code=record.get("zip_code"),
                    notes=record.get("notes"),
                    is_active=record.get("is_active", True),
                )
                session.add(obj)
                imported_count += 1

            elif entity_type == "ingredients":
                # Resolve parent FK by slug if present
                parent_id = None
                parent_slug = record.get("parent_slug")
                if parent_slug:
                    parent = (
                        session.query(Ingredient).filter(Ingredient.slug == parent_slug).first()
                    )
                    if parent:
                        parent_id = parent.id

                obj = Ingredient(
                    slug=record.get("slug"),
                    display_name=record.get("display_name"),
                    category=record.get("category"),
                    description=record.get("description"),
                    notes=record.get("notes"),
                    hierarchy_level=record.get("hierarchy_level", 2),
                    parent_ingredient_id=parent_id,
                    # Density fields
                    density_volume_value=record.get("density_volume_value"),
                    density_volume_unit=record.get("density_volume_unit"),
                    density_weight_value=record.get("density_weight_value"),
                    density_weight_unit=record.get("density_weight_unit"),
                    # Industry standard fields
                    foodon_id=record.get("foodon_id"),
                    foodex2_code=record.get("foodex2_code"),
                    langual_terms=record.get("langual_terms"),
                    fdc_ids=record.get("fdc_ids"),
                    moisture_pct=record.get("moisture_pct"),
                    allergens=record.get("allergens"),
                )
                session.add(obj)
                imported_count += 1

            elif entity_type == "products":
                # Resolve ingredient FK by slug
                ingredient_slug = record.get("ingredient_slug")
                ingredient = (
                    session.query(Ingredient).filter(Ingredient.slug == ingredient_slug).first()
                )
                if not ingredient:
                    continue  # Skip if FK not resolved

                # Resolve preferred_supplier FK - try slug first, fall back to ID
                preferred_supplier_id = None
                supplier_slug = record.get("preferred_supplier_slug")
                if supplier_slug:
                    supplier = (
                        session.query(Supplier).filter(Supplier.slug == supplier_slug).first()
                    )
                    if supplier:
                        preferred_supplier_id = supplier.id
                if not preferred_supplier_id:
                    # Fall back to ID-based resolution (legacy support)
                    old_supplier_id = record.get("preferred_supplier_id")
                    if old_supplier_id:
                        supplier = (
                            session.query(Supplier).filter(Supplier.id == old_supplier_id).first()
                        )
                        if supplier:
                            preferred_supplier_id = supplier.id

                obj = Product(
                    ingredient_id=ingredient.id,
                    brand=record.get("brand"),
                    product_name=record.get("product_name"),
                    package_unit=record.get("package_unit"),
                    package_unit_quantity=record.get("package_unit_quantity"),
                    package_size=record.get("package_size"),
                    upc_code=record.get("upc_code"),
                    gtin=record.get("gtin"),
                    preferred_supplier_id=preferred_supplier_id,
                    preferred=record.get("preferred", False),
                    is_hidden=record.get("is_hidden", False),
                    # F057: Import provisional flag and slug
                    is_provisional=record.get("is_provisional", False),
                    slug=record.get("slug"),
                    package_type=record.get("package_type"),
                    supplier=record.get("supplier"),
                    supplier_sku=record.get("supplier_sku"),
                    notes=record.get("notes"),
                )
                session.add(obj)
                imported_count += 1

            elif entity_type == "recipes":
                # F056: yield_quantity, yield_unit, yield_description removed
                # Import files may still have these for backward compat, but they're ignored
                # F080: Import slug and previous_slug fields

                recipe_name = record.get("name", "")
                recipe_slug = record.get("slug")
                previous_slug = record.get("previous_slug")

                # Generate slug if not provided (legacy export)
                if not recipe_slug and recipe_name:
                    from src.services.recipe_service import _generate_unique_slug

                    recipe_slug = _generate_unique_slug(recipe_name, session)
                    logger.info(f"Generated slug '{recipe_slug}' for recipe '{recipe_name}'")

                obj = Recipe(
                    name=recipe_name,
                    slug=recipe_slug,
                    previous_slug=previous_slug,
                    category=record.get("category"),
                    source=record.get("source"),
                    estimated_time_minutes=record.get("estimated_time_minutes"),
                    notes=record.get("notes"),
                    is_archived=record.get("is_archived", False),
                    is_production_ready=record.get("is_production_ready", True),
                )
                session.add(obj)
                session.flush()

                # Add recipe ingredients (export uses "ingredients" key)
                for ri in record.get("ingredients", []):
                    ing_slug = ri.get("ingredient_slug")
                    ingredient = (
                        session.query(Ingredient).filter(Ingredient.slug == ing_slug).first()
                    )
                    if ingredient:
                        ri_obj = RecipeIngredient(
                            recipe_id=obj.id,
                            ingredient_id=ingredient.id,
                            quantity=ri.get("quantity"),
                            unit=ri.get("unit"),
                            notes=ri.get("notes"),
                        )
                        session.add(ri_obj)

                # Add recipe components (export uses "components" key)
                # F080: Use slug-based resolution with fallback
                for rc in record.get("components", []):
                    comp_slug = rc.get("component_recipe_slug")
                    comp_name = rc.get("component_recipe_name")

                    component_id = _resolve_recipe(
                        comp_slug,
                        comp_name,
                        session,
                        context=f"RecipeComponent for '{recipe_name}'",
                    )

                    if component_id:
                        rc_obj = RecipeComponent(
                            recipe_id=obj.id,
                            component_recipe_id=component_id,
                            quantity=rc.get("quantity"),
                            notes=rc.get("notes"),
                            sort_order=rc.get("sort_order"),
                        )
                        session.add(rc_obj)

                imported_count += 1

            elif entity_type == "finished_units":
                # Feature 056: Import FinishedUnit records
                # Feature 080: Use slug-based recipe resolution
                from src.models.finished_unit import YieldMode

                # Resolve recipe FK by slug (with fallback)
                recipe_slug = record.get("recipe_slug")
                recipe_name = record.get("recipe_name")
                display_name = record.get("display_name", "unknown")

                recipe_id = _resolve_recipe(
                    recipe_slug,
                    recipe_name,
                    session,
                    context=f"FinishedUnit '{display_name}'",
                )

                if not recipe_id:
                    continue  # Skip if recipe not found

                # Parse yield_mode enum
                yield_mode_str = record.get("yield_mode")
                yield_mode = None
                if yield_mode_str:
                    try:
                        yield_mode = YieldMode(yield_mode_str)
                    except ValueError:
                        yield_mode = YieldMode.DISCRETE_COUNT  # Default

                obj = FinishedUnit(
                    recipe_id=recipe_id,
                    slug=record.get("slug"),
                    display_name=record.get("display_name"),
                    category=record.get("category"),
                    yield_mode=yield_mode,
                    items_per_batch=record.get("items_per_batch"),
                    item_unit=record.get("item_unit"),
                    batch_percentage=record.get("batch_percentage"),
                    portion_description=record.get("portion_description"),
                    inventory_count=record.get("inventory_count", 0),
                    description=record.get("description"),
                    notes=record.get("notes"),
                )
                session.add(obj)
                imported_count += 1

            elif entity_type == "purchases":
                # Resolve product FK
                product_slug = record.get("product_slug")
                if product_slug:
                    parts = product_slug.split(":")
                    if len(parts) >= 4:
                        ingredient = (
                            session.query(Ingredient).filter(Ingredient.slug == parts[0]).first()
                        )
                        if ingredient:
                            product = (
                                session.query(Product)
                                .filter(
                                    Product.ingredient_id == ingredient.id,
                                    Product.brand == (parts[1] if parts[1] else None),
                                    Product.package_unit == parts[3],
                                )
                                .first()
                            )
                            if product:
                                # Resolve supplier FK
                                supplier_name = record.get("supplier_name")
                                supplier = (
                                    session.query(Supplier)
                                    .filter(Supplier.name == supplier_name)
                                    .first()
                                )
                                if supplier:
                                    obj = Purchase(
                                        product_id=product.id,
                                        supplier_id=supplier.id,
                                        purchase_date=_parse_date(record.get("purchase_date")),
                                        unit_price=record.get("unit_price"),
                                        quantity_purchased=record.get("quantity_purchased"),
                                        notes=record.get("notes"),
                                    )
                                    session.add(obj)
                                    imported_count += 1

            elif entity_type == "inventory_items":
                # Similar FK resolution for inventory items
                product_slug = record.get("product_slug")
                if product_slug:
                    parts = product_slug.split(":")
                    if len(parts) >= 4:
                        ingredient = (
                            session.query(Ingredient).filter(Ingredient.slug == parts[0]).first()
                        )
                        if ingredient:
                            product = (
                                session.query(Product)
                                .filter(
                                    Product.ingredient_id == ingredient.id,
                                    Product.brand == (parts[1] if parts[1] else None),
                                    Product.package_unit == parts[3],
                                )
                                .first()
                            )
                            if product:
                                obj = InventoryItem(
                                    product_id=product.id,
                                    quantity=record.get("quantity"),
                                    unit_cost=record.get("unit_cost"),
                                    purchase_date=_parse_date(record.get("purchase_date")),
                                    expiration_date=_parse_date(record.get("expiration_date")),
                                    location=record.get("location"),
                                )
                                session.add(obj)
                                imported_count += 1

            elif entity_type == "material_categories":
                obj = MaterialCategory(
                    name=record.get("name"),
                    slug=record.get("slug"),
                    description=record.get("description"),
                )
                session.add(obj)
                imported_count += 1

            elif entity_type == "material_subcategories":
                # Resolve category FK
                category_slug = record.get("category_slug")
                category = (
                    session.query(MaterialCategory)
                    .filter(MaterialCategory.slug == category_slug)
                    .first()
                )
                if category:
                    obj = MaterialSubcategory(
                        category_id=category.id,
                        name=record.get("name"),
                        slug=record.get("slug"),
                        description=record.get("description"),
                    )
                    session.add(obj)
                    imported_count += 1

            elif entity_type == "materials":
                # Resolve subcategory FK
                subcategory_slug = record.get("subcategory_slug")
                subcategory = (
                    session.query(MaterialSubcategory)
                    .filter(MaterialSubcategory.slug == subcategory_slug)
                    .first()
                )
                if subcategory:
                    obj = Material(
                        subcategory_id=subcategory.id,
                        name=record.get("name"),
                        slug=record.get("slug"),
                        description=record.get("description"),
                        base_unit_type=record.get("base_unit_type"),
                    )
                    session.add(obj)
                    imported_count += 1

            elif entity_type == "material_products":
                # Resolve material FK
                material_slug = record.get("material_slug")
                material = session.query(Material).filter(Material.slug == material_slug).first()
                if material:
                    # Resolve supplier FK if present
                    supplier_id = None
                    supplier_name = record.get("supplier_name")
                    if supplier_name:
                        supplier = (
                            session.query(Supplier).filter(Supplier.name == supplier_name).first()
                        )
                        if supplier:
                            supplier_id = supplier.id

                    # Feature 058: Removed current_inventory, weighted_avg_cost
                    # Old exports may contain these fields - they are ignored
                    obj = MaterialProduct(
                        material_id=material.id,
                        name=record.get("name"),
                        slug=record.get("slug"),
                        brand=record.get("brand"),
                        sku=record.get("sku"),
                        package_unit=record.get("package_unit"),
                        package_quantity=record.get("package_quantity"),
                        quantity_in_base_units=record.get("quantity_in_base_units"),
                        supplier_id=supplier_id,
                        is_hidden=record.get("is_hidden", False),
                        notes=record.get("notes"),
                    )
                    session.add(obj)
                    imported_count += 1

            elif entity_type == "material_purchases":
                # Resolve product FK
                product_slug = record.get("product_slug")
                product = (
                    session.query(MaterialProduct)
                    .filter(MaterialProduct.slug == product_slug)
                    .first()
                )
                if product:
                    # Resolve supplier FK
                    supplier_id = None
                    supplier_slug = record.get("supplier_slug")
                    if supplier_slug:
                        supplier = (
                            session.query(Supplier).filter(Supplier.slug == supplier_slug).first()
                        )
                        if supplier:
                            supplier_id = supplier.id

                    obj = MaterialPurchase(
                        product_id=product.id,
                        supplier_id=supplier_id,
                        purchase_date=_parse_date(record.get("purchase_date")),
                        packages_purchased=record.get("packages_purchased"),
                        package_price=record.get("package_price"),
                        units_added=record.get("units_added"),
                        unit_cost=record.get("unit_cost"),
                        notes=record.get("notes"),
                    )
                    session.add(obj)
                    session.flush()  # Get ID for inventory item creation
                    imported_count += 1

            elif entity_type == "material_inventory_items":
                # Resolve product FK
                product_slug = record.get("product_slug")
                product = (
                    session.query(MaterialProduct)
                    .filter(MaterialProduct.slug == product_slug)
                    .first()
                )
                if product:
                    # Resolve purchase FK by UUID
                    purchase_id = None
                    purchase_uuid = record.get("purchase_uuid")
                    if purchase_uuid:
                        purchase = (
                            session.query(MaterialPurchase)
                            .filter(MaterialPurchase.uuid == purchase_uuid)
                            .first()
                        )
                        if purchase:
                            purchase_id = purchase.id

                    obj = MaterialInventoryItem(
                        material_product_id=product.id,
                        material_purchase_id=purchase_id,
                        quantity_purchased=record.get("quantity_purchased"),
                        quantity_remaining=record.get("quantity_remaining"),
                        cost_per_unit=record.get("cost_per_unit"),
                        purchase_date=_parse_date(record.get("purchase_date")),
                        location=record.get("location"),
                        notes=record.get("notes"),
                    )
                    session.add(obj)
                    imported_count += 1

            elif entity_type == "finished_goods":
                from src.models.finished_good import AssemblyType

                # Parse assembly_type enum
                assembly_type_str = record.get("assembly_type")
                assembly_type = None
                if assembly_type_str:
                    try:
                        assembly_type = AssemblyType(assembly_type_str)
                    except ValueError:
                        assembly_type = AssemblyType.SIMPLE

                obj = FinishedGood(
                    slug=record.get("slug"),
                    display_name=record.get("display_name"),
                    description=record.get("description"),
                    assembly_type=assembly_type,
                    packaging_instructions=record.get("packaging_instructions"),
                    inventory_count=record.get("inventory_count", 0),
                    notes=record.get("notes"),
                )
                session.add(obj)
                imported_count += 1

            elif entity_type == "events":
                from src.models.event import OutputMode, EventProductionTarget, EventAssemblyTarget
                from src.models.finished_good import FinishedGood

                # Parse output_mode enum
                output_mode_str = record.get("output_mode")
                output_mode = None
                if output_mode_str:
                    try:
                        output_mode = OutputMode(output_mode_str)
                    except ValueError:
                        pass

                event_name = record.get("name", "unknown")
                obj = Event(
                    name=event_name,
                    event_date=_parse_date(record.get("event_date")),
                    year=record.get("year"),
                    output_mode=output_mode,
                    notes=record.get("notes"),
                )
                session.add(obj)
                session.flush()  # Get event ID for FK references

                # Feature 080: Import production targets with slug resolution
                for target_data in record.get("production_targets", []):
                    recipe_slug = target_data.get("recipe_slug")
                    recipe_name = target_data.get("recipe_name")

                    recipe_id = _resolve_recipe(
                        recipe_slug,
                        recipe_name,
                        session,
                        context=f"EventProductionTarget for event '{event_name}'",
                    )

                    if recipe_id:
                        target = EventProductionTarget(
                            event_id=obj.id,
                            recipe_id=recipe_id,
                            target_batches=target_data.get("target_batches"),
                            notes=target_data.get("notes"),
                        )
                        session.add(target)

                # Import assembly targets
                for target_data in record.get("assembly_targets", []):
                    fg_slug = target_data.get("finished_good_slug")
                    if fg_slug:
                        fg = (
                            session.query(FinishedGood)
                            .filter(FinishedGood.slug == fg_slug)
                            .first()
                        )
                        if fg:
                            target = EventAssemblyTarget(
                                event_id=obj.id,
                                finished_good_id=fg.id,
                                target_quantity=target_data.get("target_quantity"),
                                notes=target_data.get("notes"),
                            )
                            session.add(target)

                imported_count += 1

            elif entity_type == "production_runs":
                # Feature 080: Resolve recipe FK by slug (with fallback)
                recipe_slug = record.get("recipe_slug")
                recipe_name = record.get("recipe_name")

                recipe_id = _resolve_recipe(
                    recipe_slug,
                    recipe_name,
                    session,
                    context="ProductionRun",
                )

                if not recipe_id:
                    continue  # Skip if recipe not found

                finished_unit_slug = record.get("finished_unit_slug")
                finished_unit = (
                    session.query(FinishedUnit)
                    .filter(FinishedUnit.slug == finished_unit_slug)
                    .first()
                    if finished_unit_slug
                    else None
                )

                event_name = record.get("event_name")
                event = (
                    session.query(Event).filter(Event.name == event_name).first()
                    if event_name
                    else None
                )

                obj = ProductionRun(
                    recipe_id=recipe_id,
                    finished_unit_id=finished_unit.id if finished_unit else None,
                    event_id=event.id if event else None,
                    num_batches=record.get("num_batches"),
                    expected_yield=record.get("expected_yield"),
                    actual_yield=record.get("actual_yield"),
                    produced_at=_parse_date(record.get("produced_at")),
                    notes=record.get("notes"),
                    production_status=record.get("production_status"),
                    loss_quantity=record.get("loss_quantity"),
                    total_ingredient_cost=record.get("total_ingredient_cost"),
                    per_unit_cost=record.get("per_unit_cost"),
                )
                session.add(obj)
                imported_count += 1

            elif entity_type == "inventory_depletions":
                # Inventory depletions reference inventory_items by complex key
                # Skip for now as this requires complex FK resolution
                pass

            session.flush()

        except Exception:
            # Skip records that fail
            continue

    return imported_count
