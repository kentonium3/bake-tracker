"""
Unit tests for Recipe Snapshot Service (Feature 037).

Tests cover:
- create_recipe_snapshot() with session management
- get_recipe_snapshots() history retrieval
- get_snapshot_by_production_run() lookup
- Error handling and edge cases
"""

import pytest

from src.models import Recipe, RecipeSnapshot, ProductionRun, Ingredient
from src.models.finished_unit import FinishedUnit
from src.models.recipe import RecipeIngredient
from src.services import recipe_snapshot_service
from src.services.recipe_snapshot_service import SnapshotCreationError


@pytest.fixture
def sample_ingredient(test_db):
    """Create a sample ingredient for testing."""
    session = test_db()
    ingredient = Ingredient(
        slug="test-flour",
        display_name="Test Flour",
        category="Flour",
    )
    session.add(ingredient)
    session.commit()
    return ingredient


@pytest.fixture
def sample_recipe(test_db, sample_ingredient):
    """Create a sample recipe with ingredients for testing.

    F056: yield_quantity, yield_unit, yield_description removed from Recipe model.
    Yield data is now on FinishedUnit (see sample_finished_unit fixture).
    """
    session = test_db()
    recipe = Recipe(
        name="Test Cookie Recipe",
        category="Cookies",
        estimated_time_minutes=45,
        notes="Test recipe for snapshots",
    )
    session.add(recipe)
    session.flush()

    # Add ingredient
    recipe_ingredient = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=sample_ingredient.id,
        quantity=2.0,
        unit="cups",
        notes="sifted",
    )
    session.add(recipe_ingredient)
    session.commit()

    return recipe


@pytest.fixture
def sample_finished_unit(test_db, sample_recipe):
    """Create a sample finished unit with yield data.

    F056: Yield data (items_per_batch, item_unit, display_name) is now on FinishedUnit.
    """
    session = test_db()
    finished_unit = FinishedUnit(
        recipe_id=sample_recipe.id,
        slug="test-cookie",
        display_name="2-inch cookies",  # This serves as yield_description
        items_per_batch=36,  # This serves as yield_quantity
        item_unit="cookies",  # This serves as yield_unit
    )
    session.add(finished_unit)
    session.commit()
    return finished_unit


@pytest.fixture
def sample_production_run(test_db, sample_recipe, sample_finished_unit):
    """Create a sample production run."""
    session = test_db()
    production_run = ProductionRun(
        recipe_id=sample_recipe.id,
        finished_unit_id=sample_finished_unit.id,
        num_batches=1,
        expected_yield=36,
        actual_yield=36,
    )
    session.add(production_run)
    session.commit()
    return production_run


class TestCreateRecipeSnapshot:
    """Tests for create_recipe_snapshot()."""

    def test_create_snapshot_success(self, test_db, sample_recipe, sample_production_run):
        """Test successful snapshot creation."""
        result = recipe_snapshot_service.create_recipe_snapshot(
            recipe_id=sample_recipe.id,
            scale_factor=1.0,
            production_run_id=sample_production_run.id,
        )

        assert result["id"] is not None
        assert result["recipe_id"] == sample_recipe.id
        assert result["production_run_id"] == sample_production_run.id
        assert result["scale_factor"] == 1.0
        assert result["is_backfilled"] is False

    def test_create_snapshot_recipe_not_found(self, test_db, sample_production_run):
        """Test error handling when recipe doesn't exist."""
        with pytest.raises(SnapshotCreationError) as exc_info:
            recipe_snapshot_service.create_recipe_snapshot(
                recipe_id=99999,  # Non-existent
                scale_factor=1.0,
                production_run_id=sample_production_run.id,
            )

        assert "not found" in str(exc_info.value)

    def test_create_snapshot_denormalizes_data(
        self, test_db, sample_recipe, sample_production_run, sample_ingredient
    ):
        """Test that snapshot contains denormalized recipe data.

        F056: yield_quantity, yield_unit, yield_description are populated from
        the recipe's FinishedUnit (sample_finished_unit fixture).
        """
        result = recipe_snapshot_service.create_recipe_snapshot(
            recipe_id=sample_recipe.id,
            scale_factor=1.5,
            production_run_id=sample_production_run.id,
        )

        # Check recipe_data - yield data now comes from FinishedUnit
        recipe_data = result["recipe_data"]
        assert recipe_data["name"] == "Test Cookie Recipe"
        assert recipe_data["category"] == "Cookies"
        assert recipe_data["yield_quantity"] == 36  # From FinishedUnit.items_per_batch
        assert recipe_data["yield_unit"] == "cookies"  # From FinishedUnit.item_unit
        assert (
            recipe_data["yield_description"] == "2-inch cookies"
        )  # From FinishedUnit.display_name

        # Check ingredients_data
        ingredients_data = result["ingredients_data"]
        assert len(ingredients_data) == 1
        assert ingredients_data[0]["ingredient_name"] == "Test Flour"
        assert ingredients_data[0]["quantity"] == 2.0
        assert ingredients_data[0]["unit"] == "cups"
        assert ingredients_data[0]["notes"] == "sifted"

    def test_create_snapshot_with_session(self, test_db, sample_recipe, sample_production_run):
        """Test that session parameter is used correctly."""
        session = test_db()

        result = recipe_snapshot_service.create_recipe_snapshot(
            recipe_id=sample_recipe.id,
            scale_factor=1.0,
            production_run_id=sample_production_run.id,
            session=session,
        )

        # Verify snapshot was created in the provided session
        assert result["id"] is not None

        # Commit the session to persist
        session.commit()

        # Verify it persists
        snapshot = session.query(RecipeSnapshot).filter_by(id=result["id"]).first()
        assert snapshot is not None

    def test_create_snapshot_scale_factor(self, test_db, sample_recipe, sample_production_run):
        """Test that scale factor is stored correctly."""
        result = recipe_snapshot_service.create_recipe_snapshot(
            recipe_id=sample_recipe.id,
            scale_factor=2.5,
            production_run_id=sample_production_run.id,
        )

        assert result["scale_factor"] == 2.5


class TestGetRecipeSnapshots:
    """Tests for get_recipe_snapshots()."""

    def test_get_snapshots_empty(self, test_db, sample_recipe):
        """Test that empty list is returned when no snapshots exist."""
        result = recipe_snapshot_service.get_recipe_snapshots(sample_recipe.id)
        assert result == []

    def test_get_snapshots_ordered(self, test_db, sample_recipe, sample_finished_unit):
        """Test that snapshots are ordered by date descending."""
        session = test_db()

        # Create multiple production runs and snapshots
        for i in range(3):
            pr = ProductionRun(
                recipe_id=sample_recipe.id,
                finished_unit_id=sample_finished_unit.id,
                num_batches=1,
                expected_yield=36,
                actual_yield=36,
            )
            session.add(pr)
            session.flush()

            recipe_snapshot_service.create_recipe_snapshot(
                recipe_id=sample_recipe.id,
                scale_factor=1.0 + i,
                production_run_id=pr.id,
                session=session,
            )

        session.commit()

        # Get snapshots
        snapshots = recipe_snapshot_service.get_recipe_snapshots(sample_recipe.id)

        # Verify order (newest first - highest scale_factor should be first)
        assert len(snapshots) == 3
        assert snapshots[0]["scale_factor"] == 3.0
        assert snapshots[1]["scale_factor"] == 2.0
        assert snapshots[2]["scale_factor"] == 1.0

    def test_get_snapshots_with_session(self, test_db, sample_recipe, sample_production_run):
        """Test that session parameter works correctly."""
        session = test_db()

        # Create snapshot using the session
        recipe_snapshot_service.create_recipe_snapshot(
            recipe_id=sample_recipe.id,
            scale_factor=1.0,
            production_run_id=sample_production_run.id,
            session=session,
        )
        session.commit()

        # Get snapshots using the session
        snapshots = recipe_snapshot_service.get_recipe_snapshots(sample_recipe.id, session=session)

        assert len(snapshots) == 1


class TestGetSnapshotByProductionRun:
    """Tests for get_snapshot_by_production_run()."""

    def test_get_by_production_run_found(self, test_db, sample_recipe, sample_production_run):
        """Test successful retrieval by production run ID."""
        # Create snapshot
        created = recipe_snapshot_service.create_recipe_snapshot(
            recipe_id=sample_recipe.id,
            scale_factor=1.5,
            production_run_id=sample_production_run.id,
        )

        # Retrieve by production run
        result = recipe_snapshot_service.get_snapshot_by_production_run(sample_production_run.id)

        assert result is not None
        assert result["id"] == created["id"]
        assert result["production_run_id"] == sample_production_run.id
        assert result["scale_factor"] == 1.5

    def test_get_by_production_run_not_found(self, test_db):
        """Test that None is returned when not found."""
        result = recipe_snapshot_service.get_snapshot_by_production_run(99999)
        assert result is None

    def test_get_by_production_run_with_session(
        self, test_db, sample_recipe, sample_production_run
    ):
        """Test that session parameter works correctly."""
        session = test_db()

        # Create snapshot
        recipe_snapshot_service.create_recipe_snapshot(
            recipe_id=sample_recipe.id,
            scale_factor=1.0,
            production_run_id=sample_production_run.id,
            session=session,
        )
        session.commit()

        # Get by production run using session
        result = recipe_snapshot_service.get_snapshot_by_production_run(
            sample_production_run.id, session=session
        )

        assert result is not None


class TestGetSnapshotById:
    """Tests for get_snapshot_by_id()."""

    def test_get_by_id_found(self, test_db, sample_recipe, sample_production_run):
        """Test successful retrieval by snapshot ID."""
        created = recipe_snapshot_service.create_recipe_snapshot(
            recipe_id=sample_recipe.id,
            scale_factor=1.0,
            production_run_id=sample_production_run.id,
        )

        result = recipe_snapshot_service.get_snapshot_by_id(created["id"])

        assert result is not None
        assert result["id"] == created["id"]

    def test_get_by_id_not_found(self, test_db):
        """Test that None is returned when not found."""
        result = recipe_snapshot_service.get_snapshot_by_id(99999)
        assert result is None


class TestSnapshotImmutability:
    """Tests to verify snapshot immutability."""

    def test_no_update_methods_exist(self):
        """Verify that no update methods are exposed."""
        # These methods should NOT exist
        assert not hasattr(recipe_snapshot_service, "update_recipe_snapshot")
        assert not hasattr(recipe_snapshot_service, "update_snapshot")
        assert not hasattr(recipe_snapshot_service, "modify_snapshot")

    def test_no_delete_methods_exist(self):
        """Verify that no delete methods are exposed."""
        assert not hasattr(recipe_snapshot_service, "delete_recipe_snapshot")
        assert not hasattr(recipe_snapshot_service, "delete_snapshot")
        assert not hasattr(recipe_snapshot_service, "remove_snapshot")


class TestCreateRecipeFromSnapshot:
    """Tests for create_recipe_from_snapshot()."""

    def test_create_recipe_from_snapshot_success(
        self, test_db, sample_recipe, sample_production_run, sample_ingredient
    ):
        """Test successful recipe creation from snapshot."""
        # First create a snapshot
        snapshot = recipe_snapshot_service.create_recipe_snapshot(
            recipe_id=sample_recipe.id,
            scale_factor=1.0,
            production_run_id=sample_production_run.id,
        )

        # Create recipe from snapshot
        result = recipe_snapshot_service.create_recipe_from_snapshot(snapshot["id"])

        assert result["id"] is not None
        assert "(restored" in result["name"]
        assert "Test Cookie Recipe" in result["name"]
        assert result["category"] == "Cookies"

    def test_create_recipe_from_snapshot_not_production_ready(
        self, test_db, sample_recipe, sample_production_run
    ):
        """Test that restored recipes are not production ready."""
        session = test_db()

        # Create snapshot
        snapshot = recipe_snapshot_service.create_recipe_snapshot(
            recipe_id=sample_recipe.id,
            scale_factor=1.0,
            production_run_id=sample_production_run.id,
        )

        # Create recipe from snapshot
        result = recipe_snapshot_service.create_recipe_from_snapshot(snapshot["id"])

        # Verify not production ready
        restored_recipe = session.query(Recipe).filter_by(id=result["id"]).first()
        assert restored_recipe is not None
        assert restored_recipe.is_production_ready is False

    def test_create_recipe_from_snapshot_restores_ingredients(
        self, test_db, sample_recipe, sample_production_run, sample_ingredient
    ):
        """Test that ingredients are restored from snapshot."""
        session = test_db()

        # Create snapshot
        snapshot = recipe_snapshot_service.create_recipe_snapshot(
            recipe_id=sample_recipe.id,
            scale_factor=1.0,
            production_run_id=sample_production_run.id,
        )

        # Create recipe from snapshot
        result = recipe_snapshot_service.create_recipe_from_snapshot(snapshot["id"])

        # Verify ingredients were restored
        restored_recipe = session.query(Recipe).filter_by(id=result["id"]).first()
        assert len(restored_recipe.recipe_ingredients) == 1
        ri = restored_recipe.recipe_ingredients[0]
        assert ri.ingredient_id == sample_ingredient.id
        assert ri.quantity == 2.0
        assert ri.unit == "cups"

    def test_create_recipe_from_snapshot_preserves_notes(
        self, test_db, sample_recipe, sample_production_run
    ):
        """Test that notes include restoration info and original notes."""
        session = test_db()

        # Create snapshot
        snapshot = recipe_snapshot_service.create_recipe_snapshot(
            recipe_id=sample_recipe.id,
            scale_factor=1.0,
            production_run_id=sample_production_run.id,
        )

        # Create recipe from snapshot
        result = recipe_snapshot_service.create_recipe_from_snapshot(snapshot["id"])

        # Verify notes contain restoration info
        restored_recipe = session.query(Recipe).filter_by(id=result["id"]).first()
        assert f"Restored from snapshot {snapshot['id']}" in restored_recipe.notes
        assert "Test recipe for snapshots" in restored_recipe.notes

    def test_create_recipe_from_snapshot_not_found(self, test_db):
        """Test error handling when snapshot doesn't exist."""
        with pytest.raises(ValueError) as exc_info:
            recipe_snapshot_service.create_recipe_from_snapshot(99999)

        assert "not found" in str(exc_info.value)

    def test_create_recipe_from_snapshot_with_session(
        self, test_db, sample_recipe, sample_production_run
    ):
        """Test that session parameter is used correctly."""
        session = test_db()

        # Create snapshot
        snapshot = recipe_snapshot_service.create_recipe_snapshot(
            recipe_id=sample_recipe.id,
            scale_factor=1.0,
            production_run_id=sample_production_run.id,
            session=session,
        )
        session.commit()

        # Create recipe from snapshot using session
        result = recipe_snapshot_service.create_recipe_from_snapshot(
            snapshot["id"], session=session
        )

        assert result["id"] is not None

    def test_create_recipe_from_snapshot_copies_yield_info(
        self, test_db, sample_recipe, sample_production_run
    ):
        """Test that yield information is copied from snapshot to FinishedUnit.

        F056: yield_quantity, yield_unit, yield_description removed from Recipe model.
        Restored recipes now get a FinishedUnit created with the yield data.
        """
        session = test_db()

        # Create snapshot
        snapshot = recipe_snapshot_service.create_recipe_snapshot(
            recipe_id=sample_recipe.id,
            scale_factor=1.0,
            production_run_id=sample_production_run.id,
        )

        # Create recipe from snapshot
        result = recipe_snapshot_service.create_recipe_from_snapshot(snapshot["id"])

        # Verify yield info copied to FinishedUnit
        restored_recipe = session.query(Recipe).filter_by(id=result["id"]).first()
        assert restored_recipe is not None

        # Check that a FinishedUnit was created with the yield data
        fu = session.query(FinishedUnit).filter_by(recipe_id=restored_recipe.id).first()
        assert fu is not None
        assert fu.items_per_batch == 36
        assert fu.item_unit == "cookies"
        assert fu.display_name == "2-inch cookies"
