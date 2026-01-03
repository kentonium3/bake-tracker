#!/usr/bin/env python3
"""Transform sample_data.json to be importable into a fresh database.

Issues addressed:
1. Ingredients missing 'category' field (required by model)
2. Purchases using ID-based FKs that won't work in fresh database
3. Inventory items using purchase_id that won't work in fresh database

Usage:
    python scripts/transform_sample_data_for_import.py
"""

import json
from pathlib import Path


def build_category_map(ingredients: list) -> dict:
    """Build a map of slug -> category (root ancestor's display_name).

    For hierarchical ingredients:
    - L0 (root): category = own display_name
    - L1: category = parent's display_name
    - L2: category = grandparent's display_name (root)
    """
    # First, build slug -> ingredient lookup
    by_slug = {ing["slug"]: ing for ing in ingredients}

    # Build category map
    category_map = {}

    for ing in ingredients:
        slug = ing["slug"]
        level = ing.get("hierarchy_level", 2)

        if level == 0:
            # Root category - use own display_name
            category_map[slug] = ing["display_name"]
        elif level == 1:
            # Subcategory - use parent's display_name
            parent_slug = ing.get("parent_slug")
            if parent_slug and parent_slug in by_slug:
                category_map[slug] = by_slug[parent_slug]["display_name"]
            else:
                # Fallback - shouldn't happen
                category_map[slug] = "Unknown"
        elif level == 2:
            # Leaf - find root ancestor
            parent_slug = ing.get("parent_slug")
            if parent_slug and parent_slug in by_slug:
                parent = by_slug[parent_slug]
                if parent.get("hierarchy_level") == 0:
                    # Parent is root
                    category_map[slug] = parent["display_name"]
                else:
                    # Parent is L1 - get grandparent
                    grandparent_slug = parent.get("parent_slug")
                    if grandparent_slug and grandparent_slug in by_slug:
                        category_map[slug] = by_slug[grandparent_slug]["display_name"]
                    else:
                        category_map[slug] = "Unknown"
            else:
                # No parent - shouldn't happen for L2
                category_map[slug] = "Unknown"
        else:
            category_map[slug] = "Unknown"

    return category_map


def transform_ingredients(ingredients: list) -> list:
    """Add category field to all ingredients."""
    category_map = build_category_map(ingredients)

    transformed = []
    for ing in ingredients:
        new_ing = dict(ing)
        new_ing["category"] = category_map.get(ing["slug"], "Unknown")
        transformed.append(new_ing)

    return transformed


def transform_purchases(purchases: list) -> list:
    """Remove ID-based FKs from purchases to force slug-based lookup."""
    transformed = []
    for purch in purchases:
        new_purch = dict(purch)
        # Remove ID-based fields that break fresh import
        new_purch.pop("id", None)
        new_purch.pop("product_id", None)
        new_purch.pop("supplier_id", None)
        transformed.append(new_purch)

    return transformed


def transform_inventory_items(items: list) -> list:
    """Remove purchase_id from inventory items."""
    transformed = []
    for item in items:
        new_item = dict(item)
        # Remove purchase_id - can't resolve in fresh database
        new_item.pop("purchase_id", None)
        transformed.append(new_item)

    return transformed


def main():
    input_path = Path("test_data/sample_data.json")
    output_path = Path("test_data/sample_data_importable.json")

    print(f"Reading {input_path}...")
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Original version: {data.get('version')}")

    # Transform ingredients
    if "ingredients" in data:
        orig_count = len(data["ingredients"])
        data["ingredients"] = transform_ingredients(data["ingredients"])
        print(f"Transformed {orig_count} ingredients (added category field)")

        # Verify categories
        categories = set(ing["category"] for ing in data["ingredients"])
        print(f"  Categories found: {len(categories)}")
        unknown = [ing["slug"] for ing in data["ingredients"] if ing["category"] == "Unknown"]
        if unknown:
            print(f"  WARNING: {len(unknown)} ingredients with Unknown category: {unknown[:5]}...")

    # Transform purchases
    if "purchases" in data:
        orig_count = len(data["purchases"])
        data["purchases"] = transform_purchases(data["purchases"])
        print(f"Transformed {orig_count} purchases (removed ID-based FKs)")

    # Transform inventory items
    if "inventory_items" in data:
        orig_count = len(data["inventory_items"])
        data["inventory_items"] = transform_inventory_items(data["inventory_items"])
        print(f"Transformed {orig_count} inventory items (removed purchase_id)")

    # Update version to indicate transformation
    data["version"] = "3.6-importable"
    data["transformed_at"] = "2026-01-02"
    data["transformation_notes"] = [
        "Added 'category' field to ingredients (derived from hierarchy)",
        "Removed ID-based FKs from purchases",
        "Removed purchase_id from inventory_items",
    ]

    # Write output
    print(f"\nWriting {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("Done!")
    print(f"\nTo import: Use {output_path} with the import function")


if __name__ == "__main__":
    main()
