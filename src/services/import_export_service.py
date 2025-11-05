"""
Import/Export Service - JSON-based data import and export for testing.

Provides minimal functionality to export and import ingredients and recipes
for testing purposes. No UI required - designed for programmatic use.
"""

import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from src.services import inventory_service, recipe_service, finished_good_service
from src.services.exceptions import ValidationError
from src.utils.constants import APP_NAME, APP_VERSION


# ============================================================================
# Result Classes
# ============================================================================


class ImportResult:
    """Result of an import operation."""

    def __init__(self):
        self.total_records = 0
        self.successful = 0
        self.skipped = 0
        self.failed = 0
        self.errors = []
        self.warnings = []

    def add_success(self):
        """Record a successful import."""
        self.successful += 1
        self.total_records += 1

    def add_skip(self, record_type: str, record_name: str, reason: str):
        """Record a skipped record."""
        self.skipped += 1
        self.total_records += 1
        self.warnings.append({
            "record_type": record_type,
            "record_name": record_name,
            "warning_type": "skipped",
            "message": reason
        })

    def add_error(self, record_type: str, record_name: str, error: str):
        """Record a failed import."""
        self.failed += 1
        self.total_records += 1
        self.errors.append({
            "record_type": record_type,
            "record_name": record_name,
            "error_type": "import_error",
            "message": error
        })

    def get_summary(self) -> str:
        """Get a summary string of the import results."""
        lines = [
            "=" * 60,
            "Import Summary",
            "=" * 60,
            f"Total Records: {self.total_records}",
            f"Successful:    {self.successful}",
            f"Skipped:       {self.skipped}",
            f"Failed:        {self.failed}",
        ]

        if self.errors:
            lines.append("\nErrors:")
            for error in self.errors:
                lines.append(f"  - {error['record_type']}: {error['record_name']}")
                lines.append(f"    {error['message']}")

        if self.warnings:
            lines.append("\nWarnings:")
            for warning in self.warnings:
                lines.append(f"  - {warning['record_type']}: {warning['record_name']}")
                lines.append(f"    {warning['message']}")

        lines.append("=" * 60)
        return "\n".join(lines)


class ExportResult:
    """Result of an export operation."""

    def __init__(self, file_path: str, record_count: int):
        self.file_path = file_path
        self.record_count = record_count
        self.success = True
        self.error = None

    def get_summary(self) -> str:
        """Get a summary string of the export results."""
        if self.success:
            return f"Exported {self.record_count} records to {self.file_path}"
        else:
            return f"Export failed: {self.error}"


# ============================================================================
# Export Functions
# ============================================================================


def export_ingredients_to_json(
    file_path: str,
    include_all: bool = True,
    category_filter: Optional[str] = None
) -> ExportResult:
    """
    Export ingredients to JSON file.

    Args:
        file_path: Path to output JSON file
        include_all: If True, export all ingredients (default)
        category_filter: Optional category to filter by

    Returns:
        ExportResult with export statistics
    """
    try:
        # Get ingredients
        ingredients = inventory_service.get_all_ingredients(category=category_filter)

        # Build export data
        export_data = {
            "version": "1.0",
            "export_date": datetime.utcnow().isoformat() + "Z",
            "source": f"{APP_NAME} v{APP_VERSION}",
            "ingredients": []
        }

        for ingredient in ingredients:
            ingredient_data = {
                "name": ingredient.name,
                "brand": ingredient.brand,
                "category": ingredient.category,
                "purchase_quantity": ingredient.purchase_quantity,
                "purchase_unit": ingredient.purchase_unit,
                "quantity": ingredient.quantity,
                "unit_cost": ingredient.unit_cost,
            }

            # Optional fields
            if ingredient.package_type:
                ingredient_data["package_type"] = ingredient.package_type

            if ingredient.density_g_per_cup:
                ingredient_data["density_g_per_cup"] = ingredient.density_g_per_cup

            if ingredient.notes:
                ingredient_data["notes"] = ingredient.notes

            export_data["ingredients"].append(ingredient_data)

        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return ExportResult(file_path, len(ingredients))

    except Exception as e:
        result = ExportResult(file_path, 0)
        result.success = False
        result.error = str(e)
        return result


def export_recipes_to_json(
    file_path: str,
    include_all: bool = True,
    category_filter: Optional[str] = None
) -> ExportResult:
    """
    Export recipes to JSON file.

    Args:
        file_path: Path to output JSON file
        include_all: If True, export all recipes (default)
        category_filter: Optional category to filter by

    Returns:
        ExportResult with export statistics
    """
    try:
        # Get recipes
        recipes = recipe_service.get_all_recipes(category=category_filter)

        # Build export data
        export_data = {
            "version": "1.0",
            "export_date": datetime.utcnow().isoformat() + "Z",
            "source": f"{APP_NAME} v{APP_VERSION}",
            "recipes": []
        }

        for recipe in recipes:
            recipe_data = {
                "name": recipe.name,
                "category": recipe.category,
                "yield_quantity": recipe.yield_quantity,
                "yield_unit": recipe.yield_unit,
            }

            # Optional fields
            if recipe.source:
                recipe_data["source"] = recipe.source

            if recipe.yield_description:
                recipe_data["yield_description"] = recipe.yield_description

            if recipe.estimated_time_minutes:
                recipe_data["estimated_time_minutes"] = recipe.estimated_time_minutes

            if recipe.notes:
                recipe_data["notes"] = recipe.notes

            # Recipe ingredients
            recipe_data["ingredients"] = []
            for ri in recipe.recipe_ingredients:
                ingredient_data = {
                    "ingredient_name": ri.ingredient.name,
                    "quantity": ri.quantity,
                    "unit": ri.unit,
                }

                # Include brand for disambiguation
                if ri.ingredient.brand:
                    ingredient_data["ingredient_brand"] = ri.ingredient.brand

                if ri.notes:
                    ingredient_data["notes"] = ri.notes

                recipe_data["ingredients"].append(ingredient_data)

            export_data["recipes"].append(recipe_data)

        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return ExportResult(file_path, len(recipes))

    except Exception as e:
        result = ExportResult(file_path, 0)
        result.success = False
        result.error = str(e)
        return result


def export_finished_goods_to_json(
    file_path: str,
    include_all: bool = True,
    category_filter: Optional[str] = None
) -> ExportResult:
    """
    Export finished goods to JSON file.

    Args:
        file_path: Path to output JSON file
        include_all: If True, export all finished goods (default)
        category_filter: Optional category to filter by

    Returns:
        ExportResult with export statistics
    """
    try:
        # Get finished goods
        finished_goods = finished_good_service.get_all_finished_goods(category=category_filter)

        # Build export data
        export_data = {
            "version": "1.0",
            "export_date": datetime.utcnow().isoformat() + "Z",
            "source": f"{APP_NAME} v{APP_VERSION}",
            "finished_goods": []
        }

        for fg in finished_goods:
            fg_data = {
                "name": fg.name,
                "recipe_name": fg.recipe.name,
                "yield_mode": fg.yield_mode.value,
            }

            # Optional fields
            if fg.category:
                fg_data["category"] = fg.category

            if fg.yield_mode.value == "discrete_count":
                fg_data["items_per_batch"] = fg.items_per_batch
                fg_data["item_unit"] = fg.item_unit
            elif fg.yield_mode.value == "batch_portion":
                fg_data["batch_percentage"] = fg.batch_percentage
                if fg.portion_description:
                    fg_data["portion_description"] = fg.portion_description

            if fg.notes:
                fg_data["notes"] = fg.notes

            export_data["finished_goods"].append(fg_data)

        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return ExportResult(file_path, len(finished_goods))

    except Exception as e:
        result = ExportResult(file_path, 0)
        result.success = False
        result.error = str(e)
        return result


def export_bundles_to_json(
    file_path: str,
    include_all: bool = True
) -> ExportResult:
    """
    Export bundles to JSON file.

    Args:
        file_path: Path to output JSON file
        include_all: If True, export all bundles (default)

    Returns:
        ExportResult with export statistics
    """
    try:
        # Get bundles
        bundles = finished_good_service.get_all_bundles()

        # Build export data
        export_data = {
            "version": "1.0",
            "export_date": datetime.utcnow().isoformat() + "Z",
            "source": f"{APP_NAME} v{APP_VERSION}",
            "bundles": []
        }

        for bundle in bundles:
            bundle_data = {
                "name": bundle.name,
                "finished_good_name": bundle.finished_good.name,
                "quantity": bundle.quantity,
            }

            # Optional fields
            if bundle.packaging_notes:
                bundle_data["packaging_notes"] = bundle.packaging_notes

            export_data["bundles"].append(bundle_data)

        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return ExportResult(file_path, len(bundles))

    except Exception as e:
        result = ExportResult(file_path, 0)
        result.success = False
        result.error = str(e)
        return result


def export_all_to_json(file_path: str) -> ExportResult:
    """
    Export all data (ingredients, recipes, finished goods, bundles) to a single JSON file.

    Args:
        file_path: Path to output JSON file

    Returns:
        ExportResult with export statistics
    """
    try:
        # Get all data
        ingredients = inventory_service.get_all_ingredients()
        recipes = recipe_service.get_all_recipes()
        finished_goods = finished_good_service.get_all_finished_goods()
        bundles = finished_good_service.get_all_bundles()

        # Build combined export data
        export_data = {
            "version": "1.0",
            "export_date": datetime.utcnow().isoformat() + "Z",
            "source": f"{APP_NAME} v{APP_VERSION}",
            "ingredients": [],
            "recipes": [],
            "finished_goods": [],
            "bundles": []
        }

        # Add ingredients
        for ingredient in ingredients:
            ingredient_data = {
                "name": ingredient.name,
                "brand": ingredient.brand,
                "category": ingredient.category,
                "purchase_quantity": ingredient.purchase_quantity,
                "purchase_unit": ingredient.purchase_unit,
                "quantity": ingredient.quantity,
                "unit_cost": ingredient.unit_cost,
            }

            if ingredient.package_type:
                ingredient_data["package_type"] = ingredient.package_type
            if ingredient.density_g_per_cup:
                ingredient_data["density_g_per_cup"] = ingredient.density_g_per_cup
            if ingredient.notes:
                ingredient_data["notes"] = ingredient.notes

            export_data["ingredients"].append(ingredient_data)

        # Add recipes
        for recipe in recipes:
            recipe_data = {
                "name": recipe.name,
                "category": recipe.category,
                "yield_quantity": recipe.yield_quantity,
                "yield_unit": recipe.yield_unit,
            }

            if recipe.source:
                recipe_data["source"] = recipe.source
            if recipe.yield_description:
                recipe_data["yield_description"] = recipe.yield_description
            if recipe.estimated_time_minutes:
                recipe_data["estimated_time_minutes"] = recipe.estimated_time_minutes
            if recipe.notes:
                recipe_data["notes"] = recipe.notes

            recipe_data["ingredients"] = []
            for ri in recipe.recipe_ingredients:
                ingredient_data = {
                    "ingredient_name": ri.ingredient.name,
                    "quantity": ri.quantity,
                    "unit": ri.unit,
                }
                if ri.ingredient.brand:
                    ingredient_data["ingredient_brand"] = ri.ingredient.brand
                if ri.notes:
                    ingredient_data["notes"] = ri.notes

                recipe_data["ingredients"].append(ingredient_data)

            export_data["recipes"].append(recipe_data)

        # Add finished goods
        for fg in finished_goods:
            fg_data = {
                "name": fg.name,
                "recipe_name": fg.recipe.name,
                "yield_mode": fg.yield_mode.value,
            }

            if fg.category:
                fg_data["category"] = fg.category
            if fg.yield_mode.value == "discrete_count":
                fg_data["items_per_batch"] = fg.items_per_batch
                fg_data["item_unit"] = fg.item_unit
            elif fg.yield_mode.value == "batch_portion":
                fg_data["batch_percentage"] = fg.batch_percentage
                if fg.portion_description:
                    fg_data["portion_description"] = fg.portion_description
            if fg.notes:
                fg_data["notes"] = fg.notes

            export_data["finished_goods"].append(fg_data)

        # Add bundles
        for bundle in bundles:
            bundle_data = {
                "name": bundle.name,
                "finished_good_name": bundle.finished_good.name,
                "quantity": bundle.quantity,
            }
            if bundle.packaging_notes:
                bundle_data["packaging_notes"] = bundle.packaging_notes

            export_data["bundles"].append(bundle_data)

        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        total_records = len(ingredients) + len(recipes) + len(finished_goods) + len(bundles)
        return ExportResult(file_path, total_records)

    except Exception as e:
        result = ExportResult(file_path, 0)
        result.success = False
        result.error = str(e)
        return result


# ============================================================================
# Import Functions
# ============================================================================


def import_ingredients_from_json(
    file_path: str,
    skip_duplicates: bool = True
) -> ImportResult:
    """
    Import ingredients from JSON file.

    Args:
        file_path: Path to JSON file
        skip_duplicates: If True, skip ingredients that already exist (default)

    Returns:
        ImportResult with import statistics
    """
    result = ImportResult()

    try:
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validate structure
        if "ingredients" not in data:
            result.add_error("file", file_path, "Missing 'ingredients' key in JSON")
            return result

        ingredients_data = data["ingredients"]

        # Import each ingredient
        for idx, ingredient_data in enumerate(ingredients_data):
            try:
                name = ingredient_data.get("name", "")
                brand = ingredient_data.get("brand", "")

                if not name:
                    result.add_error("ingredient", f"Record {idx+1}", "Missing name")
                    continue

                # Check for duplicate
                if skip_duplicates:
                    existing = inventory_service.get_all_ingredients(name_search=name)
                    # Check if exact match (name + brand)
                    for existing_ing in existing:
                        if existing_ing.name == name and existing_ing.brand == brand:
                            result.add_skip(
                                "ingredient",
                                name,
                                f"Already exists (brand: {brand or 'none'})"
                            )
                            continue

                # Create ingredient
                inventory_service.create_ingredient(ingredient_data)
                result.add_success()

            except ValidationError as e:
                result.add_error("ingredient", name, f"Validation error: {e}")
            except Exception as e:
                result.add_error("ingredient", name, str(e))

        return result

    except json.JSONDecodeError as e:
        result.add_error("file", file_path, f"Invalid JSON: {e}")
        return result
    except Exception as e:
        result.add_error("file", file_path, f"Failed to read file: {e}")
        return result


def import_recipes_from_json(
    file_path: str,
    skip_duplicates: bool = True,
    skip_missing_ingredients: bool = True
) -> ImportResult:
    """
    Import recipes from JSON file.

    Args:
        file_path: Path to JSON file
        skip_duplicates: If True, skip recipes that already exist (default)
        skip_missing_ingredients: If True, skip recipes with missing ingredients (default)

    Returns:
        ImportResult with import statistics
    """
    result = ImportResult()

    try:
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validate structure
        if "recipes" not in data:
            result.add_error("file", file_path, "Missing 'recipes' key in JSON")
            return result

        recipes_data = data["recipes"]

        # Import each recipe
        for idx, recipe_data in enumerate(recipes_data):
            try:
                name = recipe_data.get("name", "")

                if not name:
                    result.add_error("recipe", f"Record {idx+1}", "Missing name")
                    continue

                # Check for duplicate
                if skip_duplicates:
                    existing = recipe_service.get_all_recipes(name_search=name)
                    for existing_recipe in existing:
                        if existing_recipe.name == name:
                            result.add_skip("recipe", name, "Already exists")
                            continue

                # Validate ingredients exist
                recipe_ingredients = recipe_data.get("ingredients", [])
                if not recipe_ingredients:
                    result.add_error("recipe", name, "No ingredients specified")
                    continue

                # Check each ingredient exists
                missing_ingredients = []
                validated_ingredients = []

                for ri_data in recipe_ingredients:
                    ing_name = ri_data.get("ingredient_name", "")
                    ing_brand = ri_data.get("ingredient_brand", "")

                    # Find ingredient
                    candidates = inventory_service.get_all_ingredients(name_search=ing_name)
                    found = None

                    # Try exact match with brand first
                    if ing_brand:
                        for candidate in candidates:
                            if candidate.name == ing_name and candidate.brand == ing_brand:
                                found = candidate
                                break

                    # Try exact match without brand
                    if not found:
                        for candidate in candidates:
                            if candidate.name == ing_name:
                                found = candidate
                                break

                    if not found:
                        missing_ingredients.append(f"{ing_name} ({ing_brand})" if ing_brand else ing_name)
                    else:
                        # Build validated ingredient data
                        validated_ingredients.append({
                            "ingredient_id": found.id,
                            "quantity": ri_data.get("quantity"),
                            "unit": ri_data.get("unit"),
                            "notes": ri_data.get("notes")
                        })

                if missing_ingredients:
                    if skip_missing_ingredients:
                        result.add_skip(
                            "recipe",
                            name,
                            f"Missing ingredients: {', '.join(missing_ingredients)}"
                        )
                        continue
                    else:
                        result.add_error(
                            "recipe",
                            name,
                            f"Missing ingredients: {', '.join(missing_ingredients)}"
                        )
                        continue

                # Create recipe
                recipe_base_data = {
                    "name": recipe_data["name"],
                    "category": recipe_data["category"],
                    "yield_quantity": recipe_data["yield_quantity"],
                    "yield_unit": recipe_data["yield_unit"],
                }

                # Optional fields
                if "source" in recipe_data:
                    recipe_base_data["source"] = recipe_data["source"]
                if "yield_description" in recipe_data:
                    recipe_base_data["yield_description"] = recipe_data["yield_description"]
                if "estimated_time_minutes" in recipe_data:
                    recipe_base_data["estimated_time_minutes"] = recipe_data["estimated_time_minutes"]
                if "notes" in recipe_data:
                    recipe_base_data["notes"] = recipe_data["notes"]

                recipe_service.create_recipe(recipe_base_data, validated_ingredients)
                result.add_success()

            except ValidationError as e:
                result.add_error("recipe", name, f"Validation error: {e}")
            except Exception as e:
                result.add_error("recipe", name, str(e))

        return result

    except json.JSONDecodeError as e:
        result.add_error("file", file_path, f"Invalid JSON: {e}")
        return result
    except Exception as e:
        result.add_error("file", file_path, f"Failed to read file: {e}")
        return result


def import_finished_goods_from_json(
    file_path: str,
    skip_duplicates: bool = True,
    skip_missing_recipes: bool = True
) -> ImportResult:
    """
    Import finished goods from JSON file.

    Args:
        file_path: Path to JSON file
        skip_duplicates: If True, skip finished goods that already exist (default)
        skip_missing_recipes: If True, skip finished goods with missing recipes (default)

    Returns:
        ImportResult with import statistics
    """
    result = ImportResult()

    try:
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validate structure
        if "finished_goods" not in data:
            result.add_error("file", file_path, "Missing 'finished_goods' key in JSON")
            return result

        finished_goods_data = data["finished_goods"]

        # Import each finished good
        for idx, fg_data in enumerate(finished_goods_data):
            try:
                name = fg_data.get("name", "")

                if not name:
                    result.add_error("finished_good", f"Record {idx+1}", "Missing name")
                    continue

                # Check for duplicate
                if skip_duplicates:
                    existing = finished_good_service.get_all_finished_goods(name_search=name)
                    for existing_fg in existing:
                        if existing_fg.name == name:
                            result.add_skip("finished_good", name, "Already exists")
                            continue

                # Find recipe
                recipe_name = fg_data.get("recipe_name", "")
                if not recipe_name:
                    result.add_error("finished_good", name, "Missing recipe_name")
                    continue

                recipes = recipe_service.get_all_recipes(name_search=recipe_name)
                recipe = None
                for r in recipes:
                    if r.name == recipe_name:
                        recipe = r
                        break

                if not recipe:
                    if skip_missing_recipes:
                        result.add_skip("finished_good", name, f"Recipe not found: {recipe_name}")
                        continue
                    else:
                        result.add_error("finished_good", name, f"Recipe not found: {recipe_name}")
                        continue

                # Build finished good data
                fg_create_data = {
                    "name": name,
                    "recipe_id": recipe.id,
                    "yield_mode": fg_data.get("yield_mode", "discrete_count"),
                }

                # Optional fields
                if "category" in fg_data:
                    fg_create_data["category"] = fg_data["category"]
                if "items_per_batch" in fg_data:
                    fg_create_data["items_per_batch"] = fg_data["items_per_batch"]
                if "item_unit" in fg_data:
                    fg_create_data["item_unit"] = fg_data["item_unit"]
                if "batch_percentage" in fg_data:
                    fg_create_data["batch_percentage"] = fg_data["batch_percentage"]
                if "portion_description" in fg_data:
                    fg_create_data["portion_description"] = fg_data["portion_description"]
                if "notes" in fg_data:
                    fg_create_data["notes"] = fg_data["notes"]

                # Create finished good
                finished_good_service.create_finished_good(fg_create_data)
                result.add_success()

            except ValidationError as e:
                result.add_error("finished_good", name, f"Validation error: {e}")
            except Exception as e:
                result.add_error("finished_good", name, str(e))

        return result

    except json.JSONDecodeError as e:
        result.add_error("file", file_path, f"Invalid JSON: {e}")
        return result
    except Exception as e:
        result.add_error("file", file_path, f"Failed to read file: {e}")
        return result


def import_bundles_from_json(
    file_path: str,
    skip_duplicates: bool = True,
    skip_missing_finished_goods: bool = True
) -> ImportResult:
    """
    Import bundles from JSON file.

    Args:
        file_path: Path to JSON file
        skip_duplicates: If True, skip bundles that already exist (default)
        skip_missing_finished_goods: If True, skip bundles with missing finished goods (default)

    Returns:
        ImportResult with import statistics
    """
    result = ImportResult()

    try:
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validate structure
        if "bundles" not in data:
            result.add_error("file", file_path, "Missing 'bundles' key in JSON")
            return result

        bundles_data = data["bundles"]

        # Import each bundle
        for idx, bundle_data in enumerate(bundles_data):
            try:
                name = bundle_data.get("name", "")

                if not name:
                    result.add_error("bundle", f"Record {idx+1}", "Missing name")
                    continue

                # Check for duplicate
                if skip_duplicates:
                    existing = finished_good_service.get_all_bundles(name_search=name)
                    for existing_bundle in existing:
                        if existing_bundle.name == name:
                            result.add_skip("bundle", name, "Already exists")
                            continue

                # Find finished good
                fg_name = bundle_data.get("finished_good_name", "")
                if not fg_name:
                    result.add_error("bundle", name, "Missing finished_good_name")
                    continue

                finished_goods = finished_good_service.get_all_finished_goods(name_search=fg_name)
                finished_good = None
                for fg in finished_goods:
                    if fg.name == fg_name:
                        finished_good = fg
                        break

                if not finished_good:
                    if skip_missing_finished_goods:
                        result.add_skip("bundle", name, f"Finished good not found: {fg_name}")
                        continue
                    else:
                        result.add_error("bundle", name, f"Finished good not found: {fg_name}")
                        continue

                # Build bundle data
                bundle_create_data = {
                    "name": name,
                    "finished_good_id": finished_good.id,
                    "quantity": bundle_data.get("quantity", 1),
                }

                # Optional fields
                if "packaging_notes" in bundle_data:
                    bundle_create_data["packaging_notes"] = bundle_data["packaging_notes"]

                # Create bundle
                finished_good_service.create_bundle(bundle_create_data)
                result.add_success()

            except ValidationError as e:
                result.add_error("bundle", name, f"Validation error: {e}")
            except Exception as e:
                result.add_error("bundle", name, str(e))

        return result

    except json.JSONDecodeError as e:
        result.add_error("file", file_path, f"Invalid JSON: {e}")
        return result
    except Exception as e:
        result.add_error("file", file_path, f"Failed to read file: {e}")
        return result


def import_all_from_json(
    file_path: str,
    skip_duplicates: bool = True
) -> Tuple[ImportResult, ImportResult, ImportResult, ImportResult]:
    """
    Import all data (ingredients, recipes, finished goods, bundles) from a single JSON file.

    Imports in proper dependency order:
    1. Ingredients (no dependencies)
    2. Recipes (depend on ingredients)
    3. Finished goods (depend on recipes)
    4. Bundles (depend on finished goods)

    Args:
        file_path: Path to JSON file
        skip_duplicates: If True, skip duplicates (default)

    Returns:
        Tuple of (ingredient_result, recipe_result, finished_good_result, bundle_result)
    """
    import tempfile

    try:
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Import ingredients first
        ingredient_result = ImportResult()
        if "ingredients" in data:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
                json.dump({"ingredients": data["ingredients"]}, tmp)
                tmp_path = tmp.name

            ingredient_result = import_ingredients_from_json(tmp_path, skip_duplicates)
            Path(tmp_path).unlink()

        # Import recipes second
        recipe_result = ImportResult()
        if "recipes" in data:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
                json.dump({"recipes": data["recipes"]}, tmp)
                tmp_path = tmp.name

            recipe_result = import_recipes_from_json(tmp_path, skip_duplicates)
            Path(tmp_path).unlink()

        # Import finished goods third
        finished_good_result = ImportResult()
        if "finished_goods" in data:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
                json.dump({"finished_goods": data["finished_goods"]}, tmp)
                tmp_path = tmp.name

            finished_good_result = import_finished_goods_from_json(tmp_path, skip_duplicates)
            Path(tmp_path).unlink()

        # Import bundles fourth
        bundle_result = ImportResult()
        if "bundles" in data:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
                json.dump({"bundles": data["bundles"]}, tmp)
                tmp_path = tmp.name

            bundle_result = import_bundles_from_json(tmp_path, skip_duplicates)
            Path(tmp_path).unlink()

        return ingredient_result, recipe_result, finished_good_result, bundle_result

    except Exception as e:
        ingredient_result = ImportResult()
        recipe_result = ImportResult()
        finished_good_result = ImportResult()
        bundle_result = ImportResult()
        ingredient_result.add_error("file", file_path, str(e))
        return ingredient_result, recipe_result, finished_good_result, bundle_result
