"""
Import/Export CLI Utility

Simple command-line interface for exporting and importing data.
No UI required - designed for programmatic and testing use.

BACKUP/RESTORE COMMANDS (16-entity coordinated backup):

    # Create timestamped backup
    python -m src.utils.import_export_cli backup -o ./backups/

    # Create backup as ZIP archive
    python -m src.utils.import_export_cli backup -o ./backups/ --zip

    # Restore from backup (WARNING: replaces all existing data)
    python -m src.utils.import_export_cli restore ./backups/backup_20260115/

    # List available backups
    python -m src.utils.import_export_cli backup-list --dir ./backups/

    # Validate backup integrity
    python -m src.utils.import_export_cli backup-validate ./backups/backup_20260115/

CONTEXT-RICH AUG COMMANDS (AI workflow support):

    # Export products with human-readable context
    python -m src.utils.import_export_cli aug-export -t products -o aug_products.json

    # Export all entity types
    python -m src.utils.import_export_cli aug-export -t all -o ./aug_exports/

    # Import with automatic FK resolution
    python -m src.utils.import_export_cli aug-import aug_products.json

    # Import with interactive FK resolution
    python -m src.utils.import_export_cli aug-import aug_products.json --interactive

    # Validate aug file format
    python -m src.utils.import_export_cli aug-validate aug_products.json

    AI Workflow Pattern:
    1. Export: aug-export -t products -o aug_products.json
    2. Modify: (external tool or AI modifies the JSON)
    3. Import: aug-import aug_products.json --skip-on-error

CATALOG COMMANDS (selective entity operations):

    # Export specific catalog entities
    python -m src.utils.import_export_cli catalog-export --entities ingredients,products

    # Export all catalog entities (7 types)
    python -m src.utils.import_export_cli catalog-export -o ./catalog/

    # Import catalog with augment mode (update nulls + add new)
    python -m src.utils.import_export_cli catalog-import ./catalog.json --mode augment

    # Import catalog with dry-run preview
    python -m src.utils.import_export_cli catalog-import ./catalog.json --dry-run

    # Validate catalog before import
    python -m src.utils.import_export_cli catalog-validate ./catalog.json

ENTITY-SPECIFIC EXPORTS:

    # Export individual entity types
    python -m src.utils.import_export_cli export-materials materials.json
    python -m src.utils.import_export_cli export-material-products material_products.json
    python -m src.utils.import_export_cli export-material-categories categories.json
    python -m src.utils.import_export_cli export-material-subcategories subcategories.json
    python -m src.utils.import_export_cli export-suppliers suppliers.json
    python -m src.utils.import_export_cli export-purchases purchases.json

LEGACY COMMANDS (v3.2 format):

    # Export all data (v3.2 format)
    python -m src.utils.import_export_cli export test_data.json

    # Export ingredients only
    python -m src.utils.import_export_cli export-ingredients ingredients.json

    # Import all data (requires v3.2 format)
    python -m src.utils.import_export_cli import test_data.json

    # Import with replace mode (clears existing data first)
    python -m src.utils.import_export_cli import test_data.json --mode replace

F030 COMMANDS (coordinated export/view):

    # Export complete database with manifest
    python -m src.utils.import_export_cli export-complete -o ./export_dir

    # Export complete database as ZIP
    python -m src.utils.import_export_cli export-complete -o ./export_dir --zip

    # Export denormalized view
    python -m src.utils.import_export_cli export-view -t products -o view_products.json

    # Validate export checksums
    python -m src.utils.import_export_cli validate-export ./export_dir

    # Import denormalized view
    python -m src.utils.import_export_cli import-view view_products.json

    # Import view with interactive FK resolution
    python -m src.utils.import_export_cli import-view view_products.json --interactive

    # Import view in dry-run mode
    python -m src.utils.import_export_cli import-view view_products.json --dry-run
"""

import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.database import initialize_app_database, session_scope
from src.services.import_export_service import (
    export_ingredients_to_json,
    export_recipes_to_json,
    export_finished_goods_to_json,
    export_bundles_to_json,
    export_packages_to_json,
    export_recipients_to_json,
    export_events_to_json,
    export_all_to_json,
    import_all_from_json_v4,
    ImportResult,
)


def check_import_risks(import_data: dict, is_coordinated: bool = False) -> dict:
    """Check for potential import risks (CASCADE deletes and RESTRICT violations).

    When importing parent entities without their children in replace mode,
    existing child records will be cascade-deleted (CASCADE) or the import
    will fail at the database level (RESTRICT). This function identifies
    both types of risks.

    Args:
        import_data: The parsed import file data (dict with entity keys)
                    or manifest data for coordinated imports
        is_coordinated: True if this is a coordinated (manifest-based) import

    Returns:
        Dict with keys:
        - cascade_risks: List of CASCADE risk dicts (data loss if proceed)
        - restrict_risks: List of RESTRICT risk dicts (import will fail)
    """
    from src.models.product import Product
    from src.models.material_product import MaterialProduct
    from src.models.ingredient import Ingredient
    from src.models.recipe import Recipe
    from src.models.recipe import RecipeIngredient

    cascade_risks = []
    restrict_risks = []

    # Determine which entities are in the import
    if is_coordinated:
        # Coordinated import: check manifest files list
        entities_in_import = set(import_data.get("entity_types", []))
    else:
        # Single file: check top-level keys
        entities_in_import = set(import_data.keys())

    with session_scope() as session:
        # CASCADE Check 1: Ingredients without Products
        has_ingredients = "ingredients" in entities_in_import
        has_products = "products" in entities_in_import

        if has_ingredients and not has_products:
            product_count = session.query(Product).count()
            if product_count > 0:
                cascade_risks.append(
                    {
                        "parent_entity": "ingredients",
                        "child_entity": "products",
                        "child_count": product_count,
                        "warning": "Products and their inventory items will be permanently deleted.",
                    }
                )

        # CASCADE Check 2: Materials without MaterialProducts
        has_materials = "materials" in entities_in_import
        has_material_products = "material_products" in entities_in_import

        if has_materials and not has_material_products:
            mp_count = session.query(MaterialProduct).count()
            if mp_count > 0:
                cascade_risks.append(
                    {
                        "parent_entity": "materials",
                        "child_entity": "material_products",
                        "child_count": mp_count,
                        "warning": "Material products will be permanently deleted.",
                    }
                )

        # RESTRICT Check: Ingredients referenced by recipes
        # RecipeIngredient has ondelete="RESTRICT" on ingredient_id FK
        has_recipes = "recipes" in entities_in_import

        if has_ingredients and not has_recipes:
            # Get ingredient slugs from the import file
            if is_coordinated:
                # For coordinated imports, we'd need to load the ingredients file
                # For now, we assume all ingredients are provided (conservative)
                import_ingredient_slugs = None
            else:
                # Get slugs from import data
                ingredients_data = import_data.get("ingredients", [])
                import_ingredient_slugs = {
                    ing.get("slug") for ing in ingredients_data if ing.get("slug")
                }

            # Find ingredients in DB that are referenced by recipes
            referenced_ingredients = (
                session.query(Ingredient).join(RecipeIngredient).distinct().all()
            )

            if referenced_ingredients:
                # Check which referenced ingredients are missing from import
                if import_ingredient_slugs is not None:
                    # For single-file imports, check what's missing
                    missing_ingredients = [
                        ing
                        for ing in referenced_ingredients
                        if ing.slug not in import_ingredient_slugs
                    ]
                else:
                    # For coordinated imports, assume we have all needed ingredients
                    missing_ingredients = []

                if missing_ingredients:
                    # Build details: ingredient -> recipes using it
                    ingredient_recipe_map = {}
                    for ing in missing_ingredients:
                        recipes_using = (
                            session.query(Recipe.name)
                            .join(RecipeIngredient)
                            .filter(RecipeIngredient.ingredient_id == ing.id)
                            .all()
                        )
                        recipe_names = [r[0] for r in recipes_using]
                        ingredient_recipe_map[ing.name] = recipe_names

                    restrict_risks.append(
                        {
                            "risk_type": "ingredient_recipe",
                            "entity": "ingredients",
                            "blocking_entity": "recipes",
                            "missing_count": len(missing_ingredients),
                            "blocking_count": len(
                                set(
                                    r for recipes in ingredient_recipe_map.values() for r in recipes
                                )
                            ),
                            "details": ingredient_recipe_map,
                            "warning": "Import will fail - database RESTRICT constraint prevents deleting ingredients used by recipes.",
                            "remediation": [
                                "Add the missing ingredients to your import file",
                                "Include the recipes entity in the import (replaces recipes too)",
                                "Delete the affected recipes from the database before import",
                            ],
                        }
                    )

    return {"cascade_risks": cascade_risks, "restrict_risks": restrict_risks}


# Backward compatibility alias
def check_cascade_delete_risks(import_data: dict, is_coordinated: bool = False) -> list:
    """Deprecated: Use check_import_risks instead. Returns cascade_risks only."""
    return check_import_risks(import_data, is_coordinated)["cascade_risks"]


def result_to_json(result: ImportResult) -> dict:
    """Convert ImportResult to structured dict for JSON output.

    Used by CLI commands to provide machine-readable output for AI workflows
    and scripting. The output format is suitable for json.dumps().

    Args:
        result: ImportResult from an import operation

    Returns:
        dict suitable for json.dumps() with:
        - success: bool (True if no failures)
        - imported: int (successful count)
        - skipped: int (skipped count)
        - failed: int (error count)
        - errors: list[dict] (error details with field paths)
        - warnings: list[dict] (warning details)
        - entity_counts: dict (per-entity breakdown)
    """
    return {
        "success": result.failed == 0,
        "imported": result.successful,
        "skipped": result.skipped,
        "failed": result.failed,
        "errors": result.errors,
        "warnings": result.warnings,
        "entity_counts": result.entity_counts,
    }


def export_all(output_file: str):
    """Export all data in v3.2 format."""
    print(f"Exporting all data to {output_file}...")
    result = export_all_to_json(output_file)

    if result.success:
        print(result.get_summary())
        return 0
    else:
        print(f"ERROR: {result.error}")
        return 1


def export_ingredients(output_file: str):
    """Export ingredients only."""
    print(f"Exporting ingredients to {output_file}...")
    result = export_ingredients_to_json(output_file)

    if result.success:
        print(result.get_summary())
        return 0
    else:
        print(f"ERROR: {result.error}")
        return 1


def export_recipes(output_file: str):
    """Export recipes only."""
    print(f"Exporting recipes to {output_file}...")
    result = export_recipes_to_json(output_file)

    if result.success:
        print(result.get_summary())
        return 0
    else:
        print(f"ERROR: {result.error}")
        return 1


def export_finished_goods(output_file: str):
    """Export finished goods only."""
    print(f"Exporting finished goods to {output_file}...")
    result = export_finished_goods_to_json(output_file)

    if result.success:
        print(result.get_summary())
        return 0
    else:
        print(f"ERROR: {result.error}")
        return 1


def export_bundles(output_file: str):
    """Export bundles only."""
    print(f"Exporting bundles to {output_file}...")
    result = export_bundles_to_json(output_file)

    if result.success:
        print(result.get_summary())
        return 0
    else:
        print(f"ERROR: {result.error}")
        return 1


def export_packages(output_file: str):
    """Export packages only."""
    print(f"Exporting packages to {output_file}...")
    result = export_packages_to_json(output_file)

    if result.success:
        print(result.get_summary())
        return 0
    else:
        print(f"ERROR: {result.error}")
        return 1


def export_recipients(output_file: str):
    """Export recipients only."""
    print(f"Exporting recipients to {output_file}...")
    result = export_recipients_to_json(output_file)

    if result.success:
        print(result.get_summary())
        return 0
    else:
        print(f"ERROR: {result.error}")
        return 1


def export_events(output_file: str):
    """Export events only."""
    print(f"Exporting events to {output_file}...")
    result = export_events_to_json(output_file)

    if result.success:
        print(result.get_summary())
        return 0
    else:
        print(f"ERROR: {result.error}")
        return 1


# ============================================================================
# F054 Entity-Specific Export Commands
# ============================================================================


def export_materials(output_file: str) -> int:
    """Export materials only."""
    import json
    from src.models.base import session_scope
    from src.models.material import Material
    from sqlalchemy.orm import joinedload

    print(f"Exporting materials to {output_file}...")

    try:
        with session_scope() as session:
            materials = session.query(Material).options(joinedload(Material.subcategory)).all()

            records = []
            for m in materials:
                records.append(
                    {
                        "uuid": str(m.uuid) if m.uuid else None,
                        "subcategory_slug": m.subcategory.slug if m.subcategory else None,
                        "slug": m.slug,
                        "display_name": m.display_name,
                        "description": m.description,
                    }
                )

            data = {
                "version": "1.0",
                "entity_type": "materials",
                "records": records,
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        print(f"Exported {len(records)} materials to {output_file}")
        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def export_material_products(output_file: str) -> int:
    """Export material products only."""
    import json
    from src.models.base import session_scope
    from src.models.material import MaterialProduct
    from sqlalchemy.orm import joinedload

    print(f"Exporting material products to {output_file}...")

    try:
        with session_scope() as session:
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
                records.append(
                    {
                        "uuid": str(p.uuid) if p.uuid else None,
                        "material_slug": p.material.slug if p.material else None,
                        "supplier_slug": p.supplier.slug if p.supplier else None,
                        "brand": p.brand,
                        "product_name": p.product_name,
                        "package_size": p.package_size,
                        "package_unit": p.package_unit,
                        "price": float(p.price) if p.price else None,
                        "upc": p.upc,
                    }
                )

            data = {
                "version": "1.0",
                "entity_type": "material_products",
                "records": records,
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        print(f"Exported {len(records)} material products to {output_file}")
        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def export_material_categories(output_file: str) -> int:
    """Export material categories only."""
    import json
    from src.models.base import session_scope
    from src.models.material import MaterialCategory

    print(f"Exporting material categories to {output_file}...")

    try:
        with session_scope() as session:
            categories = session.query(MaterialCategory).all()

            records = []
            for c in categories:
                records.append(
                    {
                        "uuid": str(c.uuid) if c.uuid else None,
                        "name": c.name,
                        "slug": c.slug,
                        "description": c.description,
                    }
                )

            data = {
                "version": "1.0",
                "entity_type": "material_categories",
                "records": records,
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        print(f"Exported {len(records)} material categories to {output_file}")
        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def export_material_subcategories(output_file: str) -> int:
    """Export material subcategories only."""
    import json
    from src.models.base import session_scope
    from src.models.material import MaterialSubcategory
    from sqlalchemy.orm import joinedload

    print(f"Exporting material subcategories to {output_file}...")

    try:
        with session_scope() as session:
            subcategories = (
                session.query(MaterialSubcategory)
                .options(joinedload(MaterialSubcategory.category))
                .all()
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
                    }
                )

            data = {
                "version": "1.0",
                "entity_type": "material_subcategories",
                "records": records,
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        print(f"Exported {len(records)} material subcategories to {output_file}")
        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def export_suppliers(output_file: str) -> int:
    """Export suppliers only."""
    import json
    from src.models.base import session_scope
    from src.models.supplier import Supplier

    print(f"Exporting suppliers to {output_file}...")

    try:
        with session_scope() as session:
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

            data = {
                "version": "1.0",
                "entity_type": "suppliers",
                "records": records,
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        print(f"Exported {len(records)} suppliers to {output_file}")
        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def export_purchases(output_file: str) -> int:
    """Export purchases only."""
    import json
    from src.models.base import session_scope
    from src.models.purchase import Purchase
    from src.models.product import Product
    from sqlalchemy.orm import joinedload

    print(f"Exporting purchases to {output_file}...")

    try:
        with session_scope() as session:
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
                    product_slug = f"{p.product.ingredient.slug}:{p.product.slug}"

                records.append(
                    {
                        "uuid": str(p.uuid) if p.uuid else None,
                        "product_slug": product_slug,
                        "supplier_slug": p.supplier.slug if p.supplier else None,
                        "purchase_date": p.purchase_date.isoformat() if p.purchase_date else None,
                        "quantity": p.quantity,
                        "unit_price": float(p.unit_price) if p.unit_price else None,
                        "total_price": float(p.total_price) if p.total_price else None,
                        "store_location": p.store_location,
                        "notes": p.notes,
                    }
                )

            data = {
                "version": "1.0",
                "entity_type": "purchases",
                "records": records,
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        print(f"Exported {len(records)} purchases to {output_file}")
        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def import_all(input_file: str, mode: str = "merge", force: bool = False):
    """Import all data from the current import/export format file.

    Args:
        input_file: Path to JSON file to import
        mode: Import mode (merge, replace, etc.)
        force: If True, bypass cascade delete protection

    Returns:
        0 on success, 1 on failure
    """
    import json

    print(f"Importing all data from {input_file} (mode: {mode})...")

    try:
        # Load file to check for cascade risks
        with open(input_file, "r", encoding="utf-8") as f:
            import_data = json.load(f)

        # Check for import risks (only for replace mode)
        if mode == "replace" and not force:
            risks = check_import_risks(import_data, is_coordinated=False)
            cascade_risks = risks["cascade_risks"]
            restrict_risks = risks["restrict_risks"]

            # RESTRICT risks are blocking - import WILL fail at database level
            if restrict_risks:
                print("\nERROR: Import will fail due to RESTRICT constraint!")
                print("=" * 60)
                for risk in restrict_risks:
                    print(
                        f"\n  {risk['missing_count']} ingredients are used by {risk['blocking_count']} recipes"
                    )
                    print(f"  {risk['warning']}")
                    print("\n  Missing ingredients and their recipes:")
                    for ing_name, recipe_names in risk["details"].items():
                        print(f"    • {ing_name} → used by: {', '.join(recipe_names)}")
                    print("\n  To fix (choose one):")
                    for i, remedy in enumerate(risk["remediation"], 1):
                        print(f"    {i}. {remedy}")
                print("\n" + "=" * 60)
                return 1

            # CASCADE risks are warnings - data will be lost but import will succeed
            if cascade_risks:
                print("\nERROR: Import rejected due to cascade delete risk!")
                print("=" * 60)
                for risk in cascade_risks:
                    print(f"\n  Importing {risk['parent_entity']} without {risk['child_entity']}:")
                    print(f"  → {risk['child_count']} {risk['child_entity']} will be deleted")
                    print(f"  {risk['warning']}")
                print("\n" + "=" * 60)
                print("\nTo fix: Include both parent and child entities in your import file.")
                print("To override: Use --force flag (data will be permanently lost)")
                return 1

        result = import_all_from_json_v4(input_file, mode=mode)
        print(result.get_summary())

        if result.failed > 0:
            return 1
        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


# ============================================================================
# F030 Export Commands
# ============================================================================


def export_complete_cmd(output_dir: str = None, create_zip: bool = False):
    """
    Export complete database with manifest (F030).

    Creates a directory containing:
    - manifest.json with checksums and import order
    - Individual entity JSON files (suppliers, ingredients, products, etc.)
    - Optional ZIP archive

    Args:
        output_dir: Output directory (default: export_{timestamp})
        create_zip: Whether to create a ZIP archive

    Returns:
        0 on success, 1 on failure
    """
    from src.services.coordinated_export_service import export_complete

    # Generate default output directory if not provided
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"export_{timestamp}"

    print(f"Exporting complete database to {output_dir}...")

    try:
        manifest = export_complete(output_dir, create_zip=create_zip)

        # Print summary
        total_records = sum(f.record_count for f in manifest.files)
        print(f"\nExport Complete")
        print(f"---------------")
        print(f"Output directory: {output_dir}")
        print(f"Export date: {manifest.export_date}")
        print(f"Files exported: {len(manifest.files)}")
        print(f"Total records: {total_records}")
        print()
        for f in manifest.files:
            print(f"  {f.filename}: {f.record_count} records")

        if create_zip:
            zip_path = Path(output_dir).with_suffix(".zip")
            print(f"\nZIP archive: {zip_path}")

        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def export_view_cmd(view_type: str, output_path: str = None):
    """
    Export denormalized view (F030).

    Creates a view file with context fields for AI augmentation.

    Args:
        view_type: Type of view (products, inventory, purchases)
        output_path: Output file path (default: view_{type}.json)

    Returns:
        0 on success, 1 on failure
    """
    from src.services.denormalized_export_service import (
        export_products_context_rich,
        export_inventory_context_rich,
        export_purchases_context_rich,
    )

    # Map view types to export functions
    exporters = {
        "products": export_products_context_rich,
        "inventory": export_inventory_context_rich,
        "purchases": export_purchases_context_rich,
    }

    if view_type not in exporters:
        print(f"ERROR: Unknown view type '{view_type}'. Valid types: {', '.join(exporters.keys())}")
        return 1

    # Generate default output path if not provided
    if output_path is None:
        output_path = f"view_{view_type}.json"

    print(f"Exporting {view_type} view to {output_path}...")

    try:
        result = exporters[view_type](output_path)

        # Print summary
        print(f"\nExport Complete")
        print(f"---------------")
        print(f"View type: {result.export_type}")
        print(f"Output file: {result.output_path}")
        print(f"Records exported: {result.record_count}")
        print(f"Export date: {result.export_date}")

        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def validate_export_cmd(export_dir: str):
    """
    Validate export checksums (F030).

    Verifies that all files in the export directory match their
    manifest checksums.

    Args:
        export_dir: Path to export directory with manifest.json

    Returns:
        0 if valid, 1 if invalid
    """
    from src.services.coordinated_export_service import validate_export

    print(f"Validating export in {export_dir}...")

    try:
        result = validate_export(export_dir)

        if result["valid"]:
            print(f"\nValidation Passed")
            print(f"-----------------")
            print(f"Files checked: {result['files_checked']}")
            print("All checksums valid.")
            return 0
        else:
            print(f"\nValidation Failed")
            print(f"-----------------")
            print(f"Files checked: {result['files_checked']}")
            print("Errors found:")
            for error in result["errors"]:
                print(f"  - {error}")
            return 1

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


# ============================================================================
# F054 Backup/Restore Commands
# ============================================================================


def backup_cmd(output_dir: str = None, create_zip: bool = False) -> int:
    """
    Create timestamped 16-entity backup with manifest.

    Args:
        output_dir: Output directory (default: ./backups/backup_{timestamp})
        create_zip: Whether to create a ZIP archive

    Returns:
        0 on success, 1 on failure
    """
    from src.services.coordinated_export_service import export_complete

    # Generate default output directory
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"./backups/backup_{timestamp}"

    print(f"Creating backup in {output_dir}...")

    try:
        manifest = export_complete(output_dir, create_zip=create_zip)

        # Print summary
        total_records = sum(f.record_count for f in manifest.files)
        print(f"\nBackup Complete")
        print(f"---------------")
        print(f"Output directory: {output_dir}")
        print(f"Export date: {manifest.export_date}")
        print(f"Files exported: {len(manifest.files)}")
        print(f"Total records: {total_records}")
        print()
        for f in manifest.files:
            print(f"  {f.filename}: {f.record_count} records")

        if create_zip:
            zip_path = Path(output_dir).with_suffix(".zip")
            print(f"\nZIP archive: {zip_path}")

        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def restore_cmd(backup_dir: str, force: bool = False) -> int:
    """
    Restore database from backup directory.

    Uses replace mode - all existing data is cleared before import.
    The import follows dependency order from manifest.json.

    Args:
        backup_dir: Path to backup directory with manifest.json
        force: If True, bypass cascade delete protection

    Returns:
        0 on success, 1 on failure
    """
    import json
    from src.services.coordinated_export_service import import_complete

    backup_path = Path(backup_dir)
    if not backup_path.exists():
        print(f"ERROR: Backup directory not found: {backup_dir}")
        return 1

    manifest_path = backup_path / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: manifest.json not found in {backup_dir}")
        return 1

    # Load manifest to check for cascade risks
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        # Extract entity types from manifest
        entity_types = []
        for file_info in manifest_data.get("files", []):
            entity_type = file_info.get("entity_type")
            if entity_type:
                entity_types.append(entity_type)
        import_data = {"entity_types": entity_types}

        # Check for import risks (CASCADE and RESTRICT)
        if not force:
            risks = check_import_risks(import_data, is_coordinated=True)
            cascade_risks = risks["cascade_risks"]
            restrict_risks = risks["restrict_risks"]

            # RESTRICT risks are blocking - restore WILL fail at database level
            if restrict_risks:
                print("\nERROR: Restore will fail due to RESTRICT constraint!")
                print("=" * 60)
                for risk in restrict_risks:
                    print(
                        f"\n  {risk['missing_count']} ingredients are used by {risk['blocking_count']} recipes"
                    )
                    print(f"  {risk['warning']}")
                    print("\n  Missing ingredients and their recipes:")
                    for ing_name, recipe_names in risk["details"].items():
                        print(f"    • {ing_name} → used by: {', '.join(recipe_names)}")
                    print("\n  To fix (choose one):")
                    for i, remedy in enumerate(risk["remediation"], 1):
                        print(f"    {i}. {remedy}")
                print("\n" + "=" * 60)
                return 1

            # CASCADE risks are warnings - data will be lost but restore will succeed
            if cascade_risks:
                print("\nERROR: Restore rejected due to cascade delete risk!")
                print("=" * 60)
                for risk in cascade_risks:
                    print(
                        f"\n  Backup contains {risk['parent_entity']} but not {risk['child_entity']}:"
                    )
                    print(f"  → {risk['child_count']} {risk['child_entity']} will be deleted")
                    print(f"  {risk['warning']}")
                print("\n" + "=" * 60)
                print("\nTo fix: Ensure backup includes both parent and child entities.")
                print("To override: Use --force flag (data will be permanently lost)")
                return 1

    except json.JSONDecodeError as e:
        print(f"ERROR: Could not parse manifest.json: {e}")
        return 1

    print(f"Restoring from {backup_dir}...")
    print("WARNING: This will replace all existing data!")

    try:
        result = import_complete(backup_dir)

        if result.get("errors"):
            print(f"\nRestore Failed")
            print(f"--------------")
            for error in result["errors"]:
                print(f"  ERROR: {error}")
            return 1

        # Print summary
        print(f"\nRestore Complete")
        print(f"----------------")
        print(f"Files imported: {result.get('files_imported', 0)}")
        print(f"Total records: {result.get('successful', 0)}")
        print()
        entity_counts = result.get("entity_counts", {})
        for entity, count in entity_counts.items():
            print(f"  {entity}: {count} records")

        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def backup_list_cmd(backups_dir: str = "./backups/") -> int:
    """
    List available backups by scanning for manifest.json files.

    Args:
        backups_dir: Directory to scan for backups

    Returns:
        0 on success, 1 on failure
    """
    import json

    backups_path = Path(backups_dir)
    if not backups_path.exists():
        print(f"Directory not found: {backups_dir}")
        return 1

    backups = []
    for subdir in backups_path.iterdir():
        if subdir.is_dir():
            manifest_path = subdir / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                    backups.append(
                        {
                            "dir": subdir.name,
                            "path": str(subdir),
                            "date": manifest.get("export_date", "Unknown"),
                            "files": len(manifest.get("files", [])),
                            "records": sum(
                                f.get("record_count", 0) for f in manifest.get("files", [])
                            ),
                        }
                    )
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Warning: Could not read {manifest_path}: {e}")

    if not backups:
        print(f"No backups found in {backups_dir}")
        return 0

    # Sort by date descending (newest first)
    backups.sort(key=lambda x: x["date"], reverse=True)

    print(f"Available Backups in {backups_dir}")
    print("-" * 60)
    for b in backups:
        print(f"  {b['dir']}")
        print(f"    Date: {b['date']}")
        print(f"    Files: {b['files']}, Records: {b['records']}")

    return 0


def backup_validate_cmd(backup_dir: str) -> int:
    """
    Validate backup checksums.

    Args:
        backup_dir: Path to backup directory with manifest.json

    Returns:
        0 on success (all checksums valid), 1 on failure
    """
    from src.services.coordinated_export_service import validate_export

    backup_path = Path(backup_dir)
    if not backup_path.exists():
        print(f"ERROR: Backup directory not found: {backup_dir}")
        return 1

    manifest_path = backup_path / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: manifest.json not found in {backup_dir}")
        return 1

    print(f"Validating backup in {backup_dir}...")

    try:
        result = validate_export(backup_dir)

        if result["valid"]:
            print(f"\nValidation Passed")
            print(f"-----------------")
            print(f"Files checked: {result['files_checked']}")
            print("All checksums valid.")
            return 0
        else:
            print(f"\nValidation Failed")
            print(f"-----------------")
            print(f"Files checked: {result['files_checked']}")
            print("Errors found:")
            for error in result.get("errors", []):
                print(f"  - {error}")
            return 1

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


# ============================================================================
# F054 Context-Rich Aug Commands
# ============================================================================


def aug_export_cmd(entity_type: str, output_path: str = None) -> int:
    """
    Export context-rich data for AI workflows.

    Creates files with aug_ prefix containing human-readable context
    (resolved FK names, computed fields) for AI augmentation.

    Args:
        entity_type: Entity type to export (or "all")
        output_path: Output file/directory path

    Returns:
        0 on success, 1 on failure
    """
    from src.services.denormalized_export_service import (
        export_products_context_rich,
        export_ingredients_context_rich,
        export_materials_context_rich,
        export_recipes_context_rich,
        export_material_products_context_rich,
        export_finished_units_context_rich,
        export_finished_goods_context_rich,
        export_all_context_rich,
    )

    # Map entity types to export functions
    exporters = {
        "products": export_products_context_rich,
        "ingredients": export_ingredients_context_rich,
        "recipes": export_recipes_context_rich,
        "materials": export_materials_context_rich,
        "material-products": export_material_products_context_rich,
        "finished-units": export_finished_units_context_rich,
        "finished-goods": export_finished_goods_context_rich,
    }

    # The 7 spec-defined aug entity types (excludes inventory, purchases)
    AUG_SPEC_ENTITIES = {
        "products",
        "ingredients",
        "recipes",
        "materials",
        "material_products",
        "finished_units",
        "finished_goods",
    }

    try:
        if entity_type == "all":
            # Export all types to directory
            output_dir = output_path or "."
            print(f"Exporting all context-rich types to {output_dir}...")
            all_results = export_all_context_rich(output_dir)

            # Filter to only the 7 spec-defined entity types
            results = {k: v for k, v in all_results.items() if k in AUG_SPEC_ENTITIES}

            print(f"\nExport Complete")
            print(f"---------------")
            total_records = 0
            for etype, result in results.items():
                print(f"  {etype}: {result.record_count} records")
                total_records += result.record_count
            print(f"\nTotal: {total_records} records across {len(results)} files")

            # Note about extra files if any were created
            extra = set(all_results.keys()) - AUG_SPEC_ENTITIES
            if extra:
                print(f"\nNote: Additional files created: {', '.join(extra)}")

            return 0
        else:
            # Single entity type
            if output_path is None:
                output_path = f"aug_{entity_type.replace('-', '_')}.json"

            print(f"Exporting {entity_type} to {output_path}...")
            result = exporters[entity_type](output_path)

            print(f"\nExport Complete")
            print(f"---------------")
            print(f"Output file: {output_path}")
            print(f"Records exported: {result.record_count}")
            return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def aug_import_cmd(
    file_path: str,
    interactive: bool = False,
    skip_on_error: bool = False,
) -> int:
    """
    Import context-rich data with FK resolution.

    Imports context-rich export files, automatically resolving FK references
    or prompting in interactive mode.

    Args:
        file_path: Path to aug JSON file
        interactive: Enable interactive FK resolution prompts
        skip_on_error: Skip records with errors instead of failing

    Returns:
        0 on success, 1 on failure
    """
    from src.services.enhanced_import_service import import_context_rich_export

    input_path = Path(file_path)
    if not input_path.exists():
        print(f"ERROR: File not found: {file_path}")
        return 1

    mode_display = []
    if interactive:
        mode_display.append("interactive")
    if skip_on_error:
        mode_display.append("skip-on-error")
    mode_str = f" ({', '.join(mode_display)})" if mode_display else ""

    print(f"Importing from {file_path}{mode_str}...")

    # Set up resolver if interactive
    resolver = CLIFKResolver() if interactive else None

    try:
        result = import_context_rich_export(
            file_path,
            skip_on_error=skip_on_error,
            resolver=resolver,
        )

        print("\n" + result.get_summary())
        return 0 if result.base_result.failed == 0 else 1

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def aug_validate_cmd(file_path: str) -> int:
    """
    Validate aug file format and schema.

    Detects the format of an aug file and reports validation results.

    Args:
        file_path: Path to aug JSON file to validate

    Returns:
        0 if valid, 1 if invalid or error
    """
    from src.services.enhanced_import_service import detect_format

    input_path = Path(file_path)
    if not input_path.exists():
        print(f"ERROR: File not found: {file_path}")
        return 1

    print(f"Validating {file_path}...")

    try:
        format_info = detect_format(file_path)

        print(f"\nValidation Results")
        print(f"------------------")
        print(f"File: {file_path}")
        print(f"Format: {format_info.format_type.value}")
        if format_info.export_type:
            print(f"Entity type: {format_info.export_type}")
        if format_info.version:
            print(f"Version: {format_info.version}")
        print(f"Record count: {format_info.entity_count}")

        if format_info.editable_fields:
            print(f"Editable fields: {len(format_info.editable_fields)}")
        if format_info.readonly_fields:
            print(f"Readonly fields: {len(format_info.readonly_fields)}")

        print("\nStatus: VALID")
        return 0

    except Exception as e:
        print(f"\nStatus: INVALID")
        print(f"ERROR: {e}")
        return 1


# ============================================================================
# F054 Catalog Commands
# ============================================================================


# Catalog entity types supported by export/import
CATALOG_ENTITIES = [
    "suppliers",
    "ingredients",
    "products",
    "recipes",
    "finished-goods",
    "materials",
    "material-products",
]


def catalog_export_cmd(output_dir: str, entities_str: str = None) -> int:
    """
    Export catalog data to JSON files.

    Exports the 7 catalog entity types to individual JSON files in the
    specified output directory.

    Args:
        output_dir: Output directory path
        entities_str: Comma-separated entity types (default: all)

    Returns:
        0 on success, 1 on failure
    """
    from src.services.import_export_service import (
        export_ingredients_to_json,
        export_recipes_to_json,
        export_finished_goods_to_json,
    )
    from src.services.coordinated_export_service import (
        _export_suppliers,
        _export_products,
        _export_materials,
        _export_material_products,
    )
    from src.models.base import session_scope

    # Parse entities to export
    if entities_str:
        entities = [e.strip() for e in entities_str.split(",")]
        invalid = set(entities) - set(CATALOG_ENTITIES)
        if invalid:
            print(f"ERROR: Unknown entity types: {', '.join(invalid)}")
            print(f"Valid types: {', '.join(CATALOG_ENTITIES)}")
            return 1
    else:
        entities = CATALOG_ENTITIES

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Exporting catalog to {output_dir}...")
    print(f"Entities: {', '.join(entities)}")

    results = {}
    try:
        with session_scope() as session:
            for entity in entities:
                if entity == "suppliers":
                    entry = _export_suppliers(output_path, session)
                    results[entity] = entry.record_count
                elif entity == "ingredients":
                    file_path = str(output_path / "ingredients.json")
                    result = export_ingredients_to_json(file_path)
                    results[entity] = result.record_count
                elif entity == "products":
                    entry = _export_products(output_path, session)
                    results[entity] = entry.record_count
                elif entity == "recipes":
                    file_path = str(output_path / "recipes.json")
                    result = export_recipes_to_json(file_path)
                    results[entity] = result.record_count
                elif entity == "finished-goods":
                    file_path = str(output_path / "finished_goods.json")
                    result = export_finished_goods_to_json(file_path)
                    results[entity] = result.record_count
                elif entity == "materials":
                    entry = _export_materials(output_path, session)
                    results[entity] = entry.record_count
                elif entity == "material-products":
                    entry = _export_material_products(output_path, session)
                    results[entity] = entry.record_count

        # Create combined catalog.json for import compatibility
        combined_path = output_path / "catalog.json"
        combined_data = {"version": "1.0"}
        for entity in entities:
            # Map CLI entity names to file names and data keys
            file_map = {
                "suppliers": "suppliers.json",
                "ingredients": "ingredients.json",
                "products": "products.json",
                "recipes": "recipes.json",
                "finished-goods": "finished_goods.json",
                "materials": "materials.json",
                "material-products": "material_products.json",
            }
            data_key = entity.replace("-", "_")
            entity_file = output_path / file_map.get(entity, f"{data_key}.json")
            if entity_file.exists():
                import json

                with open(entity_file, "r", encoding="utf-8") as f:
                    entity_data = json.load(f)
                    # Handle different export formats
                    if "records" in entity_data:
                        combined_data[data_key] = entity_data["records"]
                    elif isinstance(entity_data, list):
                        combined_data[data_key] = entity_data
                    else:
                        combined_data[data_key] = entity_data

        import json

        with open(combined_path, "w", encoding="utf-8") as f:
            json.dump(combined_data, f, indent=2, ensure_ascii=False, default=str)

        print(f"\nCatalog Export Complete")
        print(f"-----------------------")
        print(f"Output directory: {output_dir}")
        total_records = 0
        for entity, count in results.items():
            print(f"  {entity}: {count} records")
            total_records += count
        print(f"\nTotal: {total_records} records across {len(results)} files")
        print(f"\nCombined file: {combined_path}")
        print("  (Use this file with catalog-import)")
        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def catalog_import_cmd(
    input_file: str,
    mode: str = "add",
    dry_run: bool = False,
) -> int:
    """
    Import catalog data from JSON file.

    Imports catalog entities in dependency order using the specified mode.

    Args:
        input_file: Path to catalog JSON file
        mode: Import mode ("add" or "augment")
        dry_run: Preview changes without modifying database

    Returns:
        0 on success, 1 on failure
    """
    from src.services.catalog_import_service import import_catalog

    input_path = Path(input_file)
    if not input_path.exists():
        print(f"ERROR: File not found: {input_file}")
        return 1

    mode_display = [f"mode: {mode}"]
    if dry_run:
        mode_display.append("DRY RUN")

    print(f"Importing catalog from {input_file} ({', '.join(mode_display)})...")

    try:
        result = import_catalog(
            input_file,
            mode=mode,
            dry_run=dry_run,
        )

        print("\n" + result.get_summary())

        # Check for failures
        total_failed = sum(counts.failed for counts in result.entity_counts.values())
        return 0 if total_failed == 0 else 1

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def catalog_validate_cmd(input_file: str) -> int:
    """
    Validate catalog file schema before import.

    Checks JSON structure and required fields for each entity type.

    Args:
        input_file: Path to catalog JSON file to validate

    Returns:
        0 if valid, 1 if invalid
    """
    import json
    from src.services.catalog_import_service import validate_catalog_file

    input_path = Path(input_file)
    if not input_path.exists():
        print(f"ERROR: File not found: {input_file}")
        return 1

    print(f"Validating catalog file {input_file}...")

    try:
        # Use the service's validation function
        data = validate_catalog_file(input_file)

        # Count records per entity type
        print(f"\nValidation Results")
        print(f"------------------")
        print(f"File: {input_file}")
        print(f"Format: {data.get('format', 'Unknown')}")
        print(f"Version: {data.get('version', 'Unknown')}")

        # Count entities
        entity_counts = {}
        for key, value in data.items():
            if isinstance(value, list) and key not in [
                "format",
                "version",
                "export_date",
                "source",
            ]:
                entity_counts[key] = len(value)

        if entity_counts:
            print(f"\nEntity counts:")
            for entity, count in entity_counts.items():
                print(f"  {entity}: {count} records")

        print("\nStatus: VALID")
        return 0

    except json.JSONDecodeError as e:
        print(f"\nStatus: INVALID")
        print(f"ERROR: Invalid JSON - {e}")
        return 1
    except Exception as e:
        print(f"\nStatus: INVALID")
        print(f"ERROR: {e}")
        return 1


# ============================================================================
# F030 Import Commands
# ============================================================================


class CLIFKResolver:
    """
    CLI implementation of FK resolution callback.

    Prompts the user via text input for each missing FK reference.
    Supports CREATE (new entity), MAP (existing entity), and SKIP options.
    """

    def resolve(self, missing) -> "Resolution":
        """
        Prompt user to resolve a missing FK reference.

        Args:
            missing: MissingFK instance with details about the missing reference

        Returns:
            Resolution with user's choice
        """
        from src.services.fk_resolver_service import (
            Resolution,
            ResolutionChoice,
            find_similar_entities,
        )

        print(f"\nMissing {missing.entity_type}: '{missing.missing_value}'")
        print(f"  Field: {missing.field_name}")
        print(f"  Affects {missing.affected_record_count} records")

        # Show sample records for context
        if missing.sample_records:
            print("  Sample affected records:")
            for i, sample in enumerate(missing.sample_records[:2]):
                # Show a brief summary of the sample record
                if missing.entity_type == "ingredient":
                    display = sample.get("product_name") or sample.get("brand", "")
                elif missing.entity_type == "supplier":
                    display = sample.get("product_name") or sample.get("brand", "")
                else:
                    display = str(sample)[:50]
                print(f"    {i+1}. {display}")

        # Show options
        print("\nOptions:")
        print("  [C] Create new entity")
        print("  [M] Map to existing entity")
        print("  [S] Skip these records")

        while True:
            choice = input("\nEnter choice (C/M/S): ").strip().upper()

            if choice == "C":
                return self._handle_create(missing)
            elif choice == "M":
                return self._handle_map(missing)
            elif choice == "S":
                return Resolution(
                    choice=ResolutionChoice.SKIP,
                    entity_type=missing.entity_type,
                    missing_value=missing.missing_value,
                )
            else:
                print("Invalid choice. Enter C, M, or S.")

    def _handle_create(self, missing) -> "Resolution":
        """Handle CREATE choice - prompt for required fields."""
        from src.services.fk_resolver_service import Resolution, ResolutionChoice

        print(f"\nCreate new {missing.entity_type}:")
        entity_data = {}

        if missing.entity_type == "supplier":
            # Pre-fill name from missing value
            entity_data["name"] = (
                input(f"  Name [{missing.missing_value}]: ").strip() or missing.missing_value
            )
            entity_data["city"] = input("  City (required): ").strip()
            entity_data["state"] = input("  State (2-letter, required): ").strip()
            entity_data["zip_code"] = input("  ZIP Code (required): ").strip()
            # Optional fields
            street = input("  Street address (optional): ").strip()
            if street:
                entity_data["street_address"] = street

        elif missing.entity_type == "ingredient":
            # Pre-fill slug from missing value
            entity_data["slug"] = (
                input(f"  Slug [{missing.missing_value}]: ").strip() or missing.missing_value
            )
            entity_data["display_name"] = input("  Display name (required): ").strip()
            entity_data["category"] = input("  Category (required): ").strip()
            # Optional fields
            desc = input("  Description (optional): ").strip()
            if desc:
                entity_data["description"] = desc

        elif missing.entity_type == "product":
            # Products require ingredient reference
            entity_data["ingredient_slug"] = (
                input(f"  Ingredient slug [{missing.missing_value}]: ").strip()
                or missing.missing_value
            )
            entity_data["brand"] = input("  Brand (optional): ").strip() or None
            entity_data["package_unit"] = input("  Package unit (e.g., oz, lb, required): ").strip()
            qty = input("  Package unit quantity (required): ").strip()
            try:
                entity_data["package_unit_quantity"] = float(qty)
            except ValueError:
                print("  Invalid quantity, using 1.0")
                entity_data["package_unit_quantity"] = 1.0
            # Optional fields
            name = input("  Product name (optional): ").strip()
            if name:
                entity_data["product_name"] = name

        return Resolution(
            choice=ResolutionChoice.CREATE,
            entity_type=missing.entity_type,
            missing_value=missing.missing_value,
            created_entity=entity_data,
        )

    def _handle_map(self, missing) -> "Resolution":
        """Handle MAP choice - show fuzzy search results and let user select."""
        from src.services.fk_resolver_service import (
            Resolution,
            ResolutionChoice,
            find_similar_entities,
        )

        # Perform fuzzy search
        print(f"\nSearching for similar {missing.entity_type}s...")
        similar = find_similar_entities(missing.entity_type, missing.missing_value, limit=5)

        if not similar:
            print("  No similar entities found.")
            # Fall back to asking for options again
            print("  You can:")
            print("  [C] Create new entity instead")
            print("  [S] Skip these records")
            while True:
                fallback = input("\nEnter choice (C/S): ").strip().upper()
                if fallback == "C":
                    return self._handle_create(missing)
                elif fallback == "S":
                    return Resolution(
                        choice=ResolutionChoice.SKIP,
                        entity_type=missing.entity_type,
                        missing_value=missing.missing_value,
                    )
                else:
                    print("Invalid choice. Enter C or S.")

        # Show similar entities
        print(f"\nSimilar {missing.entity_type}s found:")
        for i, entity in enumerate(similar):
            print(f"  [{i+1}] {entity['display']}")
        print(f"  [0] Cancel and choose another option")

        while True:
            choice = input("\nEnter number to select: ").strip()
            try:
                num = int(choice)
                if num == 0:
                    # Go back to main options
                    print("\nOptions:")
                    print("  [C] Create new entity")
                    print("  [M] Map to existing entity (search again)")
                    print("  [S] Skip these records")
                    sub_choice = input("\nEnter choice (C/M/S): ").strip().upper()
                    if sub_choice == "C":
                        return self._handle_create(missing)
                    elif sub_choice == "M":
                        return self._handle_map(missing)  # Recurse to search again
                    elif sub_choice == "S":
                        return Resolution(
                            choice=ResolutionChoice.SKIP,
                            entity_type=missing.entity_type,
                            missing_value=missing.missing_value,
                        )
                elif 1 <= num <= len(similar):
                    selected = similar[num - 1]
                    return Resolution(
                        choice=ResolutionChoice.MAP,
                        entity_type=missing.entity_type,
                        missing_value=missing.missing_value,
                        mapped_id=selected["id"],
                    )
                else:
                    print(f"Invalid number. Enter 0-{len(similar)}.")
            except ValueError:
                print("Please enter a number.")


def import_view_cmd(
    file_path: str,
    mode: str = "merge",
    interactive: bool = False,
    skip_on_error: bool = False,
    dry_run: bool = False,
) -> int:
    """
    Import denormalized view file (F030).

    Args:
        file_path: Path to the view JSON file
        mode: Import mode - "merge" (default) or "skip_existing"
        interactive: Enable interactive FK resolution
        skip_on_error: Skip records with errors instead of failing
        dry_run: Preview changes without modifying database

    Returns:
        0 on success, 1 on failure
    """
    from src.services.enhanced_import_service import import_context_rich_export

    mode_display = f"mode: {mode}"
    if dry_run:
        mode_display += ", DRY RUN"
    if skip_on_error:
        mode_display += ", skip-on-error"
    if interactive:
        mode_display += ", interactive"

    print(f"Importing view from {file_path} ({mode_display})...")

    # Set up resolver if interactive mode
    resolver: Optional[CLIFKResolver] = None
    if interactive:
        resolver = CLIFKResolver()

    try:
        result = import_context_rich_export(
            file_path,
            mode=mode,
            dry_run=dry_run,
            skip_on_error=skip_on_error,
            resolver=resolver,
        )

        # Print summary
        print("\n" + result.get_summary())

        # Return exit code based on failures
        return 0 if result.failed == 0 else 1

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


# ============================================================================
# F059 Material Purchase CLI Command
# ============================================================================


def lookup_material_product(identifier: str) -> Optional[dict]:
    """Look up a MaterialProduct by name or slug.

    Args:
        identifier: Product name or slug to search for

    Returns:
        Product dict if found, None otherwise
    """
    from src.services.material_catalog_service import list_products
    from src.models.material_product import MaterialProduct
    from src.services.database import session_scope

    # Try slug lookup first (exact match via direct query)
    with session_scope() as session:
        product = (
            session.query(MaterialProduct)
            .filter(MaterialProduct.slug == identifier)
            .first()
        )
        if product:
            # Get material for base_unit_type
            return {
                "id": product.id,
                "name": product.name,
                "slug": product.slug,
                "material_id": product.material_id,
                "brand": product.brand,
                "package_quantity": product.package_quantity,
                "package_unit": product.package_unit,
                "quantity_in_base_units": product.quantity_in_base_units,
                "is_provisional": product.is_provisional,
            }

    # Try name lookup (case-insensitive)
    products = list_products(include_hidden=False)
    for p in products:
        if p["name"].lower() == identifier.lower():
            return p

    # Try partial name match
    matches = [p for p in products if identifier.lower() in p["name"].lower()]
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        # Multiple matches - return None and let caller handle
        print(f"Multiple products match '{identifier}':")
        for i, m in enumerate(matches, 1):
            print(f"  {i}. {m['name']} ({m.get('brand', 'No brand')})")
        return None

    return None


def validate_new_product_args(args) -> tuple:
    """Validate arguments for creating a new provisional product.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not args.name:
        return False, "Product name is required (--name)"
    if not args.material_id:
        return False, "Material ID is required (--material-id)"
    if not args.package_size:
        return False, "Package size is required (--package-size)"
    if not args.package_unit:
        return False, "Package unit is required (--package-unit)"
    return True, ""


def prompt_for_material() -> Optional[int]:
    """Interactively prompt user to select a material.

    Returns:
        Material ID or None if cancelled
    """
    from src.services.material_catalog_service import list_materials

    materials = list_materials()
    if not materials:
        print("No materials found. Create materials first.")
        return None

    print("\nAvailable materials:")
    for i, m in enumerate(materials, 1):
        print(f"  {i}. {m['name']} ({m['base_unit_type']})")

    try:
        choice = input("\nSelect material number (or 'q' to quit): ").strip()
        if choice.lower() == 'q':
            return None
        idx = int(choice) - 1
        if 0 <= idx < len(materials):
            return materials[idx]['id']
        print("Invalid selection")
        return None
    except (ValueError, KeyboardInterrupt):
        return None


def format_purchase_success(product: dict, purchase_result: dict, created_provisional: bool) -> str:
    """Format success message for purchase."""
    lines = []

    if created_provisional:
        lines.append("=" * 50)
        lines.append("PROVISIONAL PRODUCT CREATED")
        lines.append(f"  Name: {product['name']}")
        lines.append(f"  ID: {product['id']}")
        lines.append("  (Complete product details in UI to remove provisional status)")
        lines.append("=" * 50)

    lines.append("")
    lines.append("PURCHASE RECORDED")
    lines.append(f"  Product: {product.get('name', 'N/A')}")
    lines.append(f"  Packages: {purchase_result.get('packages_purchased', 'N/A')}")
    lines.append(f"  Total Cost: ${float(purchase_result.get('total_cost', 0)):.2f}")
    lines.append(f"  Units Added: {purchase_result.get('units_added', 'N/A'):.2f}")
    lines.append(f"  Unit Cost: ${float(purchase_result.get('unit_cost', 0)):.4f}/unit")
    lines.append(f"  Date: {purchase_result.get('purchase_date', 'today')}")

    return "\n".join(lines)


def format_error(error_type: str, message: str, suggestions: list = None) -> str:
    """Format error message with suggestions."""
    lines = [f"ERROR: {error_type}", f"  {message}"]

    if suggestions:
        lines.append("")
        lines.append("Suggestions:")
        for s in suggestions:
            lines.append(f"  - {s}")

    return "\n".join(lines)


def handle_material_purchase(args) -> int:
    """Handle the purchase-material command."""
    from src.services.material_catalog_service import create_product, list_materials
    from src.services.material_purchase_service import record_purchase
    from src.models.supplier import Supplier
    from src.services.database import session_scope
    from decimal import Decimal
    from datetime import date as date_type, datetime

    product = None
    created_provisional = False

    # Validate mutual exclusivity of --product and --name
    if args.product and args.name:
        print(format_error(
            "Invalid arguments",
            "Cannot specify both --product and --name",
            ["Use --product to purchase existing product", "Use --name to create new provisional product"]
        ))
        return 1

    if args.product:
        # Look up existing product
        product = lookup_material_product(args.product)
        if not product:
            print(format_error(
                "Product not found",
                f"No product found matching '{args.product}'",
                ["Use --name to create a new provisional product", "Check product name/slug spelling"]
            ))
            return 1

    elif args.name:
        # Create provisional product
        is_valid, error = validate_new_product_args(args)
        if not is_valid:
            print(format_error("Missing required field", error))
            return 1

        try:
            # Generate slug from name
            slug = args.name.lower().replace(" ", "-")
            # Remove special characters
            import re
            slug = re.sub(r'[^a-z0-9\-]', '', slug)
            slug = re.sub(r'-+', '-', slug).strip('-')

            product = create_product(
                material_id=args.material_id,
                name=args.name,
                package_quantity=args.package_size,
                package_unit=args.package_unit,
                slug=slug,
                notes="Created as provisional product via CLI",
                is_provisional=True,
            )
            # Convert ORM object to dict
            product = {
                "id": product.id,
                "name": product.name,
                "slug": product.slug,
                "material_id": product.material_id,
                "brand": product.brand,
                "package_quantity": product.package_quantity,
                "package_unit": product.package_unit,
                "quantity_in_base_units": product.quantity_in_base_units,
                "is_provisional": product.is_provisional,
            }
            created_provisional = True
            print(f"Created provisional product: {product['name']} (ID: {product['id']})")

        except Exception as e:
            print(format_error("Product creation failed", str(e)))
            return 1

    else:
        print(format_error(
            "Missing argument",
            "Either --product or --name must be provided",
            ["--product: Look up existing product by name or slug", "--name: Create new provisional product"]
        ))
        return 1

    # Parse purchase date
    purchase_date = date_type.today()
    if args.date:
        try:
            purchase_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print(format_error("Invalid date", "Date format must be YYYY-MM-DD"))
            return 1

    # Get or create a default supplier for CLI purchases
    with session_scope() as session:
        # Look for a "CLI Purchase" or general supplier
        supplier = session.query(Supplier).filter(
            Supplier.name.ilike("%cli%")
        ).first()

        if not supplier:
            # Try to find any active supplier
            supplier = session.query(Supplier).filter(
                Supplier.is_active == True  # noqa: E712
            ).first()

        if not supplier:
            print(format_error(
                "No supplier found",
                "No active suppliers in database",
                ["Create a supplier first via the UI or import"]
            ))
            return 1

        supplier_id = supplier.id

    # Record the purchase
    try:
        purchase = record_purchase(
            product_id=product["id"],
            supplier_id=supplier_id,
            purchase_date=purchase_date,
            packages_purchased=int(args.qty),
            package_price=Decimal(str(args.cost / args.qty)),  # Cost per package
            notes=args.notes,
        )

        # Build result dict for display
        purchase_result = {
            "packages_purchased": int(args.qty),
            "total_cost": Decimal(str(args.cost)),
            "units_added": purchase.units_added,
            "unit_cost": purchase.unit_cost,
            "purchase_date": purchase_date,
        }

        print(format_purchase_success(product, purchase_result, created_provisional))
        return 0

    except Exception as e:
        print(format_error("Purchase recording failed", str(e)))
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Import/Export utility for Seasonal Baking Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  === Legacy Commands ===

  Export all data (v3.2 format):
    python -m src.utils.import_export_cli export test_data.json

  Import all data (requires v3.2 format):
    python -m src.utils.import_export_cli import test_data.json

  Import with replace mode (clears existing data):
    python -m src.utils.import_export_cli import test_data.json --mode replace

  === F030 Commands ===

  Export complete database with manifest:
    python -m src.utils.import_export_cli export-complete -o ./export_dir
    python -m src.utils.import_export_cli export-complete -o ./export_dir --zip

  Export denormalized view:
    python -m src.utils.import_export_cli export-view -t products -o view_products.json

  Validate export checksums:
    python -m src.utils.import_export_cli validate-export ./export_dir

  Import denormalized view:
    python -m src.utils.import_export_cli import-view view_products.json
    python -m src.utils.import_export_cli import-view view_products.json --interactive
    python -m src.utils.import_export_cli import-view view_products.json --dry-run

  === F054 Backup/Restore Commands ===

  Create timestamped backup:
    python -m src.utils.import_export_cli backup
    python -m src.utils.import_export_cli backup -o ./my_backup
    python -m src.utils.import_export_cli backup --zip

  Restore from backup:
    python -m src.utils.import_export_cli restore ./backups/backup_20260115_120000

  List available backups:
    python -m src.utils.import_export_cli backup-list
    python -m src.utils.import_export_cli backup-list --dir ./my_backups

  Validate backup integrity:
    python -m src.utils.import_export_cli backup-validate ./backups/backup_20260115_120000

  === F054 Context-Rich Aug Commands ===

  Export context-rich data for AI workflows:
    python -m src.utils.import_export_cli aug-export -t products
    python -m src.utils.import_export_cli aug-export -t recipes -o my_recipes.json
    python -m src.utils.import_export_cli aug-export -t all -o ./aug_exports/

  Import context-rich data:
    python -m src.utils.import_export_cli aug-import aug_products.json
    python -m src.utils.import_export_cli aug-import aug_recipes.json --interactive
    python -m src.utils.import_export_cli aug-import aug_data.json --skip-on-error

  Validate aug file format:
    python -m src.utils.import_export_cli aug-validate aug_products.json

  === F054 Catalog Commands ===

  Export catalog data (creates per-entity files + combined catalog.json):
    python -m src.utils.import_export_cli catalog-export
    python -m src.utils.import_export_cli catalog-export -o ./catalog/
    python -m src.utils.import_export_cli catalog-export --entities ingredients,recipes

  Import catalog data (use the combined catalog.json file):
    python -m src.utils.import_export_cli catalog-import ./catalog_export/catalog.json
    python -m src.utils.import_export_cli catalog-import ./catalog/catalog.json --mode augment
    python -m src.utils.import_export_cli catalog-import ./catalog/catalog.json --dry-run

  Validate catalog file:
    python -m src.utils.import_export_cli catalog-validate ./catalog_export/catalog.json

  === Entity-Specific Exports ===

  Export individual entity types:
    python -m src.utils.import_export_cli export-ingredients ingredients.json
    python -m src.utils.import_export_cli export-recipes recipes.json
    python -m src.utils.import_export_cli export-materials materials.json
    python -m src.utils.import_export_cli export-suppliers suppliers.json
    python -m src.utils.import_export_cli export-purchases purchases.json

Note: Individual entity imports (import-ingredients, etc.) are no longer
supported. Use the 'import' command with a complete v3.2 format file.
""",
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Legacy export command (requires file)
    export_parser = subparsers.add_parser("export", help="Export all data (v3.2 format)")
    export_parser.add_argument("file", help="JSON file path")

    # Legacy entity-specific export commands
    for entity in [
        "ingredients",
        "recipes",
        "finished-goods",
        "bundles",
        "packages",
        "recipients",
        "events",
    ]:
        entity_parser = subparsers.add_parser(f"export-{entity}", help=f"Export {entity} only")
        entity_parser.add_argument("file", help="JSON file path")

    # F054: Additional entity-specific export commands
    for entity in [
        "materials",
        "material-products",
        "material-categories",
        "material-subcategories",
        "suppliers",
        "purchases",
    ]:
        entity_parser = subparsers.add_parser(f"export-{entity}", help=f"Export {entity} only")
        entity_parser.add_argument("file", help="JSON file path")

    # Legacy import command
    import_parser = subparsers.add_parser("import", help="Import all data (v3.2 format)")
    import_parser.add_argument("file", help="JSON file path")
    import_parser.add_argument(
        "--mode",
        choices=["merge", "replace"],
        default="merge",
        help="Import mode: 'merge' (default) adds new records, 'replace' clears existing data first",
    )
    import_parser.add_argument(
        "--force",
        action="store_true",
        help="Force import even if it would cause cascade deletes (use with caution)",
    )

    # F030: export-complete command
    export_complete_parser = subparsers.add_parser(
        "export-complete", help="Export complete database with manifest (F030)"
    )
    export_complete_parser.add_argument(
        "-o", "--output", dest="output_dir", help="Output directory (default: export_{timestamp})"
    )
    export_complete_parser.add_argument(
        "-z", "--zip", dest="create_zip", action="store_true", help="Create ZIP archive"
    )

    # F030: export-view command
    export_view_parser = subparsers.add_parser(
        "export-view", help="Export denormalized view (F030)"
    )
    export_view_parser.add_argument(
        "-t",
        "--type",
        dest="view_type",
        choices=["products", "inventory", "purchases"],
        required=True,
        help="View type to export",
    )
    export_view_parser.add_argument(
        "-o", "--output", dest="output_path", help="Output file path (default: view_{type}.json)"
    )

    # F030: validate-export command
    validate_parser = subparsers.add_parser(
        "validate-export", help="Validate export checksums (F030)"
    )
    validate_parser.add_argument("export_dir", help="Path to export directory with manifest.json")

    # F030: import-view command
    import_view_parser = subparsers.add_parser(
        "import-view", help="Import denormalized view (F030)"
    )
    import_view_parser.add_argument("file", help="Input view JSON file path")
    import_view_parser.add_argument(
        "-m",
        "--mode",
        dest="import_mode",
        choices=["merge", "skip_existing"],
        default="merge",
        help="Import mode: 'merge' (default) updates existing and adds new, 'skip_existing' only adds new",
    )
    import_view_parser.add_argument(
        "-i", "--interactive", action="store_true", help="Enable interactive FK resolution"
    )
    import_view_parser.add_argument(
        "-s",
        "--skip-on-error",
        dest="skip_on_error",
        action="store_true",
        help="Skip records with errors instead of failing",
    )
    import_view_parser.add_argument(
        "-d",
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Preview changes without modifying database",
    )

    # F054: Backup command
    backup_parser = subparsers.add_parser(
        "backup", help="Create timestamped 16-entity backup with manifest"
    )
    backup_parser.add_argument(
        "-o",
        "--output",
        dest="output_dir",
        help="Output directory (default: ./backups/backup_{timestamp})",
    )
    backup_parser.add_argument(
        "--zip", dest="create_zip", action="store_true", help="Create compressed ZIP archive"
    )

    # F054: Restore command
    restore_parser = subparsers.add_parser(
        "restore", help="Restore database from backup (WARNING: replaces all data)"
    )
    restore_parser.add_argument("backup_dir", help="Path to backup directory with manifest.json")
    restore_parser.add_argument(
        "--force",
        action="store_true",
        help="Force restore even if it would cause cascade deletes (use with caution)",
    )
    restore_parser.epilog = (
        "NOTE: Restore uses replace mode - all existing data is cleared before import. "
        "For selective import, use catalog-import with add/augment mode instead."
    )

    # F054: Backup-list command
    backup_list_parser = subparsers.add_parser(
        "backup-list", help="List available backups in a directory"
    )
    backup_list_parser.add_argument(
        "--dir",
        dest="backups_dir",
        default="./backups/",
        help="Directory to scan for backups (default: ./backups/)",
    )

    # F054: Backup-validate command
    backup_validate_parser = subparsers.add_parser(
        "backup-validate", help="Verify backup integrity via checksums"
    )
    backup_validate_parser.add_argument(
        "backup_dir", help="Path to backup directory with manifest.json"
    )

    # F054: Aug-export command (context-rich export for AI workflows)
    aug_export_parser = subparsers.add_parser(
        "aug-export", help="Export context-rich data for AI workflows (aug_ prefix)"
    )
    aug_export_parser.add_argument(
        "-t",
        "--type",
        dest="entity_type",
        choices=[
            "ingredients",
            "products",
            "recipes",
            "materials",
            "material-products",
            "finished-units",
            "finished-goods",
            "all",
        ],
        required=True,
        help="Entity type to export",
    )
    aug_export_parser.add_argument(
        "-o", "--output", dest="output_path", help="Output file path (default: aug_{type}.json)"
    )

    # F054: Aug-import command (context-rich import with FK resolution)
    aug_import_parser = subparsers.add_parser(
        "aug-import", help="Import context-rich data with FK resolution"
    )
    aug_import_parser.add_argument("file", help="Input aug JSON file")
    aug_import_parser.add_argument(
        "-i", "--interactive", action="store_true", help="Enable interactive FK resolution"
    )
    aug_import_parser.add_argument(
        "-s",
        "--skip-on-error",
        dest="skip_on_error",
        action="store_true",
        help="Skip records with errors instead of failing",
    )

    # F054: Aug-validate command (validate aug file format)
    aug_validate_parser = subparsers.add_parser(
        "aug-validate", help="Validate aug file format and schema"
    )
    aug_validate_parser.add_argument("file", help="Aug JSON file to validate")

    # F054: Catalog-export command
    catalog_export_parser = subparsers.add_parser(
        "catalog-export", help="Export catalog data (7 entity types)"
    )
    catalog_export_parser.add_argument(
        "-o",
        "--output",
        dest="output_dir",
        default="./catalog_export/",
        help="Output directory (default: ./catalog_export/)",
    )
    catalog_export_parser.add_argument(
        "--entities", dest="entities", help="Comma-separated entity types to export (default: all)"
    )

    # F054: Catalog-import command
    catalog_import_parser = subparsers.add_parser(
        "catalog-import", help="Import catalog data with mode selection"
    )
    catalog_import_parser.add_argument(
        "input_file", help="Combined catalog JSON file (e.g., catalog.json from catalog-export)"
    )
    catalog_import_parser.add_argument(
        "-m",
        "--mode",
        dest="import_mode",
        choices=["add", "augment"],
        default="add",
        help="Import mode: 'add' (default) skip existing, 'augment' update nulls",
    )
    catalog_import_parser.add_argument(
        "-d",
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Preview changes without modifying database",
    )
    catalog_import_parser.epilog = (
        "Use the catalog.json file created by catalog-export. "
        "Example: catalog-import ./catalog_export/catalog.json"
    )

    # F054: Catalog-validate command
    catalog_validate_parser = subparsers.add_parser(
        "catalog-validate", help="Validate catalog file schema"
    )
    catalog_validate_parser.add_argument(
        "input_file", help="Combined catalog JSON file to validate (e.g., catalog.json)"
    )

    # F059: Material purchase command
    mat_purchase_parser = subparsers.add_parser(
        "purchase-material",
        help="Record a material purchase (creates provisional product if needed)"
    )
    mat_purchase_parser.add_argument(
        "--product",
        type=str,
        help="Existing product name or slug (for lookup)"
    )
    mat_purchase_parser.add_argument(
        "--name",
        type=str,
        help="New product name (creates provisional product)"
    )
    mat_purchase_parser.add_argument(
        "--material-id",
        type=int,
        dest="material_id",
        help="Material ID to link product to (required for new products)"
    )
    mat_purchase_parser.add_argument(
        "--qty",
        type=float,
        required=True,
        help="Quantity purchased (number of packages)"
    )
    mat_purchase_parser.add_argument(
        "--package-size",
        type=float,
        dest="package_size",
        help="Units per package (required for new products)"
    )
    mat_purchase_parser.add_argument(
        "--package-unit",
        type=str,
        dest="package_unit",
        help="Package unit (e.g., 'each', 'feet', 'yards') - required for new products"
    )
    mat_purchase_parser.add_argument(
        "--cost",
        type=float,
        required=True,
        help="Total cost of purchase"
    )
    mat_purchase_parser.add_argument(
        "--date",
        type=str,
        help="Purchase date (YYYY-MM-DD, defaults to today)"
    )
    mat_purchase_parser.add_argument(
        "--notes",
        type=str,
        help="Optional notes for the purchase"
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    # Initialize database (required for all operations)
    print("Initializing database...")
    initialize_app_database()

    # Execute command
    if args.command == "export":
        return export_all(args.file)
    elif args.command == "export-ingredients":
        return export_ingredients(args.file)
    elif args.command == "export-recipes":
        return export_recipes(args.file)
    elif args.command == "export-finished-goods":
        return export_finished_goods(args.file)
    elif args.command == "export-bundles":
        return export_bundles(args.file)
    elif args.command == "export-packages":
        return export_packages(args.file)
    elif args.command == "export-recipients":
        return export_recipients(args.file)
    elif args.command == "export-events":
        return export_events(args.file)
    elif args.command == "export-materials":
        return export_materials(args.file)
    elif args.command == "export-material-products":
        return export_material_products(args.file)
    elif args.command == "export-material-categories":
        return export_material_categories(args.file)
    elif args.command == "export-material-subcategories":
        return export_material_subcategories(args.file)
    elif args.command == "export-suppliers":
        return export_suppliers(args.file)
    elif args.command == "export-purchases":
        return export_purchases(args.file)
    elif args.command == "import":
        return import_all(args.file, mode=args.mode, force=args.force)
    elif args.command == "export-complete":
        return export_complete_cmd(args.output_dir, args.create_zip)
    elif args.command == "export-view":
        return export_view_cmd(args.view_type, args.output_path)
    elif args.command == "validate-export":
        return validate_export_cmd(args.export_dir)
    elif args.command == "import-view":
        return import_view_cmd(
            args.file,
            mode=args.import_mode,
            interactive=args.interactive,
            skip_on_error=args.skip_on_error,
            dry_run=args.dry_run,
        )
    elif args.command == "backup":
        return backup_cmd(args.output_dir, args.create_zip)
    elif args.command == "restore":
        return restore_cmd(args.backup_dir, force=args.force)
    elif args.command == "backup-list":
        return backup_list_cmd(args.backups_dir)
    elif args.command == "backup-validate":
        return backup_validate_cmd(args.backup_dir)
    elif args.command == "aug-export":
        return aug_export_cmd(args.entity_type, args.output_path)
    elif args.command == "aug-import":
        return aug_import_cmd(args.file, args.interactive, args.skip_on_error)
    elif args.command == "aug-validate":
        return aug_validate_cmd(args.file)
    elif args.command == "catalog-export":
        return catalog_export_cmd(args.output_dir, args.entities)
    elif args.command == "catalog-import":
        return catalog_import_cmd(args.input_file, args.import_mode, args.dry_run)
    elif args.command == "catalog-validate":
        return catalog_validate_cmd(args.input_file)
    elif args.command == "purchase-material":
        return handle_material_purchase(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
