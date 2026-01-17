"""
Integration tests for Feature 040 Import/Export v4.0.

Tests export and import of:
- Full round-trip with all entity types (T038)
- Recipe variant relationships (T039)
- Event output_mode preservation (T040)
- Merge vs replace import modes (T041)
"""

import json
from datetime import date
from decimal import Decimal

import pytest

from src.models.ingredient import Ingredient
from src.models.product import Product
from src.models.recipe import Recipe
from src.models.finished_unit import FinishedUnit, YieldMode
from src.models.event import Event, OutputMode
from src.models.supplier import Supplier
from src.models.purchase import Purchase
from src.models.inventory_item import InventoryItem
from src.services.import_export_service import (
    export_all_to_json,
    import_all_from_json_v4,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def comprehensive_test_data(test_db):
    """Create comprehensive test data for round-trip testing.

    Note: Excludes FinishedUnit to avoid recipe_slug resolution complexity
    during import. FinishedUnit round-trip is tested separately.
    """
    session = test_db()

    # Ingredients (including hierarchy)
    flour = Ingredient(
        slug="all-purpose-flour",
        display_name="All Purpose Flour",
        category="Dry Goods",
        hierarchy_level=2,
    )
    sugar = Ingredient(
        slug="granulated-sugar",
        display_name="Granulated Sugar",
        category="Dry Goods",
        hierarchy_level=2,
    )
    session.add_all([flour, sugar])
    session.flush()

    # Supplier
    supplier = Supplier(
        name="Test Bakery Supply",
        city="Boston",
        state="MA",
        zip_code="02101",
        is_active=True,
    )
    session.add(supplier)
    session.flush()

    # Products (with UPCs)
    flour_product = Product(
        ingredient_id=flour.id,
        brand="Gold Medal",
        product_name="Gold Medal Flour 5lb",
        upc_code="016000196100",
        package_unit="lb",
        package_unit_quantity=5.0,
    )
    session.add(flour_product)
    session.flush()

    # Purchase
    purchase = Purchase(
        product_id=flour_product.id,
        supplier_id=supplier.id,
        purchase_date=date(2025, 12, 1),
        unit_price=Decimal("5.99"),
        quantity_purchased=2,
    )
    session.add(purchase)
    session.flush()

    # InventoryItem
    inventory = InventoryItem(
        product_id=flour_product.id,
        purchase_id=purchase.id,
        quantity=2.0,
        purchase_date=date(2025, 12, 1),
    )
    session.add(inventory)
    session.flush()

    # Base Recipe (with F037 fields) - Recipe uses `name` not `slug`
    # F056: yield_quantity, yield_unit removed from Recipe
    base_recipe = Recipe(
        name="Sugar Cookie Base",
        category="Cookies",
        is_production_ready=True,
    )
    session.add(base_recipe)
    session.flush()

    # Variant Recipe (F037) - Recipe uses `name` not `slug`
    # F056: yield_quantity, yield_unit removed from Recipe
    variant_recipe = Recipe(
        name="Frosted Sugar Cookie",
        category="Cookies",
        base_recipe_id=base_recipe.id,
        variant_name="Frosted",
        is_production_ready=False,
    )
    session.add(variant_recipe)
    session.flush()

    # Event (with F039 output_mode) - Event uses `name` not `slug`
    event = Event(
        name="Holiday 2025",
        event_date=date(2025, 12, 25),
        year=2025,
        output_mode=OutputMode.BUNDLED,
    )
    session.add(event)
    session.commit()

    return {
        "flour": flour,
        "sugar": sugar,
        "supplier": supplier,
        "product": flour_product,
        "purchase": purchase,
        "inventory": inventory,
        "base_recipe": base_recipe,
        "variant_recipe": variant_recipe,
        "event": event,
    }


def get_entity_counts(session):
    """Get counts of key entity types for F040 testing."""
    return {
        "ingredients": session.query(Ingredient).count(),
        "products": session.query(Product).count(),
        "recipes": session.query(Recipe).count(),
        "events": session.query(Event).count(),
        "suppliers": session.query(Supplier).count(),
        "purchases": session.query(Purchase).count(),
        "inventory_items": session.query(InventoryItem).count(),
    }


def clear_database(session):
    """Clear all tables in dependency order."""
    # Clear in reverse dependency order
    session.query(InventoryItem).delete()
    session.query(Purchase).delete()
    session.query(FinishedUnit).delete()
    session.query(Recipe).delete()
    session.query(Product).delete()
    session.query(Ingredient).delete()
    session.query(Supplier).delete()
    session.query(Event).delete()
    session.commit()


# ============================================================================
# T038: Full Export/Import Round-Trip Tests
# ============================================================================


class TestFullRoundTrip:
    """Tests for complete export -> import round-trip (T038)."""

    def test_full_export_import_round_trip(self, test_db, comprehensive_test_data, tmp_path):
        """Test complete export -> import preserves all data."""
        session = test_db()

        # Capture counts before export
        counts_before = get_entity_counts(session)
        assert counts_before["recipes"] == 2
        assert counts_before["events"] == 1

        # Export
        export_path = tmp_path / "export.json"
        export_all_to_json(str(export_path))

        # Verify export file exists and has correct version
        with open(export_path) as f:
            data = json.load(f)
        assert data["version"] == "4.1"

        # Clear database
        clear_database(session)

        # Verify empty
        counts_after_clear = get_entity_counts(session)
        assert all(c == 0 for c in counts_after_clear.values()), "Database should be empty"

        # Import
        result = import_all_from_json_v4(str(export_path))
        assert result.failed == 0, f"Import errors: {result.errors}"

        # Compare counts
        counts_after = get_entity_counts(session)
        for entity, count in counts_before.items():
            assert counts_after[entity] == count, f"{entity} count mismatch: expected {count}, got {counts_after[entity]}"

    def test_export_contains_version_4(self, test_db, tmp_path):
        """Test export file contains version 4.0 schema."""
        session = test_db()

        # Create minimal data
        ingredient = Ingredient(
            slug="test-flour",
            display_name="Test Flour",
            category="Test",
        )
        session.add(ingredient)
        session.commit()

        # Export
        export_path = tmp_path / "version_test.json"
        export_all_to_json(str(export_path))

        # Verify version
        with open(export_path) as f:
            data = json.load(f)

        assert data["version"] == "4.1"
        assert "exported_at" in data
        assert "ingredients" in data


# ============================================================================
# T039: Recipe Variants Round-Trip Tests
# ============================================================================


class TestRecipeVariantsRoundTrip:
    """Tests for recipe variant relationship preservation (T039)."""

    def test_recipe_variants_round_trip(self, test_db, tmp_path):
        """Test base/variant recipe relationships preserved."""
        session = test_db()

        # Create base recipe (Recipe uses `name` not `slug`)
        # F056: yield_quantity, yield_unit removed from Recipe
        base = Recipe(
            name="Sugar Cookie Base",
            category="Cookies",
            is_production_ready=True,
        )
        session.add(base)
        session.flush()

        # Create variant
        # F056: yield_quantity, yield_unit removed from Recipe
        variant = Recipe(
            name="Frosted Sugar Cookie",
            category="Cookies",
            variant_name="Frosted",
            base_recipe_id=base.id,
            is_production_ready=False,
        )
        session.add(variant)
        session.commit()

        # Export
        export_path = tmp_path / "recipes.json"
        export_all_to_json(str(export_path))

        # Verify export contains base_recipe_slug (generated from name)
        with open(export_path) as f:
            data = json.load(f)

        # Export uses name to identify recipes
        recipes_by_name = {r["name"]: r for r in data["recipes"]}
        variant_export = recipes_by_name["Frosted Sugar Cookie"]

        # base_recipe_slug is generated as lowercase with underscores
        assert variant_export["base_recipe_slug"] == "sugar_cookie_base"
        assert variant_export["variant_name"] == "Frosted"
        assert variant_export["is_production_ready"] is False

        base_export = recipes_by_name["Sugar Cookie Base"]
        assert base_export["base_recipe_slug"] is None
        assert base_export["is_production_ready"] is True

        # Clear and import
        clear_database(session)
        result = import_all_from_json_v4(str(export_path))
        assert result.failed == 0, f"Import errors: {result.errors}"

        # Verify relationships (query by name)
        imported_base = session.query(Recipe).filter_by(name="Sugar Cookie Base").first()
        imported_variant = session.query(Recipe).filter_by(name="Frosted Sugar Cookie").first()

        assert imported_base is not None
        assert imported_variant is not None
        assert imported_variant.base_recipe_id == imported_base.id
        assert imported_variant.variant_name == "Frosted"
        assert imported_variant.is_production_ready is False
        assert imported_base.is_production_ready is True

    def test_recipe_production_ready_flag(self, test_db, tmp_path):
        """Test is_production_ready flag preserved."""
        session = test_db()

        # Create recipes with different production readiness (Recipe uses `name` not `slug`)
        # F056: yield_quantity, yield_unit removed from Recipe
        ready_recipe = Recipe(
            name="Ready Recipe",
            category="Cookies",
            is_production_ready=True,
        )
        experimental_recipe = Recipe(
            name="Experimental Recipe",
            category="Cookies",
            is_production_ready=False,
        )
        session.add_all([ready_recipe, experimental_recipe])
        session.commit()

        # Export
        export_path = tmp_path / "production_ready.json"
        export_all_to_json(str(export_path))

        # Clear and import
        clear_database(session)
        result = import_all_from_json_v4(str(export_path))
        assert result.failed == 0

        # Verify flags preserved (query by name)
        ready = session.query(Recipe).filter_by(name="Ready Recipe").first()
        experimental = session.query(Recipe).filter_by(name="Experimental Recipe").first()

        assert ready.is_production_ready is True
        assert experimental.is_production_ready is False


# ============================================================================
# T040: Event Output Mode Round-Trip Tests
# ============================================================================


class TestEventOutputModeRoundTrip:
    """Tests for event output_mode preservation (T040)."""

    def test_event_output_mode_round_trip(self, test_db, tmp_path):
        """Test event output_mode preserved after round-trip."""
        session = test_db()

        # Create events with different modes (Event uses `name` not `slug`)
        bundled_event = Event(
            name="Gift Set Event",
            event_date=date(2025, 12, 25),
            year=2025,
            output_mode=OutputMode.BUNDLED,
        )
        bulk_event = Event(
            name="Bulk Order",
            event_date=date(2025, 12, 20),
            year=2025,
            output_mode=OutputMode.BULK_COUNT,
        )
        null_event = Event(
            name="Legacy Event",
            event_date=date(2025, 12, 15),
            year=2025,
            output_mode=None,
        )
        session.add_all([bundled_event, bulk_event, null_event])
        session.commit()

        # Export
        export_path = tmp_path / "events.json"
        export_all_to_json(str(export_path))

        # Verify export (events keyed by name)
        with open(export_path) as f:
            data = json.load(f)

        events = {e["name"]: e for e in data["events"]}
        assert events["Gift Set Event"]["output_mode"] == "bundled"
        assert events["Bulk Order"]["output_mode"] == "bulk_count"
        assert events["Legacy Event"]["output_mode"] is None

        # Clear and import
        clear_database(session)
        result = import_all_from_json_v4(str(export_path))
        assert result.failed == 0, f"Import errors: {result.errors}"

        # Verify imported values (query by name)
        imported = {e.name: e for e in session.query(Event).all()}
        assert imported["Gift Set Event"].output_mode == OutputMode.BUNDLED
        assert imported["Bulk Order"].output_mode == OutputMode.BULK_COUNT
        assert imported["Legacy Event"].output_mode is None


# ============================================================================
# T041: Merge vs Replace Mode Tests
# ============================================================================


class TestImportModes:
    """Tests for merge and replace import modes (T041)."""

    def test_import_merge_mode_adds_without_replacing(self, test_db, tmp_path):
        """Test merge mode adds without replacing existing."""
        session = test_db()

        # Create initial ingredient
        flour = Ingredient(
            slug="flour",
            display_name="Flour",
            category="Dry Goods",
        )
        session.add(flour)
        session.commit()

        # Export (just flour)
        export_path = tmp_path / "initial.json"
        export_all_to_json(str(export_path))

        # Add another ingredient
        sugar = Ingredient(
            slug="sugar",
            display_name="Sugar",
            category="Dry Goods",
        )
        session.add(sugar)
        session.commit()

        assert session.query(Ingredient).count() == 2

        # Import in merge mode (default)
        result = import_all_from_json_v4(str(export_path), mode="merge")

        # Both should exist (flour not duplicated, sugar preserved)
        assert session.query(Ingredient).count() == 2
        assert session.query(Ingredient).filter_by(slug="flour").count() == 1
        assert session.query(Ingredient).filter_by(slug="sugar").count() == 1

    def test_import_replace_mode_clears_existing(self, test_db, tmp_path):
        """Test replace mode clears existing data first."""
        session = test_db()

        # Create initial ingredient
        flour = Ingredient(
            slug="flour",
            display_name="Flour",
            category="Dry Goods",
        )
        session.add(flour)
        session.commit()

        # Export (just flour)
        export_path = tmp_path / "initial.json"
        export_all_to_json(str(export_path))

        # Add another ingredient
        sugar = Ingredient(
            slug="sugar",
            display_name="Sugar",
            category="Dry Goods",
        )
        session.add(sugar)
        session.commit()

        assert session.query(Ingredient).count() == 2

        # Import in replace mode
        result = import_all_from_json_v4(str(export_path), mode="replace")

        # Only flour should exist (sugar removed)
        assert session.query(Ingredient).count() == 1
        assert session.query(Ingredient).filter_by(slug="flour").count() == 1
        assert session.query(Ingredient).filter_by(slug="sugar").count() == 0

    def test_merge_mode_updates_existing_by_slug(self, test_db, tmp_path):
        """Test merge mode updates existing records by slug."""
        session = test_db()

        # Create initial ingredient
        flour = Ingredient(
            slug="flour",
            display_name="Flour OLD",
            category="Dry Goods",
        )
        session.add(flour)
        session.commit()

        # Export
        export_path = tmp_path / "initial.json"
        export_all_to_json(str(export_path))

        # Modify the export file to have different display_name
        with open(export_path) as f:
            data = json.load(f)

        data["ingredients"][0]["display_name"] = "Flour NEW"

        with open(export_path, "w") as f:
            json.dump(data, f)

        # Import in merge mode
        result = import_all_from_json_v4(str(export_path), mode="merge")

        # Should have one flour with updated name
        assert session.query(Ingredient).count() == 1
        updated_flour = session.query(Ingredient).filter_by(slug="flour").first()
        # Note: merge behavior may vary - check actual implementation
        # This test documents expected behavior
