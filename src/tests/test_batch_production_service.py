"""Tests for batch production service.

Feature 013: Production & Inventory Tracking
Tests for check_can_produce() and record_batch_production() functions.
"""

import pytest
from decimal import Decimal
from datetime import datetime

from src.models import (
    Recipe,
    RecipeIngredient,
    Ingredient,
    Product,
    InventoryItem,
    FinishedUnit,
    ProductionRun,
    ProductionConsumption,
    RecipeComponent,
)
from src.models.finished_unit import YieldMode
from src.services import batch_production_service
from src.services.batch_production_service import (
    RecipeNotFoundError,
    FinishedUnitNotFoundError,
    FinishedUnitRecipeMismatchError,
    InsufficientInventoryError,
    ProductionRunNotFoundError,
)
from src.services.database import session_scope


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def ingredient_flour(test_db):
    """Create flour ingredient."""
    session = test_db()
    ingredient = Ingredient(
        display_name="All-Purpose Flour",
        slug="flour",
        category="Flour",
        recipe_unit="cup",
        # Density for unit conversion
        density_volume_value=1.0,
        density_volume_unit="cup",
        density_weight_value=120.0,
        density_weight_unit="g",
    )
    session.add(ingredient)
    session.commit()
    return ingredient


@pytest.fixture
def ingredient_sugar(test_db):
    """Create sugar ingredient."""
    session = test_db()
    ingredient = Ingredient(
        display_name="Granulated Sugar",
        slug="sugar",
        category="Sugar",
        recipe_unit="cup",
        density_volume_value=1.0,
        density_volume_unit="cup",
        density_weight_value=200.0,
        density_weight_unit="g",
    )
    session.add(ingredient)
    session.commit()
    return ingredient


@pytest.fixture
def product_flour(test_db, ingredient_flour):
    """Create flour product."""
    session = test_db()
    product = Product(
        ingredient_id=ingredient_flour.id,
        brand="Gold Medal",
        package_size="5 lb bag",
        purchase_unit="cup",
        purchase_quantity=20.0,
        preferred=True,
    )
    session.add(product)
    session.commit()
    return product


@pytest.fixture
def product_sugar(test_db, ingredient_sugar):
    """Create sugar product."""
    session = test_db()
    product = Product(
        ingredient_id=ingredient_sugar.id,
        brand="Domino",
        package_size="4 lb bag",
        purchase_unit="cup",
        purchase_quantity=8.0,
        preferred=True,
    )
    session.add(product)
    session.commit()
    return product


@pytest.fixture
def inventory_flour(test_db, product_flour):
    """Create flour inventory with 10 cups."""
    session = test_db()
    inv = InventoryItem(
        product_id=product_flour.id,
        quantity=10.0,
        unit_cost=Decimal("0.50"),
        purchase_date=datetime(2024, 1, 1),
    )
    session.add(inv)
    session.commit()
    return inv


@pytest.fixture
def inventory_sugar(test_db, product_sugar):
    """Create sugar inventory with 5 cups."""
    session = test_db()
    inv = InventoryItem(
        product_id=product_sugar.id,
        quantity=5.0,
        unit_cost=Decimal("0.60"),
        purchase_date=datetime(2024, 1, 1),
    )
    session.add(inv)
    session.commit()
    return inv


@pytest.fixture
def recipe_cookies(test_db, ingredient_flour, ingredient_sugar):
    """Create simple cookie recipe requiring 2 cups flour and 1 cup sugar per batch."""
    session = test_db()
    recipe = Recipe(
        name="Chocolate Chip Cookies",
        category="Cookies",
        yield_quantity=48.0,
        yield_unit="cookies",
    )
    session.add(recipe)
    session.flush()

    # Add flour ingredient
    ri_flour = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=ingredient_flour.id,
        quantity=2.0,
        unit="cup",
    )
    session.add(ri_flour)

    # Add sugar ingredient
    ri_sugar = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=ingredient_sugar.id,
        quantity=1.0,
        unit="cup",
    )
    session.add(ri_sugar)

    session.commit()
    return recipe


@pytest.fixture
def finished_unit_cookies(test_db, recipe_cookies):
    """Create FinishedUnit for cookies (48 per batch)."""
    session = test_db()
    fu = FinishedUnit(
        recipe_id=recipe_cookies.id,
        slug="chocolate-chip-cookie",
        display_name="Chocolate Chip Cookie",
        yield_mode=YieldMode.DISCRETE_COUNT,
        items_per_batch=48,
        item_unit="cookie",
        inventory_count=0,
        unit_cost=Decimal("0.10"),
    )
    session.add(fu)
    session.commit()
    return fu


@pytest.fixture
def recipe_with_ingredients_and_inventory(
    recipe_cookies, inventory_flour, inventory_sugar
):
    """Complete recipe with all required inventory in place."""
    return recipe_cookies


# =============================================================================
# Tests for check_can_produce
# =============================================================================


class TestCheckCanProduce:
    """Tests for check_can_produce() function."""

    def test_sufficient_inventory(
        self, recipe_with_ingredients_and_inventory, inventory_flour, inventory_sugar
    ):
        """Given sufficient inventory, check_can_produce returns can_produce=True."""
        recipe = recipe_with_ingredients_and_inventory
        result = batch_production_service.check_can_produce(
            recipe_id=recipe.id,
            num_batches=2,  # Needs 4 cups flour (have 10), 2 cups sugar (have 5)
        )
        assert result["can_produce"] is True
        assert result["missing"] == []

    def test_insufficient_inventory_single_ingredient(
        self, recipe_with_ingredients_and_inventory, inventory_flour, inventory_sugar
    ):
        """Given insufficient inventory, check_can_produce returns missing details."""
        recipe = recipe_with_ingredients_and_inventory
        result = batch_production_service.check_can_produce(
            recipe_id=recipe.id,
            num_batches=10,  # Needs 20 cups flour (have 10), 10 cups sugar (have 5)
        )
        assert result["can_produce"] is False
        assert len(result["missing"]) == 2  # Both flour and sugar insufficient

        # Check flour missing details
        flour_missing = next(
            (m for m in result["missing"] if m["ingredient_slug"] == "flour"), None
        )
        assert flour_missing is not None
        assert flour_missing["needed"] == Decimal("20.0")
        assert flour_missing["available"] == Decimal("10.0")
        assert flour_missing["unit"] == "cup"

        # Check sugar missing details
        sugar_missing = next(
            (m for m in result["missing"] if m["ingredient_slug"] == "sugar"), None
        )
        assert sugar_missing is not None
        assert sugar_missing["needed"] == Decimal("10.0")
        assert sugar_missing["available"] == Decimal("5.0")

    def test_recipe_not_found(self, test_db):
        """Non-existent recipe raises RecipeNotFoundError."""
        with pytest.raises(RecipeNotFoundError) as exc_info:
            batch_production_service.check_can_produce(
                recipe_id=99999,
                num_batches=1,
            )
        assert exc_info.value.recipe_id == 99999

    def test_zero_batches(self, recipe_with_ingredients_and_inventory):
        """Zero batches should always succeed (no ingredients needed)."""
        recipe = recipe_with_ingredients_and_inventory
        # Note: This is an edge case - 0 batches means 0 quantity needed
        # The behavior depends on whether we allow 0 batches
        # For now, we assume it would work but produce nothing meaningful
        result = batch_production_service.check_can_produce(
            recipe_id=recipe.id,
            num_batches=0,
        )
        # With 0 batches, 0 ingredients needed, should be True
        assert result["can_produce"] is True


# =============================================================================
# Tests for record_batch_production
# =============================================================================


class TestRecordBatchProduction:
    """Tests for record_batch_production() function."""

    def test_happy_path(
        self,
        recipe_with_ingredients_and_inventory,
        finished_unit_cookies,
        inventory_flour,
        inventory_sugar,
    ):
        """Record production: FIFO consumed, inventory incremented, records created."""
        recipe = recipe_with_ingredients_and_inventory
        recipe_id = recipe.id
        fu_id = finished_unit_cookies.id
        initial_fu_count = finished_unit_cookies.inventory_count

        result = batch_production_service.record_batch_production(
            recipe_id=recipe_id,
            finished_unit_id=fu_id,
            num_batches=2,
            actual_yield=92,
            notes="Test batch",
        )

        # Verify result structure
        assert result["production_run_id"] is not None
        assert result["recipe_id"] == recipe_id
        assert result["finished_unit_id"] == fu_id
        assert result["num_batches"] == 2
        assert result["expected_yield"] == 96  # 2 * 48
        assert result["actual_yield"] == 92
        assert result["total_ingredient_cost"] > Decimal("0")
        assert len(result["consumptions"]) == 2  # flour and sugar

        # Verify FinishedUnit inventory incremented
        with session_scope() as session:
            fu = session.query(FinishedUnit).filter_by(id=fu_id).first()
            assert fu.inventory_count == initial_fu_count + 92

        # Verify ProductionRun created
        with session_scope() as session:
            pr = session.query(ProductionRun).filter_by(id=result["production_run_id"]).first()
            assert pr is not None
            assert pr.recipe_id == recipe_id
            assert pr.actual_yield == 92
            assert pr.num_batches == 2

        # Verify ProductionConsumption records created
        with session_scope() as session:
            consumptions = (
                session.query(ProductionConsumption)
                .filter_by(production_run_id=result["production_run_id"])
                .all()
            )
            assert len(consumptions) == 2
            slugs = {c.ingredient_slug for c in consumptions}
            assert slugs == {"flour", "sugar"}

    def test_zero_yield_failed_batch(
        self,
        recipe_with_ingredients_and_inventory,
        finished_unit_cookies,
        inventory_flour,
        inventory_sugar,
    ):
        """Failed batch: actual_yield=0 allowed, ingredients still consumed."""
        recipe = recipe_with_ingredients_and_inventory

        result = batch_production_service.record_batch_production(
            recipe_id=recipe.id,
            finished_unit_id=finished_unit_cookies.id,
            num_batches=1,
            actual_yield=0,
            notes="Burned batch",
        )

        assert result["actual_yield"] == 0
        assert result["per_unit_cost"] == Decimal("0.0000")  # No division by zero

        # Ingredients still consumed
        with session_scope() as session:
            consumptions = (
                session.query(ProductionConsumption)
                .filter_by(production_run_id=result["production_run_id"])
                .all()
            )
            assert len(consumptions) == 2  # Both ingredients consumed

        # FinishedUnit count should still be 0
        with session_scope() as session:
            fu = session.query(FinishedUnit).filter_by(id=finished_unit_cookies.id).first()
            assert fu.inventory_count == 0

    def test_yield_exceeds_expected(
        self,
        recipe_with_ingredients_and_inventory,
        finished_unit_cookies,
        inventory_flour,
        inventory_sugar,
    ):
        """Yield exceeds expected: allowed and tracked."""
        recipe = recipe_with_ingredients_and_inventory

        result = batch_production_service.record_batch_production(
            recipe_id=recipe.id,
            finished_unit_id=finished_unit_cookies.id,
            num_batches=1,
            actual_yield=60,  # Expected 48
        )

        assert result["actual_yield"] == 60
        assert result["expected_yield"] == 48

        # Per unit cost should be lower since we got more items
        # total_cost / 60 < total_cost / 48
        with session_scope() as session:
            pr = session.query(ProductionRun).filter_by(id=result["production_run_id"]).first()
            assert pr.actual_yield == 60
            assert pr.expected_yield == 48

    def test_rollback_on_insufficient_inventory(
        self,
        recipe_with_ingredients_and_inventory,
        finished_unit_cookies,
        inventory_flour,
        inventory_sugar,
    ):
        """Insufficient inventory: entire operation rolls back."""
        recipe = recipe_with_ingredients_and_inventory
        initial_fu_count = finished_unit_cookies.inventory_count

        with pytest.raises(InsufficientInventoryError):
            batch_production_service.record_batch_production(
                recipe_id=recipe.id,
                finished_unit_id=finished_unit_cookies.id,
                num_batches=100,  # Way more than available
                actual_yield=4800,
            )

        # Verify no state changed - FinishedUnit count unchanged
        with session_scope() as session:
            fu = session.query(FinishedUnit).filter_by(id=finished_unit_cookies.id).first()
            assert fu.inventory_count == initial_fu_count

        # No ProductionRun created
        with session_scope() as session:
            runs = (
                session.query(ProductionRun)
                .filter_by(recipe_id=recipe.id)
                .all()
            )
            assert len(runs) == 0

    def test_finished_unit_recipe_mismatch(
        self,
        test_db,
        recipe_with_ingredients_and_inventory,
        inventory_flour,
        inventory_sugar,
    ):
        """FinishedUnit from different recipe raises error."""
        recipe = recipe_with_ingredients_and_inventory
        recipe_id = recipe.id
        session = test_db()

        # Create a different recipe
        other_recipe = Recipe(
            name="Sugar Cookies",
            category="Cookies",
            yield_quantity=36.0,
            yield_unit="cookies",
        )
        session.add(other_recipe)
        session.flush()

        # Create FinishedUnit for the other recipe
        other_fu = FinishedUnit(
            recipe_id=other_recipe.id,
            slug="sugar-cookie",
            display_name="Sugar Cookie",
            yield_mode=YieldMode.DISCRETE_COUNT,
            items_per_batch=36,
            item_unit="cookie",
            inventory_count=0,
            unit_cost=Decimal("0.15"),
        )
        session.add(other_fu)
        session.commit()

        # Capture IDs before closing session
        other_fu_id = other_fu.id

        with pytest.raises(FinishedUnitRecipeMismatchError) as exc_info:
            batch_production_service.record_batch_production(
                recipe_id=recipe_id,
                finished_unit_id=other_fu_id,  # Wrong recipe!
                num_batches=1,
                actual_yield=48,
            )
        assert exc_info.value.finished_unit_id == other_fu_id
        assert exc_info.value.recipe_id == recipe_id

    def test_finished_unit_not_found(
        self,
        recipe_with_ingredients_and_inventory,
        inventory_flour,
        inventory_sugar,
    ):
        """Non-existent FinishedUnit raises error."""
        recipe = recipe_with_ingredients_and_inventory

        with pytest.raises(FinishedUnitNotFoundError) as exc_info:
            batch_production_service.record_batch_production(
                recipe_id=recipe.id,
                finished_unit_id=99999,
                num_batches=1,
                actual_yield=48,
            )
        assert exc_info.value.finished_unit_id == 99999

    def test_recipe_not_found(self, test_db, finished_unit_cookies):
        """Non-existent recipe raises error."""
        with pytest.raises(RecipeNotFoundError) as exc_info:
            batch_production_service.record_batch_production(
                recipe_id=99999,
                finished_unit_id=finished_unit_cookies.id,
                num_batches=1,
                actual_yield=48,
            )
        assert exc_info.value.recipe_id == 99999

    def test_custom_produced_at_timestamp(
        self,
        recipe_with_ingredients_and_inventory,
        finished_unit_cookies,
        inventory_flour,
        inventory_sugar,
    ):
        """Custom produced_at timestamp is recorded."""
        recipe = recipe_with_ingredients_and_inventory
        custom_time = datetime(2024, 6, 15, 10, 30, 0)

        result = batch_production_service.record_batch_production(
            recipe_id=recipe.id,
            finished_unit_id=finished_unit_cookies.id,
            num_batches=1,
            actual_yield=48,
            produced_at=custom_time,
        )

        with session_scope() as session:
            pr = session.query(ProductionRun).filter_by(id=result["production_run_id"]).first()
            assert pr.produced_at == custom_time

    def test_per_unit_cost_calculation(
        self,
        recipe_with_ingredients_and_inventory,
        finished_unit_cookies,
        inventory_flour,
        inventory_sugar,
    ):
        """Per unit cost is correctly calculated as total_cost / actual_yield."""
        recipe = recipe_with_ingredients_and_inventory

        result = batch_production_service.record_batch_production(
            recipe_id=recipe.id,
            finished_unit_id=finished_unit_cookies.id,
            num_batches=1,
            actual_yield=50,
        )

        # Verify per_unit_cost = total_cost / actual_yield
        expected_per_unit = result["total_ingredient_cost"] / Decimal("50")
        with session_scope() as session:
            pr = session.query(ProductionRun).filter_by(id=result["production_run_id"]).first()
            # Allow small precision difference
            assert abs(pr.per_unit_cost - expected_per_unit) < Decimal("0.0001")


# =============================================================================
# Tests for History Query Functions
# =============================================================================


class TestGetProductionHistory:
    """Tests for get_production_history() function."""

    def test_empty_history(self, test_db):
        """Empty database returns empty list."""
        result = batch_production_service.get_production_history()
        assert result == []

    def test_returns_production_runs(
        self,
        recipe_with_ingredients_and_inventory,
        finished_unit_cookies,
        inventory_flour,
        inventory_sugar,
    ):
        """Returns list of production runs."""
        recipe = recipe_with_ingredients_and_inventory
        recipe_id = recipe.id
        fu_id = finished_unit_cookies.id

        # Create two production runs
        batch_production_service.record_batch_production(
            recipe_id=recipe_id,
            finished_unit_id=fu_id,
            num_batches=1,
            actual_yield=48,
        )
        batch_production_service.record_batch_production(
            recipe_id=recipe_id,
            finished_unit_id=fu_id,
            num_batches=2,
            actual_yield=90,
        )

        result = batch_production_service.get_production_history()
        assert len(result) == 2
        # Most recent first
        assert result[0]["actual_yield"] == 90
        assert result[1]["actual_yield"] == 48

    def test_filter_by_recipe(
        self,
        test_db,
        recipe_with_ingredients_and_inventory,
        finished_unit_cookies,
        inventory_flour,
        inventory_sugar,
    ):
        """Filters by recipe_id."""
        recipe = recipe_with_ingredients_and_inventory
        recipe_id = recipe.id
        fu_id = finished_unit_cookies.id

        batch_production_service.record_batch_production(
            recipe_id=recipe_id,
            finished_unit_id=fu_id,
            num_batches=1,
            actual_yield=48,
        )

        result = batch_production_service.get_production_history(recipe_id=recipe_id)
        assert len(result) == 1
        assert result[0]["recipe_id"] == recipe_id

        # Non-existent recipe returns empty
        result = batch_production_service.get_production_history(recipe_id=99999)
        assert len(result) == 0

    def test_filter_by_date_range(
        self,
        recipe_with_ingredients_and_inventory,
        finished_unit_cookies,
        inventory_flour,
        inventory_sugar,
    ):
        """Filters by date range."""
        recipe = recipe_with_ingredients_and_inventory
        recipe_id = recipe.id
        fu_id = finished_unit_cookies.id

        batch_production_service.record_batch_production(
            recipe_id=recipe_id,
            finished_unit_id=fu_id,
            num_batches=1,
            actual_yield=48,
            produced_at=datetime(2024, 6, 15),
        )

        # Within range
        result = batch_production_service.get_production_history(
            start_date=datetime(2024, 6, 1),
            end_date=datetime(2024, 6, 30),
        )
        assert len(result) == 1

        # Outside range
        result = batch_production_service.get_production_history(
            start_date=datetime(2024, 7, 1),
            end_date=datetime(2024, 7, 31),
        )
        assert len(result) == 0

    def test_include_consumptions(
        self,
        recipe_with_ingredients_and_inventory,
        finished_unit_cookies,
        inventory_flour,
        inventory_sugar,
    ):
        """Include consumption details when requested."""
        recipe = recipe_with_ingredients_and_inventory
        recipe_id = recipe.id
        fu_id = finished_unit_cookies.id

        batch_production_service.record_batch_production(
            recipe_id=recipe_id,
            finished_unit_id=fu_id,
            num_batches=1,
            actual_yield=48,
        )

        result = batch_production_service.get_production_history(include_consumptions=True)
        assert len(result) == 1
        assert "consumptions" in result[0]
        assert len(result[0]["consumptions"]) == 2  # flour and sugar

    def test_pagination(
        self,
        recipe_with_ingredients_and_inventory,
        finished_unit_cookies,
        inventory_flour,
        inventory_sugar,
    ):
        """Supports limit and offset pagination."""
        recipe = recipe_with_ingredients_and_inventory
        recipe_id = recipe.id
        fu_id = finished_unit_cookies.id

        # Create 3 production runs
        for i in range(3):
            batch_production_service.record_batch_production(
                recipe_id=recipe_id,
                finished_unit_id=fu_id,
                num_batches=1,
                actual_yield=40 + i,
            )

        # Limit to 2
        result = batch_production_service.get_production_history(limit=2)
        assert len(result) == 2

        # Offset by 1
        result = batch_production_service.get_production_history(limit=2, offset=1)
        assert len(result) == 2


class TestGetProductionRun:
    """Tests for get_production_run() function."""

    def test_get_by_id(
        self,
        recipe_with_ingredients_and_inventory,
        finished_unit_cookies,
        inventory_flour,
        inventory_sugar,
    ):
        """Returns production run by ID with full details."""
        recipe = recipe_with_ingredients_and_inventory
        recipe_id = recipe.id
        fu_id = finished_unit_cookies.id

        create_result = batch_production_service.record_batch_production(
            recipe_id=recipe_id,
            finished_unit_id=fu_id,
            num_batches=1,
            actual_yield=48,
            notes="Test run",
        )

        result = batch_production_service.get_production_run(
            create_result["production_run_id"]
        )
        assert result["id"] == create_result["production_run_id"]
        assert result["recipe_id"] == recipe_id
        assert result["actual_yield"] == 48
        assert result["notes"] == "Test run"
        assert "consumptions" in result
        assert len(result["consumptions"]) == 2

    def test_not_found(self, test_db):
        """Raises error for non-existent production run."""
        with pytest.raises(ProductionRunNotFoundError) as exc_info:
            batch_production_service.get_production_run(99999)
        assert exc_info.value.production_run_id == 99999


# =============================================================================
# Tests for Import/Export Functions
# =============================================================================


class TestExportProductionHistory:
    """Tests for export_production_history() function."""

    def test_empty_export(self, test_db):
        """Empty database returns empty production_runs list."""
        result = batch_production_service.export_production_history()
        assert result["version"] == "1.0"
        assert "exported_at" in result
        assert result["production_runs"] == []

    def test_export_with_data(
        self,
        recipe_with_ingredients_and_inventory,
        finished_unit_cookies,
        inventory_flour,
        inventory_sugar,
    ):
        """Export includes full production run data with consumptions."""
        recipe = recipe_with_ingredients_and_inventory
        recipe_id = recipe.id
        fu_id = finished_unit_cookies.id

        batch_production_service.record_batch_production(
            recipe_id=recipe_id,
            finished_unit_id=fu_id,
            num_batches=1,
            actual_yield=48,
            notes="Export test",
        )

        result = batch_production_service.export_production_history()
        assert len(result["production_runs"]) == 1

        run = result["production_runs"][0]
        assert run["recipe_name"] == recipe.name
        assert run["finished_unit_slug"] == "chocolate-chip-cookie"
        assert run["actual_yield"] == 48
        assert run["notes"] == "Export test"
        assert len(run["consumptions"]) == 2  # flour and sugar


class TestImportProductionHistory:
    """Tests for import_production_history() function."""

    def test_import_skips_duplicates(
        self,
        recipe_with_ingredients_and_inventory,
        finished_unit_cookies,
        inventory_flour,
        inventory_sugar,
    ):
        """Import with skip_duplicates=True skips existing UUIDs."""
        recipe = recipe_with_ingredients_and_inventory
        recipe_id = recipe.id
        fu_id = finished_unit_cookies.id

        batch_production_service.record_batch_production(
            recipe_id=recipe_id,
            finished_unit_id=fu_id,
            num_batches=1,
            actual_yield=48,
        )

        exported = batch_production_service.export_production_history()
        result = batch_production_service.import_production_history(exported)

        assert result["skipped"] == len(exported["production_runs"])
        assert result["imported"] == 0
        assert result["errors"] == []

    def test_import_validates_missing_recipe(self, test_db, finished_unit_cookies):
        """Import fails gracefully with missing recipe reference."""
        data = {
            "version": "1.0",
            "production_runs": [
                {
                    "uuid": "test-uuid-001",
                    "recipe_name": "nonexistent-recipe",
                    "finished_unit_slug": "chocolate-chip-cookie",
                    "num_batches": 1,
                    "expected_yield": 48,
                    "actual_yield": 48,
                    "produced_at": "2024-06-15T10:00:00",
                    "notes": None,
                    "total_ingredient_cost": "5.00",
                    "per_unit_cost": "0.1042",
                    "consumptions": [],
                }
            ],
        }
        result = batch_production_service.import_production_history(data)
        assert result["imported"] == 0
        assert len(result["errors"]) > 0
        assert "Recipe not found" in result["errors"][0]

    def test_import_validates_missing_finished_unit(
        self, test_db, recipe_with_ingredients_and_inventory
    ):
        """Import fails gracefully with missing finished unit reference."""
        recipe = recipe_with_ingredients_and_inventory
        data = {
            "version": "1.0",
            "production_runs": [
                {
                    "uuid": "test-uuid-002",
                    "recipe_name": recipe.name,
                    "finished_unit_slug": "nonexistent-fu",
                    "num_batches": 1,
                    "expected_yield": 48,
                    "actual_yield": 48,
                    "produced_at": "2024-06-15T10:00:00",
                    "notes": None,
                    "total_ingredient_cost": "5.00",
                    "per_unit_cost": "0.1042",
                    "consumptions": [],
                }
            ],
        }
        result = batch_production_service.import_production_history(data)
        assert result["imported"] == 0
        assert len(result["errors"]) > 0
        assert "FinishedUnit not found" in result["errors"][0]

    def test_export_import_roundtrip(
        self,
        test_db,
        recipe_with_ingredients_and_inventory,
        finished_unit_cookies,
        inventory_flour,
        inventory_sugar,
    ):
        """Export -> clear -> import preserves data."""
        recipe = recipe_with_ingredients_and_inventory
        recipe_id = recipe.id
        fu_id = finished_unit_cookies.id

        # Create production run
        batch_production_service.record_batch_production(
            recipe_id=recipe_id,
            finished_unit_id=fu_id,
            num_batches=2,
            actual_yield=90,
            notes="Roundtrip test",
        )

        # Export
        exported = batch_production_service.export_production_history()
        assert len(exported["production_runs"]) == 1
        original_run = exported["production_runs"][0]

        # Clear production runs
        with session_scope() as session:
            session.query(ProductionConsumption).delete()
            session.query(ProductionRun).delete()

        # Verify cleared
        verify_export = batch_production_service.export_production_history()
        assert len(verify_export["production_runs"]) == 0

        # Import
        result = batch_production_service.import_production_history(exported)
        assert result["imported"] == 1
        assert result["errors"] == []

        # Verify reimported data matches
        reimported = batch_production_service.export_production_history()
        assert len(reimported["production_runs"]) == 1

        reimp_run = reimported["production_runs"][0]
        assert reimp_run["uuid"] == original_run["uuid"]
        assert reimp_run["actual_yield"] == original_run["actual_yield"]
        assert reimp_run["total_ingredient_cost"] == original_run["total_ingredient_cost"]
        assert reimp_run["notes"] == original_run["notes"]


# =============================================================================
# Transaction Atomicity Tests (Bug Fix Verification)
# =============================================================================


class TestTransactionAtomicity:
    """Tests verifying that record_batch_production is fully atomic.

    These tests verify the fix for the Constitution Principle II violation
    where FIFO consumption was committing independently of production records.
    """

    def test_record_batch_production_rolls_back_inventory_on_later_failure(
        self,
        test_db,
        recipe_with_ingredients_and_inventory,
        finished_unit_cookies,
        inventory_flour,
        inventory_sugar,
    ):
        """Verify inventory is restored if production fails after initial consumption.

        This test validates that the atomic transaction fix works correctly:
        if any part of record_batch_production fails, ALL changes (including
        FIFO inventory decrements) are rolled back.
        """
        recipe = recipe_with_ingredients_and_inventory
        recipe_id = recipe.id
        fu_id = finished_unit_cookies.id

        # Record initial inventory quantities
        with session_scope() as session:
            flour_inv = session.query(InventoryItem).filter_by(id=inventory_flour.id).first()
            sugar_inv = session.query(InventoryItem).filter_by(id=inventory_sugar.id).first()
            fu = session.query(FinishedUnit).filter_by(id=fu_id).first()

            initial_flour_qty = flour_inv.quantity
            initial_sugar_qty = sugar_inv.quantity
            initial_fu_count = fu.inventory_count

        # Attempt production that will fail due to insufficient inventory
        # (requesting more than available)
        with pytest.raises(InsufficientInventoryError):
            batch_production_service.record_batch_production(
                recipe_id=recipe_id,
                finished_unit_id=fu_id,
                num_batches=100,  # Way more than available inventory
                actual_yield=4800,
            )

        # Verify ALL inventory quantities are unchanged (rollback worked)
        with session_scope() as session:
            flour_inv = session.query(InventoryItem).filter_by(id=inventory_flour.id).first()
            sugar_inv = session.query(InventoryItem).filter_by(id=inventory_sugar.id).first()
            fu = session.query(FinishedUnit).filter_by(id=fu_id).first()

            # Critical assertions: inventory should be EXACTLY as before
            assert flour_inv.quantity == initial_flour_qty, (
                f"Flour inventory was modified but should have rolled back. "
                f"Expected {initial_flour_qty}, got {flour_inv.quantity}"
            )
            assert sugar_inv.quantity == initial_sugar_qty, (
                f"Sugar inventory was modified but should have rolled back. "
                f"Expected {initial_sugar_qty}, got {sugar_inv.quantity}"
            )
            assert fu.inventory_count == initial_fu_count, (
                f"FinishedUnit count was modified but should have rolled back. "
                f"Expected {initial_fu_count}, got {fu.inventory_count}"
            )

        # Verify no ProductionRun was created
        with session_scope() as session:
            runs = session.query(ProductionRun).filter_by(recipe_id=recipe_id).all()
            assert len(runs) == 0, "ProductionRun should not exist after failed production"

        # Verify no ProductionConsumption records exist
        with session_scope() as session:
            consumptions = session.query(ProductionConsumption).all()
            assert len(consumptions) == 0, "No consumption records should exist after rollback"

    def test_successful_production_commits_atomically(
        self,
        test_db,
        recipe_with_ingredients_and_inventory,
        finished_unit_cookies,
        inventory_flour,
        inventory_sugar,
    ):
        """Verify successful production commits all changes together.

        This test verifies that when production succeeds, inventory decrements
        AND production records are committed in a single atomic transaction.
        """
        recipe = recipe_with_ingredients_and_inventory
        recipe_id = recipe.id
        fu_id = finished_unit_cookies.id

        # Record initial quantities
        with session_scope() as session:
            flour_inv = session.query(InventoryItem).filter_by(id=inventory_flour.id).first()
            sugar_inv = session.query(InventoryItem).filter_by(id=inventory_sugar.id).first()
            fu = session.query(FinishedUnit).filter_by(id=fu_id).first()

            initial_flour_qty = flour_inv.quantity
            initial_sugar_qty = sugar_inv.quantity
            initial_fu_count = fu.inventory_count

        # Perform successful production (1 batch = 2 cups flour, 1 cup sugar)
        result = batch_production_service.record_batch_production(
            recipe_id=recipe_id,
            finished_unit_id=fu_id,
            num_batches=1,
            actual_yield=48,
        )

        # Verify all changes were committed together
        with session_scope() as session:
            flour_inv = session.query(InventoryItem).filter_by(id=inventory_flour.id).first()
            sugar_inv = session.query(InventoryItem).filter_by(id=inventory_sugar.id).first()
            fu = session.query(FinishedUnit).filter_by(id=fu_id).first()

            # Inventory should be decremented
            assert flour_inv.quantity < initial_flour_qty, "Flour should be consumed"
            assert sugar_inv.quantity < initial_sugar_qty, "Sugar should be consumed"

            # FinishedUnit should be incremented
            assert fu.inventory_count == initial_fu_count + 48, "FinishedUnit should be incremented"

        # Verify ProductionRun exists
        with session_scope() as session:
            run = session.query(ProductionRun).filter_by(id=result["production_run_id"]).first()
            assert run is not None, "ProductionRun should exist"
            assert run.actual_yield == 48

        # Verify consumption records exist
        with session_scope() as session:
            consumptions = session.query(ProductionConsumption).filter_by(
                production_run_id=result["production_run_id"]
            ).all()
            assert len(consumptions) == 2, "Should have 2 consumption records (flour + sugar)"


# =============================================================================
# Tests for Event ID Parameter (Feature 016)
# =============================================================================


class TestRecordBatchProductionEventId:
    """Tests for event_id parameter in record_batch_production().

    Feature 016: Event-Centric Production Model
    """

    @pytest.fixture
    def event_christmas(self, test_db):
        """Create a Christmas 2024 event."""
        from src.models import Event
        from datetime import date

        session = test_db()
        event = Event(
            name="Christmas 2024",
            event_date=date(2024, 12, 25),
            year=2024,
        )
        session.add(event)
        session.commit()
        return event

    def test_record_production_with_event_id(
        self,
        recipe_with_ingredients_and_inventory,
        finished_unit_cookies,
        inventory_flour,
        inventory_sugar,
        event_christmas,
    ):
        """Production run links to event when event_id provided."""
        recipe = recipe_with_ingredients_and_inventory

        result = batch_production_service.record_batch_production(
            recipe_id=recipe.id,
            finished_unit_id=finished_unit_cookies.id,
            num_batches=1,
            actual_yield=48,
            event_id=event_christmas.id,
        )

        assert result["event_id"] == event_christmas.id

        # Verify in database
        with session_scope() as session:
            pr = session.query(ProductionRun).filter_by(id=result["production_run_id"]).first()
            assert pr.event_id == event_christmas.id

    def test_record_production_without_event_id(
        self,
        recipe_with_ingredients_and_inventory,
        finished_unit_cookies,
        inventory_flour,
        inventory_sugar,
    ):
        """Production run has null event_id when not provided (backward compatible)."""
        recipe = recipe_with_ingredients_and_inventory

        result = batch_production_service.record_batch_production(
            recipe_id=recipe.id,
            finished_unit_id=finished_unit_cookies.id,
            num_batches=1,
            actual_yield=48,
        )

        assert result["event_id"] is None

        # Verify in database
        with session_scope() as session:
            pr = session.query(ProductionRun).filter_by(id=result["production_run_id"]).first()
            assert pr.event_id is None

    def test_record_production_invalid_event_id(
        self,
        recipe_with_ingredients_and_inventory,
        finished_unit_cookies,
        inventory_flour,
        inventory_sugar,
    ):
        """ValueError raised for non-existent event_id."""
        from src.services.batch_production_service import EventNotFoundError

        recipe = recipe_with_ingredients_and_inventory

        with pytest.raises(EventNotFoundError) as exc_info:
            batch_production_service.record_batch_production(
                recipe_id=recipe.id,
                finished_unit_id=finished_unit_cookies.id,
                num_batches=1,
                actual_yield=48,
                event_id=99999,
            )
        assert exc_info.value.event_id == 99999
