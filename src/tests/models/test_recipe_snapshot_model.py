"""
Unit tests for RecipeSnapshot model and Recipe model updates (Feature 037).

Tests cover:
- RecipeSnapshot creation and JSON serialization
- Recipe variant relationships (base_recipe_id, variant_name)
- Recipe is_production_ready field
- Constraint validations
"""

import json
import pytest
from sqlalchemy.exc import IntegrityError

from src.models import Recipe, RecipeSnapshot, ProductionRun
from src.models.finished_unit import FinishedUnit


@pytest.fixture
def sample_recipe(test_db):
    """Create a sample recipe for testing.

    F056: yield_quantity, yield_unit, yield_description removed from Recipe model.
    """
    session = test_db()
    recipe = Recipe(
        name="Test Thumbprint Cookies",
        category="Cookies",
        estimated_time_minutes=45,
        notes="Test recipe for snapshots",
    )
    session.add(recipe)
    session.commit()
    return recipe


@pytest.fixture
def sample_finished_unit(test_db, sample_recipe):
    """Create a sample finished unit for production runs.

    F056: This now holds the yield data that used to be on Recipe.
    """
    session = test_db()
    finished_unit = FinishedUnit(
        recipe_id=sample_recipe.id,
        slug="test-thumbprint-cookie",
        display_name="2-inch cookies",  # Was yield_description
        items_per_batch=36,  # Was yield_quantity
        item_unit="cookies",  # Was yield_unit
    )
    session.add(finished_unit)
    session.commit()
    return finished_unit


@pytest.fixture
def sample_production_run(test_db, sample_recipe, sample_finished_unit):
    """Create a sample production run for snapshot testing."""
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
    """Tests for basic RecipeSnapshot creation."""

    def test_create_recipe_snapshot(self, test_db, sample_recipe, sample_production_run):
        """Test creating a recipe snapshot with valid data."""
        session = test_db()

        recipe_data = json.dumps({
            "name": "Test Thumbprint Cookies",
            "category": "Cookies",
            "yield_quantity": 36,
            "yield_unit": "cookies",
        })

        ingredients_data = json.dumps([
            {"ingredient_name": "Flour", "quantity": 2, "unit": "cups"},
            {"ingredient_name": "Butter", "quantity": 1, "unit": "cup"},
        ])

        snapshot = RecipeSnapshot(
            recipe_id=sample_recipe.id,
            production_run_id=sample_production_run.id,
            scale_factor=1.0,
            recipe_data=recipe_data,
            ingredients_data=ingredients_data,
        )
        session.add(snapshot)
        session.commit()

        assert snapshot.id is not None
        assert snapshot.recipe_id == sample_recipe.id
        assert snapshot.production_run_id == sample_production_run.id
        assert snapshot.scale_factor == 1.0
        assert snapshot.is_backfilled is False  # Default
        assert snapshot.snapshot_date is not None

    def test_snapshot_default_scale_factor(self, test_db, sample_recipe, sample_production_run):
        """Test that scale_factor defaults to 1.0."""
        session = test_db()

        snapshot = RecipeSnapshot(
            recipe_id=sample_recipe.id,
            production_run_id=sample_production_run.id,
            recipe_data="{}",
            ingredients_data="[]",
        )
        session.add(snapshot)
        session.commit()

        assert snapshot.scale_factor == 1.0


class TestSnapshotJsonSerialization:
    """Tests for JSON serialization/deserialization helpers."""

    def test_get_recipe_data(self, test_db, sample_recipe, sample_production_run):
        """Test get_recipe_data() parses JSON correctly."""
        session = test_db()

        recipe_data = {
            "name": "Test Recipe",
            "category": "Cookies",
            "yield_quantity": 36,
        }

        snapshot = RecipeSnapshot(
            recipe_id=sample_recipe.id,
            production_run_id=sample_production_run.id,
            recipe_data=json.dumps(recipe_data),
            ingredients_data="[]",
        )
        session.add(snapshot)
        session.commit()

        parsed = snapshot.get_recipe_data()
        assert parsed["name"] == "Test Recipe"
        assert parsed["category"] == "Cookies"
        assert parsed["yield_quantity"] == 36

    def test_get_ingredients_data(self, test_db, sample_recipe, sample_production_run):
        """Test get_ingredients_data() parses JSON correctly."""
        session = test_db()

        ingredients_data = [
            {"ingredient_name": "Flour", "quantity": 2, "unit": "cups"},
            {"ingredient_name": "Sugar", "quantity": 1, "unit": "cup"},
        ]

        snapshot = RecipeSnapshot(
            recipe_id=sample_recipe.id,
            production_run_id=sample_production_run.id,
            recipe_data="{}",
            ingredients_data=json.dumps(ingredients_data),
        )
        session.add(snapshot)
        session.commit()

        parsed = snapshot.get_ingredients_data()
        assert len(parsed) == 2
        assert parsed[0]["ingredient_name"] == "Flour"
        assert parsed[1]["quantity"] == 1

    def test_get_recipe_data_handles_empty(self, test_db, sample_recipe, sample_production_run):
        """Test get_recipe_data() handles empty string gracefully."""
        session = test_db()

        snapshot = RecipeSnapshot(
            recipe_id=sample_recipe.id,
            production_run_id=sample_production_run.id,
            recipe_data="",
            ingredients_data="[]",
        )
        session.add(snapshot)
        session.commit()

        # Empty string should return empty dict
        parsed = snapshot.get_recipe_data()
        assert parsed == {}

    def test_get_ingredients_data_handles_invalid_json(self, test_db, sample_recipe, sample_production_run):
        """Test get_ingredients_data() handles invalid JSON gracefully."""
        session = test_db()

        snapshot = RecipeSnapshot(
            recipe_id=sample_recipe.id,
            production_run_id=sample_production_run.id,
            recipe_data="{}",
            ingredients_data="not valid json",
        )
        session.add(snapshot)
        session.commit()

        # Invalid JSON should return empty list
        parsed = snapshot.get_ingredients_data()
        assert parsed == []


class TestRecipeSelfReferenceBlocked:
    """Tests for CHECK constraint preventing self-referential variants."""

    def test_recipe_self_reference_blocked(self, test_db):
        """Test that base_recipe_id cannot equal recipe id."""
        session = test_db()

        # F056: yield_quantity, yield_unit removed from Recipe model
        recipe = Recipe(
            name="Test Recipe",
            category="Cookies",
        )
        session.add(recipe)
        session.commit()

        # Try to set base_recipe_id to self
        recipe.base_recipe_id = recipe.id

        # SQLite CHECK constraint should prevent this
        with pytest.raises(IntegrityError):
            session.commit()


class TestRecipeVariantRelationship:
    """Tests for variant relationships."""

    def test_recipe_variant_relationship(self, test_db):
        """Test that variant links to base correctly."""
        session = test_db()

        # Create base recipe (F056: yield fields removed)
        base_recipe = Recipe(
            name="Thumbprint Cookies",
            category="Cookies",
        )
        session.add(base_recipe)
        session.commit()

        # Create variant (F056: yield fields removed)
        variant = Recipe(
            name="Raspberry Thumbprint Cookies",
            category="Cookies",
            base_recipe_id=base_recipe.id,
            variant_name="Raspberry",
        )
        session.add(variant)
        session.commit()

        # Verify relationship
        assert variant.base_recipe_id == base_recipe.id
        assert variant.variant_name == "Raspberry"
        assert variant.base_recipe.name == "Thumbprint Cookies"

        # Verify reverse relationship (variants backref)
        session.refresh(base_recipe)
        assert len(base_recipe.variants) == 1
        assert base_recipe.variants[0].id == variant.id

    def test_variant_orphaned_on_base_delete(self, test_db):
        """Test that variant becomes standalone when base is deleted (SET NULL)."""
        session = test_db()

        # Create base recipe (F056: yield fields removed)
        base_recipe = Recipe(
            name="Base Recipe",
            category="Cookies",
        )
        session.add(base_recipe)
        session.commit()
        base_id = base_recipe.id

        # Create variant (F056: yield fields removed)
        variant = Recipe(
            name="Variant Recipe",
            category="Cookies",
            base_recipe_id=base_id,
            variant_name="Test Variant",
        )
        session.add(variant)
        session.commit()
        variant_id = variant.id

        # Delete base recipe
        session.delete(base_recipe)
        session.commit()

        # Variant should still exist with base_recipe_id = NULL
        variant = session.query(Recipe).filter_by(id=variant_id).first()
        assert variant is not None
        assert variant.base_recipe_id is None  # SET NULL worked


class TestRecipeProductionReadyDefault:
    """Tests for is_production_ready field."""

    def test_recipe_production_ready_default(self, test_db):
        """Test that new recipes default to experimental (is_production_ready=False)."""
        session = test_db()

        # F056: yield_quantity, yield_unit removed from Recipe model
        recipe = Recipe(
            name="New Recipe",
            category="Cookies",
        )
        session.add(recipe)
        session.commit()

        assert recipe.is_production_ready is False

    def test_recipe_production_ready_toggle(self, test_db):
        """Test that is_production_ready can be toggled."""
        session = test_db()

        # F056: yield_quantity, yield_unit removed from Recipe model
        recipe = Recipe(
            name="New Recipe",
            category="Cookies",
        )
        session.add(recipe)
        session.commit()

        # Toggle to ready
        recipe.is_production_ready = True
        session.commit()

        session.refresh(recipe)
        assert recipe.is_production_ready is True


class TestSnapshotRecipeDeleteBlocked:
    """Tests for ON DELETE RESTRICT on recipe_id."""

    def test_snapshot_recipe_delete_blocked(self, test_db, sample_recipe, sample_production_run):
        """Test that recipe with snapshots cannot be deleted."""
        session = test_db()

        # Create snapshot
        snapshot = RecipeSnapshot(
            recipe_id=sample_recipe.id,
            production_run_id=sample_production_run.id,
            recipe_data="{}",
            ingredients_data="[]",
        )
        session.add(snapshot)
        session.commit()

        # Try to delete recipe - should be blocked by RESTRICT
        with pytest.raises(IntegrityError):
            session.delete(sample_recipe)
            session.commit()


class TestProductionRunSnapshotRelationship:
    """Tests for ProductionRun to RecipeSnapshot relationship."""

    def test_production_run_snapshot_relationship(self, test_db, sample_recipe, sample_production_run):
        """Test 1:1 relationship between ProductionRun and RecipeSnapshot."""
        session = test_db()

        snapshot = RecipeSnapshot(
            recipe_id=sample_recipe.id,
            production_run_id=sample_production_run.id,
            recipe_data="{}",
            ingredients_data="[]",
        )
        session.add(snapshot)
        session.commit()

        # Verify relationship from ProductionRun side
        session.refresh(sample_production_run)
        assert sample_production_run.snapshot is not None
        assert sample_production_run.snapshot.id == snapshot.id

        # Verify relationship from RecipeSnapshot side
        assert snapshot.production_run.id == sample_production_run.id

    def test_production_run_snapshot_unique_constraint(
        self, test_db, sample_recipe, sample_production_run
    ):
        """Test that production_run_id is unique (1:1 relationship)."""
        session = test_db()

        # Create first snapshot
        snapshot1 = RecipeSnapshot(
            recipe_id=sample_recipe.id,
            production_run_id=sample_production_run.id,
            recipe_data="{}",
            ingredients_data="[]",
        )
        session.add(snapshot1)
        session.commit()

        # Try to create second snapshot for same production run
        snapshot2 = RecipeSnapshot(
            recipe_id=sample_recipe.id,
            production_run_id=sample_production_run.id,  # Same production_run_id
            recipe_data="{}",
            ingredients_data="[]",
        )
        session.add(snapshot2)

        with pytest.raises(IntegrityError):
            session.commit()


class TestRecipeSnapshotToDict:
    """Tests for RecipeSnapshot.to_dict() method."""

    def test_snapshot_to_dict(self, test_db, sample_recipe, sample_production_run):
        """Test to_dict() includes parsed JSON data."""
        session = test_db()

        recipe_data = {"name": "Test", "yield_quantity": 36}
        ingredients_data = [{"ingredient_name": "Flour", "quantity": 2}]

        snapshot = RecipeSnapshot(
            recipe_id=sample_recipe.id,
            production_run_id=sample_production_run.id,
            scale_factor=1.5,
            recipe_data=json.dumps(recipe_data),
            ingredients_data=json.dumps(ingredients_data),
            is_backfilled=True,
        )
        session.add(snapshot)
        session.commit()

        result = snapshot.to_dict()

        # Verify base fields
        assert result["id"] == snapshot.id
        assert result["recipe_id"] == sample_recipe.id
        assert result["scale_factor"] == 1.5
        assert result["is_backfilled"] is True

        # Verify parsed JSON fields
        assert result["recipe_data_parsed"]["name"] == "Test"
        assert len(result["ingredients_data_parsed"]) == 1
        assert result["ingredients_data_parsed"][0]["ingredient_name"] == "Flour"
