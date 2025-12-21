#!/usr/bin/env python3
"""
Migrate production history export from v1.0 to v1.1 format.

Feature 025: Production Loss Tracking

This script transforms exported production history data from the v1.0 format
(without loss tracking) to the v1.1 format (with loss tracking fields).

Adds default loss tracking fields to existing production runs:
- production_status: "complete"
- loss_quantity: 0
- losses: []

The script is idempotent - running it on already-transformed data is safe.

Usage:
    python scripts/migrate_v1_0_to_v1_1.py input.json output.json

Examples:
    # Transform a backup file
    python scripts/migrate_v1_0_to_v1_1.py backup.json migrated.json

    # Transform in-place (output overwrites input)
    python scripts/migrate_v1_0_to_v1_1.py data.json data.json
"""

import json
import sys
from pathlib import Path
from typing import Any


def transform_v1_0_to_v1_1(data: dict[str, Any]) -> dict[str, Any]:
    """
    Transform v1.0 export to v1.1 format.

    Adds default loss tracking fields to each production run:
    - production_status: "complete" (all historical runs assumed complete)
    - loss_quantity: 0 (no loss data for historical runs)
    - losses: [] (empty loss records array)

    Args:
        data: The v1.0 format export data dictionary

    Returns:
        The transformed v1.1 format data dictionary
    """
    # Check and log version
    version = data.get("version", "1.0")
    if version == "1.1":
        print(f"Data is already v1.1 format. No transformation needed.")
        return data
    elif version != "1.0":
        print(f"Warning: Expected v1.0, got v{version}. Proceeding with transform.")

    # Transform each production run
    runs_count = 0
    for run in data.get("production_runs", []):
        # Add default loss tracking fields if not present
        run.setdefault("production_status", "complete")
        run.setdefault("loss_quantity", 0)
        run.setdefault("losses", [])
        runs_count += 1

    # Update version
    data["version"] = "1.1"

    print(f"Transformed {runs_count} production runs from v1.0 to v1.1 format")
    return data


def validate_input(data: dict[str, Any]) -> list[str]:
    """
    Validate input data structure.

    Args:
        data: The input data dictionary

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    if not isinstance(data, dict):
        errors.append("Input must be a JSON object/dictionary")
        return errors

    if "production_runs" not in data:
        errors.append("Missing 'production_runs' key in input data")
    elif not isinstance(data["production_runs"], list):
        errors.append("'production_runs' must be an array/list")

    return errors


def main() -> int:
    """
    Main entry point for the migration script.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    if len(sys.argv) != 3:
        print(__doc__)
        print("Error: Requires exactly 2 arguments: input_file output_file")
        return 1

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    # Validate input file exists
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        return 1

    # Read input file
    try:
        with open(input_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in input file: {e}")
        return 1
    except Exception as e:
        print(f"Error reading input file: {e}")
        return 1

    # Validate input structure
    validation_errors = validate_input(data)
    if validation_errors:
        for error in validation_errors:
            print(f"Validation Error: {error}")
        return 1

    # Transform data
    transformed = transform_v1_0_to_v1_1(data)

    # Write output file
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(transformed, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error writing output file: {e}")
        return 1

    print(f"Output written to: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
