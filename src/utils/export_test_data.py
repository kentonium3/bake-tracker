"""
Export utility for the new Ingredient/Variant architecture.

Exports database to JSON format compatible with load_test_data.py,
allowing manual test data to be captured and reused.
"""

import json
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional

from src.services.database import get_session
from src.models import (
    Ingredient,
    Variant,
    Purchase,
    PantryItem,
    UnitConversion,
    Recipe,
    FinishedGood,
    Bundle,
    Package,
    Recipient,
    Event,
)


def export_database_to_json(output_file: str) -> Dict[str, int]:
    """
    Export current database state to JSON file.

    Exports in the same format as sample_data.json, suitable for
    reloading with load_test_data.py.

    Args:
        output_file: Path to output JSON file

    Returns:
        Dictionary with counts of exported entities
    """
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

    try:
        # Build export data structure
        export_data = {}

        # 1. Export Ingredients (generic)
        ingredients = session.query(Ingredient).order_by(Ingredient.category, Ingredient.name).all()
        export_data["ingredients"] = []

        for ingredient in ingredients:
            ing_data = {
                "name": ingredient.name,
                "slug": ingredient.slug,
                "category": ingredient.category,
                "recipe_unit": ingredient.recipe_unit,
            }

            # Optional fields
            if ingredient.description:
                ing_data["description"] = ingredient.description
            if ingredient.notes:
                ing_data["notes"] = ingredient.notes
            # 4-field density model
            if ingredient.density_volume_value is not None:
                ing_data["density_volume_value"] = ingredient.density_volume_value
            if ingredient.density_volume_unit:
                ing_data["density_volume_unit"] = ingredient.density_volume_unit
            if ingredient.density_weight_value is not None:
                ing_data["density_weight_value"] = ingredient.density_weight_value
            if ingredient.density_weight_unit:
                ing_data["density_weight_unit"] = ingredient.density_weight_unit

            export_data["ingredients"].append(ing_data)
            counts["ingredients"] += 1

        # 2. Export Variants (brand-specific)
        variants = (
            session.query(Variant).join(Ingredient).order_by(Ingredient.name, Variant.brand).all()
        )
        export_data["variants"] = []

        for variant in variants:
            var_data = {
                "ingredient_slug": variant.ingredient.slug,
                "brand": variant.brand,
                "package_size": variant.package_size,
                "package_type": variant.package_type,
                "purchase_unit": variant.purchase_unit,
                "purchase_quantity": variant.purchase_quantity,
                "preferred": variant.preferred,
            }

            if variant.notes:
                var_data["notes"] = variant.notes

            export_data["variants"].append(var_data)
            counts["variants"] += 1

        # 3. Export Purchases (price history)
        purchases = (
            session.query(Purchase)
            .join(Variant)
            .join(Ingredient)
            .order_by(Ingredient.name, Purchase.purchase_date)
            .all()
        )
        export_data["purchases"] = []

        for purchase in purchases:
            purch_data = {
                "ingredient_slug": purchase.variant.ingredient.slug,
                "variant_brand": purchase.variant.brand,
                "purchased_at": purchase.purchase_date.isoformat(),
                "unit_cost": purchase.unit_cost,
                "quantity_purchased": purchase.quantity_purchased,
                "total_cost": purchase.total_cost,
            }

            if purchase.supplier:
                purch_data["supplier"] = purchase.supplier
            if purchase.notes:
                purch_data["notes"] = purchase.notes

            export_data["purchases"].append(purch_data)
            counts["purchases"] += 1

        # 4. Export PantryItems (actual inventory)
        pantry_items = (
            session.query(PantryItem)
            .join(Variant)
            .join(Ingredient)
            .order_by(Ingredient.name, PantryItem.purchase_date)
            .all()
        )
        export_data["pantry_items"] = []

        for item in pantry_items:
            item_data = {
                "ingredient_slug": item.variant.ingredient.slug,
                "variant_brand": item.variant.brand,
                "quantity": item.quantity,
                "purchase_date": item.purchase_date.strftime("%Y-%m-%d"),
                "location": item.location,
            }

            if item.notes:
                item_data["notes"] = item.notes

            export_data["pantry_items"].append(item_data)
            counts["pantry_items"] += 1

        # 5. Export UnitConversions
        conversions = (
            session.query(UnitConversion)
            .join(Ingredient)
            .order_by(Ingredient.name, UnitConversion.from_unit, UnitConversion.to_unit)
            .all()
        )
        export_data["unit_conversions"] = []

        for conv in conversions:
            conv_data = {
                "ingredient_slug": conv.ingredient.slug,
                "from_unit": conv.from_unit,
                "from_quantity": conv.from_quantity,
                "to_unit": conv.to_unit,
                "to_quantity": conv.to_quantity,
            }

            if conv.notes:
                conv_data["notes"] = conv.notes

            export_data["unit_conversions"].append(conv_data)
            counts["unit_conversions"] += 1

        # 6. Export Recipes with RecipeIngredients
        recipes = session.query(Recipe).order_by(Recipe.category, Recipe.name).all()
        export_data["recipes"] = []

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

            # Recipe ingredients (use NEW FK to Ingredient)
            recipe_data["ingredients"] = []
            for ri in recipe.recipe_ingredients:
                # Only export if using new ingredient FK
                if ri.ingredient_new_id:
                    ingredient = ri.active_ingredient
                    ri_data = {
                        "ingredient_slug": ingredient.slug,
                        "quantity": ri.quantity,
                        "unit": ri.unit,
                    }

                    if ri.notes:
                        ri_data["notes"] = ri.notes

                    recipe_data["ingredients"].append(ri_data)

            export_data["recipes"].append(recipe_data)
            counts["recipes"] += 1

        # 7. Export FinishedGoods
        finished_goods = session.query(FinishedGood).order_by(FinishedGood.name).all()
        export_data["finished_goods"] = []

        for fg in finished_goods:
            fg_data = {
                "name": fg.name,
                "recipe_name": fg.recipe.name,
                "yield_mode": fg.yield_mode.name,  # Use enum name (DISCRETE_COUNT, etc.)
            }

            # Optional fields
            if fg.category:
                fg_data["category"] = fg.category
            if fg.items_per_batch:
                fg_data["items_per_batch"] = fg.items_per_batch
            if fg.item_unit:
                fg_data["item_unit"] = fg.item_unit
            if fg.batch_percentage:
                fg_data["batch_percentage"] = fg.batch_percentage
            if fg.portion_description:
                fg_data["portion_description"] = fg.portion_description
            if fg.notes:
                fg_data["notes"] = fg.notes

            export_data["finished_goods"].append(fg_data)
            counts["finished_goods"] += 1

        # 8. Export Bundles
        bundles = session.query(Bundle).order_by(Bundle.name).all()
        export_data["bundles"] = []

        for bundle in bundles:
            bundle_data = {
                "name": bundle.name,
                "finished_good_name": bundle.finished_good.name,
                "quantity": bundle.quantity,
            }

            if bundle.packaging_notes:
                bundle_data["notes"] = bundle.packaging_notes

            export_data["bundles"].append(bundle_data)
            counts["bundles"] += 1

        # 9. Export Packages with PackageBundles
        packages = session.query(Package).order_by(Package.name).all()
        export_data["packages"] = []

        for package in packages:
            pkg_data = {
                "name": package.name,
            }

            if package.description:
                pkg_data["description"] = package.description

            # Package bundles
            pkg_data["bundles"] = []
            for pb in package.package_bundles:
                bundle_item = {
                    "bundle_name": pb.bundle.name,
                    "quantity": pb.quantity,
                }
                pkg_data["bundles"].append(bundle_item)

            export_data["packages"].append(pkg_data)
            counts["packages"] += 1

        # 10. Export Recipients
        recipients = session.query(Recipient).order_by(Recipient.name).all()
        export_data["recipients"] = []

        for recipient in recipients:
            recip_data = {
                "name": recipient.name,
            }

            if recipient.household_name:
                recip_data["household_name"] = recipient.household_name
            if recipient.address:
                recip_data["address"] = recipient.address
            if recipient.notes:
                recip_data["notes"] = recipient.notes

            export_data["recipients"].append(recip_data)
            counts["recipients"] += 1

        # 11. Export Events with EventRecipientPackages
        events = session.query(Event).order_by(Event.year, Event.event_date).all()
        export_data["events"] = []

        for event in events:
            event_data = {
                "name": event.name,
                "year": event.year,
                "event_date": event.event_date.strftime("%Y-%m-%d"),
            }

            if event.notes:
                event_data["notes"] = event.notes

            # Event assignments
            event_data["assignments"] = []
            for assignment in event.event_recipient_packages:
                assign_data = {
                    "recipient_name": assignment.recipient.name,
                    "package_name": assignment.package.name,
                    "quantity": assignment.quantity,
                }

                if assignment.notes:
                    assign_data["notes"] = assignment.notes

                event_data["assignments"].append(assign_data)

            export_data["events"].append(event_data)
            counts["events"] += 1

        # Write to file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        print(f"\n[OK] Database exported to {output_file}")
        return counts

    except Exception as e:
        print(f"\n[FAIL] Error exporting data: {e}")
        raise
    finally:
        session.close()


def print_export_summary(counts: Dict[str, int]) -> None:
    """
    Print a summary of exported data.

    Args:
        counts: Dictionary with entity counts
    """
    print("\n" + "=" * 60)
    print("DATABASE EXPORTED")
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
    """Export current database when run as a script."""
    import sys

    # Add parent directory to path for imports
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from src.services.database import initialize_app_database

    print("Initializing database...")
    initialize_app_database()

    # Default output file
    output_file = Path(__file__).parent.parent.parent / "test_data" / "exported_data.json"

    # Allow custom output path
    if len(sys.argv) > 1:
        output_file = Path(sys.argv[1])

    print(f"\nExporting database to: {output_file}")

    counts = export_database_to_json(str(output_file))
    print_export_summary(counts)
