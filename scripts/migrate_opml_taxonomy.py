#!/usr/bin/env python3
"""
Migrate ingredient taxonomy from Dynalist OPML to test data format.

Parses a 3-tier OPML hierarchy (Category -> Subcategory -> Ingredient)
and generates JSON files for import into the bake-tracker database.

Usage:
    python scripts/migrate_opml_taxonomy.py [--input PATH] [--output-dir PATH]
"""

import argparse
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Optional


def slugify(name: str) -> str:
    """Convert a display name to a URL-friendly slug."""
    slug = name.lower().strip()
    # Remove ID brackets and delete markers first
    slug = re.sub(r'\s*\[\d+\]\s*', '', slug)
    slug = re.sub(r'\s*\[\?\?\?\]\s*', '', slug)
    slug = re.sub(r'\s+delete\s*$', '', slug, flags=re.IGNORECASE)
    # Replace common separators with underscore (matching existing convention)
    for char in [" ", "-", "/", "&", "'", ","]:
        slug = slug.replace(char, "_")
    # Remove non-alphanumeric characters except underscore
    slug = "".join(c for c in slug if c.isalnum() or c == "_")
    # Collapse multiple underscores
    while "__" in slug:
        slug = slug.replace("__", "_")
    # Strip leading/trailing underscores
    slug = slug.strip("_")
    return slug


def extract_id(text: str, is_ingredient: bool = True) -> tuple[str, Optional[int], bool]:
    """
    Extract ingredient ID from text.

    Args:
        text: The text to parse
        is_ingredient: If True, items without IDs will be flagged as needing new IDs

    Returns:
        Tuple of (clean_name, id_or_none, needs_new_id)
    """
    # Check for [###] pattern
    match = re.search(r'\[(\d+)\]', text)
    if match:
        id_val = int(match.group(1))
        clean_name = re.sub(r'\s*\[\d+\]\s*', '', text).strip()
        return (clean_name, id_val, False)

    # Check for [???] pattern
    if '[???]' in text:
        clean_name = re.sub(r'\s*\[\?\?\?\]\s*', '', text).strip()
        return (clean_name, None, True)

    # No ID pattern - flag as needing ID if it's an ingredient (leaf node)
    clean_name = text.strip()
    # Remove any delete markers for clean name
    clean_name = re.sub(r'\s+delete\s*$', '', clean_name, flags=re.IGNORECASE).strip()
    return (clean_name, None, is_ingredient)


def is_delete_item(text: str) -> bool:
    """Check if item is marked for deletion."""
    return bool(re.search(r'\bdelete\b', text, re.IGNORECASE))


def parse_opml(opml_path: str) -> dict:
    """
    Parse OPML file and extract taxonomy structure.

    Returns dict with:
        - categories: list of category dicts
        - subcategories: list of subcategory dicts
        - ingredients: list of ingredient dicts
        - deleted: list of deleted item names
        - needs_id: list of items needing new IDs
        - max_id: highest existing ID found
        - structural_issues: items with structural problems
    """
    tree = ET.parse(opml_path)
    root = tree.getroot()
    body = root.find('body')

    # Find the main taxonomy outline (first child of body)
    main_outline = body.find('outline')
    if main_outline is None:
        raise ValueError("No outline found in OPML body")

    categories = []
    subcategories = []
    ingredients = []
    deleted = []
    needs_id = []
    structural_issues = []
    max_id = 0

    # Process each category (top-level outlines under main)
    for cat_outline in main_outline.findall('outline'):
        cat_text = cat_outline.get('text', '')

        # Skip if marked delete
        if is_delete_item(cat_text):
            deleted.append(f"Category: {cat_text}")
            continue

        clean_cat_name, cat_id, _ = extract_id(cat_text, is_ingredient=False)
        cat_slug = slugify(clean_cat_name)

        # Check if category has an ID (structural issue - categories shouldn't have IDs typically)
        if cat_id is not None:
            structural_issues.append({
                "type": "category_with_id",
                "name": clean_cat_name,
                "id": cat_id,
                "note": "Category has ingredient ID - may function as both category and ingredient"
            })
            if cat_id > max_id:
                max_id = cat_id

        # Collect subcategory names for description
        subcat_names = []

        # Process subcategories
        for subcat_outline in cat_outline.findall('outline'):
            subcat_text = subcat_outline.get('text', '')

            # Skip if marked delete
            if is_delete_item(subcat_text):
                deleted.append(f"Subcategory: {subcat_text} (under {clean_cat_name})")
                continue

            clean_subcat_name, subcat_id, subcat_needs_id = extract_id(subcat_text, is_ingredient=False)
            subcat_slug = slugify(clean_subcat_name)
            subcat_names.append(clean_subcat_name)

            # Check if subcategory has an ID (structural issue)
            if subcat_id is not None:
                structural_issues.append({
                    "type": "subcategory_with_id",
                    "name": clean_subcat_name,
                    "id": subcat_id,
                    "category": clean_cat_name,
                    "note": "Subcategory has ingredient ID - may have children"
                })
                if subcat_id > max_id:
                    max_id = subcat_id
            elif subcat_needs_id:
                structural_issues.append({
                    "type": "subcategory_needs_id",
                    "name": clean_subcat_name,
                    "category": clean_cat_name,
                    "note": "Subcategory marked [???] - needs ID assignment"
                })

            # Collect ingredient names for subcategory description
            ing_names = []

            # Process ingredients
            for ing_outline in subcat_outline.findall('outline'):
                ing_text = ing_outline.get('text', '')

                # Skip if marked delete
                if is_delete_item(ing_text):
                    deleted.append(f"Ingredient: {ing_text} (under {clean_subcat_name})")
                    continue

                clean_ing_name, ing_id, ing_needs_id = extract_id(ing_text)
                ing_slug = slugify(clean_ing_name)
                ing_names.append(clean_ing_name)

                if ing_id is not None and ing_id > max_id:
                    max_id = ing_id

                ingredient = {
                    "name": clean_ing_name,
                    "slug": ing_slug,
                    "subcategory_slug": subcat_slug,
                    "category_slug": cat_slug,
                    "existing_id": ing_id,
                    "needs_new_id": ing_needs_id,
                    "notes": ""
                }

                if ing_needs_id:
                    needs_id.append(clean_ing_name)

                # Check for nested items under ingredient (shouldn't happen at level 3)
                nested = ing_outline.findall('outline')
                if nested:
                    ingredient["notes"] = f"Has {len(nested)} nested items - review manually"
                    structural_issues.append({
                        "type": "ingredient_with_children",
                        "name": clean_ing_name,
                        "subcategory": clean_subcat_name,
                        "children_count": len(nested),
                        "note": "Ingredient has nested items - exceeds 3-level hierarchy"
                    })

                ingredients.append(ingredient)

            # Create subcategory entry
            subcat_desc = f"Contains: {', '.join(ing_names[:5])}" if ing_names else "No ingredients"
            if len(ing_names) > 5:
                subcat_desc += f" (+{len(ing_names) - 5} more)"

            subcategory = {
                "name": clean_subcat_name,
                "slug": subcat_slug,
                "category_slug": cat_slug,
                "description": subcat_desc,
                "ingredient_count": len(ing_names)
            }
            subcategories.append(subcategory)

        # Create category entry
        cat_desc = f"Includes: {', '.join(subcat_names[:4])}" if subcat_names else "No subcategories"
        if len(subcat_names) > 4:
            cat_desc += f" (+{len(subcat_names) - 4} more)"

        category = {
            "name": clean_cat_name,
            "slug": cat_slug,
            "description": cat_desc,
            "subcategory_count": len(subcat_names)
        }
        categories.append(category)

    return {
        "categories": categories,
        "subcategories": subcategories,
        "ingredients": ingredients,
        "deleted": deleted,
        "needs_id": needs_id,
        "max_id": max_id,
        "structural_issues": structural_issues
    }


def assign_new_ids(ingredients: list, max_id: int) -> tuple[list, list]:
    """
    Assign new IDs to ingredients that need them.

    Returns:
        Tuple of (updated_ingredients, assignments_made)
    """
    next_id = max_id + 1
    assignments = []

    for ing in ingredients:
        if ing["needs_new_id"]:
            ing["existing_id"] = next_id
            ing["notes"] = f"NEW ID assigned: {next_id}"
            assignments.append({
                "name": ing["name"],
                "new_id": next_id,
                "subcategory": ing["subcategory_slug"]
            })
            next_id += 1
        ing.pop("needs_new_id", None)  # Clean up temporary field

    return ingredients, assignments


def find_duplicates(ingredients: list) -> list:
    """Find potential duplicate ingredients."""
    duplicates = []

    # Group by subcategory
    by_subcat = {}
    for ing in ingredients:
        subcat = ing["subcategory_slug"]
        if subcat not in by_subcat:
            by_subcat[subcat] = []
        by_subcat[subcat].append(ing)

    # Check for similar names within same subcategory
    for subcat, ings in by_subcat.items():
        names = [ing["name"].lower() for ing in ings]
        for i, name1 in enumerate(names):
            for j, name2 in enumerate(names[i+1:], i+1):
                # Check for similarity (one contains the other, or Levenshtein-like)
                if name1 in name2 or name2 in name1:
                    duplicates.append({
                        "item1": ings[i]["name"],
                        "id1": ings[i]["existing_id"],
                        "item2": ings[j]["name"],
                        "id2": ings[j]["existing_id"],
                        "subcategory": subcat
                    })

    return duplicates


def find_id_gaps(ingredients: list) -> list:
    """Find gaps in the ID sequence."""
    ids = sorted([ing["existing_id"] for ing in ingredients if ing["existing_id"] is not None])
    if not ids:
        return []

    gaps = []
    for i in range(len(ids) - 1):
        if ids[i+1] - ids[i] > 1:
            gaps.append({
                "after_id": ids[i],
                "before_id": ids[i+1],
                "gap_size": ids[i+1] - ids[i] - 1
            })

    return gaps


def generate_report(data: dict, assignments: list, duplicates: list, gaps: list, output_path: str):
    """Generate the validation report."""
    report = []
    report.append("# Taxonomy Migration Report")
    report.append(f"\nGenerated: {datetime.now().isoformat()}")
    report.append(f"\nSource: dynalist-2025-12-31.opml")
    report.append("\n---\n")

    # Summary
    report.append("## Summary\n")
    report.append(f"- **Categories**: {len(data['categories'])}")
    report.append(f"- **Subcategories**: {len(data['subcategories'])}")
    report.append(f"- **Ingredients**: {len(data['ingredients'])}")
    report.append(f"- **Items Deleted**: {len(data['deleted'])}")
    report.append(f"- **New IDs Assigned**: {len(assignments)}")
    report.append(f"- **Max Existing ID**: {data['max_id']}")
    report.append("")

    # Deleted items
    report.append("## Deleted Items\n")
    if data['deleted']:
        for item in data['deleted']:
            report.append(f"- {item}")
    else:
        report.append("_No items marked for deletion._")
    report.append("")

    # New ID assignments
    report.append("## New IDs Assigned\n")
    if assignments:
        report.append("| Ingredient | New ID | Subcategory |")
        report.append("|------------|--------|-------------|")
        for a in assignments:
            report.append(f"| {a['name']} | {a['new_id']} | {a['subcategory']} |")
    else:
        report.append("_No new IDs needed._")
    report.append("")

    # Duplicates
    report.append("## Potential Duplicates\n")
    if duplicates:
        report.append("| Item 1 | ID | Item 2 | ID | Subcategory |")
        report.append("|--------|-----|--------|-----|-------------|")
        for d in duplicates:
            report.append(f"| {d['item1']} | {d['id1']} | {d['item2']} | {d['id2']} | {d['subcategory']} |")
    else:
        report.append("_No duplicates detected._")
    report.append("")

    # ID Gaps
    report.append("## ID Gaps\n")
    if gaps:
        report.append("| After ID | Before ID | Gap Size |")
        report.append("|----------|-----------|----------|")
        for g in gaps:
            report.append(f"| {g['after_id']} | {g['before_id']} | {g['gap_size']} |")
    else:
        report.append("_No significant gaps in ID sequence._")
    report.append("")

    # Structural issues
    report.append("## Structural Issues\n")
    if data['structural_issues']:
        for issue in data['structural_issues']:
            report.append(f"### {issue['type']}")
            report.append(f"- **Name**: {issue['name']}")
            if 'id' in issue:
                report.append(f"- **ID**: {issue['id']}")
            if 'category' in issue:
                report.append(f"- **Category**: {issue['category']}")
            if 'subcategory' in issue:
                report.append(f"- **Subcategory**: {issue['subcategory']}")
            report.append(f"- **Note**: {issue['note']}")
            report.append("")
    else:
        report.append("_No structural issues detected._")
    report.append("")

    # Orphan check
    report.append("## Orphan Check\n")
    cat_slugs = {c['slug'] for c in data['categories']}
    subcat_slugs = {s['slug'] for s in data['subcategories']}

    orphan_subcats = [s for s in data['subcategories'] if s['category_slug'] not in cat_slugs]
    orphan_ings = [i for i in data['ingredients'] if i['subcategory_slug'] not in subcat_slugs]

    if orphan_subcats:
        report.append("**Orphaned Subcategories:**")
        for s in orphan_subcats:
            report.append(f"- {s['name']} (references missing category: {s['category_slug']})")

    if orphan_ings:
        report.append("**Orphaned Ingredients:**")
        for i in orphan_ings:
            report.append(f"- {i['name']} (references missing subcategory: {i['subcategory_slug']})")

    if not orphan_subcats and not orphan_ings:
        report.append("_All relationships valid. No orphans detected._")
    report.append("")

    # Category breakdown
    report.append("## Category Breakdown\n")
    for cat in data['categories']:
        subcat_count = cat['subcategory_count']
        ing_count = sum(1 for i in data['ingredients'] if i['category_slug'] == cat['slug'])
        report.append(f"### {cat['name']}")
        report.append(f"- Subcategories: {subcat_count}")
        report.append(f"- Total Ingredients: {ing_count}")
        report.append("")

    with open(output_path, 'w') as f:
        f.write('\n'.join(report))

    return report


def load_existing_slugs(sample_data_path: str) -> dict:
    """
    Load existing slug mappings from sample_data.json.

    Returns dict mapping display_name (lowercase) -> slug
    """
    slug_map = {}
    try:
        with open(sample_data_path) as f:
            data = json.load(f)

        if 'ingredients' in data:
            for ing in data['ingredients']:
                name = ing.get('display_name', '').lower().strip()
                slug = ing.get('slug', '')
                if name and slug:
                    slug_map[name] = slug
            print(f"Loaded {len(slug_map)} existing slugs from {sample_data_path}")
    except FileNotFoundError:
        print(f"Warning: {sample_data_path} not found, will generate new slugs")
    except Exception as e:
        print(f"Warning: Error loading slugs: {e}")

    return slug_map


def apply_existing_slugs(ingredients: list, subcategories: list, slug_map: dict) -> tuple[int, int]:
    """
    Apply existing slugs from mapping to ingredients and subcategories.

    Returns tuple of (ingredients_matched, subcategories_matched)
    """
    ing_matched = 0
    subcat_matched = 0

    for ing in ingredients:
        name_lower = ing['name'].lower().strip()
        if name_lower in slug_map:
            ing['slug'] = slug_map[name_lower]
            ing_matched += 1

    # For subcategories, try to match as well (some might be in the catalog)
    for subcat in subcategories:
        name_lower = subcat['name'].lower().strip()
        if name_lower in slug_map:
            subcat['slug'] = slug_map[name_lower]
            subcat_matched += 1

    return ing_matched, subcat_matched


def main():
    parser = argparse.ArgumentParser(description='Migrate OPML taxonomy to test data format')
    parser.add_argument('--input', '-i',
                        default='test_data/dynalist-2025-12-31.opml',
                        help='Input OPML file path')
    parser.add_argument('--output-dir', '-o',
                        default='test_data',
                        help='Output directory for JSON files')
    parser.add_argument('--slug-source', '-s',
                        default='test_data/sample_data.json',
                        help='Source file for existing slug mappings')
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    # Load existing slugs
    slug_map = load_existing_slugs(args.slug_source)

    print(f"Parsing OPML: {input_path}")
    data = parse_opml(str(input_path))

    print(f"Found: {len(data['categories'])} categories, {len(data['subcategories'])} subcategories, {len(data['ingredients'])} ingredients")
    print(f"Deleted: {len(data['deleted'])} items")
    print(f"Max existing ID: {data['max_id']}")

    # Apply existing slugs
    if slug_map:
        ing_matched, subcat_matched = apply_existing_slugs(
            data['ingredients'], data['subcategories'], slug_map
        )
        print(f"Matched existing slugs: {ing_matched} ingredients, {subcat_matched} subcategories")
        unmatched = len(data['ingredients']) - ing_matched
        if unmatched > 0:
            print(f"  ({unmatched} ingredients will use generated slugs)")

    # Assign new IDs
    ingredients, assignments = assign_new_ids(data['ingredients'], data['max_id'])
    print(f"Assigned {len(assignments)} new IDs (starting from {data['max_id'] + 1})")

    # Find duplicates
    duplicates = find_duplicates(ingredients)
    print(f"Found {len(duplicates)} potential duplicates")

    # Find ID gaps
    gaps = find_id_gaps(ingredients)
    print(f"Found {len(gaps)} ID gaps")

    # Write categories JSON
    cat_path = output_dir / 'categories_taxonomy.json'
    with open(cat_path, 'w') as f:
        json.dump(data['categories'], f, indent=2)
    print(f"Wrote: {cat_path}")

    # Write subcategories JSON
    subcat_path = output_dir / 'subcategories_taxonomy.json'
    with open(subcat_path, 'w') as f:
        json.dump(data['subcategories'], f, indent=2)
    print(f"Wrote: {subcat_path}")

    # Write ingredients JSON
    ing_path = output_dir / 'ingredients_taxonomy.json'
    with open(ing_path, 'w') as f:
        json.dump(ingredients, f, indent=2)
    print(f"Wrote: {ing_path}")

    # Generate report
    report_path = output_dir / 'taxonomy_migration_report.md'
    generate_report(data, assignments, duplicates, gaps, str(report_path))
    print(f"Wrote: {report_path}")

    # Print summary
    print("\n" + "="*60)
    print("MIGRATION SUMMARY")
    print("="*60)
    print(f"Categories:     {len(data['categories'])}")
    print(f"Subcategories:  {len(data['subcategories'])}")
    print(f"Ingredients:    {len(ingredients)}")
    print(f"Deleted:        {len(data['deleted'])}")
    print(f"New IDs:        {len(assignments)}")
    print(f"Duplicates:     {len(duplicates)}")
    print(f"Structural:     {len(data['structural_issues'])}")
    print("="*60)

    if data['structural_issues']:
        print("\nSTRUCTURAL ISSUES REQUIRING REVIEW:")
        for issue in data['structural_issues']:
            print(f"  - {issue['type']}: {issue['name']}")

    if duplicates:
        print("\nPOTENTIAL DUPLICATES REQUIRING REVIEW:")
        for d in duplicates:
            print(f"  - {d['item1']} [{d['id1']}] vs {d['item2']} [{d['id2']}]")

    return 0


if __name__ == '__main__':
    exit(main())
