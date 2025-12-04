"""Integration tests for ingredient -> variant -> pantry workflow.

Tests the complete inventory management flow across multiple services.
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta

from src.services import ingredient_service, variant_service, pantry_service
from src.services.exceptions import IngredientNotFoundBySlug, VariantNotFound, ValidationError


def test_complete_inventory_workflow(test_db):
    """Test: Create ingredient -> Create variant -> Add to pantry -> Query inventory."""

    # 1. Create ingredient
    ingredient_data = {
        "name": "All-Purpose Flour",
        "category": "Flour",
        "recipe_unit": "cup",
        "density_g_per_ml": 0.4793,
    }
    ingredient = ingredient_service.create_ingredient(ingredient_data)
    assert ingredient.slug == "all_purpose_flour"
    assert ingredient.name == "All-Purpose Flour"
    assert ingredient.recipe_unit == "cup"

    # 2. Create variant
    variant_data = {
        "brand": "King Arthur",
        "package_size": "25 lb bag",
        "purchase_unit": "lb",
        "purchase_quantity": Decimal("25.0"),
        "preferred": True,
    }
    variant = variant_service.create_variant(ingredient.slug, variant_data)
    assert variant.preferred is True
    assert variant.brand == "King Arthur"
    assert variant.ingredient_id == ingredient.id

    # 3. Add to pantry
    pantry_item = pantry_service.add_to_pantry(
        variant_id=variant.id,
        quantity=Decimal("25.0"),
        purchase_date=date.today(),
        expiration_date=date.today() + timedelta(days=365),
        location="Main Pantry",
    )
    assert pantry_item.quantity == 25.0
    assert pantry_item.variant_id == variant.id
    assert pantry_item.location == "Main Pantry"

    # 4. Query total inventory (25 lb = 100 cups at 4 cups/lb)
    total = pantry_service.get_total_quantity(ingredient.slug)
    assert abs(total - Decimal("100.0")) < Decimal("0.01"), f"Expected 100.0 cups, got {total}"

    # 5. Get preferred variant
    preferred = variant_service.get_preferred_variant(ingredient.slug)
    assert preferred.id == variant.id
    assert preferred.preferred is True


def test_multiple_variants_preferred_toggle(test_db):
    """Test: Create multiple variants -> Toggle preferred -> Verify atomicity."""

    # Create ingredient
    ingredient_data = {"name": "Granulated Sugar", "category": "Sugar", "recipe_unit": "cup"}
    ingredient = ingredient_service.create_ingredient(ingredient_data)

    # Create variant 1 (preferred)
    variant1_data = {
        "brand": "C&H",
        "package_size": "4 lb bag",
        "purchase_unit": "lb",
        "purchase_quantity": Decimal("4.0"),
        "preferred": True,
    }
    variant1 = variant_service.create_variant(ingredient.slug, variant1_data)
    assert variant1.preferred is True

    # Create variant 2 (not preferred initially)
    variant2_data = {
        "brand": "Domino",
        "package_size": "5 lb bag",
        "purchase_unit": "lb",
        "purchase_quantity": Decimal("5.0"),
        "preferred": False,
    }
    variant2 = variant_service.create_variant(ingredient.slug, variant2_data)
    assert variant2.preferred is False

    # Toggle preferred to variant 2
    variant_service.set_preferred_variant(variant2.id)

    # Verify atomicity: only variant2 should be preferred
    variants = variant_service.get_variants_for_ingredient(ingredient.slug)
    preferred_count = sum(1 for v in variants if v.preferred)
    assert preferred_count == 1
    assert variants[0].id == variant2.id  # Preferred first
    assert variants[0].preferred is True


def test_pantry_items_filtering(test_db):
    """Test: Add multiple pantry items -> Filter by location and ingredient."""

    # Setup: Create ingredient and variant
    ingredient = ingredient_service.create_ingredient(
        {
            "name": "Bread Flour",
            "category": "Flour",
            "recipe_unit": "cup",
            "density_g_per_ml": 0.4793,  # 4 cups/lb
        }
    )

    variant = variant_service.create_variant(
        ingredient.slug,
        {
            "brand": "Bob's Red Mill",
            "package_size": "5 lb bag",
            "purchase_unit": "lb",
            "purchase_quantity": Decimal("5.0"),
        },
    )

    # Add pantry items to different locations
    item1 = pantry_service.add_to_pantry(
        variant_id=variant.id,
        quantity=Decimal("5.0"),
        purchase_date=date.today() - timedelta(days=30),
        location="Main Pantry",
    )

    item2 = pantry_service.add_to_pantry(
        variant_id=variant.id,
        quantity=Decimal("10.0"),
        purchase_date=date.today() - timedelta(days=15),
        location="Basement",
    )

    item3 = pantry_service.add_to_pantry(
        variant_id=variant.id,
        quantity=Decimal("3.0"),
        purchase_date=date.today(),
        location="Main Pantry",
    )

    # Filter by location
    main_pantry_items = pantry_service.get_pantry_items(
        ingredient_slug=ingredient.slug, location="Main Pantry"
    )
    assert len(main_pantry_items) == 2

    basement_items = pantry_service.get_pantry_items(
        ingredient_slug=ingredient.slug, location="Basement"
    )
    assert len(basement_items) == 1

    # Verify total quantity
    total = pantry_service.get_total_quantity(ingredient.slug)
    assert abs(total - Decimal("72.0")) < Decimal(
        "0.01"
    ), f"Expected 72.0 cups, got {total}"  # 18 lb = 72 cups at 4 cups/lb


def test_expiring_items_detection(test_db):
    """Test: Add items with various expiration dates -> Get expiring soon."""

    # Setup
    ingredient = ingredient_service.create_ingredient(
        {"name": "Yeast", "category": "Misc", "recipe_unit": "tsp"}
    )

    variant = variant_service.create_variant(
        ingredient.slug,
        {
            "brand": "Red Star",
            "package_size": "4 oz jar",
            "purchase_unit": "oz",
            "purchase_quantity": Decimal("4.0"),
        },
    )

    # Add item expiring in 7 days
    expiring_soon = pantry_service.add_to_pantry(
        variant_id=variant.id,
        quantity=Decimal("2.0"),
        purchase_date=date.today() - timedelta(days=60),
        expiration_date=date.today() + timedelta(days=7),
    )

    # Add item expiring in 30 days
    expiring_later = pantry_service.add_to_pantry(
        variant_id=variant.id,
        quantity=Decimal("4.0"),
        purchase_date=date.today() - timedelta(days=30),
        expiration_date=date.today() + timedelta(days=30),
    )

    # Add item with no expiration
    no_expiration = pantry_service.add_to_pantry(
        variant_id=variant.id, quantity=Decimal("1.0"), purchase_date=date.today()
    )

    # Get items expiring within 14 days
    expiring = pantry_service.get_expiring_soon(days=14)
    assert len(expiring) == 1
    assert expiring[0].id == expiring_soon.id

    # Get items expiring within 60 days
    expiring_60 = pantry_service.get_expiring_soon(days=60)
    assert len(expiring_60) == 2


def test_ingredient_deletion_blocked_by_variants(test_db):
    """Test: Create variant -> Attempt to delete ingredient -> Verify blocked."""

    # Create ingredient and variant
    ingredient = ingredient_service.create_ingredient(
        {"name": "Baking Powder", "category": "Misc", "recipe_unit": "tsp"}
    )

    variant = variant_service.create_variant(
        ingredient.slug,
        {"brand": "Rumford", "purchase_unit": "oz", "purchase_quantity": Decimal("8.0")},
    )

    # Attempt to delete ingredient should fail
    with pytest.raises(Exception):  # IngredientInUse exception
        ingredient_service.delete_ingredient(ingredient.slug)

    # Verify ingredient still exists
    retrieved = ingredient_service.get_ingredient(ingredient.slug)
    assert retrieved.slug == ingredient.slug
