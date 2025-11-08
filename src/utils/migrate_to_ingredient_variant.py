"""
Migration utilities for converting from legacy Ingredient model to new Ingredient/Variant/Pantry architecture.

This module provides functions to:
1. Populate UUID columns for existing records
2. Migrate legacy Ingredient records to new Ingredient + Variant + PantryItem structure
3. Update RecipeIngredient foreign key references
4. Create UnitConversion records from legacy conversion_factor data
5. Create Purchase records from legacy unit_cost data
"""

import uuid
from datetime import date, datetime
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session

from src.models import (
    IngredientLegacy,
    Ingredient,
    Variant,
    PantryItem,
    Purchase,
    UnitConversion,
    RecipeIngredient,
)


def populate_uuids(session: Session, dry_run: bool = True) -> Dict[str, int]:
    """
    Populate UUID columns for all existing records that don't have them.

    Args:
        session: Database session
        dry_run: If True, don't commit changes (default: True)

    Returns:
        Dictionary with counts of records updated per model
    """
    counts = {}

    # List of all models that need UUIDs
    models = [
        ("IngredientLegacy", IngredientLegacy),
        ("Ingredient", Ingredient),
        ("Variant", Variant),
        ("PantryItem", PantryItem),
        ("Purchase", Purchase),
        ("UnitConversion", UnitConversion),
    ]

    for model_name, model_class in models:
        # Find records without UUIDs
        records_without_uuid = session.query(model_class).filter(
            (model_class.uuid == None) | (model_class.uuid == "")
        ).all()

        count = 0
        for record in records_without_uuid:
            record.uuid = str(uuid.uuid4())
            count += 1

        counts[model_name] = count

    if not dry_run:
        session.commit()
        print(f"✓ Populated UUIDs for {sum(counts.values())} records")
    else:
        session.rollback()
        print(f"[DRY RUN] Would populate UUIDs for {sum(counts.values())} records")

    return counts


def migrate_ingredient_to_new_schema(
    legacy_ingredient: IngredientLegacy,
    session: Session
) -> Tuple[Ingredient, Variant, PantryItem, UnitConversion, Purchase]:
    """
    Migrate a single legacy Ingredient to the new schema.

    Each legacy Ingredient becomes:
    - 1 Ingredient (generic ingredient)
    - 1 Variant (the specific brand/package currently in system, marked as preferred)
    - 1 PantryItem (current inventory, if quantity > 0)
    - 1 UnitConversion (purchase → recipe unit conversion)
    - 1 Purchase (if unit_cost > 0, to seed price history)

    Args:
        legacy_ingredient: Legacy Ingredient record
        session: Database session

    Returns:
        Tuple of (Ingredient, Variant, PantryItem, UnitConversion, Purchase)
        Note: PantryItem and Purchase may be None if not applicable
    """

    # 1. Create Ingredient (generic concept)
    ingredient = Ingredient(
        name=legacy_ingredient.name,
        slug=legacy_ingredient.name.lower().replace(" ", "_").replace("-", "_"),
        category=legacy_ingredient.category,
        recipe_unit="cup",  # Default, will be overridden if different
        description=None,
        notes=legacy_ingredient.notes,
        # Populate density if available
        density_g_per_ml=legacy_ingredient.density_g_per_cup / 236.588 if legacy_ingredient.density_g_per_cup else None,
    )
    session.add(ingredient)
    session.flush()  # Get the ID

    # 2. Create Variant (specific brand/package as preferred)
    variant = Variant(
        ingredient_id=ingredient.id,
        brand=legacy_ingredient.brand,
        package_size=f"{legacy_ingredient.purchase_quantity} {legacy_ingredient.purchase_unit}" if legacy_ingredient.purchase_quantity else None,
        package_type=legacy_ingredient.package_type,
        purchase_unit=legacy_ingredient.purchase_unit,
        purchase_quantity=legacy_ingredient.purchase_quantity,
        preferred=True,  # Mark as preferred since it's the only one
        notes=f"Migrated from legacy ingredient ID {legacy_ingredient.id}",
    )
    session.add(variant)
    session.flush()

    # 3. Create PantryItem (if quantity > 0)
    pantry_item = None
    if legacy_ingredient.quantity and legacy_ingredient.quantity > 0:
        pantry_item = PantryItem(
            variant_id=variant.id,
            quantity=legacy_ingredient.quantity,
            purchase_date=legacy_ingredient.last_updated.date() if isinstance(legacy_ingredient.last_updated, datetime) else date.today(),
            location="Main Pantry",  # Default location
            notes=f"Migrated from legacy ingredient ID {legacy_ingredient.id}",
        )
        session.add(pantry_item)

    # 4. Create UnitConversion (from legacy conversion_factor if available)
    # Note: Legacy model may not have conversion_factor, need to check schema
    unit_conversion = UnitConversion(
        ingredient_id=ingredient.id,
        from_unit=legacy_ingredient.purchase_unit,
        from_quantity=1.0,
        to_unit="cup",  # Default recipe unit
        to_quantity=1.0,  # Will need to be updated based on actual conversion data
        notes=f"Migrated from legacy ingredient ID {legacy_ingredient.id}",
    )
    session.add(unit_conversion)

    # 5. Create Purchase record (if unit_cost > 0)
    purchase = None
    if legacy_ingredient.unit_cost and legacy_ingredient.unit_cost > 0:
        purchase = Purchase(
            variant_id=variant.id,
            purchase_date=legacy_ingredient.last_updated.date() if isinstance(legacy_ingredient.last_updated, datetime) else date.today(),
            unit_cost=legacy_ingredient.unit_cost,
            quantity_purchased=legacy_ingredient.quantity if legacy_ingredient.quantity else 1.0,
            total_cost=legacy_ingredient.unit_cost * (legacy_ingredient.quantity if legacy_ingredient.quantity else 1.0),
            notes=f"Migrated from legacy ingredient ID {legacy_ingredient.id}",
        )
        session.add(purchase)

    return ingredient, variant, pantry_item, unit_conversion, purchase


def migrate_all_ingredients(session: Session, dry_run: bool = True) -> Dict[str, int]:
    """
    Migrate all legacy Ingredient records to new schema.

    Args:
        session: Database session
        dry_run: If True, don't commit changes (default: True)

    Returns:
        Dictionary with migration statistics
    """
    stats = {
        "total_legacy": 0,
        "migrated_ingredients": 0,
        "created_variants": 0,
        "created_pantry_items": 0,
        "created_conversions": 0,
        "created_purchases": 0,
        "errors": 0,
    }

    # Get all legacy ingredients
    legacy_ingredients = session.query(IngredientLegacy).all()
    stats["total_legacy"] = len(legacy_ingredients)

    for legacy_ing in legacy_ingredients:
        try:
            ingredient, variant, pantry_item, conversion, purchase = migrate_ingredient_to_new_schema(
                legacy_ing, session
            )

            stats["migrated_ingredients"] += 1
            stats["created_variants"] += 1
            stats["created_conversions"] += 1

            if pantry_item:
                stats["created_pantry_items"] += 1
            if purchase:
                stats["created_purchases"] += 1

        except Exception as e:
            stats["errors"] += 1
            print(f"✗ Error migrating ingredient '{legacy_ing.name}' (ID: {legacy_ing.id}): {e}")

    if not dry_run:
        session.commit()
        print(f"✓ Migration complete: {stats['migrated_ingredients']} ingredients migrated")
    else:
        session.rollback()
        print(f"[DRY RUN] Would migrate {stats['migrated_ingredients']} ingredients")

    return stats


def update_recipe_ingredient_references(session: Session, dry_run: bool = True) -> int:
    """
    Update RecipeIngredient records to point to new Ingredient table.

    For each RecipeIngredient with ingredient_id (legacy), find the corresponding
    new Ingredient and populate ingredient_new_id.

    Args:
        session: Database session
        dry_run: If True, don't commit changes (default: True)

    Returns:
        Number of RecipeIngredient records updated
    """
    updated_count = 0

    # Get all RecipeIngredients with legacy ingredient_id but no ingredient_new_id
    recipe_ingredients = session.query(RecipeIngredient).filter(
        RecipeIngredient.ingredient_id.isnot(None),
        RecipeIngredient.ingredient_new_id.is_(None)
    ).all()

    for recipe_ing in recipe_ingredients:
        # Find the new Ingredient that was migrated from this legacy ingredient
        # We stored the legacy ID in the Variant notes during migration
        # Better approach: match by name since we converted Product → Ingredient

        legacy_ing = session.query(IngredientLegacy).get(recipe_ing.ingredient_id)
        if not legacy_ing:
            continue

        # Find matching new Ingredient by name
        new_ing = session.query(Ingredient).filter(
            Ingredient.name == legacy_ing.name
        ).first()

        if new_ing:
            recipe_ing.ingredient_new_id = new_ing.id
            updated_count += 1

    if not dry_run:
        session.commit()
        print(f"✓ Updated {updated_count} RecipeIngredient references")
    else:
        session.rollback()
        print(f"[DRY RUN] Would update {updated_count} RecipeIngredient references")

    return updated_count


def run_full_migration(session: Session, dry_run: bool = True) -> None:
    """
    Run the complete migration process.

    Steps:
    1. Populate UUIDs for all existing records
    2. Migrate legacy Ingredients to new schema
    3. Update RecipeIngredient foreign key references
    4. Validate migration results

    Args:
        session: Database session
        dry_run: If True, don't commit changes (default: True)
    """
    print("=" * 60)
    print("INGREDIENT/VARIANT MIGRATION")
    print("=" * 60)
    print(f"Mode: {'DRY RUN (no changes will be saved)' if dry_run else 'LIVE (changes will be committed)'}")
    print()

    # Step 1: Populate UUIDs
    print("Step 1: Populating UUIDs...")
    uuid_counts = populate_uuids(session, dry_run)
    for model, count in uuid_counts.items():
        if count > 0:
            print(f"  - {model}: {count} records")
    print()

    # Step 2: Migrate ingredients
    print("Step 2: Migrating legacy ingredients...")
    migration_stats = migrate_all_ingredients(session, dry_run)
    print(f"  - Total legacy ingredients: {migration_stats['total_legacy']}")
    print(f"  - Migrated successfully: {migration_stats['migrated_ingredients']}")
    print(f"  - Variants created: {migration_stats['created_variants']}")
    print(f"  - Pantry items created: {migration_stats['created_pantry_items']}")
    print(f"  - Conversions created: {migration_stats['created_conversions']}")
    print(f"  - Purchases created: {migration_stats['created_purchases']}")
    if migration_stats['errors'] > 0:
        print(f"  - Errors: {migration_stats['errors']}")
    print()

    # Step 3: Update RecipeIngredient references
    print("Step 3: Updating RecipeIngredient references...")
    updated_count = update_recipe_ingredient_references(session, dry_run)
    print(f"  - Recipe ingredients updated: {updated_count}")
    print()

    # Summary
    print("=" * 60)
    if dry_run:
        print("DRY RUN COMPLETE - No changes were saved")
        print("Run with dry_run=False to apply changes")
    else:
        print("MIGRATION COMPLETE")
    print("=" * 60)
