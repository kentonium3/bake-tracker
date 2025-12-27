#!/usr/bin/env python3
"""
Ingredient Consolidation Script

This script handles ingredient merging and renaming operations:
1. Updates ingredient slugs and display names
2. Remaps products from old ingredients to new consolidated ones
3. Deletes orphaned old ingredients
4. Updates JSON export files

Usage:
    python scripts/consolidate_ingredients.py [--dry-run] [--db PATH]

Options:
    --dry-run   Show what would be done without making changes
    --db PATH   Database path (default: data/bake_tracker.db)
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

# Import models after path setup
from src.models import Ingredient, Product, RecipeIngredient


@contextmanager
def get_session(db_path: str, dry_run: bool = False):
    """Create a session for the specified database path."""
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
        if dry_run:
            session.rollback()
        else:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Define consolidation operations
# Format: (old_slug, new_slug, new_display_name, operation_type)
# operation_type: "merge" (old -> existing new), "rename" (change slug/name in place)
CONSOLIDATIONS = [
    # Merges - old ingredient products move to existing ingredient
    ("poppy_seeds_blue", "poppy_seeds", "Poppy seeds", "merge"),
    ("almond_flour", "flour_almond", "Flour, almond", "merge"),
    ("rice_flour_brown", "flour_rice", "Flour, rice", "merge"),
    ("rice_flour_white", "flour_rice", "Flour, rice", "merge"),

    # Renames - change slug and display name in place
    ("all_purpose_wheat_flour", "flour_all_purpose", "Flour, all-purpose", "rename"),
    ("hazelnut_flour", "flour_hazelnut", "Flour, hazelnut", "rename"),
    ("semolina_flour", "flour_semolina", "Flour, semolina", "rename"),
    ("sorghum_flour", "flour_sorghum", "Flour, sorghum", "rename"),
]


def get_ingredient_by_slug(session, slug):
    """Get ingredient by slug."""
    return session.query(Ingredient).filter(Ingredient.slug == slug).first()


def get_products_by_ingredient(session, ingredient_id):
    """Get all products using an ingredient."""
    return session.query(Product).filter(Product.ingredient_id == ingredient_id).all()


def get_recipe_ingredients_by_ingredient(session, ingredient_id):
    """Get all recipe_ingredients using an ingredient."""
    return session.query(RecipeIngredient).filter(RecipeIngredient.ingredient_id == ingredient_id).all()


def consolidate_ingredients(db_path: str, dry_run: bool = False):
    """Run ingredient consolidation."""
    # Convert relative path to absolute
    if not os.path.isabs(db_path):
        db_path = os.path.abspath(db_path)

    print(f"\n{'=' * 60}")
    print(f"Ingredient Consolidation {'(DRY RUN)' if dry_run else ''}")
    print(f"Database: {db_path}")
    print(f"{'=' * 60}\n")

    results = {
        "renames": [],
        "merges": [],
        "products_updated": [],
        "ingredients_deleted": [],
        "errors": [],
    }

    with get_session(db_path, dry_run=dry_run) as session:
        for old_slug, new_slug, new_display, op_type in CONSOLIDATIONS:
            print(f"\n--- {op_type.upper()}: {old_slug} -> {new_slug} ---")

            old_ingredient = get_ingredient_by_slug(session, old_slug)

            if not old_ingredient:
                print(f"  SKIP: '{old_slug}' not found in database")
                continue

            if op_type == "rename":
                # Simple rename - update slug and display name in place
                products = get_products_by_ingredient(session, old_ingredient.id)
                print(f"  Found ingredient: id={old_ingredient.id}, '{old_ingredient.display_name}'")
                print(f"  Products using this ingredient: {len(products)}")

                if not dry_run:
                    old_ingredient.slug = new_slug
                    old_ingredient.display_name = new_display
                    session.flush()

                results["renames"].append({
                    "old_slug": old_slug,
                    "new_slug": new_slug,
                    "new_display": new_display,
                    "product_count": len(products),
                })
                print(f"  RENAMED: {old_slug} -> {new_slug} ('{new_display}')")

            elif op_type == "merge":
                # Merge - move products and recipe_ingredients to target, delete old
                new_ingredient = get_ingredient_by_slug(session, new_slug)

                if not new_ingredient:
                    # Target doesn't exist - create it by renaming old ingredient
                    print(f"  Target '{new_slug}' not found - will rename instead")
                    products = get_products_by_ingredient(session, old_ingredient.id)

                    if not dry_run:
                        old_ingredient.slug = new_slug
                        old_ingredient.display_name = new_display
                        session.flush()

                    results["renames"].append({
                        "old_slug": old_slug,
                        "new_slug": new_slug,
                        "new_display": new_display,
                        "product_count": len(products),
                    })
                    print(f"  RENAMED: {old_slug} -> {new_slug} ('{new_display}')")
                else:
                    # Target exists - move products, recipe_ingredients, and delete old
                    products = get_products_by_ingredient(session, old_ingredient.id)
                    recipe_ings = get_recipe_ingredients_by_ingredient(session, old_ingredient.id)

                    print(f"  Source ingredient: id={old_ingredient.id}, '{old_ingredient.display_name}'")
                    print(f"  Target ingredient: id={new_ingredient.id}, '{new_ingredient.display_name}'")
                    print(f"  Products to migrate: {len(products)}")
                    print(f"  Recipe ingredients to migrate: {len(recipe_ings)}")

                    # Migrate products
                    for product in products:
                        print(f"    - Product {product.id}: '{product.product_name}' ({product.brand})")
                        results["products_updated"].append({
                            "product_id": product.id,
                            "product_name": product.product_name,
                            "old_ingredient": old_slug,
                            "new_ingredient": new_slug,
                        })

                        if not dry_run:
                            product.ingredient_id = new_ingredient.id

                    # Migrate recipe ingredients
                    for ri in recipe_ings:
                        print(f"    - Recipe ingredient {ri.id}: recipe_id={ri.recipe_id}")
                        if not dry_run:
                            ri.ingredient_id = new_ingredient.id

                    if not dry_run:
                        session.flush()
                        # Delete old ingredient
                        session.delete(old_ingredient)
                        session.flush()

                    results["merges"].append({
                        "old_slug": old_slug,
                        "new_slug": new_slug,
                        "products_migrated": len(products),
                        "recipe_ingredients_migrated": len(recipe_ings),
                    })
                    results["ingredients_deleted"].append(old_slug)
                    print(f"  MERGED: {len(products)} products, {len(recipe_ings)} recipe ingredients moved")

                    # Update display name on target if needed
                    if new_ingredient.display_name != new_display:
                        print(f"  Updating target display name: '{new_ingredient.display_name}' -> '{new_display}'")
                        if not dry_run:
                            new_ingredient.display_name = new_display
                            session.flush()

        # Commit/rollback handled by context manager
        print("\n" + "=" * 60)
        if not dry_run:
            print("CHANGES COMMITTED")
        else:
            print("DRY RUN - NO CHANGES MADE")

    # Print summary
    print("\n--- SUMMARY ---")
    print(f"Renames: {len(results['renames'])}")
    print(f"Merges: {len(results['merges'])}")
    print(f"Products updated: {len(results['products_updated'])}")
    print(f"Ingredients deleted: {len(results['ingredients_deleted'])}")

    return results


def update_consolidation_mapping(mapping_path: str, dry_run: bool = False):
    """Update the consolidation mapping JSON file."""
    print(f"\n--- Updating {mapping_path} ---")

    # Read existing mapping
    with open(mapping_path, 'r') as f:
        mapping = json.load(f)

    # Add new mappings
    new_mappings = {
        "poppy_seeds_blue": "poppy_seeds",
        "all_purpose_wheat_flour": "flour_all_purpose",
        "almond_flour": "flour_almond",
        "hazelnut_flour": "flour_hazelnut",
        "rice_flour_brown": "flour_rice",
        "rice_flour_white": "flour_rice",
        "semolina_flour": "flour_semolina",
        "sorghum_flour": "flour_sorghum",
    }

    added = []
    for old, new in new_mappings.items():
        if old not in mapping:
            mapping[old] = new
            added.append(f"  {old} -> {new}")

    if added:
        print("Adding mappings:")
        for a in added:
            print(a)

        if not dry_run:
            # Sort mapping and write back
            sorted_mapping = dict(sorted(mapping.items()))
            with open(mapping_path, 'w') as f:
                json.dump(sorted_mapping, f, indent=2)
                f.write('\n')
            print("  Mapping file updated")
    else:
        print("  No new mappings to add")


def update_json_files(test_data_dir: str, dry_run: bool = False):
    """Update sample_data.json and view_*.json files with new ingredient slugs."""
    print(f"\n--- Updating JSON files in {test_data_dir} ---")

    # Mapping of old slugs to new slugs for JSON replacement
    slug_replacements = {
        "poppy_seeds_blue": "poppy_seeds",
        "all_purpose_wheat_flour": "flour_all_purpose",
        "almond_flour": "flour_almond",
        "hazelnut_flour": "flour_hazelnut",
        "rice_flour_brown": "flour_rice",
        "rice_flour_white": "flour_rice",
        "semolina_flour": "flour_semolina",
        "sorghum_flour": "flour_sorghum",
    }

    # Display name replacements
    display_replacements = {
        "Poppy seeds, blue": "Poppy seeds",
        "All-purpose wheat flour": "Flour, all-purpose",
        "Almond flour": "Flour, almond",
        "Hazelnut flour": "Flour, hazelnut",
        "Rice flour, brown": "Flour, rice",
        "Rice flour, white": "Flour, rice",
        "Semolina flour": "Flour, semolina",
        "Sorghum flour": "Flour, sorghum",
    }

    json_files = [
        "sample_data.json",
        "view_ingredients.json",
        "view_products.json",
        "view_inventory.json",
        "ingredients_catalog.json",
        "products_catalog.json",
    ]

    for filename in json_files:
        filepath = os.path.join(test_data_dir, filename)
        if not os.path.exists(filepath):
            print(f"  SKIP: {filename} not found")
            continue

        with open(filepath, 'r') as f:
            content = f.read()

        original_content = content
        changes = []

        # Replace slugs
        for old, new in slug_replacements.items():
            if old in content:
                content = content.replace(f'"{old}"', f'"{new}"')
                content = content.replace(f"'{old}'", f"'{new}'")
                changes.append(f"slug: {old} -> {new}")

        # Replace display names
        for old, new in display_replacements.items():
            if old in content:
                content = content.replace(old, new)
                changes.append(f"name: {old} -> {new}")

        if changes:
            print(f"  {filename}:")
            for change in changes:
                print(f"    - {change}")

            if not dry_run:
                with open(filepath, 'w') as f:
                    f.write(content)
                print(f"    Updated")
        else:
            print(f"  {filename}: no changes needed")


def main():
    parser = argparse.ArgumentParser(description="Consolidate ingredients")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    parser.add_argument("--db", default="data/bake_tracker.db", help="Database path")
    parser.add_argument("--prod-db", default=None, help="Production database path")
    parser.add_argument("--skip-json", action="store_true", help="Skip JSON file updates")
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Update mapping file first
    mapping_path = "test_data/ingredient_consolidation_mapping.json"
    update_consolidation_mapping(mapping_path, args.dry_run)

    # Update development database
    print(f"\n{'=' * 60}")
    print("DEVELOPMENT DATABASE")
    print(f"{'=' * 60}")
    consolidate_ingredients(args.db, args.dry_run)

    # Update production database if specified
    if args.prod_db:
        print(f"\n{'=' * 60}")
        print("PRODUCTION DATABASE")
        print(f"{'=' * 60}")
        consolidate_ingredients(args.prod_db, args.dry_run)

    # Update JSON files
    if not args.skip_json:
        update_json_files("test_data", args.dry_run)

    print("\n" + "=" * 60)
    print("DONE" + (" (DRY RUN)" if args.dry_run else ""))
    print("=" * 60)


if __name__ == "__main__":
    main()
