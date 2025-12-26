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

    # Export complete database with manifest (F030)
    python -m src.utils.import_export_cli export-complete -o ./export_dir

    # Export complete database as ZIP (F030)
    python -m src.utils.import_export_cli export-complete -o ./export_dir --zip

    # Export denormalized view (F030)
    python -m src.utils.import_export_cli export-view -t products -o view_products.json

    # Validate export checksums (F030)
    python -m src.utils.import_export_cli validate-export ./export_dir

    # Import denormalized view (F030)
    python -m src.utils.import_export_cli import-view view_products.json

    # Import view with interactive FK resolution (F030)
    python -m src.utils.import_export_cli import-view view_products.json --interactive

    # Import view in dry-run mode (F030)
    python -m src.utils.import_export_cli import-view view_products.json --dry-run

    # Import view, skipping records with errors (F030)
    python -m src.utils.import_export_cli import-view view_products.json --skip-on-error
"""

import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

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


# ============================================================================
# F030 Export Commands
# ============================================================================


def export_complete_cmd(output_dir: str = None, create_zip: bool = False):
    """
    Export complete database with manifest (F030).

    Creates a directory containing:
    - manifest.json with checksums and import order
    - Individual entity JSON files (suppliers, ingredients, products, etc.)
    - Optional ZIP archive

    Args:
        output_dir: Output directory (default: export_{timestamp})
        create_zip: Whether to create a ZIP archive

    Returns:
        0 on success, 1 on failure
    """
    from src.services.coordinated_export_service import export_complete

    # Generate default output directory if not provided
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"export_{timestamp}"

    print(f"Exporting complete database to {output_dir}...")

    try:
        manifest = export_complete(output_dir, create_zip=create_zip)

        # Print summary
        total_records = sum(f.record_count for f in manifest.files)
        print(f"\nExport Complete")
        print(f"---------------")
        print(f"Output directory: {output_dir}")
        print(f"Export date: {manifest.export_date}")
        print(f"Files exported: {len(manifest.files)}")
        print(f"Total records: {total_records}")
        print()
        for f in manifest.files:
            print(f"  {f.filename}: {f.record_count} records")

        if create_zip:
            zip_path = Path(output_dir).with_suffix(".zip")
            print(f"\nZIP archive: {zip_path}")

        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def export_view_cmd(view_type: str, output_path: str = None):
    """
    Export denormalized view (F030).

    Creates a view file with context fields for AI augmentation.

    Args:
        view_type: Type of view (products, inventory, purchases)
        output_path: Output file path (default: view_{type}.json)

    Returns:
        0 on success, 1 on failure
    """
    from src.services.denormalized_export_service import (
        export_products_view,
        export_inventory_view,
        export_purchases_view,
    )

    # Map view types to export functions
    exporters = {
        "products": export_products_view,
        "inventory": export_inventory_view,
        "purchases": export_purchases_view,
    }

    if view_type not in exporters:
        print(f"ERROR: Unknown view type '{view_type}'. Valid types: {', '.join(exporters.keys())}")
        return 1

    # Generate default output path if not provided
    if output_path is None:
        output_path = f"view_{view_type}.json"

    print(f"Exporting {view_type} view to {output_path}...")

    try:
        result = exporters[view_type](output_path)

        # Print summary
        print(f"\nExport Complete")
        print(f"---------------")
        print(f"View type: {result.view_type}")
        print(f"Output file: {result.output_path}")
        print(f"Records exported: {result.record_count}")
        print(f"Export date: {result.export_date}")

        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def validate_export_cmd(export_dir: str):
    """
    Validate export checksums (F030).

    Verifies that all files in the export directory match their
    manifest checksums.

    Args:
        export_dir: Path to export directory with manifest.json

    Returns:
        0 if valid, 1 if invalid
    """
    from src.services.coordinated_export_service import validate_export

    print(f"Validating export in {export_dir}...")

    try:
        result = validate_export(export_dir)

        if result["valid"]:
            print(f"\nValidation Passed")
            print(f"-----------------")
            print(f"Files checked: {result['files_checked']}")
            print("All checksums valid.")
            return 0
        else:
            print(f"\nValidation Failed")
            print(f"-----------------")
            print(f"Files checked: {result['files_checked']}")
            print("Errors found:")
            for error in result["errors"]:
                print(f"  - {error}")
            return 1

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


# ============================================================================
# F030 Import Commands
# ============================================================================


class CLIFKResolver:
    """
    CLI implementation of FK resolution callback.

    Prompts the user via text input for each missing FK reference.
    Supports CREATE (new entity), MAP (existing entity), and SKIP options.
    """

    def resolve(self, missing) -> "Resolution":
        """
        Prompt user to resolve a missing FK reference.

        Args:
            missing: MissingFK instance with details about the missing reference

        Returns:
            Resolution with user's choice
        """
        from src.services.fk_resolver_service import (
            Resolution,
            ResolutionChoice,
            find_similar_entities,
        )

        print(f"\nMissing {missing.entity_type}: '{missing.missing_value}'")
        print(f"  Field: {missing.field_name}")
        print(f"  Affects {missing.affected_record_count} records")

        # Show sample records for context
        if missing.sample_records:
            print("  Sample affected records:")
            for i, sample in enumerate(missing.sample_records[:2]):
                # Show a brief summary of the sample record
                if missing.entity_type == "ingredient":
                    display = sample.get("product_name") or sample.get("brand", "")
                elif missing.entity_type == "supplier":
                    display = sample.get("product_name") or sample.get("brand", "")
                else:
                    display = str(sample)[:50]
                print(f"    {i+1}. {display}")

        # Show options
        print("\nOptions:")
        print("  [C] Create new entity")
        print("  [M] Map to existing entity")
        print("  [S] Skip these records")

        while True:
            choice = input("\nEnter choice (C/M/S): ").strip().upper()

            if choice == "C":
                return self._handle_create(missing)
            elif choice == "M":
                return self._handle_map(missing)
            elif choice == "S":
                return Resolution(
                    choice=ResolutionChoice.SKIP,
                    entity_type=missing.entity_type,
                    missing_value=missing.missing_value,
                )
            else:
                print("Invalid choice. Enter C, M, or S.")

    def _handle_create(self, missing) -> "Resolution":
        """Handle CREATE choice - prompt for required fields."""
        from src.services.fk_resolver_service import Resolution, ResolutionChoice

        print(f"\nCreate new {missing.entity_type}:")
        entity_data = {}

        if missing.entity_type == "supplier":
            # Pre-fill name from missing value
            entity_data["name"] = input(
                f"  Name [{missing.missing_value}]: "
            ).strip() or missing.missing_value
            entity_data["city"] = input("  City (required): ").strip()
            entity_data["state"] = input("  State (2-letter, required): ").strip()
            entity_data["zip_code"] = input("  ZIP Code (required): ").strip()
            # Optional fields
            street = input("  Street address (optional): ").strip()
            if street:
                entity_data["street_address"] = street

        elif missing.entity_type == "ingredient":
            # Pre-fill slug from missing value
            entity_data["slug"] = input(
                f"  Slug [{missing.missing_value}]: "
            ).strip() or missing.missing_value
            entity_data["display_name"] = input("  Display name (required): ").strip()
            entity_data["category"] = input("  Category (required): ").strip()
            # Optional fields
            desc = input("  Description (optional): ").strip()
            if desc:
                entity_data["description"] = desc

        elif missing.entity_type == "product":
            # Products require ingredient reference
            entity_data["ingredient_slug"] = input(
                f"  Ingredient slug [{missing.missing_value}]: "
            ).strip() or missing.missing_value
            entity_data["brand"] = input("  Brand (optional): ").strip() or None
            entity_data["package_unit"] = input(
                "  Package unit (e.g., oz, lb, required): "
            ).strip()
            qty = input("  Package unit quantity (required): ").strip()
            try:
                entity_data["package_unit_quantity"] = float(qty)
            except ValueError:
                print("  Invalid quantity, using 1.0")
                entity_data["package_unit_quantity"] = 1.0
            # Optional fields
            name = input("  Product name (optional): ").strip()
            if name:
                entity_data["product_name"] = name

        return Resolution(
            choice=ResolutionChoice.CREATE,
            entity_type=missing.entity_type,
            missing_value=missing.missing_value,
            created_entity=entity_data,
        )

    def _handle_map(self, missing) -> "Resolution":
        """Handle MAP choice - show fuzzy search results and let user select."""
        from src.services.fk_resolver_service import (
            Resolution,
            ResolutionChoice,
            find_similar_entities,
        )

        # Perform fuzzy search
        print(f"\nSearching for similar {missing.entity_type}s...")
        similar = find_similar_entities(
            missing.entity_type, missing.missing_value, limit=5
        )

        if not similar:
            print("  No similar entities found.")
            # Fall back to asking for options again
            print("  You can:")
            print("  [C] Create new entity instead")
            print("  [S] Skip these records")
            while True:
                fallback = input("\nEnter choice (C/S): ").strip().upper()
                if fallback == "C":
                    return self._handle_create(missing)
                elif fallback == "S":
                    return Resolution(
                        choice=ResolutionChoice.SKIP,
                        entity_type=missing.entity_type,
                        missing_value=missing.missing_value,
                    )
                else:
                    print("Invalid choice. Enter C or S.")

        # Show similar entities
        print(f"\nSimilar {missing.entity_type}s found:")
        for i, entity in enumerate(similar):
            print(f"  [{i+1}] {entity['display']}")
        print(f"  [0] Cancel and choose another option")

        while True:
            choice = input("\nEnter number to select: ").strip()
            try:
                num = int(choice)
                if num == 0:
                    # Go back to main options
                    print("\nOptions:")
                    print("  [C] Create new entity")
                    print("  [M] Map to existing entity (search again)")
                    print("  [S] Skip these records")
                    sub_choice = input("\nEnter choice (C/M/S): ").strip().upper()
                    if sub_choice == "C":
                        return self._handle_create(missing)
                    elif sub_choice == "M":
                        return self._handle_map(missing)  # Recurse to search again
                    elif sub_choice == "S":
                        return Resolution(
                            choice=ResolutionChoice.SKIP,
                            entity_type=missing.entity_type,
                            missing_value=missing.missing_value,
                        )
                elif 1 <= num <= len(similar):
                    selected = similar[num - 1]
                    return Resolution(
                        choice=ResolutionChoice.MAP,
                        entity_type=missing.entity_type,
                        missing_value=missing.missing_value,
                        mapped_id=selected["id"],
                    )
                else:
                    print(f"Invalid number. Enter 0-{len(similar)}.")
            except ValueError:
                print("Please enter a number.")


def import_view_cmd(
    file_path: str,
    mode: str = "merge",
    interactive: bool = False,
    skip_on_error: bool = False,
    dry_run: bool = False,
) -> int:
    """
    Import denormalized view file (F030).

    Args:
        file_path: Path to the view JSON file
        mode: Import mode - "merge" (default) or "skip_existing"
        interactive: Enable interactive FK resolution
        skip_on_error: Skip records with errors instead of failing
        dry_run: Preview changes without modifying database

    Returns:
        0 on success, 1 on failure
    """
    from src.services.enhanced_import_service import import_view

    mode_display = f"mode: {mode}"
    if dry_run:
        mode_display += ", DRY RUN"
    if skip_on_error:
        mode_display += ", skip-on-error"
    if interactive:
        mode_display += ", interactive"

    print(f"Importing view from {file_path} ({mode_display})...")

    # Set up resolver if interactive mode
    resolver: Optional[CLIFKResolver] = None
    if interactive:
        resolver = CLIFKResolver()

    try:
        result = import_view(
            file_path,
            mode=mode,
            dry_run=dry_run,
            skip_on_error=skip_on_error,
            resolver=resolver,
        )

        # Print summary
        print("\n" + result.get_summary())

        # Return exit code based on failures
        return 0 if result.failed == 0 else 1

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

  Export complete database with manifest (F030):
    python -m src.utils.import_export_cli export-complete -o ./export_dir
    python -m src.utils.import_export_cli export-complete -o ./export_dir --zip

  Export denormalized view (F030):
    python -m src.utils.import_export_cli export-view -t products -o view_products.json

  Validate export checksums (F030):
    python -m src.utils.import_export_cli validate-export ./export_dir

  Import denormalized view (F030):
    python -m src.utils.import_export_cli import-view view_products.json
    python -m src.utils.import_export_cli import-view view_products.json --interactive
    python -m src.utils.import_export_cli import-view view_products.json --dry-run
    python -m src.utils.import_export_cli import-view view_products.json --skip-on-error

Note: Individual entity imports (import-ingredients, etc.) are no longer
supported. Use the 'import' command with a complete v3.2 format file.
""",
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Legacy export command (requires file)
    export_parser = subparsers.add_parser("export", help="Export all data (v3.2 format)")
    export_parser.add_argument("file", help="JSON file path")

    # Legacy entity-specific export commands
    for entity in ["ingredients", "recipes", "finished-goods", "bundles", "packages", "recipients", "events"]:
        entity_parser = subparsers.add_parser(
            f"export-{entity}",
            help=f"Export {entity} only"
        )
        entity_parser.add_argument("file", help="JSON file path")

    # Legacy import command
    import_parser = subparsers.add_parser("import", help="Import all data (v3.2 format)")
    import_parser.add_argument("file", help="JSON file path")
    import_parser.add_argument(
        "--mode",
        choices=["merge", "replace"],
        default="merge",
        help="Import mode: 'merge' (default) adds new records, 'replace' clears existing data first",
    )

    # F030: export-complete command
    export_complete_parser = subparsers.add_parser(
        "export-complete",
        help="Export complete database with manifest (F030)"
    )
    export_complete_parser.add_argument(
        "-o", "--output",
        dest="output_dir",
        help="Output directory (default: export_{timestamp})"
    )
    export_complete_parser.add_argument(
        "-z", "--zip",
        dest="create_zip",
        action="store_true",
        help="Create ZIP archive"
    )

    # F030: export-view command
    export_view_parser = subparsers.add_parser(
        "export-view",
        help="Export denormalized view (F030)"
    )
    export_view_parser.add_argument(
        "-t", "--type",
        dest="view_type",
        choices=["products", "inventory", "purchases"],
        required=True,
        help="View type to export"
    )
    export_view_parser.add_argument(
        "-o", "--output",
        dest="output_path",
        help="Output file path (default: view_{type}.json)"
    )

    # F030: validate-export command
    validate_parser = subparsers.add_parser(
        "validate-export",
        help="Validate export checksums (F030)"
    )
    validate_parser.add_argument(
        "export_dir",
        help="Path to export directory with manifest.json"
    )

    # F030: import-view command
    import_view_parser = subparsers.add_parser(
        "import-view",
        help="Import denormalized view (F030)"
    )
    import_view_parser.add_argument(
        "file",
        help="Input view JSON file path"
    )
    import_view_parser.add_argument(
        "-m", "--mode",
        dest="import_mode",
        choices=["merge", "skip_existing"],
        default="merge",
        help="Import mode: 'merge' (default) updates existing and adds new, 'skip_existing' only adds new"
    )
    import_view_parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Enable interactive FK resolution"
    )
    import_view_parser.add_argument(
        "-s", "--skip-on-error",
        dest="skip_on_error",
        action="store_true",
        help="Skip records with errors instead of failing"
    )
    import_view_parser.add_argument(
        "-d", "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Preview changes without modifying database"
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

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
    elif args.command == "export-complete":
        return export_complete_cmd(args.output_dir, args.create_zip)
    elif args.command == "export-view":
        return export_view_cmd(args.view_type, args.output_path)
    elif args.command == "validate-export":
        return validate_export_cmd(args.export_dir)
    elif args.command == "import-view":
        return import_view_cmd(
            args.file,
            mode=args.import_mode,
            interactive=args.interactive,
            skip_on_error=args.skip_on_error,
            dry_run=args.dry_run,
        )
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
