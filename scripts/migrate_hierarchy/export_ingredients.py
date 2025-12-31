#!/usr/bin/env python3
"""
Export ingredients from the database for hierarchy migration.

This script exports all current ingredients to a JSON file that can be used
as input for external AI categorization. The export includes all relevant
fields needed for categorization decisions.

Usage:
    python scripts/migrate_hierarchy/export_ingredients.py [--output PATH] [--db-path PATH]

Output JSON format:
{
    "metadata": {
        "export_date": "2025-12-31T12:00:00Z",
        "record_count": 487,
        "source_database": "~/Documents/BakeTracker/bake_tracker.db"
    },
    "ingredients": [
        {
            "id": 1,
            "slug": "all_purpose_flour",
            "display_name": "All-Purpose Flour",
            "category": "Flour",
            "is_packaging": false,
            "description": "Standard wheat flour for general baking"
        },
        ...
    ]
}
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


def get_default_db_path() -> str:
    """Get the default database path."""
    return os.path.expanduser("~/Documents/BakeTracker/bake_tracker.db")


def get_default_output_path() -> str:
    """Get the default output path relative to this script."""
    script_dir = Path(__file__).parent
    return str(script_dir / "output" / "ingredients_export.json")


def export_ingredients(db_path: str, output_path: str) -> dict:
    """
    Export all ingredients from the database to JSON.

    Args:
        db_path: Path to the SQLite database
        output_path: Path to write the JSON export

    Returns:
        Dictionary containing export metadata and results

    Raises:
        FileNotFoundError: If database does not exist
        sqlite3.Error: If database query fails
    """
    # Validate database exists
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")

    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    cursor = conn.cursor()

    try:
        # Query all ingredients with fields relevant for categorization
        cursor.execute("""
            SELECT
                id,
                slug,
                display_name,
                category,
                is_packaging,
                description,
                notes,
                parent_ingredient_id,
                hierarchy_level
            FROM ingredients
            ORDER BY category, display_name
        """)

        rows = cursor.fetchall()

        # Build ingredients list
        ingredients = []
        for row in rows:
            ingredient = {
                "id": row["id"],
                "slug": row["slug"],
                "display_name": row["display_name"],
                "category": row["category"],
                "is_packaging": bool(row["is_packaging"]),
            }

            # Include optional fields if present
            if row["description"]:
                ingredient["description"] = row["description"]
            if row["notes"]:
                ingredient["notes"] = row["notes"]

            # Include current hierarchy fields if set (for re-runs)
            if row["parent_ingredient_id"] is not None:
                ingredient["parent_ingredient_id"] = row["parent_ingredient_id"]
            if row["hierarchy_level"] is not None:
                ingredient["hierarchy_level"] = row["hierarchy_level"]

            ingredients.append(ingredient)

        # Build export document
        export_data = {
            "metadata": {
                "export_date": datetime.now(timezone.utc).isoformat(),
                "record_count": len(ingredients),
                "source_database": db_path,
                "schema_version": "031-ingredient-hierarchy-taxonomy"
            },
            "ingredients": ingredients
        }

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # Write JSON export
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return {
            "success": True,
            "record_count": len(ingredients),
            "output_path": output_path,
            "categories": list(set(i["category"] for i in ingredients))
        }

    finally:
        conn.close()


def main():
    """Main entry point for the export script."""
    parser = argparse.ArgumentParser(
        description="Export ingredients from database for hierarchy migration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--output", "-o",
        default=get_default_output_path(),
        help="Output JSON file path (default: %(default)s)"
    )
    parser.add_argument(
        "--db-path", "-d",
        default=get_default_db_path(),
        help="Database file path (default: %(default)s)"
    )

    args = parser.parse_args()

    print(f"Exporting ingredients from: {args.db_path}")
    print(f"Output path: {args.output}")

    try:
        result = export_ingredients(args.db_path, args.output)

        print(f"\nExport successful!")
        print(f"  Records exported: {result['record_count']}")
        print(f"  Output file: {result['output_path']}")
        print(f"  Existing categories: {len(result['categories'])}")
        print(f"    Categories: {', '.join(sorted(result['categories']))}")

        return 0

    except FileNotFoundError as e:
        print(f"\nError: {e}", file=sys.stderr)
        print("Make sure the database exists and the path is correct.", file=sys.stderr)
        return 1

    except sqlite3.Error as e:
        print(f"\nDatabase error: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
