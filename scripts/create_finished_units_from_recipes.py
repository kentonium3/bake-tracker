#!/usr/bin/env python3
"""
Create FinishedUnit records from existing Recipe yield data.

This script operates directly on the database, reading recipes with yield data
and creating corresponding FinishedUnit records.

Feature: 056-unified-yield-management (post-implementation data fix)

Usage:
    python scripts/create_finished_units_from_recipes.py
    python scripts/create_finished_units_from_recipes.py --dry-run
"""
import argparse
import re
import sys
from pathlib import Path

# Add project root and src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from sqlalchemy.orm import Session
from src.services.database import session_scope
from src.models.recipe import Recipe
from src.models.finished_unit import FinishedUnit, YieldMode


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


def get_unique_slug(base_slug: str, existing_slugs: set, session: Session) -> str:
    """
    Generate unique slug, checking both existing set and database.

    Args:
        base_slug: Base slug to make unique
        existing_slugs: Set of already-used slugs in this run
        session: Database session for additional checking

    Returns:
        Unique slug
    """
    slug = base_slug
    counter = 2

    while True:
        # Check our running set
        if slug in existing_slugs:
            slug = f"{base_slug}_{counter}"
            counter += 1
            continue

        # Check database
        exists = session.query(FinishedUnit).filter(FinishedUnit.slug == slug).first()
        if exists:
            slug = f"{base_slug}_{counter}"
            counter += 1
            continue

        break

    return slug


def create_finished_units(dry_run: bool = False, verbose: bool = False) -> dict:
    """
    Create FinishedUnit records from Recipe yield data.

    Args:
        dry_run: If True, don't commit changes
        verbose: If True, print detailed info

    Returns:
        Summary dict with counts
    """
    results = {
        "recipes_total": 0,
        "recipes_with_yield": 0,
        "recipes_already_have_fu": 0,
        "finished_units_created": 0,
        "errors": [],
        "created": []
    }

    with session_scope() as session:
        # Get all recipes
        recipes = session.query(Recipe).all()
        results["recipes_total"] = len(recipes)

        existing_slugs = set()

        for recipe in recipes:
            # Skip if recipe already has FinishedUnits
            if recipe.finished_units:
                results["recipes_already_have_fu"] += 1
                if verbose:
                    print(f"  SKIP: {recipe.name} (already has {len(recipe.finished_units)} FinishedUnit(s))")
                continue

            # Check for yield data
            if recipe.yield_quantity is None or not recipe.yield_unit:
                if verbose:
                    print(f"  SKIP: {recipe.name} (no yield data)")
                continue

            results["recipes_with_yield"] += 1

            try:
                # Generate slug
                recipe_slug = slugify(recipe.name)
                yield_suffix = slugify(recipe.yield_description) if recipe.yield_description else 'standard'
                base_slug = f"{recipe_slug}_{yield_suffix}"
                slug = get_unique_slug(base_slug, existing_slugs, session)
                existing_slugs.add(slug)

                # Generate display_name
                if recipe.yield_description:
                    display_name = recipe.yield_description
                else:
                    display_name = f"Standard {recipe.name}"

                # Create FinishedUnit
                finished_unit = FinishedUnit(
                    slug=slug,
                    display_name=display_name,
                    recipe_id=recipe.id,
                    yield_mode=YieldMode.DISCRETE_COUNT,
                    items_per_batch=int(recipe.yield_quantity),
                    item_unit=recipe.yield_unit,
                    inventory_count=0,
                    category=recipe.category
                )

                if not dry_run:
                    session.add(finished_unit)

                results["finished_units_created"] += 1
                results["created"].append({
                    "slug": slug,
                    "display_name": display_name,
                    "items_per_batch": int(recipe.yield_quantity),
                    "item_unit": recipe.yield_unit,
                    "recipe": recipe.name
                })

                if verbose:
                    print(f"  CREATE: {slug}: {display_name} ({int(recipe.yield_quantity)} {recipe.yield_unit}/batch)")

            except Exception as e:
                error_msg = f"Error processing {recipe.name}: {e}"
                results["errors"].append(error_msg)
                if verbose:
                    print(f"  ERROR: {error_msg}")

        if not dry_run:
            session.commit()
            print(f"\nCommitted {results['finished_units_created']} FinishedUnit records")
        else:
            print(f"\nDry run - {results['finished_units_created']} would be created")

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Create FinishedUnit records from existing Recipe yield data'
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without writing to database')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Print detailed processing info')

    args = parser.parse_args()

    print("Creating FinishedUnits from Recipe yield data...")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}\n")

    results = create_finished_units(dry_run=args.dry_run, verbose=args.verbose)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Recipes total:              {results['recipes_total']}")
    print(f"Recipes with yield data:    {results['recipes_with_yield']}")
    print(f"Recipes already have FU:    {results['recipes_already_have_fu']}")
    print(f"FinishedUnits created:      {results['finished_units_created']}")
    if results['errors']:
        print(f"Errors:                     {len(results['errors'])}")
        for err in results['errors']:
            print(f"  - {err}")

    if not args.verbose and results['finished_units_created'] > 0:
        print("\nCreated FinishedUnits:")
        for fu in results['created']:
            print(f"  - {fu['slug']}: {fu['display_name']} ({fu['items_per_batch']} {fu['item_unit']}/batch)")


if __name__ == '__main__':
    main()
