#!/usr/bin/env python3
"""
Migration Script: F027 Product Catalog Management

PURPOSE:
  Transform existing data for new schema including Supplier and Purchase entities.

MIGRATION STRATEGY (per Constitution VI):
  1. Export current data to JSON backup
  2. Transform JSON to include new entities/fields
  3. Delete database file (DESTRUCTIVE)
  4. Recreate schema with new models
  5. Import transformed data

ROLLBACK PROCEDURE:
  If migration fails or produces incorrect results:

  1. Stop the application

  2. Delete the new database:
     rm data/bake_tracker.db

  3. Restore from pre-migration backup:
     - Locate backup in backups/pre_f027_migration_*.json
     - Use import_export_service.import_all_from_json_v3()
     - Or: restore from your own backup if you made one

  4. Verify restoration:
     - Check record counts match original
     - Test application functionality

  5. Report issues before retrying migration

BACKUP LOCATION:
  backups/pre_f027_migration_YYYYMMDD_HHMMSS.json

USAGE:
  # Dry run (recommended first):
  python scripts/migrate_f027.py --dry-run

  # Execute migration:
  python scripts/migrate_f027.py

  # With custom paths:
  python scripts/migrate_f027.py --db-path /path/to/db --backup-dir /path/to/backups
"""

import argparse
import json
import os
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Migrate database for F027 (Product Catalog Management)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview what will happen:
  python scripts/migrate_f027.py --dry-run

  # Execute the migration:
  python scripts/migrate_f027.py

  # Specify custom paths:
  python scripts/migrate_f027.py --db-path ./my_db.db --backup-dir ./my_backups
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making changes",
    )
    parser.add_argument(
        "--backup-dir",
        default="backups",
        help="Directory for backup files (default: backups)",
    )
    parser.add_argument(
        "--db-path",
        default="data/bake_tracker.db",
        help="Path to database file (default: data/bake_tracker.db)",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip validation step (not recommended)",
    )
    parser.add_argument(
        "--output-json",
        help="Path to save transformed JSON (for inspection)",
    )
    return parser.parse_args()


def backup_current_data(args):
    """
    Export current database to JSON backup.

    Returns:
        Tuple of (backup_file_path, data_dict)
    """
    from src.services import import_export_service

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(args.backup_dir, f"pre_f027_migration_{timestamp}.json")

    os.makedirs(args.backup_dir, exist_ok=True)

    print(f"\n{'=' * 60}")
    print("STEP 1: Exporting current data to backup")
    print(f"{'=' * 60}")
    print(f"Backup file: {backup_file}")

    if args.dry_run:
        print("[DRY RUN] Would export data to backup file")
        # For dry run, still read the data to show what would be transformed
        with open(args.db_path.replace(".db", "_export.json"), "r") as f:
            data = json.load(f)
        return backup_file, data

    # Export to file
    result = import_export_service.export_all_to_json(backup_file)

    # Also load it as dict for transformation
    with open(backup_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Backup created: {backup_file}")
    print(f"  Version: {data.get('version', 'unknown')}")
    print(f"  Products: {len(data.get('products', []))}")
    print(f"  Inventory Items: {len(data.get('inventory_items', []))}")
    print(f"  Purchases: {len(data.get('purchases', []))}")
    print(f"  Suppliers: {len(data.get('suppliers', []))}")
    print(f"  Total records exported: {result.total_records}")

    return backup_file, data


def create_unknown_supplier(data):
    """
    Add Unknown supplier to data for historical records.

    The "Unknown" supplier is used for:
    - Historical purchases where the supplier was not recorded
    - Migrated inventory items that need a Purchase record

    Returns:
        Modified data dict with Unknown supplier added
    """
    print(f"\n{'=' * 60}")
    print("STEP 2: Creating Unknown supplier for historical data")
    print(f"{'=' * 60}")

    # Per data-model.md specification
    unknown_supplier = {
        "id": 1,  # Reserve ID 1 for Unknown
        "uuid": "00000000-0000-0000-0000-000000000001",
        "name": "Unknown",
        "city": "Unknown",
        "state": "XX",  # Intentionally invalid to flag Unknown entries
        "zip_code": "00000",
        "street_address": None,
        "notes": "Auto-created for historical data without supplier info",
        "is_active": True,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    # Initialize suppliers list if not present
    if "suppliers" not in data:
        data["suppliers"] = []

    # Check if Unknown supplier already exists
    existing_unknown = [s for s in data["suppliers"] if s.get("name") == "Unknown"]
    if existing_unknown:
        print("Unknown supplier already exists, skipping creation")
        return data, existing_unknown[0]["id"]

    data["suppliers"].insert(0, unknown_supplier)
    print(f"Created Unknown supplier (ID=1, state='XX')")

    return data, 1  # Return unknown_supplier_id


def transform_inventory_to_purchases(data, unknown_supplier_id):
    """
    Create Purchase records from inventory_items with unit_cost.

    Each inventory_item with a unit_cost gets a corresponding Purchase record.
    The Purchase is linked to the Unknown supplier since we don't know where
    historical items were purchased.

    Returns:
        Tuple of (modified_data, list_of_created_purchases)
    """
    print(f"\n{'=' * 60}")
    print("STEP 3: Creating Purchase records from inventory items")
    print(f"{'=' * 60}")

    # Get existing purchases to determine starting ID
    existing_purchases = data.get("purchases", [])
    max_existing_id = max([p.get("id", 0) for p in existing_purchases], default=0)
    purchase_id = max_existing_id + 1

    new_purchases = []
    warnings = []

    inventory_items = data.get("inventory_items", [])
    print(f"Processing {len(inventory_items)} inventory items...")

    items_with_cost = 0
    items_without_cost = 0

    for item in inventory_items:
        unit_cost = item.get("unit_cost")

        # Skip if no unit_cost (nothing to record)
        if unit_cost is None:
            items_without_cost += 1
            continue

        items_with_cost += 1

        # Handle zero/negative costs
        try:
            cost_value = float(unit_cost)
            if cost_value < 0:
                warnings.append(
                    f"Item {item.get('id')}: negative unit_cost={unit_cost}, using 0.00"
                )
                unit_cost = "0.00"
        except (ValueError, TypeError):
            warnings.append(
                f"Item {item.get('id')}: invalid unit_cost={unit_cost}, using 0.00"
            )
            unit_cost = "0.00"

        # Create purchase record
        purchase = {
            "id": purchase_id,
            "uuid": f"purchase-migrated-from-item-{item.get('id')}",
            "product_id": item.get("product_id"),
            "supplier_id": unknown_supplier_id,  # Historical = Unknown
            "purchase_date": item.get("purchase_date"),
            "unit_price": str(unit_cost),  # Decimal as string
            "quantity_purchased": 1,  # Each inventory item = 1 purchase event
            "notes": f"Migrated from inventory_item {item.get('id')} during F027 migration",
            "created_at": datetime.now().isoformat(),
        }
        new_purchases.append(purchase)
        purchase_id += 1

    # Append new purchases to existing
    data["purchases"] = existing_purchases + new_purchases

    print(f"  Items with unit_cost: {items_with_cost}")
    print(f"  Items without unit_cost: {items_without_cost}")
    print(f"  New purchases created: {len(new_purchases)}")

    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for w in warnings[:5]:  # Show first 5
            print(f"  - {w}")
        if len(warnings) > 5:
            print(f"  ... and {len(warnings) - 5} more")

    return data, new_purchases


def link_items_to_purchases(data, new_purchases):
    """
    Add purchase_id to inventory_items based on created Purchase records.

    Returns:
        Modified data dict with purchase_id set on inventory_items
    """
    print(f"\n{'=' * 60}")
    print("STEP 4: Linking inventory items to Purchase records")
    print(f"{'=' * 60}")

    # Build mapping: item_id → purchase_id from notes
    item_to_purchase = {}
    for purchase in new_purchases:
        notes = purchase.get("notes", "")
        if "inventory_item" in notes:
            try:
                # Extract item ID from "inventory_item 123"
                item_id = int(notes.split("inventory_item ")[-1].split(" ")[0])
                item_to_purchase[item_id] = purchase["id"]
            except (ValueError, IndexError):
                pass

    linked = 0
    already_linked = 0
    no_link = 0

    for item in data.get("inventory_items", []):
        item_id = item.get("id")

        # Check if already linked
        if item.get("purchase_id") is not None:
            already_linked += 1
            continue

        if item_id in item_to_purchase:
            item["purchase_id"] = item_to_purchase[item_id]
            linked += 1
        else:
            # No purchase (no unit_cost) - leave null
            item["purchase_id"] = None
            no_link += 1

    print(f"  Linked to new purchases: {linked}")
    print(f"  Already had purchase_id: {already_linked}")
    print(f"  No purchase (no unit_cost): {no_link}")

    return data


def initialize_product_fields(data):
    """
    Add new fields to products (is_hidden, preferred_supplier_id).

    Returns:
        Modified data dict with new fields on products
    """
    print(f"\n{'=' * 60}")
    print("STEP 5: Initializing new product fields")
    print(f"{'=' * 60}")

    products = data.get("products", [])
    updated = 0

    for product in products:
        # is_hidden: default False (visible)
        if "is_hidden" not in product:
            product["is_hidden"] = False
            updated += 1

        # preferred_supplier_id: default None (no preferred supplier)
        if "preferred_supplier_id" not in product:
            product["preferred_supplier_id"] = None

    print(f"  Products updated: {updated}")
    print(f"  is_hidden=False set for all existing products")

    return data


def validate_transformation(original_data, transformed_data, args):
    """
    Validate transformation preserves data and maintains FK integrity.

    Returns:
        True if validation passes, False otherwise
    """
    print(f"\n{'=' * 60}")
    print("STEP 6: Validating transformation")
    print(f"{'=' * 60}")

    if args.skip_validation:
        print("WARNING: Validation skipped by user request")
        return True

    errors = []
    warnings = []

    # Count preservation checks
    orig_products = len(original_data.get("products", []))
    trans_products = len(transformed_data.get("products", []))
    if orig_products != trans_products:
        errors.append(f"Product count mismatch: {orig_products} → {trans_products}")

    orig_items = len(original_data.get("inventory_items", []))
    trans_items = len(transformed_data.get("inventory_items", []))
    if orig_items != trans_items:
        errors.append(f"InventoryItem count mismatch: {orig_items} → {trans_items}")

    orig_ingredients = len(original_data.get("ingredients", []))
    trans_ingredients = len(transformed_data.get("ingredients", []))
    if orig_ingredients != trans_ingredients:
        errors.append(f"Ingredient count mismatch: {orig_ingredients} → {trans_ingredients}")

    # New entities created
    orig_suppliers = len(original_data.get("suppliers", []))
    trans_suppliers = len(transformed_data.get("suppliers", []))
    orig_purchases = len(original_data.get("purchases", []))
    trans_purchases = len(transformed_data.get("purchases", []))

    print(f"\nRecord counts:")
    print(f"  Ingredients: {orig_ingredients} → {trans_ingredients}")
    print(f"  Products: {orig_products} → {trans_products}")
    print(f"  Inventory Items: {orig_items} → {trans_items}")
    print(f"  Suppliers: {orig_suppliers} → {trans_suppliers} (+{trans_suppliers - orig_suppliers})")
    print(f"  Purchases: {orig_purchases} → {trans_purchases} (+{trans_purchases - orig_purchases})")

    # FK integrity: all purchases reference valid products
    product_ids = {p.get("id") for p in transformed_data.get("products", [])}
    for purchase in transformed_data.get("purchases", []):
        pid = purchase.get("product_id")
        if pid not in product_ids:
            errors.append(
                f"Purchase {purchase.get('id')} references invalid product {pid}"
            )

    # FK integrity: all purchases reference valid suppliers
    supplier_ids = {s.get("id") for s in transformed_data.get("suppliers", [])}
    for purchase in transformed_data.get("purchases", []):
        sid = purchase.get("supplier_id")
        if sid not in supplier_ids:
            errors.append(
                f"Purchase {purchase.get('id')} references invalid supplier {sid}"
            )

    # FK integrity: all items with purchase_id reference valid purchases
    purchase_ids = {p.get("id") for p in transformed_data.get("purchases", [])}
    for item in transformed_data.get("inventory_items", []):
        pid = item.get("purchase_id")
        if pid is not None and pid not in purchase_ids:
            errors.append(
                f"InventoryItem {item.get('id')} references invalid purchase {pid}"
            )

    # Validate all products have new fields
    for product in transformed_data.get("products", []):
        if "is_hidden" not in product:
            errors.append(f"Product {product.get('id')} missing is_hidden field")

    # Report
    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for e in errors:
            print(f"  ❌ {e}")
        return False

    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for w in warnings:
            print(f"  ⚠️ {w}")

    print(f"\n✅ Validation PASSED")
    return True


def execute_migration(data, args):
    """
    Execute the actual migration: delete DB, recreate schema, import data.

    This is the DESTRUCTIVE step. Only called if not in dry-run mode.
    """
    print(f"\n{'=' * 60}")
    print("STEP 7: Executing migration")
    print(f"{'=' * 60}")

    if args.dry_run:
        print("[DRY RUN] Would perform the following:")
        print(f"  1. Delete database: {args.db_path}")
        print(f"  2. Recreate schema with new models")
        print(f"  3. Import transformed data")
        return True

    import shutil
    from src.services.database import engine, Base
    from src.services import import_export_service

    # Step 1: Delete existing database
    if os.path.exists(args.db_path):
        print(f"Deleting existing database: {args.db_path}")
        os.remove(args.db_path)

    # Also remove WAL files if present
    for suffix in ["-wal", "-shm"]:
        wal_file = args.db_path + suffix
        if os.path.exists(wal_file):
            os.remove(wal_file)

    # Step 2: Recreate schema
    print("Recreating schema with new models...")
    Base.metadata.create_all(engine)

    # Step 3: Save transformed data to temp file and import
    print("Importing transformed data...")
    temp_file = os.path.join(args.backup_dir, "temp_transformed.json")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    result = import_export_service.import_all_from_json_v3(temp_file, mode="replace")

    # Cleanup temp file
    os.remove(temp_file)

    print(f"\nImport results:")
    for entity, counts in result.entity_counts.items():
        if isinstance(counts, dict):
            imported = counts.get("imported", 0)
            if imported > 0:
                print(f"  {entity}: {imported}")
        else:
            if counts > 0:
                print(f"  {entity}: {counts}")

    return True


def save_transformed_json(data, args):
    """Save transformed JSON to file for inspection."""
    if args.output_json:
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"\nTransformed JSON saved to: {args.output_json}")


def main():
    """Main migration entry point."""
    args = parse_args()

    print("=" * 60)
    print("F027 Migration Script - Product Catalog Management")
    print("=" * 60)
    print(f"Database: {args.db_path}")
    print(f"Backup directory: {args.backup_dir}")
    print(f"Dry run: {args.dry_run}")

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made")

    # Check database exists
    if not os.path.exists(args.db_path):
        print(f"\n❌ ERROR: Database not found at {args.db_path}")
        return 1

    try:
        # Step 1: Backup
        backup_file, original_data = backup_current_data(args)

        # Keep a copy of original for validation
        import copy
        data = copy.deepcopy(original_data)

        # Step 2: Create Unknown supplier
        data, unknown_supplier_id = create_unknown_supplier(data)

        # Step 3: Create Purchase records from inventory items
        data, new_purchases = transform_inventory_to_purchases(data, unknown_supplier_id)

        # Step 4: Link inventory items to purchases
        data = link_items_to_purchases(data, new_purchases)

        # Step 5: Initialize product fields
        data = initialize_product_fields(data)

        # Save transformed JSON if requested
        save_transformed_json(data, args)

        # Step 6: Validate
        if not validate_transformation(original_data, data, args):
            print("\n❌ Migration aborted due to validation errors")
            return 1

        # Step 7: Execute migration
        if not execute_migration(data, args):
            print("\n❌ Migration failed during execution")
            return 1

        print(f"\n{'=' * 60}")
        if args.dry_run:
            print("DRY RUN COMPLETE - No changes were made")
            print(f"To execute migration, run without --dry-run flag")
        else:
            print("✅ MIGRATION COMPLETE")
            print(f"Backup saved to: {backup_file}")
            print(f"\nIf issues occur, see ROLLBACK PROCEDURE in script header")
        print(f"{'=' * 60}")

        return 0

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
