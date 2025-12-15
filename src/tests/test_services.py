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
from src.services import ingredient_crud_service, recipe_service
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
    """Sample valid ingredient data (TD-001 schema)."""
    return {
        "display_name": "All-Purpose Flour",
        "category": "Flour",
        # 4-field density model
        "density_volume_value": 1.0,
        "density_volume_unit": "cup",
        "density_weight_value": 120.0,
        "density_weight_unit": "g",
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
        """Test creating an ingredient (TD-001 schema)."""
        ingredient = ingredient_crud_service.create_ingredient(sample_ingredient_data)

        assert ingredient.id is not None
        assert ingredient.display_name == "All-Purpose Flour"
        assert ingredient.category == "Flour"
        assert ingredient.density_volume_value == 1.0
        assert ingredient.density_weight_value == 120.0

    def test_create_ingredient_validation_error(self, db_session):
        """Test creating ingredient with invalid data."""
        invalid_data = {
            "display_name": "",  # Invalid: empty name
            "category": "Test",
        }

        with pytest.raises(ValidationError):
            ingredient_crud_service.create_ingredient(invalid_data)

    def test_get_ingredient(self, db_session, sample_ingredient_data):
        """Test retrieving an ingredient by ID."""
        created = ingredient_crud_service.create_ingredient(sample_ingredient_data)
        retrieved = ingredient_crud_service.get_ingredient(created.id)

        assert retrieved.id == created.id
        assert retrieved.display_name == created.display_name

    def test_get_ingredient_not_found(self, db_session):
        """Test retrieving non-existent ingredient."""
        with pytest.raises(IngredientNotFound) as exc_info:
            ingredient_crud_service.get_ingredient(99999)

        assert exc_info.value.ingredient_id == 99999

    def test_get_all_ingredients(self, db_session, sample_ingredient_data):
        """Test retrieving all ingredients."""
        # Create multiple ingredients
        ingredient_crud_service.create_ingredient(sample_ingredient_data)

        data2 = sample_ingredient_data.copy()
        data2["display_name"] = "Granulated Sugar"
        data2["category"] = "Sugar"
        ingredient_crud_service.create_ingredient(data2)

        ingredients = ingredient_crud_service.get_all_ingredients()

        assert len(ingredients) >= 2

    def test_get_all_ingredients_filter_by_category(self, db_session, sample_ingredient_data):
        """Test filtering ingredients by category."""
        ingredient_crud_service.create_ingredient(sample_ingredient_data)

        data2 = sample_ingredient_data.copy()
        data2["display_name"] = "Sugar"
        data2["category"] = "Sugar"
        ingredient_crud_service.create_ingredient(data2)

        flour_ingredients = ingredient_crud_service.get_all_ingredients(category="Flour")

        assert len(flour_ingredients) == 1
        assert flour_ingredients[0].category == "Flour"

    def test_get_all_ingredients_filter_by_name(self, db_session, sample_ingredient_data):
        """Test filtering ingredients by name search."""
        ingredient_crud_service.create_ingredient(sample_ingredient_data)

        data2 = sample_ingredient_data.copy()
        data2["display_name"] = "Sugar"
        ingredient_crud_service.create_ingredient(data2)

        flour_results = ingredient_crud_service.get_all_ingredients(name_search="Flour")

        assert len(flour_results) >= 1
        assert "Flour" in flour_results[0].display_name

    @pytest.mark.skip(reason="TD-001: quantity moved to InventoryItem (formerly PantryItem), not Ingredient")
    def test_get_low_stock_ingredients(self, db_session, sample_ingredient_data):
        """Test filtering by low stock threshold - OBSOLETE."""
        pass

    def test_update_ingredient(self, db_session, sample_ingredient_data):
        """Test updating an ingredient."""
        created = ingredient_crud_service.create_ingredient(sample_ingredient_data)

        update_data = sample_ingredient_data.copy()
        update_data["notes"] = "Updated notes"

        updated = ingredient_crud_service.update_ingredient(created.id, update_data)

        assert updated.id == created.id
        assert updated.notes == "Updated notes"

    def test_update_ingredient_not_found(self, db_session, sample_ingredient_data):
        """Test updating non-existent ingredient."""
        with pytest.raises(IngredientNotFound):
            ingredient_crud_service.update_ingredient(99999, sample_ingredient_data)

    def test_delete_ingredient(self, db_session, sample_ingredient_data):
        """Test deleting an ingredient."""
        created = ingredient_crud_service.create_ingredient(sample_ingredient_data)
        result = ingredient_crud_service.delete_ingredient(created.id)

        assert result is True

        with pytest.raises(IngredientNotFound):
            ingredient_crud_service.get_ingredient(created.id)

    def test_delete_ingredient_in_use(self, db_session, sample_ingredient_data, sample_recipe_data):
        """Test deleting ingredient that is used in recipes."""
        # Create ingredient
        ingredient = ingredient_crud_service.create_ingredient(sample_ingredient_data)

        # Create recipe using this ingredient
        ingredients_data = [{"ingredient_id": ingredient.id, "quantity": 2.0, "unit": "cup"}]
        recipe_service.create_recipe(sample_recipe_data, ingredients_data)

        # Try to delete ingredient
        with pytest.raises(IngredientInUse) as exc_info:
            ingredient_crud_service.delete_ingredient(ingredient.id)

        assert exc_info.value.ingredient_id == ingredient.id
        assert exc_info.value.recipe_count >= 1

    def test_delete_ingredient_in_use_force(
        self, db_session, sample_ingredient_data, sample_recipe_data
    ):
        """Test force deleting ingredient that is used in recipes."""
        # Create ingredient
        ingredient = ingredient_crud_service.create_ingredient(sample_ingredient_data)

        # Create recipe using this ingredient
        ingredients_data = [{"ingredient_id": ingredient.id, "quantity": 2.0, "unit": "cup"}]
        recipe_service.create_recipe(sample_recipe_data, ingredients_data)

        # Force delete should succeed
        result = ingredient_crud_service.delete_ingredient(ingredient.id, force=True)
        assert result is True

@pytest.mark.skip(reason="TD-001: Stock management moved to InventoryItem (formerly PantryItem), not Ingredient")
class TestInventoryServiceStockManagement:
    """Test stock management functions - OBSOLETE.

    TD-001 schema change: quantity tracking moved from Ingredient to InventoryItem.
    These tests are skipped as the underlying functionality no longer exists.
    """

    def test_update_quantity(self, db_session, sample_ingredient_data):
        """Test updating ingredient quantity - OBSOLETE."""
        pass

    def test_update_quantity_negative(self, db_session, sample_ingredient_data):
        """Test updating to negative quantity - OBSOLETE."""
        pass

    def test_adjust_quantity_positive(self, db_session, sample_ingredient_data):
        """Test adjusting quantity (positive adjustment) - OBSOLETE."""
        pass

    def test_adjust_quantity_negative(self, db_session, sample_ingredient_data):
        """Test adjusting quantity (negative adjustment) - OBSOLETE."""
        pass

    def test_adjust_quantity_would_be_negative(self, db_session, sample_ingredient_data):
        """Test adjustment that would result in negative quantity - OBSOLETE."""
        pass

class TestInventoryServiceUtilities:
    """Test inventory service utility functions."""

    def test_get_ingredient_count(self, db_session, sample_ingredient_data):
        """Test getting ingredient count."""
        initial_count = ingredient_crud_service.get_ingredient_count()

        ingredient_crud_service.create_ingredient(sample_ingredient_data)

        new_count = ingredient_crud_service.get_ingredient_count()

        assert new_count == initial_count + 1

    def test_get_category_list(self, db_session, sample_ingredient_data):
        """Test getting category list."""
        ingredient_crud_service.create_ingredient(sample_ingredient_data)

        data2 = sample_ingredient_data.copy()
        data2["display_name"] = "Sugar"
        data2["category"] = "Sugar"
        ingredient_crud_service.create_ingredient(data2)

        categories = ingredient_crud_service.get_category_list()

        assert "Flour" in categories
        assert "Sugar" in categories

    @pytest.mark.skip(reason="TD-001: Inventory value calculation moved to InventoryItem (formerly PantryItem)")
    def test_get_total_inventory_value(self, db_session, sample_ingredient_data):
        """Test calculating total inventory value - OBSOLETE."""
        pass

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
        flour = ingredient_crud_service.create_ingredient(sample_ingredient_data)

        sugar_data = sample_ingredient_data.copy()
        sugar_data["display_name"] = "Sugar"
        sugar = ingredient_crud_service.create_ingredient(sugar_data)

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
        flour = ingredient_crud_service.create_ingredient(sample_ingredient_data)

        sugar_data = sample_ingredient_data.copy()
        sugar_data["display_name"] = "Sugar"
        sugar = ingredient_crud_service.create_ingredient(sugar_data)

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
        flour = ingredient_crud_service.create_ingredient(sample_ingredient_data)

        sugar_data = sample_ingredient_data.copy()
        sugar_data["display_name"] = "Sugar"
        sugar = ingredient_crud_service.create_ingredient(sugar_data)

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
        ingredient = ingredient_crud_service.create_ingredient(sample_ingredient_data)

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
        ingredient = ingredient_crud_service.create_ingredient(sample_ingredient_data)

        ingredients_data = [{"ingredient_id": ingredient.id, "quantity": 2.0, "unit": "cup"}]
        recipe = recipe_service.create_recipe(sample_recipe_data, ingredients_data)

        result = recipe_service.remove_ingredient_from_recipe(recipe.id, ingredient.id)

        assert result is True

@pytest.mark.skip(reason="TD-001: Cost calculation requires Product/InventoryItem with price data")
class TestRecipeCostCalculations:
    """Test recipe cost calculation functions - NEEDS PRODUCT/INVENTORY DATA.

    TD-001 schema change: costs are now tracked on InventoryItem (with unit_cost),
    not on Ingredient. These tests need to be rewritten to use the new schema.
    """

    def test_calculate_recipe_cost(self, db_session, sample_recipe_data, sample_ingredient_data):
        """Test calculating recipe cost - OBSOLETE."""
        pass

    @pytest.mark.skip(reason="TD-001: Cost calculation requires Product/InventoryItem with price data")
    def test_get_recipe_with_costs(self, db_session, sample_recipe_data, sample_ingredient_data):
        """Test getting recipe with cost breakdown - NEEDS PRODUCT/INVENTORY DATA."""
        pass

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
