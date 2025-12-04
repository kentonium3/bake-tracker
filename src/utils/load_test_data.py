"""
Utility to load test data for development and testing.

This module provides functions to load sample data from JSON files
into the database using the new Ingredient/Variant architecture.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from src.services.database import get_session
from src.models import (
    Ingredient,
    Variant,
    Purchase,
    PantryItem,
    UnitConversion,
    Recipe,
    RecipeIngredient,
    FinishedGood,
    YieldMode,
    Bundle,
    Package,
    PackageBundle,
    Recipient,
    Event,
    EventRecipientPackage,
)


def load_test_data_from_json(json_file_path: str) -> Dict[str, int]:
    """
    Load test data from a JSON file into the database.

    Args:
        json_file_path: Path to JSON file containing test data

    Returns:
        Dictionary with counts of created entities
    """
    # Read JSON file
    with open(json_file_path, "r") as f:
        data = json.load(f)

    session = get_session()
    counts = {
        "ingredients": 0,
        "variants": 0,
        "purchases": 0,
        "pantry_items": 0,
        "unit_conversions": 0,
        "recipes": 0,
        "finished_goods": 0,
        "bundles": 0,
        "packages": 0,
        "recipients": 0,
        "events": 0,
    }

    # Track created entities for FK resolution
    ingredient_map = {}  # slug -> Ingredient
    variant_map = {}  # (ingredient_slug, brand) -> Variant
    recipe_map = {}  # name -> Recipe
    finished_good_map = {}  # name -> FinishedGood
    bundle_map = {}  # name -> Bundle
    package_map = {}  # name -> Package
    recipient_map = {}  # name -> Recipient

    try:
        # 1. Create Ingredients (generic)
        for ing_data in data.get("ingredients", []):
            ingredient = Ingredient(
                name=ing_data["name"],
                slug=ing_data["slug"],
                category=ing_data["category"],
                recipe_unit=ing_data.get("recipe_unit", "cup"),
                description=ing_data.get("description"),
                notes=ing_data.get("notes"),
                density_g_per_ml=ing_data.get("density_g_per_ml"),
            )
            session.add(ingredient)
            session.flush()  # Get ID
            ingredient_map[ing_data["slug"]] = ingredient
            counts["ingredients"] += 1

        # 2. Create Variants (brand-specific)
        for var_data in data.get("variants", []):
            ingredient = ingredient_map[var_data["ingredient_slug"]]
            variant = Variant(
                ingredient_id=ingredient.id,
                brand=var_data.get("brand"),
                package_size=var_data.get("package_size"),
                package_type=var_data.get("package_type"),
                purchase_unit=var_data["purchase_unit"],
                purchase_quantity=var_data["purchase_quantity"],
                preferred=var_data.get("preferred", False),
                notes=var_data.get("notes"),
            )
            session.add(variant)
            session.flush()
            variant_map[(var_data["ingredient_slug"], var_data.get("brand"))] = variant
            counts["variants"] += 1

        # 3. Create Purchases (price history)
        for purch_data in data.get("purchases", []):
            variant = variant_map[(purch_data["ingredient_slug"], purch_data["variant_brand"])]
            purchase = Purchase(
                variant_id=variant.id,
                purchase_date=datetime.fromisoformat(purch_data["purchased_at"]),
                unit_cost=purch_data["unit_cost"],
                quantity_purchased=purch_data["quantity_purchased"],
                total_cost=purch_data["total_cost"],
                supplier=purch_data.get("supplier"),
                notes=purch_data.get("notes"),
            )
            session.add(purchase)
            counts["purchases"] += 1

        # 4. Create PantryItems (actual inventory)
        for item_data in data.get("pantry_items", []):
            variant = variant_map[(item_data["ingredient_slug"], item_data["variant_brand"])]
            pantry_item = PantryItem(
                variant_id=variant.id,
                quantity=item_data["quantity"],
                purchase_date=datetime.strptime(item_data["purchase_date"], "%Y-%m-%d").date(),
                location=item_data.get("location", "Main Pantry"),
                notes=item_data.get("notes"),
            )
            session.add(pantry_item)
            counts["pantry_items"] += 1

        # 5. Create UnitConversions
        for conv_data in data.get("unit_conversions", []):
            ingredient = ingredient_map[conv_data["ingredient_slug"]]
            conversion = UnitConversion(
                ingredient_id=ingredient.id,
                from_unit=conv_data["from_unit"],
                from_quantity=conv_data["from_quantity"],
                to_unit=conv_data["to_unit"],
                to_quantity=conv_data["to_quantity"],
                notes=conv_data.get("notes"),
            )
            session.add(conversion)
            counts["unit_conversions"] += 1

        # 6. Create Recipes with RecipeIngredients
        for recipe_data in data.get("recipes", []):
            recipe = Recipe(
                name=recipe_data["name"],
                category=recipe_data["category"],
                source=recipe_data.get("source"),
                yield_quantity=recipe_data["yield_quantity"],
                yield_unit=recipe_data["yield_unit"],
                yield_description=recipe_data.get("yield_description"),
                estimated_time_minutes=recipe_data.get("estimated_time_minutes"),
                notes=recipe_data.get("notes"),
            )
            session.add(recipe)
            session.flush()

            # Add recipe ingredients
            for ing_data in recipe_data.get("ingredients", []):
                ingredient = ingredient_map[ing_data["ingredient_slug"]]
                recipe_ingredient = RecipeIngredient(
                    recipe_id=recipe.id,
                    ingredient_new_id=ingredient.id,  # Use new FK
                    quantity=ing_data["quantity"],
                    unit=ing_data["unit"],
                    notes=ing_data.get("notes"),
                )
                session.add(recipe_ingredient)

            recipe_map[recipe_data["name"]] = recipe
            counts["recipes"] += 1

        # 7. Create FinishedGoods
        for fg_data in data.get("finished_goods", []):
            recipe = recipe_map[fg_data["recipe_name"]]

            # Parse yield_mode enum
            yield_mode_str = fg_data.get("yield_mode", "DISCRETE_COUNT")
            yield_mode = YieldMode[yield_mode_str]

            finished_good = FinishedGood(
                name=fg_data["name"],
                recipe_id=recipe.id,
                category=fg_data.get("category"),
                yield_mode=yield_mode,
                items_per_batch=fg_data.get("items_per_batch"),
                item_unit=fg_data.get("item_unit"),
                batch_percentage=fg_data.get("batch_percentage"),
                portion_description=fg_data.get("portion_description"),
                notes=fg_data.get("notes"),
            )
            session.add(finished_good)
            session.flush()
            finished_good_map[fg_data["name"]] = finished_good
            counts["finished_goods"] += 1

        # 8. Create Bundles
        for bundle_data in data.get("bundles", []):
            finished_good = finished_good_map[bundle_data["finished_good_name"]]
            bundle = Bundle(
                name=bundle_data["name"],
                finished_good_id=finished_good.id,
                quantity=int(bundle_data["quantity"]),  # Bundle.quantity is Integer
                packaging_notes=bundle_data.get("notes"),
            )
            session.add(bundle)
            session.flush()
            bundle_map[bundle_data["name"]] = bundle
            counts["bundles"] += 1

        # 9. Create Packages with PackageBundles
        for pkg_data in data.get("packages", []):
            package = Package(
                name=pkg_data["name"],
                description=pkg_data.get("description"),
            )
            session.add(package)
            session.flush()

            # Add bundles to package
            for bundle_data in pkg_data.get("bundles", []):
                bundle = bundle_map[bundle_data["bundle_name"]]
                package_bundle = PackageBundle(
                    package_id=package.id,
                    bundle_id=bundle.id,
                    quantity=bundle_data["quantity"],
                )
                session.add(package_bundle)

            package_map[pkg_data["name"]] = package
            counts["packages"] += 1

        # 10. Create Recipients
        for recip_data in data.get("recipients", []):
            recipient = Recipient(
                name=recip_data["name"],
                household_name=recip_data.get("household_name"),
                address=recip_data.get("address"),
                notes=recip_data.get("notes"),
            )
            session.add(recipient)
            session.flush()
            recipient_map[recip_data["name"]] = recipient
            counts["recipients"] += 1

        # 11. Create Events with EventRecipientPackages
        for event_data in data.get("events", []):
            event = Event(
                name=event_data["name"],
                year=event_data["year"],
                event_date=datetime.strptime(event_data["event_date"], "%Y-%m-%d").date(),
                notes=event_data.get("notes"),
            )
            session.add(event)
            session.flush()

            # Add assignments
            for assign_data in event_data.get("assignments", []):
                recipient = recipient_map[assign_data["recipient_name"]]
                package = package_map[assign_data["package_name"]]
                assignment = EventRecipientPackage(
                    event_id=event.id,
                    recipient_id=recipient.id,
                    package_id=package.id,
                    quantity=assign_data["quantity"],
                    notes=assign_data.get("notes"),
                )
                session.add(assignment)

            counts["events"] += 1

        # Commit all changes
        session.commit()
        print("\n[OK] Test data loaded successfully!")
        return counts

    except Exception as e:
        session.rollback()
        print(f"\n[FAIL] Error loading test data: {e}")
        raise
    finally:
        session.close()


def print_load_summary(counts: Dict[str, int]) -> None:
    """
    Print a summary of loaded test data.

    Args:
        counts: Dictionary with entity counts
    """
    print("\n" + "=" * 60)
    print("TEST DATA LOADED")
    print("=" * 60)
    print(f"  Ingredients:      {counts['ingredients']}")
    print(f"  Variants:         {counts['variants']}")
    print(f"  Purchases:        {counts['purchases']}")
    print(f"  Pantry Items:     {counts['pantry_items']}")
    print(f"  Unit Conversions: {counts['unit_conversions']}")
    print(f"  Recipes:          {counts['recipes']}")
    print(f"  Finished Goods:   {counts['finished_goods']}")
    print(f"  Bundles:          {counts['bundles']}")
    print(f"  Packages:         {counts['packages']}")
    print(f"  Recipients:       {counts['recipients']}")
    print(f"  Events:           {counts['events']}")
    print("=" * 60)


if __name__ == "__main__":
    """Load test data when run as a script."""
    from src.services.database import initialize_app_database, reset_database

    print("Initializing database...")
    initialize_app_database()

    # Ask for confirmation before resetting
    response = input("\n[WARN]  This will RESET the database. Continue? (yes/no): ")
    if response.lower() != "yes":
        print("Cancelled.")
        exit(0)

    print("\nResetting database...")
    reset_database(confirm=True)
    initialize_app_database()

    # Load test data
    test_data_file = Path(__file__).parent.parent.parent / "test_data" / "sample_data.json"
    print(f"\nLoading test data from: {test_data_file}")

    counts = load_test_data_from_json(str(test_data_file))
    print_load_summary(counts)
