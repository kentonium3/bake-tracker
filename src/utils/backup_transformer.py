"""
Backup Transformer - Convert old backup format to current schema requirements.

F080 added slug fields to recipes, finished_units, and other entities.
This utility transforms backups created before F080 to meet current requirements.

Usage:
    python -m src.utils.backup_transformer /path/to/export_directory/

    # Or from Python:
    from src.utils.backup_transformer import transform_backup_directory
    transform_backup_directory("/path/to/export_2025-12-30_224206/")
"""

import json
import re
import unicodedata
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def _generate_slug(name: str) -> str:
    """
    Generate a URL-safe slug from a name.

    Args:
        name: Name to convert to slug

    Returns:
        Lowercase slug with hyphens, alphanumeric only
    """
    if not name:
        return "unknown"

    # Normalize unicode characters (handles accents like e -> e)
    slug = unicodedata.normalize("NFKD", name)
    slug = slug.encode("ascii", "ignore").decode("ascii")

    # Convert to lowercase
    slug = slug.lower()

    # Replace spaces and underscores with hyphens
    slug = re.sub(r"[\s_]+", "-", slug)

    # Remove non-alphanumeric characters (except hyphens)
    slug = re.sub(r"[^a-z0-9-]", "", slug)

    # Collapse multiple hyphens
    slug = re.sub(r"-+", "-", slug)

    # Remove leading/trailing hyphens
    slug = slug.strip("-")

    # Ensure not empty
    if not slug:
        return "unknown"

    # Limit length (200 chars)
    if len(slug) > 200:
        slug = slug[:200].rstrip("-")

    return slug


def _generate_unique_slug(name: str, used_slugs: set) -> str:
    """
    Generate unique slug, adding suffix if needed.

    Args:
        name: Display name to convert
        used_slugs: Set of already used slugs

    Returns:
        Unique slug
    """
    base_slug = _generate_slug(name)

    if base_slug not in used_slugs:
        return base_slug

    # Add numeric suffix for uniqueness
    counter = 2
    while f"{base_slug}-{counter}" in used_slugs:
        counter += 1

    return f"{base_slug}-{counter}"


def transform_recipes(records: List[Dict], existing_slugs: Optional[set] = None) -> List[Dict]:
    """
    Transform recipe records to include required F080 fields.

    Adds:
        - slug: Generated from recipe name if not present
        - previous_slug: Set to None if not present
        - is_production_ready: Set to True if not present (assume existing recipes are ready)

    Removes deprecated fields:
        - yield_quantity
        - yield_unit
        - yield_description

    Args:
        records: List of recipe records from old backup
        existing_slugs: Optional set of slugs already in use

    Returns:
        Transformed records
    """
    used_slugs = existing_slugs.copy() if existing_slugs else set()
    transformed = []

    for record in records:
        new_record = record.copy()

        # Generate slug if not present
        if not new_record.get("slug"):
            name = new_record.get("name", "unknown")
            slug = _generate_unique_slug(name, used_slugs)
            new_record["slug"] = slug
            used_slugs.add(slug)

        # Set previous_slug if not present
        if "previous_slug" not in new_record:
            new_record["previous_slug"] = None

        # Set is_production_ready if not present (default to True for existing recipes)
        if "is_production_ready" not in new_record:
            new_record["is_production_ready"] = True

        # Remove deprecated yield fields (they're ignored anyway, but clean up)
        for deprecated_field in ["yield_quantity", "yield_unit", "yield_description"]:
            new_record.pop(deprecated_field, None)

        transformed.append(new_record)

    return transformed


def transform_finished_units(records: List[Dict], existing_slugs: Optional[set] = None) -> List[Dict]:
    """
    Transform finished_unit records to include required F080 fields.

    Adds:
        - slug: Generated from display_name if not present
        - previous_slug: Set to None if not present

    Args:
        records: List of finished_unit records from old backup
        existing_slugs: Optional set of slugs already in use

    Returns:
        Transformed records
    """
    used_slugs = existing_slugs.copy() if existing_slugs else set()
    transformed = []

    for record in records:
        new_record = record.copy()

        # Generate slug if not present
        if not new_record.get("slug"):
            name = new_record.get("display_name", "unknown")
            slug = _generate_unique_slug(name, used_slugs)
            new_record["slug"] = slug
            used_slugs.add(slug)

        # Set previous_slug if not present
        if "previous_slug" not in new_record:
            new_record["previous_slug"] = None

        transformed.append(new_record)

    return transformed


def transform_file(file_path: Path, output_path: Optional[Path] = None) -> Dict:
    """
    Transform a single backup file to meet current schema requirements.

    Args:
        file_path: Path to the JSON backup file
        output_path: Optional output path (defaults to overwriting input)

    Returns:
        Dict with transformation stats
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    entity_type = data.get("entity_type", "")
    records = data.get("records", [])
    original_count = len(records)

    # Apply entity-specific transformations
    if entity_type == "recipes":
        records = transform_recipes(records)
    elif entity_type == "finished_units":
        records = transform_finished_units(records)
    else:
        # No transformation needed for this entity type
        return {
            "file": str(file_path),
            "entity_type": entity_type,
            "status": "skipped",
            "reason": "no transformation needed",
        }

    # Update data and write
    data["records"] = records
    data["transformed_at"] = datetime.now().isoformat()
    data["transformer_version"] = "1.0"

    target_path = output_path or file_path
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return {
        "file": str(file_path),
        "entity_type": entity_type,
        "status": "transformed",
        "records_processed": len(records),
    }


def transform_backup_directory(
    backup_dir: str | Path,
    output_dir: Optional[str | Path] = None,
    create_backup: bool = True,
) -> Dict:
    """
    Transform all applicable files in a backup directory.

    Args:
        backup_dir: Path to backup directory containing JSON files
        output_dir: Optional output directory (defaults to in-place)
        create_backup: If True and output_dir is None, create backup of originals

    Returns:
        Dict with transformation results
    """
    backup_path = Path(backup_dir)
    output_path = Path(output_dir) if output_dir else backup_path

    if not backup_path.exists():
        raise ValueError(f"Backup directory not found: {backup_path}")

    # Create backup if modifying in-place
    if create_backup and output_path == backup_path:
        backup_copy = backup_path.parent / f"{backup_path.name}_original"
        if not backup_copy.exists():
            shutil.copytree(backup_path, backup_copy)
            print(f"Created backup at: {backup_copy}")

    # Create output directory if needed
    if output_path != backup_path:
        output_path.mkdir(parents=True, exist_ok=True)

    results = {
        "backup_dir": str(backup_path),
        "output_dir": str(output_path),
        "files": [],
        "summary": {
            "transformed": 0,
            "skipped": 0,
            "errors": 0,
        },
    }

    # Transform applicable files
    for json_file in sorted(backup_path.glob("*.json")):
        if json_file.name == "manifest.json":
            # Copy manifest as-is
            if output_path != backup_path:
                shutil.copy(json_file, output_path / json_file.name)
            continue

        try:
            target_file = output_path / json_file.name if output_path != backup_path else None
            result = transform_file(json_file, target_file)
            results["files"].append(result)

            if result["status"] == "transformed":
                results["summary"]["transformed"] += 1
            else:
                results["summary"]["skipped"] += 1

        except Exception as e:
            results["files"].append({
                "file": str(json_file),
                "status": "error",
                "error": str(e),
            })
            results["summary"]["errors"] += 1

    return results


def main():
    """CLI entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.utils.backup_transformer <backup_directory> [output_directory]")
        print("\nTransforms old backup files to meet F080 schema requirements.")
        print("\nExamples:")
        print("  # Transform in-place (creates backup of originals)")
        print("  python -m src.utils.backup_transformer /path/to/export_2025-12-30_224206/")
        print()
        print("  # Transform to new directory")
        print("  python -m src.utils.backup_transformer /path/to/export/ /path/to/transformed_export/")
        sys.exit(1)

    backup_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Transforming backup: {backup_dir}")
    if output_dir:
        print(f"Output directory: {output_dir}")

    results = transform_backup_directory(backup_dir, output_dir)

    print("\n=== Transformation Results ===")
    print(f"Backup directory: {results['backup_dir']}")
    print(f"Output directory: {results['output_dir']}")
    print(f"\nSummary:")
    print(f"  Transformed: {results['summary']['transformed']}")
    print(f"  Skipped: {results['summary']['skipped']}")
    print(f"  Errors: {results['summary']['errors']}")

    print("\nFile details:")
    for file_result in results["files"]:
        status = file_result["status"]
        if status == "transformed":
            print(f"  [TRANSFORMED] {file_result['file']} ({file_result['records_processed']} records)")
        elif status == "skipped":
            print(f"  [SKIPPED] {file_result['file']} - {file_result.get('reason', 'no changes needed')}")
        elif status == "error":
            print(f"  [ERROR] {file_result['file']} - {file_result.get('error', 'unknown error')}")


if __name__ == "__main__":
    main()
