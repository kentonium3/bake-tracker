#!/usr/bin/env python3
"""
Transform legacy recipe yield data to FinishedUnit structure.

This script converts recipe yield fields (yield_quantity, yield_unit, yield_description)
into separate FinishedUnit entries during the export/transform/import migration cycle.

Feature: 056-unified-yield-management

Usage:
    python scripts/transform_yield_data.py input.json output.json
    python scripts/transform_yield_data.py input.json output.json --dry-run
"""
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def slugify(text: str) -> str:
    """
    Convert text to slug format.

    Args:
        text: Input text to slugify

    Returns:
        Lowercase slug with underscores, no special characters
    """
    if not text:
        return ""
    text = text.lower().strip()
    # Remove special characters except whitespace, hyphens, underscores
    text = re.sub(r'[^\w\s-]', '', text)
    # Replace whitespace and hyphens with underscores
    text = re.sub(r'[\s_-]+', '_', text)
    return text.strip('_')


def transform_recipe(recipe: dict, existing_slugs: set) -> tuple[dict, list[dict]]:
    """
    Transform a single recipe, extracting yield data to FinishedUnit.

    Args:
        recipe: Recipe dictionary from JSON
        existing_slugs: Set of already-used slugs (for collision detection)

    Returns:
        Tuple of (transformed_recipe, list_of_finished_units)
    """
    finished_units = []

    # Extract yield data
    yield_quantity = recipe.get('yield_quantity')
    yield_unit = recipe.get('yield_unit')
    yield_description = recipe.get('yield_description')

    # Only create FinishedUnit if we have yield data
    if yield_quantity is not None and yield_unit:
        # Generate slug
        recipe_name = recipe.get('name', 'unknown')
        recipe_slug = slugify(recipe_name)
        yield_suffix = slugify(yield_description) if yield_description else 'standard'
        base_slug = f"{recipe_slug}_{yield_suffix}"

        # Handle collision
        slug = base_slug
        counter = 2
        while slug in existing_slugs:
            slug = f"{base_slug}_{counter}"
            counter += 1
        existing_slugs.add(slug)

        # Generate display_name
        if yield_description:
            display_name = yield_description
        else:
            display_name = f"Standard {recipe_name}"

        # Create FinishedUnit entry
        finished_unit = {
            'slug': slug,
            'display_name': display_name,
            'recipe_name': recipe_name,
            'category': recipe.get('category'),
            'yield_mode': 'discrete_count',
            'items_per_batch': int(yield_quantity) if yield_quantity else None,
            'item_unit': yield_unit or 'each',
            'batch_percentage': None,
            'portion_description': None,
            'inventory_count': 0,
            'is_archived': False
        }
        finished_units.append(finished_unit)

    # Null out legacy fields in recipe (create copy to avoid mutation)
    transformed_recipe = recipe.copy()
    transformed_recipe['yield_quantity'] = None
    transformed_recipe['yield_unit'] = None
    transformed_recipe['yield_description'] = None

    return transformed_recipe, finished_units


def transform_data(data: dict) -> dict:
    """
    Transform entire export data structure.

    Args:
        data: Full JSON export data with 'recipes' key

    Returns:
        Transformed data with 'finished_units' added and recipe yield fields nulled
    """
    result = data.copy()
    existing_slugs = set()
    all_finished_units = []

    # Collect any existing finished_units slugs to avoid collision
    if 'finished_units' in data:
        for fu in data['finished_units']:
            if fu.get('slug'):
                existing_slugs.add(fu['slug'])
        all_finished_units.extend(data['finished_units'])

    # Transform recipes
    if 'recipes' in data:
        transformed_recipes = []
        for recipe in data['recipes']:
            transformed_recipe, finished_units = transform_recipe(recipe, existing_slugs)
            transformed_recipes.append(transformed_recipe)
            all_finished_units.extend(finished_units)
        result['recipes'] = transformed_recipes

    # Set finished_units (may have been extended with existing ones)
    result['finished_units'] = all_finished_units

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Transform legacy recipe yield data to FinishedUnit structure'
    )
    parser.add_argument('input_file', type=Path, help='Input JSON file')
    parser.add_argument('output_file', type=Path, help='Output JSON file')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print transformation summary without writing')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Print detailed transformation info')

    args = parser.parse_args()

    # Validate input file exists
    if not args.input_file.exists():
        print(f"Error: Input file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    # Read input
    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {args.input_file}: {e}", file=sys.stderr)
        sys.exit(1)

    # Count recipes with yield data before transform
    recipes_with_yield = sum(
        1 for r in data.get('recipes', [])
        if r.get('yield_quantity') is not None and r.get('yield_unit')
    )

    # Transform
    result = transform_data(data)

    # Report
    recipe_count = len(data.get('recipes', []))
    existing_fu_count = len(data.get('finished_units', []))
    new_fu_count = len(result.get('finished_units', [])) - existing_fu_count

    print(f"Recipes: {recipe_count} total, {recipes_with_yield} with yield data")
    print(f"FinishedUnits: {existing_fu_count} existing + {new_fu_count} created = {len(result.get('finished_units', []))} total")

    if args.verbose:
        print("\nCreated FinishedUnits:")
        for fu in result.get('finished_units', [])[-new_fu_count:]:
            print(f"  - {fu['slug']}: {fu['display_name']} ({fu['items_per_batch']} {fu['item_unit']}/batch)")

    if args.dry_run:
        print("\nDry run - no file written")
        return

    # Write output
    with open(args.output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nWritten to {args.output_file}")


if __name__ == '__main__':
    main()
