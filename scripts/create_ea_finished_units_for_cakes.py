#!/usr/bin/env python3
"""
One-time script to create EA (whole unit) FinishedUnits for cake recipes.

Cake recipes that only have SERVING-type FinishedUnits need an EA variant
to represent the whole cake as a deliverable unit. This enables creating
bare FinishedGoods for event planning.

Usage:
    # Dry run (preview only)
    python scripts/create_ea_finished_units_for_cakes.py --dry-run

    # Execute
    python scripts/create_ea_finished_units_for_cakes.py

    # Specify items per batch (default: 1)
    python scripts/create_ea_finished_units_for_cakes.py --items-per-batch 1
"""

import argparse
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.database import session_scope
from src.services.finished_unit_service import FinishedUnitService
from src.models import Recipe, FinishedUnit
from src.models.finished_unit import YieldMode


def get_cake_recipes_without_ea(session) -> list:
    """
    Find cake recipes that don't have an EA-type FinishedUnit.

    Returns list of (recipe, existing_serving_fu) tuples.
    """
    # Get all recipes with 'cake' in category (case-insensitive)
    cake_recipes = (
        session.query(Recipe)
        .filter(Recipe.category.ilike('%cake%'))
        .order_by(Recipe.name)
        .all()
    )

    results = []
    for recipe in cake_recipes:
        # Check if this recipe already has an EA FinishedUnit
        ea_unit = (
            session.query(FinishedUnit)
            .filter(
                FinishedUnit.recipe_id == recipe.id,
                FinishedUnit.yield_type == 'EA'
            )
            .first()
        )

        if ea_unit is None:
            # Get the existing SERVING unit for reference
            serving_unit = (
                session.query(FinishedUnit)
                .filter(
                    FinishedUnit.recipe_id == recipe.id,
                    FinishedUnit.yield_type == 'SERVING'
                )
                .first()
            )
            results.append((recipe, serving_unit))

    return results


def create_ea_finished_units(
    dry_run: bool = True,
    items_per_batch: int = 1,
) -> dict:
    """
    Create EA-type FinishedUnits for cake recipes that don't have them.

    Args:
        dry_run: If True, only preview what would be created
        items_per_batch: How many whole cakes one recipe batch produces

    Returns:
        dict with counts: created, skipped, errors
    """
    results = {"created": [], "skipped": [], "errors": []}

    with session_scope() as session:
        recipes_needing_ea = get_cake_recipes_without_ea(session)

        if not recipes_needing_ea:
            print("All cake recipes already have EA-type FinishedUnits!")
            return results

        print(f"\nFound {len(recipes_needing_ea)} cake recipes needing EA FinishedUnits")
        print("-" * 60)

        for recipe, serving_fu in recipes_needing_ea:
            display_name = recipe.name

            if dry_run:
                print(f"  WOULD CREATE: {display_name}")
                print(f"    - Recipe: {recipe.name} (#{recipe.id})")
                print(f"    - Category: {recipe.category}")
                print(f"    - yield_type: EA")
                print(f"    - yield_mode: DISCRETE_COUNT")
                print(f"    - items_per_batch: {items_per_batch}")
                print(f"    - item_unit: cake")
                if serving_fu:
                    print(f"    - Existing SERVING unit: FU #{serving_fu.id}")
                results["created"].append({
                    "name": display_name,
                    "recipe_id": recipe.id,
                })
            else:
                try:
                    # Create the EA FinishedUnit
                    fu = FinishedUnitService.create_finished_unit(
                        display_name=display_name,
                        recipe_id=recipe.id,
                        yield_type="EA",
                        yield_mode=YieldMode.DISCRETE_COUNT,
                        items_per_batch=items_per_batch,
                        item_unit="cake",
                        category=recipe.category,
                        notes=f"Whole cake unit (EA) - auto-generated",
                    )
                    results["created"].append({
                        "name": display_name,
                        "finished_unit_id": fu.id,
                        "recipe_id": recipe.id,
                    })
                    print(f"  CREATED: {display_name} (FinishedUnit #{fu.id})")

                except Exception as e:
                    results["errors"].append({
                        "name": display_name,
                        "recipe_id": recipe.id,
                        "error": str(e),
                    })
                    print(f"  ERROR: {display_name} - {e}")

    return results


def print_summary(results: dict, dry_run: bool):
    """Print summary of results."""
    print("\n" + "=" * 60)
    if dry_run:
        print("DRY RUN SUMMARY (no changes made)")
    else:
        print("EXECUTION SUMMARY")
    print("=" * 60)
    print(f"  {'Would create' if dry_run else 'Created'}: {len(results['created'])}")
    print(f"  Skipped: {len(results['skipped'])}")
    print(f"  Errors: {len(results['errors'])}")

    if results["errors"]:
        print("\nErrors:")
        for err in results["errors"]:
            print(f"  - {err['name']}: {err['error']}")


def main():
    parser = argparse.ArgumentParser(
        description="Create EA FinishedUnits for cake recipes"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without creating records",
    )
    parser.add_argument(
        "--items-per-batch",
        type=int,
        default=1,
        help="How many whole cakes one recipe batch produces (default: 1)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Create EA FinishedUnits for Cake Recipes")
    print("=" * 60)
    if args.dry_run:
        print("MODE: Dry run (no changes will be made)")
    else:
        print("MODE: Live execution")
    print(f"CONFIG: items_per_batch = {args.items_per_batch}")

    results = create_ea_finished_units(
        dry_run=args.dry_run,
        items_per_batch=args.items_per_batch,
    )

    print_summary(results, args.dry_run)

    if args.dry_run and results["created"]:
        print("\nTo execute, run without --dry-run flag")


if __name__ == "__main__":
    main()
