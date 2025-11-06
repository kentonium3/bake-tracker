"""
Import/Export CLI Utility

Simple command-line interface for exporting and importing data.
No UI required - designed for programmatic and testing use.

Usage Examples:
    # Export all data
    python -m src.utils.import_export_cli export test_data.json

    # Export ingredients only
    python -m src.utils.import_export_cli export-ingredients ingredients.json

    # Export recipes only
    python -m src.utils.import_export_cli export-recipes recipes.json

    # Import all data
    python -m src.utils.import_export_cli import test_data.json

    # Import ingredients only
    python -m src.utils.import_export_cli import-ingredients ingredients.json

    # Import recipes only
    python -m src.utils.import_export_cli import-recipes recipes.json
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.database import initialize_app_database
from src.services.import_export_service import (
    export_ingredients_to_json,
    export_recipes_to_json,
    export_finished_goods_to_json,
    export_bundles_to_json,
    export_packages_to_json,
    export_recipients_to_json,
    export_events_to_json,
    export_all_to_json,
    import_ingredients_from_json,
    import_recipes_from_json,
    import_finished_goods_from_json,
    import_bundles_from_json,
    import_packages_from_json,
    import_recipients_from_json,
    import_events_from_json,
    import_all_from_json,
)


def export_all(output_file: str):
    """Export all ingredients and recipes."""
    print(f"Exporting all data to {output_file}...")
    result = export_all_to_json(output_file)

    if result.success:
        print(result.get_summary())
        return 0
    else:
        print(f"ERROR: {result.error}")
        return 1


def export_ingredients(output_file: str):
    """Export ingredients only."""
    print(f"Exporting ingredients to {output_file}...")
    result = export_ingredients_to_json(output_file)

    if result.success:
        print(result.get_summary())
        return 0
    else:
        print(f"ERROR: {result.error}")
        return 1


def export_recipes(output_file: str):
    """Export recipes only."""
    print(f"Exporting recipes to {output_file}...")
    result = export_recipes_to_json(output_file)

    if result.success:
        print(result.get_summary())
        return 0
    else:
        print(f"ERROR: {result.error}")
        return 1


def export_finished_goods(output_file: str):
    """Export finished goods only."""
    print(f"Exporting finished goods to {output_file}...")
    result = export_finished_goods_to_json(output_file)

    if result.success:
        print(result.get_summary())
        return 0
    else:
        print(f"ERROR: {result.error}")
        return 1


def export_bundles(output_file: str):
    """Export bundles only."""
    print(f"Exporting bundles to {output_file}...")
    result = export_bundles_to_json(output_file)

    if result.success:
        print(result.get_summary())
        return 0
    else:
        print(f"ERROR: {result.error}")
        return 1


def export_packages(output_file: str):
    """Export packages only."""
    print(f"Exporting packages to {output_file}...")
    result = export_packages_to_json(output_file)

    if result.success:
        print(result.get_summary())
        return 0
    else:
        print(f"ERROR: {result.error}")
        return 1


def export_recipients(output_file: str):
    """Export recipients only."""
    print(f"Exporting recipients to {output_file}...")
    result = export_recipients_to_json(output_file)

    if result.success:
        print(result.get_summary())
        return 0
    else:
        print(f"ERROR: {result.error}")
        return 1


def export_events(output_file: str):
    """Export events only."""
    print(f"Exporting events to {output_file}...")
    result = export_events_to_json(output_file)

    if result.success:
        print(result.get_summary())
        return 0
    else:
        print(f"ERROR: {result.error}")
        return 1


def import_all(input_file: str):
    """Import all data (ingredients, recipes, finished goods, bundles, packages, recipients, events)."""
    print(f"Importing all data from {input_file}...")

    (ingredient_result, recipe_result, finished_good_result, bundle_result,
     package_result, recipient_result, event_result) = import_all_from_json(input_file)

    print("\n" + "=" * 60)
    print("INGREDIENT IMPORT RESULTS")
    print("=" * 60)
    print(ingredient_result.get_summary())

    print("\n" + "=" * 60)
    print("RECIPE IMPORT RESULTS")
    print("=" * 60)
    print(recipe_result.get_summary())

    print("\n" + "=" * 60)
    print("FINISHED GOOD IMPORT RESULTS")
    print("=" * 60)
    print(finished_good_result.get_summary())

    print("\n" + "=" * 60)
    print("BUNDLE IMPORT RESULTS")
    print("=" * 60)
    print(bundle_result.get_summary())

    print("\n" + "=" * 60)
    print("PACKAGE IMPORT RESULTS")
    print("=" * 60)
    print(package_result.get_summary())

    print("\n" + "=" * 60)
    print("RECIPIENT IMPORT RESULTS")
    print("=" * 60)
    print(recipient_result.get_summary())

    print("\n" + "=" * 60)
    print("EVENT IMPORT RESULTS")
    print("=" * 60)
    print(event_result.get_summary())

    if (ingredient_result.failed > 0 or recipe_result.failed > 0 or
        finished_good_result.failed > 0 or bundle_result.failed > 0 or
        package_result.failed > 0 or recipient_result.failed > 0 or
        event_result.failed > 0):
        return 1
    return 0


def import_ingredients(input_file: str):
    """Import ingredients only."""
    print(f"Importing ingredients from {input_file}...")
    result = import_ingredients_from_json(input_file)
    print(result.get_summary())

    if result.failed > 0:
        return 1
    return 0


def import_recipes(input_file: str):
    """Import recipes only."""
    print(f"Importing recipes from {input_file}...")
    result = import_recipes_from_json(input_file)
    print(result.get_summary())

    if result.failed > 0:
        return 1
    return 0


def import_finished_goods(input_file: str):
    """Import finished goods only."""
    print(f"Importing finished goods from {input_file}...")
    result = import_finished_goods_from_json(input_file)
    print(result.get_summary())

    if result.failed > 0:
        return 1
    return 0


def import_bundles(input_file: str):
    """Import bundles only."""
    print(f"Importing bundles from {input_file}...")
    result = import_bundles_from_json(input_file)
    print(result.get_summary())

    if result.failed > 0:
        return 1
    return 0


def import_packages(input_file: str):
    """Import packages only."""
    print(f"Importing packages from {input_file}...")
    result = import_packages_from_json(input_file)
    print(result.get_summary())

    if result.failed > 0:
        return 1
    return 0


def import_recipients(input_file: str):
    """Import recipients only."""
    print(f"Importing recipients from {input_file}...")
    result = import_recipients_from_json(input_file)
    print(result.get_summary())

    if result.failed > 0:
        return 1
    return 0


def import_events(input_file: str):
    """Import events only."""
    print(f"Importing events from {input_file}...")
    result = import_events_from_json(input_file)
    print(result.get_summary())

    if result.failed > 0:
        return 1
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Import/Export utility for Seasonal Baking Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Export all data:
    python -m src.utils.import_export_cli export test_data.json

  Import all data:
    python -m src.utils.import_export_cli import test_data.json

  Export/Import specific types:
    python -m src.utils.import_export_cli export-ingredients ingredients.json
    python -m src.utils.import_export_cli import-recipes recipes.json
"""
    )

    parser.add_argument(
        'command',
        choices=[
            'export', 'export-ingredients', 'export-recipes', 'export-finished-goods', 'export-bundles',
            'export-packages', 'export-recipients', 'export-events',
            'import', 'import-ingredients', 'import-recipes', 'import-finished-goods', 'import-bundles',
            'import-packages', 'import-recipients', 'import-events'
        ],
        help='Command to execute'
    )

    parser.add_argument(
        'file',
        help='JSON file path'
    )

    args = parser.parse_args()

    # Initialize database (required for all operations)
    print("Initializing database...")
    initialize_app_database()

    # Execute command
    if args.command == 'export':
        return export_all(args.file)
    elif args.command == 'export-ingredients':
        return export_ingredients(args.file)
    elif args.command == 'export-recipes':
        return export_recipes(args.file)
    elif args.command == 'export-finished-goods':
        return export_finished_goods(args.file)
    elif args.command == 'export-bundles':
        return export_bundles(args.file)
    elif args.command == 'export-packages':
        return export_packages(args.file)
    elif args.command == 'export-recipients':
        return export_recipients(args.file)
    elif args.command == 'export-events':
        return export_events(args.file)
    elif args.command == 'import':
        return import_all(args.file)
    elif args.command == 'import-ingredients':
        return import_ingredients(args.file)
    elif args.command == 'import-recipes':
        return import_recipes(args.file)
    elif args.command == 'import-finished-goods':
        return import_finished_goods(args.file)
    elif args.command == 'import-bundles':
        return import_bundles(args.file)
    elif args.command == 'import-packages':
        return import_packages(args.file)
    elif args.command == 'import-recipients':
        return import_recipients(args.file)
    elif args.command == 'import-events':
        return import_events(args.file)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
