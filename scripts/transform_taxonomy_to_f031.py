#!/usr/bin/env python3
"""
Transform taxonomy files to F031 import format.

Takes the separate category/subcategory/ingredient taxonomy files and
combines them into a single ingredients import file compatible with
the F031 hierarchy import format.

Usage:
    python scripts/transform_taxonomy_to_f031.py [--output PATH]
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def load_json(path: str) -> list:
    """Load JSON file."""
    with open(path) as f:
        return json.load(f)


def transform_to_f031(categories: list, subcategories: list, ingredients: list) -> dict:
    """
    Transform taxonomy to F031 import format.

    Returns dict in sample_data.json format with hierarchy fields.
    """
    all_ingredients = []
    next_id = 1000  # Start IDs for categories/subcategories at 1000

    # Track category slugs for parent references
    cat_slug_map = {}

    # 1. Add categories as level 0 ingredients
    for cat in categories:
        cat_slug_map[cat['slug']] = cat['slug']
        ingredient = {
            "display_name": cat['name'],
            "slug": cat['slug'],
            "category": None,  # Categories don't have the old category field
            "is_packaging": False,
            "description": f"Category: {cat['description']}",
            "hierarchy_level": 0,
            # parent_slug is None for root categories
        }
        all_ingredients.append(ingredient)

    # 2. Add subcategories as level 1 ingredients
    subcat_slug_map = {}
    for subcat in subcategories:
        subcat_slug_map[subcat['slug']] = subcat['slug']
        ingredient = {
            "display_name": subcat['name'],
            "slug": subcat['slug'],
            "category": None,
            "is_packaging": False,
            "description": f"Subcategory: {subcat['description']}",
            "hierarchy_level": 1,
            "parent_slug": subcat['category_slug'],
        }
        all_ingredients.append(ingredient)

    # 3. Add ingredients as level 2 (leaves)
    for ing in ingredients:
        ingredient = {
            "display_name": ing['name'],
            "slug": ing['slug'],
            "category": None,  # Old category field not needed with hierarchy
            "is_packaging": False,
            "description": ing.get('notes', ''),
            "hierarchy_level": 2,
            "parent_slug": ing['subcategory_slug'],
        }
        all_ingredients.append(ingredient)

    # Build export structure
    export = {
        "version": "3.6",  # F031 version with hierarchy support
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "application": "bake-tracker",
        "description": "Ingredient hierarchy taxonomy - migrated from OPML",
        "ingredients": all_ingredients,
    }

    return export


def validate_references(data: dict) -> list:
    """Validate all parent_slug references exist."""
    errors = []
    slug_set = {ing['slug'] for ing in data['ingredients']}

    for ing in data['ingredients']:
        parent_slug = ing.get('parent_slug')
        if parent_slug and parent_slug not in slug_set:
            errors.append(f"{ing['slug']}: parent_slug '{parent_slug}' not found")

    return errors


def main():
    parser = argparse.ArgumentParser(description='Transform taxonomy to F031 format')
    parser.add_argument('--categories', '-c',
                        default='test_data/categories_taxonomy.json',
                        help='Categories taxonomy file')
    parser.add_argument('--subcategories', '-s',
                        default='test_data/subcategories_taxonomy.json',
                        help='Subcategories taxonomy file')
    parser.add_argument('--ingredients', '-i',
                        default='test_data/ingredients_taxonomy.json',
                        help='Ingredients taxonomy file')
    parser.add_argument('--output', '-o',
                        default='test_data/ingredients_hierarchy_import.json',
                        help='Output file path')
    args = parser.parse_args()

    print("Loading taxonomy files...")
    categories = load_json(args.categories)
    subcategories = load_json(args.subcategories)
    ingredients = load_json(args.ingredients)

    print(f"  Categories: {len(categories)}")
    print(f"  Subcategories: {len(subcategories)}")
    print(f"  Ingredients: {len(ingredients)}")

    print("\nTransforming to F031 format...")
    data = transform_to_f031(categories, subcategories, ingredients)

    print(f"  Total items: {len(data['ingredients'])}")
    print(f"  Level 0 (categories): {sum(1 for i in data['ingredients'] if i['hierarchy_level'] == 0)}")
    print(f"  Level 1 (subcategories): {sum(1 for i in data['ingredients'] if i['hierarchy_level'] == 1)}")
    print(f"  Level 2 (leaves): {sum(1 for i in data['ingredients'] if i['hierarchy_level'] == 2)}")

    # Validate
    print("\nValidating references...")
    errors = validate_references(data)
    if errors:
        print(f"  ERRORS ({len(errors)}):")
        for err in errors[:10]:
            print(f"    - {err}")
        if len(errors) > 10:
            print(f"    ... and {len(errors) - 10} more")
    else:
        print("  All parent references valid!")

    # Write output
    output_path = Path(args.output)
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\nWrote: {output_path}")

    # Summary
    print("\n" + "="*60)
    print("TRANSFORMATION COMPLETE")
    print("="*60)
    print(f"Output: {output_path}")
    print(f"Version: {data['version']}")
    print(f"Total ingredients: {len(data['ingredients'])}")
    print(f"Validation errors: {len(errors)}")
    print("="*60)

    if errors:
        print("\nWARNING: Fix validation errors before importing!")
        return 1

    print("\nReady for import with:")
    print(f"  python -c \"from src.services.import_export_service import import_data; import_data('{output_path}')\"")

    return 0


if __name__ == '__main__':
    exit(main())
