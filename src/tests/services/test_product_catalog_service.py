"""Tests for Product Catalog Service (Feature 027).

Tests cover:
- Get products with filters (FR-014 through FR-018)
- Get product with last price
- Create product
- Update product
- Hide/unhide products (FR-003)
- Delete product with dependency checks (FR-004, FR-005)
- Purchase history (FR-012)
- Create purchase (FR-011)
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.base import Base
from src.models.supplier import Supplier
from src.models.ingredient import Ingredient
from src.models.product import Product
from src.models.purchase import Purchase
from src.models.inventory_item import InventoryItem
from src.models.recipe import Recipe, RecipeIngredient
from src.services import product_catalog_service
from src.services.product_catalog_service import ProductDependencies
from src.services.exceptions import ProductNotFound


@pytest.fixture
def engine():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create database session for testing."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def test_ingredient(session):
    """Create a test ingredient."""
    ingredient = Ingredient(
        display_name="Test Flour",
        slug="test-flour",
        category="Flour",
    )
    session.add(ingredient)
    session.flush()
    return ingredient


@pytest.fixture
def test_ingredient_butter(session):
    """Create another test ingredient."""
    ingredient = Ingredient(
        display_name="Butter",
        slug="butter",
        category="Dairy",
    )
    session.add(ingredient)
    session.flush()
    return ingredient


@pytest.fixture
def test_supplier(session):
    """Create a test supplier."""
    supplier = Supplier(
        name="Costco",
        city="Issaquah",
        state="WA",
        zip_code="98027",
    )
    session.add(supplier)
    session.flush()
    return supplier


@pytest.fixture
def test_supplier_wegmans(session):
    """Create another test supplier."""
    supplier = Supplier(
        name="Wegmans",
        city="Rochester",
        state="NY",
        zip_code="14624",
    )
    session.add(supplier)
    session.flush()
    return supplier


@pytest.fixture
def test_product(session, test_ingredient):
    """Create a test product."""
    product = Product(
        ingredient_id=test_ingredient.id,
        product_name="King Arthur Flour 25lb",
        package_unit="lb",
        package_unit_quantity=25.0,
        brand="King Arthur",
        is_hidden=False,
    )
    session.add(product)
    session.flush()
    return product


@pytest.fixture
def test_product_hidden(session, test_ingredient):
    """Create a hidden test product."""
    product = Product(
        ingredient_id=test_ingredient.id,
        product_name="Generic Flour 10lb",
        package_unit="lb",
        package_unit_quantity=10.0,
        brand="Generic",
        is_hidden=True,
    )
    session.add(product)
    session.flush()
    return product


class TestGetProducts:
    """Tests for get_products function."""

    def test_get_products_excludes_hidden(self, session, test_product, test_product_hidden):
        """Test that hidden products are excluded by default (FR-018)."""
        results = product_catalog_service.get_products(session=session)

        assert len(results) == 1
        assert results[0]["product_name"] == "King Arthur Flour 25lb"

    def test_get_products_includes_hidden(self, session, test_product, test_product_hidden):
        """Test that hidden products can be included (FR-018)."""
        results = product_catalog_service.get_products(
            include_hidden=True,
            session=session,
        )

        assert len(results) == 2

    def test_get_products_filter_by_ingredient(self, session, test_product, test_ingredient, test_ingredient_butter):
        """Test filtering by ingredient ID (FR-014)."""
        # Create product for different ingredient
        butter_product = Product(
            ingredient_id=test_ingredient_butter.id,
            product_name="Costco Butter",
            package_unit="lb",
            package_unit_quantity=1.0,
        )
        session.add(butter_product)
        session.flush()

        results = product_catalog_service.get_products(
            ingredient_id=test_ingredient.id,
            session=session,
        )

        assert len(results) == 1
        assert results[0]["ingredient_id"] == test_ingredient.id

    def test_get_products_filter_by_category(self, session, test_product, test_ingredient, test_ingredient_butter):
        """Test filtering by ingredient category (FR-015)."""
        butter_product = Product(
            ingredient_id=test_ingredient_butter.id,
            product_name="Costco Butter",
            package_unit="lb",
            package_unit_quantity=1.0,
        )
        session.add(butter_product)
        session.flush()

        results = product_catalog_service.get_products(
            category="Flour",
            session=session,
        )

        assert len(results) == 1
        assert results[0]["product_name"] == "King Arthur Flour 25lb"

    def test_get_products_filter_by_supplier(self, session, test_product, test_supplier):
        """Test filtering by preferred supplier ID (FR-016)."""
        # Update product to have preferred supplier
        test_product.preferred_supplier_id = test_supplier.id
        session.flush()

        results = product_catalog_service.get_products(
            supplier_id=test_supplier.id,
            session=session,
        )

        assert len(results) == 1
        assert results[0]["preferred_supplier_id"] == test_supplier.id

    def test_get_products_search_by_name(self, session, test_product, test_ingredient):
        """Test searching by product name (FR-017)."""
        # Create another product
        product2 = Product(
            ingredient_id=test_ingredient.id,
            product_name="Bobs Red Mill Flour",
            package_unit="lb",
            package_unit_quantity=5.0,
            brand="Bobs Red Mill",
        )
        session.add(product2)
        session.flush()

        results = product_catalog_service.get_products(
            search="King",
            session=session,
        )

        assert len(results) == 1
        assert "King" in results[0]["product_name"]

    def test_get_products_search_by_brand(self, session, test_product, test_ingredient):
        """Test searching by brand name (FR-017)."""
        product2 = Product(
            ingredient_id=test_ingredient.id,
            product_name="Premium Flour",
            package_unit="lb",
            package_unit_quantity=5.0,
            brand="Bobs Red Mill",
        )
        session.add(product2)
        session.flush()

        results = product_catalog_service.get_products(
            search="Bobs",
            session=session,
        )

        assert len(results) == 1
        assert results[0]["brand"] == "Bobs Red Mill"

    def test_get_products_with_last_price(self, session, test_product, test_supplier):
        """Test that products include last purchase price."""
        # Create a purchase
        purchase = Purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("12.99"),
            quantity_purchased=1,
        )
        session.add(purchase)
        session.flush()

        results = product_catalog_service.get_products(session=session)

        assert len(results) == 1
        assert results[0]["last_price"] == 12.99
        assert results[0]["last_purchase_date"] is not None


class TestGetProductWithLastPrice:
    """Tests for get_product_with_last_price function."""

    def test_get_product_with_last_price_success(self, session, test_product, test_supplier):
        """Test getting a product with purchase price."""
        purchase = Purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("12.99"),
            quantity_purchased=1,
        )
        session.add(purchase)
        session.flush()

        result = product_catalog_service.get_product_with_last_price(
            test_product.id,
            session=session,
        )

        assert result is not None
        assert result["product_name"] == "King Arthur Flour 25lb"
        assert result["last_price"] == 12.99

    def test_get_product_with_last_price_no_purchases(self, session, test_product):
        """Test getting a product with no purchases."""
        result = product_catalog_service.get_product_with_last_price(
            test_product.id,
            session=session,
        )

        assert result is not None
        assert result["last_price"] is None

    def test_get_product_not_found(self, session):
        """Test getting non-existent product returns None."""
        result = product_catalog_service.get_product_with_last_price(999, session=session)
        assert result is None


class TestCreateProduct:
    """Tests for create_product function."""

    def test_create_product_success(self, session, test_ingredient):
        """Test creating a product."""
        result = product_catalog_service.create_product(
            product_name="New Product",
            ingredient_id=test_ingredient.id,
            package_unit="lb",
            package_unit_quantity=10.0,
            brand="Test Brand",
            session=session,
        )

        assert result["product_name"] == "New Product"
        assert result["ingredient_id"] == test_ingredient.id
        assert result["is_hidden"] is False
        assert "id" in result

    def test_create_product_with_supplier(self, session, test_ingredient, test_supplier):
        """Test creating a product with preferred supplier."""
        result = product_catalog_service.create_product(
            product_name="New Product",
            ingredient_id=test_ingredient.id,
            package_unit="lb",
            package_unit_quantity=10.0,
            preferred_supplier_id=test_supplier.id,
            session=session,
        )

        assert result["preferred_supplier_id"] == test_supplier.id

    def test_create_product_duplicate_gtin_fails(self, session, test_ingredient):
        """Test that creating a product with duplicate GTIN fails."""
        from src.services.exceptions import ValidationError

        # Create first product with GTIN
        product_catalog_service.create_product(
            product_name="First Product",
            ingredient_id=test_ingredient.id,
            package_unit="lb",
            package_unit_quantity=10.0,
            gtin="123456789012",
            session=session,
        )

        # Try to create second product with same GTIN - should fail
        with pytest.raises(ValidationError) as exc_info:
            product_catalog_service.create_product(
                product_name="Second Product",
                ingredient_id=test_ingredient.id,
                package_unit="oz",
                package_unit_quantity=5.0,
                gtin="123456789012",
                session=session,
            )

        assert "GTIN 123456789012 is already used" in str(exc_info.value)

    def test_create_product_duplicate_upc_fails(self, session, test_ingredient):
        """Test that creating a product with duplicate UPC fails."""
        from src.services.exceptions import ValidationError

        # Create first product with UPC
        product_catalog_service.create_product(
            product_name="First Product",
            ingredient_id=test_ingredient.id,
            package_unit="lb",
            package_unit_quantity=10.0,
            upc_code="987654321098",
            session=session,
        )

        # Try to create second product with same UPC - should fail
        with pytest.raises(ValidationError) as exc_info:
            product_catalog_service.create_product(
                product_name="Second Product",
                ingredient_id=test_ingredient.id,
                package_unit="oz",
                package_unit_quantity=5.0,
                upc_code="987654321098",
                session=session,
            )

        assert "UPC 987654321098 is already used" in str(exc_info.value)


class TestUpdateProduct:
    """Tests for update_product function."""

    def test_update_product_success(self, session, test_product):
        """Test updating a product."""
        result = product_catalog_service.update_product(
            test_product.id,
            brand="Updated Brand",
            session=session,
        )

        assert result["brand"] == "Updated Brand"

    def test_update_product_multiple_fields(self, session, test_product):
        """Test updating multiple fields."""
        result = product_catalog_service.update_product(
            test_product.id,
            brand="New Brand",
            product_name="New Name",
            session=session,
        )

        assert result["brand"] == "New Brand"
        assert result["product_name"] == "New Name"

    def test_update_product_not_found(self, session):
        """Test updating non-existent product raises error."""
        with pytest.raises(ProductNotFound) as exc_info:
            product_catalog_service.update_product(999, brand="Test", session=session)

        assert exc_info.value.product_id == 999

    def test_update_product_keeps_same_gtin(self, session, test_ingredient):
        """Test that updating a product with its existing GTIN succeeds."""
        # Create product with GTIN
        result = product_catalog_service.create_product(
            product_name="Test Product",
            ingredient_id=test_ingredient.id,
            package_unit="lb",
            package_unit_quantity=10.0,
            gtin="718444190707",
            session=session,
        )
        product_id = result["id"]

        # Update product keeping same GTIN - should succeed
        updated = product_catalog_service.update_product(
            product_id,
            product_name="Updated Name",
            gtin="718444190707",  # Same GTIN
            session=session,
        )

        assert updated["product_name"] == "Updated Name"
        assert updated["gtin"] == "718444190707"

    def test_update_product_duplicate_gtin_fails(self, session, test_ingredient):
        """Test that changing to another product's GTIN fails."""
        from src.services.exceptions import ValidationError

        # Create first product with GTIN
        product_catalog_service.create_product(
            product_name="First Product",
            ingredient_id=test_ingredient.id,
            package_unit="lb",
            package_unit_quantity=10.0,
            gtin="111111111111",
            session=session,
        )

        # Create second product with different GTIN
        result = product_catalog_service.create_product(
            product_name="Second Product",
            ingredient_id=test_ingredient.id,
            package_unit="oz",
            package_unit_quantity=5.0,
            gtin="222222222222",
            session=session,
        )
        product2_id = result["id"]

        # Try to update second product with first product's GTIN - should fail
        with pytest.raises(ValidationError) as exc_info:
            product_catalog_service.update_product(
                product2_id,
                gtin="111111111111",
                session=session,
            )

        assert "GTIN 111111111111 is already used" in str(exc_info.value)

    def test_update_product_new_unique_gtin_succeeds(self, session, test_ingredient):
        """Test that changing to a unique GTIN succeeds."""
        # Create product without GTIN
        result = product_catalog_service.create_product(
            product_name="Test Product",
            ingredient_id=test_ingredient.id,
            package_unit="lb",
            package_unit_quantity=10.0,
            session=session,
        )
        product_id = result["id"]

        # Add GTIN to product - should succeed
        updated = product_catalog_service.update_product(
            product_id,
            gtin="333333333333",
            session=session,
        )

        assert updated["gtin"] == "333333333333"


class TestHideUnhideProduct:
    """Tests for hide_product and unhide_product functions."""

    def test_hide_product_success(self, session, test_product):
        """Test hiding a product (FR-003)."""
        result = product_catalog_service.hide_product(test_product.id, session=session)

        assert result["is_hidden"] is True

    def test_unhide_product_success(self, session, test_product_hidden):
        """Test unhiding a product (FR-003)."""
        result = product_catalog_service.unhide_product(test_product_hidden.id, session=session)

        assert result["is_hidden"] is False

    def test_hide_product_not_found(self, session):
        """Test hiding non-existent product raises error."""
        with pytest.raises(ProductNotFound):
            product_catalog_service.hide_product(999, session=session)

    def test_unhide_product_not_found(self, session):
        """Test unhiding non-existent product raises error."""
        with pytest.raises(ProductNotFound):
            product_catalog_service.unhide_product(999, session=session)


class TestDeleteProduct:
    """Tests for delete_product function."""

    def test_delete_product_success(self, session, test_ingredient):
        """Test deleting a product with no dependencies."""
        product = Product(
            ingredient_id=test_ingredient.id,
            product_name="To Delete",
            package_unit="lb",
            package_unit_quantity=1.0,
        )
        session.add(product)
        session.flush()
        product_id = product.id

        result = product_catalog_service.delete_product(product_id, session=session)

        assert result is True

        # Verify product is gone
        deleted = session.query(Product).filter(Product.id == product_id).first()
        assert deleted is None

    def test_delete_product_with_purchases_fails(self, session, test_product, test_supplier):
        """Test that deleting product with purchases raises error (FR-004)."""
        purchase = Purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("9.99"),
            quantity_purchased=1,
        )
        session.add(purchase)
        session.flush()

        with pytest.raises(ValueError) as exc_info:
            product_catalog_service.delete_product(test_product.id, session=session)

        assert "1 purchases" in str(exc_info.value)
        assert "Hide instead" in str(exc_info.value)

    def test_delete_product_with_inventory_fails(self, session, test_product):
        """Test that deleting product with inventory raises error (FR-005)."""
        inventory = InventoryItem(
            product_id=test_product.id,
            quantity=5.0,
        )
        session.add(inventory)
        session.flush()

        with pytest.raises(ValueError) as exc_info:
            product_catalog_service.delete_product(test_product.id, session=session)

        assert "1 inventory items" in str(exc_info.value)
        assert "Hide instead" in str(exc_info.value)

    def test_delete_product_not_found(self, session):
        """Test deleting non-existent product raises error."""
        with pytest.raises(ProductNotFound):
            product_catalog_service.delete_product(999, session=session)


class TestPurchaseHistory:
    """Tests for get_purchase_history function."""

    def test_get_purchase_history(self, session, test_product, test_supplier):
        """Test getting purchase history (FR-012)."""
        # Create multiple purchases
        purchase1 = Purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today() - timedelta(days=7),
            unit_price=Decimal("10.99"),
            quantity_purchased=1,
        )
        purchase2 = Purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("12.99"),
            quantity_purchased=2,
        )
        session.add(purchase1)
        session.add(purchase2)
        session.flush()

        results = product_catalog_service.get_purchase_history(
            test_product.id,
            session=session,
        )

        # Should be sorted by date DESC (newest first)
        assert len(results) == 2
        assert results[0]["unit_price"] == "12.99"  # More recent
        assert results[1]["unit_price"] == "10.99"  # Older

    def test_get_purchase_history_includes_supplier_info(self, session, test_product, test_supplier):
        """Test that purchase history includes supplier details."""
        purchase = Purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("12.99"),
            quantity_purchased=1,
        )
        session.add(purchase)
        session.flush()

        results = product_catalog_service.get_purchase_history(
            test_product.id,
            session=session,
        )

        assert len(results) == 1
        assert results[0]["supplier_name"] == "Costco"
        assert results[0]["supplier_location"] == "Issaquah, WA"

    def test_get_purchase_history_empty(self, session, test_product):
        """Test getting purchase history for product with no purchases."""
        results = product_catalog_service.get_purchase_history(
            test_product.id,
            session=session,
        )

        assert results == []


class TestCreatePurchase:
    """Tests for create_purchase function."""

    def test_create_purchase_success(self, session, test_product, test_supplier):
        """Test creating a purchase (FR-011)."""
        result = product_catalog_service.create_purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("12.99"),
            quantity_purchased=2,
            session=session,
        )

        assert result["product_id"] == test_product.id
        assert result["supplier_id"] == test_supplier.id
        assert result["unit_price"] == "12.99"
        assert result["quantity_purchased"] == 2
        assert result["total_cost"] == "25.98"

    def test_create_purchase_with_notes(self, session, test_product, test_supplier):
        """Test creating a purchase with notes."""
        result = product_catalog_service.create_purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("9.99"),
            quantity_purchased=1,
            notes="On sale",
            session=session,
        )

        assert result["notes"] == "On sale"

    def test_create_purchase_validates_negative_price(self, session, test_product, test_supplier):
        """Test that negative prices are rejected."""
        with pytest.raises(ValueError) as exc_info:
            product_catalog_service.create_purchase(
                product_id=test_product.id,
                supplier_id=test_supplier.id,
                purchase_date=date.today(),
                unit_price=Decimal("-5.00"),
                quantity_purchased=1,
                session=session,
            )

        assert "negative" in str(exc_info.value)

    def test_create_purchase_validates_zero_quantity(self, session, test_product, test_supplier):
        """Test that zero quantity is rejected."""
        with pytest.raises(ValueError) as exc_info:
            product_catalog_service.create_purchase(
                product_id=test_product.id,
                supplier_id=test_supplier.id,
                purchase_date=date.today(),
                unit_price=Decimal("10.00"),
                quantity_purchased=0,
                session=session,
            )

        assert "positive" in str(exc_info.value)

    def test_create_purchase_validates_negative_quantity(self, session, test_product, test_supplier):
        """Test that negative quantity is rejected."""
        with pytest.raises(ValueError) as exc_info:
            product_catalog_service.create_purchase(
                product_id=test_product.id,
                supplier_id=test_supplier.id,
                purchase_date=date.today(),
                unit_price=Decimal("10.00"),
                quantity_purchased=-1,
                session=session,
            )

        assert "positive" in str(exc_info.value)


class TestConvenienceMethods:
    """Tests for convenience methods."""

    def test_get_products_by_category(self, session, test_product, test_ingredient):
        """Test get_products_by_category convenience method."""
        results = product_catalog_service.get_products_by_category(
            "Flour",
            session=session,
        )

        assert len(results) == 1
        assert results[0]["product_name"] == "King Arthur Flour 25lb"

    def test_get_product_or_raise_success(self, session, test_product):
        """Test get_product_or_raise returns product."""
        result = product_catalog_service.get_product_or_raise(
            test_product.id,
            session=session,
        )

        assert result["product_name"] == "King Arthur Flour 25lb"

    def test_get_product_or_raise_not_found(self, session):
        """Test get_product_or_raise raises exception."""
        with pytest.raises(ProductNotFound) as exc_info:
            product_catalog_service.get_product_or_raise(999, session=session)

        assert exc_info.value.product_id == 999


class TestForceDeleteProduct:
    """Tests for force delete functionality with dependency analysis."""

    @pytest.fixture
    def product_with_purchase(self, session, test_ingredient, test_supplier):
        """Create a product with a purchase record."""
        product = Product(
            ingredient_id=test_ingredient.id,
            brand="Test Brand",
            product_name="Test Product With Purchase",
            package_unit="lb",
            package_unit_quantity=5.0,
        )
        session.add(product)
        session.flush()

        purchase = Purchase(
            product_id=product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("10.00"),
            quantity_purchased=1,
        )
        session.add(purchase)
        session.flush()

        return product

    @pytest.fixture
    def product_with_inventory(self, session, test_ingredient, test_supplier):
        """Create a product with an inventory item."""
        product = Product(
            ingredient_id=test_ingredient.id,
            brand="Test Brand",
            product_name="Test Product With Inventory",
            package_unit="oz",
            package_unit_quantity=16.0,
        )
        session.add(product)
        session.flush()

        # Purchase is required for inventory
        purchase = Purchase(
            product_id=product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("5.00"),
            quantity_purchased=2,
        )
        session.add(purchase)
        session.flush()

        inventory = InventoryItem(
            product_id=product.id,
            purchase_id=purchase.id,
            quantity=2.0,
            unit_cost=5.00,
            purchase_date=date.today(),
        )
        session.add(inventory)
        session.flush()

        return product

    @pytest.fixture
    def product_in_recipe(self, session, test_ingredient, test_supplier):
        """Create a product whose ingredient is used in a recipe."""
        product = Product(
            ingredient_id=test_ingredient.id,
            brand="Recipe Brand",
            product_name="Test Product In Recipe",
            package_unit="cup",
            package_unit_quantity=2.0,
        )
        session.add(product)
        session.flush()

        # Create a recipe that uses this ingredient
        recipe = Recipe(
            name="Test Recipe",
            category="Cookies",
            yield_quantity=12,
            yield_unit="cookies",
        )
        session.add(recipe)
        session.flush()

        # Link recipe to ingredient
        recipe_ingredient = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=test_ingredient.id,
            quantity=2.0,
            unit="cups",
        )
        session.add(recipe_ingredient)
        session.flush()

        return product

    def test_analyze_dependencies_no_dependencies(self, session, test_product):
        """Test analyzing product with no dependencies."""
        deps = product_catalog_service.analyze_product_dependencies(
            test_product.id,
            session=session,
        )

        assert isinstance(deps, ProductDependencies)
        assert deps.product_id == test_product.id
        assert deps.purchase_count == 0
        assert deps.inventory_count == 0
        assert deps.recipe_count == 0
        assert deps.can_force_delete is True
        assert deps.deletion_risk_level == "LOW"

    def test_analyze_dependencies_with_purchase(
        self, session, product_with_purchase, test_supplier
    ):
        """Test analyzing product with purchase record."""
        deps = product_catalog_service.analyze_product_dependencies(
            product_with_purchase.id,
            session=session,
        )

        assert deps.purchase_count == 1
        assert deps.has_valid_purchases is True
        assert deps.has_supplier_data is True
        assert deps.deletion_risk_level == "MEDIUM"
        assert len(deps.purchases) == 1
        assert deps.purchases[0]["price"] == 10.0

    def test_analyze_dependencies_with_inventory(
        self, session, product_with_inventory
    ):
        """Test analyzing product with inventory items."""
        deps = product_catalog_service.analyze_product_dependencies(
            product_with_inventory.id,
            session=session,
        )

        assert deps.inventory_count == 1
        assert deps.purchase_count == 1
        assert len(deps.inventory_items) == 1
        assert deps.inventory_items[0]["qty"] == 2.0

    def test_analyze_dependencies_used_in_recipe(
        self, session, product_in_recipe
    ):
        """Test analyzing product whose ingredient is used in recipe."""
        deps = product_catalog_service.analyze_product_dependencies(
            product_in_recipe.id,
            session=session,
        )

        assert deps.recipe_count == 1
        assert deps.is_used_in_recipes is True
        assert deps.can_force_delete is False
        assert deps.deletion_risk_level == "BLOCKED"
        assert "Test Recipe" in deps.recipes

    def test_force_delete_requires_confirmation(
        self, session, product_with_purchase
    ):
        """Test that force delete requires confirmed=True."""
        with pytest.raises(ValueError) as exc_info:
            product_catalog_service.force_delete_product(
                product_with_purchase.id,
                confirmed=False,
                session=session,
            )

        assert "confirmed=True" in str(exc_info.value)

    def test_force_delete_blocked_by_recipe(
        self, session, product_in_recipe
    ):
        """Test that products used in recipes cannot be force deleted."""
        with pytest.raises(ValueError) as exc_info:
            product_catalog_service.force_delete_product(
                product_in_recipe.id,
                confirmed=True,
                session=session,
            )

        assert "used in" in str(exc_info.value).lower()
        assert "recipe" in str(exc_info.value).lower()

    def test_force_delete_success_with_purchase(
        self, session, product_with_purchase, test_supplier
    ):
        """Test successful force delete of product with purchase."""
        product_id = product_with_purchase.id

        # Verify product and purchase exist
        assert session.query(Product).filter(Product.id == product_id).count() == 1
        assert session.query(Purchase).filter(Purchase.product_id == product_id).count() == 1

        # Force delete
        deps = product_catalog_service.force_delete_product(
            product_id,
            confirmed=True,
            session=session,
        )

        # Verify deleted
        assert deps.purchase_count == 1
        assert session.query(Product).filter(Product.id == product_id).count() == 0
        assert session.query(Purchase).filter(Purchase.product_id == product_id).count() == 0

    def test_force_delete_success_with_inventory(
        self, session, product_with_inventory
    ):
        """Test successful force delete of product with inventory."""
        product_id = product_with_inventory.id

        # Verify all exist
        assert session.query(Product).filter(Product.id == product_id).count() == 1
        assert session.query(Purchase).filter(Purchase.product_id == product_id).count() == 1
        assert session.query(InventoryItem).filter(InventoryItem.product_id == product_id).count() == 1

        # Force delete
        deps = product_catalog_service.force_delete_product(
            product_id,
            confirmed=True,
            session=session,
        )

        # Verify all deleted
        assert deps.inventory_count == 1
        assert deps.purchase_count == 1
        assert session.query(Product).filter(Product.id == product_id).count() == 0
        assert session.query(Purchase).filter(Purchase.product_id == product_id).count() == 0
        assert session.query(InventoryItem).filter(InventoryItem.product_id == product_id).count() == 0

    def test_force_delete_not_found(self, session):
        """Test force delete of non-existent product."""
        with pytest.raises(ProductNotFound):
            product_catalog_service.force_delete_product(
                999,
                confirmed=True,
                session=session,
            )


# =============================================================================
# Feature 031: Leaf-Only Ingredient Validation Tests
# =============================================================================

@pytest.fixture
def hierarchy_ingredients_catalog(session):
    """Create a sample ingredient hierarchy for testing leaf-only validation.

    Creates:
    - Chocolate (level 0, root)
      - Dark Chocolate (level 1, mid-tier)
        - Semi-Sweet Chips (level 2, leaf)
    """
    # Root category
    chocolate = Ingredient(
        display_name="Catalog Chocolate",
        slug="catalog-chocolate",
        category="Chocolate",
        hierarchy_level=0,
        parent_ingredient_id=None,
    )
    session.add(chocolate)
    session.flush()

    # Mid-tier category
    dark_chocolate = Ingredient(
        display_name="Catalog Dark Chocolate",
        slug="catalog-dark-chocolate",
        category="Chocolate",
        hierarchy_level=1,
        parent_ingredient_id=chocolate.id,
    )
    session.add(dark_chocolate)
    session.flush()

    # Leaf ingredient
    semi_sweet = Ingredient(
        display_name="Catalog Semi-Sweet Chips",
        slug="catalog-semi-sweet-chips",
        category="Chocolate",
        hierarchy_level=2,
        parent_ingredient_id=dark_chocolate.id,
    )
    session.add(semi_sweet)
    session.flush()

    class HierarchyData:
        def __init__(self, root, mid, leaf):
            self.root = root
            self.mid = mid
            self.leaf = leaf

    return HierarchyData(chocolate, dark_chocolate, semi_sweet)


class TestLeafOnlyProductCatalogValidation:
    """Tests for leaf-only ingredient enforcement in product catalog (Feature 031)."""

    def test_create_product_with_leaf_ingredient_succeeds(
        self, session, hierarchy_ingredients_catalog
    ):
        """Creating product with leaf ingredient (level 2) succeeds."""
        result = product_catalog_service.create_product(
            product_name="Test Leaf Product",
            ingredient_id=hierarchy_ingredients_catalog.leaf.id,
            package_unit="bag",
            package_unit_quantity=12.0,
            brand="Test Brand",
            session=session,
        )
        assert result is not None
        assert result["ingredient_id"] == hierarchy_ingredients_catalog.leaf.id

    def test_create_product_with_non_leaf_fails(
        self, session, hierarchy_ingredients_catalog
    ):
        """Creating product with non-leaf ingredient raises NonLeafIngredientError."""
        from src.services.exceptions import NonLeafIngredientError

        with pytest.raises(NonLeafIngredientError) as exc_info:
            product_catalog_service.create_product(
                product_name="Test Root Product",
                ingredient_id=hierarchy_ingredients_catalog.root.id,
                package_unit="bag",
                package_unit_quantity=12.0,
                brand="Test Brand",
                session=session,
            )
        assert "Catalog Chocolate" in str(exc_info.value)

    def test_create_product_with_mid_tier_fails(
        self, session, hierarchy_ingredients_catalog
    ):
        """Creating product with mid-tier ingredient raises NonLeafIngredientError."""
        from src.services.exceptions import NonLeafIngredientError

        with pytest.raises(NonLeafIngredientError) as exc_info:
            product_catalog_service.create_product(
                product_name="Test Mid Product",
                ingredient_id=hierarchy_ingredients_catalog.mid.id,
                package_unit="bag",
                package_unit_quantity=12.0,
                brand="Test Brand",
                session=session,
            )
        assert "Catalog Dark Chocolate" in str(exc_info.value)

    def test_update_product_ingredient_to_non_leaf_fails(
        self, session, hierarchy_ingredients_catalog
    ):
        """Updating product to use non-leaf ingredient raises NonLeafIngredientError."""
        from src.services.exceptions import NonLeafIngredientError

        # First create a product with the leaf ingredient
        product = product_catalog_service.create_product(
            product_name="Test Update Product",
            ingredient_id=hierarchy_ingredients_catalog.leaf.id,
            package_unit="bag",
            package_unit_quantity=12.0,
            brand="Test Brand",
            session=session,
        )

        # Try to update to use the root (non-leaf) ingredient
        with pytest.raises(NonLeafIngredientError):
            product_catalog_service.update_product(
                product_id=product["id"],
                ingredient_id=hierarchy_ingredients_catalog.root.id,
                session=session,
            )
