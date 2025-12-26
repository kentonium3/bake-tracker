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
from src.services import product_catalog_service
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
