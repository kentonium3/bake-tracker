#!/usr/bin/env python3
"""
Upgrade sample_data.json to F031 hierarchy format.

Merges the hierarchy structure from ingredients_hierarchy_import.json
with the existing sample_data.json, preserving:
- All non-ingredient entities (products, recipes, suppliers, etc.)
- Ingredient-specific fields (density, description, notes, etc.)
"""

import json
from datetime import datetime, timezone
from pathlib import Path


def load_json(path: str) -> dict:
    """Load JSON file."""
    with open(path) as f:
        return json.load(f)


def upgrade_sample_data(
    sample_data_path: str,
    hierarchy_path: str,
    output_path: str
) -> dict:
    """
    Upgrade sample_data.json with F031 hierarchy structure.

    Args:
        sample_data_path: Path to original sample_data.json
        hierarchy_path: Path to ingredients_hierarchy_import.json
        output_path: Path for upgraded output file

    Returns:
        Stats dict with counts
    """
    # Load files
    sample_data = load_json(sample_data_path)
    hierarchy_data = load_json(hierarchy_path)

    # Build lookup of original ingredients by slug (for preserving fields)
    original_by_slug = {}
    for ing in sample_data.get('ingredients', []):
        original_by_slug[ing['slug']] = ing

    # Build new ingredients list from hierarchy
    new_ingredients = []
    preserved_count = 0
    new_count = 0

    for hier_ing in hierarchy_data['ingredients']:
        slug = hier_ing['slug']

        # Start with hierarchy fields
        new_ing = {
            'display_name': hier_ing['display_name'],
            'slug': slug,
            'hierarchy_level': hier_ing['hierarchy_level'],
            'is_packaging': hier_ing.get('is_packaging', False),
        }

        # Add parent_slug if present
        if hier_ing.get('parent_slug'):
            new_ing['parent_slug'] = hier_ing['parent_slug']

        # Preserve fields from original if this is a leaf ingredient
        if slug in original_by_slug:
            orig = original_by_slug[slug]
            preserved_count += 1

            # Preserve these fields from original
            preserve_fields = [
                'description', 'notes',
                'density_volume_value', 'density_volume_unit',
                'density_weight_value', 'density_weight_unit',
            ]
            for field in preserve_fields:
                if field in orig and orig[field] is not None:
                    new_ing[field] = orig[field]
        else:
            new_count += 1
            # Use description from hierarchy for categories/subcategories
            if hier_ing.get('description'):
                new_ing['description'] = hier_ing['description']

        new_ingredients.append(new_ing)

    # Build upgraded sample_data
    upgraded = {
        'version': '3.6',
        'exported_at': datetime.now(timezone.utc).isoformat(),
        'application': 'bake-tracker',
    }

    # Add ingredients first
    upgraded['ingredients'] = new_ingredients

    # Preserve all other entities in original order
    preserve_entities = [
        'suppliers', 'products', 'purchases', 'inventory_items',
        'recipes', 'finished_units', 'finished_goods', 'compositions',
        'packages', 'package_finished_goods', 'recipients', 'events',
        'event_recipient_packages', 'event_production_targets',
        'event_assembly_targets', 'production_records',
        'production_runs', 'assembly_runs',
    ]

    for entity in preserve_entities:
        if entity in sample_data:
            upgraded[entity] = sample_data[entity]

    # Write output
    with open(output_path, 'w') as f:
        json.dump(upgraded, f, indent=2)

    return {
        'total_ingredients': len(new_ingredients),
        'preserved_from_original': preserved_count,
        'new_hierarchy_items': new_count,
        'other_entities_preserved': len([e for e in preserve_entities if e in sample_data]),
    }


def main():
    sample_data_path = 'test_data/sample_data.json'
    hierarchy_path = 'test_data/ingredients_hierarchy_import.json'
    output_path = 'test_data/sample_data.json'  # Overwrite original

    # Create backup
    backup_path = 'test_data/sample_data_v35_backup.json'
    print(f"Creating backup: {backup_path}")
    sample_data = load_json(sample_data_path)
    with open(backup_path, 'w') as f:
        json.dump(sample_data, f, indent=2)

    print(f"\nUpgrading {sample_data_path}...")
    stats = upgrade_sample_data(sample_data_path, hierarchy_path, output_path)

    print("\n" + "=" * 60)
    print("UPGRADE COMPLETE")
    print("=" * 60)
    print(f"Total ingredients: {stats['total_ingredients']}")
    print(f"  - Preserved from original (with density etc.): {stats['preserved_from_original']}")
    print(f"  - New hierarchy items (categories/subcats): {stats['new_hierarchy_items']}")
    print(f"Other entities preserved: {stats['other_entities_preserved']}")
    print(f"\nBackup saved to: {backup_path}")
    print(f"Upgraded file: {output_path}")
    print("=" * 60)


if __name__ == '__main__':
    main()
