"""
Import/Export CLI Utility

Simple command-line interface for exporting and importing data.
No UI required - designed for programmatic and testing use.

Usage Examples:
    # Export all data (v3.2 format)
    python -m src.utils.import_export_cli export test_data.json

    # Export ingredients only
    python -m src.utils.import_export_cli export-ingredients ingredients.json

    # Import all data (requires v3.2 format)
    python -m src.utils.import_export_cli import test_data.json

    # Import with replace mode (clears existing data first)
    python -m src.utils.import_export_cli import test_data.json --mode replace
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
    import_all_from_json_v3,
)


def export_all(output_file: str):
    """Export all data in v3.2 format."""
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


def import_all(input_file: str, mode: str = "merge"):
    """Import all data from v3.2 format file."""
    print(f"Importing all data from {input_file} (mode: {mode})...")

    try:
        result = import_all_from_json_v3(input_file, mode=mode)
        print(result.get_summary())

        if result.failed > 0:
            return 1
        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Import/Export utility for Seasonal Baking Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Export all data (v3.2 format):
    python -m src.utils.import_export_cli export test_data.json

  Import all data (requires v3.2 format):
    python -m src.utils.import_export_cli import test_data.json

  Import with replace mode (clears existing data):
    python -m src.utils.import_export_cli import test_data.json --mode replace

  Export specific entity types:
    python -m src.utils.import_export_cli export-ingredients ingredients.json
    python -m src.utils.import_export_cli export-recipes recipes.json

Note: Individual entity imports (import-ingredients, etc.) are no longer
supported. Use the 'import' command with a complete v3.2 format file.
""",
    )

    parser.add_argument(
        "command",
        choices=[
            "export",
            "export-ingredients",
            "export-recipes",
            "export-finished-goods",
            "export-bundles",
            "export-packages",
            "export-recipients",
            "export-events",
            "import",
        ],
        help="Command to execute",
    )

    parser.add_argument("file", help="JSON file path")

    parser.add_argument(
        "--mode",
        choices=["merge", "replace"],
        default="merge",
        help="Import mode: 'merge' (default) adds new records, 'replace' clears existing data first",
    )

    args = parser.parse_args()

    # Initialize database (required for all operations)
    print("Initializing database...")
    initialize_app_database()

    # Execute command
    if args.command == "export":
        return export_all(args.file)
    elif args.command == "export-ingredients":
        return export_ingredients(args.file)
    elif args.command == "export-recipes":
        return export_recipes(args.file)
    elif args.command == "export-finished-goods":
        return export_finished_goods(args.file)
    elif args.command == "export-bundles":
        return export_bundles(args.file)
    elif args.command == "export-packages":
        return export_packages(args.file)
    elif args.command == "export-recipients":
        return export_recipients(args.file)
    elif args.command == "export-events":
        return export_events(args.file)
    elif args.command == "import":
        return import_all(args.file, mode=args.mode)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
