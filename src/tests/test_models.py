"""
Tests for database models.

Tests cover:
- Model creation and persistence
- Relationships between models
- Calculated properties
- Cost calculations
- Unit conversions
- CRUD operations
"""

import pytest
from datetime import datetime

from src.models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    InventorySnapshot,
    SnapshotIngredient,
)
from src.services.database import get_session, init_database, get_engine


@pytest.fixture(scope="function")
def db_session():
    """
    Create a test database session.

    This fixture creates an in-memory database for each test,
    ensuring tests are isolated.
    """
    # Create in-memory database
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.models.base import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()


class TestIngredientModel:
    """Tests for Ingredient model."""

    def test_create_ingredient(self, db_session):
        """Test creating an ingredient."""
        ingredient = Ingredient(
            name="Flour",
            brand="King Arthur",
            category="Flour",
            purchase_unit="bag",
            purchase_unit_size="50 lb",
            recipe_unit="cup",
            conversion_factor=200.0,
            quantity=2.5,
            unit_cost=15.99,
            notes="Test notes",
        )
        db_session.add(ingredient)
        db_session.commit()

        assert ingredient.id is not None
        assert ingredient.name == "Flour"
        assert ingredient.quantity == 2.5

    def test_ingredient_total_value(self, db_session):
        """Test total value calculation."""
        ingredient = Ingredient(
            name="Sugar",
            category="Sugar",
            purchase_unit="bag",
            recipe_unit="cup",
            conversion_factor=20.0,
            quantity=5.0,
            unit_cost=10.00,
        )
        assert ingredient.total_value == 50.00

    def test_ingredient_available_recipe_units(self, db_session):
        """Test available recipe units calculation."""
        ingredient = Ingredient(
            name="Flour",
            category="Flour",
            purchase_unit="bag",
            recipe_unit="cup",
            conversion_factor=200.0,
            quantity=2.0,
            unit_cost=15.00,
        )
        assert ingredient.available_recipe_units == 400.0

    def test_convert_to_recipe_units(self, db_session):
        """Test conversion from purchase to recipe units."""
        ingredient = Ingredient(
            name="Flour",
            category="Flour",
            purchase_unit="bag",
            recipe_unit="cup",
            conversion_factor=200.0,
            quantity=1.0,
            unit_cost=15.00,
        )
        assert ingredient.convert_to_recipe_units(1.0) == 200.0
        assert ingredient.convert_to_recipe_units(0.5) == 100.0

    def test_convert_from_recipe_units(self, db_session):
        """Test conversion from recipe to purchase units."""
        ingredient = Ingredient(
            name="Flour",
            category="Flour",
            purchase_unit="bag",
            recipe_unit="cup",
            conversion_factor=200.0,
            quantity=1.0,
            unit_cost=15.00,
        )
        assert ingredient.convert_from_recipe_units(200.0) == 1.0
        assert ingredient.convert_from_recipe_units(100.0) == 0.5

    def test_get_cost_per_recipe_unit(self, db_session):
        """Test cost per recipe unit calculation."""
        ingredient = Ingredient(
            name="Flour",
            category="Flour",
            purchase_unit="bag",
            recipe_unit="cup",
            conversion_factor=200.0,
            quantity=1.0,
            unit_cost=20.00,
        )
        # $20 per bag / 200 cups per bag = $0.10 per cup
        assert ingredient.get_cost_per_recipe_unit() == 0.10

    def test_update_quantity(self, db_session):
        """Test updating quantity."""
        ingredient = Ingredient(
            name="Flour",
            category="Flour",
            purchase_unit="bag",
            recipe_unit="cup",
            conversion_factor=200.0,
            quantity=1.0,
            unit_cost=15.00,
        )
        db_session.add(ingredient)
        db_session.flush()  # Ensure default timestamp is set
        old_updated = ingredient.last_updated
        ingredient.update_quantity(2.5)
        assert ingredient.quantity == 2.5
        assert ingredient.last_updated >= old_updated

    def test_adjust_quantity(self, db_session):
        """Test adjusting quantity by delta."""
        ingredient = Ingredient(
            name="Flour",
            category="Flour",
            purchase_unit="bag",
            recipe_unit="cup",
            conversion_factor=200.0,
            quantity=5.0,
            unit_cost=15.00,
        )
        ingredient.adjust_quantity(-1.5)
        assert ingredient.quantity == 3.5

        ingredient.adjust_quantity(2.0)
        assert ingredient.quantity == 5.5

    def test_ingredient_to_dict(self, db_session):
        """Test dictionary serialization."""
        ingredient = Ingredient(
            name="Flour",
            category="Flour",
            purchase_unit="bag",
            recipe_unit="cup",
            conversion_factor=200.0,
            quantity=2.0,
            unit_cost=15.00,
        )
        data = ingredient.to_dict()

        assert data["name"] == "Flour"
        assert data["quantity"] == 2.0
        assert "total_value" in data
        assert "available_recipe_units" in data
        assert data["total_value"] == 30.00
        assert data["available_recipe_units"] == 400.0


class TestRecipeModel:
    """Tests for Recipe model."""

    def test_create_recipe(self, db_session):
        """Test creating a recipe."""
        recipe = Recipe(
            name="Chocolate Chip Cookies",
            category="Cookies",
            source="Test",
            yield_quantity=48,
            yield_unit="cookies",
            yield_description="2-inch cookies",
            estimated_time_minutes=45,
        )
        db_session.add(recipe)
        db_session.commit()

        assert recipe.id is not None
        assert recipe.name == "Chocolate Chip Cookies"
        assert recipe.yield_quantity == 48

    def test_recipe_with_ingredients(self, db_session):
        """Test recipe with ingredients and cost calculation."""
        # Create ingredient
        flour = Ingredient(
            name="Flour",
            category="Flour",
            purchase_unit="bag",
            recipe_unit="cup",
            conversion_factor=200.0,
            quantity=5.0,
            unit_cost=20.00,  # $20 per bag, $0.10 per cup
        )
        db_session.add(flour)
        db_session.flush()

        # Create recipe
        recipe = Recipe(
            name="Cookies",
            category="Cookies",
            yield_quantity=24,
            yield_unit="cookies",
        )
        db_session.add(recipe)
        db_session.flush()

        # Add ingredient to recipe
        recipe_ingredient = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=flour.id,
            quantity=2.0,  # 2 cups
            unit="cup",
        )
        db_session.add(recipe_ingredient)
        db_session.commit()

        # Refresh to load relationships
        db_session.refresh(recipe)

        # Cost should be: 2 cups × $0.10/cup = $0.20
        assert recipe.calculate_cost() == pytest.approx(0.20, rel=1e-6)

    def test_recipe_cost_per_unit(self, db_session):
        """Test cost per unit calculation."""
        # Create ingredients
        flour = Ingredient(
            name="Flour",
            category="Flour",
            purchase_unit="bag",
            recipe_unit="cup",
            conversion_factor=100.0,
            quantity=5.0,
            unit_cost=10.00,  # $0.10 per cup
        )
        sugar = Ingredient(
            name="Sugar",
            category="Sugar",
            purchase_unit="bag",
            recipe_unit="cup",
            conversion_factor=20.0,
            quantity=3.0,
            unit_cost=8.00,  # $0.40 per cup
        )
        db_session.add_all([flour, sugar])
        db_session.flush()

        # Create recipe
        recipe = Recipe(
            name="Cookies",
            category="Cookies",
            yield_quantity=48,
            yield_unit="cookies",
        )
        db_session.add(recipe)
        db_session.flush()

        # Add ingredients: 2 cups flour + 1 cup sugar
        db_session.add_all(
            [
                RecipeIngredient(
                    recipe_id=recipe.id, ingredient_id=flour.id, quantity=2.0, unit="cup"
                ),
                RecipeIngredient(
                    recipe_id=recipe.id, ingredient_id=sugar.id, quantity=1.0, unit="cup"
                ),
            ]
        )
        db_session.commit()
        db_session.refresh(recipe)

        # Total: (2 × $0.10) + (1 × $0.40) = $0.60
        # Per unit: $0.60 / 48 = $0.0125
        total_cost = recipe.calculate_cost()
        cost_per_unit = recipe.get_cost_per_unit()

        assert total_cost == pytest.approx(0.60, rel=1e-6)
        assert cost_per_unit == pytest.approx(0.0125, rel=1e-6)

    def test_recipe_to_dict(self, db_session):
        """Test recipe dictionary serialization."""
        recipe = Recipe(
            name="Test Recipe",
            category="Cookies",
            yield_quantity=24,
            yield_unit="cookies",
        )
        db_session.add(recipe)
        db_session.commit()

        data = recipe.to_dict()
        assert data["name"] == "Test Recipe"
        assert "total_cost" in data
        assert "cost_per_unit" in data


class TestRecipeIngredientModel:
    """Tests for RecipeIngredient model."""

    def test_create_recipe_ingredient(self, db_session):
        """Test creating recipe ingredient junction."""
        ingredient = Ingredient(
            name="Flour",
            category="Flour",
            purchase_unit="bag",
            recipe_unit="cup",
            conversion_factor=200.0,
            quantity=5.0,
            unit_cost=20.00,
        )
        recipe = Recipe(
            name="Cookies",
            category="Cookies",
            yield_quantity=24,
            yield_unit="cookies",
        )
        db_session.add_all([ingredient, recipe])
        db_session.flush()

        recipe_ingredient = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            quantity=3.0,
            unit="cup",
            notes="Sifted",
        )
        db_session.add(recipe_ingredient)
        db_session.commit()

        assert recipe_ingredient.id is not None
        assert recipe_ingredient.quantity == 3.0
        assert recipe_ingredient.notes == "Sifted"

    def test_recipe_ingredient_cost(self, db_session):
        """Test recipe ingredient cost calculation."""
        ingredient = Ingredient(
            name="Flour",
            category="Flour",
            purchase_unit="bag",
            recipe_unit="cup",
            conversion_factor=100.0,  # 100 cups per bag
            quantity=5.0,
            unit_cost=10.00,  # $10 per bag = $0.10 per cup
        )
        recipe = Recipe(
            name="Cookies",
            category="Cookies",
            yield_quantity=24,
            yield_unit="cookies",
        )
        db_session.add_all([ingredient, recipe])
        db_session.flush()

        recipe_ingredient = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            quantity=5.0,  # 5 cups
            unit="cup",
        )
        db_session.add(recipe_ingredient)
        db_session.commit()
        db_session.refresh(recipe_ingredient)

        # 5 cups × $0.10/cup = $0.50
        assert recipe_ingredient.calculate_cost() == pytest.approx(0.50, rel=1e-6)

    def test_get_purchase_unit_quantity(self, db_session):
        """Test conversion to purchase units."""
        ingredient = Ingredient(
            name="Flour",
            category="Flour",
            purchase_unit="bag",
            recipe_unit="cup",
            conversion_factor=200.0,  # 200 cups per bag
            quantity=5.0,
            unit_cost=20.00,
        )
        recipe = Recipe(
            name="Cookies",
            category="Cookies",
            yield_quantity=24,
            yield_unit="cookies",
        )
        db_session.add_all([ingredient, recipe])
        db_session.flush()

        recipe_ingredient = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            quantity=100.0,  # 100 cups
            unit="cup",
        )
        db_session.add(recipe_ingredient)
        db_session.commit()
        db_session.refresh(recipe_ingredient)

        # 100 cups / 200 cups per bag = 0.5 bags
        assert recipe_ingredient.get_purchase_unit_quantity() == pytest.approx(0.5, rel=1e-6)


class TestInventorySnapshotModel:
    """Tests for InventorySnapshot model."""

    def test_create_snapshot(self, db_session):
        """Test creating an inventory snapshot."""
        snapshot = InventorySnapshot(
            name="Pre-Christmas 2025",
            description="Test snapshot",
        )
        db_session.add(snapshot)
        db_session.commit()

        assert snapshot.id is not None
        assert snapshot.name == "Pre-Christmas 2025"
        assert snapshot.snapshot_date is not None

    def test_snapshot_with_ingredients(self, db_session):
        """Test snapshot with ingredients."""
        # Create ingredients
        flour = Ingredient(
            name="Flour",
            category="Flour",
            purchase_unit="bag",
            recipe_unit="cup",
            conversion_factor=200.0,
            quantity=5.0,
            unit_cost=20.00,
        )
        db_session.add(flour)
        db_session.flush()

        # Create snapshot
        snapshot = InventorySnapshot(name="Test Snapshot")
        db_session.add(snapshot)
        db_session.flush()

        # Add ingredient to snapshot
        snap_ingredient = SnapshotIngredient(
            snapshot_id=snapshot.id,
            ingredient_id=flour.id,
            quantity=3.0,
        )
        db_session.add(snap_ingredient)
        db_session.commit()
        db_session.refresh(snapshot)

        assert len(snapshot.snapshot_ingredients) == 1
        assert snapshot.snapshot_ingredients[0].quantity == 3.0

    def test_snapshot_total_value(self, db_session):
        """Test snapshot total value calculation."""
        # Create ingredients
        flour = Ingredient(
            name="Flour",
            category="Flour",
            purchase_unit="bag",
            recipe_unit="cup",
            conversion_factor=200.0,
            quantity=5.0,
            unit_cost=10.00,
        )
        sugar = Ingredient(
            name="Sugar",
            category="Sugar",
            purchase_unit="bag",
            recipe_unit="cup",
            conversion_factor=20.0,
            quantity=3.0,
            unit_cost=8.00,
        )
        db_session.add_all([flour, sugar])
        db_session.flush()

        # Create snapshot
        snapshot = InventorySnapshot(name="Test Snapshot")
        db_session.add(snapshot)
        db_session.flush()

        # Add ingredients to snapshot
        db_session.add_all(
            [
                SnapshotIngredient(snapshot_id=snapshot.id, ingredient_id=flour.id, quantity=2.0),
                SnapshotIngredient(snapshot_id=snapshot.id, ingredient_id=sugar.id, quantity=3.0),
            ]
        )
        db_session.commit()
        db_session.refresh(snapshot)

        # Total: (2 × $10.00) + (3 × $8.00) = $44.00
        assert snapshot.calculate_total_value() == pytest.approx(44.00, rel=1e-6)

    def test_get_ingredient_quantity(self, db_session):
        """Test getting specific ingredient quantity from snapshot."""
        ingredient = Ingredient(
            name="Flour",
            category="Flour",
            purchase_unit="bag",
            recipe_unit="cup",
            conversion_factor=200.0,
            quantity=5.0,
            unit_cost=20.00,
        )
        db_session.add(ingredient)
        db_session.flush()

        snapshot = InventorySnapshot(name="Test Snapshot")
        db_session.add(snapshot)
        db_session.flush()

        snap_ingredient = SnapshotIngredient(
            snapshot_id=snapshot.id,
            ingredient_id=ingredient.id,
            quantity=2.5,
        )
        db_session.add(snap_ingredient)
        db_session.commit()
        db_session.refresh(snapshot)

        assert snapshot.get_ingredient_quantity(ingredient.id) == 2.5
        assert snapshot.get_ingredient_quantity(999) == 0.0  # Non-existent ingredient


class TestModelRelationships:
    """Tests for relationships between models."""

    def test_ingredient_to_recipe_relationship(self, db_session):
        """Test ingredient can access recipes that use it."""
        ingredient = Ingredient(
            name="Flour",
            category="Flour",
            purchase_unit="bag",
            recipe_unit="cup",
            conversion_factor=200.0,
            quantity=5.0,
            unit_cost=20.00,
        )
        recipe = Recipe(
            name="Cookies",
            category="Cookies",
            yield_quantity=24,
            yield_unit="cookies",
        )
        db_session.add_all([ingredient, recipe])
        db_session.flush()

        recipe_ingredient = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            quantity=2.0,
            unit="cup",
        )
        db_session.add(recipe_ingredient)
        db_session.commit()
        db_session.refresh(ingredient)

        assert len(ingredient.recipe_ingredients) == 1
        assert ingredient.recipe_ingredients[0].recipe.name == "Cookies"

    def test_recipe_cascade_delete(self, db_session):
        """Test that deleting recipe cascades to recipe_ingredients."""
        ingredient = Ingredient(
            name="Flour",
            category="Flour",
            purchase_unit="bag",
            recipe_unit="cup",
            conversion_factor=200.0,
            quantity=5.0,
            unit_cost=20.00,
        )
        recipe = Recipe(
            name="Cookies",
            category="Cookies",
            yield_quantity=24,
            yield_unit="cookies",
        )
        db_session.add_all([ingredient, recipe])
        db_session.flush()

        recipe_ingredient = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            quantity=2.0,
            unit="cup",
        )
        db_session.add(recipe_ingredient)
        db_session.commit()

        recipe_id = recipe.id

        # Delete recipe
        db_session.delete(recipe)
        db_session.commit()

        # RecipeIngredient should also be deleted
        remaining = db_session.query(RecipeIngredient).filter_by(recipe_id=recipe_id).count()
        assert remaining == 0
