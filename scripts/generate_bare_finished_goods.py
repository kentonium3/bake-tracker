#!/usr/bin/env python3
"""
One-time script to generate "bare" FinishedGoods from existing FinishedUnits.

A "bare" FinishedGood is a simple wrapper around a single FinishedUnit with no
additional materials or bundling. This enables FinishedUnits (especially cakes)
to be selected for Events, which require FinishedGoods.

Usage:
    # Dry run (preview only)
    python scripts/generate_bare_finished_goods.py --dry-run

    # Generate for all FinishedUnits
    python scripts/generate_bare_finished_goods.py

    # Generate only for specific category (e.g., Cakes)
    python scripts/generate_bare_finished_goods.py --category Cakes

    # Generate only for specific yield_type (EA = whole items like cakes)
    python scripts/generate_bare_finished_goods.py --yield-type EA
"""

import argparse
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.database import session_scope
from src.services.finished_good_service import (
    create_finished_good,
    get_all_finished_goods,
)
from src.services.finished_unit_service import get_all_finished_units
from src.models import AssemblyType


def get_existing_finished_good_names(session) -> set:
    """Get set of existing FinishedGood display names (case-insensitive)."""
    finished_goods = get_all_finished_goods()
    return {fg.display_name.lower() for fg in finished_goods}


def generate_bare_finished_goods(
    dry_run: bool = True,
    category: str = None,
    yield_type: str = None,
) -> dict:
    """
    Generate bare FinishedGoods from FinishedUnits.

    Args:
        dry_run: If True, only preview what would be created
        category: Optional category filter (e.g., "Cakes")
        yield_type: Optional yield_type filter ("EA" or "SERVING")

    Returns:
        dict with counts: created, skipped, errors
    """
    results = {"created": [], "skipped": [], "errors": []}

    # Get all FinishedUnits with optional filtering
    finished_units = get_all_finished_units(category=category)

    # Apply yield_type filter if specified
    if yield_type:
        finished_units = [fu for fu in finished_units if fu.yield_type == yield_type]

    if not finished_units:
        print(f"No FinishedUnits found matching filters (category={category}, yield_type={yield_type})")
        return results

    print(f"\nFound {len(finished_units)} FinishedUnits to process")
    print("-" * 60)

    # Get existing FinishedGood names to avoid duplicates
    existing_names = get_existing_finished_good_names(None)

    for fu in finished_units:
        display_name = fu.display_name
        recipe_name = fu.recipe.name if fu.recipe else "Unknown"

        # Check if FinishedGood already exists with this name
        if display_name.lower() in existing_names:
            results["skipped"].append({
                "name": display_name,
                "reason": "FinishedGood already exists",
            })
            print(f"  SKIP: {display_name} (already exists)")
            continue

        if dry_run:
            print(f"  WOULD CREATE: {display_name}")
            print(f"    - Recipe: {recipe_name}")
            print(f"    - Category: {fu.category}")
            print(f"    - Yield Type: {fu.yield_type}")
            print(f"    - Component: FinishedUnit #{fu.id} (qty=1)")
            results["created"].append({"name": display_name, "finished_unit_id": fu.id})
        else:
            try:
                # Create the bare FinishedGood with single component
                fg = create_finished_good(
                    display_name=display_name,
                    assembly_type=AssemblyType.BARE,
                    components=[
                        {
                            "type": "finished_unit",
                            "id": fu.id,
                            "quantity": 1,
                            "notes": None,
                            "sort_order": 0,
                        }
                    ],
                    description=f"Bare {recipe_name} - no additional packaging",
                    notes=f"Auto-generated from FinishedUnit #{fu.id}",
                )
                results["created"].append({
                    "name": display_name,
                    "finished_good_id": fg.id,
                    "finished_unit_id": fu.id,
                })
                print(f"  CREATED: {display_name} (FinishedGood #{fg.id})")

                # Add to existing names to prevent duplicates within this run
                existing_names.add(display_name.lower())

            except Exception as e:
                results["errors"].append({
                    "name": display_name,
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
    print(f"  Would create: {len(results['created'])}" if dry_run else f"  Created: {len(results['created'])}")
    print(f"  Skipped: {len(results['skipped'])}")
    print(f"  Errors: {len(results['errors'])}")

    if results["errors"]:
        print("\nErrors:")
        for err in results["errors"]:
            print(f"  - {err['name']}: {err['error']}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate bare FinishedGoods from FinishedUnits"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without creating records",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Filter by category (e.g., 'Cakes')",
    )
    parser.add_argument(
        "--yield-type",
        type=str,
        choices=["EA", "SERVING"],
        default=None,
        help="Filter by yield type (EA=whole units like cakes, SERVING=individual items)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Generate Bare FinishedGoods from FinishedUnits")
    print("=" * 60)
    if args.dry_run:
        print("MODE: Dry run (no changes will be made)")
    else:
        print("MODE: Live execution")
    if args.category:
        print(f"FILTER: Category = {args.category}")
    if args.yield_type:
        print(f"FILTER: Yield Type = {args.yield_type}")

    results = generate_bare_finished_goods(
        dry_run=args.dry_run,
        category=args.category,
        yield_type=args.yield_type,
    )

    print_summary(results, args.dry_run)

    if args.dry_run and results["created"]:
        print("\nTo execute, run without --dry-run flag")


if __name__ == "__main__":
    main()
