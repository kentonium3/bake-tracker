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
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy.orm import Session, joinedload

from src.models.ingredient import Ingredient
from src.models.inventory_item import InventoryItem
from src.models.product import Product
from src.models.purchase import Purchase
from src.models.recipe import Recipe, RecipeIngredient, RecipeComponent
from src.models.supplier import Supplier
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
    "purchases": (5, ["products", "suppliers"]),
    "inventory_items": (6, ["products", "purchases"]),
}


# ============================================================================
# Helper Functions
# ============================================================================


def _calculate_checksum(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file."""
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


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
        records.append({
            "id": s.id,
            "uuid": str(s.uuid) if s.uuid else None,
            "name": s.name,
            "street_address": s.street_address,
            "city": s.city,
            "state": s.state,
            "zip_code": s.zip_code,
            "notes": s.notes,
            "is_active": s.is_active,
        })

    return _write_entity_file(output_dir, "suppliers", records)


def _export_ingredients(output_dir: Path, session: Session) -> FileEntry:
    """Export all ingredients to JSON file."""
    ingredients = session.query(Ingredient).all()

    records = []
    for i in ingredients:
        records.append({
            "id": i.id,
            "uuid": str(i.uuid) if i.uuid else None,
            "slug": i.slug,
            "display_name": i.display_name,
            "category": i.category,
            "description": i.description,
            "notes": i.notes,
            "is_packaging": i.is_packaging,
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
        })

    return _write_entity_file(output_dir, "ingredients", records)


def _export_products(output_dir: Path, session: Session) -> FileEntry:
    """Export all products to JSON file with FK resolution fields."""
    products = session.query(Product).options(
        joinedload(Product.ingredient),
        joinedload(Product.preferred_supplier),
    ).all()

    records = []
    for p in products:
        records.append({
            "id": p.id,
            "uuid": str(p.uuid) if p.uuid else None,
            # FK with resolution field
            "ingredient_id": p.ingredient_id,
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
            "preferred_supplier_id": p.preferred_supplier_id,
            "preferred_supplier_name": (
                p.preferred_supplier.name if p.preferred_supplier else None
            ),
            "is_hidden": p.is_hidden,
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
        })

    return _write_entity_file(output_dir, "products", records)


def _export_recipes(output_dir: Path, session: Session) -> FileEntry:
    """Export all recipes with ingredients and components to JSON file."""
    recipes = session.query(Recipe).options(
        joinedload(Recipe.recipe_ingredients).joinedload(RecipeIngredient.ingredient),
        joinedload(Recipe.recipe_components).joinedload(RecipeComponent.component_recipe),
    ).all()

    records = []
    for r in recipes:
        # Build ingredient list with FK resolution fields
        ingredients = []
        for ri in r.recipe_ingredients:
            ingredients.append({
                "ingredient_id": ri.ingredient_id,
                "ingredient_slug": ri.ingredient.slug if ri.ingredient else None,
                "quantity": ri.quantity,
                "unit": ri.unit,
                "notes": ri.notes,
            })

        # Build component list with FK resolution fields
        components = []
        for rc in r.recipe_components:
            components.append({
                "component_recipe_id": rc.component_recipe_id,
                "component_recipe_name": (
                    rc.component_recipe.name if rc.component_recipe else None
                ),
                "quantity": rc.quantity,
                "notes": rc.notes,
                "sort_order": rc.sort_order,
            })

        records.append({
            "id": r.id,
            "uuid": str(r.uuid) if r.uuid else None,
            "name": r.name,
            "category": r.category,
            "source": r.source,
            "yield_quantity": r.yield_quantity,
            "yield_unit": r.yield_unit,
            "yield_description": r.yield_description,
            "estimated_time_minutes": r.estimated_time_minutes,
            "notes": r.notes,
            "is_archived": r.is_archived,
            # Nested data
            "ingredients": ingredients,
            "components": components,
            # Timestamps
            "date_added": r.date_added.isoformat() if r.date_added else None,
            "last_modified": r.last_modified.isoformat() if r.last_modified else None,
        })

    return _write_entity_file(output_dir, "recipes", records)


def _export_purchases(output_dir: Path, session: Session) -> FileEntry:
    """Export all purchases to JSON file with FK resolution fields."""
    purchases = session.query(Purchase).options(
        joinedload(Purchase.product).joinedload(Product.ingredient),
        joinedload(Purchase.supplier),
    ).all()

    records = []
    for p in purchases:
        # Build product resolution key
        product_slug = None
        if p.product and p.product.ingredient:
            product_slug = f"{p.product.ingredient.slug}:{p.product.brand}:{p.product.package_unit_quantity}:{p.product.package_unit}"

        records.append({
            "id": p.id,
            "uuid": str(p.uuid) if p.uuid else None,
            # FK with resolution fields
            "product_id": p.product_id,
            "product_slug": product_slug,
            "supplier_id": p.supplier_id,
            "supplier_name": p.supplier.name if p.supplier else None,
            # Purchase fields
            "purchase_date": p.purchase_date.isoformat() if p.purchase_date else None,
            "unit_price": str(p.unit_price) if p.unit_price else None,
            "quantity_purchased": p.quantity_purchased,
            "notes": p.notes,
            # Timestamps
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })

    return _write_entity_file(output_dir, "purchases", records)


def _export_inventory_items(output_dir: Path, session: Session) -> FileEntry:
    """Export all inventory items to JSON file with FK resolution fields."""
    items = session.query(InventoryItem).options(
        joinedload(InventoryItem.product).joinedload(Product.ingredient),
        joinedload(InventoryItem.purchase),
    ).all()

    records = []
    for item in items:
        # Build product resolution key
        product_slug = None
        if item.product and item.product.ingredient:
            product_slug = f"{item.product.ingredient.slug}:{item.product.brand}:{item.product.package_unit_quantity}:{item.product.package_unit}"

        records.append({
            "id": item.id,
            "uuid": str(item.uuid) if item.uuid else None,
            # FK with resolution fields
            "product_id": item.product_id,
            "product_slug": product_slug,
            "purchase_id": item.purchase_id,
            # Inventory fields
            "quantity": item.quantity,
            "unit_cost": item.unit_cost,
            "purchase_date": item.purchase_date.isoformat() if item.purchase_date else None,
            "expiration_date": item.expiration_date.isoformat() if item.expiration_date else None,
            "opened_date": item.opened_date.isoformat() if item.opened_date else None,
            "location": item.location,
            "lot_or_batch": item.lot_or_batch,
            "notes": item.notes,
            # Timestamps
            "last_updated": item.last_updated.isoformat() if item.last_updated else None,
        })

    return _write_entity_file(output_dir, "inventory_items", records)


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
        export_date=datetime.utcnow().isoformat() + "Z",
        source=f"{APP_NAME} v{APP_VERSION}",
    )

    # Export in dependency order
    manifest.files.append(_export_suppliers(output_dir, session))
    manifest.files.append(_export_ingredients(output_dir, session))
    manifest.files.append(_export_products(output_dir, session))
    manifest.files.append(_export_recipes(output_dir, session))
    manifest.files.append(_export_purchases(output_dir, session))
    manifest.files.append(_export_inventory_items(output_dir, session))

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
