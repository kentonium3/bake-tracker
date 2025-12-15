"""
Tests for database models.

Tests cover:
- Model creation and persistence
- Relationships between models
- Calculated properties
- CRUD operations

TD-001: Updated for new schema:
- Ingredient: generic ingredient definitions (display_name, density)
- Product: branded products linked to ingredients
- InventoryItem: inventory tracking
- Purchase: price history
"""

import pytest
from datetime import datetime
from decimal import Decimal

from src.models import (
    Ingredient,
    Product,
    Recipe,
    RecipeIngredient,
    InventoryItem,
    Purchase,
    InventorySnapshot,
    SnapshotIngredient
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
    """Tests for Ingredient model (TD-001 schema)."""

    def test_create_ingredient(self, db_session):
        """Test creating an ingredient with new schema."""
        ingredient = Ingredient(
            display_name="All-Purpose Flour",
            slug="all_purpose_flour",
            category="Flour",
            description="Standard all-purpose flour",
            notes="Test notes"
        )
        db_session.add(ingredient)
        db_session.commit()

        assert ingredient.id is not None
        assert ingredient.display_name == "All-Purpose Flour"
        assert ingredient.slug == "all_purpose_flour"
        assert ingredient.category == "Flour"
    def test_ingredient_with_density(self, db_session):
        """Test ingredient with density specification."""
        ingredient = Ingredient(
            display_name="All-Purpose Flour",
            slug="all_purpose_flour",
            category="Flour",
            # 4-field density: 1 cup = 120g
            density_volume_value=1.0,
            density_volume_unit="cup",
            density_weight_value=120.0,
            density_weight_unit="g"
        )
        db_session.add(ingredient)
        db_session.commit()

        assert ingredient.density_volume_value == 1.0
        assert ingredient.density_volume_unit == "cup"
        assert ingredient.density_weight_value == 120.0
        assert ingredient.density_weight_unit == "g"

    def test_ingredient_get_density_g_per_ml(self, db_session):
        """Test density calculation in g/ml."""
        ingredient = Ingredient(
            display_name="All-Purpose Flour",
            slug="all_purpose_flour",
            category="Flour",
            # 1 cup = 120g, 1 cup = 236.588 ml
            density_volume_value=1.0,
            density_volume_unit="cup",
            density_weight_value=120.0,
            density_weight_unit="g"
        )
        db_session.add(ingredient)
        db_session.commit()

        density = ingredient.get_density_g_per_ml()
        # 120g / 236.588ml = ~0.507 g/ml
        assert density is not None
        assert 0.5 < density < 0.52

    def test_ingredient_without_density(self, db_session):
        """Test ingredient without density returns None."""
        ingredient = Ingredient(
            display_name="Sugar",
            slug="sugar",
            category="Sugar"
        )
        db_session.add(ingredient)
        db_session.commit()

        assert ingredient.get_density_g_per_ml() is None

    def test_ingredient_to_dict(self, db_session):
        """Test dictionary serialization."""
        ingredient = Ingredient(
            display_name="Flour",
            slug="flour",
            category="Flour"
        )
        db_session.add(ingredient)
        db_session.commit()

        data = ingredient.to_dict()

        assert data["display_name"] == "Flour"
        assert data["slug"] == "flour"
        assert data["category"] == "Flour"
    def test_ingredient_slug_uniqueness(self, db_session):
        """Test that slug must be unique."""
        from sqlalchemy.exc import IntegrityError

        ingredient1 = Ingredient(
            display_name="Flour",
            slug="flour",
            category="Flour"
        )
        db_session.add(ingredient1)
        db_session.commit()

        ingredient2 = Ingredient(
            display_name="Another Flour",
            slug="flour",  # Same slug
            category="Flour"
        )
        db_session.add(ingredient2)

        with pytest.raises(IntegrityError):
            db_session.commit()

class TestProductModel:
    """Tests for Product model."""

    def test_create_product(self, db_session):
        """Test creating a product linked to ingredient."""
        # First create ingredient
        ingredient = Ingredient(
            display_name="Flour",
            slug="flour",
            category="Flour"
        )
        db_session.add(ingredient)
        db_session.flush()

        # Create product (display_name is a computed property, not a column)
        product = Product(
            ingredient_id=ingredient.id,
            brand="King Arthur",
            package_size="5 lb bag",
            package_unit="lb",
            package_unit_quantity=Decimal("5.0")
        )
        db_session.add(product)
        db_session.commit()

        assert product.id is not None
        assert product.brand == "King Arthur"
        assert product.ingredient_id == ingredient.id
        assert product.ingredient.display_name == "Flour"
        # display_name is computed from brand + package_size
        assert "King Arthur" in product.display_name

    def test_product_preferred_flag(self, db_session):
        """Test preferred product flag."""
        ingredient = Ingredient(
            display_name="Sugar",
            slug="sugar",
            category="Sugar"
        )
        db_session.add(ingredient)
        db_session.flush()

        product = Product(
            ingredient_id=ingredient.id,
            brand="Domino",
            package_size="5 lb bag",
            package_unit="lb",
            package_unit_quantity=Decimal("5.0"),
            preferred=True
        )
        db_session.add(product)
        db_session.commit()

        assert product.preferred is True

    def test_product_ingredient_relationship(self, db_session):
        """Test product-ingredient relationship navigation."""
        ingredient = Ingredient(
            display_name="Flour",
            slug="flour",
            category="Flour"
        )
        db_session.add(ingredient)
        db_session.flush()

        product1 = Product(
            ingredient_id=ingredient.id,
            brand="Brand A",
            package_size="5 lb",
            package_unit="lb",
            package_unit_quantity=Decimal("5.0")
        )
        product2 = Product(
            ingredient_id=ingredient.id,
            brand="Brand B",
            package_size="10 lb",
            package_unit="lb",
            package_unit_quantity=Decimal("10.0")
        )
        db_session.add_all([product1, product2])
        db_session.commit()
        db_session.refresh(ingredient)

        # Ingredient can access its products
        assert len(ingredient.products) == 2

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
            estimated_time_minutes=45
        )
        db_session.add(recipe)
        db_session.commit()

        assert recipe.id is not None
        assert recipe.name == "Chocolate Chip Cookies"
        assert recipe.yield_quantity == 48

    def test_recipe_with_ingredients(self, db_session):
        """Test recipe with ingredients (TD-001 schema)."""
        # Create ingredient
        flour = Ingredient(
            display_name="Flour",
            slug="flour",
            category="Flour"
        )
        db_session.add(flour)
        db_session.flush()

        # Create recipe
        recipe = Recipe(
            name="Cookies",
            category="Cookies",
            yield_quantity=24,
            yield_unit="cookies"
        )
        db_session.add(recipe)
        db_session.flush()

        # Add ingredient to recipe (TD-001: use ingredient_id not ingredient_new_id)
        recipe_ingredient = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=flour.id,
            quantity=2.0,
            unit="cup"
        )
        db_session.add(recipe_ingredient)
        db_session.commit()

        db_session.refresh(recipe)
        assert len(recipe.recipe_ingredients) == 1
        assert recipe.recipe_ingredients[0].ingredient.display_name == "Flour"

    def test_recipe_to_dict(self, db_session):
        """Test recipe dictionary serialization."""
        recipe = Recipe(
            name="Test Recipe",
            category="Cookies",
            yield_quantity=24,
            yield_unit="cookies"
        )
        db_session.add(recipe)
        db_session.commit()

        data = recipe.to_dict()
        assert data["name"] == "Test Recipe"
        assert data["category"] == "Cookies"

class TestRecipeIngredientModel:
    """Tests for RecipeIngredient model (TD-001 schema)."""

    def test_create_recipe_ingredient(self, db_session):
        """Test creating recipe ingredient junction."""
        ingredient = Ingredient(
            display_name="Flour",
            slug="flour",
            category="Flour"
        )
        recipe = Recipe(
            name="Cookies",
            category="Cookies",
            yield_quantity=24,
            yield_unit="cookies"
        )
        db_session.add_all([ingredient, recipe])
        db_session.flush()

        recipe_ingredient = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            quantity=3.0,
            unit="cup",
            notes="Sifted"
        )
        db_session.add(recipe_ingredient)
        db_session.commit()

        assert recipe_ingredient.id is not None
        assert recipe_ingredient.quantity == 3.0
        assert recipe_ingredient.notes == "Sifted"
        assert recipe_ingredient.ingredient.display_name == "Flour"

    def test_recipe_ingredient_relationship(self, db_session):
        """Test recipe ingredient navigates to both recipe and ingredient."""
        ingredient = Ingredient(
            display_name="Sugar",
            slug="sugar",
            category="Sugar"
        )
        recipe = Recipe(
            name="Cake",
            category="Cakes",
            yield_quantity=12,
            yield_unit="slices"
        )
        db_session.add_all([ingredient, recipe])
        db_session.flush()

        recipe_ingredient = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            quantity=1.5,
            unit="cup"
        )
        db_session.add(recipe_ingredient)
        db_session.commit()
        db_session.refresh(recipe_ingredient)

        assert recipe_ingredient.recipe.name == "Cake"
        assert recipe_ingredient.ingredient.display_name == "Sugar"

class TestInventoryItemModel:
    """Tests for InventoryItem model (TD-001 schema)."""

    def test_create_inventory_item(self, db_session):
        """Test creating an inventory item with product_id."""
        ingredient = Ingredient(
            display_name="Flour",
            slug="flour",
            category="Flour"
        )
        db_session.add(ingredient)
        db_session.flush()

        product = Product(
            ingredient_id=ingredient.id,
            brand="King Arthur",
            package_size="5 lb",
            package_unit="lb",
            package_unit_quantity=Decimal("5.0")
        )
        db_session.add(product)
        db_session.flush()

        inventory_item = InventoryItem(
            product_id=product.id,
            quantity=5.0,
            unit_cost=8.99
        )
        db_session.add(inventory_item)
        db_session.commit()

        assert inventory_item.id is not None
        assert inventory_item.product_id == product.id
        assert inventory_item.quantity == 5.0

    def test_inventory_item_navigates_to_product(self, db_session):
        """Test inventory item can navigate to product and ingredient."""
        ingredient = Ingredient(
            display_name="Sugar",
            slug="sugar",
            category="Sugar"
        )
        db_session.add(ingredient)
        db_session.flush()

        product = Product(
            ingredient_id=ingredient.id,
            brand="Domino",
            package_size="5 lb",
            package_unit="lb",
            package_unit_quantity=Decimal("5.0")
        )
        db_session.add(product)
        db_session.flush()

        inventory_item = InventoryItem(
            product_id=product.id,
            quantity=3.5
        )
        db_session.add(inventory_item)
        db_session.commit()
        db_session.refresh(inventory_item)

        # Navigate through relationships
        assert inventory_item.product.brand == "Domino"
        assert inventory_item.product.ingredient.display_name == "Sugar"

class TestPurchaseModel:
    """Tests for Purchase model (TD-001 schema)."""

    def test_create_purchase(self, db_session):
        """Test creating a purchase with product_id."""
        ingredient = Ingredient(
            display_name="Butter",
            slug="butter",
            category="Dairy"
        )
        db_session.add(ingredient)
        db_session.flush()

        product = Product(
            ingredient_id=ingredient.id,
            brand="Land O Lakes",
            package_size="1 lb",
            package_unit="lb",
            package_unit_quantity=Decimal("1.0")
        )
        db_session.add(product)
        db_session.flush()

        from datetime import date

        purchase = Purchase(
            product_id=product.id,
            purchase_date=date.today(),
            quantity_purchased=2.0,
            unit_cost=5.99,
            total_cost=11.98,
            supplier="Test Store"
        )
        db_session.add(purchase)
        db_session.commit()

        assert purchase.id is not None
        assert purchase.product_id == product.id
        assert purchase.unit_cost == 5.99

class TestInventorySnapshotModel:
    """Tests for InventorySnapshot model."""

    def test_create_snapshot(self, db_session):
        """Test creating an inventory snapshot."""
        snapshot = InventorySnapshot(
            name="Pre-Christmas 2025",
            description="Test snapshot"
        )
        db_session.add(snapshot)
        db_session.commit()

        assert snapshot.id is not None
        assert snapshot.name == "Pre-Christmas 2025"
        assert snapshot.snapshot_date is not None

    def test_snapshot_with_ingredients(self, db_session):
        """Test snapshot with ingredients."""
        ingredient = Ingredient(
            display_name="Flour",
            slug="flour",
            category="Flour"
        )
        db_session.add(ingredient)
        db_session.flush()

        snapshot = InventorySnapshot(name="Test Snapshot")
        db_session.add(snapshot)
        db_session.flush()

        snap_ingredient = SnapshotIngredient(
            snapshot_id=snapshot.id,
            ingredient_id=ingredient.id,
            quantity=3.0
        )
        db_session.add(snap_ingredient)
        db_session.commit()
        db_session.refresh(snapshot)

        assert len(snapshot.snapshot_ingredients) == 1
        assert snapshot.snapshot_ingredients[0].quantity == 3.0

class TestModelRelationships:
    """Tests for relationships between models."""

    def test_ingredient_to_recipe_relationship(self, db_session):
        """Test ingredient can access recipes that use it."""
        ingredient = Ingredient(
            display_name="Flour",
            slug="flour",
            category="Flour"
        )
        recipe = Recipe(
            name="Cookies",
            category="Cookies",
            yield_quantity=24,
            yield_unit="cookies"
        )
        db_session.add_all([ingredient, recipe])
        db_session.flush()

        recipe_ingredient = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            quantity=2.0,
            unit="cup"
        )
        db_session.add(recipe_ingredient)
        db_session.commit()
        db_session.refresh(ingredient)

        assert len(ingredient.recipe_ingredients) == 1
        assert ingredient.recipe_ingredients[0].recipe.name == "Cookies"

    def test_recipe_cascade_delete(self, db_session):
        """Test that deleting recipe cascades to recipe_ingredients."""
        ingredient = Ingredient(
            display_name="Flour",
            slug="flour",
            category="Flour"
        )
        recipe = Recipe(
            name="Cookies",
            category="Cookies",
            yield_quantity=24,
            yield_unit="cookies"
        )
        db_session.add_all([ingredient, recipe])
        db_session.flush()

        recipe_ingredient = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            quantity=2.0,
            unit="cup"
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

    def test_ingredient_to_products_relationship(self, db_session):
        """Test ingredient can access its products (TD-001)."""
        ingredient = Ingredient(
            display_name="Flour",
            slug="flour",
            category="Flour"
        )
        db_session.add(ingredient)
        db_session.flush()

        product1 = Product(
            ingredient_id=ingredient.id,
            brand="Brand A",
            package_size="5 lb",
            package_unit="lb",
            package_unit_quantity=Decimal("5.0")
        )
        product2 = Product(
            ingredient_id=ingredient.id,
            brand="Brand B",
            package_size="10 lb",
            package_unit="lb",
            package_unit_quantity=Decimal("10.0")
        )
        db_session.add_all([product1, product2])
        db_session.commit()
        db_session.refresh(ingredient)

        assert len(ingredient.products) == 2
        brands = [p.brand for p in ingredient.products]
        assert "Brand A" in brands
        assert "Brand B" in brands

    def test_product_cascade_delete(self, db_session):
        """Test that deleting ingredient cascades to products."""
        ingredient = Ingredient(
            display_name="Sugar",
            slug="sugar",
            category="Sugar"
        )
        db_session.add(ingredient)
        db_session.flush()

        product = Product(
            ingredient_id=ingredient.id,
            brand="Domino",
            package_size="5 lb",
            package_unit="lb",
            package_unit_quantity=Decimal("5.0")
        )
        db_session.add(product)
        db_session.commit()

        ingredient_id = ingredient.id

        # Delete ingredient
        db_session.delete(ingredient)
        db_session.commit()

        # Product should also be deleted (cascade)
        remaining = db_session.query(Product).filter_by(ingredient_id=ingredient_id).count()
        assert remaining == 0
