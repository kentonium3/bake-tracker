"""
CLI for catalog import operations.

Imports catalog data (ingredients, products, recipes) from a JSON file
with support for ADD_ONLY and AUGMENT modes.

Usage:
    python -m src.utils.import_catalog catalog.json
    python -m src.utils.import_catalog catalog.json --mode=augment
    python -m src.utils.import_catalog catalog.json --entity=ingredients
    python -m src.utils.import_catalog catalog.json --dry-run --verbose

Exit Codes:
    0 - Success (all records processed, may have skips)
    1 - Partial success (some records failed)
    2 - Complete failure (no records imported, or critical error)
    3 - Invalid arguments or file not found
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.database import initialize_app_database
from src.services.catalog_import_service import (
    import_catalog,
    CatalogImportError,
    CatalogImportResult,
)


# Exit code constants
EXIT_SUCCESS = 0
EXIT_PARTIAL = 1
EXIT_FAILURE = 2
EXIT_INVALID_ARGS = 3


def get_exit_code(result: CatalogImportResult) -> int:
    """
    Determine exit code based on import result.

    Args:
        result: The CatalogImportResult from import operation

    Returns:
        Exit code: 0=success, 1=partial, 2=failure
    """
    if result.has_errors:
        # Check if any succeeded
        if result.total_added > 0 or result.total_augmented > 0:
            return EXIT_PARTIAL  # Some succeeded, some failed
        else:
            return EXIT_FAILURE  # All failed
    return EXIT_SUCCESS  # All succeeded (may have skips)


def print_verbose_details(result: CatalogImportResult) -> None:
    """Print detailed output for verbose mode."""
    # Print warnings (skip details)
    if result.warnings:
        print("\nSkipped Records:")
        for warning in result.warnings:
            print(f"  - {warning}")

    # Print all errors with full detail
    if result.errors:
        print("\nFailed Records:")
        for error in result.errors:
            print(f"  - [{error.error_type}] {error.entity_type}: {error.identifier}")
            print(f"      Message: {error.message}")
            print(f"      Suggestion: {error.suggestion}")

    # Print augment details
    if result._augment_details:
        print("\nAugmented Records:")
        for detail in result._augment_details:
            fields = ", ".join(detail["fields_updated"])
            print(f"  - {detail['entity_type']}: {detail['identifier']} ({fields})")


def main(args=None):
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Import catalog data (ingredients, products, recipes)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s catalog.json                           # Import all entities
  %(prog)s catalog.json --entity=ingredients      # Import only ingredients
  %(prog)s catalog.json --mode=augment            # Update null fields on existing
  %(prog)s catalog.json --dry-run                 # Preview changes
  %(prog)s catalog.json --dry-run --verbose       # Preview with details

Exit Codes:
  0 - Success (all records processed)
  1 - Partial success (some records failed)
  2 - Complete failure (no records imported)
  3 - Invalid arguments or file not found
        """,
    )

    parser.add_argument(
        "file",
        help="Path to catalog JSON file",
    )

    parser.add_argument(
        "--mode",
        choices=["add", "augment"],
        default="add",
        help="Import mode: add (create new, skip existing) or augment (update null fields)",
    )

    parser.add_argument(
        "--entity",
        action="append",
        choices=["ingredients", "products", "recipes"],
        dest="entities",
        help="Entity type to import (can specify multiple times, default: all)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying the database",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed output for each record",
    )

    parsed_args = parser.parse_args(args)

    # Show dry-run header early
    if parsed_args.dry_run:
        print("=" * 60)
        print("DRY RUN - No changes will be made")
        print("=" * 60)
        print()

    # Initialize database
    initialize_app_database()

    # Execute import
    try:
        result = import_catalog(
            file_path=parsed_args.file,
            mode=parsed_args.mode,
            entities=parsed_args.entities,
            dry_run=parsed_args.dry_run,
        )

        # Print summary
        print(result.get_summary())

        # Print verbose details if requested
        if parsed_args.verbose:
            print_verbose_details(result)

        # Return appropriate exit code
        return get_exit_code(result)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return EXIT_INVALID_ARGS

    except CatalogImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        return EXIT_INVALID_ARGS

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(main())
