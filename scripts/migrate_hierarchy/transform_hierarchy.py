#!/usr/bin/env python3
"""
Transform exported ingredients with AI-generated hierarchy suggestions.

This script merges the original ingredient export with AI-generated hierarchy
suggestions to produce an import-ready JSON file with proper parent references
and hierarchy levels calculated.

Usage:
    python scripts/migrate_hierarchy/transform_hierarchy.py \\
        --input ingredients_export.json \\
        --ai-suggestions ai_hierarchy_suggestions.json \\
        --output transformed_ingredients.json

AI Suggestions JSON Format:
{
    "categories": [
        {
            "name": "Chocolate",
            "slug": "chocolate",
            "level": 0,
            "children": ["Dark Chocolate", "Milk Chocolate", "White Chocolate"]
        },
        {
            "name": "Dark Chocolate",
            "slug": "dark_chocolate",
            "level": 1,
            "parent": "Chocolate",
            "children": []
        }
    ],
    "assignments": [
        {
            "ingredient_slug": "semi_sweet_chips",
            "parent_name": "Dark Chocolate"
        }
    ]
}

Output JSON Format:
{
    "metadata": {...},
    "new_categories": [...],
    "transformed_ingredients": [...],
    "unassigned_ingredients": [...]
}
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def slugify(name: str) -> str:
    """
    Convert a display name to a URL-friendly slug.

    Args:
        name: Display name to convert

    Returns:
        Lowercase slug with underscores
    """
    # Convert to lowercase, replace spaces and hyphens with underscores
    slug = name.lower().strip()
    # Replace common separators with underscore
    for char in [" ", "-", "/"]:
        slug = slug.replace(char, "_")
    # Remove non-alphanumeric characters except underscore
    slug = "".join(c for c in slug if c.isalnum() or c == "_")
    # Collapse multiple underscores
    while "__" in slug:
        slug = slug.replace("__", "_")
    # Strip leading/trailing underscores
    slug = slug.strip("_")
    return slug


def get_default_paths():
    """Get default input/output paths relative to this script."""
    script_dir = Path(__file__).parent
    output_dir = script_dir / "output"
    return {
        "input": str(output_dir / "ingredients_export.json"),
        "ai_suggestions": str(output_dir / "ai_hierarchy_suggestions.json"),
        "output": str(output_dir / "transformed_ingredients.json")
    }


def transform_hierarchy(
    input_path: str,
    ai_suggestions_path: str,
    output_path: str
) -> dict:
    """
    Transform exported ingredients with AI-generated hierarchy suggestions.

    Args:
        input_path: Path to the exported ingredients JSON
        ai_suggestions_path: Path to AI-generated suggestions JSON
        output_path: Path to write the transformed JSON

    Returns:
        Dictionary containing transformation results and statistics

    Raises:
        FileNotFoundError: If input files do not exist
        json.JSONDecodeError: If JSON files are malformed
        ValueError: If data validation fails
    """
    # Load input files
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if not os.path.exists(ai_suggestions_path):
        raise FileNotFoundError(f"AI suggestions file not found: {ai_suggestions_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        export_data = json.load(f)

    with open(ai_suggestions_path, "r", encoding="utf-8") as f:
        ai_suggestions = json.load(f)

    # Validate input structure
    if "ingredients" not in export_data:
        raise ValueError("Export data missing 'ingredients' key")
    if "categories" not in ai_suggestions:
        raise ValueError("AI suggestions missing 'categories' key")
    if "assignments" not in ai_suggestions:
        raise ValueError("AI suggestions missing 'assignments' key")

    # Build lookup maps
    # Map ingredient slug -> ingredient data
    ingredient_map = {
        ing["slug"]: ing for ing in export_data["ingredients"] if ing.get("slug")
    }

    # Map category name -> category data (from AI suggestions)
    category_map = {cat["name"]: cat for cat in ai_suggestions["categories"]}

    # Map ingredient slug -> parent category name (from AI suggestions)
    assignment_map = {
        asgn["ingredient_slug"]: asgn["parent_name"]
        for asgn in ai_suggestions["assignments"]
    }

    # Process new category ingredients (level 0 and 1)
    # Two-pass approach: first build slug map, then resolve parents
    new_categories = []
    category_slug_map = {}  # Map category name -> slug for parent resolution

    # Pass 1: Build slug map for all categories
    for category in ai_suggestions["categories"]:
        cat_slug = category.get("slug") or slugify(category["name"])
        category_slug_map[category["name"]] = cat_slug

    # Pass 2: Create category entries with resolved parent slugs
    for category in ai_suggestions["categories"]:
        cat_slug = category_slug_map[category["name"]]

        parent_slug = None
        if category.get("parent"):
            parent_slug = category_slug_map.get(category["parent"])

        new_cat = {
            "slug": cat_slug,
            "display_name": category["name"],
            "hierarchy_level": category["level"],
            "parent_slug": parent_slug,
            "is_new_category": True,
            "is_packaging": False,
            "category": category["name"]  # Retain for rollback
        }
        new_categories.append(new_cat)

    # Process existing ingredients - assign to hierarchy
    transformed_ingredients = []
    unassigned_ingredients = []

    for ingredient in export_data["ingredients"]:
        slug = ingredient.get("slug")
        if not slug:
            # Ingredients without slugs need manual attention
            unassigned_ingredients.append({
                "id": ingredient.get("id"),
                "display_name": ingredient.get("display_name"),
                "reason": "Missing slug"
            })
            continue

        # Check if this ingredient has an assignment
        parent_name = assignment_map.get(slug)

        if parent_name:
            # Resolve parent slug from category map
            parent_slug = category_slug_map.get(parent_name)
            if not parent_slug:
                # Parent category doesn't exist in AI suggestions
                unassigned_ingredients.append({
                    "id": ingredient.get("id"),
                    "slug": slug,
                    "display_name": ingredient.get("display_name"),
                    "reason": f"Parent category '{parent_name}' not found in categories"
                })
                # Default to leaf without parent
                transformed = {
                    **ingredient,
                    "hierarchy_level": 2,
                    "parent_slug": None,
                    "transformation_note": f"Parent '{parent_name}' not found, defaulted to orphan leaf"
                }
            else:
                # Valid assignment
                transformed = {
                    **ingredient,
                    "hierarchy_level": 2,  # Existing ingredients become leaves
                    "parent_slug": parent_slug
                }
        else:
            # No assignment - default to level 2 leaf without parent
            unassigned_ingredients.append({
                "id": ingredient.get("id"),
                "slug": slug,
                "display_name": ingredient.get("display_name"),
                "reason": "No assignment in AI suggestions"
            })
            transformed = {
                **ingredient,
                "hierarchy_level": 2,
                "parent_slug": None,
                "transformation_note": "No AI assignment, defaulted to orphan leaf"
            }

        transformed_ingredients.append(transformed)

    # Build output document
    output_data = {
        "metadata": {
            "transform_date": datetime.now(timezone.utc).isoformat(),
            "source_export": input_path,
            "ai_suggestions_source": ai_suggestions_path,
            "original_count": len(export_data["ingredients"]),
            "new_categories_count": len(new_categories),
            "transformed_count": len(transformed_ingredients),
            "unassigned_count": len(unassigned_ingredients)
        },
        "new_categories": new_categories,
        "transformed_ingredients": transformed_ingredients,
        "unassigned_ingredients": unassigned_ingredients
    }

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    return {
        "success": True,
        "output_path": output_path,
        "original_count": len(export_data["ingredients"]),
        "new_categories_count": len(new_categories),
        "transformed_count": len(transformed_ingredients),
        "unassigned_count": len(unassigned_ingredients)
    }


def main():
    """Main entry point for the transform script."""
    defaults = get_default_paths()

    parser = argparse.ArgumentParser(
        description="Transform exported ingredients with AI-generated hierarchy suggestions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--input", "-i",
        default=defaults["input"],
        help="Input ingredients export JSON (default: %(default)s)"
    )
    parser.add_argument(
        "--ai-suggestions", "-a",
        default=defaults["ai_suggestions"],
        help="AI-generated hierarchy suggestions JSON (default: %(default)s)"
    )
    parser.add_argument(
        "--output", "-o",
        default=defaults["output"],
        help="Output transformed JSON (default: %(default)s)"
    )

    args = parser.parse_args()

    print(f"Input export: {args.input}")
    print(f"AI suggestions: {args.ai_suggestions}")
    print(f"Output: {args.output}")
    print()

    try:
        result = transform_hierarchy(args.input, args.ai_suggestions, args.output)

        print("Transform successful!")
        print(f"  Original ingredients: {result['original_count']}")
        print(f"  New categories created: {result['new_categories_count']}")
        print(f"  Transformed ingredients: {result['transformed_count']}")
        print(f"  Unassigned (need review): {result['unassigned_count']}")
        print(f"  Output file: {result['output_path']}")

        if result['unassigned_count'] > 0:
            print("\nWarning: Some ingredients were not assigned to categories.")
            print("Review 'unassigned_ingredients' in the output file.")

        return 0

    except FileNotFoundError as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1

    except json.JSONDecodeError as e:
        print(f"\nJSON parsing error: {e}", file=sys.stderr)
        return 1

    except ValueError as e:
        print(f"\nValidation error: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
