#!/usr/bin/env python3
"""
Test the migration pipeline with sample data.

This script creates sample input files and runs the full pipeline to verify
the scripts work correctly together.

Usage:
    python scripts/migrate_hierarchy/test_pipeline.py
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# Add script directory to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from transform_hierarchy import transform_hierarchy
from validate_hierarchy import validate_hierarchy


def create_sample_export(path: str) -> None:
    """Create a sample ingredients export file."""
    export_data = {
        "metadata": {
            "export_date": "2025-12-31T12:00:00Z",
            "record_count": 7,
            "source_database": "test.db",
            "schema_version": "031-ingredient-hierarchy-taxonomy"
        },
        "ingredients": [
            {
                "id": 1,
                "slug": "all_purpose_flour",
                "display_name": "All-Purpose Flour",
                "category": "Flour",
                "is_packaging": False
            },
            {
                "id": 2,
                "slug": "bread_flour",
                "display_name": "Bread Flour",
                "category": "Flour",
                "is_packaging": False
            },
            {
                "id": 3,
                "slug": "whole_wheat_flour",
                "display_name": "Whole Wheat Flour",
                "category": "Flour",
                "is_packaging": False
            },
            {
                "id": 4,
                "slug": "semi_sweet_chips",
                "display_name": "Semi-Sweet Chocolate Chips",
                "category": "Chocolate",
                "is_packaging": False
            },
            {
                "id": 5,
                "slug": "unsweetened_cocoa",
                "display_name": "Unsweetened Cocoa Powder",
                "category": "Chocolate",
                "is_packaging": False
            },
            {
                "id": 6,
                "slug": "granulated_sugar",
                "display_name": "Granulated Sugar",
                "category": "Sugar",
                "is_packaging": False
            },
            {
                "id": 7,
                "slug": "gift_box_small",
                "display_name": "Small Gift Box",
                "category": "Packaging",
                "is_packaging": True
            }
        ]
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2)


def create_sample_ai_suggestions(path: str) -> None:
    """Create sample AI-generated hierarchy suggestions."""
    suggestions = {
        "categories": [
            {
                "name": "Flour & Starches",
                "slug": "flour_starches",
                "level": 0,
                "children": ["White Flour", "Whole Grain Flour"]
            },
            {
                "name": "White Flour",
                "slug": "white_flour",
                "level": 1,
                "parent": "Flour & Starches",
                "children": []
            },
            {
                "name": "Whole Grain Flour",
                "slug": "whole_grain_flour",
                "level": 1,
                "parent": "Flour & Starches",
                "children": []
            },
            {
                "name": "Chocolate & Cocoa",
                "slug": "chocolate_cocoa",
                "level": 0,
                "children": ["Chocolate Chips", "Cocoa Powders"]
            },
            {
                "name": "Chocolate Chips",
                "slug": "chocolate_chips",
                "level": 1,
                "parent": "Chocolate & Cocoa",
                "children": []
            },
            {
                "name": "Cocoa Powders",
                "slug": "cocoa_powders",
                "level": 1,
                "parent": "Chocolate & Cocoa",
                "children": []
            },
            {
                "name": "Sugar & Sweeteners",
                "slug": "sugar_sweeteners",
                "level": 0,
                "children": ["Granulated Sugars"]
            },
            {
                "name": "Granulated Sugars",
                "slug": "granulated_sugars",
                "level": 1,
                "parent": "Sugar & Sweeteners",
                "children": []
            },
            {
                "name": "Packaging",
                "slug": "packaging",
                "level": 0,
                "children": ["Boxes"]
            },
            {
                "name": "Boxes",
                "slug": "boxes",
                "level": 1,
                "parent": "Packaging",
                "children": []
            }
        ],
        "assignments": [
            {"ingredient_slug": "all_purpose_flour", "parent_name": "White Flour"},
            {"ingredient_slug": "bread_flour", "parent_name": "White Flour"},
            {"ingredient_slug": "whole_wheat_flour", "parent_name": "Whole Grain Flour"},
            {"ingredient_slug": "semi_sweet_chips", "parent_name": "Chocolate Chips"},
            {"ingredient_slug": "unsweetened_cocoa", "parent_name": "Cocoa Powders"},
            {"ingredient_slug": "granulated_sugar", "parent_name": "Granulated Sugars"},
            {"ingredient_slug": "gift_box_small", "parent_name": "Boxes"}
        ]
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(suggestions, f, indent=2)


def create_cyclic_suggestions(path: str) -> None:
    """Create AI suggestions with a cycle for testing."""
    suggestions = {
        "categories": [
            {
                "name": "Category A",
                "slug": "category_a",
                "level": 0,
                "parent": "Category B",  # Creates cycle: A -> B -> A
                "children": []
            },
            {
                "name": "Category B",
                "slug": "category_b",
                "level": 0,
                "parent": "Category A",
                "children": []
            }
        ],
        "assignments": []
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(suggestions, f, indent=2)


def test_cycle_detection() -> bool:
    """Test that cycle detection works correctly."""
    print("Testing cycle detection...")

    with tempfile.TemporaryDirectory() as tmpdir:
        export_path = os.path.join(tmpdir, "export.json")
        ai_path = os.path.join(tmpdir, "ai.json")
        transform_path = os.path.join(tmpdir, "transform.json")

        # Create minimal export
        with open(export_path, "w") as f:
            json.dump({"metadata": {}, "ingredients": []}, f)

        # Create cyclic suggestions
        create_cyclic_suggestions(ai_path)

        # Transform
        transform_hierarchy(export_path, ai_path, transform_path)

        # Validate - should detect cycle
        validation = validate_hierarchy(transform_path)

        has_cycle_error = any(e["code"] == "CYCLE_DETECTED" for e in validation.errors)
        if has_cycle_error:
            print("  Cycle detection: PASS")
            return True
        else:
            print("  Cycle detection: FAIL - no cycle detected")
            return False


def main():
    """Run the test pipeline."""
    print("=" * 60)
    print("Migration Pipeline Test")
    print("=" * 60)
    print()

    # Create temp directory for test files
    with tempfile.TemporaryDirectory() as tmpdir:
        export_path = os.path.join(tmpdir, "ingredients_export.json")
        ai_path = os.path.join(tmpdir, "ai_hierarchy_suggestions.json")
        transform_path = os.path.join(tmpdir, "transformed_ingredients.json")

        # Step 1: Create sample files
        print("Step 1: Creating sample files...")
        create_sample_export(export_path)
        create_sample_ai_suggestions(ai_path)
        print(f"  Created: {export_path}")
        print(f"  Created: {ai_path}")
        print()

        # Step 2: Run transform
        print("Step 2: Running transform...")
        try:
            result = transform_hierarchy(export_path, ai_path, transform_path)
            print(f"  Original ingredients: {result['original_count']}")
            print(f"  New categories created: {result['new_categories_count']}")
            print(f"  Transformed ingredients: {result['transformed_count']}")
            print(f"  Unassigned: {result['unassigned_count']}")
            print()
        except Exception as e:
            print(f"  ERROR: {e}")
            return 1

        # Step 3: Run validation
        print("Step 3: Running validation...")
        try:
            validation = validate_hierarchy(transform_path)
            print(f"  Total items: {validation.stats.get('total_items', 0)}")
            print(f"  Level distribution: {validation.stats.get('level_distribution', {})}")
            print(f"  Errors: {len(validation.errors)}")
            print(f"  Warnings: {len(validation.warnings)}")
            print()

            if validation.errors:
                print("  ERRORS:")
                for error in validation.errors:
                    print(f"    [{error['code']}] {error['message']}")

            if validation.warnings:
                print("  WARNINGS:")
                for warning in validation.warnings:
                    print(f"    [{warning['code']}] {warning['message']}")

        except Exception as e:
            print(f"  ERROR: {e}")
            return 1

        # Step 4: Check results
        print()
        if not validation.is_valid():
            print("=" * 60)
            print("TEST FAILED - Validation errors detected")
            print("=" * 60)
            return 1

    # Run additional tests
    print()
    cycle_pass = test_cycle_detection()

    print()
    print("=" * 60)
    if validation.is_valid() and cycle_pass:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("=" * 60)
    return 0 if (validation.is_valid() and cycle_pass) else 1


if __name__ == "__main__":
    sys.exit(main())
