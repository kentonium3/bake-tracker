#!/usr/bin/env python3
"""
Migration script to transform MaterialUnits from old schema (material_slug)
to new schema (material_product_slug).

Feature 084: MaterialUnit Schema Refactor

Usage:
    python scripts/migrate_material_units.py input.json output.json

The script:
1. Reads old-format export JSON
2. Transforms MaterialUnits using duplication strategy (N products x M units)
3. Flags orphaned MaterialUnits (Materials with 0 products)
4. Logs Compositions with material_id (user must fix manually)
5. Writes new-format JSON for import
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set


@dataclass
class MigrationLog:
    """Tracks migration decisions and statistics."""

    material_units_transformed: int = 0
    material_units_created: int = 0
    material_units_orphaned: int = 0
    compositions_skipped: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)

    def log_decision(self, message: str):
        self.decisions.append(message)
        print(f"  [DECISION] {message}")

    def log_warning(self, message: str):
        self.warnings.append(message)
        print(f"  [WARNING] {message}")

    def log_error(self, message: str):
        self.errors.append(message)
        print(f"  [ERROR] {message}")

    def summary(self) -> str:
        return f"""
Migration Summary
=================
MaterialUnits processed: {self.material_units_transformed}
MaterialUnits created (after duplication): {self.material_units_created}
Orphaned MaterialUnits (no products): {self.material_units_orphaned}
Compositions skipped (material_slug): {self.compositions_skipped}
Errors: {len(self.errors)}
Warnings: {len(self.warnings)}
"""


def main():
    parser = argparse.ArgumentParser(
        description="Transform MaterialUnits from old schema to new schema"
    )
    parser.add_argument("input_file", help="Input JSON file (old format)")
    parser.add_argument("output_file", help="Output JSON file (new format)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without writing output",
    )
    parser.add_argument("--log-file", help="Write detailed log to file")
    parser.add_argument(
        "--orphan-file",
        help="Write orphaned MaterialUnits to separate file",
    )

    args = parser.parse_args()

    # Load input
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Run migration
    log = MigrationLog()
    output_data, orphaned_units = transform_export_data(data, log)

    # Print summary
    print(log.summary())

    # Write output (unless dry run)
    if not args.dry_run:
        output_path = Path(args.output_file)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"Output written to: {output_path}")

    # Write orphan file if requested and there are orphans
    if args.orphan_file and orphaned_units:
        with open(args.orphan_file, "w", encoding="utf-8") as f:
            json.dump(orphaned_units, f, indent=2, ensure_ascii=False)
        print(f"Orphaned units written to: {args.orphan_file}")

    # Write log file if requested
    if args.log_file:
        with open(args.log_file, "w", encoding="utf-8") as f:
            f.write(f"Migration Log - {datetime.now().isoformat()}\n")
            f.write("=" * 50 + "\n\n")
            f.write(log.summary())
            f.write("\nDecisions:\n")
            for d in log.decisions:
                f.write(f"  - {d}\n")
            f.write("\nWarnings:\n")
            for w in log.warnings:
                f.write(f"  - {w}\n")
            f.write("\nErrors:\n")
            for e in log.errors:
                f.write(f"  - {e}\n")
        print(f"Log written to: {args.log_file}")

    # Exit with error code if there were errors
    if log.errors:
        sys.exit(1)


def transform_export_data(data: Dict, log: MigrationLog) -> tuple:
    """
    Transform entire export data from old to new schema.

    Returns:
        Tuple of (transformed_data, orphaned_units)
    """
    # Copy data structure, excluding items we'll transform
    output = {
        k: v for k, v in data.items() if k not in ["material_units", "compositions"]
    }

    # Build lookups from existing data
    materials = {m["slug"]: m for m in data.get("materials", [])}
    products = data.get("material_products", [])
    products_by_material = build_products_by_material_lookup(products)

    # Transform MaterialUnits
    transformed_units, orphaned_units = transform_material_units(
        data.get("material_units", []),
        materials,
        products_by_material,
        log,
    )
    output["material_units"] = transformed_units

    # Transform Compositions (skip material_slug)
    output["compositions"] = transform_compositions(
        data.get("compositions", []),
        log,
    )

    # Warn about orphans
    if log.material_units_orphaned > 0:
        log.log_warning(
            f"{log.material_units_orphaned} MaterialUnits were orphaned. "
            f"These units will NOT be in the output file. "
            f"To migrate them: create MaterialProducts for their Materials, "
            f"then re-run migration."
        )

    return output, orphaned_units


def build_products_by_material_lookup(products: List[Dict]) -> Dict[str, List[Dict]]:
    """Build lookup: material_slug -> list of products."""
    lookup: Dict[str, List[Dict]] = {}
    for p in products:
        mat_slug = p.get("material_slug", "")
        if mat_slug:
            if mat_slug not in lookup:
                lookup[mat_slug] = []
            lookup[mat_slug].append(p)
    return lookup


def get_unique_slug(base_slug: str, existing_slugs: Set[str]) -> str:
    """Generate unique slug, adding suffix if needed."""
    if base_slug not in existing_slugs:
        return base_slug
    for i in range(2, 1000):
        candidate = f"{base_slug}-{i}"
        if candidate not in existing_slugs:
            return candidate
    # Fallback with timestamp
    return f"{base_slug}-{int(datetime.now().timestamp())}"


def transform_material_units(
    units: List[Dict],
    materials: Dict[str, Dict],
    products_by_material: Dict[str, List[Dict]],
    log: MigrationLog,
) -> tuple:
    """
    Transform MaterialUnits from old schema to new schema.

    For each MaterialUnit with material_slug:
    - Find all MaterialProducts for that Material
    - Create one MaterialUnit per product (duplication)

    Returns:
        Tuple of (transformed_units, orphaned_units)
    """
    transformed = []
    orphaned = []

    # Track slugs per product to handle collisions
    slugs_by_product: Dict[str, Set[str]] = {}

    for unit in units:
        log.material_units_transformed += 1
        material_slug = unit.get("material_slug")

        # Check if already in new format
        if "material_product_slug" in unit and not material_slug:
            # Already migrated, pass through
            transformed.append(unit)
            log.material_units_created += 1
            continue

        if not material_slug:
            log.log_warning(
                f"MaterialUnit '{unit.get('name', 'unknown')}' "
                f"has no material_slug or material_product_slug - skipping"
            )
            continue

        # Get products for this material
        products = products_by_material.get(material_slug, [])

        if not products:
            # Orphaned unit - no products to assign
            log.material_units_orphaned += 1
            log.log_decision(
                f"ORPHANED: MaterialUnit '{unit.get('name')}' "
                f"(material='{material_slug}') has no MaterialProducts. "
                f"ACTION: Create MaterialProducts for this Material first, "
                f"then re-run migration."
            )
            orphaned.append(unit)
            continue

        # Create one unit per product (duplication)
        log.log_decision(
            f"DUPLICATE: MaterialUnit '{unit.get('name')}' "
            f"(material='{material_slug}') -> {len(products)} products"
        )

        for product in products:
            product_slug = product["slug"]

            # Initialize slug tracking for this product
            if product_slug not in slugs_by_product:
                slugs_by_product[product_slug] = set()

            # Generate unique slug within product
            base_slug = unit.get("slug", "")
            unique_slug = get_unique_slug(base_slug, slugs_by_product[product_slug])
            slugs_by_product[product_slug].add(unique_slug)

            new_unit = {
                "material_product_slug": product_slug,
                "name": unit.get("name"),
                "slug": unique_slug,
                "quantity_per_unit": unit.get("quantity_per_unit"),
                "description": unit.get("description"),
            }
            # Generate new UUID (let import generate it by setting to None)
            new_unit["uuid"] = None

            transformed.append(new_unit)
            log.material_units_created += 1

    return transformed, orphaned


def transform_compositions(
    compositions: List[Dict],
    log: MigrationLog,
) -> List[Dict]:
    """
    Transform Compositions, skipping those with material_slug.

    Compositions with material_slug (old generic material reference)
    cannot be auto-migrated - user must manually specify which
    MaterialUnit to use.
    """
    transformed = []
    skipped_details = []

    for comp in compositions:
        material_slug = comp.get("material_slug")

        if material_slug:
            # Skip this composition
            log.compositions_skipped += 1
            assembly_slug = comp.get("finished_good_slug", comp.get("assembly_slug", "unknown"))
            package_name = comp.get("package_name", "")
            parent = assembly_slug or package_name or "unknown"

            skipped_details.append(
                {
                    "parent": parent,
                    "material_slug": material_slug,
                    "quantity": comp.get("component_quantity", comp.get("quantity")),
                }
            )

            log.log_decision(
                f"SKIPPED: Composition in '{parent}' "
                f"references material_slug='{material_slug}'. "
                f"ACTION: Edit export file to replace material_slug "
                f"with specific material_unit_slug."
            )
            continue

        # Pass through compositions without material_slug
        transformed.append(comp)

    # Write skipped compositions summary
    if skipped_details:
        log.log_warning(
            f"\n{len(skipped_details)} Compositions were skipped. "
            f"These must be manually edited in the export file:\n"
            + "\n".join(
                f"  - Parent '{s['parent']}': "
                f"material='{s['material_slug']}' qty={s['quantity']}"
                for s in skipped_details
            )
        )

    return transformed


if __name__ == "__main__":
    main()
