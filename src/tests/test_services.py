"""
Unit tests for service layer (inventory and recipe services).

Tests cover:
- Inventory service CRUD operations
- Recipe service CRUD operations
- Search and filter functions
- Cost calculations
- Error handling
"""

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.base import Base
from src.models import Ingredient, Recipe, RecipeIngredient
from src.services import inventory_service, recipe_service
from src.services.exceptions import (
    IngredientNotFound,
    RecipeNotFound,
    IngredientInUse,
    ValidationError,
)
from src.services import database


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def db_session():
    """
    Create a test database session.

    This fixture creates an in-memory database for each test,
    ensuring tests are isolated. It also patches the global
    session factory so services use the test database.
    """
    # Create in-memory database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    # Create session factory with expire_on_commit=False
    # This prevents objects from being expired after commit
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    # Patch the global session factory
    original_get_session = database.get_session
    database._session_factory = Session

    def patched_get_session():
        return Session()

    database.get_session = patched_get_session

    # Create a session for the test
    session = Session()

    yield session

    # Cleanup
    session.close()
    database.get_session = original_get_session


@pytest.fixture
def sample_ingredient_data():
    """Sample valid ingredient data."""
    return {
        "name": "All-Purpose Flour",
        "brand": "King Arthur",
        "category": "Flour/Grains",
        "purchase_unit": "bag",
        "purchase_unit_size": "50 lb",
        "recipe_unit": "cup",
        "conversion_factor": 200.0,
        "quantity": 2.5,
        "unit_cost": 20.00,
        "notes": "Test ingredient",
    }


@pytest.fixture
def sample_recipe_data():
    """Sample valid recipe data."""
    return {
        "name": "Chocolate Chip Cookies",
        "category": "Cookies",
        "yield_quantity": 48,
        "yield_unit": "cookies",
        "yield_description": "2-inch cookies",
        "estimated_time_minutes": 45,
        "source": "Test Recipe",
        "notes": "Test notes",
    }


# ============================================================================
# Inventory Service Tests
# ============================================================================


class TestInventoryServiceCRUD:
    """Test inventory service CRUD operations."""

    def test_create_ingredient(self, db_session, sample_ingredient_data):
        """Test creating an ingredient."""
        ingredient = inventory_service.create_ingredient(sample_ingredient_data)

        assert ingredient.id is not None
        assert ingredient.name == "All-Purpose Flour"
        assert ingredient.brand == "King Arthur"
        assert ingredient.category == "Flour/Grains"
        assert ingredient.quantity == 2.5
        assert ingredient.unit_cost == 20.00

    def test_create_ingredient_validation_error(self, db_session):
        """Test creating ingredient with invalid data."""
        invalid_data = {
            "name": "",  # Invalid: empty name
            "category": "Test",
            "purchase_unit": "bag",
            "recipe_unit": "cup",
            "conversion_factor": 100.0,
        }

        with pytest.raises(ValidationError):
            inventory_service.create_ingredient(invalid_data)

    def test_get_ingredient(self, db_session, sample_ingredient_data):
        """Test retrieving an ingredient by ID."""
        created = inventory_service.create_ingredient(sample_ingredient_data)
        retrieved = inventory_service.get_ingredient(created.id)

        assert retrieved.id == created.id
        assert retrieved.name == created.name

    def test_get_ingredient_not_found(self, db_session):
        """Test retrieving non-existent ingredient."""
        with pytest.raises(IngredientNotFound) as exc_info:
            inventory_service.get_ingredient(99999)

        assert exc_info.value.ingredient_id == 99999

    def test_get_all_ingredients(self, db_session, sample_ingredient_data):
        """Test retrieving all ingredients."""
        # Create multiple ingredients
        inventory_service.create_ingredient(sample_ingredient_data)

        data2 = sample_ingredient_data.copy()
        data2["name"] = "Granulated Sugar"
        data2["category"] = "Sugar/Sweeteners"
        inventory_service.create_ingredient(data2)

        ingredients = inventory_service.get_all_ingredients()

        assert len(ingredients) >= 2

    def test_get_all_ingredients_filter_by_category(self, db_session, sample_ingredient_data):
        """Test filtering ingredients by category."""
        inventory_service.create_ingredient(sample_ingredient_data)

        data2 = sample_ingredient_data.copy()
        data2["name"] = "Sugar"
        data2["category"] = "Sugar/Sweeteners"
        inventory_service.create_ingredient(data2)

        flour_ingredients = inventory_service.get_all_ingredients(category="Flour/Grains")

        assert len(flour_ingredients) == 1
        assert flour_ingredients[0].category == "Flour/Grains"

    def test_get_all_ingredients_filter_by_name(self, db_session, sample_ingredient_data):
        """Test filtering ingredients by name search."""
        inventory_service.create_ingredient(sample_ingredient_data)

        data2 = sample_ingredient_data.copy()
        data2["name"] = "Sugar"
        inventory_service.create_ingredient(data2)

        flour_results = inventory_service.get_all_ingredients(name_search="Flour")

        assert len(flour_results) >= 1
        assert "Flour" in flour_results[0].name

    def test_get_low_stock_ingredients(self, db_session, sample_ingredient_data):
        """Test filtering by low stock threshold."""
        data1 = sample_ingredient_data.copy()
        data1["quantity"] = 0.5
        inventory_service.create_ingredient(data1)

        data2 = sample_ingredient_data.copy()
        data2["name"] = "Sugar"
        data2["quantity"] = 10.0
        inventory_service.create_ingredient(data2)

        low_stock = inventory_service.get_low_stock_ingredients(threshold=1.0)

        assert len(low_stock) >= 1
        assert all(ing.quantity <= 1.0 for ing in low_stock)

    def test_update_ingredient(self, db_session, sample_ingredient_data):
        """Test updating an ingredient."""
        created = inventory_service.create_ingredient(sample_ingredient_data)

        update_data = sample_ingredient_data.copy()
        update_data["quantity"] = 5.0
        update_data["unit_cost"] = 25.00

        updated = inventory_service.update_ingredient(created.id, update_data)

        assert updated.id == created.id
        assert updated.quantity == 5.0
        assert updated.unit_cost == 25.00

    def test_update_ingredient_not_found(self, db_session, sample_ingredient_data):
        """Test updating non-existent ingredient."""
        with pytest.raises(IngredientNotFound):
            inventory_service.update_ingredient(99999, sample_ingredient_data)

    def test_delete_ingredient(self, db_session, sample_ingredient_data):
        """Test deleting an ingredient."""
        created = inventory_service.create_ingredient(sample_ingredient_data)
        result = inventory_service.delete_ingredient(created.id)

        assert result is True

        with pytest.raises(IngredientNotFound):
            inventory_service.get_ingredient(created.id)

    def test_delete_ingredient_in_use(self, db_session, sample_ingredient_data, sample_recipe_data):
        """Test deleting ingredient that is used in recipes."""
        # Create ingredient
        ingredient = inventory_service.create_ingredient(sample_ingredient_data)

        # Create recipe using this ingredient
        ingredients_data = [{"ingredient_id": ingredient.id, "quantity": 2.0, "unit": "cup"}]
        recipe_service.create_recipe(sample_recipe_data, ingredients_data)

        # Try to delete ingredient
        with pytest.raises(IngredientInUse) as exc_info:
            inventory_service.delete_ingredient(ingredient.id)

        assert exc_info.value.ingredient_id == ingredient.id
        assert exc_info.value.recipe_count >= 1

    def test_delete_ingredient_in_use_force(
        self, db_session, sample_ingredient_data, sample_recipe_data
    ):
        """Test force deleting ingredient that is used in recipes."""
        # Create ingredient
        ingredient = inventory_service.create_ingredient(sample_ingredient_data)

        # Create recipe using this ingredient
        ingredients_data = [{"ingredient_id": ingredient.id, "quantity": 2.0, "unit": "cup"}]
        recipe_service.create_recipe(sample_recipe_data, ingredients_data)

        # Force delete should succeed
        result = inventory_service.delete_ingredient(ingredient.id, force=True)
        assert result is True


class TestInventoryServiceStockManagement:
    """Test stock management functions."""

    def test_update_quantity(self, db_session, sample_ingredient_data):
        """Test updating ingredient quantity."""
        ingredient = inventory_service.create_ingredient(sample_ingredient_data)
        updated = inventory_service.update_quantity(ingredient.id, 10.0)

        assert updated.quantity == 10.0

    def test_update_quantity_negative(self, db_session, sample_ingredient_data):
        """Test updating to negative quantity."""
        ingredient = inventory_service.create_ingredient(sample_ingredient_data)

        with pytest.raises(ValidationError):
            inventory_service.update_quantity(ingredient.id, -5.0)

    def test_adjust_quantity_positive(self, db_session, sample_ingredient_data):
        """Test adjusting quantity (positive adjustment)."""
        ingredient = inventory_service.create_ingredient(sample_ingredient_data)
        initial = ingredient.quantity

        updated = inventory_service.adjust_quantity(ingredient.id, 2.5)

        assert updated.quantity == pytest.approx(initial + 2.5, rel=1e-6)

    def test_adjust_quantity_negative(self, db_session, sample_ingredient_data):
        """Test adjusting quantity (negative adjustment)."""
        data = sample_ingredient_data.copy()
        data["quantity"] = 10.0
        ingredient = inventory_service.create_ingredient(data)

        updated = inventory_service.adjust_quantity(ingredient.id, -3.0)

        assert updated.quantity == pytest.approx(7.0, rel=1e-6)

    def test_adjust_quantity_would_be_negative(self, db_session, sample_ingredient_data):
        """Test adjustment that would result in negative quantity."""
        data = sample_ingredient_data.copy()
        data["quantity"] = 2.0
        ingredient = inventory_service.create_ingredient(data)

        with pytest.raises(ValidationError) as exc_info:
            inventory_service.adjust_quantity(ingredient.id, -5.0)

        assert "negative" in str(exc_info.value).lower()


class TestInventoryServiceUtilities:
    """Test inventory service utility functions."""

    def test_get_ingredient_count(self, db_session, sample_ingredient_data):
        """Test getting ingredient count."""
        initial_count = inventory_service.get_ingredient_count()

        inventory_service.create_ingredient(sample_ingredient_data)

        new_count = inventory_service.get_ingredient_count()

        assert new_count == initial_count + 1

    def test_get_category_list(self, db_session, sample_ingredient_data):
        """Test getting category list."""
        inventory_service.create_ingredient(sample_ingredient_data)

        data2 = sample_ingredient_data.copy()
        data2["name"] = "Sugar"
        data2["category"] = "Sugar/Sweeteners"
        inventory_service.create_ingredient(data2)

        categories = inventory_service.get_category_list()

        assert "Flour/Grains" in categories
        assert "Sugar/Sweeteners" in categories

    def test_get_total_inventory_value(self, db_session, sample_ingredient_data):
        """Test calculating total inventory value."""
        # Create two ingredients with known values
        data1 = sample_ingredient_data.copy()
        data1["quantity"] = 2.0
        data1["unit_cost"] = 10.0
        inventory_service.create_ingredient(data1)

        data2 = sample_ingredient_data.copy()
        data2["name"] = "Sugar"
        data2["quantity"] = 5.0
        data2["unit_cost"] = 8.0
        inventory_service.create_ingredient(data2)

        # Expected: (2.0 * 10.0) + (5.0 * 8.0) = 20 + 40 = 60
        total_value = inventory_service.get_total_inventory_value()

        assert total_value >= 60.0


# ============================================================================
# Recipe Service Tests
# ============================================================================


class TestRecipeServiceCRUD:
    """Test recipe service CRUD operations."""

    def test_create_recipe_without_ingredients(self, db_session, sample_recipe_data):
        """Test creating a recipe without ingredients."""
        recipe = recipe_service.create_recipe(sample_recipe_data)

        assert recipe.id is not None
        assert recipe.name == "Chocolate Chip Cookies"
        assert recipe.category == "Cookies"
        assert recipe.yield_quantity == 48

    def test_create_recipe_with_ingredients(
        self, db_session, sample_recipe_data, sample_ingredient_data
    ):
        """Test creating a recipe with ingredients."""
        # Create ingredients
        flour = inventory_service.create_ingredient(sample_ingredient_data)

        sugar_data = sample_ingredient_data.copy()
        sugar_data["name"] = "Sugar"
        sugar = inventory_service.create_ingredient(sugar_data)

        # Create recipe with ingredients
        ingredients_data = [
            {"ingredient_id": flour.id, "quantity": 3.0, "unit": "cup", "notes": "Sifted"},
            {"ingredient_id": sugar.id, "quantity": 1.5, "unit": "cup"},
        ]

        recipe = recipe_service.create_recipe(sample_recipe_data, ingredients_data)

        assert recipe.id is not None
        assert len(recipe.recipe_ingredients) == 2

    def test_create_recipe_invalid_ingredient_id(self, db_session, sample_recipe_data):
        """Test creating recipe with non-existent ingredient."""
        ingredients_data = [{"ingredient_id": 99999, "quantity": 2.0, "unit": "cup"}]

        with pytest.raises(IngredientNotFound):
            recipe_service.create_recipe(sample_recipe_data, ingredients_data)

    def test_create_recipe_validation_error(self, db_session):
        """Test creating recipe with invalid data."""
        invalid_data = {
            "name": "",  # Invalid: empty name
            "category": "Test",
            "yield_quantity": 24,
            "yield_unit": "cookies",
        }

        with pytest.raises(ValidationError):
            recipe_service.create_recipe(invalid_data)

    def test_get_recipe(self, db_session, sample_recipe_data):
        """Test retrieving a recipe by ID."""
        created = recipe_service.create_recipe(sample_recipe_data)
        retrieved = recipe_service.get_recipe(created.id)

        assert retrieved.id == created.id
        assert retrieved.name == created.name

    def test_get_recipe_not_found(self, db_session):
        """Test retrieving non-existent recipe."""
        with pytest.raises(RecipeNotFound) as exc_info:
            recipe_service.get_recipe(99999)

        assert exc_info.value.recipe_id == 99999

    def test_get_all_recipes(self, db_session, sample_recipe_data):
        """Test retrieving all recipes."""
        recipe_service.create_recipe(sample_recipe_data)

        data2 = sample_recipe_data.copy()
        data2["name"] = "Brownies"
        recipe_service.create_recipe(data2)

        recipes = recipe_service.get_all_recipes()

        assert len(recipes) >= 2

    def test_get_all_recipes_filter_by_category(self, db_session, sample_recipe_data):
        """Test filtering recipes by category."""
        recipe_service.create_recipe(sample_recipe_data)

        data2 = sample_recipe_data.copy()
        data2["name"] = "Brownies"
        data2["category"] = "Bars"
        recipe_service.create_recipe(data2)

        cookie_recipes = recipe_service.get_all_recipes(category="Cookies")

        assert len(cookie_recipes) >= 1
        assert all(r.category == "Cookies" for r in cookie_recipes)

    def test_get_all_recipes_filter_by_name(self, db_session, sample_recipe_data):
        """Test filtering recipes by name search."""
        recipe_service.create_recipe(sample_recipe_data)

        data2 = sample_recipe_data.copy()
        data2["name"] = "Brownies"
        recipe_service.create_recipe(data2)

        cookie_results = recipe_service.get_all_recipes(name_search="Cookie")

        assert len(cookie_results) >= 1
        assert "Cookie" in cookie_results[0].name

    def test_get_recipes_using_ingredient(
        self, db_session, sample_recipe_data, sample_ingredient_data
    ):
        """Test finding recipes that use a specific ingredient."""
        # Create ingredients
        flour = inventory_service.create_ingredient(sample_ingredient_data)

        sugar_data = sample_ingredient_data.copy()
        sugar_data["name"] = "Sugar"
        sugar = inventory_service.create_ingredient(sugar_data)

        # Create recipe using flour
        ingredients_data = [{"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"}]
        recipe_service.create_recipe(sample_recipe_data, ingredients_data)

        # Create another recipe using sugar
        data2 = sample_recipe_data.copy()
        data2["name"] = "Sugar Cookies"
        ingredients_data2 = [{"ingredient_id": sugar.id, "quantity": 1.0, "unit": "cup"}]
        recipe_service.create_recipe(data2, ingredients_data2)

        # Find recipes using flour
        flour_recipes = recipe_service.get_recipes_using_ingredient(flour.id)

        assert len(flour_recipes) >= 1
        assert all(
            any(ri.ingredient_id == flour.id for ri in r.recipe_ingredients) for r in flour_recipes
        )

    def test_update_recipe(self, db_session, sample_recipe_data):
        """Test updating a recipe."""
        created = recipe_service.create_recipe(sample_recipe_data)

        update_data = sample_recipe_data.copy()
        update_data["yield_quantity"] = 60
        update_data["notes"] = "Updated notes"

        updated = recipe_service.update_recipe(created.id, update_data)

        assert updated.id == created.id
        assert updated.yield_quantity == 60
        assert updated.notes == "Updated notes"

    def test_update_recipe_replace_ingredients(
        self, db_session, sample_recipe_data, sample_ingredient_data
    ):
        """Test updating recipe and replacing ingredients."""
        # Create ingredients
        flour = inventory_service.create_ingredient(sample_ingredient_data)

        sugar_data = sample_ingredient_data.copy()
        sugar_data["name"] = "Sugar"
        sugar = inventory_service.create_ingredient(sugar_data)

        # Create recipe with flour
        ingredients_data = [{"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"}]
        recipe = recipe_service.create_recipe(sample_recipe_data, ingredients_data)

        # Update with sugar instead
        new_ingredients = [{"ingredient_id": sugar.id, "quantity": 1.5, "unit": "cup"}]
        updated = recipe_service.update_recipe(recipe.id, sample_recipe_data, new_ingredients)

        assert len(updated.recipe_ingredients) == 1
        assert updated.recipe_ingredients[0].ingredient_id == sugar.id

    def test_delete_recipe(self, db_session, sample_recipe_data):
        """Test deleting a recipe."""
        created = recipe_service.create_recipe(sample_recipe_data)
        result = recipe_service.delete_recipe(created.id)

        assert result is True

        with pytest.raises(RecipeNotFound):
            recipe_service.get_recipe(created.id)


class TestRecipeIngredientManagement:
    """Test recipe ingredient management functions."""

    def test_add_ingredient_to_recipe(self, db_session, sample_recipe_data, sample_ingredient_data):
        """Test adding an ingredient to a recipe."""
        recipe = recipe_service.create_recipe(sample_recipe_data)
        ingredient = inventory_service.create_ingredient(sample_ingredient_data)

        recipe_ingredient = recipe_service.add_ingredient_to_recipe(
            recipe.id, ingredient.id, 2.0, "cup", "Test notes"
        )

        assert recipe_ingredient.recipe_id == recipe.id
        assert recipe_ingredient.ingredient_id == ingredient.id
        assert recipe_ingredient.quantity == 2.0

    def test_remove_ingredient_from_recipe(
        self, db_session, sample_recipe_data, sample_ingredient_data
    ):
        """Test removing an ingredient from a recipe."""
        ingredient = inventory_service.create_ingredient(sample_ingredient_data)

        ingredients_data = [{"ingredient_id": ingredient.id, "quantity": 2.0, "unit": "cup"}]
        recipe = recipe_service.create_recipe(sample_recipe_data, ingredients_data)

        result = recipe_service.remove_ingredient_from_recipe(recipe.id, ingredient.id)

        assert result is True


class TestRecipeCostCalculations:
    """Test recipe cost calculation functions."""

    def test_calculate_recipe_cost(self, db_session, sample_recipe_data, sample_ingredient_data):
        """Test calculating recipe cost."""
        # Create ingredient: $20 per bag, 200 cups per bag = $0.10 per cup
        ingredient = inventory_service.create_ingredient(sample_ingredient_data)

        # Create recipe using 3 cups = $0.30 total
        ingredients_data = [{"ingredient_id": ingredient.id, "quantity": 3.0, "unit": "cup"}]
        recipe = recipe_service.create_recipe(sample_recipe_data, ingredients_data)

        cost = recipe_service.calculate_recipe_cost(recipe.id)

        assert cost == pytest.approx(0.30, rel=1e-6)

    def test_get_recipe_with_costs(self, db_session, sample_recipe_data, sample_ingredient_data):
        """Test getting recipe with cost breakdown."""
        # Create two ingredients
        flour_data = sample_ingredient_data.copy()
        flour_data["unit_cost"] = 20.0
        flour_data["conversion_factor"] = 200.0
        flour = inventory_service.create_ingredient(flour_data)

        sugar_data = sample_ingredient_data.copy()
        sugar_data["name"] = "Sugar"
        sugar_data["unit_cost"] = 10.0
        sugar_data["conversion_factor"] = 100.0
        sugar = inventory_service.create_ingredient(sugar_data)

        # Create recipe
        # Flour: $20 / 200 = $0.10 per cup × 2 cups = $0.20
        # Sugar: $10 / 100 = $0.10 per cup × 1 cup = $0.10
        # Total: $0.30
        ingredients_data = [
            {"ingredient_id": flour.id, "quantity": 2.0, "unit": "cup"},
            {"ingredient_id": sugar.id, "quantity": 1.0, "unit": "cup"},
        ]
        recipe = recipe_service.create_recipe(sample_recipe_data, ingredients_data)

        result = recipe_service.get_recipe_with_costs(recipe.id)

        assert "recipe" in result
        assert "total_cost" in result
        assert "cost_per_unit" in result
        assert "ingredients" in result

        assert result["total_cost"] == pytest.approx(0.30, rel=1e-6)
        # 48 cookies: $0.30 / 48 = $0.00625 per cookie
        assert result["cost_per_unit"] == pytest.approx(0.00625, rel=1e-6)
        assert len(result["ingredients"]) == 2


class TestRecipeServiceUtilities:
    """Test recipe service utility functions."""

    def test_get_recipe_count(self, db_session, sample_recipe_data):
        """Test getting recipe count."""
        initial_count = recipe_service.get_recipe_count()

        recipe_service.create_recipe(sample_recipe_data)

        new_count = recipe_service.get_recipe_count()

        assert new_count == initial_count + 1

    def test_get_recipe_category_list(self, db_session, sample_recipe_data):
        """Test getting recipe category list."""
        recipe_service.create_recipe(sample_recipe_data)

        data2 = sample_recipe_data.copy()
        data2["name"] = "Brownies"
        data2["category"] = "Bars"
        recipe_service.create_recipe(data2)

        categories = recipe_service.get_recipe_category_list()

        assert "Cookies" in categories
        assert "Bars" in categories
