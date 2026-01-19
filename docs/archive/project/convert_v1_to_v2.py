"""
Convert v1.0 test data to v2.0 Ingredient/Variant architecture.

This script reads the v1.0 format file and converts it to the v2.0 format
that separates ingredients from variants (brands).
"""

import json
import re
from typing import Dict, List, Any


def create_slug(name: str) -> str:
    """Convert a name to a slug (lowercase with underscores)."""
    # Remove special characters and convert to lowercase
    slug = name.lower()
    # Replace spaces and hyphens with underscores
    slug = re.sub(r'[- ]+', '_', slug)
    # Remove any remaining non-alphanumeric characters (except underscores)
    slug = re.sub(r'[^a-z0-9_]', '', slug)
    # Remove duplicate underscores
    slug = re.sub(r'_+', '_', slug)
    # Remove leading/trailing underscores
    slug = slug.strip('_')
    return slug


def determine_recipe_unit(ingredient_name: str, category: str) -> str:
    """Determine the default recipe unit for an ingredient."""
    name_lower = ingredient_name.lower()

    # Weight-based ingredients
    if any(word in name_lower for word in ['chocolate chips', 'nuts', 'pecans', 'walnuts', 'almonds']):
        return 'oz'

    # Small quantity ingredients
    if any(word in name_lower for word in ['extract', 'vanilla', 'almond extract', 'food coloring', 'salt', 'baking soda', 'baking powder', 'cream of tartar', 'yeast']):
        return 'tsp'

    # Dairy (mostly by volume)
    if category == 'Dairy':
        if any(word in name_lower for word in ['cream cheese', 'butter']):
            return 'cup'
        return 'cup'

    # Eggs
    if 'egg' in name_lower:
        return 'each'

    # Liquids
    if any(word in name_lower for word in ['milk', 'cream', 'water', 'juice', 'oil', 'honey', 'syrup', 'molasses']):
        return 'cup'

    # Flour, sugar, cocoa - volume
    if category in ['Flour', 'Sugar', 'Cocoa Powders']:
        return 'cup'

    # Default to cup for most baking ingredients
    return 'cup'


def create_name_mapping(v1_data: Dict[str, Any]) -> Dict[str, str]:
    """Create mapping from recipe ingredient names to ingredient list names."""
    # Get all ingredient names
    ingredient_names = {ing['name'] for ing in v1_data.get('ingredients', [])}

    # Collect all recipe ingredient names
    recipe_ing_names = set()
    for recipe in v1_data.get('recipes', []):
        for ing in recipe.get('ingredients', []):
            recipe_ing_names.add(ing['ingredient_name'])

    # Create mapping
    name_map = {}

    # Known mappings
    known_mappings = {
        'Vanilla Extract': 'Pure Vanilla Extract',
        'Confectioners\' Sugar': 'Powdered Sugar',
        'Walnuts, Chopped': 'Walnuts',
        'Semisweet Chocolate Chips': 'Semi-Sweet Chocolate Chips',
    }

    for recipe_name in recipe_ing_names:
        # Check if exact match exists
        if recipe_name in ingredient_names:
            name_map[recipe_name] = recipe_name
        # Check known mappings
        elif recipe_name in known_mappings and known_mappings[recipe_name] in ingredient_names:
            name_map[recipe_name] = known_mappings[recipe_name]
        else:
            # Will need to create this ingredient
            name_map[recipe_name] = recipe_name

    return name_map


def convert_v1_to_v2(v1_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert v1.0 format to v2.0 format."""
    v2_data = {
        'ingredients': [],
        'variants': [],
        'unit_conversions': [],
        'recipes': [],
        'finished_goods': [],
    }

    # Track slugs to avoid duplicates
    slug_counts: Dict[str, int] = {}

    # Create name mapping for recipe ingredients
    name_mapping = create_name_mapping(v1_data)

    # Get all ingredient names we'll need
    ingredient_names_needed = set(name_mapping.values())
    existing_ingredient_names = {ing['name'] for ing in v1_data.get('ingredients', [])}
    missing_ingredient_names = ingredient_names_needed - existing_ingredient_names

    # Convert existing ingredients
    print("\nConverting ingredients to v2.0 format...")
    for v1_ing in v1_data.get('ingredients', []):
        name = v1_ing['name']
        brand = v1_ing.get('brand', 'Generic')
        category = v1_ing['category']

        # Create slug
        base_slug = create_slug(name)

        # Handle duplicate slugs
        if base_slug in slug_counts:
            slug_counts[base_slug] += 1
            slug = f"{base_slug}_{slug_counts[base_slug]}"
        else:
            slug_counts[base_slug] = 0
            slug = base_slug

        # Determine recipe unit
        recipe_unit = determine_recipe_unit(name, category)

        # Create ingredient (generic)
        ingredient = {
            'name': name,
            'slug': slug,
            'category': category,
            'recipe_unit': recipe_unit,
        }

        # Add optional fields
        if 'notes' in v1_ing:
            ingredient['notes'] = v1_ing['notes']

        # Calculate density_g_per_ml from volume_equivalents if available
        if 'volume_equivalents' in v1_ing and len(v1_ing['volume_equivalents']) > 0:
            ve = v1_ing['volume_equivalents'][0]
            if ve.get('volume_unit') == 'cup' and ve.get('weight_unit') == 'g':
                # 1 cup = 236.588 ml
                grams_per_cup = ve['weight_quantity']
                density_g_per_ml = grams_per_cup / 236.588
                ingredient['density_g_per_ml'] = round(density_g_per_ml, 3)

        v2_data['ingredients'].append(ingredient)

        # Create variant (brand-specific)
        variant = {
            'ingredient_slug': slug,
            'brand': brand,
            'purchase_unit': v1_ing.get('purchase_unit', 'lb'),
            'purchase_quantity': v1_ing.get('purchase_quantity', 1.0),
        }

        # Add optional fields
        if 'package_type' in v1_ing:
            variant['package_type'] = v1_ing['package_type']
        if 'notes' in v1_ing:
            variant['notes'] = v1_ing['notes']

        # Mark preferred if it's a known good brand
        if brand in ['King Arthur', 'Kirkland Signature', 'Ghirardelli', 'Guittard']:
            variant['preferred'] = True

        v2_data['variants'].append(variant)

        # Create unit conversion if we have volume_equivalents
        if 'volume_equivalents' in v1_ing and len(v1_ing['volume_equivalents']) > 0:
            for ve in v1_ing['volume_equivalents']:
                volume_unit = ve.get('volume_unit')
                weight_unit = ve.get('weight_unit', 'g')

                if volume_unit and weight_unit:
                    # Convert grams to pounds if needed
                    weight_qty = ve['weight_quantity']
                    if weight_unit == 'g':
                        # Convert to oz for easier use
                        weight_qty = weight_qty / 28.3495  # g to oz
                        weight_unit = 'oz'

                    conversion = {
                        'ingredient_slug': slug,
                        'from_unit': weight_unit,
                        'from_quantity': round(weight_qty, 2),
                        'to_unit': volume_unit,
                        'to_quantity': ve['volume_quantity'],
                    }
                    v2_data['unit_conversions'].append(conversion)

    # Create missing ingredients
    if missing_ingredient_names:
        print(f"\nCreating {len(missing_ingredient_names)} missing ingredients...")
        for name in sorted(missing_ingredient_names):
            print(f"  + {name}")

            # Infer category from name
            name_lower = name.lower()
            if 'flour' in name_lower:
                category = 'Flour'
            elif 'sugar' in name_lower:
                category = 'Sugar'
            elif any(word in name_lower for word in ['chocolate', 'chip']):
                category = 'Chocolate/Candies'
            elif any(word in name_lower for word in ['almond', 'walnut', 'pecan']):
                category = 'Nuts'
            elif 'extract' in name_lower:
                category = 'Extracts'
            elif any(word in name_lower for word in ['water', 'juice']):
                category = 'Misc'
            elif 'mincemeat' in name_lower:
                category = 'Dried Fruits'
            else:
                category = 'Misc'

            # Create slug
            base_slug = create_slug(name)
            if base_slug in slug_counts:
                slug_counts[base_slug] += 1
                slug = f"{base_slug}_{slug_counts[base_slug]}"
            else:
                slug_counts[base_slug] = 0
                slug = base_slug

            # Determine recipe unit
            recipe_unit = determine_recipe_unit(name, category)

            # Create ingredient
            ingredient = {
                'name': name,
                'slug': slug,
                'category': category,
                'recipe_unit': recipe_unit,
            }
            v2_data['ingredients'].append(ingredient)

            # Create generic variant
            variant = {
                'ingredient_slug': slug,
                'brand': 'Generic',
                'purchase_unit': recipe_unit,
                'purchase_quantity': 1.0,
            }
            v2_data['variants'].append(variant)

    # Build name->slug mapping for recipe conversion
    name_to_slug = {ing['name']: ing['slug'] for ing in v2_data['ingredients']}

    # Convert recipes
    print("Converting recipes...")
    for v1_recipe in v1_data.get('recipes', []):
        recipe = {
            'name': v1_recipe['name'],
            'category': v1_recipe['category'],
            'yield_quantity': v1_recipe['yield_quantity'],
            'yield_unit': v1_recipe['yield_unit'],
        }

        # Add optional fields
        if 'source' in v1_recipe:
            recipe['source'] = v1_recipe['source']
        if 'yield_description' in v1_recipe:
            recipe['yield_description'] = v1_recipe['yield_description']
        if 'estimated_time_minutes' in v1_recipe:
            recipe['estimated_time_minutes'] = v1_recipe['estimated_time_minutes']
        if 'notes' in v1_recipe:
            recipe['notes'] = v1_recipe['notes']

        # Convert ingredients to use slug
        recipe['ingredients'] = []
        for v1_ing in v1_recipe.get('ingredients', []):
            ing_name = v1_ing.get('ingredient_name') or v1_ing.get('name')

            # Apply name mapping
            if ing_name in name_mapping:
                mapped_name = name_mapping[ing_name]
            else:
                mapped_name = ing_name

            if mapped_name not in name_to_slug:
                print(f"  WARNING: Ingredient '{ing_name}' (mapped to '{mapped_name}') not found in ingredients list")
                continue

            recipe_ing = {
                'ingredient_slug': name_to_slug[mapped_name],
                'quantity': v1_ing['quantity'],
                'unit': v1_ing['unit'],
            }

            if 'notes' in v1_ing:
                recipe_ing['notes'] = v1_ing['notes']

            recipe['ingredients'].append(recipe_ing)

        v2_data['recipes'].append(recipe)

        # Create finished good if it's a discrete-count recipe
        yield_unit = recipe['yield_unit'].lower()
        if any(unit in yield_unit for unit in ['cookie', 'brownie', 'piece', 'bar', 'truffle', 'biscotti', 'cake', 'pie']):
            finished_good = {
                'name': recipe['name'],
                'recipe_name': recipe['name'],
                'category': recipe['category'],
                'yield_mode': 'DISCRETE_COUNT',
                'items_per_batch': int(recipe['yield_quantity']),
                'item_unit': recipe['yield_unit'],
            }

            if 'notes' in recipe:
                finished_good['notes'] = recipe['notes']

            v2_data['finished_goods'].append(finished_good)

    print(f"\nConversion complete!")
    print(f"  Ingredients: {len(v2_data['ingredients'])}")
    print(f"  Variants: {len(v2_data['variants'])}")
    print(f"  Unit Conversions: {len(v2_data['unit_conversions'])}")
    print(f"  Recipes: {len(v2_data['recipes'])}")
    print(f"  Finished Goods: {len(v2_data['finished_goods'])}")

    return v2_data


def main():
    """Main conversion function."""
    # Read v1.0 file
    print("Reading v1.0 file...")
    with open('examples/test_data_v2.json', 'r') as f:
        v1_data = json.load(f)

    # Convert to v2.0
    v2_data = convert_v1_to_v2(v1_data)

    # Write v2.0 file
    output_file = 'examples/test_data_v2_converted.json'
    print(f"\nWriting v2.0 file to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(v2_data, f, indent=2)

    print(f"\nConversion complete! File saved to: {output_file}")


if __name__ == '__main__':
    main()
