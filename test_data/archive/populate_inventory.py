#!/usr/bin/env python3
"""
Populate initial inventory from CSV product quantities.

Reads products_incomplete_updated.csv and creates InventoryItem records
based on the product_quantity column.

Quantity interpretation:
- blank or empty: 1 full package
- 0: Skip (no inventory)
- < 1 (decimal): Percentage of package (0.5 = 50%)
- 1: 1 full package
- > 1 (decimal like 1.2): 1 full package + 0.2 partial
- > 1 (integer like 2): N full packages
"""

import csv
import sys
from datetime import date
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.database import session_scope, init_database
from src.models.product import Product
from src.models.ingredient import Ingredient
from src.models.inventory_item import InventoryItem


def parse_quantity(qty_str: str) -> float | None:
    """
    Parse product_quantity string.

    Returns:
        float value, or None to skip (quantity = 0)
    """
    if qty_str is None or qty_str.strip() == "":
        return 1.0  # blank = 1 full package

    try:
        qty = float(qty_str.strip())
        if qty == 0:
            return None  # Skip
        return qty
    except ValueError:
        return None  # Invalid = skip


def create_inventory_items(
    product: Product,
    quantity_multiplier: float,
    purchase_date: date
) -> list[dict]:
    """
    Create inventory item data based on quantity multiplier.

    Args:
        product: The Product object
        quantity_multiplier: Value from product_quantity column
        purchase_date: Date for all items

    Returns:
        List of dicts with inventory item data
    """
    package_qty = product.package_unit_quantity
    package_unit = product.package_unit
    items = []

    if quantity_multiplier <= 0:
        return items

    # Split into full packages and partial
    full_packages = int(quantity_multiplier)
    partial_fraction = quantity_multiplier - full_packages

    # Create full package items
    for i in range(full_packages):
        items.append({
            "product_id": product.id,
            "quantity": package_qty,
            "purchase_date": purchase_date,
            "location": "pantry",
            "notes": f"Initial inventory - full package ({i+1}/{full_packages})" if full_packages > 1 else "Initial inventory - full package"
        })

    # Create partial package item if needed
    if partial_fraction > 0.001:  # Avoid floating point issues
        partial_qty = package_qty * partial_fraction
        items.append({
            "product_id": product.id,
            "quantity": round(partial_qty, 2),
            "purchase_date": purchase_date,
            "location": "pantry",
            "notes": f"Initial inventory - partial package ({partial_fraction:.0%})"
        })

    return items


def main():
    csv_path = Path(__file__).parent / "products_incomplete_updated.csv"
    today = date.today()

    # Initialize database
    init_database()

    # Statistics
    stats = {
        "rows_processed": 0,
        "rows_skipped_zero": 0,
        "rows_skipped_no_product": 0,
        "rows_skipped_multiple_products": 0,
        "rows_skipped_invalid_qty": 0,
        "inventory_items_created": 0,
        "products_with_inventory": 0,
    }

    missing_products = []
    multiple_matches = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Processing {len(rows)} rows from CSV...")
    print("=" * 60)

    with session_scope() as session:
        for row in rows:
            stats["rows_processed"] += 1

            brand = row.get("brand", "").strip()
            ingredient_slug = row.get("ingredient_slug", "").strip()
            product_name = row.get("product_name", "").strip() or None

            try:
                pkg_qty = float(row.get("package_unit_quantity", 0))
            except (ValueError, TypeError):
                pkg_qty = None

            pkg_unit = row.get("package_unit", "").strip()
            qty_str = row.get("product_quantity", "").strip()

            # Parse quantity
            quantity_multiplier = parse_quantity(qty_str)

            if quantity_multiplier is None:
                stats["rows_skipped_zero"] += 1
                continue

            if not ingredient_slug or pkg_qty is None or not pkg_unit:
                stats["rows_skipped_invalid_qty"] += 1
                continue

            # Find ingredient
            ingredient = session.query(Ingredient).filter_by(slug=ingredient_slug).first()
            if not ingredient:
                stats["rows_skipped_no_product"] += 1
                missing_products.append(f"{brand} {ingredient_slug} (ingredient not found)")
                continue

            # Find product by brand, ingredient, package_unit_quantity, package_unit
            # Note: We ignore product_name since most DB products don't have it set
            query = session.query(Product).filter(
                Product.ingredient_id == ingredient.id,
                Product.brand == brand,
                Product.package_unit_quantity == pkg_qty,
                Product.package_unit == pkg_unit
            )

            matching_products = query.all()

            if len(matching_products) == 0:
                stats["rows_skipped_no_product"] += 1
                missing_products.append(
                    f"{brand} {ingredient_slug} {pkg_qty} {pkg_unit}"
                    + (f" ({product_name})" if product_name else "")
                )
                continue

            if len(matching_products) > 1:
                stats["rows_skipped_multiple_products"] += 1
                multiple_matches.append(
                    f"{brand} {ingredient_slug} {pkg_qty} {pkg_unit}: {len(matching_products)} matches"
                )
                continue

            product = matching_products[0]

            # Create inventory items
            items_data = create_inventory_items(product, quantity_multiplier, today)

            for item_data in items_data:
                inv_item = InventoryItem(**item_data)
                session.add(inv_item)
                stats["inventory_items_created"] += 1

            if items_data:
                stats["products_with_inventory"] += 1

        # Commit all changes
        session.commit()

    # Print report
    print("\n" + "=" * 60)
    print("INVENTORY POPULATION REPORT")
    print("=" * 60)
    print(f"Rows processed:              {stats['rows_processed']}")
    print(f"Products with inventory:     {stats['products_with_inventory']}")
    print(f"Inventory items created:     {stats['inventory_items_created']}")
    print("-" * 60)
    print(f"Skipped (quantity = 0):      {stats['rows_skipped_zero']}")
    print(f"Skipped (product not found): {stats['rows_skipped_no_product']}")
    print(f"Skipped (multiple matches):  {stats['rows_skipped_multiple_products']}")
    print(f"Skipped (invalid data):      {stats['rows_skipped_invalid_qty']}")

    if missing_products:
        print("\n" + "-" * 60)
        print(f"PRODUCTS NOT FOUND ({len(missing_products)}):")
        for p in missing_products[:20]:
            print(f"  - {p}")
        if len(missing_products) > 20:
            print(f"  ... and {len(missing_products) - 20} more")

    if multiple_matches:
        print("\n" + "-" * 60)
        print(f"MULTIPLE MATCHES ({len(multiple_matches)}):")
        for m in multiple_matches:
            print(f"  - {m}")

    print("\n" + "=" * 60)
    print("Done!")

    return stats


if __name__ == "__main__":
    main()
