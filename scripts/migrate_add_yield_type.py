#!/usr/bin/env python3
"""
Migration script: Add yield_type field to finished_units export.

This script transforms a pre-083 export to the new schema by adding
yield_type='SERVING' to all finished_unit records.

Usage:
    python scripts/migrate_add_yield_type.py <export_dir>

The script modifies finished_units.json in place (with backup).
"""

import json
import shutil
import sys
from pathlib import Path
from datetime import datetime


def transform_finished_units(export_dir: Path) -> dict:
    """Transform finished_units.json to add yield_type field.

    Args:
        export_dir: Path to export directory

    Returns:
        dict with transformation results
    """
    fu_file = export_dir / "finished_units.json"

    if not fu_file.exists():
        return {
            "status": "skipped",
            "message": "finished_units.json not found",
            "records_processed": 0,
        }

    # Create backup
    backup_file = export_dir / f"finished_units.json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(fu_file, backup_file)

    # Load existing data
    with open(fu_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Handle both wrapped format (new) and list format (legacy)
    if isinstance(data, dict) and "records" in data:
        # New format: {"version": "1.0", "entity_type": "finished_units", "records": [...]}
        records = data["records"]
        is_wrapped = True
    elif isinstance(data, list):
        # Legacy format: [...]
        records = data
        is_wrapped = False
    else:
        return {
            "status": "error",
            "message": "finished_units.json has unexpected format (not a list or wrapped records)",
            "records_processed": 0,
        }

    # Transform records
    transformed_count = 0
    already_has_count = 0

    for record in records:
        if "yield_type" not in record:
            record["yield_type"] = "SERVING"
            transformed_count += 1
        else:
            already_has_count += 1

    # Write back in original format
    if is_wrapped:
        data["records"] = records
        output_data = data
    else:
        output_data = records

    with open(fu_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    return {
        "status": "success",
        "message": f"Transformed {transformed_count} records, {already_has_count} already had yield_type",
        "records_processed": len(records),
        "transformed": transformed_count,
        "already_had_yield_type": already_has_count,
        "backup_file": str(backup_file),
    }


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/migrate_add_yield_type.py <export_dir>")
        print("\nThis script transforms finished_units.json to add yield_type field.")
        print("Run AFTER exporting from old schema, BEFORE importing to new schema.")
        sys.exit(1)

    export_dir = Path(sys.argv[1])

    if not export_dir.is_dir():
        print(f"Error: {export_dir} is not a directory")
        sys.exit(1)

    print(f"Transforming exports in: {export_dir}")
    print("-" * 50)

    result = transform_finished_units(export_dir)

    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    print(f"Records processed: {result['records_processed']}")

    if result["status"] == "success":
        print(f"Transformed: {result['transformed']}")
        print(f"Already had yield_type: {result['already_had_yield_type']}")
        print(f"Backup created: {result['backup_file']}")
        print("\nTransformation complete. You can now import to the new schema.")
    elif result["status"] == "error":
        print("\nTransformation failed. Check the error message above.")
        sys.exit(1)
    else:
        print("\nNo transformation needed.")


if __name__ == "__main__":
    main()
