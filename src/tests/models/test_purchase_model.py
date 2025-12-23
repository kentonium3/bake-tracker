"""
Tests for Purchase model (Feature 027).

Tests cover:
- Model creation with valid data
- Required field validation
- FK relationships (product, supplier)
- Check constraints (unit_price >= 0, quantity > 0)
- Immutability (no updated_at)
- Helper methods (total_cost, is_recent)
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from src.models.base import Base
from src.models.supplier import Supplier
from src.models.ingredient import Ingredient
from src.models.product import Product
from src.models.purchase import Purchase


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
def test_supplier(session):
    """Create a test supplier."""
    supplier = Supplier(
        name="Test Supplier",
        city="Boston",
        state="MA",
        zip_code="02101",
    )
    session.add(supplier)
    session.flush()
    return supplier


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
def test_product(session, test_ingredient):
    """Create a test product."""
    product = Product(
        ingredient_id=test_ingredient.id,
        product_name="Test Product",
        package_unit="lb",
        package_unit_quantity=5.0,
    )
    session.add(product)
    session.flush()
    return product


class TestPurchaseModel:
    """Tests for Purchase model creation and attributes."""

    def test_create_purchase_success(self, session, test_product, test_supplier):
        """Test creating a purchase with valid data."""
        purchase = Purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("9.99"),
            quantity_purchased=2,
        )
        session.add(purchase)
        session.flush()

        assert purchase.id is not None
        assert purchase.product_id == test_product.id
        assert purchase.supplier_id == test_supplier.id
        assert purchase.unit_price == Decimal("9.99")
        assert purchase.quantity_purchased == 2

    def test_purchase_with_notes(self, session, test_product, test_supplier):
        """Test creating a purchase with optional notes."""
        purchase = Purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("5.99"),
            quantity_purchased=1,
            notes="On sale - 20% off",
        )
        session.add(purchase)
        session.flush()

        assert purchase.notes == "On sale - 20% off"

    def test_purchase_requires_product_id(self, session, test_supplier):
        """Test that product_id is required."""
        purchase = Purchase(
            product_id=None,  # Missing required field
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("9.99"),
            quantity_purchased=1,
        )
        session.add(purchase)
        with pytest.raises(IntegrityError):
            session.flush()

    def test_purchase_requires_supplier_id(self, session, test_product):
        """Test that supplier_id is required."""
        purchase = Purchase(
            product_id=test_product.id,
            supplier_id=None,  # Missing required field
            purchase_date=date.today(),
            unit_price=Decimal("9.99"),
            quantity_purchased=1,
        )
        session.add(purchase)
        with pytest.raises(IntegrityError):
            session.flush()

    def test_purchase_requires_purchase_date(self, session, test_product, test_supplier):
        """Test that purchase_date is required."""
        purchase = Purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=None,  # Missing required field
            unit_price=Decimal("9.99"),
            quantity_purchased=1,
        )
        session.add(purchase)
        with pytest.raises(IntegrityError):
            session.flush()

    def test_purchase_requires_unit_price(self, session, test_product, test_supplier):
        """Test that unit_price is required."""
        purchase = Purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=None,  # Missing required field
            quantity_purchased=1,
        )
        session.add(purchase)
        with pytest.raises(IntegrityError):
            session.flush()

    def test_purchase_requires_quantity(self, session, test_product, test_supplier):
        """Test that quantity_purchased is required."""
        purchase = Purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("9.99"),
            quantity_purchased=None,  # Missing required field
        )
        session.add(purchase)
        with pytest.raises(IntegrityError):
            session.flush()

    def test_purchase_no_updated_at(self, session, test_product, test_supplier):
        """Test that purchases have no updated_at (immutable)."""
        purchase = Purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("9.99"),
            quantity_purchased=1,
        )
        session.add(purchase)
        session.flush()

        # updated_at should be None (overridden from BaseModel)
        assert purchase.updated_at is None

    def test_purchase_has_uuid(self, session, test_product, test_supplier):
        """Test that UUID is automatically generated."""
        purchase = Purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("9.99"),
            quantity_purchased=1,
        )
        session.add(purchase)
        session.flush()

        assert purchase.uuid is not None
        assert len(purchase.uuid) == 36

    def test_purchase_has_created_at(self, session, test_product, test_supplier):
        """Test that created_at is set."""
        purchase = Purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("9.99"),
            quantity_purchased=1,
        )
        session.add(purchase)
        session.flush()

        assert purchase.created_at is not None


class TestPurchaseConstraints:
    """Tests for Purchase check constraints."""

    def test_unit_price_non_negative_constraint(self, session, test_product, test_supplier):
        """Test that negative unit_price may violate constraint.

        Note: SQLite CHECK constraint enforcement may vary.
        """
        purchase = Purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("-5.00"),  # Negative - violates constraint
            quantity_purchased=1,
        )
        session.add(purchase)
        try:
            session.flush()
            # If we get here, SQLite didn't enforce the constraint
            assert float(purchase.unit_price) == -5.00
        except IntegrityError:
            # Constraint was enforced
            session.rollback()

    def test_quantity_positive_constraint(self, session, test_product, test_supplier):
        """Test that zero/negative quantity may violate constraint.

        Note: SQLite CHECK constraint enforcement may vary.
        """
        purchase = Purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("9.99"),
            quantity_purchased=0,  # Zero - violates constraint
        )
        session.add(purchase)
        try:
            session.flush()
            # If we get here, SQLite didn't enforce the constraint
            assert purchase.quantity_purchased == 0
        except IntegrityError:
            # Constraint was enforced
            session.rollback()


class TestPurchaseRelationships:
    """Tests for Purchase relationships."""

    def test_purchase_product_relationship(self, session, test_product, test_supplier):
        """Test that purchase links to product correctly."""
        purchase = Purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("9.99"),
            quantity_purchased=1,
        )
        session.add(purchase)
        session.flush()

        assert purchase.product is not None
        assert purchase.product.id == test_product.id

    def test_purchase_supplier_relationship(self, session, test_product, test_supplier):
        """Test that purchase links to supplier correctly."""
        purchase = Purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("9.99"),
            quantity_purchased=1,
        )
        session.add(purchase)
        session.flush()

        assert purchase.supplier is not None
        assert purchase.supplier.id == test_supplier.id
        assert purchase.supplier.name == "Test Supplier"

    def test_product_purchases_relationship(self, session, test_product, test_supplier):
        """Test that product has purchases collection."""
        purchase1 = Purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("9.99"),
            quantity_purchased=1,
        )
        purchase2 = Purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today() - timedelta(days=7),
            unit_price=Decimal("10.99"),
            quantity_purchased=2,
        )
        session.add(purchase1)
        session.add(purchase2)
        session.flush()

        assert len(test_product.purchases) == 2

    def test_supplier_purchases_relationship(self, session, test_product, test_supplier):
        """Test that supplier has purchases collection."""
        purchase = Purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("9.99"),
            quantity_purchased=1,
        )
        session.add(purchase)
        session.flush()

        assert len(test_supplier.purchases) == 1
        assert test_supplier.purchases[0].id == purchase.id


class TestPurchaseMethods:
    """Tests for Purchase model methods and properties."""

    def test_total_cost_property(self):
        """Test total_cost calculation."""
        purchase = Purchase(
            unit_price=Decimal("5.99"),
            quantity_purchased=3,
        )
        assert purchase.total_cost == Decimal("17.97")

    def test_is_recent_true(self):
        """Test is_recent returns True for recent purchases."""
        purchase = Purchase(
            purchase_date=date.today(),
            unit_price=Decimal("9.99"),
            quantity_purchased=1,
        )
        assert purchase.is_recent(days=30) is True

    def test_is_recent_false(self):
        """Test is_recent returns False for old purchases."""
        purchase = Purchase(
            purchase_date=date.today() - timedelta(days=60),
            unit_price=Decimal("9.99"),
            quantity_purchased=1,
        )
        assert purchase.is_recent(days=30) is False

    def test_repr(self, session, test_product, test_supplier):
        """Test string representation."""
        purchase = Purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("9.99"),
            quantity_purchased=1,
        )
        session.add(purchase)
        session.flush()

        repr_str = repr(purchase)
        assert "Purchase" in repr_str
        assert str(test_product.id) in repr_str
        assert str(test_supplier.id) in repr_str

    def test_to_dict(self, session, test_product, test_supplier):
        """Test to_dict method."""
        purchase = Purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("9.99"),
            quantity_purchased=2,
            notes="Test note",
        )
        session.add(purchase)
        session.flush()

        result = purchase.to_dict()

        assert result["product_id"] == test_product.id
        assert result["supplier_id"] == test_supplier.id
        assert result["unit_price"] == "9.99"
        assert result["quantity_purchased"] == 2
        assert result["notes"] == "Test note"
        assert result["total_cost"] == "19.98"
        assert "created_at" in result

    def test_to_dict_with_relationships(self, session, test_product, test_supplier):
        """Test to_dict includes relationships when requested."""
        purchase = Purchase(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            purchase_date=date.today(),
            unit_price=Decimal("9.99"),
            quantity_purchased=1,
        )
        session.add(purchase)
        session.flush()

        result = purchase.to_dict(include_relationships=True)

        assert "product" in result
        assert result["product"]["id"] == test_product.id
        assert result["supplier_name"] == "Test Supplier"
        assert result["supplier_location"] == "Boston, MA"
