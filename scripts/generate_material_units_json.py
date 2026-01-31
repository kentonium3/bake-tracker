#!/usr/bin/env python3
"""
Generate material_units.json for all "each" type material products.

This script reads material_products.json and materials.json from a backup
directory and generates the corresponding material_units.json with
auto-generated units for all "each" type products.

Usage:
    python scripts/generate_material_units_json.py /path/to/backup/dir

The script will:
1. Read materials.json to build material_slug -> base_unit_type lookup
2. Read material_products.json
3. For each product whose material has base_unit_type="each":
   - Create a MaterialUnit named "1 {product_name}"
   - Set quantity_per_unit=1.0
   - Generate slug from name
4. Write material_units.json to the same backup directory

Products with linear_cm or square_cm materials are skipped (user must
define lengths/areas manually via the UI).
"""

import argparse
import json
import re
import sys
from pathlib import Path


def generate_slug(name: str) -> str:
    """Generate URL-safe slug from name using hyphen style."""
    if not name:
        return ""
    # Lowercase
    slug = name.lower()
    # Replace spaces and underscores with hyphens
    slug = re.sub(r"[\s_]+", "-", slug)
    # Remove non-alphanumeric except hyphens
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    # Collapse multiple hyphens
    slug = re.sub(r"-+", "-", slug)
    # Strip leading/trailing hyphens
    slug = slug.strip("-")
    return slug


def main():
    parser = argparse.ArgumentParser(
        description="Generate material_units.json for 'each' type products"
    )
    parser.add_argument("backup_dir", help="Path to backup directory")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without writing",
    )

    args = parser.parse_args()
    backup_path = Path(args.backup_dir)

    # Validate backup directory
    if not backup_path.exists():
        print(f"Error: Backup directory not found: {backup_path}")
        sys.exit(1)

    materials_file = backup_path / "materials.json"
    products_file = backup_path / "material_products.json"
    output_file = backup_path / "material_units.json"

    if not materials_file.exists():
        print(f"Error: materials.json not found in {backup_path}")
        sys.exit(1)

    if not products_file.exists():
        print(f"Error: material_products.json not found in {backup_path}")
        sys.exit(1)

    # Load materials to build lookup
    with open(materials_file, "r", encoding="utf-8") as f:
        materials_data = json.load(f)

    material_base_types = {}
    for mat in materials_data.get("records", []):
        slug = mat.get("slug")
        base_type = mat.get("base_unit_type", "each")
        if slug:
            material_base_types[slug] = base_type

    print(f"Loaded {len(material_base_types)} materials")

    # Load products
    with open(products_file, "r", encoding="utf-8") as f:
        products_data = json.load(f)

    products = products_data.get("records", [])
    print(f"Loaded {len(products)} material products")

    # Generate units for "each" type products
    units = []
    skipped_linear = []
    skipped_area = []

    for product in products:
        product_slug = product.get("slug")
        product_name = product.get("name")
        material_slug = product.get("material_slug")

        if not product_slug or not product_name:
            print(f"  Warning: Skipping product with missing slug/name: {product}")
            continue

        base_type = material_base_types.get(material_slug, "each")

        if base_type == "linear_cm":
            skipped_linear.append(product_name)
            continue
        elif base_type == "square_cm":
            skipped_area.append(product_name)
            continue

        # Generate unit for "each" type
        unit_name = f"1 {product_name}"
        unit_slug = generate_slug(unit_name)

        unit = {
            "material_product_slug": product_slug,
            "name": unit_name,
            "slug": unit_slug,
            "quantity_per_unit": 1.0,
            "description": f"Auto-generated unit for {product_name}",
            "uuid": None,  # Let import generate new UUID
        }
        units.append(unit)

    print(f"\nGenerated {len(units)} material units for 'each' type products")

    if skipped_linear:
        print(f"\nSkipped {len(skipped_linear)} linear_cm products (define lengths in UI):")
        for name in skipped_linear:
            print(f"  - {name}")

    if skipped_area:
        print(f"\nSkipped {len(skipped_area)} square_cm products (define areas in UI):")
        for name in skipped_area:
            print(f"  - {name}")

    # Prepare output
    output = {
        "version": "1.0",
        "entity_type": "material_units",
        "records": units,
    }

    if args.dry_run:
        print("\n[DRY RUN] Would write the following:")
        print(json.dumps(output, indent=2))
    else:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"\nWrote {output_file}")


if __name__ == "__main__":
    main()
