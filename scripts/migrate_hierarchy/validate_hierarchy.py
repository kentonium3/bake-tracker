#!/usr/bin/env python3
"""
Validate transformed hierarchy data before import.

This script performs comprehensive validation checks on the transformed
hierarchy data to ensure data integrity before import into the database.

Usage:
    python scripts/migrate_hierarchy/validate_hierarchy.py \\
        --input transformed_ingredients.json

Validation Checks:
1. No orphans - All parent references resolve to existing entries
2. Valid hierarchy levels - Only 0, 1, or 2
3. No cycles - Parent chain does not loop back to itself
4. No duplicate slugs - All slugs are unique
5. Level consistency - Children have level = parent level + 1
6. Leaf constraint - Only level 2 ingredients should be used in recipes
7. Root constraint - Level 0 ingredients must have no parent

Exit Codes:
    0 - All validations passed
    1 - Validation errors found (critical issues)
    2 - File or parsing errors
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def get_default_input_path() -> str:
    """Get default input path relative to this script."""
    script_dir = Path(__file__).parent
    return str(script_dir / "output" / "transformed_ingredients.json")


class ValidationResult:
    """Container for validation results."""

    def __init__(self):
        self.errors = []  # Critical issues that must be fixed
        self.warnings = []  # Non-critical issues for review
        self.stats = {}  # Aggregate statistics

    def add_error(self, code: str, message: str, context: dict = None):
        """Add a validation error."""
        self.errors.append({
            "code": code,
            "message": message,
            "context": context or {}
        })

    def add_warning(self, code: str, message: str, context: dict = None):
        """Add a validation warning."""
        self.warnings.append({
            "code": code,
            "message": message,
            "context": context or {}
        })

    def is_valid(self) -> bool:
        """Return True if no errors (warnings are acceptable)."""
        return len(self.errors) == 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output."""
        return {
            "is_valid": self.is_valid(),
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings,
            "stats": self.stats
        }


def validate_hierarchy(input_path: str) -> ValidationResult:
    """
    Validate transformed hierarchy data.

    Args:
        input_path: Path to the transformed JSON file

    Returns:
        ValidationResult containing errors, warnings, and statistics

    Raises:
        FileNotFoundError: If input file does not exist
        json.JSONDecodeError: If JSON file is malformed
    """
    result = ValidationResult()

    # Load input file
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Validate structure
    if "new_categories" not in data:
        result.add_error("MISSING_CATEGORIES", "Input missing 'new_categories' key")
        return result
    if "transformed_ingredients" not in data:
        result.add_error("MISSING_INGREDIENTS", "Input missing 'transformed_ingredients' key")
        return result

    new_categories = data["new_categories"]
    transformed = data["transformed_ingredients"]
    unassigned = data.get("unassigned_ingredients", [])

    # Build combined list of all items
    all_items = new_categories + transformed

    # Build lookup maps
    slug_to_item = {}  # slug -> item
    slug_to_parent = {}  # slug -> parent_slug
    slug_to_level = {}  # slug -> hierarchy_level
    level_counts = defaultdict(int)  # level -> count

    # Check for duplicate slugs and build maps
    for item in all_items:
        slug = item.get("slug")
        if not slug:
            result.add_error(
                "MISSING_SLUG",
                f"Item missing slug",
                {"display_name": item.get("display_name"), "id": item.get("id")}
            )
            continue

        if slug in slug_to_item:
            result.add_error(
                "DUPLICATE_SLUG",
                f"Duplicate slug: {slug}",
                {
                    "slug": slug,
                    "first_item": slug_to_item[slug].get("display_name"),
                    "second_item": item.get("display_name")
                }
            )
        else:
            slug_to_item[slug] = item
            slug_to_parent[slug] = item.get("parent_slug")
            level = item.get("hierarchy_level")
            slug_to_level[slug] = level
            if level is not None:
                level_counts[level] += 1

    # Validate hierarchy levels
    for slug, level in slug_to_level.items():
        if level is None:
            result.add_error(
                "MISSING_LEVEL",
                f"Missing hierarchy_level for {slug}",
                {"slug": slug, "display_name": slug_to_item[slug].get("display_name")}
            )
        elif level not in (0, 1, 2):
            result.add_error(
                "INVALID_LEVEL",
                f"Invalid hierarchy_level {level} for {slug} (must be 0, 1, or 2)",
                {"slug": slug, "level": level}
            )

    # Validate parent references (no orphans)
    for slug, parent_slug in slug_to_parent.items():
        if parent_slug is not None:
            if parent_slug not in slug_to_item:
                result.add_error(
                    "ORPHAN",
                    f"Parent '{parent_slug}' not found for '{slug}'",
                    {"slug": slug, "parent_slug": parent_slug}
                )

    # Validate root constraint (level 0 must have no parent)
    for slug, level in slug_to_level.items():
        if level == 0:
            parent = slug_to_parent.get(slug)
            if parent is not None:
                result.add_error(
                    "ROOT_HAS_PARENT",
                    f"Root ingredient '{slug}' should not have a parent",
                    {"slug": slug, "parent_slug": parent}
                )

    # Validate level consistency (child level = parent level + 1)
    for slug, parent_slug in slug_to_parent.items():
        if parent_slug is None:
            continue
        parent_level = slug_to_level.get(parent_slug)
        child_level = slug_to_level.get(slug)
        if parent_level is not None and child_level is not None:
            if child_level != parent_level + 1:
                result.add_error(
                    "LEVEL_INCONSISTENCY",
                    f"Level mismatch: '{slug}' (level {child_level}) has parent '{parent_slug}' (level {parent_level})",
                    {
                        "slug": slug,
                        "child_level": child_level,
                        "parent_slug": parent_slug,
                        "parent_level": parent_level
                    }
                )

    # Detect cycles in parent chain
    def detect_cycle(start_slug: str) -> Optional[list]:
        """
        Check if following parent chain leads to a cycle.

        Returns the cycle path if found, None otherwise.
        """
        visited = set()
        path = []
        current = start_slug

        while current is not None:
            if current in visited:
                # Found a cycle - extract the cycle portion
                cycle_start = path.index(current)
                return path[cycle_start:] + [current]
            visited.add(current)
            path.append(current)
            current = slug_to_parent.get(current)

        return None

    # Check each item for cycles (only report each cycle once)
    reported_cycles = set()
    for slug in slug_to_parent:
        cycle = detect_cycle(slug)
        if cycle:
            # Create a normalized cycle representation for deduplication
            cycle_key = tuple(sorted(cycle[:-1]))  # Exclude repeated element
            if cycle_key not in reported_cycles:
                reported_cycles.add(cycle_key)
                result.add_error(
                    "CYCLE_DETECTED",
                    f"Cycle in parent chain: {' -> '.join(cycle)}",
                    {"cycle": cycle}
                )

    # Check for unassigned ingredients (warning, not error)
    if unassigned:
        result.add_warning(
            "UNASSIGNED_INGREDIENTS",
            f"{len(unassigned)} ingredients were not assigned to categories",
            {"count": len(unassigned), "samples": unassigned[:5]}
        )

    # Check for orphan leaves (level 2 without parent) - warning
    orphan_leaves = [
        slug for slug, parent in slug_to_parent.items()
        if parent is None and slug_to_level.get(slug) == 2
    ]
    if orphan_leaves:
        result.add_warning(
            "ORPHAN_LEAVES",
            f"{len(orphan_leaves)} leaf ingredients have no parent category",
            {"count": len(orphan_leaves), "samples": orphan_leaves[:10]}
        )

    # Collect statistics
    result.stats = {
        "total_items": len(all_items),
        "new_categories": len(new_categories),
        "transformed_ingredients": len(transformed),
        "unassigned_count": len(unassigned),
        "level_distribution": dict(level_counts),
        "orphan_leaves_count": len(orphan_leaves)
    }

    return result


def main():
    """Main entry point for the validation script."""
    parser = argparse.ArgumentParser(
        description="Validate transformed hierarchy data before import",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--input", "-i",
        default=get_default_input_path(),
        help="Input transformed JSON file (default: %(default)s)"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output validation report JSON (optional)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only output errors (no statistics)"
    )

    args = parser.parse_args()

    print(f"Validating: {args.input}")
    print()

    try:
        result = validate_hierarchy(args.input)

        # Print statistics
        if not args.quiet:
            print("Statistics:")
            print(f"  Total items: {result.stats.get('total_items', 0)}")
            print(f"  New categories: {result.stats.get('new_categories', 0)}")
            print(f"  Transformed ingredients: {result.stats.get('transformed_ingredients', 0)}")
            print(f"  Unassigned: {result.stats.get('unassigned_count', 0)}")
            print()
            print("Level distribution:")
            for level, count in sorted(result.stats.get('level_distribution', {}).items()):
                level_name = {0: "Root", 1: "Mid-tier", 2: "Leaf"}.get(level, f"Level {level}")
                print(f"  {level_name} ({level}): {count}")
            print()

        # Print errors
        if result.errors:
            print(f"ERRORS ({len(result.errors)}):")
            for error in result.errors:
                print(f"  [{error['code']}] {error['message']}")
                if error.get('context'):
                    for key, value in error['context'].items():
                        print(f"    {key}: {value}")
            print()

        # Print warnings
        if result.warnings:
            print(f"WARNINGS ({len(result.warnings)}):")
            for warning in result.warnings:
                print(f"  [{warning['code']}] {warning['message']}")
            print()

        # Write output report if requested
        if args.output:
            output_dir = os.path.dirname(args.output)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as f:
                report = result.to_dict()
                report["validation_date"] = datetime.now(timezone.utc).isoformat()
                report["input_file"] = args.input
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"Validation report written to: {args.output}")
            print()

        # Final verdict
        if result.is_valid():
            print("VALIDATION PASSED - Hierarchy is ready for import")
            return 0
        else:
            print("VALIDATION FAILED - Fix errors before import")
            return 1

    except FileNotFoundError as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 2

    except json.JSONDecodeError as e:
        print(f"\nJSON parsing error: {e}", file=sys.stderr)
        return 2

    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
